"""
Energy & Oil Trading Dashboard
Main application entry point.
"""

import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from components import (
    load_css,
    render_header,
    render_top_strip,
    render_status_bar,
)

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Energy Trading Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load our custom dark theme
load_css()

# Auto-refresh every 60 seconds
# This will re-run the entire app every 60 seconds, fetching fresh data
st_autorefresh(interval=60_000, key="data_refresh")

# ============================================================
# HEADER
# ============================================================
render_header(
    title="Energy & Oil Trading Dashboard",
    subtitle="Aakarsh Varshney  •  ICE & CME energy markets  •  Live demo",
)

# ============================================================
# PERSISTENT TOP STRIP
# ============================================================
# These are placeholder values for Day 1.
# On Day 2, this will be replaced with live data from yfinance.
top_strip_items = [
    {"label": "WTI",         "value": "—", "change": "", "direction": "neutral"},
    {"label": "Brent",       "value": "—", "change": "", "direction": "neutral"},
    {"label": "WTI-Brent",   "value": "—", "change": "", "direction": "neutral"},
    {"label": "Henry Hub",   "value": "—", "change": "", "direction": "neutral"},
    {"label": "TTF",         "value": "—", "change": "", "direction": "neutral"},
    {"label": "3-2-1 Crack", "value": "—", "change": "", "direction": "neutral"},
    {"label": "DXY",         "value": "—", "change": "", "direction": "neutral"},
    {"label": "Book Delta",  "value": "—", "change": "", "direction": "neutral"},
]
render_top_strip(top_strip_items)

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1. Markets",
    "2. Fundamentals",
    "3. News & Events",
    "4. Models & Signals",
    "5. Risk & Book",
    "★ Replay",
])

with tab1:
    st.markdown("### Markets")
    st.info("Price grid, forward curves, spreads, vol surface, execution. Coming soon — Day 2.")

with tab2:
    st.markdown("### Fundamentals & Flows")
    st.info("Inventories, refinery data, OPEC nowcast, refinery yield-aware crack model. Coming soon.")

with tab3:
    st.markdown("### News & Events")
    st.info("LLM-tagged news, event calendar, major firms & traders stance. Coming soon.")

with tab4:
    st.markdown("### Models & Signals")
    st.info("Fair value, dealer gamma map, regime engine, physical-financial basis, signal inbox. Coming soon.")

with tab5:
    st.markdown("### Risk & Book")
    st.info("Positions, greeks, VaR, stress scenarios, behavioural anomaly detection. Coming soon.")

with tab6:
    st.markdown("### Replay Mode")
    st.info("Scrub through any past day with all data as it appeared. Coming soon.")

# ============================================================
# STATUS BAR
# ============================================================
render_status_bar(
    connection_status="Auto-refresh: 60s",
    last_update=datetime.now().strftime("%H:%M:%S"),
)