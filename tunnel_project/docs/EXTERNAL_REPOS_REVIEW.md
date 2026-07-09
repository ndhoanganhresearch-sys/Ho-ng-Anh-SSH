# External Repos Review for SSL Tunnel Analysis

Date: 2026-06-29

Purpose: identify external repositories/tools that can strengthen the tunnel point-cloud deformation workflow without copying large codebases into this repo.

Decision rule: keep external repos as references or optional backends first. Do not replace the current 7-step workflow unless a tool passes a small reproducible benchmark on the project datasets.

## Recommended Priority

| Priority | Repo/tool | Best use in this project | Decision |
| --- | --- | --- | --- |
| P1 | py4dgeo | Scientific M3C2 / M3C2-EP cross-check for Step 6 | Integrate as validation backend |
| P1 | PDAL `filters.m3c2` | CLI-independent M3C2 verification pipeline | Add reproducible benchmark script |
| P1 | small_gicp | Faster/stronger rigid registration backend | Prototype behind optional adapter |
| P2 | Open3D | Baseline IO, voxel, normals, ICP, visualization | Keep as stable foundation |
| P2 | IfcOpenShell | Stronger IFC/BIM export path | Use to harden `ifc_exporter.py` |
| P3 | probreg | Experimental non-rigid/probabilistic registration | Research only, not core yet |
| P3 | CloudCompare | Manual/GUI reference for M3C2 and visual QA | Use as external sanity check |

## P1: py4dgeo

Source: https://github.com/3dgeo-heidelberg/py4dgeo

Why it matters:

- Purpose-built for 3D/4D geospatial point-cloud change analysis.
- Directly relevant to Step 6 deformation detection because it supports M3C2-family workflows.
- Useful as a scientific reference implementation when comparing project output against ground truth CSV files.

Suggested project use:

- Add a small validator script under `tunnel_project/tools/` that runs py4dgeo on `T0` and `Tn` point clouds.
- Compare its result to the current Step 6 output using p50, p95, max absolute displacement, warning count, and local section error.
- Keep py4dgeo optional so the UI still runs when the dependency is missing.

Success criteria:

- Runs on one clean T0/Tn dataset and one T0-T5 dataset.
- Produces a CSV summary that can be compared with `ground_truth.csv`.
- Documents parameter choices: normal radius, cylinder radius, projection depth, core-point strategy.

Risks:

- M3C2 parameters can change results significantly.
- Direct point-to-point comparison with the current tool may be unfair unless core points and normals are aligned.

## P1: PDAL `filters.m3c2`

Source: https://pdal.io/en/stable/stages/filters.m3c2.html

Why it matters:

- PDAL provides a separate CLI/data-pipeline implementation of M3C2.
- Good for reproducibility because a JSON pipeline can be committed and rerun.
- Helps avoid relying only on one Python implementation.

Suggested project use:

- Add `tunnel_project/benchmarks/m3c2_pdal/` with a minimal pipeline JSON and README.
- Use PDAL output as an external benchmark, not as the app's first dependency.
- Store only small CSV summaries in Git; keep large generated point clouds ignored or outside Git.

Success criteria:

- One-command run from `tunnel_project/`.
- Produces comparable summary metrics to Step 6 and py4dgeo.
- Notes installation requirement separately for Windows/WSL.

Risks:

- PDAL install on Windows can be heavier than Python-only dependencies.
- Pipeline setup may need format conversion if input data is `.txt` instead of LAS/LAZ.

## P1: small_gicp

Source: https://github.com/koide3/small_gicp

Why it matters:

- The project needs robust T0/Tn alignment before deformation analysis.
- GICP-style registration can outperform plain point-to-point ICP on noisy tunnel scans.
- Python binding makes it realistic to test without rewriting the app.

Suggested project use:

- Create an optional adapter, for example `tunnel_analysis/registration_backends/small_gicp_backend.py` only after a benchmark proves value.
- First prototype in a standalone benchmark script against current registration output.
- Compare RMSE, transform error, runtime, and downstream deformation error.

Success criteria:

- Improves or matches current registration on curved/sparse/noisy tunnel datasets.
- Does not make Step 6 deformation look better by overfitting deformed regions.
- Fails gracefully when dependency is unavailable.

Risks:

- Faster registration is not automatically more correct for deformation monitoring.
- Registration must avoid using locally deformed zones as stable alignment evidence.

## P2: Open3D

Source: https://github.com/isl-org/Open3D

Why it matters:

- Stable general-purpose point-cloud toolkit.
- Good baseline for IO, downsampling, normal estimation, KD-tree operations, ICP, and visualization.
- Useful for keeping project code simple instead of maintaining custom geometry utilities everywhere.

Suggested project use:

- Continue using it as baseline infrastructure.
- Avoid replacing specialized M3C2 validation with Open3D-only distance metrics.
- Use Open3D examples to simplify low-level point-cloud preprocessing only when existing code becomes brittle.

Success criteria:

- Preprocessing remains deterministic.
- Parameters are documented in benchmark output.

## P2: IfcOpenShell

Source: https://github.com/IfcOpenShell/IfcOpenShell

Why it matters:

- The repo already has `tunnel_analysis/ifc_exporter.py`.
- IfcOpenShell can improve standards-compliant IFC generation and inspection.
- Relevant if the project moves from analysis demo to BIM/digital-twin deliverables.

Suggested project use:

- Use IfcOpenShell as a reference or optional backend for IFC validation/export.
- Add a tiny IFC smoke check: file opens, expected entities exist, metadata is present.
- Keep the current exporter simple unless a real IFC consumer requires richer geometry.

Success criteria:

- Generated IFC opens in common viewers.
- Tunnel sections, deformation warnings, and metadata are represented consistently.

Risks:

- IFC complexity can easily distract from core point-cloud math.
- Avoid building a full BIM authoring system inside this project.

## P3: probreg

Source: https://github.com/neka-nat/probreg

Why it matters:

- Provides probabilistic and non-rigid registration methods.
- Could help evaluate hard cases where rigid registration fails.

Suggested project use:

- Keep as research-only for now.
- Use on copied benchmark data, not in the app workflow.
- Compare against rigid/GICP methods with deformation ground truth.

Success criteria:

- Demonstrates clear benefit on a known failure case.
- Does not erase true deformation by treating it as non-rigid alignment.

Risks:

- Non-rigid registration can hide the exact deformation the project is trying to detect.
- Higher algorithmic complexity makes results harder to explain in papers/reports.

## P3: CloudCompare

Source: https://github.com/CloudCompare/CloudCompare

Why it matters:

- Useful GUI/CLI reference for point-cloud visual QA and M3C2-style workflows.
- Good for manual inspection when Python results look suspicious.

Suggested project use:

- Use as an external sanity-check tool, not as a code dependency.
- Keep screenshots or short notes in reports only when they support a benchmark claim.

Success criteria:

- Manual visual QA agrees with numeric warning zones.
- Disagreements are documented rather than hidden.

## Integration Roadmap

### Phase 1: Reference-only review

- Clone external repos outside Git-tracked project folders, preferably under `_ref_pointcloud/` or `_ref_trending/`.
- Do not vendor their source into `tunnel_project/`.
- Record exact commit/tag used for any benchmark.

### Phase 2: M3C2 validation triangle

- Current Step 6 output remains the app output.
- py4dgeo provides Python scientific cross-check.
- PDAL provides CLI/pipeline cross-check.
- A result is considered reliable only when the three paths agree within a documented tolerance on clean synthetic datasets.

### Phase 3: Registration benchmark

- Compare current ICP/Open3D path against small_gicp on the same T0/Tn datasets.
- Report transform error, RMSE, runtime, and downstream deformation error.
- Promote small_gicp only if it improves deformation accuracy, not just registration RMSE.

### Phase 4: IFC hardening

- Use IfcOpenShell to validate generated IFC files.
- Add only minimal export improvements needed by real BIM viewers or project reports.

## What Not To Do

- Do not commit `node_modules/`, cloned external repos, or large generated clouds.
- Do not replace Step 6 with a black-box library without benchmark evidence.
- Do not use non-rigid registration as a default deformation pipeline.
- Do not claim a research gap from GitHub popularity alone; verify with literature search separately.

## Immediate Next Actions

1. Create a tiny py4dgeo cross-check script for one T0/Tn dataset.
2. Add a PDAL pipeline example if PDAL is installed or available through WSL/conda.
3. Benchmark small_gicp on one current registration failure/hard case.
4. Add an IFC smoke validator only after choosing the expected IFC output fields.

