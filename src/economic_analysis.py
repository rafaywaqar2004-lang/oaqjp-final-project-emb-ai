"""
The tracker's one serious empirical economic-analysis module (see
app_pages/economic_analysis.py for the page that presents this).

Research question: is a country's AI governance maturity associated with
its US export-control access tier? Chosen as the strongest defensible
relationship available in this project's own curated data -- candidates
involving AI investment or compute capacity were considered and rejected
for sample size (only 4-6 of 17 countries have both a disclosed investment
and compute figure; a correlation computed on 4-6 points is not a serious
analysis, however large it looks -- see reject_reason on those in
CANDIDATE_RELATIONSHIPS below). Governance maturity and export-control
tier are both scored for all 17 tracked countries, giving a full-sample
result.

No regression is fit here deliberately -- with n=17 and two ordinal (0-5)
variables, a fitted regression line would imply a precision the data
doesn't support. Pearson and Spearman correlation coefficients are
reported instead, with an explicit ASSOCIATION-not-CAUSATION caveat and a
robustness check (does the relationship survive removing the most extreme
points, so a reader can judge whether it's driven by 2-3 outliers or holds
generally).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class CorrelationResult:
    x_label: str
    y_label: str
    n: int
    pearson_r: float
    spearman_rho: float
    robustness_note: str
    strength_label: str


CANDIDATE_RELATIONSHIPS = [
    {
        "pair": "AI investment ($bn) vs. compute capacity (MW)",
        "n": 4,
        "reject_reason": "Only 4 of 17 countries have both a disclosed investment and a disclosed compute figure -- a correlation on 4 points is not a defensible finding regardless of its magnitude (r=0.94 on n=4 is exactly the kind of result this project declines to present as real).",
    },
    {
        "pair": "US export-control tier vs. AI investment ($bn)",
        "n": 6,
        "reject_reason": "Only 6 of 17 countries have a disclosed investment figure -- too small a sample for a defensible cross-country association claim.",
    },
    {
        "pair": "AI governance maturity vs. AI investment ($bn)",
        "n": 6,
        "reject_reason": "Same 6-country sample-size limitation as above.",
    },
    {
        "pair": "Non-oil economic diversification vs. AI investment ($bn)",
        "n": 2,
        "reject_reason": "This project's live World Bank pipeline is unpopulated in this sandbox, so a manual research pass (data/curated/non_oil_diversification.csv, IMF/national-statistics sourced) supplied real diversification figures for 8 countries instead -- but only Saudi Arabia and UAE have both that figure AND a disclosed investment figure. n=2 is not a defensible correlation regardless of its size.",
    },
]


def _pearson(x: pd.Series, y: pd.Series) -> float:
    return float(np.corrcoef(x.astype(float), y.astype(float))[0, 1])


def _spearman(x: pd.Series, y: pd.Series) -> float:
    return _pearson(x.rank(), y.rank())


def _strength_label(r: float) -> str:
    abs_r = abs(r)
    if abs_r >= 0.6:
        return "moderate-to-strong"
    if abs_r >= 0.3:
        return "moderate"
    if abs_r >= 0.1:
        return "weak"
    return "negligible"


def governance_vs_tier_correlation(df: pd.DataFrame, exclude_countries: list[str] | None = None) -> CorrelationResult:
    """df must carry 'governance_raw', 'us_tier_raw', 'country'. Both are
    0-5 ordinal curated values available for all 17 tracked countries, so
    no row is ever dropped here for missing data (unlike the investment/
    compute candidates above)."""
    working = df
    if exclude_countries:
        working = df[~df["country"].isin(exclude_countries)]
    x = working["governance_raw"]
    y = working["us_tier_raw"]
    r = _pearson(x, y)
    rho = _spearman(x, y)
    return CorrelationResult(
        x_label="AI Governance Maturity (0-5)",
        y_label="US Export-Control Tier (0-5)",
        n=len(working),
        pearson_r=r,
        spearman_rho=rho,
        robustness_note=(
            f"{'Excluding ' + ', '.join(exclude_countries) + ': ' if exclude_countries else 'Full sample: '}"
            f"n={len(working)}, Pearson r={r:.3f}"
        ),
        strength_label=_strength_label(r),
    )


def diversification_vs_china_exposure(composite: pd.DataFrame, diversification: pd.DataFrame) -> CorrelationResult:
    """Supplementary exploratory finding: does non-oil economic
    diversification associate with China Exposure Depth? Uses
    data/curated/non_oil_diversification.csv -- manually researched
    (IMF/national-statistics sourced) since this project's live World Bank
    pipeline is unpopulated in its development sandbox (blocked outbound
    network access, not a data problem -- see README). Only 8 of 17
    countries have a real, sourced diversification figure (the other 9 are
    structurally not-applicable: not hydrocarbon-rent economies, so the
    proxy doesn't mean anything for them -- see that CSV's own
    figure_type/rationale columns), so this is reported as a secondary,
    smaller-sample finding alongside the primary governance-vs-tier result,
    never presented with equal weight to a full n=17 analysis."""
    merged = composite.merge(diversification[["country", "non_oil_gdp_share_pct"]], on="country", how="left")
    sub = merged.dropna(subset=["non_oil_gdp_share_pct", "china_exposure_depth"])
    x = sub["non_oil_gdp_share_pct"]
    y = sub["china_exposure_depth"]
    r = _pearson(x, y)
    rho = _spearman(x, y)
    return CorrelationResult(
        x_label="Non-Oil GDP Share (%)",
        y_label="China Exposure Depth (0-100)",
        n=len(sub),
        pearson_r=r,
        spearman_rho=rho,
        robustness_note=f"n={len(sub)} -- too small for a robustness-exclusion check to be meaningful; reported as exploratory only.",
        strength_label=_strength_label(r),
    )


def robustness_checks(df: pd.DataFrame) -> list[CorrelationResult]:
    """The full-sample result plus two exclusion checks, so a reader can
    see whether the association is driven by a couple of extreme points
    (Saudi Arabia/UAE at the high end, Yemen/Afghanistan sharing a 0/0
    floor) rather than holding generally."""
    return [
        governance_vs_tier_correlation(df),
        governance_vs_tier_correlation(df, exclude_countries=["Saudi Arabia", "United Arab Emirates"]),
        governance_vs_tier_correlation(df, exclude_countries=["Yemen", "Afghanistan"]),
    ]
