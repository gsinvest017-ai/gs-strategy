"""Isolated UI demonstration using the Phase A real synthetic futures bundle."""
import json
import os
from pathlib import Path
import tempfile

from .service import GraphService, write_json
from .output_guard import quiet_worker_output


def fixture_service(source_root, graph_path='strategies/tsmom_tx_mtx/graph.json'):
    directory = tempfile.TemporaryDirectory(prefix='live-graph-fixture-')
    root = Path(directory.name)
    previous = os.environ.get('ZIPLINE_ROOT')
    os.environ['ZIPLINE_ROOT'] = str(root / 'bundle')
    try:
        with quiet_worker_output():
            from strategies.tsmom_tx_mtx.fixture_bundle import register_fixture
            name = register_fixture()
            from zipline.data.bundles import ingest
            ingest(name, show_progress=False)
        service = GraphService(root)
        # Validate the relative target before copying anything into the sandbox.
        target = service.confined(graph_path)
        source = (Path(source_root).resolve() / graph_path).resolve()
        if not source.is_relative_to(Path(source_root).resolve() / 'strategies'):
            from .core import GraphError
            raise GraphError('fixture graph must be inside strategies')
        graph = json.loads(source.read_text(encoding='utf-8'))
        for node in graph['nodes']:
            if node['type'] == 'data.futures_bars':
                node['params'].update(bundle=name, start='2018-01-02', end='2020-12-31', data_version='auto')
        write_json(target, graph)
        layout = source.with_name('graph.layout.json')
        if layout.exists():
            write_json(target.with_name('graph.layout.json'), json.loads(layout.read_text(encoding='utf-8')))
        service.fixture = True
        service.load(graph_path)
        service._fixture_directory = directory
        service._fixture_previous_zipline_root = previous
        return service
    except BaseException:
        if previous is None:
            os.environ.pop('ZIPLINE_ROOT', None)
        else:
            os.environ['ZIPLINE_ROOT'] = previous
        directory.cleanup()
        raise


def close_fixture(service):
    # Zipline/SQLAlchemy retain cyclic reader references until collection.
    import gc
    service.engine.values.clear()
    gc.collect()
    previous = service._fixture_previous_zipline_root
    if previous is None:
        os.environ.pop('ZIPLINE_ROOT', None)
    else:
        os.environ['ZIPLINE_ROOT'] = previous
    service._fixture_directory.cleanup()
