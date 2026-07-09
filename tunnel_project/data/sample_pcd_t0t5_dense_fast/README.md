# Sample PCD T0-T5 Dense Dataset

This dataset preserves the point coverage of the sample point cloud and applies deterministic T0-T5 deformation directly to the points.

## Source

- `C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project\data\sample_pcd\u-type_tunnel_0k630 cut_1.las`
- Points per epoch: `166,186`

## Why this dataset exists

The Blender raycast version can be too sparse for GUI/M3C2 testing. This dense version keeps the original sample coverage so the deformation map does not appear as a thin strip or with large missing areas.

## Ground truth deformation

- Crown settlement: 0 to -36 mm
- Sidewall convergence: 0 to -24 mm
- Local damage: starts at T3 and reaches -30 mm at T5

## Files

- `T0.las` ... `T5.las`: recommended for tool loading.
- `T0.txt` ... `T5.txt`: debug text with `x y z nx ny nz intensity label`.
- `ground_truth.csv`, `baseline_pairs.csv`, `incremental_pairs.csv`, `manifest.json`.

## Suggested workflow

1. Load `T0.las` as reference.
2. Add `T1.las` to `T5.las` for time-series testing.
3. Run Step 6 trend/M3C2. Registration can be run too because T1-T5 include small pose bias.
