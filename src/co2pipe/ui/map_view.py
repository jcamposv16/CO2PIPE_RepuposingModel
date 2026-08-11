"""Folium map construction and click/selection handling for the pipeline map.

Ported from the map-building section of streamlit_map_eva11.py: same basemaps
(Streets/Satellite/Labels), same traps + pipelines layers, same MiniMap /
Fullscreen / MousePosition plugins and layer control. Only the styling
(selected/unselected/hover colors) now comes from co2pipe.ui.theme instead of
hardcoded hex values, and the whole thing is wrapped in functions instead of
running inline at module scope.
"""
from typing import Optional

import folium
import geopandas as gpd
import streamlit as st
from folium.plugins import Fullscreen, MiniMap, MousePosition

from co2pipe.ui import theme

# British National Grid -- appropriate projected CRS (meters) for UK/North Sea
# pipeline data, used only for the click -> nearest-geometry distance
# calculation so it isn't computed in degrees.
_CLICK_DISTANCE_CRS = "EPSG:27700"

# A resolved "nearest pipeline" farther than this from the click is treated
# as a miss (user clicked open water/land, not a pipeline) rather than
# force-selecting whatever happens to be nearest.
_CLICK_MISS_THRESHOLD_M = 5000


def _style_for(selected_feature_id: str):
    def _style(feature):
        fid = str(feature["properties"].get("FEATURE_ID"))
        is_sel = fid == selected_feature_id
        return {
            "color": theme.MAP_SELECTED if is_sel else theme.MAP_UNSELECTED,
            "weight": 8 if is_sel else 6,
            "opacity": 1.0 if is_sel else 0.85,
        }
    return _style


def _highlight(_feature):
    return {"color": theme.MAP_HOVER, "weight": 10, "opacity": 1.0}


def _trap_style(_feature):
    return {
        "color": theme.TRAP_EDGE,
        "weight": 1.5,
        "opacity": 0.9,
        "fillColor": theme.TRAP_FILL,
        "fillOpacity": theme.TRAP_ALPHA,
    }


def _trap_highlight(_feature):
    return {"weight": 3, "color": "#000000", "fillOpacity": 0.45}


def build_map(
    gdf: gpd.GeoDataFrame,
    traps_gdf: Optional[gpd.GeoDataFrame],
    selected_feature_id: str,
) -> folium.Map:
    """Build the folium Map for the pipeline network + geological traps.

    Args:
        gdf: pipeline GeoDataFrame (from co2pipe.data_loader.load_pipelines).
        traps_gdf: geological traps GeoDataFrame, or None if unavailable.
        selected_feature_id: FEATURE_ID (as string) of the currently selected pipeline.

    Deliberately NOT cached (do not add @st.cache_resource / @st.cache_data
    here). streamlit_folium.st_folium() calls `.get_root().render()` on
    whatever folium.Map it's given on every single invocation, and that
    render is NOT idempotent: rendering the same Map object a second time
    re-emits additional `tile_layer_XXXX.addTo(map_XXXX)` (and similar) script
    calls on top of the first render's output rather than regenerating clean
    HTML, so the page's embedded JS grows and duplicates a little more on
    every rerun. Caching this function returns the same object across
    reruns, which triggers exactly that -- confirmed empirically (repeated
    `.get_root().render()` calls on one cached Map produced different,
    growing output each time) as the actual cause of the map going blank
    after enough reruns. A fresh Map per call is cheap enough (29 pipeline +
    1088 trap features) that this isn't worth trying to cache again without
    also fixing folium/streamlit-folium's render non-idempotency.
    """
    # Center the map on the selected feature.
    sel_row = gdf.loc[gdf["FEATURE_ID"].astype(str) == selected_feature_id]
    if len(sel_row):
        minx, miny, maxx, maxy = sel_row.iloc[0].geometry.bounds
        c_y, c_x = (miny + maxy) / 2, (minx + maxx) / 2
    else:
        center = gdf.geometry.unary_union.centroid
        c_y, c_x = center.y, center.x

    m = folium.Map(location=[c_y, c_x], zoom_start=7, tiles=None)

    # --- Base layers --- Streets is the default basemap: show=True (and
    # added first, for readability) while Satellite is explicitly show=False
    # so it starts hidden and only appears if picked from the layer control.
    # (Relying on add-order alone doesn't reliably decide which base layer
    # renders on top when both default to shown -- explicit show= is what
    # actually controls initial visibility.)
    folium.TileLayer(
        "cartodbpositron", name="Streets (CartoDB Positron)", control=True, show=True,
    ).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr=("Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, "
              "Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"),
        name="Satellite (Esri WorldImagery)",
        control=True,
        overlay=False,
        show=False,
    ).add_to(m)
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png",
        attr="© CARTO",
        name="Labels (light)",
        control=True,
        overlay=True,
    ).add_to(m)

    # --- Geological traps layer ---
    if traps_gdf is not None and len(traps_gdf):
        name_candidates = ("trap_name", "trapname", "name", "trap")
        trap_name_col = next((c for c in traps_gdf.columns if c.lower() in name_candidates), None)

        traps_group = folium.FeatureGroup(name="Geological traps (HiSTORIEs)", show=True)
        folium.GeoJson(
            data=traps_gdf.__geo_interface__,
            name="Geological traps (HiSTORIEs)",
            style_function=_trap_style,
            highlight_function=_trap_highlight,
            tooltip=folium.GeoJsonTooltip(
                fields=[trap_name_col] if trap_name_col else [],
                aliases=["Trap:"],
                sticky=False,
                localize=True,
            ),
        ).add_to(traps_group)
        traps_group.add_to(m)

    # --- Pipeline overlay (after traps, so lines sit on top) ---
    folium.GeoJson(
        data=gdf.__geo_interface__,
        name="Pipelines",
        style_function=_style_for(selected_feature_id),
        highlight_function=_highlight,
        tooltip=folium.GeoJsonTooltip(fields=["PIPE_NAME"]),
    ).add_to(m)

    # --- Widgets: layer switcher, mini-map, fullscreen, mouse coords ---
    folium.LayerControl(position="topright", collapsed=False).add_to(m)
    MiniMap(zoom_level_offset=-2, toggle_display=True).add_to(m)
    Fullscreen(position="topleft").add_to(m)
    MousePosition(position="bottomleft", separator=" | ", prefix="Lat/Lon", num_digits=5).add_to(m)

    return m


@st.cache_resource(show_spinner=False)
def _projected_for_distance(_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Pipeline geometries reprojected to a projected CRS (meters) for accurate
    nearest-geometry distance calculations.

    Cached (unlike build_map, this is safe to cache): reprojection is a pure
    data transform with no render-on-the-same-object side effect, so reusing
    the result across reruns doesn't hit the folium non-idempotent-render
    issue -- there's nothing here that mutates on repeated use.
    """
    return _gdf.to_crs(_CLICK_DISTANCE_CRS)


def extract_clicked_feature_id(map_data: Optional[dict], gdf: gpd.GeoDataFrame) -> Optional[str]:
    """Resolve a FEATURE_ID from st_folium's returned click/hover payload.

    Mirrors the original eva11.py click-handling logic: prefer the exact
    feature (hover/click on a line), falling back to nearest-geometry lookup
    for a plain map click that didn't land exactly on a feature. Unlike the
    original, the nearest-geometry distance is computed in a projected CRS
    (meters) rather than raw lat/lon degrees, and a miss farther than
    _CLICK_MISS_THRESHOLD_M is treated as no selection rather than always
    picking the nearest pipeline regardless of how far away it is.

    Returns None if no usable selection is present in map_data.
    """
    if not map_data:
        return None

    feat = map_data.get("last_active_feature") or map_data.get("last_object_clicked")
    if feat and "properties" in feat and "FEATURE_ID" in feat["properties"]:
        return str(feat["properties"]["FEATURE_ID"])

    last_clicked = map_data.get("last_clicked")
    if last_clicked:
        lng, lat = last_clicked["lng"], last_clicked["lat"]
        click_point = (
            gpd.GeoDataFrame(geometry=gpd.points_from_xy([lng], [lat]), crs="EPSG:4326")
            .to_crs(_CLICK_DISTANCE_CRS)
            .geometry.iloc[0]
        )
        projected_gdf = _projected_for_distance(gdf)
        distances = projected_gdf.distance(click_point)
        idx = distances.idxmin()
        if distances.loc[idx] > _CLICK_MISS_THRESHOLD_M:
            return None
        return str(gdf.loc[idx, "FEATURE_ID"])

    return None
