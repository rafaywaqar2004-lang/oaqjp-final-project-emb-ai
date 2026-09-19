"""Generates the Chokepoint Exposure Map's buffer geometries and hub-to-
chokepoint distance matrix using real QGIS (PyQGIS), not a re-implementation
of its math in another library.

This is an offline/build-time step, run once (or whenever the underlying
hub/chokepoint CSVs change) and its output committed to data/computed/ --
the standard GIS pattern of doing heavy geoprocessing once and having the
lightweight web app serve the precomputed result, rather than requiring
QGIS itself (roughly 1GB of Qt/GDAL/GRASS dependencies) as a runtime
dependency of a Streamlit app on Render's free tier.

Two real QGIS engines are used, not approximated:

1. Distance matrix: QgsDistanceArea in ellipsoidal (WGS84) mode -- the same
   engine behind QGIS's own "Measure" tool and $length/$area expressions.
2. Buffer rings: QgsGeometry.buffer() (QGIS's GEOS-backed buffer engine,
   the same one QGIS's own "native:buffer" processing algorithm calls)
   run in a custom azimuthal-equidistant CRS centered exactly on each
   chokepoint -- the standard GIS technique for a true geodesic circle
   without visible projection distortion, since distance from the CRS's
   own center is preserved exactly in every direction.

Requires QGIS installed with its Python bindings (`apt-get install qgis`
on Debian/Ubuntu; the qgis.core module must be importable). Run with the
same Python QGIS was built against -- on Ubuntu 24.04 with the qgis apt
package, that's /usr/bin/python3.12, not necessarily the environment's
default `python3`:

    QT_QPA_PLATFORM=offscreen /usr/bin/python3.12 src/data_pipeline/generate_qgis_geodata.py

Output (checked into the repo, so the deployed app never needs QGIS):
  data/computed/qgis_hub_chokepoint_distances.csv
  data/computed/qgis_chokepoint_buffers.geojson
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from constants import CURATED_DIR, COMPUTED_DIR  # noqa: E402

BUFFER_RADII_M = [250_000, 500_000, 1_000_000]
BUFFER_SEGMENTS = 18  # points per quarter-circle-equivalent -> 72-point rings, smooth enough for this map's scale


def _load_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    from qgis.core import (
        QgsApplication,
        QgsCoordinateReferenceSystem,
        QgsCoordinateTransform,
        QgsDistanceArea,
        QgsGeometry,
        QgsPointXY,
        QgsProject,
    )

    qgs = QgsApplication([], False)
    qgs.initQgis()

    try:
        hubs = _load_csv(f"{CURATED_DIR}/ai_hubs.csv")
        chokepoints = _load_csv(f"{CURATED_DIR}/chokepoints.csv")

        # ---- 1. Distance matrix: QgsDistanceArea, ellipsoidal WGS84 ----
        da = QgsDistanceArea()
        da.setEllipsoid("WGS84")
        da.setSourceCrs(QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance().transformContext())

        distance_rows = []
        for hub in hubs:
            p1 = QgsPointXY(float(hub["lon"]), float(hub["lat"]))
            for cp in chokepoints:
                p2 = QgsPointXY(float(cp["lon"]), float(cp["lat"]))
                dist_km = da.measureLine(p1, p2) / 1000.0
                distance_rows.append(
                    {
                        "hub_name": hub["hub_name"],
                        "country": hub["country"],
                        "chokepoint_id": cp["chokepoint_id"],
                        "chokepoint_name": cp["name"],
                        "distance_km": round(dist_km, 2),
                    }
                )

        out_csv = Path(COMPUTED_DIR) / "qgis_hub_chokepoint_distances.csv"
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["hub_name", "country", "chokepoint_id", "chokepoint_name", "distance_km"])
            writer.writeheader()
            writer.writerows(distance_rows)
        print(f"Wrote {len(distance_rows)} distance rows to {out_csv}")

        # ---- 2. Buffer rings: QgsGeometry.buffer() in a local azimuthal-
        # equidistant CRS centered on each chokepoint, reprojected back to
        # EPSG:4326. True geodesic circles: distance from the projection's
        # own center is exact in every direction under this projection.
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        features = []
        for cp in chokepoints:
            lon, lat = float(cp["lon"]), float(cp["lat"])
            aeqd_wkt = (
                f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 "
                f"+datum=WGS84 +units=m +no_defs"
            )
            local_crs = QgsCoordinateReferenceSystem.fromProj(aeqd_wkt)
            to_local = QgsCoordinateTransform(wgs84, local_crs, QgsProject.instance())
            to_wgs84 = QgsCoordinateTransform(local_crs, wgs84, QgsProject.instance())

            center_local = to_local.transform(QgsPointXY(lon, lat))
            center_geom = QgsGeometry.fromPointXY(center_local)

            for radius_m in BUFFER_RADII_M:
                buffered = center_geom.buffer(radius_m, BUFFER_SEGMENTS)
                buffered.transform(to_wgs84)
                ring = buffered.asPolygon()[0]
                coords = [[pt.x(), pt.y()] for pt in ring]
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "chokepoint_id": cp["chokepoint_id"],
                            "chokepoint_name": cp["name"],
                            "radius_km": radius_m / 1000,
                        },
                        "geometry": {"type": "Polygon", "coordinates": [coords]},
                    }
                )

        geojson = {"type": "FeatureCollection", "features": features}
        out_geojson = Path(COMPUTED_DIR) / "qgis_chokepoint_buffers.geojson"
        with open(out_geojson, "w", encoding="utf-8") as f:
            json.dump(geojson, f)
        print(f"Wrote {len(features)} buffer ring features to {out_geojson}")

    finally:
        qgs.exitQgis()


if __name__ == "__main__":
    main()
