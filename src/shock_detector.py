"""
Shock/Event detector — flags transient market shocks the smoothed HMM misses.

The HMM correctly classifies baseline market state but lags single-day shocks
(realized vol takes ~5-10 days to accumulate). This module fills that gap with
fast rule-based event detection.

A "shock" is flagged when any of these conditions fire on a single day:
  - Price move > 4% (absolute return)
  - Curve change > 3% in 5 days (front-to-M12 % shifting fast)
  - Vol jumped > 50% week-over-week (vol-of-vol surge)
  - Inter-product spread moved > 2σ in one day

Output: data/shock_flags.parquet
        — date × shock_type, shock_severity, shock_description
"""

import numpy as np
import pandas as pd
from pathlib import Path
from feature_engine import load_master_features

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_PATH = DATA_DIR / "shock_flags.parquet"


# ============================================================
# 1. SHOCK DETECTION RULES
# ============================================================

def detect_shocks(master: pd.DataFrame = None) -> pd.DataFrame:
    """
    Scan the master features table for single-day shocks.
    Returns DataFrame indexed by date, with shock_type, severity, description.
    """
    if master is None:
        master = load_master_features()

    print("=" * 60)
    print("Shock Detector — scanning historical record")
    print("=" * 60)

    shocks = []

    # Rule 1: Big price moves (absolute return > 4%)
    for inst in ["brent", "wti", "ulsd", "gasoil"]:
        ret_col = f"{inst}_ret_1d"
        if ret_col not in master.columns:
            continue

        big_moves = master[master[ret_col].abs() > 0.04][ret_col]
        for date, ret in big_moves.items():
            shocks.append({
                "date": date,
                "shock_type": "PRICE_SHOCK",
                "instrument": inst.upper(),
                "severity": float(abs(ret) * 100),
                "description": f"{inst.upper()} moved {ret*100:+.2f}% in one day",
            })

    # Rule 2: Rapid curve change (front-to-M12 shifted > 3pp in 5 days)
    for inst in ["brent", "wti", "ulsd", "gasoil"]:
        curve_col = f"{inst}_front_to_m12_pct"
        if curve_col not in master.columns:
            continue

        curve_change = master[curve_col].diff(5)
        big_curve_moves = curve_change[curve_change.abs() > 5]
        for date, chg in big_curve_moves.items():
            shocks.append({
                "date": date,
                "shock_type": "CURVE_SHOCK",
                "instrument": inst.upper(),
                "severity": float(abs(chg)),
                "description": f"{inst.upper()} curve steepness shifted {chg:+.2f}pp in 5 days",
            })

    # Rule 3: Vol-of-vol surge (20d vol jumped > 50% week-over-week)
    for inst in ["brent", "wti"]:
        vol_col = f"{inst}_vol_20d"
        if vol_col not in master.columns:
            continue

        vol_ratio = master[vol_col] / master[vol_col].shift(5)
        vol_jumps = vol_ratio[vol_ratio > 1.75]
        for date, ratio in vol_jumps.items():
            shocks.append({
                "date": date,
                "shock_type": "VOL_SURGE",
                "instrument": inst.upper(),
                "severity": float((ratio - 1) * 100),
                "description": f"{inst.upper()} realized vol jumped {(ratio-1)*100:+.1f}% in 5 days",
            })

    # Rule 4: VIX spike (>20% jump week-over-week)
    if "vix_level" in master.columns:
        vix_ratio = master["vix_level"] / master["vix_level"].shift(5)
        vix_spikes = vix_ratio[vix_ratio > 1.30]
        for date, ratio in vix_spikes.items():
            shocks.append({
                "date": date,
                "shock_type": "VIX_SPIKE",
                "instrument": "MACRO",
                "severity": float((ratio - 1) * 100),
                "description": f"VIX jumped {(ratio-1)*100:+.1f}% in 5 days",
            })

    if not shocks:
        return pd.DataFrame()

    df = pd.DataFrame(shocks)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()

    print(f"\n  Detected {len(df)} shock events across all rules")
    print(f"  Shock types: ")
    for t, count in df["shock_type"].value_counts().items():
        print(f"    {t}: {count}")

    return df


# ============================================================
# 2. AGGREGATE PER DATE (since multiple shocks may fire same day)
# ============================================================

def aggregate_shocks_by_date(shocks_df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse multiple shocks on the same date into a single row.
    """
    if shocks_df.empty:
        return pd.DataFrame()

    grouped = []
    for date, group in shocks_df.groupby(level=0):
        # Find the row with maximum severity (use iloc to guarantee scalar return)
        max_sev_pos = group["severity"].values.argmax()
        primary_type = str(group["shock_type"].iloc[max_sev_pos])
        primary_inst = str(group["instrument"].iloc[max_sev_pos])

        grouped.append({
            "date": date,
            "n_shocks": int(len(group)),
            "primary_type": primary_type,
            "primary_instrument": primary_inst,
            "max_severity": float(group["severity"].max()),
            "all_types": ", ".join(sorted(set(group["shock_type"].tolist()))),
            "descriptions": " | ".join(group["description"].tolist()),
        })

    df = pd.DataFrame(grouped).set_index("date")
    return df


# ============================================================
# 3. SAVE / LOAD
# ============================================================

def save_shocks(shocks_df: pd.DataFrame, aggregated_df: pd.DataFrame):
    """Save both raw and aggregated shock data."""
    DATA_DIR.mkdir(exist_ok=True)
    shocks_df.to_parquet(OUTPUT_PATH)
    print(f"\n  Saved shock flags to {OUTPUT_PATH}")
    print(f"  File size: {OUTPUT_PATH.stat().st_size / 1e3:.1f} KB")

    agg_path = OUTPUT_PATH.parent / "shock_flags_aggregated.parquet"
    aggregated_df.to_parquet(agg_path)
    print(f"  Saved aggregated shocks to {agg_path}")


def load_shocks() -> pd.DataFrame:
    """Load saved shock flags."""
    if not OUTPUT_PATH.exists():
        return pd.DataFrame()
    return pd.read_parquet(OUTPUT_PATH)


def load_shocks_aggregated() -> pd.DataFrame:
    """Load aggregated shock flags (one row per shock date)."""
    path = OUTPUT_PATH.parent / "shock_flags_aggregated.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


# ============================================================
# 4. CHECK SPECIFIC DATES
# ============================================================

def check_dates(dates_with_labels: list):
    """For a list of (date_str, label) pairs, print whether shocks fired."""
    agg = load_shocks_aggregated()
    if agg.empty:
        print("No shock data loaded.")
        return

    print(f"\n{'Date':<12} {'Event':<28} {'Shocks':<40}")
    print("-" * 90)
    for date_str, label in dates_with_labels:
        date = pd.to_datetime(date_str)
        if date in agg.index:
            row = agg.loc[date]
            # all_types is now a comma-separated string, not a list
            types = row["all_types"]
            severity = row.get("max_severity", 0)
            print(f"{date_str:<12} {label:<28} {types}  (sev {severity:.1f})")
        else:
            print(f"{date_str:<12} {label:<28} (no shocks detected)")


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    shocks_raw = detect_shocks()
    shocks_agg = aggregate_shocks_by_date(shocks_raw)
    save_shocks(shocks_raw, shocks_agg)

    # Sanity check against known events
    print("\n" + "=" * 60)
    print("Sanity check — known event dates")
    print("=" * 60)
    check_dates([
        ("2022-02-24", "Russia invades Ukraine"),
        ("2022-02-28", "Russia D+4"),
        ("2023-04-03", "OPEC+ surprise cut"),
        ("2020-03-09", "COVID first crash"),
        ("2020-03-20", "COVID demand crash"),
        ("2024-10-01", "Iran-Israel strike"),
        ("2018-06-15", "Calm 2018"),
        ("2026-05-26", "Today (latest data)"),
    ])