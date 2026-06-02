"""手動上傳 PDF 的後端：解析 multipart、存檔、建立 manual paper row。

供 webui `POST /api/upload` 使用。純 stdlib（不依賴 3.13 已移除的 `cgi`）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from quant_crawler.config import PDF_DIR
from quant_crawler.pdf_fetch import local_pdf_path, pdf_filename
from quant_crawler.storage.db import Storage
from quant_crawler.storage.models import PaperRecord

MAX_FILE_BYTES = 50 * 1024 * 1024     # 單檔 50 MB 上限
_SLUG_RE = re.compile(r"[^a-z0-9]+")


# --------------------------------------------------------------------------
# multipart/form-data parser（最小可用版）
# --------------------------------------------------------------------------

@dataclass
class UploadPart:
    field_name: str
    filename: Optional[str]
    content: bytes


def _fix_utf8(s: str) -> str:
    """還原被 latin-1 解碼過的 UTF-8 字串（修中文檔名 mojibake）。

    header 整段用 latin-1 解碼，但瀏覽器的 filename="中文.pdf" 其實是 UTF-8
    bytes。把字串重新 encode 回 latin-1 bytes 再以 UTF-8 解碼即可還原；
    純 ASCII 或非 UTF-8 序列則保留原值。
    """
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def parse_boundary(content_type: str) -> Optional[bytes]:
    """從 Content-Type 取 multipart boundary。"""
    if not content_type or "multipart/form-data" not in content_type:
        return None
    m = re.search(r'boundary=("?)([^";]+)\1', content_type)
    if not m:
        return None
    return m.group(2).encode("latin-1")


def parse_multipart(body: bytes, boundary: bytes) -> List[UploadPart]:
    """切出每個 part。回傳含 filename 的（檔案）+ 純欄位 part。"""
    delim = b"--" + boundary
    parts: List[UploadPart] = []
    # 切塊；忽略前導 preamble 與結尾 `--boundary--`
    for chunk in body.split(delim):
        # 只剝除 delimiter framing 的一層 CRLF，**不**用 strip()（會誤吃
        # content 自身結尾的 \r 或 \n，例如 PDF 結尾的 `%%EOF\n`）。
        if chunk.startswith(b"\r\n"):       # delimiter 之後的 CRLF
            chunk = chunk[2:]
        if chunk.endswith(b"\r\n"):         # 下一個 delimiter 之前的 CRLF
            chunk = chunk[:-2]
        if not chunk or chunk == b"--":     # preamble / 結尾 `--`
            continue
        if b"\r\n\r\n" not in chunk:
            continue
        raw_headers, content = chunk.split(b"\r\n\r\n", 1)
        headers = raw_headers.decode("latin-1", errors="replace")
        cd = ""
        for line in headers.split("\r\n"):
            if line.lower().startswith("content-disposition:"):
                cd = line
                break
        if not cd:
            continue
        fn_m = re.search(r'filename="([^"]*)"', cd)
        name_m = re.search(r'name="([^"]*)"', cd)
        parts.append(UploadPart(
            field_name=name_m.group(1) if name_m else "",
            filename=_fix_utf8(fn_m.group(1)) if fn_m else None,
            content=content,
        ))
    return parts


# --------------------------------------------------------------------------
# 檔名 → slug / 衝突處理
# --------------------------------------------------------------------------

def slug_from_filename(filename: str) -> str:
    """`Foo Bar (2026).pdf` → `foo-bar-2026`。"""
    stem = Path(filename).stem.lower()
    slug = _SLUG_RE.sub("-", stem).strip("-")
    return (slug or "untitled")[:80]


def _unique_source_id(storage: Storage, slug: str, pdf_dir: Path) -> str:
    """若 slug 已存在（DB row 或本地檔），加數字尾碼。"""
    def taken(sid: str) -> bool:
        if local_pdf_path("manual", sid, pdf_dir).is_file():
            return True
        # 查 papers 是否已有此 manual row
        with storage._conn() as c:  # noqa: SLF001 — 內部用
            row = c.execute(
                "SELECT 1 FROM papers WHERE source='manual' AND source_id=?",
                (sid,),
            ).fetchone()
        return row is not None

    if not taken(slug):
        return slug
    i = 2
    while taken(f"{slug}-{i}"):
        i += 1
    return f"{slug}-{i}"


# --------------------------------------------------------------------------
# 單檔 / 批次上傳
# --------------------------------------------------------------------------

def _looks_like_pdf(filename: Optional[str], content: bytes) -> bool:
    if not filename or not filename.lower().endswith(".pdf"):
        return False
    return content[:5].startswith(b"%PDF")


def save_upload(
    filename: str, content: bytes,
    storage: Optional[Storage] = None, pdf_dir: Path = PDF_DIR,
) -> Dict[str, object]:
    """存一個上傳檔 + 建 manual paper row。回傳 result dict。"""
    storage = storage or Storage()
    pdf_dir = Path(pdf_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    if len(content) > MAX_FILE_BYTES:
        return {"filename": filename, "ok": False,
                "reason": f"超過 {MAX_FILE_BYTES // (1024*1024)} MB 上限"}
    if not _looks_like_pdf(filename, content):
        return {"filename": filename, "ok": False,
                "reason": "不是有效 PDF（副檔名或 magic bytes 不符）"}

    slug = slug_from_filename(filename)
    source_id = _unique_source_id(storage, slug, pdf_dir)
    dest = local_pdf_path("manual", source_id, pdf_dir)
    dest.write_bytes(content)

    rec = PaperRecord(
        source="manual",
        source_id=source_id,
        title=Path(filename).stem,
        abstract="",
        published=None,
        url="",
        pdf_url="",
        categories=[],
        keywords_hit=[],
        raw_extra={"uploaded": True, "orig_filename": filename},
        fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    storage.upsert(rec)
    return {"filename": filename, "ok": True, "source_id": source_id,
            "pdf": pdf_filename("manual", source_id), "bytes": len(content)}


def handle_upload(
    content_type: str, body: bytes,
    storage: Optional[Storage] = None, pdf_dir: Path = PDF_DIR,
) -> Dict[str, object]:
    """parse multipart + 逐檔 save。回傳 {uploaded, skipped, summary}。"""
    boundary = parse_boundary(content_type)
    if boundary is None:
        return {"error": "expected multipart/form-data", "uploaded": [],
                "skipped": []}
    parts = parse_multipart(body, boundary)
    files = [p for p in parts if p.filename]
    if not files:
        return {"error": "no files in upload", "uploaded": [], "skipped": []}

    storage = storage or Storage()
    uploaded: List[dict] = []
    skipped: List[dict] = []
    for part in files:
        res = save_upload(part.filename, part.content,
                          storage=storage, pdf_dir=pdf_dir)
        (uploaded if res["ok"] else skipped).append(res)
    return {
        "uploaded": uploaded,
        "skipped": skipped,
        "summary": f"{len(uploaded)} 成功 / {len(skipped)} 略過",
    }
