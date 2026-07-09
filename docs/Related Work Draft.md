# Related Work Draft

#paper #related-work #draft

## Tunnel deformation monitoring with laser scanning

Laser scanning has become an important tool for tunnel geometry capture because it provides dense 3D surface measurements that can be processed into cross-sections, profiles, and deformation indicators. Mobile laser scanning can support tunnel cross-section deformation monitoring, while terrestrial laser scanning has been used for 3D tunnel deformation modeling.

Relevant references:

- Camara et al. 2024: mobile laser scanning point cloud for tunnel cross-section deformation monitoring.
- Xie and Lu 2017: 3D modeling algorithm for tunnel deformation monitoring based on terrestrial laser scanning.

## Point-cloud comparison and M3C2

Point-cloud deformation monitoring requires robust comparison between epochs. The M3C2 method is widely cited for accurate 3D comparison of complex topography from terrestrial laser scanning. In this project, M3C2-style time-series signals provide complementary spatial evidence to section-level crown deformation metrics.

Relevant references:

- Lague et al. 2013: accurate 3D comparison / M3C2 foundation.
- Liu et al. 2023: multi-temporal point-cloud monitoring context.

## Synthetic LiDAR and raycasting validation

Synthetic data is useful when real ground truth is unavailable. LiDAR sensor simulation and raycasting-based validation can provide controlled measurements, but synthetic datasets must be interpreted carefully because they may not capture all field artifacts.

Relevant references:

- Gusmão et al. 2020: LiDAR sensor simulators based on parallel raycasting.
- Karur et al. 2022: synthetic LiDAR point-cloud data generation and validation.

## Gap addressed by this work

The current work addresses the validation gap by using a controlled T0-T5 tunnel dataset with known deformation values. Instead of claiming broad field robustness, the manuscript focuses on whether the workflow can recover known deformation under a reproducible synthetic benchmark.

## Links

- [[References Draft]]
- [[Citation Notes]]
- [[Ground Truth Definition]]
- [[Validation Method Draft]]
