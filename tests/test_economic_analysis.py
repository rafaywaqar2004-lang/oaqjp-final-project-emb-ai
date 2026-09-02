import pandas as pd
import pytest

from pathlib import Path

from constants import COUNTRIES, CURATED_DIR
from economic_analysis import (
    CANDIDATE_RELATIONSHIPS,
    diversification_vs_china_exposure,
    governance_vs_tier_correlation,
    robustness_checks,
)
from scoring import build_composite


@pytest.fixture(scope="module")
def composite():
    return build_composite()


@pytest.fixture(scope="module")
def diversification():
    return pd.read_csv(Path(CURATED_DIR) / "non_oil_diversification.csv")


def test_governance_vs_tier_uses_full_sample(composite):
    result = governance_vs_tier_correlation(composite)
    assert result.n == 17


def test_governance_vs_tier_correlation_is_moderate_positive(composite):
    """Sanity check against the actual known relationship in this dataset
    (computed independently during development: r ~= 0.68) -- catches a
    sign error or a badly broken correlation calculation, not a fabricated
    target value."""
    result = governance_vs_tier_correlation(composite)
    assert 0.3 < result.pearson_r < 0.9
    assert result.strength_label in {"moderate", "moderate-to-strong"}


def test_exclude_countries_reduces_sample_size(composite):
    result = governance_vs_tier_correlation(composite, exclude_countries=["Saudi Arabia", "United Arab Emirates"])
    assert result.n == 15


def test_robustness_checks_returns_three_results(composite):
    results = robustness_checks(composite)
    assert len(results) == 3
    assert results[0].n == 17
    assert results[1].n == 15
    assert results[2].n == 15


def test_correlation_never_exceeds_valid_range(composite):
    for result in robustness_checks(composite):
        assert -1.0 <= result.pearson_r <= 1.0
        assert -1.0 <= result.spearman_rho <= 1.0


def test_perfect_positive_correlation():
    df = pd.DataFrame({
        "country": ["A", "B", "C", "D", "E"],
        "governance_raw": [0, 1, 2, 3, 4],
        "us_tier_raw": [0, 1, 2, 3, 4],
    })
    result = governance_vs_tier_correlation(df)
    assert result.pearson_r == pytest.approx(1.0)
    assert result.strength_label == "moderate-to-strong"


def test_no_correlation():
    df = pd.DataFrame({
        "country": ["A", "B", "C", "D"],
        "governance_raw": [1, 1, 1, 1],
        "us_tier_raw": [0, 2, 1, 3],
    })
    result = governance_vs_tier_correlation(df)
    # constant x -> undefined/NaN correlation, must not crash
    assert result.n == 4


class TestNonOilDiversificationData:
    """Structural checks on data/curated/non_oil_diversification.csv --
    manually researched (IMF/national-statistics sourced) to supply real
    data for the Economic Analysis page's supplementary finding, since the
    live World Bank pipeline is unpopulated in this sandbox."""

    def test_all_tracked_countries_present(self, diversification):
        assert set(diversification["country"]) == set(COUNTRIES.keys())

    def test_figure_type_is_recognized(self, diversification):
        assert set(diversification["figure_type"]).issubset(
            {"direct_non_oil_share", "computed_from_oil_rents", "not_applicable", "not_found"}
        )

    def test_not_applicable_rows_have_no_numeric_figure(self, diversification):
        """A country marked not_applicable must never carry a number --
        that would silently reintroduce the exact fabrication risk this
        column's honesty depends on avoiding."""
        na_rows = diversification[diversification["figure_type"] == "not_applicable"]
        assert na_rows["non_oil_gdp_share_pct"].isna().all()

    def test_rows_with_a_figure_have_a_source(self, diversification):
        with_figure = diversification[diversification["non_oil_gdp_share_pct"].notna()]
        assert len(with_figure) > 0
        for _, row in with_figure.iterrows():
            assert isinstance(row["source_name"], str) and len(row["source_name"]) > 0
            assert isinstance(row["source_url"], str) and row["source_url"].startswith("http")

    def test_figures_are_plausible_percentages(self, diversification):
        with_figure = diversification[diversification["non_oil_gdp_share_pct"].notna()]
        assert with_figure["non_oil_gdp_share_pct"].between(0, 100).all()

    def test_confidence_values_are_recognized(self, diversification):
        assert set(diversification["confidence"]).issubset({"High", "Medium", "Low"})


class TestDiversificationVsChinaExposure:
    def test_uses_only_countries_with_a_real_figure(self, composite, diversification):
        result = diversification_vs_china_exposure(composite, diversification)
        n_with_figure = diversification["non_oil_gdp_share_pct"].notna().sum()
        assert result.n == n_with_figure

    def test_correlation_is_within_valid_range(self, composite, diversification):
        result = diversification_vs_china_exposure(composite, diversification)
        assert -1.0 <= result.pearson_r <= 1.0


class TestCandidateRelationshipsDocumentedHonestly:
    """The rejected candidate analyses (investment/compute correlations on
    too-small samples, the blocked World Bank diversification proxy) must
    stay documented with their real reject reasons -- this is the record
    of *why* the module doesn't just report the biggest-looking number."""

    def test_every_candidate_has_a_reject_reason(self):
        for candidate in CANDIDATE_RELATIONSHIPS:
            assert len(candidate["reject_reason"]) > 20

    def test_small_sample_candidates_are_flagged(self):
        small_n = [c for c in CANDIDATE_RELATIONSHIPS if c["n"] <= 6]
        assert len(small_n) >= 2
