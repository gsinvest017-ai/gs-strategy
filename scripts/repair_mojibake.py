#!/usr/bin/env python3
"""修復 papers.db 裡已經寫壞的 mojibake，並重生受影響的策略骨架。

這個腳本修的是**症狀**，不是病因
--------------------------------
病因在 ``quant_crawler/utils/http.py``：伺服器送裸的 ``Content-Type: text/html``
沒有 charset 時，requests 依 RFC 2616 退回 ``ISO-8859-1``，於是 ``resp.text``
把 UTF-8 位元組當 latin-1 解碼。`–`（U+2013，位元組 E2 80 93）就變成
`â\\x80\\x93`，其中 U+0080 是 C1 控制字元——寫進 YAML 之後 YAML 直接拒收。

那個病因已在 ``_fix_charset_fallback()`` 修掉，但**已經進了資料庫的資料不會
自己好**。本腳本負責那一半：414 筆 papers 裡把壞掉的挑出來、還原、重生骨架。

還原交給 ftfy，判定留在這裡
--------------------------
一開始這裡自己寫了 ``s.encode("latin-1").decode("utf-8")``。拿資料庫的 29 個
真實樣本實測之後換掉了：**單次還原有 5 個沒修乾淨**，因為它們是多層編碼——
``MothersÃ¢â\\x82¬â\\x84¢`` 剝一層只會變成 ``Mothersâ€™``，還要再剝一次；而且
第二層走的是 cp1252（0x80→€、0x93→"）不是 latin-1，單一編碼的往返修不動它。

``ftfy.fix_encoding()`` 把 29 個全部修乾淨（0 個殘留），而且對**本來就沒有
mojibake 形狀**的欄位一個字都沒改（實測 0 個變動）——它不會順手做引號正規化
之類的事，那些在 ``ftfy.fix_text()`` 裡，不在 ``fix_encoding()`` 裡。

分工因此是：**ftfy 決定怎麼修，本腳本決定修哪些。** 判定要同時滿足兩個條件：

1. **形狀對**：字串裡出現 ``[Â-ô][\\x80-\\xBF]`` 這種序列。這正是 UTF-8 的
   「前導位元組 + 後續位元組」被逐一映射到 latin-1 之後的長相。正常的書目文字
   幾乎不可能出現「Ã 後面緊跟一個 C1 控制字元或標點區字元」。
2. **修完是乾淨的**：修完再也找不到 C1 控制字元、``â€`` 或 ``Ã`` 這些殘骸。

不把 ftfy 無差別套在每個欄位上，是因為那樣就無法回答「它到底動了什麼、為什麼」。
有了條件 1，每一次改動都能指回一段可以看見的損壞。

用法
----
    python scripts/repair_mojibake.py                    # dry-run，印出前後對照
    python scripts/repair_mojibake.py --apply            # 寫回 papers.db
    python scripts/repair_mojibake.py --apply --regenerate  # 併重生受影響的骨架
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import ftfy
except ImportError:                                   # pragma: no cover
    # 明講而不是靜默退回自寫版本：自寫版本在多層編碼上會留下 5/29 沒修乾淨，
    # 而「修了但沒修乾淨」比「沒修」難發現得多。
    print("需要 ftfy：pip install ftfy（自寫的單次還原對多層編碼會留下殘骸）",
          file=sys.stderr)
    raise

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO / "data" / "papers.db"
DEFAULT_OUT_ROOT = REPO / "strategies" / "_generated"

#: UTF-8 的前導位元組（C2–F4）後接一個後續位元組（80–BF），兩者都被逐一
#: 映射到 latin-1 的結果。這是雙重編碼唯一會留下的、可辨識的形狀。
#: 一律用 \u escape 寫，絕不嵌字面字元。這個 class 涵蓋 U+0080-U+009F 的 C1
#: 控制字元，而那些字元在原始碼、剪貼簿、終端機之間傳遞時會被靜默吃掉——
#: 正則本身變成 mojibake 的受害者，然後偵測器沉默地少抓一半。實際踩過：
#: 下面 MOJIBAKE_RESIDUE 的 C1 範圍曾塌成一個字面連字號，於是每個含連字號的
#: 摘要都被誤判成「還有殘骸」而跳過，修復數從 32 掉到 16。
MOJIBAKE_SHAPE = re.compile("[\u00c2-\u00f4][\u0080-\u00bf]")

#: 直接存純文字的欄位。
TEXT_COLUMNS = ("title", "abstract")
#: 存 JSON 的欄位——要 parse 進去逐個字串修，不能整串當文字修，
#: 否則一旦還原改變了引號或反斜線就會產出不合法的 JSON。
JSON_COLUMNS = ("authors", "categories", "keywords_hit", "raw_extra")


#: 修完不該再出現的殘骸。比 MOJIBAKE_SHAPE 寬，因為多層編碼剝掉外層之後，
#: 內層走的是 cp1252（0x80→€、0x93→"），形狀跟 latin-1 那層不一樣。
MOJIBAKE_RESIDUE = re.compile(
    "[\u0080-\u009f]"                     # C1 控制字元：正常書目文字不會有
    "|\u00e2\u20ac"                       # cp1252 層剝完常見的殘骸
    "|[\u00c2-\u00f4][\u0080-\u00bf]"   # 修完又出現一次原始形狀
)


def looks_mojibake(text: str) -> bool:
    return bool(MOJIBAKE_SHAPE.search(text))


def repair(text: str) -> str | None:
    """還原一段 mojibake；不符合判定或修不乾淨時回 ``None``（代表不要動它）。"""
    if not looks_mojibake(text):
        return None
    fixed = ftfy.fix_encoding(text)
    if fixed == text:
        # ftfy 認為沒東西可修，但形狀判定說有。兩邊不同意時不動它——
        # 這種歧異值得人看一眼，不值得在這裡猜。
        return None
    if MOJIBAKE_RESIDUE.search(fixed):
        # 修完還有殘骸：可能層數更深或是別種損壞。留著，讓它繼續被偵測到，
        # 好過寫回一個「看起來修好了」的半成品。
        return None
    return fixed


def _repair_json_blob(blob: str) -> tuple[str, int]:
    """對 JSON 欄位裡的每個字串各自做還原，回 (新 JSON, 修了幾個字串)。"""
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return blob, 0
    count = 0

    def walk(node):
        nonlocal count
        if isinstance(node, str):
            fixed = repair(node)
            if fixed is not None:
                count += 1
                return fixed
            return node
        if isinstance(node, list):
            return [walk(x) for x in node]
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        return node

    out = walk(data)
    if count == 0:
        return blob, 0
    return json.dumps(out, ensure_ascii=False), count


@dataclass
class Fix:
    source: str
    source_id: str
    changes: dict[str, str]          # column -> 新值
    n_strings: int                   # 這筆總共修了幾個字串
    sample_before: str
    sample_after: str


def scan(db_path: Path) -> list[Fix]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    fixes: list[Fix] = []
    for row in con.execute("SELECT * FROM papers"):
        changes: dict[str, str] = {}
        n = 0
        before = after = ""
        for col in TEXT_COLUMNS:
            val = row[col] or ""
            fixed = repair(val)
            if fixed is not None:
                changes[col] = fixed
                n += 1
                if not before:
                    m = MOJIBAKE_SHAPE.search(val)
                    lo = max(0, m.start() - 40)
                    before = val[lo:m.start() + 24]
                    after = fixed[lo:lo + 60]
        for col in JSON_COLUMNS:
            val = row[col] or ""
            fixed, cnt = _repair_json_blob(val)
            if cnt:
                changes[col] = fixed
                n += cnt
        if changes:
            fixes.append(Fix(row["source"], row["source_id"], changes, n,
                             before, after))
    con.close()
    return fixes


def apply(db_path: Path, fixes: list[Fix]) -> int:
    con = sqlite3.connect(db_path)
    try:
        for fx in fixes:
            cols = ", ".join(f"{c} = ?" for c in fx.changes)
            con.execute(
                f"UPDATE papers SET {cols} WHERE source = ? AND source_id = ?",
                (*fx.changes.values(), fx.source, fx.source_id),
            )
        con.commit()
    finally:
        con.close()
    return len(fixes)


def regenerate(db_path: Path, fixes: list[Fix], out_root: Path) -> tuple[int, list[str]]:
    """對受影響的 paper 重生骨架。

    只重生這些 paper，不是全量重生——全量重生會改動 356 個目前指紋穩定的
    骨架，而分診的等價類判定就是建立在那些指紋上。
    """
    sys.path.insert(0, str(REPO))
    from quant_crawler.strategy_gen.generate import generate_bundle  # noqa: E402

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    ok, errs = 0, []
    for fx in fixes:
        row = con.execute(
            "SELECT * FROM papers WHERE source = ? AND source_id = ?",
            (fx.source, fx.source_id),
        ).fetchone()
        if row is None:
            errs.append(f"{fx.source}:{fx.source_id} 在 DB 裡找不到")
            continue
        paper = dict(row)
        for col in JSON_COLUMNS:
            try:
                paper[col] = json.loads(paper[col] or "null")
            except json.JSONDecodeError:
                pass
        try:
            generate_bundle(paper, out_root=out_root)
            ok += 1
        except Exception as exc:                      # noqa: BLE001
            errs.append(f"{fx.source}:{fx.source_id} -> {exc!r}")
    con.close()
    return ok, errs


def regenerate_unparsable(db_path: Path, out_root: Path) -> tuple[int, list[str]]:
    """重生所有目前無法解析的 manifest，不論它的 DB 列這次有沒有被修到。

    這是修復流程的收口動作，而且判準刻意跟 :func:`regenerate` 不同：那個問
    「這次我修了哪些 paper」，這個問「現在還有哪些 manifest 是壞的」。

    兩者會分岔，而且實際分岔過。一份 manifest 可能在 DB 還髒的時候生成，之後
    DB 被重爬覆蓋成乾淨的——於是 DB 列不在修復清單裡，manifest 卻還壞著。只綁
    前者的話，這 14 份會一直留在原地，而每次執行都回報「已修復」。
    """
    sys.path.insert(0, str(REPO))
    from quant_crawler.strategy_gen.generate import (  # noqa: E402
        generate_bundle,
        paper_slug,
    )
    import yaml                                        # noqa: E402

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    ok, errs = 0, []
    for row in con.execute("SELECT * FROM papers"):
        slug = paper_slug(row["source"], row["source_id"])
        manifest = out_root / slug / "manifest.yaml"
        if not manifest.is_file():
            continue
        try:
            yaml.safe_load(manifest.read_text(encoding="utf-8"))
            continue                                   # 解析得了，不用動
        except yaml.YAMLError:
            pass
        paper = dict(row)
        for col in JSON_COLUMNS:
            try:
                paper[col] = json.loads(paper[col] or "null")
            except json.JSONDecodeError:
                pass
        try:
            generate_bundle(paper, out_root=out_root)
            ok += 1
        except Exception as exc:                       # noqa: BLE001
            errs.append(f"{slug} -> {exc!r}")
    con.close()
    return ok, errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    ap.add_argument("--apply", action="store_true", help="寫回資料庫（預設只印報告）")
    ap.add_argument("--regenerate", action="store_true",
                    help="併重生受影響 paper 的策略骨架（需搭配 --apply）")
    args = ap.parse_args(argv)

    if not args.db.is_file():
        print(f"找不到資料庫：{args.db}", file=sys.stderr)
        return 2

    fixes = scan(args.db)
    if not fixes:
        print("資料庫沒有偵測到 mojibake。")
        if args.regenerate:
            # DB 乾淨不代表 manifest 乾淨——先前生成的那些不會自己好。
            ok, errs = regenerate_unparsable(args.db, args.out_root)
            print(f"重生了 {ok} 份原本無法解析的 manifest。")
            for e in errs:
                print(f"  [ERR] {e}", file=sys.stderr)
            if ok:
                print("請重跑 scripts/triage_generated.py --apply 讓 ledger 反映新狀態。")
        return 0

    by_source: dict[str, int] = {}
    total_strings = 0
    for fx in fixes:
        by_source[fx.source] = by_source.get(fx.source, 0) + 1
        total_strings += fx.n_strings

    print(f"偵測到 {len(fixes)} 筆 paper 含 mojibake，共 {total_strings} 個字串")
    print(f"來源分佈：{by_source}")
    print()
    for fx in fixes[:6]:
        if fx.sample_before:
            print(f"  {fx.source}:{fx.source_id}")
            print(f"    前 …{fx.sample_before}…")
            print(f"    後 …{fx.sample_after}…")
    if len(fixes) > 6:
        print(f"  …另 {len(fixes) - 6} 筆")
    print()

    if not args.apply:
        print("[dry-run] 尚未寫入。確認上面的前後對照無誤後加 --apply。")
        print("判定要同時滿足「形狀對」與「修完沒有殘骸」，兩者缺一都不會動它。")
        return 0

    n = apply(args.db, fixes)
    print(f"已修復 {n} 筆 paper。")

    if args.regenerate:
        ok, errs = regenerate(args.db, fixes, args.out_root)
        print(f"已重生 {ok} 個骨架到 {args.out_root}。")
        for e in errs:
            print(f"  [ERR] {e}", file=sys.stderr)
        # 再掃一次「現在還有哪些 manifest 壞著」——上面那輪只涵蓋這次修到的
        # paper，而壞掉的 manifest 未必對應到一筆這次修到的 DB 列。
        ok2, errs2 = regenerate_unparsable(args.db, args.out_root)
        if ok2 or errs2:
            print(f"另重生了 {ok2} 份原本無法解析的 manifest。")
            for e in errs2:
                print(f"  [ERR] {e}", file=sys.stderr)
        print("重生只涵蓋受影響的 paper——全量重生會改動其他骨架的指紋，"
              "而分診的等價類判定正是建立在那些指紋上。")
        print("重生後請重跑 scripts/triage_generated.py 讓 ledger 反映新狀態。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
