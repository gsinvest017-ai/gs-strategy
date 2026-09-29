"""R5 accounting uses temporary files exclusively, including process workers."""
import json
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import pytest

from scripts.triage_generated import count_existing_selection_trials, expected_max_sharpe
from strategies._common.graph.core import Cancelled, Context, GraphError
from strategies._common.graph.ledger import SelectionLedger
from strategies._common.validation.decision import audit_ledger


SNAPSHOT = {'graph': {'strategy': 'tsmom_tx_mtx', 'nodes': [], 'edges': []}, 'fingerprints': {}}


def _outputs():
    return {'Returns': pd.Series(np.random.default_rng(35).normal(0.001, 0.01, 350))}


def _read(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def _process_record(path, graph_hash):
    SelectionLedger(path).record_success(graph_hash, SNAPSHOT, _outputs(), Context())


def test_selection_33_to_34_revert_and_cancel_append_only(tmp_path):
    path = tmp_path / 'trials.jsonl'
    initial = SelectionLedger(path)
    initial.record_success('original', SNAPSHOT, _outputs(), Context())
    record = _read(path)[0]
    with path.open('a', encoding='utf-8') as handle:
        for i in range(32):
            handle.write(json.dumps({**record, 'graph_hash': f'seed-{i}', 'trial_id': f'seed-{i}'}) + '\n')
    before = path.read_bytes()
    ledger = SelectionLedger(path)
    assert ledger.summary()['selection_n'] == 33
    assert ledger.record_success('new-parameters', SNAPSHOT, _outputs(), Context())
    assert ledger.summary() == {'selection_n': 34, 'session_n': 1,
                                'expected_max_sharpe': expected_max_sharpe(34)}
    assert path.read_bytes().startswith(before)
    after = path.read_bytes()
    assert not ledger.record_success('original', SNAPSHOT, _outputs(), Context())
    assert not ledger.record_success('new-parameters', SNAPSHOT, _outputs(), Context())
    cancelled = Context()
    cancelled.token.cancel()
    with pytest.raises(Cancelled):
        ledger.record_success('cancelled', SNAPSHOT, _outputs(), cancelled)
    assert path.read_bytes() == after
    audit = audit_ledger(_read(path))
    assert audit['problems'] == []
    assert audit['n_selection_recomputed'] == count_existing_selection_trials(path) == 34
    added = _read(path)[-1]
    assert added['config_ref'] == 'strategies/tsmom_tx_mtx/manifest.yaml'
    assert added['graph_ref'] == {'graph_hash': 'new-parameters', 'snapshot': SNAPSHOT}
    assert added['stat_decision']['decision_path']['n_trials'] == 34


def test_concurrent_threads_only_append_one_record(tmp_path):
    path = tmp_path / 'trials.jsonl'
    ledgers = [SelectionLedger(path) for _ in range(12)]
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda ledger: ledger.record_success('same', SNAPSHOT, _outputs(), Context()), ledgers))
    assert sum(results) == sum(ledger.session_n for ledger in ledgers) == 1
    assert len(_read(path)) == 1
    assert audit_ledger(_read(path))['auditable']


def test_concurrent_processes_share_lock_and_deduplicate(tmp_path):
    path = tmp_path / 'trials.jsonl'
    ctx = multiprocessing.get_context('spawn')
    workers = [ctx.Process(target=_process_record, args=(path, 'same')) for _ in range(3)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=45)
        assert worker.exitcode == 0
    assert len(_read(path)) == 1
    assert count_existing_selection_trials(path) == 1


@pytest.mark.parametrize('values', [[0.0], [], [np.nan] * 30, [0.0] * 30, [np.inf] * 30])
def test_inference_failure_counts_without_inventing_facts(tmp_path, values):
    path = tmp_path / 'trials.jsonl'
    ledger = SelectionLedger(path)
    assert ledger.record_success('short', SNAPSHOT, {'Returns': pd.Series(values, dtype=float)}, Context())
    record = _read(path)[0]
    assert ledger.summary()['selection_n'] == 1
    assert record['stat_decision']['status'] == 'pending'
    assert record['stat_decision']['decision_path']['autocorr'] == 'unknown'
    assert not audit_ledger([record])['auditable']


def test_no_final_newline_is_preserved_and_malformed_file_is_rejected(tmp_path):
    path = tmp_path / 'trials.jsonl'
    ledger = SelectionLedger(path)
    assert ledger.summary() == {'selection_n': 0, 'session_n': 0, 'expected_max_sharpe': 0.0}
    path.write_bytes(b'{"stat_decision":{"delta_n":0}}')
    before = path.read_bytes()
    ledger.record_success('new', SNAPSHOT, _outputs(), Context())
    assert path.read_bytes().startswith(before + b'\n')
    path.write_bytes(b'{broken')
    with pytest.raises(GraphError, match='malformed'):
        ledger.record_success('other', SNAPSHOT, _outputs(), Context())
    assert path.read_bytes() == b'{broken'


def test_session_count_resets_and_declared_purpose_cannot_disable_accounting(tmp_path):
    path = tmp_path / 'trials.jsonl'
    ledger = SelectionLedger(path)
    snapshot = {'graph': {'strategy': 'tsmom_tx_mtx', 'nodes': [
        {'type': 'stat.facts', 'params': {'purpose': 'screening'}}]}}
    ledger.record_success('graph', snapshot, _outputs(), Context())
    assert _read(path)[0]['stat_decision']['decision_path']['purpose'] == 'selection'
    assert ledger.summary()['session_n'] == 1
    assert SelectionLedger(path).summary()['session_n'] == 0


def test_machine_specific_config_ref_rejected(tmp_path):
    ledger = SelectionLedger(tmp_path / 'trials.jsonl')
    with pytest.raises(GraphError, match='repository-relative'):
        ledger.record_success('graph', SNAPSHOT, _outputs(), Context(services={'config_ref': '/private/file'}))
    assert ledger.summary()['selection_n'] == 0


def test_strategy_identifier_rejects_uncontrolled_metadata(tmp_path):
    ledger = SelectionLedger(tmp_path / 'trials.jsonl')
    with pytest.raises(GraphError, match='strategy identifier'):
        ledger.record_success('graph', {'graph': {'strategy': '../outside', 'nodes': []}}, _outputs(), Context())
    assert ledger.summary()['selection_n'] == 0
