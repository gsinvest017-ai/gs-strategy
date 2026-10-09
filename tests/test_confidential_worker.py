import io
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from strategies._common.confidential.worker import DockerStreamingWorker, WorkerError


IMAGE = 'sha256:' + 'a' * 64
NONCE = 'test_nonce_1234567890'


def test_immutable_image_and_limits():
    for bad in ('python:3.12-slim', 'sha256:abc', '--privileged', 'a@sha256:' + 'A' * 64):
        with pytest.raises(ValueError):
            DockerStreamingWorker(bad)
    with pytest.raises(ValueError):
        DockerStreamingWorker(IMAGE, timeout=float('nan'))


def test_command_has_no_secret_or_mount():
    worker = DockerStreamingWorker(IMAGE)
    command = worker._command()
    assert '--network' in command and command[command.index('--network') + 1] == 'none'
    for flag in ('--read-only', '--cap-drop', '--pids-limit', '--memory', '--cpus', '--log-driver'):
        assert flag in command
    assert '--mount' not in command and '-v' not in command
    assert NONCE not in str(command)
    assert command[command.index('--user') + 1] == '65534:65534'


@pytest.fixture
def local_protocol(monkeypatch):
    """Contract-only bootstrap test: explicitly NOT proof of Docker isolation."""
    real_popen = subprocess.Popen
    bootstrap = Path(__file__).resolve().parents[1] / 'strategies/_common/confidential/worker_bootstrap.py'

    def fake_popen(command, **kwargs):
        return real_popen([sys.executable, '-I', '-u', str(bootstrap), command[-1]], **kwargs)

    monkeypatch.setattr(subprocess, 'Popen', fake_popen)
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: None)


def test_protocol_iterations(local_protocol):
    with DockerStreamingWorker(IMAGE) as worker:
        worker.start('def decide(history):\n return len(history)', NONCE)
        assert worker.target([], 0, 2) == 0
        assert worker.target([{'close': 1}], 1, 2) == 1
        with pytest.raises(ValueError):
            worker.target([], 3, 2)
    worker.close()
    assert worker.process.poll() is not None


def test_cleanup_uses_same_scrubbed_environment(local_protocol, monkeypatch):
    monkeypatch.setenv('DOCKER_HOST', 'tcp://wrong-daemon.invalid:1234')
    monkeypatch.setenv('STRATY_BROKER_SECRET_CANARY', 'never-in-worker')
    calls = []
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: calls.append(kw))
    with DockerStreamingWorker(IMAGE) as worker:
        worker.start('def decide(history):\n return 0', NONCE)
        assert worker.target([], 0, 1) == 0
    assert len(calls) == 1
    assert 'DOCKER_HOST' not in calls[0]['env']
    assert 'STRATY_BROKER_SECRET_CANARY' not in calls[0]['env']


def test_total_deadline_stops_idle_worker(local_protocol):
    worker = DockerStreamingWorker(IMAGE, timeout=.2)
    worker.start('def decide(history):\n return 0', NONCE)
    deadline = time.monotonic() + 2
    while worker.process.poll() is None and time.monotonic() < deadline:
        time.sleep(.02)
    assert worker.closed
    assert worker.process.poll() is not None


@pytest.mark.parametrize('source', [
    'def decide(history):\n return True',
    'def decide(history):\n return 100',
    'def decide(history):\n while True: pass',
    'def decide(history):\n import os\n os.write(1,b"x"*10000)\n return 0',
    'def decide(history):\n import sys\n sys.stderr.write("x"*10000)\n return 0',
    'def decide(history):\n import os\n os.write(1,b\'{}\\n\')\n return 0',
])
def test_reject_bad_strategy(local_protocol, source):
    with DockerStreamingWorker(IMAGE, step_timeout=.3, max_frame_bytes=4096, max_output_bytes=4096) as worker:
        worker.start(source, NONCE)
        with pytest.raises(WorkerError):
            worker.target([], 0, 2)
        assert worker.closed


def test_stdout_quota_does_not_retain_unbounded_bytes():
    worker = DockerStreamingWorker(IMAGE, max_frame_bytes=128, max_output_bytes=256)
    worker._reader(io.BytesIO(b'x' * 10000), True)
    assert worker._failed.is_set()
    assert worker._responses.empty()
    assert worker._bytes <= 129


@pytest.mark.skipif(not os.environ.get('STRATY_TEST_DOCKER_IMAGE'), reason='requires explicit immutable Docker test image')
def test_real_docker_isolation():
    source = '''
def decide(history):
 import os, socket, errno
 assert os.getuid() == 65534
 assert 'STRATY_BROKER_SECRET_CANARY' not in os.environ
 assert not os.path.exists('/var/run/docker.sock')
 assert not os.path.exists('/run/straty-broker-private-canary')
 try:
  open('/straty-write-probe','w').write('fail')
 except OSError: pass
 else: raise AssertionError('root writable')
 s=socket.socket(); s.settimeout(.2)
 try: s.connect(('1.1.1.1',443))
 except OSError: pass
 else: raise AssertionError('network available')
 finally: s.close()
 children=[]
 try:
  for _ in range(40):
   try: pid=os.fork()
   except OSError: break
   if pid==0:
    import time
    time.sleep(5)
    os._exit(0)
   children.append(pid)
  assert len(children)<32
 finally:
  for pid in children:
   os.kill(pid,9)
   os.waitpid(pid,0)
 return len(history)
'''
    with DockerStreamingWorker(os.environ['STRATY_TEST_DOCKER_IMAGE'], timeout=30, step_timeout=10) as worker:
        worker.start(source, NONCE)
        assert worker.target([{'close': 10}], 0, 2) == 1
        assert worker.target([{'close': 10}, {'close': 11}], 1, 2) == 2


@pytest.mark.skipif(not os.environ.get('STRATY_TEST_DOCKER_IMAGE'), reason='requires explicit immutable Docker test image')
@pytest.mark.parametrize('source', [
    'def decide(history):\n while True: pass',
    'def decide(history):\n import os\n os.write(1,b"x"*100000)\n return 0',
])
def test_real_docker_resource_failure(source):
    with DockerStreamingWorker(os.environ['STRATY_TEST_DOCKER_IMAGE'], step_timeout=2) as worker:
        worker.start(source, NONCE)
        with pytest.raises(WorkerError):
            worker.target([], 0, 1)
        result = subprocess.run(['docker', 'inspect', worker.name], capture_output=True)
        assert result.returncode != 0
