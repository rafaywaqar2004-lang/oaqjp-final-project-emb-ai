import pandas as pd

from chokepoint_mapping import build_exposure_figure

_HUBS = pd.DataFrame(
    [{"hub_name": "Hub A", "country": "CountryX", "lat": 25.0, "lon": 55.0, "label": "Test hub", "amount_label": "$1bn"}]
)
_CHOKEPOINTS = pd.DataFrame(
    [
        {
            "chokepoint_id": "hormuz",
            "name": "Strait of Hormuz",
            "lat": 26.6,
            "lon": 56.5,
            "description": "Test description",
            "significance": "Test significance",
        }
    ]
)
_CABLE_STATIONS = pd.DataFrame(
    [{"name": "Test Station", "country": "CountryX", "lat": 25.5, "lon": 55.5, "cable_systems": "AAE-1", "operator": "Test Operator"}]
)


def test_figure_builds_with_buffers():
    fig = build_exposure_figure(_HUBS, _CHOKEPOINTS, _CABLE_STATIONS, show_buffers=True)
    # 3 buffer rings + chokepoint markers + cable station markers + hub markers
    assert len(fig.data) == 3 + 3


def test_figure_builds_without_buffers():
    fig = build_exposure_figure(_HUBS, _CHOKEPOINTS, _CABLE_STATIONS, show_buffers=False)
    assert len(fig.data) == 3


def test_hub_marker_trace_uses_star_symbol():
    fig = build_exposure_figure(_HUBS, _CHOKEPOINTS, _CABLE_STATIONS, show_buffers=False)
    hub_trace = fig.data[-1]
    assert hub_trace.marker.symbol == "star"
    assert list(hub_trace.x) == [55.0]
    assert list(hub_trace.y) == [25.0]


def test_geojson_adds_outline_traces_without_disturbing_marker_traces():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {"id": "SAU", "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}},
        ],
    }
    fig = build_exposure_figure(_HUBS, _CHOKEPOINTS, _CABLE_STATIONS, show_buffers=False, geojson=geojson)
    assert len(fig.data) == 3 + 1
    hub_trace = fig.data[-1]
    assert hub_trace.marker.symbol == "star"
