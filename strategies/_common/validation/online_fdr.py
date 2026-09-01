"""ADDIS：把「還能再搜幾次」變成一個看得見的數字。

要解決的問題
------------
Bonferroni、Harvey-Liu-Zhu 這些修正都假設**試驗數事先已知**。auto-research
loop 不是那樣：變體是一個一個冒出來的，你不知道會有幾個，而且下一個要不要做
往往取決於上一個的結果。離線的一次性校正在這個情境下不成立——事後回頭用最終
的 N 去修正，等於用未來的資訊決定過去的門檻。

線上多重檢定就是為這個情境設計的。ADDIS（Tian & Ramdas, NeurIPS 2019）在
「多數 trial 明顯無效」時 power 最高，而那正是策略搜尋的實況：你會丟掉絕大
多數變體。它的 discard 機制把明顯的 null（p 大於 tau）直接丟掉、不花預算，
所以測一堆爛變體的代價遠低於 Bonferroni。

為什麼自己寫而不是裝套件
------------------------
``online-fdr``（BSD-3）有一份品質不錯的 ADDIS 實作。但本子套件的既定不變式是
「只依賴 numpy/scipy/pandas，以便日後整份搬進 ``gs_common.quant.validation``」
（見 ``__init__.py``），而 ``reality_check.py`` / ``pbo.py`` 也都是自寫的。
再加一個執行期依賴會破壞那個不變式。

所以走的是：**演算法自寫，正確性靠交叉驗證。**
``tests/test_online_fdr.py`` 會在 ``online-fdr`` 裝得到時，拿隨機 p 值序列
逐步比對兩邊的 alpha_t 與拒絕決策；裝不到就 skip。這比「相信自己抄對了」強，
也比多背一個依賴便宜。

「預算耗盡」在 ADDIS 裡是什麼意思
---------------------------------
ADDIS 不像 alpha-investing 那樣有一個字面上的財富帳戶。它每次檢定算出一個
``alpha_t``——這次檢定能用的顯著水準。連續投入無效變體會讓 ``alpha_t`` 單調
衰減；衰減到某個地步，你需要 p < 1e-4 才拒絕得了，那時再搜下去就沒有意義。

所以本模組把「預算耗盡」定義成 ``alpha_t < floor``，而且 **floor 由呼叫端
明講**，不給一個看起來權威的預設值。那是一個關於「多小的 p 值你還當真」的
判斷，不是一個統計常數。

p 值從哪裡來——這一段必須寫進 pre-registration
----------------------------------------------
**把 anytime-valid / online FDR 直接套在 Sharpe ratio 或策略搜尋上的論文，
查無。** 這是自己接線，不是照抄。所以本模組**拒絕**在沒有 ``p_value_source``
的情況下接受 p 值：你必須寫下這個 p 值是怎麼算出來的（PSR 的單尾 p？
block bootstrap 的經驗 p？成本後 spread 的 Newey-West t 對應的 p？），
而且那個定義要在 pre-registration 裡凍結。

不同定義給出的 p 值不可互換。一串混了三種定義的 p 值餵進 ADDIS，得到的
FDR 控制沒有任何意義——而且從輸出上完全看不出來。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

__all__ = [
    "AddisBudget",
    "AddisStep",
    "SEQUENCE_C",
    "SEQUENCE_EXPONENT",
    "budget_from_ledger",
    "PValueProvenanceError",
]

#: SAFFRON / ADDIS 論文提出的預設 gamma 序列：``gamma_j = c / j^1.6``。
#: c 取到這麼多位數不是精度需求，是為了讓 sum_j gamma_j = 1（它是
#: zeta(1.6) 的倒數）。改動這兩個常數等於換一個演算法，不是調參數。
SEQUENCE_EXPONENT = 1.6
SEQUENCE_C = 0.4374901658


def _gamma(j: int) -> float:
    """gamma 序列。j <= 0 時回 0——序列只定義在正整數上。

    回 0 而不是丟例外，是因為 ADDIS 的 alpha_t 公式會用
    ``num_test - reject_idx - candidates`` 這種可能為 0 或負的索引去查它，
    那些項本來就該不貢獻。
    """
    if j <= 0:
        return 0.0
    return SEQUENCE_C / (j ** SEQUENCE_EXPONENT)


class PValueProvenanceError(ValueError):
    """沒有寫明 p 值怎麼來的就想投進預算——拒絕。

    這不是龜毛。ADDIS 控制的是「這一串 p 值」的 FDR，而不同定義算出來的
    p 值不可互換；混著餵進去會得到一個看起來正常、實際上什麼都不保證的
    數字，而且從輸出上看不出來。
    """


@dataclass(frozen=True)
class AddisStep:
    """一次投入的結果。"""

    index: int              # 第幾次「沒有被 discard」的檢定（discard 的不編號）
    p_value: float
    alpha_t: float          # 這次檢定拿到的顯著水準；discard 時為 0
    discarded: bool         # p > tau，明顯的 null，不花預算
    candidate: bool         # p/tau <= lambda，有機會拒絕
    rejected: bool
    label: str = ""

    @property
    def spent(self) -> float:
        return 0.0 if self.discarded else self.alpha_t


@dataclass
class AddisBudget:
    """ADDIS 的線上 FDR 預算。

    參數沿用 Tian & Ramdas (2019) 的記號：

    ``alpha``   目標 FDR 水準。
    ``wealth``  初始預算 w0，必須嚴格小於 alpha（論文的條件）。
    ``lambda_`` candidate 門檻：p/tau <= lambda 才算「有機會」。
    ``tau``     discard 門檻：p > tau 直接丟掉、不花預算。

    預設值取論文建議的 lambda = tau/2、tau = 0.5、w0 = alpha/2。
    """

    alpha: float = 0.05
    wealth: float = 0.025
    lambda_: float = 0.25
    tau: float = 0.5
    history: list[AddisStep] = field(default_factory=list)

    _num_test: int = 0
    _candidates: list[bool] = field(default_factory=list)
    _reject_idx: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 < self.alpha < 1:
            raise ValueError(f"alpha 必須在 (0,1)：{self.alpha}")
        if not 0 < self.wealth < self.alpha:
            raise ValueError(
                f"初始預算 w0 必須嚴格小於 alpha（論文條件）：w0={self.wealth} "
                f"alpha={self.alpha}"
            )
        if not 0 < self.lambda_ < 1:
            raise ValueError(f"lambda 必須在 (0,1)：{self.lambda_}")
        if not self.lambda_ <= self.tau < 1:
            raise ValueError(f"必須 lambda <= tau < 1：lambda={self.lambda_} tau={self.tau}")

    # -- 核心 -------------------------------------------------------------

    def _alpha_t(self, num_test: int) -> float:
        """第 ``num_test`` 次檢定的顯著水準。逐項對應論文第 3 節的 alpha_t 公式。

        ``num_test`` 是**含這一次在內**的計數（1-based），刻意當參數傳而不是
        讀 ``self._num_test``：``next_alpha`` 要問的是「下一次會拿到多少」，
        若共用同一個內部計數器就得先遞增再還原，那種寫法差一步就是差一整個
        序列項，而 alpha_t 是個沒有直覺可以檢查的數字，錯了看不出來。
        """
        n_cand = sum(self._candidates)
        alpha_t = self.wealth * _gamma(num_test - n_cand)

        if self._reject_idx:
            tau_1 = self._reject_idx[0]
            c_1_plus = sum(self._candidates[tau_1:])
            alpha_t += (self.alpha - self.wealth) * _gamma(num_test - tau_1 - c_1_plus)
        if len(self._reject_idx) >= 2:
            alpha_t += self.alpha * sum(
                _gamma(num_test - idx - sum(self._candidates[idx:]))
                for idx in self._reject_idx[1:]
            )
        alpha_t *= self.tau - self.lambda_
        return min(self.tau * self.lambda_, alpha_t)

    def test_one(self, p_value: float, *, p_value_source: str,
                 label: str = "") -> AddisStep:
        """投入一個 p 值，拿回這次的門檻與拒絕與否。

        ``p_value_source`` 是必填的關鍵字參數，故意不給預設值——見模組
        docstring。它不參與計算，只是強迫呼叫端把「這個 p 值是怎麼算的」
        寫下來，並讓它一路留在 ``AddisStep`` 的稽核軌跡裡。
        """
        if not p_value_source or not p_value_source.strip():
            raise PValueProvenanceError(
                "必須寫明 p_value_source：這個 p 值是 PSR 的單尾 p？block "
                "bootstrap 的經驗 p？成本後 spread 的 Newey-West t 對應的 p？"
                "不同定義的 p 值不可互換，混著投進同一個預算，FDR 控制就失效了，"
                "而且從輸出上看不出來。這個定義要在 pre-registration 裡凍結。"
            )
        if not 0.0 <= p_value <= 1.0:
            raise ValueError(f"p 值必須在 [0,1]：{p_value}")

        if p_value > self.tau:
            step = AddisStep(index=self._num_test, p_value=p_value, alpha_t=0.0,
                             discarded=True, candidate=False, rejected=False,
                             label=label)
            self.history.append(step)
            return step

        self._num_test += 1
        alpha_t = self._alpha_t(self._num_test)

        scaled = p_value / self.tau
        is_candidate = scaled <= self.lambda_
        self._candidates.append(is_candidate)

        rejected = scaled <= alpha_t
        if rejected:
            self._reject_idx.append(self._num_test)

        step = AddisStep(index=self._num_test, p_value=p_value, alpha_t=alpha_t,
                         discarded=False, candidate=is_candidate,
                         rejected=rejected, label=label)
        self.history.append(step)
        return step

    # -- 報告 -------------------------------------------------------------

    @property
    def n_tested(self) -> int:
        """實際花掉預算的次數（不含被 discard 的）。"""
        return self._num_test

    @property
    def n_discarded(self) -> int:
        return sum(1 for s in self.history if s.discarded)

    @property
    def n_rejected(self) -> int:
        return len(self._reject_idx)

    @property
    def alpha_spent(self) -> float:
        return sum(s.spent for s in self.history)

    @property
    def next_alpha(self) -> float:
        """下一次檢定（若不被 discard）會拿到的門檻。

        這是儀表板上該畫的那條線：它隨著無效變體的累積單調衰減，把
        「你還剩幾次機會」變成一個看得見的數字。
        """
        return self._alpha_t(self._num_test + 1)

    def exhausted(self, floor: float) -> bool:
        """下一次的門檻是否已低於 ``floor``。

        ``floor`` 沒有預設值，因為它不是統計常數而是一個判斷：多小的 p 值
        你還當真？以本專案的有效事件數（約 10–15 個獨立崩盤），能穩定量到
        1e-3 以下的 p 值本身就可疑，1e-4 更是。給一個看起來權威的預設值，
        只會讓這個判斷被略過。
        """
        if floor <= 0:
            raise ValueError("floor 必須為正——否則預算永遠不會耗盡")
        return self.next_alpha < floor

    def curve(self) -> list[tuple[int, float]]:
        """(第幾次檢定, 該次 alpha_t)，供畫消耗曲線用；discard 的不計入。"""
        return [(s.index, s.alpha_t) for s in self.history if not s.discarded]


# --------------------------------------------------------------------------
# 與 trial ledger 的接線
# --------------------------------------------------------------------------

def budget_from_ledger(
    records: Sequence[Mapping],
    *,
    alpha: float = 0.05,
    lambda_: float = 0.25,
    tau: float = 0.5,
) -> AddisBudget:
    """把 ledger 上的 selection trial 依時序重播進一個 ADDIS 預算。

    只吃 ``purpose == "selection"``（``delta_n == 1``）的記錄：screening 與
    diagnostic 依定義不進入母體，把它們餵進來會憑空稀釋預算。

    **缺 p 值的 selection trial 會讓這個函式丟例外，不是被跳過。** 跳過等於
    默默把母體縮小，而母體縮小正是這整套東西要防的事——一個沒記 p 值的
    trial 仍然是一次嘗試。要嘛補上它的 p 值與來源，要嘛就得承認這份 ledger
    還不能用來做線上 FDR。
    """
    budget = AddisBudget(alpha=alpha, wealth=alpha / 2, lambda_=lambda_, tau=tau)
    selection: list[tuple[str, Mapping]] = []
    for rec in records:
        block = rec.get("stat_decision")
        if not isinstance(block, Mapping):
            continue
        if int(block.get("delta_n", 0)) != 1:
            continue
        selection.append((str(rec.get("started_at") or ""), rec))

    selection.sort(key=lambda kv: kv[0])

    missing: list[str] = []
    for _, rec in selection:
        block = rec["stat_decision"]
        p = block.get("p_value")
        src = block.get("p_value_source")
        if p is None or not src:
            missing.append(str(rec.get("trial_id", "?")))
            continue
        budget.test_one(float(p), p_value_source=str(src),
                        label=str(rec.get("trial_id", "")))
    if missing:
        raise PValueProvenanceError(
            f"{len(missing)} 筆 selection trial 缺 p_value 或 p_value_source："
            f"{', '.join(missing[:8])}{' …' if len(missing) > 8 else ''}。"
            "不跳過它們，是因為跳過等於默默把母體縮小——一個沒記 p 值的 trial "
            "仍然是一次嘗試。請補上，或承認這份 ledger 還不能做線上 FDR。"
        )
    return budget
