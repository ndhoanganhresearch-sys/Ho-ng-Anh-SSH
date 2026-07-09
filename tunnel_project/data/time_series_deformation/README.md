# Time-Series Deformation Dataset T0-T5

Clean synthetic dataset for validating time-series deformation analysis. All epochs are already registered.

## Files
- `T0.las` ... `T5.las`: six monitoring epochs.
- `ground_truth.csv`: absolute deformation value at each epoch.
- `baseline_pairs.csv`: accumulated deformation from T0 to Tn.
- `incremental_pairs.csv`: deformation increment from Tn to Tn+1.
- `manifest.json`: machine-readable metadata.

## Ground Truth
- Crown settlement at chainage 20 m grows from 0 to -45 mm.
- Sidewall convergence at chainage 45 m grows from 0 to -35 mm.
- Local damage at chainage 65 m appears from T3 and grows to -40 mm.

## Suggested Tool Workflow
1. Load a pair such as `T0.las` and `T5.las`.
2. Registration may be skipped or treated as identity for this clean dataset.
3. Run parameter/section/deformation analysis.
4. Compare output with `ground_truth.csv`.
