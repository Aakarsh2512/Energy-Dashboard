"""
Reusable UI components for the Energy Trading Dashboard.
Each function renders a styled element. Keeps app.py clean.
"""

import streamlit as st
from pathlib import Path


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