"""伺服器沒宣告 charset 時的解碼修正。

實測背景：``nep.repec.org`` 送的是裸的 ``Content-Type: text/html``（沒有
charset），requests 依 RFC 2616 退回 ISO-8859-1，於是 ``resp.text`` 把 UTF-8
位元組當 latin-1 解碼。`–`（E2 80 93）變成 `â\\x80\\x93`，其中 U+0080 是 C1
控制字元，寫進 YAML 之後 YAML 直接拒收——13 份 manifest 就是這樣壞掉的。

測試的重點在兩個方向都要對：**該修的要修，不該碰的絕不能碰。** 伺服器明確
宣告 latin-1 時覆蓋它，會把正確解碼的西歐語系內容弄壞——那是用一個 bug 換
另一個 bug。
"""
from __future__ import annotations

from unittest.mock import MagicMock

import requests

from quant_crawler.utils.http import _fix_charset_fallback


def _resp(*, encoding, content_type, apparent="utf-8"):
    r = MagicMock(spec=requests.Response)
    r.headers = {"content-type": content_type}
    r.encoding = encoding
    r.apparent_encoding = apparent
    r.url = "https://example.test/x"
    return r


def test_bare_text_html_gets_the_sniffed_encoding():
    """沒有 charset 的 text/html —— 這正是 repec 的形狀。"""
    r = _resp(encoding="ISO-8859-1", content_type="text/html")
    _fix_charset_fallback(r)
    assert r.encoding == "utf-8"


def test_declared_charset_is_left_alone():
    """標頭裡有 charset 就不動，即使它是 latin-1。

    那是一個宣告不是猜測。覆蓋它會把本來解碼正確的西歐語系內容弄壞。
    """
    r = _resp(encoding="ISO-8859-1",
              content_type="text/html; charset=ISO-8859-1")
    _fix_charset_fallback(r)
    assert r.encoding == "ISO-8859-1"


def test_declared_utf8_is_left_alone():
    r = _resp(encoding="utf-8", content_type="text/html; charset=utf-8")
    _fix_charset_fallback(r)
    assert r.encoding == "utf-8"


def test_non_fallback_encoding_is_left_alone():
    """只在 encoding 正好是 requests 的 fallback 值時介入。

    介入條件寫窄一點，是為了讓「它為什麼改了這個回應的編碼」永遠答得出來。
    """
    r = _resp(encoding="Shift_JIS", content_type="text/html")
    _fix_charset_fallback(r)
    assert r.encoding == "Shift_JIS"


def test_no_sniff_result_leaves_it_alone():
    r = _resp(encoding="ISO-8859-1", content_type="text/html", apparent=None)
    _fix_charset_fallback(r)
    assert r.encoding == "ISO-8859-1"


def test_sniff_agreeing_with_fallback_is_a_no_op():
    r = _resp(encoding="ISO-8859-1", content_type="text/html",
              apparent="ISO-8859-1")
    _fix_charset_fallback(r)
    assert r.encoding == "ISO-8859-1"


def test_objects_without_encoding_are_tolerated():
    """不是 requests.Response 的東西進來時不得炸。

    既有的 http 測試就是用 MagicMock(spec=Response) 餵進來的，而 `encoding`
    是 __init__ 裡設的實例屬性、不在 class spec 裡——第一版直接取屬性，
    把六個既有測試打成 AttributeError。
    """
    bare = MagicMock(spec=requests.Response)
    bare.headers = {}
    _fix_charset_fallback(bare)          # 不得丟例外


def test_the_real_mojibake_round_trip():
    """端到端：修好之後，那個破折號要是真的破折號。

    斷言裡的控制字元一律寫成 \\u escape，不要嵌字面字元。同一個坑已經踩過
    一次——scripts/repair_mojibake.py 的殘骸偵測正則裡嵌了字面 C1 字元，
    在寫檔過程中整個範圍塌成一個連字號，於是偵測器沉默地少抓一半。
    寫成 escape 的另一個好處是：斷言的內容在原始碼上看得見。
    """
    C1_PAD = "\u0080"                     # UTF-8 位元組 E2 80 93 的中間那個
    original = "2018\u20132020 US-China"   # U+2013 EN DASH

    body = original.encode("utf-8")
    assert body[4:7] == b"\xe2\x80\x93"

    wrong = body.decode("ISO-8859-1")     # requests 沒有 charset 時做的事
    assert C1_PAD in wrong, "重現不出當初的災情，這個測試就沒有意義"
    assert wrong != original

    right = body.decode("utf-8")          # 修正後做的事
    assert right == original
    assert C1_PAD not in right
