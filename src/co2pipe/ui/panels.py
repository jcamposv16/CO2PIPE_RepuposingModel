"""Compute + render functions for the three calculation panels (Transport,
Corrosion & Lifetime, Cost Model) and the selected-pipeline attribute card.

Every compute_* function below is a line-for-line port of the corresponding
block in streamlit_map_eva11.py -- same variable names, same order of
operations, same constants -- just calling into co2pipe.physics /
co2pipe.economics instead of locally-defined functions, and returning a dict
instead of writing directly to the page. Only the render_* functions are new
UI: they show headline results as st.metric, then supporting detail in an
expander, then (for cost) the chart. No calculation logic lives in a render_*
function.
"""
import datetime
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st

from co2pipe.economics import cost_models
from co2pipe.physics import co2_properties, corrosion, hydraulics, pipe_sizing, units
from co2pipe.ui import charts

MODEL_OPTIONS = {
    "PARKER": ("Parker (2004)", cost_models.CpParker, ()),
    "RUI": ("Rui et al. (2011)", cost_models.CpRui, ("AVG",)),
    "MCCOY": ("McCoy and Rubin (2008)", cost_models.CpMcCoy, ("AVG",)),
    "BROWN": ("Brown et al. (2022)", cost_models.CpBrown, ("AVG",)),
}


def extract_pipe_attributes(row) -> dict:
    """Pull the display/calculation attributes out of a pipeline GeoDataFrame row.

    Ported unchanged from eva11.py's "Extract pipeline info for all calculations"
    block, including the END_DATE cleanup (drop a trailing ".0" from a float year).
    """
    pipe_name = row.get('PIPE_NAME', 'N/A')
    length_km = float(row.get('LENGTH_M', 0)) / 1000
    length_mi = length_km * 0.621371
    od_in = float(row.get('OD_IN', 0))
    id_in = float(row.get('ID_IN', 0))
    thickness_mm = float(row.get('THICKNESS', 0))
    pipe_grade = row.get('PIPE_GRADE', 'N/A')
    start_year = int(row.get('START_DATE', 1990))
    status = str(row.get('STATUS', 'N/A')).strip()

    raw_end = row.get('END_DATE', None)
    if pd.notna(raw_end) and raw_end not in ("", "<NA>", "NaT"):
        if isinstance(raw_end, (int, np.integer)):
            end_date_str = str(raw_end)
        elif isinstance(raw_end, float) and raw_end.is_integer():
            end_date_str = str(int(raw_end))
        else:
            end_date_str = str(raw_end)
    else:
        end_date_str = None

    return dict(
        pipe_name=pipe_name, length_km=length_km, length_mi=length_mi,
        od_in=od_in, id_in=id_in, thickness_mm=thickness_mm, pipe_grade=pipe_grade,
        start_year=start_year, status=status, end_date_str=end_date_str,
    )


# ---------------------------------------------------------------------------
# Compute (pure -- no Streamlit calls, no rendering)
# ---------------------------------------------------------------------------

def compute_transport(pipe_attrs: dict, inputs: dict) -> dict:
    """Port of the "Calculate Transport Design" button block in eva11.py."""
    id_in = pipe_attrs["id_in"]
    length_km = pipe_attrs["length_km"]

    pipe_capacity_factor = inputs["pipe_capacity_factor"]
    p_in_psia = inputs["p_in_psia"]
    p_out_psia = inputs["p_out_psia"]
    tmp_c = inputs["tmp_c"]
    qm_proyection_Mtpy = inputs["qm_proyection_Mtpy"]
    h_dif_tot = inputs["h_dif_tot"]
    N_Pump = inputs["N_Pump"]
    MW_in = inputs["MW_in"]

    pipe_inner_rough = 0.0018  # in
    eta = units.Conv_Dpipeline(pipe_inner_rough, 'in', 'm')
    Dia_in_nom_in = id_in
    Dia_in_nom_m = units.Conv_Dpipeline(Dia_in_nom_in, 'in', 'm')
    volinit = 0
    p_in = units.psia_to_mpa(p_in_psia)
    p_out = units.psia_to_mpa(p_out_psia)
    p_in_Pa = p_in * 1e6
    p_out_Pa = p_out * 1e6
    tmp = units.Conv_temp(tmp_c)
    MW = MW_in * 0.001
    Nseg = N_Pump + 1
    L_seg = length_km * 1000 / Nseg
    h_dif_seg = h_dif_tot / Nseg
    p_avg = hydraulics.pav_gas(p_in, p_out)
    density = co2_properties.denDuanCO2(volinit, p_avg, tmp)
    viscosity = co2_properties.visFWVCO2(density, tmp)
    z_factor = co2_properties.zfactDuanCO2(volinit, p_avg, tmp)
    pi = np.pi
    g = 9.80665
    Rgas = 8.3144621
    Dia_g = Dia_in_nom_m
    qm_max = 100.0
    tol = 1e-6
    max_iter = 1000
    ic = 0
    error = None
    Re = None
    ff = None
    while ic <= max_iter:
        visc_Pa_s = viscosity * 1e-6
        Re = hydraulics.reynolds_number(qm_max, visc_Pa_s, Dia_g)
        ff = hydraulics.fanning_friction_colebrook(Re, Dia_g, eta)
        num_const = -64 * z_factor**2 * Rgas**2 * tmp**2 * ff * L_seg
        denom = (
            pi**2 * (
                MW * z_factor * Rgas * tmp * (p_out_Pa**2 - p_in_Pa**2)
                + 2 * g * (p_avg * 1e6)**2 * MW**2 * h_dif_seg
            )
        )
        if num_const == 0:
            error = "Physical parameters out of valid range, cannot compute maximum flow rate."
            qm_max = 0
            break
        qm_new = np.sqrt((denom * Dia_g**5) / num_const)
        if abs(qm_new - qm_max) < tol:
            qm_max = qm_new
            break
        qm_max = 0.5 * (qm_new + qm_max)
        ic += 1

    qm_max_Mtpy = qm_max * 365 * 24 * 3600 / 1e9
    required_qm_max = qm_proyection_Mtpy / pipe_capacity_factor
    required_qm_max_kgps = required_qm_max * 1e9 / (365 * 24 * 3600)

    return {
        "error": error,
        "p_avg": p_avg,
        "density": density,
        "viscosity": viscosity,
        "z_factor": z_factor,
        "ff": ff,
        "Re": Re,
        "qm_max": qm_max,
        "qm_max_Mtpy": qm_max_Mtpy,
        "required_qm_max": required_qm_max,
        "required_qm_max_kgps": required_qm_max_kgps,
        "od_in": pipe_attrs["od_in"],
        "Dia_in_nom_in": Dia_in_nom_in,
        "Dia_in_nom_m": Dia_in_nom_m,
        "suitable": (error is None) and (qm_max_Mtpy >= required_qm_max),
    }


def compute_corrosion(pipe_attrs: dict, inputs: dict, transport_results: Optional[dict] = None) -> dict:
    """Port of the "Estimate Corrosion and Lifetime" button block in eva11.py."""
    id_in = pipe_attrs["id_in"]
    pipeline_thickness = pipe_attrs["thickness_mm"]
    pipeline_start_year = pipe_attrs["start_year"]
    pipeline_status = pipe_attrs["status"]
    pipeline_end_date = pipe_attrs["end_date_str"]
    grade_tmin = pipe_attrs["pipe_grade"]

    QL = inputs["QL"]
    QG = inputs["QG"]
    WC = inputs["WC"]
    Temp = inputs["Temp"]
    Pressure = inputs["Pressure"]
    mole_percent_CO2 = inputs["mole_percent_CO2"]
    corrosion_rate_co2 = inputs["corrosion_rate_co2"]
    temp_tmin = inputs["tmp_c"]  # matches eva11.py: temp_tmin = tmp_c (transport panel's temperature)

    D = id_in / 39.3701

    if transport_results and transport_results.get("p_avg") is not None:
        pressure_tmin_bar = transport_results["p_avg"] * 10  # MPa -> bar
    else:
        pressure_tmin_bar = 80.0

    # Constants, unchanged from eva11.py
    sp_gr = 0.8
    rho_G = 200
    uo = 1.1
    ug = 0.03
    uw = 1.002
    phi_c = 0.5
    u_relmax = 7.06
    rho_oil = 850
    rho_water = 1024
    k = 0.00005
    Bicarb = 0
    IonicStrength = 50
    CalcOfpH = 1

    vsl = corrosion.v_sl(QL, D)
    vsg = corrosion.v_sg(QG, sp_gr, rho_G, D)
    vmix = corrosion.v_m(vsl, vsg)
    ul = corrosion.viscosity_liquid_ul(WC, uo, ug, uw, phi_c, u_relmax)
    lamda_ = corrosion.LAMDA(vsl, vmix)
    u_mi = corrosion.viscosity_mixture_u_mi(lamda_, ul, ug)
    rho_mixture = corrosion.density_mix(rho_oil, rho_G, rho_water, WC, lamda_)
    f = corrosion.friction_factor(k, D, vmix, rho_mixture, u_mi)
    S = corrosion.shear_stress(rho_mixture, vmix, f)
    Bicarb_moll = corrosion.convert_bicarb_mgL_to_molL(Bicarb)
    IonicStrength_moll = corrosion.convert_ionic_gL_to_molL(IonicStrength)
    fugacity_co2_value = corrosion.fugacity_co2(Pressure, Temp, mole_percent_CO2)
    pH = corrosion.pHCalculator1(Temp, Pressure, fugacity_co2_value, Bicarb_moll, IonicStrength_moll, CalcOfpH)
    fpH = corrosion.fpH_Cal(Temp, pH)
    Kt_value = corrosion.Kt(Temp)
    corrosion_rate = corrosion.Corrosion_Norsok(Kt_value, fugacity_co2_value, S, fpH)

    current_year = datetime.datetime.now().year
    status_upper = (pipeline_status or "").strip().upper()
    if status_upper in {"NOT IN USE", "ABANDONED"} and pipeline_end_date:
        try:
            end_year = int(pipeline_end_date)
        except Exception:
            end_year = current_year
        years = max(0, end_year - pipeline_start_year)
        years_label = f"{pipeline_start_year} → {end_year}"
    else:
        years = max(0, current_year - pipeline_start_year)
        years_label = f"{pipeline_start_year} → {current_year}"

    thickness_corroded = corrosion_rate * years
    pressure_tmin_pa = float(pressure_tmin_bar) * 100000  # bar -> Pa
    Tmin = pipe_sizing.tmin(pressure_tmin_pa, D, temp_tmin, grade_tmin)
    current_thickness = pipeline_thickness - thickness_corroded
    thickness_available = current_thickness - Tmin

    years_for_CO2 = None
    if corrosion_rate_co2 > 0:
        years_for_CO2 = thickness_available / corrosion_rate_co2

    return {
        "corrosion_rate": corrosion_rate,
        "years": years,
        "years_label": years_label,
        "thickness_corroded": thickness_corroded,
        "Tmin": Tmin,
        "current_thickness": current_thickness,
        "thickness_available": thickness_available,
        "years_for_CO2": years_for_CO2,
        "pH": pH,
    }


def compute_cost(pipe_attrs: dict, inputs: dict) -> dict:
    """Port of the "Calculate Pipeline Cost" button block in eva11.py."""
    model_name_key = inputs["model_name_key"]
    rate_percent = inputs["rate_percent"]
    cost_start_year = inputs["cost_start_year"]
    contingency_percent = inputs["contingency_percent"]
    N_Pump = inputs["N_Pump"]

    Dia = pipe_attrs["od_in"]
    Lnth = pipe_attrs["length_mi"]
    NumPumps = N_Pump

    years = cost_start_year - 2011
    escalation_factor = (1 + rate_percent / 100.0) ** years
    Factor_CO2 = 1.25
    offshore_factor = 1.3
    categories = ["MAT", "LAB", "ROW", "MISC", "TOT"]
    model_name, model_func, region_args = MODEL_OPTIONS[model_name_key]
    costs_per_mile = []
    for cat in categories[:-1]:
        val = model_func(Dia, Lnth, *(region_args + (cat, 2011))) / Lnth
        if cat in ("MAT", "LAB"):
            val *= Factor_CO2
        costs_per_mile.append(val)
    costs_total = [v * Lnth for v in costs_per_mile]

    surge_tank_2000 = 701_600
    control_system_2000 = 94_000
    surge_tank_factor = 657.5 / 370.6
    control_system_factor = 438.7 / 368.5
    surge_tank_2011 = surge_tank_2000 * surge_tank_factor
    control_system_2011 = control_system_2000 * control_system_factor

    total_booster_2011, _ = cost_models.costbooster(Lnth)
    total_booster_pumps = total_booster_2011 * NumPumps

    costs_total_off = [x * offshore_factor for x in costs_total]
    surge_tank_off = surge_tank_2011 * offshore_factor
    control_system_off = control_system_2011 * offshore_factor
    costs_total_proj_off = [x * escalation_factor for x in costs_total_off]
    surge_tank_proj_off = surge_tank_off * escalation_factor
    control_system_proj_off = control_system_off * escalation_factor
    booster_proj = total_booster_pumps * escalation_factor
    total_capital_proj_off = (
        sum(costs_total_proj_off)
        + surge_tank_proj_off
        + control_system_proj_off
        + booster_proj
    )
    contingency_proj_off = total_capital_proj_off * (contingency_percent / 100)
    total_capital_proj_off_with_cont = total_capital_proj_off + contingency_proj_off

    cost_labels = [
        "Material", "Labor", "ROW-Damages", "Miscellaneous",
        "CO₂ Surge Tank", "Pipeline Control System",
        f"Booster station ({NumPumps} pump(s))",
        f"Contingency ({contingency_percent:.1f}%)",
    ]
    cost_values = [
        costs_total_proj_off[0],
        costs_total_proj_off[1],
        costs_total_proj_off[2],
        costs_total_proj_off[3],
        surge_tank_proj_off,
        control_system_proj_off,
        booster_proj,
        contingency_proj_off,
    ]

    return {
        "model_name": model_name,
        "cost_start_year": cost_start_year,
        "contingency_percent": contingency_percent,
        "total_capital_proj_off": total_capital_proj_off,
        "contingency_proj_off": contingency_proj_off,
        "total_capital_proj_off_with_cont": total_capital_proj_off_with_cont,
        "cost_labels": cost_labels,
        "cost_values": cost_values,
    }


# ---------------------------------------------------------------------------
# Render (Streamlit UI only -- no calculation)
# ---------------------------------------------------------------------------

def render_attribute_card(attrs: dict) -> None:
    st.markdown(f"#### {attrs['pipe_name']}")

    r1 = st.columns(4)
    r1[0].metric("Length (km)", f"{attrs['length_km']:.2f}")
    r1[1].metric("OD (in)", f"{attrs['od_in']:.2f}")
    r1[2].metric("ID (in)", f"{attrs['id_in']:.2f}")
    r1[3].metric("Thickness (mm)", f"{attrs['thickness_mm']:.2f}")

    r2 = st.columns(4)
    r2[0].metric("Grade", attrs['pipe_grade'])
    r2[1].metric("In Service Since", str(attrs['start_year']))
    r2[2].metric("Status", attrs['status'])
    show_end_date = attrs['status'].upper() in {"NOT IN USE", "ABANDONED"} and attrs['end_date_str']
    r2[3].metric("End of Operation", attrs['end_date_str'] if show_end_date else "—")


def render_key_results_summary(transport_results: Optional[dict], corrosion_results: Optional[dict]) -> None:
    """Compact headline-results row shown below the attribute card.

    Purely a layout fix: the map runs 600px tall while the attribute card
    above only fills roughly half that, leaving a large empty block in the
    right column. This carries the three top-line numbers a user most wants
    at a glance, without duplicating the full detail already in the tabs
    below -- it reads live off st.session_state, so it fills in immediately
    once Run Analysis has been clicked (no separate compute here).
    """
    st.markdown("##### Key Results")
    if not transport_results or not corrosion_results:
        st.caption("Click **Run Analysis** in the sidebar to see headline results here.")
        return

    m = st.columns(3)
    m[0].metric("Max Flow", f"{transport_results['qm_max_Mtpy']:.2f} Mt/yr")
    m[1].metric("Corrosion Rate", f"{corrosion_results['corrosion_rate']:.3f} mm/yr")
    if corrosion_results["years_for_CO2"] is not None:
        m[2].metric("Repurposing Life", f"{corrosion_results['years_for_CO2']:.1f} yrs")
    else:
        m[2].metric("Repurposing Life", "—")


def render_transport_tab(results: Optional[dict]) -> None:
    if not results:
        st.info("Click **Run Analysis** in the sidebar to compute transport capacity.")
        return
    if results.get("error"):
        st.error(results["error"])
        return

    m = st.columns(3)
    m[0].metric("Max Flow Rate", f"{results['qm_max_Mtpy']:.2f} Mt/yr", help=f"{results['qm_max']:.1f} kg/s")
    m[1].metric("Required Flow Rate", f"{results['required_qm_max']:.2f} Mt/yr",
                help=f"{results['required_qm_max_kgps']:.1f} kg/s")
    m[2].metric("Verdict", "Suitable" if results["suitable"] else "Not suitable")

    with st.expander("Detail", expanded=False):
        st.markdown(f"**Average pressure:** {results['p_avg']:.4f} MPa")
        st.markdown(f"- Density: {results['density']:.4f} kg/m³")
        st.markdown(f"- Viscosity: {results['viscosity']:.4f} μPa·s")
        st.markdown(f"- Compressibility factor (Z): {results['z_factor']:.6f}")
        st.markdown(f"**Final Fanning friction factor:** {results['ff']:.6f}")
        st.markdown(f"**Final Reynolds number:** {results['Re']:.2e}")
        st.markdown(
            f"**Pipe used:** Nominal {results['od_in']:.1f}\" | "
            f"Standard Inner Diameter: {results['Dia_in_nom_in']:.3f}\" ({results['Dia_in_nom_m']:.4f} m)"
        )


def render_corrosion_tab(results: Optional[dict]) -> None:
    if not results:
        st.info("Click **Run Analysis** in the sidebar to compute corrosion & lifetime.")
        return

    m = st.columns(3)
    m[0].metric("Corrosion Rate", f"{results['corrosion_rate']:.3f} mm/yr")
    m[1].metric("Thickness Available", f"{results['thickness_available']:.2f} mm")
    if results["years_for_CO2"] is not None:
        m[2].metric("Repurposing Lifetime", f"{results['years_for_CO2']:.1f} yrs")
    else:
        m[2].metric("Repurposing Lifetime", "—")

    with st.expander("Detail", expanded=False):
        st.markdown(f"**Years considered for corrosion:** {results['years']} years ({results['years_label']})")
        st.markdown(f"**Estimated total thickness lost to corrosion:** {results['thickness_corroded']:.2f} mm")
        st.markdown(f"**Minimum required wall thickness (Tmin):** {results['Tmin']:.2f} mm")
        st.markdown(f"**Current wall thickness after corrosion:** {results['current_thickness']:.2f} mm")
        st.markdown(f"**In-situ pH:** {results['pH']:.2f}")
        if results["years_for_CO2"] is None:
            st.warning("Corrosion rate for CO₂ must be greater than zero to estimate years for CO₂ transport.")


def render_cost_tab(results: Optional[dict]) -> None:
    if not results:
        st.info("Click **Run Analysis** in the sidebar to compute the cost model.")
        return

    m = st.columns(3)
    m[0].metric("Total Capital Cost", f"${results['total_capital_proj_off']:,.0f}")
    m[1].metric(f"Contingency ({results['contingency_percent']:.1f}%)",
                f"${results['contingency_proj_off']:,.0f}")
    m[2].metric("Total with Contingency", f"${results['total_capital_proj_off_with_cont']:,.0f}")

    with st.expander("Detail", expanded=False):
        st.markdown(f"**Model:** {results['model_name']} (capital costs {results['cost_start_year']})")
        for label, value in zip(results["cost_labels"], results["cost_values"]):
            st.markdown(f"- {label}: ${value:,.0f}")

    col_bar, col_pie = st.columns(2, gap="large")
    bar_png = charts.render_stacked_bar_png(results["cost_labels"], results["cost_values"])
    pie_png = charts.render_donut_png(results["cost_labels"], results["cost_values"])
    with col_bar:
        st.image(bar_png, caption="Stacked Cost Breakdown", width=charts.CHART_WIDTH_PX)
    with col_pie:
        st.image(pie_png, caption="Cost Share by Category", width=charts.CHART_WIDTH_PX)
