# Tunnel T0~T5 Blender dataset (curved railway-scale, LAS-ready)

Derived from `../sample_pcd/Tunel.blend`. Built for Step 6 time-series deformation
testing. The lining keeps the original horseshoe/D shape, but the cross-section is
scaled uniformly in X/Z to railway-tunnel size and the tunnel alignment is curved in
plan view. LAS and NPY point clouds are exported for all epochs under `las_export/`.

## Files

| File | Purpose |
| --- | --- |
| `Tunel_clean_visible.blend` | Step A: full sample tunnel, cleaned + clearly visible (camera/lights/labels). |
| `Tunel_T0_T5_layout.blend` | Step C: lining-only T0~T5, side-by-side, color-coded green->red, labeled. |
| `Tunel_T0_T5_standard.blend` | Step C+D: curved railway-scale layout + true-mm deformation + nested cross-section overlays. |
| `ground_truth.csv` | Per-epoch crown settlement + local damage (mm) + measured displacement. |
| `baseline_pairs.csv` | Cumulative T0->Tn deformation. |
| `incremental_pairs.csv` | Incremental Tn->Tn+1 deformation. |
| `las_export/T0.las`..`T5.las` | Exported 60k-point epoch clouds for Step 6 testing. |

## Geometry

- Hero lining = `Cylinder` from the source file; floor/rails/cables/decoration were dropped.
- Bore: ~**6.0 m wide x 5.12 m tall x ~80 m long**, horseshoe/D profile.
- Section centre (X,Z) = **(0.0, 0.823)**, crown at Z=3.383, runs along +Y (chainage).
- Plan-view alignment: circular arc with **500 m radius**, max lateral offset ~**1.60 m** over the 80 m chord.
- 6 epochs `T0_lining`..`T5_lining`, each offset **+11 m in X** for Blender visual layout.
- Exported LAS/NPY clouds are in aligned local coordinates without the +11 m visual X offsets.
- Exported local bounds are approximately X[-3.0, 4.6], Y[-1.0, 78.95], Z[-1.74, 3.38].

## Deformation model (true scale, metres)

- **Crown settlement**: downward, height-weighted, Gaussian along chainage centred **ch.40 m**, sigma 18 m.
  Peak per epoch: T1 5, T2 12, T3 20, T4 30, T5 45 mm.
- **Local damage**: inward radial dent on the right shoulder, Gaussian centred **ch.60 m**, sigma 3 m,
  starts T3. Per epoch: T3 15, T4 25, T5 40 mm.
- `T0` is the pristine reference.
- Railway-size scaling preserves the original shape and keeps the absolute deformation deltas in mm.
- The plan curve is identical for all epochs, so T0->Tn deformation ground truth remains unchanged.

## Registration

`registration_status: pre-registered`, `transform: identity`, `rmse_mm: 0`.
Synthetic, same coordinate frame for all epochs. Pose error / auto-align is a later step.

## Cross-section overlays (visual proof)

`Tunel_T0_T5_standard.blend` contains nested cross-section rings at **ch.40 (crown)**
and **ch.60 (local damage)**, showing all six epochs T0..T5 overlaid.
Radial deformation is magnified x20 for display only; the lining mesh geometry itself
is at true mm and is the source of truth for the LAS export.

## Export status

- `las_export/T0.npy`..`T5.npy`: common-sample point clouds, 60,000 points each.
- `las_export/T0.las`..`T5.las`: LAS 1.4 exports with 0.1 mm coordinate precision.
- Sampling uses the same mesh triangle/barycentric locations for every epoch, so point order is T0->Tn comparable for synthetic checks.
