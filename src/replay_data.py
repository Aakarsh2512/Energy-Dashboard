"""
Historical data access for Replay Mode.

Given any past date, return the dashboard state as it was on that date:
- Brent forward curve (real ICE settlement)
- Brent calendar spreads + flies with z-scores against history available on that date
- WTI front month + inter-product spreads (real Yahoo daily)
- Macro snapshot
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

from settle_data import load_settlement_curves, has_real_data


# Historical event shortcuts — curated significant dates in oil markets
EVENT_SHORTCUTS = [
    {"label": "Russia invades Ukraine", "date": "2022-02-24",
     "note": "Brent spiked above $100, energy security panic"},
    {"label": "OPEC+ surprise cut (Apr 2023)", "date": "2023-04-03",
     "note": "Saudi led 1.16mb/d voluntary cut, Brent +6% on the day"},
    {"label": "Israel-Hamas war start", "date": "2023-10-09",
     "note": "Geopolitical risk premium returned, Brent +4%"},
    {"label": "Iran-Israel direct strikes", "date": "2024-04-14",
     "note": "First direct Iran attack, risk premium reset"},
    {"label": "OPEC+ production hike (Mar 2025)", "date": "2025-03-05",
     "note": "Unexpected return of supply, Brent dropped 4%"},
    {"label": "Banking stress (Mar 2023)", "date": "2023-03-15",
     "note": "SVB / Credit Suisse wobble, oil sold off on demand fears"},
    {"label": "COVID demand crash", "date": "2020-04-20",
     "note": "WTI went negative for the first time in history"},
]


# Macro symbols for Yahoo historical lookup
MACRO_SYMBOLS = {
    "WTI": "CL=F",
    "Brent": "BZ=F",
    "Henry Hub": "NG=F",
    "RBOB": "RB=F",
    "ULSD": "HO=F",
    "DXY": "DX-Y.NYB",
    "S&P 500": "^GSPC",
    "Gold": "GC=F",
    "VIX": "^VIX",
}


@st.cache_data(ttl=86400)  # cache for 24h — historical data is stable
def fetch_macro_history(start: str = "2015-01-01") -> pd.DataFrame:
    """
    Fetch daily closes for all macro symbols from start date.
    Returns DataFrame indexed by date with one column per instrument.
    """
    try:
        tickers = list(MACRO_SYMBOLS.values())
        data = yf.download(
            tickers, start=start,
            interval="1d", progress=False, auto_adjust=True,
        )
        if isinstance(data.columns, pd.MultiIndex):
            closes = data["Close"]
        else:
            closes = data[["Close"]]
        ticker_to_name = {v: k for k, v in MACRO_SYMBOLS.items()}
        closes = closes.rename(columns=ticker_to_name)
        return closes.dropna(how="all")
    except Exception as e:
        print(f"[replay_data] macro history error: {e}")
        return pd.DataFrame()


def get_available_dates(instrument: str = "Brent") -> list:
    """Return sorted list of dates with complete settlement curve data."""
    df = load_settlement_curves(instrument)
    if df.empty:
        return []
    return df.index.tolist()


def get_common_available_dates(instruments: list = None) -> list:
    """Return dates available across ALL given instruments (intersection)."""
    if instruments is None:
        instruments = ["Brent", "WTI"]

    common = None
    for inst in instruments:
        df = load_settlement_curves(inst)
        if df.empty:
            continue
        dates = set(df.index.tolist())
        common = dates if common is None else common & dates

    if common is None:
        return []
    return sorted(list(common))

def get_replay_snapshot(target_date, instrument: str = "Brent") -> dict:
    """
    Build a complete snapshot of dashboard data as of target_date.
    Works for Brent or WTI (any instrument with settlement data).
    """
    target = pd.to_datetime(target_date)
    snapshot = {
        "date": target,
        "available": False,
        "instrument": instrument,
    }

    # Settlement curve for selected instrument
    df = load_settlement_curves(instrument)
    if df.empty:
        return snapshot

    # Find nearest date <= target
    valid_dates = df.index[df.index <= target]
    if len(valid_dates) == 0:
        return snapshot

    actual_date = valid_dates[-1]
    snapshot["date"] = actual_date
    snapshot["available"] = True

    row = df.loc[actual_date]
    curve = []
    for col in df.columns:
        tenor = int(col[1:])
        if pd.notna(row[col]):
            curve.append((tenor, float(row[col])))
    snapshot["curve"] = curve

    # Prior curves for overlay
    snapshot["curve_prior"] = {}
    end_loc = df.index.get_loc(actual_date)
    for label, days_back in [("yesterday", 1), ("last_week", 5), ("last_month", 21)]:
        if end_loc < days_back:
            continue
        prior_row = df.iloc[end_loc - days_back]
        prior_curve = []
        for col in df.columns:
            tenor = int(col[1:])
            if pd.notna(prior_row[col]):
                prior_curve.append((tenor, float(prior_row[col])))
        snapshot["curve_prior"][label] = prior_curve

    # Calendar spreads + flies with z-scores
    snapshot["calendar_spreads"] = _compute_historical_spreads_at_date(df, actual_date)
    snapshot["flies"] = _compute_historical_flies_at_date(df, actual_date)

    # Macro snapshot from Yahoo
    snapshot["macro"] = _get_macro_snapshot(actual_date)

    # Inter-product spreads
    snapshot["inter_product"] = _compute_inter_product_at_date(snapshot["macro"])

    # Backward compat: keep brent_curve key alive so old code doesn't break
    snapshot["brent_curve"] = curve
    snapshot["brent_curve_prior"] = snapshot["curve_prior"]

    return snapshot
def _compute_historical_spreads_at_date(brent_df: pd.DataFrame, date) -> list:
    """Compute calendar spreads as of date with z-score vs trailing year."""
    spreads = []

    # Get history ending at date
    history = brent_df[brent_df.index <= date]
    if len(history) < 30:
        return spreads

    current_row = history.iloc[-1]

    # Trailing 252 days for z-score baseline
    baseline = history.tail(252)

    for label, m_a, m_b in [
        ("M1-M2", 1, 2),
        ("M1-M3", 1, 3),
        ("M1-M6", 1, 6),
        ("M1-M12", 1, 12),
    ]:
        col_a = f"M{m_a}"
        col_b = f"M{m_b}"
        if col_a not in current_row.index or col_b not in current_row.index:
            continue
        if pd.isna(current_row[col_a]) or pd.isna(current_row[col_b]):
            continue

        value = float(current_row[col_a] - current_row[col_b])

        # Historical spread series for z-score
        spread_series = (baseline[col_a] - baseline[col_b]).dropna()
        if len(spread_series) < 30 or spread_series.std() == 0:
            z = 0.0
        else:
            z = (value - spread_series.mean()) / spread_series.std()

        # Previous day's spread for change
        if len(history) >= 2:
            prev_row = history.iloc[-2]
            prev_value = float(prev_row[col_a] - prev_row[col_b])
            change = value - prev_value
        else:
            change = 0.0

        if abs(z) > 2.0:
            status = "EXTREME"
        elif abs(z) > 1.0:
            status = "ELEVATED"
        else:
            status = "NORMAL"

        spreads.append({
            "name": label,
            "value": value,
            "change": change,
            "z_score": float(z),
            "status": status,
        })

    return spreads


def _compute_historical_flies_at_date(brent_df: pd.DataFrame, date) -> list:
    """Compute butterfly flies as of date with z-score."""
    flies = []
    history = brent_df[brent_df.index <= date]
    if len(history) < 30:
        return flies

    current_row = history.iloc[-1]
    baseline = history.tail(252)

    for label, a, b, c in [
        ("M1-2M2+M3", 1, 2, 3),
        ("M1-2M3+M6", 1, 3, 6),
        ("M1-2M6+M12", 1, 6, 12),
    ]:
        cols = [f"M{a}", f"M{b}", f"M{c}"]
        if not all(col in current_row.index for col in cols):
            continue
        if any(pd.isna(current_row[col]) for col in cols):
            continue

        value = float(current_row[cols[0]] - 2 * current_row[cols[1]] + current_row[cols[2]])

        fly_series = (baseline[cols[0]] - 2 * baseline[cols[1]] + baseline[cols[2]]).dropna()
        if len(fly_series) < 30 or fly_series.std() == 0:
            z = 0.0
        else:
            z = (value - fly_series.mean()) / fly_series.std()

        if len(history) >= 2:
            prev_row = history.iloc[-2]
            prev_value = float(prev_row[cols[0]] - 2 * prev_row[cols[1]] + prev_row[cols[2]])
            change = value - prev_value
        else:
            change = 0.0

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
            "change": change,
            "z_score": float(z),
            "status": status,
            "shape": shape,
        })

    return flies


def _get_macro_snapshot(target_date) -> dict:
    """Return macro instrument prices as of date (from Yahoo history)."""
    target = pd.to_datetime(target_date)
    history = fetch_macro_history(start="2015-01-01")
    if history.empty:
        return {}

    # tz-naive comparison
    if history.index.tz is not None:
        history.index = history.index.tz_localize(None)
    if hasattr(target, "tz_localize") and target.tz is not None:
        target = target.tz_localize(None)

    valid = history.index[history.index <= target]
    if len(valid) == 0:
        return {}

    actual = valid[-1]
    row = history.loc[actual]

    # Previous day for change
    prior_idx = history.index[history.index < actual]
    prev_row = history.loc[prior_idx[-1]] if len(prior_idx) > 0 else row

    snapshot = {}
    for name in MACRO_SYMBOLS:
        if name in row.index and pd.notna(row[name]):
            latest = float(row[name])
            previous = float(prev_row[name]) if name in prev_row.index and pd.notna(prev_row[name]) else latest
            change = latest - previous
            if change > 0:
                direction = "up"
            elif change < 0:
                direction = "down"
            else:
                direction = "neutral"
            snapshot[name] = {
                "latest": latest,
                "previous": previous,
                "change": change,
                "direction": direction,
            }

    snapshot["_as_of"] = actual
    return snapshot


def _compute_inter_product_at_date(macro: dict) -> list:
    """Compute inter-product spreads from macro snapshot."""
    out = []
    if not macro:
        return out

    def make(name, current, previous):
        change = current - previous
        # Light z-score estimate (no history fetched for these in replay)
        sigma = abs(current) * 0.1 + 0.05
        z = change / sigma if sigma > 0 else 0
        if abs(z) > 2.0:
            status = "EXTREME"
        elif abs(z) > 1.0:
            status = "ELEVATED"
        else:
            status = "NORMAL"
        out.append({
            "name": name,
            "value": current,
            "change": change,
            "z_score": z,
            "status": status,
        })

    wti = macro.get("WTI")
    brent = macro.get("Brent")
    rbob = macro.get("RBOB")
    ulsd = macro.get("ULSD")
    hh = macro.get("Henry Hub")

    if wti and brent:
        make("WTI-Brent",
             wti["latest"] - brent["latest"],
             wti["previous"] - brent["previous"])

    if wti and rbob:
        make("RBOB-WTI",
             rbob["latest"] * 42 - wti["latest"],
             rbob["previous"] * 42 - wti["previous"])

    if wti and ulsd:
        make("ULSD-WTI",
             ulsd["latest"] * 42 - wti["latest"],
             ulsd["previous"] * 42 - wti["previous"])

    if wti and rbob and ulsd:
        crack_now = ((2 * rbob["latest"] + ulsd["latest"]) * 42 - 3 * wti["latest"]) / 3
        crack_prev = ((2 * rbob["previous"] + ulsd["previous"]) * 42 - 3 * wti["previous"]) / 3
        make("3-2-1 Crack", crack_now, crack_prev)

    if wti and hh:
        make("HH-WTI ($/MMBtu)",
             hh["latest"] - wti["latest"] / 5.8,
             hh["previous"] - wti["previous"] / 5.8)

    return out