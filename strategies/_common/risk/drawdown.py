"""Drawdown geometry, drawdown-based ratios, and MDD-constrained leverage.

Three questions live in this module, and they are the same question asked at
three different levels of commitment:

1. *Descriptive* — how deep, how long, how often (Part A).
2. *Comparative* — Calmar / Sterling / Sortino / Martin (Part B). These are the
   "risk-reward ratios" everyone quotes and almost nobody defines. Every one of
   them is ambiguous in the literature, so every function here takes an explicit
   convention argument and ``ratio_report`` returns a ``conventions`` sub-dict
   recording which one produced each number. **Two ratios from two sources are
   not comparable unless the convention is stated.**
3. *Prescriptive* — given a drawdown budget, how much leverage may I run
   (Parts C and D)?

The single fact from Part C that should change how a trader thinks:

    With **no edge** (mu = 0) the expected maximum drawdown grows like
    ``sqrt(T)`` — it is unbounded, and waiting longer guarantees a worse
    drawdown. With a **positive edge** (mu > 0) it grows only like ``log(T)``.
    An edge does not merely add return; it changes the *growth law* of the
    worst drawdown from a power of time to a logarithm of time.

    (Magdon-Ismail & Atiya 2004, "On the Maximum Drawdown of a Brownian
    Motion", Journal of Applied Probability 41(1).)

And the fact from Part D item 15: the growth cost of mis-estimating leverage
scales with ``L^2``, so the model complexity you can afford falls like
``1/L^2``. That is the quantitative content of "the more leverage you run, the
simpler your strategy has to be".

Design rule (mirrors ``strategies/_common/validation``): numpy / scipy / pandas
only, no zipline, no strategy imports — this subpackage is lift-ready into
``gs_common.quant.risk``.

Conventions used throughout
---------------------------
* A drawdown ``d_t = 1 - W_t / max_{s<=t} W_s`` is a **positive fraction** in
  ``[0, 1)``. Depths are reported positive; ``max_drawdown`` returns ``+0.25``
  for a 25% drawdown, not ``-0.25``.
* Parts C and D work in **log wealth**, where drawdowns are additive and the
  Brownian results apply. A log drawdown ``x`` corresponds to a fractional
  drawdown ``1 - exp(-x)``; the two agree to first order for small drawdowns
  and diverge for large ones. The conversion is done explicitly where needed.
* "days" in column names of ``drawdown_table`` means **bars**, whatever the bar
  frequency is. There is no calendar arithmetic anywhere in this module.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

try:
    from scipy.optimize import brentq  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "scipy is required for risk.drawdown: pip install scipy"
    ) from exc


__all__ = [
    # Part A - geometry
    "drawdown_series",
    "max_drawdown",
    "drawdown_table",
    "ulcer_index",
    "martin_ratio",
    "time_under_water",
    # Part B - ratios
    "cagr",
    "equity_from_returns",
    "calmar_ratio",
    "sterling_ratio",
    "sortino_ratio",
    "ratio_report",
    # Part C - expected maximum drawdown
    "expected_max_drawdown",
    "mdd_scaling_check",
    # Part D - MDD-constrained leverage
    "merton_fraction",
    "grossman_zhou_leverage",
    "kelly_leverage_with_dd_cap",
    "complexity_budget",
]


# --------------------------------------------------------------------------
# internal helpers
# --------------------------------------------------------------------------
def _as_1d(x: Sequence[float] | np.ndarray | pd.Series, name: str) -> np.ndarray:
    a = np.asarray(x, dtype=float).ravel()
    if a.size == 0:
        raise ValueError(f"{name} is empty")
    return a


def _equity_array(equity: Sequence[float] | np.ndarray | pd.Series) -> np.ndarray:
    w = _as_1d(equity, "equity")
    if np.any(np.isnan(w)):
        raise ValueError("equity contains NaN; forward-fill or drop before use")
    if np.any(w <= 0.0):
        # A non-positive wealth makes 1 - W/M meaningless (and >= 1), so refuse
        # rather than silently returning a drawdown outside [0, 1).
        raise ValueError("equity must be strictly positive")
    return w


def _clean_returns(returns: Sequence[float] | np.ndarray | pd.Series) -> np.ndarray:
    r = _as_1d(returns, "returns")
    r = r[~np.isnan(r)]
    if r.size < 2:
        raise ValueError("need at least 2 non-NaN return observations")
    return r


# --------------------------------------------------------------------------
# Part A - drawdown geometry
# --------------------------------------------------------------------------
def drawdown_series(
    equity: Sequence[float] | np.ndarray | pd.Series,
) -> np.ndarray | pd.Series:
    """Fractional drawdown at every bar.

    Computes ``d_t = 1 - W_t / max_{s <= t} W_s``, a value in ``[0, 1)``.

    Strictly causal by construction: the running maximum is taken over
    ``s <= t`` only (``np.maximum.accumulate``), so ``d_t`` never sees a future
    bar. Truncating the input at any point leaves the surviving values
    unchanged — see ``test_no_lookahead_drawdown_series``.

    Reference: standard definition; see e.g. Magdon-Ismail & Atiya (2004) for
    the continuous-time analogue, and Grossman & Zhou (1993) who write the same
    quantity as the ratio of wealth to its running maximum.

    Returns a ``pd.Series`` (same index) if ``equity`` is a ``pd.Series``,
    otherwise a ``np.ndarray``.
    """
    w = _equity_array(equity)
    running_max = np.maximum.accumulate(w)
    d = 1.0 - w / running_max
    if isinstance(equity, pd.Series):
        return pd.Series(d, index=equity.index, name="drawdown")
    return d


def max_drawdown(equity: Sequence[float] | np.ndarray | pd.Series) -> float:
    """Maximum drawdown as a **positive** fraction, ``max_t d_t``.

    A 25% peak-to-trough loss returns ``0.25``, not ``-0.25``. Sign conventions
    for MDD differ across libraries; this one is stated so that the ratios below
    can divide by it without an absolute value scattered everywhere.
    """
    d = drawdown_series(equity)
    return float(np.asarray(d, dtype=float).max())


def drawdown_table(
    equity: Sequence[float] | np.ndarray | pd.Series,
    top_n: int = 5,
) -> pd.DataFrame:
    """The ``top_n`` deepest drawdown episodes, one row each.

    An *episode* runs from the peak bar (the last bar at which ``d_t == 0``)
    through every consecutive bar with ``d_t > 0``, and ends at the first bar
    where ``d_t`` returns to 0 (full recovery to the old high-water mark).

    Columns
    -------
    peak_date        index label of the high-water-mark bar that started it
    trough_date      index label of the deepest bar in the episode
    recovery_date    index label of the first bar back at the old high;
                     ``pd.NaT`` if the episode had not recovered by the end of
                     the sample
    depth            max ``d_t`` within the episode, positive fraction
    drawdown_days    bars from peak to trough (``trough_i - peak_i``)
    recovery_days    bars from trough to recovery; ``NaN`` if never recovered

    "days" means **bars**; no calendar arithmetic is performed. If ``equity`` is
    a plain array the index labels are integer positions, and ``recovery_date``
    is then an object column mixing ints with ``pd.NaT`` — test it with
    ``pd.isna``, not with a dtype check.

    Rows are sorted by ``depth`` descending. Note this is not the same ordering
    as "longest" or "most painful"; a shallow multi-year drawdown can hurt more
    than a deep two-day one, which is what ``ulcer_index`` and
    ``time_under_water`` are for.
    """
    if top_n < 1:
        raise ValueError("top_n must be >= 1")
    w = _equity_array(equity)
    index = equity.index if isinstance(equity, pd.Series) else pd.RangeIndex(w.size)
    d = 1.0 - w / np.maximum.accumulate(w)
    n = d.size
    under = d > 0.0

    rows: list[dict[str, Any]] = []
    i = 0
    while i < n:
        if not under[i]:
            i += 1
            continue
        start = i                       # first bar strictly below the old high
        j = i
        while j < n and under[j]:
            j += 1
        # d[0] is 0 by construction, so a drawdown always has a peak bar before
        # it and `start - 1` can never be negative.
        peak_i = start - 1
        trough_i = start + int(np.argmax(d[start:j]))
        recovered = j < n
        rows.append(
            {
                "peak_date": index[peak_i],
                "trough_date": index[trough_i],
                "recovery_date": index[j] if recovered else pd.NaT,
                "depth": float(d[trough_i]),
                "drawdown_days": int(trough_i - peak_i),
                "recovery_days": float(j - trough_i) if recovered else float("nan"),
            }
        )
        i = j

    cols = [
        "peak_date",
        "trough_date",
        "recovery_date",
        "depth",
        "drawdown_days",
        "recovery_days",
    ]
    if not rows:
        return pd.DataFrame(columns=cols)
    table = pd.DataFrame(rows, columns=cols)
    table = table.sort_values("depth", ascending=False, kind="mergesort")
    return table.head(top_n).reset_index(drop=True)


def ulcer_index(equity: Sequence[float] | np.ndarray | pd.Series) -> float:
    """Ulcer Index: ``sqrt(mean(d_t^2))`` over the whole sample.

    Reference: Martin & McCann (1989), *The Investor's Guide to Fidelity
    Funds*. Unlike max drawdown it is a quadratic penalty on *every* bar spent
    below the high-water mark, so it punishes long shallow misery as well as
    short deep shocks.

    Convention: returned as a **fraction** (0.05 = 5%). The original
    publication works in percentage points, so an Ulcer Index quoted elsewhere
    may be 100x this value. Stated because the two are silently interchangeable
    in appearance and not in magnitude.
    """
    d = np.asarray(drawdown_series(equity), dtype=float)
    return float(np.sqrt(np.mean(d**2)))


def martin_ratio(
    returns: Sequence[float] | np.ndarray | pd.Series,
    equity: Sequence[float] | np.ndarray | pd.Series,
    periods_per_year: int = 252,
    rf: float = 0.0,
) -> float:
    """Martin (Ulcer Performance) ratio: annualised excess return / Ulcer Index.

    Formula: ``(CAGR(returns) - rf) / ulcer_index(equity)``.

    Reference: Martin & McCann (1989). ``rf`` is an **annualised** risk-free
    rate expressed as a simple fraction, subtracted from the annualised
    geometric return. Both the numerator (CAGR) and the denominator (Ulcer
    Index) are fractions, so the ratio is dimensionless.

    ``returns`` and ``equity`` are taken separately rather than deriving one
    from the other so the caller can feed a real equity curve (with
    contributions, financing, whatever) alongside the return stream actually
    being scored. If you want the self-consistent version, pass
    ``equity_from_returns(returns)``.
    """
    ui = ulcer_index(equity)
    if ui <= 0.0:
        raise ValueError("ulcer index is zero (equity never drew down); "
                         "the Martin ratio is undefined")
    return float((cagr(returns, periods_per_year) - rf) / ui)


def time_under_water(equity: Sequence[float] | np.ndarray | pd.Series) -> int:
    """Longest unbroken run of bars with ``d_t > 0``, in bars.

    That is, the length of the longest stretch during which the strategy was
    below a previous high-water mark. Returns 0 for an equity curve that never
    drew down. A final unrecovered stretch counts at its observed (truncated)
    length — the true value is a lower bound, since the sample simply ended.
    """
    d = np.asarray(drawdown_series(equity), dtype=float)
    under = d > 0.0
    best = run = 0
    for flag in under:
        run = run + 1 if flag else 0
        if run > best:
            best = run
    return int(best)


# --------------------------------------------------------------------------
# Part B - the ratios
# --------------------------------------------------------------------------
def equity_from_returns(
    returns: Sequence[float] | np.ndarray | pd.Series,
    initial: float = 1.0,
) -> np.ndarray | pd.Series:
    """Compound a return stream into an equity curve, ``W_t = W_0 prod(1+r)``.

    The returned curve starts at the first *post-return* value (length equals
    ``len(returns)``), not at ``initial``. That means a first-bar loss shows up
    as a drawdown only relative to ``initial`` if you prepend it yourself; for
    drawdown purposes this is the conservative reading used throughout, since a
    strategy that loses on bar 1 has no prior high-water mark to fall from.
    """
    r = _as_1d(returns, "returns")
    w = initial * np.cumprod(1.0 + r)
    if isinstance(returns, pd.Series):
        return pd.Series(w, index=returns.index, name="equity")
    return w


def cagr(
    returns: Sequence[float] | np.ndarray | pd.Series,
    periods_per_year: int = 252,
) -> float:
    """Geometric annualised return: ``(prod(1+r))^(periods_per_year/n) - 1``.

    NaNs are dropped. Raises if terminal wealth is <= 0 (a total wipeout has no
    finite geometric mean return, and returning a complex or NaN number there
    would quietly poison every ratio downstream).
    """
    r = _clean_returns(returns)
    total = float(np.prod(1.0 + r))
    if total <= 0.0:
        raise ValueError("terminal wealth <= 0; CAGR is undefined")
    return float(total ** (periods_per_year / r.size) - 1.0)


def calmar_ratio(
    returns: Sequence[float] | np.ndarray | pd.Series,
    periods_per_year: int = 252,
    window_years: float | None = 3.0,
) -> float:
    """Calmar ratio: ``CAGR / |MaxDD|`` over a trailing window.

    Reference: Young, T. W. (1991), "Calmar Ratio: A Smoother Tool", *Futures*.

    **The original definition is a trailing 36-month window** — CAGR over the
    last 36 months divided by the maximum drawdown over those same 36 months,
    conventionally recomputed monthly. That window is not decoration: it is what
    makes the number comparable across managers and across time. Applying the
    formula to a six-month backtest produces a number that is *not a Calmar
    ratio*, however it is labelled, and it will be wildly optimistic because a
    short sample simply has not had time to print its bad drawdown (see
    ``expected_max_drawdown``: E[MDD] grows without bound in T).

    The default therefore enforces the window: with ``window_years=3.0`` this
    function raises ``ValueError`` if the sample is shorter than
    ``3 * periods_per_year`` bars. Pass ``window_years=None`` for the
    full-sample variant, which is a legitimate and widely used statistic — it
    is just not Young's Calmar, and you should not call it one.

    Only the trailing ``window_years * periods_per_year`` bars are used; the
    monthly-recomputation convention is out of scope here (this returns one
    number for the window ending at the last bar).
    """
    r = _clean_returns(returns)
    if window_years is not None:
        need = int(round(window_years * periods_per_year))
        if r.size < need:
            raise ValueError(
                f"Calmar's original definition uses a trailing "
                f"{window_years}-year window ({need} bars) but only {r.size} "
                f"bars were supplied. Pass window_years=None for the "
                f"full-sample variant — but do not call that a Calmar ratio."
            )
        r = r[-need:]
    mdd = max_drawdown(equity_from_returns(r))
    if mdd <= 0.0:
        raise ValueError("maximum drawdown is zero; Calmar is undefined")
    return float(cagr(r, periods_per_year) / mdd)


def _annual_max_drawdowns(
    returns: Sequence[float] | np.ndarray | pd.Series,
    periods_per_year: int,
) -> list[float]:
    """Per-year maximum drawdowns, each measured *within* the year.

    If ``returns`` is a ``pd.Series`` with a ``DatetimeIndex`` the split is by
    calendar year; otherwise the series is chunked into blocks of
    ``periods_per_year`` bars.

    Approximation, stated plainly: each year's equity curve is restarted at 1.0,
    so a drawdown that straddles a year boundary is split into two shallower
    ones and under-counted. This is the usual reading of "average annual maximum
    drawdown" but it is a convention, not a theorem. A partial final block with
    at least 2 observations is still counted as a "year", which biases the
    average *down* (less time to draw down) on short samples.
    """
    if isinstance(returns, pd.Series) and isinstance(returns.index, pd.DatetimeIndex):
        blocks: list[np.ndarray] = [
            np.asarray(g.dropna(), dtype=float)
            for _, g in returns.groupby(returns.index.year)
        ]
    else:
        arr = _clean_returns(returns)
        blocks = [
            arr[i : i + periods_per_year]
            for i in range(0, arr.size, periods_per_year)
        ]
    out = [
        max_drawdown(equity_from_returns(b))
        for b in blocks
        if b.size >= 2
    ]
    if not out:
        raise ValueError("no block with >= 2 observations; cannot form annual MDDs")
    return out


def sterling_ratio(
    returns: Sequence[float] | np.ndarray | pd.Series,
    periods_per_year: int = 252,
    variant: str = "original",
    n_largest: int = 3,
) -> float:
    """Sterling ratio — **genuinely ambiguous in the literature**, so pick one.

    There is no single Sterling ratio. Two conventions are in wide circulation
    and they are not close to each other numerically:

    ``variant='original'``
        ``CAGR / (mean annual maximum drawdown + 0.10)``.
        The ``+10%`` is part of the original definition (Deane Sterling Jones,
        as reported by Kestner, L. (1996), "Getting Around the Sterling
        Ratio"). It is an arbitrary softening constant with no theoretical
        justification whatsoever; its effect is to stop the ratio exploding for
        managers with tiny measured drawdowns. Many modern vendors silently
        drop it, which roughly doubles the reported ratio for a strategy whose
        average annual MDD is around 10%. Annual MDDs come from
        ``_annual_max_drawdowns`` — see its docstring for the year-boundary
        approximation.

    ``variant='avg_n'``
        ``CAGR / mean(n_largest deepest drawdown episodes)``, the
        "average of the N largest drawdowns" convention (often N=3), which is
        what most CTA databases mean by "Sterling". Episodes come from
        ``drawdown_table``; if fewer than ``n_largest`` episodes exist, the
        average is taken over the episodes that do exist and that is *not*
        flagged — it just makes the denominator noisier.

    Raises ``ValueError`` on any other ``variant``. There is deliberately no
    default fallback to "whichever one works": silently choosing a convention
    is the actual failure mode this function exists to prevent.
    """
    if variant not in ("original", "avg_n"):
        raise ValueError(
            f"unknown Sterling variant {variant!r}; the Sterling ratio is "
            f"ambiguous in the literature, so choose explicitly: "
            f"'original' (CAGR / (mean annual MDD + 10%)) or "
            f"'avg_n' (CAGR / mean of the n_largest drawdowns)"
        )
    g = cagr(returns, periods_per_year)
    if variant == "original":
        denom = float(np.mean(_annual_max_drawdowns(returns, periods_per_year))) + 0.10
    else:
        if n_largest < 1:
            raise ValueError("n_largest must be >= 1")
        table = drawdown_table(equity_from_returns(returns), top_n=n_largest)
        if table.empty:
            raise ValueError("no drawdown episodes; Sterling 'avg_n' is undefined")
        denom = float(table["depth"].mean())
    if denom <= 0.0:
        raise ValueError("Sterling denominator is non-positive")
    return float(g / denom)


def sortino_ratio(
    returns: Sequence[float] | np.ndarray | pd.Series,
    mar: float = 0.0,
    periods_per_year: int = 252,
    denominator: str = "full",
) -> float:
    """Sortino ratio: annualised excess return over annualised downside deviation.

    Formula::

        excess_t   = r_t - mar                       (mar is per-period)
        DD_full    = sqrt( sum(min(excess,0)^2) / N )
        DD_down    = sqrt( sum(min(excess,0)^2) / N_downside )
        Sortino    = mean(excess) * P / (DD * sqrt(P)),   P = periods_per_year

    Reference: Sortino & Price (1994), "Performance Measurement in a Downside
    Risk Framework", *Journal of Investing*; the ``N`` denominator is what
    Sortino intended and is what the second-lower-partial-moment definition
    gives.

    ``denominator='full'`` (default) divides the sum of squared shortfalls by
    **N**, the total number of observations. ``denominator='downside'`` divides
    by **the count of downside observations only**.

    These are materially different numbers and practitioners mix them up
    constantly. Since ``N_downside <= N``, the 'downside' denominator is always
    the **larger** deviation, so the 'downside' Sortino is always the
    **smaller** ratio (for a positive numerator). For a strategy with a 40% loss
    rate the two differ by a factor of ``sqrt(1/0.4) ~ 1.58`` — big enough that
    quoting a Sortino without the convention is close to meaningless.

    ``mar`` is the per-period minimum acceptable return, in the same frequency
    as ``returns``. If you have an annual MAR, divide it yourself (and be aware
    that ``/periods_per_year`` vs ``(1+MAR)^(1/P)-1`` is yet another
    convention).
    """
    if denominator not in ("full", "downside"):
        raise ValueError(
            f"unknown denominator {denominator!r}; use 'full' (divide by N, the "
            f"standard) or 'downside' (divide by the downside count only)"
        )
    r = _clean_returns(returns)
    excess = r - mar
    shortfall = np.minimum(excess, 0.0)
    ssq = float(np.sum(shortfall**2))
    n_down = int(np.sum(shortfall < 0.0))
    if denominator == "full":
        n_eff = r.size
    else:
        if n_down == 0:
            raise ValueError(
                "no downside observations; the 'downside' Sortino denominator "
                "is 0/0. Use denominator='full' or a higher mar."
            )
        n_eff = n_down
    dd = math.sqrt(ssq / n_eff)
    if dd <= 0.0:
        raise ValueError("downside deviation is zero; Sortino is undefined")
    return float(np.mean(excess) * periods_per_year / (dd * math.sqrt(periods_per_year)))


def ratio_report(
    returns: Sequence[float] | np.ndarray | pd.Series,
    periods_per_year: int = 252,
) -> dict[str, Any]:
    """Every ratio in this module at once, plus the conventions that produced them.

    Returns a ``dict`` whose entries are floats, except ``'conventions'`` which
    is a ``dict[str, str]``. The point of that sub-dict is not documentation
    theatre: **these ratios are not comparable across sources unless the
    convention is stated**, so a report that carries its own conventions can be
    diffed against a third-party tearsheet honestly, and a report that cannot
    reproduce a number can at least say why.

    Keys: ``cagr``, ``vol``, ``sharpe``, ``max_drawdown``, ``ulcer_index``,
    ``time_under_water``, ``calmar``, ``sterling_original``, ``sterling_avg3``,
    ``sortino_full``, ``sortino_downside``, ``martin``, ``n_obs``,
    ``conventions``.

    ``sharpe`` here is the plain annualised Sharpe ``mean/std(ddof=1)*sqrt(P)``
    with a zero risk-free rate — the same quantity as
    ``validation.sharpe.annualized_sharpe``, recomputed locally so this
    subpackage has no cross-dependency. It carries **no** overfitting
    correction; for that use the Deflated Sharpe Ratio in
    ``strategies._common.validation``.

    Calmar: the trailing 3-year window is used when the sample is long enough;
    otherwise the function falls back to the full-sample variant and says so in
    ``conventions['calmar']``. It never silently pretends a short sample gave a
    real Calmar.
    """
    r = _clean_returns(returns)
    equity = equity_from_returns(r)
    conventions: dict[str, str] = {
        "periods_per_year": str(periods_per_year),
        "drawdown_sign": "positive fraction, d = 1 - W/running_max",
        "sharpe": "annualised mean/std(ddof=1)*sqrt(P), rf=0, no overfit correction",
        "cagr": "geometric: prod(1+r)^(P/n) - 1",
        "vol": "std(ddof=1)*sqrt(P)",
        "sterling_original": "CAGR / (mean annual MDD + 10%), Kestner (1996) reading; "
                             "annual MDDs measured within each block, equity restarted",
        "sterling_avg3": "CAGR / mean of the 3 deepest drawdown episodes",
        "sortino_full": "downside deviation divides by N (Sortino & Price 1994)",
        "sortino_downside": "downside deviation divides by the downside count only",
        "martin": "CAGR / ulcer_index, ulcer as a fraction not percentage points",
        "ulcer_index": "sqrt(mean(d^2)), fraction (x100 for the 1989 percentage form)",
        "time_under_water": "bars, longest consecutive run with d > 0",
    }

    need = 3 * periods_per_year
    if r.size >= need:
        calmar = calmar_ratio(r, periods_per_year, window_years=3.0)
        conventions["calmar"] = "Young (1991): trailing 3-year window, CAGR/|MaxDD|"
    else:
        calmar = calmar_ratio(r, periods_per_year, window_years=None)
        conventions["calmar"] = (
            f"FULL SAMPLE ({r.size} bars < {need} needed for the 3-year window) — "
            f"this is NOT Young's Calmar ratio and is biased optimistic"
        )

    out: dict[str, Any] = {
        "n_obs": float(r.size),
        "cagr": cagr(r, periods_per_year),
        "vol": float(r.std(ddof=1) * math.sqrt(periods_per_year)),
        "sharpe": float(r.mean() / r.std(ddof=1) * math.sqrt(periods_per_year)),
        "max_drawdown": max_drawdown(equity),
        "ulcer_index": ulcer_index(equity),
        "time_under_water": float(time_under_water(equity)),
        "calmar": calmar,
        "sterling_original": sterling_ratio(r, periods_per_year, variant="original"),
        "sterling_avg3": sterling_ratio(
            r, periods_per_year, variant="avg_n", n_largest=3
        ),
        "sortino_full": sortino_ratio(r, 0.0, periods_per_year, denominator="full"),
        "sortino_downside": sortino_ratio(
            r, 0.0, periods_per_year, denominator="downside"
        ),
        "martin": martin_ratio(r, equity, periods_per_year),
        "conventions": conventions,
    }
    return out


# --------------------------------------------------------------------------
# Part C - expected maximum drawdown of a Brownian motion
# --------------------------------------------------------------------------
_EMDD_METHODS = ("auto", "mc", "asymptotic", "exact")

#: Default cut-off for "T is large enough for the asymptotic to be usable".
#: The natural dimensionless time in Magdon-Ismail & Atiya is
#: ``2 mu^2 T / sigma^2`` (the argument of the logarithm in the mu>0 branch);
#: below ~10 the asymptotic is visibly wrong and below ~e it is negative.
EMDD_ASYMPTOTIC_THRESHOLD = 10.0


def _emdd_monte_carlo(
    mu: float,
    sigma: float,
    T: float,
    n_paths: int,
    seed: int,
    n_steps: int,
) -> float:
    """Monte Carlo E[MDD] of ``X_t = mu t + sigma B_t`` on ``[0, T]``.

    Absolute (additive) drawdown of the arithmetic Brownian motion, i.e. the
    log-wealth drawdown, matching the closed forms above.

    Known bias: the maximum is only monitored on a discrete grid, which
    **under**-estimates E[MDD] by roughly ``2 * 0.5826 * sigma * sqrt(dt)``
    (Broadie, Glasserman & Kou 1997 continuity correction, applied once to the
    running maximum and once to the minimum that follows it). No correction is
    applied here; increase ``n_steps`` if that matters.
    """
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    drift = mu * dt
    diff = sigma * math.sqrt(dt)
    # Cap the working array at ~2e6 doubles per chunk so large n_paths x n_steps
    # grids do not allocate hundreds of MB.
    chunk = max(1, int(2_000_000 // max(n_steps, 1)))
    total = 0.0
    remaining = n_paths
    while remaining > 0:
        m = min(chunk, remaining)
        z = rng.standard_normal((m, n_steps))
        x = np.cumsum(drift + diff * z, axis=1)
        x = np.concatenate([np.zeros((m, 1)), x], axis=1)
        run_max = np.maximum.accumulate(x, axis=1)
        total += float((run_max - x).max(axis=1).sum())
        remaining -= m
    return total / n_paths


def _emdd_asymptotic(mu: float, sigma: float, T: float) -> float:
    """Large-T asymptotic E[MDD] for ``mu != 0``. See ``expected_max_drawdown``."""
    if mu > 0.0:
        return (sigma**2 / (2.0 * mu)) * math.log(2.0 * mu**2 * T / sigma**2)
    return abs(mu) * T


def expected_max_drawdown(
    mu: float,
    sigma: float,
    T: float,
    method: str = "auto",
    n_paths: int = 20_000,
    seed: int = 0,
    n_steps: int = 2_000,
) -> float:
    """Expected maximum drawdown of a Brownian motion with drift.

    For ``X_t = mu * t + sigma * B_t`` on ``[0, T]``, returns
    ``E[ max_{t<=T} ( max_{s<=t} X_s - X_t ) ]`` — an **absolute** drawdown in
    the units of X. Since Parts C/D work in log wealth, an answer of ``0.25``
    means a log drawdown of 0.25, i.e. a fractional drawdown of
    ``1 - exp(-0.25) = 22.1%``.

    Reference: Magdon-Ismail, Atiya, Pratap & Abu-Mostafa (2004), "On the
    Maximum Drawdown of a Brownian Motion", *Journal of Applied Probability*
    41(1), 147-161.

    Three regimes
    -------------
    ``mu == 0`` — **exact closed form**::

        E[MDD] = sqrt(pi/2) * sigma * sqrt(T)    ( = 1.25331 * sigma * sqrt(T) )

    ``mu > 0`` — asymptotically, for large T::

        E[MDD] ~ (sigma^2 / (2 mu)) * log( 2 mu^2 T / sigma^2 )

    ``mu < 0`` — asymptotically, for large T::

        E[MDD] ~ |mu| * T

    The trader-relevant content: with no edge the worst drawdown grows like
    ``sqrt(T)``; with an edge it grows only like ``log(T)``; with a negative
    edge it grows *linearly* and you are simply being drained.

    Regime of validity and what this function does outside it
    ---------------------------------------------------------
    Both ``mu != 0`` expressions are leading-order asymptotics in the
    dimensionless time ``tau = 2 mu^2 T / sigma^2``. They are only usable for
    ``tau >> 1``; for ``tau <= 1`` the ``mu > 0`` form is literally negative,
    which is not an approximation but nonsense. This function therefore
    **refuses to return an invalid asymptotic**:

    * ``method='auto'``  — exact form at ``mu == 0``; the asymptotic when
      ``tau >= EMDD_ASYMPTOTIC_THRESHOLD`` (10.0); otherwise it **simulates**
      (Monte Carlo), because a simulated number is honest and a leading-order
      asymptotic outside its regime is not.
    * ``method='mc'``    — always simulate.
    * ``method='asymptotic'`` — force the asymptotic; raises at ``mu == 0``
      (there is no asymptotic there, the closed form is exact) and raises when
      ``tau`` is small enough that the expression is non-positive.
    * ``method='exact'`` — the closed form; raises unless ``mu == 0``, since no
      exact closed form is implemented for ``mu != 0``. (Magdon-Ismail & Atiya
      give one in terms of an infinite series / numerically-tabulated ``Q_p``
      function; it is deliberately **not** implemented here rather than being
      faked.)

    Monte Carlo caveats: discrete monitoring biases E[MDD] downward (see
    ``_emdd_monte_carlo``), and the estimate carries the usual ``1/sqrt(n)``
    noise. Use ``mdd_scaling_check`` to see where the asymptotic and the
    simulation part company.
    """
    if method not in _EMDD_METHODS:
        raise ValueError(f"unknown method {method!r}; use one of {_EMDD_METHODS}")
    if sigma <= 0.0:
        raise ValueError("sigma must be > 0")
    if T <= 0.0:
        raise ValueError("T must be > 0")
    if n_steps < 1:
        raise ValueError("n_steps must be >= 1")

    tau = 2.0 * mu**2 * T / sigma**2

    if method == "mc":
        return _emdd_monte_carlo(mu, sigma, T, n_paths, seed, n_steps)

    if method == "exact":
        if mu != 0.0:
            raise ValueError(
                "no exact closed form is implemented for mu != 0; the "
                "Magdon-Ismail & Atiya (2004) exact result needs their "
                "tabulated Q_p function. Use method='mc' or 'asymptotic'."
            )
        return math.sqrt(math.pi / 2.0) * sigma * math.sqrt(T)

    if method == "asymptotic":
        if mu == 0.0:
            raise ValueError(
                "mu == 0 has an exact closed form; asymptotic is not defined "
                "there. Use method='exact' or 'auto'."
            )
        val = _emdd_asymptotic(mu, sigma, T)
        if val <= 0.0:
            raise ValueError(
                f"the large-T asymptotic is non-positive at "
                f"tau = 2*mu^2*T/sigma^2 = {tau:.4g} — you are outside its "
                f"regime of validity. Use method='mc'."
            )
        return val

    # method == 'auto'
    if mu == 0.0:
        return math.sqrt(math.pi / 2.0) * sigma * math.sqrt(T)
    if tau >= EMDD_ASYMPTOTIC_THRESHOLD:
        return _emdd_asymptotic(mu, sigma, T)
    return _emdd_monte_carlo(mu, sigma, T, n_paths, seed, n_steps)


def mdd_scaling_check(
    mu: float,
    sigma: float,
    Ts: Iterable[float],
    n_paths: int = 4_000,
    seed: int = 0,
    steps_per_unit_time: int = 500,
    max_steps: int = 20_000,
    threshold: float = EMDD_ASYMPTOTIC_THRESHOLD,
) -> pd.DataFrame:
    """Asymptotic vs Monte Carlo E[MDD] across horizons — where does it break?

    One row per horizon in ``Ts``, with columns:

    ``T``               the horizon
    ``tau``             ``2*mu^2*T/sigma^2``, the dimensionless time that
                        governs whether the asymptotic applies
    ``regime_ok``       ``tau >= threshold``
    ``closed_form``     the exact ``sqrt(pi/2)*sigma*sqrt(T)`` when ``mu == 0``,
                        otherwise the large-T asymptotic (``NaN`` where that
                        expression is non-positive, i.e. plainly invalid)
    ``monte_carlo``     simulated estimate
    ``rel_error``       ``closed_form / monte_carlo - 1``

    The Monte Carlo grid uses ``n_steps = clip(steps_per_unit_time * T, 500,
    max_steps)``, so ``dt`` grows with ``T`` once the cap binds and the discrete
    monitoring bias (downward, see ``_emdd_monte_carlo``) grows with it. Read a
    few-percent positive ``rel_error`` at large ``T`` as partly that bias, not
    purely asymptotic error. This is a diagnostic, not a proof.
    """
    rows = []
    for i, T in enumerate(Ts):
        T = float(T)
        tau = 2.0 * mu**2 * T / sigma**2
        n_steps = int(np.clip(steps_per_unit_time * T, 500, max_steps))
        # Vary the seed per horizon so adjacent rows are not sharing the same
        # noise draw and cannot fake a smooth curve.
        mc = _emdd_monte_carlo(mu, sigma, T, n_paths, seed + i, n_steps)
        if mu == 0.0:
            closed = math.sqrt(math.pi / 2.0) * sigma * math.sqrt(T)
        else:
            val = _emdd_asymptotic(mu, sigma, T)
            closed = val if val > 0.0 else float("nan")
        rows.append(
            {
                "T": T,
                "tau": tau,
                "regime_ok": bool(tau >= threshold),
                "closed_form": closed,
                "monte_carlo": mc,
                "rel_error": closed / mc - 1.0 if mc > 0 else float("nan"),
            }
        )
    return pd.DataFrame(
        rows, columns=["T", "tau", "regime_ok", "closed_form", "monte_carlo", "rel_error"]
    )


# --------------------------------------------------------------------------
# Part D - MDD-constrained leverage
# --------------------------------------------------------------------------
def merton_fraction(
    mu: float,
    sigma: float,
    r: float = 0.0,
    gamma: float = 1.0,
) -> float:
    """Merton's optimal risky fraction: ``pi_M = (mu - r) / (gamma * sigma^2)``.

    Reference: Merton, R. C. (1969), "Lifetime Portfolio Selection under
    Uncertainty", *Review of Economics and Statistics* 51(3). Constant relative
    risk aversion ``gamma``, GBM prices, no constraints, continuous rebalancing.

    ``gamma = 1`` (log utility) reduces to the full Kelly fraction
    ``(mu - r)/sigma^2``. All inputs are in the same time unit; annual in,
    annual out.
    """
    if sigma <= 0.0:
        raise ValueError("sigma must be > 0")
    if gamma <= 0.0:
        raise ValueError("gamma must be > 0")
    return float((mu - r) / (gamma * sigma**2))


def grossman_zhou_leverage(
    drawdown: float | Sequence[float] | np.ndarray | pd.Series,
    alpha: float,
    merton_fraction: float,
) -> np.ndarray | pd.Series | float:
    """Optimal risky fraction under a maximum-drawdown constraint.

    Grossman & Zhou (1993), "Optimal Investment Strategies for Controlling
    Drawdowns", *Mathematical Finance* 3(3); generalised to general utility and
    multiple assets by Cvitanic & Karatzas (1995), "On Portfolio Optimization
    under Drawdown Constraints", *IMA Volumes in Mathematics and its
    Applications* 65.

    Under the constraint ``W_t >= alpha * max_{s<=t} W_s`` (never fall below
    ``alpha`` of the running high-water mark), the optimal risky fraction is::

        pi_t = pi_M * (1 - alpha / (1 - d_t)) / (1 - alpha)

    where ``d_t`` is the current drawdown ``1 - W_t / M_t`` and
    ``pi_M = (mu - r) / (gamma * sigma^2)`` is the unconstrained Merton (Kelly
    for ``gamma=1``) fraction. Values are clipped at 0 from below: past the
    floor the position is flat, not short.

    Properties (asserted in the tests):

    * ``pi = pi_M`` at ``d = 0`` — at a new high the constraint is slack.
    * ``pi = 0`` at ``d = 1 - alpha`` — exactly at the floor you are fully
      de-risked, which is what makes the constraint self-enforcing.
    * strictly decreasing in ``d`` on ``[0, 1 - alpha]``.

    On the shape — this gets described wrongly all the time
    -------------------------------------------------------
    Write the normalised cushion ``kappa_t = (W_t - alpha * M_t) / W_t``. Then
    ``pi_t = pi_M * kappa_t / (1 - alpha)``: leverage is **linear in the
    cushion**. As a function of *drawdown depth* it is
    ``pi_M * (1 - alpha/(1-d)) / (1-alpha)``, whose second derivative in ``d``
    is ``-2*alpha*pi_M / ((1-alpha)*(1-d)^3) < 0`` for ``pi_M > 0``: it is
    **concave** in ``d`` — de-risking *accelerates* as the drawdown deepens.
    Calling this "convex in drawdown" is the common description and it is
    wrong; the convex object is the cushion-based one, and only in the trivial
    linear sense.

    Practical warning: this is a continuous-time result assuming continuous
    rebalancing and GBM. In discrete time with gaps, a jump straight through
    the floor is possible and the constraint is then violated ex post. The
    formula controls the *drift* toward the floor, not a gap through it.

    Returns a ``pd.Series`` (same index) for a Series input, an ``np.ndarray``
    for array input, and a ``float`` for a scalar input.
    """
    if not (0.0 <= alpha < 1.0):
        raise ValueError("alpha must be in [0, 1)")
    scalar_in = np.isscalar(drawdown)
    d = np.asarray(drawdown, dtype=float)
    if np.any(d < 0.0) or np.any(d >= 1.0):
        raise ValueError("drawdown must be in [0, 1)")
    pi = merton_fraction * (1.0 - alpha / (1.0 - d)) / (1.0 - alpha)
    pi = np.maximum(pi, 0.0)
    if isinstance(drawdown, pd.Series):
        return pd.Series(pi, index=drawdown.index, name="leverage")
    if scalar_in:
        return float(pi)
    return pi


def kelly_leverage_with_dd_cap(
    mu: float,
    sigma: float,
    dd_cap: float,
    prob: float = 0.05,
    r: float = 0.0,
) -> dict[str, Any]:
    """Largest leverage whose **all-time** drawdown risk respects a cap.

    Setup. With leverage ``L`` on a GBM asset, log wealth is
    ``X_t = nu*t + s*B_t`` with::

        nu = L*(mu - r) - L^2 * sigma^2 / 2      (log-growth rate)
        s  = L * sigma

    For ``nu > 0`` the all-time maximum drawdown in **log** terms has the
    exponential tail (a standard result for the running maximum of a drifting
    Brownian motion; see e.g. Harris (1976) / any first-passage treatment)::

        P( D_inf > x ) = exp( -2 * nu * x / s^2 )

    Requiring ``P(fractional drawdown > dd_cap) <= prob`` means
    ``x = -log(1 - dd_cap)`` and ``exp(-2*nu*x/s^2) <= prob``. Substituting nu
    and s and writing ``K = (mu - r)/sigma^2`` for the full-Kelly fraction, the
    constraint reduces to ``x * (2K/L - 1) >= log(1/prob)``, whose solution is
    the closed form ``L_max = 2*K*x / (x + log(1/prob))``. The solve here is
    nonetheless done numerically (``brentq`` on the strictly decreasing
    constraint function over ``(eps, 2K)``) as specified, and the closed form is
    reported as ``closed_form_leverage`` so the two can be compared.

    Returned dict
    -------------
    ``leverage``               the leverage to actually run:
                               ``min(L_max, full_kelly)``. Levering past full
                               Kelly lowers growth *and* raises drawdown, so
                               returning ``L_max > K`` as "the answer" would be
                               a misleading number.
    ``max_admissible_leverage`` ``L_max`` itself, unclipped.
    ``closed_form_leverage``   ``2*K*x/(x + log(1/prob))``, for cross-checking.
    ``full_kelly``             ``(mu - r)/sigma^2``.
    ``fraction_of_kelly``      ``leverage / full_kelly``.
    ``nu``                     log-growth rate at the returned leverage.
    ``binding``                ``True`` iff the drawdown cap actually bit, i.e.
                               ``L_max < full_kelly``.
    ``note``                   plain-language statement of what happened,
                               including the infeasible case.

    Caveats, stated rather than buried
    ----------------------------------
    * This is an **all-time (infinite-horizon)** drawdown probability. Over a
      finite horizon the probability of breaching ``dd_cap`` is strictly
      smaller, so this rule is **conservative** relative to a finite-horizon
      one — deliberately.
    * It assumes **GBM**: continuous paths, constant ``mu`` and ``sigma``, iid
      increments, continuous rebalancing, no financing spread, no slippage. Real
      returns have fat tails, volatility clustering and overnight gaps, all of
      which make the true breach probability **higher** than ``prob``. Treat the
      output as an upper bound on prudent leverage, not a guarantee.
    * ``mu`` and ``sigma`` are estimates. The sensitivity of ``L`` to ``mu`` is
      linear and ``mu`` is the hardest parameter in finance to estimate; see
      ``complexity_budget`` for what that error costs.
    * If ``K <= 0`` there is no edge: ``nu <= 0`` for every ``L > 0``, all-time
      drawdown is 1 almost surely, and **no** positive leverage satisfies any
      cap. The function returns ``leverage = 0.0`` and says so in ``note``.
    """
    if sigma <= 0.0:
        raise ValueError("sigma must be > 0")
    if not (0.0 < dd_cap < 1.0):
        raise ValueError("dd_cap must be in (0, 1)")
    if not (0.0 < prob < 1.0):
        raise ValueError("prob must be in (0, 1)")

    full_kelly = (mu - r) / sigma**2
    x = -math.log(1.0 - dd_cap)          # log-drawdown equivalent of dd_cap
    log_inv_p = math.log(1.0 / prob)

    if full_kelly <= 0.0:
        return {
            "leverage": 0.0,
            "max_admissible_leverage": 0.0,
            "closed_form_leverage": 0.0,
            "full_kelly": float(full_kelly),
            "fraction_of_kelly": float("nan"),
            "nu": 0.0,
            "binding": True,
            "note": (
                "no edge (mu - r <= 0): log-growth nu <= 0 for every positive "
                "leverage, so the all-time drawdown is 1 almost surely and no "
                "leverage satisfies the cap. Returned 0."
            ),
        }

    def constraint(L: float) -> float:
        """>= 0 iff P(D_inf > x) <= prob. Strictly decreasing in L on (0, 2K)."""
        return x * (2.0 * full_kelly / L - 1.0) - log_inv_p

    lo = 1e-12 * max(full_kelly, 1.0)
    hi = 2.0 * full_kelly * (1.0 - 1e-12)
    # constraint(lo) -> +inf, constraint(hi) -> -log(1/prob) < 0, so the root is
    # bracketed and unique.
    l_max = float(brentq(constraint, lo, hi, xtol=1e-14, rtol=1e-14))
    closed_form = 2.0 * full_kelly * x / (x + log_inv_p)

    binding = l_max < full_kelly
    leverage = min(l_max, full_kelly)
    nu = leverage * (mu - r) - 0.5 * leverage**2 * sigma**2

    if binding:
        note = (
            f"drawdown cap binds: the {dd_cap:.1%} / {prob:.1%} all-time cap "
            f"admits at most L={l_max:.4f}, below full Kelly "
            f"({full_kelly:.4f}). Assumes GBM, so real fat tails and gap risk "
            f"make even this optimistic."
        )
    else:
        note = (
            f"drawdown cap does NOT bind: full Kelly ({full_kelly:.4f}) already "
            f"satisfies P(DD > {dd_cap:.1%}) <= {prob:.1%} (the cap would allow "
            f"L up to {l_max:.4f}). Returned full Kelly; going beyond it lowers "
            f"growth and raises drawdown. Assumes GBM."
        )

    return {
        "leverage": float(leverage),
        "max_admissible_leverage": float(l_max),
        "closed_form_leverage": float(closed_form),
        "full_kelly": float(full_kelly),
        "fraction_of_kelly": float(leverage / full_kelly),
        "nu": float(nu),
        "binding": bool(binding),
        "note": note,
    }


def complexity_budget(
    leverage: float,
    sigma: float,
    n_obs: int,
    growth_loss_tolerance: float = 0.001,
    k: float = 1.0,
) -> dict[str, Any]:
    """How many free parameters a strategy can afford at a given leverage.

    Derivation
    ----------
    Log-growth at leverage ``L`` is ``g(L) = L*mu - L^2*sigma^2/2``, maximised
    at ``L* = mu/sigma^2``. Suppose you run ``L_hat = L*(1 + delta)`` — a
    *relative* leverage error ``delta``, which is exactly what a mis-estimated
    ``mu`` produces. Expanding around the optimum::

        g(L) - g(L(1+delta)) = 0.5 * sigma^2 * L^2 * delta^2

    So the growth you give up scales with **L squared**. Now the heuristic step:
    a model fit with ``p`` free parameters on ``n`` observations carries a
    relative parameter error of order ``delta^2 ~ k * p / n``. Requiring the
    growth loss to stay under a tolerance ``tau``::

        0.5 * sigma^2 * L^2 * (k*p/n) <= tau
        =>  p_max = 2 * tau * n / (k * sigma^2 * L^2)

    **Admissible model complexity falls as 1/L^2.** Double the leverage and you
    may afford a quarter of the parameters. That is the quantitative form of
    "if you are going to run size, your filter had better be very simple".

    This is NOT a theorem
    ---------------------
    The first line (the quadratic growth loss) is exact — it is just a Taylor
    expansion of a quadratic, so it is the quadratic itself. The second line
    (``delta^2 ~ k*p/n``) is an **order-of-magnitude scaling argument** in the
    spirit of an AIC / effective-degrees-of-freedom penalty: it says estimation
    error grows with parameters and shrinks with data, at the usual ``p/n``
    rate. It is not derived from any specific estimator, it ignores parameter
    correlation, regularisation, non-stationarity and the fact that in practice
    ``mu`` error is dominated by *sample* noise rather than parameter count.
    ``k`` is a fudge factor absorbing all of that, and the user should calibrate
    it (e.g. by bootstrapping their own fitting procedure and measuring the
    realised spread of ``L_hat/L*``) rather than trusting ``k = 1``.

    Use the **ratio** between two leverages, which is exact under the stated
    scaling and independent of ``k``, in preference to the absolute
    ``max_parameters``, which is only as good as ``k``.

    Returns
    -------
    ``max_parameters``       ``p_max`` above (a float; not floored to an int,
                             because a budget of 0.4 parameters is a meaningful
                             statement and rounding it to 0 or 1 is not)
    ``loss_per_parameter``   ``0.5 * sigma^2 * L^2 * k / n``, the log-growth
                             given up per extra free parameter
    ``growth_loss_tolerance``/``leverage``/``sigma``/``n_obs``/``k`` echoed back
    ``assumptions``          the caveat above in one string
    """
    if leverage <= 0.0:
        raise ValueError("leverage must be > 0")
    if sigma <= 0.0:
        raise ValueError("sigma must be > 0")
    if n_obs < 1:
        raise ValueError("n_obs must be >= 1")
    if growth_loss_tolerance <= 0.0:
        raise ValueError("growth_loss_tolerance must be > 0")
    if k <= 0.0:
        raise ValueError("k must be > 0")

    loss_per_parameter = 0.5 * sigma**2 * leverage**2 * k / n_obs
    p_max = 2.0 * growth_loss_tolerance * n_obs / (k * sigma**2 * leverage**2)
    return {
        "max_parameters": float(p_max),
        "loss_per_parameter": float(loss_per_parameter),
        "leverage": float(leverage),
        "sigma": float(sigma),
        "n_obs": int(n_obs),
        "k": float(k),
        "growth_loss_tolerance": float(growth_loss_tolerance),
        "assumptions": (
            "Exact: growth loss = 0.5*sigma^2*L^2*delta^2 for a relative "
            "leverage error delta (quadratic expansion of g(L)=L*mu-L^2*sigma^2/2 "
            "about L*=mu/sigma^2). HEURISTIC: delta^2 ~ k*p/n is an "
            "order-of-magnitude AIC-style scaling, not a theorem; it ignores "
            "parameter correlation, regularisation and non-stationarity. k is a "
            "fudge factor to be calibrated by the user. The 1/L^2 ratio between "
            "two leverages is robust; the absolute p_max is only as good as k."
        ),
    }
