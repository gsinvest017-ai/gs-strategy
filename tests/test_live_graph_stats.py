import json

import numpy as np
import pandas as pd
import pytest
from scipy.stats import jarque_bera
from statsmodels.stats.diagnostic import acorr_ljungbox

from strategies._common.graph import Context, Engine, GraphError, NodeType, Registry
from strategies._common.graph.stat_nodes import derive_facts, register_nodes, resolve_payload
from strategies._common.validation import decision


def sample():
    return pd.Series(np.random.default_rng(310).normal(0.0002, 0.01, 600),
                     index=pd.bdate_range('2020-01-01', periods=600), name='returns')


def test_r6_automatic_facts_have_recomputable_provenance():
    r = sample()
    payload = derive_facts(r)
    facts, evidence = payload['facts'], payload['provenance']
    assert evidence['normal']['p_value'] == pytest.approx(jarque_bera(r).pvalue)
    assert evidence['autocorr']['p_value'] == pytest.approx(
        acorr_ljungbox(r, lags=[10], return_df=True)['lb_pvalue'].iloc[0])
    assert 1 <= facts['n_eff'] <= len(r)
    overlap = derive_facts(r, {'overlap': 'overlapping', 'holding_periods': 5})
    assert overlap['facts']['n_eff'] <= len(r) // 5
    assert 'n_trials' not in facts
    assert derive_facts([0.0] * 60)['facts']['autocorr'] == 'unknown'


def test_r6_ledger_only_trials_and_existing_resolver(monkeypatch):
    registry = Registry()
    register_nodes(registry)
    with pytest.raises(GraphError, match='unknown parameters'):
        registry.types['stat.facts'].parameters({'n_trials': 999})
    with pytest.raises(GraphError, match='LedgerN'):
        resolve_payload(derive_facts(sample()), {'selection_n': 0})
    payload = derive_facts(sample(), {'estimand': 'mean_return', 'design': 'paired'})
    payload['facts']['n_trials'] = 999
    called = []
    original = decision.resolve
    def tracked(facts, version):
        called.append(facts.n_trials)
        return original(facts, version)
    monkeypatch.setattr(decision, 'resolve', tracked)
    result = resolve_payload(payload, {'selection_n': 34})
    assert called == [34]
    assert result['n_trials_used'] == 34
    assert set(result['slots']) == {'base', 'se', 'primary', 'threshold', 'gates'}
    assert result['forbids']
    assert result['slots']['threshold']['facts']['n_trials'] == 34
    assert all(slot['rule_id'] for slot in result['slots'].values())
    assert decision.audit_record({'stat_decision': result}) == []
    json.dumps(result, allow_nan=False)


class MemoryLedger:
    def summary(self):
        return {'selection_n': 34, 'expected_max_sharpe': 2.1, 'session_n': 1}
    def record_success(self, *args):
        pass


def fixture_backtest(inputs, params, context):
    return {'Returns': sample()}


def unknown_facts(inputs, params, context):
    result = derive_facts(inputs['Returns'])
    result['facts']['autocorr'] = 'unknown'
    return {'Facts': result}


def test_r6_underdetermined_verbatim_and_report_branch_independent(tmp_path):
    registry = Registry()
    register_nodes(registry)
    registry.register(NodeType('backtest.fixture', {}, {'Returns': 'Returns'}, {}, fixture_backtest))
    registry.types['stat.facts'].function = unknown_facts
    graph = {'schema': 'live-strategy-graph/1', 'nodes': [
        {'id': 'bt', 'type': 'backtest.fixture'},
        {'id': 'ledger', 'type': 'ledger.selection_n'},
        {'id': 'facts', 'type': 'stat.facts'},
        {'id': 'resolve', 'type': 'stat.resolve'},
        {'id': 'report', 'type': 'validation.report'},
    ], 'edges': [
        {'from': ['bt', 'Returns'], 'to': ['facts', 'Returns']},
        {'from': ['bt', 'Returns'], 'to': ['report', 'Returns']},
        {'from': ['ledger', 'LedgerN'], 'to': ['report', 'LedgerN']},
        {'from': ['ledger', 'LedgerN'], 'to': ['resolve', 'LedgerN']},
        {'from': ['facts', 'Facts'], 'to': ['resolve', 'Facts']},
    ]}
    engine = Engine(registry, tmp_path)
    result = engine.run(graph, context=Context(ledger=MemoryLedger()))
    with pytest.raises(decision.UnderdeterminedError) as expected:
        resolve_payload(result['facts']['Facts'], {'selection_n': 34})
    assert engine.states['resolve']['status'] == 'error'
    assert engine.states['resolve']['message'] == str(expected.value)
    assert 'Ljung-Box' in str(expected.value)
    assert 'resolve' not in result
    assert result['report']['Report']['n_trials'] == 34
    assert result['report']['Report']['n_trials_source'] == 'ledger'
    assert registry.types['ledger.selection_n'].cacheable is False


def test_effective_sample_size_penalizes_serial_dependence():
    rng = np.random.default_rng(82)
    innovations = rng.normal(size=1000)
    correlated = innovations.copy()
    for i in range(1, len(correlated)):
        correlated[i] += 0.95 * correlated[i - 1]
    result = derive_facts(correlated)
    assert result['facts']['autocorr'] == 'yes'
    assert result['facts']['n_eff'] < 150
    # Missing cluster identities cannot be replaced by a row count.
    assert derive_facts(correlated, {'overlap': 'clustered'})['facts']['n_eff'] is None
