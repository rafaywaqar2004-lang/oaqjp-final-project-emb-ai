import pandas as pd
import pytest

from data_validation import (
    validate_all,
    validate_confidence_values,
    validate_country_column,
    validate_dates_parseable,
    validate_iso3_consistency,
    validate_no_duplicate_countries,
    validate_non_negative,
    validate_ordinal_range,
    validate_required_columns,
    validate_score_range,
    validate_weights_sum_to_one,
)


def test_repository_data_currently_has_no_validation_issues():
    """The actual curated/computed data in this repo must pass every
    check -- a real regression (a bad edit to a CSV) should fail this
    test, not slip through silently."""
    issues = validate_all()
    errors = [i for i in issues if i.severity == "error"]
    assert errors == [], "\n".join(str(e) for e in errors)


class TestCountryColumn:
    def test_valid_countries_pass(self):
        df = pd.DataFrame({"country": ["Saudi Arabia", "Qatar"]})
        assert validate_country_column(df, "test.csv") == []

    def test_unknown_country_flagged(self):
        df = pd.DataFrame({"country": ["Saudi Arabia", "Narnia"]})
        issues = validate_country_column(df, "test.csv")
        assert len(issues) == 1
        assert "Narnia" in issues[0].message

    def test_allow_extra_permits_a_documented_pseudo_country(self):
        df = pd.DataFrame({"country": ["Saudi Arabia", "GCC region-wide"]})
        assert validate_country_column(df, "test.csv", allow_extra={"GCC region-wide"}) == []

    def test_missing_country_column_is_a_noop(self):
        df = pd.DataFrame({"other": [1, 2]})
        assert validate_country_column(df, "test.csv") == []


class TestIso3Consistency:
    def test_matching_iso3_passes(self):
        df = pd.DataFrame({"country": ["Saudi Arabia"], "iso3": ["SAU"]})
        assert validate_iso3_consistency(df, "test.csv") == []

    def test_mismatched_iso3_flagged(self):
        df = pd.DataFrame({"country": ["Saudi Arabia"], "iso3": ["ARE"]})
        issues = validate_iso3_consistency(df, "test.csv")
        assert len(issues) == 1
        assert "Saudi Arabia" in issues[0].message


class TestNoDuplicateCountries:
    def test_unique_countries_pass(self):
        df = pd.DataFrame({"country": ["Saudi Arabia", "Qatar"]})
        assert validate_no_duplicate_countries(df, "test.csv") == []

    def test_duplicate_flagged(self):
        df = pd.DataFrame({"country": ["Saudi Arabia", "Saudi Arabia"]})
        issues = validate_no_duplicate_countries(df, "test.csv")
        assert len(issues) == 1
        assert "Saudi Arabia" in issues[0].message


class TestOrdinalRange:
    def test_valid_ordinal_passes(self):
        df = pd.DataFrame({"score": [0, 3, 5]})
        assert validate_ordinal_range(df, "score", "test.csv") == []

    def test_out_of_range_flagged(self):
        df = pd.DataFrame({"score": [0, 6, -1]})
        issues = validate_ordinal_range(df, "score", "test.csv")
        assert len(issues) == 1
        assert "6" in issues[0].message

    def test_nan_is_never_flagged_as_out_of_range(self):
        """Missing data (NaN) is a legitimate, honestly-marked state --
        must never be treated the same as an invalid number."""
        df = pd.DataFrame({"score": [0, float("nan"), 5]})
        assert validate_ordinal_range(df, "score", "test.csv") == []


class TestScoreRange:
    def test_valid_score_passes(self):
        df = pd.DataFrame({"net_alignment_score": [0, 50, 100]})
        assert validate_score_range(df, "net_alignment_score", "test.csv") == []

    def test_out_of_range_flagged(self):
        df = pd.DataFrame({"net_alignment_score": [-5, 105]})
        issues = validate_score_range(df, "net_alignment_score", "test.csv")
        assert len(issues) == 1


class TestNonNegative:
    def test_positive_and_zero_pass(self):
        df = pd.DataFrame({"amount_usd_bn": [0, 5.2]})
        assert validate_non_negative(df, "amount_usd_bn", "test.csv") == []

    def test_negative_flagged(self):
        df = pd.DataFrame({"amount_usd_bn": [-1.0]})
        issues = validate_non_negative(df, "amount_usd_bn", "test.csv")
        assert len(issues) == 1


class TestDatesParseable:
    def test_valid_dates_pass(self):
        df = pd.DataFrame({"announced_date": ["2025-01-15", "2026-03-01"]})
        assert validate_dates_parseable(df, "announced_date", "test.csv") == []

    def test_malformed_date_flagged(self):
        df = pd.DataFrame({"announced_date": ["2025-01-15", "not-a-date"]})
        issues = validate_dates_parseable(df, "announced_date", "test.csv")
        assert len(issues) == 1
        assert "not-a-date" in issues[0].message


class TestConfidenceValues:
    def test_recognized_values_pass(self):
        df = pd.DataFrame({"confidence": ["High", "Medium", "Low"]})
        assert validate_confidence_values(df, "test.csv") == []

    def test_unrecognized_value_flagged(self):
        df = pd.DataFrame({"confidence": ["High", "Very High"]})
        issues = validate_confidence_values(df, "test.csv")
        assert len(issues) == 1
        assert "Very High" in issues[0].message


class TestRequiredColumns:
    def test_all_present_passes(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        assert validate_required_columns(df, {"a", "b"}, "test.csv") == []

    def test_missing_column_flagged(self):
        df = pd.DataFrame({"a": [1]})
        issues = validate_required_columns(df, {"a", "b"}, "test.csv")
        assert len(issues) == 1
        assert "b" in issues[0].message


class TestWeightsSumToOne:
    def test_valid_weights_pass(self):
        assert validate_weights_sum_to_one({"a": 0.4, "b": 0.3, "c": 0.3}, "test") == []

    def test_invalid_weights_flagged(self):
        issues = validate_weights_sum_to_one({"a": 0.5, "b": 0.3}, "test")
        assert len(issues) == 1

    def test_this_projects_actual_us_integration_weights_are_valid(self):
        from scoring import US_TIER_WEIGHT, US_INVESTMENT_WEIGHT, US_COMPUTE_WEIGHT
        weights = {"tier": US_TIER_WEIGHT, "investment": US_INVESTMENT_WEIGHT, "compute": US_COMPUTE_WEIGHT}
        assert validate_weights_sum_to_one(weights, "US Integration Depth weights") == []
