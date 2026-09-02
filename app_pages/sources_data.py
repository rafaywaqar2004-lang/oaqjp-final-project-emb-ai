"""
Sources & Data -- a research data catalog: every dataset this tracker
uses, its source type, country coverage, observation count, update
cadence, missingness, methodology note, and known limitations, computed
live from the actual files rather than hard-coded. Each curated file is
also downloadable directly from this page.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from data_catalog import build_catalog  # noqa: E402
from ui import inject_base_css, page_header, footer  # noqa: E402


def main() -> None:
    inject_base_css()
    page_header(
        "Sources & Data",
        "A research data catalog -- every dataset behind this tracker, computed live from the actual files.",
        meta=["DATA AS OF: SEPTEMBER 2026"],
    )

    st.caption(
        "This page exists so a reader (or a hiring manager) can verify this tracker's own claims about its "
        "data without trusting a paragraph of prose -- coverage, observation counts, and missingness below "
        "are computed directly from the files at page-load time, not typed in by hand."
    )

    catalog = build_catalog()

    st.subheader("Curated & computed datasets")
    display_cols = ["Dataset", "Source type", "Countries covered", "Observations", "Update cadence", "Missingness"]
    st.dataframe(catalog[display_cols], hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Methodology & limitations, per dataset")
    for _, row in catalog.iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{row['Dataset']}**")
                st.caption(f"Methodology: {row['Methodology']}")
                st.caption(f"Limitations: {row['Limitations']}")
            with c2:
                st.caption(f"{row['Countries covered']} &middot; {row['Observations']} observations", unsafe_allow_html=True)
                path = Path(row["_path"])
                if path.exists() and path.suffix == ".csv":
                    with open(path, "rb") as f:
                        st.download_button(
                            "Download CSV", data=f.read(), file_name=path.name, mime="text/csv",
                            key=f"dl_{row['Dataset']}",
                        )

    st.divider()
    st.caption(
        "**Manually curated** means a specific analyst-desk research pass, cited row by row (source_name, "
        "source_url, confidence, as_of_date, rationale) -- see the Methodology page for the ordinal rubrics "
        "used to score curated factors, and README.md for the full sourcing and refresh-cadence policy. "
        "**Live, automated** means a scheduled pipeline with zero manual editing between fetch and use."
    )

    footer()


if __name__ == "__main__":
    main()
