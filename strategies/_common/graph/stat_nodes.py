"""Statistical graph adapters; decision.py remains the only prescription authority."""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import jarque_bera
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import acf

from strategies._common.validation import decision, report
from .core import GraphError, NodeType

DECLARATIONS = {
    'estimand': 'sharpe', 'design': 'one_sample', 'overlap': 'none',
    'family': 'open_mining', 'purpose': 'selection', 'holding_periods': 1,
}


def returns_frame(value):
    if isinstance(value, pd.DataFrame):
        return value
    return pd.Series(value, name='returns').to_frame()


def derive_facts(returns, declarations=None):
    declared = dict(DECLARATIONS)
    if declarations:
        if set(declarations) - set(declared):
            raise GraphError('stat.facts: only declared facts are parameters; n_trials comes from LedgerN')
        declared.update(declarations)
    series = pd.to_numeric(returns_frame(returns)['returns'], errors='coerce')
    values = series.replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    n = len(values)
    lags = min(10, n // 5)
    provenance = {
        'normal': {'test': 'Jarque-Bera', 'p_value': None, 'alpha': 0.05},
        'autocorr': {'test': 'Ljung-Box', 'p_value': None, 'alpha': 0.05, 'lags': lags},
        'n_eff': {'method': 'floor(n / max(1, 1 + 2*sum(positive ACF[1:lags])))',
                  'n_observations': n, 'lags': lags, 'p_value': None},
    }
    facts = dict(declared, normal='unknown', autocorr='unknown', n_eff=None, unit='period')
    if n >= 20 and float(np.var(values)) > 0:
        jb = float(jarque_bera(values).pvalue)
        lb = float(acorr_ljungbox(values, lags=[lags], return_df=True)['lb_pvalue'].iloc[0])
        if np.isfinite(jb):
            facts['normal'] = 'yes' if jb >= 0.05 else 'no'
            provenance['normal']['p_value'] = jb
        if np.isfinite(lb):
            facts['autocorr'] = 'yes' if lb < 0.05 else 'no'
            provenance['autocorr']['p_value'] = lb
        correlations = acf(values, nlags=lags, fft=False)[1:]
        denominator = max(1.0, 1 + 2 * float(np.maximum(correlations, 0).sum()))
        if declared['overlap'] == 'overlapping':
            denominator = max(denominator, declared['holding_periods'])
        if declared['overlap'] != 'clustered':
            facts['n_eff'] = max(1, int(np.floor(n / denominator)))
        provenance['n_eff']['denominator'] = denominator
        provenance['n_eff']['overlap'] = declared['overlap']
    return {'facts': facts, 'provenance': provenance}


def ledger_n(summary):
    n = summary.get('selection_n')
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise GraphError('LedgerN requires a positive selection_n after successful backtest')
    return n


def resolve_payload(payload, ledger_summary, version=decision.DEFAULT_RULESET_VERSION):
    values = dict(payload['facts'])
    values['n_trials'] = ledger_n(ledger_summary)
    facts = decision.Facts(**values)
    prescription = decision.resolve(facts, version=version)
    record = prescription.to_record()
    record['decision_path'] = facts.as_path()
    rs = decision.load_ruleset(version)
    def source(*keys):
        return {key: values.get(key) for key in keys}
    record['slots'] = {
        'base': {'rule_id': prescription.base_id, 'value': prescription.base_id,
                 'facts': source('estimand', 'design')},
        'se': {'rule_id': prescription.se_id, 'value': prescription.se_correction,
               'lag': prescription.se_lag, 'facts': source('overlap', 'autocorr', 'holding_periods')},
        'primary': {'rule_id': prescription.rule_id, 'value': prescription.primary_test,
                    'alternative': prescription.alternative_test, 'facts': source('normal')},
        'threshold': {'rule_id': prescription.threshold_id, 'value': prescription.threshold,
                      'facts': source('family', 'n_trials'), 'n_trials_source': 'ledger'},
        'gates': {'rule_id': [g['id'] for g in rs['gates'] if decision._gate_applies(g, facts)],
                  'value': prescription.gate_status, 'min_n_eff': prescription.min_n_eff,
                  'facts': source('estimand', 'n_eff', 'unit')},
    }
    return record


def selection_node(inputs, params, context):
    if context.ledger is None:
        raise GraphError('ledger.selection_n requires selection ledger')
    return {'LedgerN': context.ledger.summary()}


def report_node(inputs, params, context):
    return {'Report': report.build_report(returns_frame(inputs['Returns']),
        n_trials=ledger_n(inputs['LedgerN']), n_trials_source='ledger')}


def facts_node(inputs, params, context):
    return {'Facts': derive_facts(inputs['Returns'], params)}


def resolve_node(inputs, params, context):
    return {'Prescription': resolve_payload(inputs['Facts'], inputs['LedgerN'], params['ruleset_version'])}


def register_nodes(registry):
    axes = decision.load_ruleset()['axes']
    params = {key: {'type': 'string', 'default': value, 'enum': list(axes[key]['values'])}
              for key, value in DECLARATIONS.items() if key != 'holding_periods'}
    # Diagnostic graphs require the future ruleset revision, not an MVP switch.
    params['purpose']['enum'] = ['selection']
    params['holding_periods'] = {'type': 'integer', 'minimum': 1, 'default': 1}
    dependencies = (Path(__file__), Path(decision.__file__), Path(report.__file__))
    registry.register(NodeType('ledger.selection_n', {}, {'LedgerN': 'LedgerN'}, {},
        selection_node, dependencies=dependencies, cacheable=False))
    registry.register(NodeType('validation.report', {'Returns': 'Returns', 'LedgerN': 'LedgerN'},
        {'Report': 'Report'}, {}, report_node, dependencies=dependencies))
    registry.register(NodeType('stat.facts', {'Returns': 'Returns'}, {'Facts': 'Facts'}, params,
        facts_node, dependencies=dependencies))
    registry.register(NodeType('stat.resolve', {'Facts': 'Facts', 'LedgerN': 'LedgerN'},
        {'Prescription': 'Prescription'}, {'ruleset_version': {'type': 'string', 'default': '1.1',
         'enum': ['1.1']}}, resolve_node, dependencies=dependencies))
