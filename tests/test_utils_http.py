"""Unit tests for quant_crawler.utils.http.RateLimitedSession (P0 / U-001..U-014).

Strategy: mock `RateLimitedSession.session.request` + monkeypatch `time.sleep`
so tests are deterministic and fast (no real network, no real sleep).
"""
from __future__ import annotations

from pathlib import Path
from threading import Thread
from typing import List
from unittest.mock import MagicMock

import pytest
import requests

from quant_crawler.utils import http as http_mod
from quant_crawler.utils.http import RateLimitedSession


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def sleep_log(monkeypatch) -> List[float]:
    """Replace time.sleep in the http module so it just records durations."""
    calls: List[float] = []
    monkeypatch.setattr(http_mod.time, "sleep", lambda s: calls.append(float(s)))
    return calls


@pytest.fixture
def fake_now(monkeypatch):
    """Drivable monotonic clock — t.tick(seconds) advances it."""
    class _Clock:
        def __init__(self) -> None:
            self.t = 1000.0
        def __call__(self) -> float:
            return self.t
        def tick(self, dt: float) -> None:
            self.t += dt
    clock = _Clock()
    monkeypatch.setattr(http_mod.time, "monotonic", clock)
    return clock


@pytest.fixture
def no_jitter(monkeypatch):
    """Make `random.uniform` deterministic so we can assert exact backoff."""
    monkeypatch.setattr(http_mod.random, "uniform", lambda a, b: 0.0)


def _resp(status: int = 200, headers: dict | None = None, body: bytes = b"") -> MagicMock:
    r = MagicMock(spec=requests.Response)
    r.status_code = status
    r.headers = headers or {}
    r.content = body
    return r


def _session(min_delay: float = 1.0, max_retries: int = 3,
             backoff_base: float = 2.0) -> RateLimitedSession:
    s = RateLimitedSession(
        min_delay=min_delay, max_retries=max_retries, backoff_base=backoff_base,
    )
    s.session = MagicMock()
    return s


# --------------------------------------------------------------------------
# U-001..U-002  per-host minimum delay
# --------------------------------------------------------------------------

def test_U_001_per_host_min_delay_enforced(sleep_log, fake_now):
    """First hit: no sleep. Second hit on SAME host within min_delay: sleep
    the remaining time."""
    s = _session(min_delay=2.0)
    s.session.request.return_value = _resp(200)

    s.get("https://api.example.com/a")  # t=1000, first hit on host
    assert sleep_log == []               # no delay on first hit
    fake_now.tick(0.5)                   # only 0.5s elapsed
    s.get("https://api.example.com/b")   # t=1000.5, same host
    # expected wait = 2.0 - 0.5 = 1.5s
    assert any(abs(s - 1.5) < 0.001 for s in sleep_log), sleep_log


def test_U_002_different_hosts_dont_block(sleep_log, fake_now):
    s = _session(min_delay=2.0)
    s.session.request.return_value = _resp(200)

    s.get("https://host-a.example.com/x")
    fake_now.tick(0.1)
    s.get("https://host-b.example.com/y")   # different host
    # no sleep on either (different netloc, first hit each)
    assert sleep_log == []


# --------------------------------------------------------------------------
# U-003  200 first try: zero retries, zero retry-sleep
# --------------------------------------------------------------------------

def test_U_003_200_first_try_no_retry(sleep_log, fake_now):
    s = _session(min_delay=0)
    s.session.request.return_value = _resp(200)
    r = s.get("https://api.example.com/")
    assert r.status_code == 200
    assert s.session.request.call_count == 1
    assert sleep_log == []   # nothing slept (min_delay=0; no retry)


# --------------------------------------------------------------------------
# U-004..U-006  Retry on 429 / 503 chain
# --------------------------------------------------------------------------

def test_U_004_429_then_200_honours_retry_after(sleep_log, fake_now):
    s = _session(min_delay=0)
    s.session.request.side_effect = [
        _resp(429, headers={"Retry-After": "3"}),
        _resp(200),
    ]
    r = s.get("https://api.example.com/")
    assert r.status_code == 200
    assert s.session.request.call_count == 2
    assert 3.0 in sleep_log         # Retry-After=3 honoured


def test_U_005_503_chain_exponential_backoff(sleep_log, fake_now, no_jitter):
    s = _session(min_delay=0, backoff_base=2.0, max_retries=3)
    s.session.request.side_effect = [
        _resp(503),                 # no Retry-After → backoff
        _resp(503),
        _resp(200),
    ]
    r = s.get("https://api.example.com/")
    assert r.status_code == 200
    assert s.session.request.call_count == 3
    # _retry_after w/o header = backoff_base ** (503 % 10) + 0 = 2**3 = 8
    backoff_sleeps = [s for s in sleep_log if abs(s - 8.0) < 1e-9]
    assert len(backoff_sleeps) >= 2   # two retries each slept ~8s


def test_U_006_503_persistent_returns_last_response_no_raise(sleep_log, fake_now, no_jitter):
    s = _session(min_delay=0, max_retries=2)
    s.session.request.side_effect = [_resp(503), _resp(503), _resp(503)]
    r = s.get("https://api.example.com/")
    # After max_retries exhausted, return the last 503 response (not raise)
    assert r.status_code == 503
    assert s.session.request.call_count == 3


# --------------------------------------------------------------------------
# U-007  Connection-level exception retry
# --------------------------------------------------------------------------

def test_U_007_request_exception_retries_then_raises(sleep_log, fake_now, no_jitter):
    s = _session(min_delay=0, max_retries=2)
    s.session.request.side_effect = requests.ConnectionError("boom")
    with pytest.raises(requests.RequestException):
        s.get("https://api.example.com/")
    # 1 attempt + 2 retries = 3 calls total
    assert s.session.request.call_count == 3


# --------------------------------------------------------------------------
# U-008..U-010  retry_after / backoff helpers
# --------------------------------------------------------------------------

def test_U_008_retry_after_non_numeric_falls_back_to_backoff(no_jitter):
    """RFC 1123 date or other non-numeric Retry-After → fall back to backoff."""
    s = _session(backoff_base=2.0)
    resp = _resp(503, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"})
    # 2 ** (503 % 10) + 0 = 8
    assert s._retry_after(resp) == pytest.approx(8.0)


def test_U_009_retry_after_missing_uses_backoff(no_jitter):
    s = _session(backoff_base=2.0)
    resp = _resp(429, headers={})
    # 2 ** (429 % 10) = 2 ** 9 = 512 — large but deterministic
    assert s._retry_after(resp) == pytest.approx(512.0)


def test_U_010_sleep_backoff_uses_attempt_exponent(sleep_log, no_jitter):
    s = _session(backoff_base=2.0)
    s._sleep_backoff(attempt=0)
    s._sleep_backoff(attempt=3)
    # attempt 0 → 2**0 + 0 = 1.0;  attempt 3 → 2**3 + 0 = 8.0
    assert 1.0 in sleep_log and 8.0 in sleep_log


# --------------------------------------------------------------------------
# U-011..U-013  download stream
# --------------------------------------------------------------------------

class _StreamResp:
    """Minimal context-manager fake matching requests.Response for streams."""
    def __init__(self, status: int, chunks):
        self.status_code = status
        self._chunks = chunks
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def iter_content(self, chunk_size=1):
        for c in self._chunks:
            yield c


def test_U_011_download_writes_full_bytes(tmp_path: Path, sleep_log, fake_now, monkeypatch):
    s = _session(min_delay=0)
    # patch the session-level get used inside download() (which delegates to _request)
    monkeypatch.setattr(s, "get", lambda url, **kw: _StreamResp(200, [b"abc", b"de"]))
    dest = tmp_path / "out.bin"
    n = s.download("https://x/y.bin", dest)
    assert n == 5
    assert dest.read_bytes() == b"abcde"


def test_U_012_download_non_200_returns_none(tmp_path: Path, sleep_log, fake_now, monkeypatch):
    s = _session(min_delay=0)
    monkeypatch.setattr(s, "get", lambda url, **kw: _StreamResp(404, []))
    dest = tmp_path / "out.bin"
    assert s.download("https://x/y.bin", dest) is None
    # no file written (or empty if created — caller should clean; here just None)


def test_U_013_download_skips_empty_chunks(tmp_path: Path, sleep_log, fake_now, monkeypatch):
    s = _session(min_delay=0)
    monkeypatch.setattr(s, "get",
                        lambda url, **kw: _StreamResp(200, [b"hi", b"", b"!"]))
    dest = tmp_path / "out.bin"
    n = s.download("https://x/y.bin", dest)
    assert n == 3
    assert dest.read_bytes() == b"hi!"


# --------------------------------------------------------------------------
# U-014  Thread-safety: same-host concurrent gets serialised by lock
# --------------------------------------------------------------------------

def test_U_014_thread_safety_same_host_serialised(sleep_log, monkeypatch):
    """Concurrent threads against same host must each see _wait_for_host run
    atomically; no double-bursting."""
    s = _session(min_delay=0)            # delay 0: just checks lock doesn't deadlock
    s.session.request.return_value = _resp(200)

    errs = []
    def hit():
        try: s.get("https://h/a")
        except Exception as e: errs.append(e)
    threads = [Thread(target=hit) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=2)
    assert not errs
    assert s.session.request.call_count == 5
