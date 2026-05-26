"""
Energy & Oil Trading Dashboard
Main application entry point.
"""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Energy Trading Dashboard",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Header
st.title("Energy & Oil Trading Dashboard")
st.caption("Aakarsh Varshney  •  ICE & CME energy markets")

# Persistent top strip placeholder
st.divider()
cols = st.columns(8)
labels = ["WTI", "Brent", "WTI-Brent", "Henry Hub", "TTF", "3-2-1 Crack", "DXY", "Book Delta"]
for col, label in zip(cols, labels):
    with col:
        st.metric(label, "—", "—")
st.divider()

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1. Markets",
    "2. Fundamentals",
    "3. News & Events",
    "4. Models & Signals",
    "5. Risk & Book",
    "⭐ Replay",
])

with tab1:
    st.header("Markets")
    st.info("Price grid, forward curves, spreads, vol surface, execution. Coming soon.")

with tab2:
    st.header("Fundamentals & Flows")
    st.info("Inventories, refinery data, tanker tracking, OPEC nowcast. Coming soon.")

with tab3:
    st.header("News & Events")
    st.info("LLM-tagged news, event calendar, firms & traders stance. Coming soon.")

with tab4:
    st.header("Models & Signals")
    st.info("Fair value, dealer gamma map, regime engine, signal inbox. Coming soon.")

with tab5:
    st.header("Risk & Book")
    st.info("Positions, greeks, VaR, stress scenarios. Coming soon.")

with tab6:
    st.header("Replay Mode")
    st.info("Scrub through any past day with all data as it appeared. Coming soon.")