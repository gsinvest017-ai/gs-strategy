from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
import math
import os
import pickle
import tempfile
import textwrap
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


class GraphError(ValueError):
    pass


class Cancelled(Exception):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def code_fingerprint(source):
    """Same AST normalization and digest length as triage_generated."""
    if callable(source):
        source = textwrap.dedent(inspect.getsource(source))
    elif isinstance(source, Path):
        source = source.read_text(encoding='utf-8-sig')
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return hashlib.sha256(ast.dump(ast.fix_missing_locations(tree)).encode()).hexdigest()[:16]


@dataclass
class NodeType:
    id: str
    inputs: dict
    outputs: dict
    params: dict
    function: Callable
    dependencies: tuple = ()
    cacheable: bool = True

    @property
    def fingerprint(self):
        # Include explicit helper/module dependencies, not just the thin wrapper.
        return digest([code_fingerprint(self.function)] + [code_fingerprint(x) for x in self.dependencies])

    def parameters(self, values):
        if set(values) - set(self.params):
            raise GraphError(f'{self.id}: unknown parameters')
        result = {}
        types = {'integer': int, 'number': (float, int), 'string': str, 'boolean': bool, 'array': list, 'object': dict}
        for name, schema in self.params.items():
            if name not in values and 'default' not in schema:
                raise GraphError(f'{self.id}: missing parameter {name}')
            value = copy.deepcopy(values.get(name, schema.get('default')))
            if value is None and schema.get('nullable'):
                result[name] = value
                continue
            kind = schema['type']
            if not isinstance(value, types[kind]) or (kind in ('integer', 'number') and isinstance(value, bool)):
                raise GraphError(f'{self.id}: invalid parameter {name}')
            if kind in ('integer', 'number') and (not math.isfinite(value) or value < schema.get('minimum', -math.inf) or value > schema.get('maximum', math.inf)):
                raise GraphError(f'{self.id}: parameter out of range {name}')
            if 'enum' in schema and value not in schema['enum']:
                raise GraphError(f'{self.id}: invalid choice {name}')
            result[name] = value
        return result


class Registry:
    def __init__(self):
        self.types = {}

    def register(self, node):
        if node.id in self.types:
            raise GraphError(f'duplicate node type {node.id}')
        if 'Returns' in node.outputs.values() and not node.id.startswith('backtest.'):
            raise GraphError('Returns can only be produced by backtest.*')
        self.types[node.id] = node
        return node

    def describe(self):
        return [{'id': n.id, 'inputs': n.inputs, 'outputs': n.outputs, 'params': n.params,
                 'fingerprint': n.fingerprint} for n in self.types.values()]

    def normalize(self, graph):
        graph = copy.deepcopy(graph)
        if graph.get('schema') != 'live-strategy-graph/1':
            raise GraphError('unsupported graph schema')
        nodes = graph.get('nodes', [])
        ids = [n['id'] for n in nodes]
        if len(set(ids)) != len(ids):
            raise GraphError('duplicate node id')
        by_id = {n['id']: n for n in nodes}
        for n in nodes:
            if n['type'] not in self.types:
                raise GraphError(f'unknown node type {n["type"]}')
            n['params'] = self.types[n['type']].parameters(n.get('params', {}))
        incoming = {i: {} for i in ids}
        for edge in graph.get('edges', []):
            try:
                src, out = edge['from']
                dst, inp = edge['to']
                a, b = self.types[by_id[src]['type']], self.types[by_id[dst]['type']]
                valid = a.outputs[out] == b.inputs[inp] and inp not in incoming[dst]
            except (KeyError, ValueError):
                valid = False
            if not valid:
                raise GraphError(f'invalid edge: {canonical(edge)}')
            incoming[dst][inp] = (src, out)
        order = []
        while len(order) < len(ids):
            ready = [i for i in ids if i not in order and all(s in order for s, _ in incoming[i].values())]
            if not ready:
                raise GraphError('graph contains a cycle')
            # Ledger is a live external source, sampled after backtest commit.
            ready.sort(key=lambda i: (by_id[i]['type'].startswith(('ledger.', 'validation.', 'stat.')), i))
            order.append(ready[0])
        graph['nodes'] = sorted(nodes, key=lambda n: n['id'])
        graph['edges'] = sorted(graph.get('edges', []), key=canonical)
        canonical(graph)
        return graph, by_id, incoming, order


class CancelToken:
    def __init__(self):
        self.lock = threading.RLock()
        self.cancelled = False

    def cancel(self):
        with self.lock:
            self.cancelled = True

    def check(self):
        if self.cancelled:
            raise Cancelled('execution cancelled')


@dataclass
class Context:
    token: CancelToken = field(default_factory=CancelToken)
    ledger: object = None
    graph_hash: str = ''
    snapshot: dict = field(default_factory=dict)
    services: dict = field(default_factory=dict)
    progress: Callable = lambda value: None

    def check_cancelled(self):
        self.token.check()


class Engine:
    def __init__(self, registry, cache_dir):
        self.registry = registry
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.states = {}
        self.values = {}
        self.hashes = {}

    def identity(self, graph):
        g, nodes, incoming, order = self.registry.normalize(graph)
        fingerprints = {n['type']: self.registry.types[n['type']].fingerprint for n in nodes.values()}
        snapshot = {'graph': g, 'fingerprints': fingerprints}
        return digest(snapshot), snapshot

    def invalidate(self, graph, node_id):
        _, _, incoming, order = self.registry.normalize(graph)
        affected = {node_id}
        for i in order:
            if i in affected or any(s in affected for s, _ in incoming[i].values()):
                affected.add(i)
                self.states[i] = {'status': 'stale', 'result_hash': self.hashes.get(i)}
        return affected

    def _write_cache(self, key, value):
        # Local trusted pickle cache, never accepted through HTTP or sidecars.
        fd, name = tempfile.mkstemp(dir=self.cache_dir, suffix='.tmp')
        try:
            with os.fdopen(fd, 'wb') as f:
                pickle.dump(value, f, protocol=5)
            os.replace(name, self.cache_dir / (key + '.pkl'))
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def run(self, graph, *, preview=False, context=None):
        ctx = context or Context()
        g, nodes, incoming, order = self.registry.normalize(graph)
        ctx.graph_hash, ctx.snapshot = self.identity(g)
        blocked = set()
        current = {}
        for i in order:
            n = nodes[i]
            kind = self.registry.types[n['type']]
            if n['type'].startswith('backtest.') or any(s in blocked for s, _ in incoming[i].values()):
                blocked.add(i)
            if preview and (i in blocked or n['type'].startswith(('ledger.', 'validation.', 'stat.'))):
                self.states.setdefault(i, {'status': 'stale'})
                continue
            ctx.check_cancelled()
            missing = set(kind.inputs) - set(incoming[i])
            unavailable = [p for p, (s, _) in incoming[i].items() if s not in current]
            if missing or unavailable:
                self.states[i] = {'status': 'not_ready', 'message': 'missing inputs: ' + ', '.join(sorted(missing | set(unavailable)))}
                continue
            key = digest({'type': kind.id, 'implementation': kind.fingerprint, 'params': n['params'],
                          'upstream': {p: self.hashes[s] for p, (s, _) in incoming[i].items()}})
            # Cache identity of mutable external sources includes their current revision.
            if not kind.cacheable:
                key = digest([key, ctx.services.get('revision', ''), ctx.ledger.summary() if ctx.ledger else None])
            path = self.cache_dir / (key + '.pkl')
            self.states[i] = {'status': 'running', 'hash': key}
            try:
                if path.exists() and kind.cacheable:
                    with path.open('rb') as f:
                        result = pickle.load(f)
                    status = 'cached'
                else:
                    result = kind.function({p: current[s][out] for p, (s, out) in incoming[i].items()}, n['params'], ctx)
                    status = 'recomputed'
                ctx.check_cancelled()
                if not isinstance(result, dict) or set(result) != set(kind.outputs):
                    raise GraphError('node output ports do not match declaration')
                if kind.id.startswith('backtest.'):
                    if ctx.ledger is None:
                        raise GraphError('backtest requires selection ledger')
                    # Cancellation and successful selection commit have one linearization point.
                    with ctx.token.lock:
                        ctx.check_cancelled()
                        ctx.ledger.record_success(ctx.graph_hash, ctx.snapshot, result, ctx)
                if kind.cacheable and status == 'recomputed':
                    self._write_cache(key, result)
                self.hashes[i] = key if kind.cacheable else digest([key, repr(result)])
                current[i] = result
                self.values[i] = result
                self.states[i] = {'status': status, 'hash': key, 'graph_hash': ctx.graph_hash}
            except Cancelled:
                self.states[i] = {'status': 'stale', 'message': 'execution cancelled'}
                raise
            except Exception as exc:
                # Only controlled domain errors may expose messages; third-party errors can contain secrets.
                from strategies._common.validation.decision import UnderdeterminedError
                message = str(exc) if isinstance(exc, (GraphError, UnderdeterminedError)) else f'{type(exc).__name__}: node execution failed'
                self.states[i] = {'status': 'error', 'message': message}
            ctx.progress({'node': i, 'completed': len(current), 'total': len(order)})
        return current
