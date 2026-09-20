"""
Feature engineering pipeline.

Builds a master daily feature DataFrame combining:
- Curve features from settlement files (Brent, WTI, ULSD, Gasoil)
- Volatility features (rolling realized vol)
- Macro features (DXY, S&P, VIX, Gold, Copper from Yahoo)
- Seasonal features (month, quarter, cyclical encoding)

Output: data/master_features.parquet
Indexed by date, with ~25 feature columns.

This is the input to:
- regime_classifier.py (HMM fitting)
- regression_engine.py (per-spread regressions)
"""

import os
import numpy as np
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_PATH = DATA_DIR / "master_features.parquet"


# ============================================================
# 1. CURVE FEATURES (from settlement files)
# ============================================================

def _load_settlement_file(filename: str, max_tenors: int = 12) -> pd.DataFrame:
    """Load a settlement CSV in the standard wide format."""
    path = DATA_DIR / filename
    if not path.exists():
        return pd.DataFrame()

    try:
        raw = pd.read_csv(path, skiprows=2, header=None, low_memory=False)
        date_col = raw.iloc[:, 0]
        dates = pd.to_datetime(date_col, format="%d-%m-%y", errors="coerce")

        settle_data = {}
        for i in range(max_tenors):
            settle_col_idx = 1 + i * 2
            if settle_col_idx >= raw.shape[1]:
                break
            col = pd.to_numeric(raw.iloc[:, settle_col_idx], errors="coerce")
            settle_data[f"M{i+1}"] = col.values

        df = pd.DataFrame(settle_data, index=dates)
        df.index.name = "date"
        df = df[df.index.notna()].sort_index().dropna(how="all")
        return df
    except Exception as e:
        print(f"[feature_engine] Load error for {filename}: {e}")
        return pd.DataFrame()


def build_curve_features() -> pd.DataFrame:
    """Build curve-structure features for all 4 instruments."""
    instruments = {
        "brent":  ("brent_settle.csv",  31),
        "wti":    ("wti_settle.csv",    12),
        "ulsd":   ("ulsd_settle.csv",   12),
        "gasoil": ("gasoil_settle.csv", 12),
    }

    all_features = []

    for name, (filename, max_tenors) in instruments.items():
        df = _load_settlement_file(filename, max_tenors)
        if df.empty:
            print(f"[feature_engine] Skipping {name} — no data")
            continue

        feats = pd.DataFrame(index=df.index)

        # Front month level (just M1)
        feats[f"{name}_m1"] = df["M1"]

        # Front-month log returns (1-day)
        feats[f"{name}_ret_1d"] = np.log(df["M1"] / df["M1"].shift(1))

        # Realized volatility (20-day rolling std of log returns, annualized)
        feats[f"{name}_vol_20d"] = (
            feats[f"{name}_ret_1d"].rolling(20).std() * np.sqrt(252)
        )
        # Short-window realized volatility (catches shocks faster than 20d)
        feats[f"{name}_vol_5d"] = (
            feats[f"{name}_ret_1d"].rolling(5).std() * np.sqrt(252)
        )
        # Curve steepness: front-to-M12 % (where M12 exists)
        if "M12" in df.columns:
            feats[f"{name}_front_to_m12_pct"] = (
                (df["M1"] - df["M12"]) / df["M12"] * 100
            )
        # Daily change in curve steepness — catches structural shocks (OPEC cuts, etc.)
            feats[f"{name}_curve_change_5d"] = (
                feats[f"{name}_front_to_m12_pct"].diff(5)
            )
        # Curve slope: linear fit across all available tenors
        # negative slope = backwardation, positive = contango
        slopes = []
        for date_idx, row in df.iterrows():
            valid = row.dropna()
            if len(valid) >= 3:
                tenors = np.array([int(c[1:]) for c in valid.index])
                prices = valid.values.astype(float)
                slope, _ = np.polyfit(tenors, prices, 1)
                slopes.append(slope)
            else:
                slopes.append(np.nan)
        feats[f"{name}_curve_slope"] = slopes

        # Front-end curvature (butterfly proxy)
        if all(c in df.columns for c in ["M1", "M2", "M3"]):
            feats[f"{name}_front_fly"] = df["M1"] - 2 * df["M2"] + df["M3"]

        # Mid-curve curvature
        if all(c in df.columns for c in ["M1", "M3", "M6"]):
            feats[f"{name}_mid_fly"] = df["M1"] - 2 * df["M3"] + df["M6"]

        all_features.append(feats)
        print(f"[feature_engine] Built {name} features: "
              f"{feats.shape[0]} days × {feats.shape[1]} columns")

    if not all_features:
        return pd.DataFrame()

    # Outer join across all instruments
    result = all_features[0]
    for f in all_features[1:]:
        result = result.join(f, how="outer")

    return result


# ============================================================
# 2. MACRO FEATURES (from Yahoo Finance)
# ============================================================

def build_macro_features(start_date: str = "2015-01-01") -> pd.DataFrame:
    """Build macro features from Yahoo Finance daily history."""
    tickers = {
        "dxy":    "DX-Y.NYB",
        "spx":    "^GSPC",
        "vix":    "^VIX",
        "gold":   "GC=F",
        "copper": "HG=F",
    }

    feats = pd.DataFrame()

    for name, ticker in tickers.items():
        try:
            data = yf.download(
                ticker, start=start_date, progress=False, auto_adjust=False
            )
            if data.empty:
                print(f"[feature_engine] Empty data for {name} ({ticker})")
                continue

            # Handle MultiIndex columns from newer yfinance versions
            if isinstance(data.columns, pd.MultiIndex):
                close = data[("Close", ticker)] if ("Close", ticker) in data.columns else data["Close"].iloc[:, 0]
            else:
                close = data["Close"]

            close.index = pd.to_datetime(close.index).tz_localize(None)
            feats[f"{name}_level"] = close
            feats[f"{name}_ret_1d"] = np.log(close / close.shift(1))
            feats[f"{name}_mom_20d"] = (close / close.shift(20)) - 1

            print(f"[feature_engine] Built {name} macro: {len(close)} days")
        except Exception as e:
            print(f"[feature_engine] Macro error for {name}: {e}")

    return feats


# ============================================================
# 3. SEASONAL FEATURES (from date)
# ============================================================

def build_seasonal_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Build seasonal/calendar features from datetime index."""
    feats = pd.DataFrame(index=index)

    feats["month"] = index.month
    feats["quarter"] = index.quarter
    feats["day_of_year"] = index.dayofyear

    # Cyclical encoding (preserves continuity: Dec 31 → Jan 1)
    feats["month_sin"] = np.sin(2 * np.pi * index.month / 12)
    feats["month_cos"] = np.cos(2 * np.pi * index.month / 12)
    feats["doy_sin"] = np.sin(2 * np.pi * index.dayofyear / 365.25)
    feats["doy_cos"] = np.cos(2 * np.pi * index.dayofyear / 365.25)

    return feats


# ============================================================
# 4. MAIN PIPELINE
# ============================================================

def build_master_features(save: bool = True) -> pd.DataFrame:
    """
    Build the master feature DataFrame combining curve, macro, and seasonal features.
    Saves to data/master_features.parquet if save=True.
    """
    print("\n" + "=" * 60)
    print("Building master features table")
    print("=" * 60)

    # Curve features (the foundation)
    print("\n[1/3] Curve features...")
    curve_feats = build_curve_features()

    if curve_feats.empty:
        raise RuntimeError("No curve features built — check settlement CSVs")

    print(f"\n  Curve features shape: {curve_feats.shape}")
    print(f"  Date range: {curve_feats.index.min().date()} to {curve_feats.index.max().date()}")

    # Macro features
    print("\n[2/3] Macro features...")
    macro_feats = build_macro_features(
        start_date=curve_feats.index.min().strftime("%Y-%m-%d")
    )
    print(f"  Macro features shape: {macro_feats.shape}")

    # Combine curve + macro
    print("\n[3/3] Joining and adding seasonal...")
    master = curve_feats.join(macro_feats, how="left")

    # Seasonal features
    seasonal_feats = build_seasonal_features(master.index)
    master = master.join(seasonal_feats, how="left")

    # Forward-fill macro (Yahoo data lags settlement on some days)
    macro_cols = [c for c in master.columns if any(c.startswith(p) for p in
                  ["dxy_", "spx_", "vix_", "gold_", "copper_"])]
    master[macro_cols] = master[macro_cols].ffill(limit=3)

    # Drop rows where Brent M1 is missing (Brent is the anchor)
    master = master.dropna(subset=["brent_m1"])

    print(f"\n  Final master table shape: {master.shape}")
    print(f"  Date range: {master.index.min().date()} to {master.index.max().date()}")
    print(f"  Columns ({len(master.columns)}):")
    for i, col in enumerate(master.columns):
        if i < 30 or i >= len(master.columns) - 5:
            non_null = master[col].notna().sum()
            print(f"    {col:35s}  {non_null:5d}/{len(master):5d} non-null")
        elif i == 30:
            print(f"    ... ({len(master.columns) - 35} more) ...")

    if save:
        DATA_DIR.mkdir(exist_ok=True)
        master.to_parquet(OUTPUT_PATH)
        print(f"\n  Saved to {OUTPUT_PATH}")
        print(f"  File size: {OUTPUT_PATH.stat().st_size / 1e3:.1f} KB")

    return master


def load_master_features() -> pd.DataFrame:
    """Load the master features table from disk."""
    if not OUTPUT_PATH.exists():
        raise FileNotFoundError(
            f"{OUTPUT_PATH} not found. Run `python src/feature_engine.py` first."
        )
    return pd.read_parquet(OUTPUT_PATH)


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    master = build_master_features(save=True)
    print(f"\nMaster features ready: {master.shape}")
    print("Sample rows:")
    print(master.tail(3).T)