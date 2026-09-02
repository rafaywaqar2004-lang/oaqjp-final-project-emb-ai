"""
12-Month Outlook -- Base Case / Alternative Case per country, built from
this tracker's own Watch Next items. Deliberately not a machine-learning
forecast (see src/outlook.py's docstring) -- every probability is a
qualitative, explicitly analyst-assigned band, never a fabricated
percentage.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from constants import COUNTRIES  # noqa: E402
from outlook_engine import build_outlook  # noqa: E402
from scoring import build_composite  # noqa: E402
from watch_next import load_watch_indicators, watch_items_for  # noqa: E402
from ui import inject_base_css, page_header, confidence_pill, footer  # noqa: E402


@st.cache_data(ttl=3600)
def _composite() -> pd.DataFrame:
    return build_composite()


def _probability_badge(probability: str) -> str:
    return f'<span style="font-family:\'IBM Plex Mono\', monospace; font-weight:700; font-size:0.78rem; text-transform:uppercase;">{probability}</span>'


def main() -> None:
    inject_base_css()
    page_header(
        "12-Month Outlook",
        "Base Case vs. Alternative Case, per country -- not a forecast. Every probability is an analyst-assigned qualitative band, never a fabricated percentage.",
        meta=["DATA AS OF: SEPTEMBER 2026"],
    )

    st.warning(
        "**This is not a predictive model.** This tracker has no historical trend data yet (Score Momentum "
        "is honestly reporting 'Insufficient data' everywhere -- see any Country Deep Dive's Trend section), "
        "so there is nothing to fit a forecast to. Every assessment below is **ANALYST JUDGMENT**, explicitly "
        "labeled as such, built from this tracker's own Watch Next indicators -- never a **MODEL OUTPUT** "
        "(the only model output here is the current position figure, also labeled).",
        icon="⚠️",
    )

    country = st.selectbox("Country", options=list(COUNTRIES.keys()))
    row = _composite()[_composite()["country"] == country].iloc[0]
    watch_df = watch_items_for(load_watch_indicators(), country=country)
    country_watch_items = watch_df[watch_df["scope"] == country]

    outlook = build_outlook(row, country_watch_items)

    st.subheader("Current Position")
    st.caption("MODEL OUTPUT -- computed by this tracker's composite scoring, not a projection.")
    st.info(outlook.current_position_label)

    st.divider()
    bc1, bc2 = st.columns(2)
    with bc1:
        st.subheader("Base Case")
        st.caption(f"{outlook.base_case.label}")
        st.markdown(outlook.base_case.assessment)
        st.markdown(f"**Probability:** {_probability_badge(outlook.base_case.probability)}", unsafe_allow_html=True)
        st.markdown(f"**Confidence:** {confidence_pill(outlook.base_case.confidence)}", unsafe_allow_html=True)
        st.caption(f"Evidence: {outlook.base_case.evidence}")
    with bc2:
        st.subheader("Alternative Case")
        st.caption(f"{outlook.alternative_case.label}")
        st.markdown(outlook.alternative_case.assessment)
        st.markdown(f"**Probability:** {_probability_badge(outlook.alternative_case.probability)}", unsafe_allow_html=True)
        st.markdown(f"**Confidence:** {confidence_pill(outlook.alternative_case.confidence)}", unsafe_allow_html=True)
        st.caption(f"Evidence: {outlook.alternative_case.evidence}")

    st.divider()
    st.subheader("What Would Change Our View")
    if outlook.watch_items.empty:
        st.caption(
            f"No country-specific indicator is on file for {country}. See the Overview's regional Watch Next "
            "section for region-wide indicators (e.g. a new bilateral US authorization precedent) that could "
            "still shift this country's position indirectly."
        )
    else:
        for _, item in outlook.watch_items.iterrows():
            with st.container(border=True):
                st.markdown(f"**{item['indicator']}**")
                st.caption(item["why_it_matters"])
                st.caption(f"Current signal: {item['current_signal']}")

    st.caption(
        "See the Country Deep Dive page for this country's full Key Judgments, Key Drivers, and Strategic "
        "Implications, and the Scenario Lab to test how sensitive the current position is to the "
        "methodology's own weighting choices."
    )

    footer()


if __name__ == "__main__":
    main()
