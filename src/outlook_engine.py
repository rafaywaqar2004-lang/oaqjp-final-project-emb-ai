"""
12-Month Outlook -- deliberately NOT a machine-learning forecast (this
tracker has no historical trend data to train one from -- see
src/momentum.py's own honesty about that). Instead: a templated Base Case
("current position persists, absent a specific disclosed pending event")
and an Alternative Case built directly from this country's own Watch Next
items (already real, already cited elsewhere). Probability is reported as
a qualitative, explicitly analyst-assigned band (Likely/Possible/Unlikely)
-- never a fabricated numeric percentage implying a false quantitative
precision this project's data doesn't support.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class OutlookCase:
    assessment: str
    probability: str  # "Likely" | "Possible" | "Unlikely" | "N/A"
    confidence: str
    evidence: str
    label: str = "ANALYST JUDGMENT"  # never "MODEL OUTPUT" -- this page computes nothing predictive


@dataclass
class CountryOutlook:
    country: str
    current_position_label: str  # explicitly labeled MODEL OUTPUT -- the one real computed number here
    base_case: OutlookCase
    alternative_case: OutlookCase
    watch_items: pd.DataFrame


def build_outlook(row: pd.Series, country_watch_items: pd.DataFrame) -> CountryOutlook:
    country = row["country"]
    score = row["net_alignment_score"]
    current_position_label = (
        f"Net Alignment {score:.0f}/100 (US Integration {row['us_integration_depth']:.0f}, "
        f"China Exposure {row['china_exposure_depth']:.0f})" if pd.notna(score) else "Insufficient data to compute a current position"
    )

    if country_watch_items.empty:
        base_case = OutlookCase(
            assessment=f"Absent a specific disclosed pending event, {country}'s current position is likely to persist over the next 12 months.",
            probability="Likely",
            confidence="Low",
            evidence="No country-specific pending policy or infrastructure decision is on file for this country (see Watch Next) -- this is an absence-of-evidence judgment, not a strong prediction.",
        )
        alternative_case = OutlookCase(
            assessment=f"No specific, disclosed pending indicator exists for {country} that this tracker can point to as a plausible near-term driver of change.",
            probability="N/A",
            confidence="Insufficient data",
            evidence="See the Overview's regional Watch Next items for region-wide (not country-specific) indicators that could still affect this country indirectly (e.g. a new bilateral US authorization precedent, or a regional BIS Country Group review).",
        )
    else:
        item = country_watch_items.iloc[0]
        base_case = OutlookCase(
            assessment=f"Absent resolution of the pending item below, {country}'s current position is likely to persist over the next 12 months.",
            probability="Likely" if item["confidence"] == "Low" else "Possible",
            confidence=item["confidence"],
            evidence=f"Based on 1 disclosed pending indicator ('{item['indicator']}') that has not yet resolved as of this tracker's last review.",
        )
        alternative_case = OutlookCase(
            assessment=f"If '{item['indicator']}' resolves, {country}'s position could shift: {item['why_it_matters']}",
            probability="Possible",
            confidence=item["confidence"],
            evidence=f"Current signal: {item['current_signal']} (see Watch Next / {item['source_ref']}).",
        )

    return CountryOutlook(
        country=country,
        current_position_label=current_position_label,
        base_case=base_case,
        alternative_case=alternative_case,
        watch_items=country_watch_items,
    )
