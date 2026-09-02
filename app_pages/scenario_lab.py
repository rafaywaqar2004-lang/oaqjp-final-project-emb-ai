"""
Scenario Lab -- live reweighting of the alignment methodology. Never
touches the underlying curated data; only changes how the same cited
numbers are combined. Same purpose as the MENASA Risk Monitor's own
Scenario Lab: let a reader stress-test the methodology's sensitivity
to its own weighting choices, with named presets carrying a stated
analytical rationale rather than being arbitrary slider positions.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from constants import COUNTRIES  # noqa: E402
from scoring import (  # noqa: E402
    build_composite,
    CHINA_DIGITAL_WEIGHT,
    CHINA_TELECOM_WEIGHT,
    COMPUTE_CEILING_MW,
    INVESTMENT_CEILING_USD_BN,
)
from ui import inject_base_css, footer, GREEN, GOLD, GRAY, CHART_BASELINE, CHART_SCENARIO  # noqa: E402

N_ROBUSTNESS_SAMPLES = 150
ROBUSTNESS_SEED = 42


PRESETS = {
    "Default (as scored)": {
        "tier": 40, "investment": 30, "compute": 30, "axis_balance": 50,
        "china_telecom": 50, "china_digital": 50,
        "rationale": "The methodology as scored throughout the rest of this tracker -- see README.md for the full weighting rationale.",
    },
    "Export-control-centric": {
        "tier": 70, "investment": 15, "compute": 15, "axis_balance": 50,
        "china_telecom": 50, "china_digital": 50,
        "rationale": "For an analyst who treats formal BIS export-control status as the single most decisive signal of US integration, discounting capital and hardware commitments that could still be reversed by a change in the regulatory relationship.",
    },
    "Capital-and-hardware-centric": {
        "tier": 15, "investment": 45, "compute": 40, "axis_balance": 50,
        "china_telecom": 50, "china_digital": 50,
        "rationale": "For an analyst who thinks money and physical infrastructure already committed on the ground is stickier and more predictive than a regulatory label that could change with the next administration or the next bilateral deal.",
    },
    "China-exposure-weighted": {
        "tier": 40, "investment": 30, "compute": 30, "axis_balance": 25,
        "china_telecom": 50, "china_digital": 50,
        "rationale": "For an analyst prioritizing hedging-risk exposure -- how deep a state's Chinese technology ties run -- over how deep its US integration runs, when assessing overall alignment.",
    },
    "US-integration-weighted": {
        "tier": 40, "investment": 30, "compute": 30, "axis_balance": 75,
        "china_telecom": 50, "china_digital": 50,
        "rationale": "For an analyst who thinks US chip-access depth is the more strategically consequential axis right now, and Chinese telecom exposure is a secondary, slower-moving signal by comparison.",
    },
    "China-telecom-centric": {
        "tier": 40, "investment": 30, "compute": 30, "axis_balance": 50,
        "china_telecom": 80, "china_digital": 20,
        "rationale": "For an analyst who treats physical telecom-backbone vendor choice (Huawei 5G/fiber) as the harder-to-reverse hedging signal, discounting AI/cloud partnerships that can be renegotiated or dual-sourced more easily.",
    },
    "China-digital-ties-centric": {
        "tier": 40, "investment": 30, "compute": 30, "axis_balance": 50,
        "china_telecom": 20, "china_digital": 80,
        "rationale": "For an analyst who thinks AI-model, cloud, and digital-infrastructure partnerships with Chinese firms are the more strategically consequential exposure right now -- these touch the AI stack directly, where legacy telecom contracts may not.",
    },
}


def esc(text) -> str:
    return "" if text is None or (isinstance(text, float) and pd.isna(text)) else str(text).replace("$", "\\$")


@st.cache_data(ttl=3600)
def _robustness_table(n_samples: int = N_ROBUSTNESS_SAMPLES, seed: int = ROBUSTNESS_SEED) -> pd.DataFrame:
    """Samples n_samples random-but-valid weight configurations (all three
    US Integration sub-weights, both China Exposure sub-weights, and
    axis_balance drawn uniformly, exactly the same valid range the sliders
    above allow) and recomputes the full ranking each time via the same
    build_composite() used everywhere else in this tracker -- no separate
    model, no shortcuts. Reports, per country: how often it lands in the
    top 3, its median rank, and its full rank range across all samples.
    This is scenario/rank *stability*, not a statistical confidence
    interval -- it describes how sensitive the ranking is to plausible
    reweighting, nothing more."""
    rng = np.random.default_rng(seed)
    countries = list(COUNTRIES.keys())
    ranks: dict[str, list[int]] = {c: [] for c in countries}
    top3_hits: dict[str, int] = {c: 0 for c in countries}

    for _ in range(n_samples):
        tier_w, invest_w, compute_w = rng.uniform(1, 100, size=3)
        china_telecom_w, china_digital_w = rng.uniform(1, 100, size=2)
        axis_balance = rng.uniform(0, 100)
        df = build_composite(
            tier_weight=float(tier_w), investment_weight=float(invest_w), compute_weight=float(compute_w),
            axis_balance=float(axis_balance) / 100,
            china_telecom_weight=float(china_telecom_w) / 100, china_digital_weight=float(china_digital_w) / 100,
        )
        ranked = df.dropna(subset=["net_alignment_score"]).sort_values("net_alignment_score", ascending=False)
        for rank, country in enumerate(ranked["country"], start=1):
            ranks[country].append(rank)
            if rank <= 3:
                top3_hits[country] += 1

    rows = []
    for c in countries:
        r = ranks[c]
        if not r:
            continue
        rows.append({
            "country": c,
            "median_rank": int(np.median(r)),
            "rank_min": min(r),
            "rank_max": max(r),
            "rank_range": max(r) - min(r),
            "top3_pct": top3_hits[c] / n_samples,
            "n_samples_scored": len(r),
        })
    return pd.DataFrame(rows).sort_values("median_rank")


def _robustness_label(rank_range: int) -> tuple[str, str]:
    if rank_range <= 2:
        return "HIGH", GREEN
    if rank_range <= 5:
        return "MODERATE", GOLD
    return "LOW", GRAY


def _scenario_interpretation(merged: pd.DataFrame, preset_name: str) -> str:
    """Deterministic, templated interpretation of a scenario run against the
    baseline -- filled from the actual computed ranks, never a free-form
    generated sentence. Mirrors this project's country_brief.py discipline:
    real numbers into a template, not an LLM call."""
    m = merged.dropna(subset=["baseline", "scenario"]).copy()
    if len(m) < 2:
        return "Not enough countries have both a baseline and scenario score to assess ranking stability."

    m["baseline_rank"] = m["baseline"].rank(ascending=False, method="min").astype(int)
    m["scenario_rank"] = m["scenario"].rank(ascending=False, method="min").astype(int)
    m["rank_shift"] = (m["scenario_rank"] - m["baseline_rank"]).abs()

    baseline_top5 = set(m.sort_values("baseline_rank").head(5)["country"])
    scenario_top5 = set(m.sort_values("scenario_rank").head(5)["country"])
    top5_overlap = len(baseline_top5 & scenario_top5)
    big_movers = m[m["rank_shift"] >= 3]

    if preset_name == "Default (as scored)":
        return "This is the scored default -- by definition, it reproduces the baseline ranking exactly."

    if top5_overlap == 5 and big_movers.empty:
        return (
            f"Under **{preset_name}**, the top 5 countries are unchanged and no country's rank moved by 3 or "
            "more places -- the regional ranking looks robust to this particular reweighting."
        )
    if top5_overlap >= 3:
        movers_txt = ", ".join(f"{r['country']} ({int(r['baseline_rank'])}→{int(r['scenario_rank'])})" for _, r in big_movers.sort_values("rank_shift", ascending=False).head(3).iterrows())
        return (
            f"Under **{preset_name}**, {top5_overlap} of the top 5 countries are unchanged, but "
            f"{len(big_movers)} countries move 3+ ranking places" + (f" -- notably {movers_txt}" if movers_txt else "") +
            ". This weighting has a real but partial effect on the ranking."
        )
    return (
        f"Under **{preset_name}**, only {top5_overlap} of the top 5 countries are unchanged from baseline -- "
        "this reweighting materially reorders the regional ranking, not just individual scores. Treat this "
        "scenario's ranking as a genuinely different picture, not a minor variation on the default."
    )


@st.cache_data(ttl=3600)
def _composite(
    tier: float, investment: float, compute: float, axis_balance: float,
    investment_ceiling: float = INVESTMENT_CEILING_USD_BN, compute_ceiling: float = COMPUTE_CEILING_MW,
    china_telecom: float = CHINA_TELECOM_WEIGHT * 100, china_digital: float = CHINA_DIGITAL_WEIGHT * 100,
) -> pd.DataFrame:
    return build_composite(
        tier_weight=tier, investment_weight=investment, compute_weight=compute,
        axis_balance=axis_balance / 100,
        investment_ceiling=investment_ceiling, compute_ceiling=compute_ceiling,
        china_telecom_weight=china_telecom / 100, china_digital_weight=china_digital / 100,
    )


def main() -> None:
    inject_base_css()
    st.title("Scenario Lab")
    st.caption(
        "**ASSUMPTION TEST** -- not a forecast. Live reweighting of the alignment methodology: these controls "
        "change how the tracker's cited figures are *combined*, never the figures themselves. Nothing here "
        "edits data/curated/*.csv; every underlying number stays exactly as sourced elsewhere in this tracker."
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

    st.subheader("China Exposure Depth -- relative weights")
    st.caption(
        "How much should Chinese telecom-vendor penetration (Huawei 5G/fiber) count vs. Chinese AI/cloud/"
        "digital-infrastructure ties, when scoring hedging exposure? Renormalized to sum to 100% automatically."
    )
    cc1, cc2 = st.columns(2)
    china_telecom_w = cc1.slider("Chinese telecom penetration", 0, 100, preset["china_telecom"], key=f"china_telecom_{preset_name}")
    china_digital_w = cc2.slider("Chinese AI/cloud/digital ties", 0, 100, preset["china_digital"], key=f"china_digital_{preset_name}")

    china_total = china_telecom_w + china_digital_w
    if china_total == 0:
        st.warning("Both China Exposure weights are 0 -- set at least one above 0 to compute China Exposure Depth.")
        return
    st.caption(f"Normalized: telecom {china_telecom_w/china_total:.0%} &middot; digital ties {china_digital_w/china_total:.0%}", unsafe_allow_html=True)

    st.subheader("Net Alignment Score -- axis balance")
    axis_balance = st.slider(
        "How much should US Integration Depth count vs. China Exposure Depth?",
        0, 100, preset["axis_balance"],
        format="%d%% US Integration",
        key=f"axis_{preset_name}",
        help="At 50%, this reproduces the tracker's scored formula exactly: 50 + (US Integration - China Exposure) / 2.",
    )
    st.caption(f"{axis_balance}% US Integration Depth &middot; {100 - axis_balance}% China Exposure Depth (inverted)", unsafe_allow_html=True)

    scenario_df = _composite(tier_w, invest_w, compute_w, axis_balance, china_telecom=china_telecom_w, china_digital=china_digital_w)
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
        orientation="h", marker_color=CHART_BASELINE, opacity=0.85,
    ))
    fig.add_trace(go.Bar(
        y=merged["country"], x=merged["scenario"], name=preset_name,
        orientation="h", marker_color=CHART_SCENARIO,
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

    st.info(_scenario_interpretation(merged, preset_name), icon="\U0001F9ED")
    st.caption(
        "This interpretation is templated from the actual computed ranks above (top-5 overlap, count of "
        "3+-place rank shifts) -- never a free-form generated summary."
    )

    st.divider()
    st.subheader("Normalization sensitivity")
    st.caption(
        "The $50bn investment ceiling and 6,000MW compute ceiling (see Methodology) are documented judgment "
        "calls, not derived constants -- 'what it would take to score 100' is an explicit choice, not "
        "self-evident. This checks whether the ranking holds up under an equally-defensible alternative."
    )
    nc1, nc2 = st.columns(2)
    inv_ceiling = nc1.radio("Investment ceiling ($bn)", [25, 50, 100], index=1, horizontal=True, key="inv_ceiling")
    comp_ceiling = nc2.radio("Compute ceiling (MW)", [3000, 6000, 9000], index=1, horizontal=True, key="comp_ceiling")

    sensitivity_df = _composite(
        tier_w, invest_w, compute_w, axis_balance, investment_ceiling=inv_ceiling, compute_ceiling=comp_ceiling,
        china_telecom=china_telecom_w, china_digital=china_digital_w,
    )
    sens_merged = scenario_df[["country", "net_alignment_score"]].rename(columns={"net_alignment_score": "default_ceilings"})
    sens_merged["alternative_ceilings"] = sensitivity_df["net_alignment_score"]
    sens_merged = sens_merged.dropna(subset=["default_ceilings", "alternative_ceilings"])
    sens_merged["default_rank"] = sens_merged["default_ceilings"].rank(ascending=False, method="min").astype(int)
    sens_merged["alternative_rank"] = sens_merged["alternative_ceilings"].rank(ascending=False, method="min").astype(int)
    sens_merged["rank_shift"] = (sens_merged["alternative_rank"] - sens_merged["default_rank"]).abs()

    if inv_ceiling == 50 and comp_ceiling == 6000:
        st.caption("These are the scored default ceilings -- select a different value above to compare.")
    else:
        shifted = sens_merged[sens_merged["rank_shift"] > 0].sort_values("rank_shift", ascending=False)
        if shifted.empty:
            st.success(f"No country's rank changes at ${inv_ceiling}bn / {comp_ceiling}MW ceilings -- the ranking is insensitive to this choice.", icon="✅")
        else:
            st.warning(
                f"{len(shifted)} of {len(sens_merged)} countries' rank changes at ${inv_ceiling}bn / {comp_ceiling}MW "
                "ceilings (vs. the scored $50bn / 6,000MW default):",
                icon="⚠️",
            )
            st.dataframe(
                shifted[["country", "default_rank", "alternative_rank", "default_ceilings", "alternative_ceilings"]].rename(columns={
                    "country": "Country", "default_rank": "Rank (default)", "alternative_rank": "Rank (alternative)",
                    "default_ceilings": "Score (default)", "alternative_ceilings": "Score (alternative)",
                }).round(1),
                hide_index=True,
                use_container_width=True,
            )

    st.divider()
    st.subheader("Model robustness / rank stability")
    st.caption(
        f"Samples {N_ROBUSTNESS_SAMPLES} random-but-valid weight configurations (uniform draws across each "
        "slider's full valid range, fixed seed for reproducibility) and recomputes the ranking each time with "
        "the same `build_composite()` used everywhere in this tracker. This measures how much a country's rank "
        "moves as reasonable analysts might reasonably disagree about weighting -- it is **scenario/rank "
        "stability, not a statistical confidence interval or a claim of significance**."
    )
    if st.button(f"Run robustness analysis ({N_ROBUSTNESS_SAMPLES} samples)"):
        with st.spinner(f"Sampling {N_ROBUSTNESS_SAMPLES} weight configurations..."):
            robustness_df = _robustness_table()
        display_df = robustness_df.rename(columns={
            "country": "Country", "median_rank": "Median Rank", "rank_min": "Best Rank",
            "rank_max": "Worst Rank", "rank_range": "Rank Range", "top3_pct": "Top-3 Frequency",
        }).copy()
        display_df["Robustness"] = robustness_df["rank_range"].apply(lambda r: _robustness_label(r)[0])
        display_df["Top-3 Frequency"] = display_df["Top-3 Frequency"].map(lambda x: f"{x:.0%}")
        st.dataframe(
            display_df[["Country", "Median Rank", "Best Rank", "Worst Rank", "Rank Range", "Top-3 Frequency", "Robustness"]],
            hide_index=True,
            use_container_width=True,
        )
        st.caption(
            f"**Robustness** here means rank-range width across the {N_ROBUSTNESS_SAMPLES} samples: HIGH = rank "
            "moves by at most 2 places, MODERATE = at most 5, LOW = more than 5. A country can have LOW top-3 "
            "frequency and still be HIGH robustness (e.g. a country that consistently ranks last, regardless of "
            "weighting, is exactly as *stable* as one that consistently ranks first) -- the two columns answer "
            "different questions."
        )

    st.divider()
    st.caption(
        "This tool exists to test the methodology's own sensitivity to its weighting choices, not to suggest "
        "any one configuration is more 'correct' than the scored default. See README.md for the rationale "
        "behind the default weights, and the standalone brief for the substantive analysis behind the numbers."
    )

    footer()


if __name__ == "__main__":
    main()
