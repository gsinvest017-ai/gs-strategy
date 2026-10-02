"""Point-in-time guards, CoT normalisation, call cache and the OpenAI-compatible provider."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading

import pandas as pd
import pytest

from strategies._common.compose import llm, pit, walkforward
from strategies._common.graph.core import GraphError


def test_clean_start_and_contamination_mask():
    start = pit.clean_start('2025-07-31', 5)            # Thursday
    assert start == pd.Timestamp('2025-08-08')          # 6 business days later
    mask = pit.contaminated(pd.bdate_range('2025-08-06', '2025-08-11'), '2025-07-31', 5)
    assert mask.tolist() == [True, True, False, False]   # Wed Thu | Fri Mon


def test_document_knowledge_time_fails_closed():
    assert pit.parse_time('2024-01-02') == pd.Timestamp('2024-01-02')
    assert pit.parse_time('Wed, 23 Sep 2026 01:00:01 -0700') == pd.Timestamp('2026-09-23 08:00:01')
    for bad in (None, '', 'soon', '2024-13-45'):
        assert pit.parse_time(bad) is None
    # The stored text is the latest revision: known from the later of the two dates.
    assert pit.knowledge_time('2024-01-02', '2025-03-01') == pd.Timestamp('2025-03-01')
    assert pit.knowledge_time(None, '2025-03-01') is None
    known = pd.Timestamp('2025-03-01')
    assert not pit.visible(known, '2025-03-01', lag_days=1)
    assert pit.visible(known, '2025-03-02', lag_days=1)
    assert not pit.visible(None, '2030-01-01')


def test_registry_rejects_non_http_base_urls(tmp_path):
    registry = tmp_path / 'models.yaml'
    registry.write_text("models:\n  evil:\n    provider: openai\n    base_url: file:///etc\n"
                        "    cutoff: '2025-01-31'\n", encoding='utf-8')
    with pytest.raises(GraphError, match='http'):
        pit.registry(registry)
    with pytest.raises(GraphError, match='http'):
        llm.OpenAICompatibleProvider({'base_url': 'file:///etc/passwd'}, {})


def test_registry_entries_are_pinned_individually():
    names = pit.model_names()
    assert {'fixture-momentum', 'fixture-contrarian', 'qwen3-235b-2507', 'qwen3.8-27b'} <= set(names)
    assert pit.spec_digest('fixture-momentum') != pit.spec_digest('fixture-contrarian')
    with pytest.raises(GraphError, match='unknown model'):
        pit.model_spec('nope')


@pytest.mark.parametrize('message, content, reasoning', [
    ({'content': '{"a": 1}', 'reasoning': '想一想'}, '{"a": 1}', '想一想'),
    ({'content': '{"a": 1}', 'reasoning_content': 'r'}, '{"a": 1}', 'r'),
    ({'content': '<think>先看動能</think>\n{"a": 1}'}, '{"a": 1}', '先看動能'),
    ({'content': '先看動能</think>{"a": 1}'}, '{"a": 1}', '先看動能'),
])
def test_reasoning_is_separated_from_the_answer(message, content, reasoning):
    out = llm.normalize_message(message)
    assert out == {'content': content, 'reasoning': reasoning}


def test_json_object_extraction():
    assert llm.parse_json_object('```json\n{"direction": "long", "confidence": 0.7}\n```') == {
        'direction': 'long', 'confidence': 0.7}
    assert llm.parse_json_object('答案如下 {"x": {"y": 2}} 以上') == {'x': {'y': 2}}
    assert llm.parse_json_object('{broken} then {"ok": true}') == {'ok': True}
    assert llm.parse_json_object('no json') is None


def test_call_cache_replays_without_calling_again(tmp_path, monkeypatch):
    cache = llm.CallCache(tmp_path)
    messages = [{'role': 'user', 'content': 'FEATURES: {"ret_20d_pct": 2.0, "vol_20d_pct": 1.0}'}]
    first = llm.chat('fixture-momentum', messages, cache=cache)
    assert not first['cached'] and '"long"' in first['content']
    monkeypatch.setattr(llm.FixtureProvider, 'complete', lambda *a, **k: pytest.fail('provider called'))
    second = llm.chat('fixture-momentum', messages, cache=cache)
    assert second['cached'] and second['content'] == first['content']
    swapped = llm.CallCache(tmp_path / 'other')
    monkeypatch.undo()
    assert '"short"' in llm.chat('fixture-contrarian', messages, cache=swapped)['content']


class _FakeVLLM(BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.seen.append({'ua': self.headers.get('User-Agent'), 'auth': self.headers.get('Authorization'),
                          'model': body['model']})
        payload = {'choices': [{'message': {'content': '{"direction": "flat", "confidence": 0.4}',
                                            'reasoning': '波動放大，先觀望'}}], 'usage': {'total_tokens': 9}}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def test_openai_compatible_provider_captures_reasoning_and_hides_key(tmp_path, monkeypatch):
    server = HTTPServer(('127.0.0.1', 0), _FakeVLLM)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        registry = tmp_path / 'models.yaml'
        registry.write_text(
            'api_key_env: TEST_LLM_KEY\nmodels:\n  local:\n    provider: openai\n'
            f'    base_url: http://127.0.0.1:{server.server_port}/v1\n    api_model: served-name\n'
            "    cutoff: '2025-01-31'\n", encoding='utf-8')
        monkeypatch.setenv('TEST_LLM_KEY', 'sk-test-secret')
        cache = llm.CallCache(tmp_path / 'calls')
        out = llm.chat('local', [{'role': 'user', 'content': 'hi'}], cache=cache, path=registry)
        assert out['reasoning'] == '波動放大，先觀望' and out['usage'] == {'total_tokens': 9}
        assert _FakeVLLM.seen[-1] == {'ua': llm.USER_AGENT, 'auth': 'Bearer sk-test-secret', 'model': 'served-name'}
        assert all('sk-test-secret' not in p.read_text(encoding='utf-8') for p in (tmp_path / 'calls').iterdir())
        monkeypatch.delenv('TEST_LLM_KEY')
        with pytest.raises(GraphError, match='API key unavailable'):
            llm.chat('local', [{'role': 'user', 'content': 'new prompt'}], cache=cache, path=registry)
    finally:
        server.shutdown()


def test_walk_forward_folds_and_in_sample_only_selection():
    days = pd.bdate_range('2025-01-01', periods=120)
    plan = walkforward.folds(days, train_days=40, test_days=20, embargo_days=1)
    tests = [f['test'] for f in plan]
    assert tests[0] == (41, 61) and all(a[1] == b[0] for a, b in zip(tests, tests[1:]))
    assert all(f['train'][0] == 0 and f['train'][1] == f['test'][0] - 1 for f in plan)
    rolling = walkforward.folds(days, train_days=40, test_days=20, embargo_days=1, scheme='rolling')
    assert all(f['train'][1] - f['train'][0] == 40 for f in rolling)

    bars = pd.DataFrame({'settle': 20000.0, 'close': 20000.0,
                         'ret': [0.01 if i % 2 else -0.004 for i in range(120)]}, index=days)
    signals = pd.DataFrame({'direction': 1.0, 'confidence': [0.9 if i % 3 else 0.5 for i in range(120)]}, index=days)
    sim = {'capital_base': 1e9, 'point_value': 200, 'fee_per_contract': 0, 'slippage_points': 0}
    _, _, table = walkforward.run(signals, bars, grid=[0.0, 0.8], exposure=1.0, train_days=40, test_days=20,
                                  embargo_days=1, scheme='anchored', sim=sim)
    # Tampering with out-of-sample returns must not change the threshold chosen for that fold.
    tampered = bars.copy()
    tampered.iloc[61:, tampered.columns.get_loc('ret')] = -0.05
    _, _, table2 = walkforward.run(signals, tampered, grid=[0.0, 0.8], exposure=1.0, train_days=40,
                                   test_days=20, embargo_days=1, scheme='anchored', sim=sim)
    assert table[0]['chosen_threshold'] == table2[0]['chosen_threshold']
    assert table[0]['is_sharpe'] == table2[0]['is_sharpe']
