"""
Methodology -- the full weighting rationale, rubrics, and known limitations,
in-app rather than buried in the GitHub README. Same purpose as the MENASA
Risk Monitor's own Methodology & Data tab.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from constants import CURATED_DIR  # noqa: E402
from scoring import COMPUTE_CEILING_MW, INVESTMENT_CEILING_USD_BN  # noqa: E402
from ui import inject_base_css, footer  # noqa: E402

st.set_page_config(page_title="Methodology | Gulf AI Tracker", page_icon="\U0001F4D0", layout="wide")


def main() -> None:
    inject_base_css()
    st.title("Methodology")
    st.caption(
        "How the Net Alignment Score is built, why it's built that way, and where it's known to be thin. "
        "The full, longer-form version of this page lives in the repository's README.md."
    )

    st.subheader("Two axes, not one score pretending to be simple")
    st.markdown(
        """
A Gulf state maximizing ties with **both** Washington and Beijing at once — the empirically observed
pattern — is hedging, not "confused." A single linear score would collapse that signal. So the index is
built in two layers:

1. **US Integration Depth** (0-100): a weighted average of US export-control access tier, disclosed
   in-country AI investment, and disclosed compute capacity.
2. **China Exposure Depth** (0-100): currently Chinese tech penetration alone — a documented single-factor
   limitation, not an oversight (see below).
3. **Net Alignment Score** (0-100, 50 = neutral), *derived*: `50 + (US Integration Depth − China Exposure Depth) / 2`.
   **50 does not mean "inactive"** — a country maxing out both axes and a country doing little on either
   can both land near 50. Try the **Scenario Explorer** page to see how sensitive this reading is to how
   the two axes are weighted against each other.
        """
    )

    st.divider()
    st.subheader("Factor weights and why")

    weights_df = pd.DataFrame([
        {"Factor": "US export-control access tier", "Axis": "US Integration Depth", "Weight": "40%", "Type": "Ordinal (0-5), curated"},
        {"Factor": "Disclosed AI infrastructure investment", "Axis": "US Integration Depth", "Weight": "30%", "Type": f"Log-scale, ceiling ${INVESTMENT_CEILING_USD_BN}bn"},
        {"Factor": "Disclosed/under-development compute capacity", "Axis": "US Integration Depth", "Weight": "30%", "Type": f"Log-scale, ceiling {COMPUTE_CEILING_MW:,}MW"},
        {"Factor": "Chinese tech penetration", "Axis": "China Exposure Depth", "Weight": "100%", "Type": "Ordinal (0-5), curated"},
        {"Factor": "AI governance maturity", "Axis": "Context only, not scored", "Weight": "—", "Type": "Ordinal (0-5), curated"},
        {"Factor": "Non-oil economic diversification", "Axis": "Context only, not scored", "Weight": "—", "Type": "World Bank, live-refreshed"},
    ])
    st.dataframe(weights_df, hide_index=True, use_container_width=True)

    st.markdown(
        """
**Export-control tier is weighted heaviest (40%)** within US Integration Depth because it's the structural
gatekeeper — a state's formal BIS status determines what capital and hardware commitments are even legally
possible, before either of the other two factors can move. **Investment and compute are weighted equally
(30% each)** because capital committed and physical infrastructure built are distinct facts that don't
always move together — a state can announce big dollar figures well ahead of actual buildout, or vice versa.

**Fixed-ceiling log-scale normalization, not dataset-relative min-max**, for the two dollar/MW factors. With
only 2-3 countries carrying any disclosed investment/compute figure, min-max normalization would stretch a
modest real gap (Saudi Arabia's \\$34.2bn vs. the UAE's \\$15.2bn) into an artificial 100-vs-0 spread,
misrepresenting two countries that are both genuinely substantial. Fixed ceilings keep scores stable as new
deals are disclosed and make "what it would take to score 100" an explicit, documented choice rather than
an artifact of who else happens to be in the dataset this month.

**Governance maturity and non-oil diversification are shown as context, not folded into the score** — a
mature AI regulator or a diversified economy doesn't inherently signal pro-US or pro-China bloc alignment;
they're state-capacity signals, not alignment signals.
        """
    )

    st.divider()
    st.subheader("Ordinal rubrics")
    tab1, tab2 = st.tabs(["US export-control access tier", "Chinese tech penetration"])
    with tab1:
        st.markdown(
            """
| Score | Meaning |
|---|---|
| 0 | Comprehensively restricted / arms-embargoed (Country Group D:5 equivalent) |
| 1 | No bilateral framework; standard case-by-case EAR licensing |
| 2 | Some licensing accommodation, no formal bilateral deal or approved-entity status |
| 3 | Bespoke, entity-specific authorization for a capped chip volume |
| 4 | Formal bilateral AI cooperation framework; license-free access for BIS-approved entities |
| 5 | Full closest-ally treatment; broad license-free access, no entity-specific cap |
            """
        )
    with tab2:
        st.markdown(
            """
| Score | Meaning |
|---|---|
| 0 | No significant Chinese ICT vendor presence |
| 1 | Minimal, isolated non-core relationships |
| 2 | Moderate -- a few Huawei contracts, non-core |
| 3 | Significant -- Huawei is a major/core RAN vendor for at least one major carrier |
| 4 | Deep -- Huawei core RAN across multiple major carriers, plus cloud/enterprise expansion |
| 5 | Extensive -- Huawei is the leading/sole 5G vendor across all major carriers, plus deep economic ties |
            """
        )
    st.caption(
        "These are analyst-desk judgment calls against a documented rubric, not a single clean pulled "
        "number -- disclosed openly rather than disguised as a hard figure. The specific source(s) and a "
        "`confidence` rating behind every country's score are in `data/curated/*.csv`."
    )

    st.divider()
    st.subheader("Missing-data handling")
    st.markdown(
        """
A country missing one of the three US Integration Depth inputs still gets a score — the weighted average
renormalizes over whichever factors are available. A country with **zero** available inputs for an axis
shows `N/A` for that axis and the derived Net Alignment Score, and renders gray on the Overview map rather
than silently defaulting to a floor score. This mirrors how the companion MENASA Risk Monitor handles the
Iran sanctions/missing-data problem.
        """
    )

    st.divider()
    st.subheader("Confidence in the current dataset")

    @st.cache_data(ttl=3600)
    def _confidence_counts() -> pd.DataFrame:
        frames = []
        for name, col in [
            ("Export control tier", "export_control_tier.csv"),
            ("Chinese tech penetration", "chinese_tech_penetration.csv"),
            ("Governance maturity", "governance_maturity.csv"),
        ]:
            df = pd.read_csv(Path(CURATED_DIR) / col)
            counts = df["confidence"].value_counts()
            frames.append(pd.Series(counts, name=name))
        return pd.concat(frames, axis=1).fillna(0).astype(int).reindex(["High", "Medium", "Low"])

    conf_df = _confidence_counts()
    st.dataframe(conf_df, use_container_width=True)
    st.caption(
        "Count of countries at each confidence level, per factor. `Low`-confidence rows are flagged for "
        "follow-up in each CSV's own `rationale` column rather than presented at the same weight as "
        "well-sourced ones -- see README.md's Known Limitations section for exactly which rows and why."
    )

    st.divider()
    st.caption(
        "This is a research/portfolio project, not a commissioned or institutional assessment. Full "
        "methodology, sourcing cadence, and known limitations: README.md. The standalone brief, 'Gulf AI "
        "Ambitions and Geopolitical Risk,' is the region-wide analytical companion to this index."
    )

    footer()


if __name__ == "__main__":
    main()
