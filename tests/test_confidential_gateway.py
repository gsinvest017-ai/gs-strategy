import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ssl
import ipaddress
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import threading
import time
from urllib.parse import urlencode

import pytest

from strategies._common.confidential import local_gateway as gateway


def certificate(tmp_path, name, host='127.0.0.1'):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(host))]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, hashes.SHA256()))
    cert_file, key_file = tmp_path / (name + '.pem'), tmp_path / (name + '.key')
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return str(cert_file), str(key_file)


@pytest.fixture
def running(tmp_path):
    received = []

    class Backend(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.do_POST()

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            received.append((self.path, dict(self.headers), body))
            output = b'{"ciphertext":"opaque"}'
            self.send_response(200)
            self.send_header('Content-Length', str(len(output)))
            self.send_header('Content-Type', 'application/json')
            self.send_header('Set-Cookie', 'evil=1')
            self.end_headers()
            self.wfile.write(output)

    backend = ThreadingHTTPServer(('127.0.0.1', 0), Backend)
    backend_cert, backend_key = certificate(tmp_path, 'backend')
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(backend_cert, backend_key)
    backend.socket = context.wrap_socket(backend.socket, server_side=True)
    gateway_cert, gateway_key = certificate(tmp_path, 'gateway')
    server = gateway.GatewayServer({'tls_cert_file': gateway_cert, 'tls_key_file': gateway_key,
                                    'upstream_ca_file': backend_cert, 'port': 0, 'upstream_port': backend.server_port,
                                    'subject': 'kevin2-local', 'proxy_token': 'p' * 40,
                                    'login_secret': 's' * 40})
    threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (backend, server)]
    for thread in threads:
        thread.start()
    yield server, received
    for service in (server, backend):
        service.shutdown()
        service.server_close()
    for thread in threads:
        thread.join()


class AuthCookie(str):
    pass


def request(server, method='GET', path='/api/session', body=None, headers=None):
    conn = http.client.HTTPSConnection('127.0.0.1', server.server_port, timeout=3, context=ssl.create_default_context(cafile=server.config['tls_cert_file']))
    headers = dict(headers or {})
    if isinstance(headers.get('Cookie'), AuthCookie):
        headers.setdefault('X-Straty-Session-Proof', headers['Cookie'].proof)
    conn.request(method, path, body, headers)
    response = conn.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    conn.close()
    return result


def login(server):
    status, headers, body = request(server, 'POST', '/login', urlencode({'password': 's' * 40}),
                                 {'Origin': f'https://127.0.0.1:{server.server_port}',
                                  'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'})
    assert status == 200
    assert 'HttpOnly' in headers['Set-Cookie']
    assert 'Secure' in headers['Set-Cookie']
    assert headers['Set-Cookie'].startswith('__Host-straty_session=')
    assert 'Domain=' not in headers['Set-Cookie']
    assert 'SameSite=Strict' in headers['Set-Cookie']
    cookie = AuthCookie(headers['Set-Cookie'].split(';')[0])
    cookie.proof = json.loads(body)['session_proof']
    return cookie


def test_login_required_and_no_header_impersonation(running):
    server, received = running
    assert request(server)[0] == 401
    assert request(server, headers={'X-Straty-Subject': 'kevin2-local', 'X-Straty-Proxy-Token': 'p' * 40})[0] == 401
    assert request(server, path='/')[0] == 303
    status, headers, body = request(server, path='/login')
    assert status == 200
    # no-referrer turns browser form POST Origin into null, failing CSRF validation.
    assert headers['Referrer-Policy'] == 'same-origin'
    assert "form-action 'self'" in headers['Content-Security-Policy']
    assert received == []


def test_proxy_strips_client_identity_cookies_and_preserves_ciphertext(running):
    server, received = running
    cookie = login(server)
    status, headers, body = request(server, 'POST', '/api/confidential/jobs?x=1', b'{"opaque":true}',
        {'Cookie': cookie, 'Origin': f'https://127.0.0.1:{server.server_port}', 'Content-Type': 'application/json',
         'X-Straty-Subject': 'attacker', 'X-Straty-Proxy-Token': 'attacker', 'X-Auth-Request-Email': 'attacker',
         'Authorization': 'Bearer evil', 'X-Forwarded-Host': 'evil'})
    assert status == 200 and body == b'{"ciphertext":"opaque"}'
    assert 'Set-Cookie' not in headers
    path, forwarded, payload = received[-1]
    assert path == '/api/confidential/jobs?x=1' and payload == b'{"opaque":true}'
    assert forwarded['X-Straty-Subject'] == 'kevin2-local'
    assert forwarded['X-Straty-Proxy-Token'] == 'p' * 40
    assert forwarded['Origin'] == f"http://127.0.0.1:{server.config['upstream_port']}"
    assert not {'Cookie', 'Authorization', 'X-Auth-Request-Email', 'X-Forwarded-Host'} & forwarded.keys()


@pytest.mark.parametrize('origin', [None, 'null', 'http://evil.test', 'http://localhost:1'])
def test_login_csrf_blocked(running, origin):
    server, received = running
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    if origin is not None:
        headers['Origin'] = origin
    assert request(server, 'POST', '/login', 'password=' + 's' * 40, headers)[0] == 403
    assert not received and not server.sessions


def test_rate_limit_and_secret_failure(running):
    server, _ = running
    headers = {'Origin': f'https://127.0.0.1:{server.server_port}', 'Content-Type': 'application/x-www-form-urlencoded'}
    for _ in range(5):
        assert request(server, 'POST', '/login', 'password=wrong', headers)[0] == 401
    assert request(server, 'POST', '/login', 'password=' + 's' * 40, headers)[0] == 429
    assert len(server.attempts) == 5


def test_logout_and_expiry(running):
    server, _ = running
    cookie = login(server)
    assert request(server, headers={'Cookie': cookie})[0] == 200
    assert request(server, 'POST', '/logout', b'', {'Cookie': cookie})[0] == 403
    assert request(server, 'POST', '/logout', b'', {'Cookie': cookie, 'Origin': f'https://127.0.0.1:{server.server_port}'})[0] == 303
    assert request(server, headers={'Cookie': cookie})[0] == 401
    cookie = login(server)
    server.sessions[cookie.split('=', 1)[1]]['expiry'] = time.monotonic() - 1
    assert request(server, headers={'Cookie': cookie})[0] == 401


@pytest.mark.parametrize('path', ['http://evil.test/api/session', '//evil.test/api/session', '/\\evil.test', '/api/session#fragment'])
def test_request_target_restrictions(running, path):
    server, received = running
    assert request(server, path=path, headers={'Host': f'127.0.0.1:{server.server_port}'})[0] == 400
    assert not received


def test_host_body_method_and_response_limits(running, monkeypatch):
    server, received = running
    assert request(server, headers={'Host': 'evil.test'})[0] == 403
    assert request(server, method='DELETE')[0] == 501
    assert request(server, headers={'Content-Length': str(gateway.MAX_BODY + 1)})[0] == 413
    assert request(server, headers={'Transfer-Encoding': 'chunked'})[0] == 400
    cookie = login(server)
    monkeypatch.setattr(gateway, 'MAX_RESPONSE', 10)
    assert request(server, headers={'Cookie': cookie})[0] == 502


def test_config_validation(tmp_path):
    (tmp_path / 'proxy').write_text('p' * 40)
    (tmp_path / 'secret').write_text('s' * 40)
    path = tmp_path / 'config.json'
    config = {'schema': 'straty-local-gateway/1', 'subject': 'kevin2-local', 'port': 9113,
              'upstream_port': 9114, 'proxy_token_file': 'proxy', 'login_secret_file': 'secret'}
    cert, key = certificate(tmp_path, 'config')
    config.update(tls_cert_file=cert, tls_key_file=key, upstream_ca_file=cert)
    path.write_text(json.dumps(config))
    assert gateway.load_config(path)['login_secret'] == 's' * 40
    config['subject'] = 'bad\r\nheader'
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        gateway.load_config(path)


@pytest.mark.parametrize('header,values', [('Host', ['127.0.0.1:{port}', 'evil.test']),
                                         ('Origin', ['https://127.0.0.1:{port}'] * 2),
                                         ('Content-Length', ['0', '2'])])
def test_duplicate_security_headers_rejected(running, header, values):
    server, received = running
    conn = http.client.HTTPSConnection('127.0.0.1', server.server_port, timeout=3, context=ssl.create_default_context(cafile=server.config['tls_cert_file']))
    conn.putrequest('GET', '/api/session', skip_host=header == 'Host')
    for value in values:
        conn.putheader(header, value.format(port=server.server_port))
    conn.endheaders()
    response = conn.getresponse()
    assert response.status in (400, 403)
    response.read()
    conn.close()
    assert not received


def test_bounded_sessions(running, monkeypatch):
    server, _ = running
    monkeypatch.setattr(gateway, 'MAX_SESSIONS', 1)
    login(server)
    headers = {'Origin': f'https://127.0.0.1:{server.server_port}', 'Content-Type': 'application/x-www-form-urlencoded'}
    assert request(server, 'POST', '/login', 'password=' + 's' * 40, headers)[0] == 503
    assert len(server.sessions) == 1


def test_upstream_wrong_certificate_never_receives_identity(running):
    server, received = running
    cookie = login(server)
    # Simulate a replacement listener: its certificate is not the pinned leaf.
    server.upstream_context = ssl.create_default_context(cafile=server.config['tls_cert_file'])
    assert request(server, headers={'Cookie': cookie})[0] == 502
    assert received == []


def test_browser_rejects_untrusted_gateway_before_credentials(running):
    server, received = running
    client = http.client.HTTPSConnection('127.0.0.1', server.server_port, timeout=3,
        context=ssl.create_default_context(cafile=server.config['upstream_ca_file']))
    with pytest.raises(ssl.SSLCertVerificationError):
        client.request('POST', '/login', body='password=' + 's' * 40)
    client.close()
    assert not server.attempts and not server.sessions and not received


def test_plain_http_cannot_login_and_http_origin_rejected(running):
    server, received = running
    client = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
    with pytest.raises((OSError, http.client.HTTPException)):
        client.request('GET', '/login')
        client.getresponse()
    client.close()
    headers = {'Origin': f'http://127.0.0.1:{server.server_port}', 'Content-Type': 'application/x-www-form-urlencoded'}
    assert request(server, 'POST', '/login', 'password=' + 's' * 40, headers)[0] == 403
    assert not server.sessions and not received


def test_secure_cookie_policy_does_not_send_to_other_http_port(running):
    from http.cookiejar import CookieJar
    from urllib.request import Request
    from email.message import Message
    server, _ = running
    cookie = login(server)
    headers = Message()
    headers['Set-Cookie'] = cookie + '; Secure; HttpOnly; SameSite=Strict; Path=/'

    class Response:
        def info(self):
            return headers

    jar = CookieJar()
    jar.extract_cookies(Response(), Request(f'https://127.0.0.1:{server.server_port}/login'))
    insecure = Request('http://127.0.0.1:9999/')
    jar.add_cookie_header(insecure)
    assert not insecure.has_header('Cookie')
    # Cookie ports are not isolated: TLS authentication is also mandatory.
    secure = Request('https://127.0.0.1:9999/')
    jar.add_cookie_header(secure)
    assert secure.has_header('Cookie')


def test_stolen_cookie_without_origin_scoped_proof_cannot_read_api(running):
    server, received = running
    cookie = login(server)
    assert request(server, headers={'Cookie': str(cookie)})[0] == 403
    assert request(server, headers={'Cookie': cookie, 'X-Straty-Session-Proof': 'wrong'})[0] == 403
    assert request(server, headers={'Cookie': cookie})[0] == 200
    assert 'X-Straty-Session-Proof' not in received[-1][1]
    assert request(server, path='/login', headers={'Cookie': cookie})[2].find(cookie.proof.encode()) == -1


def test_html_login_delivers_proof_once_under_nonce_csp(running):
    server, _ = running
    status, headers, body = request(server, 'POST', '/login', 'password=' + 's' * 40,
        {'Origin': f'https://127.0.0.1:{server.server_port}', 'Content-Type': 'application/x-www-form-urlencoded'})
    assert status == 200
    assert b'sessionStorage.setItem("straty_session_proof"' in body
    assert b'location.replace("/")' in body
    assert b'localStorage' not in body
    assert "script-src 'nonce-" in headers['Content-Security-Policy']
    assert headers['Cache-Control'] == 'no-store'
