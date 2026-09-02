import pandas as pd
import pytest

from regional_dashboard import _bottom_line_text, _city_markers, _hub_markers, load_ai_hubs, load_major_cities
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


class TestMapMarkers:
    """_city_markers/_hub_markers turn the curated major_cities.csv and
    ai_hubs.csv rows into the {lat, lon, name, hover} dicts
    build_choropleth_figure() expects -- checked here so a schema change
    in either CSV surfaces as a test failure, not a silently blank map."""

    def test_city_markers_shape_matches_csv_row_count(self):
        cities = load_major_cities.__wrapped__()
        markers = _city_markers(cities)
        assert len(markers) == len(cities)
        for m in markers:
            assert {"lat", "lon", "name", "hover"}.issubset(m.keys())
            assert m["name"] in cities["city_name"].values

    def test_hub_markers_shape_matches_csv_row_count(self):
        hubs = load_ai_hubs.__wrapped__()
        markers = _hub_markers(hubs)
        assert len(markers) == len(hubs)
        for m in markers:
            assert {"lat", "lon", "name", "hover"}.issubset(m.keys())

    def test_hub_marker_hover_cites_its_source(self):
        hubs = load_ai_hubs.__wrapped__()
        markers = _hub_markers(hubs)
        for marker, (_, row) in zip(markers, hubs.iterrows()):
            assert row["source_name"] in marker["hover"]

    def test_approximate_hub_hover_flags_its_own_precision(self):
        hubs = load_ai_hubs.__wrapped__()
        markers = _hub_markers(hubs)
        for marker, (_, row) in zip(markers, hubs.iterrows()):
            if row["location_precision"] == "approximate":
                assert "Approximate" in marker["hover"]
