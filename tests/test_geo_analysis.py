import pandas as pd
import pytest

from geo_analysis import (
    compute_hub_chokepoint_distances,
    country_concentration,
    exposure_band,
    geodesic_buffer_ring,
    geodesic_distance_km,
    nearest_chokepoint_per_hub,
)


def test_geodesic_distance_zero_for_same_point():
    assert geodesic_distance_km(50.0, 25.0, 50.0, 25.0) == pytest.approx(0.0, abs=1e-6)


def test_geodesic_distance_known_value():
    # London Heathrow to Paris CDG is a well-documented ~344km great-circle distance.
    lhr = (-0.4543, 51.4700)
    cdg = (2.5479, 49.0097)
    dist = geodesic_distance_km(lhr[0], lhr[1], cdg[0], cdg[1])
    assert 335 < dist < 355


def test_geodesic_distance_symmetric():
    a = geodesic_distance_km(56.5, 26.6, 43.333, 12.583)
    b = geodesic_distance_km(43.333, 12.583, 56.5, 26.6)
    assert a == pytest.approx(b, rel=1e-9)


def test_geodesic_buffer_ring_points_at_correct_radius():
    lon, lat, radius_km = 50.0, 25.0, 500.0
    lons, lats = geodesic_buffer_ring(lon, lat, radius_km, n_points=36)
    for ring_lon, ring_lat in list(zip(lons, lats))[:-1]:
        d = geodesic_distance_km(lon, lat, ring_lon, ring_lat)
        assert d == pytest.approx(radius_km, rel=1e-2)


def test_geodesic_buffer_ring_is_closed():
    lons, lats = geodesic_buffer_ring(50.0, 25.0, 300.0, n_points=8)
    assert lons[0] == pytest.approx(lons[-1])
    assert lats[0] == pytest.approx(lats[-1])


@pytest.mark.parametrize(
    "distance_km,expected_band",
    [
        (0, "Within 250km"),
        (249.9, "Within 250km"),
        (250, "250-500km"),
        (499.9, "250-500km"),
        (500, "500-1000km"),
        (999.9, "500-1000km"),
        (1000, "Over 1000km"),
        (5000, "Over 1000km"),
    ],
)
def test_exposure_band_thresholds(distance_km, expected_band):
    assert exposure_band(distance_km) == expected_band


@pytest.fixture
def sample_hubs():
    return pd.DataFrame(
        [
            {"hub_name": "Hub A", "country": "CountryX", "lat": 25.0, "lon": 55.0},
            {"hub_name": "Hub B", "country": "CountryX", "lat": 24.0, "lon": 54.0},
            {"hub_name": "Hub C", "country": "CountryY", "lat": 30.0, "lon": 32.0},
        ]
    )


@pytest.fixture
def sample_chokepoints():
    return pd.DataFrame(
        [
            {"chokepoint_id": "cp1", "name": "Chokepoint One", "lat": 26.6, "lon": 56.5},
            {"chokepoint_id": "cp2", "name": "Chokepoint Two", "lat": 30.7, "lon": 32.3},
        ]
    )


def test_compute_hub_chokepoint_distances_shape(sample_hubs, sample_chokepoints):
    result = compute_hub_chokepoint_distances(sample_hubs, sample_chokepoints)
    assert len(result) == len(sample_hubs) * len(sample_chokepoints)
    assert set(result.columns) >= {"hub_name", "country", "chokepoint_name", "distance_km", "exposure_band"}
    assert (result["distance_km"] >= 0).all()


def test_nearest_chokepoint_per_hub_picks_minimum(sample_hubs, sample_chokepoints):
    distances = compute_hub_chokepoint_distances(sample_hubs, sample_chokepoints)
    nearest = nearest_chokepoint_per_hub(distances)
    assert len(nearest) == len(sample_hubs)
    for _, row in nearest.iterrows():
        hub_rows = distances[distances["hub_name"] == row["hub_name"]]
        assert row["distance_km"] == hub_rows["distance_km"].min()


def test_country_concentration_sums_to_total(sample_hubs, sample_chokepoints):
    distances = compute_hub_chokepoint_distances(sample_hubs, sample_chokepoints)
    nearest = nearest_chokepoint_per_hub(distances)
    concentration = country_concentration(nearest)
    for country, group in concentration.groupby("country"):
        assert group["hub_count"].sum() == group["total_hubs"].iloc[0]
        assert group["share"].sum() == pytest.approx(1.0)


def test_real_data_files_load_and_compute():
    hubs = pd.read_csv("data/curated/ai_hubs.csv")
    chokepoints = pd.read_csv("data/curated/chokepoints.csv")
    assert len(hubs) > 0
    assert len(chokepoints) == 3
    distances = compute_hub_chokepoint_distances(hubs, chokepoints)
    assert distances["distance_km"].min() > 0
    assert distances["distance_km"].max() < 20000  # sanity: never more than half Earth's circumference
