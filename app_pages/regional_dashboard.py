"""
Regional Dashboard -- the flagship page. Companion piece to the MENASA Risk
Monitor: tracks how Gulf states, plus a wider set of non-Gulf regional
states and comparators, are navigating the US-China AI/chip competition, via
a Net Alignment Score built from 6 factors. See README.md for full
methodology and country-set history.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scoring import build_composite  # noqa: E402
from mapping import build_choropleth_figure  # noqa: E402
from ui import inject_base_css, page_header, bottom_line, kpi_card, kpi_row, footer, BLUE, RED, NAVY, GRAY, GOLD  # noqa: E402
from constants import GULF_COUNTRIES, COMPARATOR_COUNTRIES  # noqa: E402

GEOJSON_PATH = Path(__file__).resolve().parents[1] / "data" / "geo" / "region_countries.geojson"


def country_tag(country: str) -> str:
    if country in GULF_COUNTRIES:
        return "Gulf"
    if country in COMPARATOR_COUNTRIES:
        return "Comparator"
    return "Regional"


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


def _bottom_line_text(df: pd.DataFrame) -> tuple[str, str]:
    """Templated, computed-from-real-data bottom line -- counts and the
    modal country are pulled from the actual scored dataframe, never
    hard-coded. Returns (text, confidence_label)."""
    scored = df.dropna(subset=["us_integration_depth", "china_exposure_depth"])
    if scored.empty:
        return "Insufficient scored data to characterize a regional pattern.", "Insufficient"

    q_hedgers = scored[(scored["us_integration_depth"] >= 50) & (scored["china_exposure_depth"] >= 50)]
    q_us = scored[(scored["us_integration_depth"] >= 50) & (scored["china_exposure_depth"] < 50)]
    q_autonomous = scored[(scored["us_integration_depth"] < 50) & (scored["china_exposure_depth"] < 50)]
    q_china = scored[(scored["us_integration_depth"] < 50) & (scored["china_exposure_depth"] >= 50)]

    quadrants = {
        "hedging simultaneously with both blocs": q_hedgers,
        "leaning US without significant Chinese tech exposure": q_us,
        "engaging with neither bloc deeply": q_autonomous,
        "leaning China without significant US integration": q_china,
    }
    modal_label, modal_df = max(quadrants.items(), key=lambda kv: len(kv[1]))
    n = len(modal_df)
    example = modal_df.sort_values("net_alignment_score", ascending=False, na_position="last")["country"].iloc[0] if n else "n/a"

    text = (
        f"Of {len(scored)} countries with both sub-scores available, <b>{n} ({n / len(scored):.0%})</b> "
        f"are currently <b>{modal_label}</b> -- {example} is the clearest example. "
        f"{'This makes hedging, not binary bloc alignment, the dominant regional pattern.' if modal_label.startswith('hedging') else 'This is the single largest positioning group in the current dataset, though not necessarily a regional majority.'}"
    )
    return text, "Moderate"


def main() -> None:
    inject_base_css()

    df = load_data()
    scored = df.dropna(subset=["net_alignment_score"])

    page_header(
        "Gulf AI & Tech-Bloc Alignment",
        "Strategic positioning across competing technology ecosystems",
        meta=[f"{len(df)} COUNTRIES", "DATA AS OF: SEPTEMBER 2026", f"COVERAGE: {len(scored)}/{len(df)} SCORED"],
    )

    bl_text, bl_confidence = _bottom_line_text(df)
    bottom_line(f"ANALYST'S BOTTOM LINE &middot; Confidence: {bl_confidence.upper()}", bl_text)

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
  sub-scores together, not the headline number alone (see the positioning chart below).
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
- **No historical time series exists yet.** Every score below is a single current snapshot -- there is no
  month-over-month or trend data to report, and this page will never show a fabricated "+X vs. prior period"
  delta. That becomes possible once multiple dated snapshots accumulate in `data/computed/`.
            """
        )

    st.subheader("US-China positioning")
    scored_xy = df.dropna(subset=["us_integration_depth", "china_exposure_depth"])
    fig_pos = go.Figure()
    fig_pos.add_shape(type="line", x0=50, x1=50, y0=-4, y1=104, line=dict(color=GRAY, width=1, dash="dot"))
    fig_pos.add_shape(type="line", x0=-4, x1=104, y0=50, y1=50, line=dict(color=GRAY, width=1, dash="dot"))
    # x = China Exposure (low->high), y = US Integration (low->high): low-x/high-y is the
    # "low China, high US" corner, etc. -- verified against the axis ranges, not assumed.
    quadrant_labels = [
        dict(x=25, y=97, text="LOW CHINA / HIGH US<br><i>US-oriented</i>", showarrow=False, font=dict(size=10, color=GRAY)),
        dict(x=75, y=97, text="HIGH CHINA / HIGH US<br><i>Strategic hedgers</i>", showarrow=False, font=dict(size=10, color=GRAY)),
        dict(x=25, y=3, text="LOW CHINA / LOW US<br><i>Low integration</i>", showarrow=False, font=dict(size=10, color=GRAY)),
        dict(x=75, y=3, text="HIGH CHINA / LOW US<br><i>China-oriented</i>", showarrow=False, font=dict(size=10, color=GRAY)),
    ]
    fig_pos.update_layout(annotations=quadrant_labels)
    fig_pos.add_trace(
        go.Scatter(
            x=scored_xy["china_exposure_depth"],
            y=scored_xy["us_integration_depth"],
            mode="markers",
            text=scored_xy["country"],
            marker=dict(size=13, color=NAVY, line=dict(width=1, color="white")),
            customdata=scored_xy[["net_alignment_score"]],
            hovertemplate="<b>%{text}</b><br>US Integration: %{y:.0f}<br>China Exposure: %{x:.0f}<br>Net Alignment: %{customdata[0]:.0f}<extra></extra>",
        )
    )
    fig_pos.update_xaxes(title="China Exposure Depth", range=[-4, 104])
    fig_pos.update_yaxes(title="US Integration Depth", range=[-4, 104])
    fig_pos.update_layout(height=560, plot_bgcolor="white", margin=dict(t=30))
    st.plotly_chart(fig_pos, use_container_width=True)
    st.caption(
        "Quadrants are analytical descriptions, not political judgments. A country in the top-right is not "
        "'confused' -- it is maximizing ties with both blocs at once, which this project's own methodology "
        "treats as a distinct, deliberate strategy (see Methodology). Countries with a missing sub-score are "
        "omitted from this chart; see the map below for those. Hover a point for exact values, or see the "
        "table below."
    )
    with st.expander("Positioning data (for reading without hovering)"):
        st.dataframe(
            scored_xy[["country", "us_integration_depth", "china_exposure_depth", "net_alignment_score"]]
            .sort_values("net_alignment_score", ascending=False)
            .rename(columns={
                "country": "Country", "us_integration_depth": "US Integration",
                "china_exposure_depth": "China Exposure", "net_alignment_score": "Net Alignment",
            }),
            hide_index=True,
            use_container_width=True,
        )

    st.subheader("Map by factor")
    MAP_METRICS = {
        "Net Alignment Score": dict(col="net_alignment_score", range=(0, 100), colorscale=[RED, "#f0e6c8", "#a9c4de", BLUE], unit="", cb="0=China-leaning<br>100=US-integrated"),
        "US Integration Depth": dict(col="us_integration_depth", range=(0, 100), colorscale=["#f0e6c8", BLUE], unit="", cb="US Integration Depth"),
        "China Exposure Depth": dict(col="china_exposure_depth", range=(0, 100), colorscale=["#f0e6c8", RED], unit="", cb="China Exposure Depth"),
        "AI Investment ($bn, scored deals)": dict(col="investment_usd_bn", range=(0, max(1.0, df["investment_usd_bn"].max(skipna=True) or 1.0)), colorscale=["#f0e6c8", BLUE], unit="bn", cb="Disclosed AI investment ($bn)"),
        "Compute Capacity (MW, scored deals)": dict(col="compute_mw", range=(0, max(1.0, df["compute_mw"].max(skipna=True) or 1.0)), colorscale=["#f0e6c8", BLUE], unit="MW", cb="Compute capacity (MW)"),
        "AI Governance Maturity (0-5)": dict(col="governance_raw", range=(0, 5), colorscale=["#f0e6c8", GOLD], unit="/5", cb="Governance maturity (0-5)"),
    }
    metric_name = st.selectbox("Metric", options=list(MAP_METRICS.keys()))
    metric = MAP_METRICS[metric_name]
    metric_col = metric["col"]

    geojson = load_geojson()
    # All 17 countries in the bundled GeoJSON are scored; context_ids stays wired up in
    # build_choropleth_figure() in case a future country is added to the map before it's
    # researched and scored (see the pattern this project already went through once).
    context_ids = frozenset(f["id"] for f in geojson["features"] if not f["properties"].get("scored"))
    context_names = {f["id"]: f["properties"]["name"] for f in geojson["features"] if f["id"] in context_ids}
    scores = {row["iso3"]: (None if pd.isna(row[metric_col]) else row[metric_col]) for _, row in df.iterrows()}

    def _hover(row: pd.Series) -> str:
        if pd.isna(row[metric_col]):
            return f"<b>{row['country']}</b><br>{metric_name}: insufficient data"
        val = f"{row[metric_col]:.0f}{metric['unit']}" if metric_col not in ("investment_usd_bn",) else f"${row[metric_col]:.1f}{metric['unit']}"
        return (
            f"<b>{row['country']}</b><br>{metric_name}: {val}"
            f"<br>Net Alignment: {row['net_alignment_score']:.0f}" if pd.notna(row["net_alignment_score"]) else f"<b>{row['country']}</b><br>{metric_name}: {val}"
        )

    hover = {row["iso3"]: _hover(row) for _, row in df.iterrows()}
    hover.update({iso3: f"<b>{name}</b><br>Not tracked by this index -- shown for regional context only" for iso3, name in context_names.items()})
    fig = build_choropleth_figure(
        geojson=geojson,
        scores=scores,
        hover_text=hover,
        colorscale=metric["colorscale"],
        value_range=metric["range"],
        context_ids=context_ids,
        colorbar_title=metric["cb"],
    )
    fig.update_layout(height=560)
    st.plotly_chart(fig, use_container_width=True)
    if metric_col in ("investment_usd_bn", "compute_mw"):
        st.caption(
            f"Only deals counted in the score are shown (see Methodology) -- gray/darker-gray countries may "
            f"still have disclosed activity that didn't meet this project's sourcing bar; check the Country "
            f"Deep Dive page before reading a gap here as genuine zero activity."
        )
    if metric_name == "Net Alignment Score":
        st.caption(
            "**65-100** deep US integration &middot; **50-64** US-leaning, hedging &middot; "
            "**35-49** China-leaning, hedging &middot; **0-34** deep China exposure. All 17 countries on "
            "this map are scored -- hover any of them for the US/China sub-score breakdown.",
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"Darker shading = higher {metric_name}. Light gray = insufficient data for this factor specifically.")
    missing = sorted([c for c in df["country"] if pd.isna(df.loc[df["country"] == c, metric_col]).all()])
    if missing:
        st.caption(f"Tracked but insufficient data for {metric_name} (darker gray, bordered): {', '.join(missing)}")

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
        gov_fig.update_traces(marker_color=NAVY)
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
            wb_fig.update_traces(marker_color=NAVY)
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
