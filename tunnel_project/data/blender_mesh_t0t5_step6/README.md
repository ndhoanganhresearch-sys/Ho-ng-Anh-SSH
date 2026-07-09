# Blender Mesh T0-T5 Step 6 Dataset

Six tunnel meshes are created in Blender through MCP, then their mesh vertices are exported as point clouds and converted to LAS by the wrapper script.

This dataset is for Step 6 testing only. It does not use raycasting.

## Files

- `T0.las` ... `T5.las`: LAS point clouds for the tool.
- `T0.txt` ... `T5.txt`: debug text point clouds with columns `x y z nx ny nz intensity label`.
- `blender_mesh_t0t5_step6.blend`: Blender scene containing six tunnel meshes arranged side by side for visual inspection.
- `ground_truth.csv`, `baseline_pairs.csv`, `incremental_pairs.csv`, `manifest.json`.

## Ground truth

- Crown settlement at chainage 20 m: 0 to -45 mm.
- Sidewall convergence at chainage 45 m: 0 to -35 mm.
- Local damage at chainage 65 m: starts at T3 and reaches -40 mm.

## Suggested test

Load `T0.las` as reference, add `T1.las` to `T5.las`, then run Step 6 trend/M3C2/technical section.
