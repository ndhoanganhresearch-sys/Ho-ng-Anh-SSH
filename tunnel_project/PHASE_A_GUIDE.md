# Phase A: Create T0 Clean Reference
## Step-by-step guide to raycast the clean tunnel baseline

**Timeline:** ~30 minutes (15 min Blender setup + 15 min raycast)

**Output:** `T0.las` (364 points, clean reference, ~0mm deformation)

---

## Prerequisites

- Blender MCP connected ✓
- Python venv ready (`..\.venv\Scripts\python.exe`)
- Input: `data/blender_lidar_t0t5/tunnel_lidar_scene.blend`
- Output dir: `data/blender_lidar_t0t5/`

---

## Step 1: Blender Setup (5 min)

### 1a. Open tunnel scene
```
File: tunnel_project/data/blender_lidar_t0t5/tunnel_lidar_scene.blend
Expected:
├─ Tunnel_Lining (16,100 vertices) - main scanning target
├─ Rail_R, Rail_L (curves)
└─ Sleeper_0..N (floor infrastructure)
```

### 1b. Verify Tunnel_Lining mesh
```
Object: Tunnel_Lining
├─ Type: MESH
├─ Vertices: 16,100
├─ State: Clean (no deformation)
└─ Location: (0, 0, 0)
```

**Action:** In Blender, click on Tunnel_Lining, check properties panel.

---

## Step 2: Python Raycast (25 min)

### 2a. Run raycasting script

```bash
cd tunnel_project
..\.venv\Scripts\python.exe phase_a_raycast.py
```

**Script does:**
1. Opens tunnel_lidar_scene.blend
2. Creates UV sphere @ (0, 10, 3) with 512 rays
3. Raycasts each ray to Tunnel_Lining
4. Gets 364 hit positions
5. Adds distance-dependent noise (5mm + 2mm per 10m)
6. Exports T0.las
7. Saves T0.json metadata

**Expected output:**
```
✓ Raycast complete!
  Rays cast: 482
  Hits: 364 (75.5% coverage)
  Distance range: 1.157m - 45.027m
  Noise applied: 5mm + 2mm per 10m

✓ LAS file created!
  Path: data/blender_lidar_t0t5/T0.las
  Points: 364
  X: -4.230 to 4.920 m
  Y: 0.310 to 55.120 m
  Z: -2.780 to 4.270 m
```

### 2b. Record T0 metadata

After raycast, file saved: `T0.json`
```json
{
  "source": "raycasting_TLSynth_protocol_phase_a",
  "mesh_source": "tunnel_lidar_scene.blend (clean)",
  "scanner_location": [0, 10, 3],
  "scanner_sphere_subdivisions": "32x16",
  "noise_model": "5mm + 2mm per 10m distance",
  "point_count": 364,
  "radius_design": 3.0,
  "deformation_prescribed": "none (reference)",
  "registration_status": "identity (no transformation)",
  "created_date": "2026-06-23",
  "validated": false
}
```

---

## Step 3: Verify T0 (5 min)

### 3a. Load and check LAS

```bash
..\.venv\Scripts\python.exe verify_synthetic_las.py
```

Expected output:
```
Synthetic LAS verification:
  Points: 364
  X range: -4.230 to 4.920 m
  Y range: 0.310 to 55.120 m
  Z range: -2.780 to 4.270 m
  File: data/blender_lidar_t0t5/T0.las

Ready to test with tunnel_analysis tool!
```

### 3b. Quick validation checklist

- [ ] T0.las exists (364 points)
- [ ] X range ~ [-4.2, 4.9] m (tunnel cross-section)
- [ ] Y range ~ [0.3, 55.1] m (tunnel length)
- [ ] Z range ~ [-2.7, 4.2] m (height)
- [ ] T0.json metadata file present
- [ ] File size ~40-50 KB

---

## Step 4: Optional - Load into Tool (optional, 10 min)

### Test in tunnel_analysis app

```bash
..\.venv\Scripts\python.exe run_tunnel_analysis.py
```

In app:
1. Load T0.las
2. Step 1-2: Load & process
3. Step 3: Auto-align (skip if identity registration)
4. Step 4-5: Extract geometry
5. Step 6: Check section view
   - Should see circle with ~3m radius
   - Eccentricity should be near 0
   - Ovality should be < 0.1%

**Record baseline:**
```
T0 baseline metrics:
├─ Radius (fitted): 3.0000 m (design: 3.0 m) ✓
├─ Eccentricity: 0.1 mm (should be ~0) ✓
├─ Ovality: 0.05% (should be minimal) ✓
└─ Section fit: converged, clean ✓
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| **Raycast: 0 hits** | Scanner sphere inside/outside tunnel | Adjust scanner location (0, 10, 3) |
| **Few hits (<300)** | Low sphere subdivisions | Increase to 64x32 (1024 rays) |
| **LAS file missing** | laspy not installed | `pip install laspy` in venv |
| **File can't open in app** | Corrupted LAS format | Re-run raycast, check laspy version |
| **Radius ≠ 3.0m** | Mesh deformation (shouldn't be) | Verify tunnel_lidar_scene.blend is clean |

---

## Next: Phase B

Once T0 is verified:
1. **Phase B:** Inject deformation into mesh
2. Create tunnel_deformed.blend
3. Raycast deformed mesh → Tn.las

See: `PHASE_B_GUIDE.md` (coming next)

---

## Command Summary

```bash
cd tunnel_project

# Run Phase A raycast
..\.venv\Scripts\python.exe phase_a_raycast.py

# Verify output
..\.venv\Scripts\python.exe verify_synthetic_las.py

# Optional: test in app
..\.venv\Scripts\python.exe run_tunnel_analysis.py
```

---

**Expected time:** 30 min ⏱️  
**Output:** T0.las + T0.json (clean reference)  
**Status:** ✓ Phase A ready to execute
