#!/usr/bin/env python3
"""檢查 git commit message 是否符合本 repo 的中文撰寫規範。

對應 spec：docs/spec/git-commit-style.md

用法：
    check_commit_msg.py HEAD                        # 檢查最近一次 commit
    check_commit_msg.py <commit-sha>                # 檢查指定 commit
    check_commit_msg.py --file .git/COMMIT_EDITMSG  # 給 commit-msg hook 用
    check_commit_msg.py --stdin                     # 從 stdin 讀
    check_commit_msg.py --strict HEAD               # 任一 issue 即 exit 1

預設為 lint 模式：印 warning 但 exit 0；`--strict` 才用非零 exit code。
純 stdlib 實作，無外部相依。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

# --- 規範常數（與 docs/spec/git-commit-style.md 一致）-----------------------

MAX_SUBJECT_LEN = 72  # 不含 prefix

# Prefix 模式：兩格內出現 `<word>:` 視為 prefix，後面接空白
PREFIX_RE = re.compile(
    r"^("
    r"M\d+[a-z]?"                          # safe-yolo Mn / M21a
    r"|feat|fix|refactor|chore|test|docs|build|ci|perf|style|revert|merge"
    r")\s*:\s*",
    re.IGNORECASE,
)

# 純機械訊息：dependabot / lockfile / Merge pull request / Revert ...
SKIP_AUTO_RE = re.compile(
    r"^(Merge (pull request|branch|remote-tracking branch)|"
    r"Revert \"|"
    r"Bump\s+\S+\s+from|"          # dependabot
    r"chore\(deps\)|chore: bump|"
    r"Update\s+.*lock)",            # lockfile bump (package-lock.json, Pipfile.lock, etc.)
    re.IGNORECASE,
)

# Git trailer：line 開頭 Key: Value
TRAILER_RE = re.compile(
    r"^([A-Z][A-Za-z-]+(-By)?|Closes|Refs|Fixes|See-Also|Reviewed-By):\s",
)


def _is_cjk(ch: str) -> bool:
    """判斷一字元是否為 CJK Unified Ideograph（不含日文假名 / 韓文）。"""
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0x20000 <= cp <= 0x2A6DF
    )


def _strip_ascii_tokens(text: str) -> str:
    """移除常見「規範允許保留原文」的 ASCII token，避免它們稀釋中文比例。

    粗略 heuristic：保留中文 + 標點，其餘 ASCII run 視為可忽略。
    """
    cleaned: List[str] = []
    for ch in text:
        if _is_cjk(ch):
            cleaned.append(ch)
        elif unicodedata.category(ch).startswith("P") and ord(ch) > 0x7F:
            # 全形標點視為中文一部分
            cleaned.append(ch)
    return "".join(cleaned)


@dataclass
class CheckResult:
    subject: str
    body: str
    warnings: List[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""

    @property
    def ok(self) -> bool:
        return not self.warnings


def check(message: str) -> CheckResult:
    """檢查一份 commit message；回傳 (subject, body, warnings)。"""
    lines = message.splitlines()
    # 去除前置空行
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return CheckResult("", "", ["empty commit message"])
    subject = lines[0]
    # body：subject 後第一行 blank 之後到結尾
    body_lines = lines[2:] if len(lines) >= 3 else []
    body = "\n".join(body_lines).rstrip()

    r = CheckResult(subject=subject, body=body)

    # 1. 機械訊息直接 skip
    if SKIP_AUTO_RE.match(subject):
        r.skipped = True
        r.skip_reason = "auto-generated tool message (dependabot / merge / revert)"
        return r

    # 2. Prefix 偵測（不算進長度上限）
    m = PREFIX_RE.match(subject)
    if m:
        rest = subject[m.end():].strip()
    else:
        rest = subject.strip()

    # 3. 長度檢查
    if len(rest) > MAX_SUBJECT_LEN:
        r.warnings.append(
            f"subject 過長：{len(rest)} > {MAX_SUBJECT_LEN}（不含 prefix）"
        )

    # 4. 中文檢查 — 主體至少要有一個 CJK 字元
    # 技術識別符（檔名/函式/CLI flag）保留原文，所以不強制比例，只要求「存在」
    cjk_chars = sum(1 for c in rest if _is_cjk(c))
    if cjk_chars == 0:
        r.warnings.append(
            "subject 不含繁體中文字元 — 違反 docs/spec/git-commit-style.md"
        )

    # 5. body 行寬（≤ 80）— 跳過 git trailer 行
    for i, ln in enumerate(body.splitlines(), start=3):
        if TRAILER_RE.match(ln):
            continue
        # 計算「視覺寬度」近似：CJK 算 2，其他算 1
        width = sum(2 if _is_cjk(c) else 1 for c in ln)
        if width > 100:   # 寬鬆：給程式碼/URL 留空間
            r.warnings.append(
                f"body 第 {i} 行視覺寬度 {width} > 100"
            )

    return r


# --- 取 commit message 的來源 ----------------------------------------------

def _from_git_ref(ref: str) -> str:
    out = subprocess.run(
        ["git", "log", "-1", "--format=%B", ref],
        capture_output=True, text=True, check=True,
    )
    return out.stdout


def _from_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _from_stdin() -> str:
    return sys.stdin.read()


# --- 報告 ------------------------------------------------------------------

def _format(r: CheckResult) -> str:
    if r.skipped:
        return f"[SKIP] {r.subject!r}  ({r.skip_reason})"
    if r.ok:
        return f"[OK]   {r.subject!r}"
    lines = [f"[WARN] {r.subject!r}"]
    for w in r.warnings:
        lines.append(f"       - {w}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--file", help="從檔案讀（commit-msg hook 用）")
    g.add_argument("--stdin", action="store_true", help="從 stdin 讀")
    p.add_argument("ref", nargs="?", default="HEAD",
                   help="commit ref（預設 HEAD；--file/--stdin 時忽略）")
    p.add_argument("--strict", action="store_true",
                   help="任一 warning 即 exit 1（預設 lint 模式 exit 0）")
    args = p.parse_args(argv)

    if args.file:
        msg = _from_file(args.file)
    elif args.stdin:
        msg = _from_stdin()
    else:
        try:
            msg = _from_git_ref(args.ref)
        except subprocess.CalledProcessError as e:
            print(f"git log 失敗：{e.stderr}", file=sys.stderr)
            return 2

    r = check(msg)
    print(_format(r), file=sys.stderr if r.warnings else sys.stdout)
    if r.warnings and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
