#!/usr/bin/env python3
"""驗證事前登記檔完整、而且它宣告的檢定計畫真的解析得出一份處方。

只檢查「填了沒」是不夠的。這個驗證器真正要擋的是**看起來完整、但推導不出檢定
的登記檔**——那種檔案給人一種已經事前登記過的錯覺，實際上等到跑完資料才會發現
還有選擇空間，而那時候再選就不是事前了。

所以它把 ``stat_plan`` 直接餵進 :func:`validation.decision.resolve`：解析得出
處方才算數。解析不出來（例如 overlap=overlapping 卻沒填 holding_periods），
就是這份登記還沒把檢定綁死。

另外兩項刻意不放行：

* ``falsification`` 為空。沒有事先寫下「什麼結果出現就放棄」，就擋不住
  「結果不如預期就不斷追加變體直到挖出顯著為止」。
* ``family: open_mining`` 卻沒有 ``p_value_definition``。連續挖掘要走線上 FDR，
  而不同定義的 p 值不可互換，混著投進同一個預算會讓 FDR 控制失效。

用法
----
    python scripts/check_preregistration.py                 # 驗全部
    python scripts/check_preregistration.py 001-foo.yaml    # 驗指定幾份
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
PREREG_DIR = REPO / "experiments" / "preregistration"
#: 範本本身欄位是空的，不是一份未通過的登記檔。用檔名比對而不是內容裡的 `id`，
#: 因為一份真的登記檔可以（也應該）被要求 id 與檔名一致，範本則刻意不一致。
TEMPLATE_FILENAME = "TEMPLATE.yaml"

REQUIRED_TEXT = (
    "id", "title", "author", "registered_at",
    "hypothesis", "economic_mechanism",
)


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def validate(path: Path) -> list[str]:
    problems: list[str] = []

    def bad(msg: str) -> None:
        problems.append(msg)

    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return [f"不是合法 YAML：{e}"]

    if doc.get("schema") != "preregistration/1":
        bad("schema 必須是 preregistration/1")

    for field in REQUIRED_TEXT:
        if _blank(doc.get(field)):
            bad(f"`{field}` 是空的")

    if doc.get("id") != path.stem:
        bad(f"`id`（{doc.get('id')!r}）與檔名（{path.stem!r}）不一致")

    if not doc.get("falsification"):
        bad("`falsification` 是空的——沒有事先寫下什麼結果就放棄，"
            "就擋不住結果不如預期時不斷追加變體")

    sample = doc.get("sample") or {}
    if sample.get("contains_full_bear_market") is None:
        bad("`sample.contains_full_bear_market` 未填。規範 §五 要求樣本期至少含"
            "一次完整空頭，否則判決要降級為「繼續累積」——未填不等於符合")

    plan = doc.get("stat_plan") or {}
    family = plan.get("family")
    if family == "open_mining" and _blank(doc.get("p_value_definition")):
        bad("`family: open_mining` 必須填 `p_value_definition`：連續挖掘要走線上 "
            "FDR，而不同定義的 p 值不可互換，混著投進同一個預算會讓 FDR 控制失效")

    fdr = doc.get("online_fdr") or {}
    if fdr.get("enabled") and fdr.get("exhausted_floor") is None:
        bad("`online_fdr.enabled` 為真時必須填 `exhausted_floor`："
            "「多小的 p 值還當真」是判斷不是統計常數，沒有預設值可套")

    # --- 關鍵：這份計畫推導得出一份檢定處方嗎 ---------------------------
    sys.path.insert(0, str(REPO))
    from strategies._common.validation.decision import (  # noqa: E402
        DecisionError,
        Facts,
        resolve,
    )

    known = set(Facts.__dataclass_fields__)
    facts_kw = {k: v for k, v in plan.items() if k in known and v is not None}
    missing_for_resolve = {"estimand", "design", "overlap", "family", "purpose"} - set(facts_kw)
    if missing_for_resolve:
        bad(f"`stat_plan` 缺 {sorted(missing_for_resolve)}，推導不出檢定處方")
    else:
        # n_eff 在登記時通常還不知道（樣本要跑過才算得出有效獨立觀測數），
        # 所以這裡塞一個佔位值只為了讓其餘槽位解析得動。閘門是否過關要等
        # 真正的 n_eff 出來才判——這裡驗的是「檢定選定了沒」。
        facts_kw.setdefault("n_eff", 1)
        facts_kw.setdefault("autocorr", "unknown")
        try:
            resolve(Facts(**facts_kw))
        except DecisionError as e:
            bad(f"`stat_plan` 推導不出檢定處方：{e}")
        except TypeError as e:
            bad(f"`stat_plan` 欄位有誤：{e}")

    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="*", type=Path,
                    help="要驗的登記檔（預設驗 experiments/preregistration/ 全部）")
    args = ap.parse_args(argv)

    if args.files:
        paths = [p if p.is_absolute() else PREREG_DIR / p for p in args.files]
    else:
        paths = sorted(PREREG_DIR.glob("*.yaml"))

    paths = [p for p in paths if p.name != TEMPLATE_FILENAME]
    if not paths:
        print("沒有登記檔可驗（TEMPLATE.yaml 不算）。")
        return 0

    failed = 0
    for path in paths:
        problems = validate(path)
        if problems:
            failed += 1
            print(f"✗ {path.name}", file=sys.stderr)
            for p in problems:
                print(f"    {p}", file=sys.stderr)
        else:
            print(f"✓ {path.name}")
    if failed:
        print(f"\n{failed}/{len(paths)} 份登記檔未通過。", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
