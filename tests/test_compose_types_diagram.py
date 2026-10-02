"""Parametric port types and the >> / @ composition laws."""
from pathlib import Path
import tempfile

import pytest

from strategies._common.compose.diagram import CompositionError, Diagram, box
from strategies._common.compose.types import Ty, compatible
from strategies._common.graph.core import Engine, GraphError, NodeType, Registry
from strategies._common.graph.service import default_registry
from strategies.llm_view_tx import compose_graph

ROOT = Path(__file__).resolve().parents[1]


def test_type_parsing_and_specialisation():
    assert Ty.parse('Signals[llm]') == Ty('Signals', ('llm',))
    assert str(Ty.parse('Series[TX, 1d]')) == 'Series[TX,1d]'
    assert compatible('Signals[llm]', 'Signals')
    assert compatible('Signals[llm]', 'Signals[llm]')
    assert compatible('Signals[llm]', 'Signals[*]')
    assert not compatible('Signals[rule]', 'Signals[llm]')
    assert not compatible('Signals', 'Signals[llm]')
    assert not compatible('Score', 'Sigma')
    assert compatible('Score', 'Score')
    for bad in ('', 'Signals[]', '1abc', 'Signals[llm', 'a b'):
        with pytest.raises(ValueError):
            Ty.parse(bad)
    assert not compatible('Signals[]', 'Signals')


def _fn(inputs, params, context):
    return {}


def toy_registry():
    registry = Registry()
    for node in (
        NodeType('data.a', {}, {'X': 'Series[TX]'}, {}, _fn),
        NodeType('feature.f', {'X': 'Series'}, {'Y': 'Score'}, {'k': {'type': 'integer', 'default': 1}}, _fn),
        NodeType('feature.g', {'Y': 'Score'}, {'Z': 'Signals[rule]'}, {}, _fn),
        NodeType('feature.h', {'Z': 'Signals'}, {'W': 'Weights'}, {}, _fn),
        NodeType('feature.need_llm', {'Z': 'Signals[llm]'}, {'V': 'Weights'}, {}, _fn),
        NodeType('feature.side', {'X': 'Series'}, {'S': 'Sigma'}, {}, _fn),
    ):
        registry.register(node)
    return registry


def graph_hash(registry, diagram):
    engine = Engine(registry, cache_dir=tempfile.mkdtemp(prefix='compose-law-'))
    return engine.identity(diagram.to_graph(registry))[0]


def test_sequential_composition_is_associative_and_unital():
    r = toy_registry()
    a, f, g, h = (box(r, 'data.a', 'a'), box(r, 'feature.f', 'f'), box(r, 'feature.g', 'g'),
                  box(r, 'feature.h', 'h'))
    left = ((a >> f) >> g) >> h
    right = a >> (f >> (g >> h))
    assert graph_hash(r, left) == graph_hash(r, right)
    unit = Diagram.id()
    assert graph_hash(r, unit >> a >> f) == graph_hash(r, a >> f) == graph_hash(r, a >> f >> unit)


def test_outputs_are_copyable_and_tensor_is_symmetric():
    r = toy_registry()
    a = box(r, 'data.a', 'a')
    f, side = box(r, 'feature.f', 'f'), box(r, 'feature.side', 'side')
    # X feeds both branches (cartesian copy); f @ side and side @ f give the same graph.
    assert graph_hash(r, a >> (f @ side)) == graph_hash(r, a >> (side @ f))
    graph = (a >> (f @ side)).to_graph(r)
    assert sorted(e['to'][0] for e in graph['edges']) == ['f', 'side']


def test_incompatible_wiring_fails_while_composing():
    r = toy_registry()
    chain = box(r, 'data.a', 'a') >> box(r, 'feature.f', 'f') >> box(r, 'feature.g', 'g')
    with pytest.raises(CompositionError, match='Signals\\[rule\\] into need.Z: Signals\\[llm\\]'):
        chain >> box(r, 'feature.need_llm', 'need')
    with pytest.raises(CompositionError, match='open'):
        box(r, 'feature.f', 'f').to_graph(r)
    with pytest.raises(CompositionError, match='unique'):
        box(r, 'data.a', 'a') @ box(r, 'data.a', 'a')


def test_registry_rejects_parametric_mismatch_in_documents():
    r = toy_registry()
    graph = {'schema': 'live-strategy-graph/1',
             'nodes': [{'id': 'a', 'type': 'data.a', 'params': {}}, {'id': 'f', 'type': 'feature.f', 'params': {}},
                       {'id': 'g', 'type': 'feature.g', 'params': {}}, {'id': 'n', 'type': 'feature.need_llm', 'params': {}}],
             'edges': [{'from': ['a', 'X'], 'to': ['f', 'X']}, {'from': ['f', 'Y'], 'to': ['g', 'Y']},
                       {'from': ['g', 'Z'], 'to': ['n', 'Z']}]}
    with pytest.raises(GraphError, match='invalid edge at index 2'):
        r.normalize(graph)


def test_returns_rule_sees_through_parameters():
    r = Registry()
    with pytest.raises(GraphError, match='Returns can only be produced'):
        r.register(NodeType('feature.cheat', {}, {'Returns': 'Returns[oos]'}, {}, _fn))
    with pytest.raises(GraphError, match='invalid port type'):
        r.register(NodeType('feature.bad', {}, {'Y': 'Score['}, {}, _fn))


def test_checked_in_graph_is_the_composed_pipeline():
    registry = default_registry()
    current = (ROOT / 'strategies/llm_view_tx/graph.json').read_text(encoding='utf-8')
    assert compose_graph.render(registry) == current
    print(compose_graph.pipeline(registry).signature())
