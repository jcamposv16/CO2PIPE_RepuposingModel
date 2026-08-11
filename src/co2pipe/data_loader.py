"""Cached GeoJSON loaders for the CO2PIPE pipeline network and geological-trap layers.

Ported from the _load_gdf / _load_traps functions in streamlit_map_eva11.py, wired
to the path constants in co2pipe.config instead of hardcoded relative paths.
"""
from typing import Optional

import geopandas as gpd
import streamlit as st

from co2pipe.config import PIPELINE_COLUMNS, PIPELINE_GEOJSON, TRAPS_GEOJSON


@st.cache_data(show_spinner=False)
def load_pipelines() -> Optional[gpd.GeoDataFrame]:
    """Load the UK pipeline network layer.

    Expected schema (columns kept from the source GeoJSON, see co2pipe.config.PIPELINE_COLUMNS):
        FEATURE_ID  - unique pipeline segment identifier
        PIPE_NAME   - human-readable pipeline name
        OD_IN       - outer diameter, inches
        ID_IN       - inner diameter, inches
        PIPE_GRADE  - API 5L steel grade string, e.g. "X60"
        LENGTH_M    - segment length, meters
        THICKNESS   - wall thickness, mm
        START_DATE  - year the segment entered service
        STATUS      - operational status, e.g. "IN USE", "NOT IN USE", "ABANDONED"
        END_DATE    - year service ended, if applicable
        geometry    - LineString / MultiLineString pipeline geometry

    Returns:
        The pipeline GeoDataFrame, or None if the source file is missing (after
        surfacing a clear st.error naming the path that was checked). Pipeline
        data is required for the app to function, so callers should treat a
        None return as fatal to the current page.
    """
    if not PIPELINE_GEOJSON.exists():
        st.error(f"Pipeline data file not found: {PIPELINE_GEOJSON}")
        return None

    gdf = gpd.read_file(PIPELINE_GEOJSON)[PIPELINE_COLUMNS]
    # Keep geometry precision reasonable (smaller payload to the map), matching
    # the original eva11.py loader.
    from shapely import set_precision
    gdf["geometry"] = gdf.geometry.apply(lambda geom: set_precision(geom, 1e-6))
    return gdf


@st.cache_data(show_spinner=False)
def load_traps() -> Optional[gpd.GeoDataFrame]:
    """Load the geological CO2 storage trap layer (HiSTORIEs project).

    This layer is decorative/contextual on the map only -- no calculation panel
    depends on it -- but a missing file is still surfaced clearly rather than
    raised as an unhandled exception.

    Returns:
        The traps GeoDataFrame, or None if the source file is missing (after
        surfacing a clear st.error naming the path that was checked).
    """
    if not TRAPS_GEOJSON.exists():
        st.error(f"Geological traps file not found: {TRAPS_GEOJSON}")
        return None

    tgdf = gpd.read_file(TRAPS_GEOJSON)
    try:
        from shapely import set_precision
        tgdf["geometry"] = tgdf.geometry.apply(lambda geom: set_precision(geom, 1e-6))
    except Exception:
        pass
    return tgdf
