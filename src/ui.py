"""
Shared visual chrome for the Streamlit app -- design tokens, page header,
KPI/evidence/confidence components, and footer every page uses, so the whole
app reads as one restrained "institutional research" product (CSIS/CFR/PIIE
style) rather than each page reinventing its own styling.

Color semantics (deliberately NOT "blue = good, red = bad"):
  blue  = US integration      gold = caution / uncertainty
  red   = China exposure      green = confirmed / operational
                               gray = neutral / unavailable
"""

from __future__ import annotations

import streamlit as st

# -- Design tokens ---------------------------------------------------------
BG = "#F5F4EF"
SURFACE = "#FFFFFF"
SURFACE_2 = "#ECEAE3"
TEXT = "#17202A"
NAVY = "#102A43"
BLUE = "#2463A5"        # US Integration
BLUE_SOFT = "#DCE8F3"
RED = "#B5473A"          # China Exposure
RED_SOFT = "#F3E1DE"
GOLD = "#A77B20"         # caution / uncertainty
GOLD_SOFT = "#F1E8D2"
GREEN = "#397A5B"        # confirmed / operational
GREEN_SOFT = "#E1EBE5"
GRAY = "#6B7280"         # neutral / unavailable
GRAY_SOFT = "#E9E8E0"
LINE = "#D7D5CB"

_CONFIDENCE_COLORS = {
    "high": (GREEN_SOFT, GREEN),
    "moderate": (GOLD_SOFT, GOLD),
    "low": (GRAY_SOFT, GRAY),
    "gap": (GRAY_SOFT, GRAY),
    "insufficient": (GRAY_SOFT, GRAY),
}


def inject_base_css() -> None:
    """Hide default Streamlit chrome and apply the shared design tokens.
    Safe to call once per page."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@600;700&family=Public+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap');

        #MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
        div[data-testid="stDecoration"] {{ display: none; }}
        a[href*="streamlit.io/cloud"], div[data-testid="stStatusWidget"] {{ display: none; }}

        h1, h2, h3, h4 {{ font-family: 'Source Serif 4', Georgia, serif !important; }}

        .page-header {{
            display: flex; justify-content: space-between; align-items: flex-end;
            flex-wrap: wrap; gap: 0.6rem; border-bottom: 2px solid {NAVY}; padding-bottom: 0.7rem;
            margin-bottom: 0.3rem;
        }}
        .page-header-title {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 700; font-size: 1.85rem; color: {TEXT}; line-height: 1.15; }}
        .page-header-subtitle {{ font-size: 0.92rem; color: {GRAY}; margin-top: 0.15rem; }}
        .page-header-meta {{ display: flex; gap: 0.9rem; font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: {GRAY}; text-transform: uppercase; letter-spacing: 0.03em; }}

        .kpi-row {{ display: flex; gap: 0.9rem; flex-wrap: wrap; margin: 0.6rem 0 1.4rem; }}
        .kpi-card {{
            flex: 1 1 200px; background: {SURFACE}; border: 1px solid {LINE};
            border-left: 3px solid {NAVY}; border-radius: 0.25rem; padding: 0.85rem 1.05rem;
        }}
        .kpi-label {{
            font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em;
            color: {GRAY}; font-weight: 600; margin-bottom: 0.3rem; font-family: 'IBM Plex Mono', monospace;
        }}
        .kpi-value-row {{ display: flex; align-items: baseline; gap: 0.5rem; }}
        .kpi-value {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 1.7rem; font-weight: 700; color: {TEXT}; }}
        .kpi-delta {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; font-weight: 600; }}
        .kpi-delta.up {{ color: {GREEN}; }}
        .kpi-delta.down {{ color: {RED}; }}
        .kpi-sub {{ font-size: 0.78rem; color: {GRAY}; margin-top: 0.2rem; }}

        .pill {{
            display: inline-block; padding: 0.12rem 0.55rem; border-radius: 3px;
            font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em;
            font-family: 'IBM Plex Mono', monospace;
        }}

        .bottom-line {{
            background: {SURFACE_2}; border-left: 4px solid {NAVY}; border-radius: 0.25rem;
            padding: 1.1rem 1.3rem; margin: 0.8rem 0 1.4rem;
        }}
        .bottom-line-label {{
            font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.06em; color: {NAVY}; margin-bottom: 0.5rem;
        }}

        .evidence-card {{
            background: {SURFACE}; border: 1px solid {LINE}; border-radius: 0.3rem;
            padding: 0.8rem 1rem; margin-bottom: 0.6rem;
        }}
        .evidence-label {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: {GRAY}; text-transform: uppercase; letter-spacing: 0.03em; }}
        .evidence-title {{ font-weight: 600; color: {TEXT}; margin: 0.2rem 0; }}

        .app-footer {{
            margin-top: 2.5rem; padding-top: 0.9rem; border-top: 1px solid {LINE};
            font-size: 0.75rem; color: {GRAY}; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.4rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str, meta: list[str] | None = None) -> None:
    """Restrained institutional page header: title, subtitle, right-aligned
    mono metadata (e.g. '17 COUNTRIES', 'DATA AS OF: SEPTEMBER 2026')."""
    meta_html = "".join(f"<span>{m}</span>" for m in (meta or []))
    st.markdown(
        f"""
        <div class="page-header">
            <div>
                <div class="page-header-title">{title}</div>
                <div class="page-header-subtitle">{subtitle}</div>
            </div>
            <div class="page-header-meta">{meta_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def bottom_line(label: str, text: str) -> None:
    """A restrained callout for an analyst's bottom-line assessment. `text`
    must be generated from the actual current data -- never hard-coded
    example language presented as a live finding."""
    st.markdown(
        f"""
        <div class="bottom-line">
            <div class="bottom-line-label">{label}</div>
            <div>{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, sub: str = "", delta: float | None = None) -> str:
    delta_html = ""
    if delta is not None:
        direction = "up" if delta >= 0 else "down"
        arrow = "↑" if delta >= 0 else "↓"
        delta_html = f'<span class="kpi-delta {direction}">{arrow} {delta:+.0f}</span>'
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value-row"><div class="kpi-value">{value}</div>{delta_html}</div>{sub_html}</div>'
    )


def kpi_row(cards: list[str]) -> None:
    st.markdown(f'<div class="kpi-row">{"".join(cards)}</div>', unsafe_allow_html=True)


def confidence_pill(confidence: str) -> str:
    key = confidence.lower().split()[0] if confidence else "gap"
    bg, fg = _CONFIDENCE_COLORS.get(key, _CONFIDENCE_COLORS["gap"])
    return f'<span class="pill" style="background:{bg}; color:{fg};">{confidence}</span>'


def evidence_card(title: str, subtitle: str, source_type: str, supports: str, confidence: str, verified: str, url: str | None) -> None:
    link_html = f'<a href="{url}" target="_blank">View Source</a>' if url else '<span style="color:#6B7280;">Source URL unavailable</span>'
    st.markdown(
        f"""
        <div class="evidence-card">
            <div class="evidence-label">EVIDENCE &middot; {source_type}</div>
            <div class="evidence-title">{title}</div>
            <div style="font-size:0.85rem; color:{GRAY};">{subtitle}</div>
            <div style="margin-top:0.5rem; display:flex; gap:0.8rem; align-items:center; font-size:0.8rem;">
                <span>Supports: <b>{supports}</b></span>
                {confidence_pill(confidence)}
                <span style="color:{GRAY};">Verified: {verified}</span>
                {link_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
