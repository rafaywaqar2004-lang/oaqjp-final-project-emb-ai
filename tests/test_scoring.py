import math

import pandas as pd
import pytest

from constants import COUNTRIES
from scoring import (
    COMPUTE_CEILING_MW,
    INVESTMENT_CEILING_USD_BN,
    US_COMPUTE_WEIGHT,
    US_INVESTMENT_WEIGHT,
    US_TIER_WEIGHT,
    _log_scale_normalize,
    build_composite,
)


def test_weights_sum_to_one():
    assert US_TIER_WEIGHT + US_INVESTMENT_WEIGHT + US_COMPUTE_WEIGHT == pytest.approx(1.0)


class TestLogScaleNormalize:
    def test_zero_maps_to_zero(self):
        result = _log_scale_normalize(pd.Series([0.0]), ceiling=100)
        assert result.iloc[0] == pytest.approx(0.0)

    def test_ceiling_maps_to_hundred(self):
        result = _log_scale_normalize(pd.Series([100.0]), ceiling=100)
        assert result.iloc[0] == pytest.approx(100.0)

    def test_above_ceiling_clips_at_hundred(self):
        result = _log_scale_normalize(pd.Series([1_000_000.0]), ceiling=100)
        assert result.iloc[0] == pytest.approx(100.0)

    def test_nan_passes_through(self):
        result = _log_scale_normalize(pd.Series([float("nan")]), ceiling=100)
        assert pd.isna(result.iloc[0])

    def test_monotonic_increasing(self):
        result = _log_scale_normalize(pd.Series([1.0, 10.0, 50.0, 99.0]), ceiling=100)
        values = result.tolist()
        assert values == sorted(values)

    def test_two_values_dont_collapse_to_extremes(self):
        """Regression test for the real bug caught during development: with
        only 2 data points, naive min-max normalization stretched a modest
        gap ($34.2bn vs $15.2bn) into an artificial 100-vs-0 spread. The
        fixed-ceiling approach must not reproduce that."""
        result = _log_scale_normalize(pd.Series([34.2, 15.2]), ceiling=INVESTMENT_CEILING_USD_BN)
        higher, lower = result.iloc[0], result.iloc[1]
        assert higher > lower
        assert lower > 50  # both substantial relative to the ceiling -- neither should read as "near zero"
        assert (higher - lower) < 30  # a 2x gap in dollar terms should not read as an ~80-100pt spread


@pytest.fixture(scope="module")
def composite_df():
    return build_composite()


class TestBuildComposite:
    @pytest.fixture
    def df(self, composite_df):
        return composite_df

    def test_all_eight_countries_present(self, df):
        assert set(df["country"]) == set(COUNTRIES.keys())
        assert len(df) == 8

    def test_iso3_codes_match_constants(self, df):
        for _, row in df.iterrows():
            assert row["iso3"] == COUNTRIES[row["country"]]

    def test_net_alignment_score_in_range_or_nan(self, df):
        for value in df["net_alignment_score"]:
            assert pd.isna(value) or 0 <= value <= 100

    def test_us_integration_depth_in_range_or_nan(self, df):
        for value in df["us_integration_depth"]:
            assert pd.isna(value) or 0 <= value <= 100

    def test_china_exposure_depth_matches_penetration_score(self, df):
        # China Exposure Depth is currently a single-factor axis (see README
        # limitations) -- it should equal the normalized penetration score exactly.
        for _, row in df.iterrows():
            if pd.notna(row["china_penetration_score_100"]):
                assert row["china_exposure_depth"] == pytest.approx(row["china_penetration_score_100"])

    def test_factors_available_never_exceeds_three(self, df):
        assert df["us_integration_factors_available"].max() <= 3
        assert df["us_integration_factors_available"].min() >= 0

    def test_net_alignment_formula(self, df):
        """50 + (US Integration Depth - China Exposure Depth) / 2, clipped to [0, 100]."""
        for _, row in df.iterrows():
            if pd.notna(row["us_integration_depth"]) and pd.notna(row["china_exposure_depth"]):
                expected = 50 + (row["us_integration_depth"] - row["china_exposure_depth"]) / 2
                expected = max(0, min(100, expected))
                assert row["net_alignment_score"] == pytest.approx(expected)
            else:
                assert pd.isna(row["net_alignment_score"])

    def test_missing_investment_is_nan_not_zero(self, df):
        """A country with no scored investment deals must show NaN, never 0 --
        0 would silently claim 'known to have no investment,' which is a
        different (and unsupported) claim from 'no data was found.'"""
        no_investment = df[df["investment_usd_bn"].isna()]
        assert not no_investment.empty  # sanity: this scenario actually occurs in the current dataset
        for _, row in no_investment.iterrows():
            assert pd.isna(row["investment_score_100"])

    def test_us_integration_renormalizes_over_available_factors(self, df):
        """A country missing some of the 3 US Integration inputs should have
        its weighted average computed over only the available ones, not
        silently treat the missing ones as zero."""
        for _, row in df.iterrows():
            n_available = row["us_integration_factors_available"]
            if n_available == 0:
                assert pd.isna(row["us_integration_depth"])
            elif n_available == 1 and pd.notna(row["us_tier_score_100"]) and pd.isna(row["investment_score_100"]) and pd.isna(row["compute_score_100"]):
                # only the tier factor was available -- the weighted average
                # over one factor must equal that factor's own value exactly
                assert row["us_integration_depth"] == pytest.approx(row["us_tier_score_100"])
