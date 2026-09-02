"""
Economic Analysis -- this tracker's one serious empirical economic-
analysis module (see src/economic_analysis.py for the computation and its
docstring for why this specific relationship was chosen over the
candidates that were considered and rejected for sample size). Structured
as QUESTION / DATA / VARIABLES / METHOD / RESULT / LIMITATION, with an
explicit ASSOCIATION-not-CAUSATION framing throughout.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from economic_analysis import CANDIDATE_RELATIONSHIPS, diversification_vs_china_exposure, robustness_checks  # noqa: E402
from constants import CURATED_DIR  # noqa: E402
from scoring import build_composite  # noqa: E402
from ui import inject_base_css, page_header, footer, NAVY, GRAY  # noqa: E402


@st.cache_data(ttl=3600)
def _composite() -> pd.DataFrame:
    return build_composite()


@st.cache_data(ttl=3600)
def _diversification() -> pd.DataFrame:
    return pd.read_csv(Path(CURATED_DIR) / "non_oil_diversification.csv")


def main() -> None:
    inject_base_css()
    page_header(
        "Economic Analysis",
        "One serious empirical question, answered with this tracker's own curated data -- not a fabricated econometrics exercise.",
        meta=["DATA AS OF: SEPTEMBER 2026"],
    )

    df = _composite()

    st.subheader("Question")
    st.markdown(
        "**Is a country's AI governance maturity associated with its US export-control access tier?** In "
        "other words: do countries that have built more institutional capacity around AI (a dedicated "
        "regulator, a national strategy, binding sectoral rules) also tend to hold more favorable US chip-"
        "access status -- or are the two unrelated?"
    )

    st.subheader("Data")
    st.markdown(
        f"All **{len(df)} tracked countries**, a single cross-sectional snapshot (September 2026) from this "
        "tracker's own curated datasets (`data/curated/governance_maturity.csv` and "
        "`data/curated/export_control_tier.csv`) -- no external dataset, no scraped panel, nothing beyond "
        "what this project already sources and cites elsewhere."
    )

    st.subheader("Variables")
    v1, v2 = st.columns(2)
    v1.markdown("**AI Governance Maturity** (0-5 ordinal)\n\nExistence of a national AI strategy, a dedicated authority/regulator, and binding sectoral rules.")
    v2.markdown("**US Export-Control Tier** (0-5 ordinal)\n\nFormal BIS bilateral chip-access status -- see Methodology page for the full rubric.")
    st.caption("Both variables are scored for all 17 tracked countries -- unlike investment/compute figures, no row is dropped for missing data here.")

    st.subheader("Method")
    st.markdown(
        "**Pearson and Spearman correlation coefficients**, not a fitted regression. With n=17 and two "
        "5-point ordinal scales, a regression line would imply a precision the data doesn't support -- a "
        "correlation coefficient makes the same point about association strength without that false "
        "precision. Reported alongside two **robustness checks**: does the association survive excluding "
        "the two highest-scoring countries (Saudi Arabia, UAE), and does it survive excluding the two "
        "countries that share a 0/0 floor (Yemen, Afghanistan)? If a correlation only exists because of 2-4 "
        "extreme points, that's worth knowing before treating it as a general pattern."
    )

    st.subheader("Result")
    results = robustness_checks(df)
    full = results[0]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["governance_raw"], y=df["us_tier_raw"], mode="markers+text",
        text=df["country"], textposition="top center", textfont=dict(size=9, color=GRAY),
        marker=dict(size=11, color=NAVY, line=dict(width=1, color="white")),
        hovertemplate="<b>%{text}</b><br>Governance: %{x}/5<br>US Tier: %{y}/5<extra></extra>",
    ))
    fig.update_xaxes(title="AI Governance Maturity (0-5)", range=[-0.5, 5.5], dtick=1)
    fig.update_yaxes(title="US Export-Control Tier (0-5)", range=[-0.5, 5.5], dtick=1)
    fig.update_layout(height=480, plot_bgcolor="white", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("Pearson r (full sample, n=17)", f"{full.pearson_r:.2f}")
    rc2.metric("Spearman ρ (full sample, n=17)", f"{full.spearman_rho:.2f}")
    rc3.metric("Association strength", full.strength_label.replace("-", " ").title())

    st.markdown("**Robustness checks:**")
    robustness_df = pd.DataFrame([
        {"Sample": "Full sample", "n": r.n, "Pearson r": f"{r.pearson_r:.2f}"} for r in results
    ])
    robustness_df.loc[1, "Sample"] = "Excluding Saudi Arabia & UAE"
    robustness_df.loc[2, "Sample"] = "Excluding Yemen & Afghanistan"
    st.dataframe(robustness_df, hide_index=True, use_container_width=True)
    st.caption(
        f"The association ({full.pearson_r:.2f} full sample) weakens somewhat but does not disappear under "
        "either exclusion (r stays between "
        f"{min(r.pearson_r for r in results):.2f} and {max(r.pearson_r for r in results):.2f}) -- this is "
        "not purely an artifact of 2-4 extreme points, though the small overall sample means this should "
        "still be read as suggestive, not definitive."
    )

    st.subheader("Limitation")
    st.info(
        "**ASSOCIATION, not CAUSATION.** At least three distinct causal stories are consistent with this "
        "same correlation, and cross-sectional data from a single snapshot cannot distinguish between them:\n\n"
        "1. Governance maturity → tier: countries seen as having more institutional capacity may be judged "
        "more 'ready' partners for bilateral chip-access deals.\n"
        "2. Tier → governance: countries that win chip-access deals may build governance institutions "
        "afterward, partly as a condition of those deals (the Saudi/UAE authorizations both carry explicit "
        "'security and reporting conditions').\n"
        "3. A confound: both could be driven by a third factor (overall state AI ambition/capacity) that "
        "this analysis doesn't measure directly.\n\n"
        "No claim of statistical significance is made or implied -- with n=17, a formal significance test "
        "would itself be a form of false precision. This module reports **descriptive association strength**, "
        "explicitly, and nothing more.",
        icon="⚠️",
    )

    st.divider()
    st.subheader("Supplementary finding: economic diversification vs. China exposure")
    st.caption(
        "This project's live World Bank pipeline for non-oil economic diversification is unpopulated in its "
        "development sandbox (outbound network access to api.worldbank.org is blocked there -- see the "
        "Sources & Data page). Rather than leave this angle unexplored, a manual research pass sourced real, "
        "cited non-oil GDP share figures from IMF/national-statistics releases for 8 of 17 countries "
        "(`data/curated/non_oil_diversification.csv`) -- the other 9 are structurally not-applicable "
        "(not hydrocarbon-rent economies, so the proxy itself doesn't mean anything for them, not a data gap)."
    )
    div = _diversification()
    div_result = diversification_vs_china_exposure(df, div)
    dv1, dv2, dv3 = st.columns(3)
    dv1.metric("Pearson r (n=8)", f"{div_result.pearson_r:.2f}")
    dv2.metric("Spearman ρ (n=8)", f"{div_result.spearman_rho:.2f}")
    dv3.metric("Association strength", div_result.strength_label.replace("-", " ").title())

    div_fig = go.Figure()
    merged = df.merge(div[["country", "non_oil_gdp_share_pct", "confidence"]], on="country", how="left")
    plot_df = merged.dropna(subset=["non_oil_gdp_share_pct"])
    div_fig.add_trace(go.Scatter(
        x=plot_df["non_oil_gdp_share_pct"], y=plot_df["china_exposure_depth"], mode="markers+text",
        text=plot_df["country"], textposition="top center", textfont=dict(size=9, color=GRAY),
        marker=dict(size=11, color=NAVY, line=dict(width=1, color="white")),
        hovertemplate="<b>%{text}</b><br>Non-oil GDP share: %{x}%<br>China Exposure: %{y:.0f}<extra></extra>",
    ))
    div_fig.update_xaxes(title="Non-Oil GDP Share (%)")
    div_fig.update_yaxes(title="China Exposure Depth (0-100)", range=[-5, 105])
    div_fig.update_layout(height=420, plot_bgcolor="white", margin=dict(t=20))
    st.plotly_chart(div_fig, use_container_width=True)

    st.warning(
        f"**n={div_result.n} -- exploratory only, not a robustness-checked finding.** A moderate negative "
        "association (more diversified economies tending toward somewhat lower China Exposure Depth) is "
        "visible in this 8-country sample, but a sample this size cannot rule out one or two countries "
        "driving the entire pattern, and no causal direction is implied (diversified economies might simply "
        "have less need for any single foreign technology partner, oil or tech). Presented as a secondary, "
        "smaller-sample supplement to the primary n=17 governance/tier finding above, not a replacement for it.",
        icon="🔍",
    )
    with st.expander("Non-oil GDP share by country, with sources"):
        st.dataframe(
            div[div["non_oil_gdp_share_pct"].notna()][["country", "non_oil_gdp_share_pct", "as_of_year", "figure_type", "confidence", "source_name"]].rename(columns={
                "non_oil_gdp_share_pct": "Non-oil GDP share (%)", "as_of_year": "As of", "figure_type": "Figure type",
                "confidence": "Confidence", "source_name": "Source",
            }),
            hide_index=True, use_container_width=True,
        )

    with st.expander("Other relationships considered and rejected -- and why"):
        st.caption(
            "In choosing 'the strongest defensible relationship' (per this project's own analytical "
            "standard), these candidates were considered first and rejected -- shown here so the choice "
            "above isn't a black box."
        )
        st.dataframe(
            pd.DataFrame(CANDIDATE_RELATIONSHIPS).rename(columns={
                "pair": "Candidate relationship", "n": "n (countries with both values)", "reject_reason": "Why it was rejected",
            }),
            hide_index=True, use_container_width=True,
        )

    st.caption(
        "This is a descriptive/associational analysis appropriate to a 17-country cross-section, not a "
        "claim of statistical significance or a predictive model. See the Sources & Data page for the "
        "underlying datasets."
    )

    footer()


if __name__ == "__main__":
    main()
