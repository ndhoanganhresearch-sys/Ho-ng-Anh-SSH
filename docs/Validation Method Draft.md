# Validation Method Draft

#paper #method #validation #step6 #deformation

## Purpose

Draft the validation/method section for the deformation monitoring paper using the verified T0-T5 benchmark evidence.

## Dataset and Ground Truth

The validation uses the synthetic time-series tunnel deformation dataset described in [[Dataset T0-T5]] and [[Ground Truth Definition]]. The dataset contains six epochs, `T0` to `T5`, with `T0` serving as the clean baseline. Each epoch contains `15456` tunnel point-cloud samples. The tunnel has a length of `80 m` and a design radius of `3.0 m`.

Ground-truth deformation is provided by `ground_truth.csv`, with cumulative crown settlement increasing from `T0` to `T5`. The final epoch has a known crown deformation of approximately `45 mm` near chainage `20 m`.

## Pipeline

The validation pipeline follows the project Step 6 workflow in [[Step 6 Deformation]]:

1. Load the baseline point cloud `T0` and target epochs `T1` to `T5`.
2. Extract the tunnel centerline and Frenet frames from `T0`.
3. Compute per-section deformation metrics for each `T0 -> Tn` pair.
4. Compare measured crown deformation against ground truth.
5. Compute time-series deformation signals using `M3C2`.
6. Generate overview figures, crown profiles, and T0-T5 heatmaps.

## Verification Commands

```powershell
cd tunnel_project
.\agent_verify.ps1 step6
..\.venv\Scripts\python.exe benchmark_timeseries_t0t5.py
```

## Key Results

The Step 6 verification gate passed, and the T0-T5 benchmark completed with `17 passed / 0 failed`.

| Pair | Expected crown max | Measured crown max | Absolute error |
| --- | ---: | ---: | ---: |
| T0 -> T1 | `5.00 mm` | `5.00 mm` | `0.00 mm` |
| T0 -> T2 | `12.00 mm` | `12.00 mm` | `0.00 mm` |
| T0 -> T3 | `20.00 mm` | `19.09 mm` | `0.91 mm` |
| T0 -> T4 | `30.00 mm` | `29.05 mm` | `0.95 mm` |
| T0 -> T5 | `45.00 mm` | `44.05 mm` | `0.95 mm` |

The final `T0 -> T5` comparison measured `44.05 mm` crown deformation against the expected `45.00 mm`, giving an absolute error of `0.95 mm`.

## Interpretation

The benchmark supports the claim that the Step 6 deformation workflow can track cumulative crown deformation across multiple epochs in a controlled synthetic tunnel dataset. The crown deformation trend is monotonic and remains close to the known ground truth across all target epochs.

The validation currently supports synthetic-data claims. It does not yet prove field deployment robustness on real tunnel scans with occlusion, scanner drift, wet surfaces, traffic objects, or mixed sensor noise.

## Publication-Ready Claim

Supported claim:

> In a controlled T0-T5 synthetic tunnel deformation benchmark, the proposed Step 6 workflow recovered cumulative crown deformation with less than `1 mm` absolute crown-maximum error for epochs T3-T5 and exact recovery for T1-T2 under the tested configuration.

## Limitations to State

- Synthetic deformation is cleaner than real tunnel monitoring data.
- Registration was not the main stressor in the aligned T0-T5 benchmark.
- The validation focuses on crown maxima and supporting deformation indicators, not full structural diagnosis.
- Real-world validation still needs field data or a more realistic synthetic clutter/raycasting benchmark.

## Evidence Links

- [[Step 6 Benchmark Table]]
- [[EXP Step6 T0-T5]]
- [[Ground Truth Definition]]
- [[Research Claims]]
- `tunnel_project/output/timeseries_benchmark/timeseries_benchmark_report.json`
- `tunnel_project/output/timeseries_benchmark/timeseries_benchmark_overview.png`
- `tunnel_project/output/timeseries_benchmark/crown_profile_per_epoch.png`
- `tunnel_project/output/timeseries_benchmark/m3c2_heatmap_T0_T5.png`
