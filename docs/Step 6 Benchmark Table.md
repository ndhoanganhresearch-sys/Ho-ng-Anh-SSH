# Step 6 Benchmark Table

#benchmark #step6 #deformation #validation

## Purpose

Track Step 6 deformation results for T0-T5 and connect each result to evidence.

## Verification Commands

```powershell
cd tunnel_project
.\agent_verify.ps1 step6
..\.venv\Scripts\python.exe benchmark_timeseries_t0t5.py
```

## Latest Result

- Date: 2026-06-30
- Gate: `agent_verify.ps1 step6` -> PASS
- Time-series benchmark: `17 passed / 0 failed`
- Report: `tunnel_project/output/timeseries_benchmark/timeseries_benchmark_report.json`
- Figures:
  - `tunnel_project/output/timeseries_benchmark/timeseries_benchmark_overview.png`
  - `tunnel_project/output/timeseries_benchmark/crown_profile_per_epoch.png`
  - `tunnel_project/output/timeseries_benchmark/m3c2_heatmap_T0_T5.png`

## Baseline Benchmark Table

| Pair | Expected crown max | Measured crown max | Abs error | Status | Evidence |
| --- | ---: | ---: | ---: | --- | --- |
| T0 -> T1 | `5.00 mm` | `5.00 mm` | `0.00 mm` | Pass | [[EXP Step6 T0-T5]] |
| T0 -> T2 | `12.00 mm` | `12.00 mm` | `0.00 mm` | Pass | [[EXP Step6 T0-T5]] |
| T0 -> T3 | `20.00 mm` | `19.09 mm` | `0.91 mm` | Pass | [[EXP Step6 T0-T5]] |
| T0 -> T4 | `30.00 mm` | `29.05 mm` | `0.95 mm` | Pass | [[EXP Step6 T0-T5]] |
| T0 -> T5 | `45.00 mm` | `44.05 mm` | `0.95 mm` | Pass | [[EXP Step6 T0-T5]] |

## Additional Signals

| Epoch | Convergence max | Heatmap p95 | Heatmap max | Ovality mean | Eccentricity mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| T1 | `0.00 mm` | `1.00 mm` | `5.00 mm` | `0.0218%` | `0.15 mm` |
| T2 | `9.60 mm` | `4.00 mm` | `12.00 mm` | `0.0453%` | `0.36 mm` |
| T3 | `23.60 mm` | `9.00 mm` | `20.00 mm` | `0.0840%` | `0.67 mm` |
| T4 | `43.60 mm` | `15.00 mm` | `30.00 mm` | `0.1342%` | `1.01 mm` |
| T5 | `69.60 mm` | `24.00 mm` | `45.00 mm` | `0.2036%` | `1.52 mm` |

## Forecast

- Method: `M3C2`
- Forecast rate: `1.2057 mm/epoch`
- R2: `0.9997`
- Caution threshold crossing: `9.14` epochs
- Critical threshold crossing: `14.67` epochs
- Low confidence: `false`

## Links

- [[Ground Truth Definition]]
- [[Step 6 Deformation]]
- [[EXP Step6 T0-T5]]
- [[Experiment Log]]
- [[Research Claims]]
