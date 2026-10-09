"""Trusted, single-process confidential broker. Stores ciphertext, never metrics.

Host administrators, this module and its private configuration are trusted.
The HTTP graph service must authenticate a stable subject before calling it.
"""
from __future__ import annotations

import base64
from pathlib import Path
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager

from .crypto import public_key, seal, open_envelope, sign, verify
from .manifest import canonical_json, parse_json, sha256, freeze_run, trusted_package_fingerprint
from .worker import DockerStreamingWorker

PACKAGE = Path(__file__).parent
HEADER_FIELDS = {'schema', 'subject', 'submission_id', 'owner_key_id', 'broker_key_id',
                 'recipient_key_id', 'recipient_fingerprint', 'dataset_id', 'dataset_sha256',
                 'engine_sha256', 'config_sha256', 'seed', 'issued_at', 'expires_at'}


class BrokerError(ValueError):
    pass


def key_fingerprint(public):
    return sha256(base64.b64decode(public, validate=True))


class Broker:
    def __init__(self, policy_path, *, evaluator=None):
        path = Path(policy_path).resolve()
        self.policy = parse_json(path.read_bytes())
        if self.policy.get('schema') != 'straty-broker/1':
            raise BrokerError('invalid broker policy')
        def resolved(value):
            p = Path(value)
            return (path.parent / p).resolve() if not p.is_absolute() else p.resolve()
        self.root = resolved(self.policy['root'])
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Kernel-held lifetime lock prevents two brokers recovering each other's
        # in-flight jobs. It is released on crash without unsafe PID heuristics.
        self._lease = (self.root / 'broker.lock').open('a+b')
        self._lease.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                if not self._lease.read(1):
                    self._lease.write(b'0'); self._lease.flush()
                self._lease.seek(0)
                msvcrt.locking(self._lease.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._lease.close()
            raise BrokerError('broker store already in use') from None
        try:
            self.image = self.policy['image']
            # Constructor validates digest without starting a container.
            DockerStreamingWorker(self.image)
            self.engine = trusted_package_fingerprint(PACKAGE, self.image)
            if self.policy['engine_sha256'] != self.engine:
                raise BrokerError('approved engine does not match installed package')
            self.decrypt_id = self.policy['decrypt_key']['id']
            self.sign_id = self.policy['signing_key']['id']
            self.decrypt_private = resolved(self.policy['decrypt_key']['path']).read_text(encoding='utf-8').strip()
            self.sign_private = resolved(self.policy['signing_key']['path']).read_text(encoding='utf-8').strip()
            self.decrypt_public = public_key(self.decrypt_private, 'x25519')
            self.sign_public = public_key(self.sign_private, 'ed25519')
            self.datasets = {}
            for name, item in self.policy['datasets'].items():
                with resolved(item['path']).open('rb') as f:
                    data = f.read(8 * 1024 * 1024 + 1)
                if len(data) > 8 * 1024 * 1024 or sha256(data) != item['sha256']:
                    raise BrokerError('dataset snapshot mismatch')
                self.datasets[name] = data
            self.subjects = self.policy['subjects']
            self.db_path = self.root / 'jobs.sqlite'
            with self._db() as db:
                db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, subject TEXT NOT NULL, '
                           'submission_id TEXT NOT NULL, request_hash TEXT NOT NULL, request_json BLOB NOT NULL, '
                           'execution TEXT NOT NULL, verification TEXT NOT NULL, delivery TEXT NOT NULL, '
                           'result_json BLOB, UNIQUE(subject, submission_id))')
                db.execute("UPDATE jobs SET execution='interrupted', verification='not_run', delivery='not_ready' "
                           "WHERE execution IN ('accepted','running')")
            self.lock = threading.RLock()
            self.active = None
            self.thread = None
            self.worker = None
            self.closed = False
            self.evaluator = evaluator
        except BaseException:
            self._lease.close()
            raise

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _key(self, subject, purpose, key_id):
        key = self.subjects[subject][purpose][key_id]
        now = int(time.time())
        if (key.get('active') is not True or now < key.get('valid_from', 0)
                or now >= key.get('expires_at', 2**63 - 1)):
            raise BrokerError('key unavailable')
        return key['public_key']

    def capabilities(self, subject):
        if subject not in self.subjects:
            raise BrokerError('access denied')
        return {'schema': 'straty-capabilities/1', 'engine_sha256': self.engine, 'image': self.image,
                'broker_key_id': self.decrypt_id, 'broker_public': self.decrypt_public,
                'broker_signing_key_id': self.sign_id, 'broker_signing_public': self.sign_public,
                'adapter': 'daily-futures-next-open/1', 'cache_reuse': False,
                'datasets': {name: sha256(self.datasets[name]) for name in self.subjects[subject]['datasets']}}

    def submit(self, subject, request):
        """Validate signature and bindings before atomic replay reservation."""
        try:
            encoded = canonical_json(request)
            if len(encoded) > 1_000_000 or set(request) != {'header', 'envelope', 'signature'}:
                raise BrokerError('invalid submission')
            request = parse_json(encoded)
            h = request['header']
            now = int(time.time())
            if (set(h) != HEADER_FIELDS or h['schema'] != 'straty-submission/1' or h['subject'] != subject
                    or h['broker_key_id'] != self.decrypt_id or h['engine_sha256'] != self.engine
                    or type(h['submission_id']) is not str or len(h['submission_id']) != 32
                    or any(c not in '0123456789abcdef' for c in h['submission_id'])
                    or type(h['seed']) is not int or not 0 <= h['seed'] < 2**64
                    or type(h['issued_at']) is not int or type(h['expires_at']) is not int
                    or not h['issued_at'] <= now < h['expires_at'] <= h['issued_at'] + 86400):
                raise BrokerError('invalid submission')
            owner = self._key(subject, 'signing_keys', h['owner_key_id'])
            recipient = self._key(subject, 'recipient_keys', h['recipient_key_id'])
            if (h['recipient_fingerprint'] != key_fingerprint(recipient)
                    or h['dataset_id'] not in self.subjects[subject]['datasets']
                    or h['dataset_sha256'] != sha256(self.datasets[h['dataset_id']])):
                raise BrokerError('invalid submission')
            verify({'header': h, 'envelope': request['envelope']}, request['signature'], owner)
            with self.lock:
                if self.closed or self.active:
                    raise BrokerError('broker unavailable')
                job_id = uuid.uuid4().hex
                with self._db() as db:
                    db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)',
                               (job_id, subject, h['submission_id'], sha256(encoded), encoded,
                                'accepted', 'not_run', 'not_ready', None))
                self.active = job_id
                self.thread = threading.Thread(target=self._run, args=(job_id, request, recipient), daemon=True)
                self.thread.start()
            return self.status(subject, job_id)
        except Exception:
            raise BrokerError('submission rejected') from None

    def _run(self, job_id, request, recipient):
        h = request['header']
        started = int(time.time())
        try:
            with self._db() as db:
                db.execute("UPDATE jobs SET execution='running' WHERE id=?", (job_id,))
            payload = open_envelope(request['envelope'], self.decrypt_private, h)
            if set(payload) != {'source', 'config'} or sha256(canonical_json(payload['config'])) != h['config_sha256']:
                raise BrokerError('invalid payload')
            if trusted_package_fingerprint(PACKAGE, self.image) != self.engine:
                raise BrokerError('engine changed')
            frozen = freeze_run(source=payload['source'], data=self.datasets[h['dataset_id']], config=payload['config'],
                                owner=h['subject'], recipient_fingerprint=h['recipient_fingerprint'], image=self.image,
                                seed=h['seed'], engine_sha256=self.engine,
                                worker_sha256=sha256((PACKAGE / 'worker_bootstrap.py').read_bytes()))
            evaluator = self.evaluator
            if evaluator is None:
                from .engine import evaluate
                evaluator = evaluate
            with DockerStreamingWorker(self.image, timeout=120, step_timeout=10, max_output_bytes=4*1024*1024) as worker:
                with self.lock:
                    if self.closed:
                        raise BrokerError('broker closed')
                    self.worker = worker
                result = evaluator(frozen, worker, h['submission_id'])
            if trusted_package_fingerprint(PACKAGE, self.image) != self.engine:
                raise BrokerError('engine changed')
            # Only the trusted evaluator can set these; worker replies are integers.
            verified = result['verification']['status']
            if verified not in ('passed', 'failed'):
                raise BrokerError('invalid verifier output')
            binding = {'schema': 'straty-result/1', 'job_id': job_id, 'subject': h['subject'],
                       'submission_id': h['submission_id'], 'request_hash': sha256(canonical_json(request)),
                       'recipient_key_id': h['recipient_key_id'], 'recipient_fingerprint': h['recipient_fingerprint']}
            envelope = seal({'binding': binding, 'manifest': frozen.identity, 'result': result}, recipient, binding)
            receipt = {**binding, 'schema': 'straty-receipt/1', 'broker_signing_key_id': self.sign_id,
                       'result_envelope_hash': sha256(canonical_json(envelope)), 'execution': 'succeeded',
                       'verification': verified, 'delivery': 'available', 'started_at': started,
                       'finished_at': int(time.time()), 'research_qualification': 'not_evaluated'}
            bundle = {'binding': binding, 'envelope': envelope, 'receipt': receipt, 'signature': sign(receipt, self.sign_private)}
            with self._db() as db:
                db.execute("UPDATE jobs SET execution='succeeded',verification=?,delivery='available',result_json=? WHERE id=?",
                           (verified, canonical_json(bundle), job_id))
        except Exception:
            # Never persist exception text, source, locals, stdout or financial results.
            with self._db() as db:
                db.execute("UPDATE jobs SET execution='failed',verification='not_run',delivery='not_ready' WHERE id=?", (job_id,))
        finally:
            with self.lock:
                self.worker = None
                self.active = None

    def status(self, subject, job_id):
        with self._db() as db:
            row = db.execute('SELECT id,execution,verification,delivery FROM jobs WHERE id=? AND subject=?', (job_id, subject)).fetchone()
        if row is None:
            raise BrokerError('unknown job')
        return dict(row)

    def result(self, subject, job_id):
        with self._db() as db:
            row = db.execute("SELECT result_json FROM jobs WHERE id=? AND subject=? AND delivery='available'", (job_id, subject)).fetchone()
        if row is None:
            raise BrokerError('result unavailable')
        return parse_json(bytes(row['result_json']))

    def close(self):
        with self.lock:
            self.closed = True
            if self.worker is not None:
                self.worker.cancel()
        if self.thread:
            self.thread.join(timeout=135)
            if self.thread.is_alive():
                raise BrokerError('broker is still stopping')
        self._lease.close()
