"""
Gulf AI & Tech-Bloc Alignment Tracker -- Overview page.

Companion piece to the MENASA Risk Monitor: tracks how Gulf states, plus a
wider set of non-Gulf regional states and comparators, are navigating the
US-China AI/chip competition, via a Net Alignment Score built from 6 factors.
See README.md for full methodology and country-set history.
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
from ui import inject_base_css, kpi_card, kpi_row, footer  # noqa: E402
from constants import GULF_COUNTRIES, COMPARATOR_COUNTRIES  # noqa: E402

GEOJSON_PATH = Path(__file__).resolve().parent / "data" / "geo" / "region_countries.geojson"

st.set_page_config(
    page_title="Gulf AI & Tech-Bloc Alignment Tracker",
    page_icon="assets/favicon.png",
    layout="wide",
)


def country_tag(country: str) -> str:
    if country in GULF_COUNTRIES:
        return "🌊 Gulf"
    if country in COMPARATOR_COUNTRIES:
        return "🔶 Comparator"
    return "🗺️ Regional"


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
    inject_base_css()
    st.title("Gulf AI & Tech-Bloc Alignment Tracker")
    st.caption(
        "How Gulf states -- plus a wider set of non-Gulf regional states and comparators -- are navigating "
        "the US-China AI/chip competition, and what it means for regional stability and Western strategic interests."
    )

    df = load_data()

    scored = df.dropna(subset=["net_alignment_score"])
    most_us = scored.loc[scored["net_alignment_score"].idxmax()] if not scored.empty else None
    most_china = scored.loc[scored["net_alignment_score"].idxmin()] if not scored.empty else None
    coverage = f"{len(scored)} / {len(df)}"

    kpi_row(
        [
            kpi_card(
                "Regional avg. alignment",
                f"{scored['net_alignment_score'].mean():.0f}" if not scored.empty else "N/A",
                "Net Alignment Score, 0-100 scale",
            ),
            kpi_card(
                "Most US-integrated",
                most_us["country"] if most_us is not None else "N/A",
                f"Score {most_us['net_alignment_score']:.0f}" if most_us is not None else "",
            ),
            kpi_card(
                "Most China-leaning",
                most_china["country"] if most_china is not None else "N/A",
                f"Score {most_china['net_alignment_score']:.0f}" if most_china is not None else "",
            ),
            kpi_card(
                "Composite score coverage",
                coverage,
                "countries with enough disclosed data to score",
            ),
        ]
    )

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
  Afghanistan, Bahrain, Iran, Kuwait, Oman, Pakistan, Qatar, Turkey, and Yemen currently have no disclosed
  investment/compute figures that met this project's sourcing bar -- see the Methodology page and README for
  what was and wasn't found.
- **This started as an 8-country Gulf tracker** (Saudi Arabia, UAE, Qatar, Bahrain, Kuwait, Oman, plus
  Pakistan and Turkey as comparators) and later grew to 17 countries so the map's neighboring states --
  originally shown only as unscored gray context -- are properly scored too, not just filler. All 17 use
  the identical methodology; see README.md for exactly when and why each group was added.
            """
        )

    st.subheader("Net Alignment Score by country")
    geojson = load_geojson()
    # All 17 countries in the bundled GeoJSON are scored; context_ids stays wired up in
    # build_choropleth_figure() in case a future country is added to the map before it's
    # researched and scored (see the pattern this project already went through once).
    context_ids = frozenset(f["id"] for f in geojson["features"] if not f["properties"].get("scored"))
    context_names = {f["id"]: f["properties"]["name"] for f in geojson["features"] if f["id"] in context_ids}
    scores = {row["iso3"]: (None if pd.isna(row["net_alignment_score"]) else row["net_alignment_score"]) for _, row in df.iterrows()}

    def _hover(row: pd.Series) -> str:
        if pd.isna(row["net_alignment_score"]):
            return f"<b>{row['country']}</b><br>Insufficient data for a composite score"
        us = f"{row['us_integration_depth']:.0f}" if pd.notna(row["us_integration_depth"]) else "N/A"
        cn = f"{row['china_exposure_depth']:.0f}" if pd.notna(row["china_exposure_depth"]) else "N/A"
        return (
            f"<b>{row['country']}</b><br>Net Alignment: {row['net_alignment_score']:.0f}"
            f"<br>US Integration Depth: {us}<br>China Exposure Depth: {cn}"
        )

    hover = {row["iso3"]: _hover(row) for _, row in df.iterrows()}
    hover.update({iso3: f"<b>{name}</b><br>Not tracked by this index -- shown for regional context only" for iso3, name in context_names.items()})
    fig = build_choropleth_figure(
        geojson=geojson,
        scores=scores,
        hover_text=hover,
        colorscale=["#e01b24", "#f8e45c", "#62a0ea", "#1a5fb4"],
        context_ids=context_ids,
    )
    fig.update_layout(height=560)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "**65-100** deep US integration &middot; **50-64** US-leaning, hedging &middot; "
        "**35-49** China-leaning, hedging &middot; **0-34** deep China exposure. All 17 countries on "
        "this map are scored -- hover any of them for the US/China sub-score breakdown.",
        unsafe_allow_html=True,
    )
    missing = sorted([c for c in df["country"] if pd.isna(df.loc[df["country"] == c, "net_alignment_score"]).all()])
    if missing:
        st.caption(f"Tracked but insufficient data for a composite score (darker gray, bordered): {', '.join(missing)}")

    st.divider()
    st.subheader("Country ranking")

    ranked = df.sort_values("net_alignment_score", ascending=False, na_position="last")
    ranked_rows = list(ranked.iterrows())
    for start in range(0, len(ranked_rows), 4):
        cols = st.columns(4)
        for col, (_, row) in zip(cols, ranked_rows[start:start + 4]):
            with col:
                score = row["net_alignment_score"]
                tag = country_tag(row["country"])
                with st.container(border=True):
                    st.caption(f"{tag}")
                    st.markdown(f"**{row['country']}**")
                    st.metric("Net Alignment", f"{score:.0f}" if pd.notna(score) else "N/A", label_visibility="collapsed")
                    if pd.notna(score):
                        st.progress(int(score))
                    st.caption(alignment_label(score))
                    us = row["us_integration_depth"]
                    cn = row["china_exposure_depth"]
                    st.caption(
                        (f"US {us:.0f}" if pd.notna(us) else "US N/A")
                        + " &middot; "
                        + (f"China {cn:.0f}" if pd.notna(cn) else "China N/A"),
                        unsafe_allow_html=True,
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

    footer()


if __name__ == "__main__":
    main()
