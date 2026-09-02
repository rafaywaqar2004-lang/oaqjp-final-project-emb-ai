"""
Policy Event Tracker -- a chronological, sourced feed of chip-policy events
shaping the US-China AI/chip competition. Same spirit as a "live conflicts"
tracker: dated, cited, filterable, not a live feed (see the note in-page).
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from constants import CURATED_DIR, COUNTRIES  # noqa: E402
from ui import inject_base_css, footer, confidence_pill  # noqa: E402


_CATEGORY_COLOR = {
    "Regulatory Framework": "#2454a6",
    "Bilateral Authorization": "#3d7a52",
    "Enforcement Action": "#a93a2e",
    "Legislation": "#8a6416",
}
_CATEGORY_ICON = {
    "Regulatory Framework": "\U0001F4D1",
    "Bilateral Authorization": "\U0001F91D",
    "Enforcement Action": "\U0001F6A8",
    "Legislation": "\U0001F3DB",
}


def esc(text) -> str:
    return "" if text is None or (isinstance(text, float) and pd.isna(text)) else str(text).replace("$", "\\$")


@st.cache_data(ttl=3600)
def load_events() -> pd.DataFrame:
    df = pd.read_csv(Path(CURATED_DIR) / "policy_events.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date", ascending=False)


@st.cache_data(ttl=3600)
def load_tier_scores() -> pd.DataFrame:
    return pd.read_csv(Path(CURATED_DIR) / "export_control_tier.csv")


def _affected_countries(countries_text: str) -> list[str]:
    """Every event in this tracker is chip/export-policy news, so the one
    honest model-component link every event supports is export-control
    tier -- never a fabricated numeric score delta (no historical scores
    exist to compute one from). This just resolves *which* tracked
    countries the free-text `countries` field actually names."""
    text_lower = countries_text.lower()
    if "global" in text_lower or "all 8 tracked" in text_lower or "all 17 tracked" in text_lower:
        return list(COUNTRIES.keys())
    return [c for c in COUNTRIES if c in countries_text]


def _render_model_impact(countries_text: str, tier_df: pd.DataFrame) -> None:
    affected = _affected_countries(countries_text)
    if not affected:
        st.caption("Model impact: qualitative relevance only -- no tracked country named specifically enough to link to a scored factor.")
        return
    st.markdown(
        "**Model impact** &middot; Indicator: *US export-control access* &rarr; Component: "
        "*US Integration Depth (40% weight)*"
    )
    rows = tier_df[tier_df["country"].isin(affected)]
    if len(affected) > 6:
        st.caption(f"Affects export-control-tier scoring for all {len(affected)} tracked countries (current baseline, not this event's isolated effect).")
    else:
        for _, r in rows.iterrows():
            st.markdown(
                f"- {r['country']}: current tier **{r['tier_score']}/5** {confidence_pill(r['confidence'])}",
                unsafe_allow_html=True,
            )
    st.caption(
        "This shows each country's *current* scored tier, not this specific event's isolated numeric effect -- "
        "no historical/pre-event score exists to compute a real delta from, and this project does not invent one."
    )


def main() -> None:
    inject_base_css()
    st.title("Policy Event Tracker")
    st.caption(
        "A chronological, sourced feed of the chip-policy events driving the alignment scores elsewhere in this "
        "tracker -- the regulatory rescission that reopened bilateral dealmaking, the deals that followed, the "
        "enforcement cases testing the diversion risk, and the legislation responding to them."
    )
    st.info(
        "**This is a curated, periodically-updated timeline, not a live feed.** Each event below is individually "
        "dated and sourced -- see the Sources expander on each card. New events are added when a session with "
        "research access reviews the space, not automatically. Last reviewed: September 2026.",
        icon="ℹ️",
    )

    events = load_events()
    tier_df = load_tier_scores()

    categories = sorted(events["category"].unique())
    selected = st.multiselect("Filter by category", options=categories, default=categories)
    filtered = events[events["category"].isin(selected)]

    if filtered.empty:
        st.warning("No events match the selected filters.")
        return

    col_timeline, col_summary = st.columns([3, 1])

    with col_summary:
        st.subheader("By category")
        counts = events["category"].value_counts().reset_index()
        counts.columns = ["category", "count"]
        fig = px.bar(
            counts, x="count", y="category", orientation="h",
            color="category", color_discrete_map=_CATEGORY_COLOR,
        )
        fig.update_layout(showlegend=False, height=260, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"{len(events)} events tracked, {events['date'].min():%b %Y} – {events['date'].max():%b %Y}.")

    with col_timeline:
        st.subheader(f"Timeline ({len(filtered)} of {len(events)} events)")
        for _, row in filtered.iterrows():
            color = _CATEGORY_COLOR.get(row["category"], "#7c8188")
            icon = _CATEGORY_ICON.get(row["category"], "\U0001F4CC")
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"**{row['date']:%d %B %Y}** &nbsp; {icon} <span style='color:{color}; font-weight:600; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.04em;'>{esc(row['category'])}</span>", unsafe_allow_html=True)
                    st.markdown(f"##### {esc(row['title'])}")
                st.write(esc(row["summary"]))
                st.caption(f"**Countries:** {esc(row['countries'])}")
                with st.expander("Model impact & source"):
                    _render_model_impact(row["countries"], tier_df)
                    st.divider()
                    st.markdown(f"**Source:** [{esc(row['source_name'])}]({row['source_url']})")

    st.divider()
    st.caption(
        "This tracker's events are curated for relevance to the Gulf AI & Tech-Bloc Alignment Tracker's own "
        "scored factors -- it is not an exhaustive record of every US-China chip-policy development. See the "
        "standalone brief, 'Gulf AI Ambitions and Geopolitical Risk,' for analysis connecting these events to "
        "the composite scores, and `data/curated/policy_events.csv` for the full sourced record."
    )

    footer()


if __name__ == "__main__":
    main()
