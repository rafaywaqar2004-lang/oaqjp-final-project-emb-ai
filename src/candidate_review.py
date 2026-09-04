"""
Loads the candidate-events queue (fetched by
src/data_pipeline/fetch_candidate_events.py from the Federal Register and
OFAC) and the reviewer's own decisions on each candidate, for the
Candidate Events admin page.

Nothing here writes to data/curated/policy_events.csv -- that only happens
when a human, on the app page, reviews a specific candidate and submits
the pre-filled "Add to Policy Events" form. This module only tracks which
candidates have already been looked at (confirmed or rejected) so the
queue doesn't keep re-showing them.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from constants import CANDIDATE_EVENTS_DIR

CANDIDATES_PATH = Path(CANDIDATE_EVENTS_DIR) / "candidates.csv"
REVIEW_LOG_PATH = Path(CANDIDATE_EVENTS_DIR) / "review_log.csv"
REVIEW_LOG_COLUMNS = ["source", "external_id", "status", "reviewed_at"]


def load_candidates() -> pd.DataFrame:
    """Empty (not missing-file-error) DataFrame with the right columns if
    the pipeline hasn't run yet -- the page should say so, not crash."""
    if not CANDIDATES_PATH.exists():
        return pd.DataFrame(columns=["source", "external_id", "date", "title", "summary", "url", "matched_countries"])
    return pd.read_csv(CANDIDATES_PATH, dtype=str, keep_default_na=False)


def load_review_log() -> pd.DataFrame:
    if not REVIEW_LOG_PATH.exists():
        return pd.DataFrame(columns=REVIEW_LOG_COLUMNS)
    return pd.read_csv(REVIEW_LOG_PATH, dtype=str, keep_default_na=False)


def pending_candidates(candidates: pd.DataFrame, review_log: pd.DataFrame) -> pd.DataFrame:
    """Candidates not yet marked confirmed/rejected, newest first. A
    candidate is identified by (source, external_id) -- OFAC and Federal
    Register external_ids are drawn from different id spaces, so both
    fields are needed to avoid an accidental collision."""
    if candidates.empty:
        return candidates
    if review_log.empty:
        return candidates.sort_values("date", ascending=False)
    reviewed_keys = set(zip(review_log["source"], review_log["external_id"]))
    mask = ~candidates.apply(lambda r: (r["source"], r["external_id"]) in reviewed_keys, axis=1)
    return candidates[mask].sort_values("date", ascending=False)


def record_review(source: str, external_id: str, status: str) -> None:
    """Appends one decision to the review log. `status` is "confirmed" or
    "rejected". Writes directly to the running server's filesystem -- same
    ephemeral-on-most-hosts caveat as this project's other admin editors
    (see the Candidate Events page's own disclaimer)."""
    log = load_review_log()
    new_row = pd.DataFrame([{
        "source": source, "external_id": external_id, "status": status,
        "reviewed_at": pd.Timestamp.today().isoformat(),
    }])
    updated = pd.concat([log, new_row], ignore_index=True)
    REVIEW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    updated.to_csv(REVIEW_LOG_PATH, index=False)
