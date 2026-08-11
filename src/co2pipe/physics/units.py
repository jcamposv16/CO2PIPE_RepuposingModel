"""Unit conversion helpers used throughout the pipeline physics calculations.

Extracted verbatim (formulas and constants unchanged) from streamlit_map_eva11.py.
"""


def flowrate_Mtpy_to_kgps(FR_val: float) -> float:
    """Convert a CO2 mass flow rate from million tonnes per year to kilograms per second.

    Units in: Mtonnes/year
    Units out: kg/s
    """
    kg_per_s = FR_val * 1_000_000 * 1000 / (365 * 24 * 3600)
    return kg_per_s


def psia_to_mpa(P_Val: float) -> float:
    """Convert pressure from psia to MPa.

    Units in: psia
    Units out: MPa
    """
    P_MPa = P_Val * 6894.757 / 1_000_000
    return P_MPa


def Conv_Lpipeline(length_miles: float) -> float:
    """Convert pipeline length from miles to meters.

    Units in: miles
    Units out: meters
    """
    L_pipeline_meter = length_miles * 1609.344
    return L_pipeline_meter


def Conv_temp(temp_c: float) -> float:
    """Convert temperature from Celsius to Kelvin.

    Units in: degrees C
    Units out: K
    """
    temp_k = temp_c + 273.15
    return temp_k


def Conv_Dpipeline(D_val: float, U_in: str, U_out: str) -> float:
    """Convert a pipeline diameter between meters and inches.

    Units in: D_val in the unit given by U_in ('m' or 'in')
    Units out: D_val converted to the unit given by U_out ('m' or 'in')
    """
    if U_in == 'm' and U_out == 'in':
        # 1 meter = 39.3701 inches
        return D_val * 39.3701
    elif U_in == 'in' and U_out == 'm':
        return D_val / 39.3701
    elif U_in == U_out:
        return D_val
    else:
        raise ValueError("Invalid units. Allowed: 'm' and 'in'.")
