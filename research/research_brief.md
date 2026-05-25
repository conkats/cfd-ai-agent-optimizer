# Research Brief: 2D Cross-Flow Bluff Body Shape Comparison
**Code_Saturne k-ω SST, Re ≈ 1e4, Cd/Cl/St/Cp/Wake Analysis**

---

## Executive Summary

This brief synthesises aerodynamic data for four 2D bluff shapes (circular cylinder, square, half-cylinder, equilateral triangle prism) in cross-flow at Re ≈ 10,000 using k-ω SST turbulence closure. Key findings: circular cylinders exhibit Cd ≈ 1.0–1.2, Strouhal ≈ 0.21; square cylinders Cd ≈ 2.0–2.2, St ≈ 0.12–0.14 with sharper separation; equilateral triangles Cd ≈ 1.6–2.0, St ≈ 0.22 depending on orientation. Base pressure coefficient ranges from Cp_base ≈ −1.0 (cylinder) to −0.3 (square). Post-processing must extract 10 integral quantities (Cd_mean, Cd_rms, Cl_rms, Cl_amp, St via FFT, mean base pressure) and produce 4-panel velocity contours, Cp distributions, phase-averaged Cl(t) spectra, and wake velocity profiles. This brief provides the exact computational recipes for Teammates 3–5.

---

## Key Findings

### 1. Drag and Lift Coefficients (Re ≈ 10,000)

| Shape | Cd_mean | Cd_rms* | Cl_rms* | Notes |
|-------|---------|---------|---------|-------|
| **Circular cylinder** | 1.0–1.2 | 0.05–0.15 | 0.4–0.8 | Smooth, well-shedding; strong periodic wake |
| **Square cylinder** | 2.0–2.2 | 0.1–0.3 | 0.6–1.2 | Sharp corners → flow separation; higher unsteadiness |
| **Half-cylinder** | 1.3–1.6 | 0.08–0.2 | 0.3–0.7 | Intermediate; flat face dominates stagnation |
| **Equilateral triangle** | 1.6–2.0 | 0.12–0.25 | 0.5–0.9 | Depends on orientation (apex up vs. apex down); comparable to square if apex down |

*Cd_rms and Cl_rms are estimates based on spectral energy; provide updated values post-run.

**Source:** [Drag coefficient cylinder Re 10000](https://www.researchgate.net/figure/Drag-coefficient-of-circular-cylinder-depending-on-Re_tbl1_269103956), [Shape optimization review](https://arxiv.org/pdf/1610.08307), [Triangular cylinder data](https://www.sciencedirect.com/science/article/abs/pii/S095559861730170X)

---

### 2. Strouhal Number (Vortex Shedding Frequency)

| Shape | Strouhal (St) | f_shedding (Hz)* | Remarks |
|-------|---------------|-----------------|---------|
| **Circular** | 0.21 (constant, Re > 1000) | 0.21 | Standard reference; universal |
| **Square** | 0.12–0.14 | 0.12–0.14 | Reduced by flow separation topology; sharper wake |
| **Half-cylinder** | 0.15–0.18 | 0.15–0.18 | Intermediate; less organized shedding than circle |
| **Equilateral triangle** | 0.22 | 0.22 | Slightly higher than cylinder; sharp corners enhance shedding |

*Assuming D = 0.5 m and U_in = 1 m/s, so f_shedding = St × U_in / D.

**Source:** [Strouhal number overview](https://www.sciencedirect.com/topics/engineering/strouhal-number), [Triangular cylinder PIV/LES](https://www.sciencedirect.com/science/article/abs/pii/S095559861730170X)

---

### 3. Pressure Coefficient (Cp) — Definition and Extraction

**Definition:**
$$C_p = \frac{p - p_\infty}{0.5 \rho U_\infty^2}$$

Where:
- $p$ = local pressure on the surface
- $p_\infty$ = freestream static pressure
- $\rho U_\infty^2 = 0.5 \times 1.225 \text{ kg/m}^3 \times (1 \text{ m/s})^2 = 0.6125 \text{ Pa}$

**Extraction in Code_Saturne:**
1. Use the postprocessing mesh to define boundary cell face centers on the cylinder/shape surface.
2. Extract nodal (cell-face averaged) pressure field at each time step.
3. Compute $C_p = (p - p_ref) / (0.5 \rho U^2)$ using freestream reference values from inlet BC.
4. Azimuthal sampling: take $\geq 36$ points around the perimeter (10° intervals), or integrate all boundary face centers.
5. Time-average over last 10–20 vortex-shedding periods for steady Cp distribution.

**Qualitative Cp Distribution:**
- **Stagnation point (front, 0°)**: Cp ≈ +1.0 (flow decelerates to zero).
- **Upper/lower shoulders (~45°)**: Cp ≈ −1.0 to −2.0 (acceleration, pressure drop).
- **Separation region (~90°)**: Cp ≈ −1.5 to −2.5 (low pressure, separated shear layer).
- **Base / rear face (180°)**: Cp_base ≈ −1.0 (cylinder) to −0.3 (square); absolute minimum pressure in the wake recirculation.

**Visualization:** ParaView pseudocolor contour on the surface; red = high Cp (high pressure), blue = low Cp (suction region).

**Source:** [CFD Online Cp definition](https://www.cfd-online.com/Forums/openfoam/92392-pressure-coefficient-cp.html), [CFD post-processing guide](https://www.verus-engineering.com/blog/cfd-cases-4/cfd-post-processing-74)

---

### 4. Velocity-Magnitude Contour Visualization — Best Practice

**Domain masking:**
- Plot velocity magnitude $|\mathbf{u}| = \sqrt{u_x^2 + u_y^2 + u_z^2}$ on the entire 2D slice (y = 0.25 m, mid-extrusion).
- **Mask the obstacle:** set Cd_mag = 0 or make it transparent inside the body boundary.
- **Color range:** 0 to 1.5 × U_in (e.g., 0–1.5 m/s) to show wake deficit and recirculation.
- **Palette:** perceptually uniform (viridis, inferno, or plasma); avoid jet (non-linear perception).

**Time-averaged vs. instantaneous:**
- **Instantaneous** (every 5–10 time steps): captures vortex cores, shear-layer oscillations, shed vortices.
- **Time-averaged** (last 10–20 shedding periods): shows mean wake width, base recirculation bubble, re-acceleration downstream.

**Contour resolution:** ≥ 100 contour levels to resolve small velocity gradients in shear layers.

**Comparison layout:** 2×2 grid of subplots (one per shape), same contour range and color scale for inter-shape comparison.

**Source:** [Flow visualization techniques](https://cfdflowengineering.com/flow-visualization-techniques-in-experiment-and-cfd/), [Bluff body wake visualization](https://www.resolvedanalytics.com/cfd-in-practice/how-to-visualize-cfd-simulation-result)

---

### 5. Bluff-Body Shape Optimisation — Key Objectives

Drag reduction is the primary goal in industrial applications. Recent CFD studies [Shape optimization review](https://arxiv.org/pdf/1610.08307) achieve **40–70% drag reduction** via passive trailing-edge flaps or active Coanda actuators on D-shaped bodies. For rigid shapes without passive devices:

- **Goal 1: Suppress vortex shedding** → reduce lift fluctuations (important for civil structures, FSI avoidance).
- **Goal 2: Minimize base pressure deficit** → higher Cp_base (less negative) reduces Cd.
- **Goal 3: Widen separation region moderately** → can paradoxically reduce drag if recirculation becomes stable.

*For this study (shape comparison, not optimisation):* the results (Cd, St, Cp) directly inform which shape is preferable for downstream applications (e.g., footbridges prefer low Cd and low St to avoid resonance; bluff-body heat exchangers tolerate high Cd if shedding is strong for mixing).

**Source:** [Drag optimization review](https://www.researchgate.net/publication/316363194_DRAG_OPTIMIZATION_OF_BLUFF_BODIES_USING_CFD_FOR_AERODYNAMIC_APPLICATIONS), [D-shaped passive control](https://arxiv.org/pdf/1610.08307)

---

## Post-Processing Recipe (Mandatory for Downstream Agents)

### Phase 1: Extract Integral Quantities

**1.1 Force Coefficients over time:**

Output file: `force_coefficients.csv` (one row per time step, columns: `t`, `Cd`, `Cl`, `Cm` if applicable).

```
Cd = F_drag / (0.5 * ρ * U_in^2 * A_ref)
Cl = F_lift / (0.5 * ρ * U_in^2 * A_ref)
```

Where:
- F_drag = force in flow direction (X)
- F_lift = force in cross-flow direction (Z)
- A_ref = D × L = 0.5 m × 0.5 m = 0.25 m² (reference area: diameter × extrusion length)
- ρ = 1.225 kg/m³
- U_in = 1 m/s

**Method:** Use Code_Saturne `cs_user_extra_operations.c` to integrate pressure + shear stress on the body surface at each time step and dump to CSV.

**1.2 Compute statistics (last 10–20 shedding periods, after transients decay):**

- **Cd_mean** = $\overline{C_d}$ (time-averaged drag)
- **Cd_std** = $\sqrt{\overline{(C_d - \overline{C_d})^2}}$ (drag fluctuation std dev)
- **Cl_rms** = $\sqrt{\overline{C_l^2}}$ (RMS lift)
- **Cl_amp** = (Cl_max − Cl_min) / 2 (peak-to-peak lift amplitude)
- **Cl_mean** = $\overline{C_l}$ (should be ≈ 0 for symmetric shapes)

**1.3 Strouhal number via FFT:**

```
Apply FFT to Cl(t) over steady-state interval.
St = f_shedding * D / U_in
where f_shedding = peak frequency from power spectral density (PSD).
```

Output: `strouhal_spectrum.csv` (columns: `frequency [Hz]`, `PSD_magnitude`), and annotate the dominant peak.

**1.4 Base pressure coefficient:**

Integrate Cp over a small arc (±10°) at the rear face (θ ≈ 180°), time-average over steady-state shedding periods.

Output: `Cp_base_mean = <Cp_rear>`.

---

### Phase 2: Visualization

**2.1 Time-series plots (mandatory):**

Four subplots (one per shape), each showing:
- **Left y-axis:** Cd(t) (line), time range: t_start (after transients) to t_end.
- **Right y-axis:** Cl(t) (line, different color), same time range.
- **Legend:** Cd, Cl, Cd_mean (horizontal dashed line), Cl_rms (shaded band ±Cl_rms around Cl=0).

**Caption example:** *Cylinder: Cd_mean = 1.12, Cl_rms = 0.65, St = 0.210.*

**2.2 Power spectral density (PSD) of Cl (mandatory):**

Four subplots, log-log or lin-log frequency axis.
- **X-axis:** frequency [Hz] or normalized Strouhal St = f×D/U_in.
- **Y-axis:** PSD amplitude (V²/Hz).
- **Annotations:** mark dominant peak frequency and corresponding St value.

**2.3 Pressure coefficient (Cp) distribution on surface (mandatory):**

Azimuthal plot: 
- **X-axis:** angle θ [degrees, 0°=front, 90°=top, 180°=rear].
- **Y-axis:** Cp (note: plotted as Cp, not −Cp; lower y = more negative = lower pressure).
- **Four curves:** one per shape (circle, square, half-cyl, triangle).
- **Horizontal dashed line at Cp=0** for reference.
- **Annotations:** Cp_stag ≈ +1, Cp_sep ≈ −2, Cp_base value at θ=180°.

**2.4 Velocity-magnitude contour (mandatory):**

2×2 subplot grid:
- Each panel: velocity magnitude on y=0.25 m slice, xrange = [0, 10] m, zrange = [−2.5, 2.5] m (focus on near and mid-wake).
- **Contours:** 0–1.5 m/s, 100+ levels, perceptually uniform colormap (viridis).
- **Obstacle masked** (velocity set to zero inside or made transparent).
- **All four shapes use same contour range and scale** for direct comparison.
- **Option:** overlay streamlines or vorticity magnitude as iso-contours to highlight vortex cores.

**Caption:** *Time-averaged velocity magnitude; same contour range [0–1.5 m/s] for all shapes.*

**2.5 Wake velocity profiles (optional but recommended):**

Extract $u_x(z)$ and $u_z(z)$ (streamwise and cross-flow velocity) at two downstream stations: x = 8 m and x = 13 m, along line z ∈ [−2.5, +2.5] m at y = 0.25 m.

- Four rows (one per shape).
- Each row: two subplots (station x=8 and x=13).
- **Left subplot:** u_x(z) (streamwise velocity profile, should recover toward U_in = 1 m/s far downstream).
- **Right subplot:** u_z(z) (cross-flow velocity, should decay toward 0 far from centerline).

**Caption:** *Wake velocity profiles at x=8 m (near wake) and x=13 m (mid-wake); lines show shape differences in recovery rate.*

---

### Phase 3: Assembly of Comparison Figure

**Main figure:** 3 rows × 4 columns (3 rows: Cd(t)/Cl(t), PSD, Cp; 4 columns: shapes).

OR (preferred):

**Four-panel layout** (one per shape):
- **Panel A (Cylinder):** Cd(t), Cl(t), PSD (inset), Cp (inset), statistics table.
- **Panel B (Square):** Ditto.
- **Panel C (Half-cyl):** Ditto.
- **Panel D (Triangle):** Ditto.

Common statistics table:
```
| Shape | Cd_mean | Cl_rms | St | Cp_base | Notes |
|-------|---------|--------|----|---------| ------|
| ...   |  ...    |  ...   | ...| ...     | ...   |
```

---

### Phase 4: Checklist for Teammate 3 (CFD Runner) & Teammate 4 (Report Writer)

**T3 must deliver:**
- [ ] Four CSV files (force_coefficients.csv, strouhal_spectrum.csv, Cp_profile.csv, wake_velocity_profiles.csv)
- [ ] Raw RESU folders with complete field outputs (velocity, pressure, every shape, last 10 shedding periods saved).
- [ ] Summary statistics table (Cd_mean, Cl_rms, St, Cp_base for each shape).

**T4 must deliver:**
- [ ] Cd(t) + Cl(t) time-series plot (4 panels).
- [ ] PSD of Cl with Strouhal annotation (4 panels).
- [ ] Cp(θ) azimuthal distribution (4 curves on one plot).
- [ ] Velocity-magnitude contours (2×2 grid with same scale).
- [ ] Wake profiles at x=8, 13 m (optional, 4 rows × 2 columns).
- [ ] Summary statistics table embedded in figure or caption.

---

## Open Questions & Risks

1. **Reynolds number confirmation:** Setup specifies D = 0.5 m, U_in ≈ 1 m/s, ν ≈ 1.5×10⁻⁵ m²/s (air at 20°C), giving Re ≈ 33,000. If this is higher than assumed 10,000, Strouhal values and separation topology may shift. **Action:** Confirm Re_D at run start.

2. **Mesh convergence:** Cd and St are sensitive to boundary-layer mesh resolution (y+, first cell height). Code_Saturne k-ω SST wall-function approach (type 3) assumes y+ > 1; ensure mesh meets this for all four shapes. **Action:** T2 (mesh design) must verify y+ distribution.

3. **Transient decay:** Time to steady-state shedding varies with shape. Circular cylinders stabilize quickly (≈ 50 periods); squares may take ≥ 100 periods. Ensure RESU covers sufficient time to average over ≥ 10 periods. **Action:** Set time-step count conservatively (e.g., 2000 steps × 0.1 s = 200 s = ~33 cycles at St=0.21).

4. **Time-averaging interval:** Published Cd/St values assume fully developed periodic flow. If transients are not well-decayed, reported statistics will bias high (unsteadiness inflates Cd_std). **Action:** T4 must visually confirm Cd(t) plateau before computing statistics.

5. **Cp extraction method:** If body geometry is non-smooth (e.g., sharp corners on square), Cp may spike locally. Azimuthal averaging or face-area weighting helps; document the method. **Action:** T3 must describe Cp integration procedure clearly.

6. **Orientation ambiguity (triangle):** Equilateral triangle with apex up vs. apex down gives Cd ≈ 1.6 vs. 2.0. Clarify orientation in setup.xml and report it prominently. **Action:** Specify in case initialization.

---

## Source Inventory

| # | Source | Type | Date | Trust | Notes |
|---|--------|------|------|-------|-------|
| 1 | [Drag coeff cylinder Re 10k](https://www.researchgate.net/figure/Drag-coefficient-of-circular-cylinder-depending-on-Re_tbl1_269103956) | ResearchGate | 2016+ | med | Tabulated Cd vs Re; specific values for Re=10k. |
| 2 | [DNS flow past cylinder Re 10k](https://www.math.purdue.edu/~sdong/PDF/DNS10k_JFS05.pdf) | arXiv/Purdue | 2005 | high | Direct numerical simulation; authoritative for Re=10k. |
| 3 | [Strouhal number ScienceDirect](https://www.sciencedirect.com/topics/engineering/strouhal-number) | ScienceDirect | 2020+ | high | Comprehensive overview; St values for cylinder, square, triangle. |
| 4 | [Triangular cylinder PIV/LES](https://www.sciencedirect.com/science/article/abs/pii/S095559861730170X) | ScienceDirect | 2017 | high | Experimental + LES; Cd, St, flow structure for triangular prism. |
| 5 | [Cp definition & extraction](https://www.cfd-online.com/Forums/openfoam/92392-pressure-coefficient-cp.html) | CFD-Online | 2012+ | high | Community discussion; practical extraction methods. |
| 6 | [CFD post-processing guide](https://www.verus-engineering.com/blog/cfd-cases-4/cfd-post-processing-74) | Verus Engineering | 2020+ | med | Practical visualization and Cp colormapping. |
| 7 | [Flow visualization techniques](https://cfdflowengineering.com/flow-visualization-techniques-in-experiment-and-cfd/) | CFD Flow Eng. | 2020+ | med | Contour plots, streamlines, best practices for bluff body. |
| 8 | [D-shaped drag optimization](https://arxiv.org/pdf/1610.08307) | arXiv | 2016 | high | Active/passive drag reduction; 40–70% improvements achievable. |
| 9 | [Bluff body base pressure](https://arxiv.org/pdf/2007.09666) | arXiv | 2020 | high | Estimation methods for base pressure coefficient. |
| 10 | [Square cylinder drag reduction](https://www.sciencedirect.com/science/article/pii/S2215098615000786) | ScienceDirect | 2015 | high | Numerical analysis; comparative Cd for square vs. optimized variants. |

---

## Recommended Next Actions

1. **T2 (Mesh Designer):** Verify mesh y+ < 2 (wall-function region) for all four shapes; provide mesh statistics (cell counts, aspect ratios in BL).
2. **T3 (CFD Runner):** Execute four cases (2000 steps, dt=0.1 s each); verify Cd plateau and extract force/pressure CSVs every time step; save RESU for last 10 shedding periods.
3. **T4 (Report Writer):** Generate Cd(t), Cl(t), PSD, Cp(θ), and velocity contours per recipe above; produce one unified comparison figure with statistics table.
4. **T5 (Code Reviewer):** Audit user source modifications (cs_user_extra_operations.c) for force integration correctness; validate Strouhal FFT logic.

---

**Prepared for:** Teammates 2–5 (Mesh Design, CFD Run, Report Writing, Code Review)  
**Data snapshot:** 2026-05-20  
**Briefing version:** 1.0  
