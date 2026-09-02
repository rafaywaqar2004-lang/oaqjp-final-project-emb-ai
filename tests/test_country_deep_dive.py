import pandas as pd
import pytest

from constants import COUNTRIES
from country_deep_dive import _data_quality_summary, _key_drivers_table, _strategic_implications
from country_brief import load_curated
from scoring import build_composite


@pytest.fixture(scope="module")
def composite():
    return build_composite()


@pytest.fixture(scope="module")
def curated():
    return load_curated()


@pytest.mark.parametrize("country", list(COUNTRIES.keys()))
def test_key_drivers_table_has_all_five_components(country, composite, curated):
    row = composite[composite["country"] == country].iloc[0]
    table = _key_drivers_table(row, curated, country)
    assert len(table) == 5
    assert set(table["Axis"]) == {"US Integration Depth", "China Exposure Depth"}
    assert (table["Axis"] == "US Integration Depth").sum() == 3
    assert (table["Axis"] == "China Exposure Depth").sum() == 2


def test_key_drivers_table_missing_raw_value_shows_na(composite, curated):
    """Qatar has no scored investment/compute deals -- those rows must show
    'N/A', never a fabricated number."""
    row = composite[composite["country"] == "Qatar"].iloc[0]
    table = _key_drivers_table(row, curated, "Qatar")
    inv_row = table[table["Component"] == "AI Investment"].iloc[0]
    assert inv_row["Raw Value"] == "N/A"
    assert inv_row["Scored (0-100)"] == "N/A"


def test_key_drivers_confidence_matches_curated_row_via_the_same_mapping_the_rest_of_the_app_uses(composite, curated):
    """Every other confidence label in this app (country_brief.py's
    confidence_pill badges) maps the curated CSVs' raw 'Medium' value to
    the display label 'Moderate' -- this table must use the identical
    mapping, not a raw passthrough, or the same underlying confidence
    would read as two different things on the same page."""
    row = composite[composite["country"] == "Saudi Arabia"].iloc[0]
    table = _key_drivers_table(row, curated, "Saudi Arabia")
    tier_row = table[table["Component"] == "US Export-Control Tier"].iloc[0]
    curated_conf = curated["tier"][curated["tier"]["country"] == "Saudi Arabia"].iloc[0]["confidence"]
    expected = {"High": "High", "Medium": "Moderate", "Low": "Low"}[curated_conf]
    assert tier_row["Confidence"] == expected


def test_key_drivers_never_shows_raw_medium_label(composite, curated):
    """'Medium' is the curated CSVs' raw value -- this table must always
    display the app-wide 'Moderate' label instead, never the raw value."""
    for country in COUNTRIES:
        row = composite[composite["country"] == country].iloc[0]
        table = _key_drivers_table(row, curated, country)
        assert "Medium" not in set(table["Confidence"])


@pytest.mark.parametrize("country", list(COUNTRIES.keys()))
def test_strategic_implications_returns_three_qualified_sections(country, composite):
    row = composite[composite["country"] == country].iloc[0]
    implications = _strategic_implications(row)
    assert set(implications.keys()) == {"policymakers", "investors", "corporates"}
    for text in implications.values():
        assert isinstance(text, str) and len(text) > 20
        # never a buy/sell-style recommendation
        assert "buy" not in text.lower() and "sell" not in text.lower()


def test_strategic_implications_mentions_country_name(composite):
    row = composite[composite["country"] == "Saudi Arabia"].iloc[0]
    implications = _strategic_implications(row)
    assert "Saudi Arabia" in implications["policymakers"]


def test_strategic_implications_handles_missing_axis_data():
    row = pd.Series({
        "country": "Testland", "us_integration_depth": float("nan"), "china_exposure_depth": float("nan"),
        "us_tier_raw": float("nan"), "china_penetration_raw": float("nan"), "net_alignment_score": float("nan"),
    })
    implications = _strategic_implications(row)
    assert "insufficient" in implications["policymakers"].lower()
    assert implications["policymakers"] == implications["investors"] == implications["corporates"]


@pytest.mark.parametrize("country", list(COUNTRIES.keys()))
def test_data_quality_summary_has_four_rows(country, composite, curated):
    row = composite[composite["country"] == country].iloc[0]
    summary = _data_quality_summary(row, curated, country)
    assert len(summary) == 4
    assert "Dimension" in summary.columns and "Value" in summary.columns
