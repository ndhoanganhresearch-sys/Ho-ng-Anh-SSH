# Phase B: Generate a Deformed Epoch (T1–T5)

## Deform the real curved mesh by a known amount, then raycast it

**Output:** `data/blender_lidar_t0t5/<EPOCH>_raycast.txt` (+ `.json`)

**Engine:** `tools/raycast_tunnel_epochs.py` — same script as Phase A, `--epoch Tn`

---

## Why the same engine

Phase A and Phase B use **one** code path and the **same** 3 stations, ray grid,
and noise seed. Only the mesh differs (clean vs deformed). So every measured
difference between T0 and Tn is deformation — by construction, not by careful
copying of config.

---

## Deformation model (matches ground_truth.csv)

The engine deforms `Tunnel_Lining` in the **local cross-section frame** of the
curved alignment, reading per-epoch magnitudes straight from the manifest specs:

| Type | Chainage (arc-len) | σ (along chainage) | θ (cross-section) | T5 peak |
| --- | ---: | ---: | ---: | ---: |
| Crown settlement | 20 m | 3.0 m | 90° (crown) | -45 mm |
| Sidewall convergence | 45 m | 3.0 m | 0°/180° (both walls) | -35 mm |
| Local damage | 65 m | 1.2 m | 55° (patch) | -40 mm |

Per-epoch values (mm), from `ground_truth.csv`:

| Epoch | Crown | Convergence | Local |
| --- | ---: | ---: | ---: |
| T1 | -5 | 0 | 0 |
| T2 | -12 | -5 | 0 |
| T3 | -20 | -12 | -15 |
| T4 | -30 | -22 | -25 |
| T5 | -45 | -35 | -40 |

How each is applied (see `make_deformer()` in the engine):
- **Crown** — move down in Z, angular weight `max(0, sin θ)`, Gaussian in arc-length.
- **Convergence** — move both walls inward laterally, weight `|cos θ|`, Gaussian in s.
- **Local** — radial inward at θ≈55°, narrow Gaussian in s **and** in angle (±15°).

Chainage is **arc length** `s = R·asin(y/R)` on the R=500 m curve, and the
cross-section frame is lateral≈X, up≈Z (valid because the curve is horizontal).

---

## Run it

```powershell
cd "C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project"
blender -b data\blender_lidar_t0t5\tunnel_lidar_scene.blend ^
        -P tools\raycast_tunnel_epochs.py -- --epoch T5
```

(Or via Blender MCP with `EPOCH = "T5"`.) Repeat for T1…T4 as needed.

**Expected:**
```
RAYCAST TUNNEL EPOCH: T5
  deformed verts: ~9,600
  hits: ~112,500
  -> data/blender_lidar_t0t5/T5_raycast.txt
  clean .blend restored
```

---

## Verify the deformation is present

```powershell
..\.venv\Scripts\python.exe -c "import numpy as np; t0=np.loadtxt(r'data\blender_lidar_t0t5\T0_raycast.txt'); t5=np.loadtxt(r'data\blender_lidar_t0t5\T5_raycast.txt'); t0=t0[t0[:,4]==1]; t5=t5[t5[:,4]==1]; import math; s=lambda a:500*np.arcsin(np.clip(a[:,1]/500,-1,1)); cz=lambda a,c:(lambda m: a[m][:,2].mean())((np.abs(s(a)-c)<1)); print('crownZ@20 dZ %.1f mm (GT -45)'%((cz(t5,20)-cz(t0,20))*1000))"
```

- [ ] Crown Z @ 20 m drops by ~40–45 mm (peak window)
- [ ] Point count within ±0.1% of T0
- [ ] `<EPOCH>_raycast.json` has the correct `deformation_prescribed` values

Formal pass/fail is **Phase C**.

---

## Next: Phase C

Validate measured vs ground truth. See `PHASE_C_GUIDE.md`.
