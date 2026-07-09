# Code-to-Paper Mapping

Maps each paper section to the source code modules, key functions, and parameters that must be referenced.

## Section 4: Preprocessing + Denoising

| Paper Claim | Module | Function/Class | Key Parameters |
|------------|--------|---------------|----------------|
| PCA morphological classification | `preprocessing.py` | `_morphological_filter()` | k=20, linearity>=0.30, sphericity>=0.12 |
| Radial MAD filtering | `preprocessing.py` | `_radial_mad_filter()` | k=2.5, factor=1.4826 |
| Cylindrical-grid cable detection | `preprocessing.py` | `_wall_cable_filter()` | 60x180 bins, protrusion=0.05m, axial continuity |
| Safety guard | `preprocessing.py` | `_safety_guard()` | max_removal=30% |
| Range crop | `preprocessing.py` | `range_crop()` | 3 distance modes |
| Voxel downsample | `preprocessing.py` | `voxel_downsample()` | 0.02/0.05/0.10 m |

## Section 5: Registration

| Paper Claim | Module | Function/Class | Key Parameters |
|------------|--------|---------------|----------------|
| Target-based rigid | `registration.py` | `_target_based_registration()` | rigid transform from known targets |
| FPFH + GROR | `registration.py` | `_feature_registration()` | FPFH radius, GROR outlier rejection |
| Two-stage ICP | `registration.py` | `_icp_registration()` | P2P ICP + GICP |
| Trimmed ICP | `registration.py` | `_trimmed_icp()` | 80% correspondence trimming |

## Section 6: Frenet-Frame Geometry

| Paper Claim | Module | Function/Class | Key Parameters |
|------------|--------|---------------|----------------|
| Cubic B-spline centerline | `geometry.py` | `_fit_centerline_bspline()` | C2 continuity, per-chunk fitting |
| Kasa circle fit per chunk | `geometry.py` | `_kasa_circle_fit()` | arc>220 deg or occupancy>=24/36 |
| Gravity-anchored Frenet frames | `geometry.py` | `_compute_frenet_frames()` | T=central diff, N=global-Z projection, B=NxT |
| Adaptive slice thickness | `geometry.py` | `_extract_sections()` | eps=0.55*median_spacing, clipped [0.05, 0.5]m |

## Section 7: Parameter Extraction

| Paper Claim | Module | Function/Class | Key Parameters |
|------------|--------|---------------|----------------|
| Crown settlement | `parameters.py` | `_crown_settlement()` | p99 of B-projection |
| Lateral convergence | `parameters.py` | `_lateral_convergence()` | p99-p1 of N-projection |
| Ovality (Fitzgibbon) | `parameters.py` | `_ovality_fitzgibbon()` | direct LSQ ellipse |
| Eccentricity | `parameters.py` | `_eccentricity()` | circle-fit center deviation, moving-median detrending |
| Clearance detection | `parameters.py` | `_clearance_check()` | design envelope comparison |

## Section 8: M3C2 Change Detection

| Paper Claim | Module | Function/Class | Key Parameters |
|------------|--------|---------------|----------------|
| M3C2 distance | `timeseries.py` | `_m3c2_distance()` | normal-direction cloud comparison |
| Level of Detection | `timeseries.py` | `_lod_threshold()` | 95% confidence from local roughness |
| Deformation warnings | `section_warnings.py` | `_classify_warning()` | KR C-08080 thresholds |

## Section 9: Output Generation

| Paper Claim | Module | Function/Class | Key Parameters |
|------------|--------|---------------|----------------|
| PDF report | `pdf_reporter.py` | `generate_report()` | ReportLab, per-section plots |
| IFC4X3 BIM | `ifc_exporter.py` | `export_ifc()` | IfcAlignment, tessellated shells, status colours |
| CSV/Excel | `parameters.py` | `export_results()` | openpyxl multi-sheet |

## Section 10: RAG Assistant

| Paper Claim | Module | Function/Class | Key Parameters |
|------------|--------|---------------|----------------|
| Vector store | `rag_ai.py` | `_init_chromadb()` | ChromaDB + SentenceTransformer all-MiniLM-L6-v2 |
| LLM inference | `rag_ai.py` | `_query_llm()` | Ollama Qwen2.5:3b, temp=0.15 |
| Knowledge base | `rag_ai.py` | `_load_standards()` | 15+ curated safety standard excerpts |
| Rule-based fallback | `rag_ai.py` | `_rule_based_assessment()` | deterministic when LLM unavailable |

## How to Use

Before writing any methodology section:
1. Read the corresponding module file to verify function names and parameters still match.
2. If a function was renamed or parameter changed, update this map AND the draft.
3. Never cite a parameter value without verifying it in the current code.
