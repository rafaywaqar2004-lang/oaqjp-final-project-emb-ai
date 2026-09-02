import numpy as np
import pytest

from constants import COUNTRIES
from scenario_lab import N_ROBUSTNESS_SAMPLES, ROBUSTNESS_SEED, _robustness_label, _robustness_table


@pytest.fixture(scope="module")
def robustness_df():
    return _robustness_table.__wrapped__(n_samples=30, seed=ROBUSTNESS_SEED)


def test_every_country_appears(robustness_df):
    assert set(robustness_df["country"]) == set(COUNTRIES.keys())


def test_ranks_are_within_valid_range(robustness_df):
    n = len(COUNTRIES)
    for col in ["median_rank", "rank_min", "rank_max"]:
        assert robustness_df[col].between(1, n).all()


def test_rank_range_is_nonnegative_and_consistent(robustness_df):
    assert (robustness_df["rank_range"] == robustness_df["rank_max"] - robustness_df["rank_min"]).all()
    assert (robustness_df["rank_range"] >= 0).all()


def test_top3_pct_is_a_fraction(robustness_df):
    assert robustness_df["top3_pct"].between(0, 1).all()


def test_reproducible_with_fixed_seed():
    a = _robustness_table.__wrapped__(n_samples=20, seed=123)
    b = _robustness_table.__wrapped__(n_samples=20, seed=123)
    pd_testing_equal = a.reset_index(drop=True).equals(b.reset_index(drop=True))
    assert pd_testing_equal


def test_different_seeds_can_differ():
    a = _robustness_table.__wrapped__(n_samples=20, seed=1)
    b = _robustness_table.__wrapped__(n_samples=20, seed=2)
    # Not asserting they must differ (could coincide), just that both are valid, independently computed tables.
    assert len(a) == len(b) == len(COUNTRIES)


@pytest.mark.parametrize("rank_range,expected", [(0, "HIGH"), (2, "HIGH"), (3, "MODERATE"), (5, "MODERATE"), (6, "LOW"), (17, "LOW")])
def test_robustness_label_thresholds(rank_range, expected):
    label, _color = _robustness_label(rank_range)
    assert label == expected


def test_default_sample_count_is_reasonable():
    # documented in the UI copy -- keep the constant and the copy in sync by asserting a sane bound
    assert 50 <= N_ROBUSTNESS_SAMPLES <= 1000
