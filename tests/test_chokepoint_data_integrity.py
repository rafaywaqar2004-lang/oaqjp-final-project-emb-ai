import pandas as pd

CHOKEPOINTS = pd.read_csv("data/curated/chokepoints.csv")
CABLE_STATIONS = pd.read_csv("data/curated/cable_landing_stations.csv")
AI_HUBS = pd.read_csv("data/curated/ai_hubs.csv")


def test_chokepoints_have_source_urls():
    for col in ["coordinate_source_url", "significance_source_url"]:
        assert CHOKEPOINTS[col].notna().all()
        assert (CHOKEPOINTS[col].str.startswith("http")).all()


def test_chokepoints_coordinates_in_valid_range():
    assert CHOKEPOINTS["lat"].between(-90, 90).all()
    assert CHOKEPOINTS["lon"].between(-180, 180).all()


def test_no_duplicate_chokepoint_ids():
    assert CHOKEPOINTS["chokepoint_id"].is_unique


def test_cable_stations_have_source_or_explicit_cross_reference():
    # Tartus and Barka intentionally point back to ai_hubs.csv instead of
    # duplicating a URL (they're the same site already cited there) --
    # everything else must carry its own source_url.
    cross_referenced = {"tartus_syr", "barka_omn"}
    for _, row in CABLE_STATIONS.iterrows():
        if row["station_id"] in cross_referenced:
            continue
        assert isinstance(row["source_url"], str) and row["source_url"].startswith("http")


def test_cable_stations_cross_referenced_rows_exist_in_ai_hubs():
    cross_referenced_countries = {"Syria", "Oman"}
    for country in cross_referenced_countries:
        assert (AI_HUBS["country"] == country).any()
