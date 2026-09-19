"""Builds the chokepoint exposure figure: AI hubs, chokepoints, cable landing
stations, and geodesic buffer rings, all drawn as plain plotly go.Scatter
traces in lon/lat Cartesian space.

Deliberately not folium/Leaflet: this project's existing map (mapping.py)
already ruled out any renderer with a runtime CDN/network dependency, to
keep it reliably self-contained on Render -- see that module's own
docstring. This follows the same constraint at render time.

The buffer rings themselves are real QGIS output, not computed here or at
request time: src/data_pipeline/generate_qgis_geodata.py runs PyQGIS's own
QgsGeometry.buffer() engine (offline, via QGIS installed locally) and
writes data/computed/qgis_chokepoint_buffers.geojson, which this module
just reads and draws -- the standard GIS pattern of doing heavy
geoprocessing once and serving the precomputed result. geo_analysis.py's
pyproj-based geodesic_buffer_ring() is kept only as a fallback for tests
that don't have the QGIS file on hand, and as the independently-computed
value tests/test_qgis_geodata.py checks the QGIS output against.
"""
from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd

from geo_analysis import geodesic_buffer_ring
from ui import BLUE, GOLD, GREEN, RED

CHOKEPOINT_COLORS = {
    "hormuz": RED,
    "bab_el_mandeb": "#8e44ad",
    "suez_canal": BLUE,
}

BUFFER_RADII_KM = [250, 500, 1000]


def _country_outline_traces(geojson: dict) -> list[go.Scatter]:
    """Faint country outlines for geographic orientation, reusing the same
    data/geo/region_countries.geojson the Regional Dashboard's own map
    already draws from -- not a new data source, just a lighter render of
    an already-verified layer, purely for reference (no fill/hover)."""
    traces = []
    for feature in geojson["features"]:
        geometry = feature["geometry"]
        rings = [geometry["coordinates"][0]] if geometry["type"] == "Polygon" else [poly[0] for poly in geometry["coordinates"]]
        for ring in rings:
            traces.append(
                go.Scatter(
                    x=[pt[0] for pt in ring],
                    y=[pt[1] for pt in ring],
                    mode="lines",
                    line=dict(color="#c3c0b3", width=0.7),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
    return traces


def _buffer_ring_coords(chokepoint_row, radius_km: float, qgis_buffers: dict | None) -> tuple[list[float], list[float]]:
    if qgis_buffers is not None:
        for feature in qgis_buffers["features"]:
            props = feature["properties"]
            if props["chokepoint_id"] == chokepoint_row["chokepoint_id"] and props["radius_km"] == radius_km:
                coords = feature["geometry"]["coordinates"][0]
                return [pt[0] for pt in coords], [pt[1] for pt in coords]
        raise KeyError(f"No QGIS buffer ring found for {chokepoint_row['chokepoint_id']} at {radius_km}km")
    return geodesic_buffer_ring(chokepoint_row["lon"], chokepoint_row["lat"], radius_km)


def build_exposure_figure(
    hubs: pd.DataFrame,
    chokepoints: pd.DataFrame,
    cable_stations: pd.DataFrame,
    show_buffers: bool = True,
    geojson: dict | None = None,
    qgis_buffers: dict | None = None,
) -> go.Figure:
    """qgis_buffers: the FeatureCollection loaded from
    data/computed/qgis_chokepoint_buffers.geojson (real QGIS output). When
    omitted -- e.g. in a unit test that doesn't need the actual file -- the
    buffer rings fall back to a live pyproj computation instead.
    """
    fig = go.Figure()

    if geojson is not None:
        for trace in _country_outline_traces(geojson):
            fig.add_trace(trace)

    if show_buffers:
        for _, cp in chokepoints.iterrows():
            color = CHOKEPOINT_COLORS.get(cp["chokepoint_id"], "#555555")
            for radius_km in BUFFER_RADII_KM:
                lons, lats = _buffer_ring_coords(cp, radius_km, qgis_buffers)
                fig.add_trace(
                    go.Scatter(
                        x=lons,
                        y=lats,
                        mode="lines",
                        fill="toself",
                        fillcolor=color,
                        opacity=0.06,
                        line=dict(color=color, width=1),
                        hoverinfo="text",
                        text=f"{cp['name']} -- {radius_km}km geodesic buffer (QGIS-generated)",
                        name=f"{cp['name']} {radius_km}km",
                        showlegend=False,
                    )
                )

    fig.add_trace(
        go.Scatter(
            x=chokepoints["lon"],
            y=chokepoints["lat"],
            mode="markers",
            marker=dict(
                size=16,
                symbol="triangle-up",
                color=[CHOKEPOINT_COLORS.get(cid, "#555555") for cid in chokepoints["chokepoint_id"]],
                line=dict(width=1, color="white"),
            ),
            hoverinfo="text",
            hovertext=[f"<b>{row['name']}</b><br>{row['description']}<br><br><i>{row['significance']}</i>" for _, row in chokepoints.iterrows()],
            name="Chokepoints",
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=cable_stations["lon"],
            y=cable_stations["lat"],
            mode="markers",
            marker=dict(size=8, symbol="circle", color=GREEN, line=dict(width=1, color="white")),
            hoverinfo="text",
            hovertext=[
                f"<b>{row['name']}, {row['country']}</b><br>Cable systems: {row['cable_systems']}<br>Operator: {row['operator']}"
                for _, row in cable_stations.iterrows()
            ],
            name="Cable landing stations",
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=hubs["lon"],
            y=hubs["lat"],
            mode="markers",
            marker=dict(size=11, symbol="star", color=GOLD, line=dict(width=1, color="white")),
            hoverinfo="text",
            hovertext=[
                f"<b>{row['hub_name']}</b> ({row['country']})<br>{row['label']}<br>{row.get('amount_label', '')}"
                for _, row in hubs.iterrows()
            ],
            name="AI infrastructure hubs",
            showlegend=False,
        )
    )

    fig.update_xaxes(visible=False, showgrid=False, zeroline=False, range=[20, 70])
    fig.update_yaxes(visible=False, showgrid=False, zeroline=False, scaleanchor="x", scaleratio=1, range=[5, 42])
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=560,
    )
    return fig
