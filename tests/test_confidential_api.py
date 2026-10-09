import json
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pytest

from strategies._common.graph.api import GraphHTTPServer
from strategies._common.graph.access import AccessDenied


class Access:
    def authenticate(self, headers, ip):
        subject = headers.get('X-Subject')
        if subject not in ('alice', 'bob'):
            raise AccessDenied()
        return subject, None


class Broker:
    def capabilities(self, subject):
        return {'subject': subject}

    def submit(self, subject, request):
        return {'id': subject, 'execution': 'accepted'}

    def status(self, subject, job_id):
        if subject != job_id:
            raise ValueError('unknown job')
        return {'id': job_id, 'execution': 'running'}

    def result(self, subject, job_id):
        if subject != job_id:
            raise ValueError('unknown job')
        return {'ciphertext': 'opaque'}


def test_confidential_requires_access():
    with pytest.raises(ValueError):
        GraphHTTPServer(('127.0.0.1', 0), None, broker=Broker())


def test_confidential_routes_auth_and_strict_json():
    server = GraphHTTPServer(('127.0.0.1', 0), None, access=Access(), broker=Broker())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def call(path, subject='alice', raw=None):
        request = Request(f'http://127.0.0.1:{server.server_port}/api/confidential/{path}', data=raw,
                          headers={'X-Subject': subject, 'Content-Type': 'application/json'})
        try:
            with urlopen(request) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.load(exc)
    try:
        assert call('capabilities')[1] == {'subject': 'alice'}
        assert call('capabilities', subject='anonymous')[0] == 403
        assert call('jobs', raw=b'{}')[0] == 202
        assert call('jobs/alice')[1]['execution'] == 'running'
        assert call('jobs/alice', subject='bob')[0] == 400
        assert call('jobs/alice/result', subject='bob')[0] == 400
        assert call('jobs/alice/result')[1] == {'ciphertext': 'opaque'}
        assert call('jobs', raw=b'{"seed":1,"seed":2}')[0] == 400
        assert call('jobs', raw=b'{"seed":NaN}')[0] == 400
    finally:
        server.shutdown(); server.server_close(); thread.join()
