# Phase C: Validate Against Ground Truth

## Measure deformation from the raycast clouds and compare to ground_truth.csv

**Output:** `data/blender_lidar_t0t5/validation_results.csv` + `validation_report.md`

**Script:** `phase_c_validate.py` (runs in the project venv — no Blender, no GUI)

---

## What it does

Reproduces the Step-6 geometric measurement directly on the point clouds, in the
same curved cross-section frame they were generated in, then compares the peak
deformation per zone against the answer key in `ground_truth.csv`.

- **Crown settlement** — change in mean crown-Z in a tight window around (s=20, θ=90°).
- **Sidewall convergence** — change in mean half-width |lateral| around (s=45, θ=0/180°).
- **Local damage** — change in mean radius around (s=65, θ=55°).

Window: ±0.75 m arc-length, ±10° angular around each peak. Tolerance: 8 mm on peak.

---

## Run it

```powershell
cd "C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project"
..\.venv\Scripts\python.exe phase_c_validate.py --epoch T5
```

**Example result (T5):**
```
PHASE C VALIDATION  epoch: T5
  crown_settlement       GT= -45.0  measured= -46.9  err= 1.9  PASS
  sidewall_convergence   GT= -35.0  measured= -32.7  err= 2.3  PASS
  local_damage           GT= -40.0  measured= -34.5  err= 5.5  PASS
MAE 3.2 mm  ->  PASS
```

Outputs:
- `validation_results.csv` — one row per metric (GT, measured, error, status)
- `validation_report.md` — a readable summary table + verdict

---

## Interpreting results

- **Crown / convergence** track GT to ~2 mm — the broad (σ=3 m) features are
  well sampled by the 1° ray grid.
- **Local damage** reads a few mm low: the patch is narrow (σ=1.2 m, ±15°), so
  averaging inside the window dilutes the peak. Tightening the window or raising
  ray density (azimuth/elevation step → 0.5°) recovers more of it.
- All within the 8 mm tolerance → the raycast track and the geometric pipeline
  agree on mm-scale deformation.

---

## Optional: validate in the PyQt tool

The clouds are plain `x y z intensity label` text (label 1 = lining), so the app
loads them directly:

1. `..\.venv\Scripts\python.exe run_tunnel_analysis.py`
2. Load `T0_raycast.txt`, add `T5_raycast.txt` as a second scan.
3. Run Step 6 (`6.2 M3C2 deformation map T0→Tn`); expect signal at chainage
   20/45/65 m, near-zero elsewhere.

This cross-checks the tool's Step 6 against the same ground truth.

---

## Repeat across epochs

```powershell
..\.venv\Scripts\python.exe phase_c_validate.py --epoch T3
..\.venv\Scripts\python.exe phase_c_validate.py --epoch T5
```

(Generate each `Tn_raycast.txt` first via Phase B.) Progressive epochs let you
plot measured-vs-GT across the whole T0→T5 series.
