"""Chokepoint Exposure Map -- geodesic proximity analysis between this
tracker's verified AI infrastructure hubs (data/curated/ai_hubs.csv) and
three physical chokepoints (Strait of Hormuz, Bab-el-Mandeb, Suez Canal)
plus real submarine cable landing stations. See README.md for the full
methodology and its stated limitations.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from chokepoint_mapping import build_exposure_figure  # noqa: E402
from geo_analysis import country_concentration, exposure_band, nearest_chokepoint_per_hub  # noqa: E402
from ui import inject_base_css, page_header, footer  # noqa: E402

CURATED_DIR = Path(__file__).resolve().parents[1] / "data" / "curated"
COMPUTED_DIR = Path(__file__).resolve().parents[1] / "data" / "computed"
GEOJSON_PATH = Path(__file__).resolve().parents[1] / "data" / "geo" / "region_countries.geojson"


@st.cache_data(ttl=3600)
def load_geojson() -> dict:
    with open(GEOJSON_PATH) as f:
        return json.load(f)


@st.cache_data(ttl=3600)
def load_qgis_buffers() -> dict:
    with open(COMPUTED_DIR / "qgis_chokepoint_buffers.geojson") as f:
        return json.load(f)


@st.cache_data(ttl=3600)
def load_ai_hubs() -> pd.DataFrame:
    return pd.read_csv(CURATED_DIR / "ai_hubs.csv")


@st.cache_data(ttl=3600)
def load_chokepoints() -> pd.DataFrame:
    return pd.read_csv(CURATED_DIR / "chokepoints.csv")


@st.cache_data(ttl=3600)
def load_cable_landing_stations() -> pd.DataFrame:
    return pd.read_csv(CURATED_DIR / "cable_landing_stations.csv")


@st.cache_data(ttl=3600)
def load_qgis_distances() -> pd.DataFrame:
    """The hub-to-chokepoint distance matrix as computed by real QGIS
    (QgsDistanceArea, ellipsoidal WGS84) -- see
    src/data_pipeline/generate_qgis_geodata.py. exposure_band is added
    here from the same banding function the pyproj cross-check tests use,
    not recomputed differently."""
    df = pd.read_csv(COMPUTED_DIR / "qgis_hub_chokepoint_distances.csv")
    df["exposure_band"] = df["distance_km"].apply(exposure_band)
    return df


def main() -> None:
    inject_base_css()
    page_header(
        "Chokepoint Exposure Map",
        "Where this tracker's verified AI infrastructure sites sit relative to the physical straits, "
        "canals, and cable corridors their region's connectivity and energy trade actually depends on.",
        meta=["DATA AS OF: SEPTEMBER 2026"],
    )

    hubs = load_ai_hubs()
    chokepoints = load_chokepoints()
    cable_stations = load_cable_landing_stations()

    st.caption(
        "Gold stars are the same 14 AI infrastructure sites tracked on the Regional Dashboard's map -- "
        "unchanged, reused directly from data/curated/ai_hubs.csv. Green dots are real submarine cable "
        "landing stations. Triangles are the three chokepoints this page tracks. Every marker traces to a "
        "cited source -- see the Sources & Data page. Full methodology and limitations below the map."
    )

    show_buffers = st.checkbox("Show 250 / 500 / 1000km geodesic buffer rings", value=True)
    fig = build_exposure_figure(
        hubs, chokepoints, cable_stations,
        show_buffers=show_buffers, geojson=load_geojson(), qgis_buffers=load_qgis_buffers(),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Buffer rings are real QGIS output -- generated offline by "
        "`src/data_pipeline/generate_qgis_geodata.py` via PyQGIS's own geometry engine "
        "(`QgsGeometry.buffer()` in a locally-centered azimuthal-equidistant projection), not "
        "approximated at render time. See the Methodology section below."
    )

    st.divider()
    st.subheader("Country exposure breakdown")
    st.caption(
        "Geodesic distance from each tracked AI hub to each chokepoint, computed by real QGIS "
        "(`QgsDistanceArea`, ellipsoidal WGS84 -- the engine behind QGIS's own Measure tool). "
        "No traffic-share or dependency percentage is invented here -- this is distance only, computed "
        "from the same verified lat/lon values shown on the map above."
    )

    distances = load_qgis_distances()
    nearest = nearest_chokepoint_per_hub(distances)

    countries = sorted(hubs["country"].unique())
    selected = st.selectbox("Country", countries)
    country_hubs = distances[distances["country"] == selected]
    st.dataframe(
        country_hubs[["hub_name", "chokepoint_name", "distance_km", "exposure_band"]]
        .sort_values(["hub_name", "distance_km"])
        .reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Nearest chokepoint, all tracked hubs"):
        st.dataframe(
            nearest[["hub_name", "country", "chokepoint_name", "distance_km", "exposure_band"]].sort_values("distance_km"),
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Concentration: does a country's tracked footprint sit near just one chokepoint?"):
        st.caption(
            "Purely geometric: for each country, what share of its tracked hubs share the same nearest "
            "chokepoint. A share of 1.0 means every tracked hub in that country is nearest to the same "
            "single chokepoint -- it says nothing about actual traffic routing, only about geographic "
            "clustering of the sites this project has verified."
        )
        st.dataframe(country_concentration(nearest), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Methodology & limitations")
    st.markdown(
        """
**What this is.** A geodesic proximity analysis between two verified datasets: this tracker's 14 AI
infrastructure hubs (reused unchanged, each already cited on the Regional Dashboard) and three physical
chokepoints -- Strait of Hormuz, Bab-el-Mandeb, Suez Canal -- plus five real submarine cable landing
stations. The distance matrix and buffer rings shown above are **real QGIS output**, not a re-implementation
of its math: `src/data_pipeline/generate_qgis_geodata.py` runs actual PyQGIS -- `QgsDistanceArea` in
ellipsoidal (WGS84) mode for every hub-to-chokepoint distance (the same engine behind QGIS's own "Measure"
tool), and `QgsGeometry.buffer()` for the rings, applied in a custom azimuthal-equidistant projection
centered on each chokepoint so the buffer is a true geodesic circle rather than a flat-projection
approximation. This is an offline/build-time step -- its output is checked into
`data/computed/qgis_hub_chokepoint_distances.csv` and `qgis_chokepoint_buffers.geojson` and simply read by
this page, the standard GIS pattern of doing heavy geoprocessing once rather than requiring QGIS itself
(roughly 1GB of dependencies) as a runtime dependency of this app. A separate, independently-implemented
`pyproj`-based calculation (`src/geo_analysis.py`) is kept and tested against this QGIS output
(`tests/test_qgis_geodata.py`) as a cross-check, not as the production source.

**What this is not.** Not a cable-routing model -- proximity to a chokepoint is not the same as a hub's
actual network traffic being routed through it; real routing depends on which specific cable systems an
operator contracts with, which is not public for most hubs here. Where a hub's own source material *does*
state a direct cable relationship (Oman's Barka site, ~2km from the AAE-1 landing station; Syria's Tartus
site, itself a SilkLink landing station), that is carried over as a documented fact, not inferred from
distance. Not a traffic-share or economic-loss estimate -- the percentages in each chokepoint's tooltip
(e.g. ~21% of global petroleum liquids through Hormuz, per EIA; ~15% of global maritime trade through Suez,
per the IMF) are those chokepoints' own documented global significance, never reprojected onto an
individual hub. Not a risk score -- there is no composite index here, only descriptive geometry.

**Known gaps.** Cable landing stations are verified and included only for Saudi Arabia (Jeddah), Qatar
(Doha), UAE (Fujairah), Oman (Barka), and Syria (Tartus). For the remaining tracked countries with an AI
hub -- Israel, Egypt, Iraq, Jordan, Turkey, Bahrain, Pakistan -- no cable landing station has been added to
this dataset; rather than estimate one, those countries appear with hub-to-chokepoint geodesic distance
only. See the Sources & Data page for the full citation list.
        """
    )

    footer()


if __name__ == "__main__":
    main()
