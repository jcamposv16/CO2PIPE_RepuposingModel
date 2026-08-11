"""Pipe schedule sizing, minimum wall thickness, and steel grade lookups.

Extracted verbatim (formulas and constants unchanged) from streamlit_map_eva11.py.
"""
from co2pipe.physics.units import Conv_Dpipeline


def Pipe_Size(Dia: float, Dia_units: str) -> int:
    """Round a diameter up to the nearest standard nominal pipe size (NPS).

    Units in: Dia in the unit given by Dia_units ('m' or 'in')
    Units out: nominal pipe size in inches (2000 flags an oversized/out-of-range pipe)
    """
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


def Dia_in_nom(Dia_nom: float, Dia_nom_units: str) -> float:
    """Standard nominal inner diameter (inches) for a given nominal pipe size.

    Units in: Dia_nom in the unit given by Dia_nom_units ('m' or 'in')
    Units out: nominal inner diameter in inches (99.9 flags an oversized/out-of-range pipe)
    """
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


def Pthick_nom(Dia_nom: float, Dia_nom_units: str) -> float:
    """Standard nominal wall thickness (inches) for a given nominal pipe size.

    Units in: Dia_nom in the unit given by Dia_nom_units ('m' or 'in')
    Units out: nominal wall thickness in inches
    """
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


def get_minimum_yield_strength(grade: str) -> int:
    """Specified Minimum Yield Strength (SMYS) for a pipe steel grade.

    Source: standard API 5L pipe grade SMYS table.
    Units in: grade string, e.g. "X60"
    Units out: psi
    """
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


def temp_derating_factor(temp_c: float) -> float:
    """Temperature derating factor applied to allowable stress for wall-thickness design.

    Units in: temp_c in degrees C
    Units out: dimensionless factor (interpolated from a fixed lookup table)
    """
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
    pressure: float,           # Internal pressure, Pa (or same units as yield strength)
    diameter: float,           # Outside diameter, m
    temp_c: float,             # Temperature in Celsius
    grade: str,                # Pipe grade string, e.g. "X60"
) -> float:
    """Minimum required pipe wall thickness.

    Source: Barlow's formula with temperature derating (ASME B31-style design equation).
    Units in: pressure in Pa, diameter in m, temp_c in degrees C, grade as API 5L string
    Units out: millimeters
    """
    # Get SMYS (Specified Minimum Yield Strength) in psi, convert to Pa (1 psi = 6894.76 Pa)
    S_psi = get_minimum_yield_strength(grade)
    S = S_psi * 6894.76     # Pa

    F = 0.72                # Allowable stress factor for pipeline
    T = temp_derating_factor(temp_c)  # Temperature derating factor

    # Po (external pressure) is neglected as per your comment: (Pi - Po) → pressure
    t_min_m = (pressure * diameter) / (2 * S * F * T)
    t_min_mm = t_min_m * 1000  # convert to millimeters

    return t_min_mm
