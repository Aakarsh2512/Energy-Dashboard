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
# st_autorefresh(interval=60_000, key="data_refresh")

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

# Compute 3-2-1 crack live from real data for the strip
from forward_curves import compute_inter_product_spreads
_ips = compute_inter_product_spreads(market_data)
_crack = _ips.get("3-2-1 Crack", {})

top_strip_items = [
    build_top_strip_item("WTI", "WTI"),
    build_top_strip_item("Brent", "Brent"),
    build_top_strip_item("WTI-Brent", "WTI-Brent"),
    build_top_strip_item("Henry Hub", "Henry Hub", decimals=3),
    build_top_strip_item("RBOB", "RBOB", decimals=3),
    build_top_strip_item("ULSD", "ULSD", decimals=3),
    {
        "label": "3-2-1 Crack",
        "value": f"{_crack['value']:.2f}" if _crack else "—",
        "change": f"{(_crack['value']-_crack['previous']):+.2f}" if _crack else "",
        "direction": ("up" if _crack and _crack['value'] > _crack['previous'] else "down" if _crack and _crack['value'] < _crack['previous'] else "neutral"),
    },
    build_top_strip_item("DXY", "DXY"),
]

render_top_strip(top_strip_items)

# ============================================================
# TABS
# ============================================================
# Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Markets",
    "Inventory",
    "Seasonality",
    "News & Events",
    "Spreads, Flies & Correlations",
    "★ Strategy Lab",
    "★ Replay",
])

with tab1:
    from components import (
        render_price_grid,
        render_macro_panel,
        render_live_chart_panel,
        render_forward_curve_with_selector,
        render_alert_strip,
        render_news_compact,
        render_key_correlations_mini,
    )

    price_grid_instruments = [
        {"name": "WTI",       "label": "WTI Crude",        "decimals": 2},
        {"name": "Brent",     "label": "Brent Crude",      "decimals": 2},
        {"name": "Henry Hub", "label": "Henry Hub Gas",    "decimals": 3},
        {"name": "RBOB",      "label": "RBOB Gasoline",    "decimals": 3},
        {"name": "ULSD",      "label": "ULSD / HO",        "decimals": 3},
        {"name": "WTI-Brent", "label": "WTI-Brent Spread", "decimals": 2},
    ]

    # ============================================================
    # THREE-COLUMN LAYOUT
    # Left: Price Grid + Macro
    # Center: TradingView Live Chart + Forward Curve (with selector)
    # Right: Alerts + News + Key Correlations
    # ============================================================
    left, center, right = st.columns([1.1, 1.7, 0.85])

    with left:
        render_price_grid(market_data, price_grid_instruments)
        render_macro_panel(market_data)
        # Key correlations summary
        render_key_correlations_mini()

    with center:
        # Live TradingView chart on top
        render_live_chart_panel()

        # Forward curve below with mode selector
        render_forward_curve_with_selector(market_data)

    with right:
        # Live Alerts (the highlight feature)
        render_alert_strip(market_data, max_alerts=6)

        # Compact news feed
        render_news_compact(market_data, max_items=5)

        

with tab2:
    from components import render_inventory_tab
    render_inventory_tab(market_data)

with tab3:
    from components import render_seasonality_tab
    render_seasonality_tab(market_data)

with tab4 :
    from components import render_news_tab
    render_news_tab(market_data)

with tab5:
    from components import render_spreads_tab
    render_spreads_tab(market_data)

with tab6:
    from components import render_strategies_tab
    render_strategies_tab(market_data)

with tab7:
    from components import render_replay_tab
    render_replay_tab(market_data)
    
# ============================================================
# STATUS BAR
# ============================================================
render_status_bar(
    connection_status="Auto-refresh: 60s",
    last_update=datetime.now().strftime("%H:%M:%S"),
)