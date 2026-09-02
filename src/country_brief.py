"""
Auto-generates a short, analyst-style country brief (BLUF + key judgments)
from the tracker's own curated and computed data -- no free-text generation,
no LLM call at runtime. Every sentence is built from a real cell in
data/curated/*.csv or data/computed/composite_scores.csv, so the brief
changes only when the underlying data changes, and every claim in it is
traceable back to a specific sourced row.

This is the Phase 3 "downloadable PDF brief" pattern, generalized to run
for any of the 8 countries rather than hand-written once.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from constants import CURATED_DIR
from scoring import build_composite


@dataclass
class Judgment:
    text: str
    confidence: str  # "High confidence" / "Moderate confidence" / "Low confidence" / "Data gap"


@dataclass
class CountryBrief:
    country: str
    iso3: str
    as_of: str
    bluf: str
    key_judgments: list[Judgment]
    investment_note: str
    compute_note: str
    sources: list[dict] = field(default_factory=list)


_CONFIDENCE_MAP = {"High": "High confidence", "Medium": "Moderate confidence", "Low": "Low confidence"}


def _confidence_label(raw: str) -> str:
    return _CONFIDENCE_MAP.get(str(raw).strip(), "Moderate confidence")


def _alignment_band(score: float) -> str:
    if pd.isna(score):
        return "insufficient data to place on the alignment spectrum"
    if score >= 65:
        return "deep US integration"
    if score >= 50:
        return "US-leaning, hedging"
    if score >= 35:
        return "China-leaning, hedging"
    return "deep China exposure"


def _tier_characterization(tier: int) -> str:
    if pd.isna(tier):
        return "has no scored US export-control access tier on record"
    tier = int(tier)
    if tier >= 4:
        return "holds one of the most favorable US chip-access positions in this comparison set"
    if tier == 3:
        return "has secured a bespoke, capped chip-access arrangement rather than a country-wide rule"
    if tier == 2:
        return "has no disclosed bilateral chip-export framework, though some licensing accommodation may exist"
    return "has no disclosed bilateral chip-export arrangement of any kind identified in this research"


def load_curated() -> dict[str, pd.DataFrame]:
    base = Path(CURATED_DIR)
    return {
        "tier": pd.read_csv(base / "export_control_tier.csv"),
        "china": pd.read_csv(base / "chinese_tech_penetration.csv"),
        "governance": pd.read_csv(base / "governance_maturity.csv"),
        "investment": pd.read_csv(base / "ai_investment_deals.csv"),
        "compute": pd.read_csv(base / "compute_capacity_deals.csv"),
    }


def generate_brief(country: str, curated: dict[str, pd.DataFrame] | None = None, composite: pd.DataFrame | None = None) -> CountryBrief:
    curated = curated or load_curated()
    composite = composite if composite is not None else build_composite()

    row = composite[composite["country"] == country].iloc[0]
    tier_row = curated["tier"][curated["tier"]["country"] == country]
    china_row = curated["china"][curated["china"]["country"] == country]
    gov_row = curated["governance"][curated["governance"]["country"] == country]

    inv_deals = curated["investment"][(curated["investment"]["country"] == country) & (curated["investment"]["counted_in_score"] == True)]  # noqa: E712
    compute_deals = curated["compute"][(curated["compute"]["country"] == country) & (curated["compute"]["counted_in_score"] == True)]  # noqa: E712

    score = row["net_alignment_score"]
    band = _alignment_band(score)
    score_text = f"{score:.0f}/100" if pd.notna(score) else "not computed (insufficient data)"

    if pd.notna(row["us_integration_depth"]) and pd.notna(row["china_exposure_depth"]):
        bluf = (
            f"{country}'s Net Alignment Score is {score_text}, placing it in the '{band}' range on the "
            f"tracker's 0 (China-leaning) to 100 (US-integrated) spectrum -- built from a US Integration "
            f"Depth of {row['us_integration_depth']:.0f}/100 (based on {int(row['us_integration_factors_available'])} of 3 "
            f"available inputs) against a China Exposure Depth of {row['china_exposure_depth']:.0f}/100."
        )
    else:
        bluf = (
            f"{country}'s Net Alignment Score could not be computed -- insufficient public data on the "
            f"US Integration and/or China Exposure axis. See the key judgments below for what is and isn't "
            f"known."
        )

    judgments: list[Judgment] = []

    if not tier_row.empty:
        t = tier_row.iloc[0]
        judgments.append(Judgment(
            text=f"On US export-control access, {country} {_tier_characterization(t['tier_score'])}: {t['tier_label']}. {t['rationale']}",
            confidence=_confidence_label(t["confidence"]),
        ))

    inv_total = inv_deals["amount_usd_bn"].sum() if not inv_deals.empty else 0
    compute_total = compute_deals["capacity_mw"].sum() if not compute_deals.empty else 0
    if inv_total > 0 or compute_total > 0:
        parts = []
        if inv_total > 0:
            top_deal = inv_deals.sort_values("amount_usd_bn", ascending=False).iloc[0]
            parts.append(f"${inv_total:.1f}bn in disclosed, in-country AI infrastructure investment (largest single item: {top_deal['deal_name']}, ${top_deal['amount_usd_bn']:.1f}bn, {top_deal['announced_date']})")
        if compute_total > 0:
            parts.append(f"{compute_total:.0f}MW of disclosed or under-development AI compute/data-center capacity")
        judgments.append(Judgment(
            text=f"{country} has {' and '.join(parts)}. Aspirational or globally-anchored figures not tied to a specific disclosed deal are excluded from these totals -- see the tracker's data files for the full deal-by-deal record.",
            confidence="Moderate confidence",
        ))
        investment_note = f"${inv_total:.1f}bn disclosed" if inv_total > 0 else "No disclosed dollar figure"
        compute_note = f"{compute_total:.0f}MW disclosed/under development" if compute_total > 0 else "No disclosed MW figure"
    else:
        judgments.append(Judgment(
            text=f"No disclosed AI infrastructure investment or compute-capacity figure at country-specific, deal-level detail was identified for {country} in this research pass. This reflects a gap in public disclosure at the sourcing bar this project uses, not necessarily a gap in underlying activity.",
            confidence="Data gap",
        ))
        investment_note = "No disclosed figure found"
        compute_note = "No disclosed figure found"

    if not china_row.empty:
        c = china_row.iloc[0]
        judgments.append(Judgment(
            text=f"On Chinese technology penetration, {country} is characterized as '{c['penetration_label']}'. {c['rationale']}",
            confidence=_confidence_label(c["confidence"]),
        ))

    if not gov_row.empty:
        g = gov_row.iloc[0]
        judgments.append(Judgment(
            text=f"On AI governance maturity, {country} is characterized as '{g['governance_label']}'. {g['rationale']}",
            confidence=_confidence_label(g["confidence"]),
        ))

    sources = []
    for topic, df in (("Export control", tier_row), ("Chinese tech penetration", china_row), ("Governance", gov_row)):
        if not df.empty:
            r = df.iloc[0]
            sources.append({"topic": topic, "name": r["source_name"], "url": r.get("source_url", ""), "date": r["as_of_date"]})
    for _, r in inv_deals.iterrows():
        sources.append({"topic": "Investment", "name": r["source_name"], "url": r.get("source_url", ""), "date": r["announced_date"]})
    for _, r in compute_deals.iterrows():
        sources.append({"topic": "Compute capacity", "name": r["source_name"], "url": r.get("source_url", ""), "date": r["announced_date"]})

    return CountryBrief(
        country=country,
        iso3=row["iso3"],
        as_of="September 2026",
        bluf=bluf,
        key_judgments=judgments,
        investment_note=investment_note,
        compute_note=compute_note,
        sources=sources,
    )
