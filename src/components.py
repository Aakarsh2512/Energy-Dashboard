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
    instrument_name = "WTI"
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
    """Render the full News & Events tab with keyword filtering."""
    from news_data import fetch_and_tag_news, summarize_sentiment

    with st.spinner("Fetching headlines and running LLM tagging (this takes ~30-50 seconds on first load, then cached)..."):
        tagged_news = fetch_and_tag_news(max_to_tag=50)

    if not tagged_news:
        st.markdown(
            '<div class="panel"><div class="panel-title">News</div>'
            '<div style="color:#8B9DAE; padding:30px; text-align:center;">'
            'Could not fetch news. Check Groq API key in .env and internet connection.'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    # ============================================================
    # KEYWORD FILTER
    # ============================================================
    col_search, col_count, col_blank = st.columns([3, 1.5, 2])

    with col_search:
        keyword = st.text_input(
            "Filter by keyword",
            placeholder="Type keywords to filter (e.g. OPEC, Russia, inventory)",
            label_visibility="collapsed",
            key="news_keyword_filter",
        )

    if keyword and keyword.strip():
        kw_lower = keyword.strip().lower()
        keywords = [k.strip() for k in kw_lower.replace(",", " ").split() if k.strip()]
        filtered_news = []
        for item in tagged_news:
            title = item.get("title", "").lower()
            reaction = item.get("tags", {}).get("reaction", "").lower()
            if any(kw in title or kw in reaction for kw in keywords):
                filtered_news.append(item)
    else:
        filtered_news = tagged_news

    with col_count:
        st.markdown(
            f'<div style="padding:6px 0; color:#8B9DAE; font-size:0.78rem; '
            f'font-family:JetBrains Mono;">'
            f'{len(filtered_news)} of {len(tagged_news)} headlines'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ============================================================
    # SENTIMENT SUMMARY (recalculated on filtered set)
    # ============================================================
    sentiment = summarize_sentiment(filtered_news)
    net = sentiment["net_score"]

    if net > 15:
        net_color = "#2ECC71"
        net_label = "BULLISH BIAS"
    elif net < -15:
        net_color = "#E74C3C"
        net_label = "BEARISH BIAS"
    else:
        net_color = "#8B9DAE"
        net_label = "MIXED / NEUTRAL"

    filter_note = f' (filtered by "{keyword}")' if keyword and keyword.strip() else ""

    st.markdown(
        f'<div class="panel">'
        f'<div class="panel-title">★ LLM News Sentiment{filter_note}</div>'
        f'<div style="display:flex; align-items:center; gap:24px;">'
        f'<div>'
        f'<span style="font-size:1.6rem; font-weight:700; color:{net_color}; '
        f'font-family:JetBrains Mono;">{net:+.0f}</span>'
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
        f'Headlines from FinancialJuice, tagged by Llama 3.3 70B (Groq). '
        f'Net score = (bullish − bearish) / total.'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ============================================================
    # NEWS CARDS
    # ============================================================
    if not filtered_news:
        st.markdown(
            f'<div class="panel"><div class="panel-title">Tagged Headlines</div>'
            f'<div style="color:#8B9DAE; padding:30px; text-align:center;">'
            f'No headlines match "{keyword}". Try different keywords or clear the filter.'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        '<div class="panel"><div class="panel-title">Tagged Headlines</div>',
        unsafe_allow_html=True,
    )

    for item in filtered_news:
        _render_news_card(item)

    st.markdown('</div>', unsafe_allow_html=True)

def _render_news_card(item: dict):
    """Render a single tagged news card."""
    tags = item["tags"]
    direction = tags.get("direction", "neutral")
    magnitude = tags.get("magnitude", "minor")
    confidence = tags.get("confidence", 0.0)
    reaction = tags.get("reaction", "")
    contracts = tags.get("contracts", [])

    arrows = {"bullish": "▲", "bearish": "▼", "neutral": "▬"}
    arrow = arrows.get(direction, "▬")

    dir_colors = {"bullish": "#2ECC71", "bearish": "#E74C3C", "neutral": "#8B9DAE"}
    dir_color = dir_colors.get(direction, "#8B9DAE")

    # Magnitude affects left border thickness
    border_width = {"minor": "2px", "moderate": "3px", "major": "4px"}.get(magnitude, "2px")

    contracts_html = ""
    for c in contracts:
        contracts_html += f'<span class="news-contract-tag">{c}</span>'

    title = item.get("title", "")
    published = item.get("published", "")

    st.markdown(
        f'<div class="news-card" style="border-left:{border_width} solid {dir_color};">'
        f'<div class="news-card-top">'
        f'<span class="news-direction" style="color:{dir_color};">{arrow} {direction.upper()}</span>'
        f'<span class="news-magnitude">{magnitude}</span>'
        f'<span class="news-confidence">conf {confidence:.0%}</span>'
        f'<span class="news-contracts">{contracts_html}</span>'
        f'</div>'
        f'<div class="news-title">{title}</div>'
        f'<div class="news-reaction">→ {reaction}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_news_compact(market_data: dict, max_items: int = 5):
    """Compact news panel for the Markets tab right column."""
    from news_data import fetch_and_tag_news

    tagged_news = fetch_and_tag_news(max_to_tag=50)

    if not tagged_news:
        st.markdown(
            '<div class="panel"><div class="panel-title">★ LLM-Tagged News</div>'
            '<div style="color:#8B9DAE; padding:14px; text-align:center; font-size:0.8rem;">'
            'News feed unavailable.</div></div>',
            unsafe_allow_html=True,
        )
        return

    cards_html = ""
    for item in tagged_news[:max_items]:
        tags = item["tags"]
        direction = tags.get("direction", "neutral")
        arrows = {"bullish": "▲", "bearish": "▼", "neutral": "▬"}
        arrow = arrows.get(direction, "▬")
        dir_colors = {"bullish": "#2ECC71", "bearish": "#E74C3C", "neutral": "#8B9DAE"}
        dir_color = dir_colors.get(direction, "#8B9DAE")

        title = item.get("title", "")
        # Truncate long titles for compact view
        if len(title) > 90:
            title = title[:87] + "..."

        cards_html += (
            f'<div class="news-compact-row" style="border-left:2px solid {dir_color};">'
            f'<span class="news-compact-arrow" style="color:{dir_color};">{arrow}</span>'
            f'<span class="news-compact-title">{title}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="panel">'
        f'<div class="panel-title">★ LLM-Tagged News</div>'
        f'<div class="news-compact-list">{cards_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )