import pandas as pd
import pytest

from constants import COUNTRIES
from country_brief import load_curated
from scoring import build_composite
from strategic_risk_engine import RISK_LEVELS, assess_all, assess_country


@pytest.fixture(scope="module")
def composite():
    return build_composite()


@pytest.fixture(scope="module")
def curated():
    return load_curated()


@pytest.mark.parametrize("country", list(COUNTRIES.keys()))
def test_every_country_gets_four_dimensions(country, composite, curated):
    row = composite[composite["country"] == country].iloc[0]
    dims = assess_country(row, curated)
    assert len(dims) == 4
    names = {d.name for d in dims}
    assert names == {"US Policy Exposure", "China Exposure", "Infrastructure Execution Risk", "Measurement Confidence Risk"}


@pytest.mark.parametrize("country", list(COUNTRIES.keys()))
def test_every_dimension_has_a_recognized_level_and_real_basis(country, composite, curated):
    row = composite[composite["country"] == country].iloc[0]
    for d in assess_country(row, curated):
        assert d.level in RISK_LEVELS
        assert isinstance(d.basis, str) and len(d.basis) > 10


def test_high_tier_country_shows_high_us_policy_exposure(composite, curated):
    """UAE holds this dataset's most favorable disclosed bilateral tier
    (4/5) -- it should show the most, not the least, exposure to a future
    US policy reversal."""
    row = composite[composite["country"] == "United Arab Emirates"].iloc[0]
    dims = {d.name: d for d in assess_country(row, curated)}
    assert dims["US Policy Exposure"].level == "High"


def test_no_tier_country_shows_low_us_policy_exposure(composite, curated):
    row = composite[composite["country"] == "Yemen"].iloc[0]
    dims = {d.name: d for d in assess_country(row, curated)}
    assert dims["US Policy Exposure"].level == "Low"


def test_country_with_no_deals_on_file_gets_insufficient_execution_risk(composite, curated):
    row = composite[composite["country"] == "Kuwait"].iloc[0]
    dims = {d.name: d for d in assess_country(row, curated)}
    assert dims["Infrastructure Execution Risk"].level == "Insufficient data"


def test_country_with_only_under_development_deals_gets_high_execution_risk(composite, curated):
    """UAE's only two counted compute deals (Stargate phase 1, Khazna
    expansion) are both under_development -- 100% not-yet-built should
    read as High execution risk, not Low."""
    row = composite[composite["country"] == "United Arab Emirates"].iloc[0]
    dims = {d.name: d for d in assess_country(row, curated)}
    assert dims["Infrastructure Execution Risk"].level == "High"


def test_never_fabricates_a_rating_for_missing_data():
    """A country with no scored tier and no curated rows at all must
    report Insufficient data on every dimension it can't support, never
    guess a plausible-looking rating."""
    row = pd.Series({
        "country": "Testland", "us_tier_raw": float("nan"), "china_exposure_depth": float("nan"),
    })
    empty = pd.DataFrame(columns=["country", "confidence"])
    empty_deals = pd.DataFrame(columns=["country", "counted_in_score", "capacity_mw", "status"])
    curated_empty = {"tier": empty, "china": empty, "china_digital": empty, "compute": empty_deals, "investment": empty_deals}
    dims = {d.name: d for d in assess_country(row, curated_empty)}
    assert dims["US Policy Exposure"].level == "Insufficient data"
    assert dims["China Exposure"].level == "Insufficient data"
    assert dims["Infrastructure Execution Risk"].level == "Insufficient data"
    assert dims["Measurement Confidence Risk"].level == "Insufficient data"


def test_assess_all_returns_one_row_per_country(composite, curated):
    df = assess_all(composite, curated)
    assert len(df) == len(composite)
    assert set(df["Country"]) == set(composite["country"])
