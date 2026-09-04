"""
Sanctions & Entity List Exposure -- a Sanctions Exposure Score (0-100) built
from data/curated/sanctions_data.csv, following this project's standing
missing-data rule: a factor with no verified value is EXCLUDED from the
weighted average (weights renormalized over whatever is available), never
scored as zero or guessed. Every country currently has real data for 5 of
the 6 weighted factors (BIS tier, OFAC programs, CAATSA status, secondary-
sanctions risk, and evasion risk -- the last two are analyst judgments
derived transparently from the OFAC/EU/CAATSA facts already in the same
row, see each country's `rationale`). Only `entity_list_count` stays
"RESEARCH_NEEDED" in the curated CSV for all 17 countries: no source found
publishes a live per-country tally of the BIS Entity List (it's a rolling
list built from decades of individual Federal Register rules, not a
country-indexed database). `factors_available` is carried through so the UI
can disclose exactly how many of the 6 factors backed each country's score,
the same way scoring.py discloses `*_factors_available` for the two
composite axes.

BIS tier restrictiveness is deliberately NOT re-typed here as a fresh
judgment call -- it's derived directly from this project's own already-cited
data/curated/export_control_tier.csv `tier_score` (0-5, 5=most favorable):
restrictiveness_100 = (5 - tier_score) / 5 * 100. This keeps the two modules
from silently disagreeing about the same underlying BIS Country Group facts.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from constants import CURATED_DIR
from scoring import _weighted_average, build_composite

ENTITY_LIST_WEIGHT = 0.25
BIS_TIER_WEIGHT = 0.20
OFAC_WEIGHT = 0.20
CAATSA_WEIGHT = 0.10
SECONDARY_RISK_WEIGHT = 0.15
EVASION_RISK_WEIGHT = 0.10

SANCTIONS_WEIGHTS = {
    "entity_list_score_100": ENTITY_LIST_WEIGHT,
    "bis_tier_score_100": BIS_TIER_WEIGHT,
    "ofac_score_100": OFAC_WEIGHT,
    "caatsa_score_100": CAATSA_WEIGHT,
    "secondary_risk_score_100": SECONDARY_RISK_WEIGHT,
    "evasion_risk_score_100": EVASION_RISK_WEIGHT,
}

# Documented assumption, not a derived constant: 20 or more BIS Entity List
# entries from one country (among this tracker's 17) would already be an
# extreme outlier, so 20 is used as the "scores 100" ceiling for the
# fixed-ceiling normalization -- mirrors scoring.py's own fixed-ceiling
# rationale for investment/compute (stable as new entries are added, not an
# artifact of who's in the data set this month).
ENTITY_LIST_CEILING = 20

_SEVERITY_BAND_CUTOFFS = [(20, "None"), (40, "Low"), (60, "Moderate"), (80, "High"), (101, "Severe")]


def load_sanctions() -> pd.DataFrame:
    return pd.read_csv(Path(CURATED_DIR) / "sanctions_data.csv")


def _load_tier() -> pd.Series:
    return pd.read_csv(Path(CURATED_DIR) / "export_control_tier.csv").set_index("country")["tier_score"]


def _parse_int_or_nan(value) -> float:
    try:
        return float(int(str(value).strip()))
    except (ValueError, TypeError):
        return float("nan")


def _entity_list_score(count) -> float:
    n = _parse_int_or_nan(count)
    if pd.isna(n):
        return float("nan")
    return min(100.0, n / ENTITY_LIST_CEILING * 100)


def _bis_tier_score(tier_score: float) -> float:
    if pd.isna(tier_score):
        return float("nan")
    return (5 - tier_score) / 5 * 100


def _is_research_needed(value) -> bool:
    """Same dtype-safety rule as investment_flow_engine.py's own
    _is_research_needed(): a non-string is "research needed" only if it's
    actually missing (NaN/None), never just because it fails isinstance(str)
    -- currently inert here since ofac_programs/caatsa_status/etc. are
    free-text fields pandas never infers as numeric, but a bare
    `not isinstance(value, str)` check would silently misclassify a real
    value the moment that stops being true, so it's fixed defensively."""
    if isinstance(value, str):
        return value.strip().lower().startswith("research_needed")
    return pd.isna(value)


def _ofac_score(programs) -> float:
    if _is_research_needed(programs):
        return float("nan")
    p = programs.strip()
    if p.lower().startswith("none"):
        return 0.0
    count = len([x for x in p.split(";") if x.strip()])
    return min(100.0, count * 50.0)


def _caatsa_score(status) -> float:
    if _is_research_needed(status):
        return float("nan")
    s = status.strip().lower()
    if "threatened" in s or "risk of" in s:
        return 50.0
    if s.startswith("none") or s.startswith("n/a"):
        return 0.0
    # Anything else describing an actual designation (e.g. "... sanctions
    # imposed ... over the S-400 purchase") counts as an active designation.
    return 100.0


def _severity_score(value, mapping: dict[str, float]) -> float:
    if _is_research_needed(value):
        return float("nan")
    v = value.strip().lower()
    for key, score in mapping.items():
        if v.startswith(key):
            return score
    return float("nan")


def severity_band(score_100: float) -> str:
    """Maps a 0-100 sub-score to one of the 5 display bands used by the
    heatmap and summary table. NaN maps to "Insufficient data" -- distinct
    from "None", since "we don't know" and "verified zero risk" must never
    be shown as the same color (this project's standing rule against
    conflating a data gap with a real finding)."""
    if pd.isna(score_100):
        return "Insufficient data"
    for ceiling, label in _SEVERITY_BAND_CUTOFFS:
        if score_100 < ceiling:
            return label
    return "Severe"


def build_sanctions_composite() -> pd.DataFrame:
    """Returns one row per country: every curated sanctions_data.csv column,
    each factor's derived 0-100 sub-score and severity band, the composite
    Sanctions Exposure Score (weighted average, renormalized over whatever
    factors are actually available), and net_alignment_score joined in from
    scoring.build_composite() for the positioning scatter plot."""
    df = load_sanctions()
    tier = _load_tier()

    df["bis_tier_raw_score"] = df["country"].map(tier)
    df["entity_list_score_100"] = df["entity_list_count"].apply(_entity_list_score)
    df["bis_tier_score_100"] = df["bis_tier_raw_score"].apply(_bis_tier_score)
    df["ofac_score_100"] = df["ofac_programs"].apply(_ofac_score)
    df["caatsa_score_100"] = df["caatsa_status"].apply(_caatsa_score)
    df["secondary_risk_score_100"] = df["secondary_sanctions_risk"].apply(
        lambda v: _severity_score(v, {"low": 0.0, "moderate": 50.0, "high": 100.0})
    )
    df["evasion_risk_score_100"] = df["sanctions_evasion_risk"].apply(
        lambda v: _severity_score(v, {"low": 0.0, "moderate": 50.0, "high": 75.0, "severe": 100.0})
    )

    _BAND_COLUMN_NAMES = {
        "entity_list_score_100": "entity_list_band",
        "bis_tier_score_100": "bis_tier_band",
        "ofac_score_100": "ofac_band",
        "caatsa_score_100": "caatsa_band",
        "secondary_risk_score_100": "secondary_risk_band",
        "evasion_risk_score_100": "evasion_risk_band",
    }
    for score_col, band_col in _BAND_COLUMN_NAMES.items():
        df[band_col] = df[score_col].apply(severity_band)

    df["sanctions_exposure_score"], df["sanctions_factors_available"] = _weighted_average(df, SANCTIONS_WEIGHTS)

    composite = build_composite()[["country", "net_alignment_score"]]
    df = df.merge(composite, on="country", how="left")
    return df


def heatmap_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Country x sanction-type matrix of severity bands, for the heatmap.
    `df` must already be build_sanctions_composite()'s output (the *_band
    columns it computes)."""
    band_cols = {
        "Entity List": "entity_list_band",
        "BIS Tier": "bis_tier_band",
        "OFAC Programs": "ofac_band",
        "CAATSA": "caatsa_band",
        "Secondary Sanctions Risk": "secondary_risk_band",
        "Evasion Risk": "evasion_risk_band",
    }
    out = pd.DataFrame({"country": df["country"]})
    for label, col in band_cols.items():
        out[label] = df[col]
    return out.set_index("country")
