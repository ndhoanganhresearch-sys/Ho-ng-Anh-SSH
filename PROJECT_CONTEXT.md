# SSL Smart Tunnel Monitoring System (4D-LiDAR)

## Project Identity

- Owner: Nguyen Duy Hoang Anh, Master researcher at Smart Structure Lab (SSL).
- Institution: Chungbuk National University (CBNU), South Korea.
- Advisor: Prof. Hyungchul "Henry" Yoon.
- Research object: Osong Tunnel.
- Input device: Faro Focus laser scanner, `.LAS` / `.PLY` point clouds.
- Target hardware: 32 GB RAM workstation with multi-core CPU.

## Five-Layer Architecture

1. Physical: acquire point-cloud data from Faro Focus.
2. Preprocessing: statistical outlier filtering, voxel downsampling, and target-intensity detection.
3. Geometric: construct design and measured tunnel centerlines using Frenet-Serret frames and B-Splines.
4. Evaluation: multi-station registration, deformation heatmaps, and RMSE validation.
5. AI/BIM: 4D deformation trend analysis, crack recognition, and work-order reporting.

## Registration Engine

The registration engine uses sequential stitching:

- Station `N` is registered to station `N-1` using common targets.
- SVD estimates the rigid rotation and translation from matched target centroids.
- RMSE controls registration quality, with a target threshold below 5 mm.
- Point-to-plane ICP refines tunnel-wall alignment using surface normals.
- Accumulated transforms bring every station into Station 1 as the global origin.

## 4D Deformation Analysis

- Time steps: compare overlapping scans from `T0`, `T1`, `T2`, and later campaigns.
- Delta methods: cloud-to-cloud or M3C2 surface displacement in millimeters.
- Monitoring outputs:
  - Crown settlement.
  - Wall convergence.
- Visual outputs: monthly trend line charts and deformation heatmaps.

## Application UI

The target application should converge into a single `TunnelApp.py` style interface with 10 functional tabs:

1. Overview: 3D full-tunnel view with LOD management.
2. Registration: station manager and target matching.
3. RANSAC: tunnel plane/cylinder segmentation.
4. Centerline: design and measured tunnel axes.
5. Section: cross-section slicing by chainage.
6. Rings: concrete segment ring analysis.
7. Time-Series: deformation trend charts.
8. Heatmap: deviation map, green for OK and red for warnings above 3 mm.
9. Results: statistics and tabular outputs.
10. AI Chat: assistant for direct tunnel-data queries.

## Coding Rules

- Keep functions complete, with explicit error handling.
- Use `numpy` and `Open3D` for matrix and point-cloud operations.
- Downsample point clouds for 3D overview rendering to protect 32 GB RAM systems.
- Include ground-truth comparison against simulated Blender data where possible.
- Preserve real tunnel proportions in 3D plots, especially `ax.set_box_aspect([1, 10, 1])`.

## Development Backlog

1. Complete a multi-threaded `StationManager`.
2. Build the tunnel environmental noise filtering module using statistical outlier removal.
3. Develop BIM/IFC export from the measured centerline.
4. Upgrade AI trend detection for continuous settlement alerts.

