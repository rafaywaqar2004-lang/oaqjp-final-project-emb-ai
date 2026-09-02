from pathlib import Path

import pandas as pd
import pytest

from constants import CURATED_DIR

VALID_CATEGORIES = {"Regulatory Framework", "Bilateral Authorization", "Enforcement Action", "Legislation"}


@pytest.fixture(scope="module")
def events():
    df = pd.read_csv(Path(CURATED_DIR) / "policy_events.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_at_least_one_event(events):
    assert len(events) > 0


def test_dates_parse_and_are_not_in_the_future(events):
    # "the future" relative to this project's stated as-of date (September 2026)
    as_of = pd.Timestamp("2026-09-02")
    assert (events["date"] <= as_of).all()


def test_categories_are_all_recognized(events):
    assert set(events["category"]).issubset(VALID_CATEGORIES)


def test_every_event_has_a_source(events):
    for _, row in events.iterrows():
        assert isinstance(row["source_name"], str) and len(row["source_name"]) > 0
        assert isinstance(row["source_url"], str) and row["source_url"].startswith("http")


def test_every_event_has_a_nonempty_summary_and_countries(events):
    for _, row in events.iterrows():
        assert len(row["summary"]) > 20
        assert len(row["countries"]) > 0


def test_no_duplicate_titles(events):
    assert events["title"].is_unique
