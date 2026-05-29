"""
Seasonality analysis for the Energy Trading Dashboard.
Computes year-overlay, monthly returns, and average seasonal paths from
historical price data.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
from typing import Optional


# Instruments available for seasonality analysis
SEASONALITY_INSTRUMENTS = {
    "WTI":         {"ticker": "CL=F", "label": "WTI Crude"},
    "Brent":       {"ticker": "BZ=F", "label": "Brent Crude"},
    "RBOB":        {"ticker": "RB=F", "label": "RBOB Gasoline"},
    "ULSD":        {"ticker": "HO=F", "label": "ULSD / Heating Oil"},
    "Natural Gas": {"ticker": "NG=F", "label": "Natural Gas"},
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@st.cache_data(ttl=3600)
def fetch_long_history(ticker: str, years: int = 8) -> Optional[pd.DataFrame]:
    """Fetch several years of daily prices for seasonality analysis."""
    try:
        end = datetime.now()
        start = end.replace(year=end.year - years)

        series = yf.Ticker(ticker).history(start=start, end=end, interval="1d")["Close"].dropna()
        if len(series) < 100:
            return None

        df = series.to_frame(name="price")
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df["year"] = df.index.year
        df["month"] = df.index.month
        df["day_of_year"] = df.index.dayofyear
        return df
    except Exception as e:
        print(f"[seasonality] {ticker}: {e}")
        return None


def build_year_overlay(df: pd.DataFrame, years_to_show: int = 5) -> dict:
    """Build normalized year-over-year price paths, rebased to 100 at year start."""
    current_year = df["year"].max()
    years = range(current_year - years_to_show, current_year + 1)

    overlays = {}
    for year in years:
        year_data = df[df["year"] == year].copy()
        if len(year_data) < 10:
            continue
        first_price = year_data["price"].iloc[0]
        year_data["normalized"] = (year_data["price"] / first_price) * 100
        overlays[year] = year_data[["day_of_year", "normalized"]]

    return overlays


def build_monthly_returns(df: pd.DataFrame, drop_partial_years: bool = True) -> Optional[pd.DataFrame]:
    """
    Compute monthly returns pivot: rows=year, columns=month, values=return%.
    By default drops years that don't have all 12 months of data,
    so the heatmap is clean and aligned.
    """
    monthly = df["price"].resample("ME").last()
    monthly_returns = monthly.pct_change() * 100

    mr_df = monthly_returns.to_frame(name="return")
    mr_df["year"] = mr_df.index.year
    mr_df["month"] = mr_df.index.month

    pivot = mr_df.pivot_table(values="return", index="year", columns="month", aggfunc="mean")

    if drop_partial_years:
        # Keep only years that have data for all 12 months
        complete_years = pivot.dropna(thresh=12).index
        pivot = pivot.loc[complete_years]

    return pivot


def build_average_seasonal_path(df: pd.DataFrame, years_back: int = 8) -> Optional[pd.DataFrame]:
    """Compute average normalized price path across years with std band."""
    current_year = df["year"].max()
    years = range(current_year - years_back, current_year)

    paths = []
    for year in years:
        year_data = df[df["year"] == year].copy()
        if len(year_data) < 50:
            continue
        first = year_data["price"].iloc[0]
        year_data["norm"] = (year_data["price"] / first) * 100
        s = year_data.set_index("day_of_year")["norm"]
        paths.append(s)

    if not paths:
        return None

    combined = pd.concat(paths, axis=1)
    avg_path = combined.mean(axis=1)
    std_path = combined.std(axis=1)

    result = pd.DataFrame({
        "day_of_year": avg_path.index,
        "avg": avg_path.values,
        "upper": (avg_path + std_path).values,
        "lower": (avg_path - std_path).values,
    }).sort_values("day_of_year")

    return result


def best_worst_months(monthly_pivot: pd.DataFrame) -> dict:
    """Identify the historically best and worst months."""
    avg_by_month = monthly_pivot.mean()

    best_month_num = avg_by_month.idxmax()
    worst_month_num = avg_by_month.idxmin()

    # Win rate per month (% of years positive)
    win_rates = (monthly_pivot > 0).mean() * 100

    return {
        "best_month": MONTH_NAMES[int(best_month_num) - 1],
        "best_return": float(avg_by_month.max()),
        "worst_month": MONTH_NAMES[int(worst_month_num) - 1],
        "worst_return": float(avg_by_month.min()),
        "avg_by_month": avg_by_month,
        "win_rates": win_rates,
    }


def current_month_seasonal_context(df: pd.DataFrame) -> Optional[dict]:
    """How does the current month typically perform, and how is it doing this year?"""
    monthly_pivot = build_monthly_returns(df)
    if monthly_pivot is None:
        return None

    current_month = datetime.now().month
    if current_month not in monthly_pivot.columns:
        return None

    historical = monthly_pivot[current_month].dropna()
    avg_return = historical.mean()
    win_rate = (historical > 0).mean() * 100

    return {
        "month_name": MONTH_NAMES[current_month - 1],
        "avg_return": float(avg_return),
        "win_rate": float(win_rate),
        "years_count": len(historical),
    }