"""Shared CLI/HTTP lifecycle and JSON artifact serialization."""
from __future__ import annotations

import copy
import contextlib
import logging
import dataclasses
import json
import math
import os
from pathlib import Path
import tempfile
import threading
import uuid

from .core import Cancelled, Context, Engine, GraphError, Registry, digest
from .ledger import SelectionLedger


def default_registry():
    from strategies.tsmom_tx_mtx.graph_nodes import register_nodes as strategy_nodes
    from .stat_nodes import register_nodes as stat_nodes
    registry = Registry()
    strategy_nodes(registry)
    stat_nodes(registry)
    return registry


def json_value(value, limit=60, offset=0):
    """Expose portable data only; omit internal executable/cache representations."""
    import numpy as np
    import pandas as pd
    if dataclasses.is_dataclass(value):
        value = dataclasses.asdict(value)
    if isinstance(value, (pd.Series, pd.DataFrame)):
        frame = value.to_frame() if isinstance(value, pd.Series) else value
        end = max(0, len(frame) - offset)
        sample = frame.iloc[max(0, end-limit):end]
        return {'index': [x.isoformat() if hasattr(x, 'isoformat') else str(x) for x in sample.index],
                'columns': list(map(str, sample.columns)),
                'data': json_value(sample.to_numpy().tolist(), limit, offset), 'total': len(frame)}
    if isinstance(value, dict):
        if 'values' in value and isinstance(value['values'], (pd.Series, pd.DataFrame)):
            return {'values': json_value(value['values'], limit, offset),
                    'source': json_value(value.get('source', {}), limit, offset)}
        return {str(k): json_value(v, limit, offset) for k,v in value.items() if k != 'histories'}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [json_value(v, limit, offset) for v in value]
    if isinstance(value, np.generic):
        return json_value(value.item(), limit, offset)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if hasattr(value, 'symbol'):
        return str(value.symbol)
    return None


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(json_value(value), handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            handle.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def restore_sidecar(document, registry):
    snapshot = document.get('graph_snapshot')
    if not isinstance(snapshot, dict) or digest(snapshot) != document.get('graph_hash'):
        raise GraphError('sidecar graph snapshot/hash mismatch')
    warnings = []
    for name, old in snapshot.get('fingerprints', {}).items():
        node = registry.types.get(name)
        if node is None or node.fingerprint != old:
            warnings.append('節點實作已變更，無法保證重現：' + name)
    return {'graph': copy.deepcopy(snapshot['graph']), 'graph_hash': document['graph_hash'], 'warnings': warnings}


def save_artifact(context, values, path, manifest=None):
    from strategies._common.validation import report
    from .stat_nodes import returns_frame
    output = next((v for v in values.values() if 'Returns' in v), None)
    if output is None:
        return None
    validation = next((v['Report'] for v in values.values() if 'Report' in v), None)
    if validation is None:
        try:
            validation = report.build_report(returns_frame(output['Returns']),
                n_trials=context.ledger.summary()['selection_n'], n_trials_source='ledger')
        except (ValueError, ArithmeticError):
            validation = {'schema': report.SCHEMA, 'warnings': ['統計資料不足，請補足觀測後再檢定。']}
    document = {**validation, 'graph_hash': context.graph_hash, 'graph_snapshot': context.snapshot}
    write_json(path, document)
    if manifest is not None:
        report.apply_to_manifest(Path(manifest), document)
    return Path(path)


class GraphService:
    def __init__(self, root, *, registry=None, cache_dir=None, ledger_path=None):
        self.root = Path(root).resolve()
        self.registry = registry or default_registry()
        self.engine = Engine(self.registry, cache_dir or self.root / '.cache/live-strategy-graph')
        self.ledger = SelectionLedger(ledger_path or self.root / 'log/trials.jsonl')
        self.graph = None
        self.path = None
        self.saved_hash = None
        self.jobs = {}
        self.active = None
        self.lock = threading.RLock()

    def confined(self, relative, *, sidecar=False):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise GraphError('path must be inside workspace')
        if sidecar:
            if not path.name.endswith('.validation.json'):
                raise GraphError('expected validation sidecar JSON')
        elif path.name != 'graph.json' or not path.is_relative_to(self.root / 'strategies'):
            raise GraphError('expected strategies/<id>/graph.json')
        return path

    def idle(self):
        if self.active is not None and self.jobs[self.active]['status'] == 'running':
            raise GraphError('execution active; cancel or wait before editing')

    def set_graph(self, graph, path=None, *, saved=False):
        with self.lock:
            self.idle()
            graph = self.registry.normalize(graph)[0]
            new_path = self.confined(path) if path is not None else self.path
            self.graph = graph
            self.path = new_path
            self.engine.states = {n['id']: {'status': 'stale'} for n in graph['nodes']}
            self.engine.values = {}
            self.engine.hashes = {}
            if saved:
                self.saved_hash = self.engine.identity(graph)[0]
            return self.document()

    def load(self, relative):
        path = self.confined(relative)
        graph = json.loads(path.read_text(encoding='utf-8-sig'))
        return self.set_graph(graph, relative, saved=True)

    def document(self):
        if self.graph is None:
            return {'graph': None, 'dirty': False}
        key = self.engine.identity(self.graph)[0]
        return {'graph': copy.deepcopy(self.graph), 'graph_hash': key,
                'path': self.path.relative_to(self.root).as_posix() if self.path else None,
                'dirty': key != self.saved_hash}

    def save(self, relative=None):
        with self.lock:
            self.idle()
            if self.graph is None:
                raise GraphError('load a graph first')
            path = self.confined(relative) if relative else self.path
            if path is None:
                raise GraphError('graph save path required')
            write_json(path, self.graph)
            self.path = path
            self.saved_hash = self.engine.identity(self.graph)[0]
            return self.document()

    def parameters(self, node_id, params):
        with self.lock:
            self.idle()
            graph = copy.deepcopy(self.graph)
            if graph is None:
                raise GraphError('load a graph first')
            node = next((n for n in graph['nodes'] if n['id'] == node_id), None)
            if node is None:
                raise GraphError('unknown node')
            node['params'].update(params)
            graph = self.registry.normalize(graph)[0]
            self.engine.invalidate(graph, node_id)
            self.graph = graph
            return self.document()

    def start(self, preview=False):
        with self.lock:
            self.idle()
            if self.graph is None:
                raise GraphError('load a graph first')
            graph = copy.deepcopy(self.graph)
            job_id = uuid.uuid4().hex
            job = {'id': job_id, 'status': 'running', 'preview': preview, 'progress': {}}
            ctx = Context(ledger=self.ledger, progress=lambda value: job.update(progress=value))
            self.jobs[job_id] = job
            self.active = job_id
            self._token = ctx.token
            def work():
                try:
                    if any(n['type'] == 'data.futures_bars' for n in graph['nodes']):
                        from strategies.tsmom_tx_mtx.graph_nodes import prepare_graph
                        prepared = prepare_graph(graph)
                        with self.lock:
                            self.graph = prepared
                    else:
                        prepared = graph
                    values = self.engine.run(prepared, preview=preview, context=ctx)
                    inspected = {n['id'] for n in prepared['nodes'] if not preview or not n['type'].startswith(('backtest.', 'ledger.', 'validation.', 'stat.'))}
                    errors = [state for node_id, state in self.engine.states.items() if node_id in inspected and state['status'] in ('error','not_ready')]
                    if not preview and ctx.token.committed:
                        artifact = self.root / '.graph-runs' / (ctx.graph_hash + '.validation.json')
                        manifest = self.path.parent / 'manifest.yaml' if self.path else None
                        save_artifact(ctx, values, artifact, manifest)
                        job['sidecar'] = artifact.relative_to(self.root).as_posix()
                    job['status'] = 'error' if errors else 'complete'
                except Cancelled:
                    job['status'] = 'cancelled'
                except Exception:
                    job['status'] = 'error'
                    job['message'] = 'execution failed; no external error text exposed'
            def quiet_work():
                # Third-party imports may print connection settings; never persist or expose them.
                previous = logging.root.manager.disable
                with open(os.devnull, 'w') as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                    logging.disable(logging.CRITICAL)
                    try:
                        work()
                    finally:
                        logging.disable(previous)
            thread = threading.Thread(target=quiet_work, name='live-graph-worker', daemon=True)
            self._thread = thread
            thread.start()
            return dict(job)

    def cancel(self, job_id):
        with self.lock:
            if self.active != job_id or self.jobs[job_id]['status'] != 'running':
                raise GraphError('job is not running')
            accepted = self._token.cancel()
            return {'accepted': accepted, 'reason': 'cancellation requested' if accepted else 'backtest already committed'}

    def node(self, node_id, limit=60, offset=0):
        if node_id not in self.engine.states:
            raise GraphError('unknown node')
        outputs = self.engine.values.get(node_id, {})
        result = {'id': node_id, **dict(self.engine.states[node_id]), 'outputs': json_value(outputs,limit,offset)}
        if 'Returns' in outputs:
            from .stat_nodes import returns_frame
            equity = (1 + returns_frame(outputs['Returns'])['returns']).cumprod()
            result['equity'] = json_value(equity,limit,offset)
        return result
