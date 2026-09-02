from mapping import build_choropleth_figure

_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {"id": "SAU", "properties": {"name": "Saudi Arabia", "scored": True},
         "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}},
        {"id": "ARE", "properties": {"name": "United Arab Emirates", "scored": True},
         "geometry": {"type": "Polygon", "coordinates": [[[2, 0], [2, 1], [3, 1], [3, 0], [2, 0]]]}},
    ],
}


def _base_kwargs():
    return dict(
        geojson=_GEOJSON,
        scores={"SAU": 60.0, "ARE": None},
        hover_text={"SAU": "Saudi Arabia", "ARE": "UAE"},
        colorscale=["#f0e6c8", "#2463A5"],
    )


def test_figure_builds_without_markers():
    fig = build_choropleth_figure(**_base_kwargs())
    # 2 country polygons + 1 invisible colorbar trace, no marker traces
    assert len(fig.data) == 3


def test_city_markers_add_one_trace():
    markers = [{"lat": 24.7, "lon": 46.7, "name": "Riyadh", "hover": "Riyadh"}]
    fig = build_choropleth_figure(**_base_kwargs(), city_markers=markers)
    assert len(fig.data) == 4
    city_trace = fig.data[2]
    assert list(city_trace.x) == [46.7]
    assert list(city_trace.y) == [24.7]


def test_hub_markers_add_one_trace_with_star_symbol():
    markers = [{"lat": 28.0, "lon": 35.3, "name": "NEOM", "hover": "NEOM hub"}]
    fig = build_choropleth_figure(**_base_kwargs(), hub_markers=markers)
    assert len(fig.data) == 4
    hub_trace = fig.data[2]
    assert hub_trace.marker.symbol == "star"
    assert list(hub_trace.hovertext) == ["NEOM hub"]


def test_city_and_hub_markers_both_render_as_separate_traces():
    city = [{"lat": 24.7, "lon": 46.7, "name": "Riyadh", "hover": "Riyadh"}]
    hub = [{"lat": 28.0, "lon": 35.3, "name": "NEOM", "hover": "NEOM hub"}]
    fig = build_choropleth_figure(**_base_kwargs(), city_markers=city, hub_markers=hub)
    # 2 polygons + city trace + hub trace + colorbar trace
    assert len(fig.data) == 5


def test_empty_marker_lists_add_no_traces():
    fig = build_choropleth_figure(**_base_kwargs(), city_markers=[], hub_markers=[])
    assert len(fig.data) == 3
