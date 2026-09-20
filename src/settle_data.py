"""
Unified loader for settlement CSV files.

Handles Brent (LCOSettle), WTI (wti_settle), ULSD (ulsd_settle), Gasoil (gasoil_settle).
All files share the same wide format: rows = dates, paired columns = (timestamp, settle).

Returns DataFrames indexed by date with columns M1, M2, ..., MN.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# Map instrument name -> (filename, max tenors loaded)
SETTLEMENT_FILES = {
    "Brent":  {"file": "brent_settle.csv",  "max_tenors": 31},
    "WTI":    {"file": "wti_settle.csv",    "max_tenors": 12},
    "ULSD":   {"file": "ulsd_settle.csv",   "max_tenors": 12},
    "Gasoil": {"file": "gasoil_settle.csv", "max_tenors": 12},
}


@st.cache_data(ttl=3600)
def load_settlement_curves(instrument: str) -> pd.DataFrame:
    """
    Load settlement data for the given instrument into a wide DataFrame.
    Returns DataFrame indexed by date with columns M1, M2, ..., MN.
    Returns empty DataFrame if file missing or malformed.
    """
    if instrument not in SETTLEMENT_FILES:
        return pd.DataFrame()

    config = SETTLEMENT_FILES[instrument]
    path = DATA_DIR / config["file"]
    max_tenors = config["max_tenors"]

    if not path.exists():
        return pd.DataFrame()

    try:
        # First 2 rows are headers; data starts row 3
        raw = pd.read_csv(path, skiprows=2, header=None, low_memory=False)

        # Column 0 is the date for all paired columns (they all repeat the same date)
        date_col = raw.iloc[:, 0]
        dates = pd.to_datetime(date_col, format="%d-%m-%y", errors="coerce")

        # Settle prices live at column indices 1, 3, 5, ... (odd indices)
        settle_data = {}
        for i in range(max_tenors):
            settle_col_idx = 1 + i * 2
            if settle_col_idx >= raw.shape[1]:
                break
            col = pd.to_numeric(raw.iloc[:, settle_col_idx], errors="coerce")
            settle_data[f"M{i+1}"] = col.values

        df = pd.DataFrame(settle_data, index=dates)
        df.index.name = "date"

        # Drop rows where date couldn't be parsed
        df = df[df.index.notna()]

        # Sort chronologically (oldest first)
        df = df.sort_index()

        # Drop fully-empty rows
        df = df.dropna(how="all")

        print(f"[settle_data] Loaded {instrument}: {len(df)} days, {df.shape[1]} tenors, "
              f"range {df.index.min().date()} to {df.index.max().date()}")

        return df

    except Exception as e:
        print(f"[settle_data] Load error for {instrument}: {type(e).__name__}: {e}")
        return pd.DataFrame()


def get_latest_curve(instrument: str):
    """Return latest curve as list of (tenor, price) tuples."""
    df = load_settlement_curves(instrument)
    if df.empty:
        return None, None

    latest_row = df.iloc[-1]
    latest_date = df.index[-1]

    curve = []
    for col in df.columns:
        tenor = int(col[1:])  # "M1" -> 1
        if pd.notna(latest_row[col]):
            curve.append((tenor, float(latest_row[col])))

    return curve, latest_date


def get_historical_curves(instrument: str):
    """Return today, yesterday, last_week, last_month curves."""
    df = load_settlement_curves(instrument)
    if df.empty or len(df) < 6:
        return None

    result = {"latest_date": df.index[-1]}

    def row_to_curve(row):
        curve = []
        for col in df.columns:
            tenor = int(col[1:])
            if pd.notna(row[col]):
                curve.append((tenor, float(row[col])))
        return curve

    result["today"] = row_to_curve(df.iloc[-1])
    if len(df) >= 2:
        result["yesterday"] = row_to_curve(df.iloc[-2])
    if len(df) >= 6:
        result["last_week"] = row_to_curve(df.iloc[-6])
    if len(df) >= 22:
        result["last_month"] = row_to_curve(df.iloc[-22])

    return result


def get_curve_as_of(instrument: str, date) -> list:
    """Return curve as of a specific date (or nearest prior trading day)."""
    df = load_settlement_curves(instrument)
    if df.empty:
        return []

    target = pd.to_datetime(date)
    if target in df.index:
        row = df.loc[target]
    else:
        prior = df.index[df.index <= target]
        if len(prior) == 0:
            return []
        row = df.loc[prior[-1]]

    curve = []
    for col in df.columns:
        tenor = int(col[1:])
        if pd.notna(row[col]):
            curve.append((tenor, float(row[col])))
    return curve


def get_historical_curves_as_of(instrument: str, date):
    """Return today/yesterday/last_week/last_month curves as of a given date."""
    df = load_settlement_curves(instrument)
    if df.empty:
        return None

    target = pd.to_datetime(date)
    valid = df.index[df.index <= target]
    if len(valid) == 0:
        return None

    end_loc = df.index.get_loc(valid[-1])
    result = {"latest_date": valid[-1]}

    def row_to_curve(row):
        curve = []
        for col in df.columns:
            tenor = int(col[1:])
            if pd.notna(row[col]):
                curve.append((tenor, float(row[col])))
        return curve

    result["today"] = row_to_curve(df.iloc[end_loc])
    if end_loc >= 1:
        result["yesterday"] = row_to_curve(df.iloc[end_loc - 1])
    if end_loc >= 5:
        result["last_week"] = row_to_curve(df.iloc[end_loc - 5])
    if end_loc >= 21:
        result["last_month"] = row_to_curve(df.iloc[end_loc - 21])

    return result


def compute_historical_spread(instrument: str, m_a: int, m_b: int) -> pd.Series:
    """Return historical M_a - M_b spread time series."""
    df = load_settlement_curves(instrument)
    if df.empty:
        return pd.Series(dtype=float)

    col_a = f"M{m_a}"
    col_b = f"M{m_b}"
    if col_a not in df.columns or col_b not in df.columns:
        return pd.Series(dtype=float)

    return (df[col_a] - df[col_b]).dropna()


def compute_historical_fly(instrument: str, m_a: int, m_b: int, m_c: int) -> pd.Series:
    """Return historical butterfly fly time series M_a - 2*M_b + M_c."""
    df = load_settlement_curves(instrument)
    if df.empty:
        return pd.Series(dtype=float)

    cols = [f"M{m_a}", f"M{m_b}", f"M{m_c}"]
    if not all(c in df.columns for c in cols):
        return pd.Series(dtype=float)

    return (df[cols[0]] - 2 * df[cols[1]] + df[cols[2]]).dropna()


def real_zscore(current_value: float, history_series: pd.Series, lookback_days: int = 252) -> float:
    """Compute z-score of current_value vs trailing window of historical series."""
    if history_series.empty:
        return 0.0
    recent = history_series.tail(lookback_days)
    if len(recent) < 30 or recent.std() == 0:
        return 0.0
    return float((current_value - recent.mean()) / recent.std())


def has_real_data(instrument: str) -> bool:
    """Return True if real settlement data is available for this instrument."""
    if instrument not in SETTLEMENT_FILES:
        return False
    df = load_settlement_curves(instrument)
    return not df.empty