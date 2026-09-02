import pandas as pd
import pytest

from watch_next import load_watch_indicators, watch_items_for


@pytest.fixture(scope="module")
def indicators():
    return load_watch_indicators()


def test_loads_real_file_with_expected_columns(indicators):
    expected = {"indicator", "scope", "why_it_matters", "current_signal", "direction", "confidence", "source_ref"}
    assert expected.issubset(set(indicators.columns))
    assert len(indicators) > 0


def test_every_row_has_a_source_ref(indicators):
    for _, row in indicators.iterrows():
        assert isinstance(row["source_ref"], str) and len(row["source_ref"]) > 0


def test_confidence_values_are_recognized(indicators):
    assert set(indicators["confidence"]).issubset({"High", "Medium", "Low"})


def test_watch_items_for_none_returns_only_regional(indicators):
    items = watch_items_for(indicators, country=None)
    assert (items["scope"] == "Regional").all()


def test_watch_items_for_country_includes_country_specific_and_regional(indicators):
    items = watch_items_for(indicators, country="Egypt")
    assert "Egypt" in set(items["scope"])
    assert "Regional" in set(items["scope"])
    # nothing from another country's scope leaks in
    assert set(items["scope"]).issubset({"Egypt", "Regional"})


def test_watch_items_for_country_with_no_specific_items_returns_regional_only():
    indicators = pd.DataFrame([
        {"indicator": "x", "scope": "Regional", "why_it_matters": "y", "current_signal": "z", "direction": "Stable", "confidence": "High", "source_ref": "ref"},
    ])
    items = watch_items_for(indicators, country="Qatar")
    assert len(items) == 1
    assert items.iloc[0]["scope"] == "Regional"
