<div align="center">

# ♻️ CO2PIPE

### Pipeline Repurposing Analysis Tool for Carbon Capture and Storage

*Technical and economic feasibility assessment of repurposing UK offshore oil and gas pipelines for CO₂ transport*

<br>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![GeoPandas](https://img.shields.io/badge/GeoPandas-1.1-139C5A?style=flat&logo=geopandas&logoColor=white)
![Folium](https://img.shields.io/badge/Folium-0.20-77B829?style=flat&logo=leaflet&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat&logo=numpy&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?style=flat&logo=pandas&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?style=flat&logo=python&logoColor=white)
![Shapely](https://img.shields.io/badge/Shapely-2.1-4B8BBE?style=flat)
![pytest](https://img.shields.io/badge/pytest-33_passing-0A9EDC?style=flat&logo=pytest&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![Hugging Face](https://img.shields.io/badge/🤗_Spaces-Deployed-FFD21E?style=flat)
![License](https://img.shields.io/badge/License-Academic-lightgrey?style=flat)

</div>

---

## Overview

**CO2PIPE** is an interactive decision-support tool that evaluates whether existing offshore oil and gas pipelines on the UK Continental Shelf can be safely and economically repurposed for CO₂ transport in Carbon Capture and Storage (CCS) projects.

The tool integrates three independent engineering assessments — **hydraulic capacity**, **corrosion and remaining lifetime**, and **capital cost estimation** — into a single geospatial interface, enabling rapid screening of candidate assets without requiring specialist modelling software.

Developed as part of an MSc Global Sustainability Engineering dissertation at Heriot-Watt University (course B41SD).

---

## Motivation

CO₂ transport and storage account for approximately **25–40% of total CCS project costs**, requiring substantial upfront capital for new pipeline and storage infrastructure. The UK Continental Shelf holds over **12,000 km of offshore pipelines** and more than **300 platforms** — assets that, if repurposed rather than decommissioned, could substantially accelerate CCS deployment.

Published studies suggest repurposing can reduce pipeline costs by **53–82%** relative to new construction. However, assessment of candidate pipelines remains difficult: historical operational records are incomplete, integrity data is fragmented across sources, and no accessible screening tool exists for early-stage evaluation.

CO2PIPE addresses this gap by consolidating a validated pipeline database with three physics- and economics-based evaluation modules in a single application.

---

## Evaluation Modules

<table>
<tr>
<th width="33%">🔵 Transport Capacity</th>
<th width="33%">🟠 Corrosion &amp; Lifetime</th>
<th width="33%">🟢 Cost Model</th>
</tr>
<tr>
<td valign="top">

Determines whether a pipeline can hydraulically carry the required CO₂ flow under dense-phase conditions.

**Output:** Max flow rate (Mt/yr), suitability verdict

</td>
<td valign="top">

Estimates historical material loss under hydrocarbon service and forecasts residual life under CO₂ service.

**Output:** Corrosion rate (mm/yr), available wall thickness, remaining lifetime (yrs)

</td>
<td valign="top">

Estimates CAPEX for constructing an equivalent new offshore CO₂ pipeline as the cost-saving baseline.

**Output:** Total capital cost, category breakdown, contingency

</td>
</tr>
</table>

<br>

### 1. CO₂ Transport Capacity Design

| Component | Method | Reference |
|---|---|---|
| CO₂ density | Duan equation of state, solved by Newton-Raphson | Duan et al. (1992) |
| CO₂ viscosity | Semi-empirical correlation (zero-density + excess terms) | Fenghour, Wakeham & Vesovic (1998) |
| Friction factor | Colebrook-White (iterative), initialised via Zigrang-Sylvester | Colebrook (1939) |
| Average pressure | Compressible-flow average between inlet and outlet | Mohitpour et al. (2003) |
| Maximum flow capacity | Iterative mass-flow solver coupled to Reynolds number and friction factor | McCoy & Rubin (2008) |

A pipeline is classified as **suitable** when the calculated maximum transport capacity exceeds the projected CO₂ demand, adjusted by a user-defined capacity factor.

**Inputs:** capacity factor · inlet/outlet pressure (psia) · temperature (°C) · target CO₂ flow (Mt/yr) · elevation change (m) · number of compression stations · CO₂ molecular weight

---

### 2. Corrosion Assessment & Remaining Lifetime

Implements the full **NORSOK M-506** CO₂ corrosion model, including its supporting chemistry:

$$CR_{NOR} = K_t \cdot (f_{CO_2})^{0.62} \cdot \left(\frac{S}{19}\right)^{0.146 + 0.0324\log_{10}(f_{CO_2})} \cdot f(pH)_t$$

| Component | Method |
|---|---|
| CO₂ fugacity | Pressure- and temperature-corrected partial pressure with real-gas coefficient |
| In-situ pH | Carbonate equilibrium chemistry — Henry's Law, dissociation constants K₁/K₂, ionic strength correction, FeCO₃ saturation |
| Wall shear stress | Multiphase mixture velocity, no-slip holdup, mixture density and viscosity |
| Minimum wall thickness | Barlow's formula with design factor 0.72 and temperature derating |
| Steel grade strength | API 5L SMYS lookup (A25 through X70) |

The remaining repurposing lifetime is derived from the available wall thickness margin — original thickness less historical corrosion loss less minimum required thickness — divided by the expected CO₂ corrosion rate. A negative margin indicates the asset is **unsuitable** for reuse.

**Inputs:** historical liquid/gas flow rates · water cut · CO₂ mole percent · operating pressure (bar) and temperature (°C) · expected CO₂ corrosion rate (mm/yr)

---

### 3. CAPEX Cost Estimation

Four published regression models, each decomposing cost into **materials**, **labour**, **right-of-way & damages**, and **miscellaneous**:

| Model | Reference | Base year | Regional resolution |
|---|---|---|---|
| **Parker** | Parker (2004), UC Davis ITS | 2000 | National |
| **Rui et al.** | Rui et al. (2011), *Oil & Gas Journal* | 2008 | 7 regions |
| **McCoy & Rubin** | McCoy & Rubin (2008), *Int. J. GHG Control* | 2004 | 6 regions |
| **Brown et al.** | Brown et al. (2022), *Int. J. Hydrogen Energy* | 2018 | 9 regions |

Costs are escalated from each model's base year to the project start year using a user-defined inflation rate, adjusted by an offshore factor, and supplemented with fixed costs for a **CO₂ surge tank**, **pipeline control system**, and **booster stations**. A project contingency factor is applied to the total.

**Inputs:** cost model · escalation rate (%) · project start year · contingency factor (%)

---

## Case Study — Goldeneye Pipeline

The framework was validated against the **Goldeneye pipeline** (20", 101.68 km, API 5L X60, in service 2003–2011), a primary candidate for infrastructure reuse in the **Acorn CCS project**, UK Central North Sea.

<table>
<tr><th align="left">Module</th><th align="left">Result</th><th align="left">Assessment</th></tr>
<tr>
<td><b>Hydraulic capacity</b></td>
<td>Density ~904 kg/m³ · Viscosity ~0.093 μPa·s<br><b>Max capacity: 9.1 MtCO₂/yr</b></td>
<td>✅ Exceeds the 5 MtCO₂/yr Acorn requirement. Properties consistent with published Acorn documentation.</td>
</tr>
<tr>
<td><b>Corrosion &amp; lifetime</b></td>
<td>Historical rate 0.373 mm/yr · Loss ~8.2 mm<br>Effective thickness ~14 mm vs. T<sub>min</sub> 6.23 mm<br><b>Available margin: 7.8 mm → 78 years</b></td>
<td>✅ Dry hydrocarbon service (zero water production) preserved wall integrity. Sufficient residual strength for long-term reuse.</td>
</tr>
<tr>
<td><b>Cost saving</b></td>
<td>Parker (2004), 2025 basis, 3% escalation, 10% contingency<br><b>New-build equivalent: $228.5 million</b></td>
<td>✅ Labour ~53%, materials ~24%, miscellaneous ~16%. Reuse avoids the majority of this expenditure.</td>
</tr>
</table>

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Interface** | Streamlit · custom CSS theming |
| **Geospatial** | GeoPandas · Shapely · Folium / Leaflet · pyproj (EPSG:4326 ↔ EPSG:27700) |
| **Numerical** | NumPy · pandas · iterative Newton-Raphson solvers |
| **Visualisation** | Matplotlib (server-side PNG rendering for render stability) |
| **Testing** | pytest — 33 regression tests validating all physics and economics modules to `rel=1e-12` |
| **Deployment** | Docker · Hugging Face Spaces |

---

## Project Structure

```
CO2PIPE/
├── app.py                          # Streamlit entrypoint (thin — wiring only)
├── Dockerfile
├── requirements.txt
├── .streamlit/config.toml          # Theme configuration
│
├── data/
│   ├── pipelines_uk.geojson        # 27 UK offshore pipelines (NSTA)
│   └── traps_histories.geojson     # CO₂ geological storage traps (HiSTORIEs)
│
├── src/co2pipe/
│   ├── config.py                   # Paths, constants, UI defaults
│   ├── data_loader.py              # Cached GeoJSON loaders
│   │
│   ├── physics/                    # Pure functions — no UI dependencies
│   │   ├── units.py                # Unit conversions
│   │   ├── co2_properties.py       # Duan EOS, Peng-Robinson, Span-Wagner, viscosity
│   │   ├── hydraulics.py           # Reynolds, Colebrook-White, average pressure
│   │   ├── pipe_sizing.py          # ASME/API schedules, Barlow's formula, SMYS
│   │   └── corrosion.py            # NORSOK M-506 full chain
│   │
│   ├── economics/
│   │   └── cost_models.py          # Parker · Rui · McCoy · Brown + escalation
│   │
│   └── ui/
│       ├── theme.py                # Colour palette and CSS injection
│       ├── map_view.py             # Folium map builder and click resolution
│       ├── panels.py               # Compute and render functions per module
│       └── charts.py               # Stacked bar and donut cost charts
│
├── tests/
│   └── test_physics.py             # 33 regression tests
└── archive/                        # Superseded development iterations
```

**Design principle:** calculation logic is fully decoupled from the interface. No module under `physics/` or `economics/` imports Streamlit, allowing every correlation to be tested, reused, or called independently of the web application.

---

## Getting Started

**Requirements:** Python 3.11+ · pip

```bash
# Clone
git clone https://huggingface.co/spaces/jcamposv16/CO2PIPE
cd CO2PIPE

# Install dependencies
pip install -r requirements.txt

# Launch
streamlit run app.py --server.port=8507
```

The application opens at **http://localhost:8507**

### Running the test suite

```bash
pytest tests/test_physics.py -v
```

All 33 regression tests validate the physics and economics modules against reference values captured from the original validated implementation.

### Docker

```bash
docker build -t co2pipe .
docker run -p 8501:8501 co2pipe
```

---

## Usage

1. **Select a pipeline** — via the sidebar dropdown or by clicking a line on the map. Attributes (length, OD, ID, wall thickness, grade, service dates, status) populate automatically.
2. **Adjust parameters** — expand the Transport, Corrosion, or Cost Model sections in the sidebar. Defaults are pre-populated with typical values for sensitivity testing.
3. **Run Analysis** — computes all three modules simultaneously.
4. **Review results** — headline metrics, supporting detail, and cost breakdown charts are presented across three tabs.

---

## Data Sources

| Dataset | Source | Notes |
|---|---|---|
| **Pipeline network** | North Sea Transition Authority (NSTA) UKCS Offshore Infrastructure open data | 8,000+ records screened |
| **Candidate screening** | BEIS consultation — *CCUS projects: re-use of oil and gas assets* | 51 pipelines identified |
| **Final dataset** | Cross-referenced, validated, standardised, and enriched | **27 pipelines** with complete technical specifications |
| **Geological traps** | HiSTORIEs project CO₂ storage trap layer | 1,088 features, EPSG:4326 |

Missing engineering specifications were supplemented through review of OGA archival documents, journal publications, and industry case studies. Where direct records were unavailable, engineering standards were applied to infer typical material properties consistent with historical construction practice.

---

## Methodology Alignment

The evaluation workflow follows the structure defined in **DNV-SE-0657**, *Re-qualification of pipeline systems for transport of hydrogen and carbon dioxide*, which specifies a ten-step process combining hydraulic assessment (establishing a revised basis of design) with integrity assessment (determining remaining safe operational life). CO2PIPE implements the analytical components of that specification.

---

## Roadmap

- [ ] Life cycle assessment (LCA) module — embodied carbon and avoided decommissioning emissions
- [ ] Risk assessment module
- [ ] Cluster-scale network optimisation
- [ ] Expanded dataset coverage beyond the current 27 validated pipelines
- [ ] Export of results to PDF/Excel for project documentation

---

## References

<details>
<summary><b>Thermodynamics and hydraulics</b></summary>

<br>

- Duan, Z., Møller, N. & Weare, J.H. (1992). An equation of state for the CH₄-CO₂-H₂O system: I. Pure systems from 0 to 1000 °C and 0 to 8000 bar. *Geochimica et Cosmochimica Acta*, 56, 2605–2617.
- Fenghour, A., Wakeham, W.A. & Vesovic, V. (1998). The viscosity of carbon dioxide. *Journal of Physical and Chemical Reference Data*, 27(1), 31–44.
- Span, R. & Wagner, W. (1996). A new equation of state for carbon dioxide covering the fluid region.
- Colebrook, C.F. (1939). Turbulent flow in pipes, with particular reference to the transition region between the smooth and rough pipe laws. *Journal of the Institution of Civil Engineers*, 11(4), 133–156.
- McCoy, S.T. & Rubin, E.S. (2008). An engineering-economic model of pipeline transport of CO₂ with application to carbon capture and storage. *International Journal of Greenhouse Gas Control*, 2(2), 219–229.
- Mohitpour, M., Golshan, H. & Murray, M.A. (2003). *Pipeline Design & Construction: A Practical Approach*. ASME Press.
- Mohitpour, M., Seevam, P., Botros, K.K., Rothwell, B. & Ennis, C. (2012). *Pipeline Transportation of Carbon Dioxide Containing Impurities*. ASME Press.

</details>

<details>
<summary><b>Corrosion and integrity</b></summary>

<br>

- NORSOK (2025). *CO₂ Corrosion Rate Calculation Model*, M-506.
- Nešić, S. (2007). Key issues related to modelling of internal corrosion of oil and gas pipelines — A review. *Corrosion Science*, 49(12), 4308–4338.
- Doğan, B. & Altınten, A. (2023). Mathematical modelling of CO₂ corrosion with NORSOK M-506. *Bitlis Eren University Journal of Science*, 12(1), 84–92.
- ASME (2003). *ASME B31.8 — Gas Transmission and Distribution Piping Systems*.
- DNV (2023). *DNV-SE-0657 — Re-qualification of pipeline systems for transport of hydrogen and carbon dioxide*.
- Ahamad, M., Rahman, H. & Osman, S. (2022). Pipeline wall thickness assessment of various material grades and water depths using American and Norwegian standards. *Jurnal Kejuruteraan*, 34, 1135–1147.

</details>

<details>
<summary><b>Cost models</b></summary>

<br>

- Parker, N. (2004). *Using Natural Gas Transmission Pipeline Costs to Estimate Hydrogen Pipeline Costs*. UCD-ITS-RR-04-35, Institute of Transportation Studies, UC Davis.
- Rui, Z., Metz, P., Reynolds, D., Chen, G. & Zhou, X. (2011). Regression models estimate pipeline construction costs. *Oil and Gas Journal*, 109, 120–127.
- Brown, D., Reddi, K. & Elgowainy, A. (2022). The development of natural gas and hydrogen pipeline capital cost estimating equations. *International Journal of Hydrogen Energy*, 47(79), 33813–33826.
- NETL (2024). *FECM/NETL CO₂ Transport Cost Model: Description and User's Manual*.

</details>

<details>
<summary><b>Policy and context</b></summary>

<br>

- IPCC (2005). *Carbon Dioxide Capture and Storage*. Cambridge University Press.
- IPCC (2021). *Climate Change 2021 — The Physical Science Basis*. Cambridge University Press.
- CCC (2025). *Progress in Reducing Emissions — 2025 Report to Parliament*. Climate Change Committee.
- DESNZ (2023). *Carbon Capture, Usage and Storage: A Vision to Establish a Competitive Market*.
- Bentham, M., Mallows, T., Lowndes, J. & Green, A. (2014). CO₂ STORage Evaluation Database (CO₂ Stored) — The UK's online storage atlas. *Energy Procedia*, 63, 5103–5113.
- Calvillo, C., Race, J., Chang, E., Turner, K. & Katris, A. (2022). Characterisation of UK industrial clusters and techno-economic cost assessment for CO₂ transport and storage implementation. *International Journal of Greenhouse Gas Control*, 119, 103695.

</details>

---

## Author

**Jean Carlos Campos Valverde**  
MSc Global Sustainability Engineering — Heriot-Watt University, Edinburgh  
School of Engineering and Physical Sciences

**Supervisors:** Prof. Susana Garcia Lopez · Dr. Amir Jahanbakhsh

📧 jc3021@hw.ac.uk

---

<div align="center">
<sub>Developed as part of the B41SD Sustainability Dissertation — <i>Repurposing Oil and Gas Infrastructure for Accelerating Decarbonization in the United Kingdom</i></sub>
</div>
