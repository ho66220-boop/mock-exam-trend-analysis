"""Small statistics helpers for reliability gating and confidence intervals.

Used across the report scripts so that (a) small subgroups are visibly flagged
rather than presented with equal weight, and (b) headline means carry a
bootstrap 95% CI instead of looking like exact facts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Below this per-cell sample size, a number is treated as unreliable and flagged.
MIN_RELIABLE_N = 10


def reliability_tag(n: int) -> str:
    """Return an inline marker for small cells (empty string when reliable)."""
    return "" if int(n) >= MIN_RELIABLE_N else f" ⚠️소표본(n<{MIN_RELIABLE_N}, 참고불가)"


def bootstrap_ci(
    values, confidence: float = 0.95, n_boot: int = 2000, seed: int = 42
) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean. NaN-safe. (nan, nan) if too few points."""
    arr = pd.Series(values).dropna().to_numpy(dtype=float)
    if arr.size == 0:
        return (np.nan, np.nan)
    if arr.size < 3:
        return (float(arr.mean()), float(arr.mean()))
    rng = np.random.default_rng(seed)
    boot_means = rng.choice(arr, size=(n_boot, arr.size), replace=True).mean(axis=1)
    lo = float(np.percentile(boot_means, (1 - confidence) / 2 * 100))
    hi = float(np.percentile(boot_means, (1 + confidence) / 2 * 100))
    return (lo, hi)


def fmt_mean_ci(values, decimals: int = 1) -> str:
    """Format 'mean [lo–hi]' with a bootstrap 95% CI."""
    arr = pd.Series(values).dropna().to_numpy(dtype=float)
    if arr.size == 0:
        return "n/a"
    mean = arr.mean()
    lo, hi = bootstrap_ci(arr)
    return f"{mean:.{decimals}f} [{lo:.{decimals}f}–{hi:.{decimals}f}]"
