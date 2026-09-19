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

# Each of the 3 marker layers (chokepoints, cable stations, hubs) is drawn
# as a halo trace + the real marker trace -- see build_exposure_figure's
# own _halo() helper.
_MARKER_TRACE_COUNT = 3 * 2


def test_figure_builds_with_buffers():
    fig = build_exposure_figure(_HUBS, _CHOKEPOINTS, _CABLE_STATIONS, show_buffers=True)
    # 3 buffer rings (1 chokepoint x 3 radii) + the 6 halo/marker traces
    assert len(fig.data) == 3 + _MARKER_TRACE_COUNT


def test_figure_builds_without_buffers():
    fig = build_exposure_figure(_HUBS, _CHOKEPOINTS, _CABLE_STATIONS, show_buffers=False)
    assert len(fig.data) == _MARKER_TRACE_COUNT


def test_hub_marker_trace_uses_star_symbol():
    fig = build_exposure_figure(_HUBS, _CHOKEPOINTS, _CABLE_STATIONS, show_buffers=False)
    hub_trace = fig.data[-1]  # halos are added immediately before each real marker trace
    assert hub_trace.marker.symbol == "star"
    assert list(hub_trace.x) == [55.0]
    assert list(hub_trace.y) == [25.0]


def test_missing_basemap_file_does_not_add_a_layout_image(monkeypatch, tmp_path):
    """When static/chokepoint_basemap.png hasn't been generated yet (e.g. a
    fresh clone before running generate_qgis_basemap.py), the figure should
    still build -- just without a background image -- not raise."""
    import chokepoint_mapping as cm

    monkeypatch.setattr(cm, "BASEMAP_PATH", tmp_path / "does-not-exist.png")
    fig = build_exposure_figure(_HUBS, _CHOKEPOINTS, _CABLE_STATIONS, show_buffers=False)
    assert len(fig.layout.images) == 0


def test_real_basemap_file_is_added_as_a_layout_image():
    """When the real, checked-in basemap exists, it should be attached as a
    background image at the same lon/lat extent the data traces use."""
    import chokepoint_mapping as cm

    fig = build_exposure_figure(_HUBS, _CHOKEPOINTS, _CABLE_STATIONS, show_buffers=False)
    if not cm.BASEMAP_PATH.exists():
        return  # not generated in this environment -- covered by the missing-file test above
    assert len(fig.layout.images) == 1
    image = fig.layout.images[0]
    assert image.source.startswith("data:image/png;base64,")
    assert image.x == cm.BASEMAP_LON_RANGE[0]
    assert image.y == cm.BASEMAP_LAT_RANGE[1]
