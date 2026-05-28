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
# Fetch live data
from market_data import fetch_market_data, add_derived_metrics, format_value, format_change

@st.cache_data(ttl=30)  # cache for 55 seconds, just below auto-refresh interval
def get_data():
    data = fetch_market_data()
    data = add_derived_metrics(data)
    return data

market_data = get_data()

def build_top_strip_item(label: str, data_key: str, decimals: int = 2):
    """Helper to build a top strip item from market_data."""
    item_data = market_data.get(data_key)
    if item_data is None:
        return {"label": label, "value": "—", "change": "", "direction": "neutral"}
    return {
        "label": label,
        "value": format_value(item_data["latest"], decimals),
        "change": format_change(item_data["change"], decimals),
        "direction": item_data["direction"],
    }

top_strip_items = [
    build_top_strip_item("WTI", "WTI"),
    build_top_strip_item("Brent", "Brent"),
    build_top_strip_item("WTI-Brent", "WTI-Brent"),
    build_top_strip_item("Henry Hub", "Henry Hub", decimals=3),
    {"label": "TTF",         "value": "—", "change": "", "direction": "neutral"},  # not free
    {"label": "3-2-1 Crack", "value": "—", "change": "", "direction": "neutral"},  # to compute
    build_top_strip_item("DXY", "DXY"),
    {"label": "Book Delta",  "value": "+47k bbl", "change": "demo", "direction": "neutral"},
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
    from components import render_price_grid, render_macro_panel, render_execution_panel

    price_grid_instruments = [
        {"name": "WTI",       "label": "WTI Crude",        "decimals": 2},
        {"name": "Brent",     "label": "Brent Crude",      "decimals": 2},
        {"name": "Henry Hub", "label": "Henry Hub Gas",    "decimals": 3},
        {"name": "RBOB",      "label": "RBOB Gasoline",    "decimals": 3},
        {"name": "ULSD",      "label": "ULSD / HO",        "decimals": 3},
        {"name": "WTI-Brent", "label": "WTI-Brent Spread", "decimals": 2},
    ]

    # Three-column layout matching the proposal mockup
    left, center, right = st.columns([1.1, 1.4, 0.9])

    with left:
        render_price_grid(market_data, price_grid_instruments)
        render_macro_panel(market_data)

    with center:
        from components import (
            render_forward_curve_panel,
            render_calendar_spreads_panel,
            render_interproduct_spreads_panel,
        )

        render_forward_curve_panel(market_data)
        render_calendar_spreads_panel(market_data)
        render_interproduct_spreads_panel(market_data)

        st.markdown(
            '<div class="panel" style="min-height: 100px;">'
            '<div class="panel-title">Implied Vol Surface</div>'
            '<div style="color:#8B9DAE; padding:20px 0; text-align:center; font-size:0.85rem;">'
            'Vol surface, skew, term structure. Coming Day 5.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    with right:
        render_execution_panel()

        st.markdown(
            '<div class="panel" style="min-height: 200px;">'
            '<div class="panel-title">★ Signal Inbox</div>'
            '<div style="color:#8B9DAE; padding:20px 0; text-align:center; font-size:0.85rem;">'
            'Consolidated alerts ranked by historical edge.<br>Coming Day 7.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

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