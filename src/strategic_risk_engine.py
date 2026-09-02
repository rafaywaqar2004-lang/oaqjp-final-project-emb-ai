"""
Strategic Risk -- rates each tracked country on a small set of risk
dimensions derived transparently from this tracker's own existing scored
data (never a separately invented risk score). Every rating traces back to
a specific number already computed elsewhere in this project.

Two dimensions the brief's own list names -- "semiconductor dependency"
and "geopolitical volatility" -- are deliberately NOT rated per-country
here. Semiconductor dependency would just restate US Policy Exposure +
China Exposure in different words (this project's own two axes already
measure exactly that). Geopolitical volatility would require a political
judgment this project's curated data doesn't support without guessing --
per this project's standing rule, that means exposing the limitation
rather than inventing a rating.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

RISK_LEVELS = ("Low", "Moderate", "High", "Insufficient data")

_CONFIDENCE_RANK = {"High": 0, "Medium": 1, "Low": 2}


@dataclass
class RiskDimension:
    name: str
    level: str
    basis: str


def _us_policy_exposure(row: pd.Series) -> RiskDimension:
    tier = row["us_tier_raw"]
    if pd.isna(tier):
        return RiskDimension("US Policy Exposure", "Insufficient data", "No scored US export-control tier on record.")
    if tier >= 4:
        return RiskDimension("US Policy Exposure", "High", f"Tier {tier:.0f}/5 -- holds a broad, license-free bilateral arrangement with the most to lose if US export-control policy tightens.")
    if tier >= 2:
        return RiskDimension("US Policy Exposure", "Moderate", f"Tier {tier:.0f}/5 -- some disclosed access or accommodation that could be revised.")
    return RiskDimension("US Policy Exposure", "Low", f"Tier {tier:.0f}/5 -- little or no current bilateral arrangement at risk of reversal.")


def _china_exposure_risk(row: pd.Series) -> RiskDimension:
    depth = row["china_exposure_depth"]
    if pd.isna(depth):
        return RiskDimension("China Exposure", "Insufficient data", "China Exposure Depth could not be computed (insufficient underlying data).")
    if depth >= 65:
        return RiskDimension("China Exposure", "High", f"China Exposure Depth {depth:.0f}/100 -- deep telecom/digital ties carry real transmission-channel risk from future US secondary-sanctions actions.")
    if depth >= 35:
        return RiskDimension("China Exposure", "Moderate", f"China Exposure Depth {depth:.0f}/100 -- meaningful but not dominant Chinese technology ties.")
    return RiskDimension("China Exposure", "Low", f"China Exposure Depth {depth:.0f}/100 -- limited disclosed Chinese telecom/digital engagement.")


def _infrastructure_execution_risk(country: str, compute_deals: pd.DataFrame, investment_deals: pd.DataFrame) -> RiskDimension:
    """Share of a country's counted, disclosed AI compute capacity that is
    still under_development/target rather than already disclosed_current.
    Falls back to investment deal_type if no compute deals are on file."""
    comp = compute_deals[(compute_deals["country"] == country) & (compute_deals["counted_in_score"] == True) & compute_deals["capacity_mw"].notna()]  # noqa: E712
    if not comp.empty:
        total = comp["capacity_mw"].sum()
        not_yet_built = comp[comp["status"] != "disclosed_current"]["capacity_mw"].sum()
        share = not_yet_built / total if total > 0 else 0.0
        if share >= 0.66:
            return RiskDimension("Infrastructure Execution Risk", "High", f"{share:.0%} of this country's counted, disclosed compute capacity is still under development or a stated target, not yet operating.")
        if share >= 0.25:
            return RiskDimension("Infrastructure Execution Risk", "Moderate", f"{share:.0%} of counted compute capacity is still under development or a stated target.")
        return RiskDimension("Infrastructure Execution Risk", "Low", f"Only {share:.0%} of counted compute capacity is still under development -- most is already operating.")

    inv = investment_deals[(investment_deals["country"] == country) & (investment_deals["counted_in_score"] == True)]
    if not inv.empty:
        return RiskDimension("Infrastructure Execution Risk", "Insufficient data", "Disclosed investment exists but no compute-capacity deal is on file to assess build-out status against.")
    return RiskDimension("Infrastructure Execution Risk", "Insufficient data", "No disclosed, scored investment or compute-capacity deal on file for this country.")


def _measurement_confidence_risk(country: str, curated: dict[str, pd.DataFrame]) -> RiskDimension:
    """How much of this country's own scored position rests on Low- or
    Medium-confidence curated rows -- a risk in the *assessment* itself,
    not a claim about the country's real-world position."""
    confidences = []
    for key in ("tier", "china", "china_digital"):
        row = curated[key][curated[key]["country"] == country]
        if not row.empty:
            confidences.append(row.iloc[0]["confidence"])
    if not confidences:
        return RiskDimension("Measurement Confidence Risk", "Insufficient data", "No curated rows found for this country's core scored factors.")
    worst = max(confidences, key=lambda c: _CONFIDENCE_RANK.get(c, 1))
    n_low = sum(1 for c in confidences if c == "Low")
    if worst == "Low":
        return RiskDimension("Measurement Confidence Risk", "High", f"{n_low} of {len(confidences)} core factors are Low confidence -- this country's own scored position is less certain than most.")
    if worst == "Medium":
        return RiskDimension("Measurement Confidence Risk", "Moderate", "Core factors are Medium confidence -- a reasonably but not fully verified position.")
    return RiskDimension("Measurement Confidence Risk", "Low", "All core factors are High confidence -- a well-verified position.")


def assess_country(row: pd.Series, curated: dict[str, pd.DataFrame]) -> list[RiskDimension]:
    return [
        _us_policy_exposure(row),
        _china_exposure_risk(row),
        _infrastructure_execution_risk(row["country"], curated["compute"], curated["investment"]),
        _measurement_confidence_risk(row["country"], curated),
    ]


def assess_all(composite: pd.DataFrame, curated: dict[str, pd.DataFrame]) -> pd.DataFrame:
    records = []
    for _, row in composite.iterrows():
        dims = assess_country(row, curated)
        record = {"Country": row["country"]}
        for d in dims:
            record[d.name] = d.level
        records.append(record)
    return pd.DataFrame(records)
