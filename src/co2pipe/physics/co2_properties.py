"""CO2 thermodynamic property correlations (Span-Wagner, Peng-Robinson, Duan EOS).

Extracted verbatim (formulas and constants unchanged) from streamlit_map_eva11.py.

Note: a handful of internal helper functions (densvSWCO2, fvolPRCO2, d1fvolPRCO2,
fDuanCO2, d1fDuanCO2) are not part of the caller's explicitly requested public list
but are required dependencies of volPRCO2 / volDuanCO2's Newton-Raphson solvers and
are therefore included so those functions run unchanged. denDuanCO2 is likewise not
in the requested list but is included because the eva11.py transport-design panel
calls it directly to get CO2 mass density. See the accompanying summary for details.
"""
import numpy as np


def vpSWCO2(tmp: float) -> float:
    """CO2 saturation (vapor) pressure.

    Source: Span & Wagner (1996) CO2 equation of state, vapor-pressure correlation.
    Units in: tmp in K
    Units out: MPa
    """
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


def denslSWCO2(tmp: float) -> float:
    """CO2 saturated liquid density.

    Source: Span & Wagner (1996) CO2 equation of state, saturated-liquid-density correlation.
    Units in: tmp in K
    Units out: kg/m3
    """
    tmpcrit = 304.1282  # Critical temperature (K)
    dencrit = 467.6     # Critical density (kg/m3)

    a = [1.9245108, -0.62385555, -0.32731127, 0.39245142]
    n = [0.34, 0.5, 10/6, 11/6]

    Tr = tmp / tmpcrit
    sum_terms = sum(a[i] * (1 - Tr)**n[i] for i in range(4))

    density = dencrit * np.exp(sum_terms)

    return density


def densvSWCO2(tmp: float) -> float:
    """CO2 saturated vapor density.

    Source: Span & Wagner (1996) CO2 equation of state, saturated-vapor-density correlation.
    Units in: tmp in K
    Units out: kg/m3

    Internal helper used by volPRCO2 / volDuanCO2 to bound the initial molar-volume
    guess in the vapor region.
    """
    tmpcrit = 304.1282  # Critical temperature (K)
    dencrit = 467.6     # Critical density (kg/m3)

    a = [-1.7074879, -0.8227467, -4.6008549, -10.111178, -29.742252]
    n = [0.34, 0.5, 1.0, 7/3, 14/3]

    Tr = tmp / tmpcrit
    sum_terms = sum(a[i] * (1 - Tr)**n[i] for i in range(5))
    density = dencrit * np.exp(sum_terms)

    return density


def fvolPRCO2(vol: float, pres: float, tmp: float) -> float:
    """Peng-Robinson (1976) cubic EOS residual function in molar volume, F(v) = 0 at the root.

    Units in: vol in m3/mol, pres in MPa, tmp in K
    Units out: dimensionless residual (MPa * (m3/mol)^3 scale)

    Internal helper (Newton-Raphson residual) used by volPRCO2.
    """
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


def d1fvolPRCO2(vol: float, pres: float, tmp: float) -> float:
    """Derivative of fvolPRCO2 with respect to molar volume.

    Units in: vol in m3/mol, pres in MPa, tmp in K
    Units out: dF/dv

    Internal helper (Newton-Raphson derivative) used by volPRCO2.
    """
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


def volPRCO2(volinit: float, pres: float, tmp: float) -> float:
    """CO2 molar volume from the Peng-Robinson (1976) EOS via Newton-Raphson root-finding.

    Source: Peng-Robinson (1976) cubic equation of state.
    Units in: volinit in m3/mol (pass 0 or negative for auto initial guess), pres in MPa, tmp in K
    Units out: molar volume in m3/mol
    """
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


def fDuanCO2(vol: float, pres: float, tmp: float) -> float:
    """Duan et al. CO2 equation-of-state residual function in molar volume, F(v) = 0 at the root.

    Units in: vol in m3/mol, pres in MPa, tmp in K
    Units out: dimensionless residual

    Internal helper (Newton-Raphson residual) used by volDuanCO2.
    """
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


def d1fDuanCO2(vol: float, pres: float, tmp: float) -> float:
    """Derivative of fDuanCO2 with respect to molar volume.

    Units in: vol in m3/mol, pres in MPa, tmp in K
    Units out: dF/dv

    Internal helper (Newton-Raphson derivative) used by volDuanCO2.
    """
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


def volDuanCO2(volinit: float, pres: float, tmp: float) -> float:
    """CO2 molar volume from the Duan et al. equation of state via Newton-Raphson root-finding.

    Source: Duan et al. CO2 equation of state (citation not specified in the original source file).
    Units in: volinit in m3/mol (pass 0 or negative for auto initial guess), pres in MPa, tmp in K
    Units out: molar volume in m3/mol
    """
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


def denDuanCO2(volinit: float, pres: float, tmp: float) -> float:
    """CO2 mass density from the Duan et al. equation of state.

    Source: Duan et al. CO2 equation of state (via volDuanCO2 molar volume).
    Units in: volinit in m3/mol, pres in MPa, tmp in K
    Units out: kg/m3

    Not in the caller's originally requested function list, but included here because
    the eva11.py transport-design panel calls this function directly to get CO2 density.
    """
    MW = 44.0095   # Molecular weight of CO2 (g/mol)
    mol_vol = volDuanCO2(volinit, pres, tmp)  # Molar volume (m3/mol)
    density = MW * 0.001 / mol_vol

    return density


def zfactDuanCO2(volinit: float, pres: float, tmp: float) -> float:
    """CO2 compressibility (Z) factor from the Duan et al. equation of state.

    Source: Duan et al. CO2 equation of state (via volDuanCO2 molar volume).
    Units in: volinit in m3/mol, pres in MPa, tmp in K
    Units out: dimensionless
    """
    Rgas = 0.000008314  # Universal gas constant (m3-MPa/(K-mol))
    mol_vol = volDuanCO2(volinit, pres, tmp)  # Calculate molar volume (m3/mol)
    z_factor = (pres * mol_vol) / (Rgas * tmp)

    return z_factor


def visFWVCO2(den: float, tmp: float) -> float:
    """CO2 dynamic viscosity.

    Source: Fenghour, Wakeham & Vesovic (1998) CO2 viscosity correlation
    (identified from function-name convention "FWV"; not explicitly cited in source code).
    Units in: den in kg/m3, tmp in K
    Units out: microPa*s (uPa*s)
    """
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
