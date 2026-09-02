"""
Scenario Explorer -- live reweighting of the alignment methodology. Never
touches the underlying curated data; only changes how the same cited
numbers are combined. Same purpose as the MENASA Risk Monitor's own
Scenario Explorer: let a reader stress-test the methodology's sensitivity
to its own weighting choices, with named presets carrying a stated
analytical rationale rather than being arbitrary slider positions.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from constants import COUNTRIES  # noqa: E402
from scoring import build_composite  # noqa: E402
from ui import inject_base_css, footer  # noqa: E402

st.set_page_config(page_title="Scenario Explorer | Gulf AI Tracker", page_icon="\U0001F39B️", layout="wide")

PRESETS = {
    "Default (as scored)": {
        "tier": 40, "investment": 30, "compute": 30, "axis_balance": 50,
        "rationale": "The methodology as scored throughout the rest of this tracker -- see README.md for the full weighting rationale.",
    },
    "Export-control-centric": {
        "tier": 70, "investment": 15, "compute": 15, "axis_balance": 50,
        "rationale": "For an analyst who treats formal BIS export-control status as the single most decisive signal of US integration, discounting capital and hardware commitments that could still be reversed by a change in the regulatory relationship.",
    },
    "Capital-and-hardware-centric": {
        "tier": 15, "investment": 45, "compute": 40, "axis_balance": 50,
        "rationale": "For an analyst who thinks money and physical infrastructure already committed on the ground is stickier and more predictive than a regulatory label that could change with the next administration or the next bilateral deal.",
    },
    "China-exposure-weighted": {
        "tier": 40, "investment": 30, "compute": 30, "axis_balance": 25,
        "rationale": "For an analyst prioritizing hedging-risk exposure -- how deep a state's Chinese technology ties run -- over how deep its US integration runs, when assessing overall alignment.",
    },
    "US-integration-weighted": {
        "tier": 40, "investment": 30, "compute": 30, "axis_balance": 75,
        "rationale": "For an analyst who thinks US chip-access depth is the more strategically consequential axis right now, and Chinese telecom exposure is a secondary, slower-moving signal by comparison.",
    },
}


def esc(text) -> str:
    return "" if text is None or (isinstance(text, float) and pd.isna(text)) else str(text).replace("$", "\\$")


@st.cache_data(ttl=3600)
def _composite(tier: float, investment: float, compute: float, axis_balance: float) -> pd.DataFrame:
    return build_composite(
        tier_weight=tier, investment_weight=investment, compute_weight=compute,
        axis_balance=axis_balance / 100,
    )


def main() -> None:
    inject_base_css()
    st.title("Scenario Explorer")
    st.caption(
        "Live reweighting of the alignment methodology -- these controls change how the tracker's cited "
        "figures are *combined*, never the figures themselves. Nothing here edits data/curated/*.csv; every "
        "underlying number stays exactly as sourced elsewhere in this tracker."
    )

    if "preset_choice" not in st.session_state:
        st.session_state.preset_choice = "Default (as scored)"

    preset_name = st.selectbox("Start from a preset", options=list(PRESETS.keys()), key="preset_choice")
    preset = PRESETS[preset_name]
    st.info(f"**{preset_name}:** {preset['rationale']}", icon="\U0001F4CB")

    st.subheader("US Integration Depth -- relative weights")
    st.caption("These three sliders are renormalized to sum to 100% automatically -- set them to any relative proportion.")
    c1, c2, c3 = st.columns(3)
    tier_w = c1.slider("US export-control tier", 0, 100, preset["tier"], key=f"tier_{preset_name}")
    invest_w = c2.slider("AI investment volume", 0, 100, preset["investment"], key=f"invest_{preset_name}")
    compute_w = c3.slider("Compute capacity", 0, 100, preset["compute"], key=f"compute_{preset_name}")

    total = tier_w + invest_w + compute_w
    if total == 0:
        st.warning("All three weights are 0 -- set at least one above 0 to compute US Integration Depth.")
        return
    st.caption(f"Normalized: tier {tier_w/total:.0%} &middot; investment {invest_w/total:.0%} &middot; compute {compute_w/total:.0%}", unsafe_allow_html=True)

    st.subheader("Net Alignment Score -- axis balance")
    axis_balance = st.slider(
        "How much should US Integration Depth count vs. China Exposure Depth?",
        0, 100, preset["axis_balance"],
        format="%d%% US Integration",
        key=f"axis_{preset_name}",
        help="At 50%, this reproduces the tracker's scored formula exactly: 50 + (US Integration - China Exposure) / 2.",
    )
    st.caption(f"{axis_balance}% US Integration Depth &middot; {100 - axis_balance}% China Exposure Depth (inverted)", unsafe_allow_html=True)

    scenario_df = _composite(tier_w, invest_w, compute_w, axis_balance)
    baseline_df = _composite(40, 30, 30, 50)

    st.divider()
    st.subheader("Net Alignment Score: scenario vs. baseline")

    merged = scenario_df[["country", "iso3", "net_alignment_score"]].rename(columns={"net_alignment_score": "scenario"})
    merged["baseline"] = baseline_df["net_alignment_score"]
    merged["delta"] = merged["scenario"] - merged["baseline"]
    merged = merged.sort_values("scenario", ascending=True, na_position="first")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=merged["country"], x=merged["baseline"], name="Baseline (as scored)",
        orientation="h", marker_color="#c3c0b3", opacity=0.85,
    ))
    fig.add_trace(go.Bar(
        y=merged["country"], x=merged["scenario"], name=preset_name,
        orientation="h", marker_color="#2454a6",
    ))
    fig.update_layout(
        barmode="group", height=420, margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Net Alignment Score (0-100)", legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis_range=[0, 100],
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Biggest movers under this scenario")
    movers = merged.dropna(subset=["delta"]).reindex(merged["delta"].abs().sort_values(ascending=False).index)
    if movers.empty:
        st.caption("No countries have both a baseline and scenario score to compare (insufficient underlying data).")
    else:
        for _, row in movers.head(4).iterrows():
            direction = "more US-integrated" if row["delta"] > 0 else "more China-leaning"
            st.caption(f"**{esc(row['country'])}**: {row['baseline']:.0f} → {row['scenario']:.0f} ({row['delta']:+.1f}, reads {direction} under this scenario)")

    st.divider()
    st.caption(
        "This tool exists to test the methodology's own sensitivity to its weighting choices, not to suggest "
        "any one configuration is more 'correct' than the scored default. See README.md for the rationale "
        "behind the default weights, and the standalone brief for the substantive analysis behind the numbers."
    )

    footer()


if __name__ == "__main__":
    main()
