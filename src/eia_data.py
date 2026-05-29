"""
EIA data fetching for the Energy Trading Dashboard.

Pulls weekly petroleum and natural gas data from the free EIA API.
Series IDs and conventions documented at: https://www.eia.gov/opendata/
"""

import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

EIA_API_KEY = os.getenv("EIA_API_KEY")
BASE_URL = "https://api.eia.gov/v2"


# ============================================================
# SERIES REGISTRY
# ============================================================

INVENTORY_SERIES = {
    "us_crude_stocks": {
        "label": "US Crude Oil Stocks",
        "unit": "kbbl",
        "endpoint": "petroleum/stoc/wstk/data",
        "facet_series": "WCESTUS1",
        "color": "#E67E22",
    },
    "cushing_stocks": {
        "label": "Cushing Stocks (WTI delivery)",
        "unit": "kbbl",
        "endpoint": "petroleum/stoc/wstk/data",
        "facet_series": "W_EPC0_SAX_YCUOK_MBBL",
        "color": "#E74C3C",
    },
    "us_gasoline_stocks": {
        "label": "US Gasoline Stocks (RBOB proxy)",
        "unit": "kbbl",
        "endpoint": "petroleum/stoc/wstk/data",
        "facet_series": "WGTSTUS1",
        "color": "#2ECC71",
    },
    "us_distillate_stocks": {
        "label": "US Distillate Stocks (ULSD proxy)",
        "unit": "kbbl",
        "endpoint": "petroleum/stoc/wstk/data",
        "facet_series": "WDISTUS1",
        "color": "#5BA8D9",
    },
    "us_natgas_storage": {
        "label": "US Natural Gas Storage (Lower 48)",
        "unit": "Bcf",
        "endpoint": "natural-gas/stor/wkly/data",
        "facet_series": "NW2_EPG0_SWO_R48_BCF",
        "color": "#9B59B6",
    },
    "us_refinery_util": {
        "label": "US Refinery Utilization",
        "unit": "%",
        "endpoint": "petroleum/sum/sndw/data",
        "facet_series": "WPULEUS3",
        "color": "#F39C12",
    },
}


# ============================================================
# FETCH
# ============================================================

@st.cache_data(ttl=3600)  # cache for 1 hour (EIA data updates weekly)
def fetch_series(series_key: str, start_date: str = "2018-01-01") -> Optional[pd.DataFrame]:
    """Fetch a single EIA series by its key in INVENTORY_SERIES."""
    if series_key not in INVENTORY_SERIES:
        return None

    if not EIA_API_KEY:
        print("[eia_data] No EIA_API_KEY in .env")
        return None

    spec = INVENTORY_SERIES[series_key]
    url = f"{BASE_URL}/{spec['endpoint']}"

    params = {
        "api_key": EIA_API_KEY,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": spec["facet_series"],
        "start": start_date,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"[eia_data] {series_key}: HTTP {response.status_code}")
            return None

        data = response.json()
        records = data.get("response", {}).get("data", [])
        if not records:
            print(f"[eia_data] {series_key}: empty response")
            return None

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["period"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.sort_values("date").reset_index(drop=True)
        return df[["date", "value"]]

    except Exception as e:
        print(f"[eia_data] {series_key}: exception {e}")
        return None


# ============================================================
# ANALYTICS
# ============================================================

def build_seasonality_envelope(df: pd.DataFrame, years_back: int = 5) -> pd.DataFrame:
    """Build 5-year min/max/avg envelope by week-of-year + current year path."""
    df = df.copy()
    df["year"] = df["date"].dt.year
    df["week"] = df["date"].dt.isocalendar().week.astype(int)

    current_year = df["year"].max()
    historical_years = range(current_year - years_back, current_year)

    historical = df[df["year"].isin(historical_years)]
    envelope = historical.groupby("week")["value"].agg(["min", "max", "mean"]).reset_index()
    envelope.columns = ["week", "hist_min", "hist_max", "hist_avg"]

    current = df[df["year"] == current_year][["week", "value"]].rename(columns={"value": "current"})
    result = envelope.merge(current, on="week", how="left")
    return result


def compute_surprise(df: pd.DataFrame) -> dict:
    """
    Compute the surprise of the most recent print vs the trailing 4-week average change.
    """
    if df is None or len(df) < 6:
        return None

    df = df.copy().sort_values("date")
    df["change"] = df["value"].diff()

    latest = df.iloc[-1]
    recent_changes = df["change"].iloc[-5:-1]  # 4 weeks before latest

    if recent_changes.std() == 0:
        return None

    expected = recent_changes.mean()
    actual = latest["change"]
    surprise = actual - expected
    z = (surprise) / recent_changes.std() if recent_changes.std() > 0 else 0

    return {
        "date": latest["date"],
        "actual_change": float(actual),
        "expected_change": float(expected),
        "surprise": float(surprise),
        "zscore": float(z),
    }


def current_vs_5yr_avg(df: pd.DataFrame) -> dict:
    """Show how current value compares to historical same-week average."""
    if df is None or len(df) == 0:
        return None

    df = df.copy()
    df["year"] = df["date"].dt.year
    df["week"] = df["date"].dt.isocalendar().week.astype(int)

    current_year = df["year"].max()
    current_week = df[df["year"] == current_year]["week"].max()

    current_row = df[(df["year"] == current_year) & (df["week"] == current_week)]
    if len(current_row) == 0:
        return None
    current_val = current_row["value"].iloc[-1]

    historical = df[
        (df["year"] >= current_year - 5) & (df["year"] < current_year) & (df["week"] == current_week)
    ]
    if len(historical) == 0:
        return None

    avg_val = historical["value"].mean()
    diff = current_val - avg_val
    diff_pct = (diff / avg_val) * 100 if avg_val != 0 else 0

    return {
        "current": float(current_val),
        "avg_5yr": float(avg_val),
        "diff": float(diff),
        "diff_pct": float(diff_pct),
        "is_above_avg": current_val > avg_val,
    }