# The SSL Smart Tunnel Monitoring System: An Automated LiDAR-Based Point Cloud Processing Pipeline for Structural Health Monitoring of Underground Tunnels

**Keywords:** LiDAR point cloud; tunnel structural health monitoring; automatic denoising; Frenet frame; M3C2 change detection; IFC4X3; retrieval-augmented generation

## Abstract

Automated structural health monitoring (SHM) of underground tunnels using terrestrial LiDAR remains challenging due to the presence of non-structural clutter (cables, lighting fixtures, and personnel) that contaminates raw point clouds and introduces systematic errors in geometric analysis. Conventional workflows require extensive manual preprocessing, limiting scalability to large tunnel networks. This study proposes the SSL Smart Tunnel Monitoring System, an end-to-end Python-based pipeline that automates the full analysis chain from raw LiDAR ingestion to report generation. The proposed system introduces three principal contributions: (1) a three-stage cascaded auto-denoising algorithm that removes 82.6% of injected clutter while retaining 99.99% of tunnel lining points without labelled training data; (2) a Frenet-frame-based cross-section extraction method that reduces the systematic ovality bias present in axis-aligned slicing approaches; and (3) an end-to-end inspection pipeline with a local Retrieval-Augmented Generation (RAG) module that drafts preliminary engineering summaries on-device without transmitting data to external servers. Validation on synthetic ground-truth datasets demonstrates that the section extraction recovers a median radius within 0.0005% of the design value on reference geometry, and the clearance detection module achieves 100% precision and recall against labelled intrusion points. The pipeline produces IFC4X3-compatible Building Information Models, professional PDF reports, and structured data outputs informed by Korean railway and tunnel design standards (KR C-08080, KDS 27 25 00).

## 1. Introduction

Underground tunnels are critical components of transportation networks, yet they pose unique challenges for inspection and maintenance. Major tunnel fire incidents in Europe, including the Mont Blanc (1999, 39 fatalities) and Tauern (1999, 12 fatalities) disasters, exposed fundamental weaknesses in tunnel safety management and accelerated regulatory reform across the continent [1,2]. While these events primarily concerned fire safety, they drew attention to the broader problem of monitoring the structural condition of aging tunnel assets.

The European Union subsequently adopted Directive 2004/54/EC, establishing minimum safety requirements for road tunnels exceeding 500 m in the Trans-European network [1]. Korean railway and tunnel standards (KR C-08080, KDS 27 25 00) specify survey intervals of not less than six months for tunnels in deformation-sensitive ground [3,4]. A single unplanned closure of a metropolitan rail tunnel in Seoul results in estimated direct losses of USD 1–3 million per day [5]. These regulatory and economic pressures motivate the development of automated geometric monitoring methods that can scale to large tunnel networks.

Terrestrial LiDAR scanning has become widely adopted for tunnel structural health monitoring (SHM), capturing dense full-section 3D point clouds in a single survey pass with minimal disruption to traffic [6,7]. Building on this capability, researchers have developed automated methods for specific inspection subtasks. Jung et al. [8] extracted ovality metrics from mobile laser scanning data using iterative circle fitting, demonstrating the feasibility of automated geometric assessment for precast tunnel segments. Gikas [9] extended this approach to long-term convergence monitoring by applying least-squares cylinder fitting to successive scans during highway tunnel excavation. Ye et al. [10] combined 3D semantic segmentation with point cloud processing to detect surface cracks at millimetre scale, and Attard et al. [11] benchmarked five commercial inspection packages, reporting significant variability depending on preprocessing. The pattern is consistent: each tool addresses one piece of the inspection problem. Yet these methods assume clean input data. In practice, raw tunnel scans contain 5–30% non-structural points from cables, lighting fixtures, and personnel. Standard statistical outlier removal [17] targets random Gaussian noise and fails against the structured, elongated geometry of wall-mounted cable runs.

A related limitation concerns cross-section extraction in curved tunnels. Conventional approaches slice the point cloud perpendicular to a global coordinate axis, which can introduce oblique cuts that overestimate ovality in curved alignments [18]. Slicing perpendicular to the local tunnel axis via Frenet frames addresses this bias, a technique established in pipeline inspection [19] but not yet applied in open-source tunnel analysis tools.

Concurrent advances in point cloud registration have enabled precise multi-epoch comparison. Segal et al. [12] introduced the Generalised Iterative Closest Point (GICP) algorithm, modelling local surface geometry as Gaussian distributions to achieve tighter alignment than standard ICP on planar tunnel walls. Yang et al. [13] further improved convergence with Go-ICP, a globally optimal formulation that reduces sensitivity to initialisation. These registration methods underpin the Multiscale Model to Model Cloud Comparison (M3C2) algorithm of Lague et al. [14], which derives a Level-of-Detection (LoD) threshold at 95% confidence from local point cloud roughness, formalising multi-epoch change detection. However, translating M3C2 displacement maps into prioritised maintenance actions still demands manual review by a qualified engineer for every report cycle. Recent work on Retrieval-Augmented Generation (RAG) [15] has shown that grounding large language model (LLM) outputs in retrieved domain documents reduces hallucination in technical contexts [16], but no system has applied this approach to draft preliminary tunnel inspection summaries.

This study proposes the SSL Smart Tunnel Monitoring System to address all three gaps within a single, standards-informed pipeline. The system ingests raw multi-station scans in common formats (LAS, LAZ, PLY, TXT) and applies a cascaded denoising algorithm to separate structural lining from clutter. Multi-scan registration is performed through a coarse-to-fine fallback chain combining target-based alignment, feature matching, and Trimmed ICP. Cross-sections are extracted via gravity-anchored Frenet frames derived from cubic B-spline centerlines, and deformation metrics are computed for each section. A local RAG module, powered by an on-device LLM, drafts preliminary engineering summaries from the extracted metrics without transmitting data to external servers.

The principal contributions of this study are as follows:

1. We develop a three-stage cascaded auto-denoising algorithm combining morphological PCA-based classification, radial MAD statistical filtering, and cylindrical-grid wall-cable detection. The algorithm requires no labelled training data and includes a safety guard that prevents over-removal. On synthetic ground-truth data, it achieves a noise recall of 0.826 while retaining 99.99% of tunnel lining points. Algorithm parameters and implementation details are presented in Section 4.

2. We introduce a Frenet-frame cross-section extraction method that uses cubic B-spline centerline fitting, gravity-anchored local frames, and adaptive slice thickness to ensure geometric orthogonality to the tunnel axis. On reference geometry, the method recovers a median radius within 0.0005% of the design value, substantially reducing the ovality bias of world-frame slicing. The full formulation is given in Section 6.

3. We present an end-to-end open-source inspection pipeline that produces IFC4X3-compatible BIM models, professional PDF inspection reports, and structured CSV/Excel workbooks from raw LiDAR input. A local RAG module drafts preliminary engineering summaries by retrieving relevant standard excerpts and falls back to deterministic rule-based assessment when the LLM is unavailable. The clearance detection module achieves 100% precision and recall against labelled intrusion points on synthetic test cases.

The remainder of this paper is organised as follows. Section 2 surveys related work. Section 3 describes the system architecture. Sections 4 through 8 detail the denoising cascade, multi-scan registration, Frenet-frame geometric analysis, parameter extraction, and multi-epoch change detection, respectively. Section 9 covers the RAG engineering assistant. Section 10 describes output generation. Section 11 reports experimental validation. Section 12 concludes with a summary and future directions.


## 2. Related Work

Automated tunnel monitoring draws on four research threads: LiDAR-based geometric inspection, point cloud denoising, multi-epoch registration, and AI-assisted structural assessment. Each thread has matured independently. The gap this study addresses lies in their integration.

### 2.1 LiDAR-based tunnel inspection

Terrestrial laser scanning records dense full-section point clouds in a single survey pass, and this capability reshaped how tunnel geometry is documented [6,7]. Early work focused on isolated metrics. Jung et al. [8] fitted circles iteratively to mobile laser scans of precast segments and recovered ovality at the segment scale, showing that geometric defects could be quantified without manual cross-section drawing. Gikas [9] applied least-squares cylinder fitting to successive scans during highway tunnel excavation, tracking convergence over construction stages. Ye et al. [10] coupled 3D semantic segmentation with point cloud processing to localise surface cracks at millimetre scale, and Attard et al. [11] benchmarked five commercial inspection packages, reporting that results varied substantially with the preprocessing each package applied. Fekete et al. [18] documented how oblique slicing in drill-and-blast tunnels distorts the apparent cross-section when the tunnel curves.

The pattern is consistent. Each tool solves one piece of the inspection problem, and each assumes the input cloud already represents only the tunnel lining. That assumption rarely holds in operational tunnels.

### 2.2 Point cloud denoising

The dominant cleaning method in the point cloud literature is statistical outlier removal, which flags points whose mean neighbour distance exceeds a global threshold [17]. The method targets random, Gaussian-distributed noise and isolated stray returns. Cable runs, conduit, and lighting fixtures in a tunnel are neither random nor isolated: they are elongated, locally dense structures mounted against the lining. Geometric classifiers based on local principal component analysis can separate linear from planar neighbourhoods, but published pipelines apply them to terrain or building facades rather than to the closed cylindrical geometry of a tunnel, where the lining itself is a curved surface that confounds a single global threshold. The result is that clutter survives cleaning or, when thresholds are tightened, structural points are removed with it.

### 2.3 Registration for multi-epoch comparison

Comparing scans across epochs requires alignment to a common frame. The Iterative Closest Point family is standard, and Segal et al. [12] generalised it by modelling local surface patches as Gaussian distributions, which improves alignment on the planar walls typical of tunnels. Yang et al. [13] removed the dependence on a good initial guess with a globally optimal branch-and-bound formulation. Feature-based coarse alignment using Fast Point Feature Histograms [22] and graph-based outlier rejection [23] now provides reliable initialisation, and voxelised GICP variants [24] reach sub-millimetre accuracy at interactive speed. These advances feed directly into change detection: the Multiscale Model to Model Cloud Comparison (M3C2) algorithm of Lague et al. [14] derives a Level of Detection from local roughness and registration uncertainty, separating real deformation from noise at a stated confidence level. What remains open is the engineering chain after the displacement map is produced. Registration and M3C2 are well-characterised in isolation, yet packaging them into a repeatable tunnel workflow that an inspector can run end to end is largely left to bespoke scripts.

### 2.4 AI-assisted structural assessment

Translating a displacement map into a maintenance decision still requires a qualified engineer to read every report. Retrieval-Augmented Generation [15] grounds large language model output in retrieved domain documents, and Jiang et al. [16] showed that this grounding reduces hallucination when language models support vision-based structural health monitoring. These systems are typically cloud-hosted, which conflicts with the data-handling constraints of critical infrastructure, and none has been specialised for tunnel inspection metrics. A local, standards-grounded assistant that drafts a preliminary summary while keeping survey data on-device has not been demonstrated.

### 2.5 Summary

Table 1 positions the proposed system against representative prior work. Existing methods each cover part of the chain from raw scan to engineering report; none covers the full chain with automated denoising of structured clutter, Frenet-frame cross-section extraction, and an on-device assessment assistant in a single open pipeline.

**Table 1.** Capability comparison with representative prior work (●: provided, ◐: partial, ○: not addressed).

| Capability | Jung [8] | Gikas [9] | Ye [10] | Commercial [11] | This study |
|---|---|---|---|---|---|
| Automated clutter denoising | ○ | ○ | ◐ | ◐ | ● |
| Curvature-correct sectioning | ○ | ◐ | ○ | ○ | ● |
| Multi-epoch M3C2 detection | ○ | ◐ | ○ | ◐ | ● |
| BIM (IFC) output | ○ | ○ | ○ | ◐ | ● |
| On-device AI assistant | ○ | ○ | ○ | ○ | ● |
| Open source | ○ | ○ | ○ | ○ | ● |
## 3. System Architecture

The SSL Smart Tunnel Monitoring System is a Python package organised as a layered pipeline. Raw scans enter at one end; structured data, BIM models, and reports leave at the other. A single shared state object, the `PipelineContext`, carries data between layers, so each stage reads the previous stage's output and writes its own without global variables or file round-trips.

### 3.1 Pipeline overview

Figure 1 shows the processing chain. The headless orchestrator `run_pipeline` executes the stages in fixed order: ingestion, range crop, voxel downsampling, denoising, centerline and Frenet-frame extraction, profile detection, cross-section computation, parameter extraction, and output generation. The same layers back the interactive desktop application, which exposes the chain as seven user-facing steps. Decoupling the orchestrator from the user interface lets the identical analysis run in batch mode for benchmarking and in interactive mode for inspection.

**Figure 1.** End-to-end pipeline. Ingestion → preprocessing (range crop, voxel, denoise) → registration → centerline and Frenet frames → section extraction → parameter extraction → multi-epoch change detection → output (CSV/Excel, PDF, IFC) and RAG assistant. The `PipelineContext` is the shared carrier across all stages.

### 3.2 The PipelineContext

All intermediate results are fields of one dataclass, defined in `models.py`. The principal fields are the input scans, the registered point array, the fitted centerline and its smoothed form, the per-section Frenet frames, the list of section geometries, and the dictionary of global parameters. Table 2 summarises the carrier. Because every layer mutates the same object, the pipeline state is fully inspectable at any breakpoint, which simplified both debugging and the construction of the validation harness.

**Table 2.** Principal `PipelineContext` fields (`models.py`).

| Field | Type | Produced by | Meaning |
|---|---|---|---|
| `scans` | list of point cloud bundles | ingestion | input clouds (one per station/epoch) |
| `normalized_points` | N×3 array | preprocessing | cropped, downsampled, denoised cloud |
| `registered_points` | N×3 array | registration | cloud aligned to the reference frame |
| `centerline`, `centerline_smooth` | M×3 arrays | geometry | B-spline tunnel axis |
| `frenet_frames` | list of {T, N, B} | geometry | orthonormal frame per section |
| `sections` | list of section geometries | parameter extraction | per-chainage measurements |
| `parameters` | dict | parameter extraction | global summary metrics |

### 3.3 Data ingestion

The ingestion layer (`io_layer.py`) reads the formats common in tunnel survey practice. LAS and LAZ files are parsed through the laspy stack; PLY through a dedicated reader; and the plain-text family (TXT, XYZ, PTS, CSV, ASC) through a column reader that preserves coordinates, optional normals, intensity, and per-point labels when present. Each file becomes a point cloud bundle, the unit the rest of the pipeline consumes. Support for labelled text input matters for validation: it lets synthetic ground-truth clouds carry per-point class labels through the same path as field data.

### 3.4 Module organisation

The package separates concerns by file, which keeps each algorithm independently testable. Table 3 lists the core modules referenced in the following sections. The geometric and parameter layers depend only on NumPy and SciPy; the registration and change-detection layers use optional accelerated backends (small_gicp, Open3D, py4dgeo) with pure-Python fallbacks; and the assistant and export layers are optional, so the core geometric analysis runs with a minimal dependency set.

**Table 3.** Core modules of the `tunnel_analysis` package.

| Module | Responsibility | Paper section |
|---|---|---|
| `io_layer.py` | scan ingestion (LAS/LAZ/PLY/TXT) | 3.3 |
| `preprocessing.py` | range crop, voxel, three-stage denoising | 4 |
| `registration.py` | target/feature/ICP alignment | 5 |
| `geometry.py` | B-spline centerline, Frenet frames, sectioning | 6 |
| `parameters.py` | crown, convergence, ovality, eccentricity, clearance | 7 |
| `timeseries.py` | M3C2 change detection, spatiotemporal trends | 8 |
| `section_warnings.py` | per-section severity classification | 8 |
| `rag_ai.py` | on-device RAG assistant | 9 |
| `ifc_exporter.py`, `pdf_reporter.py` | IFC, PDF, CSV/Excel output | 10 |
| `batch.py` | headless orchestrator (`run_pipeline`) | 3.1 |
## 4. Data Preprocessing and Three-Stage Denoising

Raw tunnel scans contain 5–30% non-structural points. The preprocessing layer (`preprocessing.py`) reduces the cloud to clean lining points through a fixed sequence: range crop, voxel downsampling, and a three-stage cascaded denoising algorithm. The cascade requires no labelled training data and is the first principal contribution of this study.

### 4.1 Range crop and downsampling

Ingestion is followed by a range crop that discards returns beyond a working radius, with a default limit of 20 m. The function `range_crop` supports three distance references: Euclidean distance from the sensor origin, distance from the cloud centroid, and radial distance from the principal axis of the cloud. The axis mode suits the tube geometry of a tunnel, where distant returns from adjacent chambers or portal openings are far in radius but not in axial position. Voxel downsampling (`voxel_downsample`, default leaf size 0.05 m) then enforces uniform spacing, which both bounds memory for large surveys and stabilises the neighbourhood statistics used by the cascade.

### 4.2 Stage 1 — morphological classification

The first stage, `semantic_noise_removal`, classifies each point from the geometry of its local neighbourhood. For every point the *k* = 20 nearest neighbours are gathered and their covariance is decomposed into eigenvalues *λ*₁ ≥ *λ*₂ ≥ *λ*₃ ≥ 0. Two normalised shape descriptors follow:

$$ L = \frac{\lambda_1 - \lambda_2}{\lambda_1 + \lambda_2 + \lambda_3}, \qquad S = \frac{\lambda_3}{\lambda_1 + \lambda_2 + \lambda_3} \tag{1} $$

where *L* is linearity and *S* is sphericity. Cables and conduit produce highly linear neighbourhoods, so points with *L* ≥ 0.30 are flagged as cable clutter; an additional ratio test *λ*₂ ⁄ *λ*₁ < 0.15 rejects elongated lining patches that would otherwise be misclassified. Lighting fixtures and other compact objects produce near-spherical neighbourhoods, so points with *S* ≥ 0.12 and a local extent below 0.20 m are flagged as fixture clutter. Personnel are removed by clustering planar points (planarity above 0.4) with DBSCAN [26] (*ε* = 0.15 m, minimum 5 samples) and rejecting clusters whose height falls in 1.2–2.2 m and whose width is below 0.8 m, the envelope of a standing person.

### 4.3 Stage 2 — radial robust statistics

The lining of a tunnel section forms a tight band of radii about a central value. The second stage exploits this by working in the cylindrical frame of the dominant principal axis, dividing the cloud into 0.5 m axial slices and, within each slice, comparing every point's radius *r* to the slice median *R*~med~. A robust scatter estimate uses the median absolute deviation:

$$ \tau = k_\sigma \cdot 1.4826 \cdot \mathrm{MAD}(r), \qquad k_\sigma = 2.5 \tag{2} $$

The constant 1.4826 converts the MAD to a standard-deviation-equivalent under a Gaussian model, and *k*~σ~ sets the acceptance width. A point is retained when

$$ |r - R_\text{med}| \le \tau \quad \text{and} \quad r \ge 0.40\,R_\text{med} \tag{3} $$

The first condition rejects radial outliers; the second removes interior returns, such as equipment near the tunnel axis, that lie far inside the lining band. Operating per slice keeps the test local, so it adapts to a tunnel whose radius changes along its length.

### 4.4 Stage 3 — wall-mounted protrusion detection

Cable trays run continuously along the wall and present a linear, planar signature that can survive the first two stages. The third stage, `_detect_wall_protrusion`, builds a cylindrical occupancy grid of 60 axial by 180 angular cells and estimates the local wall radius as the 90th percentile of point radii within each angular column. Points protruding inward by more than 0.05 m relative to this envelope are candidates for removal. A protrusion is confirmed as a fixture only when it persists across at least three axial cells, the axial-continuity test that distinguishes a continuous cable run from incidental lining roughness.

### 4.5 Safety guard

Each classifier could, on atypical geometry, flag a large fraction of structural points. A safety guard caps any single class at 30% of the cloud: if a gate would remove more than this fraction, it is disabled and a warning is recorded rather than risking destruction of the lining. This guard makes the cascade safe to run unattended, which is a precondition for batch processing of large tunnel networks.

The three stages run in the order above inside `auto_denoise`. On the labelled synthetic case (Section 11), the cascade removed 82.6% of injected clutter (noise recall 0.826) while retaining 99.99% of tunnel lining points, with precision 1.00 and F1 0.90.
## 5. Multi-Scan Registration

Multi-station and multi-epoch surveys produce clouds in different coordinate frames. Registration (`registration.py`) aligns them to a common reference through a coarse-to-fine fallback chain that selects the strongest available method for the data at hand. The chain is implemented in `register_epochs`.

### 5.1 Method selection

The pipeline prefers the most constrained method the scene supports and falls back when its preconditions are not met. When survey targets are detected, a target-based rigid transform is used directly. Without targets, the pipeline computes a feature-based coarse alignment, refines it with generalised ICP, and validates the result against a divergence guard. The final transform is the one with the lowest root-mean-square error among the as-is, coarse, and refined candidates, which prevents a failed refinement from degrading an already adequate alignment.

### 5.2 Target-based alignment

When at least three targets are matched between clouds, their centres define a rigid transform recovered in closed form by the Horn singular-value-decomposition solution, with correspondences accepted within a 2.0 m gate. This path is exact up to target-centroiding error and is preferred wherever targets exist, as is standard in surveying practice.

### 5.3 Feature-based coarse alignment

Without targets, the clouds are downsampled to a working resolution derived from their extent (cloud span divided by 600, clipped to 0.02–0.12 m) and described by Fast Point Feature Histograms [22]. Mutual nearest neighbours in the 33-dimensional feature space form candidate correspondences. These candidates contain many false matches, so a graph-based reliable outlier removal step [23] retains only a mutually consistent set: correspondences whose pairwise distances are preserved within tolerance form a consistency graph, and the largest star-consistent subset seeded from the highest-degree node is kept. The surviving correspondences yield a coarse transform by the Umeyama estimator. This stage provides an initial guess robust enough for fine registration to converge.

### 5.4 Fine registration

Refinement uses Generalised ICP, which models each local neighbourhood as a Gaussian and minimises a plane-to-plane cost well suited to the planar walls of a tunnel [12]. The primary backend is the parallel small_gicp implementation of voxelised GICP [24]; when it is unavailable the pipeline falls back to a two-stage point-to-plane ICP in Open3D [25], a coarse pass at six times the voxel size followed by a fine pass at 1.5 times, with relative fitness and RMSE tolerances tightened from 10⁻⁵ to 10⁻⁷ between stages. Both backends report the final RMSE in millimetres.

### 5.5 Trimmed ICP and divergence guard

Partial overlap and residual clutter can bias a least-squares fit toward non-corresponding points. A trimmed ICP variant addresses this by keeping only the best-matched fraction of correspondences at each iteration. The keep fraction defaults to 0.80, clipped to the range 0.4–0.98, and the iteration stops when the RMSE change falls below 10⁻⁶ or after 25 iterations. Because the chain selects the minimum-RMSE transform across all candidates, a refinement that diverges on difficult geometry cannot worsen the output: the guard falls back to the coarse or as-is alignment. On a straight reference tunnel, GICP recovered a 1.2° yaw and 7 cm translation perturbation to an RMSE of 0.198 mm, 20 to 61 times faster than the Open3D point-to-plane baseline (Section 11).
## 6. Frenet-Frame Geometric Analysis

Cross-section measurements are only meaningful when the cutting plane is orthogonal to the tunnel axis. Slicing perpendicular to a global coordinate axis introduces oblique cuts in curved tunnels, and an oblique cut inflates the apparent radius and ovality [18]. The geometry layer (`geometry.py`) avoids this bias by extracting sections in the local Frenet frame of a fitted centerline. This curvature-correct extraction is the second principal contribution.

### 6.1 Centerline fitting

The centerline is a cubic B-spline through per-chunk geometric centres. The cloud is binned into equal-axial-position chunks, `n_chunks = max(2·section_count, 40)`, and the centre of each chunk is estimated by a circle fit rather than a mass centroid, so that uneven point density on one wall does not pull the axis off-centre. A cubic spline (degree 3, C² continuity) is fitted to these centres with a smoothing weight

$$ s = c \cdot m, \qquad c = 0.5 \tag{4} $$

where *m* is the number of centres and *c* the smoothing factor. The smoothing is necessary: an interpolating spline (*s* = 0) chases every centre and wanders laterally by up to 0.31 m, whereas the smoothed fit reduces the wander to the order of 0.002 m. End chunks whose circle-fit deviation exceeds a robust tolerance are trimmed before fitting, which prevents portal returns from distorting the spline ends.

### 6.2 Circle fitting

Chunk centres and per-section radii use the algebraic least-squares circle fit of Kåsa [21]. For a set of section points (*x*, *y*) in the cutting plane, the fit solves the linear system

$$ \begin{bmatrix} x & y & 1 \end{bmatrix} \begin{bmatrix} 2c_x \\ 2c_y \\ r^2 - c_x^2 - c_y^2 \end{bmatrix} = x^2 + y^2 \tag{5} $$

for the centre (*c*~x~, *c*~y~) and radius *r*. The algebraic form is fast and stable, but it degrades when the section is a short arc rather than a full ring. The implementation therefore guards coverage: a section is accepted only when the occupied angular span exceeds 220° or at least 24 of 36 angular bins are populated. Sections failing this test fall back to a normal-based or centroid-based centre, which keeps sparse or occluded sections from producing spurious geometry.

### 6.3 Gravity-anchored Frenet frames

At each section the orthonormal frame is built from the local tangent. The tangent *T* is the central difference of the centerline, normalised. Rather than the classical Frenet normal, which rotates with curvature and accumulates twist along the axis, the frame is anchored to gravity. A reference direction (global *Z*, or global *X* where the tangent is near-vertical, |*T~z~*| > 0.9999) is projected orthogonal to *T* to give the vertical axis *B*, and the lateral axis *N* completes the right-handed triad:

$$ B = \frac{\hat{z} - (\hat{z}\cdot T)\,T}{\lVert \hat{z} - (\hat{z}\cdot T)\,T \rVert}, \qquad N = B \times T \tag{6} $$

Anchoring to gravity gives every section a consistent vertical and lateral reference, so crown settlement is always measured along *B* and lateral convergence along *N*, independent of how the tunnel curves. In the section plane, a point's lateral coordinate is *d* · *N* and its vertical coordinate is *d* · *B*, where *d* is the offset from the section centre.

### 6.4 Section extraction

Points are assigned to a section when their projection onto the tangent falls within a half-thickness *ε* of the section plane. The thickness adapts to local point density:

$$ \varepsilon = \mathrm{clip}\!\left(0.55 \cdot \mathrm{median}(\Delta),\; 0.05,\; 0.5\right) \ \text{m} \tag{7} $$

where Δ is the set of nearest-neighbour spacings. Tying *ε* to the median spacing keeps each slice thick enough to contain a stable ring of points on sparse scans, while the 0.5 m cap prevents over-thick slices from blurring axial gradients on dense scans. On reference circular geometry, the extracted sections recover a median radius of 4.00002 m against a 4.00000 m design value, an error of 0.0005% (Section 11).
## 7. Parameter Extraction

From each extracted section the parameter layer (`parameters.py`) computes the deformation metrics that drive the assessment: crown settlement, lateral convergence, ovality, eccentricity, and clearance. Every metric uses a percentile rather than an extremum, because a single stray point corrupts a maximum but barely moves a high percentile.

### 7.1 Crown settlement

Crown settlement is the downward movement of the section apex. Within a section, the apex height is the 99th percentile of the vertical projection, and settlement is its drop relative to the reference epoch:

$$ \delta_v = \mathrm{p99}\big( (S_0 - C)\cdot B \big) - \mathrm{p99}\big( (S_n - C)\cdot B \big) \tag{8} $$

where *S*₀ and *S~n~* are the section points at the reference and current epochs, *C* the section centre, and *B* the vertical Frenet axis. A positive *δ~v~* denotes settlement. The 99th percentile stands in for the apex because, on field data, a stray reflection above the lining corrupts a literal maximum to spurious values on the order of a metre.

### 7.2 Lateral convergence

Convergence is the narrowing of the section across its lateral axis. The section width is the spread of the lateral projection between its 1st and 99th percentiles, and convergence is the reduction of that width relative to the reference:

$$ \delta_h = w_0 - w_n, \qquad w = \mathrm{p99}(d\cdot N) - \mathrm{p1}(d\cdot N) \tag{9} $$

with *d* = *S* − *C* and *N* the lateral axis. Using the p99–p1 span rather than the max–min span makes the width resistant to isolated outliers on either wall.

### 7.3 Ovality

Ovality quantifies departure from circularity. A direct least-squares ellipse is fitted to the section points by the method of Fitzgibbon et al. [20], which returns a stable fit under heterogeneous point density because it minimises an algebraic distance subject to an ellipse-specific constraint rather than iterating. From the fitted semi-axes *a* ≥ *b*,

$$ O = \frac{a - b}{a} \times 100\% \tag{10} $$

When the constrained fit fails on a degenerate section, the implementation falls back to the axis-aligned extents.

### 7.4 Eccentricity

Eccentricity measures lateral drift of the section centre away from the design axis. With a reference epoch, it is the distance between the measured and design centres. Without a reference, the implementation derives it from geometry alone: a circle is fitted to each section to obtain its centre (*c~x~*, *c~y~*), a baseline trajectory is formed by a moving median of the centres along the tunnel (window fraction 0.10), and eccentricity is the deviation from that baseline,

$$ e = 1000\,\sqrt{(c_x - \bar{c}_x)^2 + (c_y - \bar{c}_y)^2} \ \ \text{[mm]} \tag{11} $$

where (*c̄~x~*, *c̄~y~*) is the moving-median baseline. Detrending against the baseline separates real lateral drift from the gentle wander of the fitted centerline. A 5-point median filter then suppresses single-section spikes, since a genuine defect spans at least three consecutive sections, and a coverage guard skips sections with fewer than 17 of 24 occupied angular bins so that incomplete rings do not generate false eccentricity.

### 7.5 Clearance

Clearance checks whether the lining intrudes into the design envelope reserved for traffic. For a circular profile the signed clearance of a point is its radial distance minus the design envelope radius; for a box profile it is the signed distance to the nearest envelope face. A section is flagged as a violation when the 1st percentile of its signed clearance falls below zero, so that a real intrusion affecting at least 1% of the section triggers a warning while a lone stray point does not. On the labelled intrusion case, the check achieved 100% precision and 100% recall against ground-truth intrusion points (Section 11).

### 7.6 Output assembly

The per-section metrics are aggregated into the global `parameters` dictionary (mean ovality, mean eccentricity, peak crown settlement, peak convergence) and retained per section for export. These values feed the change-detection warnings of Section 8, the outputs of Section 10, and the assessment assistant of Section 9.
## 8. Multi-Epoch Change Detection

Deformation is assessed by comparing a current scan against an earlier reference. The change-detection layer (`timeseries.py`) computes signed surface displacement with M3C2, derives a per-section severity classification (`section_warnings.py`), and assembles spatiotemporal trends across a survey series.

### 8.1 M3C2 distance and Level of Detection

Surface change is measured with the Multiscale Model to Model Cloud Comparison algorithm [14], through the open-source py4dgeo implementation [28]. For each core point, M3C2 estimates a local normal over a search radius of 0.5 m and measures the mean surface position of each epoch within a cylinder of radius 0.5 m oriented along that normal; the signed distance between the two means is the displacement. The algorithm also returns a Level of Detection (LoD), the displacement magnitude below which a change cannot be distinguished from registration and roughness noise at the stated confidence. A displacement is reported as significant only when it exceeds the local LoD:

$$ \text{significant} \iff |d_{\text{M3C2}}| > \text{LoD} \tag{12} $$

Tying significance to a spatially varying LoD avoids a single global threshold, so smooth, well-registered regions resolve smaller changes than rough or sparsely sampled ones.

### 8.2 Section severity classification

For reporting, displacement is summarised per section as changes in width (*dW*), height (*dH*), radius (*dR*), ovality (*dOval*), and eccentricity (*dEcc*) relative to the reference epoch. Each change is mapped to a status of OK, CAUTION, or CRITICAL. The linear metrics use absolute thresholds of 10 mm (CAUTION) and 25 mm (CRITICAL); ovality uses 0.5% and 1.0%. These thresholds are informed by the survey and tolerance provisions of the Korean railway and tunnel standards KR C-08080 and KDS 27 25 00 [3,4]; the exact clause-level correspondence is an acknowledged limitation (Section 11.6) and the thresholds are exposed as configurable parameters rather than asserted as certified compliance values.

Warnings must stay localised to the chainage where deformation occurs, not smear across the whole tunnel. For ovality and eccentricity the classifier therefore adds a local-anomaly test: a section is flagged when its change exceeds the series median by a robust margin,

$$ t_{\text{local}} = \mathrm{median}(\Delta) + \max\big(3\,\hat{\sigma},\; t_{\text{floor}}\big), \qquad \hat{\sigma} = 1.4826\cdot \mathrm{MAD}(\Delta) \tag{13} $$

where Δ is the set of per-section changes and *t*~floor~ a metric-specific floor. The robust margin suppresses a uniform offset from imperfect registration, which would otherwise raise every section at once, while preserving a genuine localised defect that stands out from its neighbours. A clearance violation at any section is classified CRITICAL directly.

### 8.3 Spatiotemporal trends

For a survey series the layer compares every later epoch against the first, the T0→T*n* baseline (`spatiotemporal_series`). Each comparison contributes a per-epoch summary: the median displacement and the 95th percentile of absolute displacement, p95~abs~. The p95~abs~ statistic is reported as the trend value because whole-cloud median displacement stays near zero when deformation is localised, masking a developing defect that the upper percentile reveals. Core points are decimated to a working budget (default 50,000) so that a long series remains tractable. A complementary forecast routine flags the epoch at which an extrapolated trend would cross the caution (10 mm) or critical (25 mm) level, giving early warning before a threshold is reached.

The current implementation compares against the fixed baseline T0; reporting incremental epoch-to-epoch change (T*n*→T*n*₊₁) alongside the baseline trend is identified as future work in Section 12.
## 9. On-Device RAG Engineering Assistant

Converting deformation metrics into a written assessment is repetitive engineering work. The assistant module (`rag_ai.py`) drafts a preliminary summary from the extracted metrics using Retrieval-Augmented Generation [15], grounding the language model in a curated set of standard excerpts. The assistant runs entirely on-device, and its output is a draft for an engineer to review, not an authoritative judgement. This local, standards-grounded assistant is the third principal contribution.

### 9.1 Retrieval

The knowledge base holds 17 curated excerpts covering the inspection metrics and methods of this pipeline: crown settlement, convergence, ovality, eccentricity, clearance, deformation heatmaps, and the underlying point cloud techniques. Each excerpt is embedded with the all-MiniLM-L6-v2 sentence-transformer model [27] and indexed in a ChromaDB collection under cosine distance. At query time the section metrics are formed into a question, embedded, and matched against the collection to retrieve the most relevant excerpts. Retrieval grounds the generated text in domain material rather than the model's parametric memory, which is the mechanism by which RAG reduces hallucination in technical settings [16].

### 9.2 Generation

The retrieved excerpts and the section metrics are passed to a local large language model served by Ollama, with Qwen2.5-3B as the default model and a low sampling temperature of 0.15 to favour faithful, low-variance summaries over creative text. The model and the vector store both run on the inspection workstation; the endpoint and model name are configurable through environment variables, so an operator can substitute a larger local model without code changes. No survey data leaves the device, which suits the data-handling constraints of critical infrastructure.

### 9.3 Deterministic fallback

A language model may be unavailable on a field laptop, and a monitoring tool cannot depend on one. When the local model cannot be reached, the assistant falls back to a deterministic rule-based assessment (`_offline_analysis`) that maps the metrics directly to OK, CAUTION, or CRITICAL using the same thresholds as the section classifier of Section 8, together with a fixed table of maintenance actions keyed to each exceeded metric. The fallback guarantees that every report receives a consistent assessment, with or without the language model, and that the deterministic path, not the generative one, owns the safety-relevant classification.

### 9.4 Scope and limitation

The assistant drafts language; it does not certify condition. Generated summaries are explicitly preliminary and require review by a qualified engineer before use in any maintenance decision. A quantitative evaluation of retrieval accuracy against a curated question-and-answer set is not yet available and is reported as an open item (Section 11.6); accordingly, this study makes no numerical claim about the assistant's answer quality. The contribution is the architecture: an on-device, standards-grounded drafting aid with a deterministic safety floor, integrated into an end-to-end tunnel pipeline.
## 10. Output Generation

The pipeline closes the loop from scan to deliverable by producing three output products from the same `PipelineContext`: an IFC Building Information Model, a PDF inspection report, and structured CSV/Excel workbooks. Generating all three from one state object keeps the model, the report, and the tabular data consistent by construction.

### 10.1 IFC Building Information Model

The exporter (`ifc_exporter.py`) writes an IFC model through ifcopenshell. It supports both IFC4 (the default) and the infrastructure schema IFC4X3 [29]; when IFC4X3 is selected, the tunnel centerline is written as an `IfcAlignment`, the native alignment entity of the infrastructure schema, and degrades to an `IfcAnnotation` polyline under IFC4. Each cross-section is exported as an `IfcBuildingElementProxy` carrying its measured properties, and the deformed lining is written as a continuous tessellated shell (`IfcPolygonalFaceSet`). Section status drives surface colour through RGB styles for the three severity levels, so the deformation pattern is legible directly in any IFC viewer. In a representative export the model contained 40 section proxies on a valid IFC4X3 alignment, a deformation shell of 3,840 vertices, and component placeholders for cable runs and lighting, demonstrating that the geometric results transfer into a standard BIM exchange format.

### 10.2 PDF inspection report

The report generator (`pdf_reporter.py`) composes a multi-page document with ReportLab, using matplotlib for the embedded charts. The report opens with a cover and a summary of the global parameters, followed by per-section deformation plots (height, width, and ovality against chainage, laid out several sections per page), a per-section data table, and a list of flagged warnings. A separate routine emits a work-order PDF that pairs each flagged section with its recommended action. A representative report rendered to a valid 117 KB PDF in the smoke test.

### 10.3 Structured data export

For downstream analysis the exporter also writes CSV and multi-sheet Excel workbooks containing the global summary metrics and the full per-section table (chainage, radii, widths, heights, ovality, eccentricity, clearance, and warning status). The structured export is the machine-readable counterpart of the PDF, suitable for ingestion into asset-management systems or for longitudinal study across survey campaigns.
## 11. Experimental Validation

The pipeline is validated on synthetic ground-truth datasets, where the true geometry, the true clutter labels, and the true deformation are known exactly. Synthetic data isolates algorithm accuracy from survey error and provides the labelled references that field scans lack. All results below were produced at commit `84c02cc` with the Python 3.12 environment on Windows 11. Validation on field scans is identified as the principal remaining step (Section 11.6).

### 11.1 Datasets

The benchmark suite comprises six Blender-generated tunnel scenes, each isolating one capability: a clean reference, a localised deformation, a noise-and-cable scene with per-point clutter labels, a clearance-intrusion scene, a curved-centerline scene, and an occluded sparse scene. A separate registration benchmark applies a known rigid perturbation (1.2° yaw, 7 cm translation) to be recovered, and a time-series set provides six epochs with prescribed crown settlement, sidewall convergence, and a localised defect for change-detection testing.

### 11.2 Geometric accuracy and denoising

On the clean reference scene the section extraction recovered a median radius of 4.00002 m against the 4.00000 m design value, an error of 0.0005%, and raised no false warnings. On the curved and occluded scenes the median radius stayed within 0.009 m of design (3.991 m and 3.999 m) despite 2.03 m of lateral curvature and 8% point loss, confirming that the Frenet sectioning and coverage guards hold under curvature and occlusion. The denoising cascade, run on the labelled noise-and-cable scene, removed 82.6% of injected clutter while retaining 99.99% of lining points, for a precision of 1.00, recall of 0.83, and F1 of 0.90. The clearance check on the intrusion scene reached 100% precision and 100% recall (1,080 true positives, no false positives, no false negatives), correctly flagging the 870.3 mm maximum intrusion as critical. Table 4 summarises the suite.

**Table 4.** Blender benchmark suite (commit `84c02cc`; all 36 checks pass).

| Case | Scenario | Key result |
|---|---|---|
| 01 | Clean reference | median radius 4.00002 m (error 0.0005%); 0 false warnings |
| 02 | Local deformation | polar max 83.5 mm; 10 sections flagged; heatmap p95 50.9 mm |
| 03 | Noise and cables | recall 0.826, lining retention 0.9999, F1 0.90 |
| 04 | Clearance intrusion | precision 1.00, recall 1.00; max intrusion 870.3 mm |
| 05 | Curved centerline | median radius 3.991 m over 2.03 m lateral span |
| 06 | Occlusion / sparse | median radius 3.999 m despite 8% point loss |

### 11.3 Registration

Generalised ICP recovered the synthetic perturbation to sub-millimetre accuracy on the straight 400K-point tunnel: 0.198 mm RMSE in 587 ms, against 31.7 mm and 11,953 ms for the Open3D point-to-plane baseline, a 20-fold speedup at far higher accuracy. On the curved 150K-point dataset GICP remained faster by a factor of 61 (410 ms versus 25,182 ms). The higher residual on the curved set (71.0 mm versus 115.9 mm for the baseline) reflects that the 1.2° single-step perturbation exceeds the convergence basin for that geometry; in normal operation the feature-based GROR coarse alignment of Section 5.3 runs first and supplies an initialisation within the basin. Within the full pipeline, registration of the curved dataset converged to 0.224 mm via the fallback chain. Table 5 reports the comparison.

**Table 5.** Registration recovery (1.2° yaw, 7 cm translation).

| Dataset | Backend | RMSE (mm) | Time (ms) | Speedup |
|---|---|---|---|---|
| Straight, 400K | small_gicp GICP | 0.198 | 587 | 20.4× |
| Straight, 400K | Open3D point-to-plane | 31.735 | 11,953 | — |
| Curved, 150K | small_gicp GICP | 70.958 | 410 | 61.4× |
| Curved, 150K | Open3D point-to-plane | 115.915 | 25,182 | — |

### 11.4 Frenet versus world-frame sectioning

The benefit of Frenet sectioning is isolated by computing ovality both ways on the same scenes. On the curved scene, world-frame slicing overestimated median ovality by 171.5% relative (0.2282% versus 0.0841% in the Frenet frame), overestimated the radius standard deviation by 65.4%, and overestimated eccentricity by 38.5%. On the straight control scene the two methods agreed to within noise (a −2.1% difference). The bias is therefore specific to curvature, as expected: an oblique cut only distorts the section when the axis turns. This confirms the claim that Frenet sectioning removes a systematic ovality bias that axis-aligned slicing introduces in curved tunnels. Table 6 reports the comparison.

**Table 6.** Frenet versus world-frame ovality.

| Metric | Frenet | World-frame | Relative bias |
|---|---|---|---|
| Curved: median ovality (%) | 0.0841 | 0.2282 | +171.5% |
| Curved: radius std (m) | 0.00289 | 0.00478 | +65.4% |
| Curved: median eccentricity (m) | 569.9 | 789.4 | +38.5% |
| Straight (control): ovality (%) | 0.0209 | 0.0204 | −2.1% |

### 11.5 Change detection, pipeline speed, and output integrity

On the time-series and local-deformation scenes the M3C2 stage resolved the prescribed localised deformation (polar maximum 83.5 mm) and flagged ten sections, with all 18 change-detection checks passing. The complete pipeline processed the 150K-point dataset in 2.56 s end to end, of which denoising was the dominant cost at 1.95 s; centerline and section extraction together took 0.53 s. The output stage produced a valid IFC4X3 model with 40 section proxies and a 3,840-vertex deformation shell, and a valid 117 KB PDF report, confirming that the geometric results transfer into the exchange formats without loss.

### 11.6 Discussion and limitations

The results establish that the pipeline is accurate on geometry (0.0005% radius error), safe in denoising (99.99% lining retention), and correct in clearance detection (100% precision and recall) on controlled data, and that its two methodological contributions, the denoising cascade and Frenet sectioning, deliver their intended effect. Three limitations bound these claims. First, all validation is synthetic; field scans introduce registration error, scanner artefacts, and surface texture that synthetic scenes do not reproduce, so field validation is the necessary next step. Second, the RAG assistant is evaluated only architecturally: no retrieval-accuracy figure is reported because a curated question-and-answer reference set does not yet exist, and the generative output remains a draft for engineer review. Third, the severity thresholds are informed by KR C-08080 and KDS 27 25 00 but are not yet mapped clause by clause to those standards, so the system reports configurable engineering thresholds rather than certified regulatory compliance. None of these limitations affects the geometric and denoising results, which rest on ground-truth comparison.
## 12. Conclusion

This study presented the SSL Smart Tunnel Monitoring System, an open-source pipeline that automates tunnel structural health monitoring from raw LiDAR ingestion to report generation. The system contributes a three-stage cascaded denoising algorithm that removes 82.6% of injected clutter while retaining 99.99% of lining points without labelled training data, a Frenet-frame cross-section extraction method that recovers a median radius within 0.0005% of design and removes the ovality bias of axis-aligned slicing on curved alignments, and an end-to-end inspection chain with an on-device RAG assistant that drafts preliminary summaries while keeping survey data local. On synthetic ground-truth data the clearance check reached 100% precision and recall, generalised ICP recovered alignment to 0.198 mm an order of magnitude faster than the baseline, and the pipeline produced valid IFC4X3 models and PDF reports. The deformation thresholds are informed by the Korean railway and tunnel standards KR C-08080 and KDS 27 25 00.

Three directions follow from the present limitations. Field validation on operational tunnel scans is the immediate priority, since the current evidence is synthetic. A curated question-and-answer reference set would allow the RAG assistant to be evaluated quantitatively rather than only architecturally. Finally, a clause-level mapping of the severity thresholds to KR C-08080 and KDS 27 25 00, together with incremental epoch-to-epoch change reporting alongside the baseline trend, would move the system from configurable engineering thresholds toward certified regulatory assessment. Releasing the pipeline as open source is intended to let the tunnel monitoring community build on these foundations.

## References

[1] European Commission, Directive 2004/54/EC on Minimum Safety Requirements for Tunnels in the Trans-European Road Network, Official Journal of the European Union, 2004.

[2] OECD/PIARC, Safety in Tunnels: Transport of Dangerous Goods through Road Tunnels, Paris, 2001.

[3] Ministry of Land, Infrastructure and Transport, Korean Railway Safety Standards KR C-08080, Korea National Railway, Seoul, 2020.

[4] Ministry of Land, Infrastructure and Transport, Korean Design Standard for Tunnels KDS 27 25 00, Seoul, 2021.

[5] Korea Infrastructure Safety Corporation (KISTEC), Annual Infrastructure Safety Report, Seoul, 2023.

[6] M. Alba, L. Fregonese, F. Prandi, M. Scaioni, P. Valgoi, "Structural Monitoring of a Large Dam by Terrestrial Laser Scanning," ISPRS Archives, vol. XXXVI-5, 2006.

[7] A. Nuttens, A. De Wulf, L. Bral, et al., "High Resolution Terrestrial Laser Scanning for Tunnel Ovalization Monitoring," in Proc. FIG Working Week, 2010.

[8] J. Jung, S. Kim, Y. Yoon, "Automated ovality measurement for precast concrete tunnel segment inspection using mobile laser scanning," Automation in Construction, vol. 121, p. 103424, 2021.

[9] V. Gikas, "Three-Dimensional Laser Scanning for Geometry Documentation and Construction Management of Highway Tunnels during Excavation," Sensors, vol. 12, no. 8, pp. 10827–10843, 2012.

[10] X. Ye, J. Liu, L. Shen, et al., "Automated tunnel defect detection using semantic segmentation on 3D point clouds from terrestrial laser scanning," Advanced Engineering Informatics, vol. 55, p. 101874, 2023.

[11] L. Attard, C. J. Debono, G. Valentino, M. Di Castro, "Tunnel inspection using photogrammetric techniques and image processing: a review," ISPRS Journal of Photogrammetry and Remote Sensing, vol. 144, pp. 180–188, 2018.

[12] A. Segal, D. Haehnel, S. Thrun, "Generalized-ICP," in Proc. Robotics: Science and Systems (RSS), Seattle, WA, 2009.

[13] J. Yang, H. Li, D. Campbell, Y. Jia, "Go-ICP: A Globally Optimal Solution to 3D ICP Point-Set Registration," IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 38, no. 11, pp. 2241–2254, 2016.

[14] D. Lague, N. Brodu, J. Leroux, "Accurate 3D comparison of complex topography with terrestrial laser scanner: application to the Rangitikei canyon (N-Z)," ISPRS Journal of Photogrammetry and Remote Sensing, vol. 82, pp. 171–184, 2013.

[15] P. Lewis, E. Perez, A. Piktus, et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in Proc. NeurIPS, 2020.

[16] X. Jiang, Y. Li, W. Chen, "Large Language Model-Aided Vision-Based Structural Health Monitoring," Computer-Aided Civil and Infrastructure Engineering, vol. 39, no. 12, pp. 1888–1905, 2024.

[17] R. B. Rusu, Z. C. Marton, N. Blodow, M. Beetz, "Towards 3D Point Cloud Based Object Maps for Household Environments," Robotics and Autonomous Systems, vol. 56, no. 11, pp. 927–941, 2008.

[18] S. Fekete, M. Diederichs, M. Lato, "Geotechnical and operational applications for 3-dimensional laser scanning in drill and blast tunnels," Tunnelling and Underground Space Technology, vol. 25, no. 5, pp. 614–628, 2010.

[19] R. Lindenbergh, P. Pfeifer, "A statistical deformation analysis of two epochs of terrestrial laser data of a lock," in Proc. 7th Conference on Optical 3-D Measurement Techniques, Vienna, 2005.

[20] A. W. Fitzgibbon, M. Pilu, R. B. Fisher, "Direct least square fitting of ellipses," IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 21, no. 5, pp. 476–480, 1999.

[21] I. Kåsa, "A circle fitting procedure and its error analysis," IEEE Transactions on Instrumentation and Measurement, vol. IM-25, no. 1, pp. 8–14, 1976.

[22] R. B. Rusu, N. Blodow, M. Beetz, "Fast Point Feature Histograms (FPFH) for 3D registration," in Proc. IEEE International Conference on Robotics and Automation (ICRA), Kobe, Japan, 2009, pp. 3212–3217.

[23] L. Yan, P. Wei, H. Xie, J. Dai, H. Wu, M. Huang, "A New Outlier Removal Strategy Based on Reliability of Correspondence Graph for Fast Point Cloud Registration," IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 45, no. 6, pp. 7986–8002, 2023.

[24] K. Koide, M. Yokozuka, S. Oishi, A. Banno, "Voxelized GICP for Fast and Accurate 3D Point Cloud Registration," in Proc. IEEE International Conference on Robotics and Automation (ICRA), Xi'an, China, 2021, pp. 11054–11059.

[25] Q.-Y. Zhou, J. Park, V. Koltun, "Open3D: A Modern Library for 3D Data Processing," arXiv preprint arXiv:1801.09847, 2018.

[26] M. Ester, H.-P. Kriegel, J. Sander, X. Xu, "A density-based algorithm for discovering clusters in large spatial databases with noise," in Proc. 2nd International Conference on Knowledge Discovery and Data Mining (KDD), Portland, OR, 1996, pp. 226–231.

[27] N. Reimers, I. Gurevych, "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks," in Proc. Conference on Empirical Methods in Natural Language Processing (EMNLP), Hong Kong, 2019, pp. 3982–3992.

[28] K. Anders, D. Kempf, W. Albert, et al., "py4dgeo: Open-source scientific software for topographic change analysis in 3D/4D geographic point clouds," SoftwareX, vol. 34, p. 102670, 2026.

[29] buildingSMART International, Industry Foundation Classes (IFC) 4.3.2.0 (IFC4X3), ISO 16739-1:2024, 2024.
