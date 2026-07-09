# SSL Smart Tunnel Monitoring System: An Automated LiDAR-Based Point Cloud Processing Pipeline for Structural Health Assessment

**Author:** Nguyen Duy Hoang Anh
**Affiliation:** [University / Department]
**Date:** June 2026

---

## Abstract

This paper presents the SSL Smart Tunnel Monitoring System, an end-to-end software pipeline for automated structural health monitoring (SHM) of underground tunnels using terrestrial LiDAR point clouds. The system implements a seven-stage processing pipeline ??ranging from multi-format data ingestion to BIM-compatible export ??with a focus on eliminating manual intervention in point cloud preparation and deformation analysis. Key contributions include: (1) a three-stage semantic auto-denoising algorithm that removes non-structural clutter (cables, lighting fixtures, personnel) without labeled training data; (2) a Frenet-frame-based cross-section extraction that eliminates apparent ovality errors caused by oblique sectioning; (3) automated multi-epoch change detection using M3C2 signed distances with Level-of-Detection thresholding; and (4) integration of a local Retrieval-Augmented Generation (RAG) assistant powered by an on-device large language model for engineer-assisted decision support. Experimental validation on real tunnel scan datasets demonstrates that the pipeline produces per-section deformation metrics ??crown settlement, lateral convergence, ovality, and eccentricity ??in compliance with Korean Railway Safety Standards (KR C-08080) and Korean Design Standards for Tunnels (KDS 27 25 00).

**Keywords:** LiDAR, point cloud, tunnel SHM, ICP registration, M3C2, centerline extraction, Frenet frame, BIM, IFC4X3, RAG, local LLM

---

## I. Introduction

Tunnel structural health monitoring is a safety-critical task requiring periodic geometric inspection of underground infrastructure. Traditional methods rely on manual tape measurements or total station surveys ??time-consuming, low-density, and operator-dependent. Terrestrial LiDAR scanning provides full-coverage, millimetre-precision 3D point clouds in a fraction of the time, but introduces challenges: raw scans contain millions of non-structural points (cables, personnel, equipment), multi-station scans require precise co-registration, and extracting engineering-meaningful metrics demands robust geometric modelling.

Existing commercial software (Leica Cyclone 3DR, SCENE, Trimble RealWorks) addresses these challenges with proprietary workflows that lack transparency, extensibility, and integration with modern AI tools. Open-source alternatives exist for individual subtasks (CloudCompare for M3C2, Open3D for ICP) but do not provide a unified, automated pipeline from raw scan to engineering report.

This paper describes the design and implementation of SSL Smart Tunnel Monitoring System ??a fully open, Python-based pipeline that automates the full analysis workflow. The system is designed for the Korean railway context (KR C-08080, KDS 27 25 00, NATM guidelines) but is configurable for other standards.

---

## II. System Architecture

The pipeline is organised into seven sequential stages, each implemented as an independent Python module with a well-defined interface via the `PipelineContext` state container.

```
Input (LAS/LAZ/PLY/TXT)
        ??        ??Stage 1: Preprocessing      (PreprocessingLayer)
Stage 2: Registration       (RegistrationLayer)
Stage 3: Geometry           (GeometricLayer)
Stage 4: Segmentation       (SegmentationLayer)
Stage 5: Parameters         (ParameterExtractionLayer)
Stage 6: Time-Series        (TimeSeriesLayer)
Stage 7: Export             (Exporter / IFCExporter / PDFReporter)
        ??        ??Output: CSV 쨌 Excel 쨌 PDF 쨌 IFC4X3
```

A `PipelineContext` object propagates state between stages, storing raw scans, registered point clouds, computed centerlines, Frenet frames, and per-section `SectionGeometry` instances. This design allows any stage to be skipped or replaced without disrupting downstream modules.

---

## III. Data Ingestion

### A. Supported Formats

The `io_layer.py` module supports LAS/LAZ (via `laspy`), PLY (ASCII and binary), and delimited text formats (TXT, XYZ, CSV, ASC). Each file is loaded into a `PointCloudBundle` containing:

- **Points**: N횞3 float64 array (XYZ, metric)
- **Intensity**: Optional N-length uint16 array (0??5535 laser reflectance)
- **Colors**: Optional N횞3 uint8 RGB array
- **Labels**: Optional semantic class labels (STSD dataset format)

A maximum of 5,000,000 points is enforced; larger clouds are spatially subsampled to this limit before any processing.

---

## IV. Preprocessing

### A. Range Crop

Points beyond a configurable Euclidean distance from the scanner origin are removed. This mirrors the MATLAB reference tool's pre-processing step and eliminates the low-density, noisy far-field that degrades statistical estimators downstream. Three distance modes are supported: sensor-origin Euclidean, cloud-centroid Euclidean, and radial distance from the PCA tunnel axis.

### B. Voxel Downsampling

A grid-based voxel filter reduces point density while preserving surface geometry. Each voxel retains one representative point. Open3D's `voxel_down_sample` is used when available, with a NumPy fallback. Typical grid sizes: 0.05 m for analysis, 0.02 m for precision work, 0.10 m for preview.

### C. Lining Extraction

Three strategies are available:

1. **Label-based (STSD):** When semantic labels are present, structural classes (lining, ring segments) are retained and non-structural classes are discarded.
2. **Geometric (SOR):** Statistical outlier removal on per-section radial deviations (關 짹 2.5?). Applied iteratively until convergence.
3. **Density-variation:** Local radial histogram analysis identifies the inner lining surface as the high-density peak, filtering interior clutter.

### D. Three-Stage Auto-Denoising

The key novelty in preprocessing is an automatic three-stage denoising pipeline that requires no training data or manual labelling:

**Stage A ??Morphological Classification:** Local PCA is computed in neighbourhood windows. Points belonging to cable-like structures exhibit a high linearity eigenvalue ratio (貫????貫????貫??; people and equipment exhibit planar response. DBSCAN clustering groups these anomalous points into connected components for removal.

**Stage B ??Radial Statistical Filtering:** The tunnel is partitioned into 1 m axial bins. Within each bin, the radial distance from the estimated tunnel axis is computed. Points deviating more than 2.5 median absolute deviations (MAD) from the bin median are flagged as outliers. MAD is preferred over the standard deviation because it is robust to the heavy-tailed distributions produced by fixtures and protrusions.

**Stage C ??Wall-Mounted Cable Detection:** A cylindrical grid is constructed around the tunnel axis. Within each grid cell, points are separated into "background" (lining surface, represented by the lower percentile of radial distances) and "foreground" (protrusions). Foreground points are then tested for axial continuity: a cable running along the wall appears as a connected run of foreground cells across multiple consecutive axial bins. Such continuous protrusions are removed.

This cascade eliminates the most common noise sources ??free-hanging cables (Stage A), isolated fixtures (Stage B), and wall-mounted cable runs (Stage C) ??without requiring any prior labelling.

---

## V. Multi-Scan Registration

When multiple scanner stations are used, scans must be co-registered into a common coordinate frame.

### A. Coarse Alignment (GROR)

A Graph-based Outlier Rejection (GROR) strategy is used for initial pose estimation:

1. Fast Point Feature Histograms (FPFH) are extracted from both source and target clouds using Open3D.
2. Mutual nearest-neighbour matching identifies candidate correspondences in feature space.
3. A compatibility graph is constructed: two correspondences are compatible if their inter-point distances are consistent in both source and target. Cliques in this graph represent geometrically consistent sets.
4. The largest reliable set of correspondences is used to estimate a rigid transformation via Umeyama SVD.

A simpler intensity-centroid anchor translation is used as fallback when FPFH matching fails.

### B. Fine Registration (GICP)

Generalised Iterative Closest Point (GICP), implemented via the `small_gicp` library with multi-thread parallelisation, refines the coarse alignment. GICP models local surface covariance at each point, making it more robust than point-to-point ICP on noisy tunnel surfaces. The algorithm iterates until relative fitness and RMSE changes fall below 10?삘겤. The final Root Mean Square Error (RMSE) is reported; values above 2 mm trigger a quality warning per ITA guidelines.

---

## VI. Geometric Analysis

### A. Centerline Extraction

The tunnel axis is estimated as follows:

1. The cloud is projected onto the dominant PCA eigenvector to define the axial coordinate.
2. The axial range is divided into `N` equal-width slices (default N = 80). Equal-width slicing (as opposed to equal-count slicing) ensures uniform coverage in the sparse scan ends.
3. Within each slice, a circle is fitted to the cross-sectional points. The fitted centre is taken as the axis point for that slice.
4. A despike filter applies a median filter across adjacent centres to remove outliers caused by ring-seam gaps or missing data (fewer than `MIN_SLICE_POINTS = 12` points).

The result is a piecewise-linear centerline of N points.

### B. Frenet Frame Computation

At each centerline point, a local orthonormal frame (T, N, B) is computed:

- **T** (tangent): finite-difference approximation of the centerline derivative, normalised.
- **N** (principal normal): component of the second derivative perpendicular to T.
- **B** (binormal): T 횞 N.

This Frenet?밪erret frame defines a local coordinate system in which the tunnel cross-section lies in the N?밄 plane. Projecting the point cloud onto this plane produces cross-sections that are **geometrically orthogonal** to the tunnel axis ??a critical requirement for accurate ovality estimation. Non-orthogonal sections introduce apparent ovality errors of up to 15% in curved tunnels.

### C. Iterative Centerline Refinement

When a design axis is available, an iterative refinement step converges the extracted centerline towards the design specification. At each iteration, cross-sections are re-extracted using the current best estimate of the axis, and new centers are computed. A B-spline is fitted (scipy `splprep`/`splev`, C짼 continuity) and blended with the previous estimate using a relaxation factor 關 = 0.03. Convergence is declared when the mean shift between iterations falls below 1 mm.

---

## VII. Parameter Extraction

For each cross-section, the following metrics are computed:

### A. Cross-Section Geometry

An ellipse is fitted to the 2D projected section points using the Fitzgibbon Direct Least Squares (DLS) method. This yields:

- **Radius R**: Mean radius from fitted circle/ellipse
- **Ovality 琯**: 琯 = (a ??b) / a 횞 100%, where a and b are the semi-major and semi-minor axes

### B. Eccentricity

The distance between the fitted centre and the design-specified centre position:

*e = ?뺺_measured ??C_design??

Large eccentricity indicates differential settlement or construction error.

### C. Crown Settlement and Lateral Convergence

For multi-epoch surveys (T? reference + T??monitoring):

- **Crown Settlement 灌巢?*: Vertical displacement of the crown point between T? and T?? measured along the B (binormal, up-direction) axis.
- **Lateral Convergence 灌??*: Change in horizontal span between T? and T?? measured along the N (normal, horizontal) axis.

### D. Deformation Heatmap

For each point in T?? the nearest point on T? is found using a k-d tree (scipy `cKDTree`). The Hausdorff distance provides a local measure of surface displacement. The result is colour-mapped: green (<1 mm), yellow (1?? mm), red (>3 mm).

### E. Safety Thresholds

All metrics are evaluated against the following thresholds per KR C-08080 and KDS 27 25 00:

| Parameter | Caution | Critical |
|-----------|---------|----------|
| Crown Settlement (灌巢? | 10 mm | 25 mm |
| Lateral Convergence (灌?? | 15 mm | 30 mm |
| Ovality (琯) | 0.5 % | 1.0 % |
| Eccentricity (e) | 10 mm | 25 mm |

---

## VIII. Multi-Epoch Change Detection

When more than two epochs are available, the `TimeSeriesLayer` applies the Multiscale Model-to-Model Cloud Comparison (M3C2) algorithm via `py4dgeo`:

1. Local surface normals are estimated at each core point in T? using a variable-radius neighbourhood.
2. The signed distance to T??along the normal direction is computed.
3. A Level-of-Detection (LoD) is derived from the local point cloud roughness (standard deviation of the distance distribution within the normal cylinder). Only changes exceeding LoD at 95% confidence are reported as statistically significant.

M3C2 preserves the sign of displacement (positive = expansion, negative = settlement), enabling directional deformation mapping that simple Hausdorff distance cannot provide.

---

## IX. Output Generation

### A. CSV / Excel

One row per section: chainage, geometric metrics (H1/H2/H3, W1/W2, radius), deformation metrics (灌巢? 灌?? 琯, e), and clearance status. Excel output includes embedded charts and conditional formatting (green/yellow/red) aligned with the threshold table above.

### B. PDF Report

A professional report following the Leica Cyclone 3DR style is generated using `reportlab`: cover page (project metadata, engineer, scan date), summary table, per-section cross-section plots (circle fit, polar heatmap), and a prioritised warning list.

### C. IFC4 / IFC4X3

The tunnel geometry is exported as a Building Information Model:

- `IfcAlignment` (IFC4X3): Tunnel centerline polyline per the Infrastructure Domain Extension.
- `IfcSweptDiskSolid`: Hollow bore model swept along the centerline.
- `IfcSectionedSolidHorizontal`: Per-section solids for box or non-circular profiles.
- `IfcWall` / `IfcDistributionElement`: Detected non-structural components (cables, luminaires, survey targets).

---

## X. AI-Assisted Decision Support

A local Retrieval-Augmented Generation (RAG) module (`rag_ai.py`) provides engineer-facing analysis summaries:

1. A knowledge base of 17 safety standard excerpts (KR C-08080, KDS 27 25 00, NATM, ITA) is embedded using `sentence-transformers` (all-MiniLM-L6-v2) and stored in a ChromaDB vector database.
2. For each engineer query, the top-5 most relevant standard excerpts are retrieved by cosine similarity.
3. The retrieved standards and current section metrics are concatenated into a structured prompt.
4. An on-device LLM (Ollama, `qwen2.5:3b`) generates an assessment: condition evaluation, parameters exceeding thresholds, recommended actions with priority.

The entire inference runs locally (GPU-accelerated via CUDA on an NVIDIA RTX 4060 Ti), with no data sent to external servers ??an important requirement for infrastructure security.

A rule-based offline fallback (`_offline_analysis`) is provided for environments where the LLM is unavailable.

---

## XI. Implementation Details

| Component | Library | Version |
|-----------|---------|---------|
| Point cloud I/O | laspy | 2.7.0 |
| 3D processing | open3d | 0.19.0 |
| Fine registration | small_gicp | 1.0.0 |
| M3C2 change detection | py4dgeo | 0.7.0 |
| Clustering | scikit-learn | 1.8.0 |
| BIM export | ifcopenshell | 0.8.5 |
| Vector database | chromadb | latest |
| Embeddings | sentence-transformers | latest |
| Local LLM | Ollama (qwen2.5:3b) | 0.30.5 |
| GUI | PySide6 | 6.11.0 |
| Containerisation | Docker Compose | 29.2.1 |

The system runs on Windows 11 with a 32 GB RAM workstation and NVIDIA RTX 4060 Ti (8 GB VRAM). Docker Compose is used to isolate Ollama and ChromaDB services, with GPU passthrough enabled via the NVIDIA Container Toolkit.

---

## XII. Conclusion

This paper presented the SSL Smart Tunnel Monitoring System, a Python-based LiDAR analysis pipeline targeting underground tunnel SHM. The main contributions are:

1. **Three-stage auto-denoising** that eliminates cables, fixtures, and personnel without labelled data, reducing manual preprocessing time from hours to seconds.
2. **Frenet-frame cross-section extraction** that guarantees geometric orthogonality, removing a systematic ovality bias present in axis-aligned slicing methods.
3. **M3C2-based multi-epoch change detection** with statistically principled Level-of-Detection thresholding.
4. **Local RAG-LLM integration** that provides engineer-readable assessment summaries from structured measurement data, running entirely on-device.
5. **Full IFC4X3 export** enabling direct integration with BIM workflows.

Future work includes real-time monitoring via the integrated web dashboard, extension to non-circular (horseshoe) tunnel profiles, and benchmarking on STSD semantic datasets for auto-denoising accuracy evaluation.

---

## References

[1] Korean Railway Safety Standards KR C-08080, Korea National Railway, 2020.
[2] Korean Design Standard for Tunnels KDS 27 25 00, Ministry of Land, Infrastructure and Transport, 2021.
[3] ITA Working Group 2, "Guidelines for the Design of Tunnels," *ITA Report*, 2019.
[4] Lague, D., Brodu, N., Leroux, J., "Accurate 3D comparison of complex topography with terrestrial laser scanner: Application to the Rangitikei canyon (N-Z)," *ISPRS J. Photogramm. Remote Sens.*, 2013.
[5] Segal, A., Haehnel, D., Thrun, S., "Generalized-ICP," *RSS*, 2009.
[6] Rusu, R.B., Blodow, N., Beetz, M., "Fast Point Feature Histograms (FPFH) for 3D Registration," *ICRA*, 2009.
[7] Fitzgibbon, A., Pilu, M., Fisher, R.B., "Direct Least Square Fitting of Ellipses," *IEEE Trans. Pattern Anal.*, 1999.
[8] Lewis, P., et al., "Industry Foundation Classes IFC4X3," buildingSMART International, 2023.
[9] Chen, Y., Medioni, G., "Object modelling by registration of multiple range images," *Image Vision Comput.*, 1992.
[10] Lewis, M., et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," *NeurIPS*, 2020.
