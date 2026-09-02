"""
Sources & Data catalog -- one row per dataset this tracker uses, with
coverage/observation counts computed live from the actual files (never
hard-coded), alongside static methodology/limitation notes. Backs the
Sources & Data page (Section 22 of the "9+/10 credibility upgrade" brief).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from constants import COUNTRIES, CURATED_DIR, COMPUTED_DIR, WORLDBANK_DIR


@dataclass
class DatasetEntry:
    name: str
    path: Path
    source_type: str
    update_cadence: str
    methodology_note: str
    limitations: str
    country_col: str | None = "country"


_REGISTRY: list[DatasetEntry] = [
    DatasetEntry(
        name="Composite Scores",
        path=Path(COMPUTED_DIR) / "composite_scores.csv",
        source_type="Computed (from the curated datasets below)",
        update_cadence="Regenerated on every `python src/scoring.py` run",
        methodology_note="See the Methodology page for the full weighting formula.",
        limitations="Only as current as the curated inputs it's built from -- see each factor's own dataset below.",
    ),
    DatasetEntry(
        name="Composite Score History",
        path=Path(COMPUTED_DIR) / "composite_scores_history.csv",
        source_type="Computed, append-only (one dated snapshot per refresh)",
        update_cadence="One row set appended per calendar day a refresh runs (same-day re-runs replace, not duplicate)",
        methodology_note="Backs Score Momentum (src/momentum.py) -- see the Trend section on any Country Deep Dive.",
        limitations="Only 1 dated snapshot exists as of this catalog -- too few observations for any trend to be computable yet. This is expected, not a data-quality gap: history only started accumulating recently.",
    ),
    DatasetEntry(
        name="US Export-Control Tier",
        path=Path(CURATED_DIR) / "export_control_tier.csv",
        source_type="Manually curated",
        update_cadence="Ad hoc, as bilateral chip-access deals or BIS regulatory changes are disclosed",
        methodology_note="0-5 ordinal rubric -- see Methodology page. Feeds US Integration Depth at 40% weight.",
        limitations="Qatar, Bahrain, Kuwait, Oman, and Turkey remain Low confidence pending direct access to BIS's own Country Group table (blocked in this project's research sandbox).",
    ),
    DatasetEntry(
        name="Chinese Telecom Penetration",
        path=Path(CURATED_DIR) / "chinese_tech_penetration.csv",
        source_type="Manually curated",
        update_cadence="Ad hoc, as telecom vendor deals are disclosed",
        methodology_note="0-5 ordinal rubric -- see Methodology page. Feeds China Exposure Depth at 50% weight.",
        limitations="Chiefly Huawei/ZTE RAN and 5G vendor relationships -- does not capture every category of Chinese telecom engagement.",
    ),
    DatasetEntry(
        name="Chinese AI/Cloud/Digital Ties",
        path=Path(CURATED_DIR) / "chinese_digital_ties.csv",
        source_type="Manually curated",
        update_cadence="Ad hoc, as cloud/AI-model/financing deals are disclosed",
        methodology_note="0-5 ordinal rubric -- see Methodology page. Feeds China Exposure Depth at 50% weight.",
        limitations="Newer, thinner research pass than the telecom factor -- 3 of 17 rows are Low confidence, resting on a single MOU or marketing announcement rather than an audited deployment figure.",
    ),
    DatasetEntry(
        name="AI Governance Maturity",
        path=Path(CURATED_DIR) / "governance_maturity.csv",
        source_type="Manually curated",
        update_cadence="Ad hoc, as national AI strategies/regulators are established",
        methodology_note="0-5 ordinal rubric -- see Methodology page. Shown as context; not folded into Net Alignment.",
        limitations="A state-capacity signal, not an alignment signal -- a mature regulator doesn't imply pro-US or pro-China positioning.",
    ),
    DatasetEntry(
        name="AI Investment Deals",
        path=Path(CURATED_DIR) / "ai_investment_deals.csv",
        source_type="Manually curated, long-format (one row per deal)",
        update_cadence="Ad hoc, as deals are announced",
        methodology_note="Only deals with `counted_in_score = TRUE` (a specific, dated, disclosed dollar figure) feed the composite score; headline/aspirational figures are recorded but excluded.",
        limitations="An undercount by design -- only deals meeting this project's sourcing bar are counted. 9 of 17 countries show no disclosed figure at this level of specificity.",
    ),
    DatasetEntry(
        name="Compute Capacity Deals",
        path=Path(CURATED_DIR) / "compute_capacity_deals.csv",
        source_type="Manually curated, long-format (one row per project)",
        update_cadence="Ad hoc, as data-center/compute projects are announced",
        methodology_note="Only `counted_in_score = TRUE` current/under-development capacity feeds the score; long-run targets are shown for context only.",
        limitations="Same undercount-by-design limitation as AI Investment Deals.",
    ),
    DatasetEntry(
        name="Policy Events",
        path=Path(CURATED_DIR) / "policy_events.csv",
        source_type="Manually curated",
        update_cadence="Ad hoc, as a session with research access reviews the space (not a live feed)",
        methodology_note="Each event links to the scored factor it affects (Model impact & source) and carries a Loosening/Tightening direction classification.",
        limitations="Curated for relevance to this tracker's own scored factors -- not an exhaustive record of every US-China chip-policy development.",
        country_col=None,
    ),
    DatasetEntry(
        name="Watch Next Indicators",
        path=Path(CURATED_DIR) / "watch_indicators.csv",
        source_type="Manually curated",
        update_cadence="Ad hoc, alongside the curated datasets each indicator references",
        methodology_note="Each indicator is derived from an already-cited pending/target/unresolved item elsewhere in the curated data -- see each row's source_ref.",
        limitations="A curated sample of the most consequential pending items, not an exhaustive list.",
        country_col=None,
    ),
    DatasetEntry(
        name="Major Cities (map layer)",
        path=Path(CURATED_DIR) / "major_cities.csv",
        source_type="Manually curated (standard geographic reference, not an analytical claim)",
        update_cadence="Static -- one reference city per country",
        methodology_note="Shown on the Regional Dashboard map for geographic orientation only.",
        limitations="Framed as 'major city,' never 'capital,' to sidestep disputed political-status questions (see each row's own notes).",
    ),
    DatasetEntry(
        name="AI/Compute Hubs (map layer)",
        path=Path(CURATED_DIR) / "ai_hubs.csv",
        source_type="Manually curated",
        update_cadence="Ad hoc, alongside the investment/compute/digital-ties datasets these sites are drawn from",
        methodology_note="A hub only appears if its site is explicitly named in an already-cited deal elsewhere in the curated data.",
        limitations="Only 9 sites across 6 countries meet this bar -- not an exhaustive map of regional AI infrastructure.",
    ),
    DatasetEntry(
        name="Non-Oil Diversification (manual research)",
        path=Path(CURATED_DIR) / "non_oil_diversification.csv",
        source_type="Manually curated (IMF/national-statistics sourced, one-time research pass)",
        update_cadence="Ad hoc -- built specifically to supply real data for the Economic Analysis page while the live World Bank pipeline below is unpopulated in this sandbox",
        methodology_note="Real non-oil GDP share figures for the 8 countries where the concept applies and a source could be found; the other 9 are marked structurally not-applicable (not hydrocarbon-rent economies), never estimated. See the Economic Analysis page's supplementary finding.",
        limitations="Only 8 of 17 countries have a usable figure. Confidence varies per row (High for a named national-statistics release, Medium for a press-relayed figure, Low for Iran's dated 2021 secondary-sourced figure) -- see each row's own confidence/rationale.",
    ),
    DatasetEntry(
        name="World Bank Indicators (non-oil diversification proxy, FDI)",
        path=Path(WORLDBANK_DIR) / "worldbank_latest.csv",
        source_type="Live, automated (World Bank API v2)",
        update_cadence="Weekly, GitHub Actions (Mondays)",
        methodology_note="`src/data_pipeline/fetch_worldbank.py`. Non-oil diversification proxy = 100 - Oil rents (% of GDP).",
        limitations="This project's development sandbox blocks api.worldbank.org outbound -- the columns are currently unpopulated here. Resolves automatically on Render/GitHub Actions, which have normal outbound access; not a code defect. See the Economic Analysis page for a manually-sourced substitute used while this pipeline is unpopulated.",
    ),
]


def build_catalog() -> pd.DataFrame:
    rows = []
    for entry in _REGISTRY:
        if not entry.path.exists():
            rows.append({
                "Dataset": entry.name, "Source type": entry.source_type, "Countries covered": "N/A (file missing)",
                "Observations": 0, "Update cadence": entry.update_cadence, "Missingness": "N/A",
                "Methodology": entry.methodology_note, "Limitations": entry.limitations, "_path": str(entry.path),
            })
            continue
        df = pd.read_csv(entry.path)
        n_obs = len(df)
        if entry.country_col and entry.country_col in df.columns:
            # Some long-format deal files carry a non-tracked pseudo-country
            # row (e.g. "GCC region-wide" context rows, never scored) --
            # count only rows that resolve to one of the 17 tracked countries.
            covered = df[df[entry.country_col].isin(COUNTRIES)][entry.country_col].nunique()
            coverage = f"{covered} / {len(COUNTRIES)} countries"
        else:
            coverage = "Not country-indexed"

        numeric_cols = df.select_dtypes(include="number").columns
        if len(numeric_cols) > 0 and n_obs > 0:
            missing_pct = df[numeric_cols].isna().mean().mean() * 100
            missingness = f"{missing_pct:.0f}% of numeric cells" if missing_pct > 0 else "None"
        else:
            missingness = "N/A"

        rows.append({
            "Dataset": entry.name,
            "Source type": entry.source_type,
            "Countries covered": coverage,
            "Observations": n_obs,
            "Update cadence": entry.update_cadence,
            "Missingness": missingness,
            "Methodology": entry.methodology_note,
            "Limitations": entry.limitations,
            "_path": str(entry.path),
        })
    return pd.DataFrame(rows)
