"""
Composite scoring for the Gulf AI & Tech-Bloc Alignment Tracker.

Methodology summary (see README.md for full rationale):

Six factors are grouped onto two axes plus a context group:

  US Integration Depth (0-100), weighted average of:
    - US export-control access tier (0-5 ordinal, curated)   weight 0.40
    - Disclosed in-country AI infrastructure investment ($bn) weight 0.30
    - Disclosed/under-development compute capacity (MW)       weight 0.30

  China Exposure Depth (0-100):
    - Chinese tech penetration (0-5 ordinal, curated)          weight 1.00
    (single-factor axis -- documented as a limitation; see README)

  Net Alignment Score (0-100, 50 = neutral):
    50 + (US Integration Depth - China Exposure Depth) / 2

  Context factors (shown separately, NOT folded into Net Alignment):
    - AI governance maturity (0-5 ordinal, curated)
    - Non-oil economic diversification proxy (World Bank, live-refreshed)

Missing factors are excluded from an axis's weighted average (weights
renormalized over whatever is available) and surfaced as "insufficient
public data" rather than imputed or scored as zero.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from constants import COUNTRIES, CURATED_DIR, WORLDBANK_DIR

US_TIER_WEIGHT = 0.40
US_INVESTMENT_WEIGHT = 0.30
US_COMPUTE_WEIGHT = 0.30

# Fixed-ceiling log-scale normalization anchors. Deliberately NOT dataset-
# relative min-max: with only 2-3 countries carrying disclosed investment/
# compute figures in this data set, min-max would stretch a modest gap
# (e.g. $34bn vs $15bn) into a 100-vs-0 score, which misrepresents two
# countries that are both genuinely substantial. Fixed ceilings keep scores
# stable as new deals are added and make "what would it take to score 100"
# an explicit, documented choice rather than an artifact of who else is in
# the data set this month.
INVESTMENT_CEILING_USD_BN = 50   # chosen above Saudi Arabia's current scored total ($34.2bn) to leave headroom
COMPUTE_CEILING_MW = 6000        # matches Saudi Arabia's own disclosed 2034 target; a round, sourced "high end" anchor


def _log_scale_normalize(series: pd.Series, ceiling: float) -> pd.Series:
    """log10(x+1) / log10(ceiling+1) * 100, clipped to [0, 100]. NaN passes through."""
    denom = math.log10(ceiling + 1)

    def _score(x: float) -> float | None:
        if pd.isna(x):
            return None
        return min(100.0, math.log10(x + 1) / denom * 100)

    return series.apply(_score)


def load_curated() -> dict[str, pd.DataFrame]:
    base = Path(CURATED_DIR)
    return {
        "export_control_tier": pd.read_csv(base / "export_control_tier.csv"),
        "chinese_tech_penetration": pd.read_csv(base / "chinese_tech_penetration.csv"),
        "governance_maturity": pd.read_csv(base / "governance_maturity.csv"),
        "ai_investment_deals": pd.read_csv(base / "ai_investment_deals.csv"),
        "compute_capacity_deals": pd.read_csv(base / "compute_capacity_deals.csv"),
    }


def load_worldbank() -> pd.DataFrame:
    path = Path(WORLDBANK_DIR) / "worldbank_latest.csv"
    if not path.exists():
        return pd.DataFrame(columns=["country", "iso3", "non_oil_diversification_proxy"])
    return pd.read_csv(path)


def _aggregate_investment(deals: pd.DataFrame) -> pd.Series:
    counted = deals[deals["counted_in_score"] == True]  # noqa: E712
    totals = counted.groupby("country")["amount_usd_bn"].sum(min_count=1)
    return totals


def _aggregate_compute(deals: pd.DataFrame) -> pd.Series:
    counted = deals[deals["counted_in_score"] == True]  # noqa: E712
    totals = counted.groupby("country")["capacity_mw"].sum(min_count=1)
    return totals


def build_composite() -> pd.DataFrame:
    curated = load_curated()
    wb = load_worldbank()

    countries = list(COUNTRIES.keys())
    df = pd.DataFrame({"country": countries, "iso3": [COUNTRIES[c] for c in countries]})

    tier = curated["export_control_tier"].set_index("country")["tier_score"]
    china = curated["chinese_tech_penetration"].set_index("country")["penetration_score"]
    gov = curated["governance_maturity"].set_index("country")["governance_score"]
    invest_bn = _aggregate_investment(curated["ai_investment_deals"])
    compute_mw = _aggregate_compute(curated["compute_capacity_deals"])

    df["us_tier_raw"] = df["country"].map(tier)
    df["china_penetration_raw"] = df["country"].map(china)
    df["governance_raw"] = df["country"].map(gov)
    df["investment_usd_bn"] = df["country"].map(invest_bn)
    df["compute_mw"] = df["country"].map(compute_mw)

    if not wb.empty:
        wb_indexed = wb.set_index("country")["non_oil_diversification_proxy"]
        df["non_oil_diversification_proxy"] = df["country"].map(wb_indexed)
    else:
        df["non_oil_diversification_proxy"] = float("nan")

    # Normalize each raw input to 0-100.
    df["us_tier_score_100"] = df["us_tier_raw"] / 5 * 100
    df["china_penetration_score_100"] = df["china_penetration_raw"] / 5 * 100
    df["governance_score_100"] = df["governance_raw"] / 5 * 100
    df["investment_score_100"] = _log_scale_normalize(df["investment_usd_bn"], INVESTMENT_CEILING_USD_BN)
    df["compute_score_100"] = _log_scale_normalize(df["compute_mw"], COMPUTE_CEILING_MW)

    # US Integration Depth: weighted average over available factors only,
    # with weights renormalized so a missing factor doesn't silently
    # penalize a country -- it's just excluded, and we track how many
    # of the 3 factors were available for transparency.
    weights = {
        "us_tier_score_100": US_TIER_WEIGHT,
        "investment_score_100": US_INVESTMENT_WEIGHT,
        "compute_score_100": US_COMPUTE_WEIGHT,
    }

    def weighted_us_integration(row: pd.Series) -> tuple[float | None, int]:
        available = {k: w for k, w in weights.items() if pd.notna(row[k])}
        if not available:
            return None, 0
        total_weight = sum(available.values())
        value = sum(row[k] * (w / total_weight) for k, w in available.items())
        return value, len(available)

    results = df.apply(weighted_us_integration, axis=1)
    df["us_integration_depth"] = results.apply(lambda r: r[0])
    df["us_integration_factors_available"] = results.apply(lambda r: r[1])

    df["china_exposure_depth"] = df["china_penetration_score_100"]

    df["net_alignment_score"] = df.apply(
        lambda r: (
            50 + (r["us_integration_depth"] - r["china_exposure_depth"]) / 2
            if pd.notna(r["us_integration_depth"]) and pd.notna(r["china_exposure_depth"])
            else float("nan")
        ),
        axis=1,
    )
    df["net_alignment_score"] = df["net_alignment_score"].clip(lower=0, upper=100)

    return df


if __name__ == "__main__":
    result = build_composite()
    out_path = Path("data/computed/composite_scores.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False)
    print(result[["country", "us_integration_depth", "china_exposure_depth", "net_alignment_score"]])
    print(f"\nWrote {out_path}")
