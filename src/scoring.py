"""
Composite scoring for the Gulf AI & Tech-Bloc Alignment Tracker.

Methodology summary (see README.md for full rationale):

Seven factors are grouped onto two axes plus a context group:

  US Integration Depth (0-100), weighted average of:
    - US export-control access tier (0-5 ordinal, curated)   weight 0.40
    - Disclosed in-country AI infrastructure investment ($bn) weight 0.30
    - Disclosed/under-development compute capacity (MW)       weight 0.30

  China Exposure Depth (0-100), weighted average of:
    - Chinese telecom penetration (0-5 ordinal, curated)       weight 0.50
      (Huawei/ZTE RAN/5G vendor relationships)
    - Chinese AI/cloud/digital-infrastructure ties (0-5,        weight 0.50
      ordinal, curated) -- Chinese cloud regions (Huawei
      Cloud/Alibaba Cloud/Tencent Cloud), Chinese-origin AI
      model deployments (Qwen/Ernie/DeepSeek/Pangu), and
      BRI/CPEC-style Chinese financing of digital infrastructure.
      Added specifically to close this axis's prior single-factor
      limitation -- see README's "Country set" / PROGRESS.md for
      when and why.

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

import datetime
import math
from pathlib import Path

import pandas as pd

from constants import COUNTRIES, CURATED_DIR, WORLDBANK_DIR

US_TIER_WEIGHT = 0.40
US_INVESTMENT_WEIGHT = 0.30
US_COMPUTE_WEIGHT = 0.30

CHINA_TELECOM_WEIGHT = 0.50
CHINA_DIGITAL_WEIGHT = 0.50

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
        "chinese_digital_ties": pd.read_csv(base / "chinese_digital_ties.csv"),
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


def _weighted_average(df: pd.DataFrame, weights: dict[str, float]) -> tuple[pd.Series, pd.Series]:
    """Weighted average across the given 0-100 columns, per row, renormalized
    over whatever columns are actually available for that row (a missing
    factor is excluded, never treated as 0) -- shared by both US Integration
    Depth and China Exposure Depth so the two axes' missing-data handling
    can't drift apart. Returns (value, n_factors_available)."""

    def _row(row: pd.Series) -> tuple[float | None, int]:
        available = {k: w for k, w in weights.items() if pd.notna(row[k])}
        if not available:
            return None, 0
        total_weight = sum(available.values())
        value = sum(row[k] * (w / total_weight) for k, w in available.items())
        return value, len(available)

    results = df.apply(_row, axis=1)
    return results.apply(lambda r: r[0]), results.apply(lambda r: r[1])


def build_composite(
    tier_weight: float = US_TIER_WEIGHT,
    investment_weight: float = US_INVESTMENT_WEIGHT,
    compute_weight: float = US_COMPUTE_WEIGHT,
    axis_balance: float = 0.5,
    investment_ceiling: float = INVESTMENT_CEILING_USD_BN,
    compute_ceiling: float = COMPUTE_CEILING_MW,
    china_telecom_weight: float = CHINA_TELECOM_WEIGHT,
    china_digital_weight: float = CHINA_DIGITAL_WEIGHT,
) -> pd.DataFrame:
    """
    tier_weight / investment_weight / compute_weight: relative weights within
    US Integration Depth (renormalized to sum to 1 -- pass any positive
    numbers, e.g. 40/30/30 or 70/15/15, not necessarily already summing to 1).
    Defaults reproduce the scored methodology exactly.

    china_telecom_weight / china_digital_weight: relative weights within
    China Exposure Depth (same renormalization rule as the US Integration
    weights above). Defaults (50/50) reproduce the scored methodology
    exactly. Lets a Scenario Lab viewer ask "what if telecom vendor choice
    matters more than AI/cloud/financing ties, or vice versa" -- the same
    kind of question the US-side weights already let them ask.

    axis_balance: how much Net Alignment Score weighs US Integration Depth
    vs. China Exposure Depth, in [0, 1]. Default 0.5 reproduces the scored
    formula (50 + (US - China) / 2) exactly. Used by the Scenario Lab
    (app_pages/scenario_lab.py) to let a viewer ask "what if I weighted
    China exposure more heavily than US integration" -- never changes the
    underlying curated data, only how it's combined.

    investment_ceiling / compute_ceiling: the fixed-ceiling log-scale
    normalization anchors (see module docstring for why fixed, not
    dataset-relative). Defaults reproduce the scored methodology exactly.
    Also used by the Scenario Lab's normalization-sensitivity section, to
    let a viewer check whether the ranking holds up under an alternative,
    equally-defensible ceiling choice -- these are documented judgment
    calls, not derived constants, and this is how that's made checkable
    rather than just asserted.
    """
    curated = load_curated()
    wb = load_worldbank()

    countries = list(COUNTRIES.keys())
    df = pd.DataFrame({"country": countries, "iso3": [COUNTRIES[c] for c in countries]})

    tier = curated["export_control_tier"].set_index("country")["tier_score"]
    china = curated["chinese_tech_penetration"].set_index("country")["penetration_score"]
    china_digital = curated["chinese_digital_ties"].set_index("country")["digital_ties_score"]
    gov = curated["governance_maturity"].set_index("country")["governance_score"]
    invest_bn = _aggregate_investment(curated["ai_investment_deals"])
    compute_mw = _aggregate_compute(curated["compute_capacity_deals"])

    df["us_tier_raw"] = df["country"].map(tier)
    df["china_penetration_raw"] = df["country"].map(china)
    df["china_digital_raw"] = df["country"].map(china_digital)
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
    df["china_digital_score_100"] = df["china_digital_raw"] / 5 * 100
    df["governance_score_100"] = df["governance_raw"] / 5 * 100
    df["investment_score_100"] = _log_scale_normalize(df["investment_usd_bn"], investment_ceiling)
    df["compute_score_100"] = _log_scale_normalize(df["compute_mw"], compute_ceiling)

    # US Integration Depth and China Exposure Depth: weighted averages over
    # available factors only, with weights renormalized so a missing factor
    # doesn't silently penalize a country -- it's just excluded, and we
    # track how many factors were available for transparency.
    df["us_integration_depth"], df["us_integration_factors_available"] = _weighted_average(df, {
        "us_tier_score_100": tier_weight,
        "investment_score_100": investment_weight,
        "compute_score_100": compute_weight,
    })
    df["china_exposure_depth"], df["china_exposure_factors_available"] = _weighted_average(df, {
        "china_penetration_score_100": china_telecom_weight,
        "china_digital_score_100": china_digital_weight,
    })

    df["net_alignment_score"] = df.apply(
        lambda r: (
            50 + axis_balance * r["us_integration_depth"] - (1 - axis_balance) * r["china_exposure_depth"]
            if pd.notna(r["us_integration_depth"]) and pd.notna(r["china_exposure_depth"])
            else float("nan")
        ),
        axis=1,
    )
    df["net_alignment_score"] = df["net_alignment_score"].clip(lower=0, upper=100)

    return df


def append_history_snapshot(result: pd.DataFrame, history_path: str | Path = "data/computed/composite_scores_history.csv") -> None:
    """Appends a dated snapshot of the scored columns to a running history
    file -- the one thing that has to start happening *before* Score
    Momentum, trend charts, or a real 12-Month Outlook can ever be built
    honestly (this tracker stores only a single current value per country
    otherwise; see PROGRESS.md). Idempotent per day: re-running this on the
    same date replaces that date's rows rather than duplicating them, so a
    same-day re-run (e.g. a second manual refresh) doesn't skew a future
    average with a duplicate observation."""
    history_path = Path(history_path)
    today = datetime.date.today().isoformat()

    snapshot = result[["country", "iso3", "us_integration_depth", "china_exposure_depth", "net_alignment_score"]].copy()
    snapshot.insert(0, "snapshot_date", today)

    if history_path.exists():
        existing = pd.read_csv(history_path)
        existing = existing[existing["snapshot_date"] != today]
        combined = pd.concat([existing, snapshot], ignore_index=True)
    else:
        combined = snapshot

    history_path.parent.mkdir(parents=True, exist_ok=True)
    combined.sort_values(["snapshot_date", "country"]).to_csv(history_path, index=False)


if __name__ == "__main__":
    result = build_composite()
    out_path = Path("data/computed/composite_scores.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False)
    append_history_snapshot(result)
    print(result[["country", "us_integration_depth", "china_exposure_depth", "net_alignment_score"]])
    print(f"\nWrote {out_path}")
    print("Appended dated snapshot to data/computed/composite_scores_history.csv")
