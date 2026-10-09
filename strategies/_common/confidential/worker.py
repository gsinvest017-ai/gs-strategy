"""Docker-only target oracle. The broker, never this worker, computes PnL.

Docker daemon and host administrator are trusted. No automatic subprocess
fallback exists. Source travels only on stdin; host logs retain no worker text.
"""
from __future__ import annotations

import base64
import json
import math
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
import uuid


class WorkerError(RuntimeError):
    """A deliberately generic failure, safe to include in job metadata."""


class DockerStreamingWorker:
    def __init__(self, image, *, timeout=60, step_timeout=5,
                 max_frame_bytes=1048576, max_output_bytes=1048576, docker='docker'):
        if not isinstance(image, str) or not re.fullmatch(r'(?:sha256:|[A-Za-z0-9][A-Za-z0-9._/:~-]*@sha256:)[a-f0-9]{64}', image):
            raise ValueError('immutable Docker image digest required')
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in (timeout, step_timeout)):
            raise ValueError('positive finite deadlines required')
        if any(type(v) is not int or v < 128 for v in (max_frame_bytes, max_output_bytes)):
            raise ValueError('positive bounded frame and output quotas required')
        self.image, self.docker = image, docker
        self.timeout, self.step_timeout = timeout, step_timeout
        self.max_frame_bytes, self.max_output_bytes = max_frame_bytes, max_output_bytes
        self.name = 'straty-private-' + uuid.uuid4().hex
        self.process = None
        self.started = False
        self.closed = False
        self._failed = threading.Event()
        self._responses = queue.Queue(maxsize=4)
        self._bytes = 0
        self._counter_lock = threading.Lock()
        self._close_lock = threading.Lock()
        self._threads = []
        self._last_seq = -1
        self._env = {k: os.environ[k] for k in ('PATH', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'HOME', 'USERPROFILE') if k in os.environ}
        self._watchdog = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _command(self):
        bootstrap = Path(__file__).with_name('worker_bootstrap.py').read_bytes()
        code = "import base64;exec(compile(base64.b64decode('" + base64.b64encode(bootstrap).decode('ascii') + "'),'<bootstrap>','exec'))"
        return [self.docker, 'run', '-i', '--rm', '--name', self.name,
                '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges', '--pids-limit', '32',
                '--memory', '128m', '--memory-swap', '128m', '--cpus', '1',
                '--user', '65534:65534', '--tmpfs', '/tmp:size=16m,mode=1777,noexec,nosuid,nodev',
                '--log-driver', 'none', '--ulimit', 'nofile=64:64',
                '--entrypoint', 'python', self.image, '-I', '-B', '-u', '-c', code,
                str(self.max_frame_bytes)]

    def _charge(self, size):
        with self._counter_lock:
            self._bytes += size
            if self._bytes > self.max_output_bytes:
                self._failed.set()
                return False
        return True

    def _reader(self, stream, stdout):
        try:
            while not self.closed:
                data = stream.readline(self.max_frame_bytes + 1) if stdout else stream.read(4096)
                if not data:
                    break
                if not self._charge(len(data)):
                    return
                if stdout:
                    if len(data) > self.max_frame_bytes or not data.endswith(b'\n'):
                        self._failed.set()
                        return
                    try:
                        self._responses.put_nowait(data)
                    except queue.Full:
                        self._failed.set()
                        return
        except (OSError, ValueError):
            pass
        finally:
            if stdout:
                self._failed.set()

    def _remaining(self):
        remaining = self._deadline - time.monotonic()
        if remaining <= 0 or self.closed:
            raise WorkerError('restricted worker failed')
        return min(remaining, self.step_timeout)

    def _exchange(self, frame):
        try:
            raw = (json.dumps(frame, allow_nan=False, separators=(',', ':')) + '\n').encode('utf-8')
            if len(raw) > self.max_frame_bytes:
                raise WorkerError('restricted worker frame limit')
            deadline = time.monotonic() + self._remaining()
            written = threading.Event()
            write_failed = threading.Event()

            def write():
                try:
                    pending = memoryview(raw)
                    while pending:
                        count = self.process.stdin.write(pending)
                        if not count:
                            raise OSError('worker stdin closed')
                        pending = pending[count:]
                    self.process.stdin.flush()
                except (OSError, ValueError):
                    write_failed.set()
                finally:
                    written.set()

            writer = threading.Thread(target=write, daemon=True)
            writer.start()
            while not written.wait(min(0.02, max(0, deadline - time.monotonic()))):
                if self._failed.is_set() or time.monotonic() >= deadline:
                    raise WorkerError('restricted worker failed')
            if write_failed.is_set():
                raise WorkerError('restricted worker failed')
            while True:
                if self._failed.is_set() or self.closed or time.monotonic() >= deadline:
                    raise WorkerError('restricted worker failed')
                try:
                    raw = self._responses.get(timeout=min(0.02, deadline - time.monotonic()))
                    break
                except queue.Empty:
                    continue
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError('duplicate field')
                    result[key] = value
                return result
            result = json.loads(raw, object_pairs_hook=unique,
                                parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
            if not isinstance(result, dict):
                raise WorkerError('restricted worker failed')
            return result
        except (WorkerError, OSError, ValueError, TypeError, RecursionError):
            self.close()
            raise WorkerError('restricted worker failed') from None

    def start(self, strategy_source: str, job_nonce: str):
        if self.started or self.closed:
            raise WorkerError('restricted worker unavailable')
        if not isinstance(strategy_source, str) or not isinstance(job_nonce, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', job_nonce):
            raise ValueError('strategy source and opaque nonce required')
        self.started = True
        self._nonce = job_nonce
        self._deadline = time.monotonic() + self.timeout
        # Do not pass broker credentials through Docker client environment.
        try:
            self.process = subprocess.Popen(self._command(), stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                            env=self._env, bufsize=0)
        except OSError:
            self.closed = True
            raise WorkerError('restricted worker unavailable') from None
        self._watchdog = threading.Timer(max(0, self._deadline - time.monotonic()), self.close)
        self._watchdog.daemon = True
        self._watchdog.start()
        for stream, stdout in ((self.process.stdout, True), (self.process.stderr, False)):
            thread = threading.Thread(target=self._reader, args=(stream, stdout), daemon=True)
            thread.start()
            self._threads.append(thread)
        response = self._exchange({'source': strategy_source, 'nonce': job_nonce})
        if response != {'nonce': job_nonce, 'ready': True} or type(response.get('ready')) is not bool:
            self.close()
            raise WorkerError('restricted worker failed')
        return self

    def target(self, history: list[dict], seq: int, max_contracts: int) -> int:
        if not self.started or self.closed:
            raise WorkerError('restricted worker unavailable')
        if type(seq) is not int or seq != self._last_seq + 1 or type(max_contracts) is not int or max_contracts < 0:
            raise ValueError('sequential request and integer position limit required')
        if not isinstance(history, list) or any(not isinstance(bar, dict) for bar in history):
            raise ValueError('history must be a list of bars')
        response = self._exchange({'nonce': self._nonce, 'seq': seq, 'history': history,
                                   'max_contracts': max_contracts})
        if (set(response) != {'nonce', 'seq', 'target'} or response['nonce'] != self._nonce
                or type(response['seq']) is not int or response['seq'] != seq
                or type(response['target']) is not int or abs(response['target']) > max_contracts):
            self.close()
            raise WorkerError('restricted worker failed')
        self._last_seq = seq
        return response['target']

    def close(self):
        with self._close_lock:
            if self.closed:
                return
            self.closed = True
            self._failed.set()
            if self._watchdog is not None:
                self._watchdog.cancel()
            if self.process is None:
                return
            try:
                subprocess.run([self.docker, 'rm', '-f', self.name], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
                               env=self._env)
            except (OSError, subprocess.TimeoutExpired):
                pass
            try:
                self.process.kill()
                self.process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                pass
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                try:
                    stream.close()
                except OSError:
                    pass

    cancel = close
