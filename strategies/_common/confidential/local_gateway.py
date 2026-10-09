"""Single-user, loopback-only HTTPS gateway with authenticated upstream TLS.

The Windows/WSL administrator, certificate trust store and secret ACL are trusted.
This local single-user login is not a shared-host OIDC replacement.
"""
import argparse
from collections import deque
import hmac
from http.client import HTTPSConnection, HTTPException
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import ssl
import threading
import time
from urllib.parse import parse_qs, urlsplit

MAX_BODY = 2_000_000
MAX_RESPONSE = 32 * 1024 * 1024
SESSION_SECONDS = 8 * 60 * 60
MAX_SESSIONS = 128
COOKIE = '__Host-straty_session'
LOGIN_PAGE = b'''<!doctype html><html lang="zh-Hant"><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>StratyUI Login</title>
<h1>StratyUI \xe6\x9c\xac\xe6\xa9\x9f\xe7\x99\xbb\xe5\x85\xa5</h1>
<form method="post" action="/login"><label>Password <input type="password"
name="password" required autocomplete="current-password"></label>
<button type="submit">Login</button></form></html>'''


def load_config(path):
    path = Path(path).resolve()
    config = json.loads(path.read_text(encoding='utf-8'))
    if config.get('schema') != 'straty-local-gateway/1':
        raise ValueError('unsupported gateway config')
    subject = config.get('subject')
    if not isinstance(subject, str) or not subject or not subject.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in subject):
        raise ValueError('invalid subject')
    for field in ('port', 'upstream_port'):
        if type(config.get(field)) is not int or not 1 <= config[field] <= 65535:
            raise ValueError('invalid port')
    if config['port'] == config['upstream_port']:
        raise ValueError('gateway and upstream must use separate ports')
    for field, destination in (('proxy_token_file', 'proxy_token'), ('login_secret_file', 'login_secret')):
        secret_path = Path(config[field])
        if not secret_path.is_absolute():
            secret_path = path.parent / secret_path
        value = secret_path.read_text(encoding='utf-8').strip()
        if len(value) < 32 or not value.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in value):
            raise ValueError('invalid gateway secret')
        config[destination] = value
    for field in ('tls_cert_file', 'tls_key_file', 'upstream_ca_file'):
        resource = Path(config[field])
        if not resource.is_absolute():
            resource = path.parent / resource
        if not resource.is_file():
            raise ValueError('TLS material unavailable')
        config[field] = str(resource.resolve())
    return config


class GatewayServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, config):
        self.config = config
        self.sessions = {}
        self.attempts = deque(maxlen=5)
        self.lock = threading.Lock()
        self.connections = threading.BoundedSemaphore(32)
        self.upstream_context = ssl.create_default_context(cafile=config['upstream_ca_file'])
        self.upstream_context.minimum_version = ssl.TLSVersion.TLSv1_2
        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.minimum_version = ssl.TLSVersion.TLSv1_2
        server_context.load_cert_chain(config['tls_cert_file'], config['tls_key_file'])
        super().__init__(('127.0.0.1', config['port']), GatewayHandler)
        # Perform bounded handshakes in request threads, not the accept loop.
        self.socket = server_context.wrap_socket(self.socket, server_side=True, do_handshake_on_connect=False)

    def process_request(self, request, client_address):
        if not self.connections.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.connections.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.connections.release()

    def handle_error(self, request, client_address):
        # Never print request internals or exceptions containing backend data.
        pass


class GatewayHandler(BaseHTTPRequestHandler):
    server_version = 'StratyLocal'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(10)
        self.connection.do_handshake()

    def log_message(self, *args):
        pass

    def reply(self, status, body=b'{"error":"request rejected"}', *, headers=(), content_type='application/json'):
        self.close_connection = True
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        # Preserve Origin on same-origin native form POSTs; suppress cross-origin referrers.
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Connection', 'close')
        for key, value in headers:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        self.reply(code)

    def do_GET(self):
        self.dispatch(False)

    def do_POST(self):
        self.dispatch(True)

    def session(self):
        if len(self.headers.get_all('Cookie', [])) != 1:
            return None
        try:
            cookie = SimpleCookie()
            cookie.load(self.headers['Cookie'])
            token = cookie[COOKIE].value
        except (CookieError, KeyError):
            return None
        with self.server.lock:
            now = time.monotonic()
            self.server.sessions = {k: v for k, v in self.server.sessions.items() if v['expiry'] > now}
            return token if token in self.server.sessions else None

    def dispatch(self, mutation):
        try:
            self._dispatch(mutation)
        except (TimeoutError, OSError, ValueError, HTTPException):
            self.reply(502)

    def _dispatch(self, mutation):
        hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        if len(self.headers.get_all('Host', [])) != 1 or self.headers['Host'] not in hosts:
            return self.reply(403)
        host = self.headers['Host']
        origins = self.headers.get_all('Origin', [])
        if (mutation and origins != ['https://' + host]) or (origins and origins != ['https://' + host]):
            return self.reply(403)
        parsed = urlsplit(self.path)
        # BaseHTTPRequestHandler normalizes leading // before dispatch.
        original_path = self.requestline.split()[1]
        if not self.path.startswith('/') or original_path.startswith('//') or '\\' in self.path or parsed.scheme or parsed.netloc or parsed.fragment:
            return self.reply(400)
        if self.headers.get_all('Transfer-Encoding') or self.headers.get_all('Expect'):
            return self.reply(400)
        lengths = self.headers.get_all('Content-Length', [])
        if len(lengths) > 1 or (lengths and not lengths[0].isdigit()):
            return self.reply(400)
        length = int(lengths[0]) if lengths else 0
        if length > MAX_BODY or (not mutation and length):
            return self.reply(413)
        if not mutation and parsed.path == '/login':
            return self.reply(200, LOGIN_PAGE, content_type='text/html; charset=utf-8', headers=[('Content-Security-Policy', "default-src 'none'; form-action 'self'; frame-ancestors 'none'")])
        token = self.session()
        if mutation and parsed.path == '/login':
            with self.server.lock:
                now = time.monotonic()
                while self.server.attempts and self.server.attempts[0] <= now - 60:
                    self.server.attempts.popleft()
                if len(self.server.attempts) >= 5:
                    return self.reply(429, headers=[('Retry-After', '60')])
                self.server.attempts.append(now)
            if length > 4096 or self.headers.get_content_type() != 'application/x-www-form-urlencoded':
                return self.reply(400)
            body = self.rfile.read(length)
            fields = parse_qs(body.decode('utf-8'), max_num_fields=2, strict_parsing=True)
            passwords = fields.get('password', [])
            if len(passwords) != 1 or not hmac.compare_digest(passwords[0].encode(), self.server.config['login_secret'].encode()):
                return self.reply(401)
            with self.server.lock:
                now = time.monotonic()
                self.server.sessions = {k: v for k, v in self.server.sessions.items() if v['expiry'] > now}
                if token:
                    self.server.sessions.pop(token, None)
                if len(self.server.sessions) >= MAX_SESSIONS:
                    return self.reply(503)
                token = secrets.token_urlsafe(32)
                proof = secrets.token_urlsafe(32)
                self.server.sessions[token] = {'expiry': now + SESSION_SECONDS, 'proof': proof}
            headers = [('Set-Cookie', f'{COOKIE}={token}; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}')]
            if self.headers.get('Accept') == 'application/json':
                return self.reply(200, json.dumps({'session_proof': proof}).encode(), headers=headers)
            nonce = secrets.token_urlsafe(24)
            page = ('<!doctype html><html><meta charset="utf-8"><title>StratyUI</title>'
                    f'<script nonce="{nonce}">sessionStorage.setItem("straty_session_proof",'
                    + json.dumps(proof) + ');location.replace("/");</script></html>').encode()
            headers.append(('Content-Security-Policy', f"default-src 'none'; script-src 'nonce-{nonce}'; frame-ancestors 'none'; base-uri 'none'"))
            return self.reply(200, page, headers=headers, content_type='text/html; charset=utf-8')
        if token is None:
            return self.reply(401) if parsed.path.startswith('/api/') else self.reply(303, b'', headers=[('Location', '/login')])
        if parsed.path.startswith('/api/') or parsed.path == '/logout':
            supplied = self.headers.get_all('X-Straty-Session-Proof', [])
            with self.server.lock:
                session = self.server.sessions.get(token)
                expected = session['proof'] if session else ''
            if len(supplied) != 1 or not expected or not hmac.compare_digest(supplied[0].encode(), expected.encode()):
                return self.reply(403)
        if mutation and parsed.path == '/logout':
            with self.server.lock:
                self.server.sessions.pop(token, None)
            return self.reply(303, b'', headers=[('Location', '/login'), ('Set-Cookie', f'{COOKIE}=; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')])
        body = self.rfile.read(length) if mutation else None
        if mutation and len(body) != length:
            return self.reply(400)
        config = self.server.config
        headers = {key: self.headers[key] for key in ('Accept', 'Content-Type', 'Accept-Encoding') if self.headers.get(key)}
        headers.update({'Host': f"127.0.0.1:{config['upstream_port']}", 'X-Straty-Subject': config['subject'], 'X-Straty-Proxy-Token': config['proxy_token']})
        if mutation:
            headers['Origin'] = f"http://127.0.0.1:{config['upstream_port']}"
        connection = HTTPSConnection('127.0.0.1', config['upstream_port'], timeout=10, context=self.server.upstream_context)
        try:
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            output = response.read(MAX_RESPONSE + 1)
            if len(output) > MAX_RESPONSE:
                return self.reply(502)
            # Explicit allowlist excludes Set-Cookie, identity, redirects, and hop headers.
            response_headers = [(k, v) for k, v in response.getheaders() if k.lower() in {'content-encoding', 'content-disposition'}]
            self.reply(response.status, output, headers=response_headers, content_type=response.getheader('Content-Type', 'application/octet-stream'))
        finally:
            connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    server = GatewayServer(load_config(args.config))
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
