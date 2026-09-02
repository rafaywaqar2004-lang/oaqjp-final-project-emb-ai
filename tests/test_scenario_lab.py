import numpy as np
import pandas as pd
import pytest

from constants import COUNTRIES
from scenario_lab import N_ROBUSTNESS_SAMPLES, ROBUSTNESS_SEED, _robustness_label, _robustness_table, _scenario_interpretation


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


class TestScenarioInterpretation:
    def _merged(self, baseline_scores: dict, scenario_scores: dict) -> pd.DataFrame:
        countries = list(baseline_scores.keys())
        return pd.DataFrame({
            "country": countries,
            "baseline": [baseline_scores[c] for c in countries],
            "scenario": [scenario_scores[c] for c in countries],
        })

    def test_default_preset_always_says_reproduces_baseline(self):
        merged = self._merged({"A": 10, "B": 20}, {"A": 99, "B": 1})  # scores irrelevant for this preset name
        text = _scenario_interpretation(merged, "Default (as scored)")
        assert "reproduces the baseline ranking exactly" in text

    def test_identical_scores_report_no_movement(self):
        scores = {"A": 80, "B": 60, "C": 40, "D": 20, "E": 10, "F": 5}
        merged = self._merged(scores, scores)
        text = _scenario_interpretation(merged, "Some Preset")
        assert "robust to this particular reweighting" in text

    def test_disjoint_top5_reports_material_reordering(self):
        # 10 countries, baseline top 5 (A-E) and scenario top 5 (F-J) share zero members --
        # the clearest possible case of a scenario materially reordering the ranking.
        baseline = {"A": 100, "B": 90, "C": 80, "D": 70, "E": 60, "F": 50, "G": 40, "H": 30, "I": 20, "J": 10}
        scenario = {"A": 10, "B": 20, "C": 30, "D": 40, "E": 50, "F": 60, "G": 70, "H": 80, "I": 90, "J": 100}
        merged = self._merged(baseline, scenario)
        text = _scenario_interpretation(merged, "Some Preset")
        assert "materially reorders" in text

    def test_too_few_comparable_countries_is_handled(self):
        merged = pd.DataFrame({"country": ["A"], "baseline": [50.0], "scenario": [60.0]})
        text = _scenario_interpretation(merged, "Some Preset")
        assert "Not enough countries" in text
