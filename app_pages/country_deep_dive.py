"""
Country Deep Dive -- an intelligence-profile page per country: current
position, key judgments, the factor-level drivers behind the two composite
axes, trend (where real dated history exists), recent policy developments,
qualified strategic implications, forward-looking indicators to watch, and
a data-quality summary -- plus the auto-generated BLUF brief and a
downloadable PDF version. Every number and sentence here is templated from
a cited row in data/curated/*.csv or a value in the composite score, never
free-form generation.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from constants import COUNTRIES, CURATED_DIR  # noqa: E402
from country_brief import _alignment_band, generate_brief, load_curated  # noqa: E402
from momentum import compute_momentum, load_history  # noqa: E402
from pdf_export import build_country_pdf  # noqa: E402
from policy_events import _affected_countries  # noqa: E402
from scoring import build_composite  # noqa: E402
from watch_next import load_watch_indicators, watch_items_for  # noqa: E402
from ui import (  # noqa: E402
    inject_base_css, page_header, confidence_pill, momentum_badge, watch_item, watch_next, footer,
    BLUE, RED, GRAY,
)


def esc(text) -> str:
    """Escape literal '$' so Streamlit's markdown renderer doesn't treat a
    pair of dollar amounts (e.g. "$34.2bn ... $23.0bn") as a LaTeX math span."""
    return "" if text is None or (isinstance(text, float) and pd.isna(text)) else str(text).replace("$", "\\$")


@st.cache_data(ttl=3600)
def _composite() -> pd.DataFrame:
    return build_composite()


@st.cache_data(ttl=3600)
def _curated() -> dict[str, pd.DataFrame]:
    return load_curated()


@st.cache_data(ttl=3600)
def _brief(country: str):
    return generate_brief(country, curated=_curated(), composite=_composite())


@st.cache_data(ttl=3600)
def _policy_events() -> pd.DataFrame:
    df = pd.read_csv(Path(CURATED_DIR) / "policy_events.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date", ascending=False)


# Component -> (raw column, scored column, axis, weight label)
US_DRIVERS = [
    ("US Export-Control Tier", "us_tier_raw", "us_tier_score_100", "40%"),
    ("AI Investment", "investment_usd_bn", "investment_score_100", "30%"),
    ("Compute Capacity", "compute_mw", "compute_score_100", "30%"),
]
CHINA_DRIVERS = [
    ("Chinese Telecom Penetration", "china_penetration_raw", "china_penetration_score_100", "50%"),
    ("Chinese AI/Cloud/Digital Ties", "china_digital_raw", "china_digital_score_100", "50%"),
]


# Same High/Medium/Low -> High/Moderate/Low mapping country_brief.py uses for
# every other confidence label in this app (its confidence_pill badges
# included) -- kept here as a short label ("Moderate", not "Moderate
# confidence") for compact table/summary display, but never a different
# *classification* of the same underlying curated value.
_CONFIDENCE_SHORT_MAP = {"High": "High", "Medium": "Moderate", "Low": "Low"}


def _driver_confidence(curated: dict[str, pd.DataFrame], key: str, country: str) -> str:
    df = curated[key]
    row = df[df["country"] == country]
    if row.empty:
        return "Insufficient"
    raw = str(row.iloc[0]["confidence"]).strip()
    return _CONFIDENCE_SHORT_MAP.get(raw, raw)


def _key_drivers_table(row: pd.Series, curated: dict[str, pd.DataFrame], country: str) -> pd.DataFrame:
    conf_lookup = {
        "us_tier_raw": _driver_confidence(curated, "tier", country),
        "china_penetration_raw": _driver_confidence(curated, "china", country),
        "china_digital_raw": _driver_confidence(curated, "china_digital", country),
    }
    records = []
    for axis, drivers in (("US Integration Depth", US_DRIVERS), ("China Exposure Depth", CHINA_DRIVERS)):
        for label, raw_col, scored_col, weight in drivers:
            raw_val = row[raw_col]
            scored_val = row[scored_col]
            if raw_col in conf_lookup:
                confidence = conf_lookup[raw_col]
            else:
                confidence = "Moderate" if pd.notna(scored_val) else "Data gap"
            records.append({
                "Axis": axis,
                "Component": label,
                "Raw Value": "N/A" if pd.isna(raw_val) else (f"{raw_val:.1f}" if raw_col in ("investment_usd_bn", "compute_mw") else f"{raw_val:.0f}/5"),
                "Scored (0-100)": "N/A" if pd.isna(scored_val) else f"{scored_val:.0f}",
                "Weight": weight,
                "Confidence": confidence,
            })
    return pd.DataFrame(records)


def _strategic_implications(row: pd.Series) -> dict[str, str]:
    """Templated implications, keyed off the country's actual scored
    position -- never a generic sentence repeated for every country, and
    never a BUY/SELL-style recommendation. Distinct branches for the four
    quadrants plus the insufficient-data case."""
    us = row["us_integration_depth"]
    china = row["china_exposure_depth"]
    tier = row["us_tier_raw"]
    country = row["country"]

    if pd.isna(us) or pd.isna(china):
        note = f"{country} has insufficient disclosed data on one or both axes to support a differentiated strategic read."
        return {"policymakers": note, "investors": note, "corporates": note}

    band = _alignment_band(row["net_alignment_score"])

    if pd.notna(tier) and tier >= 3:
        policymakers = (
            f"{country} holds a disclosed bilateral US chip-access arrangement (tier {tier:.0f}/5) -- any further "
            "authorization or restriction decision here has a directly measurable effect on this tracker's "
            "US Integration Depth score, not just a qualitative one."
        )
    else:
        policymakers = (
            f"{country} has no disclosed bilateral US chip-access framework (tier {tier:.0f}/5)" if pd.notna(tier) else
            f"{country} has no scored US export-control tier on record"
        ) + " -- a first authorization here would be a first-order, immediately scoreable policy event under this tracker's own methodology."

    if us >= 50 and china >= 50:
        investors = (
            f"{country}'s position ({band}) reflects material technology ties to both the US and Chinese "
            "ecosystems simultaneously -- greater diversification of technology-supply exposure than a "
            "single-bloc-aligned peer, but also dual exposure to either side's future export-control or "
            "sanctions decisions."
        )
    elif us >= china:
        investors = (
            f"{country}'s greater relative dependence on US-controlled advanced-chip access ({band}) may increase "
            "exposure to future US export-control policy changes specifically, relative to a more diversified peer."
        )
    else:
        investors = (
            f"{country}'s greater relative Chinese telecom/digital-infrastructure exposure ({band}) carries "
            "transmission-channel risk from future US secondary-sanctions or entity-list actions targeting "
            "Chinese technology vendors operating in-country."
        )

    china_penetration = row["china_penetration_raw"]
    if pd.notna(china_penetration) and china_penetration >= 3:
        corporates = (
            f"Corporates with in-country supply chains should note {country}'s scored Chinese telecom-vendor "
            f"penetration ({china_penetration:.0f}/5) -- interoperability and vendor-lock-in considerations apply "
            "when integrating US-origin AI infrastructure alongside an existing Chinese-vendor telecom backbone."
        )
    else:
        corporates = (
            f"{country}'s scored Chinese telecom-vendor penetration is low or undisclosed "
            f"({'N/A' if pd.isna(china_penetration) else f'{china_penetration:.0f}/5'}) -- available public data does not "
            "indicate a significant Chinese-vendor lock-in consideration for corporates integrating US-origin AI infrastructure here."
        )

    return {"policymakers": policymakers, "investors": investors, "corporates": corporates}


def _data_quality_summary(row: pd.Series, curated: dict[str, pd.DataFrame], country: str) -> pd.DataFrame:
    confidences = [
        _driver_confidence(curated, "tier", country),
        _driver_confidence(curated, "china", country),
        _driver_confidence(curated, "china_digital", country),
        _driver_confidence(curated, "governance", country),
    ]
    n_available = int(row["us_integration_factors_available"]) + int(row["china_exposure_factors_available"])
    return pd.DataFrame([
        {"Dimension": "Factor coverage", "Value": f"{n_available} of 5 scored factors available (3 US Integration + 2 China Exposure)"},
        {"Dimension": "Confidence distribution", "Value": ", ".join(confidences)},
        {"Dimension": "Investment/compute deals on file", "Value": f"{len(curated['investment'][curated['investment']['country'] == country])} investment, {len(curated['compute'][curated['compute']['country'] == country])} compute record(s)"},
        {"Dimension": "Data as of", "Value": "September 2026"},
    ])


def main() -> None:
    inject_base_css()

    country = st.selectbox("Country", options=list(COUNTRIES.keys()))
    curated = _curated()
    composite = _composite()
    brief = _brief(country)
    row = composite[composite["country"] == country].iloc[0]

    band = _alignment_band(row["net_alignment_score"])
    overall_confidences = [
        _driver_confidence(curated, "tier", country), _driver_confidence(curated, "china", country),
        _driver_confidence(curated, "china_digital", country),
    ]
    page_confidence = "High" if all(c == "High" for c in overall_confidences) else (
        "Low" if any(c in ("Low", "Insufficient") for c in overall_confidences) else "Moderate"
    )

    page_header(
        f"{country}: Country Intelligence",
        "Auto-generated from this tracker's own cited data -- every sentence traceable to a specific sourced row.",
        meta=["DATA AS OF: SEPTEMBER 2026", f"CONFIDENCE: {page_confidence.upper()}"],
    )

    st.subheader("Current Position")
    m1, m2, m3 = st.columns(3)
    m1.metric("Net Alignment Score", f"{row['net_alignment_score']:.0f}" if pd.notna(row["net_alignment_score"]) else "N/A")
    m2.metric("US Integration Depth", f"{row['us_integration_depth']:.0f}" if pd.notna(row["us_integration_depth"]) else "N/A")
    m3.metric("China Exposure Depth", f"{row['china_exposure_depth']:.0f}" if pd.notna(row["china_exposure_depth"]) else "N/A")
    st.caption(f"Positioning: **{band}**. See the Regional Dashboard's US-China positioning chart for this country plotted against all others.")

    st.divider()
    st.subheader("Bottom Line Up Front")
    st.info(esc(brief.bluf))

    st.subheader("Key Judgments")
    for i, j in enumerate(brief.key_judgments, start=1):
        with st.container(border=True):
            st.markdown(f"**{i:02d}** &nbsp; {confidence_pill(j.confidence)}", unsafe_allow_html=True)
            st.write(esc(j.text))

    st.divider()
    st.subheader("Key Drivers")
    st.caption("The factor-level components underlying US Integration Depth and China Exposure Depth for this country.")
    st.dataframe(_key_drivers_table(row, curated, country), hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Trend")
    history = load_history()
    for metric_col, metric_label in (
        ("net_alignment_score", "Net Alignment"), ("us_integration_depth", "US Integration Depth"), ("china_exposure_depth", "China Exposure Depth"),
    ):
        m = compute_momentum(history, country, metric_col)
        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown(f"**{metric_label}**")
        with c2:
            if m.direction == "Insufficient data":
                st.markdown(f"{momentum_badge(m.direction)} &nbsp; {m.note}", unsafe_allow_html=True)
            else:
                st.markdown(
                    f"{momentum_badge(m.direction)} &nbsp; {m.previous:.0f} &rarr; {m.current:.0f} ({m.change:+.1f}) &middot; {m.note}",
                    unsafe_allow_html=True,
                )

    country_history = history[history["country"] == country].sort_values("snapshot_date")
    if len(country_history) >= 2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=country_history["snapshot_date"], y=country_history["us_integration_depth"],
            name="US Integration Depth", mode="lines+markers", line=dict(color=BLUE, width=2),
        ))
        fig.add_trace(go.Scatter(
            x=country_history["snapshot_date"], y=country_history["china_exposure_depth"],
            name="China Exposure Depth", mode="lines+markers", line=dict(color=RED, width=2),
        ))
        fig.add_trace(go.Scatter(
            x=country_history["snapshot_date"], y=country_history["net_alignment_score"],
            name="Net Alignment", mode="lines+markers", line=dict(color=GRAY, width=2, dash="dot"),
        ))
        fig.update_layout(
            height=320, margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(title="Score (0-100)", range=[0, 100]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)
        has_backfilled = "source" in country_history.columns and (country_history["source"] == "backfilled").any()
        if has_backfilled:
            st.caption(
                "Dates before the most recent snapshot are a **reconstruction**, not point-in-time historical "
                "measurements: investment/compute figures are real deals filtered by their own disclosed "
                "announcement date, and Saudi Arabia's/the UAE's export-control tier reflects two documented "
                "step-changes (see Methodology). Chinese-tie and governance factors are held at today's curated "
                "values across all historical dates because no dated evidence of when they changed exists in "
                "this project's sourcing -- so pre-2026 China Exposure Depth may understate how gradually those "
                "ties actually built up. See the Sources & Data page for full provenance."
            )

    st.divider()
    st.subheader("What Changed")
    events = _policy_events()
    country_events = events[events["countries"].apply(lambda c: country in _affected_countries(c))]
    if country_events.empty:
        st.caption(f"No policy events in the tracker's curated feed are specifically linked to {country}. See the full Policy Event Tracker for region-wide/global events.")
    else:
        for _, ev in country_events.head(5).iterrows():
            with st.container(border=True):
                st.markdown(f"**{ev['date']:%d %B %Y}** &mdash; {esc(ev['title'])}")
                st.caption(esc(ev["summary"]))
                st.caption(f"[{esc(ev['source_name'])}]({ev['source_url']})")
        st.caption("See the full **Policy Event Tracker** page for the complete feed, filters, and model-impact links.")

    st.divider()
    st.subheader("Strategic Implications")
    implications = _strategic_implications(row)
    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        st.markdown("**Policymakers**")
        st.caption(implications["policymakers"])
    with ic2:
        st.markdown("**Investors**")
        st.caption(implications["investors"])
    with ic3:
        st.markdown("**Corporates**")
        st.caption(implications["corporates"])
    st.caption("Qualified analytical framing, not a recommendation to buy, sell, or adopt any specific position.")

    st.divider()
    st.subheader("What to Watch")
    watch_df = watch_items_for(load_watch_indicators(), country=country)
    if watch_df.empty:
        st.caption("No specific leading indicators on file for this country beyond the regional items on the Overview page.")
    else:
        watch_next([
            watch_item(r["indicator"], r["why_it_matters"], r["current_signal"], r["direction"], r["confidence"])
            for _, r in watch_df.iterrows()
        ])

    st.divider()
    col_inv, col_compute = st.columns(2)

    inv = curated["investment"][curated["investment"]["country"] == country].sort_values("announced_date")
    compute = curated["compute"][curated["compute"]["country"] == country].sort_values("announced_date")

    with col_inv:
        st.subheader("Investment timeline")
        if inv.empty:
            st.caption("No investment records on file for this country.")
        for _, r in inv.iterrows():
            counted = "✅ counted in score" if r["counted_in_score"] else "context only, not scored"
            amount = f"${r['amount_usd_bn']:.1f}bn" if pd.notna(r["amount_usd_bn"]) else "amount undisclosed"
            with st.container(border=True):
                st.markdown(f"**{r['announced_date']}** &mdash; {esc(r['deal_name'])}")
                st.caption(f"{esc(amount)} &middot; {r['deal_type']} &middot; {counted}")
                st.caption(esc(r["notes"]))

    with col_compute:
        st.subheader("Compute / data-center timeline")
        if compute.empty:
            st.caption("No compute-capacity records on file for this country.")
        for _, r in compute.iterrows():
            counted = "✅ counted in score" if r["counted_in_score"] else "context only, not scored"
            capacity = f"{r['capacity_mw']:.0f}MW" if pd.notna(r["capacity_mw"]) else "capacity undisclosed"
            with st.container(border=True):
                st.markdown(f"**{r['announced_date']}** &mdash; {esc(r['project_name'])}")
                st.caption(f"{esc(capacity)} &middot; {r['status']} &middot; {counted}")
                st.caption(esc(r["notes"]))

    st.divider()
    st.subheader("Data Quality")
    data_quality_df = _data_quality_summary(row, curated, country)
    st.dataframe(data_quality_df, hide_index=True, use_container_width=True)
    st.caption(
        "Confidence labels are pulled directly from each curated row's own `confidence` column -- never a "
        "separately invented composite score. 'Insufficient' means no sourced row exists for that factor at all."
    )

    st.divider()
    st.subheader("Sources")
    for src in brief.sources:
        st.caption(f"**{src['topic']}** &mdash; {src['name']} ({src['date']})" + (f" &mdash; {src['url']}" if src["url"] else ""))

    st.caption(
        "This is a research/portfolio product, not a commissioned or institutional assessment. "
        "See the tracker's README for full methodology and the standalone brief for the region-wide analysis."
    )

    pdf_bytes = build_country_pdf(
        brief,
        current_position={
            "Net Alignment Score": f"{row['net_alignment_score']:.0f}/100" if pd.notna(row["net_alignment_score"]) else "N/A",
            "US Integration Depth": f"{row['us_integration_depth']:.0f}/100" if pd.notna(row["us_integration_depth"]) else "N/A",
            "China Exposure Depth": f"{row['china_exposure_depth']:.0f}/100" if pd.notna(row["china_exposure_depth"]) else "N/A",
            "Positioning": band,
        },
        key_drivers=_key_drivers_table(row, curated, country),
        what_changed=[{"date": f"{ev['date']:%Y-%m-%d}", "title": ev["title"]} for _, ev in country_events.head(5).iterrows()],
        strategic_implications=implications,
        watch_items=watch_df,
        data_quality=data_quality_df,
    )
    st.download_button(
        "\U0001F4C4 Download full country brief (PDF)",
        data=pdf_bytes,
        file_name=f"{country.replace(' ', '_').lower()}_ai_alignment_brief.pdf",
        mime="application/pdf",
    )

    footer()


if __name__ == "__main__":
    main()
