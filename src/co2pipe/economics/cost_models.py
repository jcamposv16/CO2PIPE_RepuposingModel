"""Pipeline capital cost (CAPEX) estimation models.

Extracted verbatim (formulas and constants unchanged) from streamlit_map_eva11.py.

Note on a duplicate found in the original source: eva11.py defined `costbooster`
TWICE (once taking length_km and returning a single float in EUR, then immediately
redefined taking length_mi and returning a (total_usd, cost_per_mile_usd) tuple).
Because Python keeps only the last definition, the app only ever used the second,
tuple-returning version -- confirmed by its one live call site (Cost Model panel:
`total_booster_2011, _ = costbooster(Lnth)`). Only that live version is kept here;
the shadowed first definition is dropped as dead code.

The eva11.py `total_cost(length_km, diameter_inch)` helper is also dropped: it was
never called anywhere in the app, and due to the costbooster duplicate above it was
actually broken (it called costbooster(length_km) expecting a float back, but by
that point in the file costbooster returns a 2-tuple, so total_cost would raise
TypeError: unsupported operand type(s) for +: 'float' and 'tuple' if it were ever
invoked). Not part of the caller's requested function list, so it is not extracted.
"""
import math


def costpipe(length_km: float, diameter_inch: float) -> float:
    """Estimate the investment cost for an offshore CO2 pipeline (ANSI 1500).

    Source: IEA (2002) offshore pipeline cost constants, fixed terrain factor of 1.2.
    Units in: length_km in kilometers, diameter_inch in inches
    Units out: Euros (€)
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


def costbooster(length_mi: float):
    """Investment cost for offshore booster stations.

    Source: IEA GHG (2002) offshore booster station cost (70,000 €/km base year 2000),
    escalated to 2011 USD via the Handy-Whitman index.
    Units in: length_mi in miles
    Units out: tuple of (total cost in 2011 USD, cost per mile in 2011 USD/mi)
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


def CpParker(Dia: float, Lnth: float, Categ: str, ConYr: int):
    """Pipeline capital costs by category (materials, labor, ROW, misc, or total).

    Source: Parker, N., 2004. "Using Natural Gas Transmission Pipeline Costs to Estimate
    Hydrogen Pipeline Costs", UCD-ITS-RR-04-35, Institute of Transportation Studies, UC Davis.
    Units in: Dia (diameter) in inches, Lnth (length) in miles,
              Categ in {"MAT","LAB","ROW","MISC","TOT"}, ConYr in {2011, 0 (=2000 base year)}
    Units out: USD (in the requested cost year), or the string "Error" for an unknown category
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


def CpRui1(Dia: float, Lnth: float, Reg: str, Categ: str, ConYr: int):
    """Pipeline capital costs by category for a single US region.

    Source: Rui, Z., P. Metz, D. Reynolds, G. Chen, and X. Zhou, 2011. "Regression Models
    Estimate Pipeline Construction Costs", Oil and Gas Journal, July 4, 2011.
    Units in: Dia (diameter) in inches, Lnth (length) in miles,
              Reg in {"CEN","NE","SE","MW","SW","WEST","CAN"},
              Categ in {"MAT","LAB","ROW","MISC","TOT"}, ConYr in {2011, 0 (=2008 base year)}
    Units out: USD (in the requested cost year), or the string "Error" for an unknown region/category
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


def CpRui(Dia: float, Lnth: float, Reg: str, Categ: str, ConYr: int):
    """Pipeline capital costs by category, with region "AVG" averaging six US regions.

    Source: Rui et al. (2011) — see CpRui1.
    Units in: Dia in inches, Lnth in miles, Reg in {"CEN","NE","SE","MW","SW","WEST","CAN","AVG"},
              Categ in {"MAT","LAB","ROW","MISC","TOT"}, ConYr in {2011, 0 (=2008 base year)}
    Units out: USD (in the requested cost year), or the string "Error" for an unknown region/category
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


def CpMcCoy1(Dia: float, Lnth: float, Reg: str, Categ: str, ConYr: int):
    """Pipeline capital costs by category for a single US region.

    Source: McCoy, S. and E. Rubin, 2008. "An Engineering-Economic Model of Pipeline
    Transport of CO2 with Application to Carbon Capture and Storage", Int. J. of
    Greenhouse Gas Control, Vol. 2, pgs. 219-229.
    Units in: Dia (diameter) in inches, Lnth (length) in miles,
              Reg in {"CEN","NE","SE","MW","SW","WEST"},
              Categ in {"MAT","LAB","ROW","MISC","TOT"}, ConYr in {2011, 0 (=2004 base year)}
    Units out: USD (in the requested cost year), or the string "Error" for an unknown region/category
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


def CpMcCoy(Dia: float, Lnth: float, Reg: str, Categ: str, ConYr: int):
    """Pipeline capital costs by category, with region "AVG" averaging six US regions.

    Source: McCoy and Rubin (2008) — see CpMcCoy1.
    Units in: Dia in inches, Lnth in miles, Reg in {"CEN","NE","SE","MW","SW","WEST","AVG"},
              Categ in {"MAT","LAB","ROW","MISC","TOT"}, ConYr in {2011, 0 (=2004 base year)}
    Units out: USD (in the requested cost year), or the string "Error" for an unknown region/category
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


def CpBrown1(Dia: float, Lnth: float, Reg: str, Categ: str, ConYr: int):
    """Pipeline capital costs by category for a single US region.

    Source: Brown, D., K. Reddi and A. Elgowainy, 2022. "The Development of Natural Gas
    and Hydrogen Pipeline Capital Cost Estimating Equations", International Journal of
    Hydrogen Energy, Vol. 47, pgs. 33813-33826.
    Units in: Dia (diameter) in inches, Lnth (length) in miles,
              Reg in {"NE","MA","SE","GL","GP","RM","PN","SW","CA"},
              Categ in {"MAT","LAB","ROW","MISC","TOT"}, ConYr in {2011, 0 (=2018 base year)}
    Units out: USD (in the requested cost year), or the string "Error" for an unknown region/category
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


def CpBrown(Dia: float, Lnth: float, Reg: str, Categ: str, ConYr: int):
    """Pipeline capital costs by category, with region "AVG" averaging nine US regions.

    Source: Brown et al. (2022) — see CpBrown1.
    Units in: Dia in inches, Lnth in miles,
              Reg in {"NE","MA","SE","GL","GP","RM","PN","SW","CA","AVG"},
              Categ in {"MAT","LAB","ROW","MISC","TOT"}, ConYr in {2011, 0 (=2018 base year)}
    Units out: USD (in the requested cost year), or the string "Error" for an unknown region/category
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


def escalation_factor(escalation_rate_percent: float, starting_year: int) -> float:
    """Cost escalation factor from the 2011 base year to a project's starting year.

    Units in: escalation_rate_percent in percent (e.g. 3 for 3%), starting_year as a calendar year
    Units out: dimensionless multiplier
    """
    years = starting_year - 2011
    escalation_rate = escalation_rate_percent / 100.0
    escalation_factor = (1 + escalation_rate) ** years
    return escalation_factor
