# Ground Truth Definition

#dataset #ground-truth #deformation #validation

## Purpose

Define the reference deformation values used to validate the T0-T5 tunnel deformation pipeline.

## Source Files

- Dataset note: [[Dataset T0-T5]]
- Dataset folder: `tunnel_project/data/time_series_deformation/`
- Ground truth: `tunnel_project/data/time_series_deformation/ground_truth.csv`
- Baseline pairs: `tunnel_project/data/time_series_deformation/baseline_pairs.csv`
- Incremental pairs: `tunnel_project/data/time_series_deformation/incremental_pairs.csv`
- Manifest: `tunnel_project/data/time_series_deformation/manifest.json`

## Expected Validation Logic

1. Use `T0` as the clean baseline.
2. Compare each target epoch `Tn` against `T0`.
3. Measure deformation in consistent units.
4. Compare measured values against `ground_truth.csv`.
5. Record per-epoch error in [[Step 6 Benchmark Table]].

## Known Ground Truth Summary

- Tunnel length: `80 m`
- Tunnel radius: `3.0 m`
- Points per epoch: `15456`
- Epochs: `T0` to `T5`
- Crown settlement near chainage `20 m`: `0 -> -45 mm` from `T0` to `T5`

## Acceptance Criteria

- [ ] Units are explicitly recorded for every result.
- [ ] Each epoch result links to an experiment note.
- [ ] Each experiment links to raw command output or exported figure.
- [ ] Benchmark table includes error against ground truth.
- [ ] Any failed/weak result is marked before being used in [[Research Claims]].

## Links

- [[Dataset T0-T5]]
- [[Step 6 Deformation]]
- [[Step 6 Benchmark Table]]
- [[Research Claims]]
