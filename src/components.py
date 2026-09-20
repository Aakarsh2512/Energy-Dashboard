"""
Reusable UI components for the Energy Trading Dashboard.
Each function renders a styled element. Keeps app.py clean.
"""

import streamlit as st
from pathlib import Path
import pandas as pd

def load_css():
    """Inject the custom CSS into the page. Call this once at the top of app.py."""
    css_path = Path(__file__).parent / "styles" / "custom.css"
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def render_header(title: str, subtitle: str, show_live_badge: bool = True):
    """
    Render the dashboard header with title, optional LIVE badge, and subtitle.
    """
    live_badge_html = '<span class="live-badge">Live</span>' if show_live_badge else ""

    st.markdown(
        f'''
        <div class="dashboard-header">
            <span class="dashboard-title">{title}</span>
            {live_badge_html}
        </div>
        <div class="dashboard-subtitle">{subtitle}</div>
        ''',
        unsafe_allow_html=True,
    )


def render_top_strip(items: list[dict]):
    """
    Render the persistent top strip of quotes.

    items: list of dicts like:
        {"label": "WTI", "value": "82.15", "change": "+0.42", "direction": "up"}
        direction is "up", "down", or "neutral"
    """
    # Arrow symbols by direction
    arrows = {
        "up": "▲",
        "down": "▼",
        "neutral": "▬",
    }

    html_parts = ['<div class="top-strip">']

    for item in items:
        direction = item.get("direction", "neutral")
        change_text = item.get("change", "")

        # Build the change indicator with an arrow
        if change_text:
            arrow = arrows.get(direction, "")
            change_html = (
                f'<span class="top-strip-change {direction}">'
                f'<span class="trend-arrow">{arrow}</span>'
                f'{change_text}'
                f'</span>'
            )
        else:
            change_html = ""

        html_parts.append(
            f'<div class="top-strip-item">'
            f'<span class="top-strip-label">{item["label"]}</span>'
            f'<span class="top-strip-value">{item["value"]}</span>'
            f'{change_html}'
            f'</div>'
        )

    html_parts.append('</div>')
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_panel(title: str, content_callback, is_unique: bool = False):
    """
    Render a panel with a title and content.

    title: panel title (uppercase will be applied via CSS)
    content_callback: a function that renders the panel content using Streamlit
    is_unique: if True, panel gets the gold-bordered "unique feature" styling
    """
    panel_class = "panel-unique" if is_unique else "panel"
    st.markdown(
        f'<div class="{panel_class}"><div class="panel-title">{title}</div>',
        unsafe_allow_html=True,
    )
    content_callback()
    st.markdown('</div>', unsafe_allow_html=True)


def render_status_bar(connection_status: str = "Live", last_update: str = "—"):
    """Footer-style status bar showing connection state and last update time."""
    st.markdown(
        f'<div class="status-bar">'
        f'<span><span class="status-indicator"></span>{connection_status}</span>'
        f'<span>Last update: {last_update}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
def render_price_grid(market_data: dict, instruments: list[dict]):
    """
    Render the Price Grid panel — compact 2-column layout.
    """
    from market_data import compute_zscore, zscore_to_color

    # Build all cards as HTML
    cards_html = ""
    for inst in instruments:
        data = market_data.get(inst["name"])
        if data is None:
            cards_html += _build_price_card_empty_html(inst["label"])
        else:
            z = compute_zscore(data["history"])
            color = zscore_to_color(z)
            cards_html += _build_price_card_html(
                label=inst["label"],
                value=data["latest"],
                change=data["change"],
                change_pct=data["change_pct"],
                direction=data["direction"],
                zscore=z,
                color=color,
                decimals=inst.get("decimals", 2),
            )

    st.markdown(
        f'''
        <div class="panel">
            <div class="panel-title">Price Grid</div>
            <div class="price-grid-2col">
                {cards_html}
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def _build_price_card_html(label, value, change, change_pct, direction, zscore, color, decimals):
    arrows = {"up": "▲", "down": "▼", "neutral": "▬"}
    arrow = arrows.get(direction, "")
    change_sign = "+" if change >= 0 else ""

    # Determine z-score severity class for styling
    abs_z = abs(zscore)
    if abs_z >= 2:
        z_severity = "z-extreme"
        z_label = "OVERSOLD" if zscore < 0 else "OVERBOUGHT"
    elif abs_z >= 1:
        z_severity = "z-elevated"
        z_label = "BELOW AVG" if zscore < 0 else "ABOVE AVG"
    else:
        z_severity = "z-neutral"
        z_label = "NEUTRAL"

    # Direction class for z-score colour (independent of price direction)
    if zscore < -1:
        z_color_class = "z-cold"
    elif zscore > 1:
        z_color_class = "z-hot"
    else:
        z_color_class = "z-mid"

    return (
        f'<div class="price-card-compact" style="border-left: 4px solid {color};">'
        f'<div class="price-card-header">'
        f'<span class="price-card-label">{label}</span>'
        f'<div class="zscore-badge {z_severity} {z_color_class}">'
        f'<span class="zscore-value">{zscore:+.2f}σ</span>'
        f'<span class="zscore-label">{z_label}</span>'
        f'</div>'
        f'</div>'
        f'<div class="price-card-value">{value:.{decimals}f}</div>'
        f'<div class="price-card-change {direction}">'
        f'<span>{arrow}</span>'
        f'<span>{change_sign}{change:.{decimals}f}</span>'
        f'<span class="price-card-pct">({change_sign}{change_pct:.2f}%)</span>'
        f'</div>'
        f'</div>'
    )


def _build_price_card_empty_html(label):
    return (
        f'<div class="price-card-compact" style="border-left: 3px solid #2F3E50;">'
        f'<div class="price-card-header">'
        f'<span class="price-card-label">{label}</span>'
        f'</div>'
        f'<div class="price-card-value muted">—</div>'
        f'<div class="price-card-change neutral">no data</div>'
        f'</div>'
    )


# Keep the old helpers for compatibility but they're unused now
def _render_price_card(*args, **kwargs):
    pass

def _render_price_card_empty(*args, **kwargs):
    pass


def render_macro_panel(market_data: dict):
    """Render the cross-asset macro panel — compact horizontal tiles."""

    macros = [
        {"name": "DXY",      "label": "DXY",      "decimals": 2},
        {"name": "Gold",     "label": "Gold",     "decimals": 2},
        {"name": "Copper",   "label": "Copper",   "decimals": 3},
        {"name": "S&P 500",  "label": "S&P 500",  "decimals": 2},
        {"name": "VIX",      "label": "VIX",      "decimals": 2},
    ]

    tiles_html = ""
    for macro in macros:
        data = market_data.get(macro["name"])
        if data is None:
            tiles_html += (
                f'<div class="macro-tile">'
                f'<div class="macro-tile-label">{macro["label"]}</div>'
                f'<div class="macro-tile-value muted">—</div>'
                f'<div class="macro-tile-change neutral">no data</div>'
                f'</div>'
            )
        else:
            arrows = {"up": "▲", "down": "▼", "neutral": "▬"}
            arrow = arrows.get(data["direction"], "")
            sign = "+" if data["change_pct"] >= 0 else ""
            tiles_html += (
                f'<div class="macro-tile">'
                f'<div class="macro-tile-label">{macro["label"]}</div>'
                f'<div class="macro-tile-value">{data["latest"]:.{macro["decimals"]}f}</div>'
                f'<div class="macro-tile-change {data["direction"]}">'
                f'{arrow} {sign}{data["change_pct"]:.2f}%'
                f'</div>'
                f'</div>'
            )

    st.markdown(
        f'''
        <div class="panel">
            <div class="panel-title">Cross-Asset Macro</div>
            <div class="macro-grid">
                {tiles_html}
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
def _render_macro_tile(label, value, change_pct, direction, decimals):
    arrows = {"up": "▲", "down": "▼", "neutral": "▬"}
    arrow = arrows.get(direction, "")
    sign = "+" if change_pct >= 0 else ""

    st.markdown(
        f'''
        <div class="macro-tile">
            <div class="macro-tile-label">{label}</div>
            <div class="macro-tile-value">{value:.{decimals}f}</div>
            <div class="macro-tile-change {direction}">
                {arrow} {sign}{change_pct:.2f}%
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def render_execution_panel():
    """Render the execution & microstructure panel — compact mock DOM and order stats."""
    import random
    from datetime import datetime

    random.seed(datetime.now().minute)

    # Build the DOM HTML as a single string so it stays inside the panel
    centre = 91.59

    asks = []
    for i in range(5, 0, -1):
        price = round(centre + i * 0.02, 2)
        size = random.randint(20, 250)
        asks.append({"price": price, "size": size})

    bids = []
    for i in range(1, 6):
        price = round(centre - i * 0.02, 2)
        size = random.randint(20, 250)
        bids.append({"price": price, "size": size})

    all_rows = asks + [{"price": None, "size": None, "spread": True}] + bids
    max_size = max(r["size"] for r in all_rows if r.get("size"))

    # Build DOM rows as HTML string
    dom_rows_html = ""
    for row in all_rows:
        if row.get("spread"):
            dom_rows_html += (
                '<div class="dom-spread-row">'
                '<span class="dom-spread-label">SPREAD</span>'
                '<span class="dom-spread-value">0.02</span>'
                '</div>'
            )
        else:
            bar_width = (row["size"] / max_size) * 100
            is_ask = row in asks
            side_class = "dom-ask" if is_ask else "dom-bid"
            dom_rows_html += (
                f'<div class="dom-row {side_class}">'
                f'<div class="dom-bar" style="width:{bar_width}%;"></div>'
                f'<span class="dom-price">{row["price"]:.2f}</span>'
                f'<span class="dom-size">{row["size"]}</span>'
                f'</div>'
            )

    # Calculate imbalance
    bids_total = sum(r["size"] for r in bids)
    asks_total = sum(r["size"] for r in asks)
    total = bids_total + asks_total
    imbalance = ((bids_total - asks_total) / total) * 100 if total > 0 else 0
    imb_dir = "up" if imbalance > 0 else ("down" if imbalance < 0 else "neutral")
    sign = "+" if imbalance >= 0 else ""

    # Build the entire panel in one HTML block so structure stays clean
    st.markdown(
        f'''
        <div class="panel exec-panel">
            <div class="panel-title">Execution &amp; Microstructure (WTI front)</div>
            <div class="exec-grid">
                <div class="dom-container">
                    {dom_rows_html}
                </div>
                <div class="exec-stats">
                    <div class="exec-stat-row">
                        <span class="exec-stat-label">Bid Imbalance</span>
                        <span class="exec-stat-value {imb_dir}">{sign}{imbalance:.1f}%</span>
                    </div>
                    <div class="exec-stat-row">
                        <span class="exec-stat-label">Working</span>
                        <span class="exec-stat-value">3</span>
                    </div>
                    <div class="exec-stat-row">
                        <span class="exec-stat-label">Fills Today</span>
                        <span class="exec-stat-value">47</span>
                    </div>
                    <div class="exec-stat-row">
                        <span class="exec-stat-label">Slippage</span>
                        <span class="exec-stat-value down">-0.3 bp</span>
                    </div>
                    <div class="exec-stat-row">
                        <span class="exec-stat-label">Liquidity</span>
                        <span class="exec-stat-value">87/100</span>
                    </div>
                </div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
def render_forward_curve_panel(market_data: dict):
    """Render the forward curve panel with today/yesterday/last week overlays."""
    import plotly.graph_objects as go
    from forward_curves import build_curves_with_history, classify_curve_structure

    # Default to WTI; we'll add a selector later
    instrument_name = st.selectbox(
        "Forward curve instrument",
        ["WTI", "Brent"],
        index=1,  # Default to Brent so the real data shows by default
        key="fwd_curve_instrument",
        label_visibility="collapsed",
    )
    curves = build_curves_with_history(instrument_name, market_data)

    if curves is None or "today" not in curves:
        st.markdown(
            '<div class="panel"><div class="panel-title">Forward Curve</div>'
            '<div style="padding:20px; text-align:center; color:#8B9DAE;">No data</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    structure = classify_curve_structure(curves["today"])
    structure_color = {
        "CONTANGO": "#E67E22",
        "BACKWARDATION": "#5BA8D9",
        "FLAT": "#7F8C8D",
    }.get(structure, "#7F8C8D")

    # Panel header (we put the Plotly chart inside a Streamlit container)
    st.markdown(
        f'<div class="panel" style="padding-bottom:6px;">'
        f'<div class="panel-title" style="display:flex; justify-content:space-between; align-items:center;">'
        f'<span>Forward Curve — {instrument_name}</span>'
        f'<span style="font-size:0.7rem; padding:2px 8px; border-radius:3px; '
        f'background-color:rgba(255,255,255,0.05); color:{structure_color};">'
        f'{structure}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Build the chart
    fig = go.Figure()

    style = {
        "today":     {"color": "#2E75B6", "width": 2.5, "dash": "solid",  "name": "Today"},
        "yesterday": {"color": "#5B6E80", "width": 1.5, "dash": "dash",   "name": "Yesterday"},
        "last_week": {"color": "#3D4F62", "width": 1.2, "dash": "dot",    "name": "Last Week"},
    }

    for key in ["last_week", "yesterday", "today"]:  # bottom to top draw order
        if key not in curves:
            continue
        curve = curves[key]
        tenors = [m for m, _ in curve]
        prices = [p for _, p in curve]
        s = style[key]
        fig.add_trace(go.Scatter(
            x=tenors,
            y=prices,
            mode='lines+markers' if key == "today" else 'lines',
            line=dict(color=s["color"], width=s["width"], dash=s["dash"]),
            marker=dict(size=4, color=s["color"]) if key == "today" else None,
            name=s["name"],
        ))

    fig.update_layout(
        height=300,
        margin=dict(l=40, r=20, t=10, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8B9DAE", family="Inter, sans-serif", size=11),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.12,
            xanchor="right",
            x=1,
            font=dict(size=10),
        ),
        xaxis=dict(
            title="Tenor (months)",
            gridcolor="rgba(31, 58, 92, 0.4)",
            zeroline=False,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            title="Price",
            gridcolor="rgba(31, 58, 92, 0.4)",
            zeroline=False,
            tickfont=dict(size=10),
        ),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown('</div>', unsafe_allow_html=True)


def render_calendar_spreads_panel(market_data: dict):
    """Render calendar spreads with z-score-based mean-reversion flags."""
    from forward_curves import build_curve_for_instrument, compute_calendar_spreads

    instrument_name = "WTI"
    curve = build_curve_for_instrument(instrument_name, market_data)

    if curve is None:
        return

    spreads = compute_calendar_spreads(curve)

    if not spreads:
        return

    rows_html = ""
    for name, value in spreads.items():
        # Classify based on simple thresholds (in $/bbl for WTI)
        abs_v = abs(value)
        if abs_v >= 3:
            flag_class = "spread-extreme"
            flag_text = "WIDE"
        elif abs_v >= 1.5:
            flag_class = "spread-elevated"
            flag_text = "ELEVATED"
        else:
            flag_class = "spread-normal"
            flag_text = "NORMAL"

        sign = "+" if value >= 0 else ""
        rows_html += (
            f'<div class="spread-row">'
            f'<span class="spread-name">{name}</span>'
            f'<span class="spread-value">{sign}{value:.2f}</span>'
            f'<span class="spread-flag {flag_class}">{flag_text}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="panel">'
        f'<div class="panel-title">Calendar Spreads — {instrument_name}</div>'
        f'<div class="spread-list">{rows_html}</div>'
        f'<div class="spread-footnote">Flags based on absolute spread vs ±$1.5 / ±$3.0 thresholds. '
        f'Real desks would z-score against history.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_interproduct_spreads_panel(market_data: dict):
    """Render inter-product spreads (WTI-Brent, 3-2-1 Crack, etc.)"""
    from forward_curves import compute_inter_product_spreads

    spreads = compute_inter_product_spreads(market_data)

    if not spreads:
        return

    rows_html = ""
    for name, info in spreads.items():
        value = info["value"]
        prev = info["previous"]
        change = round(value - prev, 2)
        unit = info["unit"]

        sign = "+" if value >= 0 else ""
        change_sign = "+" if change >= 0 else ""

        direction = "up" if change > 0 else ("down" if change < 0 else "neutral")
        arrows = {"up": "▲", "down": "▼", "neutral": "▬"}
        arrow = arrows[direction]

        rows_html += (
            f'<div class="spread-row">'
            f'<span class="spread-name">{name}</span>'
            f'<span class="spread-value">{sign}{value:.2f}</span>'
            f'<span class="spread-change {direction}">{arrow} {change_sign}{change:.2f}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="panel">'
        f'<div class="panel-title">Inter-Product Spreads</div>'
        f'<div class="spread-list">{rows_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    
def render_inventory_tab(market_data: dict):
    import plotly.graph_objects as go
    from eia_data import (
        INVENTORY_SERIES, fetch_series,
        build_seasonality_envelope, compute_surprise, current_vs_5yr_avg
    )

    # ============================================================
    # CONTROLS — instrument selector and date range
    # ============================================================

    instrument_labels = {k: v["label"] for k, v in INVENTORY_SERIES.items()}

    col_sel, col_range, col_blank = st.columns([2, 1.5, 3])

    with col_sel:
        selected_key = st.selectbox(
            "Instrument",
            options=list(instrument_labels.keys()),
            format_func=lambda k: instrument_labels[k],
            label_visibility="collapsed",
        )

    with col_range:
        date_range = st.selectbox(
            "Range",
            options=["4 weeks", "12 weeks", "52 weeks", "5 years", "All"],
            index=3,
            label_visibility="collapsed",
        )

    # ============================================================
    # FETCH
    # ============================================================

    df = fetch_series(selected_key, start_date="2018-01-01")

    if df is None or len(df) == 0:
        st.markdown(
            '<div class="panel">'
            '<div class="panel-title">Inventory</div>'
            '<div style="color:#8B9DAE; padding:30px; text-align:center;">'
            'Could not fetch EIA data. Check your API key in .env'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    spec = INVENTORY_SERIES[selected_key]

    # Filter to date range
    range_map = {
        "4 weeks": 28, "12 weeks": 84, "52 weeks": 365,
        "5 years": 365 * 5, "All": None,
    }
    days_back = range_map[date_range]
    if days_back:
        cutoff = df["date"].max() - pd.Timedelta(days=days_back)
        df_filtered = df[df["date"] >= cutoff]
    else:
        df_filtered = df

    # ============================================================
    # LAYOUT: chart left, stats right
    # ============================================================

    left, right = st.columns([2.4, 1])

    with left:
        st.markdown(
            f'<div class="panel" style="padding-bottom:6px;">'
            f'<div class="panel-title">{spec["label"]}</div>',
            unsafe_allow_html=True,
        )

        # Build the main chart with 5-year envelope
        envelope = build_seasonality_envelope(df, years_back=5)

        fig = go.Figure()

        # 5-year max (invisible top of band)
        fig.add_trace(go.Scatter(
            x=envelope["week"], y=envelope["hist_max"],
            line=dict(width=0), showlegend=False, hoverinfo='skip',
        ))
        # 5-year min + fill
        fig.add_trace(go.Scatter(
            x=envelope["week"], y=envelope["hist_min"],
            line=dict(width=0), fill='tonexty',
            fillcolor='rgba(46, 117, 182, 0.15)',
            name='5-yr range', hoverinfo='skip',
        ))
        # 5-year average
        fig.add_trace(go.Scatter(
            x=envelope["week"], y=envelope["hist_avg"],
            line=dict(color='#7F8C8D', width=1.5, dash='dash'),
            name='5-yr avg',
        ))
        # Current year
        current_only = envelope[["week", "current"]].dropna()
        fig.add_trace(go.Scatter(
            x=current_only["week"], y=current_only["current"],
            line=dict(color=spec["color"], width=2.5),
            name='Current year',
            mode='lines+markers',
            marker=dict(size=4),
        ))

        fig.update_layout(
            height=380,
            margin=dict(l=40, r=20, t=10, b=40),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8B9DAE", family="Inter, sans-serif", size=11),
            legend=dict(
                orientation="h", yanchor="top", y=1.12, xanchor="right", x=1,
                font=dict(size=10),
            ),
            xaxis=dict(
                title="Week of year",
                gridcolor="rgba(31, 58, 92, 0.4)",
                zeroline=False,
            ),
            yaxis=dict(
                title=spec["unit"],
                gridcolor="rgba(31, 58, 92, 0.4)",
                zeroline=False,
            ),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        # Stat panels
        comparison = current_vs_5yr_avg(df)
        surprise = compute_surprise(df)

        # Current vs 5-yr avg
        if comparison:
            diff_color = "#E74C3C" if comparison["is_above_avg"] else "#5BA8D9"
            arrow = "▲" if comparison["is_above_avg"] else "▼"
            sign = "+" if comparison["diff"] > 0 else ""
            unit = spec["unit"]

            st.markdown(
                f'<div class="panel">'
                f'<div class="panel-title">Current vs 5-yr avg</div>'
                f'<div class="big-stat">'
                f'<span class="big-stat-value">{comparison["current"]:,.0f}</span>'
                f'<span class="big-stat-unit">{unit}</span>'
                f'</div>'
                f'<div class="big-stat-context" style="color:{diff_color};">'
                f'{arrow} {sign}{comparison["diff"]:,.0f} {unit} '
                f'({sign}{comparison["diff_pct"]:.1f}%) vs 5-yr avg'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Surprise
        if surprise:
            abs_z = abs(surprise["zscore"])
            if abs_z >= 2:
                surprise_label = "MAJOR SURPRISE"
                surprise_class = "spread-extreme"
            elif abs_z >= 1:
                surprise_label = "ELEVATED"
                surprise_class = "spread-elevated"
            else:
                surprise_label = "AS EXPECTED"
                surprise_class = "spread-normal"

            sign_act = "+" if surprise["actual_change"] >= 0 else ""
            sign_exp = "+" if surprise["expected_change"] >= 0 else ""

            st.markdown(
                f'<div class="panel">'
                f'<div class="panel-title">Latest release surprise</div>'
                f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
                f'<span style="color:#8B9DAE; font-size:0.72rem;">Release date</span>'
                f'<span style="color:#E8EEF4; font-family:JetBrains Mono; font-size:0.78rem;">'
                f'{surprise["date"].strftime("%b %d %Y")}</span>'
                f'</div>'
                f'<div style="display:flex; justify-content:space-between; margin-bottom:6px;">'
                f'<span style="color:#8B9DAE; font-size:0.72rem;">Actual change</span>'
                f'<span style="color:#E8EEF4; font-family:JetBrains Mono; font-size:0.78rem;">'
                f'{sign_act}{surprise["actual_change"]:,.0f}</span>'
                f'</div>'
                f'<div style="display:flex; justify-content:space-between; margin-bottom:6px;">'
                f'<span style="color:#8B9DAE; font-size:0.72rem;">4-wk avg change</span>'
                f'<span style="color:#8B9DAE; font-family:JetBrains Mono; font-size:0.78rem;">'
                f'{sign_exp}{surprise["expected_change"]:,.0f}</span>'
                f'</div>'
                f'<div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">'
                f'<span style="color:#8B9DAE; font-size:0.72rem;">Surprise (z-score)</span>'
                f'<span class="spread-flag {surprise_class}">{surprise["zscore"]:+.2f}σ • {surprise_label}</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ============================================================
    # SECOND ROW: European gas storage
    # ============================================================

    render_european_gas_storage_panel()


def render_european_gas_storage_panel():
    """Render European gas storage from GIE AGSI+."""
    import plotly.graph_objects as go
    from european_storage import fetch_european_storage_overall

    df = fetch_european_storage_overall()

    if df is None or len(df) == 0:
        return

    latest = df.iloc[-1]
    latest_pct = latest["full_pct"]

    # Color based on storage level (winter risk indicator)
    if latest_pct >= 80:
        pct_color = "#2ECC71"
        pct_label = "WELL-SUPPLIED"
    elif latest_pct >= 50:
        pct_color = "#F39C12"
        pct_label = "MODERATE"
    else:
        pct_color = "#E74C3C"
        pct_label = "LOW — winter risk"

    left, right = st.columns([2.4, 1])

    with left:
        st.markdown(
            '<div class="panel" style="padding-bottom:6px;">'
            '<div class="panel-title">European Gas Storage (GIE AGSI+, free)</div>',
            unsafe_allow_html=True,
        )

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["full_pct"],
            mode='lines',
            line=dict(color='#9B59B6', width=2.5),
            fill='tozeroy',
            fillcolor='rgba(155, 89, 182, 0.12)',
            name='% Full',
        ))
        fig.add_hline(y=80, line_dash="dot", line_color="#2ECC71",
                      annotation_text="80% — well-supplied",
                      annotation_position="right",
                      annotation_font_color="#2ECC71",
                      annotation_font_size=10)
        fig.add_hline(y=50, line_dash="dot", line_color="#E74C3C",
                      annotation_text="50% — winter risk",
                      annotation_position="right",
                      annotation_font_color="#E74C3C",
                      annotation_font_size=10)

        fig.update_layout(
            height=300,
            margin=dict(l=40, r=20, t=10, b=40),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8B9DAE", family="Inter, sans-serif", size=11),
            showlegend=False,
            xaxis=dict(gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False),
            yaxis=dict(title="% full", gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False, range=[0, 105]),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown(
            f'<div class="panel">'
            f'<div class="panel-title">Current storage</div>'
            f'<div class="big-stat">'
            f'<span class="big-stat-value">{latest_pct:.1f}</span>'
            f'<span class="big-stat-unit">%</span>'
            f'</div>'
            f'<div class="big-stat-context" style="color:{pct_color};">'
            f'{pct_label}'
            f'</div>'
            f'<div style="display:flex; justify-content:space-between; margin-top:10px; '
            f'padding-top:8px; border-top:1px solid #1F3A5C;">'
            f'<span style="color:#8B9DAE; font-size:0.72rem;">Total</span>'
            f'<span style="color:#E8EEF4; font-family:JetBrains Mono; font-size:0.78rem;">'
            f'{latest["gas_in_storage"]:,.0f} TWh</span>'
            f'</div>'
            f'<div style="display:flex; justify-content:space-between; margin-top:6px;">'
            f'<span style="color:#8B9DAE; font-size:0.72rem;">As of</span>'
            f'<span style="color:#E8EEF4; font-family:JetBrains Mono; font-size:0.78rem;">'
            f'{latest["date"].strftime("%b %d")}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

def render_seasonality_tab(market_data: dict):
    """Render the full Seasonality tab."""
    import plotly.graph_objects as go
    import plotly.express as px
    from seasonality import (
        SEASONALITY_INSTRUMENTS, MONTH_NAMES,
        fetch_long_history, build_year_overlay, build_monthly_returns,
        build_average_seasonal_path, best_worst_months,
        current_month_seasonal_context,
    )

    # ============================================================
    # CONTROLS
    # ============================================================

    inst_labels = {k: v["label"] for k, v in SEASONALITY_INSTRUMENTS.items()}

    col_sel, col_years, col_blank = st.columns([2, 1.5, 3])

    with col_sel:
        selected = st.selectbox(
            "Instrument",
            options=list(inst_labels.keys()),
            format_func=lambda k: inst_labels[k],
            label_visibility="collapsed",
            key="seasonality_instrument",
        )

    with col_years:
        years_show = st.selectbox(
            "Years to overlay",
            options=[3, 5, 8],
            index=1,
            label_visibility="collapsed",
            key="seasonality_years",
        )

    ticker = SEASONALITY_INSTRUMENTS[selected]["ticker"]
    df = fetch_long_history(ticker, years=8)

    if df is None:
        st.markdown(
            '<div class="panel"><div class="panel-title">Seasonality</div>'
            '<div style="color:#8B9DAE; padding:30px; text-align:center;">'
            'Could not fetch historical data.</div></div>',
            unsafe_allow_html=True,
        )
        return

    # ============================================================
    # ROW 1: Year overlay (left) + current month context (right)
    # ============================================================

    left, right = st.columns([2.4, 1])

    with left:
        st.markdown(
            f'<div class="panel" style="padding-bottom:6px;">'
            f'<div class="panel-title">{inst_labels[selected]} — Year Overlay (normalized)</div>',
            unsafe_allow_html=True,
        )

        overlays = build_year_overlay(df, years_to_show=years_show)
        current_year = max(overlays.keys())

        fig = go.Figure()
        for year, data in overlays.items():
            is_current = (year == current_year)
            fig.add_trace(go.Scatter(
                x=data["day_of_year"],
                y=data["normalized"],
                name=str(year),
                line=dict(
                    width=3 if is_current else 1.2,
                    color="#E67E22" if is_current else "#5B6E80",
                ),
                opacity=1.0 if is_current else 0.4,
            ))

        fig.update_layout(
            height=360,
            margin=dict(l=40, r=20, t=10, b=40),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8B9DAE", family="Inter, sans-serif", size=11),
            legend=dict(orientation="h", yanchor="top", y=1.12, font=dict(size=10)),
            xaxis=dict(title="Day of year", gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False),
            yaxis=dict(title="% of year start (100 = Jan 1)", gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        context = current_month_seasonal_context(df)
        if context:
            ret_color = "#2ECC71" if context["avg_return"] > 0 else "#E74C3C"
            ret_sign = "+" if context["avg_return"] > 0 else ""

            st.markdown(
                f'<div class="panel">'
                f'<div class="panel-title">{context["month_name"]} — typical behaviour</div>'
                f'<div class="big-stat">'
                f'<span class="big-stat-value" style="color:{ret_color};">'
                f'{ret_sign}{context["avg_return"]:.1f}%</span>'
                f'</div>'
                f'<div class="big-stat-context" style="color:#8B9DAE;">'
                f'avg return in {context["month_name"]} over {context["years_count"]} years'
                f'</div>'
                f'<div style="display:flex; justify-content:space-between; margin-top:12px; '
                f'padding-top:8px; border-top:1px solid #1F3A5C;">'
                f'<span style="color:#8B9DAE; font-size:0.72rem;">Win rate</span>'
                f'<span style="color:#E8EEF4; font-family:JetBrains Mono; font-size:0.85rem;">'
                f'{context["win_rate"]:.0f}%</span>'
                f'</div>'
                f'<div style="color:#5B6E80; font-size:0.65rem; margin-top:8px; font-style:italic;">'
                f'% of past years where {context["month_name"]} closed positive'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Best/worst months
        monthly_pivot = build_monthly_returns(df)
        if monthly_pivot is not None:
            bw = best_worst_months(monthly_pivot)
            st.markdown(
                f'<div class="panel">'
                f'<div class="panel-title">Seasonal extremes</div>'
                f'<div style="display:flex; justify-content:space-between; margin-bottom:8px;">'
                f'<span style="color:#8B9DAE; font-size:0.72rem;">Best month</span>'
                f'<span style="color:#2ECC71; font-family:JetBrains Mono; font-size:0.8rem;">'
                f'{bw["best_month"]} (+{bw["best_return"]:.1f}%)</span>'
                f'</div>'
                f'<div style="display:flex; justify-content:space-between;">'
                f'<span style="color:#8B9DAE; font-size:0.72rem;">Worst month</span>'
                f'<span style="color:#E74C3C; font-family:JetBrains Mono; font-size:0.8rem;">'
                f'{bw["worst_month"]} ({bw["worst_return"]:.1f}%)</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ============================================================
    # ROW 2: Monthly returns heatmap (full width)
    # ============================================================

    # For the heatmap specifically, use only complete years (clean alignment)
    heatmap_pivot = build_monthly_returns(df, drop_partial_years=True)

    if heatmap_pivot is not None and len(heatmap_pivot) > 0:
        st.markdown(
            '<div class="panel" style="padding-bottom:6px;">'
            '<div class="panel-title">Monthly Returns Heatmap (complete years only)</div>',
            unsafe_allow_html=True,
        )

        heatmap_data = heatmap_pivot.copy()
        heatmap_data.columns = [MONTH_NAMES[int(c) - 1] for c in heatmap_data.columns]
        heatmap_data = heatmap_data.sort_index(ascending=False)  # recent years on top

        fig = px.imshow(
            heatmap_data,
            color_continuous_scale=["#C0392B", "#142638", "#27AE60"],
            color_continuous_midpoint=0,
            aspect="auto",
            labels=dict(color="Return %"),
            text_auto=".1f",
        )
        fig.update_layout(
            height=320,
            margin=dict(l=40, r=20, t=10, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8B9DAE", family="Inter, sans-serif", size=10),
            coloraxis_colorbar=dict(title="%", thickness=12, len=0.7),
        )
        fig.update_xaxes(side="top", tickfont=dict(size=10))
        fig.update_yaxes(tickfont=dict(size=10))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # ============================================================
    # ROW 3: Average seasonal path with confidence band
    # ============================================================

    seasonal = build_average_seasonal_path(df, years_back=8)
    if seasonal is not None:
        st.markdown(
            '<div class="panel" style="padding-bottom:6px;">'
            '<div class="panel-title">Average Seasonal Path (8-year, with ±1σ band)</div>',
            unsafe_allow_html=True,
        )

        fig = go.Figure()
        # Upper band
        fig.add_trace(go.Scatter(
            x=seasonal["day_of_year"], y=seasonal["upper"],
            line=dict(width=0), showlegend=False, hoverinfo='skip',
        ))
        # Lower band + fill
        fig.add_trace(go.Scatter(
            x=seasonal["day_of_year"], y=seasonal["lower"],
            line=dict(width=0), fill='tonexty',
            fillcolor='rgba(46, 117, 182, 0.15)',
            name='±1σ', hoverinfo='skip',
        ))
        # Average
        fig.add_trace(go.Scatter(
            x=seasonal["day_of_year"], y=seasonal["avg"],
            line=dict(color="#E67E22", width=2.5),
            name='Average path',
        ))

        fig.update_layout(
            height=320,
            margin=dict(l=40, r=20, t=10, b=40),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8B9DAE", family="Inter, sans-serif", size=11),
            showlegend=False,
            xaxis=dict(title="Day of year", gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False),
            yaxis=dict(title="% of year start (100 = Jan 1)", gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

def render_news_tab(market_data: dict):
    """Render News & Events tab. Reads from background worker cache."""
    from news_data import get_tagged_news, get_worker_status, summarize_sentiment

    headlines = get_tagged_news()
    status = get_worker_status()

    if not headlines:
        st.markdown(
            '<div class="panel"><div class="panel-title">News</div>'
            '<div style="color:#8B9DAE; padding:30px; text-align:center;">'
            '<b>Starting news pipeline...</b><br>'
            f'<span style="font-size:0.78rem; margin-top:6px; display:inline-block;">'
            f'Status: {status["status"]}. Refresh the page in 10-15 seconds.'
            f'</span>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    # ============================================================
    # WORKER STATUS BAR
    # ============================================================
    tagged_count = status["tagged_count"]
    total = status["headline_count"]
    tag_pct = (tagged_count / total * 100) if total > 0 else 0
    in_progress = status["tag_in_progress"]
    progress_emoji = "⟳" if in_progress else "✓"

    last_fetch_str = (
        status["last_fetch"].strftime("%H:%M:%S")
        if status["last_fetch"] else "—"
    )

    st.markdown(
        f'<div class="panel" style="margin-bottom:8px;">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; gap:14px;">'
        f'<div style="color:#8B9DAE; font-size:0.72rem; font-family:JetBrains Mono;">'
        f'<span style="color:#2ECC71;">{progress_emoji}</span> '
        f'LLM tagging: <b style="color:#E5EBF0;">{tagged_count}/{total}</b> '
        f'<span style="color:#5B6E80;">({tag_pct:.0f}%)</span> · '
        f'last RSS fetch: <b style="color:#E5EBF0;">{last_fetch_str}</b>'
        f'</div>'
        f'<div style="color:#5B6E80; font-size:0.65rem; font-style:italic;">'
        f'Background worker · Gemini 2.5 Flash-Lite'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ============================================================
    # KEYWORD FILTER
    # ============================================================
    col_search, col_count, _ = st.columns([3, 1.5, 2])

    with col_search:
        keyword = st.text_input(
            "Filter by keyword",
            placeholder="Type keywords to filter (e.g. OPEC, Russia, inventory)",
            label_visibility="collapsed",
            key="news_keyword_filter",
        )

    if keyword and keyword.strip():
        kw_lower = keyword.strip().lower()
        kw_list = [k.strip() for k in kw_lower.replace(",", " ").split() if k.strip()]
        filtered = []
        for h in headlines:
            title = h.get("title", "").lower()
            reaction = h.get("tags", {}).get("reaction", "").lower()
            if any(kw in title or kw in reaction for kw in kw_list):
                filtered.append(h)
    else:
        filtered = headlines

    with col_count:
        st.markdown(
            f'<div style="padding:6px 0; color:#8B9DAE; font-size:0.78rem; '
            f'font-family:JetBrains Mono;">'
            f'{len(filtered)} of {len(headlines)} headlines'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ============================================================
    # SENTIMENT SUMMARY (only over tagged headlines)
    # ============================================================
    sentiment = summarize_sentiment(filtered)
    net = sentiment["net_score"]

    if sentiment["total"] == 0:
        net_color = "#8B9DAE"
        net_label = "AWAITING TAGS"
        net_display = "—"
    else:
        if net > 15:
            net_color = "#2ECC71"
            net_label = "BULLISH BIAS"
        elif net < -15:
            net_color = "#E74C3C"
            net_label = "BEARISH BIAS"
        else:
            net_color = "#8B9DAE"
            net_label = "MIXED / NEUTRAL"
        net_display = f"{net:+.0f}"

    filter_note = f' (filtered by "{keyword}")' if keyword and keyword.strip() else ""

    st.markdown(
        f'<div class="panel">'
        f'<div class="panel-title">★ LLM News Sentiment{filter_note}</div>'
        f'<div style="display:flex; align-items:center; gap:24px; flex-wrap:wrap;">'
        f'<div>'
        f'<span style="font-size:1.6rem; font-weight:700; color:{net_color}; '
        f'font-family:JetBrains Mono;">{net_display}</span>'
        f'<span style="color:#8B9DAE; font-size:0.7rem; margin-left:6px;">net score</span>'
        f'</div>'
        f'<div style="padding:4px 12px; border-radius:4px; background:rgba(255,255,255,0.05); '
        f'color:{net_color}; font-size:0.7rem; font-weight:700; letter-spacing:0.5px;">{net_label}</div>'
        f'<div style="display:flex; gap:16px; font-size:0.78rem; font-family:JetBrains Mono;">'
        f'<span style="color:#2ECC71;">▲ {sentiment["bullish"]} bullish</span>'
        f'<span style="color:#E74C3C;">▼ {sentiment["bearish"]} bearish</span>'
        f'<span style="color:#8B9DAE;">▬ {sentiment["neutral"]} neutral</span>'
        f'</div>'
        f'</div>'
        f'<div style="color:#5B6E80; font-size:0.65rem; margin-top:8px; font-style:italic;">'
        f'Live from FinancialJuice. Tagged by Gemini 2.5 Flash-Lite in a background worker thread.'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ============================================================
    # HEADLINES LIST
    # ============================================================
    if not filtered:
        st.markdown(
            f'<div class="panel"><div class="panel-title">Headlines</div>'
            f'<div style="color:#8B9DAE; padding:30px; text-align:center;">'
            f'No headlines match "{keyword}".'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        '<div class="panel"><div class="panel-title">Headlines</div>',
        unsafe_allow_html=True,
    )

    for item in filtered:
        _render_news_card(item)

    st.markdown('</div>', unsafe_allow_html=True)


def _render_news_card(item: dict):
    """Render a single news card with tagging visualization."""
    tags = item.get("tags", {})
    is_tagged = item.get("is_tagged", False)
    direction = tags.get("direction", "neutral")
    magnitude = tags.get("magnitude", "minor")
    confidence = tags.get("confidence", 0.0)
    reaction = tags.get("reaction", "")
    contracts = tags.get("contracts", [])

    arrows = {"bullish": "▲", "bearish": "▼", "neutral": "▬"}
    arrow = arrows.get(direction, "▬")
    colors = {"bullish": "#2ECC71", "bearish": "#E74C3C", "neutral": "#8B9DAE"}
    color = colors.get(direction, "#8B9DAE")

    title = item.get("title", "")
    published = item.get("published", "")
    published_short = published[:25] if published else ""

    # Border style based on tagged state
    if is_tagged:
        border_style = f"border-left:2px solid {color};"
        tagged_state_html = ""
    else:
        border_style = "border-left:2px dashed #5B6E80;"
        tagged_state_html = '<span style="font-size:0.6rem; color:#5B6E80; font-style:italic; margin-left:6px;">pending tag</span>'

    # Contracts row (only shown if contracts exist)
    if contracts:
        contracts_str = " · ".join(contracts)
        contracts_html = f'<div style="color:#5BA8D9; font-size:0.66rem; margin-top:3px; font-family:JetBrains Mono;">{contracts_str}</div>'
    else:
        contracts_html = ""

    # Build the full card HTML in pieces (avoids messy f-string escaping)
    card_html = (
        f'<div class="news-card" style="{border_style}">'
        f'<div class="news-card-top">'
        f'<span style="color:{color}; font-weight:700; font-size:0.74rem; font-family:JetBrains Mono;">{arrow} {direction.upper()}</span>'
        f'<span class="news-mag-badge">{magnitude.upper()}</span>'
        f'<span style="color:#8B9DAE; font-size:0.62rem; margin-left:6px;">conf {confidence*100:.0f}%</span>'
        f'{tagged_state_html}'
        f'<span style="margin-left:auto; color:#5B6E80; font-size:0.62rem; font-family:JetBrains Mono;">{published_short}</span>'
        f'</div>'
        f'<div class="news-title">{title}</div>'
        f'<div style="color:#8B9DAE; font-size:0.74rem; margin-top:4px; font-style:italic;">→ {reaction}</div>'
        f'{contracts_html}'
        f'</div>'
    )

    st.markdown(card_html, unsafe_allow_html=True)
    


def render_news_compact(market_data: dict, max_items: int = 5):
    """Compact news panel for Markets tab. Reads from worker cache."""
    from news_data import get_tagged_news

    try:
        headlines = get_tagged_news()
    except Exception:
        headlines = []

    if not headlines:
        st.markdown(
            '<div class="panel">'
            '<div class="panel-title">Live News Feed</div>'
            '<div style="color:#8B9DAE; padding:14px; text-align:center; font-size:0.78rem;">'
            'News pipeline starting...<br>'
            '<span style="font-size:0.66rem; color:#5B6E80;">'
            'Headlines arrive within ~15 seconds.</span>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    # Prioritize tagged items; if not enough tagged, fill with untagged
    tagged_items = [h for h in headlines if h.get("is_tagged")]
    untagged_items = [h for h in headlines if not h.get("is_tagged")]

    display = (tagged_items + untagged_items)[:max_items]

    cards_html = ""
    for item in display:
        tags = item.get("tags", {})
        direction = tags.get("direction", "neutral")
        is_tagged = item.get("is_tagged", False)

        arrows = {"bullish": "▲", "bearish": "▼", "neutral": "▬"}
        arrow = arrows.get(direction, "▬")
        colors = {"bullish": "#2ECC71", "bearish": "#E74C3C", "neutral": "#8B9DAE"}
        color = colors.get(direction, "#8B9DAE") if is_tagged else "#5B6E80"

        title = item.get("title", "")
        if len(title) > 88:
            title = title[:85] + "..."

        cards_html += (
            f'<div class="news-compact-row" style="border-left:2px solid {color};">'
            f'<span class="news-compact-arrow" style="color:{color};">{arrow}</span>'
            f'<span class="news-compact-title">{title}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="panel">'
        f'<div class="panel-title">Live News Feed</div>'
        f'<div class="news-compact-list">{cards_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def render_spreads_tab(market_data: dict):
    """Render Spreads, Flies & Correlations tab with interactive charts."""
    from spreads_flies import (
        compute_calendar_spreads_table,
        compute_flies,
    )

    # ============================================================
    # TOP: DUAL FORWARD CURVE OVERLAY
    # ============================================================
    render_dual_forward_curve_panel(market_data)

    # ============================================================
    # INSTRUMENT SELECTOR (for calendar spreads & flies)
    # ============================================================
    col_inst, col_blank = st.columns([1, 3])
    with col_inst:
        instrument = st.selectbox(
            "Instrument for calendar spreads & flies",
            ["Brent", "WTI", "ULSD", "Gasoil"],
            key="spreads_instrument",
        )

    # ============================================================
    # CALENDAR SPREADS: table on left, history chart on right
    # ============================================================
    left, right = st.columns([1, 1.3])

    with left:
        _render_spread_panel(
            title=f"Calendar Spreads — {instrument}",
            spreads=compute_calendar_spreads_table(market_data, instrument),
            unit="$",
            note=(
                f"Real {instrument} settlement data, z-scores against trailing 252-day window."
            ),
        )

    with right:
        render_spread_history_chart(instrument)

    # ============================================================
    # FLIES: table on left, history chart on right
    # ============================================================
    left2, right2 = st.columns([1, 1.3])

    with left2:
        _render_fly_panel(
            title=f"Butterfly Flies — {instrument}",
            flies=compute_flies(market_data, instrument),
            note="Positive = curve peak. Negative = valley. Tracks curvature.",
        )

    with right2:
        render_fly_history_chart(instrument)

    # ============================================================
    # INTER-PRODUCT SPREADS with sparklines (full width)
    # ============================================================
    render_inter_product_with_sparklines(market_data)

    # ============================================================
    # CORRELATION MATRIX (full width, Phase 2 work)
    # ============================================================
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    render_correlation_panel()

def _render_spread_panel(title: str, spreads: list, unit: str = "$", note: str = ""):
    """Reusable spread display panel with z-score badges."""
    if not spreads:
        st.markdown(
            f'<div class="panel"><div class="panel-title">{title}</div>'
            f'<div style="color:#8B9DAE; padding:20px;">No data available.</div></div>',
            unsafe_allow_html=True,
        )
        return

    rows_html = ""
    for s in spreads:
        z = s["z_score"]
        status = s["status"]
        value = s["value"]
        change = s["change"]

        # Color logic
        if status == "EXTREME":
            badge_color = "#E74C3C"
            border_color = "#E74C3C"
            badge_glow = "box-shadow: 0 0 8px rgba(231, 76, 60, 0.5);"
        elif status == "ELEVATED":
            badge_color = "#E67E22"
            border_color = "#E67E22"
            badge_glow = ""
        else:
            badge_color = "#8B9DAE"
            border_color = "#2E75B6"
            badge_glow = ""

        change_color = "#2ECC71" if change >= 0 else "#E74C3C"
        change_arrow = "▲" if change >= 0 else "▼"

        rows_html += (
            f'<div class="spread-row" style="border-left:2px solid {border_color};">'
            f'<div class="spread-name">{s["name"]}</div>'
            f'<div class="spread-value">{unit}{value:+.2f}</div>'
            f'<div class="spread-change" style="color:{change_color};">'
            f'{change_arrow} {change:+.2f}'
            f'</div>'
            f'<div class="spread-badge" style="background:{badge_color}; color:white; {badge_glow}">'
            f'{status} · z {z:+.1f}σ'
            f'</div>'
            f'</div>'
        )

    note_html = (
        f'<div style="color:#5B6E80; font-size:0.65rem; margin-top:8px; font-style:italic;">{note}</div>'
        if note else ""
    )

    st.markdown(
        f'<div class="panel">'
        f'<div class="panel-title">{title}</div>'
        f'<div class="spread-list">{rows_html}</div>'
        f'{note_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_fly_panel(title: str, flies: list, note: str = ""):
    """Render butterfly fly panel — value + shape + status."""
    if not flies:
        st.markdown(
            f'<div class="panel"><div class="panel-title">{title}</div>'
            f'<div style="color:#8B9DAE; padding:20px;">No data available.</div></div>',
            unsafe_allow_html=True,
        )
        return

    rows_html = ""
    for f in flies:
        z = f["z_score"]
        status = f["status"]
        value = f["value"]
        change = f["change"]
        shape = f["shape"]

        if status == "EXTREME":
            badge_color = "#E74C3C"
            border_color = "#E74C3C"
            badge_glow = "box-shadow: 0 0 8px rgba(231, 76, 60, 0.5);"
        elif status == "ELEVATED":
            badge_color = "#E67E22"
            border_color = "#E67E22"
            badge_glow = ""
        else:
            badge_color = "#8B9DAE"
            border_color = "#2E75B6"
            badge_glow = ""

        change_color = "#2ECC71" if change >= 0 else "#E74C3C"
        change_arrow = "▲" if change >= 0 else "▼"

        rows_html += (
            f'<div class="fly-row" style="border-left:2px solid {border_color};">'
            f'<div class="fly-header">'
            f'<span class="fly-name">{f["name"]}</span>'
            f'<span class="fly-shape">{shape}</span>'
            f'</div>'
            f'<div class="fly-body">'
            f'<span class="fly-value">${value:+.2f}</span>'
            f'<span class="fly-change" style="color:{change_color};">{change_arrow} {change:+.2f}</span>'
            f'<span class="fly-badge" style="background:{badge_color}; color:white; {badge_glow}">'
            f'{status} · z {z:+.1f}σ'
            f'</span>'
            f'</div>'
            f'</div>'
        )

    note_html = (
        f'<div style="color:#5B6E80; font-size:0.65rem; margin-top:8px; font-style:italic;">{note}</div>'
        if note else ""
    )

    st.markdown(
        f'<div class="panel">'
        f'<div class="panel-title">{title}</div>'
        f'<div class="fly-list">{rows_html}</div>'
        f'{note_html}'
        f'</div>',
        unsafe_allow_html=True,
    )
# ============================================================
# CORRELATION MATRIX PANEL (Phase 2)
# ============================================================

def render_correlation_panel():
    """Render the rolling correlation matrix as a heatmap."""
    import plotly.graph_objects as go
    from correlations import (
        fetch_correlation_data,
        compute_correlation_matrix,
        compute_correlation_change,
        find_notable_correlations,
        find_correlation_breaks,
    )

    # ============================================================
    # WINDOW SELECTOR
    # ============================================================
    col_window, col_blank = st.columns([1, 3])
    with col_window:
        window_label = st.selectbox(
            "Correlation window",
            ["30 days", "60 days", "90 days"],
            key="corr_window",
        )

    window_map = {"30 days": 30, "60 days": 60, "90 days": 90}
    window_days = window_map[window_label]

    # ============================================================
    # FETCH DATA
    # ============================================================
    with st.spinner(f"Computing {window_label} correlations..."):
        prices = fetch_correlation_data(window_days=window_days)

    if prices is None or prices.empty:
        st.markdown(
            '<div class="panel"><div class="panel-title">Correlation Matrix</div>'
            '<div style="color:#8B9DAE; padding:20px;">No data available.</div></div>',
            unsafe_allow_html=True,
        )
        return

    corr_matrix = compute_correlation_matrix(prices, window_days=window_days)

    if corr_matrix.empty:
        st.markdown(
            '<div class="panel"><div class="panel-title">Correlation Matrix</div>'
            '<div style="color:#8B9DAE; padding:20px;">Not enough data to compute correlations.</div></div>',
            unsafe_allow_html=True,
        )
        return

    # ============================================================
    # TWO-COLUMN: Heatmap | Notable + Breaks
    # ============================================================
    left, right = st.columns([1.4, 1])

    with left:
        st.markdown(
            f'<div class="panel">'
            f'<div class="panel-title">Rolling Correlation Heatmap ({window_label})</div>',
            unsafe_allow_html=True,
        )

        # Build heatmap
        symbols = corr_matrix.columns.tolist()
        z_values = corr_matrix.values

        # Build text annotations for each cell
        text = [[f"{val:.2f}" for val in row] for row in z_values]

        fig = go.Figure(data=go.Heatmap(
            z=z_values,
            x=symbols,
            y=symbols,
            text=text,
            texttemplate="%{text}",
            textfont={"size": 10, "color": "#0A1729"},
            colorscale=[
                [0.0, "#E74C3C"],   # strong negative = red
                [0.25, "#F39C12"],  # mild negative = orange
                [0.5, "#FFFFFF"],   # zero = white
                [0.75, "#5BA8D9"],  # mild positive = light blue
                [1.0, "#2E75B6"],   # strong positive = blue
            ],
            zmin=-1,
            zmax=1,
            showscale=True,
            colorbar=dict(
                title=dict(text="ρ", font=dict(color="#8B9DAE", size=11)),
                tickfont=dict(color="#8B9DAE", size=10),
                thickness=10,
                len=0.8,
            ),
        ))

        fig.update_layout(
            height=440,
            margin=dict(l=80, r=20, t=20, b=80),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8B9DAE", family="Inter, sans-serif", size=10),
            xaxis=dict(
                tickangle=-45,
                tickfont=dict(size=10, color="#C3D0DC"),
                side="bottom",
            ),
            yaxis=dict(
                tickfont=dict(size=10, color="#C3D0DC"),
                autorange="reversed",
            ),
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown(
            '<div style="color:#5B6E80; font-size:0.65rem; margin-top:-4px; font-style:italic;">'
            'Blue = positive correlation, red = negative, white = uncorrelated. '
            'Computed on daily returns from Yahoo Finance historicals.'
            '</div></div>',
            unsafe_allow_html=True,
        )

    with right:
        # Notable correlations
        notable = find_notable_correlations(corr_matrix, threshold=0.6)

        notable_html = ""
        if notable:
            for n in notable[:6]:
                v = n["value"]
                color = "#2E75B6" if v > 0 else "#E74C3C"
                notable_html += (
                    f'<div class="corr-pair-row" style="border-left:2px solid {color};">'
                    f'<div class="corr-pair-name">{n["pair"]}</div>'
                    f'<div class="corr-pair-value" style="color:{color};">{v:+.2f}</div>'
                    f'<div class="corr-pair-tag" style="background:{color};">{n["strength"]}</div>'
                    f'</div>'
                )
        else:
            notable_html = (
                '<div style="color:#8B9DAE; padding:14px; font-size:0.78rem; text-align:center;">'
                'No strong correlations (|ρ| > 0.6) in this window.'
                '</div>'
            )

        st.markdown(
            f'<div class="panel">'
            f'<div class="panel-title">Notable Correlations (|ρ| > 0.6)</div>'
            f'<div class="corr-pair-list">{notable_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Correlation breaks (shifts vs prior window)
        delta = compute_correlation_change(prices, window_days=window_days, lookback_days=window_days)
        breaks = find_correlation_breaks(delta, threshold=0.3) if not delta.empty else []

        breaks_html = ""
        if breaks:
            for b in breaks[:6]:
                d = b["delta"]
                color = "#2ECC71" if d > 0 else "#E74C3C"
                arrow = "▲" if d > 0 else "▼"
                breaks_html += (
                    f'<div class="corr-pair-row" style="border-left:2px solid {color};">'
                    f'<div class="corr-pair-name">{b["pair"]}</div>'
                    f'<div class="corr-pair-value" style="color:{color};">{arrow} {d:+.2f}</div>'
                    f'<div class="corr-pair-tag" style="background:{color};">{b["direction"]}</div>'
                    f'</div>'
                )
        else:
            breaks_html = (
                '<div style="color:#8B9DAE; padding:14px; font-size:0.78rem; text-align:center;">'
                'No significant correlation shifts vs prior window.'
                '</div>'
            )

        st.markdown(
            f'<div class="panel">'
            f'<div class="panel-title">Correlation Breaks (Δρ &gt; 0.3)</div>'
            f'<div class="corr-pair-list">{breaks_html}</div>'
            f'<div style="color:#5B6E80; font-size:0.62rem; margin-top:6px; font-style:italic;">'
            f'Compares current {window_label} window to the prior {window_label} window.'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
# ============================================================
# ALERT STRIP (Phase 3) — Markets tab right column
# ============================================================

def render_alert_strip(market_data: dict, max_alerts: int = 6):
    """Render the live alert strip on the Markets tab right column."""
    from alerts import generate_alerts, alert_summary, severity_color

    try:
        alerts = generate_alerts(market_data, max_alerts=max_alerts)
    except Exception as e:
        print(f"[components] alerts error: {e}")
        alerts = []

    summary = alert_summary(alerts)

    # Header with summary counts
    counts_html = ""
    if summary["CRITICAL"] > 0:
        counts_html += f'<span class="alert-count alert-count-critical">{summary["CRITICAL"]} crit</span>'
    if summary["HIGH"] > 0:
        counts_html += f'<span class="alert-count alert-count-high">{summary["HIGH"]} high</span>'
    if summary["MEDIUM"] > 0:
        counts_html += f'<span class="alert-count alert-count-medium">{summary["MEDIUM"]} med</span>'

    if not alerts:
        st.markdown(
            '<div class="panel panel-unique">'
            '<div class="panel-title">★ Live Alerts</div>'
            '<div style="color:#8B9DAE; padding:14px; text-align:center; font-size:0.78rem;">'
            'No alerts firing. All spreads and correlations within normal ranges.'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    cards_html = ""
    for a in alerts:
        sev = a["severity"]
        color = severity_color(sev)
        glow = "box-shadow: 0 0 6px " + color + "80;" if sev == "CRITICAL" else ""
        pulse_class = " alert-card-pulse" if sev == "CRITICAL" else ""

        cards_html += (
            f'<div class="alert-card{pulse_class}" style="border-left:3px solid {color}; {glow}">'
            f'<div class="alert-row-top">'
            f'<span class="alert-sev" style="color:{color}; border-color:{color};">{sev}</span>'
            f'<span class="alert-cat">{a["category"]}</span>'
            f'<span class="alert-time">{a["timestamp"]}</span>'
            f'</div>'
            f'<div class="alert-headline">{a["headline"]}</div>'
            f'<div class="alert-detail">{a["detail"]}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="panel panel-unique">'
        f'<div class="panel-title" style="display:flex; justify-content:space-between; align-items:center;">'
        f'<span>★ Live Alerts</span>'
        f'<span class="alert-counts-row">{counts_html}</span>'
        f'</div>'
        f'<div class="alert-list">{cards_html}</div>'
        f'<div style="color:#5B6E80; font-size:0.62rem; margin-top:8px; font-style:italic;">'
        f'Triggered when spreads exceed ±1.5σ, correlations shift &gt;0.3, or curve structure is extreme.'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# KEY CORRELATIONS MINI-PANEL (Phase 3) — Markets tab right column
# ============================================================

def render_key_correlations_mini():
    """Compact correlation summary panel for Markets tab."""
    try:
        from correlations import (
            fetch_correlation_data,
            compute_correlation_matrix,
            find_notable_correlations,
            compute_correlation_change,
            find_correlation_breaks,
        )

        prices = fetch_correlation_data(window_days=30)
        if prices.empty:
            return

        corr = compute_correlation_matrix(prices, window_days=30)
        if corr.empty:
            return

        notable = find_notable_correlations(corr, threshold=0.6)
        delta = compute_correlation_change(prices, window_days=30, lookback_days=30)
        breaks = find_correlation_breaks(delta, threshold=0.3) if not delta.empty else []

    except Exception as e:
        print(f"[components] key correlations error: {e}")
        return

    rows_html = ""

    # Top 3 strongest correlations
    for n in notable[:3]:
        v = n["value"]
        color = "#2E75B6" if v > 0 else "#E74C3C"
        rows_html += (
            f'<div class="key-corr-row" style="border-left:2px solid {color};">'
            f'<span class="key-corr-pair">{n["pair"]}</span>'
            f'<span class="key-corr-val" style="color:{color};">ρ {v:+.2f}</span>'
            f'</div>'
        )

    # Top 2 correlation breaks
    if breaks:
        rows_html += '<div class="key-corr-divider">SHIFTS (vs prior 30d)</div>'
        for b in breaks[:2]:
            d = b["delta"]
            color = "#2ECC71" if d > 0 else "#E74C3C"
            arrow = "▲" if d > 0 else "▼"
            rows_html += (
                f'<div class="key-corr-row" style="border-left:2px solid {color};">'
                f'<span class="key-corr-pair">{b["pair"]}</span>'
                f'<span class="key-corr-val" style="color:{color};">{arrow} {d:+.2f}</span>'
                f'</div>'
            )

    if not rows_html:
        rows_html = (
            '<div style="color:#8B9DAE; padding:10px; text-align:center; font-size:0.75rem;">'
            'No strong correlations active.</div>'
        )

    st.markdown(
        f'<div class="panel">'
        f'<div class="panel-title">Key Correlations (30d)</div>'
        f'<div class="key-corr-list">{rows_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
# ============================================================
# PHASE 4 — INTERACTIVE CHARTS FOR SPREADS TAB
# ============================================================

def render_dual_forward_curve_panel(market_data: dict):
    """Render WTI + Brent forward curves overlaid on one chart."""
    import plotly.graph_objects as go
    from forward_curves import build_curve_for_instrument

    brent_curve = build_curve_for_instrument("Brent", market_data)
    wti_curve = build_curve_for_instrument("WTI", market_data)

    if not brent_curve and not wti_curve:
        return

    fig = go.Figure()

    if brent_curve:
        tenors = [m for m, _ in brent_curve]
        prices = [p for _, p in brent_curve]
        fig.add_trace(go.Scatter(
            x=tenors, y=prices,
            mode="lines+markers",
            line=dict(color="#2E75B6", width=2.5),
            marker=dict(size=4, color="#2E75B6"),
            name="Brent (real ICE)",
            hovertemplate="<b>Brent M%{x}</b><br>$%{y:.2f}<extra></extra>",
        ))

    if wti_curve:
        tenors = [m for m, _ in wti_curve]
        prices = [p for _, p in wti_curve]
        fig.add_trace(go.Scatter(
            x=tenors, y=prices,
            mode="lines+markers",
            line=dict(color="#E67E22", width=2.5),
            marker=dict(size=3, color="#E67E22"),
            name="WTI (NYMEX)",
            hovertemplate="<b>WTI M%{x}</b><br>$%{y:.2f}<extra></extra>",
        ))

    fig.update_layout(
        height=320,
        margin=dict(l=50, r=20, t=20, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8B9DAE", family="Inter, sans-serif", size=11),
        legend=dict(
            orientation="h",
            yanchor="top", y=1.12,
            xanchor="right", x=1,
            font=dict(size=10),
        ),
        xaxis=dict(
            title="Tenor (months)",
            gridcolor="rgba(31, 58, 92, 0.4)",
            zeroline=False,
        ),
        yaxis=dict(
            title="Price ($/bbl)",
            gridcolor="rgba(31, 58, 92, 0.4)",
            zeroline=False,
        ),
        hovermode="x unified",
    )

    st.markdown(
        '<div class="panel">'
        '<div class="panel-title">Forward Curves — WTI vs Brent</div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        '<div style="color:#5B6E80; font-size:0.65rem; font-style:italic; margin-top:-4px;">'
        'Brent: real ICE settlement (31 contract months). WTI: parametric model anchored to live front month. '
        'Hover for tenor and price.'
        '</div></div>',
        unsafe_allow_html=True,
    )


def render_spread_history_chart(instrument: str = "Brent"):
    """Interactive spread history chart with σ bands. Works for any instrument with settlement data."""
    import plotly.graph_objects as go
    from settle_data import compute_historical_spread, has_real_data

    if not has_real_data(instrument):
        st.markdown(
            f'<div class="panel">'
            f'<div class="panel-title">Spread History</div>'
            f'<div style="color:#8B9DAE; padding:18px; text-align:center; font-size:0.78rem;">'
            f'No historical settlement data available for {instrument}.'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<div class="panel"><div class="panel-title">{instrument} Spread History (90 days, ±1σ / ±2σ bands)</div>',
        unsafe_allow_html=True,
    )

    selected = st.radio(
        "Select spread",
        ["M1-M2", "M1-M3", "M1-M6", "M1-M12"],
        horizontal=True,
        label_visibility="collapsed",
        key=f"{instrument}_spread_history_pick",
    )

    spread_map = {"M1-M2": (1, 2), "M1-M3": (1, 3), "M1-M6": (1, 6), "M1-M12": (1, 12)}
    m_a, m_b = spread_map[selected]

    series = compute_historical_spread(instrument, m_a, m_b)
    if series.empty:
        st.markdown('<div style="color:#8B9DAE; padding:20px;">No data available.</div></div>', unsafe_allow_html=True)
        return

    recent = series.tail(90)
    full = series.tail(252)
    mean = float(full.mean())
    std = float(full.std())
    last_val = float(recent.iloc[-1])

    fig = go.Figure()

    fig.add_hrect(y0=mean + 2 * std, y1=mean - 2 * std,
                  fillcolor="rgba(231, 76, 60, 0.06)", line_width=0, layer="below")
    fig.add_hrect(y0=mean + std, y1=mean - std,
                  fillcolor="rgba(46, 117, 182, 0.10)", line_width=0, layer="below")

    fig.add_hline(y=mean, line_dash="dash", line_color="#5B6E80",
                  line_width=1, annotation_text=f"μ = {mean:.2f}",
                  annotation_position="right", annotation_font_size=10,
                  annotation_font_color="#8B9DAE")
    fig.add_hline(y=mean + std, line_dash="dot", line_color="#2E75B6", line_width=1, opacity=0.5)
    fig.add_hline(y=mean - std, line_dash="dot", line_color="#2E75B6", line_width=1, opacity=0.5)
    fig.add_hline(y=mean + 2 * std, line_dash="dot", line_color="#E74C3C", line_width=1, opacity=0.4)
    fig.add_hline(y=mean - 2 * std, line_dash="dot", line_color="#E74C3C", line_width=1, opacity=0.4)

    fig.add_trace(go.Scatter(
        x=recent.index.tolist(), y=recent.values.tolist(),
        mode="lines",
        line=dict(color="#5BA8D9", width=2),
        name=selected,
        hovertemplate="<b>%{x|%d %b %Y}</b><br>" + selected + ": %{y:.2f}<extra></extra>",
    ))

    z = (last_val - mean) / std if std > 0 else 0
    marker_color = "#E74C3C" if abs(z) > 2 else "#E67E22" if abs(z) > 1 else "#2ECC71"
    fig.add_trace(go.Scatter(
        x=[recent.index[-1]], y=[last_val],
        mode="markers",
        marker=dict(size=10, color=marker_color, line=dict(width=2, color="white")),
        hovertemplate=f"<b>Latest</b><br>{last_val:.2f} · z {z:+.2f}σ<extra></extra>",
    ))

    fig.update_layout(
        height=320,
        margin=dict(l=50, r=80, t=20, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8B9DAE", family="Inter, sans-serif", size=11),
        showlegend=False,
        xaxis=dict(gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False),
        yaxis=dict(
            title=f"{selected} spread",
            gridcolor="rgba(31, 58, 92, 0.4)",
            zeroline=True,
            zerolinecolor="rgba(139, 157, 174, 0.3)",
            zerolinewidth=1,
        ),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        '<div style="color:#5B6E80; font-size:0.65rem; font-style:italic; margin-top:-4px;">'
        '90 days shown · μ and σ from trailing 252-day window · '
        'green = within 1σ, orange = 1-2σ, red = beyond 2σ'
        '</div></div>',
        unsafe_allow_html=True,
    )

def render_fly_history_chart(instrument: str = "Brent"):
    """Interactive butterfly history chart with σ bands."""
    import plotly.graph_objects as go
    from settle_data import compute_historical_fly, has_real_data

    if not has_real_data(instrument):
        st.markdown(
            f'<div class="panel">'
            f'<div class="panel-title">Fly History</div>'
            f'<div style="color:#8B9DAE; padding:18px; text-align:center; font-size:0.78rem;">'
            f'No historical settlement data available for {instrument}.'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<div class="panel"><div class="panel-title">{instrument} Butterfly Fly History (90 days, ±1σ / ±2σ bands)</div>',
        unsafe_allow_html=True,
    )

    selected = st.radio(
        "Select fly",
        ["M1-2M2+M3", "M1-2M3+M6", "M1-2M6+M12"],
        horizontal=True,
        label_visibility="collapsed",
        key=f"{instrument}_fly_history_pick",
    )

    fly_map = {
        "M1-2M2+M3": (1, 2, 3),
        "M1-2M3+M6": (1, 3, 6),
        "M1-2M6+M12": (1, 6, 12),
    }
    a, b, c = fly_map[selected]

    series = compute_historical_fly(instrument, a, b, c)
    if series.empty:
        st.markdown('<div style="color:#8B9DAE; padding:20px;">No data.</div></div>', unsafe_allow_html=True)
        return

    recent = series.tail(90)
    full = series.tail(252)
    mean = float(full.mean())
    std = float(full.std())
    last_val = float(recent.iloc[-1])

    fig = go.Figure()

    fig.add_hrect(y0=mean + 2 * std, y1=mean - 2 * std,
                  fillcolor="rgba(231, 76, 60, 0.06)", line_width=0, layer="below")
    fig.add_hrect(y0=mean + std, y1=mean - std,
                  fillcolor="rgba(155, 89, 182, 0.10)", line_width=0, layer="below")

    fig.add_hline(y=mean, line_dash="dash", line_color="#5B6E80",
                  line_width=1, annotation_text=f"μ = {mean:.2f}",
                  annotation_position="right", annotation_font_size=10,
                  annotation_font_color="#8B9DAE")
    fig.add_hline(y=mean + std, line_dash="dot", line_color="#9B59B6", line_width=1, opacity=0.5)
    fig.add_hline(y=mean - std, line_dash="dot", line_color="#9B59B6", line_width=1, opacity=0.5)
    fig.add_hline(y=mean + 2 * std, line_dash="dot", line_color="#E74C3C", line_width=1, opacity=0.4)
    fig.add_hline(y=mean - 2 * std, line_dash="dot", line_color="#E74C3C", line_width=1, opacity=0.4)
    fig.add_hline(y=0, line_color="rgba(139, 157, 174, 0.3)", line_width=1)

    fig.add_trace(go.Scatter(
        x=recent.index.tolist(), y=recent.values.tolist(),
        mode="lines",
        line=dict(color="#9B59B6", width=2),
        name=selected,
        hovertemplate="<b>%{x|%d %b %Y}</b><br>" + selected + ": %{y:+.2f}<extra></extra>",
    ))

    z = (last_val - mean) / std if std > 0 else 0
    marker_color = "#E74C3C" if abs(z) > 2 else "#E67E22" if abs(z) > 1 else "#2ECC71"
    fig.add_trace(go.Scatter(
        x=[recent.index[-1]], y=[last_val],
        mode="markers",
        marker=dict(size=10, color=marker_color, line=dict(width=2, color="white")),
        hovertemplate=f"<b>Latest</b><br>{last_val:+.2f} · z {z:+.2f}σ<extra></extra>",
    ))

    fig.update_layout(
        height=320,
        margin=dict(l=50, r=80, t=20, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8B9DAE", family="Inter, sans-serif", size=11),
        showlegend=False,
        xaxis=dict(gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False),
        yaxis=dict(title=f"{selected}", gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        '<div style="color:#5B6E80; font-size:0.65rem; font-style:italic; margin-top:-4px;">'
        'Positive values = curve peak (hump). Negative = valley (kink). '
        'Extreme readings often flag relative-value opportunities.'
        '</div></div>',
        unsafe_allow_html=True,
    )


def render_inter_product_with_sparklines(market_data: dict):
    """Inter-product spreads table with inline sparklines."""
    import plotly.graph_objects as go
    from spreads_flies import (
        compute_interproduct_spreads_table,
        compute_inter_product_sparklines,
    )

    spreads = compute_interproduct_spreads_table(market_data)
    sparklines = compute_inter_product_sparklines(days=60)

    if not spreads:
        return

    st.markdown(
        '<div class="panel"><div class="panel-title">Inter-Product Spreads (60-day sparklines)</div>',
        unsafe_allow_html=True,
    )

    for s in spreads:
        name = s["name"]
        value = s["value"]
        change = s["change"]
        status = s["status"]
        z = s["z_score"]

        # Color for status
        if status == "EXTREME":
            badge_color = "#E74C3C"
            border_color = "#E74C3C"
        elif status == "ELEVATED":
            badge_color = "#E67E22"
            border_color = "#E67E22"
        else:
            badge_color = "#8B9DAE"
            border_color = "#2E75B6"

        change_color = "#2ECC71" if change >= 0 else "#E74C3C"
        change_arrow = "▲" if change >= 0 else "▼"

        # Layout: 4 columns — info | sparkline | value | badge
        c_info, c_spark, c_val, c_badge = st.columns([2, 2, 1.3, 1.5])

        with c_info:
            st.markdown(
                f'<div style="border-left:2px solid {border_color}; padding-left:10px; padding-top:8px;">'
                f'<div style="color:#C3D0DC; font-size:0.82rem; font-weight:600; '
                f'font-family:JetBrains Mono;">{name}</div>'
                f'<div style="color:{change_color}; font-size:0.7rem; font-family:JetBrains Mono;">'
                f'{change_arrow} {change:+.2f}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with c_spark:
            spark_series = sparklines.get(name, [])
            if spark_series and len(spark_series) > 2:
                spark_fig = go.Figure()
                spark_fig.add_trace(go.Scatter(
                    y=spark_series,
                    mode="lines",
                    line=dict(color=border_color, width=1.5),
                    hoverinfo="skip",
                    showlegend=False,
                ))
                spark_fig.update_layout(
                    height=44,
                    margin=dict(l=0, r=0, t=4, b=4),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(visible=False),
                    yaxis=dict(visible=False),
                )
                st.plotly_chart(spark_fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.markdown('<div style="height:44px;"></div>', unsafe_allow_html=True)

        with c_val:
            st.markdown(
                f'<div style="padding-top:14px; color:#E5EBF0; font-size:0.92rem; '
                f'font-weight:700; font-family:JetBrains Mono; text-align:right;">'
                f'${value:+.2f}</div>',
                unsafe_allow_html=True,
            )

        with c_badge:
            st.markdown(
                f'<div style="padding-top:14px;">'
                f'<span style="background:{badge_color}; color:white; padding:3px 8px; '
                f'border-radius:4px; font-size:0.62rem; font-weight:700; letter-spacing:0.4px; '
                f'font-family:JetBrains Mono;">{status} · z {z:+.1f}σ</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div style="color:#5B6E80; font-size:0.65rem; margin-top:10px; font-style:italic;">'
        'All values computed from live Yahoo Finance prices. Sparklines show 60-day trend.'
        '</div></div>',
        unsafe_allow_html=True,
    )
# ============================================================
# LIVE TRADINGVIEW CHARTS (Markets tab bottom panel)
# ============================================================

def render_live_chart_panel():
    """
    Render a TradingView live chart embed on the Markets tab.
    User picks which of the 5 products to view via pill selector.
    """
    import streamlit.components.v1 as components

    # Map our friendly names to TradingView symbols
    SYMBOL_MAP = {
        "WTI Crude": {
            "tv_symbol": "NYMEX:CL1!",
            "description": "WTI front-month continuous (NYMEX)",
        },
        "Brent Crude": {
            "tv_symbol": "ICEEUR:BRN1!",
            "description": "Brent front-month continuous (ICE Europe)",
        },
        "Natural Gas": {
            "tv_symbol": "NYMEX:NG1!",
            "description": "Henry Hub front-month continuous (NYMEX)",
        },
        "RBOB Gasoline": {
            "tv_symbol": "NYMEX:RB1!",
            "description": "RBOB Gasoline front-month continuous (NYMEX)",
        },
        "ULSD / Heat Oil": {
            "tv_symbol": "NYMEX:HO1!",
            "description": "ULSD Heating Oil front-month continuous (NYMEX)",
        },
    }

    # ============================================================
    # PANEL HEADER + PRODUCT SELECTOR
    # ============================================================
    st.markdown(
        '<div class="panel">'
        '<div class="panel-title" style="display:flex; justify-content:space-between; align-items:center;">'
        '<span>Live Charts</span>'
        '<span style="color:#5B6E80; font-size:0.62rem; font-style:italic; font-weight:400; letter-spacing:0;">'
        'powered by TradingView · candlesticks default'
        '</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    selected = st.radio(
        "Select product",
        list(SYMBOL_MAP.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="live_chart_pick",
    )

    info = SYMBOL_MAP[selected]
    tv_symbol = info["tv_symbol"]
    description = info["description"]

    # ============================================================
    # CONTEXT LINE
    # ============================================================
    st.markdown(
        f'<div style="color:#8B9DAE; font-size:0.7rem; margin: 4px 0 8px 0; font-family:JetBrains Mono;">'
        f'<span style="color:#5BA8D9;">●</span> {description}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ============================================================
    # TRADINGVIEW IFRAME EMBED
    # ============================================================
    # Use the basic /widgetembed/ URL — works without any auth, free, no key needed
    tv_url = (
        f"https://s.tradingview.com/widgetembed/"
        f"?symbol={tv_symbol}"
        f"&interval=60"               # 60-min default candles
        f"&theme=dark"
        f"&style=1"                   # 1 = candlesticks
        f"&toolbarbg=0A1729"          # match our dark navy
        f"&hide_top_toolbar=0"        # show top toolbar (interval, indicators)
        f"&hide_side_toolbar=0"       # show side toolbar (drawing tools)
        f"&hide_legend=0"
        f"&allow_symbol_change=1"     # let user search other symbols if they want
        f"&save_image=1"
        f"&studies=Volume@tv-basicstudies"  # add volume by default
    )

    iframe_html = f"""
    <div style="border-radius: 6px; overflow: hidden; border: 1px solid rgba(46, 117, 182, 0.2);">
        <iframe
            src="{tv_url}"
            width="100%"
            height="420"
            frameborder="0"
            allowtransparency="true"
            scrolling="no"
            allowfullscreen
            style="display: block; background: #0A1729;">
        </iframe>
    </div>
    """

    components.html(iframe_html, height=440)

    # ============================================================
    # FOOTER NOTE
    # ============================================================
    st.markdown(
        '<div style="color:#5B6E80; font-size:0.65rem; margin-top:8px; font-style:italic;">'
        'Live candlestick chart with volume. Top toolbar adjusts timeframe (1m / 5m / 1h / 1D / 1W). '
        'Side toolbar adds indicators and drawing tools. '
        'Quote delay depends on the exchange — typically 15 min for free CME/ICE feeds.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )
# ============================================================
# REPLAY MODE TAB
# ============================================================
def render_replay_tab(market_data: dict):
    """Render the Replay Mode tab — historical date scrubbing with event animations."""
    import plotly.graph_objects as go
    from datetime import datetime, timedelta
    from replay_data import (
        get_available_dates,
        get_replay_snapshot,
        EVENT_SHORTCUTS,
    )
    from replay_alerts import generate_replay_alerts, severity_color

    # ============================================================
    # STATE MANAGEMENT
    # ============================================================
    # Initialize replay_instrument FIRST since get_available_dates needs it
    if "replay_instrument" not in st.session_state:
        st.session_state["replay_instrument"] = "Brent"
    replay_instrument = st.session_state["replay_instrument"]

    available_dates = get_available_dates(replay_instrument)
    if not available_dates:
        st.markdown(
            '<div class="panel"><div class="panel-title">Replay Mode</div>'
            '<div style="color:#8B9DAE; padding:30px; text-align:center;">'
            'No historical Brent settlement data loaded. Check data/brent_settle.csv exists.'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    min_date = available_dates[0].date()
    max_date = available_dates[-1].date()

    # Initialize session state
    if "replay_date" not in st.session_state:
        st.session_state["replay_date"] = max_date
    if "replay_autoplay" not in st.session_state:
        st.session_state["replay_autoplay"] = False
    if "replay_autoplay_target" not in st.session_state:
        st.session_state["replay_autoplay_target"] = None
    if "replay_autoplay_speed" not in st.session_state:
        st.session_state["replay_autoplay_speed"] = 0.6
    if "replay_event_date" not in st.session_state:
        st.session_state["replay_event_date"] = None
    if "replay_event_label" not in st.session_state:
        st.session_state["replay_event_label"] = ""

    current = st.session_state["replay_date"]
    current_pd = pd.Timestamp(current)
    print(f"[replay] TICK current={current}, autoplay={st.session_state['replay_autoplay']}, "
          f"target={st.session_state.get('replay_autoplay_target')}, "
          f"event_label={st.session_state.get('replay_event_label')!r}")

    # ============================================================
    # TOP BANNER — flashes red on event day, purple otherwise
    # ============================================================
    event_date = st.session_state.get("replay_event_date")
    event_label = st.session_state.get("replay_event_label", "")
    is_event_day = (event_date is not None and current == event_date)

    if is_event_day:
        st.markdown(
            f'<div class="event-banner-flash" style="border-radius: 6px; '
            f'padding: 14px 18px; margin-bottom: 14px; display:flex; '
            f'justify-content:space-between; align-items:center; gap:14px; flex-wrap:wrap;">'
            f'<div>'
            f'<span style="color:#FFFFFF; font-size:0.78rem; font-weight:800; letter-spacing:1.4px;">'
            f'⚡ EVENT DAY</span>'
            f'<span style="color:#FFFFFF; font-size:1.2rem; font-weight:800; '
            f'margin-left:14px; font-family:JetBrains Mono;">'
            f'{current_pd.strftime("%A, %d %b %Y")}</span>'
            f'</div>'
            f'<div style="color:#FFFFFF; font-size:0.85rem; font-weight:700;">'
            f'{event_label}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        anim_hint = ""
        if event_label and st.session_state.get("replay_autoplay"):
            anim_hint = (
                f'<span style="color:#9B59B6; font-size:0.72rem; margin-left:14px; '
                f'background:rgba(155,89,182,0.18); padding:3px 8px; border-radius:3px;">'
                f'↻ animating to {event_label}</span>'
            )

        st.markdown(
            f'<div style="background: linear-gradient(135deg, rgba(155, 89, 182, 0.15), rgba(46, 117, 182, 0.10)); '
            f'border: 1px solid rgba(155, 89, 182, 0.4); border-radius: 6px; '
            f'padding: 10px 16px; margin-bottom: 14px; display:flex; '
            f'justify-content:space-between; align-items:center; gap:14px; flex-wrap:wrap;">'
            f'<div>'
            f'<span style="color:#9B59B6; font-size:0.68rem; font-weight:800; letter-spacing:1px;">'
            f'◷ REPLAY MODE</span>'
            f'<span style="color:#E5EBF0; font-size:1.1rem; font-weight:700; '
            f'margin-left:14px; font-family:JetBrains Mono;">'
            f'{current_pd.strftime("%A, %d %b %Y")}</span>'
            f'{anim_hint}'
            f'</div>'
            f'<div style="color:#8B9DAE; font-size:0.7rem; font-style:italic;">'
            f'Dashboard state reconstructed from real historical data'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ============================================================
    # CONTROLS: date display + step buttons + autoplay
    # ============================================================
    st.markdown(
        '<div class="panel"><div class="panel-title">Playback Controls</div>',
        unsafe_allow_html=True,
    )

    # Instrument selector row
    c_inst_label, c_inst_pick, c_inst_blank = st.columns([0.7, 2, 5])
    with c_inst_label:
        st.markdown(
            '<div style="padding: 8px 0; color: #8B9DAE; font-size: 0.74rem; '
            'font-weight: 600; letter-spacing: 0.5px; font-family: JetBrains Mono;">'
            'INSTRUMENT</div>',
            unsafe_allow_html=True,
        )
    with c_inst_pick:
        picked_inst = st.radio(
            "Instrument",
            ["Brent", "WTI"],
            index=0 if replay_instrument == "Brent" else 1,
            horizontal=True,
            label_visibility="collapsed",
            key="replay_inst_pick",
        )
        if picked_inst != replay_instrument:
            # Reset replay date to the latest available for the new instrument
            new_dates = get_available_dates(picked_inst)
            if new_dates:
                st.session_state["replay_date"] = new_dates[-1].date()
            st.session_state["replay_instrument"] = picked_inst
            st.session_state["replay_autoplay"] = False
            st.session_state["replay_autoplay_target"] = None
            st.session_state["replay_event_date"] = None
            st.session_state["replay_event_label"] = ""
            st.rerun()

    c_date, c_jumpstart, c_back_w, c_back_d, c_fwd_d, c_fwd_w, c_jumpend, c_play = st.columns(
        [2.2, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 1.4]
    )

    def step_date(delta_days):
        new = current + timedelta(days=delta_days)
        if new < min_date:
            new = min_date
        if new > max_date:
            new = max_date
        st.session_state["replay_date"] = new
        st.session_state["replay_autoplay"] = False
        st.session_state["replay_event_date"] = None
        st.session_state["replay_event_label"] = ""

    with c_jumpstart:
        if st.button("Earliest", key="replay_btn_start",
                     help="Jump to earliest date", use_container_width=True):
            st.session_state["replay_date"] = min_date
            st.session_state["replay_autoplay"] = False
            st.session_state["replay_event_date"] = None
            st.session_state["replay_event_label"] = ""

    with c_back_w:
        if st.button("- 1 wk", key="replay_btn_bw",
                     help="Back 1 week", use_container_width=True):
            step_date(-7)

    with c_back_d:
        if st.button("- 1 day", key="replay_btn_bd",
                     help="Back 1 day", use_container_width=True):
            step_date(-1)

    with c_fwd_d:
        if st.button("+ 1 day", key="replay_btn_fd",
                     help="Forward 1 day", use_container_width=True):
            step_date(1)

    with c_fwd_w:
        if st.button("+ 1 wk", key="replay_btn_fw",
                     help="Forward 1 week", use_container_width=True):
            step_date(7)

    with c_jumpend:
        if st.button("Latest", key="replay_btn_end",
                     help="Jump to latest date", use_container_width=True):
            st.session_state["replay_date"] = max_date
            st.session_state["replay_autoplay"] = False
            st.session_state["replay_event_date"] = None
            st.session_state["replay_event_label"] = ""

    with c_play:
        if st.session_state["replay_autoplay"]:
            if st.button("⏸  Pause", key="replay_btn_play",
                         use_container_width=True):
                print("[replay] Pause clicked")
                st.session_state["replay_autoplay"] = False
                st.session_state["replay_autoplay_target"] = None
                st.session_state["replay_event_date"] = None
                st.session_state["replay_event_label"] = ""
        else:
            if st.button("▶  Auto-play 30d", key="replay_btn_play",
                         help="Animate forward 30 days from current date",
                         use_container_width=True):
                target_date = min(max_date, current + timedelta(days=30))
                print(f"[replay] Auto-play 30d clicked: current={current}, target={target_date}")
                st.session_state["replay_autoplay"] = True
                st.session_state["replay_autoplay_target"] = target_date
                st.session_state["replay_autoplay_speed"] = 0.4
                st.session_state["replay_event_date"] = None
                st.session_state["replay_event_label"] = ""

    # ============================================================
    # EVENT SHORTCUTS — each triggers an animated playthrough
    # ============================================================
    st.markdown(
        '<div style="color:#8B9DAE; font-size:0.7rem; font-weight:600; '
        'letter-spacing:0.5px; margin-top:14px; margin-bottom:6px;">'
        'JUMP TO EVENT · animates ±13 days around the event date'
        '</div>',
        unsafe_allow_html=True,
    )

    event_cols = st.columns(4)
    for i, event in enumerate(EVENT_SHORTCUTS[:8]):
        col = event_cols[i % 4]
        with col:
            if st.button(event["label"], key=f"event_{i}",
                         use_container_width=True, help=event["note"]):
                event_dt = pd.to_datetime(event["date"]).date()

                start_date = max(min_date, event_dt - timedelta(days=3))
                end_date = min(max_date, event_dt + timedelta(days=10))

                print(f"[replay] ===== EVENT BUTTON CLICKED =====")
                print(f"[replay] Event: {event['label']!r}")
                print(f"[replay] event_dt={event_dt}, start={start_date}, end={end_date}")

                st.session_state["replay_date"] = start_date
                st.session_state["replay_autoplay"] = True
                st.session_state["replay_autoplay_target"] = end_date
                st.session_state["replay_autoplay_speed"] = 0.6
                st.session_state["replay_event_date"] = event_dt
                st.session_state["replay_event_label"] = event["label"]

                print(f"[replay] AFTER setting state: replay_date={st.session_state['replay_date']}, "
                      f"autoplay={st.session_state['replay_autoplay']}")
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ============================================================
    # AUTOPLAY ENGINE — uses st_autorefresh for reliable browser-side refresh
    # ============================================================
     # Re-read current from session state (button handlers may have updated it)
    current = st.session_state["replay_date"]
    current_pd = pd.Timestamp(current)
    if st.session_state["replay_autoplay"]:
        target = st.session_state["replay_autoplay_target"]
        speed = st.session_state.get("replay_autoplay_speed", 0.6)

        print(f"[replay] AUTOPLAY ACTIVE: current={current}, target={target}, speed={speed}")

        if target and current < target:
            from streamlit_autorefresh import st_autorefresh

            # Schedule the next browser-side refresh in `speed` seconds.
            # tick_count increments each time the autorefresh fires.
            tick_count = st_autorefresh(
                interval=int(speed * 1000),
                limit=10000,
                key="replay_autoplay_ticker",
            )

            # Advance the date by 1 day on each render while autoplay is active
            new = current + timedelta(days=1)
            if new > max_date:
                new = max_date
            print(f"[replay] Tick {tick_count}: advancing {current} -> {new}")
            st.session_state["replay_date"] = new
        else:
            print(f"[replay] AUTOPLAY DONE: current={current}, target={target}")
            st.session_state["replay_autoplay"] = False
            st.session_state["replay_autoplay_target"] = None

    # ============================================================
    # GET SNAPSHOT FOR CURRENT DATE
    # ============================================================
    snapshot = get_replay_snapshot(current, instrument=replay_instrument)

    if not snapshot.get("available"):
        st.markdown(
            '<div class="panel"><div class="panel-title">Snapshot</div>'
            '<div style="color:#8B9DAE; padding:20px; text-align:center;">'
            'No data available for this date. Pick another.'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    # ============================================================
    # MACRO SNAPSHOT STRIP
    # ============================================================
    macro = snapshot.get("macro", {})
    if macro:
        tiles_html = ""
        for name in ["Brent", "WTI", "DXY", "S&P 500", "VIX", "Gold"]:
            info = macro.get(name)
            if not info:
                continue
            color = "#2ECC71" if info["change"] >= 0 else "#E74C3C"
            arrow = "▲" if info["change"] >= 0 else "▼"
            tiles_html += (
                f'<div class="replay-tile">'
                f'<div class="replay-tile-label">{name}</div>'
                f'<div class="replay-tile-value">{info["latest"]:.2f}</div>'
                f'<div class="replay-tile-change" style="color:{color};">'
                f'{arrow} {info["change"]:+.2f}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div class="panel">'
            f'<div class="panel-title">Macro Snapshot · As of {snapshot["date"].strftime("%d %b %Y")}</div>'
            f'<div class="replay-tile-row">{tiles_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ============================================================
    # TWO COLUMNS: forward curve | calendar spreads + flies
    # ============================================================
    c_curve, c_data = st.columns([1.3, 1])

    with c_curve:
        st.markdown(
            f'<div class="panel"><div class="panel-title">{replay_instrument} Forward Curve — Replay</div>',
            unsafe_allow_html=True,
        )

        fig = go.Figure()

        priors = snapshot.get("brent_curve_prior", {})
        style_map = {
            "last_month": {"color": "#3D4F62", "width": 1, "dash": "dot",  "name": "1 month prior"},
            "last_week":  {"color": "#5B6E80", "width": 1.2, "dash": "dash", "name": "1 week prior"},
            "yesterday":  {"color": "#7F8C8D", "width": 1.5, "dash": "dash", "name": "Day prior"},
        }
        for key in ["last_month", "last_week", "yesterday"]:
            curve = priors.get(key)
            if not curve:
                continue
            tenors = [m for m, _ in curve]
            prices = [p for _, p in curve]
            s = style_map[key]
            fig.add_trace(go.Scatter(
                x=tenors, y=prices,
                mode="lines",
                line=dict(color=s["color"], width=s["width"], dash=s["dash"]),
                name=s["name"],
            ))

        curve = snapshot.get("brent_curve", [])
        if curve:
            tenors = [m for m, _ in curve]
            prices = [p for _, p in curve]
            fig.add_trace(go.Scatter(
                x=tenors, y=prices,
                mode="lines+markers",
                line=dict(color="#9B59B6", width=2.5),
                marker=dict(size=4, color="#9B59B6"),
                name=f"This day ({snapshot['date'].strftime('%d %b')})",
            ))

        fig.update_layout(
            height=320,
            margin=dict(l=50, r=20, t=20, b=40),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8B9DAE", family="Inter, sans-serif", size=11),
            legend=dict(orientation="h", yanchor="top", y=1.13,
                        xanchor="right", x=1, font=dict(size=9)),
            xaxis=dict(title="Tenor (months)",
                       gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False),
            yaxis=dict(title="Settlement ($/bbl)",
                       gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            '<div style="color:#5B6E80; font-size:0.65rem; font-style:italic; margin-top:-4px;">'
            'Curves shown: that-day settlement (purple), 1 day prior, 1 week prior, 1 month prior.'
            '</div></div>',
            unsafe_allow_html=True,
        )

    with c_data:
        spreads = snapshot.get("calendar_spreads", [])
        if spreads:
            rows_html = ""
            for s in spreads:
                z = s["z_score"]
                status = s["status"]
                if status == "EXTREME":
                    border = "#E74C3C"
                    badge = "#E74C3C"
                elif status == "ELEVATED":
                    border = "#E67E22"
                    badge = "#E67E22"
                else:
                    border = "#2E75B6"
                    badge = "#8B9DAE"
                rows_html += (
                    f'<div class="replay-row" style="border-left:2px solid {border};">'
                    f'<span class="replay-row-name">{s["name"]}</span>'
                    f'<span class="replay-row-val">${s["value"]:+.2f}</span>'
                    f'<span class="replay-row-badge" style="background:{badge};">'
                    f'{status} · z {z:+.1f}σ</span>'
                    f'</div>'
                )
            st.markdown(
                f'<div class="panel">'
                f'<div class="panel-title">{replay_instrument} Calendar Spreads</div>'
                f'<div class="replay-row-list">{rows_html}</div>'
                f'<div style="color:#5B6E80; font-size:0.62rem; margin-top:6px; font-style:italic;">'
                f'Z-scores computed against the 252-day window ending {snapshot["date"].strftime("%d %b %Y")}.'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        flies = snapshot.get("flies", [])
        if flies:
            rows_html = ""
            for f in flies:
                z = f["z_score"]
                status = f["status"]
                if status == "EXTREME":
                    border = "#E74C3C"
                    badge = "#E74C3C"
                elif status == "ELEVATED":
                    border = "#E67E22"
                    badge = "#E67E22"
                else:
                    border = "#9B59B6"
                    badge = "#8B9DAE"
                rows_html += (
                    f'<div class="replay-row" style="border-left:2px solid {border};">'
                    f'<span class="replay-row-name">{f["name"]}</span>'
                    f'<span class="replay-row-val">{f["value"]:+.2f}</span>'
                    f'<span class="replay-row-badge" style="background:{badge};">'
                    f'{status} · z {z:+.1f}σ</span>'
                    f'</div>'
                )
            st.markdown(
                f'<div class="panel">'
                f'<div class="panel-title">{replay_instrument} Butterfly Flies</div>'
                f'<div class="replay-row-list">{rows_html}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ============================================================
    # ALERTS THAT WOULD HAVE FIRED
    # ============================================================
    alerts = generate_replay_alerts(snapshot, max_alerts=12)

    if not alerts:
        st.markdown(
            '<div class="panel panel-unique">'
            '<div class="panel-title">★ Alerts That Would Have Fired</div>'
            '<div style="color:#8B9DAE; padding:20px; text-align:center; font-size:0.85rem;">'
            'No alerts fire on this date — all monitored signals within normal ranges.'
            '</div></div>',
            unsafe_allow_html=True,
        )
    else:
        cards_html = ""
        for a in alerts:
            sev = a["severity"]
            color = severity_color(sev)
            cards_html += (
                f'<div class="alert-card" style="border-left:3px solid {color};">'
                f'<div class="alert-row-top">'
                f'<span class="alert-sev" style="color:{color}; border-color:{color};">{sev}</span>'
                f'<span class="alert-cat">{a["category"]}</span>'
                f'</div>'
                f'<div class="alert-headline">{a["headline"]}</div>'
                f'<div class="alert-detail">{a["detail"]}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div class="panel panel-unique">'
            f'<div class="panel-title">★ Alerts That Would Have Fired ({len(alerts)})</div>'
            f'<div class="replay-alerts-grid">{cards_html}</div>'
            f'<div style="color:#5B6E80; font-size:0.65rem; margin-top:8px; font-style:italic;">'
            f'Computed by running the live alert engine against this date&apos;s data, '
            f'with z-scores using only data available up to {snapshot["date"].strftime("%d %b %Y")}. '
            f'No look-ahead bias.'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ============================================================
    # INTER-PRODUCT SPREADS
    # ============================================================
    ip = snapshot.get("inter_product", [])
    if ip:
        rows_html = ""
        for s in ip:
            status = s["status"]
            if status == "EXTREME":
                border = "#E74C3C"
                badge = "#E74C3C"
            elif status == "ELEVATED":
                border = "#E67E22"
                badge = "#E67E22"
            else:
                border = "#2E75B6"
                badge = "#8B9DAE"
            change_color = "#2ECC71" if s["change"] >= 0 else "#E74C3C"
            change_arrow = "▲" if s["change"] >= 0 else "▼"
            rows_html += (
                f'<div class="replay-row" style="border-left:2px solid {border};">'
                f'<span class="replay-row-name">{s["name"]}</span>'
                f'<span class="replay-row-val">${s["value"]:+.2f}</span>'
                f'<span style="color:{change_color}; font-size:0.74rem; font-family:JetBrains Mono;">'
                f'{change_arrow} {s["change"]:+.2f}</span>'
                f'<span class="replay-row-badge" style="background:{badge};">'
                f'{status}</span>'
                f'</div>'
            )
        st.markdown(
            f'<div class="panel">'
            f'<div class="panel-title">Inter-Product Spreads · As of {snapshot["date"].strftime("%d %b %Y")}</div>'
            f'<div class="replay-row-list">{rows_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
# ============================================================
# FORWARD CURVE WITH MODE SELECTOR (Markets tab, center column)
# ============================================================

def render_forward_curve_with_selector(market_data: dict):
    SETTLEMENT_TENORS = {"Brent": 31, "WTI": 12, "ULSD": 12, "Gasoil": 12}
    """
    Forward curve panel with a 3-mode selector:
    1. WTI only (parametric, with today/yesterday/last-week overlays)
    2. Brent only (real ICE settlement, with overlays)
    3. WTI vs Brent overlay (single curve each, today only)
    """
    import plotly.graph_objects as go
    from forward_curves import build_curve_for_instrument, build_curves_with_history

    st.markdown(
        '<div class="panel">'
        '<div class="panel-title">Forward Curve</div>',
        unsafe_allow_html=True,
    )

    mode = st.radio(
        "Curve view",
        ["Brent (real)", "WTI (real)", "ULSD (real)", "Gasoil (real)", "WTI vs Brent"],
        horizontal=True,
        label_visibility="collapsed",
        key="fwd_curve_mode",
    )

    fig = go.Figure()

    if mode == "WTI vs Brent":
        # Side-by-side overlay
        brent_curve = build_curve_for_instrument("Brent", market_data)
        wti_curve = build_curve_for_instrument("WTI", market_data)

        if brent_curve:
            tenors = [m for m, _ in brent_curve]
            prices = [p for _, p in brent_curve]
            fig.add_trace(go.Scatter(
                x=tenors, y=prices,
                mode="lines+markers",
                line=dict(color="#2E75B6", width=2.5),
                marker=dict(size=4, color="#2E75B6"),
                name="Brent (real ICE)",
                hovertemplate="<b>Brent M%{x}</b><br>$%{y:.2f}<extra></extra>",
            ))

        if wti_curve:
            tenors = [m for m, _ in wti_curve]
            prices = [p for _, p in wti_curve]
            fig.add_trace(go.Scatter(
                x=tenors, y=prices,
                mode="lines+markers",
                line=dict(color="#E67E22", width=2, dash="dash"),
                marker=dict(size=3, color="#E67E22"),
                name="WTI (NYMEX)",
                hovertemplate="<b>WTI M%{x}</b><br>$%{y:.2f}<extra></extra>",
            ))

        note = (
            "Brent: real ICE settlement, 31 contract months. "
            "WTI: real NYMEX settlement, 12 contract months."
        )

    else:
        # Single instrument with historical overlays
        if mode.startswith("Brent"):
            instrument = "Brent"
        elif mode.startswith("WTI ("):
            instrument = "WTI"
        elif mode.startswith("ULSD"):
            instrument = "ULSD"
        elif mode.startswith("Gasoil"):
            instrument = "Gasoil"
        else:
            instrument = "Brent"

        color_main = {
            "Brent":  "#2E75B6",
            "WTI":    "#E67E22",
            "ULSD":   "#2ECC71",
            "Gasoil": "#9B59B6",
        }.get(instrument, "#2E75B6")
        curves = build_curves_with_history(instrument, market_data)

        if not curves:
            st.markdown(
                '<div style="color:#8B9DAE; padding:20px;">'
                'Curve data unavailable.'
                '</div></div>',
                unsafe_allow_html=True,
            )
            return

        # Prior curves (faded)
        last_month = curves.get("last_month") if isinstance(curves, dict) else None
        last_week = curves.get("last_week")
        yesterday = curves.get("yesterday")
        today = curves.get("today")

        if last_month:
            fig.add_trace(go.Scatter(
                x=[m for m, _ in last_month],
                y=[p for _, p in last_month],
                mode="lines",
                line=dict(color="#3D4F62", width=1, dash="dot"),
                name="1 month prior",
            ))
        if last_week:
            fig.add_trace(go.Scatter(
                x=[m for m, _ in last_week],
                y=[p for _, p in last_week],
                mode="lines",
                line=dict(color="#5B6E80", width=1.2, dash="dash"),
                name="1 week prior",
            ))
        if yesterday:
            fig.add_trace(go.Scatter(
                x=[m for m, _ in yesterday],
                y=[p for _, p in yesterday],
                mode="lines",
                line=dict(color="#7F8C8D", width=1.5, dash="dash"),
                name="Day prior",
            ))
        if today:
            fig.add_trace(go.Scatter(
                x=[m for m, _ in today],
                y=[p for _, p in today],
                mode="lines+markers",
                line=dict(color=color_main, width=2.5),
                marker=dict(size=4, color=color_main),
                name="Today",
            ))

        # Date label
        latest_date_str = ""
        if instrument == "Brent":
            try:
                from brent_data import get_historical_curves
                hist = get_historical_curves()
                if hist and "latest_date" in hist:
                    latest_date_str = f" (as of {hist['latest_date'].strftime('%d %b %Y')})"
            except Exception:
                pass

        # Determine note based on instrument
        latest_date_str = ""
        try:
            from settle_data import get_historical_curves, has_real_data
            if has_real_data(instrument):
                hist = get_historical_curves(instrument)
                if hist and "latest_date" in hist:
                    latest_date_str = f" (as of {hist['latest_date'].strftime('%d %b %Y')})"
                tenor_count = SETTLEMENT_TENORS.get(instrument, 12)
                note = f"Real {instrument} settlement, {tenor_count} contract months{latest_date_str}."
            else:
                note = (
            "Brent: real ICE settlement, 31 contract months. "
            "WTI: real NYMEX settlement, 12 contract months."
        )
        except Exception:
            note = (
            "Brent: real ICE settlement, 31 contract months. "
            "WTI: real NYMEX settlement, 12 contract months."
        )

    fig.update_layout(
        height=300,
        margin=dict(l=50, r=20, t=20, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8B9DAE", family="Inter, sans-serif", size=10),
        legend=dict(
            orientation="h",
            yanchor="top", y=1.12,
            xanchor="right", x=1,
            font=dict(size=9),
        ),
        xaxis=dict(
            title="Tenor (months)",
            gridcolor="rgba(31, 58, 92, 0.4)",
            zeroline=False,
        ),
        yaxis=dict(
            title="Price ($/bbl)",
            gridcolor="rgba(31, 58, 92, 0.4)",
            zeroline=False,
        ),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        f'<div style="color:#5B6E80; font-size:0.65rem; font-style:italic; margin-top:-4px;">'
        f'{note}'
        f'</div></div>',
        unsafe_allow_html=True,
    )
# ============================================================
# STRATEGY LAB TAB
# ============================================================
def render_strategies_tab(market_data: dict):
    """Strategy Lab — configure, backtest, save/load, and compare strategies."""
    import plotly.graph_objects as go
    from strategy_engine import run_backtest
    from strategy_store import list_strategies, save_strategy, load_strategy, delete_strategy

    # Initialize comparison-mode session state
    if "strat_compare_mode" not in st.session_state:
        st.session_state["strat_compare_mode"] = False
    if "strat_loaded_config" not in st.session_state:
        st.session_state["strat_loaded_config"] = None

    # ============================================================
    # HERO BANNER
    # ============================================================
    st.markdown(
        '<div style="background: linear-gradient(135deg, rgba(46, 117, 182, 0.12), rgba(91, 168, 217, 0.08)); '
        'border: 1px solid rgba(46, 117, 182, 0.4); border-radius: 6px; '
        'padding: 12px 18px; margin-bottom: 14px;">'
        '<div style="color:#5BA8D9; font-size:0.7rem; font-weight:800; letter-spacing:1.2px;">'
        '⚡ STRATEGY LAB</div>'
        '<div style="color:#E5EBF0; font-size:0.95rem; margin-top:3px;">'
        'Configure a rule-based trading strategy and backtest it against real settlement history.'
        '</div>'
        '<div style="color:#8B9DAE; font-size:0.72rem; font-style:italic; margin-top:6px;">'
        'Bring your own idea. Pick when to enter, what to trade, when to exit. '
        'Save strategies to build a library and compare them side by side.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ============================================================
    # LIBRARY PANEL: load + compare toggle
    # ============================================================
    st.markdown(
        '<div class="panel"><div class="panel-title">Strategy Library</div>',
        unsafe_allow_html=True,
    )

    saved_names = list_strategies()

    lib_col1, lib_col2, lib_col3 = st.columns([2, 1, 1])

    with lib_col1:
        if saved_names:
            selected_to_load = st.selectbox(
                "Load saved strategy",
                ["— select —"] + saved_names,
                key="strat_load_pick",
                label_visibility="collapsed",
            )
            if selected_to_load != "— select —":
                if st.session_state.get("strat_loaded_name_last") != selected_to_load:
                    st.session_state["strat_loaded_config"] = load_strategy(selected_to_load)
                    st.session_state["strat_loaded_name_last"] = selected_to_load
                    st.rerun()
        else:
            st.markdown(
                '<div style="color:#8B9DAE; font-size:0.78rem; padding: 8px 0;">'
                'No saved strategies yet. Build one below and save it.'
                '</div>',
                unsafe_allow_html=True,
            )

    with lib_col2:
        compare_clicked = st.checkbox(
            "Compare two strategies",
            value=st.session_state["strat_compare_mode"],
            key="strat_compare_chk",
            help="Run two strategies side-by-side for comparison.",
        )
        if compare_clicked != st.session_state["strat_compare_mode"]:
            st.session_state["strat_compare_mode"] = compare_clicked
            st.rerun()

    with lib_col3:
        if saved_names and selected_to_load != "— select —":
            if st.button("Delete strategy", key="strat_delete_btn",
                         use_container_width=True):
                delete_strategy(selected_to_load)
                st.session_state["strat_loaded_config"] = None
                st.session_state["strat_loaded_name_last"] = None
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # ============================================================
    # If in COMPARE MODE → split layout
    # ============================================================
    if st.session_state["strat_compare_mode"]:
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(
                '<div style="color:#5BA8D9; font-size:0.78rem; font-weight:800; '
                'letter-spacing:1.2px; padding: 4px 0 10px 0;">STRATEGY A</div>',
                unsafe_allow_html=True,
            )
            strat_a, run_a = _render_rule_builder(slot="A", default_config=st.session_state.get("strat_loaded_config"))

        with col_b:
            st.markdown(
                '<div style="color:#9B59B6; font-size:0.78rem; font-weight:800; '
                'letter-spacing:1.2px; padding: 4px 0 10px 0;">STRATEGY B</div>',
                unsafe_allow_html=True,
            )
            strat_b, run_b = _render_rule_builder(slot="B", default_config=None)

        # Run both if either is clicked (or both)
        if run_a or run_b:
            result_a = run_backtest(strat_a)
            result_b = run_backtest(strat_b)
            _render_comparison_results(strat_a, strat_b, result_a, result_b)
        else:
            st.markdown(
                '<div class="panel">'
                '<div class="panel-title">Backtest Results · Comparison</div>'
                '<div style="color:#8B9DAE; padding:30px; text-align:center; font-size:0.9rem;">'
                'Configure both strategies and click <b>Run Backtest</b> on either side to compare.'
                '</div></div>',
                unsafe_allow_html=True,
            )
        return

    # ============================================================
    # SINGLE-STRATEGY MODE
    # ============================================================
    strategy, run_clicked = _render_rule_builder(
        slot="single",
        default_config=st.session_state.get("strat_loaded_config"),
    )

    if not run_clicked:
        st.markdown(
            '<div class="panel">'
            '<div class="panel-title">Backtest Results</div>'
            '<div style="color:#8B9DAE; padding:30px; text-align:center; font-size:0.9rem;">'
            'Configure your rules above and click <b>Run Backtest</b> to see results.'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    with st.spinner("Running backtest..."):
        result = run_backtest(strategy)

    _render_single_result(strategy, result)

    # ============================================================
    # SAVE STRATEGY PANEL (only after a successful backtest)
    # ============================================================
    if result.get("ok") and result["stats"]["num_trades"] > 0:
        st.markdown(
            '<div class="panel"><div class="panel-title">Save This Strategy</div>',
            unsafe_allow_html=True,
        )
        save_col1, save_col2 = st.columns([3, 1])
        with save_col1:
            save_name = st.text_input(
                "Strategy name",
                value=strategy.get("name", ""),
                key="strat_save_name",
                label_visibility="collapsed",
                placeholder="e.g. Brent M1-M2 mean reversion 2σ",
            )
        with save_col2:
            if st.button("💾  Save to Library", key="strat_save_btn",
                         use_container_width=True, type="primary"):
                if save_strategy(save_name, strategy):
                    st.success(f"Saved as '{save_name}'.")
                else:
                    st.error("Please enter a name.")
        st.markdown('</div>', unsafe_allow_html=True)


def _render_rule_builder(slot: str, default_config: dict = None):
    """
    Render the rule-builder form (signal, position, exit, lookback).
    Returns: (strategy_config_dict, run_button_clicked).
    `slot` is "single", "A", or "B" — used for unique widget keys.
    """
    # Helper: pull defaults from a loaded config or use sane defaults
    def _from_cfg(path: list, default):
        if not default_config:
            return default
        ref = default_config
        for p in path:
            if not isinstance(ref, dict) or p not in ref:
                return default
            ref = ref[p]
        return ref

    metric_label_map = {
        "spread_M1_M2": "M1-M2 spread",
        "spread_M1_M3": "M1-M3 spread",
        "spread_M1_M6": "M1-M6 spread",
        "spread_M1_M12": "M1-M12 spread",
        "fly_M1_M2_M3": "M1-2*M2+M3 fly",
        "fly_M1_M3_M6": "M1-2*M3+M6 fly",
        "fly_M1_M6_M12": "M1-2*M6+M12 fly",
        "front_to_M12_pct": "Front-to-M12 % (curve steepness)",
        "front_vs_ma_20": "% deviation from 20-day MA",
        "front_vs_ma_60": "% deviation from 60-day MA",
        "front_vs_ma_200": "% deviation from 200-day MA",
    }

    # Reverse map for picking
    z_metrics = ["M1-M2 spread", "M1-M3 spread", "M1-M6 spread", "M1-M12 spread",
                 "M1-2*M2+M3 fly", "M1-2*M3+M6 fly", "M1-2*M6+M12 fly"]
    curve_metrics = ["Front-to-M12 % (curve steepness)"]
    price_metrics = ["% deviation from 20-day MA", "% deviation from 60-day MA",
                     "% deviation from 200-day MA"]

    # ---- Determine default signal type from loaded config ----
    default_sig_type = _from_cfg(["signal", "type"], "z_score")
    sig_type_labels = ["Z-score (statistical extreme)", "Curve shape", "Price deviation"]
    sig_type_index = {"z_score": 0, "curve_shape": 1, "price": 2}.get(default_sig_type, 0)

    default_inst = _from_cfg(["signal", "instrument"], "Brent")
    inst_options = ["Brent", "WTI", "ULSD", "Gasoil"]
    inst_index = inst_options.index(default_inst) if default_inst in inst_options else 0

    default_metric_engine = _from_cfg(["signal", "metric"], "spread_M1_M2")
    default_metric_label = metric_label_map.get(default_metric_engine, "M1-M2 spread")

    default_threshold = _from_cfg(["signal", "entry_threshold"], 2.0)
    default_entry_dir = _from_cfg(["signal", "entry_direction"], "above")

    default_struct = _from_cfg(["position", "structure"], "calendar_spread")
    struct_labels = ["Calendar spread", "Butterfly fly", "Outright (front month)"]
    struct_engine_to_label = {
        "calendar_spread": "Calendar spread",
        "fly": "Butterfly fly",
        "outright": "Outright (front month)",
    }
    default_struct_label = struct_engine_to_label.get(default_struct, "Calendar spread")
    struct_index = struct_labels.index(default_struct_label)

    default_pos_dir = _from_cfg(["position", "direction"], "short")

    default_exit_rules = _from_cfg(["exit", "rules"], ["mean_revert", "time_stop"])
    exit_rule_labels = {
        "mean_revert": "Signal reverts to mean",
        "signal_reverse": "Signal crosses back over threshold",
        "time_stop": "Time stop (max holding days)",
    }
    default_exit_labels = [exit_rule_labels[r] for r in default_exit_rules if r in exit_rule_labels]
    if _from_cfg(["exit", "profit_target_pct"], None) is not None:
        default_exit_labels.append("Profit target %")
    if _from_cfg(["exit", "stop_loss_pct"], None) is not None:
        default_exit_labels.append("Stop loss %")

    default_time_stop = _from_cfg(["exit", "time_stop_days"], 20)
    default_lookback = _from_cfg(["lookback_years"], 5)

    # ============================================================
    # RULE BUILDER PANEL
    # ============================================================
    st.markdown(
        '<div class="panel"><div class="panel-title">Rule Builder</div>',
        unsafe_allow_html=True,
    )

    # ---- SIGNAL ----
    st.markdown(
        '<div style="color:#5BA8D9; font-size:0.72rem; font-weight:700; '
        'letter-spacing:1px; margin-bottom:8px;">1. SIGNAL · WHEN TO ENTER</div>',
        unsafe_allow_html=True,
    )

    sig_col1, sig_col2, sig_col3 = st.columns([1, 1, 1])

    with sig_col1:
        signal_type = st.selectbox(
            "Signal type",
            sig_type_labels,
            index=sig_type_index,
            key=f"strat_sigtype_{slot}",
        )

    with sig_col2:
        instrument = st.selectbox(
            "Instrument",
            inst_options,
            index=inst_index,
            key=f"strat_inst_{slot}",
        )

    with sig_col3:
        if signal_type.startswith("Z-score"):
            metric_options = z_metrics
        elif signal_type == "Curve shape":
            metric_options = curve_metrics
        else:
            metric_options = price_metrics

        metric_default_index = 0
        if default_metric_label in metric_options:
            metric_default_index = metric_options.index(default_metric_label)

        metric_choice = st.selectbox(
            "What to measure",
            metric_options,
            index=metric_default_index,
            key=f"strat_metric_{slot}",
        )

    sig_col4, sig_col5 = st.columns([1, 1])

    with sig_col4:
        if signal_type.startswith("Z-score"):
            threshold = st.slider(
                "Entry threshold (σ)",
                min_value=0.5, max_value=3.5,
                value=float(default_threshold) if -3.5 <= float(default_threshold) <= 3.5 else 2.0,
                step=0.1,
                key=f"strat_thresh_{slot}",
            )
        elif signal_type == "Curve shape":
            threshold = st.slider(
                "Entry threshold (% front-to-M12)",
                min_value=-25.0, max_value=25.0,
                value=float(default_threshold) if -25 <= float(default_threshold) <= 25 else -8.0,
                step=0.5,
                key=f"strat_thresh_{slot}",
                help="Negative = contango. Positive = backwardation.",
            )
        else:
            threshold = st.slider(
                "Entry threshold (% deviation)",
                min_value=-30.0, max_value=30.0,
                value=float(default_threshold) if -30 <= float(default_threshold) <= 30 else -10.0,
                step=0.5,
                key=f"strat_thresh_{slot}",
                help="Negative = price below MA. Positive = above MA.",
            )

    with sig_col5:
        entry_dir_idx = 0 if default_entry_dir == "above" else 1
        entry_dir = st.radio(
            "Trigger when value goes",
            ["above threshold", "below threshold"],
            index=entry_dir_idx,
            horizontal=True,
            key=f"strat_entry_dir_{slot}",
        )

    # ---- POSITION ----
    st.markdown(
        '<div style="color:#5BA8D9; font-size:0.72rem; font-weight:700; '
        'letter-spacing:1px; margin-top:18px; margin-bottom:8px;">'
        '2. POSITION · WHAT TO TRADE</div>',
        unsafe_allow_html=True,
    )

    pos_col1, pos_col2 = st.columns([1, 1])

    with pos_col1:
        structure = st.selectbox(
            "Position structure",
            struct_labels,
            index=struct_index,
            key=f"strat_struct_{slot}",
        )

    with pos_col2:
        position_dir = st.radio(
            "Position direction",
            ["long", "short"],
            index=0 if default_pos_dir == "long" else 1,
            horizontal=True,
            key=f"strat_pos_dir_{slot}",
        )

    # ---- EXIT ----
    st.markdown(
        '<div style="color:#5BA8D9; font-size:0.72rem; font-weight:700; '
        'letter-spacing:1px; margin-top:18px; margin-bottom:8px;">'
        '3. EXIT · WHEN TO CLOSE</div>',
        unsafe_allow_html=True,
    )

    exit_col1, exit_col2 = st.columns([1, 1])

    with exit_col1:
        exit_rules_picked = st.multiselect(
            "Exit rules (any triggers exit)",
            ["Signal reverts to mean", "Signal crosses back over threshold",
             "Time stop (max holding days)", "Profit target %", "Stop loss %"],
            default=default_exit_labels,
            key=f"strat_exit_rules_{slot}",
        )

    with exit_col2:
        time_stop = st.number_input(
            "Time stop (days)",
            min_value=1, max_value=120, value=int(default_time_stop), step=1,
            key=f"strat_time_stop_{slot}",
        )

        profit_target = None
        stop_loss = None
        default_profit_pct = _from_cfg(["exit", "profit_target_pct"], None)
        default_stop_pct = _from_cfg(["exit", "stop_loss_pct"], None)

        if "Profit target %" in exit_rules_picked:
            pt_default = float(default_profit_pct) * 100 if default_profit_pct else 5.0
            profit_target = st.number_input(
                "Profit target (%)", min_value=0.5, max_value=50.0,
                value=pt_default, step=0.5,
                key=f"strat_pt_{slot}",
            ) / 100.0
        if "Stop loss %" in exit_rules_picked:
            sl_default = abs(float(default_stop_pct) * 100) if default_stop_pct else 3.0
            stop_loss = -st.number_input(
                "Stop loss (%)", min_value=0.5, max_value=50.0,
                value=sl_default, step=0.5,
                key=f"strat_sl_{slot}",
            ) / 100.0

    # ---- LOOKBACK ----
    st.markdown(
        '<div style="color:#5BA8D9; font-size:0.72rem; font-weight:700; '
        'letter-spacing:1px; margin-top:18px; margin-bottom:8px;">'
        '4. BACKTEST WINDOW</div>',
        unsafe_allow_html=True,
    )

    lookback_years = st.slider(
        "Years of history to test",
        min_value=1, max_value=10, value=int(default_lookback), step=1,
        key=f"strat_lookback_{slot}",
    )

    # ---- RUN BUTTON ----
    st.markdown('<div style="margin-top: 22px;"></div>', unsafe_allow_html=True)
    run_clicked = st.button(
        f"▶  Run Backtest{' (A)' if slot == 'A' else ' (B)' if slot == 'B' else ''}",
        key=f"strat_run_{slot}",
        use_container_width=True,
        type="primary",
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ---- BUILD STRATEGY CONFIG ----
    strategy = _build_strategy_config(
        signal_type=signal_type,
        instrument=instrument,
        metric_choice=metric_choice,
        threshold=threshold,
        entry_dir=entry_dir,
        structure=structure,
        position_dir=position_dir,
        exit_rules_picked=exit_rules_picked,
        time_stop=time_stop,
        profit_target=profit_target,
        stop_loss=stop_loss,
        lookback_years=lookback_years,
    )

    return strategy, run_clicked


def _render_single_result(strategy, result):
    """Render results panel for a single-strategy backtest."""
    import plotly.graph_objects as go

    if not result.get("ok"):
        st.markdown(
            f'<div class="panel">'
            f'<div class="panel-title">Backtest Results</div>'
            f'<div style="color:#E74C3C; padding:20px; text-align:center;">'
            f'Backtest failed: {result.get("reason", "Unknown error")}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        return

    stats = result["stats"]
    trades = result["trades"]

    st.markdown(
        f'<div class="panel">'
        f'<div class="panel-title">Backtest Results · {strategy["name"]}</div>',
        unsafe_allow_html=True,
    )

    if stats["num_trades"] == 0:
        st.markdown(
            '<div style="color:#8B9DAE; padding:20px; text-align:center;">'
            'No trades fired with these rules. Try loosening the entry threshold.'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    win_color = "#2ECC71" if stats["win_rate"] >= 0.55 else "#E67E22" if stats["win_rate"] >= 0.4 else "#E74C3C"
    pnl_color = "#2ECC71" if stats["total_pnl"] > 0 else "#E74C3C"
    sharpe_color = "#2ECC71" if stats["sharpe"] > 1 else "#E67E22" if stats["sharpe"] > 0 else "#E74C3C"

    tiles_html = (
        f'<div class="replay-tile-row">'
        f'<div class="replay-tile">'
        f'<div class="replay-tile-label">TRADES FIRED</div>'
        f'<div class="replay-tile-value">{stats["num_trades"]}</div>'
        f'<div class="replay-tile-change" style="color:#8B9DAE;">'
        f'avg {stats["avg_holding_days"]}d holding</div>'
        f'</div>'

        f'<div class="replay-tile">'
        f'<div class="replay-tile-label">WIN RATE</div>'
        f'<div class="replay-tile-value">{stats["win_rate"]*100:.1f}%</div>'
        f'<div class="replay-tile-change" style="color:{win_color};">'
        f'{"strong" if stats["win_rate"] >= 0.55 else "weak" if stats["win_rate"] < 0.4 else "ok"}</div>'
        f'</div>'

        f'<div class="replay-tile">'
        f'<div class="replay-tile-label">TOTAL PnL</div>'
        f'<div class="replay-tile-value" style="color:{pnl_color};">'
        f'${stats["total_pnl"]:+.2f}</div>'
        f'<div class="replay-tile-change" style="color:#8B9DAE;">'
        f'avg ${stats["avg_pnl"]:+.3f}/trade</div>'
        f'</div>'

        f'<div class="replay-tile">'
        f'<div class="replay-tile-label">SHARPE</div>'
        f'<div class="replay-tile-value" style="color:{sharpe_color};">'
        f'{stats["sharpe"]:.2f}</div>'
        f'<div class="replay-tile-change" style="color:#8B9DAE;">'
        f'risk-adjusted</div>'
        f'</div>'

        f'<div class="replay-tile">'
        f'<div class="replay-tile-label">BEST TRADE</div>'
        f'<div class="replay-tile-value" style="color:#2ECC71;">'
        f'${stats["best_trade"]:+.2f}</div>'
        f'</div>'

        f'<div class="replay-tile">'
        f'<div class="replay-tile-label">WORST TRADE</div>'
        f'<div class="replay-tile-value" style="color:#E74C3C;">'
        f'${stats["worst_trade"]:+.2f}</div>'
        f'<div class="replay-tile-change" style="color:#8B9DAE;">'
        f'max DD ${stats["max_drawdown"]:.2f}</div>'
        f'</div>'
        f'</div>'
    )

    st.markdown(tiles_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if result["equity_curve"]:
        st.markdown(
            '<div class="panel"><div class="panel-title">Cumulative P/L Curve</div>',
            unsafe_allow_html=True,
        )

        curve = result["equity_curve"]
        dates = [c[0] for c in curve]
        values = [c[1] for c in curve]

        fig = go.Figure()
        fig.add_hline(y=0, line_color="rgba(139,157,174,0.3)", line_width=1)
        fig.add_trace(go.Scatter(
            x=dates, y=values,
            mode="lines",
            line=dict(color="#5BA8D9", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(91, 168, 217, 0.08)",
            name="Cumulative P/L",
            hovertemplate="<b>%{x|%d %b %Y}</b><br>$%{y:+.2f}<extra></extra>",
        ))

        for t in trades:
            color = "#2ECC71" if t["pnl"] > 0 else "#E74C3C"
            ydata = [v for d, v in curve if d == t["exit_date"]]
            yval = ydata[0] if ydata else 0
            fig.add_trace(go.Scatter(
                x=[t["exit_date"]], y=[yval],
                mode="markers",
                marker=dict(size=6, color=color, line=dict(width=1, color="white")),
                showlegend=False,
                hovertemplate=(
                    f"<b>Trade closed {t['exit_date'].strftime('%d %b %Y')}</b><br>"
                    f"Entered {t['entry_date'].strftime('%d %b %Y')}<br>"
                    f"Entry: {t['entry_value']:.2f}<br>"
                    f"Exit: {t['exit_value']:.2f}<br>"
                    f"PnL: ${t['pnl']:+.2f}<br>"
                    f"Exit: {t['exit_reason']}<br>"
                    f"Held: {t['holding_days']}d<extra></extra>"
                ),
            ))

        fig.update_layout(
            height=320,
            margin=dict(l=50, r=20, t=20, b=40),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8B9DAE", family="Inter, sans-serif", size=11),
            showlegend=False,
            xaxis=dict(gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False),
            yaxis=dict(title="Cumulative P/L ($)",
                       gridcolor="rgba(31, 58, 92, 0.4)",
                       zeroline=True,
                       zerolinecolor="rgba(139, 157, 174, 0.3)"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown(
            '<div style="color:#5B6E80; font-size:0.65rem; font-style:italic; margin-top:-4px;">'
            'Dots = trade exits. Green = winning, red = losing. Hover for details.'
            '</div></div>',
            unsafe_allow_html=True,
        )

    if trades:
        with st.expander(f"View all {len(trades)} trades", expanded=False):
            import pandas as pd
            trade_df = pd.DataFrame([
                {
                    "Entry": t["entry_date"].strftime("%Y-%m-%d"),
                    "Exit": t["exit_date"].strftime("%Y-%m-%d"),
                    "Days": t["holding_days"],
                    "Entry value": f"{t['entry_value']:+.2f}",
                    "Exit value": f"{t['exit_value']:+.2f}",
                    "P/L": f"${t['pnl']:+.2f}",
                    "Exit reason": t["exit_reason"],
                }
                for t in trades
            ])
            st.dataframe(trade_df, use_container_width=True, hide_index=True)


def _render_comparison_results(strat_a, strat_b, result_a, result_b):
    """Render side-by-side comparison panel for two strategy backtests."""
    import plotly.graph_objects as go

    st.markdown(
        '<div class="panel">'
        '<div class="panel-title">Backtest Results · Comparison</div>',
        unsafe_allow_html=True,
    )

    if not result_a.get("ok") or not result_b.get("ok"):
        st.markdown(
            f'<div style="color:#E74C3C; padding:20px; text-align:center;">'
            f'A: {result_a.get("reason", "ok") if not result_a.get("ok") else "ok"} · '
            f'B: {result_b.get("reason", "ok") if not result_b.get("ok") else "ok"}'
            f'</div>',
            unsafe_allow_html=True,
        )

    stats_a = result_a["stats"]
    stats_b = result_b["stats"]

    # Comparison table — 5 key metrics
    def cell(val_a, val_b, formatter, higher_is_better=True):
        try:
            a = float(val_a)
            b = float(val_b)
            if a > b:
                a_color, b_color = ("#2ECC71" if higher_is_better else "#E74C3C", "#8B9DAE")
            elif b > a:
                a_color, b_color = ("#8B9DAE", "#2ECC71" if higher_is_better else "#E74C3C")
            else:
                a_color = b_color = "#8B9DAE"
        except (ValueError, TypeError):
            a_color = b_color = "#E5EBF0"

        return (
            f'<div style="display:flex; gap:10px;">'
            f'<div style="flex:1; color:{a_color}; font-family:JetBrains Mono; font-weight:700;">{formatter(val_a)}</div>'
            f'<div style="flex:1; color:{b_color}; font-family:JetBrains Mono; font-weight:700;">{formatter(val_b)}</div>'
            f'</div>'
        )

    rows_html = ""
    rows_html += f'<div style="display:flex; gap:10px; padding: 8px 0; border-bottom: 1px solid rgba(46,117,182,0.2);"><div style="flex:0 0 160px; color:#8B9DAE; font-size:0.72rem; font-weight:600;">METRIC</div><div style="flex:1; color:#5BA8D9; font-size:0.78rem; font-weight:700;">A: {strat_a["name"][:40]}</div><div style="flex:1; color:#9B59B6; font-size:0.78rem; font-weight:700;">B: {strat_b["name"][:40]}</div></div>'

    comparisons = [
        ("Trades fired", stats_a["num_trades"], stats_b["num_trades"],
            lambda v: f"{v}", True),
        ("Win rate", stats_a["win_rate"], stats_b["win_rate"],
            lambda v: f"{v*100:.1f}%", True),
        ("Total PnL", stats_a["total_pnl"], stats_b["total_pnl"],
            lambda v: f"${v:+.2f}", True),
        ("Avg PnL / trade", stats_a["avg_pnl"], stats_b["avg_pnl"],
            lambda v: f"${v:+.3f}", True),
        ("Sharpe", stats_a["sharpe"], stats_b["sharpe"],
            lambda v: f"{v:.2f}", True),
        ("Best trade", stats_a["best_trade"], stats_b["best_trade"],
            lambda v: f"${v:+.2f}", True),
        ("Worst trade", stats_a["worst_trade"], stats_b["worst_trade"],
            lambda v: f"${v:+.2f}", False),
        ("Max drawdown", stats_a["max_drawdown"], stats_b["max_drawdown"],
            lambda v: f"${v:.2f}", False),
        ("Avg holding", stats_a["avg_holding_days"], stats_b["avg_holding_days"],
            lambda v: f"{v}d", True),
    ]

    for metric_name, va, vb, fmt, hib in comparisons:
        rows_html += (
            f'<div style="display:flex; gap:10px; padding: 6px 0; '
            f'border-bottom: 1px solid rgba(31,58,92,0.3);">'
            f'<div style="flex:0 0 160px; color:#E5EBF0; font-size:0.78rem;">{metric_name}</div>'
            f'<div style="flex:2;">{cell(va, vb, fmt, hib)}</div>'
            f'</div>'
        )

    st.markdown(rows_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Combined equity curves
    if result_a.get("equity_curve") and result_b.get("equity_curve"):
        st.markdown(
            '<div class="panel"><div class="panel-title">Cumulative P/L Curves Side-by-Side</div>',
            unsafe_allow_html=True,
        )

        fig = go.Figure()
        fig.add_hline(y=0, line_color="rgba(139,157,174,0.3)", line_width=1)

        for label, curve, color in [
            ("A: " + strat_a["name"][:40], result_a["equity_curve"], "#5BA8D9"),
            ("B: " + strat_b["name"][:40], result_b["equity_curve"], "#9B59B6"),
        ]:
            dates = [c[0] for c in curve]
            values = [c[1] for c in curve]
            fig.add_trace(go.Scatter(
                x=dates, y=values,
                mode="lines",
                line=dict(color=color, width=2.2),
                name=label,
                hovertemplate=f"<b>%{{x|%d %b %Y}}</b><br>{label}: $%{{y:+.2f}}<extra></extra>",
            ))

        fig.update_layout(
            height=320,
            margin=dict(l=50, r=20, t=20, b=40),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8B9DAE", family="Inter, sans-serif", size=11),
            legend=dict(orientation="h", yanchor="top", y=1.15,
                        xanchor="right", x=1, font=dict(size=9)),
            xaxis=dict(gridcolor="rgba(31, 58, 92, 0.4)", zeroline=False),
            yaxis=dict(title="Cumulative P/L ($)",
                       gridcolor="rgba(31, 58, 92, 0.4)",
                       zeroline=True,
                       zerolinecolor="rgba(139, 157, 174, 0.3)"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown('</div>', unsafe_allow_html=True)


def _build_strategy_config(
    signal_type, instrument, metric_choice, threshold, entry_dir,
    structure, position_dir, exit_rules_picked, time_stop,
    profit_target, stop_loss, lookback_years
):
    """Translate UI selections to the strategy config dict the engine expects."""

    if signal_type.startswith("Z-score"):
        sig_engine_type = "z_score"
    elif signal_type == "Curve shape":
        sig_engine_type = "curve_shape"
    else:
        sig_engine_type = "price"

    metric_map = {
        "M1-M2 spread": "spread_M1_M2",
        "M1-M3 spread": "spread_M1_M3",
        "M1-M6 spread": "spread_M1_M6",
        "M1-M12 spread": "spread_M1_M12",
        "M1-2*M2+M3 fly": "fly_M1_M2_M3",
        "M1-2*M3+M6 fly": "fly_M1_M3_M6",
        "M1-2*M6+M12 fly": "fly_M1_M6_M12",
        "Front-to-M12 % (curve steepness)": "front_to_M12_pct",
        "% deviation from 20-day MA": "front_vs_ma_20",
        "% deviation from 60-day MA": "front_vs_ma_60",
        "% deviation from 200-day MA": "front_vs_ma_200",
    }
    engine_metric = metric_map.get(metric_choice, "spread_M1_M2")

    struct_map = {
        "Calendar spread": "calendar_spread",
        "Butterfly fly": "fly",
        "Outright (front month)": "outright",
    }
    engine_struct = struct_map.get(structure, "outright")

    exit_engine_rules = []
    if "Signal reverts to mean" in exit_rules_picked:
        exit_engine_rules.append("mean_revert")
    if "Signal crosses back over threshold" in exit_rules_picked:
        exit_engine_rules.append("signal_reverse")
    if "Time stop (max holding days)" in exit_rules_picked:
        exit_engine_rules.append("time_stop")

    entry_engine_dir = "above" if "above" in entry_dir else "below"

    name = f"{instrument} {metric_choice} · {entry_engine_dir} {threshold:+g}"

    return {
        "name": name,
        "signal": {
            "type": sig_engine_type,
            "instrument": instrument,
            "metric": engine_metric,
            "lookback_days": 252,
            "entry_threshold": threshold,
            "entry_direction": entry_engine_dir,
        },
        "position": {
            "structure": engine_struct,
            "direction": position_dir,
        },
        "exit": {
            "rules": exit_engine_rules,
            "time_stop_days": time_stop,
            "profit_target_pct": profit_target,
            "stop_loss_pct": stop_loss,
        },
        "lookback_years": lookback_years,
    }

def _build_strategy_config(
    signal_type, instrument, metric_choice, threshold, entry_dir,
    structure, position_dir, exit_rules_picked, time_stop,
    profit_target, stop_loss, lookback_years
):
    """Translate UI selections to the strategy config dict the engine expects."""

    # --- Map signal type ---
    if signal_type.startswith("Z-score"):
        sig_engine_type = "z_score"
    elif signal_type == "Curve shape":
        sig_engine_type = "curve_shape"
    else:
        sig_engine_type = "price"

    # --- Map metric ---
    metric_map = {
        "M1-M2 spread": "spread_M1_M2",
        "M1-M3 spread": "spread_M1_M3",
        "M1-M6 spread": "spread_M1_M6",
        "M1-M12 spread": "spread_M1_M12",
        "M1-2*M2+M3 fly": "fly_M1_M2_M3",
        "M1-2*M3+M6 fly": "fly_M1_M3_M6",
        "M1-2*M6+M12 fly": "fly_M1_M6_M12",
        "Front-to-M12 % (curve steepness)": "front_to_M12_pct",
        "% deviation from 20-day MA": "front_vs_ma_20",
        "% deviation from 60-day MA": "front_vs_ma_60",
        "% deviation from 200-day MA": "front_vs_ma_200",
    }
    engine_metric = metric_map.get(metric_choice, "spread_M1_M2")

    # --- Map structure ---
    struct_map = {
        "Calendar spread": "calendar_spread",
        "Butterfly fly": "fly",
        "Outright (front month)": "outright",
    }
    engine_struct = struct_map.get(structure, "outright")

    # --- Map exit rules ---
    exit_engine_rules = []
    if "Signal reverts to mean" in exit_rules_picked:
        exit_engine_rules.append("mean_revert")
    if "Signal crosses back over threshold" in exit_rules_picked:
        exit_engine_rules.append("signal_reverse")
    if "Time stop (max holding days)" in exit_rules_picked:
        exit_engine_rules.append("time_stop")

    # --- Map entry direction ---
    entry_engine_dir = "above" if "above" in entry_dir else "below"

    # --- Build name ---
    name = f"{instrument} {metric_choice} · enter {entry_engine_dir} {threshold:+g}"

    return {
        "name": name,
        "signal": {
            "type": sig_engine_type,
            "instrument": instrument,
            "metric": engine_metric,
            "lookback_days": 252,
            "entry_threshold": threshold,
            "entry_direction": entry_engine_dir,
        },
        "position": {
            "structure": engine_struct,
            "direction": position_dir,
        },
        "exit": {
            "rules": exit_engine_rules,
            "time_stop_days": time_stop,
            "profit_target_pct": profit_target,
            "stop_loss_pct": stop_loss,
        },
        "lookback_years": lookback_years,
    }