"""Builds the chokepoint exposure figure: a real QGIS-rendered basemap with
AI hubs, chokepoints, cable landing stations, and geodesic buffer rings
plotted on top as plotly go.Scatter traces in the same lon/lat Cartesian
space the basemap was rendered at.

Deliberately not folium/Leaflet: this project's existing map (mapping.py)
already ruled out any renderer with a runtime CDN/network dependency, to
keep it reliably self-contained on Render -- see that module's own
docstring. This follows the same constraint at render time.

The basemap itself is a real QGIS render, not Plotly line traces:
src/data_pipeline/generate_qgis_basemap.py renders
data/geo/region_countries.geojson (the same bundled boundaries the
Regional Dashboard's own choropleth uses) via QgsMapSettings +
QgsMapRendererParallelJob, styled in this project's own paper/ink palette,
to static/chokepoint_basemap.png -- anti-aliased polygon fills, not raw
vector outlines. Checked into the repo as a build-time asset; QGIS itself
is not a runtime dependency of the deployed app.

The buffer rings are also real QGIS output, not computed here or at
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

import base64
from pathlib import Path

import plotly.graph_objects as go
import pandas as pd

from geo_analysis import geodesic_buffer_ring
from ui import BLUE, GOLD, GREEN, NAVY, RED

CHOKEPOINT_COLORS = {
    "hormuz": RED,
    "bab_el_mandeb": "#8e44ad",
    "suez_canal": BLUE,
}

BUFFER_RADII_KM = [250, 500, 1000]

# Must match generate_qgis_basemap.py's LON_RANGE/LAT_RANGE exactly, or the
# image will not line up with the data traces plotted on it.
BASEMAP_LON_RANGE = (20, 70)
BASEMAP_LAT_RANGE = (5, 42)
BASEMAP_PATH = Path(__file__).resolve().parents[1] / "static" / "chokepoint_basemap.png"


def _basemap_data_uri() -> str | None:
    """Base64-encodes the QGIS-rendered basemap PNG as a data URI so Plotly
    can place it via add_layout_image without depending on Streamlit's
    static-file serving being configured/reachable -- works identically in
    local dev and production. Returns None if the basemap hasn't been
    generated yet."""
    if not BASEMAP_PATH.exists():
        return None
    encoded = base64.b64encode(BASEMAP_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


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
    qgis_buffers: dict | None = None,
) -> go.Figure:
    """qgis_buffers: the FeatureCollection loaded from
    data/computed/qgis_chokepoint_buffers.geojson (real QGIS output). When
    omitted -- e.g. in a unit test that doesn't need the actual file -- the
    buffer rings fall back to a live pyproj computation instead.
    """
    fig = go.Figure()

    basemap_uri = _basemap_data_uri()
    if basemap_uri is not None:
        fig.add_layout_image(
            dict(
                source=basemap_uri,
                xref="x", yref="y",
                x=BASEMAP_LON_RANGE[0], y=BASEMAP_LAT_RANGE[1],
                sizex=BASEMAP_LON_RANGE[1] - BASEMAP_LON_RANGE[0],
                sizey=BASEMAP_LAT_RANGE[1] - BASEMAP_LAT_RANGE[0],
                xanchor="left", yanchor="top",
                sizing="stretch", layer="below",
            )
        )

    if show_buffers:
        for _, cp in chokepoints.iterrows():
            color = CHOKEPOINT_COLORS.get(cp["chokepoint_id"], "#555555")
            for i, radius_km in enumerate(BUFFER_RADII_KM):
                lons, lats = _buffer_ring_coords(cp, radius_km, qgis_buffers)
                fig.add_trace(
                    go.Scatter(
                        x=lons,
                        y=lats,
                        mode="lines",
                        fill="toself",
                        fillcolor=color,
                        opacity=0.10 if i == 0 else 0.07,
                        line=dict(color=color, width=1.1, dash="solid" if i == 0 else "dot"),
                        hoverinfo="text",
                        text=f"{cp['name']} -- {radius_km}km geodesic buffer (QGIS-generated)",
                        name=f"{cp['name']} {radius_km}km",
                        showlegend=False,
                    )
                )

    # A soft white halo underneath each marker layer -- otherwise a plain
    # white marker outline (the original styling) all but disappears
    # against the basemap's own pale cream/paper land fill.
    def _halo(x, y, size):
        return go.Scatter(
            x=x, y=y, mode="markers",
            marker=dict(size=size, color="rgba(255,255,255,0.85)", line=dict(width=0)),
            hoverinfo="skip", showlegend=False,
        )

    fig.add_trace(_halo(chokepoints["lon"], chokepoints["lat"], 22))
    fig.add_trace(
        go.Scatter(
            x=chokepoints["lon"],
            y=chokepoints["lat"],
            mode="markers",
            marker=dict(
                size=16,
                symbol="triangle-up",
                color=[CHOKEPOINT_COLORS.get(cid, "#555555") for cid in chokepoints["chokepoint_id"]],
                line=dict(width=1.3, color=NAVY),
            ),
            hoverinfo="text",
            hovertext=[f"<b>{row['name']}</b><br>{row['description']}<br><br><i>{row['significance']}</i>" for _, row in chokepoints.iterrows()],
            name="Chokepoints",
            showlegend=False,
        )
    )

    fig.add_trace(_halo(cable_stations["lon"], cable_stations["lat"], 12))
    fig.add_trace(
        go.Scatter(
            x=cable_stations["lon"],
            y=cable_stations["lat"],
            mode="markers",
            marker=dict(size=8, symbol="circle", color=GREEN, line=dict(width=1, color=NAVY)),
            hoverinfo="text",
            hovertext=[
                f"<b>{row['name']}, {row['country']}</b><br>Cable systems: {row['cable_systems']}<br>Operator: {row['operator']}"
                for _, row in cable_stations.iterrows()
            ],
            name="Cable landing stations",
            showlegend=False,
        )
    )

    fig.add_trace(_halo(hubs["lon"], hubs["lat"], 16))
    fig.add_trace(
        go.Scatter(
            x=hubs["lon"],
            y=hubs["lat"],
            mode="markers",
            marker=dict(size=11, symbol="star", color=GOLD, line=dict(width=1, color=NAVY)),
            hoverinfo="text",
            hovertext=[
                f"<b>{row['hub_name']}</b> ({row['country']})<br>{row['label']}<br>{row.get('amount_label', '')}"
                for _, row in hubs.iterrows()
            ],
            name="AI infrastructure hubs",
            showlegend=False,
        )
    )

    fig.update_xaxes(visible=False, showgrid=False, zeroline=False, range=list(BASEMAP_LON_RANGE), constrain="domain")
    fig.update_yaxes(visible=False, showgrid=False, zeroline=False, scaleanchor="x", scaleratio=1, range=list(BASEMAP_LAT_RANGE))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=560,
    )
    return fig
