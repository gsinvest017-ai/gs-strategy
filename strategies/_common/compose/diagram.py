"""Compositional construction of strategy graphs (string-diagram DSL).

Node types are morphisms ``dom -> cod`` whose objects are the parametric port
types of :mod:`.types`.  A :class:`Diagram` is a partially wired graph with a
set of *free inputs* (its domain) and *available outputs* (its codomain):

* ``f >> g``  sequential composition: each free input of ``g`` is wired to the
  output of ``f`` with the **same port name**; the types must be compatible or
  composition fails immediately (not at run time).  Inputs of ``g`` that ``f``
  does not provide stay free.
* ``f @ g``   parallel composition (tensor): disjoint union of the two diagrams.
* ``Diagram.id()`` is the unit of both.

Wiring is cartesian: an output may feed several inputs, so ``f``'s outputs
remain available after ``f >> g`` (``g`` shadows equal names).  Matching is by
name only, never by "the unique compatible type", which keeps ``>>``
associative; ``tests/test_compose_diagram.py`` checks the laws by comparing
graph hashes.

``to_graph`` closes the diagram into a ``live-strategy-graph/1`` document; the
registry's ``normalize`` remains the single validator, so a diagram cannot
produce a graph the engine would reject.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from strategies._common.graph.core import GraphError
from .types import compatible


class CompositionError(GraphError):
    pass


@dataclass(frozen=True)
class Diagram:
    nodes: tuple = ()
    edges: tuple = ()
    # name -> tuple of (node_id, port, type): every free input slot with that name
    dom: dict = field(default_factory=dict)
    # name -> (node_id, port, type)
    cod: dict = field(default_factory=dict)

    @classmethod
    def id(cls):
        return cls()

    @classmethod
    def box(cls, registry, type_id, node_id=None, **params):
        if type_id not in registry.types:
            raise CompositionError(f'unknown node type {type_id}')
        kind = registry.types[type_id]
        node_id = node_id or type_id
        node = {'id': node_id, 'type': type_id, 'params': kind.parameters(params)}
        return cls(nodes=(node,), edges=(),
                   dom={port: ((node_id, port, t),) for port, t in kind.inputs.items()},
                   cod={port: (node_id, port, t) for port, t in kind.outputs.items()})

    def __rshift__(self, other):
        if not isinstance(other, Diagram):
            return NotImplemented
        _disjoint(self, other)
        edges = list(self.edges) + list(other.edges)
        dom = {k: tuple(v) for k, v in self.dom.items()}
        for name, slots in other.dom.items():
            if name in self.cod:
                src, out, produced = self.cod[name]
                for dst, inp, wanted in slots:
                    if not compatible(produced, wanted):
                        raise CompositionError(
                            f'cannot compose {src}.{out}: {produced} into {dst}.{inp}: {wanted}')
                    edges.append({'from': [src, out], 'to': [dst, inp]})
            else:
                dom[name] = dom.get(name, ()) + tuple(slots)
        return Diagram(self.nodes + other.nodes, tuple(edges), dom, {**self.cod, **other.cod})

    def __matmul__(self, other):
        if not isinstance(other, Diagram):
            return NotImplemented
        _disjoint(self, other)
        clash = set(self.cod) & set(other.cod)
        if clash:
            raise CompositionError('parallel composition has ambiguous outputs: ' + ', '.join(sorted(clash)))
        dom = {k: tuple(v) for k, v in self.dom.items()}
        for name, slots in other.dom.items():
            dom[name] = dom.get(name, ()) + tuple(slots)
        return Diagram(self.nodes + other.nodes, self.edges + other.edges, dom, {**self.cod, **other.cod})

    def signature(self):
        """Human-readable ``dom -> cod`` (types, not node ids)."""
        ins = sorted({f'{name}: {t}' for name, slots in self.dom.items() for _, _, t in slots})
        outs = sorted(f'{name}: {t}' for name, (_, _, t) in self.cod.items())
        return '(' + ', '.join(ins) + ') -> (' + ', '.join(outs) + ')'

    def to_graph(self, registry, strategy=None):
        if self.dom:
            missing = ', '.join(f'{d}.{p}' for slots in self.dom.values() for d, p, _ in slots)
            raise CompositionError('diagram is open; unwired inputs: ' + missing)
        graph = {'schema': 'live-strategy-graph/1', 'nodes': copy.deepcopy(list(self.nodes)),
                 'edges': copy.deepcopy(list(self.edges))}
        if strategy:
            graph['strategy'] = strategy
        return registry.normalize(graph)[0]


def _disjoint(a, b):
    clash = {n['id'] for n in a.nodes} & {n['id'] for n in b.nodes}
    if clash:
        raise CompositionError('node ids must be unique across a composition: ' + ', '.join(sorted(clash)))


def box(registry, type_id, node_id=None, **params):
    return Diagram.box(registry, type_id, node_id, **params)
