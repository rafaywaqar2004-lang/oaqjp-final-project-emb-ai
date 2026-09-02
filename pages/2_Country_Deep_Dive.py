"""
Country Deep Dive -- an auto-generated analyst-style brief per country
(BLUF + key judgments, exactly like the standalone Gulf-wide brief, but
templated from the live dataset for any tracked country) plus an
investment/compute timeline and a downloadable PDF version.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from constants import COUNTRIES  # noqa: E402
from country_brief import generate_brief, load_curated  # noqa: E402
from pdf_export import build_country_pdf  # noqa: E402
from scoring import build_composite  # noqa: E402
from ui import inject_base_css, confidence_pill, footer  # noqa: E402

st.set_page_config(page_title="Country Deep Dive | Gulf AI Tracker", page_icon="assets/favicon.png", layout="wide")


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


def main() -> None:
    inject_base_css()
    st.title("Country Deep Dive")
    st.caption(
        "An auto-generated analyst brief per country -- every sentence is templated from a cited row in "
        "data/curated/*.csv, not free-form generation. Same BLUF/key-judgment format as the standalone "
        "Gulf-wide brief, applied per country and kept in sync with the live dataset."
    )

    country = st.selectbox("Country", options=list(COUNTRIES.keys()))
    brief = _brief(country)
    row = _composite()[_composite()["country"] == country].iloc[0]

    m1, m2, m3 = st.columns(3)
    m1.metric("Net Alignment Score", f"{row['net_alignment_score']:.0f}" if pd.notna(row["net_alignment_score"]) else "N/A")
    m2.metric("US Integration Depth", f"{row['us_integration_depth']:.0f}" if pd.notna(row["us_integration_depth"]) else "N/A")
    m3.metric("China Exposure Depth", f"{row['china_exposure_depth']:.0f}" if pd.notna(row["china_exposure_depth"]) else "N/A")

    pdf_bytes = build_country_pdf(brief)
    st.download_button(
        "\U0001F4C4 Download country brief (PDF)",
        data=pdf_bytes,
        file_name=f"{country.replace(' ', '_').lower()}_ai_alignment_brief.pdf",
        mime="application/pdf",
    )

    st.divider()
    st.subheader("Bottom Line Up Front")
    st.info(esc(brief.bluf))

    st.subheader("Key Judgments")
    for i, j in enumerate(brief.key_judgments, start=1):
        with st.container(border=True):
            st.markdown(f"**{i:02d}** &nbsp; {confidence_pill(j.confidence)}", unsafe_allow_html=True)
            st.write(esc(j.text))

    st.divider()
    col_inv, col_compute = st.columns(2)

    curated = _curated()
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
    st.subheader("Sources")
    for src in brief.sources:
        st.caption(f"**{src['topic']}** &mdash; {src['name']} ({src['date']})" + (f" &mdash; {src['url']}" if src["url"] else ""))

    st.caption(
        "This is a research/portfolio product, not a commissioned or institutional assessment. "
        "See the tracker's README for full methodology and the standalone brief for the region-wide analysis."
    )

    footer()


if __name__ == "__main__":
    main()
