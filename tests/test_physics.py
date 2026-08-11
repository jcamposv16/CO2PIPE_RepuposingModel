"""Regression tests for the co2pipe.physics / co2pipe.economics modules.

Expected values were captured by executing the UNMODIFIED original function
definitions from src/streamlit_map_eva11.py (lines 1-1575, before any Streamlit
or data-loading code), called with the same inputs used below -- see the
capture script that produced these numbers for the exact procedure. Every
assertion here exists to prove the extraction into co2pipe.* did not change a
single formula, constant, or default value.

Inputs mirror the app's default UI values where the panel supplies them
(transport panel: p_in=2200 psia, p_out=1200 psia, temp=12 C; corrosion panel:
QL=1000 m3/d, QG=5 Mm3/d, WC=0.10, Temp=13 C, Pressure=50 bar, %CO2=1) and
representative example values elsewhere (e.g. a 6" pipe, a 20"/50-mile line).
"""
import pytest

from co2pipe.physics import units, co2_properties, hydraulics, pipe_sizing, corrosion
from co2pipe.economics import cost_models

APPROX = dict(rel=1e-12)


# ---------------------------------------------------------------------------
# units.py
# ---------------------------------------------------------------------------

def test_flowrate_Mtpy_to_kgps():
    assert units.flowrate_Mtpy_to_kgps(4.3) == pytest.approx(136.3521055301877, **APPROX)


def test_psia_to_mpa():
    assert units.psia_to_mpa(2200.0) == pytest.approx(15.168465399999999, **APPROX)
    assert units.psia_to_mpa(1200.0) == pytest.approx(8.2737084, **APPROX)


def test_Conv_Lpipeline():
    assert units.Conv_Lpipeline(100.0) == pytest.approx(160934.4, **APPROX)


def test_Conv_temp():
    assert units.Conv_temp(12.0) == pytest.approx(285.15, **APPROX)


def test_Conv_Dpipeline():
    assert units.Conv_Dpipeline(6.0, 'in', 'm') == pytest.approx(0.15239991770404443, **APPROX)
    assert units.Conv_Dpipeline(0.1524, 'm', 'in') == pytest.approx(6.000003240000001, **APPROX)
    assert units.Conv_Dpipeline(5.0, 'in', 'in') == pytest.approx(5.0, **APPROX)
    with pytest.raises(ValueError):
        units.Conv_Dpipeline(5.0, 'in', 'ft')


# ---------------------------------------------------------------------------
# co2_properties.py
# ---------------------------------------------------------------------------

_TMP = units.Conv_temp(12.0)
_P_IN = units.psia_to_mpa(2200.0)
_P_OUT = units.psia_to_mpa(1200.0)
_P_AVG = hydraulics.pav_gas(_P_IN, _P_OUT)


def test_vpSWCO2():
    assert co2_properties.vpSWCO2(_TMP) == pytest.approx(4.7297050250489, **APPROX)


def test_denslSWCO2():
    assert co2_properties.denslSWCO2(_TMP) == pytest.approx(845.8484129747935, **APPROX)


def test_volPRCO2():
    assert co2_properties.volPRCO2(0, _P_AVG, _TMP) == pytest.approx(4.759606637233073e-05, **APPROX)


def test_volDuanCO2():
    assert co2_properties.volDuanCO2(0, _P_AVG, _TMP) == pytest.approx(4.777202262028304e-05, **APPROX)


def test_zfactDuanCO2():
    assert co2_properties.zfactDuanCO2(0, _P_AVG, _TMP) == pytest.approx(0.2429986584191486, **APPROX)


def test_denDuanCO2():
    assert co2_properties.denDuanCO2(0, _P_AVG, _TMP) == pytest.approx(921.2400393805904, **APPROX)


def test_visFWVCO2():
    density = co2_properties.denDuanCO2(0, _P_AVG, _TMP)
    assert co2_properties.visFWVCO2(density, _TMP) == pytest.approx(97.18196206335165, **APPROX)


# ---------------------------------------------------------------------------
# hydraulics.py
# ---------------------------------------------------------------------------

_ETA = units.Conv_Dpipeline(0.0018, 'in', 'm')
_DIA_G = units.Conv_Dpipeline(6.0, 'in', 'm')
_VISC_UPAS = co2_properties.visFWVCO2(co2_properties.denDuanCO2(0, _P_AVG, _TMP), _TMP)
_VISC_PAS = _VISC_UPAS * 1e-6


def test_pav_gas():
    assert hydraulics.pav_gas(_P_IN, _P_OUT) == pytest.approx(12.059065184313724, **APPROX)


def test_reynolds_number():
    re = hydraulics.reynolds_number(50.0, _VISC_PAS, _DIA_G)
    assert re == pytest.approx(4298428.701502954, **APPROX)


def test_fanning_friction_factor():
    re = hydraulics.reynolds_number(50.0, _VISC_PAS, _DIA_G)
    haaland = hydraulics.fanning_friction_factor(_DIA_G, re, _ETA, 0)
    zigrang_sylvester = hydraulics.fanning_friction_factor(_DIA_G, re, _ETA, 1)
    assert haaland == pytest.approx(0.0037809568512980098, **APPROX)
    assert zigrang_sylvester == pytest.approx(0.003779794365587452, **APPROX)


def test_fanning_friction_colebrook():
    re = hydraulics.reynolds_number(50.0, _VISC_PAS, _DIA_G)
    ff = hydraulics.fanning_friction_colebrook(re, _DIA_G, _ETA)
    assert ff == pytest.approx(0.003779794937831668, **APPROX)


# ---------------------------------------------------------------------------
# pipe_sizing.py
# ---------------------------------------------------------------------------

def test_Pipe_Size():
    assert pipe_sizing.Pipe_Size(6.0, 'in') == 6


def test_Dia_in_nom():
    assert pipe_sizing.Dia_in_nom(6.0, 'in') == 6


def test_Pthick_nom():
    assert pipe_sizing.Pthick_nom(6.0, 'in') == pytest.approx(0.28, **APPROX)


def test_get_minimum_yield_strength():
    assert pipe_sizing.get_minimum_yield_strength('X60') == 60000
    with pytest.raises(ValueError):
        pipe_sizing.get_minimum_yield_strength('NOPE')


def test_temp_derating_factor():
    assert pipe_sizing.temp_derating_factor(150.0) == pytest.approx(0.9656546762589928, **APPROX)


def test_tmin():
    pressure_pa = 50.0 * 100000
    result = pipe_sizing.tmin(pressure_pa, 0.1524, 12.0, 'X60')
    assert result == pytest.approx(1.27915176807379, **APPROX)


# ---------------------------------------------------------------------------
# corrosion.py (full NORSOK M-506 chain, mirroring the corrosion panel exactly)
# ---------------------------------------------------------------------------

def test_corrosion_norsok_chain():
    QL, QG, WC, Temp, Pressure, mole_percent_CO2 = 1000.0, 5.0, 0.10, 13.0, 50.0, 1.0
    sp_gr, rho_G, uo, ug, uw = 0.8, 200, 1.1, 0.03, 1.002
    phi_c, u_relmax = 0.5, 7.06
    rho_oil, rho_water, k = 850, 1024, 0.00005
    Bicarb, IonicStrength, CalcOfpH = 0, 50, 1
    D = 6.0 / 39.3701

    vsl = corrosion.v_sl(QL, D)
    vsg = corrosion.v_sg(QG, sp_gr, rho_G, D)
    vmix = corrosion.v_m(vsl, vsg)
    ul = corrosion.viscosity_liquid_ul(WC, uo, ug, uw, phi_c, u_relmax)
    lamda_ = corrosion.LAMDA(vsl, vmix)
    u_mi = corrosion.viscosity_mixture_u_mi(lamda_, ul, ug)
    rho_mixture = corrosion.density_mix(rho_oil, rho_G, rho_water, WC, lamda_)
    f = corrosion.friction_factor(k, D, vmix, rho_mixture, u_mi)
    S = corrosion.shear_stress(rho_mixture, vmix, f)
    bicarb_moll = corrosion.convert_bicarb_mgL_to_molL(Bicarb)
    ionic_moll = corrosion.convert_ionic_gL_to_molL(IonicStrength)
    fugacity = corrosion.fugacity_co2(Pressure, Temp, mole_percent_CO2)
    pH = corrosion.pHCalculator1(Temp, Pressure, fugacity, bicarb_moll, ionic_moll, CalcOfpH)
    fpH = corrosion.fpH_Cal(Temp, pH)
    Kt_value = corrosion.Kt(Temp)
    corrosion_rate = corrosion.Corrosion_Norsok(Kt_value, fugacity, S, fpH)

    assert vsl == pytest.approx(0.6344931111104107, **APPROX)
    assert vsg == pytest.approx(15.303600465190806, **APPROX)
    assert vmix == pytest.approx(15.938093576301217, **APPROX)
    assert ul == pytest.approx(1.4657739045766545, **APPROX)
    assert lamda_ == pytest.approx(0.03980984978365642, **APPROX)
    assert u_mi == pytest.approx(0.08715794346449046, **APPROX)
    assert rho_mixture == pytest.approx(226.5690937456123, **APPROX)
    assert f == pytest.approx(0.003953313907710813, **APPROX)
    assert S == pytest.approx(113.76396415809482, **APPROX)
    assert bicarb_moll == pytest.approx(0.0, **APPROX)
    assert ionic_moll == pytest.approx(0.8555783709787816, **APPROX)
    assert fugacity == pytest.approx(0.4067645160862029, **APPROX)
    assert pH == pytest.approx(3.988375877771213, **APPROX)
    assert fpH == pytest.approx(1.5150504058935763, **APPROX)
    assert Kt_value == pytest.approx(0.537, **APPROX)
    assert corrosion_rate == pytest.approx(0.5913367082519982, **APPROX)


# ---------------------------------------------------------------------------
# economics/cost_models.py
# ---------------------------------------------------------------------------

_DIA, _LNTH = 20.0, 50.0


def test_costpipe():
    assert cost_models.costpipe(_LNTH * 1.60934, _DIA) == pytest.approx(67042543.91999999, **APPROX)


def test_costbooster_returns_tuple():
    # Regression guard for the duplicate `costbooster` definition found in eva11.py:
    # only the second (length_mi -> tuple) definition was ever live/callable.
    total, per_mile = cost_models.costbooster(_LNTH)
    assert total == pytest.approx(11330123.56321839, **APPROX)
    assert per_mile == pytest.approx(226602.4712643678, **APPROX)


def test_CpParker():
    assert cost_models.CpParker(_DIA, _LNTH, 'TOT', 2011) == pytest.approx(69462178.64360408, **APPROX)


def test_CpRui():
    assert cost_models.CpRui(_DIA, _LNTH, 'AVG', 'TOT', 2011) == pytest.approx(38586567.6978913, **APPROX)


def test_CpRui1():
    assert cost_models.CpRui1(_DIA, _LNTH, 'CEN', 'TOT', 2011) == pytest.approx(25931734.169189677, **APPROX)


def test_CpMcCoy():
    assert cost_models.CpMcCoy(_DIA, _LNTH, 'AVG', 'TOT', 2011) == pytest.approx(46564754.27198777, **APPROX)


def test_CpMcCoy1():
    assert cost_models.CpMcCoy1(_DIA, _LNTH, 'MW', 'TOT', 0) == pytest.approx(37755915.81965901, **APPROX)


def test_CpBrown():
    assert cost_models.CpBrown(_DIA, _LNTH, 'AVG', 'TOT', 2011) == pytest.approx(45625572.51008891, **APPROX)


def test_CpBrown1():
    assert cost_models.CpBrown1(_DIA, _LNTH, 'NE', 'TOT', 0) == pytest.approx(94106127.7188534, **APPROX)


def test_escalation_factor():
    assert cost_models.escalation_factor(3.0, 2025) == pytest.approx(1.512589724855112, **APPROX)
