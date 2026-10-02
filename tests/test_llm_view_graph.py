"""End-to-end LLM-view graph on fixture data: PIT, hot swap, N accounting, replay."""
import json
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import pytest

from strategies._common.compose import replay
from strategies._common.graph.core import Context, GraphError
from strategies._common.graph.service import GraphService, default_registry, prepare_any
from strategies.llm_view_tx import graph_nodes as nodes

ROOT = Path(__file__).resolve().parents[1]
GRAPH = 'strategies/llm_view_tx/graph.json'


def fixture_graph(**overrides):
    graph = json.loads((ROOT / GRAPH).read_text(encoding='utf-8'))
    for node in graph['nodes']:
        p = node['params']
        if node['type'] == 'data.quantdata_futures':
            p.update(source='fixture', start='2023-01-02', end='2026-09-30', data_version='auto')
        if node['type'] == 'rag.research_context':
            p.update(backend='fixture')
        if node['type'] in ('agent.llm_view', 'pit.memorization_probe'):
            p.update(model='fixture-momentum', model_spec='auto')
        p.update(overrides.get(node['id'], {}))
    return graph


@pytest.fixture
def service(tmp_path):
    target = tmp_path / GRAPH
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(fixture_graph(), indent=2), encoding='utf-8')
    svc = GraphService(tmp_path, ledger_path=tmp_path / 'log' / 'trials.jsonl', cache_dir=tmp_path / 'cache')
    svc.load(GRAPH)
    return svc


def run(svc, preview=False):
    job = svc.start(preview=preview)
    svc._thread.join()
    return svc.job(job['id'])


def test_full_run_records_one_trial_and_replays(service):
    job = run(service)
    assert job['status'] == 'complete', job.get('message')
    states = service.engine.states
    assert {states[i]['status'] for i in ('data', 'view', 'docs', 'agent', 'backtest', 'probe')} <= {'recomputed'}
    assert service.ledger.summary()['selection_n'] == 1
    signals = service.engine.values['agent']['Signals']
    assert signals['clean_start'] == '2024-07-08'
    assert all(d >= '2024-07-08' for d in signals['traces'])            # contaminated dates never called
    returns = service.engine.values['backtest']['Returns']
    assert returns.index[0] >= pd.Timestamp('2024-07-08') + pd.offsets.BDay(60)
    frames = service.replay()
    assert frames['available'] and frames['cutoff'] == '2024-06-28'
    called = [c for c in frames['decisions'] if c['called']]
    assert called and all(c["reasoning"] and c["decision"]["parse_ok"] for c in called)
    assert {service.engine.values["agent"]["Signals"]["traces"][c["date"]]["reasoning_source"] for c in called} == {"analysis"}
    assert any(d['contaminated'] for d in frames['days']) and any(d['oos'] for d in frames['days'])
    assert not any(d['oos'] and d['contaminated'] for d in frames['days'])
    assert frames['probe']['leak_suspected'] is False
    sidecar = json.loads((service.root / job['sidecar']).read_text(encoding='utf-8'))
    assert sidecar['graph_hash'] == job['graph_hash']


def test_rerun_is_cached_and_hot_swap_is_a_new_trial(service):
    assert run(service)['status'] == 'complete'
    assert run(service)['status'] == 'complete'
    assert service.engine.states['agent']['status'] == 'cached'
    assert service.ledger.summary()['selection_n'] == 1
    # Downstream statistical declarations never add N.
    facts = next(n for n in service.graph['nodes'] if n['id'] == 'facts')['params']['family']
    other = next(v for v in default_registry().types['stat.facts'].params['family']['enum'] if v != facts)
    service.parameters('facts', {'family': other})
    assert run(service)['status'] == 'complete'
    assert service.ledger.summary()['selection_n'] == 1
    # Swapping the model is one parameter; the graph and wiring are untouched.
    service.parameters('agent', {'model': 'fixture-contrarian', 'model_spec': 'auto'})
    assert run(service)['status'] == 'complete'
    assert service.ledger.summary()['selection_n'] == 2
    signals = service.engine.values['agent']['Signals']
    assert signals['model'] == 'fixture-contrarian' and signals['clean_start'] == '2024-01-08'


def test_preview_calls_the_model_but_never_the_ledger(service):
    job = run(service, preview=True)
    assert job['status'] == 'complete', job.get('message')
    assert service.engine.states['agent']['status'] == 'recomputed'
    assert service.engine.states['backtest']['status'] == 'stale'
    assert service.ledger.summary()['selection_n'] == 0


def test_insufficient_clean_sample_fails_closed(tmp_path):
    graph = fixture_graph(backtest={'min_clean_oos_days': 5000})
    target = tmp_path / GRAPH
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(graph), encoding='utf-8')
    svc = GraphService(tmp_path, ledger_path=tmp_path / 'trials.jsonl', cache_dir=tmp_path / 'cache')
    svc.load(GRAPH)
    job = run(svc)
    assert job['status'] == 'error'
    assert '乾淨樣本外天數不足' in job['message']
    # Downstream nodes name the missing port and the upstream cause, all in Chinese.
    assert '缺少輸入：Returns（上游：模型知識截止後的乾淨樣本外天數不足' in job['message']
    assert 'missing' not in job['message'] and '操作失敗' not in job['message']
    assert svc.ledger.summary()['selection_n'] == 0


def test_contaminated_inspection_never_enters_returns(tmp_path):
    graph = prepare_any(fixture_graph(agent={'include_contaminated': True}))
    registry = default_registry()
    _, by_id, _, _ = registry.normalize(graph)
    ctx = Context(services={'root': tmp_path})
    p = {k: by_id[k]['params'] for k in by_id}
    bars = nodes.quantdata_futures({}, p['data'], ctx)
    view = nodes.market_view(bars, p['view'], ctx)
    docs = nodes.research_context(view, p['docs'], ctx)
    signals = nodes.llm_view({**view, **docs}, p['agent'], ctx)['Signals']
    dirty = [d for d, t in signals['traces'].items() if t['contaminated']]
    assert dirty, 'inspection mode should call the model on contaminated dates'
    assert signals['values'].loc[pd.to_datetime(dirty)].isna().all().all()


def test_signals_are_point_in_time(tmp_path):
    """Rewriting every bar after t must leave every decision at or before t unchanged."""
    graph = prepare_any(fixture_graph())
    _, by_id, _, _ = default_registry().normalize(graph)
    p = {k: by_id[k]['params'] for k in by_id}
    ctx = Context(services={'root': tmp_path})
    frame = nodes.load_bars(p['data'])
    t = pd.Timestamp('2025-06-30')
    tampered = frame.copy()
    after = tampered.index > t
    tampered.loc[after, 'ret'] = -tampered.loc[after, 'ret'] * 3
    tampered.loc[after, 'open_interest'] *= 2

    def signals(bars):
        source = dict(p['data'])
        view = nodes.market_view({'PriceBars': {'source': source, 'values': bars}}, p['view'], ctx)
        docs = nodes.research_context(view, p['docs'], ctx)
        return nodes.llm_view({**view, **docs}, p['agent'], ctx)['Signals']

    a, b = signals(frame), signals(tampered)
    upto = a['values'].index <= t
    pd.testing.assert_frame_equal(a['values'][upto], b['values'][upto])
    assert {d: a['traces'][d]['prompt'] for d in a['traces'] if d <= '2025-06-30'} == \
           {d: b['traces'][d]['prompt'] for d in b['traces'] if d <= '2025-06-30'}
    assert not a['values'][~upto].equals(b['values'][~upto])


def test_papers_backend_filters_by_knowledge_time(tmp_path):
    db = tmp_path / 'data' / 'papers.db'
    db.parent.mkdir()
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE papers (source TEXT, source_id TEXT, title TEXT, abstract TEXT, published TEXT, updated TEXT)')
        conn.executemany('INSERT INTO papers VALUES (?,?,?,?,?,?)', [
            ('arxiv', '1', 'Index futures momentum', 'momentum in index futures', '2024-01-10', None),
            ('arxiv', '2', 'Volatility trend reversal', 'volatility and trend reversal', 'Wed, 23 Sep 2026 01:00:01 -0700', None),
            ('arxiv', '3', 'Momentum revised later', 'momentum futures', '2023-01-01', '2025-12-01'),
            ('arxiv', '4', 'Undated momentum', 'momentum futures volatility', 'someday', None),
        ])
    view = {'MarketView': {'values': pd.DataFrame(index=pd.to_datetime(['2024-01-10', '2024-02-01', '2026-01-05'])),
                           'cadence': 'weekly', 'source': {}}}
    params = {'backend': 'papers', 'query': 'index futures momentum volatility trend reversal',
              'db_path': 'data/papers.db', 'top_k': 5, 'lag_days': 1, 'snippet_chars': 50}
    docs = nodes.research_context(view, params, Context(services={'root': tmp_path}))['Docs']
    ids = {d: [x['id'] for x in v] for d, v in docs['values'].items()}
    assert ids['2024-01-10'] == []                       # published that day: not yet visible
    assert ids['2024-02-01'] == ['arxiv:1']               # revised doc counts from its update date
    assert set(ids['2026-01-05']) == {'arxiv:1', 'arxiv:3'}
    assert docs['excluded_unknown_time'] == 1


def test_data_version_is_content_addressed():
    graph = prepare_any(fixture_graph())
    data = next(n for n in graph['nodes'] if n['type'] == 'data.quantdata_futures')
    assert data['params']['data_version'] == nodes.bars_version(nodes.load_bars(data['params']))
    with pytest.raises(GraphError, match='釘選'):
        nodes.quantdata_futures({}, {**data['params'], 'data_version': '0' * 16}, Context())
