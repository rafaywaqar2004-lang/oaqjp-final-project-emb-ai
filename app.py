"""
Gulf AI & Tech-Bloc Alignment Tracker -- Overview page.

Companion piece to the MENASA Risk Monitor: tracks how Gulf states (plus
Pakistan and Turkey as non-Gulf comparators) are navigating the US-China
AI/chip competition, via a Net Alignment Score built from 6 factors.
See README.md for full methodology.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from scoring import build_composite  # noqa: E402
from mapping import build_choropleth_figure  # noqa: E402

GEOJSON_PATH = Path(__file__).resolve().parent / "data" / "geo" / "gulf_countries.geojson"

st.set_page_config(
    page_title="Gulf AI & Tech-Bloc Alignment Tracker",
    page_icon="\U0001F310",
    layout="wide",
)

GULF = {"Saudi Arabia", "United Arab Emirates", "Qatar", "Bahrain", "Kuwait", "Oman"}


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    return build_composite()


@st.cache_data(ttl=3600)
def load_geojson() -> dict:
    with open(GEOJSON_PATH) as f:
        return json.load(f)


def alignment_label(score: float) -> str:
    if pd.isna(score):
        return "Insufficient data"
    if score >= 65:
        return "Deep US integration"
    if score >= 50:
        return "US-leaning, hedging"
    if score >= 35:
        return "China-leaning, hedging"
    return "Deep China exposure"


def main() -> None:
    st.title("Gulf AI & Tech-Bloc Alignment Tracker")
    st.caption(
        "How Gulf states -- plus Pakistan and Turkey as smaller-scale comparators -- are navigating "
        "the US-China AI/chip competition, and what it means for regional stability and Western strategic interests."
    )

    df = load_data()

    with st.expander("Read this before the numbers -- what this index does and doesn't show", expanded=False):
        st.markdown(
            """
This is a research/portfolio project, **not** a forecasting or investment tool.

- **Net Alignment Score (0-100, 50 = neutral)** is a *derived* number: 50 + (US Integration Depth − China Exposure Depth) / 2.
  It measures relative positioning between two axes, not "goodness." A hedging state that maximizes ties with **both**
  blocs can score near the middle for the same reason as a state doing little on either front -- read the two
  sub-scores together, not the headline number alone.
- **US Integration Depth** blends 3 factors (US export-control access tier, disclosed in-country AI investment,
  disclosed compute/data-center capacity). **China Exposure Depth** currently rests on a single factor (Chinese tech
  penetration, chiefly Huawei's telecom footprint) -- a documented limitation, not an oversight.
- Two more factors -- **AI governance maturity** and **non-oil economic diversification** -- are shown as context and
  are *not* folded into the alignment score, since a mature AI regulator or a diversified economy doesn't inherently
  mean pro-US or pro-China.
- Where public data was too thin to support a number, that cell is **explicitly marked missing**, not estimated.
  Qatar, Bahrain, Kuwait, Oman, Pakistan, and Turkey currently have no disclosed investment/compute figures that met
  this project's sourcing bar -- see the Methodology page and README for what was and wasn't found.
            """
        )

    col_map, col_legend = st.columns([3, 1])

    with col_map:
        st.subheader("Net Alignment Score by country")
        geojson = load_geojson()
        scores = {row["iso3"]: (None if pd.isna(row["net_alignment_score"]) else row["net_alignment_score"]) for _, row in df.iterrows()}
        hover = {
            row["iso3"]: (
                f"{row['country']}<br>Net Alignment: {row['net_alignment_score']:.0f}"
                if pd.notna(row["net_alignment_score"])
                else f"{row['country']}<br>Insufficient data for a composite score"
            )
            for _, row in df.iterrows()
        }
        fig = build_choropleth_figure(
            geojson=geojson,
            scores=scores,
            hover_text=hover,
            colorscale=["#e01b24", "#f8e45c", "#62a0ea", "#1a5fb4"],
        )
        st.plotly_chart(fig, use_container_width=True)
        missing = sorted([c for c in df["country"] if pd.isna(df.loc[df["country"] == c, "net_alignment_score"]).all()])
        if missing:
            st.caption(f"Gray on the map (insufficient data for a composite score): {', '.join(missing)}")

    with col_legend:
        st.subheader("Legend")
        st.markdown(
            "- **65-100**: Deep US integration\n"
            "- **50-64**: US-leaning, hedging\n"
            "- **35-49**: China-leaning, hedging\n"
            "- **0-34**: Deep China exposure\n\n"
            "*Gray on the map = insufficient public data for a composite score.*"
        )

    st.divider()
    st.subheader("Country ranking")

    ranked = df.sort_values("net_alignment_score", ascending=False, na_position="last")
    for _, row in ranked.iterrows():
        c1, c2, c3, c4 = st.columns([2, 1, 3, 2])
        with c1:
            tag = "🌊 Gulf" if row["country"] in GULF else "🔶 Comparator"
            st.markdown(f"**{row['country']}**  \n<small>{tag}</small>", unsafe_allow_html=True)
        with c2:
            score = row["net_alignment_score"]
            st.metric("Net Alignment", f"{score:.0f}" if pd.notna(score) else "N/A")
        with c3:
            if pd.notna(score):
                st.progress(int(score))
            st.caption(alignment_label(score))
        with c4:
            us = row["us_integration_depth"]
            cn = row["china_exposure_depth"]
            st.caption(
                f"US Integration: {us:.0f}" if pd.notna(us) else "US Integration: N/A"
            )
            st.caption(
                f"China Exposure: {cn:.0f}" if pd.notna(cn) else "China Exposure: N/A"
            )

    st.divider()
    st.subheader("Context factors (not scored into alignment)")
    ctx_col1, ctx_col2 = st.columns(2)
    with ctx_col1:
        gov_fig = px.bar(
            df.sort_values("governance_raw", ascending=True, na_position="first"),
            x="governance_raw",
            y="country",
            orientation="h",
            range_x=[0, 5],
            labels={"governance_raw": "AI Governance Maturity (0-5)", "country": ""},
            title="AI Governance Maturity",
        )
        gov_fig.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(gov_fig, use_container_width=True)
    with ctx_col2:
        if df["non_oil_diversification_proxy"].notna().any():
            wb_fig = px.bar(
                df.sort_values("non_oil_diversification_proxy", ascending=True, na_position="first"),
                x="non_oil_diversification_proxy",
                y="country",
                orientation="h",
                labels={"non_oil_diversification_proxy": "Non-oil diversification proxy (%)", "country": ""},
                title="Non-oil Economic Diversification (World Bank, live-refreshed)",
            )
            wb_fig.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(wb_fig, use_container_width=True)
        else:
            st.info(
                "World Bank data has not been fetched in this environment yet. This layer is populated by "
                "`src/data_pipeline/fetch_worldbank.py`, run on a schedule by the GitHub Actions workflow once "
                "deployed. It could not be fetched live during development because this sandbox's network policy "
                "blocks `api.worldbank.org` -- it is not a code issue and will resolve automatically on Render/GH Actions."
            )

    st.caption(
        "See the **Country Comparison** page for a full factor-by-factor radar/bar breakdown, and README.md "
        "for the complete methodology, weights, sourcing, and known limitations."
    )


if __name__ == "__main__":
    main()
