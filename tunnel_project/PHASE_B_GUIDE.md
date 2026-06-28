# Phase B: Inject Deformation & Raycast Tn

## Step-by-step guide to create a deformed monitoring epoch from the clean T0 reference

**Timeline:** ~45 minutes (15 min deform mesh + 15 min raycast + 15 min verify)

**Output:** `Tn.las` (same scanner setup as T0, with known deformation injected)

**Prereq:** Phase A complete — `T0.las` + `T0.json` exist and verified.

---

## Why Phase B matters

T0 is a clean reference. To validate the tool we need a **second epoch with deformation we already know the answer to**. Phase B injects a prescribed deformation into the mesh, then raycasts it with the **exact same scanner setup as Phase A**. Because only the mesh changed, every measured difference between T0 and Tn is caused by deformation alone — that is our ground truth.

```
T0.las  =  raycast( clean mesh,     scanner @ (0,10,3), noise N )
Tn.las  =  raycast( deformed mesh,  scanner @ (0,10,3), noise N )
          └──────────────┬──────────────┘
        only the mesh differs → all measured Δ is deformation
```

---

## Prerequisites

- Phase A done: `T0.las`, `T0.json` present and verified
- Blender + Python venv ready (`..\.venv\Scripts\python.exe`)
- Input: `data/blender_lidar_t0t5/tunnel_lidar_scene.blend` (clean)
- Reference: `phase_a_raycast.py` (scanner/noise config must be reused verbatim)
- Ground truth target: `data/blender_lidar_t0t5/ground_truth.csv`

---

## Step 1: Define the deformation prescription (5 min)

Pick what to inject. Keep it identical to `ground_truth.csv` so the answer key matches the dataset. Current dataset prescription:

| Deformation | Chainage (Y) | T5 magnitude | Extent | Shape |
| --- | ---: | ---: | --- | --- |
| Crown settlement | 20 m | -45 mm (Z down) | ±2 m | Gaussian taper |
| Sidewall convergence | 45 m | -35 mm (X inward) | ±3 m | Gaussian taper, both sides |
| Local damage | 65 m | -40 mm | ±1 m | sharp local dip (from T3 onward) |

> For a single T0→Tn pair, start with **one** deformation (e.g. crown -7 mm @ 20 m) so you can isolate one measurement pipeline. Add the others once that passes (Scenario B → C in the protocol).

Record the exact prescription you use — you will compare against it in Phase C / validation.

---

## Step 2: Deform the mesh (15 min)

Deformation is applied to `Tunnel_Lining` vertices in Blender via `bmesh`. The scanner and noise config are **left untouched** — they come straight from `phase_a_raycast.py`.

### 2a. Deformation logic (bmesh)

```python
import bpy, bmesh
from math import exp

CHAINAGE_AXIS = "y"          # tunnel runs along Y
TUNNEL_RADIUS = 3.0          # meters (design radius)

def gaussian_taper(d, sigma):
    """1.0 at the peak, smoothly decaying to the edges of the extent."""
    return exp(-(d * d) / (2.0 * sigma * sigma))

def deform_vertex(co):
    y = co.y

    # Crown settlement @ Y=20m, peak -7mm, extent ±2m
    if 18.0 < y < 22.0:
        offset = -0.007 * gaussian_taper(y - 20.0, sigma=0.8)
        co.z += offset                       # crown drops

    # Sidewall convergence @ Y=45m, peak -5mm each side, extent ±3m
    if 42.0 < y < 48.0:
        factor = -0.005 * gaussian_taper(y - 45.0, sigma=1.2)
        co.x *= (1.0 + factor / TUNNEL_RADIUS)   # walls move inward

    # Local damage @ Y=65m, peak -15mm, extent ±1m (sharp)
    if 64.0 < y < 66.0:
        offset = -0.015 * gaussian_taper(y - 65.0, sigma=0.3)
        co.z += offset

    return co

bpy.ops.wm.open_mainfile(
    filepath=r"data\blender_lidar_t0t5\tunnel_lidar_scene.blend")

tunnel = bpy.data.objects["Tunnel_Lining"]
bm = bmesh.new()
bm.from_mesh(tunnel.data)
for v in bm.verts:
    v.co = deform_vertex(v.co)
bm.to_mesh(tunnel.data)
bm.free()
tunnel.data.update()

bpy.ops.wm.save_as_mainfile(
    filepath=r"data\blender_lidar_t0t5\tunnel_deformed_Tn.blend")
```

### 2b. Validate the deformed mesh

- [ ] Crown height @ 20 m decreased ≈ 7 mm
- [ ] Width @ 45 m decreased ≈ 5 mm each side
- [ ] Mesh still manifold (no holes / non-manifold edges)
- [ ] Deformation subtle (mm-level), not visually obvious — that's correct
- [ ] Vertex count unchanged (16,100) — we move vertices, never add/delete

---

## Step 3: Raycast the deformed mesh (15 min)

Reuse the **exact** scanner block from `phase_a_raycast.py` — only the input `.blend` changes. Critical: do **not** re-roll new scanner subdivisions or noise constants, or the difference will contain non-deformation noise.

```python
# Must match phase_a_raycast.py byte-for-byte:
SCANNER_LOCATION   = Vector([0, 10, 3])
SCANNER_RADIUS     = 0.1
SPHERE_SUBDIVISIONS = (32, 16)
NOISE_BASE_MM      = 5
NOISE_SLOPE        = 2

BLENDER_FILE = r"data\blender_lidar_t0t5\tunnel_deformed_Tn.blend"   # <-- only change
OUTPUT_NAME  = "Tn"
```

Then run the identical pipeline: open scene → add scanner UV sphere → BVHTree raycast each vertex → distance-dependent Gaussian noise → export `Tn.las` + `Tn.json`.

The cleanest path is to copy `phase_a_raycast.py` to `phase_b_raycast.py`, change only the four lines above, and run:

```powershell
cd "C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project"
..\.venv\Scripts\python.exe phase_b_raycast.py
```

**Expected output:**
```
✓ Raycast complete!
  Rays cast: 482
  Hits: ~364 (within ±5% of T0)
  Distance range: ~1.1m - ~45m
  Noise applied: 5mm + 2mm per 10m

✓ LAS file created!
  Path: data/blender_lidar_t0t5/Tn.las
  Points: ~364
```

### 3a. Write the Tn metadata

`Tn.json` records the **prescribed** deformation so validation has the answer key:

```json
{
  "source": "raycasting_TLSynth_protocol_phase_b",
  "mesh_source": "tunnel_deformed_Tn.blend",
  "scanner_location": [0, 10, 3],
  "scanner_sphere_subdivisions": "32x16",
  "noise_model": "5mm + 2mm per 10m distance",
  "deformation_prescribed": {
    "crown_settlement_mm": -7.0,
    "convergence_mm": -5.0,
    "local_damage_mm": -15.0,
    "chainage": {"crown": 20, "convergence": 45, "local": 65}
  },
  "ground_truth_file": "ground_truth.csv",
  "registration_status": "identity (same scanner as T0)",
  "validation_status": "pending"
}
```

---

## Step 4: Verify Tn against T0 (10 min)

### 4a. Sanity check the LAS

```powershell
..\.venv\Scripts\python.exe verify_synthetic_las.py
```

- [ ] `Tn.las` exists, point count within ±5% of T0
- [ ] Y range matches T0 (tunnel length unchanged)
- [ ] X/Z ranges slightly tighter than T0 near deformed chainages
- [ ] `Tn.json` present with `deformation_prescribed` block

### 4b. Quick deformation cross-check (optional)

Load both into the tool and run Step 6 (`6.2 M3C2 deformation map T0→Tn`). Expect signal concentrated at the prescribed chainages, near-zero elsewhere:

```
Near chainage 20m  → crown settlement ≈ -7mm   (GT: -7mm)
Near chainage 45m  → convergence      ≈ -5mm   (GT: -5mm)
Near chainage 65m  → local damage     ≈ -15mm  (GT: -15mm)
Elsewhere          → ≈ 0mm (noise floor only)
```

Formal error calculation vs ground truth is **Phase C** (validation).

---

## Troubleshooting

| Issue | Cause | Fix |
| --- | --- | --- |
| **Deformation invisible in tool** | Magnitude too small vs noise floor | Increase to -10mm+ for first test, or lower noise |
| **Deformation everywhere, not localized** | `gaussian_taper` sigma too large | Reduce sigma so taper falls inside the extent |
| **Tn point count very different from T0** | Mesh became non-manifold / scanner moved | Re-check 2b manifold; confirm scanner config matches Phase A |
| **Signal at wrong chainage** | Y/Z axis confusion in `deform_vertex` | Tunnel runs along Y; crown is Z, walls are X |
| **Non-zero deformation far from peaks** | Scanner/noise differs from T0 | Copy scanner + noise block verbatim from `phase_a_raycast.py` |
| **Mesh has holes after deform** | Edited vertex count / deleted verts | Only move `v.co`, never add/remove vertices |

---

## Next: Phase C

Once Tn is verified:
1. **Phase C:** Load T0 + Tn into the tool, measure every metric, compute `error = |measured − ground_truth|`
2. Record in `validation_results.csv` (PASS if error < tolerance: 1mm crown/convergence, 2mm local)
3. Repeat for Scenarios B (single metric), C (combined), D (offset scanner) — see `RAYCASTING_GROUNDTRUTH_PROTOCOL.md` §4

See: `RAYCASTING_GROUNDTRUTH_PROTOCOL.md` §3 (Validate Tool Accuracy)

---

## Command Summary

```powershell
cd "C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project"

# 1. Deform mesh in Blender (Step 2 script) -> tunnel_deformed_Tn.blend
# 2. Raycast deformed mesh (copy of phase_a_raycast.py, 4 lines changed)
..\.venv\Scripts\python.exe phase_b_raycast.py

# 3. Verify output
..\.venv\Scripts\python.exe verify_synthetic_las.py
```

---

**Expected time:** ~45 min ⏱️
**Output:** Tn.las + Tn.json (deformed epoch, scanner identical to T0)
**Status:** Phase B ready to execute — answer key lives in `ground_truth.csv`
