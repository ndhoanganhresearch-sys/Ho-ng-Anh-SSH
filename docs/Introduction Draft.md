# Introduction Draft

#paper #introduction #draft

Tunnel deformation monitoring is an important task for underground infrastructure maintenance because tunnel lining geometry can change over time due to ground movement, construction disturbance, material degradation, or operational loading. Laser scanning and point-cloud processing provide a dense geometric record of tunnel surfaces and can support deformation assessment across repeated inspection epochs.

Recent studies have used mobile or terrestrial laser scanning for tunnel cross-section deformation monitoring and 3D tunnel deformation modeling. These works show that point clouds can capture detailed tunnel geometry and support cross-section-based deformation analysis. However, real monitoring data often lacks precise ground truth, making it difficult to quantify the numerical accuracy of a deformation workflow.

This work focuses on controlled validation. A synthetic time-series tunnel dataset with known T0-T5 deformation values is used to evaluate whether the Step 6 deformation workflow can recover cumulative crown deformation across multiple epochs. The validation uses T0 as the baseline and compares subsequent epochs T1-T5 against known ground-truth deformation values.

The main contribution is a reproducible evidence chain connecting dataset definition, ground truth, benchmark execution, numeric error, figures, and research claims. In the tested T0-T5 benchmark, the workflow recovered crown maximum deformation with exact recovery for T1-T2 and less than 1 mm absolute error for T3-T5.

## Citation Placement

- Tunnel monitoring motivation: Camara et al. 2024; Xie and Lu 2017.
- Point-cloud comparison background: Lague et al. 2013.
- Synthetic validation motivation: Gusmão et al. 2020; Karur et al. 2022.

## Links

- [[References Draft]]
- [[Manuscript Outline - Tunnel Time-Series Deformation]]
- [[Dataset T0-T5]]
- [[Step 6 Benchmark Table]]
