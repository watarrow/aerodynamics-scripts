# WatArrow Aerodynamics Scripts

Python scripts used by the WatArrow aerodynamics subteam for airfoil selection, wing/tail sizing, and stability analysis.

---

## 1. Clone the repository

You need [Git](https://git-scm.com/downloads) installed.

Then create a folder where you want the scripts, open the terminal there and type these commands:

```bash
git clone https://github.com/watarrow/aerodynamics-scripts.git
cd aerodynamics-scripts
```

To pull the latest versions later:

```bash
git pull
```

---

## 2. Set up a virtual environment with the OpenVSP Python API

### 2.1 Download OpenVSP & Python

1. Download OpenVSP (Python 3.13 version) from <https://openvsp.org/download.php> and unzip it somewhere permanent.
2. Install Python version 3.13 (64-bit) from <https://www.python.org/downloads/> if you don't already have it.

### 2.2 Create and activate the venv

Run these from inside the `aerodynamics-scripts` folder.

**Windows (PowerShell):**

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activate script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again.

Once it's active, your prompt will start with `(.venv)`.

### 2.3 Install the OpenVSP API into the venv

With the venv active, `cd` into OpenVSP's `python` folder and install its packages:

```bash
cd "C:\OpenVSP-3.xx.x-win64\python"    # your path
pip install -r requirements.txt
cd <back to aerodynamics-scripts>
```

### 2.4 Install the other dependencies

```bash
pip install numpy scipy pandas matplotlib plotly pyvista dash dash-bootstrap-components neuralfoil aerosandbox requests
```

### 2.5 Verify

```bash
python -c "import openvsp as vsp; vsp.VSPCheckSetup(); print(vsp.GetVSPVersion())"
```

If this prints a version string, you're set up. An `ImportError` or `DLL load failed` almost always means the venv's Python version doesn't match the one OpenVSP was built for.

---

## 3. Before running anything

Create an `Airfoils/` folder in the repo root where you can store your airfoil files (`Airfoils/goe322.dat`, `Airfoils/mh61.dat`, etc). Selig-format `.dat` files are available from the [UIUC Airfoil Database](https://m-selig.ae.illinois.edu/ads/coord_database.html).

### Default workflow

```
constraint_analysis.py        →  pick wing loading (W/S) and T/W
airfoil_analyzer.py           →  pick an airfoil for the wing
vsp_design_space_explore.py   →  learn the design space, tighten bounds
vsp_optimization.py           →  optimize the wing size
tail_sizer.py                 →  size the tail
vsp_single_design_*.py        →  full aero/stability analysis of one design
3dof_*.py, dynamic_modes.py   →  dynamic stability checks
```

---

## 4. Scripts

### `constraint_analysis.py`
Draws a T/W vs. W/S constraint diagram from cruise, takeoff and landing requirements, and shades the feasible region.

- **Edit:** `V_cruise`, takeoff and landing ground roll (`s_to`, `s_land`), `C_Lmax`, `C_D0`, `AR`, `e`.
- **Output:** an interactive matplotlib plot.

### `airfoil_analyzer.py` + `airfoils.json`
A local Dash web app for comparing airfoils. It filters the airfoils in `airfoils.json` by thickness and camber or by name, computes polars with NeuralFoil at your Reynolds number, and plots Cl/Cd/Cm polars, a Cl_max vs. (L/D)_max Pareto front, and the airfoil profiles.

- **Run:** `python airfoil_analyzer.py`, then open the URL it prints (usually <http://127.0.0.1:8050>).
- **Output:** results stay in the browser. Nothing is written to disk.
- `airfoils.json` is the airfoil database, with max thickness % and max camber % for each airfoil. Keep it in the repo root.

### `vsp_design_space_explore.py`
Run this before `vsp_optimization.py`. It imports the bounds, constraints and helper functions from `vsp_optimization.py`, so the two files must stay in the same folder and in sync. It does three things:

- samples the design space with a scrambled Sobol sequence (`N_SAMPLES = 256` by default)
- runs one-at-a-time sweeps of each variable
- reports which constraints are active, suggests tighter bounds from the feasible samples, and flags variables that barely affect drag so you can freeze them

- **Edit:** `N_SAMPLES`, `OAT_NPTS` and the tolerances at the top. The design variables and bounds themselves come from `vsp_optimization.py`.
- **Output:** `dse_samples.csv`, `dse_oat.csv`, and matplotlib plots.

### `vsp_optimization.py`
Optimizes a wing with SciPy differential evolution. Each candidate wing is built in OpenVSP and analyzed with VSPAERO. The objective is cruise drag, plus penalties for not carrying the aircraft's weight, not trimming at the target static margin, insufficient pitch stability (Cm_α), and violating aspect-ratio or tip-chord limits. Parasitic drag comes from a skin-friction and form-factor model, and weight is estimated from span and planform area.

- **Edit:**
  - `VELOCITY` (cruise speed) and `AIRFOIL_FILE`
  - `BOUNDS` for the 7 design variables: root chord, taper, LE sweep, washout, span, dihedral, alpha
  - the weight model (`M_FIXED`, `M_SPAR_PER_M`, `M_SKIN_PER_M2`)
  - constraint targets (`STATIC_MARGIN`, `CMA_MAX`, `AR_MIN`/`AR_MAX`, `TIP_CHORD_MIN`)
  - `popsize` and `maxiter` in `main()`
- **Output:**
  - every evaluation is logged to `optimization_results.csv`
  - the best feasible design is printed and shown in a 3D PyVista window
- **Tips:** Runs can take hours. `Ctrl+C` stops the run cleanly and still reports the best feasible design logged so far.

### `tail_sizer.py`
Sizes the horizontal and vertical tails for a conventional layout using tail volume coefficients (`V_H`, `V_V`). For every combination of wing config × tail moment arm × horizontal-tail aspect ratio, it places the CG at the target static margin (`SM`), then adjusts the tail incidence with a secant search in VSPAERO until the pitching moment is trimmed.

- **Edit:**
  - `wing_configs` (one dict per candidate wing)
  - `tail_moment_arms`, `htail_aspect_ratios`
  - `htail_params`, `vtail_params`
  - `velocity`, `alpha`, `SM`, `airfoil_file`
- **Output:** `tail_sizing_options.csv`, one row per combination with tail span/chord, vertical-tail height, incidence, and whether it converged. Rows are written as they finish, so a crash keeps completed results.

### `vsp_single_design_conventional.py`
Builds one conventional wing + H-tail + V-tail aircraft and analyzes it in full. It runs a VSPAERO alpha sweep (−5° to 14°) at each velocity (10–45 m/s), then a stability analysis at `stability_velocity`. It also fits an Oswald efficiency from each polar and grades each stability derivative against `stability_targets`.

- **Edit:**
  - `wing_params`, `htail_params`, `vtail_params`
  - `x_cg`, `airfoil_file`, `stability_velocity`
  - `velocities`, `alphas`, `stability_targets`
- **Output:**
  - `aero_full.csv`: CL, CD, Cm, lift, drag and Oswald efficiency at each velocity and alpha
  - `stability.csv`: stability derivatives
  - an interactive Plotly dashboard that opens in your browser

### `vsp_single_design_delta.py`
The same full analysis as the conventional script, for a tailless swept/delta flying wing. The MAC is computed from root chord and taper.

- **Edit:** `wing_params` (root chord, taper, sweep, washout, span, dihedral, alpha), plus `x_cg`, `airfoil_file`, `stability_velocity`, `velocities`, `alphas`.
- **Output:** `aero_full.csv`, `stability.csv`, and a browser dashboard.

> Each run of either single-design script deletes and overwrites `aero_full.csv` and `stability.csv` in the repo root. To keep a run, rename the files or move them into `databases/` for the stability scripts.

### Stability (no OpenVSP needed)

All three read the CSVs produced by a single-design script. Put them in `databases/` first.

#### `3dof_longitudinal_stability.py`
Finds an approximate trim point (velocity and alpha where lift ≈ weight and Cm ≈ 0) from `databases/aero_full.csv`. It then applies a pitch disturbance (+3° alpha, 5°/s pitch rate) and integrates the nonlinear 3-DOF longitudinal equations.

- **Edit:** `mass`, `I_y`, `S_wing`, `c_bar`, and the initial disturbance.
- **Input:** `databases/aero_full.csv`, `databases/stability.csv` (for `Cm_q`).
- **Output:** time histories of V, α, q and θ.

#### `3dof_lateral_stability.py`
Simulates the lateral-directional response (sideslip, roll rate, yaw rate, bank, heading) to a 5° sideslip and 10°/s roll-rate disturbance at `V_trim`. It interpolates the derivatives by velocity from `databases/stability.csv`.

- **Edit:** `mass`, `I_x`, `I_z`, `I_xz`, `S_wing`, `b_span`, `V_trim`, and the initial disturbance.
- **Output:** response plots.

#### `dynamic_modes.py`
Builds the linearized longitudinal and lateral state-space matrices and computes their eigenvalues. It plots them alongside the classic approximations: short period, phugoid, Dutch roll, roll and spiral. Lateral derivatives and `Cm_q` come from `databases/stability.csv`. The other longitudinal coefficients are hard-coded near the top of the file.

- **Edit:** mass and inertias, reference geometry, `Vtrim`, `alpha_trim_deg`, and the hard-coded `CL0`, `CD0`, `CLa`, `CMa`, `CLq` etc. Update these from your `aero_full.csv`.
- **Output:** eigenvalues printed to the terminal and a root-locus style plot. Left half-plane means stable.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'openvsp'` | The venv isn't active |
| `ImportError: DLL load failed` / `_vsp` import errors | The venv's Python version doesn't match the OpenVSP build. Recreate the venv with the right version. |
| Airfoil file not found | Create `Airfoils/` and add the `.dat` file |
| `FileNotFoundError: databases/...csv` | Run a single-design script and move `aero_full.csv` and `stability.csv` into `databases/`. |
| VSPAERO very slow | Lower `NCPU`, or lower `WING_SPAN_RES` / `WING_CHORD_RES`. |
