# Raycasting Ground Truth Protocol
## Applying TLSynth Techniques for Synthetic Tunnel Validation

**Purpose:** Create synthetic ground-truth tunnel point clouds with known deformation using raycasting, to validate tunnel analysis tool accuracy.

**Reference:** TLSynth paper §3.1-3.5 (Scanning Simulation Pipeline)

**Author:** Claude Code + TLSynth methodology

---

## 1. TLSynth Workflow Overview

```
TLSynth Paper (§3)
├─ §3.1 Scanning Simulation
│  ├─ UV sphere vertex normals = ray sources
│  ├─ Geometry Nodes Raycast node = ray casting engine
│  └─ Output: Hit Position = point cloud
├─ §3.2 Noise Model
│  ├─ Distance-dependent: r_noise = noise_mean + noise_std × d
│  └─ Gaussian noise on each point
├─ §3.3 Point Deletion
│  └─ Optional: remove points based on occlusion/coverage
├─ §3.4 Color Assignment
│  └─ Optional: assign RGB from mesh material
└─ §3.5 Export
   └─ Export as PLY/LAZ/LAS format
```

---

## 2. Protocol: Create Ground Truth T0 → Tn Pair

### **Phase A: Prepare Clean Reference (T0)**

#### A.1 Load tunnel mesh
```
Input: tunnel_lidar_scene.blend (or equivalent)
├─ Tunnel_Lining (16100 vertices, smooth surface)
├─ Rails (reference geometry, not scanned)
└─ Sleepers (on-ground objects, optional to include)

Decision: Scan only Tunnel_Lining or include supporting geometry?
→ Recommended: Tunnel_Lining only (focuses on structural deformation)
```

#### A.2 Setup scanner position
```
Scanner location: (X, Y, Z) in world coordinates
Examples:
├─ Station scan: (0, 10, 3) = 10m along tunnel, 3m height
├─ Mobile scan: (1, 15, 3) = offset 1m from centerline
└─ Multi-angle: repeat with different (X, Z) positions

Sphere parameters:
├─ Radius: 0.1m (small, doesn't intersect mesh)
├─ Subdivisions: 32×16 (512 vertices → 512 rays)
└─ Material: white (for reference)
```

#### A.3 Raycast clean tunnel
```python
# Pseudocode (see convert_raycast_to_las.py)
for vertex in scanner_sphere:
    world_pos = scanner_center + vertex_offset
    ray_direction = (world_pos - scanner_center).normalized()
    
    hit_location, hit_distance = raycast(world_pos, ray_direction, tunnel_lining_mesh)
    
    if hit:
        # Add distance-dependent noise (TLSynth §3.2)
        noise_mm = 5 + (hit_distance / 10) * 2
        noisy_point = hit_location + gaussian(0, noise_mm / 1000)
        
        T0_points.append(noisy_point)

T0_points → export T0.las
```

**Output:** `T0.las` (clean reference, ~364-500 points depending on coverage)

**Metrics to record:**
```
T0_metadata:
├─ Point count: N
├─ Radius (fitted): R_0 (should ≈ 3.000m)
├─ Eccentricity: e_0 (should ≈ 0mm)
├─ Ovality: Oval_0 (should ≈ 0%)
└─ Scanner location: (X, Y, Z)
```

---

### **Phase B: Inject Known Deformation**

#### B.1 Define deformation prescription
```
Choose deformation type and magnitude:

Option 1: Crown settlement (common)
├─ Chainage: 20m (along tunnel Y-axis)
├─ Magnitude: -7mm (downward)
├─ Extent: ±2m (affects sections 19-21m)
└─ Shape: Gaussian taper (sharp at 20m, smooth at edges)

Option 2: Sidewall convergence (common)
├─ Chainage: 45m
├─ Magnitude: -5mm (inward)
├─ Extent: ±3m (affects sections 42-48m)
└─ Symmetry: Both sides (left + right)

Option 3: Combined (realistic)
├─ Crown: -7mm @ 20m
├─ Convergence: -5mm @ 45m
├─ Local damage: -15mm @ 65m (point defect)
└─ Span: 3 epochs → T0, T1, T2 progression

Record prescription in: ground_truth.csv
```

#### B.2 Modify tunnel mesh
```
Blender script:
1. Load tunnel_lidar_scene.blend
2. Select Tunnel_Lining mesh
3. Apply deformation via:
   a) Proportional editing (manual)
   b) Displace modifier (parametric)
   c) Python bmesh (automated, recommended)

Example (bmesh):
for vertex in mesh.vertices:
    chainage_y = vertex.co.y
    
    # Crown settlement at Y=20m
    if 18 < chainage_y < 22:
        offset = -0.007 * gaussian_taper(chainage_y - 20)
        vertex.co.z += offset  # -7mm
    
    # Sidewall convergence at Y=45m
    if 42 < chainage_y < 48:
        offset = -0.005 * gaussian_taper(chainage_y - 45)
        vertex.co.x *= (1 + offset / radius)  # -5mm inward
        vertex.co.y *= (1 + offset / radius)

mesh.update()
blender_file.save("tunnel_deformed.blend")
```

**Validate deformation:**
```
After modification:
├─ Crown height @ 20m should decrease ≈ 7mm ✓
├─ Width @ 45m should decrease ≈ 5mm (each side) ✓
├─ Mesh remains manifold (no holes) ✓
└─ Visual inspection: deformation subtle (mm-level) ✓
```

#### B.3 Record ground truth values
```
ground_truth.csv:
chainage,crown_settle_mm,convergence_mm,local_damage_mm,notes
20.0,-7.0,0.0,0.0,Crown settlement peak
45.0,0.0,-5.0,0.0,Sidewall convergence peak
65.0,0.0,0.0,-15.0,Localized defect

Also save:
T0_radius: 3.0000m
T1_radius: 2.9950m (slight decrease due to convergence)
T1_eccentricity: 1.5mm (increased due to asymmetric deformation)
```

---

### **Phase C: Raycast Deformed Tunnel**

#### C.1 Raycast with identical scanner setup
```python
# IMPORTANT: Use SAME scanner position as T0
scanner_location = (0, 10, 3)  # Must match T0
scanner_sphere = UV_Sphere(radius=0.1, location=scanner_location)

# Load deformed mesh
tunnel_deformed_mesh = load("tunnel_deformed.blend").Tunnel_Lining

# Raycast (identical process to A.3)
for vertex in scanner_sphere:
    world_pos = scanner_center + vertex_offset
    ray_direction = (world_pos - scanner_center).normalized()
    
    hit_location, hit_distance = raycast(world_pos, ray_direction, tunnel_deformed_mesh)
    
    if hit:
        # Same noise model as T0 (TLSynth §3.2)
        noise_mm = 5 + (hit_distance / 10) * 2
        noisy_point = hit_location + gaussian(0, noise_mm / 1000)
        
        Tn_points.append(noisy_point)

Tn_points → export Tn.las
```

**Critical requirements:**
```
✓ Scanner position identical to T0
✓ Noise parameters identical to T0
✓ Ray count identical (same sphere subdivision)
✓ Only difference: target mesh (T0 clean vs Tn deformed)
→ All measurement differences are due to deformation only
```

#### C.2 Validate point cloud
```
Tn_metadata:
├─ Point count: should ≈ T0 count (within ±5%)
├─ Radius (fitted): R_n (should ≈ 2.99m, slightly less)
├─ Eccentricity: e_n (should increase ≈ 1-2mm)
├─ Ovality: Oval_n (should increase ≈ 0.05%)
└─ Distance distribution: similar to T0 (same scanner position)
```

**Output:** `Tn.las` (deformed reference, same point count as T0)

---

## 3. Protocol: Validate Tool Accuracy

### **Step 1: Load into tunnel_analysis tool**
```
1. Launch app
2. Step 1: Load T0.las → analyze geometry
3. Record baseline:
   ├─ R_measured = 3.0000m (should match ground truth)
   ├─ e_measured = 0.1mm (should be near 0)
   └─ section fits OK? ✓
```

### **Step 2: Load Tn and measure deformation**
```
1. Step 2-5: Load Tn.las → analyze geometry
2. Step 6: Deformation measurement (T0 vs Tn)
3. Recorded metrics:
   ├─ Crown settlement = ?mm (GT: -7mm)
   ├─ Sidewall convergence = ?mm (GT: -5mm)
   ├─ Eccentricity change = ?mm (GT: +1-2mm)
   └─ Local damage = ?mm (GT: -15mm @ chainage 65m)
```

### **Step 3: Calculate error and confidence**
```
For each metric:
error_mm = |measured_mm - ground_truth_mm|

Acceptance criteria (±3mm industry standard):
├─ Crown settlement: error < 1mm → PASS
├─ Convergence: error < 1mm → PASS
├─ Local damage: error < 2mm → PASS
└─ Mean absolute error: < 1mm → PASS

If all PASS → Tool is validated ✓
If any FAIL → Debug (registration issue, noise, fitting) ✗
```

---

## 4. Repeatability: Multiple Scenarios

To build confidence, repeat Protocol with variations:

### **Scenario A: No deformation (T0 → T0)**
```
Expected: All metrics unchanged (error ≈ 0mm)
Purpose: Verify registration and noise floor
```

### **Scenario B: Single metric deformation**
```
├─ Scenario B1: Crown only (-7mm, no convergence)
├─ Scenario B2: Convergence only (-5mm, no crown)
├─ Scenario B3: Local damage only (-15mm, no other)
Purpose: Isolate each measurement pipeline
```

### **Scenario C: Combined deformation (realistic)**
```
├─ Crown: -7mm @ 20m
├─ Convergence: -5mm @ 45m
├─ Local: -15mm @ 65m
Purpose: Test realistic multi-component deformation
```

### **Scenario D: Different scanner position**
```
├─ T0 from scanner at (0, 10, 3)
├─ Tn from scanner at (1.5, 12, 3.5) (offset position)
Purpose: Test if deformation is independent of scanner position
```

**Record results:**
```
validation_results.csv:
scenario,metric,ground_truth_mm,measured_mm,error_mm,status
A_ref,radius,3.0000,3.0001,0.0001,PASS
B1_crown,crown_settle,-7.0,-6.8,0.2,PASS
B2_conv,convergence,-5.0,-5.1,0.1,PASS
C_combined,crown_settle,-7.0,-6.9,0.1,PASS
C_combined,convergence,-5.0,-5.0,0.0,PASS
D_offset,crown_settle,-7.0,-6.85,0.15,PASS
```

---

## 5. Documentation & Reproducibility

### **File structure:**
```
tunnel_project/data/blender_lidar_t0t5/
├─ tunnel_lidar_scene.blend (reference, clean)
├─ tunnel_deformed_T1.blend (crown -7mm @ 20m)
├─ tunnel_deformed_T2.blend (+ convergence -5mm @ 45m)
├─ tunnel_deformed_T3.blend (+ local damage -15mm @ 65m)
├─ T0.las (clean reference, 364 points)
├─ T1.las (T1 deformed)
├─ T2.las (T1+T2 deformed)
├─ T3.las (T1+T2+T3 deformed)
├─ ground_truth.csv (prescribed deformation values)
├─ validation_results.csv (measured vs GT comparison)
└─ RAYCASTING_GROUNDTRUTH_PROTOCOL.md (this file)
```

### **Metadata: Each LAS file must have JSON companion**
```
T0.json:
{
  "source": "raycasting_TLSynth_protocol",
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

T1.json:
{
  "source": "raycasting_TLSynth_protocol",
  "mesh_source": "tunnel_deformed_T1.blend",
  "scanner_location": [0, 10, 3],
  "deformation_prescribed": {
    "crown_settlement_mm": -7.0,
    "chainage": 20,
    "extent": "±2m"
  },
  "ground_truth_file": "ground_truth.csv",
  "validation_status": "pending",
  "created_date": "2026-06-23"
}
```

### **Validation report template:**
```
validation_report_T0_T1.md:

# Validation: T0 vs T1

## Ground Truth
- Crown settlement: -7mm @ chainage 20m
- Noise model: 5mm + 2mm per 10m

## Measured Results
- Crown settlement: -6.8mm ± 0.2mm
- Error: 0.2mm (2.9% relative)

## Verdict
✓ PASS - Error within ±1mm tolerance

## Notes
- Point cloud clean, no outliers
- Centerline extraction smooth
- Section fitting converged
- Recommendation: Tool ready for field validation
```

---

## 6. Implementation Checklist

- [ ] Load tunnel_lidar_scene.blend
- [ ] Verify Tunnel_Lining mesh (16100 verts, clean)
- [ ] Setup scanner sphere @ (0, 10, 3)
- [ ] Raycast T0 → export T0.las
- [ ] Record T0 metadata (radius, e, oval)
- [ ] Create deformed mesh (crown -7mm @ 20m)
- [ ] Raycast Tn → export Tn.las
- [ ] Record Tn metadata
- [ ] Load T0.las into tool
- [ ] Load Tn.las into tool
- [ ] Measure deformation metrics
- [ ] Calculate error vs ground truth
- [ ] Document results in validation_results.csv
- [ ] Repeat for Scenario B, C, D
- [ ] Write final validation report
- [ ] Commit to git

---

## 7. References

- **TLSynth paper:** Remote Sensing 2025, §3.1-3.5
  - Raycasting mechanics: §3.1
  - Noise model: §3.2
  - Point deletion: §3.3
  - Export: §3.5

- **SSL Tunnel validation:** Your T0→T5 time-series
  - MAE 0.58mm, max error 2.45mm
  - Validates mm-level deformation measurement

- **Implementation:** `convert_raycast_to_las.py`, `verify_synthetic_las.py`

---

## 8. Expected Timeline

| Task | Time | Who |
|------|------|-----|
| T0 raycast | 15 min | Blender script |
| T1-T3 deformation | 30 min | Manual mesh edit |
| Raycast T1-T3 | 15 min | Blender script |
| Tool validation | 30 min | tunnel_analysis app |
| Error calculation | 10 min | Python |
| **Total** | **~2 hours** | — |

---

**This protocol ensures synthetic ground truth is created rigorously,
following TLSynth methodology, and ready for tool validation.**
