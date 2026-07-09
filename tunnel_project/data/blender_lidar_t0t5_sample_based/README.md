# Blender LiDAR T0-T5 Sample-Based Dataset

This dataset is generated from `data/sample_pcd/Tunel.blend`, not from a procedural tunnel.

## Source

- Blender source: `data/sample_pcd/Tunel.blend`
- Epochs: `T0` to `T5`
- Columns: `x y z nx ny nz intensity label`

## Labels

1 lining, 2 rail/track, 4 cable/pipe, 5 fixture, 6 walkway/panel, 7 target, 8 equipment/other.

## Ground truth deformation

- Crown settlement: 0 to -35 mm
- Sidewall convergence: 0 to -22 mm
- Local damage: starts at T3 and reaches -28 mm at T5

## Suggested workflow

1. Load `T0.las` as reference.
2. Add `T1.las` to `T5.las`.
3. Run registration because T1-T5 include small pose bias.
4. Run Step 6 time-series/M3C2 analysis.
