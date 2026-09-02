"""
Lightweight, dependency-free choropleth renderer.

Plotly's built-in geo trace (`go.Choropleth` / `px.choropleth`) fetches its
world-atlas topojson from `cdn.plot.ly` at render time -- even when a custom
GeoJSON is supplied and the base layer is set invisible, in the Plotly.js
version this project runs against. That is an external runtime dependency
this project deliberately avoids (the brief ruled out ArcGIS for the same
reason: no external auth/network dependency to keep this running reliably
on Render). This module draws country polygons directly as filled
`go.Scatter` shapes in plain lon/lat Cartesian space instead of using
Plotly's geo subplot machinery, so the map has zero runtime network calls.
"""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.colors import sample_colorscale


def _polygon_rings(geometry: dict) -> list[list[list[float]]]:
    """Return a flat list of exterior rings (lon/lat coordinate lists) for a
    Polygon or MultiPolygon geometry. Interior holes are dropped -- fine at
    the scale/precision this map is drawn at."""
    gtype = geometry["type"]
    coords = geometry["coordinates"]
    if gtype == "Polygon":
        return [coords[0]]
    if gtype == "MultiPolygon":
        return [poly[0] for poly in coords]
    raise ValueError(f"Unsupported geometry type: {gtype}")


def build_choropleth_figure(
    geojson: dict,
    scores: dict[str, float],
    hover_text: dict[str, str],
    colorscale: list[str],
    value_range: tuple[float, float] = (0, 100),
    missing_color: str = "#d0d0d0",
    context_ids: frozenset[str] = frozenset(),
    context_color: str = "#eeede6",
    context_line_color: str = "#c3c0b3",
) -> go.Figure:
    """
    geojson: FeatureCollection with each feature's `id` matching the keys of `scores`/`hover_text`.
    scores: {feature_id: numeric value or None}
    hover_text: {feature_id: hover label}
    context_ids: feature ids rendered as muted geographic context (e.g. neighboring countries not
        tracked by this index at all) rather than "tracked but missing data" -- a lighter fill and a
        softer border than `missing_color`, so a reader doesn't read them as data gaps.
    """
    lo, hi = value_range
    fig = go.Figure()

    for feature in geojson["features"]:
        fid = feature["id"]
        is_context = fid in context_ids
        value = scores.get(fid)
        if is_context:
            color, line_color, line_width = context_color, context_line_color, 0.5
        else:
            color = missing_color if value is None else sample_colorscale(colorscale, [(value - lo) / (hi - lo)])[0]
            line_color, line_width = "#333333", 0.7
        rings = _polygon_rings(feature["geometry"])
        for i, ring in enumerate(rings):
            lons = [pt[0] for pt in ring]
            lats = [pt[1] for pt in ring]
            fig.add_trace(
                go.Scatter(
                    x=lons,
                    y=lats,
                    mode="lines",
                    fill="toself",
                    fillcolor=color,
                    line=dict(color=line_color, width=line_width),
                    hoverinfo="text",
                    text=hover_text.get(fid, fid),
                    name=hover_text.get(fid, fid),
                    showlegend=False,
                )
            )

    # Invisible marker trace purely to render a shared colorbar legend.
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(
                colorscale=colorscale,
                cmin=lo,
                cmax=hi,
                color=[lo],
                showscale=True,
                colorbar=dict(title="0=China-leaning<br>100=US-integrated", len=0.8),
                size=0.1,
            ),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig.update_xaxes(visible=False, showgrid=False, zeroline=False)
    fig.update_yaxes(visible=False, showgrid=False, zeroline=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=460,
    )
    return fig
