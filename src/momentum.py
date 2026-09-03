"""
Score Momentum -- reads data/computed/composite_scores_history.csv (built by
scoring.append_history_snapshot()) and classifies how a country's score is
moving. This module is the honest gate between "we have historical data" and
"we don't": every function here returns an explicit insufficient-data result
rather than fabricating a trend when fewer than the required number of dated
snapshots exist, per this project's standing no-fabrication rule.

As of this module's introduction, the history file held exactly one dated
snapshot -- so every call returned INSUFFICIENT_DATA. That was the correct,
honest behavior, not a bug. src/historical_backfill.py later reconstructed 18
additional dated snapshots from real, dated evidence already in this
project's curated data (deal announcement dates, two documented
export-control tier step-changes) -- see that module's docstring for exactly
what is reconstructed vs. held constant. This module's own classification
logic needed no change: a "backfilled" snapshot is just another dated
observation in the history file. Callers that display momentum/trend results
should still disclose when backfilled rows are in view (see
app_pages/country_deep_dive.py's Trend section for the pattern) since a
reconstruction is not the same claim as a point-in-time measurement.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from constants import COMPUTED_DIR

HISTORY_PATH = Path(COMPUTED_DIR) / "composite_scores_history.csv"

# A change smaller than this (in score points) is classified "Stable" rather
# than "Increasing"/"Declining" -- avoids reading noise as a real move.
STABLE_BAND = 2.0

DIRECTION_LABELS = (
    "Accelerating", "Increasing", "Stable", "Declining", "Rapidly declining", "Insufficient data",
)


@dataclass
class MomentumResult:
    metric: str
    current: float | None
    previous: float | None
    change: float | None
    direction: str
    n_observations: int
    note: str


def _insufficient(metric: str, n_observations: int, current: float | None = None) -> MomentumResult:
    note = (
        f"Trend unavailable -- requires at least 2 dated observations (currently {n_observations})."
        if n_observations < 2
        else "Trend unavailable -- requires at least 3 dated observations to classify acceleration."
    )
    return MomentumResult(
        metric=metric, current=current, previous=None, change=None,
        direction="Insufficient data", n_observations=n_observations, note=note,
    )


def load_history(history_path: str | Path = HISTORY_PATH) -> pd.DataFrame:
    history_path = Path(history_path)
    if not history_path.exists():
        return pd.DataFrame(columns=["snapshot_date", "country", "iso3", "us_integration_depth", "china_exposure_depth", "net_alignment_score"])
    df = pd.read_csv(history_path)
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    return df


def _classify(latest_change: float, prior_change: float | None) -> str:
    """latest_change: most recent period's delta. prior_change: the period
    before that, or None if only 2 observations exist (in which case we can
    report direction but never acceleration -- that requires comparing two
    consecutive changes)."""
    if abs(latest_change) <= STABLE_BAND:
        return "Stable"
    if prior_change is None:
        return "Increasing" if latest_change > 0 else "Declining"
    # Acceleration/deceleration: is the most recent move larger in magnitude
    # than the one before it, in the same direction?
    same_direction = (latest_change > 0) == (prior_change > 0)
    if latest_change > 0:
        return "Accelerating" if (same_direction and abs(latest_change) > abs(prior_change)) else "Increasing"
    return "Rapidly declining" if (same_direction and abs(latest_change) > abs(prior_change)) else "Declining"


def compute_momentum(history: pd.DataFrame, country: str, metric: str = "net_alignment_score") -> MomentumResult:
    """Computes momentum for one country/metric from the history dataframe.
    Never interpolates or estimates a missing snapshot -- a country absent
    from the history for a given date simply isn't counted for that date."""
    rows = history[history["country"] == country].sort_values("snapshot_date")
    rows = rows.dropna(subset=[metric])
    n = len(rows)

    if n == 0:
        return _insufficient(metric, 0)
    if n == 1:
        return _insufficient(metric, 1, current=float(rows[metric].iloc[-1]))

    current = float(rows[metric].iloc[-1])
    previous = float(rows[metric].iloc[-2])
    change = current - previous

    if n == 2:
        return MomentumResult(
            metric=metric, current=current, previous=previous, change=change,
            direction=_classify(change, prior_change=None), n_observations=n,
            note="Direction based on 2 observations -- acceleration cannot be classified until a 3rd dated snapshot exists.",
        )

    prior = float(rows[metric].iloc[-3])
    prior_change = previous - prior
    direction = _classify(change, prior_change)
    return MomentumResult(
        metric=metric, current=current, previous=previous, change=change,
        direction=direction, n_observations=n,
        note=f"Based on {n} dated observations ({rows['snapshot_date'].iloc[0]:%Y-%m-%d} to {rows['snapshot_date'].iloc[-1]:%Y-%m-%d}).",
    )


def regional_momentum(history: pd.DataFrame, metric: str = "net_alignment_score") -> MomentumResult:
    """Same classification, applied to the regional average of `metric`
    across all countries present in each snapshot date -- used for the
    Overview KPI row rather than a single country."""
    if history.empty:
        return _insufficient(metric, 0)
    by_date = history.dropna(subset=[metric]).groupby("snapshot_date")[metric].mean().sort_index()
    n = len(by_date)
    if n == 0:
        return _insufficient(metric, 0)
    if n == 1:
        return _insufficient(metric, 1, current=float(by_date.iloc[-1]))

    current = float(by_date.iloc[-1])
    previous = float(by_date.iloc[-2])
    change = current - previous
    if n == 2:
        return MomentumResult(
            metric=metric, current=current, previous=previous, change=change,
            direction=_classify(change, prior_change=None), n_observations=n,
            note="Direction based on 2 observations -- acceleration cannot be classified until a 3rd dated snapshot exists.",
        )
    prior = float(by_date.iloc[-3])
    prior_change = previous - prior
    return MomentumResult(
        metric=metric, current=current, previous=previous, change=change,
        direction=_classify(change, prior_change), n_observations=n,
        note=f"Based on {n} dated regional snapshots.",
    )
