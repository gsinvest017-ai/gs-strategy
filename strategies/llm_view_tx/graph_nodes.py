"""LLM-view strategy on TX: QUANTDATA + research RAG -> hot-swappable LLM -> walk-forward.

Pipeline (each line is a node type, ports are parametric types):

    data.quantdata_futures   ()                         -> PriceBars
    feature.market_view      PriceBars                  -> MarketView
    rag.research_context     MarketView                 -> Docs
    agent.llm_view           MarketView, Docs           -> Signals[llm]
    backtest.walk_forward    Signals, PriceBars         -> Returns, Positions, WalkForward
    pit.memorization_probe   PriceBars                  -> ProbeReport      (diagnostic)

Every value the LLM sees for decision date *d* is computed from rows dated
<= *d* and documents known before *d*; decision dates within the model's
knowledge cutoff (+ buffer) are never called or scored unless explicitly
requested for inspection, and even then never enter ``Returns``.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
import json
import math
from pathlib import Path
import re
import sqlite3

import numpy as np
import pandas as pd

from strategies._common.graph.core import GraphError, NodeType, digest
from strategies._common.compose import llm, pit, walkforward

HERE = Path(__file__).parent
COMPOSE = Path(pit.__file__).parent
SUPPORTED_ROOTS = ('TX', 'MTX')

SYSTEM_PROMPT = ('你是一位嚴謹的量化研究員。只能根據使用者提供的數字與研究摘要做判斷；'
                 '不要使用任何你對特定日期、事件或價格走勢的記憶。輸出必須是單一 JSON 物件。')


# --------------------------------------------------------------------- data

def _fixture_bars(root, start, end, seed=20261002):
    """Synthetic daily futures with mild, regime-switching momentum (offline tests/UI)."""
    days = pd.bdate_range('2022-01-03', '2026-09-30')
    rng = np.random.default_rng(seed)
    drift = np.repeat(rng.choice([-0.0008, 0.0002, 0.0009], size=len(days) // 40 + 1), 40)[:len(days)]
    noise = rng.normal(0, 0.011, len(days))
    ret = drift + noise + 0.08 * np.r_[0, noise[:-1]]
    settle = 15000 * np.cumprod(1 + ret)
    frame = pd.DataFrame({'close': settle * (1 + rng.normal(0, 0.0005, len(days))), 'settle': settle,
                          'ret': ret, 'volume': rng.integers(60000, 140000, len(days)).astype(float),
                          'open_interest': 90000 + np.cumsum(rng.normal(0, 800, len(days))),
                          'contract': [f'{root}{d.year}{d.month:02d}' for d in days]}, index=days)
    return frame.loc[pd.Timestamp(start):pd.Timestamp(end)]


def _quantdata_bars(root, start, end):
    from strategies._common import qd
    raw = qd.futures_continuous(root, start, end)
    if raw.empty:
        raise GraphError('QUANTDATA 在指定區間沒有資料')
    frame = pd.DataFrame({
        'close': pd.to_numeric(raw['close'], errors='coerce').to_numpy(),
        'settle': pd.to_numeric(raw['settle'], errors='coerce').to_numpy(),
        # roi is settle-to-settle on the same contract, in percent: no roll jumps.
        'ret': pd.to_numeric(raw['roi'], errors='coerce').to_numpy() / 100.0,
        'volume': pd.to_numeric(raw['volume'], errors='coerce').to_numpy(),
        'open_interest': pd.to_numeric(raw['open_interest'], errors='coerce').to_numpy(),
        'contract': raw['contract_code'].astype(str).to_numpy(),
    }, index=pd.DatetimeIndex(pd.to_datetime(raw['trading_date'])).tz_localize(None))
    return frame[~frame.index.duplicated(keep='last')].sort_index()


def load_bars(p):
    if p['root'] not in SUPPORTED_ROOTS:
        raise GraphError('root must be TX or MTX')
    loader = _fixture_bars if p['source'] == 'fixture' else _quantdata_bars
    frame = loader(p['root'], p['start'], p['end'])
    frame['ret'] = frame['ret'].fillna(0.0)
    return frame


def bars_version(frame):
    return digest(json.loads(frame.to_json(orient='split', date_format='iso')))[:16]


def quantdata_futures(inputs, p, ctx):
    frame = load_bars(p)
    if p['data_version'] in ('auto', 'initial'):
        raise GraphError('pin data_version with prepare_graph before execution')
    if bars_version(frame) != p['data_version']:
        raise GraphError('QUANTDATA 資料內容與釘選的版本不同，請重新執行預判')
    return {'PriceBars': {'source': dict(p), 'values': frame, 'knowledge': 'close'}}


# ----------------------------------------------------------------- features

def decision_dates(index, cadence):
    s = pd.Series(index, index=index)
    if cadence == 'daily':
        return pd.DatetimeIndex(index)
    rule = {'weekly': 'W-FRI', 'monthly': 'ME'}[cadence]
    return pd.DatetimeIndex(s.groupby(pd.Grouper(freq=rule)).last().dropna().to_numpy())


def view_row(history):
    """Features at the last row of ``history`` using nothing after it."""
    level = (1 + history['ret']).cumprod()
    def ret(n):
        return float((level.iloc[-1] / level.iloc[-1 - n] - 1) * 100) if len(level) > n else None
    daily = history['ret']
    vol20 = float(daily.tail(20).std(ddof=1) * 100) if len(daily) >= 20 else None
    vol60 = float(daily.tail(60).std(ddof=1) * 100) if len(daily) >= 60 else None
    oi = history['open_interest']
    volume = history['volume'].tail(20)
    return {
        'ret_5d_pct': ret(5), 'ret_20d_pct': ret(20), 'ret_60d_pct': ret(60),
        'vol_20d_pct': vol20, 'vol_ratio_20_60': (vol20 / vol60) if vol20 and vol60 else None,
        'drawdown_60d_pct': float((level.iloc[-1] / level.tail(60).max() - 1) * 100),
        'oi_change_20d_pct': float((oi.iloc[-1] / oi.iloc[-21] - 1) * 100) if len(oi) > 20 and oi.iloc[-21] else None,
        'volume_z_20': float((volume.iloc[-1] - volume.mean()) / volume.std(ddof=1)) if len(volume) >= 20 and volume.std(ddof=1) else None,
    }


def market_view(inputs, p, ctx):
    bars = inputs['PriceBars']
    frame = bars['values']
    dates = decision_dates(frame.index, p['cadence'])
    dates = dates[dates >= frame.index[0] + pd.offsets.BDay(p['warmup_days'])]
    rows = {}
    for d in dates:
        ctx.check_cancelled()
        rows[d] = view_row(frame.loc[:d])
    values = pd.DataFrame.from_dict(rows, orient='index').round(4)
    return {'MarketView': {'source': bars['source'], 'values': values, 'cadence': p['cadence']}}


# ---------------------------------------------------------------------- RAG

FIXTURE_DOCS = [
    {'id': 'fixture:tsmom', 'title': 'Time-series momentum in equity index futures',
     'abstract': 'Past 12-month and 1-month returns predict index futures returns; volatility scaling improves the Sharpe ratio.',
     'published': '2022-06-01'},
    {'id': 'fixture:volreg', 'title': 'Volatility regimes and trend persistence',
     'abstract': 'Trend signals weaken when short-term volatility rises sharply relative to its longer average.',
     'published': '2023-03-15'},
    {'id': 'fixture:drawdown', 'title': 'Drawdown-conditioned reversal in Asian index futures',
     'abstract': 'Deep 60-day drawdowns are followed by partial reversal; momentum crashes cluster after rebounds.',
     'published': '2024-02-20'},
    {'id': 'fixture:oi', 'title': 'Open interest growth and futures returns',
     'abstract': 'Rising open interest alongside positive returns signals trend continuation in index futures.',
     'published': '2025-01-10'},
    {'id': 'fixture:llm', 'title': 'Language models as discretionary overlays',
     'abstract': 'LLM judgements add value only out of sample after the model knowledge cutoff; earlier periods leak.',
     'published': '2025-11-05'},
]

_WORD = re.compile(r'[A-Za-z][A-Za-z\-]+|[一-鿿]')


def _tokens(text):
    return [w.lower() for w in _WORD.findall(text or '')]


def _bm25(query, docs, k1=1.5, b=0.75):
    terms = set(_tokens(query))
    bodies = [_tokens(d['title'] + ' ' + d['abstract']) for d in docs]
    if not bodies:
        return []
    avg = sum(map(len, bodies)) / len(bodies) or 1
    scores = []
    for body in bodies:
        score = 0.0
        for t in terms:
            df = sum(t in other for other in bodies)
            tf = body.count(t)
            if tf:
                idf = math.log(1 + (len(bodies) - df + 0.5) / (df + 0.5))
                score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(body) / avg))
        scores.append(score)
    return scores


def _papers(path):
    if not path.is_file():
        raise GraphError('找不到論文資料庫 papers.db')
    with sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True) as conn:
        rows = conn.execute('SELECT source, source_id, title, abstract, published, updated FROM papers').fetchall()
    return [{'id': f'{s}:{i}', 'title': t, 'abstract': a or '', 'published': pub, 'updated': upd}
            for s, i, t, a, pub, upd in rows]


def _gs_rag(root, query):
    try:
        from gs_rag import get_retriever
    except ImportError as exc:
        raise GraphError('gs-rag 未安裝，無法使用 gs_rag 後端') from exc
    retriever, _ = get_retriever(Path(root) / 'data' / 'gsrag.db', backend='bm25')
    docs = []
    for hit in retriever.search(query, where=None, top_k=200):
        meta = hit.get('metadata') or {}
        year = str(meta.get('year') or '')
        # Only a year is indexed: assume the document is known from the next 1 January.
        published = f'{int(year) + 1}-01-01' if year.isdigit() else None
        docs.append({'id': str(hit.get('id') or meta.get('source_id')), 'title': meta.get('title', ''),
                     'abstract': hit.get('text', ''), 'published': published})
    return docs


def research_context(inputs, p, ctx):
    view = inputs['MarketView']
    root = Path(ctx.services.get('root', Path.cwd()))
    if p['backend'] == 'none':
        docs = []
    elif p['backend'] == 'fixture':
        docs = copy.deepcopy(FIXTURE_DOCS)
    elif p['backend'] == 'papers':
        docs = _papers(root / p['db_path'])
    else:
        docs = _gs_rag(root, p['query'])
    for doc, score in zip(docs, _bm25(p['query'], docs)):
        doc['score'] = round(score, 4)
        doc['knowledge_time'] = pit.knowledge_time(doc.get('published'), doc.get('updated'))
    ranked = sorted((d for d in docs if d['score'] > 0 and d['knowledge_time'] is not None),
                    key=lambda d: (-d['score'], d['id']))
    values = {}
    for d in view['values'].index:
        chosen = [x for x in ranked if pit.visible(x['knowledge_time'], d, p['lag_days'])][:p['top_k']]
        values[d.date().isoformat()] = [{'id': x['id'], 'title': x['title'], 'score': x['score'],
                                         'knowledge_time': x['knowledge_time'].date().isoformat(),
                                         'snippet': x['abstract'][:p['snippet_chars']]} for x in chosen]
    return {'Docs': {'source': {'backend': p['backend'], 'query': p['query']}, 'values': values,
                     'excluded_unknown_time': sum(d['knowledge_time'] is None for d in docs)}}


# -------------------------------------------------------------------- agent

def build_messages(date, features, docs, *, anonymize, cadence):
    instrument = '某股價指數期貨（已匿名，不提供名稱與日期）' if anonymize else '台灣加權指數期貨（台指期 TX）近月'
    lines = [f'標的：{instrument}']
    if not anonymize:
        lines.append(f'決策日：{date}（收盤後決策，持有到下一個決策日）')
    else:
        lines.append('收盤後決策，持有到下一個決策日。')
    lines.append(f'決策頻率：{ {"daily": "每日", "weekly": "每週", "monthly": "每月"}[cadence] }')
    clean = {k: (None if v is None or (isinstance(v, float) and not math.isfinite(v)) else round(float(v), 3))
             for k, v in features.items()}
    lines.append('FEATURES: ' + json.dumps(clean, ensure_ascii=False, sort_keys=True))
    lines.append('欄位：報酬與波動單位為 %，drawdown 為距 60 日高點的跌幅，volume_z 為成交量 20 日 z 分數。')
    if docs:
        lines.append('相關研究摘要（皆在決策日之前已公開）：')
        lines.extend(f'- {d["title"]}：{d["snippet"]}' for d in docs)
    # Non-reasoning models return no CoT channel; the analysis field is the
    # written-out reasoning for them and a summary for reasoning models.
    lines.append('只輸出一個 JSON 物件：{"analysis": "逐步分析：先看趨勢、再看波動與回撤、再看籌碼、最後對照研究摘要（3 到 6 句）", '
                 '"direction": "long" | "short" | "flat", "confidence": 0 到 1 的數字, "rationale": "一句話結論"}')
    return [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': '\n'.join(lines)}]


def parse_decision(content):
    value = llm.parse_json_object(content) or {}
    direction = {'long': 1.0, 'short': -1.0, 'flat': 0.0}.get(str(value.get('direction', '')).lower())
    try:
        confidence = float(value.get('confidence'))
    except (TypeError, ValueError):
        confidence = None
    ok = direction is not None and confidence is not None and 0 <= confidence <= 1
    return {'direction': direction if ok else 0.0, 'confidence': confidence if ok else 0.0,
            'rationale': str(value.get('rationale', ''))[:300],
            'analysis': str(value.get('analysis', ''))[:2000], 'parse_ok': ok}


def _cache(ctx):
    return llm.CallCache(Path(ctx.services.get('root', Path.cwd())) / '.cache' / 'llm-calls')


def _check_spec(p):
    if p['model_spec'] in ('auto', 'initial'):
        raise GraphError('pin model_spec with prepare_graph before execution')
    if pit.spec_digest(p['model']) != p['model_spec']:
        raise GraphError('模型登錄表中此模型的設定已變更，請重新執行預判')


def llm_view(inputs, p, ctx):
    _check_spec(p)
    view, docs = inputs['MarketView'], inputs['Docs']
    spec = pit.model_spec(p['model'])
    start = pit.clean_start(spec['cutoff'], p['buffer_days'])
    dates = list(view['values'].index)
    dirty = {d for d in dates if d < start}
    todo = [d for d in dates if d not in dirty or p['include_contaminated']]
    cache = _cache(ctx)

    def call(d):
        ctx.check_cancelled()
        iso = d.date().isoformat()
        features = view['values'].loc[d].to_dict()
        messages = build_messages(iso, features, docs['values'].get(iso, []),
                                  anonymize=p['anonymize'], cadence=view['cadence'])
        reply = llm.chat(p['model'], messages, cache=cache, temperature=p['temperature'],
                         max_tokens=p['max_tokens'])
        return d, messages, reply

    traces, rows, done = {}, {}, 0
    with ThreadPoolExecutor(max_workers=max(1, int(spec.get('concurrency', 1)))) as pool:
        for d, messages, reply in pool.map(call, todo):
            decision = parse_decision(reply['content'])
            iso = d.date().isoformat()
            rows[d] = {'direction': decision['direction'], 'confidence': decision['confidence']}
            # CoT: the model's reasoning channel when it has one, else its written analysis.
            reasoning = reply['reasoning'] or decision['analysis']
            traces[iso] = {'prompt': messages[-1]['content'], 'reasoning': reasoning,
                           'reasoning_source': 'model' if reply['reasoning'] else ('analysis' if reasoning else 'none'),
                           'content': reply['content'], 'decision': decision, 'usage': reply.get('usage', {}),
                           'cached': reply['cached'], 'call_key': reply['call_key'],
                           'contaminated': d in dirty, 'docs': [x['id'] for x in docs['values'].get(iso, [])]}
            done += 1
            ctx.progress({'phase': 'llm', 'completed': done, 'total': len(todo)})
    values = pd.DataFrame.from_dict(rows, orient='index', columns=['direction', 'confidence'])
    values = values.reindex(dates)
    # Contaminated rows are blanked even when computed for inspection.
    values.loc[[d for d in dates if d in dirty]] = np.nan
    return {'Signals': {'source': view['source'], 'values': values, 'traces': traces, 'model': p['model'],
                        'cutoff': spec['cutoff'], 'cutoff_basis': spec.get('cutoff_basis', ''),
                        'clean_start': start.date().isoformat(),
                        'contaminated': sorted(d.date().isoformat() for d in dirty),
                        'anonymize': p['anonymize']}}


# ---------------------------------------------------------------- backtest

def walk_forward(inputs, p, ctx):
    signals, bars = inputs['Signals'], inputs['PriceBars']
    frame = bars['values']
    if signals['source'] != bars['source']:
        raise GraphError('Signals 與 PriceBars 的資料來源必須相同')
    grid = list(p['thresholds'])
    if not grid or any(isinstance(t, bool) or not isinstance(t, (int, float)) or not 0 <= t <= 1 for t in grid):
        raise GraphError('thresholds 必須是 0 到 1 之間的數字清單')
    clean = pd.Timestamp(signals['clean_start'])
    days = frame.index[frame.index >= clean]
    oos_days = len(days) - p['train_days'] - p['embargo_days']
    if oos_days < p['min_clean_oos_days']:
        raise GraphError(f'模型知識截止後的乾淨樣本外天數不足（{max(oos_days, 0)} < {p["min_clean_oos_days"]}）')
    sim = {'capital_base': p['capital_base'], 'point_value': p['point_value'],
           'fee_per_contract': p['fee_per_contract'], 'slippage_points': p['slippage_points']}
    returns, positions, table = walkforward.run(
        signals['values'], frame, grid=grid, exposure=p['exposure'], train_days=p['train_days'],
        test_days=p['test_days'], embargo_days=p['embargo_days'], scheme=p['scheme'], sim=sim, clean_start=clean)
    benchmark, _ = walkforward.simulate(pd.Series(p['exposure'], index=frame.index), frame, **sim)
    ctx.check_cancelled()
    summary = {'folds': table, 'model': signals['model'], 'cutoff': signals['cutoff'],
               'clean_start': signals['clean_start'], 'oos_start': returns.index[0].date().isoformat(),
               'oos_end': returns.index[-1].date().isoformat(), 'oos_days': len(returns),
               'oos_sharpe': walkforward.sharpe(returns),
               'benchmark_sharpe': walkforward.sharpe(benchmark.loc[returns.index]),
               'grid': grid, 'engine': 'vector-futures (research grade, not Zipline)'}
    return {'Returns': returns, 'Positions': positions.to_frame(bars['source']['root']),
            'WalkForward': {**summary, 'benchmark': benchmark.loc[returns.index]}}


# -------------------------------------------------------------------- probe

def memorization_probe(inputs, p, ctx):
    """Ask the model to *recall* settlement prices; recall before the cutoff that
    is much sharper than after it is evidence the model memorised the period."""
    _check_spec(p)
    frame = inputs['PriceBars']['values']
    spec = pit.model_spec(p['model'])
    start = pit.clean_start(spec['cutoff'], 0)
    rng = np.random.default_rng(p['seed'])
    pre = frame.index[frame.index < pd.Timestamp(spec['cutoff'])]
    post = frame.index[frame.index >= start]
    def sample(index):
        k = min(len(index), p['n_dates'])
        return sorted(rng.choice(index, size=k, replace=False)) if k else []
    cache = _cache(ctx)
    rows = []
    for group, dates in (('pre_cutoff', sample(pre)), ('post_cutoff', sample(post))):
        for d in dates:
            ctx.check_cancelled()
            d = pd.Timestamp(d)
            # A refusal hides memorisation, so a best guess is required.
            prompt = ('這是記憶測試（recall test），沒有提供任何資料：台灣期貨交易所台指期（TX）近月合約在 '
                      f'{d.date().isoformat()} 的結算價是多少點？即使不確定，也必須給出你最好的估計數字，不得拒答。'
                      '只輸出 JSON：{"close": 數字}')
            reply = llm.chat(p['model'], [{'role': 'user', 'content': prompt}], cache=cache,
                             temperature=0.0, max_tokens=p['max_tokens'])
            guess = (llm.parse_json_object(reply['content']) or {}).get('close')
            actual = float(frame.loc[d, 'settle'])
            error = abs(float(guess) / actual - 1) * 100 if isinstance(guess, (int, float)) and guess > 0 else None
            rows.append({'date': d.date().isoformat(), 'group': group, 'guess': guess, 'actual': actual,
                         'abs_pct_error': error})
    def stats(group):
        part = [r for r in rows if r['group'] == group]
        errors = [r['abs_pct_error'] for r in part if r['abs_pct_error'] is not None]
        return {'n': len(part), 'answered': len(errors),
                'median_abs_pct_error': float(np.median(errors)) if errors else None}
    pre_s, post_s = stats('pre_cutoff'), stats('post_cutoff')
    suspected = bool(pre_s['answered'] and pre_s['answered'] >= 0.5 * pre_s['n']
                     and pre_s['median_abs_pct_error'] is not None and pre_s['median_abs_pct_error'] < 3
                     and (post_s['median_abs_pct_error'] is None
                          or pre_s['median_abs_pct_error'] < 0.5 * post_s['median_abs_pct_error']))
    return {'ProbeReport': {'model': p['model'], 'cutoff': spec['cutoff'], 'pre_cutoff': pre_s,
                            'post_cutoff': post_s, 'leak_suspected': suspected, 'rows': rows,
                            'rule': '事前作答率 ≥ 50%、誤差中位數 < 3%，且明顯優於事後（< 0.5 倍）即視為疑似記憶'}}


# ----------------------------------------------------------------- registry

def prepare_graph(graph):
    """Pin data content and the selected model entries before identity is computed."""
    graph = copy.deepcopy(graph)
    for node in graph['nodes']:
        params = node.setdefault('params', {})
        if node['type'] == 'data.quantdata_futures' and params.get('data_version', 'auto') in ('auto', 'initial'):
            merged = {**_DATA_DEFAULTS, **params}
            params['data_version'] = bars_version(load_bars(merged))
        if node['type'] in ('agent.llm_view', 'pit.memorization_probe') and params.get('model_spec', 'auto') in ('auto', 'initial'):
            params['model_spec'] = pit.spec_digest(params.get('model', _MODEL_DEFAULT))
    return graph


_MODEL_DEFAULT = 'fixture-momentum'
_DATA_DEFAULTS = {'root': 'TX', 'source': 'quantdata', 'start': '2024-01-02', 'end': '2026-10-01',
                  'data_version': 'auto'}


def register_nodes(registry):
    def param(kind, default, **extra):
        return {'type': kind, 'default': default, **extra}
    models = pit.model_names()
    model = param('string', _MODEL_DEFAULT, enum=models)
    deps_core = (HERE / 'graph_nodes.py', COMPOSE / 'pit.py', COMPOSE / 'llm.py')
    specs = [
        ('data.quantdata_futures', {}, {'PriceBars': 'PriceBars'},
         {'root': param('string', 'TX', enum=list(SUPPORTED_ROOTS)),
          'source': param('string', 'quantdata', enum=['quantdata', 'fixture']),
          'start': param('string', _DATA_DEFAULTS['start']), 'end': param('string', _DATA_DEFAULTS['end']),
          'data_version': param('string', 'auto')}, quantdata_futures, deps_core),
        ('feature.market_view', {'PriceBars': 'PriceBars'}, {'MarketView': 'MarketView'},
         {'cadence': param('string', 'weekly', enum=['daily', 'weekly', 'monthly']),
          'warmup_days': param('integer', 61, minimum=21)}, market_view, deps_core),
        ('rag.research_context', {'MarketView': 'MarketView'}, {'Docs': 'Docs'},
         {'backend': param('string', 'papers', enum=['papers', 'gs_rag', 'fixture', 'none']),
          'query': param('string', 'index futures momentum volatility trend reversal'),
          'db_path': param('string', 'data/papers.db'), 'top_k': param('integer', 3, minimum=0, maximum=10),
          'lag_days': param('integer', 1, minimum=0), 'snippet_chars': param('integer', 240, minimum=40, maximum=1200)},
         research_context, deps_core),
        ('agent.llm_view', {'MarketView': 'MarketView', 'Docs': 'Docs'}, {'Signals': 'Signals[llm]'},
         {'model': model, 'model_spec': param('string', 'auto'), 'anonymize': param('boolean', True),
          'buffer_days': param('integer', 5, minimum=0), 'include_contaminated': param('boolean', False),
          'temperature': param('number', 0.0, minimum=0, maximum=2), 'max_tokens': param('integer', 2048, minimum=64)},
         llm_view, deps_core),
        ('backtest.walk_forward', {'Signals': 'Signals', 'PriceBars': 'PriceBars'},
         {'Returns': 'Returns', 'Positions': 'Positions', 'WalkForward': 'WalkForward'},
         {'scheme': param('string', 'anchored', enum=['anchored', 'rolling']),
          'train_days': param('integer', 60, minimum=10), 'test_days': param('integer', 21, minimum=5),
          'embargo_days': param('integer', 1, minimum=0), 'thresholds': param('array', [0.0, 0.6, 0.75]),
          'exposure': param('number', 1.0, minimum=0, maximum=3),
          'capital_base': param('number', 10_000_000, minimum=1), 'point_value': param('number', 200, minimum=1),
          'fee_per_contract': param('number', 250, minimum=0), 'slippage_points': param('number', 2, minimum=0),
          'min_clean_oos_days': param('integer', 60, minimum=1)},
         walk_forward, deps_core + (COMPOSE / 'walkforward.py',)),
        ('pit.memorization_probe', {'PriceBars': 'PriceBars'}, {'ProbeReport': 'ProbeReport'},
         {'model': model, 'model_spec': param('string', 'auto'), 'n_dates': param('integer', 8, minimum=1, maximum=40),
          'seed': param('integer', 7), 'max_tokens': param('integer', 1024, minimum=64)},
         memorization_probe, deps_core),
    ]
    for name, ins, outs, params, fn, deps in specs:
        registry.register(NodeType(name, ins, outs, params, fn, dependencies=deps))
