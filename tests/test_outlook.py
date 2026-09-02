import pandas as pd
import pytest

from constants import COUNTRIES
from outlook_engine import build_outlook
from scoring import build_composite
from watch_next import load_watch_indicators, watch_items_for


@pytest.fixture(scope="module")
def composite():
    return build_composite()


@pytest.fixture(scope="module")
def indicators():
    return load_watch_indicators()


@pytest.mark.parametrize("country", list(COUNTRIES.keys()))
def test_every_country_produces_a_full_outlook(country, composite, indicators):
    row = composite[composite["country"] == country].iloc[0]
    country_items = watch_items_for(indicators, country=country)
    country_items = country_items[country_items["scope"] == country]
    outlook = build_outlook(row, country_items)

    assert outlook.country == country
    assert outlook.base_case.probability in {"Likely", "Possible", "Unlikely", "N/A"}
    assert outlook.alternative_case.probability in {"Likely", "Possible", "Unlikely", "N/A"}
    assert outlook.base_case.label == "ANALYST JUDGMENT"
    assert outlook.alternative_case.label == "ANALYST JUDGMENT"


def test_country_with_no_watch_items_gets_na_alternative(composite, indicators):
    row = composite[composite["country"] == "Qatar"].iloc[0]
    empty = pd.DataFrame(columns=indicators.columns)
    outlook = build_outlook(row, empty)
    assert outlook.alternative_case.probability == "N/A"
    assert outlook.base_case.probability == "Likely"
    assert "no country-specific pending" in outlook.base_case.evidence.lower() or "no known" in outlook.base_case.evidence.lower() or "no country-specific" in outlook.base_case.evidence.lower() or "absence" in outlook.base_case.evidence.lower()


def test_country_with_a_watch_item_builds_alternative_from_it(composite, indicators):
    row = composite[composite["country"] == "Egypt"].iloc[0]
    country_items = indicators[indicators["scope"] == "Egypt"]
    assert not country_items.empty, "test assumes Egypt has a watch item on file"
    outlook = build_outlook(row, country_items)
    assert country_items.iloc[0]["indicator"] in outlook.alternative_case.assessment


def test_current_position_reflects_the_real_composite_score(composite, indicators):
    row = composite[composite["country"] == "Saudi Arabia"].iloc[0]
    empty = pd.DataFrame(columns=indicators.columns)
    outlook = build_outlook(row, empty)
    assert f"{row['net_alignment_score']:.0f}" in outlook.current_position_label


def test_never_reports_a_fabricated_numeric_probability():
    """Probability must always be one of the fixed qualitative labels --
    never a numeric percentage, which would imply a precision this
    project's data doesn't support."""
    row = pd.Series({
        "country": "Testland", "net_alignment_score": 50.0,
        "us_integration_depth": 50.0, "china_exposure_depth": 50.0,
    })
    empty = pd.DataFrame(columns=["indicator", "scope", "why_it_matters", "current_signal", "direction", "confidence", "source_ref"])
    outlook = build_outlook(row, empty)
    assert outlook.base_case.probability in {"Likely", "Possible", "Unlikely", "N/A"}
    assert not any(char.isdigit() for char in outlook.base_case.probability)


def test_handles_missing_net_alignment_score():
    row = pd.Series({
        "country": "Testland", "net_alignment_score": float("nan"),
        "us_integration_depth": float("nan"), "china_exposure_depth": float("nan"),
    })
    empty = pd.DataFrame(columns=["indicator", "scope", "why_it_matters", "current_signal", "direction", "confidence", "source_ref"])
    outlook = build_outlook(row, empty)
    assert "insufficient" in outlook.current_position_label.lower()
