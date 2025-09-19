import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import pandas as pd
import json
import numpy as np
import math
import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from io import BytesIO




# ---- ALL YOUR PIPELINE & FLUID PROPERTY FUNCTIONS HERE ----



def vpSWCO2(tmp):

    # Critical properties of CO2
    tmpcrit = 304.1282  # Critical temperature (K)
    prescrit = 7.3773   # Critical pressure (MPa)

    # Coefficients from Span and Wagner (1996)
    a1 = -7.0602087
    a2 = 1.9391218
    a3 = -1.6463597
    a4 = -3.2995634

    # Exponents for the Span-Wagner equation
    n1 = 1.0
    n2 = 1.5
    n3 = 2.0
    n4 = 4.0

    # Reduced temperature
    Tr = tmp / tmpcrit

    # Compute the summation term of Span-Wagner equation
    sum_terms = (
        a1 * (1 - Tr)**n1 +
        a2 * (1 - Tr)**n2 +
        a3 * (1 - Tr)**n3 +
        a4 * (1 - Tr)**n4
    )

    # Calculate vapor pressure
    vp = prescrit * np.exp((tmpcrit / tmp) * sum_terms)

    return vp

def denslSWCO2(tmp):

    tmpcrit = 304.1282  # Critical temperature (K)
    dencrit = 467.6     # Critical density (kg/m3)

    a = [1.9245108, -0.62385555, -0.32731127, 0.39245142]
    n = [0.34, 0.5, 10/6, 11/6]

    Tr = tmp / tmpcrit
    sum_terms = sum(a[i] * (1 - Tr)**n[i] for i in range(4))

    density = dencrit * np.exp(sum_terms)

    return density

def densvSWCO2(tmp):

    tmpcrit = 304.1282  # Critical temperature (K)
    dencrit = 467.6     # Critical density (kg/m3)

    a = [-1.7074879, -0.8227467, -4.6008549, -10.111178, -29.742252]
    n = [0.34, 0.5, 1.0, 7/3, 14/3]

    Tr = tmp / tmpcrit
    sum_terms = sum(a[i] * (1 - Tr)**n[i] for i in range(5))
    density = dencrit * np.exp(sum_terms)

    return density

def fvolPRCO2(vol, pres, tmp):

    Rgas = 0.000008314  # Universal gas constant (m3-MPa/K-mol)
    tmpcrit = 304.1282  # Critical temperature (K)
    prescrit = 7.3773   # Critical pressure (MPa)
    waf = 0.22394       # Acentric factor

    m1 = 0.37464 + 1.54226 * waf - 0.26992 * waf ** 2
    a1 = 0.45724 * (Rgas * tmpcrit) ** 2 * (1 + m1 * (1 - np.sqrt(tmp / tmpcrit))) ** 2 / prescrit
    b1 = 0.0778 * Rgas * tmpcrit / prescrit

    result = (
        pres * vol ** 3
        + (pres * b1 - Rgas * tmp) * vol ** 2
        + (a1 - 3 * pres * b1 ** 2 - 2 * Rgas * tmp * b1) * vol
        + pres * b1 ** 3 + Rgas * tmp * b1 ** 2 - a1 * b1
    )
    return result

def d1fvolPRCO2(vol, pres, tmp):

    Rgas = 0.000008314  # Universal gas constant (m3-MPa/K-mol)
    tmpcrit = 304.1282  # Critical temperature (K)
    prescrit = 7.3773   # Critical pressure (MPa)
    waf = 0.22394       # Acentric factor

    m1 = 0.37464 + 1.54226 * waf - 0.26992 * waf ** 2
    a1 = 0.45724 * (Rgas * tmpcrit) ** 2 * (1 + m1 * (1 - np.sqrt(tmp / tmpcrit))) ** 2 / prescrit
    b1 = 0.0778 * Rgas * tmpcrit / prescrit

    result = (
        3 * pres * vol ** 2
        + 2 * (pres * b1 - Rgas * tmp) * vol
        + (a1 - 3 * pres * b1 ** 2 - 2 * Rgas * tmp * b1)
    )
    return result

def volPRCO2(volinit, pres, tmp):

    # Universal gas constant (m3-MPa/K-mol)
    Rgas = 0.000008314
    # Desired accuracy of result
    tol = 1e-5

    # Properties of CO2
    tmpcrit = 304.1282   # Critical temperature (K)
    prescrit = 7.3773    # Critical pressure (MPa)
    dencrit = 467.6      # Critical density (kg/m3)
    MW = 44.0095         # Molecular weight (g/mol)
    volcrit = MW * 0.001 / dencrit  # Critical molar volume (m3/mol)

    # Determine initial guess
    if volinit <= 0:
        vol1a = Rgas * tmp / pres
        # Determine if CO2 is in vapor, liquid or supercritical region
        if tmp > tmpcrit:
            if pres > prescrit:
                # In supercritical region: Initial guess should be smaller than critical molar volume
                if vol1a > 0.95 * volcrit:
                    vol1a = 0.95 * volcrit
            else:
                # In vapor region: Initial guess should be greater than critical molar volume
                if vol1a < 1.05 * volcrit:
                    vol1a = 1.05 * volcrit
        else:
            pvap = vpSWCO2(tmp)
            if pres > pvap:
                # In liquid region: Initial guess should be less than sat. liquid molar volume
                denlsat = denslSWCO2(tmp)
                vollsat = MW * 0.001 / denlsat
                if vol1a > 0.95 * vollsat:
                    vol1a = 0.95 * vollsat
            else:
                # In vapor region: Initial guess should be greater than sat. vapor molar volume
                denvsat = densvSWCO2(tmp)
                volvsat = MW * 0.001 / denvsat
                if vol1a < 1.05 * volvsat:
                    vol1a = 1.05 * volvsat
    else:
        vol1a = volinit

    # Determine molar volume using Newton-Raphson method

    # Outer loop: volume positivity and convergence, up to 100 attempts
    vol2 = None
    for i in range(100):
        if i == 0:
            pass  # do nothing, first guess already set
        else:
            if vol2 is not None and vol2 > 0:
                break
            else:
                vol1a = vol1a * 1.05
        vol1 = vol1a
        # Inner loop: Newton-Raphson, up to 1000 iterations
        for j in range(1000):
            f = fvolPRCO2(vol1, pres, tmp)
            df = d1fvolPRCO2(vol1, pres, tmp)
            if df == 0:
                # Avoid division by zero, reset guess
                vol1 = vol1 + 1e-5
                continue
            vol2 = vol1 - f / df
            reldif = abs(vol1 - vol2) / abs(vol2)
            if reldif <= tol:
                break
            else:
                vol1 = vol2
    return vol2

def denPRCO2(volinit, pres, tmp):

    MW = 44.0095  # Molecular weight of CO2 (g/mol)
    # Calculate molar volume in m3/mol, then convert to density
    mol_vol = volPRCO2(volinit, pres, tmp)
    density = MW * 0.001 / mol_vol

    return density

def zfactPRCO2(volinit, pres, tmp):

    Rgas = 0.000008314  # Universal gas constant (m3-MPa/(K-mol))
    mol_vol = volPRCO2(volinit, pres, tmp)  # Calculate molar volume
    z_factor = (pres * mol_vol) / (Rgas * tmp)

    return z_factor

def presPRCO2(vol, tmp):

    Rgas = 0.000008314  # Universal gas constant (m3-MPa/K-mol)
    tmpcrit = 304.1282  # Critical temperature (K)
    prescrit = 7.3773   # Critical pressure (MPa)
    waf = 0.22394       # Acentric factor

    m1 = 0.37464 + 1.54226 * waf - 0.26992 * waf ** 2
    a1 = 0.45724 * (Rgas * tmpcrit) ** 2 * (1 + m1 * (1 - np.sqrt(tmp / tmpcrit))) ** 2 / prescrit
    b1 = 0.0778 * Rgas * tmpcrit / prescrit

    numerator = Rgas * tmp
    denominator = vol - b1
    pressure_term = numerator / denominator
    attraction_term = a1 / (vol * (vol + b1) + b1 * (vol - b1))

    pres = pressure_term - attraction_term

    return pres

def compPRCO2(volinit, pres, tmp):

    Rgas = 0.000008314  # Universal gas constant (m3-MPa/K-mol)
    tmpcrit = 304.1282  # Critical temperature (K)
    prescrit = 7.3773   # Critical pressure (MPa)
    waf = 0.22394       # Acentric factor

    m1 = 0.37464 + 1.54226 * waf - 0.26992 * waf ** 2
    a1 = 0.45724 * (Rgas * tmpcrit) ** 2 * (1 + m1 * (1 - np.sqrt(tmp / tmpcrit))) ** 2 / prescrit
    b1 = 0.0778 * Rgas * tmpcrit / prescrit

    # Calculate molar volume at specified P, T
    vol = volPRCO2(volinit, pres, tmp)

    # Calculate derivative of pressure with respect to molar volume
    dP_dv = (
        -Rgas * tmp / (vol - b1) ** 2
        + a1 * (2 * vol + 2 * b1) / (vol * (vol + b1) + b1 * (vol - b1)) ** 2
    )

    # Compressibility calculation
    comp = (-1 / vol) * (1 / dP_dv)

    return comp

def fDuanCO2(vol, pres, tmp):

    Rgas = 0.08314467  # Universal gas constant (L-bar/K-mol)
    tmpcrit = 304.1282   # Critical temperature (K)
    prescrit = 7.3773    # Critical pressure (MPa)
    volcrit = Rgas * tmpcrit / (prescrit * 10)  # "Critical" molar volume (L/mol). prescrit * 10 to convert to bar.

    # Constants for Duan et al. CO2 equation of state
    a1 = 0.0899288497
    a2 = -0.494783127
    a3 = 0.0477922245
    a4 = 0.0103808883
    a5 = -0.0282516861
    a6 = 0.0949887563
    a7 = 0.00052060088
    a8 = -0.000293540971
    a9 = -0.00177265112
    a10 = -0.0000251101973
    a11 = 0.0000893353441
    a12 = 0.0000788998563
    a13 = -0.0166727022
    a14 = 1.398
    a15 = 0.0296

    # Reduced parameters
    Tr = tmp / tmpcrit
    Pr = pres / prescrit
    Vr = vol * 1000 / volcrit  # Convert m3/mol -> L/mol, then to reduced volume

    # Calculate intermediate values
    b1 = a1 + (a2 / Tr**2) + (a3 / Tr**3)
    b2 = a4 + (a5 / Tr**2) + (a6 / Tr**3)
    b3 = a7 + (a8 / Tr**2) + (a9 / Tr**3)
    b4 = a10 + (a11 / Tr**2) + (a12 / Tr**3)
    b5 = a13 / Tr**3

    # Calculate the nonlinear function
    result = (
        Pr * Vr**6 / Tr
        - Vr**5
        - b1 * Vr**4
        - b2 * Vr**3
        - b3 * Vr
        - b4
        - b5 * Vr * (a14 * Vr**2 + a15) * np.exp(-a15 / Vr**2)
    )
    return result

def d1fDuanCO2(vol, pres, tmp):

    Rgas = 0.08314467  # Universal gas constant (L-bar/K-mol)
    tmpcrit = 304.1282   # Critical temperature (K)
    prescrit = 7.3773    # Critical pressure (MPa)
    volcrit = Rgas * tmpcrit / (prescrit * 10)  # "Critical" molar volume (L/mol)

    # Constants for Duan et al. CO2 equation of state
    a1 = 0.0899288497
    a2 = -0.494783127
    a3 = 0.0477922245
    a4 = 0.0103808883
    a5 = -0.0282516861
    a6 = 0.0949887563
    a7 = 0.00052060088
    a8 = -0.000293540971
    a9 = -0.00177265112
    a10 = -0.0000251101973
    a11 = 0.0000893353441
    a12 = 0.0000788998563
    a13 = -0.0166727022
    a14 = 1.398
    a15 = 0.0296

    # Reduced parameters
    Tr = tmp / tmpcrit
    Pr = pres / prescrit
    Vr = vol * 1000 / volcrit  # Convert m3/mol -> L/mol, then to reduced volume

    # Calculate intermediate values
    b1 = a1 + (a2 / Tr**2) + (a3 / Tr**3)
    b2 = a4 + (a5 / Tr**2) + (a6 / Tr**3)
    b3 = a7 + (a8 / Tr**2) + (a9 / Tr**3)
    b4 = a10 + (a11 / Tr**2) + (a12 / Tr**3)
    b5 = a13 / Tr**3

    # d f / d Vr (Vr = reduced molar volume)
    exp_term = np.exp(-a15 / Vr**2)
    dfdVr = (
        6 * Pr * Vr**5 / Tr
        - 5 * Vr**4
        - 4 * b1 * Vr**3
        - 3 * b2 * Vr**2
        - b3
        - (3 * b5 * a14 * Vr**2 + b5 * a15) * exp_term
        - (b5 * a14 * Vr**3 + b5 * a15 * Vr) * (2 * a15 / Vr**3) * exp_term
    )

    # Need to return d f / d vol (Vr = vol * 1000 / volcrit)
    # d f / d vol = (1000 / volcrit) * d f / d Vr
    result = (1000 / volcrit) * dfdVr

    return result

def volDuanCO2(volinit, pres, tmp):

    # Universal gas constant (m3-MPa/K-mol)
    Rgas = 0.000008314
    # Desired accuracy of result
    tol = 1e-5

    # Properties of CO2
    tmpcrit = 304.1282   # Critical temperature (K)
    prescrit = 7.3773    # Critical pressure (MPa)
    dencrit = 467.6      # Critical density (kg/m3)
    MW = 44.0095         # Molecular weight (g/mol)
    volcrit = MW * 0.001 / dencrit  # critical molar volume (m3/mol)

    # Determine initial guess
    if volinit <= 0:
        vol1a = Rgas * tmp / pres
        # Determine if CO2 is in vapor, liquid or supercritical region
        if tmp > tmpcrit:
            if pres > prescrit:
                # Supercritical region, use slightly higher molar volume from ideal gas law
                '''
                In supercritical region
                Use slightly higher molar volume
                from ideal gas law as initial guess
                Except for higher temp and pressures
                where multiple roots are closer together
                and a much higher molar volume
                than ideal gas law works better as
                initial guess
                '''
                vol1a = vol1a * 1.05
                if (tmp > 500) and (pres > 30):
                    vol1a = vol1a * 5
            else:
                # Vapor region, use slightly smaller molar volume
                vol1a = vol1a * 0.95
        else:
            pvap = vpSWCO2(tmp)
            if pres > pvap:
                # Liquid region: initial guess less than sat. liquid molar volume
                denlsat = denslSWCO2(tmp)
                vollsat = MW * 0.001 / denlsat
                if vol1a > 0.95 * vollsat:
                    vol1a = 0.95 * vollsat
            else:
                # Vapor region: initial guess greater than sat. vapor molar volume
                denvsat = densvSWCO2(tmp)
                volvsat = MW * 0.001 / denvsat
                if vol1a < 1.05 * volvsat:
                    vol1a = 1.05 * volvsat
    else:
        vol1a = volinit

    # Newton-Raphson method for root-finding (molar volume)

    vol2 = None
    for i in range(100):
        if i == 0:
            pass  # do nothing, first guess already set
        else:
            if vol2 is not None and vol2 > 0:
                break
            else:
                vol1a = vol1a * 1.05
        vol1 = vol1a
        for j in range(1000):
            f = fDuanCO2(vol1, pres, tmp)
            df = d1fDuanCO2(vol1, pres, tmp)
            if df == 0:
                vol1 = vol1 + 1e-5  # avoid division by zero
                continue
            vol2 = vol1 - f / df
            reldif = abs(vol1 - vol2) / abs(vol2)
            if reldif <= tol:
                break
            else:
                vol1 = vol2
    return vol2

def denDuanCO2(volinit, pres, tmp):

    MW = 44.0095   # Molecular weight of CO2 (g/mol)
    mol_vol = volDuanCO2(volinit, pres, tmp)  # Molar volume (m3/mol)
    density = MW * 0.001 / mol_vol

    return density

def zfactDuanCO2(volinit, pres, tmp):

    Rgas = 0.000008314  # Universal gas constant (m3-MPa/(K-mol))
    mol_vol = volDuanCO2(volinit, pres, tmp)  # Calculate molar volume (m3/mol)
    z_factor = (pres * mol_vol) / (Rgas * tmp)

    return z_factor

def presDuanCO2(vol, tmp):

    Rgas = 0.08314467  # Universal gas constant (L-bar/K-mol)
    tmpcrit = 304.1282   # Critical temperature (K)
    prescrit = 7.3773    # Critical pressure (MPa)
    volcrit = Rgas * tmpcrit / (prescrit * 10)  # "Critical" molar volume (L/mol)

    # Constants for Duan et al. CO2 equation of state
    a1 = 0.0899288497
    a2 = -0.494783127
    a3 = 0.0477922245
    a4 = 0.0103808883
    a5 = -0.0282516861
    a6 = 0.0949887563
    a7 = 0.00052060088
    a8 = -0.000293540971
    a9 = -0.00177265112
    a10 = -0.0000251101973
    a11 = 0.0000893353441
    a12 = 0.0000788998563
    a13 = -0.0166727022
    a14 = 1.398
    a15 = 0.0296

    # Reduced properties
    Tr = tmp / tmpcrit
    Vr = vol * 1000 / volcrit  # Convert m3/mol -> L/mol -> reduced volume

    # Intermediate b parameters (b1, b2, b3, b4, b5)
    b1 = (a1 + (a2 / Tr**2) + (a3 / Tr**3)) / Vr
    b2 = (a4 + (a5 / Tr**2) + (a6 / Tr**3)) / Vr**2
    b3 = (a7 + (a8 / Tr**2) + (a9 / Tr**3)) / Vr**4
    b4 = (a10 + (a11 / Tr**2) + (a12 / Tr**3)) / Vr**5
    b5 = (a13 / (Tr**3 * Vr**2)) * (a14 + a15 / Vr**2) * np.exp(-a15 / Vr**2)

    # Reduced pressure
    Pr = (Tr / Vr) * (1 + b1 + b2 + b3 + b4 + b5)
    pres = Pr * prescrit  # Return pressure in MPa

    return pres


def compDuanCO2(volinit, pres, tmp):

    Rgas = 0.08314467  # Universal gas constant (L-bar/K-mol)
    tmpcrit = 304.1282   # Critical temperature (K)
    prescrit = 7.3773    # Critical pressure (MPa)
    volcrit = Rgas * tmpcrit / (prescrit * 10)  # "Critical" molar volume (L/mol)

    # Calculate molar volume at specified P, T
    vol = volDuanCO2(volinit, pres, tmp)

    # Duan EOS constants
    a1 = 0.0899288497
    a2 = -0.494783127
    a3 = 0.0477922245
    a4 = 0.0103808883
    a5 = -0.0282516861
    a6 = 0.0949887563
    a7 = 0.00052060088
    a8 = -0.000293540971
    a9 = -0.00177265112
    a10 = -0.0000251101973
    a11 = 0.0000893353441
    a12 = 0.0000788998563
    a13 = -0.0166727022
    a14 = 1.398
    a15 = 0.0296

    Tr = tmp / tmpcrit
    Pr = pres / prescrit
    Vr = vol * 1000 / volcrit

    # Intermediate values
    b1 = a1 + (a2 / Tr**2) + (a3 / Tr**3)
    b2 = a4 + (a5 / Tr**2) + (a6 / Tr**3)
    b3 = a7 + (a8 / Tr**2) + (a9 / Tr**3)
    b4 = a10 + (a11 / Tr**2) + (a12 / Tr**3)
    b5 = a13 / Tr**3

    # Derivative of reduced pressure wrt reduced volume
    exp_term = np.exp(-a15 / Vr**2)
    df_dVr = (
        -3 * b5 * a14 * Tr * Vr**-4
        - 5 * b5 * a15 * Tr * Vr**-6
    ) * exp_term + (
        (b5 * a14 * Tr * Vr**-3 + b5 * a15 * Tr * Vr**-5)
        * (2 * a15 * Vr**-3) * exp_term
    )

    dPr_dVr = (
        -Tr * Vr**-2
        - 2 * b1 * Tr * Vr**-3
        - 3 * b2 * Tr * Vr**-4
        - 5 * b3 * Tr * Vr**-6
        - 6 * b4 * Tr * Vr**-7
        + df_dVr
    )

    # Compressibility calculation (volcrit in L/mol, vol in m3/mol)
    comp = (-volcrit / (prescrit * vol * 1000)) * (1 / dPr_dVr)
    return comp


def visFWVCO2(den, tmp):

    # Zero-density viscosity term coefficients
    tmpcs = 251.196  # K
    az = [0.235156, -0.491266, 0.05211155, 0.05347906, -0.01537102]
    CSR = 0.0
    log_term = np.log(tmp / tmpcs)
    for j in range(5):
        CSR += az[j] * (log_term) ** j
    visz = 1.00697 * np.sqrt(tmp) / np.exp(CSR)

    # Excess viscosity term coefficients
    d11 = 0.004071119
    d21 = 0.00007198037
    d64 = 2.411697E-17
    d81 = 2.971072E-23
    d82 = -1.627888E-23

    visexc = (
        d11 * den
        + d21 * den ** 2
        + d64 * den ** 6 * (tmp / tmpcs) ** -3
        + d81 * den ** 8
        + d82 * den ** 8 * (tmp / tmpcs) ** -1
    )

    viscosity = visz + visexc

    return viscosity

def reynolds_number(FR, Visc, Dia):

    pi = np.pi
    Re = 4 * FR / (pi * Visc * Dia)

    return Re

def fanning_friction_factor(Dia, Re, eta, FF_Eq):

    RelRough = eta / Dia

    if FF_Eq == 0:
        # McCollum and Ogden (2006) / Haaland equation
        # Fanning = 1/4 * Darcy, where Darcy is given by Haaland
        # The Haaland equation: 1/Calc_Temp^2 = Darcy
        Calc_Temp = np.log10(6.91 / Re + (RelRough / 3.7) ** 1.11)
        FFF = 1 / (4 * (-1.8 * Calc_Temp) ** 2)
    else:
        # McCoy & Rubin (2008) / Zigrang & Sylvester equation
        # Fanning = 1/4 * Darcy, Darcy from Zigrang & Sylvester
        Calc_Temp = -2 * np.log10(
            RelRough / 3.7
            - (5.02 / Re) * np.log10(
                RelRough / 3.7
                - (5.02 / Re) * np.log10(
                    RelRough / 3.7 + 13 / Re
                )
            )
        )
        FFF = 1 / (4 * Calc_Temp ** 2)

    return FFF

def fanning_friction_colebrook(ReN, Dia, eta):

    RelRough = eta / Dia

    # Initial guess using Zigrang & Sylvester as in F_Fact(..., FF_Eq=1)
    def zigrang_sylvester_approx():
        return fanning_friction_factor(Dia, ReN, eta, 1)

    ff_new = 4 * zigrang_sylvester_approx()
    a_new = np.sqrt(1 / ff_new)
    a_diff = 1e-5  # convergence tolerance
    ic = 0

    while ic <= 1000:
        if ic == 0:
            a = a_new
        else:
            a = a_new

        # Colebrook-White implicit function and its derivative
        func_F = a + 2 * np.log10(RelRough / 3.7 + (2.51 / ReN) * a)
        dfunc_F = 1 + (2.18 / ReN) / (RelRough / 3.7 + (2.51 / ReN) * a)

        a_new = a - func_F / dfunc_F

        # Check for convergence
        if abs(a / a_new - 1) < a_diff:
            break
        ic += 1

    # Convert root to friction factor (1/a_new^2 = Moody, /4 = Fanning)
    FFF_Cole = 1 / (4 * a_new ** 2)

    return FFF_Cole

def pav_gas(p_in, p_out):

    pav = (2 / 3) * (p_out + p_in - p_out * p_in / (p_out + p_in))

    return pav

def flowrate_Mtpy_to_kgps(FR_val):

    kg_per_s = FR_val * 1_000_000 * 1000 / (365 * 24 * 3600)
    return kg_per_s

def psia_to_mpa(P_Val):

    P_MPa = P_Val * 6894.757 / 1_000_000
    return P_MPa


def Conv_Lpipeline(length_miles):

    L_pipeline_meter = length_miles * 1609.344
    return L_pipeline_meter

def Conv_temp(temp_c):

    temp_k = temp_c + 273.15
    return temp_k


def Conv_Dpipeline(D_val, U_in, U_out):

    if U_in == 'm' and U_out == 'in':
        # 1 meter = 39.3701 inches
        return D_val * 39.3701
    elif U_in == 'in' and U_out == 'm':
        return D_val / 39.3701
    elif U_in == U_out:
        return D_val
    else:
        raise ValueError("Invalid units. Allowed: 'm' and 'in'.")


def Pipe_Size(Dia, Dia_units):

    # Convert the diameter to inches if needed
    Dia_in = Conv_Dpipeline(Dia, Dia_units, 'in')

    if Dia_in <= 4:
        PS = 4
    elif Dia_in <= 6:
        PS = 6
    elif Dia_in <= 8:
        PS = 8
    elif Dia_in <= 10:
        PS = 10
    elif Dia_in <= 12:
        PS = 12
    elif Dia_in <= 15.162:
        PS = 16
    elif Dia_in <= 18.952:
        PS = 20
    elif Dia_in <= 22.742:
        PS = 24
    elif Dia_in <= 28.428:
        PS = 30
    elif Dia_in <= 34.114:
        PS = 36
    elif Dia_in <= 39.8:
        PS = 42
    elif Dia_in <= 45.5:
        PS = 48
    else:
        PS = 2000  # Flag for 'oversized' pipe

    return PS

def Dia_in_nom(Dia_nom, Dia_nom_units):

    Dia = Conv_Dpipeline(Dia_nom, Dia_nom_units, 'in')  # Convert input to inches if necessary

    if Dia <= 4:
        Dia_in_nom = 4
    elif Dia <= 6:
        Dia_in_nom = 6
    elif Dia <= 8:
        Dia_in_nom = 8
    elif Dia <= 10:
        Dia_in_nom = 10
    elif Dia <= 12:
        Dia_in_nom = 12
    elif Dia <= 16:
        Dia_in_nom = 15.162
    elif Dia <= 20:
        Dia_in_nom = 18.952
    elif Dia <= 24:
        Dia_in_nom = 22.742
    elif Dia <= 30:
        Dia_in_nom = 28.428
    elif Dia <= 36:
        Dia_in_nom = 34.114
    elif Dia <= 42:
        Dia_in_nom = 39.8
    elif Dia <= 48:
        Dia_in_nom = 45.5
    else:
        Dia_in_nom = 99.9  # Flag for oversized

    return Dia_in_nom

def Pthick_nom(Dia_nom, Dia_nom_units):

    # Convert nominal diameter to inches
    Dia = Conv_Dpipeline(Dia_nom, Dia_nom_units, 'in')

    if Dia <= 4:
        Pthick_nom = 0.237
    elif Dia <= 6:
        Pthick_nom = 0.28
    elif Dia <= 8:
        Pthick_nom = 0.322
    elif Dia <= 10:
        Pthick_nom = 0.365
    elif Dia <= 12:
        Pthick_nom = 0.375
    elif Dia <= 16:
        Pthick_nom = 0.419
    elif Dia <= 20:
        Pthick_nom = 0.524
    elif Dia <= 24:
        Pthick_nom = 0.629
    elif Dia <= 30:
        Pthick_nom = 0.786
    elif Dia <= 36:
        Pthick_nom = 0.943
    elif Dia <= 42:
        Pthick_nom = 1.1
    elif Dia <= 48:
        Pthick_nom = 1.25
    else:
        Pthick_nom = 0.5 * (2000 - 99.9)  # Placeholder for oversized

    return Pthick_nom

# ---- Paste all your corrosion functions here (as per your corrosion code) ----
# e.g. v_sl(), v_sg(), v_m(), viscosity_liquid_ul(), ... Kt(), Corrosion_Norsok(), tmin(), etc.

# --- Function Definitions (identical to your provided logic) ---
def v_sl(QL_m3d, D_m):
    QL_m3s = QL_m3d / (24 * 3600)
    area = np.pi / 4 * D_m**2
    vsl = QL_m3s / area
    return vsl

def v_sg(QG_Mm3d, sp_gr, rho_G, D):
    rho_GSC = 2.7 * 14.5 * sp_gr * 16.018 / 520
    QG_m3s = QG_Mm3d * 1_000_000 / (24 * 3600)
    area = np.pi / 4 * D ** 2
    vsg = QG_m3s * rho_GSC / (rho_G * area)
    return vsg

def v_m(v_sl, v_sg):
    return v_sl + v_sg

def viscosity_liquid_ul(WC, uo, ug, uw, phi_c, u_relmax):
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

def LAMDA(v_sl, u_m):
    return v_sl / u_m if u_m != 0 else 0.0

def viscosity_mixture_u_mi(LAMDA, ul, ug):
    u_mi = LAMDA * ul + (1 - LAMDA) * ug
    return u_mi

def density_mix(rho_oil, rho_gas, rho_water, WC, lamda):
    rho_l = rho_water * WC + rho_oil * (1 - WC)
    rho_mix = lamda * rho_l + (1 - lamda) * rho_gas
    return rho_mix

def friction_factor(k, D, vmix, rho_mixture, u_mi):
    u_mi_Pa_s = u_mi / 1000
    term1 = 20000 * k / D
    term2 = 1e6 * u_mi_Pa_s / (rho_mixture * vmix * D)
    exponent = (term1 + term2) ** 0.33
    f = 0.001375 * (1 + exponent)
    return f

def shear_stress(rho_mixture, vmix, f):
    S = 0.5 * rho_mixture * f * (vmix ** 2)
    return S

def convert_bicarb_mgL_to_molL(bicarb_mgL):
    M_NaHCO3 = 84.01
    return bicarb_mgL / 1000 / M_NaHCO3

def convert_ionic_gL_to_molL(ionic_gL):
    M_NaCl = 58.44
    return ionic_gL / M_NaCl

def fugacity_co2(P_bar, T_C, mole_percent_CO2):
    T_K = T_C + 273.15
    P_use = P_bar if P_bar <= 250 else 250
    a = 10 ** (P_use * (0.0031 - 1.4 / T_K))
    pCO2 = (mole_percent_CO2 / 100) * P_bar
    f_CO2 = a * pCO2
    return f_CO2

def pHCalculator1(Temp, Pressure, fugacity_CO2, Bicarb, IonicStrength, CalcOfpH=1):
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

def fpH_FixT(tempe, iph):
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

def fpH_Cal(Tempe,IpH):
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

def Kt(temp):
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

def Corrosion_Norsok(Kt, FugacityofCO2, shearstress, fpH_Cal):
    if FugacityofCO2 > 0:
        exponent = 0.146 + 0.0324 * math.log10(FugacityofCO2)
        corrosion = Kt * FugacityofCO2**0.62 * (shearstress / 19)**exponent * fpH_Cal
    else:
        corrosion = 0.0
    return corrosion

    # Tmin calculation (convert bar to Pa)

def get_minimum_yield_strength(grade):
    grade = grade.upper()
    yield_strengths = {
        'A25': 25000,
        'A': 30000,
        'B': 35000,
        'X42': 42000,
        'X46': 46000,
        'X52': 52000,
        'X56': 56000,
        'X60': 60000,
        'X65': 65000,
        'X70': 70000,
    }
    if grade in yield_strengths:
        return yield_strengths[grade]
    else:
        raise ValueError("Unknown grade. Valid grades are: " + ", ".join(yield_strengths.keys()))


def temp_derating_factor(temp_c):
    # List of tuples: (temp_C, factor)
    table = [
        (121.1, 1.000),
        (148.9, 0.967),
        (176.7, 0.933),
        (204.4, 0.900),
        (232.2, 0.867),
    ]

    # Below minimum, use the first value
    if temp_c <= table[0][0]:
        return table[0][1]
    # Above maximum, use the last value
    if temp_c >= table[-1][0]:
        return table[-1][1]

    # Otherwise, interpolate
    for i in range(len(table) - 1):
        t1, f1 = table[i]
        t2, f2 = table[i+1]
        if t1 <= temp_c <= t2:
            # Linear interpolation
            factor = f1 + (f2 - f1) * (temp_c - t1) / (t2 - t1)
            return factor

    # Should not reach here
    raise ValueError("Temperature is out of interpolation range.")


def tmin(
    pressure,           # Internal pressure, Pa (or same units as yield strength)
    diameter,           # Outside diameter, m
    temp_c,             # Temperature in Celsius
    grade,              # Pipe grade string, e.g. "X60"
):

    # Get SMYS (Specified Minimum Yield Strength) in psi, convert to Pa (1 psi = 6894.76 Pa)
    S_psi = get_minimum_yield_strength(grade)
    S = S_psi * 6894.76     # Pa

    F = 0.72                # Allowable stress factor for pipeline
    T = temp_derating_factor(temp_c)  # Temperature derating factor

    # Po (external pressure) is neglected as per your comment: (Pi - Po) → pressure
    t_min_m = (pressure * diameter) / (2 * S * F * T)
    t_min_mm = t_min_m * 1000  # convert to millimeters

    return t_min_mm

import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter





# === PASTE ALL YOUR FUNCTIONS HERE (costbooster, CpParker, CpRui, etc.) ===

import math

def costpipe(length_km, diameter_inch):
    """
    Estimate the investment cost for an offshore CO2 pipeline (ANSI 1500)
    using IEA (2002) constants and a fixed terrain factor of 1.2.

    Args:
        length_km (float): Pipeline length in kilometers.
        diameter_inch (float): Pipeline diameter in inches.

    Returns:
        float: Investment cost in Euros (€).
    """
    # Offshore pipeline constants
    C1 = 0.4048
    C2 = 4.6936
    C3 = 0.00153
    C4 = 0.0113
    C5 = 0.000511
    C6 = 0.000204

    TF = 1.2  # Fixed terrain factor for offshore

    L = length_km
    D = diameter_inch

    invpipe = (
        (C1 * L + C2 +
         (C3 * L - C4) * D +
         (C5 * L - C6) * D**2
        ) * 1e6 * TF
    )

    return invpipe  # Euros


def costbooster(length_km):
    """
    Calculate the investment cost for offshore booster stations.

    Args:
        length_km (float): Pipeline length in kilometers.

    Returns:
        float: Booster station investment cost in Euros (€).
    """
    InvBS_norm = 70000  # €/km for offshore (from IEA GHG 2002)
    return InvBS_norm * length_km

def costbooster(length_mi):
    """
    Calculate the investment cost for offshore booster stations in 2011 USD per mile.

    Args:
        length_mi (float): Pipeline length in miles.

    Returns:
        float: Booster station investment cost (2011 USD, total for all miles).
        float: Booster station investment cost per mile (2011 USD/mi).
    """
    # Base cost in 2000 EUR: 70,000 €/km (from IEA GHG 2002)
    # Conversion factors
    km_per_mile = 1.60934
    base_cost_eur_per_km = 70000  # €/km (offshore, from IEA)
    base_year_eur_to_usd = 1      # If you have a EUR to USD conversion, update here
    base_year_2000_to_2011 = 525 / 261

    # Total cost in 2000 EUR
    length_km = length_mi * km_per_mile
    cost_eur_2000 = base_cost_eur_per_km * length_km

    # Escalate to 2011 USD (if assuming EUR=USD, else add fx conversion)
    cost_usd_2011 = cost_eur_2000 * base_year_2000_to_2011 * base_year_eur_to_usd

    # Cost per mile
    cost_per_mile_2011 = cost_usd_2011 / length_mi

    return cost_usd_2011, cost_per_mile_2011

def total_cost(length_km, diameter_inch):
    """
    Return the total investment cost (pipeline + booster stations) for offshore.
    """
    pipe = costpipe(length_km, diameter_inch)
    booster = costbooster(length_km)
    total_cost = pipe + booster
    return total_cost


def CpParker(Dia, Lnth, Categ, ConYr):
    """
    Function CpParker (Parker, 2004)
    ------------------------------------
    Calculates pipeline capital costs for the following categories:
    materials (MAT), labor (LAB), ROW (right of way), MISC (miscellaneous), or TOT (total costs).
    The function uses equations from Parker (2004), with costs reported in either 2000 or 2011 dollars.

    Reference:
        Parker, N., 2004. "Using Natural Gas Transmission Pipeline Costs to Estimate Hydrogen Pipeline Costs",
        UCD-ITS-RR-04-35, Institute of Transportation Studies, UC Davis.

    Args:
        Dia   : Pipeline diameter in inches
        Lnth  : Pipeline length in miles
        Categ : Cost category string ("MAT", "LAB", "ROW", "MISC", "TOT")
        ConYr : Control year for cost reporting (2011 or 0 for 2000 base year)

    Returns:
        Capital cost of the specified pipeline category, in the requested year.
        Returns "Error" if category is not recognized.
    """
    # Calculate capital costs in 2000 dollars
    Cmat1  = 35000 + Lnth * (330.5 * Dia**2 + 687 * Dia + 26960)
    Clab1  = 185000 + Lnth * (343 * Dia**2 + 2074 * Dia + 170013)
    Crow1  = 40000 + Lnth * (577 * Dia + 29788)
    Cmisc1 = 95000 + Lnth * (8417 * Dia + 7324)
    Ctot1  = Cmat1 + Clab1 + Crow1 + Cmisc1

    # Adjust costs to 2011 dollars if requested
    if ConYr == 2011:
        Cmat  = Cmat1  * (525 / 261)   # Handy-Whitman index
        Clab  = Clab1  * (525 / 261)   # Handy-Whitman index
        Crow  = Crow1  * (113.8 / 88.7)  # GDP chain-type price index
        Cmisc = Cmisc1 * (190.9 / 122.3) # Producer price index
        Ctot  = Cmat + Clab + Crow + Cmisc
    else:
        # Report costs in 2000 dollars, the base year
        Cmat  = Cmat1
        Clab  = Clab1
        Crow  = Crow1
        Cmisc = Cmisc1
        Ctot  = Cmat + Clab + Crow + Cmisc

    # Return the requested cost category (case-insensitive)
    Categ = Categ.strip().upper()
    if   Categ == "MAT":
        return Cmat
    elif Categ == "LAB":
        return Clab
    elif Categ == "ROW":
        return Crow
    elif Categ == "MISC":
        return Cmisc
    elif Categ == "TOT":
        return Ctot
    else:
        return "Error"



def CpRui1(Dia, Lnth, Reg, Categ, ConYr):
    """
    Function CpRui1
    ------------------------
    Calculates pipeline capital costs for the following categories:
    materials (MAT), labor (LAB), ROW (right of way), MISC (miscellaneous), or TOT (total costs)
    using the equations from Rui et al. (2011), with costs in either 2008 or 2011 dollars.

    Reference:
        Rui, Z., P. Metz, D. Reynolds, G. Chen, and X. Zhou, 2011. "Regression Models Estimate Pipeline Construction Costs",
        Oil and Gas Journal, July 4, 2011.

    Args:
        Dia   : Pipeline diameter in inches
        Lnth  : Pipeline length in miles
        Reg   : "CEN", "NE", "SE", "MW", "SW", "WEST", or "CAN"
        Categ : "MAT", "LAB", "ROW", "MISC", or "TOT"
        ConYr : 2011 or 0 (0 = 2008 base year, 2011 = 2011 dollars)

    Returns:
        Capital cost for the category (in the requested year) or "Error" if region or category is invalid.
    """
    Reg = Reg.strip().upper()
    # Region adjustment factors
    region_map = {
        "CEN":  (0,      0,      0,      0),
        "NE":   (0,    0.784,  0.645,  0.704),
        "SE":   (0.176,0.772,  0.798,  0.967),
        "MW":  (-0.098,0.541,  1.064,  0.547),
        "SW":   (0,    0.498,  0.981,  0.699),
        "WEST": (0,    0.653,  0.778,  0),
        "CAN": (-0.196, 0,   -0.83,     0)
    }

    if Reg not in region_map:
        return "Error"

    aregmat, areglab, aregrow, aregmisc = region_map[Reg]

    # Cross-sectional area (ft^2) and length in feet
    SA = math.pi * (Dia / 24.0)**2
    Lnthft = Lnth * 5280.0

    # 2008 dollars
    Cmat1  = math.exp(4.814 + aregmat) * SA**0.734 * Lnthft**0.873
    Clab1  = math.exp(5.697 + areglab) * SA**0.459 * Lnthft**0.808
    Crow1  = math.exp(1.259 + aregrow) * SA**0.191 * Lnthft**1.027
    Cmisc1 = math.exp(5.58  + aregmisc) * SA**0.458 * Lnthft**0.765
    Ctot1  = Cmat1 + Clab1 + Crow1 + Cmisc1

    # Adjust to 2011 dollars if requested
    if ConYr == 2011:
        Cmat  = Cmat1  * (525 / 604)      # Handy-Whitman index for gas pipelines
        Clab  = Clab1  * (525 / 604)      # Handy-Whitman index
        Crow  = Crow1  * (113.8 / 108.5)  # GDP chain-type price index
        Cmisc = Cmisc1 * (190.9 / 196.3)  # Producer price index
        Ctot  = Cmat + Clab + Crow + Cmisc
    else:
        Cmat, Clab, Crow, Cmisc, Ctot = Cmat1, Clab1, Crow1, Cmisc1, Ctot1

    Categ = Categ.strip().upper()
    if   Categ == "MAT":
        return Cmat
    elif Categ == "LAB":
        return Clab
    elif Categ == "ROW":
        return Crow
    elif Categ == "MISC":
        return Cmisc
    elif Categ == "TOT":
        return Ctot
    else:
        return "Error"

def CpRui(Dia, Lnth, Reg, Categ, ConYr):
    """
    Function CpRui
    -------------------------
    Calculates pipeline capital costs for the given region, category, and year.
    If Reg = "AVG", returns the average cost for the six lower 48 US regions.

    Args:
        Dia   : Pipeline diameter in inches
        Lnth  : Pipeline length in miles
        Reg   : Region string ("CEN", "NE", "SE", "MW", "SW", "WEST", "CAN", "AVG")
        Categ : Cost category ("MAT", "LAB", "ROW", "MISC", "TOT")
        ConYr : Year (2011 or 0 for 2008 base year)
    Returns:
        Cost for the requested category and region.
    """
    Reg = Reg.strip().upper()
    if Reg == "AVG":
        regions = ["CEN", "NE", "SE", "MW", "SW", "WEST"]
        costs = [CpRui1(Dia, Lnth, r, Categ, ConYr) for r in regions]
        if "Error" in costs:
            return "Error"
        return sum(costs) / len(costs)
    else:
        return CpRui1(Dia, Lnth, Reg, Categ, ConYr)


def CpMcCoy1(Dia, Lnth, Reg, Categ, ConYr):
    """
    Function CpMcCoy1
    ------------------------
    Calculates pipeline capital costs for the following categories:
    materials (MAT), labor (LAB), ROW (right of way), MISC (miscellaneous), or TOT (total costs)
    using the equations from McCoy and Rubin (2008), with costs in either 2004 or 2011 dollars.

    Reference:
        McCoy, S. and E. Rubin, 2008. "An Engineering-Economic Model of Pipeline Transport of CO2 with Application to Carbon Capture and Storage",
        Int. J. of Greenhouse Gas Control, Vol. 2, pgs. 219-229.

    Args:
        Dia   : Pipeline diameter in inches
        Lnth  : Pipeline length in miles
        Reg   : "CEN", "NE", "SE", "MW", "SW", or "WEST"
        Categ : "MAT", "LAB", "ROW", "MISC", or "TOT"
        ConYr : 2011 or 0 (0 = 2004 base year, 2011 = 2011 dollars)

    Returns:
        Capital cost for the category (in the requested year) or "Error" if region or category is invalid.
    """
    import math
    Reg = Reg.strip().upper()
    region_map = {
        "MW":    (0,     0,      0,      0),
        "NE":    (0,   0.075,    0,    0.145),
        "SE": (0.074,    0,      0,    0.132),
        "CEN":   (0,  -0.187, -0.382, -0.369),
        "SW":    (0,  -0.216,    0,      0),
        "WEST":  (0,     0,      0,   -0.377),
    }
    if Reg not in region_map:
        return "Error"

    aregmat, areglab, aregrow, aregmisc = region_map[Reg]
    Lnthkm = Lnth * 1.60934

    # 2004 dollars
    Cmat1  = 10 ** (3.112 + aregmat) * Lnthkm ** 0.901 * Dia ** 1.59
    Clab1  = 10 ** (4.487 + areglab) * Lnthkm ** 0.82  * Dia ** 0.94
    Crow1  = 10 ** (3.95  + aregrow) * Lnthkm ** 1.049 * Dia ** 0.403
    Cmisc1 = 10 ** (4.39  + aregmisc) * Lnthkm ** 0.783 * Dia ** 0.791
    Ctot1  = Cmat1 + Clab1 + Crow1 + Cmisc1

    if ConYr == 2011:
        # Escalate to 2011 dollars
        Cmat  = Cmat1  * (525 / 400)
        Clab  = Clab1  * (525 / 400)
        Crow  = Crow1  * (113.8 / 96.77)
        Cmisc = Cmisc1 * (190.9 / 139.6)
        Ctot  = Cmat + Clab + Crow + Cmisc
    else:
        Cmat, Clab, Crow, Cmisc, Ctot = Cmat1, Clab1, Crow1, Cmisc1, Ctot1

    Categ = Categ.strip().upper()
    if   Categ == "MAT":
        return Cmat
    elif Categ == "LAB":
        return Clab
    elif Categ == "ROW":
        return Crow
    elif Categ == "MISC":
        return Cmisc
    elif Categ == "TOT":
        return Ctot
    else:
        return "Error"

def CpMcCoy(Dia, Lnth, Reg, Categ, ConYr):
    """
    Function CpMcCoy
    -------------------------
    Calculates pipeline capital costs for the given region, category, and year.
    If Reg = "AVG", returns the average cost for the six lower 48 US regions.

    Args:
        Dia   : Pipeline diameter in inches
        Lnth  : Pipeline length in miles
        Reg   : Region string ("CEN", "NE", "SE", "MW", "SW", "WEST", "AVG")
        Categ : Cost category ("MAT", "LAB", "ROW", "MISC", "TOT")
        ConYr : Year (2011 or 0 for 2004 base year)
    Returns:
        Cost for the requested category and region.
    """
    Reg = Reg.strip().upper()
    if Reg == "AVG":
        regions = ["CEN", "NE", "SE", "MW", "SW", "WEST"]
        costs = [CpMcCoy1(Dia, Lnth, r, Categ, ConYr) for r in regions]
        if "Error" in costs:
            return "Error"
        return sum(costs) / len(costs)
    else:
        return CpMcCoy1(Dia, Lnth, Reg, Categ, ConYr)



def CpBrown1(Dia, Lnth, Reg, Categ, ConYr):
    """
    Function CpBrown1
    ------------------------
    Calculates pipeline capital costs for the following categories:
    materials (MAT), labor (LAB), ROW (right of way), MISC (miscellaneous), or TOT (total costs)
    using the equations from Brown et al. (2022), with costs in either 2018 or 2011 dollars.

    Reference:
        Brown, D., K. Reddi and A. Elgowainy, 2022. "The Development of Natural Gas and Hydrogen Pipeline Capital Cost Estimating Equations",
        International Journal of Hydrogen Energy, Vol. 47, pgs. 33813-33826.

    Args:
        Dia   : Pipeline diameter in inches
        Lnth  : Pipeline length in miles
        Reg   : "NE", "MA", "SE", "GL", "GP", "RM", "PN", "SW", or "CA"
        Categ : "MAT", "LAB", "ROW", "MISC", or "TOT"
        ConYr : 2011 or 0 (0 = 2018 base year, 2011 = 2011 dollars)

    Returns:
        Capital cost for the category (in the requested year) or "Error" if region or category is invalid.
    """
    Reg = Reg.strip().upper()
    Dia = float(Dia)
    Lnth = float(Lnth)

    # Calculate natural gas pipeline capital costs in 2018 dollars per inch-mile
    if Reg == "NE":
        Cmat1 = 10409 * Dia ** 0.296847 * Lnth ** -0.07257
        Clab1 = 249131 * Dia ** -0.33162 * Lnth ** -0.17892
        Cmisc1 = 65990 * Dia ** -0.29673 * Lnth ** -0.06856
        Crow1 = 83124 * Dia ** -0.66357 * Lnth ** -0.07544
    elif Reg == "MA":
        Cmat1 = 9113 * Dia ** 0.279875 * Lnth ** -0.0084
        Clab1 = 43692 * Dia ** 0.05683 * Lnth ** -0.10108
        Cmisc1 = 14616 * Dia ** 0.16354 * Lnth ** -0.16186
        Crow1 = 1942 * Dia ** 0.17394 * Lnth ** -0.01555
    elif Reg == "GL":
        Cmat1 = 8971 * Dia ** 0.255012 * Lnth ** -0.03138
        Clab1 = 58154 * Dia ** -0.14821 * Lnth ** -0.10596
        Cmisc1 = 41238 * Dia ** -0.34751 * Lnth ** -0.11104
        Crow1 = 14259 * Dia ** -0.65318 * Lnth ** 0.06865
    elif Reg in ("GP", "RM"):
        Cmat1 = 5813 * Dia ** 0.31599 * Lnth ** -0.00376
        Clab1 = 10406 * Dia ** 0.20953 * Lnth ** -0.08419
        Cmisc1 = 4944 * Dia ** 0.17351 * Lnth ** -0.07621
        Crow1 = 2751 * Dia ** -0.28294 * Lnth ** 0.00731
    elif Reg in ("SE", "PN"):
        Cmat1 = 6207 * Dia ** 0.38224 * Lnth ** -0.05211
        Clab1 = 32094 * Dia ** 0.0611 * Lnth ** -0.14828
        Cmisc1 = 11270 * Dia ** 0.19077 * Lnth ** -0.13669
        Crow1 = 9531 * Dia ** -0.37284 * Lnth ** 0.02616
    elif Reg in ("SW", "CA"):
        Cmat1 = 5605 * Dia ** 0.41642 * Lnth ** -0.06441
        Clab1 = 95295 * Dia ** -0.53848 * Lnth ** 0.0307
        Cmisc1 = 19211 * Dia ** -0.14178 * Lnth ** -0.04697
        Crow1 = 72634 * Dia ** -1.07566 * Lnth ** 0.05284
    else:
        return "Error"

    # Costs are per inch-mile, so multiply by Dia * Lnth to get total costs
    Cmat1 = Cmat1 * Dia * Lnth
    Clab1 = Clab1 * Dia * Lnth
    Cmisc1 = Cmisc1 * Dia * Lnth
    Crow1 = Crow1 * Dia * Lnth
    Ctot1 = Cmat1 + Clab1 + Crow1 + Cmisc1

    # Adjust to 2011 dollars if requested
    if ConYr == 2011:
        adj = 519 / 629  # Average Handy-Whitman index for gas transmission plants
        Cmat = Cmat1 * adj
        Clab = Clab1 * adj
        Crow = Crow1 * adj
        Cmisc = Cmisc1 * adj
        Ctot = Cmat + Clab + Crow + Cmisc
    else:
        Cmat, Clab, Crow, Cmisc, Ctot = Cmat1, Clab1, Crow1, Cmisc1, Ctot1

    Categ = Categ.strip().upper()
    if   Categ == "MAT":
        return Cmat
    elif Categ == "LAB":
        return Clab
    elif Categ == "ROW":
        return Crow
    elif Categ == "MISC":
        return Cmisc
    elif Categ == "TOT":
        return Ctot
    else:
        return "Error"

def CpBrown(Dia, Lnth, Reg, Categ, ConYr):
    """
    Function CpBrown
    -------------------------
    Calculates pipeline capital costs for the given region, category, and year.
    If Reg = "AVG", returns the average cost for the nine US regions.

    Args:
        Dia   : Pipeline diameter in inches
        Lnth  : Pipeline length in miles
        Reg   : Region string ("NE", "MA", "SE", "GL", "GP", "RM", "PN", "SW", "CA", "AVG")
        Categ : Cost category ("MAT", "LAB", "ROW", "MISC", "TOT")
        ConYr : Year (2011 or 0 for 2018 base year)
    Returns:
        Cost for the requested category and region.
    """
    Reg = Reg.strip().upper()
    if Reg == "AVG":
        regions = ["NE", "MA", "SE", "GL", "GP", "RM", "PN", "SW", "CA"]
        costs = [CpBrown1(Dia, Lnth, r, Categ, ConYr) for r in regions]
        if "Error" in costs:
            return "Error"
        return sum(costs) / len(costs)
    else:
        return CpBrown1(Dia, Lnth, Reg, Categ, ConYr)


def escalation_factor(escalation_rate_percent, starting_year):
    """
    Calculate the escalation factor from 2011 to the project's starting year.

    Args:
        escalation_rate_percent (float): Annual escalation rate in percent (e.g., 3 for 3%)
        starting_year (int): Starting year of the project (e.g., 2025)

    Returns:
        float: Escalation factor
    """
    years = starting_year - 2011
    escalation_rate = escalation_rate_percent / 100.0
    escalation_factor = (1 + escalation_rate) ** years
    return escalation_factor

def _fig_to_png(fig, width_px=540):
    """Render a Matplotlib fig to PNG bytes at a fixed width to keep layout stable."""
    buf = BytesIO()
    # lock the physical size; DPI*inches = pixels
    target_dpi = 110
    fig.set_dpi(target_dpi)
    w_in = width_px / target_dpi
    # keep aspect consistent per chart type
    if fig.get_figheight() < 1.0:
        fig.set_size_inches(w_in, w_in * 0.75, forward=True)
    else:
        # respect current aspect but clamp width
        fig.set_size_inches(w_in, fig.get_figheight(), forward=True)
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf

# ... [All your function definitions go here, including cost model functions CpParker, CpRui, CpMcCoy, CpBrown, costbooster, etc.] ...

# Load pipeline data (now includes ID_IN and START_DATE)

columns_to_keep = [
    "FEATURE_ID", "PIPE_NAME", "OD_IN", "ID_IN", "PIPE_GRADE",
    "LENGTH_M", "THICKNESS", "START_DATE", "geometry"
]

# Optional micro-optimizations for Shapely
try:
    import shapely.speedups as _sx
    _sx.enable()
except Exception:
    pass

@st.cache_data(show_spinner=False)
def _load_gdf():
    g = gpd.read_file("src/data_pipelines_uk.geojson")[columns_to_keep]
    # keep geometry precision reasonable (smaller payload to the map)
    from shapely import set_precision
    g["geometry"] = g.geometry.apply(lambda geom: set_precision(geom, 1e-6))
    return g

gdf = _load_gdf()

# ---- keep one selected feature in session ----
if "selected_feature_id" not in st.session_state:
    st.session_state.selected_feature_id = str(gdf.iloc[0]["FEATURE_ID"])

# Colors
BLUE  = "#2C7BE5"   # default
RED   = "#FF5A5F"   # selected
HOVER = "#4ECDC4"   # hover

def _style_for(feature):
    """Color the selected pipe in red; others blue."""
    fid = str(feature["properties"].get("FEATURE_ID"))
    is_sel = (fid == st.session_state.selected_feature_id)
    return {"color": RED if is_sel else BLUE,
            "weight": 8 if is_sel else 6,
            "opacity": 1.0 if is_sel else 0.85}

def _highlight(feature):
    """Subtle highlight on hover."""
    return {"color": HOVER, "weight": 10, "opacity": 1.0}

# ------------- Map build -------------
# center the map on the selected feature (nice UX)
_sel_row = gdf.loc[gdf["FEATURE_ID"].astype(str) == st.session_state.selected_feature_id]
if len(_sel_row):
    minx, miny, maxx, maxy = _sel_row.iloc[0].geometry.bounds
    c_y = (miny + maxy) / 2
    c_x = (minx + maxx) / 2
    m = folium.Map(location=[c_y, c_x], zoom_start=7, tiles="cartodbpositron")
else:
    center = gdf.geometry.unary_union.centroid
    m = folium.Map(location=[center.y, center.x], zoom_start=6, tiles="cartodbpositron")

# Add GeoJSON (use __geo_interface__ to avoid an expensive to_json() copy)
gj = folium.GeoJson(
    data=gdf.__geo_interface__,
    name="Pipelines",
    style_function=_style_for,
    highlight_function=_highlight,
    tooltip=folium.GeoJsonTooltip(fields=["PIPE_NAME"]),
)
gj.add_to(m)

st.set_page_config(layout="wide")
st.markdown("""
<style>
    .stCard {background:#fff; padding:1.3rem 1.5rem 0.8rem 1.5rem; border-radius:18px;
             border:1.5px solid #f0f0f0; box-shadow:0 2px 12px rgba(40,60,120,0.11);}
    .tight-row {margin-bottom:-1.2rem;}
</style>
""", unsafe_allow_html=True)

with st.container():
    # --- TOP ROW: Map & Pipeline Info ---
    c1, c2 = st.columns([1.3, 1.6], gap="medium")
    with c1:
        st.markdown('<div class="stCard tight-row">', unsafe_allow_html=True)
        st.markdown("#### Pipeline Map")

        # IMPORTANT: give the map a stable key so Streamlit doesn't re-create it unnecessarily
        map_data = st_folium(m, width=900, height=520, key="main_map")

        # Update the selected feature if the user clicked or hovered
        if map_data:
            # 1) exact feature hover/click (preferred — keeps FEATURE_ID)
            feat = map_data.get("last_active_feature") or map_data.get("last_object_clicked")
            if feat and "properties" in feat and "FEATURE_ID" in feat["properties"]:
                new_id = str(feat["properties"]["FEATURE_ID"])
                if new_id != st.session_state.selected_feature_id:
                    st.session_state.selected_feature_id = new_id
                    st.rerun()  # update immediately instead of waiting ~30s
            # 2) fallback: plain map click near a line – pick the closest geometry
            elif map_data.get("last_clicked"):
                lng, lat = map_data["last_clicked"]["lng"], map_data["last_clicked"]["lat"]
                pt = gpd.points_from_xy([lng], [lat])[0]
                idx = gdf.distance(pt).idxmin()
                new_id = str(gdf.loc[idx, "FEATURE_ID"])
                if new_id != st.session_state.selected_feature_id:
                    st.session_state.selected_feature_id = new_id
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # compute the clicked_row for downstream panels using the persistent selection
    _sel_mask = gdf["FEATURE_ID"].astype(str) == st.session_state.selected_feature_id
    clicked_row = gdf.loc[_sel_mask].iloc[0] if _sel_mask.any() else gdf.iloc[0]


    # --- Extract pipeline info for all calculations ---
    pipe_name = clicked_row.get('PIPE_NAME', 'N/A')
    length_km = float(clicked_row.get('LENGTH_M', 0)) / 1000
    length_mi = length_km * 0.621371  # convert km to miles for cost model
    od_in = float(clicked_row.get('OD_IN', 0))
    id_in = float(clicked_row.get('ID_IN', 0))
    thickness_mm = float(clicked_row.get('THICKNESS', 0))
    pipe_grade = clicked_row.get('PIPE_GRADE', 'N/A')
    start_year = int(clicked_row.get('START_DATE', 1990))

    with c2:
        st.markdown('<div class="stCard tight-row">', unsafe_allow_html=True)
        st.markdown("#### Pipeline Information")
        st.markdown(f"**Pipe Name:** {pipe_name}")
        st.markdown(f"**Length (km):** {length_km:.2f}")
        st.markdown(f"**OD (in):** {od_in:.2f}")
        st.markdown(f"**ID (in):** {id_in:.2f}")
        st.markdown(f"**Thickness (mm):** {thickness_mm:.2f}")
        st.markdown(f"**Pipe Grade:** {pipe_grade}")
        st.markdown(f"**Start of Operation:** {start_year}")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- BOTTOM ROW: Transport, Corrosion, Cost Model ---
    c3, c4, c5 = st.columns([1.0, 1.0, 1.0], gap="medium")
    # -- Transport Design --
    with c3:
        st.markdown('<div class="stCard tight-row">', unsafe_allow_html=True)
        st.markdown("#### CO2 Transport Capacity Design")
        st.markdown("*Transport/Flow Capacity Evaluation*")
        # Inputs for transport design
        pipe_capacity_factor = st.number_input("Pipeline capacity factor (e.g. 0.85)", value=0.85, min_value=0.1, max_value=1.0, step=0.01, key="CapFact")
        p_in_psia = st.number_input("Segment inlet pressure (psia):", value=2200.0, key="Pin")
        p_out_psia = st.number_input("Segment outlet pressure (psia):", value=1200.0, key="Pout")
        tmp_c = st.number_input("Temperature (°C):", value=12.0, key="Temp")
        qm_proyection_Mtpy = st.number_input("Annual average CO₂ mass flow rate (Mtonnes/yr):", value=4.3, key="QCO2")
        h_dif_tot = st.number_input("Total elevation change (meters):", value=0.0, key="Elev")
        N_Pump = st.number_input("Number of pumps/compressor stations:", value=0, min_value=0, step=1, key="Pumps")
        MW_in = st.number_input("Molecular weight of CO₂ (g/mol):", value=44.0095, key="MW")
        # ...[your transport design calculation logic and outputs, unchanged]...

        if st.button("Calculate Transport Design"):
            # Use the constant for roughness
            pipe_inner_rough = 0.0018  # in
            eta = Conv_Dpipeline(pipe_inner_rough, 'in', 'm')
            Dia_in_nom_in = id_in
            Dia_in_nom_m = Conv_Dpipeline(Dia_in_nom_in, 'in', 'm')
            volinit = 0
            p_in = psia_to_mpa(p_in_psia)
            p_out = psia_to_mpa(p_out_psia)
            p_in_Pa = p_in * 1e6
            p_out_Pa = p_out * 1e6
            tmp = Conv_temp(tmp_c)
            MW = MW_in * 0.001
            Nseg = N_Pump + 1
            L_seg = length_km * 1000 / Nseg  # convert back to meters
            h_dif_seg = h_dif_tot / Nseg
            p_avg = pav_gas(p_in, p_out)
            density = denDuanCO2(volinit, p_avg, tmp)
            viscosity = visFWVCO2(density, tmp)
            z_factor = zfactDuanCO2(volinit, p_avg, tmp)
            pi = np.pi
            g = 9.80665
            Rgas = 8.3144621
            Dia_g = Dia_in_nom_m
            qm_max = 100.0
            tol = 1e-6
            max_iter = 1000
            ic = 0
            while ic <= max_iter:
                visc_Pa_s = viscosity * 1e-6
                Re = reynolds_number(qm_max, visc_Pa_s, Dia_g)
                ff = fanning_friction_colebrook(Re, Dia_g, eta)
                num_const = -64 * z_factor**2 * Rgas**2 * tmp**2 * ff * L_seg
                denom = (
                    pi**2 * (
                        MW * z_factor * Rgas * tmp * (p_out_Pa**2 - p_in_Pa**2)
                        + 2 * g * (p_avg * 1e6)**2 * MW**2 * h_dif_seg
                    )
                )
                if num_const == 0:
                    st.error("Physical parameters out of valid range, cannot compute maximum flow rate.")
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
            required_qm_max_kgps = required_qm_max * 1e9 / (365*24*3600)
            st.markdown("---")
            st.markdown(f"**Average pressure:** {p_avg:.4f} MPa")
            st.markdown(f"**Maximum mass flow rate:** {qm_max:.3f} kg/s ({qm_max_Mtpy:.3f} Mtonnes/year)")
            st.markdown(f"- Density: {density:.4f} kg/m³")
            st.markdown(f"- Viscosity: {viscosity:.4f} μPa·s")
            st.markdown(f"- Compressibility factor (Z): {z_factor:.6f}")
            st.markdown(f"**Final Fanning friction factor:** {ff:.6f}")
            st.markdown(f"**Final Reynolds number:** {Re:.2e}")
            st.markdown(f"**Pipe used:** Nominal {od_in:.1f}\" | Standard Inner Diameter: {Dia_in_nom_in:.3f}\" ({Dia_in_nom_m:.4f} m)")
            st.markdown("---")
            st.markdown(f"**Required design flow rate (capacity adjusted):** {required_qm_max:.3f} Mtonnes/year ({required_qm_max_kgps:.3f} kg/s)")
            if qm_max_Mtpy >= required_qm_max:
                st.success("The existing pipeline IS SUITABLE for the projected CO₂ transport at the specified conditions.")
            else:
                st.error("The existing pipeline IS NOT SUITABLE for the projected CO₂ transport at the specified conditions.")
        st.markdown('</div>', unsafe_allow_html=True)


    # -- Corrosion Calculate --
    with c4:
        st.markdown('<div class="stCard tight-row">', unsafe_allow_html=True)
        st.markdown("#### Corrosion Calculate & Lifetime")
        st.markdown("*Estimation of Pipeline Corrosion Rate and Pipeline Repurposing Lifetime*")
        st.markdown("_Based on NORSOK M-506 Model_")
        # User inputs
        QL = st.number_input("Liquid rate QL (m³/d):", value=1000.0)
        QG = st.number_input("Gas rate QG (Mm³/d):", value=5.0)
        WC = st.number_input("Water cut WC (fraction 0-1):", value=0.10)
        Temp = st.number_input("Temperature Temp (°C):", value=13.0)
        Pressure = st.number_input("Pressure (bar):", value=50.0)
        mole_percent_CO2 = st.number_input("Mole percent CO2 (%):", value=1.0)
        corrosion_rate_co2 = st.number_input("Estimated corrosion rate for CO2 transport (mm/year):", value=0.1)


        # -- Pipeline parameters are auto-filled --
        D = id_in  # internal diameter from pipeline info (inches)
        D = D / 39.3701  # convert to meters if needed (if data is in inches)
        pipeline_thickness = thickness_mm
        pipeline_start_year = start_year

        # Tmin parameters from pipeline data
        pressure_tmin_bar = None
        temp_tmin = None
        grade_tmin = None
        if 'p_avg' in locals():
            pressure_tmin_bar = p_avg * 10  # MPa to bar (1 MPa = 10 bar)
        else:
            pressure_tmin_bar = 80.0
        temp_tmin = tmp_c
        grade_tmin = pipe_grade


        # --- Results ---
        if st.button("Estimate Corrosion and Lifetime"):
            # Constants (copy from your corrosion code)
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

            # --- Calculations (paste your code logic here as before) ---
            vsl = v_sl(QL, D)
            vsg = v_sg(QG, sp_gr, rho_G, D)
            vmix = v_m(vsl, vsg)
            ul = viscosity_liquid_ul(WC, uo, ug, uw, phi_c, u_relmax)
            lamda_ = LAMDA(vsl, vmix)
            u_mi = viscosity_mixture_u_mi(lamda_, ul, ug)
            rho_mixture = density_mix(rho_oil, rho_G, rho_water, WC, lamda_)
            f = friction_factor(k, D, vmix, rho_mixture, u_mi)
            S = shear_stress(rho_mixture, vmix, f)
            Bicarb_moll = convert_bicarb_mgL_to_molL(Bicarb)
            IonicStrength_moll = convert_ionic_gL_to_molL(IonicStrength)
            fugacity_co2_value = fugacity_co2(Pressure, Temp, mole_percent_CO2)
            pH = pHCalculator1(Temp, Pressure, fugacity_co2_value, Bicarb_moll, IonicStrength_moll, CalcOfpH)
            fpH = fpH_Cal(Temp, pH)
            Kt_value = Kt(Temp)
            corrosion_rate = Corrosion_Norsok(Kt_value, fugacity_co2_value, S, fpH)  # mm/year

            st.markdown(f"### Estimated Corrosion Rate: **{corrosion_rate:.3f} mm/year**")

            # --- Age calculations ---
            current_year = datetime.datetime.now().year
            years = current_year - pipeline_start_year
            thickness_corroded = corrosion_rate * years
            st.markdown(f"**Years in operation:** {years} years")
            st.markdown(f"**Estimated total thickness lost to corrosion:** {thickness_corroded:.2f} mm")

            # --- Tmin calculation ---
            pressure_tmin_pa = float(pressure_tmin_bar) * 100000  # bar to Pa
            Tmin = tmin(pressure_tmin_pa, D, temp_tmin, grade_tmin)
            st.markdown(f"**Minimum required wall thickness (Tmin):** {Tmin:.2f} mm")

            # --- Thickness calculations ---
            current_thickness = pipeline_thickness - thickness_corroded
            thickness_available = current_thickness - Tmin
            st.markdown(f"**Current wall thickness after corrosion:** {current_thickness:.2f} mm")
            st.markdown(f"**Thickness available (Current thickness - Tmin):** {thickness_available:.2f} mm")

            # --- Repurposing for CO2 transport ---
            if corrosion_rate_co2 > 0:
                years_for_CO2 = thickness_available / corrosion_rate_co2
                st.success(f"Number of years pipeline can be safely repurposed for CO2 transport: **{years_for_CO2:.2f} years**")
            else:
                st.warning("Corrosion rate for CO2 must be greater than zero to estimate years for CO2 transport.")

        st.markdown('</div>', unsafe_allow_html=True)

    # -- Cost Model Calculate --
    with c5:
        st.markdown('<div class="stCard tight-row">', unsafe_allow_html=True)
        st.markdown("#### Cost Model Calculate")
        st.markdown("*CO₂ Offshore Pipeline CAPEX Estimation*")

        # Inputs using selected pipeline info:
        model_options = {
            "PARKER":      ("Parker (2004)", CpParker, ()),
            "RUI":         ("Rui et al. (2011)", CpRui, ("AVG",)),
            "MCCOY":       ("McCoy and Rubin (2008)", CpMcCoy, ("AVG",)),
            "BROWN":       ("Brown et al. (2022)", CpBrown, ("AVG",))
        }
        model_name_key = st.selectbox("Model:", list(model_options.keys()), key="cost_model")
        rate_percent = st.number_input("Escalation rate (%):", value=3.0, min_value=0.0, key="EscRate")
        cost_start_year = st.number_input("Project start year:", value=2025, min_value=2011, key="CostYear")
        contingency_percent = st.number_input("Project Contingency Factor (%):", value=10.0, min_value=0.0, key="ContFactor")

        Dia = od_in                  # inches
        Lnth = length_km * 0.621371  # miles
        NumPumps = N_Pump

        if st.button("Calculate Pipeline Cost"):
            years = cost_start_year - 2011
            escalation_factor = (1 + rate_percent / 100.0) ** years
            Factor_CO2 = 1.25
            offshore_factor = 1.3
            categories = ["MAT", "LAB", "ROW", "MISC", "TOT"]
            model_name, model_func, region_args = model_options[model_name_key]
            costs_per_mile = []
            for cat in categories[:-1]:
                val = model_func(Dia, Lnth, *(region_args + (cat, 2011))) / Lnth
                if cat in ("MAT", "LAB"):
                    val *= Factor_CO2
                costs_per_mile.append(val)
            costs_total = [v * Lnth for v in costs_per_mile]
            # Surge tank, control system, booster station costs
            surge_tank_2000 = 701_600
            control_system_2000 = 94_000
            surge_tank_factor = 657.5 / 370.6
            control_system_factor = 438.7 / 368.5
            surge_tank_2011 = surge_tank_2000 * surge_tank_factor
            control_system_2011 = control_system_2000 * control_system_factor
            # Booster station (offshore) per pump
            total_booster_2011, _ = costbooster(Lnth)
            total_booster_pumps = total_booster_2011 * NumPumps
            # OFFSHORE COSTS for Project Year (apply escalation and offshore factor)
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
            # Markdown Output
            st.markdown("="*65)
            st.markdown(f"### CO2 offshore Pipeline cost based on {model_name} (capital costs {cost_start_year})")
            st.markdown(f"Material:        ${costs_total_proj_off[0]:,.0f}")
            st.markdown(f"Labor:           ${costs_total_proj_off[1]:,.0f}")
            st.markdown(f"ROW-Damages:     ${costs_total_proj_off[2]:,.0f}")
            st.markdown(f"Miscellaneous:   ${costs_total_proj_off[3]:,.0f}")
            st.markdown(f"CO₂ Surge Tank:           ${surge_tank_proj_off:,.0f}")
            st.markdown(f"Pipeline Control System:  ${control_system_proj_off:,.0f}")
            st.markdown(f"Booster station Offshore total cost ({NumPumps} pump(s)): ${booster_proj:,.0f}")
            st.markdown(f"Total capital cost (before contingencies): ${total_capital_proj_off:,.0f}")
            st.markdown(f"Contingency ({contingency_percent:.1f}%): ${contingency_proj_off:,.0f}")
            st.markdown(f"Total capital cost (with contingency): ${total_capital_proj_off_with_cont:,.0f}")
            st.markdown("="*65)
            # --- Define the cost breakdown for plotting ---
            cost_labels = [
                "Material", "Labor", "ROW-Damages", "Miscellaneous",
                "CO₂ Surge Tank", "Pipeline Control System",
                f"Booster station ({NumPumps} pump(s))",
                f"Contingency ({contingency_percent:.1f}%)"
            ]
            cost_values = [
                costs_total_proj_off[0],
                costs_total_proj_off[1],
                costs_total_proj_off[2],
                costs_total_proj_off[3],
                surge_tank_proj_off,
                control_system_proj_off,
                booster_proj,
                contingency_proj_off
            ]
            colors = [
                '#8dd3c7', '#bebada', '#fb8072', '#80b1d3',
                '#fdb462', '#b3de69', '#fccde5', '#bc80bd'
            ]
            import matplotlib.pyplot as plt

            # -----------------------------
            # STABLE CHARTS (no shaking)

            with st.expander("See Detailed Cost Charts", expanded=True):
                # two fixed columns so the page height/width doesn't reflow on rerun
                col_bar, col_pie = st.columns(2, gap="large")
            
                # ---------- Stacked Bar (legend ABOVE, outside axes) ----------
                fig_bar, ax_bar = plt.subplots(figsize=(6, 7), dpi=110)
            
                # cumulative bottoms
                bottoms = [0.0]
                for i in range(1, len(cost_values)):
                    bottoms.append(bottoms[-1] + cost_values[i - 1])
            
                # convert to MMUSD so y-axis ticks stay small and stable
                vals_mm = [v / 1e6 for v in cost_values]
                bottoms_mm = [b / 1e6 for b in bottoms]
            
                # single stacked bar
                bars = []
                for i, (val, color) in enumerate(zip(vals_mm, colors)):
                    b = ax_bar.bar("Total", val, bottom=bottoms_mm[i], color=color, label=cost_labels[i], width=0.65)
                    bars.append(b)
            
                ax_bar.set_ylabel("Cost (MMUSD)")
                ax_bar.set_xticks([])
                ax_bar.set_title("CO₂ Offshore Pipeline Stacked Cost Breakdown", pad=36)
            
                # — Legend above (outside axes, inside figure canvas) —
                handles, labels = ax_bar.get_legend_handles_labels()
                fig_bar.legend(
                    handles,
                    labels,
                    loc="lower center",
                    bbox_to_anchor=(0.5, 0.995),  # top-center, just inside the figure border
                    ncol=3,                       # adjust columns to your preference
                    fontsize=9,
                    frameon=False,
                    title="Categories",
                    title_fontsize=10,
                )
                # leave space at the top for the legend
                fig_bar.subplots_adjust(top=0.78)
            
                with col_bar:
                    bar_png = _fig_to_png(fig_bar, width_px=520)
                    # ✅ use_container_width fixes the deprecation warning
                    st.image(bar_png, caption="Stacked Cost Breakdown", use_container_width=True)
                plt.close(fig_bar)
            
                # ---------- Donut Pie (legend ABOVE, outside axes) ----------
                fig_pie, ax_pie = plt.subplots(figsize=(6, 6), dpi=110)
            
                wedges, _texts = ax_pie.pie(
                    cost_values,
                    labels=None,
                    autopct=None,
                    startangle=140,
                    colors=colors,
                    wedgeprops=dict(width=0.38),
                )
            
                total = float(sum(cost_values))
                for i, w in enumerate(wedges):
                    angle = (w.theta2 + w.theta1) / 2.0
                    pct = 100.0 * cost_values[i] / total
                    # short, neat pointers just outside the ring
                    x = 0.95 * np.cos(np.deg2rad(angle))
                    y = 0.95 * np.sin(np.deg2rad(angle))
                    ax_pie.annotate(
                        f"{pct:.1f}%",
                        xy=(x, y),
                        xytext=(1.12 * x, 1.12 * y),
                        textcoords="data",
                        ha="center",
                        va="center",
                        fontsize=10,
                        arrowprops=dict(arrowstyle="-", lw=0.8),
                        color=colors[i],
                    )
            
                ax_pie.axis("equal")
                ax_pie.set_title("Cost Share by Category", pad=36)
            
                # — Legend above (outside axes) —
                fig_pie.legend(
                    wedges,
                    cost_labels,
                    loc="lower center",
                    bbox_to_anchor=(0.5, 0.995),
                    ncol=3,
                    fontsize=9,
                    frameon=False,
                    title="Categories",
                    title_fontsize=10,
                )
                # space for legend
                fig_pie.subplots_adjust(top=0.78)
            
                with col_pie:
                    pie_png = _fig_to_png(fig_pie, width_px=520)
                    # ✅ use_container_width fixes the deprecation warning
                    st.image(pie_png, caption="Cost Share by Category", use_container_width=True)
                plt.close(fig_pie)
          
        st.markdown('</div>', unsafe_allow_html=True)



