"""
Country Comparison -- factor-by-factor radar and bar views across all 8 countries.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scoring import build_composite  # noqa: E402
from ui import inject_base_css, footer  # noqa: E402

st.set_page_config(page_title="Country Comparison | Gulf AI Tracker", page_icon="\U0001F4CA", layout="wide")

FACTOR_COLUMNS = {
    "us_tier_score_100": "US Export-Control Access",
    "investment_score_100": "AI Investment Volume",
    "compute_score_100": "Compute/Data-Center Capacity",
    "china_penetration_score_100": "Chinese Tech Penetration",
    "governance_score_100": "AI Governance Maturity",
}


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    return build_composite()


def main() -> None:
    inject_base_css()
    st.title("Country Comparison")
    st.caption("All factors normalized to 0-100 for comparability. Hover a bar/vertex for the underlying raw value.")

    df = load_data()

    countries = st.multiselect(
        "Countries to compare",
        options=list(df["country"]),
        default=list(df["country"]),
    )
    view_df = df[df["country"].isin(countries)]

    if view_df.empty:
        st.warning("Select at least one country.")
        return

    st.subheader("Radar: all 6 factors")
    fig = go.Figure()
    categories = list(FACTOR_COLUMNS.values()) + [list(FACTOR_COLUMNS.values())[0]]
    for _, row in view_df.iterrows():
        values = [row[col] if pd.notna(row[col]) else 0 for col in FACTOR_COLUMNS]
        values = values + [values[0]]
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill="toself",
                name=row["country"],
                opacity=0.55,
            )
        )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=560,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "A factor plotted at 0 on the radar may mean 'insufficient public data', not necessarily 'zero activity' -- "
        "check the bar breakdown below and the underlying data/curated/*.csv files before reading a 0 as a genuine floor score."
    )

    st.divider()
    st.subheader("Factor-by-factor bars")
    factor_choice = st.selectbox("Factor", options=list(FACTOR_COLUMNS.keys()), format_func=lambda k: FACTOR_COLUMNS[k])
    bar_df = view_df.sort_values(factor_choice, ascending=True, na_position="first")
    bar_fig = px.bar(
        bar_df,
        x=factor_choice,
        y="country",
        orientation="h",
        range_x=[0, 100],
        labels={factor_choice: FACTOR_COLUMNS[factor_choice], "country": ""},
    )
    bar_fig.update_layout(height=420, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(bar_fig, use_container_width=True)

    st.divider()
    st.subheader("Raw data table")
    display_cols = [
        "country", "us_tier_raw", "china_penetration_raw", "governance_raw",
        "investment_usd_bn", "compute_mw", "non_oil_diversification_proxy",
        "us_integration_depth", "china_exposure_depth", "net_alignment_score",
    ]
    st.dataframe(
        view_df[display_cols].rename(columns={
            "us_tier_raw": "US Tier (0-5)",
            "china_penetration_raw": "China Penetration (0-5)",
            "governance_raw": "Governance (0-5)",
            "investment_usd_bn": "Investment ($bn, scored deals)",
            "compute_mw": "Compute (MW, scored deals)",
            "non_oil_diversification_proxy": "Non-oil proxy (%)",
            "us_integration_depth": "US Integration Depth",
            "china_exposure_depth": "China Exposure Depth",
            "net_alignment_score": "Net Alignment",
        }),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Full source citations for every curated figure live in data/curated/*.csv (columns: source_name, source_url, "
        "confidence, rationale/notes). This table shows what feeds the score; it is not the full research record."
    )

    footer()


if __name__ == "__main__":
    main()
