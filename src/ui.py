"""
Shared visual chrome for the Streamlit app -- one place for the CSS, pill
badges, and footer every page uses, so the "policy product" look (paper/ink
palette, Source Serif 4 headings) matches the standalone briefs instead of
each page reinventing its own styling.
"""

from __future__ import annotations

import streamlit as st

_PILL_COLORS = {
    "high": ("#e4ecf7", "#2454a6"),
    "moderate": ("#f1e8d2", "#8a6416"),
    "low": ("#f1e8d2", "#8a6416"),
    "gap": ("#f6e8e5", "#a93a2e"),
}


def inject_base_css() -> None:
    """Hide default Streamlit chrome and apply the paper/ink design tokens
    shared with the standalone briefs. Safe to call once per page."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@600;700&family=Public+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap');

        #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
        div[data-testid="stDecoration"] { display: none; }
        a[href*="streamlit.io/cloud"], div[data-testid="stStatusWidget"] { display: none; }

        h1, h2, h3, h4 { font-family: 'Source Serif 4', Georgia, serif !important; }

        .kpi-row { display: flex; gap: 0.9rem; flex-wrap: wrap; margin: 0.6rem 0 1.4rem; }
        .kpi-card {
            flex: 1 1 200px; background: var(--secondary-background-color, #e9e8e0);
            border: 1px solid #d7d5cb; border-radius: 0.6rem; padding: 0.9rem 1.1rem;
        }
        .kpi-label {
            font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em;
            color: #7c8188; font-weight: 600; margin-bottom: 0.25rem;
        }
        .kpi-value { font-family: 'Source Serif 4', Georgia, serif; font-size: 1.7rem; font-weight: 700; color: #1b1e22; }
        .kpi-sub { font-size: 0.78rem; color: #52585f; margin-top: 0.15rem; }

        .pill {
            display: inline-block; padding: 0.12rem 0.55rem; border-radius: 999px;
            font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em;
        }

        .app-footer {
            margin-top: 2.5rem; padding-top: 0.9rem; border-top: 1px solid #d7d5cb;
            font-size: 0.75rem; color: #7c8188; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.4rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>{sub_html}</div>'
    )


def kpi_row(cards: list[str]) -> None:
    st.markdown(f'<div class="kpi-row">{"".join(cards)}</div>', unsafe_allow_html=True)


def confidence_pill(confidence: str) -> str:
    key = confidence.lower().split()[0] if confidence else "gap"
    bg, fg = _PILL_COLORS.get(key, _PILL_COLORS["gap"])
    return f'<span class="pill" style="background:{bg}; color:{fg};">{confidence}</span>'


def footer(last_updated: str = "September 2026") -> None:
    st.markdown(
        f"""
        <div class="app-footer">
            <span>Muhammad Rafay Waqar &middot; Gulf AI &amp; Tech-Bloc Alignment Tracker &middot; research/portfolio project</span>
            <span>Data last reviewed: {last_updated}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
