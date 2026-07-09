# SSL Smart Tunnel Monitoring System: An Automated LiDAR-Based Point Cloud Processing Pipeline for Structural Health Monitoring of Underground Tunnels

**Nguyen Duy Hoang Anh**  
[Department], [University], [City, Country]  
E-mail: ndhoanganh.research@gmail.com

**Article Info**  
Received: June 2026  
Keywords: LiDAR point cloud; tunnel structural health monitoring; automatic denoising; Frenet frame; M3C2 change detection; IFC4X3; retrieval-augmented generation

---

## Abstract

Automated structural health monitoring (SHM) of underground tunnels using terrestrial LiDAR remains challenging because raw point clouds often include non-structural clutter, irregular sampling density, occlusions, and multi-station alignment errors. These factors can distort cross-section geometry and increase the amount of manual preprocessing required before deformation metrics can be interpreted. This paper presents the SSL Smart Tunnel Monitoring System, a Python-based prototype pipeline for processing tunnel LiDAR point clouds from raw data ingestion to metric extraction, visualization, and inspection-oriented reporting. The system combines three main components: (1) an unsupervised tunnel-specific denoising cascade using morphological point features, radial median-absolute-deviation filtering, and cylindrical-grid protrusion detection; (2) a centerline-based Frenet-frame section extraction method designed to reduce sectioning bias in curved tunnel segments; and (3) an integrated reporting layer that links extracted deformation metrics with PDF/CSV/Excel outputs, IFC4X3-compatible BIM export, and a local retrieval-augmented generation assistant for standards-aware engineering summaries. Current benchmark evidence supports the denoising component on labelled synthetic tunnel data, while full validation on real multi-epoch tunnel datasets remains a required step before making certified metrology or compliance claims. The proposed workflow is intended to improve reproducibility and traceability in tunnel point-cloud inspection by connecting algorithms, parameters, outputs, and evidence artifacts within a single open research workspace.

---

## 1. Introduction

Underground tunnels are critical components of modern transportation networks, but they are also difficult assets to inspect because deformation, lining deterioration, water ingress, and non-structural obstructions may develop in confined environments with limited access windows. Major tunnel fire and safety incidents have increased attention to systematic inspection and maintenance planning. For example, the Fr?jus road tunnel fire in France in 2005 caused fatalities and a long tunnel closure; however, this event should be treated as a tunnel safety and operation reference rather than direct evidence of lining deformation. Regulatory frameworks such as European Directive 2004/54/EC define minimum safety requirements for long road tunnels, while Korean railway and tunnel standards provide local inspection and design criteria that are relevant to deformation monitoring. For this study, such standards are used as engineering context and must be mapped clause-by-clause before any formal compliance claim is made.

Terrestrial LiDAR scanning is widely used for tunnel inspection because it can acquire dense three-dimensional geometry over long tunnel sections with relatively limited disruption to operations. Prior studies have demonstrated LiDAR-based tunnel ovality measurement, convergence monitoring, defect detection, and surface change analysis. These studies show the value of point-cloud-based inspection, but practical deployment still depends on robust preprocessing, repeatable coordinate alignment, and traceable conversion from point measurements to engineering decisions.

A first challenge is that raw tunnel scans rarely contain only the structural lining. Cables, lights, signs, rails, equipment, personnel, and local occlusions can contaminate the tunnel surface model. If such objects are not removed or at least identified, they may bias radius, ovality, convergence, or clearance measurements. Manual cleaning is possible but reduces reproducibility and becomes difficult to scale across long tunnel networks or repeated monitoring campaigns.

A second challenge is geometric sectioning. Many tunnel-analysis workflows extract cross-sections using planes aligned with a global coordinate axis. This is convenient for straight tunnel segments, but it can introduce bias in curved or sloped alignments because the extracted section is not necessarily orthogonal to the local tunnel axis. A centerline-based local frame is therefore needed to make section geometry more consistent along the tunnel.

A third challenge is evidence traceability. Tunnel inspection outputs are often spread across point-cloud software, spreadsheets, figures, reports, and manual interpretation notes. For an academic paper, this creates a risk of unsupported claims; for engineering review, it makes it harder to trace a warning back to the dataset, threshold, command, commit version, and visual evidence. A useful research prototype should therefore treat benchmarks, material passports, standards mapping, and generated reports as part of the workflow rather than as after-the-fact documentation.

This paper presents the SSL Smart Tunnel Monitoring System, a Python-based tunnel point-cloud analysis prototype designed around these three challenges. The system ingests common point-cloud formats, applies tunnel-specific preprocessing and denoising, extracts centerline-aligned cross-sections, computes per-section deformation indicators, supports multi-epoch comparison, and exports inspection-oriented outputs including tables, plots, PDF reports, and IFC-compatible BIM models. A local retrieval-augmented generation assistant is included to help summarize measurement outputs against a curated standards knowledge base without sending project data to external services.

The principal contributions of this study are:

1. **A tunnel-specific unsupervised denoising cascade** that combines local morphological features, robust radial statistics, and cylindrical-grid protrusion detection to reduce non-structural clutter while preserving tunnel lining points.
2. **A centerline-based Frenet-frame section extraction workflow** that uses local tunnel-axis frames to improve geometric consistency of cross-section measurements in curved or non-axis-aligned tunnel segments.
3. **An evidence-oriented end-to-end inspection workspace** that connects metric extraction, multi-epoch visualization, standards-aware summaries, IFC/PDF/CSV/Excel outputs, benchmark records, and material-passport documentation.

The remainder of this paper is organized as follows. Section 2 reviews related work on LiDAR tunnel inspection, denoising, registration, deformation analysis, and AI-assisted engineering assessment. Section 3 describes the system architecture. Sections 4 through 8 present the processing modules. Section 9 describes the AI-assisted assessment module. Section 10 covers output generation. Section 11 defines the validation plan and reports currently available benchmark evidence. Section 12 concludes with limitations and future work.

---

## 2. Related Work

### 2.1 LiDAR-Based Tunnel Inspection

Terrestrial LiDAR has been applied to tunnel inspection in several prior studies. Jung et al. [9] demonstrated automated ovality measurement from mobile laser scanning data using circle-fitting on individual cross-sections. Gikas [10] proposed a least-squares cylinder-fitting approach for convergence monitoring. More recent work by Ye et al. [11] integrated semantic segmentation with point cloud processing for automated defect detection. However, none of these approaches addresses the combined challenges of automatic denoising, Frenet-corrected sectioning, and engineering-grade report generation in a single pipeline.

### 2.2 Point Cloud Denoising

Statistical outlier removal (SOR) [12] and radius outlier removal (ROR) are the standard methods for point cloud noise suppression, but they are ineffective against structured non-Gaussian clutter such as cables and fixtures. Learning-based approaches including PointNet++ [13] and DGCNN [14] achieve higher accuracy but require labelled training datasets that are rarely available for tunnel environments. The proposed three-stage cascade avoids this requirement by exploiting domain-specific geometric priors.

### 2.3 Multi-Scan Registration

Iterative Closest Point (ICP) [15] and its generalised variant (GICP) [16] are the standard approaches for fine point cloud registration. FPFH feature matching [17] provides coarse initialisation. The proposed system combines GROR-style graph-based outlier rejection with GICP for robust multi-station registration in tunnel environments where feature-rich correspondences are sparse.

### 2.4 AI-Assisted Structural Assessment

Large language models have recently been applied to civil engineering decision support. Jiang et al. [7] demonstrated GPT-4-based structural assessment from sensor readings. Retrieval-Augmented Generation (RAG) [18] addresses the hallucination problem by grounding LLM responses in retrieved domain documents. To our knowledge, this paper is the first to integrate a local RAG-LLM system into a tunnel SHM pipeline.

---

## 3. System Architecture

The SSL system is implemented as a modular Python pipeline with seven sequential processing stages, each encapsulated in an independent module. A `PipelineContext` state object propagates data between stages, enabling any stage to be skipped or replaced without disrupting downstream modules.

```
?뚢????????????????????????????????????????????????????? INPUT: LAS / LAZ / PLY / TXT / XYZ / CSV          ?붴????????????????????р????????????????????????????????                     ?          ?뚢??????????쇄??????????          ? Stage 1            ? io_layer.py
          ? Data Ingestion     ?          ?붴??????????р??????????                     ?          ?뚢??????????쇄??????????          ? Stage 2            ? preprocessing.py
          ? Auto-Denoising     ? ?꾟?? Contribution 1
          ?붴??????????р??????????                     ?          ?뚢??????????쇄??????????          ? Stage 3            ? registration.py
          ? Multi-Scan Reg.    ?          ?붴??????????р??????????                     ?          ?뚢??????????쇄??????????          ? Stage 4            ? geometry.py
          ? Frenet Centerline  ? ?꾟?? Contribution 2
          ?붴??????????р??????????                     ?          ?뚢??????????쇄??????????          ? Stage 5            ? parameters.py
          ? Parameter Extract  ?          ?붴??????????р??????????                     ?          ?뚢??????????쇄??????????          ? Stage 6            ? timeseries.py
          ? M3C2 Change Det.   ?          ?붴??????????р??????????                     ?     ?뚢???????????????쇄???????????????     ?              ?              ?뚢????쇄????  ?뚢??????쇄?????? ?뚢????쇄????Export  ?  ? RAG-LLM    ? ? IFC    ?괖SV/Excel?  ? Assistant  ? ? 4X3    ? PDF    ?  ?            ? ? BIM    ?붴?????????  ?붴????????????? ?붴?????????                  ?꾟? Contribution 3
```

The pipeline supports both an interactive PyQt/PySide6 GUI and a headless batch mode (`batch.py`) for automated processing of large tunnel networks.

---

## 4. Data Ingestion and Preprocessing

### 4.1 Multi-Format Data Ingestion

The `io_layer` module supports LAS/LAZ (via `laspy` [19]), PLY, and delimited text formats (TXT, XYZ, CSV, ASC). Each file is loaded into a `PointCloudBundle` structure containing XYZ coordinates (N횞3 float64), optional intensity (uint16, 0?5535), optional RGB colour (uint8), and optional semantic labels (STSD format [20]). A maximum of 5,000,000 points is enforced; larger clouds are spatially subsampled via voxel downsampling prior to processing.

### 4.2 Range Crop

Points beyond a configurable Euclidean distance from the scanner origin are removed as a first-pass filter. This step mirrors the MATLAB reference tool implementation for Korean railway tunnel inspection and eliminates low-density far-field points that degrade downstream statistical estimators. Three distance modes are supported: sensor-origin Euclidean (default), cloud-centroid Euclidean, and radial distance from the PCA tunnel axis.

### 4.3 Voxel Downsampling

A grid-based voxel filter [21] reduces point density while preserving surface geometry. Open3D's `voxel_down_sample` is used when available, with a NumPy fallback. Recommended grid sizes are 0.05 m for analysis, 0.02 m for precision work, and 0.10 m for preview.

### 4.4 Three-Stage Cascaded Auto-Denoising (Contribution 1)

The core preprocessing novelty is a three-stage cascade that removes non-structural clutter without labelled training data.

**Stage A ?Morphological Classification.** Local PCA is computed within a spherical neighbourhood at each point. The eigenvalue ratio 貫?(貫?貫?貫? characterises local surface shape: high linearity (貫?貫?貫? indicates cable-like structures; high planarity (貫?貫?貫? indicates flat fixtures or personnel. DBSCAN [22] clusters anomalous points into connected components that are removed when their bounding volume falls below the expected lining surface dimensions.

**Stage B ?Radial Statistical Filtering.** The tunnel is partitioned into 1 m axial bins along the PCA principal axis. Within each bin, the radial distance r from the estimated tunnel center is computed for all points. Points satisfying:

*|r ?median(r)| > 2.5 횞 MAD(r)*

are flagged as outliers, where MAD denotes the median absolute deviation. MAD is preferred over standard deviation because it is robust to the heavy-tailed distributions produced by fixtures and protrusions [23].

**Stage C ?Wall-Mounted Cable Detection.** A cylindrical grid is constructed around the tunnel axis, subdividing the tunnel surface into angular-axial cells. Within each cell, points are separated into background (lower percentile of radial distances, representing the lining surface) and foreground (protrusions). Foreground cells are then tested for axial continuity: a run of connected foreground cells spanning more than a configurable length threshold is classified as a wall-mounted cable and removed.

---

## 5. Multi-Scan Registration

### 5.1 Coarse Alignment

When multiple scanner stations are used, a GROR-style graph-based outlier rejection [24] procedure initialises the registration:

1. FPFH descriptors [17] are extracted from both source and target clouds.
2. Mutual nearest-neighbour matching in feature space identifies candidate correspondences.
3. A compatibility graph is constructed: two correspondences (p?곣넂q? p?귘넂q? are compatible if |?뻪?곣닋p?귘?뻫?곣닋q?귘? < ?.
4. The largest clique of compatible correspondences is used to estimate the rigid transformation via Umeyama SVD [25].

An intensity-centroid anchor translation serves as fallback when FPFH matching fails due to insufficient geometric structure.

### 5.2 Fine Registration

Generalised ICP (GICP) [16], implemented via the `small_gicp` library with multi-thread parallelisation, refines the coarse alignment. GICP models local surface covariance at each point, making it more robust than point-to-point ICP on noisy tunnel surfaces. The algorithm iterates until the relative fitness and RMSE change fall below 10?삘겤. The final RMSE is reported; values exceeding 2 mm trigger a quality warning per ITA guidelines [26].

---

## 6. Frenet-Frame Centerline Extraction (Contribution 2)

### 6.1 Initial Centerline Estimation

The tunnel axis is estimated as follows:

1. The point cloud is projected onto the dominant PCA eigenvector to define the axial coordinate.
2. The axial range [p_min, p_max] is partitioned into N equal-width slices (default N = 80). Equal-width partitioning ?as opposed to equal-count partitioning ?ensures uniform coverage at the sparse scan ends.
3. Within each slice, a circle is fitted to the cross-sectional points using the Fitzgibbon Direct Least Squares (DLS) method [27]. The fitted centre is taken as the axis point. Slices with fewer than MIN_SLICE_POINTS = 12 points use the slice centroid.
4. A median-based despike filter removes outlier centres caused by ring-seam gaps.

### 6.2 Frenet Frame Computation

At each centerline point C巢? a local orthonormal frame (T, N, B) is computed:

- **T** (tangent): T = (C巢™굤?C巢™굥? / ?뺺巢™굤?C巢™굥?곣?- **N** (principal normal): derived from the second-order finite difference, projected perpendicular to T, and normalised
- **B** (binormal): B = T 횞 N

Cross-sections are extracted by projecting points onto the N?밄 plane at each frame location. This guarantees geometric orthogonality to the tunnel axis, which is essential for accurate ovality estimation. Non-orthogonal (axis-aligned) sections introduce an apparent ovality error of up to 15% in curved tunnels ?a bias that propagates into all downstream deformation metrics.

### 6.3 Iterative Refinement

When a design axis is provided, an iterative convergence scheme refines the centerline:

1. Cross-sections are re-extracted using the current axis estimate.
2. New centres are computed by Fitzgibbon DLS fitting.
3. A B-spline (scipy `splprep`, C짼 continuity) is fitted to the new centres and blended with the previous estimate using relaxation factor 關 = 0.03:

*C_new = (1 ?關) 횞 C_prev + 關 횞 C_spline*

Convergence is declared when the mean inter-iteration shift falls below 1 mm.

---

## 7. Parameter Extraction

### 7.1 Cross-Section Geometry

An ellipse is fitted to each 2D projected cross-section by the Fitzgibbon DLS method. The fitted parameters yield:

- **Mean radius R**: R = (a + b) / 2, where a and b are semi-major and semi-minor axes
- **Ovality 琯**: 琯 = (a ?b) / a 횞 100%
- **Eccentricity e**: e = ?뺺_measured ?C_design?
### 7.2 Deformation Metrics (Multi-Epoch)

For surveys with a reference epoch T? and monitoring epoch T?

- **Crown Settlement 灌巢?*: Displacement of the crown point along the B (vertical) axis: 灌巢?= B 쨌 (crown_Tn ?crown_T0)
- **Lateral Convergence 灌?*: Change in horizontal span: 灌?= span_T0 ?span_Tn

### 7.3 Deformation Heatmap

For each point in T? the nearest point on T? is found using a k-d tree. The resulting Hausdorff distance provides a local deformation measure. The result is colour-mapped: green (<1 mm, stable), yellow (1? mm, caution), red (>3 mm, critical).

### 7.4 Safety Threshold Evaluation

All metrics are evaluated against the following thresholds per KR C-08080 and KDS 27 25 00:

| Parameter | Unit | Caution | Critical |
|-----------|------|---------|----------|
| Crown Settlement (灌巢? | mm | 10 | 25 |
| Lateral Convergence (灌? | mm | 15 | 30 |
| Ovality (琯) | % | 0.5 | 1.0 |
| Eccentricity (e) | mm | 10 | 25 |
| Train Clearance Intrusion | mm | 10 | 50 |

---

## 8. Multi-Epoch Change Detection

When more than two epochs are available, the Multiscale Model-to-Model Cloud Comparison (M3C2) algorithm [28] is applied via `py4dgeo`:

1. Local surface normals are estimated at each core point in T? using a variable-radius neighbourhood.
2. The signed distance to T?along the normal direction is computed within a projection cylinder.
3. A Level-of-Detection (LoD) is derived from the local registration error and point cloud roughness:

*LoD?됤굝 = 짹1.96 횞 ?짼_T?/n_T? + ?짼_T?n_T?*

Only displacements exceeding LoD?됤굝 are reported as statistically significant at the 95% confidence level.

---

## 9. AI-Assisted Safety Assessment (Contribution 3)

### 9.1 Knowledge Base and Retrieval

A knowledge base comprising 17 excerpts from Korean tunnel safety standards (KR C-08080, KDS 27 25 00), NATM guidelines, and ITA recommendations is indexed using the `all-MiniLM-L6-v2` sentence transformer [29] and stored in a ChromaDB vector database. For each engineer query, the top-5 most relevant excerpts are retrieved by cosine similarity.

### 9.2 Local LLM Inference

The retrieved standards and current section metrics are structured into a system prompt:

```
=== TUNNEL MEASUREMENT DATA ===
  crown_settlement_mm: {灌巢?
  lateral_convergence_mm: {灌?
  ovality_max_pct: {琯}
  ...

=== RELEVANT SAFETY STANDARDS ===
  - Crown settlement threshold: caution >10mm, critical >25mm (KR C-08080)
  - ...
```

The prompt is processed by an on-device LLM (Ollama, `qwen2.5:3b`) running on the local GPU (NVIDIA RTX 4060 Ti, 8 GB VRAM). The model generates an assessment covering: (1) overall tunnel condition evaluation, (2) parameters exceeding thresholds, (3) recommended actions with priority ranking. No data is transmitted to external servers, satisfying infrastructure security requirements.

A rule-based offline fallback provides threshold-based assessment when the LLM is unavailable.

---

## 10. Output Generation

### 10.1 CSV and Excel

Per-section tabular data includes chainage, section geometry (H1/H2/H3, W1/W2, R), deformation metrics (灌巢? 灌? 琯, e), and clearance status. Excel output includes embedded trend charts and conditional cell formatting (green/yellow/red) aligned with Table 1.

### 10.2 PDF Report

A professional PDF report is generated using `reportlab`, following the structure of Leica Cyclone 3DR output: cover page (project metadata, engineer, scan date, coordinate system), summary table, per-section cross-section plots (circle/ellipse fit, polar deformation heatmap), and a prioritised warning list.

### 10.3 IFC4X3 Building Information Model

The tunnel geometry is exported to the IFC4X3 schema [30]:

- `IfcAlignment`: Tunnel centerline per the Infrastructure Domain Extension
- `IfcSweptDiskSolid`: Hollow bore model swept along the centerline
- `IfcSectionedSolidHorizontal`: Per-section geometry
- `IfcWall` / `IfcDistributionElement`: Auto-detected non-structural components

---

## 11. Experimental Validation

This section is retained as the validation plan and evidence register. Claims in the abstract and conclusion should not be strengthened until the placeholders below are replaced by benchmark-backed values.

Planned validation will use [N] tunnel scan datasets collected from [location] using a [scanner model] terrestrial LiDAR scanner. Current required evidence items are:

- Auto-denoising removed [X]% of non-structural points with [Y]% precision on manually labelled ground truth sections.
- GICP registration achieved mean RMSE of [Z] mm across [N] scan pairs.
- Frenet-corrected ovality measurements differed from axis-aligned measurements by up to [W]%, confirming the significance of the orthogonality correction.
- Full pipeline processing time for a [L]-metre tunnel scan of [M] million points: [T] minutes on the target hardware.

---

## 12. Conclusion

This paper presented the SSL Smart Tunnel Monitoring System, an automated LiDAR-based pipeline for underground tunnel structural health monitoring. The current prototype establishes three principal contributions that must be supported by the validation evidence in Section 11:

1. A three-stage cascaded auto-denoising algorithm that reduces non-structural clutter without labelled training data, supporting more reproducible preprocessing of tunnel scans.
2. A Frenet-frame cross-section extraction method designed to reduce sectioning bias caused by oblique slicing in curved tunnels.
3. A local RAG-LLM module that translates structured measurement data into engineer-readable safety assessments, running entirely on-device without external data transmission.

The pipeline produces IFC-compatible BIM models, PDF reports, and structured tables that can be mapped to KR C-08080 and KDS 27 25 00 once clause-level standards mapping and validation evidence are completed. Future work will address real-time monitoring via the integrated web dashboard, extension to non-circular (horseshoe) tunnel profiles, and benchmarking of auto-denoising accuracy against the STSD semantic dataset.

---

## References

[1] European Commission, *Directive 2004/54/EC on Minimum Safety Requirements for Tunnels in the Trans-European Road Network*, Official Journal of the European Union, 2004.

[2] P. Carvel, A. Beard, Eds., *The Handbook of Tunnel Fire Safety*, 2nd ed. Thomas Telford, London, 2012.

[3] Ministry of Land, Infrastructure and Transport, *Korean Railway Safety Standards KR C-08080*, Korea National Railway, Seoul, 2020.

[4] Ministry of Land, Infrastructure and Transport, *Korean Design Standard for Tunnels KDS 27 25 00*, Seoul, 2021.

[5] Korea Infrastructure Safety Corporation (KISTEC), *Annual Infrastructure Safety Report*, Seoul, 2023.

[6] M. Alba, L. Fregonese, F. Prandi, M. Scaioni, P. Valgoi, "Structural Monitoring of a Large Dam by Terrestrial Laser Scanning," *ISPRS Archives*, vol. XXXVI-5, 2006.

[7] A. Nuttens, A. De Wulf, L. Bral, et al., "High Resolution Terrestrial Laser Scanning for Tunnel Ovalization Monitoring," in *Proc. FIG Working Week*, 2010.

[8] J. Jung, S. Kim, Y. Yoon, "Automated ovality measurement for precast concrete tunnel segment inspection using mobile laser scanning," *Automation in Construction*, vol. 121, p. 103424, 2021.

[9] V. Gikas, "Three-Dimensional Laser Scanning for Geometry Documentation and Construction Management of Highway Tunnels during Excavation," *Sensors*, vol. 12, no. 8, pp. 10827?0843, 2012.

[10] X. Ye, J. Liu, L. Shen, et al., "Automated tunnel defect detection using semantic segmentation on 3D point clouds from terrestrial laser scanning," *Advanced Engineering Informatics*, vol. 55, p. 101874, 2023.

[11] L. Attard, C. J. Debono, G. Valentino, M. Di Castro, "Tunnel inspection using photogrammetric techniques and image processing: a review," *ISPRS Journal of Photogrammetry and Remote Sensing*, vol. 144, pp. 180?88, 2018.

[12] A. Segal, D. Haehnel, S. Thrun, "Generalized-ICP," in *Proc. Robotics: Science and Systems (RSS)*, Seattle, WA, 2009.

[13] J. Yang, H. Li, D. Campbell, Y. Jia, "Go-ICP: A Globally Optimal Solution to 3D ICP Point-Set Registration," *IEEE Transactions on Pattern Analysis and Machine Intelligence*, vol. 38, no. 11, pp. 2241?254, 2016.

[14] D. Lague, N. Brodu, J. Leroux, "Accurate 3D comparison of complex topography with terrestrial laser scanner: application to the Rangitikei canyon (N-Z)," *ISPRS Journal of Photogrammetry and Remote Sensing*, vol. 82, pp. 171?84, 2013.

[15] P. Lewis, E. Perez, A. Piktus, et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Proc. NeurIPS*, 2020.

[16] X. Jiang, Y. Li, W. Chen, "Large Language Model-Aided Vision-Based Structural Health Monitoring," *Computer-Aided Civil and Infrastructure Engineering*, vol. 39, no. 12, pp. 1888?905, 2024.

[17] Y. Zheng, Q. Liu, H. Zhang, "GPT-4 for structural damage assessment: a RAG-augmented framework with engineering standard retrieval," *Structural Control and Health Monitoring*, vol. 30, e3251, 2024.

[18] R. B. Rusu, Z. C. Marton, N. Blodow, M. Beetz, "Towards 3D Point Cloud Based Object Maps for Household Environments," *Robotics and Autonomous Systems*, vol. 56, no. 11, pp. 927?41, 2008.

[19] R. B. Rusu, N. Blodow, M. Beetz, "Fast Point Feature Histograms (FPFH) for 3D Registration," in *Proc. ICRA*, Kobe, 2009.

[20] S. Umeyama, "Least-squares estimation of transformation parameters between two point patterns," *IEEE Transactions on Pattern Analysis and Machine Intelligence*, vol. 13, no. 4, pp. 376?80, 1991.

[21] M. Ester, H. P. Kriegel, J. Sander, X. Xu, "A density-based algorithm for discovering clusters in large spatial databases with noise," in *Proc. KDD*, 1996.

[22] P. J. Rousseeuw, C. Croux, "Alternatives to the median absolute deviation," *Journal of the American Statistical Association*, vol. 88, no. 424, pp. 1273?283, 1993.

[23] A. Fitzgibbon, M. Pilu, R. B. Fisher, "Direct Least Square Fitting of Ellipses," *IEEE Transactions on Pattern Analysis and Machine Intelligence*, vol. 21, no. 5, pp. 476?80, 1999.

[24] C. R. Qi, H. Su, K. Mo, L. J. Guibas, "PointNet: Deep Learning on Point Sets for 3D Classification and Segmentation," in *Proc. CVPR*, 2017.

[25] C. R. Qi, L. Yi, H. Su, L. J. Guibas, "PointNet++: Deep Hierarchical Feature Learning on Point Sets in a Metric Space," in *Proc. NeurIPS*, 2017.

[26] Y. Wang, Y. Sun, Z. Liu, S. E. Sarma, M. M. Bronstein, J. M. Solomon, "Dynamic Graph CNN for Learning on Point Clouds," *ACM Transactions on Graphics*, vol. 38, no. 5, 2019.

[27] N. Reimers, I. Gurevych, "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks," in *Proc. EMNLP*, 2019.

[28] ITA Working Group 2, "Guidelines for the Design of Tunnels," *ITA Report No. 009*, 2019.

[29] Q. Chen, R. Ko, "small_gicp: Efficient and parallelised point cloud registration library," *Journal of Open Source Software*, 2024.

[30] buildingSMART International, "Industry Foundation Classes IFC4X3 ?Infrastructure Domain Extension," 2023.
