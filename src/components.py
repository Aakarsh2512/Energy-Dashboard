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


def render_header(title: str, subtitle: str):
    """Render the dashboard header — title and subtitle line."""
    st.markdown(f"<h1>{title}</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:#8B9DAE; font-size:0.85rem; margin-bottom:0.5rem;'>{subtitle}</div>",
        unsafe_allow_html=True,
    )


def render_top_strip(items: list[dict]):
    """
    Render the persistent top strip of quotes.

    items: list of dicts like:
        {"label": "WTI", "value": "82.15", "change": "+0.42", "direction": "up"}
        direction is "up", "down", or "neutral"
    """
    html_parts = ['<div class="top-strip">']

    for item in items:
        change_class = item.get("direction", "neutral")
        change_text = item.get("change", "")
        change_html = (
            f'<span class="top-strip-change {change_class}">{change_text}</span>'
            if change_text else ""
        )

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