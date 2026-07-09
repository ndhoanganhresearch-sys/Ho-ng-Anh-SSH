# Reference Repo Integration Status

This file explains how each local reference repository has influenced or been integrated into the SSL Tunnel Analysis project, what is already present in `tunnel_project/`, and what remains unused.

## Summary

| Reference Repo | Integration Level | Current Project Areas Affected | Overall Status |
| --- | --- | --- | --- |
| `_ref_FY387_calc` | Concept / benchmark influence | T0/Tn deformation workflow, synthetic fixtures, Step 6 tests | Partially integrated as workflow ideas, not code |
| `_ref_SAM4Tun` | Concept influence only | Segmentation roadmap, tunnel lining/component ideas | Not integrated into production code |
| `_ref_GROR` | Partial conceptual integration | Registration fallback naming/idea, robust alignment tests | Mentioned in UI/workflow, original C++ algorithm not integrated |
| `_ref_Cloud2BIM` | Concept influence | IFC/BIM exporter, tunnel lining entity export | Similar output goal integrated, original code not integrated |
| `_ref_PowerLine` | Minimal / not integrated | Cable/noise detection inspiration only | Not integrated |
| `_ref_trending/MinerU` | Tooling integration | Document-to-Markdown/JSON and RAG ingest | Installed, tested, and used for one DOCX |
| `_ref_trending/codebase-memory-mcp` | Installed tooling only | Future codebase-memory/MCP evaluation | Not wired into project MCP yet |
| `_ref_trending/lingbot-map` | Reference only | Future 3D reconstruction/mapping ideas | Not integrated into production code |
| `_ref_trending/cupy` | Installed package trial | Future GPU acceleration prototypes | Blocked by Windows CUDA/Application Control import issue |

## Trending Repo Routing

Use `tunnel_project/docs/TRENDING_REPO_DECISION_GUIDE.md` for the decision table and
`tunnel_project/tools/choose_trending_repo.py "<task>"` for a simple score-based recommendation.
The default policy is:

- MinerU may be used directly for document/RAG tooling because it has been smoke-tested.
- codebase-memory-mcp may be evaluated in isolation, but `.mcp.json` should not be changed until it passes an MCP/query smoke test.
- lingbot-map is algorithm reference only until a tunnel-specific prototype exists.
- CuPy must not replace NumPy production code until import works and CPU-vs-GPU benchmarks prove value.

## 1. `_ref_FY387_calc`

Remote: `https://github.com/FY387/Deformation-calculation-of-metro-tunnels-based-on-point-clouds.git`

### What The Reference Repo Contains

- README for metro tunnel deformation point-cloud datasets.
- Dataset links for terrestrial laser scanner and railcar/mobile laser scanning equipment.
- Notes that coordinates are scanner-coordinate based rather than real-world geographic coordinates.
- No local production code files were found in the clone beyond README and repository metadata.

### What Is Integrated In This Project

Integration is mainly at the workflow and benchmark-design level.

Current project areas that overlap:

- `tunnel_project/tunnel_analysis/parameters.py` computes tunnel section deformation metrics.
- `tunnel_project/tunnel_analysis/registration.py` and UI epoch registration align T0/Tn scans.
- `tunnel_project/test_deformation_groundtruth.py` protects ground-truth deformation behavior.
- `tunnel_project/test_step6_evaluation.py` protects Step 6 evaluation behavior.
- `tunnel_project/test_pipeline_end_to_end.py` protects the end-to-end T0/Tn pipeline.
- `tunnel_project/BENCHMARK_BASELINES.md` now tracks benchmark expectations.
- `tunnel_project/PROJECT_ROADMAP.md` puts T0/Tn deformation as the main value path.

### Integration Depth

- Code copied: none confirmed.
- Dataset copied: none confirmed from FY387 links.
- Concepts adopted: T0/Tn tunnel deformation comparison, scanner-coordinate dataset thinking, deformation benchmark mindset.
- Tests added in project: yes, but they are project-local synthetic/regression tests, not direct FY387 test imports.

### What Is Not Integrated Yet

- FY387 original datasets are not stored as first-class fixtures in `tunnel_project/data/`.
- No direct loader/adapter for FY387 dataset folder structure exists.
- No documented comparison table against FY387 metrics exists.
- No provenance record confirms any project fixture came from FY387 data.
- No paper-to-code mapping for FY387 method equations exists yet.

### Recommended Next Step

If using FY387 seriously, create `docs/references/FY387_DATASET_NOTES.md` and a small adapter/test that records dataset source, coordinate assumptions, expected metrics, and whether the data may be redistributed.

## 2. `_ref_SAM4Tun`

Remote: `https://github.com/zxy239/SAM4Tun.git`

### What The Reference Repo Contains

- `SAM4Tun.ipynb`, a large notebook for tunnel lining point-cloud component segmentation.
- README describing no-training tunnel lining component segmentation using SAM, point-cloud unfolding, panoramic images, prompt engineering, density variation filtering, and point-cloud up-sampling.
- Local scratch files currently present: `_nb.py`, `_nbcode.py`, `_nbmd.py`, `_nbtail.py`.

### What Is Integrated In This Project

Currently this is only conceptual influence.

Project areas that could relate:

- `tunnel_project/tunnel_analysis/segmentation.py` handles segmentation-like project logic.
- `tunnel_project/tunnel_analysis/preprocessing.py` and auto-denoise logic handle non-structural clutter.
- `tunnel_project/tunnel_analysis/ui/main_window.py` visualizes sections, labels, and 3D markers.
- `tunnel_project/PROJECT_ROADMAP.md` lists component/segmentation ideas as future AI/document/segmentation improvements.

### Integration Depth

- Code copied: none confirmed.
- Model dependency integrated: no SAM dependency integrated.
- Notebook pipeline integrated: no.
- Conceptual overlap: yes, especially tunnel unfolding, lining component segmentation, and component-level damage localization.

### What Is Not Integrated Yet

- No SAM model loading or Segment Anything dependency in project runtime.
- No tunnel panoramic unfolding pipeline equivalent to SAM4Tun.
- No prompt generation pipeline for lining components.
- No component-level lining instance IDs tied to deformation warnings.
- No benchmark comparing current segmentation/denoise output against SAM4Tun-style component segmentation.
- Scratch files in `_ref_SAM4Tun` are not managed or documented beyond inventory notes.

### Recommended Next Step

Do not integrate SAM directly yet. First create a lightweight `segmentation_experiment_sam4tun.md` note describing which notebook cells matter, what inputs are required, and what a minimal smoke test would look like.

## 3. `_ref_GROR`

Remote: `https://github.com/WPC-WHU/GROR.git`

### What The Reference Repo Contains

- C++/PCL implementation of GROR, a graph-reliability outlier removal strategy for robust point-cloud registration.
- `include/` and `src/` C++ code.
- `CMakeLists.txt` build file.
- README and TPAMI paper reference.

### What Is Integrated In This Project

Integration is partial and mostly conceptual/naming-level.

Project evidence:

- `tunnel_project/tunnel_analysis/ui/main_window.py` contains a comment/step mentioning fallback to intensity anchor + GROR coarse align.
- `tunnel_project/tunnel_analysis/registration.py` contains project-native registration logic, including target/SVD alignment, ICP refinement, and trimmed ICP behavior.
- `tunnel_project/test_register_epochs.py` and `tunnel_project/test_register_guard.py` protect registration behavior so local deformation is not absorbed.
- `tunnel_project/BENCHMARK_BASELINES.md` tracks epoch registration as a golden area.

### Integration Depth

- Original GROR C++ code compiled into project: no.
- PCL dependency added for GROR: no.
- Python wrapper for GROR: no.
- Conceptual idea adopted: robust registration under outliers / coarse robust fallback.
- Production behavior: project uses its own registration stack, not GROR itself.

### What Is Not Integrated Yet

- Correspondence graph reliability algorithm is not implemented in Python project code.
- No C++ extension or executable call to `_ref_GROR` exists.
- No benchmark compares GROR against current trimmed ICP/register_epochs.
- No license/dependency decision has been recorded for GROR integration.
- No data-driven proof exists that GROR improves this tunnel dataset.

### Recommended Next Step

Keep GROR as a benchmark candidate only. If needed, build a comparison task: current register_epochs vs GROR-inspired outlier rejection on box shift, long-tunnel guard, and local deformation fixtures.

## 4. `_ref_Cloud2BIM`

Remote: `https://github.com/VaclavNezerka/Cloud2BIM.git`

### What The Reference Repo Contains

- Python Scan-to-BIM workflow.
- `cloud2entities.py` for extracting entities from point clouds.
- `generate_ifc.py` for IFC generation.
- `space_generator.py`, plotting utilities, configs, sample input/output folders.
- Focuses on building elements such as slabs, walls, windows, and doors.

### What Is Integrated In This Project

The output direction is integrated, but the original repo code is not directly integrated.

Project areas:

- `tunnel_project/tunnel_analysis/ifc_exporter.py` exports tunnel-related IFC/BIM outputs.
- `tunnel_project/smoke_test_ifc_export.py` verifies IFC spatial hierarchy, centerline annotation/alignment, continuous tunnel lining, component counts, and cable tube export.
- `tunnel_project/tunnel_analysis/exporter.py` and `pdf_reporter.py` support engineering outputs.
- UI exposes IFC export options and IFC4X3/IfcAlignment-related behavior.

### Integration Depth

- Original Cloud2BIM code copied: none confirmed.
- IFC concept integrated: yes, strongly.
- Domain adapted: project focuses on tunnel lining/centerline/deformation, not building slabs/windows/doors.
- Tests present: yes, project has IFC smoke tests.

### What Is Not Integrated Yet

- Cloud2BIM entity recognition workflow is not imported.
- No building-style slab/wall/window/door extraction is used.
- No Cloud2BIM config or output folder is used by app runtime.
- No direct comparison between Cloud2BIM IFC structure and project IFC output exists.
- No Scan-to-BIM architectural element recognition has been adapted to tunnel components.

### Recommended Next Step

Use Cloud2BIM only as an IFC/Scan-to-BIM reference. The project should continue with tunnel-specific IFC entities: lining, centerline, warnings, cables, and deformation property sets.

## 5. `_ref_PowerLine`

Remote: `https://github.com/lyuhaitao/PowerLineDetection.git`

### What The Reference Repo Contains

- Jupyter notebooks, especially `index.ipynb`.
- `lyutool/` Python package with helper functions.
- Project appears to target power-line detection and notebook-based workflows.

### What Is Integrated In This Project

There is no confirmed direct integration.

Possible conceptual overlap:

- `tunnel_project/tunnel_analysis/preprocessing.py` and auto-denoise workflows detect/remove non-structural clutter.
- Project stats include `n_cable`, `n_wall_cable`, `n_light`, and `n_person` in denoise/reporting flows.
- `tunnel_project/smoke_test_auto_denoise.py` and `validate_auto_denoise_stsd.py` are relevant to cable/noise filtering.

### Integration Depth

- Code copied: none confirmed.
- Notebook used in app: no.
- Cable detection concept: possible loose inspiration only.
- Priority: low.

### What Is Not Integrated Yet

- No power-line detection algorithm is imported.
- No notebook pipeline is connected to tunnel denoise.
- No benchmark shows PowerLineDetection helps wall-cable filtering.
- No dependency or package from `_ref_PowerLine` is installed into the app.

### Recommended Next Step

Do not integrate unless wall-cable detection becomes a bottleneck. If needed, inspect only the line/cable heuristics and compare against existing auto-denoise metrics.

## Cross-Repo Integration Gaps

The project currently has strong local implementation but weak provenance tracking for reference influence.

Missing management artifacts:

- A per-reference license summary.
- A code-origin log for any future copied/adapted code.
- A benchmark comparison matrix against FY387/SAM4Tun/GROR ideas.
- A clear distinction in docs between implemented behavior and research inspiration.

## Recommended Policy

Use this rule before integrating any reference repo:

1. Write the target project problem first.
2. Identify the smallest idea or function to test.
3. Record source repo, file, license, and commit.
4. Implement a project-native adapter or experiment, not a whole repo import.
5. Add a regression or benchmark before promoting it.
6. Update `REPO_INVENTORY.md`, `REPO_INTEGRATION_STATUS.md`, and `BENCHMARK_BASELINES.md` if it affects production behavior.
