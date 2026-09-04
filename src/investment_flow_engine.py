"""
Sovereign AI Investment Flow Tracker -- tracks government-directed and
sovereign-wealth-fund AI/tech capital flows from data/curated/investment_flows.csv,
and derives a Capital Alignment Ratio (US-bound investment as a share of
US+China-bound investment) per source country. This is a genuinely different
signal from this project's existing composite score: `data/curated/
ai_investment_deals.csv` + `scoring.py`'s US Integration Depth measures
disclosed investment RECEIVED in-country (feeds the composite score);
this module measures capital SENT OUT by Gulf-state sovereign funds and
which bloc's ecosystem it lands in. The two datasets are deliberately kept
separate -- see README.md for why.

Two judgment calls made explicit here, not buried in the numbers:

1. **Same-country ("sovereign launch") deals are excluded from cross-border
   flow calculations.** deal_id 003 (HUMAIN's $40bn sovereign AI buildout)
   has source_country == destination_country == Saudi Arabia -- it is
   domestic capital deployment, not a flow TO another country, so including
   it in a "capital flow direction" metric would be a category error (and
   at $40bn, it would swamp every other deal in the dataset by more than
   25x). It is still shown in the deal-level table and reported separately
   as a domestic sovereign buildout total.

2. **The Capital Alignment Ratio is computed strictly over
   bloc_affiliation in {"US", "China"}.** "US-aligned" (used for the HUMAIN
   launch's own bloc label, reflecting its US-partner-heavy buildout
   strategy) and any future "Neutral" label are excluded from the ratio's
   numerator/denominator entirely -- included in "US" would overstate how
   literally US-bound the capital is; excluding them is the more
   conservative, literal reading of "US / (US + China)".

Rows whose deal_value_usd_millions is "RESEARCH_NEEDED" are excluded from
every dollar total (never treated as zero) and counted separately, per this
project's standing missing-data rule.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from constants import CURATED_DIR
from scoring import build_composite

FLOWS_PATH = Path(CURATED_DIR) / "investment_flows.csv"

TRACKED_SOURCE_COUNTRIES = [
    "Saudi Arabia", "United Arab Emirates", "Qatar", "Bahrain", "Kuwait", "Oman",
    "Turkey", "Pakistan",
]


def _is_research_needed(value) -> bool:
    """A string is "research needed" only if it's literally the marker text;
    any other non-string is "research needed" only if it's actually missing
    (NaN/None) -- NOT simply because it isn't a str. A column with zero
    remaining RESEARCH_NEEDED cells gets read back by pandas as a numeric
    dtype (int64/float64), so a bare `not isinstance(value, str)` check would
    misclassify every real, confirmed dollar value as unconfirmed the moment
    a country's data gap is fully closed -- exactly the scenario this
    project's own research passes are working toward."""
    if isinstance(value, str):
        return value.strip().upper() == "RESEARCH_NEEDED"
    return pd.isna(value)


def load_flows() -> pd.DataFrame:
    df = pd.read_csv(FLOWS_PATH, dtype={"deal_id": str})
    return df


def _parse_value(value) -> float:
    if _is_research_needed(value):
        return float("nan")
    try:
        return float(value)
    except (ValueError, TypeError):
        return float("nan")


def with_parsed_value(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["deal_value_usd_millions_parsed"] = df["deal_value_usd_millions"].apply(_parse_value)
    df["is_cross_border"] = df["source_country"] != df["destination_country"]
    return df


def unconfirmed_value_count(df: pd.DataFrame) -> int:
    """Deals with a RESEARCH_NEEDED deal_value_usd_millions -- excluded from
    every dollar total below, counted here so the UI can disclose how many
    tracked deals have no confirmed value rather than silently omitting them."""
    if df.empty:
        return 0
    return int(df["deal_value_usd_millions"].apply(_is_research_needed).sum())


def cross_border_flows(df: pd.DataFrame) -> pd.DataFrame:
    """Excludes same-country ("sovereign launch") deals -- see module
    docstring for why."""
    df = with_parsed_value(df)
    return df[df["is_cross_border"]]


def domestic_sovereign_deals(df: pd.DataFrame) -> pd.DataFrame:
    df = with_parsed_value(df)
    return df[~df["is_cross_border"]]


def bloc_totals(df: pd.DataFrame) -> dict[str, float]:
    """Total confirmed-value $M per bloc_affiliation, over cross-border
    flows only. NaN (unconfirmed) values are excluded via groupby's default
    NaN handling -- never treated as zero."""
    flows = cross_border_flows(df)
    totals = flows.groupby("bloc_affiliation")["deal_value_usd_millions_parsed"].sum(min_count=1)
    return {k: float(v) for k, v in totals.items() if pd.notna(v)}


def capital_alignment_ratio(us_total: float, china_total: float) -> float | None:
    """US / (US + China) * 100. None if both are zero/missing (never a
    divide-by-zero, never a guessed 50%)."""
    denom = (us_total or 0) + (china_total or 0)
    if denom <= 0:
        return None
    return (us_total or 0) / denom * 100


def per_country_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per TRACKED_SOURCE_COUNTRIES entry: us_total_usd_millions,
    china_total_usd_millions, capital_alignment_ratio (0-100 or NaN if no
    US/China-bloc cross-border deal with a confirmed value is on file for
    that country), n_deals, n_deals_unconfirmed_value. Joined against
    scoring.build_composite()'s net_alignment_score for the positioning
    scatter plot."""
    flows = cross_border_flows(df)
    flows = flows[flows["bloc_affiliation"].isin(["US", "China"])]

    records = []
    for country in TRACKED_SOURCE_COUNTRIES:
        country_deals = df[df["source_country"] == country]
        country_flows = flows[flows["source_country"] == country]
        us_total = country_flows.loc[country_flows["bloc_affiliation"] == "US", "deal_value_usd_millions_parsed"].sum(min_count=1)
        china_total = country_flows.loc[country_flows["bloc_affiliation"] == "China", "deal_value_usd_millions_parsed"].sum(min_count=1)
        us_total = 0.0 if pd.isna(us_total) else float(us_total)
        china_total = 0.0 if pd.isna(china_total) else float(china_total)
        ratio = capital_alignment_ratio(us_total, china_total)
        records.append({
            "country": country,
            "us_total_usd_millions": us_total,
            "china_total_usd_millions": china_total,
            "capital_alignment_ratio": ratio,
            "n_deals": int(len(country_deals)),
            "n_deals_unconfirmed_value": unconfirmed_value_count(country_deals),
        })

    result = pd.DataFrame(records)
    composite = build_composite()[["country", "net_alignment_score"]]
    return result.merge(composite, on="country", how="left")


def by_quarter(df: pd.DataFrame) -> pd.DataFrame:
    """US-bound vs. China-bound confirmed-value $M per calendar quarter,
    over cross-border flows only. Deals with a RESEARCH_NEEDED date are
    excluded (never bucketed into a guessed quarter)."""
    flows = cross_border_flows(df)
    flows = flows[flows["bloc_affiliation"].isin(["US", "China"])]
    flows = flows[~flows["date"].apply(_is_research_needed)]
    flows = flows.dropna(subset=["deal_value_usd_millions_parsed"])
    flows = flows.copy()
    # date is "YYYY-MM" for most deals but "YYYY-MM-DD" for a few with a
    # disclosed exact date -- format="mixed" handles both without guessing.
    flows["quarter"] = pd.PeriodIndex(pd.to_datetime(flows["date"], format="mixed"), freq="Q").astype(str)
    pivot = flows.pivot_table(
        index="quarter", columns="bloc_affiliation", values="deal_value_usd_millions_parsed",
        aggfunc="sum",
    ).fillna(0)
    for col in ("US", "China"):
        if col not in pivot.columns:
            pivot[col] = 0.0
    return pivot.reset_index().sort_values("quarter")


def by_sector(df: pd.DataFrame) -> pd.DataFrame:
    """Confirmed-value $M total per sector, over cross-border flows only."""
    flows = cross_border_flows(df)
    totals = flows.groupby("sector")["deal_value_usd_millions_parsed"].sum(min_count=1).dropna()
    return totals.reset_index().rename(columns={"deal_value_usd_millions_parsed": "total_usd_millions"})


def sankey_data(df: pd.DataFrame) -> dict:
    """Nodes/links for a Plotly Sankey: source_country -> destination_country,
    width proportional to confirmed deal value, colored by bloc_affiliation.
    Deals with no confirmed value are excluded (a zero-width link is
    meaningless); same-country deals are excluded (see module docstring)."""
    flows = cross_border_flows(df)
    flows = flows.dropna(subset=["deal_value_usd_millions_parsed"])

    countries = sorted(set(flows["source_country"]) | set(flows["destination_country"]))
    index = {c: i for i, c in enumerate(countries)}

    bloc_color = {"US": "#2463A5", "China": "#B5473A", "US-aligned": "#8FB6DC", "Neutral": "#6B7280"}
    links = {
        "source": [index[r["source_country"]] for _, r in flows.iterrows()],
        "target": [index[r["destination_country"]] for _, r in flows.iterrows()],
        "value": [r["deal_value_usd_millions_parsed"] for _, r in flows.iterrows()],
        "color": [bloc_color.get(r["bloc_affiliation"], "#6B7280") for _, r in flows.iterrows()],
        "label": [f"{r['source_fund']} -> {r['destination_company']}" for _, r in flows.iterrows()],
    }
    return {"labels": countries, "links": links}
