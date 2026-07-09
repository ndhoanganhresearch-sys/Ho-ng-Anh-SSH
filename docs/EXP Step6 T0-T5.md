# EXP Step6 T0-T5

#experiment #step6 #deformation #validation

## Goal

Validate cumulative deformation from baseline `T0` to final epoch `T5`, and confirm the full T0-T5 benchmark series.

## Dataset

- [[Dataset T0-T5]]
- [[Ground Truth Definition]]

## Commands Run

```powershell
cd tunnel_project
.\agent_verify.ps1 step6
..\.venv\Scripts\python.exe benchmark_timeseries_t0t5.py
```

## Result Summary

- `agent_verify.ps1 step6`: PASS
- `benchmark_timeseries_t0t5.py`: `17 passed / 0 failed`
- All 6 epochs loaded: `T0` to `T5`, each `15456` points
- Centerline extracted: `80` frames
- Profile detected: `Circle`
- Design radius: `3.0 m`
- Time-series method: `M3C2`

## T0 -> T5 Result

- Expected crown max: `45.00 mm`
- Measured crown max: `44.05 mm`
- Absolute error: `0.95 mm`
- Convergence max: `69.60 mm`
- Heatmap p95: `24.00 mm`
- Heatmap max: `45.00 mm`
- Status: Pass

## Output Files

- Report: `tunnel_project/output/timeseries_benchmark/timeseries_benchmark_report.json`
- Overview figure: `tunnel_project/output/timeseries_benchmark/timeseries_benchmark_overview.png`
- Crown profile figure: `tunnel_project/output/timeseries_benchmark/crown_profile_per_epoch.png`
- M3C2 heatmap: `tunnel_project/output/timeseries_benchmark/m3c2_heatmap_T0_T5.png`

## Interpretation

The benchmark supports the core deformation claim: Step 6 tracks cumulative crown deformation across T0-T5 with sub-millimeter to about 1 mm absolute error on crown maxima for the tested synthetic dataset.

## Links

- [[Step 6 Deformation]]
- [[Step 6 Benchmark Table]]
- [[Experiment Log]]
- [[Research Claims]]
