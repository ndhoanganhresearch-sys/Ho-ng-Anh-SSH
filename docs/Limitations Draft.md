# Limitations Draft

#paper #limitations #validation #future-work

## Purpose

Document limitations that must be stated clearly before using the T0-T5 benchmark as publication evidence.

## Current Validation Scope

The current evidence supports synthetic time-series tunnel deformation validation, not full real-world deployment.

Supported scope:

- Controlled synthetic tunnel geometry.
- Known T0-T5 ground truth.
- Clean baseline `T0` and aligned target epochs.
- Step 6 deformation evaluation with benchmarked crown maxima.
- M3C2 time-series signal generation.

Not yet fully supported:

- Real tunnel scans under operational conditions.
- Strong occlusion from trains, equipment, cables, water, dust, or maintenance objects.
- Severe registration drift between field epochs.
- Scanner-specific noise models and mixed sensor data.
- Structural diagnosis beyond geometric deformation indicators.

## Limitations to Include in Paper

### Synthetic Dataset Limitation

The T0-T5 dataset provides controlled ground truth and repeatability, but does not reproduce all noise sources and surface artifacts found in field tunnel monitoring.

### Registration Stress Limitation

The time-series benchmark focuses on deformation recovery after the point clouds are in a comparable frame. It is not a complete stress test of registration under large field misalignment.

### Metric Scope Limitation

The benchmark emphasizes crown deformation, convergence, heatmap response, ovality, and eccentricity. These are geometric indicators, not a complete structural safety diagnosis.

### Generalization Limitation

The current validation should be interpreted as proof-of-workflow for controlled tunnel deformation monitoring. Additional field data or high-fidelity raycasting scenes are needed before claiming operational robustness.

## Mitigation Plan

- Use [[Reference Repo Decisions]] to decide whether GROR-style robust registration should be prototyped.
- Use [[PUBLICATION_ROADMAP]] raycasting validation plan for more realistic synthetic scenes.
- Add real or semi-real clutter benchmarks before making field-deployment claims.
- Keep unsupported claims marked as partial in [[Research Claims]].

## Links

- [[Validation Method Draft]]
- [[Research Claims]]
- [[Step 6 Benchmark Table]]
- [[Reference Repo Decisions]]
- [[PUBLICATION_ROADMAP]]
