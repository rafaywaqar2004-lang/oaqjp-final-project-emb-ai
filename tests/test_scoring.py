import math
from pathlib import Path

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

    def test_all_countries_present(self, df):
        assert set(df["country"]) == set(COUNTRIES.keys())
        assert len(df) == len(COUNTRIES)

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


class TestScenarioOverrides:
    """Covers the Scenario Lab's override parameters (app_pages/scenario_lab.py).
    These must never touch data/curated/*.csv -- only change how the same
    curated numbers are combined."""

    def test_default_ceilings_reproduce_baseline_exactly(self):
        baseline = build_composite()
        overridden = build_composite(investment_ceiling=INVESTMENT_CEILING_USD_BN, compute_ceiling=COMPUTE_CEILING_MW)
        pd.testing.assert_frame_equal(baseline, overridden)

    def test_tighter_ceiling_raises_scores_for_countries_with_disclosed_deals(self):
        """A country with a nonzero disclosed investment/compute figure should
        score higher (or equal) against a lower ceiling -- tightening the
        ceiling can only make an existing figure look larger relative to it,
        never smaller."""
        loose = build_composite(investment_ceiling=100, compute_ceiling=12000)
        tight = build_composite(investment_ceiling=25, compute_ceiling=3000)
        has_investment = loose["investment_usd_bn"].notna()
        assert (tight.loc[has_investment, "investment_score_100"] >= loose.loc[has_investment, "investment_score_100"] - 1e-9).all()

    def test_ceiling_override_can_change_the_ranking(self):
        """Regression guard for the normalization-sensitivity feature: this
        is only a meaningful check if some country's rank can actually move
        under a tighter ceiling -- verified against the real curated data,
        not asserted blindly."""
        default_df = build_composite()
        tight_df = build_composite(investment_ceiling=25, compute_ceiling=3000)
        d = default_df.dropna(subset=["net_alignment_score"]).set_index("country")["net_alignment_score"].rank(ascending=False, method="min")
        t = tight_df.dropna(subset=["net_alignment_score"]).set_index("country")["net_alignment_score"].rank(ascending=False, method="min")
        assert not d.equals(t)  # at least one country's rank actually moves

    def test_default_params_reproduce_baseline_exactly(self):
        baseline = build_composite()
        overridden = build_composite(
            tier_weight=US_TIER_WEIGHT, investment_weight=US_INVESTMENT_WEIGHT,
            compute_weight=US_COMPUTE_WEIGHT, axis_balance=0.5,
        )
        pd.testing.assert_frame_equal(baseline, overridden)

    def test_weights_are_renormalized_not_required_to_sum_to_one(self):
        """Scenario presets pass human-friendly numbers like 70/15/15, not
        fractions that already sum to 1 -- the function must renormalize."""
        df_raw = build_composite(tier_weight=70, investment_weight=15, compute_weight=15)
        df_fraction = build_composite(tier_weight=0.70, investment_weight=0.15, compute_weight=0.15)
        pd.testing.assert_series_equal(df_raw["us_integration_depth"], df_fraction["us_integration_depth"])

    def test_tier_heavy_weighting_moves_scores_toward_tier_factor(self):
        """A country whose tier score differs a lot from its investment/compute
        scores should visibly shift when tier is weighted much more heavily."""
        baseline = build_composite().set_index("country")
        tier_heavy = build_composite(tier_weight=100, investment_weight=1, compute_weight=1).set_index("country")
        # Saudi Arabia has real investment/compute data in the curated set, so
        # its US Integration Depth composition actually changes under this reweighting.
        assert not math.isclose(
            baseline.loc["Saudi Arabia", "us_integration_depth"],
            tier_heavy.loc["Saudi Arabia", "us_integration_depth"],
            abs_tol=0.01,
        )

    def test_axis_balance_zero_ignores_us_integration(self):
        """axis_balance=0 should make Net Alignment depend only on China
        Exposure Depth (inverted, since higher China exposure still means
        lower alignment): 50 - China Exposure Depth, clipped to [0, 100]."""
        df = build_composite(axis_balance=0.0)
        for _, row in df.iterrows():
            if pd.notna(row["china_exposure_depth"]):
                expected = max(0, min(100, 50 - row["china_exposure_depth"]))
                assert row["net_alignment_score"] == pytest.approx(expected)

    def test_axis_balance_one_ignores_china_exposure(self):
        """axis_balance=1 should make Net Alignment depend only on US
        Integration Depth: 50 + US Integration Depth, clipped to [0, 100]."""
        df = build_composite(axis_balance=1.0)
        for _, row in df.iterrows():
            if pd.notna(row["us_integration_depth"]):
                expected = max(0, min(100, 50 + row["us_integration_depth"]))
                assert row["net_alignment_score"] == pytest.approx(expected)

    def test_scenario_never_mutates_curated_csvs_on_disk(self, tmp_path):
        """A regression guard: scenario overrides operate purely in memory on
        DataFrames built fresh each call -- running one must not write
        anything back to data/curated/."""
        import os

        curated_dir = Path(__file__).resolve().parents[1] / "data" / "curated"
        before = {f: os.path.getmtime(curated_dir / f) for f in os.listdir(curated_dir)}
        build_composite(tier_weight=99, investment_weight=1, compute_weight=1, axis_balance=0.1)
        after = {f: os.path.getmtime(curated_dir / f) for f in os.listdir(curated_dir)}
        assert before == after


class TestAppendHistorySnapshot:
    """Covers append_history_snapshot() -- the mechanism that lets Score
    Momentum/trend features be built honestly later instead of fabricated
    now (see PROGRESS.md)."""

    def test_creates_file_with_expected_columns(self, tmp_path):
        from scoring import append_history_snapshot

        result = build_composite()
        history_path = tmp_path / "history.csv"
        append_history_snapshot(result, history_path)

        assert history_path.exists()
        df = pd.read_csv(history_path)
        assert set(df.columns) == {"snapshot_date", "country", "iso3", "us_integration_depth", "china_exposure_depth", "net_alignment_score"}
        assert len(df) == len(COUNTRIES)

    def test_same_day_rerun_replaces_not_duplicates(self, tmp_path):
        from scoring import append_history_snapshot

        result = build_composite()
        history_path = tmp_path / "history.csv"
        append_history_snapshot(result, history_path)
        append_history_snapshot(result, history_path)  # same day, re-run

        df = pd.read_csv(history_path)
        assert len(df) == len(COUNTRIES)  # not 2x

    def test_different_day_appends(self, tmp_path, monkeypatch):
        import datetime as real_datetime

        import scoring as scoring_module

        result = build_composite()
        history_path = tmp_path / "history.csv"

        class _FixedDate(real_datetime.date):
            _today = real_datetime.date(2026, 1, 1)

            @classmethod
            def today(cls):
                return cls._today

        monkeypatch.setattr(scoring_module.datetime, "date", _FixedDate)
        scoring_module.append_history_snapshot(result, history_path)

        _FixedDate._today = real_datetime.date(2026, 2, 1)
        scoring_module.append_history_snapshot(result, history_path)

        df = pd.read_csv(history_path)
        assert len(df) == len(COUNTRIES) * 2
        assert set(df["snapshot_date"]) == {"2026-01-01", "2026-02-01"}
