"""Discard worker console output without silencing unrelated threads."""
from contextlib import contextmanager
import logging
import sys
import threading


_local = threading.local()
_lock = threading.RLock()
_users = 0


class _ThreadStream:
    def __init__(self, stream):
        self.stream = stream

    def write(self, value):
        if getattr(_local, 'quiet', False):
            return len(value)
        return self.stream.write(value)

    def flush(self):
        if not getattr(_local, 'quiet', False):
            self.stream.flush()

    def __getattr__(self, name):
        return getattr(self.stream, name)


@contextmanager
def quiet_worker_output():
    global _users
    with _lock:
        if _users == 0:
            quiet_worker_output.streams = (sys.stdout, sys.stderr)
            quiet_worker_output.handle = logging.Logger.handle
            original = logging.Logger.handle

            def handle(logger, record):
                if not getattr(_local, 'quiet', False):
                    return original(logger, record)

            sys.stdout, sys.stderr = _ThreadStream(sys.stdout), _ThreadStream(sys.stderr)
            logging.Logger.handle = handle
        _users += 1
    previous = getattr(_local, 'quiet', False)
    _local.quiet = True
    try:
        yield
    finally:
        _local.quiet = previous
        with _lock:
            _users -= 1
            if _users == 0:
                sys.stdout, sys.stderr = quiet_worker_output.streams
                logging.Logger.handle = quiet_worker_output.handle
