"""Renders the Chokepoint Exposure Map's background as a real QGIS map
render (QgsMapSettings + QgsMapRendererParallelJob), not Plotly line
traces -- anti-aliased polygon fills/borders styled in this project's own
paper/ink palette (src/ui.py), instead of the thin raw vector outlines
previously drawn as go.Scatter traces.

Uses the same bundled data/geo/region_countries.geojson every other map in
this app already uses -- no new geographic data, just a higher-quality,
project-styled render of it.

Offline/build-time step: output is checked into
static/chokepoint_basemap.png and src/chokepoint_mapping.py places it as a
Plotly background image (fig.add_layout_image) at the exact same lon/lat
extent the data traces are plotted in, so QGIS's render and Plotly's data
markers line up pixel-for-pixel. QGIS itself is not a runtime dependency
of the deployed app -- only the static PNG is.

Run with the Python QGIS was built against (e.g. /usr/bin/python3.12 on
Ubuntu 24.04 with the qgis apt package):

    QT_QPA_PLATFORM=offscreen /usr/bin/python3.12 src/data_pipeline/generate_qgis_basemap.py
"""
from __future__ import annotations

from pathlib import Path

# Must match src/chokepoint_mapping.py's fig.update_xaxes/update_yaxes range
# exactly, or the image will not align with the data traces plotted on it.
LON_RANGE = (20, 70)
LAT_RANGE = (5, 42)

# This project's own paper/ink palette (src/ui.py) -- land reads as the
# same warm cream/paper surface the rest of the app uses, water as a
# quiet, slightly cool contrast so the two are legible apart without
# competing with the data markers plotted on top.
LAND_FILL = "#ECEAE3"     # SURFACE_2
LAND_BORDER = "#B9B6A8"   # a shade darker than LINE, for a crisper coastline at render scale
WATER_FILL = "#E7EDF1"    # quiet cool contrast to the warm land tone

OUTPUT_WIDTH = 1600
OUTPUT_HEIGHT = round(OUTPUT_WIDTH * (LAT_RANGE[1] - LAT_RANGE[0]) / (LON_RANGE[1] - LON_RANGE[0]))


def main() -> None:
    from qgis.core import (
        QgsApplication,
        QgsCoordinateReferenceSystem,
        QgsFillSymbol,
        QgsMapSettings,
        QgsMapRendererParallelJob,
        QgsProject,
        QgsRectangle,
        QgsVectorLayer,
    )
    from qgis.PyQt.QtCore import QSize
    from qgis.PyQt.QtGui import QColor

    qgs = QgsApplication([], False)
    qgs.initQgis()

    try:
        repo_root = Path(__file__).resolve().parents[2]
        geojson_path = repo_root / "data" / "geo" / "region_countries.geojson"

        layer = QgsVectorLayer(str(geojson_path), "countries", "ogr")
        if not layer.isValid():
            raise RuntimeError(f"Failed to load {geojson_path} as a QGIS vector layer")

        symbol = QgsFillSymbol.createSimple(
            {
                "color": LAND_FILL,
                "outline_color": LAND_BORDER,
                "outline_width": "0.4",
                "outline_width_unit": "MM",
            }
        )
        layer.renderer().setSymbol(symbol)

        settings = QgsMapSettings()
        settings.setLayers([layer])
        settings.setBackgroundColor(QColor(WATER_FILL))
        settings.setOutputSize(QSize(OUTPUT_WIDTH, OUTPUT_HEIGHT))
        settings.setExtent(QgsRectangle(LON_RANGE[0], LAT_RANGE[0], LON_RANGE[1], LAT_RANGE[1]))
        settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        settings.setOutputDpi(96)

        render_flags = settings.flags()
        settings.setFlag(QgsMapSettings.Antialiasing, True)

        job = QgsMapRendererParallelJob(settings)
        job.start()
        job.waitForFinished()

        image = job.renderedImage()
        out_dir = repo_root / "static"
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / "chokepoint_basemap.png"
        image.save(str(out_path), "PNG")
        print(f"Wrote {OUTPUT_WIDTH}x{OUTPUT_HEIGHT} QGIS basemap render to {out_path}")

    finally:
        qgs.exitQgis()


if __name__ == "__main__":
    main()
