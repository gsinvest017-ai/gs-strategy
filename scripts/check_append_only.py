#!/usr/bin/env python3
"""擋住對「只准新增、不准改寫」的檔案所做的改寫。

對應 spec：docs/spec/statistical-decision-tree.md §7、docs/spec/auto-research-funnel.md §4

守的是兩件事，兩件都是統計紀律的物理前提：

**Pre-registration 不可改寫。** 統計檢定的效力建立在「假說先於資料」之上。
若事前登記檔可以在看完結果之後被編輯，那它就只是一份晚一點才寫的報告，
提供不了任何保證。所以既有的 ``experiments/preregistration/*.yaml`` 一旦
commit 就凍結：只能新增檔案，不能修改、不能刪除、不能改名。

**Trial ledger 只能追加。** ``log/trials.jsonl`` 是 DSR 分母的來源。既有行
若可以被改寫，就可以在事後把一次失敗的嘗試從母體裡拿掉，讓 N 變小、DSR 變
好看——而那是這整套設計要防的頭號行為。所以只准在檔尾追加。

為什麼是 hook 而不是規則
------------------------
兩件事都可以寫在文件裡請人遵守，但「請人遵守」擋不住的正是最需要擋的情境：
結果不如預期、時間壓力大、而改一行就能讓數字好看。用資料結構與 exit code
強制，比用 prompt 或 convention 約束可靠——這一條是從 gs-MINT 的
GATE_REGISTRY_POLICY 學來的。

繞過的方式是 ``git commit --no-verify``，而且刻意留著。硬要繞過時它會在
reflog 與 CI 上留下痕跡；把繞過做成不可能，只會讓人改成在 hook 外面動手。

用法
----
    check_append_only.py                 # 檢查目前 staged 的變更（pre-commit 用）
    check_append_only.py --rev-range A..B   # 檢查一段 commit 範圍（CI 用）
純 stdlib，無外部相依。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass

#: 一旦 commit 就凍結的路徑（前綴比對）。新增檔案永遠允許。
FROZEN_PREFIXES = ("experiments/preregistration/",)

#: 只准在檔尾追加的檔案。
APPEND_ONLY_PATHS = ("log/trials.jsonl",)


@dataclass
class Violation:
    path: str
    kind: str
    detail: str

    def render(self) -> str:
        return f"  ✗ {self.path}\n    {self.kind}：{self.detail}"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    ).stdout


def _staged_changes(rev_range: str | None) -> list[tuple[str, str, str]]:
    """回傳 (status, old_path, new_path)。status 是 A/M/D/R… """
    if rev_range:
        raw = _git("diff", "--name-status", "-M", rev_range)
    else:
        raw = _git("diff", "--cached", "--name-status", "-M")
    out = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            out.append((status, parts[1], parts[2]))
        else:
            out.append((status, parts[1], parts[1]))
    return out


def _blob(rev: str, path: str) -> list[str] | None:
    r = subprocess.run(["git", "show", f"{rev}:{path}"],
                       capture_output=True, text=True, check=False)
    if r.returncode != 0:
        return None
    return r.stdout.splitlines()


def _staged_lines(path: str) -> list[str] | None:
    r = subprocess.run(["git", "show", f":{path}"],
                       capture_output=True, text=True, check=False)
    if r.returncode != 0:
        return None
    return r.stdout.splitlines()


def check(rev_range: str | None = None, base: str = "HEAD") -> list[Violation]:
    violations: list[Violation] = []
    for status, old_path, new_path in _staged_changes(rev_range):
        # --- 凍結的路徑：只准新增 ---------------------------------------
        for prefix in FROZEN_PREFIXES:
            if not (old_path.startswith(prefix) or new_path.startswith(prefix)):
                continue
            if status == "A":
                continue                                  # 新增永遠可以
            kind = {"M": "修改", "D": "刪除"}.get(status[0], f"變更（{status}）")
            if status.startswith("R"):
                kind = "改名"
            violations.append(Violation(
                new_path, f"pre-registration 不可{kind}",
                "事前登記一旦 commit 就凍結。判準要改，就開一份新的登記檔並在"
                "裡面寫明它取代了哪一份、為什麼——那樣讀者看得到判準變過，"
                "而就地編輯會讓「事前」這兩個字失去意義。",
            ))

        # --- append-only 的檔案：既有行不可改 ----------------------------
        if new_path in APPEND_ONLY_PATHS:
            if status == "A":
                continue
            if status == "D" or status.startswith("R"):
                violations.append(Violation(
                    new_path, "ledger 不可刪除或改名",
                    "它是 DSR 分母的唯一來源。",
                ))
                continue
            before = _blob(base, old_path)
            after = _staged_lines(new_path)
            if before is None or after is None:
                continue
            if len(after) < len(before):
                violations.append(Violation(
                    new_path, "ledger 被截短",
                    f"{len(before)} 行 -> {len(after)} 行。刪掉既有的 trial 等於"
                    "把一次嘗試從母體裡拿掉，N 變小、DSR 變好看。",
                ))
                continue
            for i, (b, a) in enumerate(zip(before, after), start=1):
                if b != a:
                    violations.append(Violation(
                        new_path, f"ledger 第 {i} 行被改寫",
                        "只准在檔尾追加。同一個 trial 要更新，就再追加一行"
                        "相同 trial_id 的記錄——harness 取同 id 的最後一筆，"
                        "而改寫會讓歷史狀態消失。",
                    ))
                    break
    return violations


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rev-range", help="改檢查一段 commit 範圍，例如 origin/main..HEAD")
    ap.add_argument("--base", default="HEAD",
                    help="比對基準（預設 HEAD；檢查 staged 變更時用它取既有內容）")
    args = ap.parse_args(argv)

    violations = check(args.rev_range, base=args.base)
    if not violations:
        return 0

    print("[append-only] 這些變更違反了「只准新增、不准改寫」：", file=sys.stderr)
    for v in violations:
        print(v.render(), file=sys.stderr)
    print("", file=sys.stderr)
    print("為什麼擋：事前登記可事後編輯，「假說先於資料」就不成立；ledger 既有行"
          "可改寫，就可以在事後把失敗的嘗試從 DSR 的分母裡拿掉。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
