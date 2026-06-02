"""quant_crawler.webui.upload 的單元測試。"""
from __future__ import annotations

from pathlib import Path

import pytest

from quant_crawler.storage.db import Storage
from quant_crawler.webui import upload


@pytest.fixture
def store(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "papers.db")


@pytest.fixture
def pdf_dir(tmp_path: Path) -> Path:
    d = tmp_path / "pdfs"
    d.mkdir()
    return d


_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def _multipart(files):
    """組一個 multipart/form-data body。files = [(field, filename, bytes)]。"""
    boundary = "----testboundary123"
    parts = []
    for field, filename, content in files:
        head = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field}"'
            + (f'; filename="{filename}"' if filename else "")
            + "\r\nContent-Type: application/pdf\r\n\r\n"
        ).encode("latin-1")
        parts.append(head + content + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("latin-1"))
    body = b"".join(parts)
    ct = f"multipart/form-data; boundary={boundary}"
    return ct, body


# --- boundary / multipart parsing ----------------------------------------

def test_parse_boundary():
    assert upload.parse_boundary(
        "multipart/form-data; boundary=abc123") == b"abc123"
    assert upload.parse_boundary('multipart/form-data; boundary="q"') == b"q"
    assert upload.parse_boundary("application/json") is None


def test_parse_multipart_utf8_chinese_filename():
    """瀏覽器送 UTF-8 中文檔名不該變 mojibake。"""
    fn = "中文動量策略.pdf"
    boundary = "----b"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="files"; '
        f'filename="{fn}"\r\nContent-Type: application/pdf\r\n\r\n'
    ).encode("utf-8") + _PDF + f"\r\n--{boundary}--\r\n".encode("utf-8")
    parts = upload.parse_multipart(body, boundary.encode())
    files = [p for p in parts if p.filename]
    assert len(files) == 1
    assert files[0].filename == fn       # 還原成正確中文
    assert files[0].content == _PDF


def test_chinese_title_preserved_in_paper_row(store, pdf_dir):
    fn = "中文動量策略.pdf"
    boundary = "----b"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="files"; '
        f'filename="{fn}"\r\nContent-Type: application/pdf\r\n\r\n'
    ).encode("utf-8") + _PDF + f"\r\n--{boundary}--\r\n".encode("utf-8")
    res = upload.handle_upload(
        f"multipart/form-data; boundary={boundary}", body,
        storage=store, pdf_dir=pdf_dir,
    )
    assert len(res["uploaded"]) == 1
    rows = store.latest(limit=5, source="manual")
    assert rows[0].title == "中文動量策略"   # 非 mojibake


def test_parse_multipart_extracts_files():
    ct, body = _multipart([
        ("files", "a.pdf", _PDF),
        ("files", "b.pdf", _PDF + b"more"),
    ])
    parts = upload.parse_multipart(body, upload.parse_boundary(ct))
    files = [p for p in parts if p.filename]
    assert len(files) == 2
    assert files[0].filename == "a.pdf"
    assert files[0].content == _PDF
    assert files[1].content == _PDF + b"more"


# --- slug ----------------------------------------------------------------

@pytest.mark.parametrize("fn,expect", [
    ("Foo Bar (2026).pdf", "foo-bar-2026"),
    ("momentum_paper.PDF", "momentum-paper"),
    ("  spaced  .pdf", "spaced"),
    ("中文標題.pdf", "untitled"),   # 非 alnum 全被換掉 → fallback
])
def test_slug_from_filename(fn, expect):
    assert upload.slug_from_filename(fn) == expect


# --- save_upload ---------------------------------------------------------

def test_save_upload_writes_pdf_and_row(store, pdf_dir):
    res = upload.save_upload("My Paper.pdf", _PDF, storage=store, pdf_dir=pdf_dir)
    assert res["ok"] is True
    assert res["source_id"] == "my-paper"
    # 檔案存在（pdf_filename 把 source_id 的 `-` sanitise 成 `_`）
    assert (pdf_dir / "manual_my_paper.pdf").read_bytes() == _PDF
    # DB row 建立
    rows = store.latest(limit=5, source="manual")
    assert len(rows) == 1
    assert rows[0].title == "My Paper"
    assert rows[0].raw_extra.get("uploaded") is True


def test_save_upload_rejects_non_pdf(store, pdf_dir):
    res = upload.save_upload("notes.txt", b"hello", storage=store, pdf_dir=pdf_dir)
    assert res["ok"] is False
    assert "PDF" in res["reason"]
    assert store.count(source="manual") == 0


def test_save_upload_rejects_fake_pdf_ext(store, pdf_dir):
    # 副檔名對但 magic bytes 不對
    res = upload.save_upload("evil.pdf", b"<html>", storage=store, pdf_dir=pdf_dir)
    assert res["ok"] is False


def test_save_upload_rejects_oversize(store, pdf_dir, monkeypatch):
    monkeypatch.setattr(upload, "MAX_FILE_BYTES", 10)
    res = upload.save_upload("big.pdf", _PDF + b"x" * 100,
                             storage=store, pdf_dir=pdf_dir)
    assert res["ok"] is False
    assert "上限" in res["reason"]


def test_save_upload_dedup_source_id(store, pdf_dir):
    r1 = upload.save_upload("dup.pdf", _PDF, storage=store, pdf_dir=pdf_dir)
    r2 = upload.save_upload("dup.pdf", _PDF + b"v2", storage=store, pdf_dir=pdf_dir)
    assert r1["source_id"] == "dup"
    assert r2["source_id"] == "dup-2"      # 衝突加尾碼
    assert (pdf_dir / "manual_dup.pdf").is_file()
    assert (pdf_dir / "manual_dup_2.pdf").is_file()   # `-` → `_` by pdf_filename
    assert store.count(source="manual") == 2


# --- handle_upload (end-to-end multipart) --------------------------------

def test_handle_upload_batch(store, pdf_dir):
    ct, body = _multipart([
        ("files", "one.pdf", _PDF),
        ("files", "two.pdf", _PDF),
        ("files", "bad.txt", b"nope"),       # 會 skip
    ])
    res = upload.handle_upload(ct, body, storage=store, pdf_dir=pdf_dir)
    assert len(res["uploaded"]) == 2
    assert len(res["skipped"]) == 1
    assert store.count(source="manual") == 2


def test_handle_upload_non_multipart(store, pdf_dir):
    res = upload.handle_upload("application/json", b"{}",
                               storage=store, pdf_dir=pdf_dir)
    assert "error" in res
    assert res["uploaded"] == []


def test_handle_upload_no_files(store, pdf_dir):
    # multipart 但只有純欄位、無 filename
    body = (b'------b\r\nContent-Disposition: form-data; name="x"\r\n\r\n'
            b'val\r\n------b--\r\n')
    res = upload.handle_upload("multipart/form-data; boundary=----b",
                               body, storage=store, pdf_dir=pdf_dir)
    assert "error" in res
