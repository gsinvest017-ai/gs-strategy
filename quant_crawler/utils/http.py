"""Thin polite-HTTP wrapper: per-host rate limiting + retries with backoff."""
from __future__ import annotations

import random
import time
from threading import Lock
from typing import Optional
from urllib.parse import urlparse

import requests
from requests import Response

from quant_crawler.config import (
    DEFAULT_BACKOFF_BASE,
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_USER_AGENT,
)
from quant_crawler.utils.logging import get_logger

log = get_logger("http")

#: 伺服器沒宣告 charset 時 requests 會退回的編碼。
#:
#: 這是 RFC 2616 對 ``text/*`` 的預設，requests 至今仍遵守它。問題是現代網站
#: 幾乎都送 UTF-8，卻常常忘了在 Content-Type 裡宣告——於是 ``resp.text`` 把
#: UTF-8 位元組當成 latin-1 解碼，`–`（E2 80 93）就變成 `â\x80\x93`。存成
#: UTF-8 之後，U+0080 這個控制字元就進了資料庫與 YAML，而 YAML 拒收控制字元。
#:
#: 實測 ``nep.repec.org`` 正是這一型：Content-Type 是裸的 ``text/html``，
#: 但 HTML body 自己宣告 ``charset=utf-8``。
_REQUESTS_CHARSET_FALLBACK = "ISO-8859-1"


def _fix_charset_fallback(resp: Response) -> None:
    """伺服器沒宣告 charset 時，改用內容推斷的編碼而不是 latin-1。

    只在**兩個條件同時成立**時介入：``resp.encoding`` 正好是 requests 的
    fallback 值，而且 Content-Type 標頭裡真的找不到 ``charset=``。伺服器明確
    宣告 latin-1 時不動它——那是一個宣告，不是猜測，覆蓋它會把正確解碼的
    西歐語系內容弄壞。

    修在這一層而不是各個 crawler 裡，是因為六個 crawler（aqr / arxiv / fed /
    nber / repec / wiley）全都吃 ``resp.text``，逐一修等於留六個可以再犯的地方。
    """
    declared = "charset=" in resp.headers.get("content-type", "").lower()
    if declared or resp.encoding != _REQUESTS_CHARSET_FALLBACK:
        return
    guess = resp.apparent_encoding
    if not guess:
        return
    log.debug("no charset on %s; %s -> %s", resp.url, resp.encoding, guess)
    resp.encoding = guess


class RateLimitedSession:
    """Minimum-delay-per-host wrapper around requests.Session."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        min_delay: float = 2.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept": "*/*"})
        self.min_delay = min_delay
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.timeout = timeout
        self._last_hit: dict[str, float] = {}
        self._lock = Lock()

    def _wait_for_host(self, url: str) -> None:
        host = urlparse(url).netloc
        with self._lock:
            now = time.monotonic()
            last = self._last_hit.get(host, 0.0)
            wait = self.min_delay - (now - last)
            if wait > 0:
                time.sleep(wait)
            self._last_hit[host] = time.monotonic()

    def get(self, url: str, **kwargs) -> Response:
        return self._request("GET", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> Response:
        kwargs.setdefault("timeout", self.timeout)
        attempt = 0
        while True:
            self._wait_for_host(url)
            try:
                resp = self.session.request(method, url, **kwargs)
            except requests.RequestException as e:
                log.warning("request error %s on %s (attempt %d)", e, url, attempt + 1)
                if attempt >= self.max_retries:
                    raise
                self._sleep_backoff(attempt)
                attempt += 1
                continue

            if resp.status_code in (429, 500, 502, 503, 504):
                if attempt >= self.max_retries:
                    log.error(
                        "giving up on %s after %d attempts (last status %d)",
                        url,
                        attempt + 1,
                        resp.status_code,
                    )
                    return resp
                retry_after = self._retry_after(resp)
                log.warning(
                    "status %d on %s, retrying after %.1fs", resp.status_code, url, retry_after
                )
                time.sleep(retry_after)
                attempt += 1
                continue
            _fix_charset_fallback(resp)
            return resp

    def _retry_after(self, resp: Response) -> float:
        ra = resp.headers.get("Retry-After")
        if ra is not None:
            try:
                return float(ra)
            except ValueError:
                pass
        return self.backoff_base ** (resp.status_code % 10) + random.uniform(0, 1)

    def _sleep_backoff(self, attempt: int) -> None:
        time.sleep(self.backoff_base**attempt + random.uniform(0, 1))

    def download(self, url: str, dest, chunk_size: int = 1 << 15) -> Optional[int]:
        """Stream a response to disk; returns bytes written or None on failure."""
        with self.get(url, stream=True) as resp:
            if resp.status_code != 200:
                log.warning("download failed %s -> %d", url, resp.status_code)
                return None
            total = 0
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)
            return total
