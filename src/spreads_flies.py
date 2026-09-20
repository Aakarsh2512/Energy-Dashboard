"""
Spreads and flies computation for the Energy Trading Dashboard.

Computes:
- Calendar spreads (M1-M2, M1-M3, M1-M6, M1-M12) for WTI, Brent
- Butterfly flies (M1 - 2*M2 + M3, M1 - 2*M6 + M12)
- Inter-product spreads (WTI-Brent, RBOB-WTI, ULSD-WTI, cracks)
- Z-scores vs rolling history for each

Front-month prices from Yahoo (real). Back months from parametric curve model.
"""

import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
from forward_curves import build_curve_for_instrument


# --------------------------------------------------------------------
# Calendar Spreads & Flies (from forward curve)
# --------------------------------------------------------------------

def compute_calendar_spreads_table(market_data: dict, instrument: str = "WTI") -> list:
    """
    Compute calendar spreads with REAL z-scores from settlement history
    for any instrument that has settlement data (Brent, WTI, ULSD, Gasoil).
    Falls back to sigma-estimate for instruments without real data.
    """
    front_data = market_data.get(instrument)
    if not front_data and instrument not in ("Brent", "WTI", "ULSD", "Gasoil"):
        return []

    curve_today = build_curve_for_instrument(instrument, market_data)
    if not curve_today:
        return []

    curve_dict_today = dict(curve_today)

    # Get yesterday's curve from real data if available
    try:
        from settle_data import get_historical_curves, has_real_data
        if has_real_data(instrument):
            hist = get_historical_curves(instrument)
            curve_dict_yest = dict(hist["yesterday"]) if hist and "yesterday" in hist else {}
            real_z_available = True
        else:
            real_z_available = False
            if front_data:
                prev_price = front_data["previous"]
                market_data_yest = dict(market_data)
                market_data_yest[instrument] = {**front_data, "latest": prev_price}
                curve_yest = build_curve_for_instrument(instrument, market_data_yest)
                curve_dict_yest = dict(curve_yest) if curve_yest else {}
            else:
                curve_dict_yest = {}
    except Exception:
        real_z_available = False
        curve_dict_yest = {}

    # Z-score helpers if real data is available
    if real_z_available:
        from settle_data import compute_historical_spread, real_zscore

    spreads = []
    for label, m_a, m_b in [
        ("M1-M2", 1, 2),
        ("M1-M3", 1, 3),
        ("M1-M6", 1, 6),
        ("M1-M12", 1, 12),
    ]:
        if m_a not in curve_dict_today or m_b not in curve_dict_today:
            continue

        value = curve_dict_today[m_a] - curve_dict_today[m_b]
        prev = curve_dict_yest.get(m_a, 0) - curve_dict_yest.get(m_b, 0)
        change = value - prev

        if real_z_available:
            hist_series = compute_historical_spread(instrument, m_a, m_b)
            z = real_zscore(value, hist_series, lookback_days=252)
        else:
            sigma_estimate = abs(value) * 0.15 + 0.05
            z = change / sigma_estimate if sigma_estimate > 0 else 0

        if abs(z) > 2.0:
            status = "EXTREME"
        elif abs(z) > 1.0:
            status = "ELEVATED"
        else:
            status = "NORMAL"

        spreads.append({
            "name": label,
            "value": value,
            "prev_value": prev,
            "change": change,
            "z_score": z,
            "status": status,
        })

    return spreads
def compute_flies(market_data: dict, instrument: str = "WTI") -> list:
    """
    Compute butterfly flies with REAL z-scores for any instrument that has
    settlement data. Falls back to sigma-estimate otherwise.
    """
    front_data = market_data.get(instrument)
    if not front_data and instrument not in ("Brent", "WTI", "ULSD", "Gasoil"):
        return []

    curve_today = build_curve_for_instrument(instrument, market_data)
    if not curve_today:
        return []

    curve_dict_today = dict(curve_today)

    try:
        from settle_data import get_historical_curves, has_real_data
        if has_real_data(instrument):
            hist = get_historical_curves(instrument)
            curve_dict_yest = dict(hist["yesterday"]) if hist and "yesterday" in hist else {}
            real_z_available = True
        else:
            real_z_available = False
            if front_data:
                prev_price = front_data["previous"]
                market_data_yest = dict(market_data)
                market_data_yest[instrument] = {**front_data, "latest": prev_price}
                curve_yest = build_curve_for_instrument(instrument, market_data_yest)
                curve_dict_yest = dict(curve_yest) if curve_yest else {}
            else:
                curve_dict_yest = {}
    except Exception:
        real_z_available = False
        curve_dict_yest = {}

    if real_z_available:
        from settle_data import compute_historical_fly, real_zscore

    flies = []
    for label, a, b, c in [
        ("M1-2M2+M3", 1, 2, 3),
        ("M1-2M3+M6", 1, 3, 6),
        ("M1-2M6+M12", 1, 6, 12),
    ]:
        if not all(m in curve_dict_today for m in [a, b, c]):
            continue

        value = curve_dict_today[a] - 2 * curve_dict_today[b] + curve_dict_today[c]
        prev = curve_dict_yest.get(a, 0) - 2 * curve_dict_yest.get(b, 0) + curve_dict_yest.get(c, 0)
        change = value - prev

        if real_z_available:
            hist_series = compute_historical_fly(instrument, a, b, c)
            z = real_zscore(value, hist_series, lookback_days=252)
        else:
            sigma_estimate = abs(value) * 0.2 + 0.1
            z = change / sigma_estimate if sigma_estimate > 0 else 0

        if abs(z) > 2.0:
            status = "EXTREME"
        elif abs(z) > 1.0:
            status = "ELEVATED"
        else:
            status = "NORMAL"

        if abs(value) < 0.1:
            shape = "Flat"
        elif value > 0:
            shape = "Peak (humped)"
        else:
            shape = "Valley (dipped)"

        flies.append({
            "name": label,
            "value": value,
            "prev_value": prev,
            "change": change,
            "z_score": z,
            "status": status,
            "shape": shape,
        })

    return flies
def compute_interproduct_spreads_table(market_data: dict) -> list:
    """
    Compute inter-product spreads from real prices.
    Returns list of dicts with same structure as calendar spreads.
    """
    spreads = []

    # Helper to compute a spread with z-score
    def add_spread(name, current, previous, sigma_pct=0.1):
        change = current - previous
        sigma = abs(current) * sigma_pct + 0.05
        z = change / sigma if sigma > 0 else 0
        if abs(z) > 2.0:
            status = "EXTREME"
        elif abs(z) > 1.0:
            status = "ELEVATED"
        else:
            status = "NORMAL"
        spreads.append({
            "name": name,
            "value": current,
            "prev_value": previous,
            "change": change,
            "z_score": z,
            "status": status,
        })

    # WTI-Brent
    wti = market_data.get("WTI", {})
    brent = market_data.get("Brent", {})
    if wti and brent:
        add_spread(
            "WTI-Brent",
            wti["latest"] - brent["latest"],
            wti["previous"] - brent["previous"],
        )

    # RBOB-WTI (gasoline crack per gallon basis)
    rbob = market_data.get("RBOB", {})
    if wti and rbob:
        rbob_bbl_now = rbob["latest"] * 42
        rbob_bbl_prev = rbob["previous"] * 42
        add_spread(
            "RBOB-WTI",
            rbob_bbl_now - wti["latest"],
            rbob_bbl_prev - wti["previous"],
        )

    # ULSD-WTI (heating oil crack)
    ulsd = market_data.get("ULSD", {})
    if wti and ulsd:
        ulsd_bbl_now = ulsd["latest"] * 42
        ulsd_bbl_prev = ulsd["previous"] * 42
        add_spread(
            "ULSD-WTI",
            ulsd_bbl_now - wti["latest"],
            ulsd_bbl_prev - wti["previous"],
        )

    # 3-2-1 Crack
    if wti and rbob and ulsd:
        crack_now = ((2 * rbob["latest"] + 1 * ulsd["latest"]) * 42 - 3 * wti["latest"]) / 3
        crack_prev = ((2 * rbob["previous"] + 1 * ulsd["previous"]) * 42 - 3 * wti["previous"]) / 3
        add_spread("3-2-1 Crack", crack_now, crack_prev)

    # 5-3-2 Crack (5 WTI → 3 gasoline + 2 distillate)
    if wti and rbob and ulsd:
        crack_532_now = ((3 * rbob["latest"] + 2 * ulsd["latest"]) * 42 - 5 * wti["latest"]) / 5
        crack_532_prev = ((3 * rbob["previous"] + 2 * ulsd["previous"]) * 42 - 5 * wti["previous"]) / 5
        add_spread("5-3-2 Crack", crack_532_now, crack_532_prev)

    # NatGas-Crude correlation (Henry Hub vs WTI in MMBtu equivalent)
    hh = market_data.get("Henry Hub", {})
    if wti and hh:
        # Crude in $/MMBtu: WTI / 5.8 (energy content conversion)
        wti_mmbtu_now = wti["latest"] / 5.8
        wti_mmbtu_prev = wti["previous"] / 5.8
        add_spread(
            "HH-WTI ($/MMBtu)",
            hh["latest"] - wti_mmbtu_now,
            hh["previous"] - wti_mmbtu_prev,
        )

    return spreads
@st.cache_data(ttl=3600)
def get_inter_product_history(days: int = 60) -> dict:
    """
    Fetch 60 days of history for WTI, Brent, RBOB, ULSD, HH.
    Returns dict of {symbol: [list of closes]} for sparkline rendering.
    """
    import yfinance as yf

    symbols = {
        "WTI": "CL=F",
        "Brent": "BZ=F",
        "RBOB": "RB=F",
        "ULSD": "HO=F",
        "Henry Hub": "NG=F",
    }

    out = {}
    try:
        tickers = list(symbols.values())
        data = yf.download(tickers, period=f"{days+10}d", interval="1d", progress=False, auto_adjust=True)

        if isinstance(data.columns, pd.MultiIndex):
            closes = data["Close"]
        else:
            closes = data[["Close"]]

        ticker_to_name = {v: k for k, v in symbols.items()}
        closes = closes.rename(columns=ticker_to_name)

        for name in symbols:
            if name in closes.columns:
                series = closes[name].dropna().tail(days)
                out[name] = series.tolist()
    except Exception as e:
        print(f"[spreads_flies] inter-product history error: {e}")

    return out


def compute_inter_product_sparklines(days: int = 60) -> dict:
    """
    Compute historical time series for each inter-product spread.
    Returns dict of {spread_name: [list of values]}
    """
    hist = get_inter_product_history(days=days)
    if not hist:
        return {}

    out = {}
    n = min(len(s) for s in hist.values()) if hist else 0
    if n < 5:
        return {}

    # Truncate all series to same length
    aligned = {k: v[-n:] for k, v in hist.items()}

    wti = aligned.get("WTI", [])
    brent = aligned.get("Brent", [])
    rbob = aligned.get("RBOB", [])
    ulsd = aligned.get("ULSD", [])
    hh = aligned.get("Henry Hub", [])

    if wti and brent and len(wti) == len(brent):
        out["WTI-Brent"] = [w - b for w, b in zip(wti, brent)]

    if wti and rbob and len(wti) == len(rbob):
        out["RBOB-WTI"] = [(r * 42) - w for w, r in zip(wti, rbob)]

    if wti and ulsd and len(wti) == len(ulsd):
        out["ULSD-WTI"] = [(u * 42) - w for w, u in zip(wti, ulsd)]

    if wti and rbob and ulsd and len(wti) == len(rbob) == len(ulsd):
        out["3-2-1 Crack"] = [
            ((2 * r + 1 * u) * 42 - 3 * w) / 3
            for w, r, u in zip(wti, rbob, ulsd)
        ]
        out["5-3-2 Crack"] = [
            ((3 * r + 2 * u) * 42 - 5 * w) / 5
            for w, r, u in zip(wti, rbob, ulsd)
        ]

    if wti and hh and len(wti) == len(hh):
        out["HH-WTI ($/MMBtu)"] = [h - (w / 5.8) for w, h in zip(wti, hh)]

    return out