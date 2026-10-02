"""餵給 /stat-tree 面板的即時資料。

為什麼要有 localhost 版
-----------------------
決策樹本身是一份規章，寫成文件就夠了。但「現在的母體 N 是多少」「前沿還剩
幾個沒分診」「線上 FDR 的門檻衰減到哪裡」這些數字**每天都在變**，而規章文件
與任何靜態快照都答不出來——它們只會停在寫下來的那一刻，然後在讀的人不知情
的情況下慢慢變成錯的。

所以這個面板刻意不是把文件抄一份貼上來。它讀三個活的來源：

* ``rulesets/stat-ruleset-*.yaml`` —— 規則集本身（版本、槽位、門檻）
* ``log/trials.jsonl`` —— 母體、分診結果、稽核狀態
* ``experiments/preregistration/`` —— 登記檔數量與驗證狀態

讀不到就明說讀不到，不填零
--------------------------
每一塊都可能不存在（ledger 還沒建、登記目錄是空的）。那些情況一律回
``available: false`` 加一句原因，而不是回 0。把「還沒有」顯示成 0，會讓
一個從未跑過分診的 repo 看起來像一個分診完發現沒東西的 repo——這正是整套
設計要防的錯誤形狀。
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / "log" / "trials.jsonl"
RULESET_DIR = REPO / "strategies" / "_common" / "validation" / "rulesets"
PREREG_DIR = REPO / "experiments" / "preregistration"
GENERATED = REPO / "strategies" / "_generated"


def _unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason}


def _rel(path: Path) -> str:
    """顯示用的 repo 相對路徑；路徑不在 repo 底下時退回絕對路徑。

    直接用 ``Path.relative_to`` 會在路徑落在 repo 外時丟 ValueError。那在正常
    執行時不會發生，但在測試裡把常數指到暫存目錄就會——於是「顯示一個路徑」
    這種零風險的動作把整個面板炸掉。
    """
    try:
        return str(path.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(path)


def _jsonable(value):
    """把 YAML 讀出來的值轉成 JSON 送得出去的東西。

    PyYAML 會把 ``dated: 2026-08-31`` 解析成 ``datetime.date``，而 date 不是
    JSON 可序列化的型別——面板會在瀏覽器端才炸，後端測試卻全綠。
    """
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


# ---------------------------------------------------------------------------
# 規則集
# ---------------------------------------------------------------------------

def ruleset_summary() -> dict:
    import yaml

    candidates = sorted(RULESET_DIR.glob("stat-ruleset-*.yaml"))
    if not candidates:
        return _unavailable(f"{RULESET_DIR} 底下找不到規則集")
    path = candidates[-1]
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return _unavailable(f"規則集不是合法 YAML：{e}")

    return {
        "available": True,
        "version": doc.get("version"),
        "path": _rel(path),
        "derived_from": _jsonable(doc.get("derived_from", {})),
        "n_base_rules": len(doc.get("base") or []),
        "n_se_rules": len(doc.get("se_policy") or []),
        "n_thresholds": len((doc.get("multiplicity") or {}).get("thresholds") or []),
        "n_gates": len(doc.get("gates") or []),
        "base": [
            {
                "id": r.get("id"),
                "parametric": r.get("parametric"),
                "nonparametric": r.get("nonparametric"),
                "absent_because": r.get("nonparametric_absent_because")
                or r.get("parametric_absent_because"),
                "impl_status": r.get("impl_status"),
            }
            for r in (doc.get("base") or [])
        ],
        "se_policy": [
            {"id": r.get("id"), "when": _jsonable(r.get("when")),
             "correction": r.get("correction"), "lag_rule": r.get("lag_rule")}
            for r in (doc.get("se_policy") or [])
        ],
        "thresholds": [
            {"id": r.get("id"), "when": _jsonable(r.get("when")),
             "rule": r.get("rule"), "cite": r.get("cite")}
            for r in ((doc.get("multiplicity") or {}).get("thresholds") or [])
        ],
        "n_accounting": _jsonable((doc.get("multiplicity") or {}).get("n_accounting", {})),
        "gates": [
            {"id": g.get("id"), "min_n_eff": g.get("min_n_eff"),
             "soft_floor": g.get("soft_floor"), "on_fail": g.get("on_fail"),
             "reference_line": _jsonable(g.get("reference_line")),
             "requirement": g.get("requirement")}
            for g in (doc.get("gates") or [])
        ],
    }


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

def _read_ledger() -> list[dict] | None:
    if not LEDGER.is_file():
        return None
    out: list[dict] = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def ledger_summary() -> dict:
    records = _read_ledger()
    if records is None:
        return _unavailable(
            f"{_rel(LEDGER)} 還不存在——尚未跑過 "
            "scripts/triage_generated.py --apply"
        )
    # 同 trial_id 取最後一筆，與 harness 的 collect() 一致。
    latest: dict[str, dict] = {}
    for rec in records:
        tid = rec.get("trial_id")
        if tid:
            latest[tid] = rec
    nodes = list(latest.values())

    dispositions = Counter(str(n.get("disposition") or "（未判定）") for n in nodes)
    n_selection = sum(
        int((n.get("stat_decision") or {}).get("delta_n", 0)) for n in nodes
    )
    no_claim = sum(
        1 for n in nodes
        if (n.get("stat_decision") or {}).get("no_statistical_claim") is True
    )

    return {
        "available": True,
        "path": _rel(LEDGER),
        "n_lines": len(records),
        "n_trials": len(nodes),
        "n_selection": n_selection,
        "n_no_statistical_claim": no_claim,
        "dispositions": dict(dispositions.most_common()),
        "deflation_benchmark": _benchmark(n_selection),
    }


def _benchmark(n: int) -> dict:
    """DSR 的 deflation benchmark：真實 Sharpe = 0 時 N 次試驗的 E[max SR]。

    這條線是面板上最該被看見的數字：它會隨母體上升，而且**套用在所有既有與
    未來的策略上**。把它跟「若把前沿全部當 selection 跑會變成多少」並排，
    「多跑一個候選要付什麼代價」才會從一句話變成一個數字。
    """
    import math
    from statistics import NormalDist

    def emax(k: int) -> float | None:
        if k < 2:
            return None
        gamma = 0.5772156649015329
        nd = NormalDist()
        return ((1 - gamma) * nd.inv_cdf(1 - 1 / k)
                + gamma * nd.inv_cdf(1 - 1 / (k * math.e)))

    frontier = _frontier_size()
    hypothetical = n + frontier if frontier is not None else None
    return {
        "n_selection": n,
        "current": emax(n),
        "if_frontier_all_run": emax(hypothetical) if hypothetical else None,
        "hypothetical_n": hypothetical,
    }


def _frontier_size() -> int | None:
    """_generated 底下還沒有任何 trial 指到的候選數。"""
    if not GENERATED.is_dir():
        return None
    records = _read_ledger() or []
    tried = {r.get("config_ref") for r in records if r.get("config_ref")}
    n = 0
    for man in GENERATED.glob("*/manifest.yaml"):
        rel = _rel(man)
        if rel not in tried:
            n += 1
    return n


# ---------------------------------------------------------------------------
# 稽核
# ---------------------------------------------------------------------------

def audit_summary() -> dict:
    """把 ledger 的 decision_path 餵回 resolver 重算，回報對不上的地方。"""
    records = _read_ledger()
    if records is None:
        return _unavailable("ledger 還不存在")
    sys.path.insert(0, str(REPO))
    try:
        from strategies._common.validation.decision import audit_ledger
    except Exception as e:                                # noqa: BLE001
        return _unavailable(f"載入不了 decision 模組：{e!r}")
    out = audit_ledger(records)
    return {
        "available": True,
        "auditable": out["auditable"],
        "n_records": out["n_records"],
        "n_selection_recomputed": out["n_selection_recomputed"],
        "problems": out["problems"][:20],
        "n_problems": len(out["problems"]),
    }


# ---------------------------------------------------------------------------
# 事前登記
# ---------------------------------------------------------------------------

def preregistration_summary() -> dict:
    if not PREREG_DIR.is_dir():
        return _unavailable(f"{_rel(PREREG_DIR)} 不存在")
    sys.path.insert(0, str(REPO))
    try:
        from scripts.check_preregistration import TEMPLATE_FILENAME, validate
    except Exception as e:                                # noqa: BLE001
        return _unavailable(f"載入不了驗證器：{e!r}")

    entries = []
    for path in sorted(PREREG_DIR.glob("*.yaml")):
        if path.name == TEMPLATE_FILENAME:
            continue
        problems = validate(path)
        entries.append({"name": path.name, "ok": not problems,
                        "problems": problems})
    return {
        "available": True,
        "path": _rel(PREREG_DIR),
        "n": len(entries),
        "n_ok": sum(1 for e in entries if e["ok"]),
        "entries": entries,
        # 空目錄不是錯，但它意味著目前沒有任何 selection trial 指得回一份登記。
        "note": ("目前沒有任何登記檔——依規範 §一 關卡零，此時所有顯著結果都只能"
                 "標「探索性發現」，門檻升到 |t| >= 3。"
                 if not entries else None),
    }


# ---------------------------------------------------------------------------
# 線上 FDR
# ---------------------------------------------------------------------------

def online_fdr_summary() -> dict:
    """把 ledger 上的 selection trial 重播進 ADDIS 預算。

    缺 p 值時**不是**回一個空預算，而是說明缺在哪裡。回空預算會讓面板顯示
    「還有滿滿的搜尋預算」，而真相是「我們根本還沒開始記 p 值」。
    """
    records = _read_ledger()
    if records is None:
        return _unavailable("ledger 還不存在")
    sys.path.insert(0, str(REPO))
    try:
        from strategies._common.validation.online_fdr import (
            PValueProvenanceError,
            budget_from_ledger,
        )
    except Exception as e:                                # noqa: BLE001
        return _unavailable(f"載入不了 online_fdr 模組：{e!r}")
    try:
        budget = budget_from_ledger(records)
    except PValueProvenanceError as e:
        return _unavailable(str(e))
    return {
        "available": True,
        "n_tested": budget.n_tested,
        "n_discarded": budget.n_discarded,
        "n_rejected": budget.n_rejected,
        "next_alpha": budget.next_alpha,
        "alpha_spent": budget.alpha_spent,
        "curve": budget.curve(),
    }


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def payload() -> dict[str, Any]:
    return {
        "ruleset": ruleset_summary(),
        "ledger": ledger_summary(),
        "audit": audit_summary(),
        "preregistration": preregistration_summary(),
        "online_fdr": online_fdr_summary(),
    }
