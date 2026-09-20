"""
Convert intraday 1-minute settlement files to daily settlement CSVs.

Reads CL_data.csv (WTI), HO_data.csv (ULSD), LGO_data.csv (Gasoil) from Downloads,
picks the last row of each trading day,
and writes data/wti_settle.csv, data/ulsd_settle.csv, data/gasoil_settle.csv

Run from the project root:
    python src/convert_intraday_to_daily.py
"""

import os
import pandas as pd
from pathlib import Path

DOWNLOADS_DIR = Path(os.path.expanduser("~/Downloads"))
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

CONVERSIONS = [
    {"source": "CL_data.csv",  "output": "wti_settle.csv",     "label": "WTI"},
    {"source": "HO_data.csv",  "output": "ulsd_settle.csv",    "label": "ULSD"},
    {"source": "LGO_data.csv", "output": "gasoil_settle.csv",  "label": "Gasoil"},
]

MAX_CONTRACTS = 12


def convert_one_file(source_path: Path, output_path: Path, label: str) -> bool:
    print(f"\n{'='*60}")
    print(f"Converting {label}: {source_path.name}")
    print(f"{'='*60}")

    if not source_path.exists():
        print(f"  SKIP: {source_path} not found")
        return False

    print(f"  Reading {source_path} ({source_path.stat().st_size / 1e6:.1f} MB)...")

    try:
        df = pd.read_csv(source_path, skiprows=1, low_memory=False)
        print(f"  Loaded {len(df):,} rows, {df.shape[1]} columns")
        print(f"  Column names (first 7): {df.columns.tolist()[:7]}")
    except Exception as e:
        print(f"  ERROR reading: {e}")
        return False

    cols = df.columns.tolist()
    timestamp_col = cols[0]

    # Identify the weighted_mid columns by NAME, not by position
    # Source structure: timestamp, c1||contract, c1||weighted_mid, c2||contract, c2||weighted_mid, ...
    price_cols = []
    for col_name in cols:
        if "weighted_mid" in str(col_name).lower():
            price_cols.append(col_name)
        if len(price_cols) >= MAX_CONTRACTS:
            break

    print(f"  Found {len(price_cols)} price columns: {price_cols[:3]}...")

    if len(price_cols) == 0:
        print(f"  ERROR: No 'weighted_mid' columns found. Cannot proceed.")
        return False

    # Parse timestamps
    print(f"  Parsing timestamps...")
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")
    df = df[df[timestamp_col].notna()].copy()

    print(f"  Date range: {df[timestamp_col].min()} to {df[timestamp_col].max()}")

    df["_date"] = df[timestamp_col].dt.date

    print(f"  Resampling to daily (last row per day)...")
    daily = df.groupby("_date", as_index=False).last()
    print(f"  Got {len(daily):,} trading days")

    # Build output rows: [date, settle1, date, settle2, ..., date, settleN]
    output_rows = []
    for _, row in daily.iterrows():
        date_str = row[timestamp_col].strftime("%d-%m-%y")
        out_row = []
        for price_col in price_cols:
            settle_value = row[price_col]
            out_row.append(date_str)
            out_row.append(settle_value)
        output_rows.append(out_row)

    # Build header rows
    n_contracts = len(price_cols)
    contract_headers = []
    field_headers = []
    for c_idx in range(1, n_contracts + 1):
        contract_headers.extend([f"{label}{c_idx}", f"{label}{c_idx}"])
        field_headers.extend(["Timestamp", "SETTLE"])

    print(f"  Writing {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(",".join(contract_headers) + "\n")
        f.write(",".join(field_headers) + "\n")
        for row in output_rows:
            row_strs = [str(v) if v is not None and not pd.isna(v) else "" for v in row]
            f.write(",".join(row_strs) + "\n")

    print(f"  Wrote {len(output_rows):,} daily rows x {n_contracts} contracts")
    print(f"  File size: {output_path.stat().st_size / 1e3:.1f} KB")

    # Sanity check: verify the first written row has numbers, not contract codes
    print(f"  Sanity check: first data row = {output_rows[0][:6]}")

    return True


def main():
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Source folder: {DOWNLOADS_DIR}")
    print(f"Output folder: {OUTPUT_DIR}")

    successes = 0
    for conv in CONVERSIONS:
        source = DOWNLOADS_DIR / conv["source"]
        output = OUTPUT_DIR / conv["output"]
        if convert_one_file(source, output, conv["label"]):
            successes += 1

    print(f"\n{'='*60}")
    print(f"Done. Converted {successes}/{len(CONVERSIONS)} files.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()