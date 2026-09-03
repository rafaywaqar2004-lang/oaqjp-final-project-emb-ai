"""
Historical backfill for the composite score.

This module reconstructs genuinely dated PAST values of US Integration
Depth, China Exposure Depth, and Net Alignment Score -- so Score Momentum
and Trend (src/momentum.py) have more than the single "day this shipped"
snapshot to work with. It is a RECONSTRUCTION run today against today's
curated data, not a set of point-in-time computations actually made on
those historical dates -- every place this data is surfaced must say so.

What is genuinely reconstructed, and why it's defensible:

  - AI investment and compute-capacity deals: filtered by each deal's own
    `announced_date` column in ai_investment_deals.csv / compute_capacity_
    deals.csv. A deal announced after the snapshot date is simply excluded
    from that snapshot's investment/compute totals -- purely mechanical,
    no judgment involved.

  - Two documented export-control tier step-changes, both cited in
    export_control_tier.csv's own rationale text:
      * Saudi Arabia: tier 0 -> 3 effective 2025-11-19 (HUMAIN capped
        authorization). Before that date the rationale discloses no
        bilateral arrangement existed, so tier 0 is used.
      * United Arab Emirates: tier 4 effective 2026-07-10 (BIS Country
        Group A:5 upgrade). BEFORE that date, this module uses tier 2 as
        an ANALYST INFERENCE -- the same Country Group D:3/D:4 bucket
        Qatar and Bahrain are currently scored in -- because no source
        found this session states the UAE's specific pre-upgrade tier
        number. This is flagged via the `us_tier_inferred` column and
        must never be presented as directly sourced.

What is held constant, and why: Chinese telecom/digital-ties penetration
and AI governance maturity are held at their CURRENT curated values across
every historical snapshot, because no dated evidence exists in this
project's sourcing for when those relationships, deployments, or laws
changed. This is a disclosed simplification -- it means pre-2026 China
Exposure Depth values are likely somewhat overstated for countries whose
Chinese ties visibly deepened over the backfill window (which the
underlying penetration_score/digital_ties_score rationale text may itself
describe), not a claim that those ties were literally unchanged. See
README.md's Methodology section and PROGRESS.md for the same disclosure
in narrative form.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd

from constants import COMPUTED_DIR, COUNTRIES
from scoring import (
    CHINA_DIGITAL_WEIGHT,
    CHINA_TELECOM_WEIGHT,
    COMPUTE_CEILING_MW,
    INVESTMENT_CEILING_USD_BN,
    US_COMPUTE_WEIGHT,
    US_INVESTMENT_WEIGHT,
    US_TIER_WEIGHT,
    _log_scale_normalize,
    _weighted_average,
    load_curated,
)

HISTORY_PATH = Path(COMPUTED_DIR) / "composite_scores_history.csv"

# (effective_date, tier_score, is_inferred) per country, sorted ascending.
# A date far in the past acts as "since before any data in this project."
_FAR_PAST = datetime.date(1900, 1, 1)

TIER_STEP_CHANGES: dict[str, list[tuple[datetime.date, float, bool]]] = {
    "Saudi Arabia": [
        (_FAR_PAST, 0, False),
        (datetime.date(2025, 11, 19), 3, False),
    ],
    "United Arab Emirates": [
        (_FAR_PAST, 2, True),
        (datetime.date(2026, 7, 10), 4, False),
    ],
}


def _tier_as_of(country: str, as_of: datetime.date, current_tier: float) -> tuple[float, bool]:
    """Tier score as of `as_of`. Countries with no documented step change
    (i.e. not in TIER_STEP_CHANGES) keep their current curated tier score
    for every historical date -- see module docstring."""
    changes = TIER_STEP_CHANGES.get(country)
    if not changes:
        return current_tier, False
    value, inferred = current_tier, False
    for change_date, tier, is_inferred in changes:
        if change_date <= as_of:
            value, inferred = tier, is_inferred
    return value, inferred


def _aggregate_as_of(deals: pd.DataFrame, value_col: str, as_of: datetime.date) -> pd.Series:
    counted = deals[deals["counted_in_score"] == True].copy()  # noqa: E712
    counted["announced_date"] = pd.to_datetime(counted["announced_date"]).dt.date
    counted = counted[counted["announced_date"] <= as_of]
    return counted.groupby("country")[value_col].sum(min_count=1)


def build_composite_as_of(as_of: datetime.date) -> pd.DataFrame:
    """Reconstructs the composite score as of `as_of`, reusing the exact
    same weights, normalization, and weighted-average logic as
    scoring.build_composite() (default weights only -- this is the scored
    methodology's own history, not a Scenario Lab what-if). The only
    differences from build_composite(): which deals are counted (filtered
    by announced_date <= as_of) and which tier value applies for Saudi
    Arabia / the UAE (see TIER_STEP_CHANGES)."""
    curated = load_curated()
    countries = list(COUNTRIES.keys())
    df = pd.DataFrame({"country": countries, "iso3": [COUNTRIES[c] for c in countries]})

    current_tier = curated["export_control_tier"].set_index("country")["tier_score"]
    china = curated["chinese_tech_penetration"].set_index("country")["penetration_score"]
    china_digital = curated["chinese_digital_ties"].set_index("country")["digital_ties_score"]

    tier_and_flag = df["country"].apply(
        lambda c: _tier_as_of(c, as_of, current_tier.get(c, float("nan")))
    )
    df["us_tier_raw"] = tier_and_flag.apply(lambda t: t[0])
    df["us_tier_inferred"] = tier_and_flag.apply(lambda t: t[1])

    df["china_penetration_raw"] = df["country"].map(china)
    df["china_digital_raw"] = df["country"].map(china_digital)

    invest_bn = _aggregate_as_of(curated["ai_investment_deals"], "amount_usd_bn", as_of)
    compute_mw = _aggregate_as_of(curated["compute_capacity_deals"], "capacity_mw", as_of)
    df["investment_usd_bn"] = df["country"].map(invest_bn)
    df["compute_mw"] = df["country"].map(compute_mw)

    df["us_tier_score_100"] = df["us_tier_raw"] / 5 * 100
    df["china_penetration_score_100"] = df["china_penetration_raw"] / 5 * 100
    df["china_digital_score_100"] = df["china_digital_raw"] / 5 * 100
    df["investment_score_100"] = _log_scale_normalize(df["investment_usd_bn"], INVESTMENT_CEILING_USD_BN)
    df["compute_score_100"] = _log_scale_normalize(df["compute_mw"], COMPUTE_CEILING_MW)

    df["us_integration_depth"], _ = _weighted_average(df, {
        "us_tier_score_100": US_TIER_WEIGHT,
        "investment_score_100": US_INVESTMENT_WEIGHT,
        "compute_score_100": US_COMPUTE_WEIGHT,
    })
    df["china_exposure_depth"], _ = _weighted_average(df, {
        "china_penetration_score_100": CHINA_TELECOM_WEIGHT,
        "china_digital_score_100": CHINA_DIGITAL_WEIGHT,
    })

    df["net_alignment_score"] = df.apply(
        lambda r: (
            50 + 0.5 * r["us_integration_depth"] - 0.5 * r["china_exposure_depth"]
            if pd.notna(r["us_integration_depth"]) and pd.notna(r["china_exposure_depth"])
            else float("nan")
        ),
        axis=1,
    )
    df["net_alignment_score"] = df["net_alignment_score"].clip(lower=0, upper=100)
    df["as_of_date"] = as_of.isoformat()
    return df


def backfill_dates() -> list[datetime.date]:
    """Every date this project has real, dated evidence to reconstruct
    from: the union of all counted deals' announced_date values (from
    both deal CSVs) plus the two documented tier step-change dates.
    Deliberately NOT an arbitrary monthly/quarterly grid -- every date
    here corresponds to a real disclosed event, per this project's
    no-fabrication rule."""
    curated = load_curated()
    dates: set[datetime.date] = set()
    for key, col in (("ai_investment_deals", "amount_usd_bn"), ("compute_capacity_deals", "capacity_mw")):
        deals = curated[key]
        counted = deals[deals["counted_in_score"] == True]  # noqa: E712
        dates.update(pd.to_datetime(counted["announced_date"]).dt.date.tolist())
    for changes in TIER_STEP_CHANGES.values():
        for change_date, _tier, _inferred in changes:
            if change_date != _FAR_PAST:
                dates.add(change_date)
    return sorted(dates)


def run_backfill(history_path: str | Path = HISTORY_PATH) -> pd.DataFrame:
    """Builds a reconstructed snapshot for every date in backfill_dates()
    and merges them into the history file, tagged source="backfilled" so
    they're distinguishable from source="live_pipeline" snapshots written
    by scoring.append_history_snapshot() on each real pipeline run.
    Idempotent: reruns replace prior rows with source="backfilled" for the
    same dates rather than duplicating them, and never touch
    source="live_pipeline" rows."""
    history_path = Path(history_path)

    snapshots = []
    for as_of in backfill_dates():
        result = build_composite_as_of(as_of)
        snap = result[["country", "iso3", "us_integration_depth", "china_exposure_depth", "net_alignment_score"]].copy()
        snap.insert(0, "snapshot_date", as_of.isoformat())
        snap["source"] = "backfilled"
        snapshots.append(snap)
    backfilled = pd.concat(snapshots, ignore_index=True)

    if history_path.exists():
        existing = pd.read_csv(history_path)
        if "source" not in existing.columns:
            existing["source"] = "live_pipeline"
        backfilled_dates = set(backfilled["snapshot_date"].unique())
        existing = existing[~((existing["source"] == "backfilled") & (existing["snapshot_date"].isin(backfilled_dates)))]
        combined = pd.concat([existing, backfilled], ignore_index=True)
    else:
        combined = backfilled

    history_path.parent.mkdir(parents=True, exist_ok=True)
    combined.sort_values(["snapshot_date", "country"]).to_csv(history_path, index=False)
    return combined


if __name__ == "__main__":
    combined = run_backfill()
    b_dates = sorted(combined.loc[combined["source"] == "backfilled", "snapshot_date"].unique())
    all_dates = sorted(combined["snapshot_date"].unique())
    print(f"Reconstructed (backfilled) snapshot dates ({len(b_dates)}): {b_dates}")
    print(f"Total distinct snapshot dates in history ({len(all_dates)}, incl. live_pipeline): {all_dates}")
    print(f"Total history rows: {len(combined)}")
    print(f"Wrote {HISTORY_PATH}")
