"""
Sanctions & Entity List Exposure -- a Sanctions Exposure Score (0-100) per
country built from data/curated/sanctions_data.csv (see
src/sanctions_engine.py for the scoring logic). Every country's score is
currently backed by 5 of the 6 weighted factors (BIS tier, OFAC programs,
CAATSA status, secondary-sanctions risk, and evasion risk) -- only BIS
Entity List count is "RESEARCH_NEEDED" for all 17 countries, since no
source found publishes a live per-country tally of the Entity List (see
src/sanctions_engine.py's docstring). That gap is disclosed on this page,
not hidden behind a number that looks more complete than it is.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from constants import CURATED_DIR  # noqa: E402
from sanctions_engine import (  # noqa: E402
    SANCTIONS_WEIGHTS, build_sanctions_composite, heatmap_matrix, severity_band,
)
from ui import (  # noqa: E402
    inject_base_css, page_header, key_findings_card, confidence_pill, footer,
    SEVERITY_COLORS, SEVERITY_BAND_ORDER, GRAY, NAVY,
)
from pdf_export import generate_sanctions_brief  # noqa: E402

SANCTIONS_CSV_PATH = Path(CURATED_DIR) / "sanctions_data.csv"


@st.cache_data(ttl=3600)
def _sanctions_composite() -> pd.DataFrame:
    return build_sanctions_composite()


def _score_band_summary(df: pd.DataFrame) -> tuple[str, str, str]:
    """Bottom line / key judgment / why-it-matters text, generated from the
    actual current data -- never hard-coded example findings."""
    scored = df.dropna(subset=["sanctions_exposure_score"])
    n_full_data = int((df["sanctions_factors_available"] >= 5).sum())
    if scored.empty:
        return (
            "No country currently has enough verified sanctions data to compute a Sanctions Exposure Score.",
            "N/A", "N/A",
        )
    top = scored.sort_values("sanctions_exposure_score", ascending=False).iloc[0]
    bottom = scored.sort_values("sanctions_exposure_score", ascending=True).iloc[0]
    if n_full_data == len(df):
        coverage_clause = (
            f"All {len(df)} countries currently have verified data for 5 or more of the 6 weighted factors -- "
            "only BIS Entity List count remains RESEARCH_NEEDED across the board, since no source found "
            "publishes a live per-country tally of the Entity List."
        )
    else:
        coverage_clause = (
            f"Only {n_full_data} of {len(df)} countries currently have verified data for 5 or more of the 6 "
            "weighted factors -- the rest still have one or more RESEARCH_NEEDED factors pending further sourcing."
        )
    bluf = (
        f"Of {len(scored)} tracked countries, {top['country']} carries the highest disclosed Sanctions Exposure "
        f"Score ({top['sanctions_exposure_score']:.0f}/100) and {bottom['country']} the lowest "
        f"({bottom['sanctions_exposure_score']:.0f}/100). {coverage_clause}"
    )
    key_judgment = (
        f"{top['country']}'s exposure is driven primarily by its BIS Country Group classification "
        f"({severity_band(top['bis_tier_score_100'])} band) "
        + (f"and an active CAATSA-related designation" if top.get("caatsa_score_100", 0) >= 80 else "")
        + " -- see the per-country detail below for the specific factors behind the number."
    )
    why = (
        "A high Sanctions Exposure Score compounds risk that is otherwise invisible on the Net Alignment axis "
        "alone: a country can score as 'hedging' on US-China alignment while separately facing real US/EU/UN "
        "restriction exposure that has nothing to do with its chip-market positioning."
    )
    return bluf, key_judgment, why


def _view_calculation_expander() -> None:
    with st.expander("View Calculation"):
        st.markdown(
            """
The Sanctions Exposure Score (0-100) is a weighted average of six 0-100 sub-scores, **renormalized over
whichever factors have verified data** for a given country (a missing factor is excluded, never scored as
zero) -- the same missing-data rule this tracker's composite Net Alignment Score uses.

| Factor | Weight | How it's derived |
|---|---|---|
| Entity List count | 25% | `min(100, count / 20 * 100)` -- 20+ BIS Entity List entries from one of these 17 countries would already be an extreme outlier, so 20 is used as the "scores 100" ceiling. |
| BIS tier restrictiveness | 20% | `(5 - tier_score) / 5 * 100`, reusing this project's own already-cited `export_control_tier.csv` tier_score (0-5, 5 = most favorable) -- never re-derived as a fresh judgment call. |
| OFAC active programs | 20% | `min(100, program_count * 50)` -- "None" scores 0; each additional named program adds 50, capped at 100. |
| CAATSA status | 10% | An active designation scores 100, a disclosed "threatened" status scores 50, "None" scores 0. |
| Secondary sanctions risk | 15% | Low=0, Moderate=50, High=100 (from the curated `secondary_sanctions_risk` analyst judgment). |
| Evasion risk | 10% | Low=0, Moderate=50, High=75, Severe=100 (from the curated `sanctions_evasion_risk` analyst judgment). |

Weights sum to 100%. "Insufficient data" factors are excluded and the remaining weights renormalized to sum
to 1 for that country -- exactly how many factors backed a given score is shown as "N of 6 factors" wherever
the score appears on this page.
            """
        )


def _summary_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df[[
        "country", "entity_list_count", "bis_tier", "ofac_programs", "caatsa_status",
        "secondary_sanctions_risk", "sanctions_evasion_risk", "sanctions_exposure_score", "sanctions_factors_available",
    ]].copy()
    out["sanctions_exposure_score"] = out["sanctions_exposure_score"].round(1)
    out["Composite Sanctions Score"] = out.apply(
        lambda r: f"{r['sanctions_exposure_score']:.0f}/100 ({int(r['sanctions_factors_available'])}/6 factors)"
        if pd.notna(r["sanctions_exposure_score"]) else "Insufficient data", axis=1,
    )
    out = out.rename(columns={
        "country": "Country", "entity_list_count": "Entity List Count", "bis_tier": "BIS Tier",
        "ofac_programs": "OFAC Programs", "caatsa_status": "CAATSA Status",
        "secondary_sanctions_risk": "Secondary Sanctions Risk", "sanctions_evasion_risk": "Evasion Risk",
    })
    return out[[
        "Country", "Entity List Count", "BIS Tier", "OFAC Programs", "CAATSA Status",
        "Secondary Sanctions Risk", "Evasion Risk", "Composite Sanctions Score",
    ]]


def _heatmap(df: pd.DataFrame) -> go.Figure:
    matrix = heatmap_matrix(df)
    band_to_rank = {b: i for i, b in enumerate(SEVERITY_BAND_ORDER)}
    z = matrix.apply(lambda col: col.map(band_to_rank))
    text = matrix.values
    colorscale = [[i / (len(SEVERITY_BAND_ORDER) - 1), SEVERITY_COLORS[b]] for i, b in enumerate(SEVERITY_BAND_ORDER)]
    fig = go.Figure(data=go.Heatmap(
        z=z.values, x=matrix.columns, y=matrix.index, text=text, texttemplate="%{text}",
        colorscale=colorscale, zmin=0, zmax=len(SEVERITY_BAND_ORDER) - 1,
        colorbar=dict(
            tickmode="array", tickvals=list(range(len(SEVERITY_BAND_ORDER))), ticktext=SEVERITY_BAND_ORDER,
        ),
        hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
    ))
    fig.update_layout(height=560, margin=dict(t=20, b=10))
    return fig


def _bar_chart(df: pd.DataFrame) -> go.Figure:
    scored = df.dropna(subset=["sanctions_exposure_score"]).sort_values("sanctions_exposure_score", ascending=True)
    # Same 5-band severity palette as the heatmap, interpolated as a proper
    # multi-stop scale (not a naive 2-color green->red lerp, which muddies
    # through a dull brown in the middle).
    scale = [
        [0.0, SEVERITY_COLORS["None"]], [0.25, SEVERITY_COLORS["Low"]], [0.5, SEVERITY_COLORS["Moderate"]],
        [0.75, SEVERITY_COLORS["High"]], [1.0, SEVERITY_COLORS["Severe"]],
    ]
    fig = px.bar(
        scored, x="sanctions_exposure_score", y="country", orientation="h",
        color="sanctions_exposure_score", color_continuous_scale=scale,
        range_color=(0, 100), labels={"sanctions_exposure_score": "Sanctions Exposure Score", "country": ""},
    )
    fig.update_layout(height=520, margin=dict(t=20), coloraxis_showscale=False)
    return fig


def _positioning_scatter(df: pd.DataFrame) -> go.Figure:
    scored = df.dropna(subset=["sanctions_exposure_score", "net_alignment_score"])
    fig = go.Figure()
    fig.add_shape(type="line", x0=50, x1=50, y0=-4, y1=104, line=dict(color=GRAY, width=1, dash="dot"))
    fig.add_shape(type="line", x0=-4, x1=104, y0=50, y1=50, line=dict(color=GRAY, width=1, dash="dot"))
    fig.update_layout(annotations=[
        dict(x=25, y=97, text="CHINA-LEANING &amp; SANCTIONS-EXPOSED<br><i>(HIGHEST RISK)</i>", showarrow=False, font=dict(size=10, color=GRAY)),
        dict(x=75, y=97, text="US-INTEGRATED &amp; SANCTIONS-EXPOSED", showarrow=False, font=dict(size=10, color=GRAY)),
        dict(x=25, y=3, text="CHINA-LEANING &amp; LOW SANCTIONS", showarrow=False, font=dict(size=10, color=GRAY)),
        dict(x=75, y=3, text="US-INTEGRATED &amp; LOW SANCTIONS", showarrow=False, font=dict(size=10, color=GRAY)),
    ])
    fig.add_trace(go.Scatter(
        x=scored["net_alignment_score"], y=scored["sanctions_exposure_score"], mode="markers+text",
        text=scored["country"], textposition="top center", textfont=dict(size=9, color=GRAY),
        marker=dict(size=13, color=NAVY, line=dict(width=1, color="white")),
        hovertemplate="<b>%{text}</b><br>Net Alignment: %{x:.0f}<br>Sanctions Exposure: %{y:.0f}<extra></extra>",
    ))
    fig.update_xaxes(title="Net Alignment Score (0=China-leaning, 100=US-integrated)", range=[-4, 104])
    fig.update_yaxes(title="Sanctions Exposure Score (0-100)", range=[-4, 104])
    fig.update_layout(height=560, plot_bgcolor="white", margin=dict(t=30))
    return fig


def _admin_data_editor() -> None:
    with st.expander("Edit sanctions data (admin)"):
        st.caption(
            "Edits here write directly to data/curated/sanctions_data.csv on this running server. On most "
            "hosted deployments (e.g. Render, Streamlit Community Cloud) the filesystem is ephemeral -- a "
            "redeploy or restart will discard any change made here that wasn't also committed to the "
            "repository. Treat this as a convenience for local editing/review, not a permanent data store."
        )
        raw = pd.read_csv(SANCTIONS_CSV_PATH)
        edited = st.data_editor(raw, num_rows="dynamic", use_container_width=True, key="sanctions_data_editor")
        if st.button("Save changes to sanctions_data.csv"):
            try:
                edited.to_csv(SANCTIONS_CSV_PATH, index=False)
                st.cache_data.clear()
                st.success("Saved. Reload the page to see the recalculated scores.")
            except OSError as e:
                st.error(f"Could not write to {SANCTIONS_CSV_PATH}: {e}")


def main() -> None:
    inject_base_css()
    page_header(
        "Sanctions & Entity List Exposure",
        "US/EU/UN sanctions, export-control restrictiveness, and evasion-risk exposure, alongside this tracker's own Net Alignment Score",
        meta=["17 COUNTRIES", "MANUALLY CURATED -- VERIFY BEFORE RELYING ON THIS DATA"],
    )

    st.warning(
        "**Disclaimer:** Sanctions data on this page is manually curated and may not reflect real-time "
        "changes. Several fields are explicitly marked RESEARCH_NEEDED where this project has not yet "
        "independently verified a figure -- those factors are excluded from the composite score, not "
        "guessed. Verify with official sources (BIS, OFAC, EU, UN -- see Sources & Data) before relying on "
        "this data for any real decision."
    )

    with st.spinner("Loading sanctions data..."):
        try:
            df = _sanctions_composite()
        except (FileNotFoundError, KeyError) as e:
            st.error(f"Could not load sanctions data: {e}")
            return

    bluf, key_judgment, why = _score_band_summary(df)
    key_findings_card(bluf, key_judgment, "Moderate", why)

    st.download_button(
        "\U0001F4C4 Download Sanctions Brief (PDF)",
        data=generate_sanctions_brief(df, bluf, key_judgment, why),
        file_name="gulf_sanctions_exposure_brief.pdf",
        mime="application/pdf",
    )

    st.divider()
    st.subheader("Summary")
    st.dataframe(
        _summary_table(df), hide_index=True, use_container_width=True, row_height=220,
        column_config={
            "Country": st.column_config.TextColumn("Country", width=140),
            "Entity List Count": st.column_config.TextColumn("Entity List Count", width=160),
            "BIS Tier": st.column_config.TextColumn("BIS Tier", width=300),
            "OFAC Programs": st.column_config.TextColumn("OFAC Programs", width=350),
            "CAATSA Status": st.column_config.TextColumn("CAATSA Status", width=220),
            "Secondary Sanctions Risk": st.column_config.TextColumn("Secondary Sanctions Risk", width=220),
            "Evasion Risk": st.column_config.TextColumn("Evasion Risk", width=220),
            "Composite Sanctions Score": st.column_config.TextColumn("Composite Sanctions Score", width=220),
        },
    )
    _view_calculation_expander()

    st.divider()
    st.subheader("Sanctions heatmap")
    st.caption("Color intensity = severity band per factor. Gray = insufficient verified data, never confused with a real 'None' finding.")
    st.plotly_chart(_heatmap(df), use_container_width=True)

    st.divider()
    st.subheader("Countries ranked by Sanctions Exposure Score")
    st.plotly_chart(_bar_chart(df), use_container_width=True)

    st.divider()
    st.subheader("Sanctions Exposure vs. Net Alignment")
    st.plotly_chart(_positioning_scatter(df), use_container_width=True)
    st.caption(
        "Countries in the top-left quadrant face the greatest strategic risk -- deep Chinese tech integration "
        "combined with active sanctions exposure. Countries missing either score are omitted from this chart."
    )

    st.divider()
    _admin_data_editor()

    footer()


if __name__ == "__main__":
    main()
