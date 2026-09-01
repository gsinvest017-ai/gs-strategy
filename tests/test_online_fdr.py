"""ADDIS 線上 FDR 預算的測試。

最重要的一組是「與 ``online-fdr`` 套件逐步比對」。自寫演算法的風險不是寫不
出來，是**寫錯了但看起來很合理**——alpha_t 是一個沒有直覺可以檢查的數字，
差一個索引、少減一項 candidate 計數，輸出依然單調遞減、依然落在合理區間。
所以正確性不能靠讀程式碼確認，要靠跟一份獨立實作對數字。

套件裝不到時那組會 skip；其餘的測試釘住的是規範層面的性質（拒絕匿名 p 值、
不跳過缺 p 值的 trial、discard 不花預算）。
"""
from __future__ import annotations

import random

import pytest

from strategies._common.validation.online_fdr import (
    AddisBudget,
    PValueProvenanceError,
    budget_from_ledger,
)

SRC = "PSR 單尾 p（Bailey & López de Prado 2014），pre-reg #001 §3 凍結"


# ---------------------------------------------------------------------------
# 一、與獨立實作交叉驗證
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 7, 42, 1234])
def test_matches_online_fdr_package_step_by_step(seed):
    """逐步比對 alpha_t 與拒絕決策；任何一步不同就失敗。

    只比對最終的拒絕總數是不夠的：兩份實作可以在中途分岔又碰巧收斂到同一個
    計數。要抓到差一個索引這種錯誤，必須每一步都對。
    """
    pkg = pytest.importorskip(
        "online_fdr.investing.addis.addis",
        reason="online-fdr 未安裝；交叉驗證跳過（pip install online-fdr）",
    )
    rng = random.Random(seed)
    # 混一批明顯的 null（大 p）與少數真訊號（小 p），才會同時走到
    # discard、candidate、reject 三條路徑。
    p_values = [
        rng.uniform(0.6, 1.0) if rng.random() < 0.6 else rng.uniform(0.0, 0.06)
        for _ in range(120)
    ]

    alpha, w0, lam, tau = 0.05, 0.025, 0.25, 0.5
    mine = AddisBudget(alpha=alpha, wealth=w0, lambda_=lam, tau=tau)
    theirs = pkg.Addis(alpha=alpha, wealth=w0, lambda_=lam, tau=tau)

    for i, p in enumerate(p_values):
        step = mine.test_one(p, p_value_source=SRC)
        their_reject = theirs.test_one(p)
        assert step.rejected == their_reject, f"第 {i} 步拒絕決策不同 (p={p:.5f})"
        if not step.discarded:
            assert step.alpha_t == pytest.approx(theirs.alpha, rel=1e-12), (
                f"第 {i} 步 alpha_t 不同：自寫 {step.alpha_t!r} vs 套件 {theirs.alpha!r}"
            )

    assert mine.n_rejected == len(theirs.reject_idx)


# ---------------------------------------------------------------------------
# 二、p 值來源必須寫明
# ---------------------------------------------------------------------------

def test_refuses_anonymous_p_value():
    """不同定義的 p 值不可互換，所以來源是必填。"""
    b = AddisBudget()
    with pytest.raises(PValueProvenanceError) as e:
        b.test_one(0.01, p_value_source="")
    assert "pre-registration" in str(e.value)


def test_p_value_source_is_keyword_only():
    """故意設成 keyword-only 且無預設值，讓「忘了寫」在呼叫端就是 TypeError。"""
    b = AddisBudget()
    with pytest.raises(TypeError):
        b.test_one(0.01, SRC)          # type: ignore[misc]


def test_rejects_out_of_range_p():
    b = AddisBudget()
    for bad in (-0.01, 1.5):
        with pytest.raises(ValueError):
            b.test_one(bad, p_value_source=SRC)


# ---------------------------------------------------------------------------
# 三、ADDIS 的行為性質
# ---------------------------------------------------------------------------

def test_discarded_tests_cost_nothing():
    """p > tau 的明顯 null 被丟掉、不花預算——這正是 ADDIS 比 Bonferroni 強的地方。"""
    b = AddisBudget(tau=0.5)
    before = b.next_alpha
    for _ in range(50):
        step = b.test_one(0.9, p_value_source=SRC)
        assert step.discarded and step.spent == 0.0
    assert b.n_tested == 0
    assert b.n_discarded == 50
    assert b.next_alpha == pytest.approx(before), "被 discard 的檢定不該改變下一次的門檻"


def test_threshold_decays_when_fed_only_useless_variants():
    """連續投入無效（但不到被 discard 的）變體，門檻要單調衰減。

    這就是「你還剩幾次機會」那條曲線。不衰減的話，這整個模組沒有存在意義。
    """
    b = AddisBudget()
    first = b.next_alpha
    for _ in range(40):
        b.test_one(0.45, p_value_source=SRC)      # 沒被 discard，但也拒絕不了
    assert b.next_alpha < first
    curve = b.curve()
    assert len(curve) == 40
    assert curve[-1][1] < curve[0][1]


def test_exhausted_requires_an_explicit_floor():
    """floor 沒有預設值：多小的 p 值還當真，是判斷不是常數。"""
    b = AddisBudget()
    for _ in range(60):
        b.test_one(0.45, p_value_source=SRC)
    assert b.exhausted(floor=1.0) is True
    assert b.exhausted(floor=1e-12) is False
    with pytest.raises(ValueError):
        b.exhausted(floor=0.0)


def test_initial_wealth_must_be_below_alpha():
    """論文條件 w0 < alpha；違反時直接拒絕，不要靜默夾住。"""
    with pytest.raises(ValueError):
        AddisBudget(alpha=0.05, wealth=0.05)
    with pytest.raises(ValueError):
        AddisBudget(lambda_=0.6, tau=0.5)          # 必須 lambda <= tau


# ---------------------------------------------------------------------------
# 四、與 trial ledger 的接線
# ---------------------------------------------------------------------------

def _rec(tid, started, *, delta_n=1, p=None, src=SRC):
    block = {"delta_n": delta_n, "purpose": "selection" if delta_n else "screening"}
    if p is not None:
        block["p_value"] = p
        block["p_value_source"] = src
    return {"trial_id": tid, "started_at": started, "stat_decision": block}


def test_ledger_replay_uses_only_selection_trials():
    """screening / diagnostic 依定義不進母體，餵進來會憑空稀釋預算。"""
    records = [
        _rec("t-1", "2026-01-01T00:00:00Z", p=0.30),
        _rec("t-screen", "2026-01-02T00:00:00Z", delta_n=0),
        _rec("t-2", "2026-01-03T00:00:00Z", p=0.02),
    ]
    b = budget_from_ledger(records)
    assert len(b.history) == 2
    assert [s.label for s in b.history] == ["t-1", "t-2"]


def test_ledger_replay_is_in_time_order_not_file_order():
    """線上程序的結論取決於順序，所以要照 started_at 排，不能照檔案順序。"""
    records = [
        _rec("t-late", "2026-03-01T00:00:00Z", p=0.01),
        _rec("t-early", "2026-01-01T00:00:00Z", p=0.40),
    ]
    b = budget_from_ledger(records)
    assert [s.label for s in b.history] == ["t-early", "t-late"]


def test_ledger_replay_refuses_to_skip_a_selection_trial_missing_its_p_value():
    """跳過等於默默把母體縮小——而母體縮小正是整套設計要防的事。"""
    records = [
        _rec("t-1", "2026-01-01T00:00:00Z", p=0.02),
        _rec("t-nop", "2026-01-02T00:00:00Z"),          # 沒有 p_value
    ]
    with pytest.raises(PValueProvenanceError) as e:
        budget_from_ledger(records)
    assert "t-nop" in str(e.value)


def test_ledger_replay_refuses_p_value_without_source():
    records = [_rec("t-1", "2026-01-01T00:00:00Z", p=0.02, src="")]
    with pytest.raises(PValueProvenanceError):
        budget_from_ledger(records)


def test_empty_ledger_gives_a_fresh_budget():
    b = budget_from_ledger([])
    assert b.n_tested == 0
    assert b.next_alpha > 0
