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
