"""
European gas storage data from GIE AGSI+ (free, no API key required for basic queries).
"""

import requests
import pandas as pd
import streamlit as st
from typing import Optional

AGSI_BASE = "https://agsi.gie.eu/api"


@st.cache_data(ttl=3600)
def fetch_european_storage_overall(year: int = None) -> Optional[pd.DataFrame]:
    """
    Fetch overall European gas storage levels (sum across all reporting countries).
    Returns DataFrame with date, gas_in_storage (TWh), full_pct.
    """
    if year is None:
        year = pd.Timestamp.now().year

    try:
        url = f"{AGSI_BASE}/?type=eu&date_from={year}-01-01"
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"[gie_agsi] HTTP {response.status_code}")
            return None

        data = response.json()
        if "data" not in data:
            return None

        records = data["data"]
        if not records:
            return None

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["gasDayStart"])
        df["gas_in_storage"] = pd.to_numeric(df["gasInStorage"], errors="coerce")
        df["full_pct"] = pd.to_numeric(df["full"], errors="coerce")
        return df.sort_values("date").reset_index(drop=True)[["date", "gas_in_storage", "full_pct"]]

    except Exception as e:
        print(f"[gie_agsi] exception: {e}")
        return None