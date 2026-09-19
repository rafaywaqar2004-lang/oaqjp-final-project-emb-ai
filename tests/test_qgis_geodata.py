"""Validates the checked-in QGIS-generated data (data/computed/qgis_*)
against an independently-implemented pyproj calculation (geo_analysis.py).

This is the test that actually backs the claim "QGIS was used": it proves
the committed QGIS output is internally consistent and matches a second,
independent geodesic implementation -- not just that the files exist. If
someone edits data/curated/ai_hubs.csv or chokepoints.csv without
re-running src/data_pipeline/generate_qgis_geodata.py, this is what catches
the resulting drift.
"""
import json

import pandas as pd
import pytest

from geo_analysis import compute_hub_chokepoint_distances, geodesic_distance_km

QGIS_DISTANCES_PATH = "data/computed/qgis_hub_chokepoint_distances.csv"
QGIS_BUFFERS_PATH = "data/computed/qgis_chokepoint_buffers.geojson"


@pytest.fixture(scope="module")
def qgis_distances():
    return pd.read_csv(QGIS_DISTANCES_PATH)


@pytest.fixture(scope="module")
def qgis_buffers():
    with open(QGIS_BUFFERS_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def pyproj_distances():
    hubs = pd.read_csv("data/curated/ai_hubs.csv")
    chokepoints = pd.read_csv("data/curated/chokepoints.csv")
    return compute_hub_chokepoint_distances(hubs, chokepoints)


def test_qgis_distances_file_has_expected_shape(qgis_distances):
    hubs = pd.read_csv("data/curated/ai_hubs.csv")
    chokepoints = pd.read_csv("data/curated/chokepoints.csv")
    assert len(qgis_distances) == len(hubs) * len(chokepoints)
    assert set(qgis_distances.columns) == {"hub_name", "country", "chokepoint_id", "chokepoint_name", "distance_km"}


def test_qgis_distances_match_independent_pyproj_calculation(qgis_distances, pyproj_distances):
    """The whole point of this test: real QGIS (QgsDistanceArea, ellipsoidal
    WGS84) and an independently-implemented pyproj.Geod calculation should
    agree to well under 1km on every one of these regional-scale (dozens to
    thousands of km) distances -- both ultimately use the WGS84 ellipsoid,
    just via different libraries."""
    merged = qgis_distances.merge(
        pyproj_distances, on=["hub_name", "chokepoint_id"], suffixes=("_qgis", "_pyproj")
    )
    assert len(merged) == len(qgis_distances), "every QGIS row should have a matching pyproj row"
    diff_km = (merged["distance_km_qgis"] - merged["distance_km_pyproj"]).abs()
    assert diff_km.max() < 1.0, f"largest QGIS/pyproj disagreement: {diff_km.max():.3f}km"


def test_qgis_buffer_rings_are_at_the_correct_radius(qgis_buffers):
    """Every point on a generated buffer ring should sit within a small
    tolerance of its stated radius from the chokepoint's own coordinates --
    confirms the azimuthal-equidistant reprojection trick actually produced
    a true geodesic circle, not a distorted ellipse."""
    chokepoints = pd.read_csv("data/curated/chokepoints.csv").set_index("chokepoint_id")
    for feature in qgis_buffers["features"]:
        props = feature["properties"]
        cp = chokepoints.loc[props["chokepoint_id"]]
        radius_km = props["radius_km"]
        coords = feature["geometry"]["coordinates"][0]
        # Sample every 10th point rather than all ~72 for test speed.
        for lon, lat in coords[::10]:
            dist = geodesic_distance_km(cp["lon"], cp["lat"], lon, lat)
            assert dist == pytest.approx(radius_km, rel=0.01), (
                f"{props['chokepoint_id']} {radius_km}km ring point at ({lon:.3f},{lat:.3f}) "
                f"is actually {dist:.1f}km from center"
            )


def test_qgis_buffer_rings_are_closed(qgis_buffers):
    for feature in qgis_buffers["features"]:
        coords = feature["geometry"]["coordinates"][0]
        assert coords[0] == pytest.approx(coords[-1]), "ring should close (first point == last point)"


def test_qgis_buffers_cover_all_chokepoints_and_radii():
    chokepoints = pd.read_csv("data/curated/chokepoints.csv")
    with open(QGIS_BUFFERS_PATH) as f:
        buffers = json.load(f)
    seen = {(f["properties"]["chokepoint_id"], f["properties"]["radius_km"]) for f in buffers["features"]}
    expected = {(cid, r) for cid in chokepoints["chokepoint_id"] for r in (250.0, 500.0, 1000.0)}
    assert seen == expected
