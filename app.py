"""CO2PIPE -- thin Streamlit entrypoint.

All calculation logic lives in src/co2pipe/physics and src/co2pipe/economics;
all UI logic lives in src/co2pipe/ui. This file only wires them together:
page config, sidebar inputs, map + attribute card, and the three results tabs.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st
from streamlit_folium import st_folium

from co2pipe import config
from co2pipe.data_loader import load_pipelines, load_traps
from co2pipe.ui import map_view, panels, theme

st.set_page_config(
    layout="wide",
    page_title="CO2PIPE — Pipeline Repurposing Analysis",
    page_icon="♻️",
)
theme.inject_css()

st.markdown(
    f"""
    <div style="display:flex; align-items:baseline; gap:0.75rem; margin-bottom:0.5rem;">
        <span style="font-size:1.6rem; font-weight:700; color:{theme.TEXT_PRIMARY};">♻️ CO2PIPE</span>
        <span style="font-size:0.95rem; color:{theme.TEXT_SECONDARY};">
            Pipeline Repurposing Analysis — UK Oil &amp; Gas Pipelines for CO₂ Transport
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

pipelines = load_pipelines()
traps = load_traps()

if pipelines is None:
    st.stop()

pipe_ids = pipelines["FEATURE_ID"].astype(str).tolist()
pipe_name_lookup = dict(zip(pipelines["FEATURE_ID"].astype(str), pipelines["PIPE_NAME"]))

if "selected_feature_id" not in st.session_state:
    st.session_state.selected_feature_id = pipe_ids[0]

col_map, col_attrs = st.columns([0.6, 0.4], gap="medium")

with col_map:
    fmap = map_view.build_map(pipelines, traps, st.session_state.selected_feature_id)
    map_data = st_folium(
        fmap,
        height=600,
        use_container_width=True,
        key="main_map",
        # Restrict what the component sends back on every interaction (pan/
        # zoom/etc. otherwise also count as "changed" and force a rerun --
        # per streamlit-folium's own docs, anything NOT listed here simply
        # won't trigger one). These three are the only keys
        # extract_clicked_feature_id ever reads.
        returned_objects=["last_active_feature", "last_object_clicked", "last_clicked"],
    )

# Resolve a map click BEFORE the sidebar selectbox (same key) is instantiated
# below, so the two stay in sync without a widget-state conflict: writing to
# st.session_state.selected_feature_id after that key's widget has already
# rendered THIS run raises StreamlitAPIException, regardless of whether a
# rerun follows or not.
#
# st.rerun() IS deliberately back here, guarded, after being removed for the
# earlier grey-flash: build_map() above was already called with the OLD
# selection (a click can only be discovered by calling st_folium(), by which
# point this run's map has already rendered stale -- confirmed by tracing
# actual build_map() calls). Without a forced rerun, the highlight only
# catches up on whatever the NEXT unrelated interaction happens to be, which
# reads as "stuck one selection behind." The earlier grey-flash was caused by
# @st.cache_resource on build_map making folium re-render (non-idempotently)
# the same Map object every rerun, not by having two renders per se; that
# caching is gone now, so this guarded rerun costs one extra full,
# independently-fresh map build -- confirmed safe and non-looping below.
clicked_id = map_view.extract_clicked_feature_id(map_data, pipelines)
if clicked_id and clicked_id in pipe_ids and clicked_id != st.session_state.selected_feature_id:
    st.session_state.selected_feature_id = clicked_id
    st.rerun()

with st.sidebar:
    st.markdown("### Select Pipeline")
    st.selectbox(
        "Pipeline",
        options=pipe_ids,
        format_func=lambda fid: pipe_name_lookup.get(fid, fid),
        key="selected_feature_id",
        label_visibility="collapsed",
    )

    with st.expander("Transport", expanded=True):
        st.number_input(
            "Pipeline capacity factor (e.g. 0.85)", min_value=0.1, max_value=1.0, step=0.01,
            value=config.DEFAULTS["pipe_capacity_factor"], key="pipe_capacity_factor",
        )
        st.number_input(
            "Segment inlet pressure (psia):",
            value=config.DEFAULTS["p_in_psia"], key="p_in_psia",
        )
        st.number_input(
            "Segment outlet pressure (psia):",
            value=config.DEFAULTS["p_out_psia"], key="p_out_psia",
        )
        st.number_input(
            "Temperature (°C):",
            value=config.DEFAULTS["tmp_c"], key="tmp_c",
        )
        st.number_input(
            "Annual average CO₂ mass flow rate (Mtonnes/yr):",
            value=config.DEFAULTS["qm_proyection_Mtpy"], key="qm_proyection_Mtpy",
        )
        st.number_input(
            "Total elevation change (meters):",
            value=config.DEFAULTS["h_dif_tot"], key="h_dif_tot",
        )
        st.number_input(
            "Number of pumps/compressor stations:", min_value=0, step=1,
            value=config.DEFAULTS["N_Pump"], key="N_Pump",
        )
        st.number_input(
            "Molecular weight of CO₂ (g/mol):",
            value=config.DEFAULTS["MW_in"], key="MW_in",
        )

    with st.expander("Corrosion", expanded=False):
        st.number_input(
            "Liquid rate QL (m³/d):",
            value=config.DEFAULTS["QL"], key="QL",
        )
        st.number_input(
            "Gas rate QG (Mm³/d):",
            value=config.DEFAULTS["QG"], key="QG",
        )
        st.number_input(
            "Water cut WC (fraction 0-1):",
            value=config.DEFAULTS["WC"], key="WC",
        )
        st.number_input(
            "Temperature Temp (°C):",
            value=config.DEFAULTS["Temp"], key="Temp",
        )
        st.number_input(
            "Pressure (bar):",
            value=config.DEFAULTS["Pressure"], key="Pressure",
        )
        st.number_input(
            "Mole percent CO2 (%):",
            value=config.DEFAULTS["mole_percent_CO2"], key="mole_percent_CO2",
        )
        st.number_input(
            "Estimated corrosion rate for CO2 transport (mm/year):",
            value=config.DEFAULTS["corrosion_rate_co2"], key="corrosion_rate_co2",
        )

    with st.expander("Cost Model", expanded=False):
        st.selectbox("Model:", list(panels.MODEL_OPTIONS.keys()), key="model_name_key")
        st.number_input(
            "Escalation rate (%):", min_value=0.0,
            value=config.DEFAULTS["rate_percent"], key="rate_percent",
        )
        st.number_input(
            "Project start year:", min_value=2011,
            value=config.DEFAULTS["cost_start_year"], key="cost_start_year",
        )
        st.number_input(
            "Project Contingency Factor (%):", min_value=0.0,
            value=config.DEFAULTS["contingency_percent"], key="contingency_percent",
        )

    st.markdown("---")
    run_clicked = st.button("Run Analysis", type="primary", use_container_width=True)

selected_row = pipelines.loc[pipelines["FEATURE_ID"].astype(str) == st.session_state.selected_feature_id].iloc[0]
pipe_attrs = panels.extract_pipe_attributes(selected_row)

# Compute BEFORE col_attrs renders below, so a Run Analysis click updates the
# Key Results summary in the same rerun instead of lagging one click behind.
if run_clicked:
    inputs = {k: st.session_state[k] for k in config.DEFAULTS}
    transport_results = panels.compute_transport(pipe_attrs, inputs)
    corrosion_results = panels.compute_corrosion(pipe_attrs, inputs, transport_results=transport_results)
    cost_results = panels.compute_cost(pipe_attrs, inputs)
    st.session_state["transport_results"] = transport_results
    st.session_state["corrosion_results"] = corrosion_results
    st.session_state["cost_results"] = cost_results

with col_attrs:
    panels.render_attribute_card(pipe_attrs)
    panels.render_key_results_summary(
        st.session_state.get("transport_results"),
        st.session_state.get("corrosion_results"),
    )

st.markdown("---")
tab_transport, tab_corrosion, tab_cost = st.tabs(["Transport Capacity", "Corrosion & Lifetime", "Cost Model"])
with tab_transport:
    panels.render_transport_tab(st.session_state.get("transport_results"))
with tab_corrosion:
    panels.render_corrosion_tab(st.session_state.get("corrosion_results"))
with tab_cost:
    panels.render_cost_tab(st.session_state.get("cost_results"))
