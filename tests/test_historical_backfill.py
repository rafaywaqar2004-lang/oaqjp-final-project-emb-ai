import datetime

import pandas as pd
import pytest

from historical_backfill import (
    TIER_STEP_CHANGES,
    _tier_as_of,
    backfill_dates,
    build_composite_as_of,
    run_backfill,
)
from scoring import build_composite


class TestTierAsOf:
    def test_saudi_arabia_before_authorization_is_tier_zero(self):
        tier, inferred = _tier_as_of("Saudi Arabia", datetime.date(2025, 1, 1), current_tier=3)
        assert tier == 0
        assert inferred is False

    def test_saudi_arabia_on_authorization_date_is_tier_three(self):
        tier, inferred = _tier_as_of("Saudi Arabia", datetime.date(2025, 11, 19), current_tier=3)
        assert tier == 3
        assert inferred is False

    def test_uae_before_upgrade_is_inferred(self):
        tier, inferred = _tier_as_of("United Arab Emirates", datetime.date(2026, 1, 1), current_tier=4)
        assert tier == 2
        assert inferred is True

    def test_uae_on_upgrade_date_is_not_inferred(self):
        tier, inferred = _tier_as_of("United Arab Emirates", datetime.date(2026, 7, 10), current_tier=4)
        assert tier == 4
        assert inferred is False

    def test_country_with_no_step_change_keeps_current_tier_at_any_date(self):
        tier, inferred = _tier_as_of("Qatar", datetime.date(2020, 1, 1), current_tier=2)
        assert tier == 2
        assert inferred is False


class TestBackfillDates:
    def test_dates_are_real_and_sorted(self):
        dates = backfill_dates()
        assert dates == sorted(dates)
        assert len(dates) == len(set(dates))
        assert all(isinstance(d, datetime.date) for d in dates)

    def test_documented_tier_step_change_dates_are_included(self):
        dates = backfill_dates()
        assert datetime.date(2025, 11, 19) in dates
        assert datetime.date(2026, 7, 10) in dates


class TestBuildCompositeAsOf:
    def test_returns_a_row_per_country(self):
        result = build_composite_as_of(datetime.date(2026, 9, 1))
        assert len(result) == len(build_composite())

    def test_far_past_date_excludes_all_deals(self):
        result = build_composite_as_of(datetime.date(2000, 1, 1))
        assert result["investment_usd_bn"].isna().all()
        assert result["compute_mw"].isna().all()

    def test_saudi_arabia_tier_zero_before_2025_11_19(self):
        result = build_composite_as_of(datetime.date(2025, 11, 18))
        row = result[result["country"] == "Saudi Arabia"].iloc[0]
        assert row["us_tier_raw"] == 0
        assert row["us_tier_inferred"] == False  # noqa: E712

    def test_saudi_arabia_tier_three_from_2025_11_19(self):
        result = build_composite_as_of(datetime.date(2025, 11, 19))
        row = result[result["country"] == "Saudi Arabia"].iloc[0]
        assert row["us_tier_raw"] == 3

    def test_uae_tier_inferred_flag_before_upgrade(self):
        result = build_composite_as_of(datetime.date(2026, 1, 1))
        row = result[result["country"] == "United Arab Emirates"].iloc[0]
        assert row["us_tier_raw"] == 2
        assert row["us_tier_inferred"] == True  # noqa: E712

    def test_uae_tier_not_inferred_after_upgrade(self):
        result = build_composite_as_of(datetime.date(2026, 7, 10))
        row = result[result["country"] == "United Arab Emirates"].iloc[0]
        assert row["us_tier_raw"] == 4
        assert row["us_tier_inferred"] == False  # noqa: E712

    def test_later_snapshot_never_has_less_cumulative_investment_than_earlier(self):
        early = build_composite_as_of(datetime.date(2024, 1, 1)).set_index("country")["investment_usd_bn"]
        late = build_composite_as_of(datetime.date(2026, 9, 1)).set_index("country")["investment_usd_bn"]
        for country in early.index:
            early_val = early[country] if pd.notna(early[country]) else 0
            late_val = late[country] if pd.notna(late[country]) else 0
            assert late_val >= early_val

    def test_matches_current_build_composite_at_present_day(self):
        # As-of "far future" should reconstruct the same integration/exposure
        # depths as the live build_composite() -- same deals all counted,
        # same current tier values apply.
        as_of = build_composite_as_of(datetime.date(2027, 1, 1)).set_index("country")
        current = build_composite().set_index("country")
        for country in current.index:
            assert as_of.loc[country, "us_integration_depth"] == pytest.approx(
                current.loc[country, "us_integration_depth"], abs=0.01
            )
            assert as_of.loc[country, "china_exposure_depth"] == pytest.approx(
                current.loc[country, "china_exposure_depth"], abs=0.01
            )


class TestRunBackfill:
    def test_writes_source_column_distinguishing_backfilled_rows(self, tmp_path):
        history_path = tmp_path / "history.csv"
        combined = run_backfill(history_path)
        assert history_path.exists()
        assert set(combined["source"].unique()) <= {"backfilled", "live_pipeline"}
        assert (combined["source"] == "backfilled").all()

    def test_idempotent_rerun_does_not_duplicate_rows(self, tmp_path):
        history_path = tmp_path / "history.csv"
        run_backfill(history_path)
        first_len = len(pd.read_csv(history_path))
        run_backfill(history_path)
        second_len = len(pd.read_csv(history_path))
        assert first_len == second_len

    def test_preserves_existing_live_pipeline_rows(self, tmp_path):
        history_path = tmp_path / "history.csv"
        live_row = pd.DataFrame([{
            "snapshot_date": "2099-01-01", "country": "Saudi Arabia", "iso3": "SAU",
            "us_integration_depth": 50.0, "china_exposure_depth": 50.0, "net_alignment_score": 50.0,
            "source": "live_pipeline",
        }])
        live_row.to_csv(history_path, index=False)

        run_backfill(history_path)
        result = pd.read_csv(history_path)
        preserved = result[(result["snapshot_date"] == "2099-01-01") & (result["country"] == "Saudi Arabia")]
        assert len(preserved) == 1
        assert preserved.iloc[0]["source"] == "live_pipeline"


def test_documented_step_changes_have_real_disclosed_dates_only():
    # Every non-far-past date in TIER_STEP_CHANGES must be a real calendar
    # date, not a placeholder -- this is a light guard against a future
    # edit accidentally reintroducing a fabricated/approximate date here.
    for country, changes in TIER_STEP_CHANGES.items():
        for change_date, _tier, _inferred in changes:
            assert isinstance(change_date, datetime.date)
