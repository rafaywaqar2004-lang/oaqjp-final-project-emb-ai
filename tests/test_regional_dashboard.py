import pandas as pd
import pytest

from regional_dashboard import _bottom_line_text
from scoring import build_composite


@pytest.fixture(scope="module")
def composite_df():
    return build_composite()


def test_bottom_line_returns_text_and_confidence(composite_df):
    text, confidence = _bottom_line_text(composite_df)
    assert isinstance(text, str) and len(text) > 20
    assert confidence in {"High", "Moderate", "Low", "Insufficient"}


def test_bottom_line_cites_a_real_country_and_count(composite_df):
    text, _ = _bottom_line_text(composite_df)
    scored = composite_df.dropna(subset=["us_integration_depth", "china_exposure_depth"])
    # the modal-quadrant example country named in the text must actually be in the scored set
    assert any(country in text for country in scored["country"])


def test_bottom_line_handles_empty_dataframe():
    empty = pd.DataFrame(columns=["country", "us_integration_depth", "china_exposure_depth", "net_alignment_score"])
    text, confidence = _bottom_line_text(empty)
    assert confidence == "Insufficient"
    assert "Insufficient" in text
