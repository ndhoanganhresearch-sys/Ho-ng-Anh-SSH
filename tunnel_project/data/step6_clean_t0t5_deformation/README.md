# Step 6 Clean T0-T5 Deformation Dataset

Clean synthetic dataset for Step 6 only.

- No raycasting.
- No scanner simulation.
- T0-T5 are already registered in the same coordinate system.
- Deformation includes upper/crown deflection and local damage.

## Ground truth

- Upper deflection at chainage 20 m: 0 -> -45 mm.
- Local damage at chainage 65 m: starts at T3 and reaches -40 mm.

## Files

- `T0.las` ... `T5.las`: LAS point clouds for the tool.
- `T0.txt` ... `T5.txt`: debug text files.
- `ground_truth.csv`, `baseline_pairs.csv`, `incremental_pairs.csv`, `manifest.json`.
- `step6_clean_t0t5_preview.blend`: optional Blender preview scene.

## Suggested workflow

Load `T0.las` as reference, add `T1.las` to `T5.las`, then run Step 6 trend/M3C2/technical section.
