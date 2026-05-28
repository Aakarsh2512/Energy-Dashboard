"""
Forward curve construction for the Energy Trading Dashboard.

Builds synthetic forward curves anchored to live front-month prices.
The curve shape is parameterised so it stays realistic even though we
don't have full back-month data from the free feed.
"""

import numpy as np
import pandas as pd
from typing import Optional


# ============================================================
# CURVE MODEL
# ============================================================

CURVE_PARAMS = {
    "WTI": {
        "contango_strength": 0.3,
        "long_term_anchor": 72.0,
        "max_tenor": 24,
    },
    "Brent": {
        "contango_strength": 0.3,
        "long_term_anchor": 76.0,
        "max_tenor": 24,
    },
    "Henry Hub": {
        "contango_strength": 0.6,
        "long_term_anchor": 3.50,
        "max_tenor": 24,
    },
}


def model_forward_curve(front_month_price: float,
                        contango_strength: float = 0.3,
                        long_term_anchor: float = 72.0,
                        max_tenor: int = 24) -> list:
    """
    Build a synthetic forward curve from the front-month price.
    Returns list of (tenor_in_months, price) tuples.
    """
    curve = []
    for m in range(1, max_tenor + 1):
        decay = 1 - np.exp(-contango_strength * (m - 1) / 6)
        price = front_month_price + (long_term_anchor - front_month_price) * decay
        curve.append((m, round(price, 2)))
    return curve


def build_curve_for_instrument(name: str, market_data: dict) -> Optional[list]:
    """Build a forward curve for a given instrument from market_data."""
    if name not in CURVE_PARAMS:
        return None

    instrument = market_data.get(name)
    if instrument is None:
        return None

    front = instrument["latest"]
    params = CURVE_PARAMS[name]

    return model_forward_curve(
        front_month_price=front,
        contango_strength=params["contango_strength"],
        long_term_anchor=params["long_term_anchor"],
        max_tenor=params["max_tenor"],
    )


def build_curves_with_history(name: str, market_data: dict) -> Optional[dict]:
    """
    Build today's curve plus prior overlays using historical front-month prices.
    Returns dict like {"today": curve, "yesterday": curve, "last_week": curve}
    """
    if name not in CURVE_PARAMS:
        return None

    instrument = market_data.get(name)
    if instrument is None or not instrument.get("history"):
        return None

    history = instrument["history"]
    params = CURVE_PARAMS[name]

    curves = {}

    # Today's curve
    today_front = history[-1]
    curves["today"] = model_forward_curve(today_front, **params)

    # Yesterday
    if len(history) >= 2:
        yest_front = history[-2]
        curves["yesterday"] = model_forward_curve(yest_front, **params)

    # Last week (5 trading days ago)
    if len(history) >= 6:
        lw_front = history[-6]
        curves["last_week"] = model_forward_curve(lw_front, **params)

    return curves


# ============================================================
# CALENDAR SPREADS
# ============================================================

def compute_calendar_spreads(curve: list) -> dict:
    """Compute key calendar spreads from a forward curve."""
    if not curve:
        return {}

    curve_dict = dict(curve)
    spreads = {}

    pairs = [(1, 2), (1, 6), (1, 12), (6, 12)]
    for m1, m2 in pairs:
        if m1 in curve_dict and m2 in curve_dict:
            key = f"M{m1}-M{m2}"
            spreads[key] = round(curve_dict[m1] - curve_dict[m2], 2)

    return spreads


def classify_curve_structure(curve: list) -> str:
    """Return CONTANGO, BACKWARDATION, or FLAT based on curve shape."""
    if not curve or len(curve) < 2:
        return "—"

    front = curve[0][1]
    back = curve[-1][1]
    diff = back - front

    # Use 1% as the threshold for meaningful shape
    if abs(diff / front) < 0.01:
        return "FLAT"
    return "CONTANGO" if diff > 0 else "BACKWARDATION"


# ============================================================
# INTER-PRODUCT SPREADS
# ============================================================

def compute_inter_product_spreads(market_data: dict) -> dict:
    """Compute commonly-traded inter-product spreads."""
    spreads = {}

    # WTI-Brent
    if market_data.get("WTI") and market_data.get("Brent"):
        wti = market_data["WTI"]["latest"]
        brent = market_data["Brent"]["latest"]
        wti_prev = market_data["WTI"]["previous"]
        brent_prev = market_data["Brent"]["previous"]
        spreads["WTI-Brent"] = {
            "value": round(wti - brent, 2),
            "previous": round(wti_prev - brent_prev, 2),
            "unit": "$/bbl",
        }

    # 3-2-1 Crack:  3 barrels crude -> 2 barrels gasoline + 1 barrel ULSD
    # Standard formula: (2 * RBOB + 1 * ULSD) - 3 * WTI
    # RBOB and ULSD are in $/gal, convert to $/bbl (42 gal/bbl), then take avg per barrel
    if market_data.get("WTI") and market_data.get("RBOB") and market_data.get("ULSD"):
        wti = market_data["WTI"]["latest"]
        rbob_per_bbl = market_data["RBOB"]["latest"] * 42
        ulsd_per_bbl = market_data["ULSD"]["latest"] * 42

        crack = ((2 * rbob_per_bbl) + (1 * ulsd_per_bbl)) / 3 - wti

        wti_prev = market_data["WTI"]["previous"]
        rbob_prev_bbl = market_data["RBOB"]["previous"] * 42
        ulsd_prev_bbl = market_data["ULSD"]["previous"] * 42
        crack_prev = ((2 * rbob_prev_bbl) + (1 * ulsd_prev_bbl)) / 3 - wti_prev

        spreads["3-2-1 Crack"] = {
            "value": round(crack, 2),
            "previous": round(crack_prev, 2),
            "unit": "$/bbl",
        }

    return spreads


def compute_spread_zscore(current: float, history: list) -> float:
    """Compute z-score for a spread given its historical values."""
    if not history or len(history) < 20:
        return 0.0
    arr = np.array(history[-20:])
    if arr.std() == 0:
        return 0.0
    return float((current - arr.mean()) / arr.std())