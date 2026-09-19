"""Geodesic proximity analysis between AI infrastructure hubs (data/curated/
ai_hubs.csv) and physical chokepoints (data/curated/chokepoints.csv --
straits, canals, cable corridors).

Real buffer rings and real geodesic distances computed from verified
coordinates, not an illustrative or fabricated proximity score. Every input
coordinate comes from a curated CSV, each row of which carries its own
source_name/source_url. This module strictly computes "how many kilometres
apart are these two verified points" -- it never invents a traffic-share,
dependency percentage, or precision beyond what the source data states.

Uses pyproj's Geod (WGS84 ellipsoid) for true geodesic distances/buffers --
pure computation, no network calls -- rather than a flat-projection
approximation, which would distort distances unevenly across the 15-45
degree longitude spread the tracked hubs cover.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")

# Distance bands (km) used to classify exposure -- analysis thresholds
# chosen for these buffer rings, not sourced facts. Documented as such on
# the Methodology page.
EXPOSURE_BANDS = [
    (0, 250, "Within 250km"),
    (250, 500, "250-500km"),
    (500, 1000, "500-1000km"),
    (1000, float("inf"), "Over 1000km"),
]


def geodesic_distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """True ellipsoidal (WGS84) distance in km between two lon/lat points."""
    _, _, distance_m = _GEOD.inv(lon1, lat1, lon2, lat2)
    return distance_m / 1000.0


def geodesic_buffer_ring(lon: float, lat: float, radius_km: float, n_points: int = 72) -> tuple[list[float], list[float]]:
    """A true geodesic circle (constant-radius ring on the WGS84 ellipsoid)
    around (lon, lat). Returns (lons, lats) as closed-ring coordinate lists
    (first point repeated at the end), ready to hand to a plotly Scatter
    trace with fill='toself'.
    """
    azimuths = np.linspace(0, 360, n_points, endpoint=False)
    lons, lats, _ = _GEOD.fwd(
        np.full(n_points, lon),
        np.full(n_points, lat),
        azimuths,
        np.full(n_points, radius_km * 1000.0),
    )
    lons = list(lons) + [lons[0]]
    lats = list(lats) + [lats[0]]
    return lons, lats


def exposure_band(distance_km: float) -> str:
    for low, high, label in EXPOSURE_BANDS:
        if low <= distance_km < high:
            return label
    return EXPOSURE_BANDS[-1][2]


def compute_hub_chokepoint_distances(hubs: pd.DataFrame, chokepoints: pd.DataFrame) -> pd.DataFrame:
    """Cross join of every hub against every chokepoint with geodesic
    distance and exposure band. Returns one row per (hub, chokepoint) pair.
    """
    rows = []
    for _, hub in hubs.iterrows():
        for _, cp in chokepoints.iterrows():
            dist_km = geodesic_distance_km(hub["lon"], hub["lat"], cp["lon"], cp["lat"])
            rows.append(
                {
                    "hub_name": hub["hub_name"],
                    "country": hub["country"],
                    "hub_lat": hub["lat"],
                    "hub_lon": hub["lon"],
                    "chokepoint_id": cp["chokepoint_id"],
                    "chokepoint_name": cp["name"],
                    "distance_km": round(dist_km, 1),
                    "exposure_band": exposure_band(dist_km),
                }
            )
    return pd.DataFrame(rows)


def nearest_chokepoint_per_hub(distances: pd.DataFrame) -> pd.DataFrame:
    """Reduce the full (hub, chokepoint) distance table to each hub's single
    nearest chokepoint."""
    idx = distances.groupby("hub_name")["distance_km"].idxmin()
    return distances.loc[idx].reset_index(drop=True)


def country_concentration(nearest: pd.DataFrame) -> pd.DataFrame:
    """For each country, what share of its tracked hubs share the same
    nearest chokepoint -- a purely geometric concentration signal: a share
    of 1.0 means every tracked hub in that country is nearest to the same
    single chokepoint. Says nothing about actual traffic routing, only
    about geographic clustering of the sites this project has verified.
    """
    grouped = nearest.groupby(["country", "chokepoint_name"]).size().reset_index(name="hub_count")
    totals = nearest.groupby("country").size().rename("total_hubs")
    grouped = grouped.merge(totals, on="country")
    grouped["share"] = (grouped["hub_count"] / grouped["total_hubs"]).round(3)
    return grouped.sort_values(["country", "hub_count"], ascending=[True, False])
