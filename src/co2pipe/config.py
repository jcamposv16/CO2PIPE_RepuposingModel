"""Project paths and UI default values for CO2PIPE.

No absolute paths are hardcoded: PROJECT_ROOT is resolved relative to this file,
and the data directory can be overridden entirely via the CO2PIPE_DATA_DIR
environment variable (e.g. for tests, or an alternate deployment layout).
"""
import os
from pathlib import Path

# This file lives at <project root>/src/co2pipe/config.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DATA_DIR = Path(os.environ.get("CO2PIPE_DATA_DIR", PROJECT_ROOT / "data"))

PIPELINE_GEOJSON = DATA_DIR / "pipelines_uk.geojson"
TRAPS_GEOJSON = DATA_DIR / "traps_histories.geojson"

# Columns kept from the pipeline GeoJSON. See data_loader.load_pipelines for the
# meaning of each field.
PIPELINE_COLUMNS = [
    "FEATURE_ID", "PIPE_NAME", "OD_IN", "ID_IN", "PIPE_GRADE",
    "LENGTH_M", "THICKNESS", "START_DATE", "STATUS", "END_DATE",
    "geometry",
]

# All Streamlit widget default values, in one place. Keys are the EXACT local
# variable names eva11.py assigned each widget's return value to, so a sidebar
# widget built as `st.number_input(..., key="p_in_psia", value=DEFAULTS["p_in_psia"])`
# reproduces both the original variable name and its default unchanged.
DEFAULTS = {
    # -- "CO2 Transport Capacity Design" panel --
    "pipe_capacity_factor": 0.85,
    "p_in_psia": 2200.0,
    "p_out_psia": 1200.0,
    "tmp_c": 12.0,
    "qm_proyection_Mtpy": 4.30,
    "h_dif_tot": 0.0,
    "N_Pump": 0,
    "MW_in": 44.0095,

    # -- "Corrosion Calculate & Lifetime" panel (NORSOK M-506) --
    "QL": 1000.0,
    "QG": 5.0,
    "WC": 0.10,
    "Temp": 13.0,               # corrosion-panel temperature; distinct from tmp_c
    "Pressure": 50.0,
    "mole_percent_CO2": 1.00,
    "corrosion_rate_co2": 0.10,

    # -- "Cost Model Calculate" panel --
    "model_name_key": "PARKER",  # selectbox default = first option
    "rate_percent": 3.0,
    "cost_start_year": 2025,
    "contingency_percent": 10.0,
}
