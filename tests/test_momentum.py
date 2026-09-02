import pandas as pd
import pytest

from momentum import compute_momentum, load_history, regional_momentum


def _history(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    """rows: (date, country, net_alignment_score) tuples."""
    df = pd.DataFrame(rows, columns=["snapshot_date", "country", "net_alignment_score"])
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    return df


class TestComputeMomentum:
    def test_zero_observations_is_insufficient(self):
        result = compute_momentum(_history([]), "Saudi Arabia")
        assert result.direction == "Insufficient data"
        assert result.n_observations == 0
        assert result.current is None

    def test_one_observation_is_insufficient_but_reports_current(self):
        history = _history([("2026-01-01", "Saudi Arabia", 55.0)])
        result = compute_momentum(history, "Saudi Arabia")
        assert result.direction == "Insufficient data"
        assert result.n_observations == 1
        assert result.current == pytest.approx(55.0)
        assert result.change is None

    def test_two_observations_classify_direction_not_acceleration(self):
        history = _history([
            ("2026-01-01", "Saudi Arabia", 50.0),
            ("2026-02-01", "Saudi Arabia", 58.0),
        ])
        result = compute_momentum(history, "Saudi Arabia")
        assert result.n_observations == 2
        assert result.direction == "Increasing"
        assert result.change == pytest.approx(8.0)
        assert "acceleration cannot be classified" in result.note

    def test_small_change_is_stable(self):
        history = _history([
            ("2026-01-01", "Saudi Arabia", 50.0),
            ("2026-02-01", "Saudi Arabia", 51.0),
        ])
        result = compute_momentum(history, "Saudi Arabia")
        assert result.direction == "Stable"

    def test_three_observations_can_detect_acceleration(self):
        history = _history([
            ("2026-01-01", "Saudi Arabia", 40.0),
            ("2026-02-01", "Saudi Arabia", 45.0),
            ("2026-03-01", "Saudi Arabia", 58.0),
        ])
        result = compute_momentum(history, "Saudi Arabia")
        assert result.n_observations == 3
        assert result.direction == "Accelerating"

    def test_three_observations_can_detect_rapidly_declining(self):
        history = _history([
            ("2026-01-01", "Saudi Arabia", 60.0),
            ("2026-02-01", "Saudi Arabia", 55.0),
            ("2026-03-01", "Saudi Arabia", 40.0),
        ])
        result = compute_momentum(history, "Saudi Arabia")
        assert result.direction == "Rapidly declining"

    def test_slowing_increase_is_just_increasing_not_accelerating(self):
        history = _history([
            ("2026-01-01", "Saudi Arabia", 40.0),
            ("2026-02-01", "Saudi Arabia", 55.0),
            ("2026-03-01", "Saudi Arabia", 60.0),
        ])
        result = compute_momentum(history, "Saudi Arabia")
        assert result.direction == "Increasing"

    def test_country_absent_from_history_is_insufficient(self):
        history = _history([("2026-01-01", "Saudi Arabia", 50.0)])
        result = compute_momentum(history, "Qatar")
        assert result.direction == "Insufficient data"
        assert result.n_observations == 0

    def test_never_fabricates_a_missing_snapshot(self):
        """A country with only 1 of 2 snapshot dates present must not have
        the missing date interpolated or assumed -- it stays insufficient."""
        history = _history([
            ("2026-01-01", "Saudi Arabia", 50.0),
            ("2026-02-01", "Qatar", 40.0),
        ])
        result = compute_momentum(history, "Saudi Arabia")
        assert result.n_observations == 1
        assert result.direction == "Insufficient data"


class TestRegionalMomentum:
    def test_insufficient_with_one_snapshot_date(self):
        history = _history([
            ("2026-01-01", "Saudi Arabia", 50.0),
            ("2026-01-01", "Qatar", 40.0),
        ])
        result = regional_momentum(history)
        assert result.direction == "Insufficient data"
        assert result.n_observations == 1

    def test_two_snapshot_dates_average_correctly(self):
        history = _history([
            ("2026-01-01", "Saudi Arabia", 50.0),
            ("2026-01-01", "Qatar", 30.0),
            ("2026-02-01", "Saudi Arabia", 60.0),
            ("2026-02-01", "Qatar", 40.0),
        ])
        result = regional_momentum(history)
        assert result.n_observations == 2
        assert result.current == pytest.approx(50.0)
        assert result.previous == pytest.approx(40.0)
        assert result.direction == "Increasing"


def test_load_history_returns_empty_frame_for_missing_file(tmp_path):
    missing = tmp_path / "does_not_exist.csv"
    df = load_history(missing)
    assert df.empty
    assert "net_alignment_score" in df.columns


def test_load_history_parses_real_file():
    """Smoke test against the actual repository history file -- must load
    without error and carry a real, parseable snapshot_date column."""
    df = load_history()
    assert not df.empty
    assert pd.api.types.is_datetime64_any_dtype(df["snapshot_date"])
