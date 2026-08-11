"""Multiphase flow properties and CO2 internal corrosion rate (NORSOK M-506).

Extracted verbatim (formulas and constants unchanged) from streamlit_map_eva11.py.

Note: LAMDA, viscosity_mixture_u_mi, density_mix, convert_bicarb_mgL_to_molL,
convert_ionic_gL_to_molL, and fpH_FixT are not part of the caller's explicitly
requested public list, but fpH_FixT is a required dependency of fpH_Cal, and the
other four are called directly by the eva11.py corrosion panel alongside the
requested functions. See the accompanying summary for details.
"""
import math

import numpy as np


def v_sl(QL_m3d: float, D_m: float) -> float:
    """Superficial liquid velocity in a pipe.

    Units in: QL_m3d (liquid rate) in m3/day, D_m (internal diameter) in m
    Units out: m/s
    """
    QL_m3s = QL_m3d / (24 * 3600)
    area = np.pi / 4 * D_m**2
    vsl = QL_m3s / area
    return vsl


def v_sg(QG_Mm3d: float, sp_gr: float, rho_G: float, D: float) -> float:
    """Superficial gas velocity in a pipe.

    Units in: QG_Mm3d (gas rate) in million m3/day, sp_gr (gas specific gravity, air=1),
              rho_G (in-situ gas density) in kg/m3, D (internal diameter) in m
    Units out: m/s
    """
    rho_GSC = 2.7 * 14.5 * sp_gr * 16.018 / 520
    QG_m3s = QG_Mm3d * 1_000_000 / (24 * 3600)
    area = np.pi / 4 * D ** 2
    vsg = QG_m3s * rho_GSC / (rho_G * area)
    return vsg


def v_m(v_sl: float, v_sg: float) -> float:
    """Mixture (superficial) velocity.

    Units in: v_sl, v_sg in m/s
    Units out: m/s
    """
    return v_sl + v_sg


def viscosity_liquid_ul(WC: float, uo: float, ug: float, uw: float, phi_c: float, u_relmax: float) -> float:
    """Effective liquid-phase viscosity for an oil/water mixture (Volume-of-Fluid / Brinkman-type model).

    Units in: WC (water cut, fraction 0-1), uo/ug/uw (oil/gas/water viscosity, cP),
              phi_c (dimensionless phase-inversion water cut), u_relmax (dimensionless)
    Units out: cP
    """
    R = uw / uo
    KO_Wet = phi_c / 1.187 / (1 - 1 / (u_relmax ** 0.4))
    KW_Wet = (1 - phi_c) / 1.187 / (1 - ((R / u_relmax) ** 0.4))
    WC_KW = (1 - WC) / KW_Wet
    WC_KOIL = WC / KO_Wet
    if WC < phi_c:
        REL_VISC_MIX = (1 + (WC_KOIL / (1.187 - WC_KOIL))) ** 2.5
    else:
        REL_VISC_MIX = R * (1 + (WC_KW / (1.187 - WC_KW))) ** 2.5
    ul = REL_VISC_MIX * uo
    return ul


def LAMDA(v_sl: float, u_m: float) -> float:
    """No-slip liquid holdup (input liquid fraction).

    Units in: v_sl in m/s, u_m (mixture velocity) in m/s
    Units out: dimensionless (0-1)
    """
    return v_sl / u_m if u_m != 0 else 0.0


def viscosity_mixture_u_mi(LAMDA: float, ul: float, ug: float) -> float:
    """No-slip mixture viscosity.

    Units in: LAMDA (no-slip liquid holdup, 0-1), ul (liquid viscosity) in cP, ug (gas viscosity) in cP
    Units out: cP
    """
    u_mi = LAMDA * ul + (1 - LAMDA) * ug
    return u_mi


def density_mix(rho_oil: float, rho_gas: float, rho_water: float, WC: float, lamda: float) -> float:
    """No-slip mixture density.

    Units in: rho_oil, rho_gas, rho_water in kg/m3, WC (water cut, 0-1), lamda (no-slip liquid holdup, 0-1)
    Units out: kg/m3
    """
    rho_l = rho_water * WC + rho_oil * (1 - WC)
    rho_mix = lamda * rho_l + (1 - lamda) * rho_gas
    return rho_mix


def friction_factor(k: float, D: float, vmix: float, rho_mixture: float, u_mi: float) -> float:
    """Multiphase flow friction factor.

    Units in: k (pipe roughness) same length unit as D, D (internal diameter) in m,
              vmix (mixture velocity) in m/s, rho_mixture in kg/m3, u_mi (mixture viscosity) in cP
    Units out: dimensionless
    """
    u_mi_Pa_s = u_mi / 1000
    term1 = 20000 * k / D
    term2 = 1e6 * u_mi_Pa_s / (rho_mixture * vmix * D)
    exponent = (term1 + term2) ** 0.33
    f = 0.001375 * (1 + exponent)
    return f


def shear_stress(rho_mixture: float, vmix: float, f: float) -> float:
    """Wall shear stress for multiphase flow.

    Units in: rho_mixture in kg/m3, vmix (mixture velocity) in m/s, f (friction factor) dimensionless
    Units out: Pa
    """
    S = 0.5 * rho_mixture * f * (vmix ** 2)
    return S


def convert_bicarb_mgL_to_molL(bicarb_mgL: float) -> float:
    """Convert bicarbonate concentration from mg/L (as NaHCO3) to mol/L.

    Units in: mg/L
    Units out: mol/L
    """
    M_NaHCO3 = 84.01
    return bicarb_mgL / 1000 / M_NaHCO3


def convert_ionic_gL_to_molL(ionic_gL: float) -> float:
    """Convert ionic strength / salinity from g/L (as NaCl) to mol/L.

    Units in: g/L
    Units out: mol/L
    """
    M_NaCl = 58.44
    return ionic_gL / M_NaCl


def fugacity_co2(P_bar: float, T_C: float, mole_percent_CO2: float) -> float:
    """CO2 fugacity in a gas mixture at pipeline conditions.

    Source: NORSOK M-506 CO2 fugacity correlation.
    Units in: P_bar (total pressure) in bar, T_C in degrees C, mole_percent_CO2 in %
    Units out: bar
    """
    T_K = T_C + 273.15
    P_use = P_bar if P_bar <= 250 else 250
    a = 10 ** (P_use * (0.0031 - 1.4 / T_K))
    pCO2 = (mole_percent_CO2 / 100) * P_bar
    f_CO2 = a * pCO2
    return f_CO2


def pHCalculator1(Temp: float, Pressure: float, fugacity_CO2: float, Bicarb: float,
                   IonicStrength: float, CalcOfpH: int = 1) -> float:
    """In-situ pH of a CO2-saturated brine, from carbonate equilibrium chemistry.

    Source: NORSOK M-506 (associated pH-of-water calculation for CO2 corrosion modelling).
    Units in: Temp in degrees C, Pressure in bar, fugacity_CO2 in bar,
              Bicarb in mol/L, IonicStrength in mol/L, CalcOfpH selects the equilibrium branch
    Units out: pH (dimensionless)
    """
    T_K = Temp + 273.15
    P_psi = Pressure * 14.5038
    T_F = Temp * 1.8 + 32
    if Temp <= 80:
        KH = 55.5084 / (np.exp(4.8 + 3934.4/T_K - 941290.2/T_K**2)) * 10 ** (-0.00001234*P_psi - 0.107*IonicStrength)
    else:
        KH = 55.5084 / (np.exp(1713.53*(1-T_K/647)**(1/3)/T_K + 3.875 + 3680.09/T_K - 1198506.1/T_K**2)) * 10 ** (-0.00002564*P_psi - 0.491*IonicStrength**0.5 + 0.379*IonicStrength - 0.06506*IonicStrength**1.5 - 0.001458*IonicStrength*T_F)

    K0 = 0.00258
    log10 = np.log10
    K1 = (1 / K0) * 10 ** (
        -356.3094 - 0.06091964*T_K + 21834.37/T_K + 126.8339*log10(T_K)
        - 1684915/T_K**2
        - (-0.00002564*P_psi - 0.491*IonicStrength**0.5 + 0.379*IonicStrength - 0.06506*IonicStrength**1.5 - 0.001458*IonicStrength*T_F)
    )
    K2 = 10 ** (
        -107.8871 - 0.03252849*T_K + 5151.79/T_K + 38.92561*log10(T_K)
        - 563713.9/T_K**2
        - (-2.118e-5*P_psi - 1.255*IonicStrength**0.5 + 0.867*IonicStrength - 0.174*IonicStrength**1.5 - 0.001588*T_F*IonicStrength)
    )
    Ksp_FeCO3 = 10 ** (-(10.13 + 0.0182*Temp - 2.44*IonicStrength**0.5 + 0.72*IonicStrength))
    Kw = 10 ** (-(29.3868 - 0.0737549*T_K + 7.47881e-5*T_K**2))
    CO2_conc = KH * fugacity_CO2
    if CalcOfpH == 2:
        SatpHCoeff = 2 * Ksp_FeCO3 / (KH * K0 * K1 * K2 * fugacity_CO2)
    else:
        SatpHCoeff = 0
    Hion = 10 ** -3.5
    if fugacity_CO2 > 20:
        Hion = 10 ** -2.9
    for _ in range(100):
        fHion = (SatpHCoeff * Hion ** 4
                 + Hion ** 3
                 + Bicarb * Hion ** 2
                 - Hion * (K1 * K0 * KH * fugacity_CO2 + Kw)
                 - 2 * K1 * K2 * K0 * KH * fugacity_CO2)
        fdHion = (4 * SatpHCoeff * Hion ** 3
                  + 3 * Hion ** 2
                  + 2 * Bicarb * Hion
                  - (K1 * K0 * KH * fugacity_CO2 + Kw))
        oldHion = Hion
        if fdHion == 0:
            break
        Hion = oldHion - fHion / fdHion
        if Hion <= 0:
            Hion = 1e-14
        if abs(Hion - oldHion) < 1e-6 * oldHion:
            break
    pH = -np.log10(Hion) if Hion > 0 else 14.0
    return pH


def fpH_FixT(tempe: float, iph: float) -> float:
    """pH-correction factor f(pH) at one of NORSOK M-506's fixed reference temperatures.

    Source: NORSOK M-506, piecewise f(pH) vs. temperature table.
    Units in: tempe in degrees C (must be one of the NORSOK reference temperatures), iph (pH, dimensionless)
    Units out: dimensionless correction factor

    Internal helper used by fpH_Cal to interpolate between reference temperatures.
    """
    # (Your piecewise function for f(pH) at each temperature goes here)
    tempo = 7
    if tempe==5.0:
        if (iph>=3.5) and (iph<=4.6): tempo = 2.0676 + 0.2309 * iph
        if (iph>4.6) and (iph<=6.5): tempo = 4.342 - (1.061 * iph) + (0.0708 * iph ** 2)
    if tempe==15.0:
        if (iph>=3.5) and (iph<=4.6): tempo= 2.0676 - (0.2309 * iph)
        if (iph>4.6) and (iph<=6.5): tempo= 4.986 - (1.191 * iph) + (0.0708 * iph ** 2)
    if tempe==20.0:
        if (iph>=3.5) and (iph<=4.6): tempo= 2.0676 - (0.2309 * iph)
        if (iph>4.6) and (iph<=6.5): tempo= 5.1885 - (1.2353 * iph) + (0.0708 * iph ** 2)
    if tempe==40.0:
        if (iph>=3.5) and (iph<=4.6): tempo= 2.0676 - (0.2309 * iph)
        if (iph>4.6) and (iph<=6.5): tempo= 5.1885 - (1.2353 * iph) + (0.0708 * iph ** 2)
    if tempe==60.0:
        if (iph>=3.5) and (iph<=4.6): tempo= 1.836 - (0.1818 * iph)
        if (iph>4.6) and (iph<=6.5): tempo= 15.444 - (6.1291 * iph) + (0.8204 * iph ** 2) - (0.0371 * iph ** 3)
    if tempe==80.0:
        if (iph>=3.5) and (iph<=4.6): tempo= 2.6727 - (0.3636 * iph)
        if (iph>4.6) and (iph<=6.5): tempo= 331.68 * math.exp(-1.2618 * iph)
    if tempe==90.0:
        if (iph>=3.5) and (iph<=4.57): tempo= 3.1355 - (0.4673 * iph)
        if (iph>4.57) and (iph<=5.62): tempo= 21254 * math.exp(-2.1811 * iph)
        if (iph>5.62) and (iph<=6.5): tempo= 0.4014 - (0.0538 * iph)
    if tempe==120.0:
        if (iph>=3.5) and (iph<=4.3): tempo = 1.5375 - (0.125 * iph)
        if (iph>4.3) and (iph<=5.0): tempo= 5.9757 - 1.157 * iph
        if (iph>5.0) and (iph<=6.5): tempo=  0.546125 - (0.071225 * iph)
    if tempe==150.0:
        if (iph>=3.5) and (iph<=3.8): tempo = 1
        if (iph>3.8) and (iph<=5.0): tempo= 17.634 - (7.0945 * iph) + (0.715 * iph ** 2)
        if (iph>5.0) and (iph<=6.5): tempo=  0.037
    return tempo


def fpH_Cal(Tempe: float, IpH: float) -> float:
    """pH-correction factor f(pH), interpolated to the actual operating temperature.

    Source: NORSOK M-506, f(pH) vs. temperature table (linear interpolation between
    the fixed reference temperatures handled by fpH_FixT).
    Units in: Tempe in degrees C, IpH (pH, dimensionless)
    Units out: dimensionless correction factor
    """
    TempRange = [5.0, 15.0, 20.0, 40.0, 60.0, 80.0, 90.0, 120.0, 150.0]
    loc=0
    for i, temp_i in enumerate(TempRange):
        if temp_i > Tempe:
            loc=i
            break
    TempLower = TempRange[loc - 1]
    TempUpper = TempRange[loc]
    fpHLower = fpH_FixT(TempLower, IpH)
    fpHUpper = fpH_FixT(TempUpper, IpH)
    tempo = (fpHUpper - fpHLower) / (TempUpper - TempLower)
    tempo = fpHLower + (Tempe - TempLower) * tempo
    return tempo


def Kt(temp: float) -> float:
    """Temperature constant Kt for the NORSOK M-506 corrosion rate equation.

    Source: NORSOK M-506, Kt vs. temperature lookup table (linear interpolation).
    Units in: temp in degrees C
    Units out: dimensionless
    """
    temp_table=(5,15,20, 40, 60, 80,90, 120, 150)
    value_table=(0.42,1.59,4.762,8.927,10.695,9.949,6.250,7.770,5.203)
    for i,temp_i in enumerate(temp_table):
        if temp<temp_i:
            temp_lower=temp_table[i-1]
            temp_upper=temp_table[i]
            value_lower=value_table[i-1]
            value_upper=value_table[i]
            break
    return value_lower+ abs(value_upper-value_lower)/abs(temp_upper-temp_lower)


def Corrosion_Norsok(Kt: float, FugacityofCO2: float, shearstress: float, fpH_Cal: float) -> float:
    """CO2 internal corrosion rate.

    Source: NORSOK M-506 corrosion rate equation.
    Units in: Kt dimensionless, FugacityofCO2 in bar, shearstress in Pa, fpH_Cal dimensionless
    Units out: mm/year
    """
    if FugacityofCO2 > 0:
        exponent = 0.146 + 0.0324 * math.log10(FugacityofCO2)
        corrosion = Kt * FugacityofCO2**0.62 * (shearstress / 19)**exponent * fpH_Cal
    else:
        corrosion = 0.0
    return corrosion
