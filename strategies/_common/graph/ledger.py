"""Append-only selection accounting, serialized across threads and processes."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import threading
import time

from scripts.triage_generated import count_existing_selection_trials, expected_max_sharpe
from strategies._common.validation.decision import DecisionError, DEFAULT_RULESET_VERSION
from .core import GraphError, canonical


_locks_guard = threading.Lock()
_locks = {}


@contextmanager
def _exclusive(path):
    """Use an OS-released advisory lock; a crashed worker cannot leave a stale lock."""
    key = str(path.resolve())
    with _locks_guard:
        local = _locks.setdefault(key, threading.RLock())
    with local:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.with_suffix(path.suffix + '.lock').open('a+b') as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                while True:
                    try:
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        time.sleep(0.01)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _records(path):
    if not path.exists():
        return []
    try:
        records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        if any(not isinstance(record, dict) for record in records):
            raise ValueError
        return records
    except (ValueError, UnicodeError):
        raise GraphError('selection ledger is malformed; append refused') from None


def _config_ref(snapshot, context):
    graph = snapshot.get('graph', snapshot)
    strategy = graph.get('strategy')
    if strategy is not None and (not isinstance(strategy, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', strategy)):
        raise GraphError('invalid strategy identifier')
    value = context.services.get('config_ref') or (
        f'strategies/{strategy}/manifest.yaml' if strategy else 'strategies/live_graph/manifest.yaml')
    value = str(value).replace('\\', '/')
    path = PurePosixPath(value)
    if (path.is_absolute() or '..' in path.parts or ':' in value
            or not re.fullmatch(r'[A-Za-z0-9_./-]+', value)):
        raise GraphError('config_ref must be a repository-relative path')
    return path.as_posix()


def _stat_record(outputs, snapshot, n_trials):
    from .stat_nodes import DECLARATIONS, derive_facts, resolve_payload
    graph = snapshot.get('graph', snapshot)
    declarations = next((node.get('params', {}) for node in graph.get('nodes', [])
                         if node.get('type') == 'stat.facts'), {})
    declarations = {**declarations, 'purpose': 'selection'}
    try:
        payload = derive_facts(outputs['Returns'], declarations)
    except GraphError:
        raise
    except (ArithmeticError, ValueError):
        payload = {'facts': {**DECLARATIONS, **declarations, 'normal': 'unknown',
                             'autocorr': 'unknown', 'n_eff': None, 'unit': 'period'},
                   'provenance': {'status': 'numerical_failure'}}
    try:
        record = resolve_payload(payload, {'selection_n': n_trials}, DEFAULT_RULESET_VERSION)
        return {**record, 'purpose': 'selection'}
    except DecisionError:
        # Successful observed performance must count even when inference is unresolved.
        # Do not invent missing evidence merely to make the legacy audit pass.
        return {
            'ruleset_version': DEFAULT_RULESET_VERSION,
            'purpose': 'selection', 'delta_n': 1,
            'status': 'pending', 'rule_id': None,
            'decision_path': {**payload['facts'], 'n_trials': n_trials},
            'provenance': payload.get('provenance', {}),
            'inference_available': False,
        }


class SelectionLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.session_n = 0

    def summary(self):
        with _exclusive(self.path):
            _records(self.path)
            n = count_existing_selection_trials(self.path)
            return {'selection_n': n, 'expected_max_sharpe': expected_max_sharpe(n),
                    'session_n': self.session_n}

    def record_success(self, graph_hash, snapshot, outputs, context):
        """Return whether this completed graph first entered the selection population."""
        with context.token.lock, _exclusive(self.path):
            context.check_cancelled()
            records = _records(self.path)
            if any(record.get('graph_hash') == graph_hash for record in records):
                return False
            n = count_existing_selection_trials(self.path) + 1
            stat = _stat_record(outputs, snapshot, n)
            now = datetime.now(timezone.utc).isoformat()
            record = {
                'schema': 'research-trial/v1', 'trial_id': 't-graph-' + graph_hash,
                'parent_trial_id': None, 'repo': 'gs-strategy', 'level': 'trial',
                'state': 'complete', 'started_at': now, 'finished_at': now,
                'purpose': 'selection', 'config_ref': _config_ref(snapshot, context),
                'config_sha256': graph_hash, 'graph_hash': graph_hash,
                'graph_ref': {'graph_hash': graph_hash, 'snapshot': snapshot},
                'stat_decision': stat,
            }
            data = (canonical(record) + '\n').encode('utf-8')
            context.check_cancelled()
            with self.path.open('ab') as handle:
                # Preserve existing bytes, including a valid last line without LF.
                prefix = b''
                if self.path.stat().st_size:
                    with self.path.open('rb') as reader:
                        reader.seek(-1, os.SEEK_END)
                        if reader.read(1) != b'\n':
                            prefix = b'\n'
                handle.write(prefix + data)
                handle.flush()
                os.fsync(handle.fileno())
            self.session_n += 1
            return True
