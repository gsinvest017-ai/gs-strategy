"""python -m strategies._common.graph {run,serve,types}."""
import argparse
import json
from pathlib import Path

from .api import GraphHTTPServer
from .service import GraphService, json_value
from .core import GraphError
from strategies._common.validation.decision import UnderdeterminedError


def serve_ui(args):
    from .fixture import fixture_service, close_fixture
    from .output_guard import quiet_worker_output
    service = server = None
    try:
        with quiet_worker_output():
            if args.fixture:
                service = fixture_service(Path(__file__).resolve().parents[3], args.graph)
            else:
                service = GraphService(args.root or Path.cwd(), cache_dir=args.cache_dir, ledger_path=args.ledger)
                try:
                    service.initial_graph_path = service.confined(args.graph).relative_to(service.root).as_posix()
                    service.load(args.graph)
                except GraphError:
                    # The UI retries the validated path through the existing load
                    # endpoint so its controlled edge error remains reviewable.
                    pass
            server = GraphHTTPServer(('127.0.0.1', args.port), service,
                                     ui_dist=Path(__file__).parent / 'ui' / 'dist')
        print(f'Live Strategy Graph UI: http://127.0.0.1:{server.server_port}', flush=True)
        server.serve_forever()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        print(json.dumps({'error': 'graph UI could not start or continue'}))
        return 1
    finally:
        if server is not None:
            server.server_close()
        if service is not None:
            if service.active:
                service._token.cancel()
                service._thread.join()
            if args.fixture:
                try:
                    with quiet_worker_output():
                        close_fixture(service)
                except Exception:
                    print(json.dumps({'error': 'fixture cleanup could not complete'}))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Live Strategy Graph (CPU)')
    parser.add_argument('command', choices=['run','serve','types','ui'])
    parser.add_argument('--graph', default='strategies/tsmom_tx_mtx/graph.json')
    parser.add_argument('--root', type=Path)
    parser.add_argument('--cache-dir', type=Path)
    parser.add_argument('--ledger', type=Path)
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--port', type=int, default=9102)
    parser.add_argument('--fixture', action='store_true')
    args = parser.parse_args(argv)
    if args.fixture and (args.command != 'ui' or args.root or args.cache_dir or args.ledger):
        parser.error('--fixture requires ui and forbids root/cache-dir/ledger overrides')
    if args.command == 'ui':
        return serve_ui(args)
    service = GraphService(args.root or Path.cwd(), cache_dir=args.cache_dir, ledger_path=args.ledger)
    if args.command == 'types':
        print(json.dumps(service.registry.describe(),ensure_ascii=False))
        return 0
    if args.command == 'serve':
        server = GraphHTTPServer(('127.0.0.1',args.port),service)
        print(f'Live Strategy Graph API: http://127.0.0.1:{server.server_port}',flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            if service.active:
                service._token.cancel()
        finally:
            server.server_close()
        return 0
    try:
        service.load(args.graph)
        job = service.start(preview=args.preview)
        try:
            service._thread.join()
        except KeyboardInterrupt:
            service.cancel(job['id'])
            service._thread.join()
        result = {**service.jobs[job['id']], 'nodes':service.engine.states, 'ledger':service.ledger.summary()}
        print(json.dumps(json_value(result),ensure_ascii=False,sort_keys=True))
        return 0 if result['status'] == 'complete' else 1
    except (GraphError, UnderdeterminedError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 1
    except Exception:
        print(json.dumps({'error':'graph execution could not start'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
