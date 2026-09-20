"""
Rolling correlation matrix for the Energy Trading Dashboard.

Computes pairwise correlations across energy instruments and macro symbols
using real Yahoo Finance historical data.
"""

import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf


# Symbols we track for correlation analysis
CORRELATION_SYMBOLS = {
    "WTI": "CL=F",
    "Brent": "BZ=F",
    "NatGas": "NG=F",
    "RBOB": "RB=F",
    "ULSD": "HO=F",
    "DXY": "DX-Y.NYB",
    "S&P 500": "^GSPC",
    "Gold": "GC=F",
    "VIX": "^VIX",
    "Copper": "HG=F",
}


@st.cache_data(ttl=3600)  # cache for 1 hour
def fetch_correlation_data(window_days: int = 90) -> pd.DataFrame:
    """
    Fetch daily close prices for all correlation symbols.
    Returns a DataFrame indexed by date with one column per instrument.
    """
    try:
        # Fetch enough history for the longest window we support
        period_str = f"{max(window_days * 2, 180)}d"

        tickers = list(CORRELATION_SYMBOLS.values())
        data = yf.download(
            tickers,
            period=period_str,
            interval="1d",
            progress=False,
            auto_adjust=True,
        )

        # Extract just the Close prices
        if isinstance(data.columns, pd.MultiIndex):
            closes = data["Close"]
        else:
            closes = data[["Close"]]

        # Rename columns from tickers to friendly names
        ticker_to_name = {v: k for k, v in CORRELATION_SYMBOLS.items()}
        closes = closes.rename(columns=ticker_to_name)

        # Drop any rows that are entirely NaN
        closes = closes.dropna(how="all")

        return closes
    except Exception as e:
        print(f"[correlations] fetch error: {e}")
        return pd.DataFrame()


def compute_correlation_matrix(prices: pd.DataFrame, window_days: int = 30) -> pd.DataFrame:
    """
    Compute correlation matrix on daily returns over the trailing window.
    """
    if prices is None or prices.empty:
        return pd.DataFrame()

    # Take last N days
    recent = prices.tail(window_days + 1)

    # Daily returns
    returns = recent.pct_change().dropna()

    if returns.empty or len(returns) < 5:
        return pd.DataFrame()

    return returns.corr()


def compute_correlation_change(prices: pd.DataFrame, window_days: int = 30,
                                lookback_days: int = 30) -> pd.DataFrame:
    """
    Compute change in correlation matrix vs lookback_days ago.
    Returns a DataFrame showing how each correlation has shifted.
    """
    if prices is None or prices.empty:
        return pd.DataFrame()

    if len(prices) < window_days + lookback_days + 1:
        return pd.DataFrame()

    # Current window correlation
    current_window = prices.tail(window_days + 1)
    current_corr = current_window.pct_change().dropna().corr()

    # Past window correlation (window_days ending lookback_days ago)
    past_window = prices.iloc[-(window_days + lookback_days + 1):-lookback_days]
    past_corr = past_window.pct_change().dropna().corr()

    # The change
    delta = current_corr - past_corr
    return delta


def find_notable_correlations(corr_matrix: pd.DataFrame, threshold: float = 0.6) -> list:
    """
    Find correlations that are notably strong (high positive or negative).
    Returns sorted list of dicts: {pair, value, strength}.
    """
    if corr_matrix.empty:
        return []

    notable = []
    cols = corr_matrix.columns.tolist()
    seen = set()

    for i, a in enumerate(cols):
        for j, b in enumerate(cols):
            if i >= j:  # skip diagonal and lower triangle
                continue
            pair_key = tuple(sorted([a, b]))
            if pair_key in seen:
                continue
            seen.add(pair_key)

            value = corr_matrix.loc[a, b]
            if pd.isna(value):
                continue

            if abs(value) >= threshold:
                if value > 0:
                    strength = "STRONG POSITIVE"
                else:
                    strength = "STRONG NEGATIVE"
                notable.append({
                    "pair": f"{a} ↔ {b}",
                    "value": value,
                    "strength": strength,
                })

    notable.sort(key=lambda x: abs(x["value"]), reverse=True)
    return notable


def find_correlation_breaks(delta_matrix: pd.DataFrame, threshold: float = 0.3) -> list:
    """
    Find correlations that have changed significantly.
    A "correlation break" is when a pair's correlation shifts by >threshold.
    """
    if delta_matrix.empty:
        return []

    breaks = []
    cols = delta_matrix.columns.tolist()
    seen = set()

    for i, a in enumerate(cols):
        for j, b in enumerate(cols):
            if i >= j:
                continue
            pair_key = tuple(sorted([a, b]))
            if pair_key in seen:
                continue
            seen.add(pair_key)

            delta = delta_matrix.loc[a, b]
            if pd.isna(delta):
                continue

            if abs(delta) >= threshold:
                direction = "STRENGTHENED" if delta > 0 else "WEAKENED"
                breaks.append({
                    "pair": f"{a} ↔ {b}",
                    "delta": delta,
                    "direction": direction,
                })

    breaks.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return breaks