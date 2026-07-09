# Manuscript Outline - Tunnel Time-Series Deformation

#paper #manuscript #outline #tunnel-monitoring

## Working Title

Time-Series Tunnel Deformation Monitoring from Point Clouds Using Ground-Truth Synthetic Validation

## Target Direction

Paper-first direction focused on controlled validation of the Step 6 deformation workflow using the T0-T5 synthetic tunnel benchmark.

## Core Contribution

This manuscript validates a point-cloud-based tunnel deformation workflow on a controlled T0-T5 time-series dataset with known ground truth. The workflow recovers cumulative crown deformation with less than `1 mm` crown-maximum error for T3-T5 and exact recovery for T1-T2 under the tested synthetic configuration.

## Manuscript Structure

### 1. Abstract

Source: [[Paper Abstract Draft]]

Status: Drafted.

### 2. Introduction

Purpose:

- Motivate tunnel deformation monitoring.
- Explain why point-cloud time-series monitoring is useful.
- Explain why validation is difficult without ground truth.
- Position this work as controlled synthetic validation.

Citations:

- Camara et al. 2024 for mobile laser scanning tunnel deformation monitoring.
- Xie and Lu 2017 for terrestrial laser scanning tunnel deformation monitoring.
- Lague et al. 2013 for point-cloud comparison background.

Draft source: [[Introduction Draft]]

### 3. Related Work

Subsections:

1. Tunnel deformation monitoring with laser scanning.
2. Point-cloud distance and M3C2-style comparison.
3. Synthetic LiDAR/raycasting validation.

Citations:

- [[References Draft]]

Draft source: [[Related Work Draft]]

### 4. Dataset and Ground Truth

Source notes:

- [[Dataset T0-T5]]
- [[Ground Truth Definition]]

Key facts:

- Six epochs: `T0` to `T5`.
- Tunnel length: `80 m`.
- Radius: `3.0 m`.
- Points per epoch: `15456`.
- Final crown settlement near chainage `20 m`: about `45 mm`.

### 5. Method

Source notes:

- [[Validation Method Draft]]
- [[Step 6 Deformation]]

Method steps:

1. Load T0-T5 point clouds.
2. Use T0 as baseline.
3. Extract centerline and Frenet frames.
4. Compute per-section deformation metrics.
5. Compare T0 against each Tn.
6. Compute M3C2/time-series signal.
7. Generate figures and benchmark table.

### 6. Results

Source notes:

- [[Step 6 Benchmark Table]]
- [[EXP Step6 T0-T5]]
- [[Figure Table Index]]
- [[Figure Captions]]

Main result:

| Pair | Expected crown max | Measured crown max | Absolute error |
| --- | ---: | ---: | ---: |
| T0 -> T1 | `5.00 mm` | `5.00 mm` | `0.00 mm` |
| T0 -> T2 | `12.00 mm` | `12.00 mm` | `0.00 mm` |
| T0 -> T3 | `20.00 mm` | `19.09 mm` | `0.91 mm` |
| T0 -> T4 | `30.00 mm` | `29.05 mm` | `0.95 mm` |
| T0 -> T5 | `45.00 mm` | `44.05 mm` | `0.95 mm` |

Figures:

- `docs/assets/timeseries_benchmark_overview.png`
- `docs/assets/crown_profile_per_epoch.png`
- `docs/assets/m3c2_heatmap_T0_T5.png`

### 7. Discussion

Points to discuss:

- The deformation trend is recovered monotonically from T1 to T5.
- The final T0-T5 error is below `1 mm` for crown maximum.
- M3C2 heatmap provides spatial evidence, while crown profile provides section-level evidence.
- The evidence supports controlled synthetic validation, not broad field deployment.

Draft source: [[Discussion Draft]]

### 8. Limitations

Source: [[Limitations Draft]]

Core limitations:

- Synthetic data does not capture all real tunnel scanning artifacts.
- Registration stress is limited in the current T0-T5 benchmark.
- The method measures geometric indicators, not direct structural safety.
- More field/raycasting validation is needed.

### 9. Conclusion

Draft source: [[Conclusion Draft]]

Main conclusion:

The Step 6 workflow accurately tracks controlled time-series crown deformation in the T0-T5 synthetic tunnel benchmark and provides a reproducible evidence chain for future paper/report development.

### 10. References

Source: [[References Draft]]

## Current Evidence Chain

```text
Dataset T0-T5
  -> Ground Truth Definition
  -> Step 6 Benchmark Table
  -> EXP Step6 T0-T5
  -> Figure Captions
  -> Paper Section Draft - Validation
  -> Manuscript Outline
  -> Research Claims
```

## Remaining Work

- [ ] Add formal in-text citations in target journal style.
- [ ] Add full related work paragraphs.
- [ ] Decide target journal formatting.
- [ ] Convert outline to DOCX/LaTeX/Markdown manuscript.
- [ ] Add real-data or raycasting validation if required by target journal.

## Links

- [[Paper Abstract Draft]]
- [[Introduction Draft]]
- [[Related Work Draft]]
- [[Validation Method Draft]]
- [[Paper Section Draft - Validation]]
- [[Discussion Draft]]
- [[Conclusion Draft]]
- [[Limitations Draft]]
- [[References Draft]]
- [[Research Claims]]
