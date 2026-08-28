"""Data-snooping corrections for a *zoo* of candidate strategies.

CPCV / PSR / DSR / PBO (the sibling modules) each answer "is *this one*
backtest overfit?". None of them answer the question you actually have after
a screening run: **you tried M strategies and kept the best - is the winner
real?** That is a multiple-testing problem across models, and the three tests
implemented here are the standard answers:

* White (2000) "A Reality Check for Data Snooping" - bootstrap the
  distribution of ``max_k sqrt(T) * mean(f_k)`` under the least-favourable
  null and compare the observed maximum against it.
* Hansen (2005) "A Test for Superior Predictive Ability" - the same idea, but
  studentised and with a *recentring* rule that stops hopeless models from
  inflating the null distribution. Uniformly no less powerful than White's RC.
* Romano & Wolf (2005) stepwise multiple testing (StepM) - instead of one
  yes/no on the maximum, iteratively identify *which* models beat the
  benchmark while controlling the familywise error rate at ``alpha``.

All three depend on a time-series bootstrap that preserves serial dependence:
Politis & Romano's (1994) stationary bootstrap, plus the simpler circular
block bootstrap.

Design rule (matching ``sharpe.py`` / ``cpcv.py``): numpy only, no zipline, no
pandas requirement, consumes plain arrays - so this subpackage stays
lift-ready into ``gs_common.quant.validation``.

**Ex-post only.** Every statistic here is a full-sample, end-of-backtest
diagnostic: it reads the whole performance panel at once and is therefore
*deliberately* non-causal. Nothing in this module may be used to generate a
trading signal or a point-in-time factor. ``EX_POST_ONLY`` names the
functions this warning applies to, and ``tests/test_reality_check.py``
asserts that none of them returns a per-timestamp series that a caller could
mistake for a signal.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

#: Functions that consume the *entire* performance panel and are non-causal by
#: design. They are backtest post-mortem statistics, never signal generators.
EX_POST_ONLY = frozenset(
    {
        "whites_reality_check",
        "hansens_spa",
        "stepwise_multiple_testing",
        "snooping_report",
    }
)

#: Below this many periods the bootstrap max-distribution is too coarse for
#: the resulting p-value to mean anything, so we refuse rather than return a
#: confident-looking number.
MIN_OBS = 20

# Guards against division by ~0 when a candidate's performance differential is
# (numerically) constant - e.g. a strategy that never traded.
_OMEGA_FLOOR = 1e-12


# --------------------------------------------------------------------------- #
# bootstrap index generators
# --------------------------------------------------------------------------- #
def stationary_bootstrap_indices(
    n: int,
    mean_block: float,
    n_boot: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Politis & Romano (1994) stationary bootstrap resampling indices.

    Computes an ``(n_boot, n)`` integer array of positions into a series of
    length ``n``. Construction, per replicate, for ``t = 0 .. n-1``::

        i_0 ~ Uniform{0..n-1}
        i_t = (i_{t-1} + 1) mod n    with probability 1 - p
        i_t ~ Uniform{0..n-1}        with probability p,    p = 1 / mean_block

    i.e. block lengths are Geometric(p) with mean ``mean_block``, and blocks
    wrap around the end of the series. The wrap-around plus the uniform block
    starts make the resampled series (strictly) stationary, which is the whole
    point of the scheme: unlike the fixed-length moving-block bootstrap, the
    marginal distribution of every sampled index is exactly Uniform{0..n-1},
    so bootstrap means are unbiased for the sample mean.

    Reference: Politis, D.N. & Romano, J.P. (1994), "The Stationary
    Bootstrap", JASA 89(428), 1303-1313.
    """
    if n < 2:
        raise ValueError("n must be >= 2 to bootstrap a series")
    if not np.isfinite(mean_block) or mean_block < 1.0:
        raise ValueError("mean_block must be a finite float >= 1")
    if n_boot < 1:
        raise ValueError("n_boot must be >= 1")

    p = 1.0 / float(mean_block)
    idx = np.empty((n_boot, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, size=n_boot)
    # Draw both random streams up front: one uniform per step to decide
    # "start a new block?", one uniform position for when the answer is yes.
    new_block = rng.random((n_boot, n - 1)) < p
    fresh = rng.integers(0, n, size=(n_boot, n - 1))
    for t in range(1, n):
        cont = (idx[:, t - 1] + 1) % n
        idx[:, t] = np.where(new_block[:, t - 1], fresh[:, t - 1], cont)
    return idx


def circular_block_bootstrap_indices(
    n: int,
    block_size: int,
    n_boot: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Circular (wrap-around) moving-block bootstrap resampling indices.

    Returns an ``(n_boot, n)`` integer array. ``ceil(n / block_size)`` blocks
    of *fixed* length ``block_size`` are drawn with uniform starts in
    ``{0..n-1}``; block ``j`` contributes the positions
    ``(start_j + 0 .. start_j + block_size - 1) mod n``; the concatenation is
    truncated back to length ``n``.

    Wrapping (Politis & Romano 1992) is what makes every index equally likely,
    removing the under-weighting of the first and last observations that the
    non-circular moving-block bootstrap of Kuensch (1989) suffers from.

    Reference: Politis, D.N. & Romano, J.P. (1992), "A circular
    block-resampling procedure for stationary data", in *Exploring the Limits
    of Bootstrap*, Wiley, 263-270.
    """
    if n < 2:
        raise ValueError("n must be >= 2 to bootstrap a series")
    if block_size < 1 or block_size > n:
        raise ValueError("block_size must be in [1, n]")
    if n_boot < 1:
        raise ValueError("n_boot must be >= 1")

    n_blocks = int(np.ceil(n / block_size))
    starts = rng.integers(0, n, size=(n_boot, n_blocks))
    offsets = np.arange(block_size, dtype=np.int64)
    idx = (starts[:, :, None] + offsets[None, None, :]) % n
    return idx.reshape(n_boot, n_blocks * block_size)[:, :n].astype(np.int64)


# --------------------------------------------------------------------------- #
# shared internals
# --------------------------------------------------------------------------- #
def _as_panel(perf: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray:
    """Validate and normalise the performance panel to a 2-D ``(T, M)`` array."""
    arr = np.asarray(perf, dtype=float)
    if arr.ndim == 1:
        arr = arr[:, None]
    if arr.ndim != 2:
        raise ValueError("perf must be 1-D (T,) or 2-D (T, M)")
    t_obs, n_models = arr.shape
    if n_models < 1:
        raise ValueError("perf must contain at least one candidate model")
    if t_obs < MIN_OBS:
        raise ValueError(
            f"need at least {MIN_OBS} observations to bootstrap a reality "
            f"check; got T={t_obs}. With fewer periods the bootstrap "
            f"max-distribution is degenerate and any p-value it produces is "
            f"noise, so this refuses rather than guessing."
        )
    if not np.all(np.isfinite(arr)):
        raise ValueError("perf contains NaN/inf; clean or drop those periods first")
    return arr


def _bootstrap_column_means(perf: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """Column means of ``perf[indices[b]]`` for every replicate ``b``.

    Materialising ``perf[indices]`` would be an ``(n_boot, T, M)`` array - 200 MB
    at n_boot=1000, T=500, M=50. Instead we count how often each row is drawn
    (an ``(n_boot, T)`` matrix) and get every replicate mean from one matmul.
    """
    n_boot, t_obs = indices.shape
    flat = (np.arange(n_boot, dtype=np.int64)[:, None] * t_obs + indices).ravel()
    counts = np.bincount(flat, minlength=n_boot * t_obs).reshape(n_boot, t_obs)
    return (counts.astype(float) @ perf) / float(t_obs)


def _boot_indices(t_obs: int, n_boot: int, mean_block: float, seed: int) -> np.ndarray:
    return stationary_bootstrap_indices(
        t_obs, mean_block, n_boot, np.random.default_rng(seed)
    )


def _omega(perf: np.ndarray, boot_means: np.ndarray, t_obs: int) -> np.ndarray:
    """Hansen's ``omega_k``: the bootstrap std of ``sqrt(T) * mean(f_k)``.

    Formula::

        omega_k^2 = (1/B) * sum_b [ sqrt(T) * (f*_{b,k} - f_bar_k) ]^2

    Approximation notice: Hansen (2005) permits either a HAC kernel estimator
    or a bootstrap estimator for ``omega_k``; this is the bootstrap one, taken
    as the raw second moment about the *sample* mean (not about the bootstrap
    mean). It inherits its dependence structure from the stationary
    bootstrap's block length, so it is *not* identical to a Bartlett-kernel
    HAC estimate, and the two can differ materially when ``mean_block``
    mismatches the true autocorrelation length. The literature gives no
    definitive rule for choosing that block length.
    """
    centred = np.sqrt(t_obs) * (boot_means - perf.mean(axis=0))
    om = np.sqrt(np.mean(centred**2, axis=0))
    return np.maximum(om, _OMEGA_FLOOR)


# --------------------------------------------------------------------------- #
# White's Reality Check
# --------------------------------------------------------------------------- #
def whites_reality_check(
    perf: Sequence[Sequence[float]] | np.ndarray,
    n_boot: int = 1000,
    mean_block: float = 10.0,
    seed: int = 0,
) -> dict:
    """White's (2000) Reality Check for data snooping.

    ``perf`` is a ``(T, M)`` panel of a *performance differential*: period-t
    value ``f_{t,k}`` = (strategy k's return) - (benchmark's return), for M
    candidates. The null is the least-favourable configuration::

        H0:  max_k E[f_k] <= 0        ("no candidate beats the benchmark")

    Computes, with ``f_bar_k = mean_t f_{t,k}``::

        V     = max_k sqrt(T) * f_bar_k
        V*_b  = max_k sqrt(T) * ( f*_{b,k} - f_bar_k )          (recentred)
        p     = (1/B) * sum_b 1{ V*_b > V }

    where ``f*_{b,k}`` is the mean of column k over the b-th stationary
    bootstrap resample. Recentring by ``f_bar_k`` is what imposes the null: it
    forces every candidate's bootstrap mean to zero expectation, so ``V*`` is
    the distribution of the best-of-M statistic *when nobody has skill*.

    Returns ``statistic``, ``p_value``, ``best_index``, ``n_models``,
    ``n_obs`` and the raw ``bootstrap_dist`` (length ``n_boot``).

    Ex-post diagnostic only - see the module docstring.

    Reference: White, H. (2000), "A Reality Check for Data Snooping",
    Econometrica 68(5), 1097-1126.
    """
    arr = _as_panel(perf)
    t_obs, n_models = arr.shape
    f_bar = arr.mean(axis=0)
    scaled = np.sqrt(t_obs) * f_bar
    best = int(np.argmax(scaled))
    v_stat = float(scaled[best])

    idx = _boot_indices(t_obs, n_boot, mean_block, seed)
    boot_means = _bootstrap_column_means(arr, idx)
    v_boot = np.max(np.sqrt(t_obs) * (boot_means - f_bar), axis=1)
    p_value = float(np.mean(v_boot > v_stat))

    return {
        "statistic": v_stat,
        "p_value": p_value,
        "best_index": best,
        "n_models": int(n_models),
        "n_obs": int(t_obs),
        "bootstrap_dist": v_boot,
    }


# --------------------------------------------------------------------------- #
# Hansen's SPA
# --------------------------------------------------------------------------- #
def hansens_spa(
    perf: Sequence[Sequence[float]] | np.ndarray,
    n_boot: int = 1000,
    mean_block: float = 10.0,
    seed: int = 0,
) -> dict:
    """Hansen's (2005) test for Superior Predictive Ability.

    Same null as White's RC (``max_k E[f_k] <= 0``) but it fixes the RC's two
    weaknesses: it studentises, and it does not recentre models that are
    obviously terrible.

    Why the recentring matters - this is the whole point of SPA. White's RC
    recentres *every* candidate to mean zero before taking the maximum. A
    strategy with a hugely negative true mean therefore contributes a
    mean-zero, full-variance draw to the bootstrap maximum, exactly as if it
    were a serious contender. Add fifty hopeless strategies to the zoo and the
    RC null distribution shifts right, the critical value rises, and a
    genuinely good strategy stops being significant: the test is dragged
    toward non-rejection by junk you already knew was junk. Hansen's
    recentring leaves such models at their (very negative) sample mean, so
    they can never be the bootstrap maximum, the null distribution stays
    tight, and SPA gets more power at the same size.

    Statistic, with ``omega_k`` from :func:`_omega`::

        T_spa = max( 0,  max_k sqrt(T) * f_bar_k / omega_k )

    Bootstrap, with a per-model recentring target ``g_k``::

        Z*_{b,k} = sqrt(T) * ( f*_{b,k} - g_k ) / omega_k
        T*_b     = max( 0, max_k Z*_{b,k} )
        p        = (1/B) * sum_b 1{ T*_b > T_spa }

    Three choices of ``g_k`` give the three p-values, all returned:

    ``p_lower``
        ``g_k = f_bar_k * 1{ f_bar_k >= 0 }``. Recentres the fewest models ->
        smallest p -> *liberal* (a lower bound on the true p-value).
    ``p_consistent``
        ``g_k = f_bar_k * 1{ f_bar_k >= -sqrt(omega_k^2 / T * 2*log(log T)) }``.
        Hansen's recommended rule. The threshold shrinks at the
        law-of-the-iterated-logarithm rate, which is what makes the test
        consistent: models with a truly negative mean are eventually excluded
        with probability one, while models near the boundary are kept.
    ``p_upper``
        ``g_k = f_bar_k`` for every k. Recentres everything, i.e. exactly
        White's RC in studentised form -> largest p -> *conservative* (an
        upper bound).

    By construction ``p_lower <= p_consistent <= p_upper``.

    Approximation notice: ``omega_k`` is the bootstrap estimator rather than a
    HAC kernel estimator (see :func:`_omega`), and the LIL threshold uses
    ``log(log(T))`` with no small-sample adjustment - for T in the low
    hundreds the consistent threshold sits close enough to the lower rule that
    ``p_lower`` and ``p_consistent`` frequently coincide. Note also that
    ``p_upper`` is the *studentised* RC, so it need not equal
    :func:`whites_reality_check`'s p-value exactly; the two agree only when
    ``omega`` is near-constant across models.

    Ex-post diagnostic only - see the module docstring.

    Reference: Hansen, P.R. (2005), "A Test for Superior Predictive Ability",
    Journal of Business & Economic Statistics 23(4), 365-380.
    """
    arr = _as_panel(perf)
    t_obs, n_models = arr.shape
    f_bar = arr.mean(axis=0)

    idx = _boot_indices(t_obs, n_boot, mean_block, seed)
    boot_means = _bootstrap_column_means(arr, idx)
    omega = _omega(arr, boot_means, t_obs)

    z_obs = np.sqrt(t_obs) * f_bar / omega
    best = int(np.argmax(z_obs))
    t_spa = float(max(0.0, z_obs[best]))

    # Hansen's LIL threshold. log(log(T)) is only positive for T > e, which
    # MIN_OBS = 20 guarantees.
    lil = np.sqrt(omega**2 / t_obs * 2.0 * np.log(np.log(t_obs)))
    keep = {
        "lower": f_bar >= 0.0,
        "consistent": f_bar >= -lil,
        "upper": np.ones(n_models, dtype=bool),
    }

    p_values: dict[str, float] = {}
    for rule, mask in keep.items():
        g = np.where(mask, f_bar, 0.0)
        z_boot = np.sqrt(t_obs) * (boot_means - g) / omega
        t_boot = np.maximum(0.0, z_boot.max(axis=1))
        p_values[rule] = float(np.mean(t_boot > t_spa))

    return {
        "statistic": t_spa,
        "p_lower": p_values["lower"],
        "p_consistent": p_values["consistent"],
        "p_upper": p_values["upper"],
        "omega": omega,
        "best_index": best,
        "n_models": int(n_models),
        "n_obs": int(t_obs),
        "n_recentred_consistent": int(keep["consistent"].sum()),
    }


# --------------------------------------------------------------------------- #
# Romano-Wolf stepwise multiple testing
# --------------------------------------------------------------------------- #
def stepwise_multiple_testing(
    perf: Sequence[Sequence[float]] | np.ndarray,
    alpha: float = 0.05,
    n_boot: int = 1000,
    mean_block: float = 10.0,
    seed: int = 0,
    max_steps: int = 50,
) -> dict:
    """Romano & Wolf (2005) StepM: *which* models beat the benchmark, at FWER alpha.

    White's RC and Hansen's SPA answer a single yes/no about the best model.
    StepM answers the more useful question - give me the set of models I may
    claim beat the benchmark, with the probability of making *any* false claim
    held at ``alpha``.

    Algorithm (studentised variant), with ``Z_k = sqrt(T) * f_bar_k / omega_k``:

    1. Let ``S`` = all models, ``R`` = {} (rejected so far).
    2. Bootstrap the max statistic over the *surviving* set only::

           maxZ*_b = max_{k in S} sqrt(T) * (f*_{b,k} - f_bar_k) / omega_k

    3. Critical value ``c = quantile(maxZ*, 1 - alpha)``.
    4. Reject every ``k in S`` with ``Z_k > c``; move them from ``S`` to ``R``.
    5. Stop if nothing new was rejected (or ``S`` is empty); otherwise repeat.

    Recomputing the maximum over the shrinking survivor set is what buys the
    power: once the obvious winners are removed, the null distribution of the
    maximum is that of a smaller family, so the critical value falls and
    marginal winners can still be detected - while the familywise error rate
    stays at ``alpha``.

    The same bootstrap resample indices are reused across steps, as in the
    original; this keeps the step-to-step critical values comparable and is
    also the only way the procedure is affordable.

    Approximation notice: ``omega_k`` is the bootstrap estimator (see
    :func:`_omega`), and studentisation uses a *fixed* ``omega`` computed once
    from the full model set rather than re-estimated on each surviving subset.
    Romano & Wolf's asymptotics do not require re-estimation, but a
    finite-sample implementation that re-estimated could differ slightly.

    Returns ``rejected`` (sorted model indices), ``steps`` (loop iterations
    actually run, including the final one that rejected nothing),
    ``critical_values`` (one per iteration) and ``n_models``.

    Ex-post diagnostic only - see the module docstring.

    Reference: Romano, J.P. & Wolf, M. (2005), "Stepwise Multiple Testing as
    Formalized Data Snooping", Econometrica 73(4), 1237-1282.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    if max_steps < 1:
        raise ValueError("max_steps must be >= 1")

    arr = _as_panel(perf)
    t_obs, n_models = arr.shape
    f_bar = arr.mean(axis=0)

    idx = _boot_indices(t_obs, n_boot, mean_block, seed)
    boot_means = _bootstrap_column_means(arr, idx)
    omega = _omega(arr, boot_means, t_obs)

    z_obs = np.sqrt(t_obs) * f_bar / omega
    z_boot = np.sqrt(t_obs) * (boot_means - f_bar) / omega  # (n_boot, M)

    surviving = np.ones(n_models, dtype=bool)
    rejected: list[int] = []
    critical_values: list[float] = []
    steps = 0

    while steps < max_steps and surviving.any():
        steps += 1
        crit = float(np.quantile(z_boot[:, surviving].max(axis=1), 1.0 - alpha))
        critical_values.append(crit)
        newly = np.where(surviving & (z_obs > crit))[0]
        if newly.size == 0:
            break
        rejected.extend(int(k) for k in newly)
        surviving[newly] = False

    return {
        "rejected": sorted(rejected),
        "steps": steps,
        "critical_values": critical_values,
        "n_models": int(n_models),
        "n_obs": int(t_obs),
        "alpha": float(alpha),
    }


# --------------------------------------------------------------------------- #
# one-call wrapper
# --------------------------------------------------------------------------- #
def snooping_report(
    perf: Sequence[Sequence[float]] | np.ndarray,
    names: Sequence[str] | None = None,
    alpha: float = 0.05,
    n_boot: int = 1000,
    mean_block: float = 10.0,
    seed: int = 0,
    max_steps: int = 50,
) -> dict:
    """Run RC + SPA + StepM on one performance panel and summarise the three.

    Convenience entry point for a screening pipeline: hand it the ``(T, M)``
    panel of performance differentials for every candidate you tried (yes,
    *every* one - the correction is only valid if the panel contains the
    models you discarded as well as the one you kept) and get back all three
    tests plus a one-line ``verdict`` string.

    ``names`` optionally labels the columns; when given it must have length M,
    and the report echoes the winner's name and the names of the StepM
    rejections.

    ``best_index`` / ``best_name`` are SPA's winner, i.e. the argmax of the
    *studentised* statistic. That is not always the argmax of the raw mean
    reported by ``reality_check['best_index']``: a model with a smaller mean
    but a much tighter ``omega`` can outrank it. Both indices are kept in the
    returned sub-dicts so the disagreement is visible rather than silently
    resolved.

    The ``verdict`` wording and its thresholds (SPA's consistent p-value
    against ``alpha``) are a reporting convention of this repo, not a result
    from the literature - read the string as a summary of the numbers, never
    as a fourth test.

    Ex-post diagnostic only - see the module docstring.
    """
    arr = _as_panel(perf)
    n_models = arr.shape[1]
    if names is not None:
        names = list(names)
        if len(names) != n_models:
            raise ValueError(
                f"names has length {len(names)} but perf has {n_models} models"
            )

    rc = whites_reality_check(arr, n_boot=n_boot, mean_block=mean_block, seed=seed)
    spa = hansens_spa(arr, n_boot=n_boot, mean_block=mean_block, seed=seed)
    stepm = stepwise_multiple_testing(
        arr,
        alpha=alpha,
        n_boot=n_boot,
        mean_block=mean_block,
        seed=seed,
        max_steps=max_steps,
    )

    best = int(spa["best_index"])
    best_name = names[best] if names is not None else f"model_{best}"
    rejected_names = [
        names[k] if names is not None else f"model_{k}" for k in stepm["rejected"]
    ]

    n_rej = len(stepm["rejected"])
    if spa["p_consistent"] <= alpha and n_rej > 0:
        verdict = (
            f"SURVIVES: SPA p_consistent={spa['p_consistent']:.4f} <= {alpha}; "
            f"StepM keeps {n_rej}/{n_models} model(s) at FWER {alpha} "
            f"(best: {best_name})."
        )
    elif spa["p_consistent"] <= alpha:
        verdict = (
            f"MARGINAL: SPA rejects the joint null "
            f"(p_consistent={spa['p_consistent']:.4f}) but StepM cannot name a "
            f"single model at FWER {alpha} - the evidence is diffuse, so do "
            f"not claim {best_name} specifically."
        )
    else:
        verdict = (
            f"DATA SNOOPING: best model {best_name} is not significant once "
            f"the {n_models}-model search is accounted for "
            f"(RC p={rc['p_value']:.4f}, "
            f"SPA p_consistent={spa['p_consistent']:.4f} > {alpha})."
        )

    return {
        "reality_check": rc,
        "spa": spa,
        "stepm": stepm,
        "best_index": best,
        "best_name": best_name,
        "rejected_names": rejected_names,
        "n_models": int(n_models),
        "n_obs": int(arr.shape[0]),
        "alpha": float(alpha),
        "verdict": verdict,
    }
