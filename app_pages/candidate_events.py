"""
Candidate Events -- a research-assist review queue, NOT a live feed. Two
official, free, public sources (the Federal Register API for BIS
documents, and OFAC's Recent Actions page) are polled on a schedule by
src/data_pipeline/fetch_candidate_events.py and written to
data/candidate_events/candidates.csv. Nothing from either source is ever
added to this tracker's own data automatically -- every candidate sits
here until a human reviews it and either dismisses it or confirms it via
the pre-filled form below, which appends a properly-categorized row to
data/curated/policy_events.csv exactly the way every other event in this
project was added. This keeps the project's standing rule intact: a fact
becomes part of the tracker only once a person has actually read the
source and decided it belongs, never because an API returned it.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from candidate_review import load_candidates, load_review_log, pending_candidates, record_review  # noqa: E402
from constants import CURATED_DIR, COUNTRIES  # noqa: E402
from ui import inject_base_css, page_header, kpi_card, kpi_row, footer, GRAY  # noqa: E402

POLICY_EVENTS_PATH = Path(CURATED_DIR) / "policy_events.csv"
CATEGORIES = ["Regulatory Framework", "Bilateral Authorization", "Enforcement Action", "Legislation"]
DIRECTIONS = ["Tightening", "Loosening"]


def esc(text) -> str:
    return "" if text is None or (isinstance(text, float) and pd.isna(text)) else str(text).replace("$", "\\$")


@st.cache_data(ttl=3600)
def _candidates() -> pd.DataFrame:
    return load_candidates()


def _review_log() -> pd.DataFrame:
    # Not cached: must reflect this session's own just-recorded decisions
    # immediately, or a reviewed candidate would reappear until the cache
    # (and every other cached call on the page) expired.
    return load_review_log()


def _add_to_policy_events_form(candidate: pd.Series) -> None:
    with st.form(f"add_form_{candidate['source']}_{candidate['external_id']}"):
        st.caption(
            "Writes directly to data/curated/policy_events.csv on this running server. On most hosted "
            "deployments (e.g. Render) the filesystem is ephemeral -- a redeploy or restart will discard "
            "this change unless it's also committed to the repository. Review every field before submitting; "
            "nothing here has been fact-checked beyond what the source itself says."
        )
        date = st.text_input("Date (YYYY-MM-DD)", value=candidate["date"])
        title = st.text_input("Title", value=candidate["title"])
        category = st.selectbox("Category", options=CATEGORIES)
        direction = st.selectbox("Direction", options=DIRECTIONS)
        countries = st.text_input(
            "Countries", value=candidate["matched_countries"] or "",
            help="This project's canonical country names, semicolon-separated, or a broader description "
                 "like 'Global (incl. all 17 tracked countries)' if the rule isn't country-specific.",
        )
        summary = st.text_area("Summary", value=candidate["summary"] or "")
        source_name = st.text_input("Source name", value=candidate["source"])
        source_url = st.text_input("Source URL", value=candidate["url"])
        submitted = st.form_submit_button("Add to Policy Events")
        if submitted:
            if not date or not title:
                st.error("Date and title are required.")
                return
            raw = pd.read_csv(POLICY_EVENTS_PATH)
            new_row = pd.DataFrame([{
                "date": date, "title": title, "category": category, "direction": direction,
                "countries": countries, "summary": summary, "source_name": source_name, "source_url": source_url,
            }])
            updated = pd.concat([raw, new_row], ignore_index=True)
            try:
                updated.to_csv(POLICY_EVENTS_PATH, index=False)
                record_review(candidate["source"], candidate["external_id"], "confirmed")
                st.cache_data.clear()
                st.success(f"Added to Policy Events. Reload the page to see it reflected on the Policy Events tab.")
            except OSError as e:
                st.error(f"Could not write to {POLICY_EVENTS_PATH}: {e}")


def _candidate_card(candidate: pd.Series) -> None:
    with st.container(border=True):
        st.markdown(f"**{esc(candidate['date'])}** &middot; {esc(candidate['source'])}")
        st.markdown(f"##### {esc(candidate['title'])}")
        if candidate["summary"]:
            st.caption(esc(candidate["summary"]))
        if candidate["matched_countries"]:
            st.caption(f"Matches tracked countries: **{esc(candidate['matched_countries'])}**")
        st.markdown(f"[View source]({candidate['url']})")

        c1, c2 = st.columns([1, 3])
        with c1:
            if st.button("Not relevant", key=f"reject_{candidate['source']}_{candidate['external_id']}"):
                record_review(candidate["source"], candidate["external_id"], "rejected")
                st.rerun()
        with c2:
            with st.expander("Add to Policy Events..."):
                _add_to_policy_events_form(candidate)


def main() -> None:
    inject_base_css()
    page_header(
        "Candidate Events",
        "A research-assist review queue for new BIS/OFAC actions -- not a live feed. See disclaimer below.",
        meta=["ADMIN", "REVIEW REQUIRED BEFORE ANYTHING IS ADDED"],
    )

    st.warning(
        "**This is a candidate queue, not a live feed.** Two official sources (the Federal Register API for "
        "BIS documents, OFAC's Recent Actions page) are polled on a schedule and listed below. Nothing here "
        "is part of this tracker's data until a human reviews it and submits the form on a specific candidate "
        "-- an item appearing here is not itself a verified fact, only a lead worth checking."
    )

    candidates = _candidates()
    if candidates.empty:
        st.info(
            "No candidates on file yet. Run `python src/data_pipeline/fetch_candidate_events.py` (or wait for "
            "its scheduled GitHub Actions run) to populate this queue."
        )
        footer()
        return

    log = _review_log()
    pending = pending_candidates(candidates, log)

    n_confirmed = int((log["status"] == "confirmed").sum()) if not log.empty else 0
    n_rejected = int((log["status"] == "rejected").sum()) if not log.empty else 0
    kpi_row([
        kpi_card("Pending Review", str(len(pending)), f"of {len(candidates)} fetched"),
        kpi_card("Confirmed", str(n_confirmed), "added to Policy Events"),
        kpi_card("Dismissed", str(n_rejected), "marked not relevant"),
    ])

    st.divider()

    if pending.empty:
        st.success("No pending candidates -- every fetched item has been reviewed.")
        footer()
        return

    source_options = sorted(pending["source"].unique())
    selected_sources = st.multiselect("Filter by source", options=source_options, default=source_options)
    only_matched = st.checkbox("Only show candidates matching a tracked country", value=False)

    filtered = pending[pending["source"].isin(selected_sources)]
    if only_matched:
        filtered = filtered[filtered["matched_countries"] != ""]

    st.caption(f"Showing {len(filtered)} of {len(pending)} pending candidates.")
    for _, candidate in filtered.iterrows():
        _candidate_card(candidate)

    footer()


if __name__ == "__main__":
    main()
