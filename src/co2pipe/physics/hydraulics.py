"""Pipeline hydraulics: Reynolds number, friction factors, and average pressure.

Extracted verbatim (formulas and constants unchanged) from streamlit_map_eva11.py.
"""
import numpy as np


def reynolds_number(FR: float, Visc: float, Dia: float) -> float:
    """Reynolds number for flow in a circular pipe.

    Units in: FR (mass flow rate) in kg/s, Visc (dynamic viscosity) in Pa*s, Dia in m
    Units out: dimensionless
    """
    pi = np.pi
    Re = 4 * FR / (pi * Visc * Dia)

    return Re


def fanning_friction_factor(Dia: float, Re: float, eta: float, FF_Eq: int) -> float:
    """Fanning friction factor via an explicit correlation.

    Source: FF_Eq=0 uses the Haaland equation (McCollum and Ogden, 2006);
    FF_Eq!=0 uses the Zigrang & Sylvester equation (McCoy & Rubin, 2008).
    Units in: Dia in m, Re dimensionless, eta (pipe roughness) in m
    Units out: dimensionless (Fanning friction factor)
    """
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


def fanning_friction_colebrook(ReN: float, Dia: float, eta: float) -> float:
    """Fanning friction factor via the implicit Colebrook-White equation, solved by iteration.

    Source: Colebrook-White equation, initial guess from Zigrang & Sylvester
    (via fanning_friction_factor(..., FF_Eq=1)).
    Units in: ReN dimensionless (Reynolds number), Dia in m, eta (pipe roughness) in m
    Units out: dimensionless (Fanning friction factor)
    """
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


def pav_gas(p_in: float, p_out: float) -> float:
    """Average pipeline segment pressure for compressible (gas) flow.

    Units in: p_in, p_out in any consistent pressure unit (e.g. MPa)
    Units out: same unit as inputs
    """
    pav = (2 / 3) * (p_out + p_in - p_out * p_in / (p_out + p_in))

    return pav
