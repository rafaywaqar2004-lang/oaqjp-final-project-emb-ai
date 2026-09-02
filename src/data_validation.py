"""
Data validation -- structural sanity checks over the curated CSVs and the
computed composite scores. Flags a problem as an explicit ValidationIssue
rather than silently coercing bad data (e.g. clipping an out-of-range
score, or dropping a duplicate row without saying so). Run as part of the
test suite (tests/test_data_validation.py exercises this against the
actual repository data on every CI run) and importable for a one-off
manual check via `python -m data_validation` from src/.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from constants import COUNTRIES, CURATED_DIR


@dataclass
class ValidationIssue:
    dataset: str
    severity: str  # "error" | "warning"
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.dataset}: {self.message}"


def validate_country_column(df: pd.DataFrame, dataset_name: str, allow_extra: set[str] | None = None) -> list[ValidationIssue]:
    """Every value in a 'country' column must be one of the 17 tracked
    countries, unless explicitly allowed (e.g. a documented 'GCC
    region-wide' context row). Never silently ignored."""
    issues: list[ValidationIssue] = []
    if "country" not in df.columns:
        return issues
    allow_extra = allow_extra or set()
    unknown = set(df["country"].unique()) - set(COUNTRIES.keys()) - allow_extra
    if unknown:
        issues.append(ValidationIssue(dataset_name, "error", f"Unrecognized country value(s) not in the tracked 17: {sorted(unknown)}"))
    return issues


def validate_iso3_consistency(df: pd.DataFrame, dataset_name: str) -> list[ValidationIssue]:
    """A row's iso3 column must match the ISO3 code this project's own
    constants.py assigns to that country name -- catches a copy-paste
    error (right country, wrong code, or vice versa)."""
    issues: list[ValidationIssue] = []
    if not {"country", "iso3"}.issubset(df.columns):
        return issues
    for _, row in df.iterrows():
        expected = COUNTRIES.get(row["country"])
        if expected is not None and row["iso3"] != expected:
            issues.append(ValidationIssue(dataset_name, "error", f"{row['country']}: iso3 column says '{row['iso3']}', expected '{expected}'"))
    return issues


def validate_no_duplicate_countries(df: pd.DataFrame, dataset_name: str) -> list[ValidationIssue]:
    """For one-row-per-country datasets (curated factor scores, composite
    scores) -- a duplicate country is always a bug, never valid data."""
    issues: list[ValidationIssue] = []
    if "country" not in df.columns:
        return issues
    dupes = df["country"][df["country"].duplicated()].unique()
    if len(dupes) > 0:
        issues.append(ValidationIssue(dataset_name, "error", f"Duplicate country row(s): {sorted(dupes)}"))
    return issues


def validate_ordinal_range(df: pd.DataFrame, column: str, dataset_name: str, lo: int = 0, hi: int = 5) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if column not in df.columns:
        return issues
    values = df[column].dropna()
    out_of_range = values[(values < lo) | (values > hi)]
    if not out_of_range.empty:
        issues.append(ValidationIssue(dataset_name, "error", f"'{column}' has {len(out_of_range)} value(s) outside the valid [{lo}, {hi}] ordinal range: {sorted(out_of_range.unique())}"))
    return issues


def validate_score_range(df: pd.DataFrame, column: str, dataset_name: str, lo: float = 0, hi: float = 100) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if column not in df.columns:
        return issues
    values = df[column].dropna()
    out_of_range = values[(values < lo) | (values > hi)]
    if not out_of_range.empty:
        issues.append(ValidationIssue(dataset_name, "error", f"'{column}' has {len(out_of_range)} value(s) outside the valid [{lo}, {hi}] score range"))
    return issues


def validate_non_negative(df: pd.DataFrame, column: str, dataset_name: str) -> list[ValidationIssue]:
    """Investment dollars and compute MW can be zero or missing, never
    negative -- a negative value here is always a data-entry bug."""
    issues: list[ValidationIssue] = []
    if column not in df.columns:
        return issues
    values = df[column].dropna()
    negative = values[values < 0]
    if not negative.empty:
        issues.append(ValidationIssue(dataset_name, "error", f"'{column}' has {len(negative)} negative value(s) -- impossible for a disclosed dollar/MW figure."))
    return issues


def validate_dates_parseable(df: pd.DataFrame, column: str, dataset_name: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if column not in df.columns:
        return issues
    values = df[column].dropna()
    parsed = pd.to_datetime(values, errors="coerce")
    malformed = values[parsed.isna()]
    if not malformed.empty:
        issues.append(ValidationIssue(dataset_name, "error", f"'{column}' has {len(malformed)} value(s) that don't parse as a date: {list(malformed.unique())[:5]}"))
    return issues


def validate_confidence_values(df: pd.DataFrame, dataset_name: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if "confidence" not in df.columns:
        return issues
    unrecognized = set(df["confidence"].dropna().unique()) - {"High", "Medium", "Low"}
    if unrecognized:
        issues.append(ValidationIssue(dataset_name, "error", f"Unrecognized confidence value(s): {sorted(unrecognized)}"))
    return issues


def validate_required_columns(df: pd.DataFrame, required: set[str], dataset_name: str) -> list[ValidationIssue]:
    missing = required - set(df.columns)
    if missing:
        return [ValidationIssue(dataset_name, "error", f"Missing required column(s): {sorted(missing)}")]
    return []


def validate_weights_sum_to_one(weights: dict[str, float], dataset_name: str, tolerance: float = 1e-6) -> list[ValidationIssue]:
    total = sum(weights.values())
    if abs(total - 1.0) > tolerance:
        return [ValidationIssue(dataset_name, "error", f"Weights {weights} sum to {total}, expected 1.0")]
    return []


def validate_all() -> list[ValidationIssue]:
    """Runs the full battery of checks against this repository's actual
    curated CSVs and computed composite scores. Never raises -- returns
    the issue list so a caller (or a test) decides what to do with it."""
    issues: list[ValidationIssue] = []
    base = Path(CURATED_DIR)

    ordinal_files = {
        "export_control_tier.csv": "tier_score",
        "chinese_tech_penetration.csv": "penetration_score",
        "chinese_digital_ties.csv": "digital_ties_score",
        "governance_maturity.csv": "governance_score",
    }
    for filename, score_col in ordinal_files.items():
        path = base / filename
        if not path.exists():
            continue
        df = pd.read_csv(path)
        issues += validate_country_column(df, filename)
        issues += validate_iso3_consistency(df, filename)
        issues += validate_no_duplicate_countries(df, filename)
        issues += validate_ordinal_range(df, score_col, filename)
        issues += validate_confidence_values(df, filename)
        issues += validate_dates_parseable(df, "as_of_date", filename)

    deal_files = {
        "ai_investment_deals.csv": "amount_usd_bn",
        "compute_capacity_deals.csv": "capacity_mw",
    }
    for filename, amount_col in deal_files.items():
        path = base / filename
        if not path.exists():
            continue
        df = pd.read_csv(path)
        issues += validate_country_column(df, filename, allow_extra={"GCC region-wide"})
        issues += validate_non_negative(df, amount_col, filename)
        issues += validate_dates_parseable(df, "announced_date", filename)

    composite_path = Path("data/computed/composite_scores.csv")
    if composite_path.exists():
        df = pd.read_csv(composite_path)
        issues += validate_country_column(df, "composite_scores.csv")
        issues += validate_iso3_consistency(df, "composite_scores.csv")
        issues += validate_no_duplicate_countries(df, "composite_scores.csv")
        for col in ("net_alignment_score", "us_integration_depth", "china_exposure_depth"):
            issues += validate_score_range(df, col, "composite_scores.csv")

    return issues
