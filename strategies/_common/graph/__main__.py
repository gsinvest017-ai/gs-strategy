"""python -m strategies._common.graph {run,serve,types}."""
import argparse
import json
from pathlib import Path

from .api import GraphHTTPServer
from .service import GraphService, json_value


def main(argv=None):
    parser = argparse.ArgumentParser(description='Live Strategy Graph (CPU)')
    parser.add_argument('command', choices=['run','serve','types'])
    parser.add_argument('--graph', default='strategies/tsmom_tx_mtx/graph.json')
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--cache-dir', type=Path)
    parser.add_argument('--ledger', type=Path)
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--port', type=int, default=9102)
    args = parser.parse_args(argv)
    service = GraphService(args.root, cache_dir=args.cache_dir, ledger_path=args.ledger)
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
    except Exception:
        print(json.dumps({'error':'graph execution could not start'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
