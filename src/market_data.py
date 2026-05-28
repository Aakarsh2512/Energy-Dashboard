"""
Market data fetching for the Energy Trading Dashboard.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from typing import Optional

# ============================================================
# CONFIGURATION
# ============================================================

INSTRUMENTS = {
    "WTI":       {"ticker": "CL=F",     "unit": "$/bbl"},
    "Brent":     {"ticker": "BZ=F",     "unit": "$/bbl"},
    "Henry Hub": {"ticker": "NG=F",     "unit": "$/MMBtu"},
    "RBOB":      {"ticker": "RB=F",     "unit": "$/gal"},
    "ULSD":      {"ticker": "HO=F",     "unit": "$/gal"},
    "DXY":       {"ticker": "DX-Y.NYB", "unit": ""},
    "Gold":      {"ticker": "GC=F",     "unit": "$/oz"},
    "Copper":    {"ticker": "HG=F",     "unit": "$/lb"},
    "S&P 500":   {"ticker": "^GSPC",    "unit": ""},
    "VIX":       {"ticker": "^VIX",     "unit": ""},
}


# ============================================================
# FETCH FUNCTION
# ============================================================

def fetch_market_data(lookback_days: int = 30) -> dict:
    """
    Fetch latest prices for all configured instruments.
    Returns None for any instrument that fails — does not silently use stale data.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days + 10)

    result = {}

    # Fetch each ticker individually using Ticker().history() which is more reliable
    # than batch yf.download for current prices
    for name, info in INSTRUMENTS.items():
        ticker_str = info["ticker"]

        try:
            ticker = yf.Ticker(ticker_str)
            series = ticker.history(
                start=start_date,
                end=end_date,
                interval="1d",
                auto_adjust=True,
            )["Close"].dropna()

            if len(series) < 2:
                print(f"[market_data] {name} ({ticker_str}): insufficient data")
                result[name] = None
                continue

            latest = float(series.iloc[-1])
            previous = float(series.iloc[-2])
            change = latest - previous
            change_pct = (change / previous) * 100 if previous != 0 else 0

            if change > 0.001:
                direction = "up"
            elif change < -0.001:
                direction = "down"
            else:
                direction = "neutral"

            # Get the timestamp of the latest data point
            latest_ts = series.index[-1]

            result[name] = {
                "ticker": ticker_str,
                "latest": round(latest, 2),
                "previous": round(previous, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "direction": direction,
                "unit": info["unit"],
                "history": series.tolist(),
                "timestamps": [str(ts) for ts in series.index],
                "latest_timestamp": str(latest_ts),
                "fetched_at": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"[market_data] {name} ({ticker_str}): error - {e}")
            result[name] = None

        # Small delay between requests to avoid rate limiting
        time.sleep(0.15)

    return result


def add_derived_metrics(data: dict) -> dict:
    """Add computed metrics like WTI-Brent spread."""
    if data.get("WTI") and data.get("Brent"):
        wti = data["WTI"]
        brent = data["Brent"]

        spread_latest = round(wti["latest"] - brent["latest"], 2)
        spread_prev = round(wti["previous"] - brent["previous"], 2)
        spread_change = round(spread_latest - spread_prev, 2)

        if spread_change > 0.001:
            direction = "up"
        elif spread_change < -0.001:
            direction = "down"
        else:
            direction = "neutral"

        data["WTI-Brent"] = {
            "ticker": "derived",
            "latest": spread_latest,
            "previous": spread_prev,
            "change": spread_change,
            "change_pct": 0,
            "direction": direction,
            "unit": "$/bbl",
            "history": [],
            "timestamps": [],
            "latest_timestamp": wti.get("latest_timestamp", ""),
            "fetched_at": datetime.now().isoformat(),
        }

    return data


def format_value(value: Optional[float], decimals: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}"


def format_change(change: Optional[float], decimals: int = 2) -> str:
    if change is None:
        return ""
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.{decimals}f}"


# ============================================================
# Z-SCORE & SPARKLINE HELPERS
# ============================================================

def compute_zscore(history: list, window: int = 20) -> float:
    if not history or len(history) < window + 1:
        return 0.0

    series = np.array(history[-(window + 1):])
    current = series[-1]
    window_data = series[:-1]

    mean = window_data.mean()
    std = window_data.std()

    if std == 0:
        return 0.0

    return float((current - mean) / std)


def zscore_to_color(z: float) -> str:
    if z <= -2:
        return "#1F77B4"
    elif z <= -1:
        return "#5BA8D9"
    elif z < 1:
        return "#5B6E80"
    elif z < 2:
        return "#E67E22"
    else:
        return "#E74C3C"


def get_sparkline_data(history: list, points: int = 30) -> list:
    if not history:
        return []
    return history[-points:]


def data_freshness_label(fetched_at_iso: str) -> str:
    """Return a label like 'live', 'recent', or 'stale' based on age."""
    if not fetched_at_iso:
        return "unknown"
    try:
        fetched = datetime.fromisoformat(fetched_at_iso)
        age_seconds = (datetime.now() - fetched).total_seconds()
        if age_seconds < 90:
            return "live"
        elif age_seconds < 600:
            return "recent"
        else:
            return "stale"
    except Exception:
        return "unknown"