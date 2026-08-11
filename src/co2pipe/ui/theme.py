"""Light, restrained visual theme for CO2PIPE: color constants + CSS injection.

Categorical chart palette validated against the dataviz skill's palette method:
`node scripts/validate_palette.js "<hexes>" --mode light --surface "#FFFFFF"`
-- see the accompanying summary for the full validator report (one WARN,
mitigated by direct labels + legend, matching the skill's documented default
behavior for this exact palette on a white surface).
"""
import streamlit as st

# ---------------------------------------------------------------------------
# Core surfaces & text (light, restrained, engineering-tool feel)
# ---------------------------------------------------------------------------
BG = "#F5F6F8"                  # page background, warm-neutral grey
SURFACE = "#FFFFFF"             # cards, sidebar, chart background
SURFACE_ALT = "#EEF0F3"         # subtle zebra / secondary fill
BORDER = "#DDE1E6"              # hairline borders

TEXT_PRIMARY = "#16202E"
TEXT_SECONDARY = "#4A5567"
TEXT_MUTED = "#7C8697"

# ---------------------------------------------------------------------------
# Single accent color for all interactive elements (buttons, active tab,
# selected pipeline on the map, metric emphasis). Deep petrol blue --
# desaturated so it reads as technical, not consumer/marketing.
# ---------------------------------------------------------------------------
ACCENT = "#0E5C8E"
ACCENT_HOVER = "#0A4A73"
ACCENT_TINT = "#DCEAF4"         # selected-row / hover background wash

# ---------------------------------------------------------------------------
# Map: selected vs. unselected pipeline styling
# ---------------------------------------------------------------------------
MAP_SELECTED = ACCENT
MAP_UNSELECTED = "#8A94A3"      # muted grey -- visible on both basemaps
MAP_HOVER = "#2E86C4"

# Geological trap layer (unchanged from the previous theme)
TRAP_EDGE = "#C43C00"
TRAP_FILL = "#FF7F0E"
TRAP_ALPHA = 0.28

# ---------------------------------------------------------------------------
# Status colors (reserved -- never reused for chart series identity)
# ---------------------------------------------------------------------------
STATUS_GOOD = "#1E7B4F"
STATUS_WARNING = "#B7791F"
STATUS_CRITICAL = "#B3261E"

# ---------------------------------------------------------------------------
# Categorical palette for the cost-breakdown charts (bar + donut), fixed
# order, 8 slots for the 8 cost categories. Light-mode set, validated via
# `node scripts/validate_palette.js "<hexes>" --mode light --surface "#FFFFFF"`:
# lightness band, chroma floor, CVD separation, and normal-vision floor all
# PASS. Contrast-vs-surface WARNs on 3 slots (aqua, yellow, magenta fall
# below 3:1 on pure white) -- mitigated per the skill's "relief rule" by the
# direct percentage labels + always-on legend in charts.py (never bare fills
# relying on the color alone for identity).
# ---------------------------------------------------------------------------
CATEGORICAL = [
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 green
    "#4a3aa7",  # 7 violet
    "#e34948",  # 8 red
]

CHART_GRIDLINE = BORDER
CHART_BASELINE = BORDER

FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


def inject_css() -> None:
    """Inject the app-wide CSS: light page background, header fix so the
    Streamlit toolbar stops overlapping the title, metric card styling,
    sidebar, buttons, and tabs. Does not create any container elements of
    its own -- callers must not wrap content in empty
    st.container()/st.markdown("") calls either.
    """
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-family: {FONT_FAMILY};
        }}

        /* -- page background -- */
        .stApp {{
            background-color: {BG};
        }}

        /* -- Streamlit's own toolbar sits in stHeader; make it blend into BG
           instead of a solid white bar overlapping the app title below it -- */
        [data-testid="stHeader"] {{
            background-color: {BG};
        }}

        /* -- tighten default Streamlit padding/spacing, and push content down
           far enough that the title never sits under the toolbar -- */
        .block-container {{
            padding-top: 3.25rem;
            padding-bottom: 2rem;
            max-width: 100%;
        }}
        div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div {{
            gap: 0.5rem;
        }}
        [data-testid="stExpander"] {{
            margin-bottom: 0.5rem;
        }}

        /* -- sidebar -- */
        [data-testid="stSidebar"] {{
            background-color: {SURFACE};
            border-right: 1px solid {BORDER};
        }}
        [data-testid="stSidebar"] .block-container {{
            padding-top: 1rem;
        }}

        /* -- headings -- */
        h1, h2, h3, h4 {{
            color: {TEXT_PRIMARY};
            font-weight: 600;
        }}
        h1 {{ font-size: 1.5rem; margin-bottom: 0; }}

        /* -- metric cards: flat white surface, hairline border, no shadow -- */
        [data-testid="stMetric"] {{
            background-color: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 0.9rem 1rem;
            box-shadow: none;
        }}
        [data-testid="stMetricLabel"] {{
            color: {TEXT_MUTED};
        }}
        [data-testid="stMetricValue"] {{
            color: {TEXT_PRIMARY};
            font-size: 1.35rem;
            font-weight: 600;
        }}

        /* -- buttons: single accent color -- */
        .stButton > button {{
            background-color: {ACCENT};
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            font-weight: 600;
        }}
        .stButton > button:hover {{
            background-color: {ACCENT_HOVER};
            color: #FFFFFF;
        }}

        /* -- tabs -- */
        button[data-baseweb="tab"] {{
            color: {TEXT_SECONDARY};
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {ACCENT};
            border-bottom: 2px solid {ACCENT} !important;
        }}

        /* -- expander header -- */
        [data-testid="stExpander"] summary {{
            font-weight: 600;
            color: {TEXT_PRIMARY};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
