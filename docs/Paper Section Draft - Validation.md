# Paper Section Draft - Validation

#paper #draft #validation #method #results

## 1. Validation Dataset

The validation experiment used a synthetic time-series tunnel deformation dataset containing six epochs, denoted `T0` through `T5`. The baseline epoch `T0` represents the undeformed reference tunnel, while subsequent epochs introduce increasing deformation magnitudes. Each epoch contains `15456` point samples from a tunnel with an `80 m` length and a `3.0 m` design radius. The ground-truth deformation values are stored in `ground_truth.csv`, enabling direct numerical comparison between measured and expected deformation.

The final epoch `T5` contains approximately `45 mm` crown settlement near chainage `20 m`, providing a controlled benchmark for evaluating whether the proposed workflow can recover cumulative deformation across time.

## 2. Validation Workflow

The deformation validation followed the Step 6 processing workflow. First, the baseline point cloud `T0` was used to extract the tunnel centerline and construct Frenet frames. Then, each target epoch `T1` to `T5` was compared against `T0` to estimate cumulative deformation. Per-section deformation indicators included crown deformation, convergence, ovality, eccentricity, and spatial distance-map response.

A time-series deformation analysis was also computed using an M3C2-based distance signal. The benchmark generated an overview plot, per-epoch crown profile, and a T0-T5 M3C2 heatmap for visual interpretation.

## 3. Quantitative Results

The verification gate `agent_verify.ps1 step6` passed successfully. The dedicated T0-T5 benchmark script completed with `17 passed / 0 failed`.

| Pair | Expected crown max | Measured crown max | Absolute error |
| --- | ---: | ---: | ---: |
| T0 -> T1 | `5.00 mm` | `5.00 mm` | `0.00 mm` |
| T0 -> T2 | `12.00 mm` | `12.00 mm` | `0.00 mm` |
| T0 -> T3 | `20.00 mm` | `19.09 mm` | `0.91 mm` |
| T0 -> T4 | `30.00 mm` | `29.05 mm` | `0.95 mm` |
| T0 -> T5 | `45.00 mm` | `44.05 mm` | `0.95 mm` |

The measured crown maximum deformation closely matched the known ground truth across all epochs. For the final `T0 -> T5` comparison, the measured crown deformation was `44.05 mm`, compared with the expected `45.00 mm`, resulting in an absolute error of `0.95 mm`.

## 4. Visual Results

The benchmark generated three visual outputs:

- [[Figure Captions#Figure 1. Time-series benchmark overview|Figure 1]] summarizes the overall T0-T5 benchmark behavior.
- [[Figure Captions#Figure 2. Crown deformation profile by epoch|Figure 2]] shows per-epoch crown deformation profiles.
- [[Figure Captions#Figure 3. M3C2 deformation heatmap for T0-T5|Figure 3]] shows the spatial T0-T5 deformation response.

These figures support the numerical benchmark by showing the progressive deformation trend and the spatial localization of the final-epoch deformation.

## 5. Interpretation

The results indicate that the Step 6 workflow can recover cumulative crown deformation in a controlled synthetic tunnel dataset with high numerical accuracy. The monotonic increase in deformation from `T1` to `T5`, together with the low crown-maximum error, supports the use of the workflow for controlled time-series deformation validation.

The evidence currently supports a synthetic benchmark claim, not a full field-deployment claim. Real-world tunnel monitoring would require additional validation under occlusion, registration drift, variable scanner noise, and operational clutter.

## 6. Limitations

The main limitations are summarized in [[Limitations Draft]]. The current validation is synthetic, aligned, and controlled. It does not fully represent real field scans, severe registration challenges, or structural safety assessment. Therefore, the supported claim should be framed as controlled validation of a deformation measurement workflow.

## 7. Paper-Ready Claim

In a controlled T0-T5 synthetic tunnel deformation benchmark, the Step 6 workflow recovered cumulative crown deformation with exact crown-maximum recovery for T1-T2 and less than `1 mm` absolute crown-maximum error for T3-T5 under the tested configuration.

## Evidence Links

- [[Validation Method Draft]]
- [[Step 6 Benchmark Table]]
- [[EXP Step6 T0-T5]]
- [[Figure Table Index]]
- [[Figure Captions]]
- [[Limitations Draft]]
- [[Citation Notes]]

## 8. Suggested Citations

Use [[References Draft]] for bibliography details.

- Tunnel monitoring context: Camara et al. (2024), Xie and Lu (2017).
- Point-cloud distance/M3C2 method: Lague et al. (2013).
- Multi-temporal point-cloud monitoring context: Liu et al. (2023).
- Synthetic LiDAR/raycasting validation: Gusmão et al. (2020), Karur et al. (2022).
