"""
Support & Resistance level detector for spread/fly time series.

Finds historically significant price levels by:
  1. Detecting persistent local extrema
  2. Clustering nearby extrema into "levels"
  3. Counting touches and requiring multi-year persistence
  4. Classifying as support (below current) or resistance (above current)

Used downstream by opportunity_ranker.py — a spread sitting near a multi-touch
S/R level gets a stronger trade signal.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from settle_data import load_settlement_curves, compute_historical_spread, compute_historical_fly


# ============================================================
# CORE: Detect levels in a time series
# ============================================================

def detect_levels(
    series: pd.Series,
    window: int = 20,
    cluster_tolerance: float = None,
    min_touches: int = 3,
    min_years_spread: float = 1.5,
    touch_tolerance: float = None,
) -> list:
    """
    Detect significant support/resistance levels in a time series.

    Args:
        series: time-indexed pd.Series (e.g., daily spread values)
        window: ±N days for local extrema detection (20 = 1 month)
        cluster_tolerance: how close two extrema must be to belong to same level.
                           If None, auto-set to ~5% of series std.
        min_touches: minimum number of times a level must be tested
        min_years_spread: extrema in a level must span at least this many years
        touch_tolerance: how close a price must come to count as a "touch".
                         If None, auto-set to ~3% of series std.

    Returns:
        list of dicts:
        [
            {
                "level": 2.45,
                "type": "resistance",       # set later based on current value
                "touches": 5,
                "first_touched": Timestamp,
                "last_touched": Timestamp,
                "years_spread": 3.2,
                "strength": 0.78,           # 0-1 composite score
                "extrema_type": "max",      # max-cluster or min-cluster
            },
            ...
        ]
    """
    if series.empty or len(series) < window * 2:
        return []

    series = series.dropna()
    if series.empty:
        return []

    # Auto-set tolerances if not specified
    series_std = float(series.std())
    if cluster_tolerance is None:
        cluster_tolerance = series_std * 0.15
    if touch_tolerance is None:
        touch_tolerance = series_std * 0.10

    # Find local extrema
    extrema = _find_local_extrema(series, window)

    # Separate into maxima and minima
    maxima = [(d, v) for d, v, kind in extrema if kind == "max"]
    minima = [(d, v) for d, v, kind in extrema if kind == "min"]

    # Cluster each
    max_clusters = _cluster_extrema(maxima, cluster_tolerance, "max")
    min_clusters = _cluster_extrema(minima, cluster_tolerance, "min")

    all_clusters = max_clusters + min_clusters

    # Filter: must have enough touches and span enough years
    significant = []
    for c in all_clusters:
        # Count touches: days where series came within touch_tolerance of level
        touches = ((series - c["level"]).abs() <= touch_tolerance).sum()

        if touches < min_touches:
            continue

        years_spread = (c["last_touched_in_series"] - c["first_extreme"]).days / 365.25
        if years_spread < min_years_spread:
            continue

        # Strength score: log(touches) × recency bias
        # Recency: more recent touches weighted higher
        max_date = series.index[-1]
        days_since_last = (max_date - c["last_touched_in_series"]).days
        recency = max(0.3, 1.0 - days_since_last / 730)  # decay over 2 years

        strength = (np.log1p(touches) / np.log1p(20)) * recency  # normalize to [0, 1]

        significant.append({
            "level": float(c["level"]),
            "touches": int(touches),
            "first_touched": c["first_extreme"],
            "last_touched": c["last_touched_in_series"],
            "years_spread": float(years_spread),
            "strength": float(min(1.0, strength)),
            "extrema_type": c["kind"],
        })

    # Sort by level value descending
    significant.sort(key=lambda x: -x["level"])
    return significant


def _find_local_extrema(series: pd.Series, window: int):
    """Find local maxima and minima using ±window day comparison."""
    arr = series.values
    dates = series.index

    extrema = []
    for i in range(window, len(arr) - window):
        center = arr[i]
        left = arr[i - window:i]
        right = arr[i + 1:i + window + 1]

        if center > left.max() and center > right.max():
            extrema.append((dates[i], float(center), "max"))
        elif center < left.min() and center < right.min():
            extrema.append((dates[i], float(center), "min"))

    return extrema


def _cluster_extrema(extrema: list, tolerance: float, kind: str) -> list:
    """
    Group extrema whose values are within `tolerance` of each other.
    Returns list of cluster dicts.
    """
    if not extrema:
        return []

    # Sort by value
    sorted_ext = sorted(extrema, key=lambda x: x[1])

    clusters = []
    current = [sorted_ext[0]]

    for ext in sorted_ext[1:]:
        if ext[1] - current[-1][1] <= tolerance:
            current.append(ext)
        else:
            if len(current) >= 2:
                clusters.append(_summarize_cluster(current, kind))
            current = [ext]

    if len(current) >= 2:
        clusters.append(_summarize_cluster(current, kind))

    return clusters


def _summarize_cluster(extrema: list, kind: str) -> dict:
    """Build a cluster summary dict."""
    dates = [e[0] for e in extrema]
    values = [e[1] for e in extrema]

    return {
        "level": float(np.mean(values)),  # cluster center
        "first_extreme": min(dates),
        "last_touched_in_series": max(dates),
        "kind": kind,
    }


# ============================================================
# CLASSIFY: support vs resistance based on current value
# ============================================================

def classify_levels(levels: list, current_value: float) -> list:
    """
    Given a list of detected levels and the current series value,
    classify each as 'support' (below current) or 'resistance' (above current).
    """
    classified = []
    for lvl in levels:
        lvl = dict(lvl)
        lvl["type"] = "resistance" if lvl["level"] > current_value else "support"
        lvl["distance"] = abs(lvl["level"] - current_value)
        lvl["distance_pct"] = (
            abs(lvl["level"] - current_value) / max(abs(current_value), 0.01) * 100
        )
        classified.append(lvl)

    classified.sort(key=lambda x: x["distance"])
    return classified


# ============================================================
# CONVENIENCE: detect for a specific spread or fly
# ============================================================

def detect_spread_levels(instrument: str, m_a: int, m_b: int, **kwargs) -> dict:
    """Detect S/R levels for a calendar spread (e.g., Brent M1-M2)."""
    series = compute_historical_spread(instrument, m_a, m_b)
    if series.empty:
        return {"levels": [], "current_value": None, "name": f"{instrument} M{m_a}-M{m_b}"}

    levels = detect_levels(series, **kwargs)
    current = float(series.iloc[-1])
    classified = classify_levels(levels, current)

    return {
        "name": f"{instrument} M{m_a}-M{m_b}",
        "instrument": instrument,
        "current_value": current,
        "current_date": series.index[-1],
        "levels": classified,
        "supports": [l for l in classified if l["type"] == "support"][:5],
        "resistances": [l for l in classified if l["type"] == "resistance"][:5],
    }


def detect_fly_levels(instrument: str, m_a: int, m_b: int, m_c: int, **kwargs) -> dict:
    """Detect S/R levels for a butterfly fly (e.g., Brent M1-2M2+M3)."""
    series = compute_historical_fly(instrument, m_a, m_b, m_c)
    if series.empty:
        return {
            "levels": [],
            "current_value": None,
            "name": f"{instrument} M{m_a}-2M{m_b}+M{m_c}",
        }

    levels = detect_levels(series, **kwargs)
    current = float(series.iloc[-1])
    classified = classify_levels(levels, current)

    return {
        "name": f"{instrument} M{m_a}-2M{m_b}+M{m_c}",
        "instrument": instrument,
        "current_value": current,
        "current_date": series.index[-1],
        "levels": classified,
        "supports": [l for l in classified if l["type"] == "support"][:5],
        "resistances": [l for l in classified if l["type"] == "resistance"][:5],
    }


# ============================================================
# BATCH: detect for all major spreads & flies
# ============================================================

def detect_all_levels() -> dict:
    """
    Detect S/R levels for the full universe of spreads and flies.
    Returns dict keyed by series name.
    """
    universe = {}

    for instrument in ["Brent", "WTI", "ULSD", "Gasoil"]:
        # Calendar spreads
        for m_a, m_b in [(1, 2), (1, 3), (1, 6), (1, 12)]:
            key = f"{instrument}_M{m_a}_M{m_b}"
            try:
                result = detect_spread_levels(instrument, m_a, m_b)
                if result.get("current_value") is not None:
                    universe[key] = result
                    print(f"  {key:25s}: current {result['current_value']:+7.2f}, "
                          f"{len(result['supports'])}S / {len(result['resistances'])}R")
            except Exception as e:
                print(f"  {key}: error {e}")

        # Flies
        for m_a, m_b, m_c in [(1, 2, 3), (1, 3, 6), (1, 6, 12)]:
            key = f"{instrument}_M{m_a}_M{m_b}_M{m_c}_fly"
            try:
                result = detect_fly_levels(instrument, m_a, m_b, m_c)
                if result.get("current_value") is not None:
                    universe[key] = result
                    print(f"  {key:25s}: current {result['current_value']:+7.2f}, "
                          f"{len(result['supports'])}S / {len(result['resistances'])}R")
            except Exception as e:
                print(f"  {key}: error {e}")

    return universe


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Support & Resistance Detection — Full Universe")
    print("=" * 60)
    all_results = detect_all_levels()
    print(f"\nDetected S/R for {len(all_results)} series")