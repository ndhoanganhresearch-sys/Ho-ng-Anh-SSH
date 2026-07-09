# SSL Tunnel Analysis

Python tool for tunnel point-cloud monitoring. The maintained application is the
`tunnel_analysis` package, launched through `run_tunnel_analysis.py`.

## Main Entrypoint

Run from `tunnel_project`:

```powershell
..\.venv\Scripts\python.exe run_tunnel_analysis.py
```

or double-click/use:

```powershell
.\run.bat
```

Legacy prototypes such as `TunnelApp.py`, `main_app.py`, and files under
`New folder/` are historical references. Do not use them as the primary app
unless a task explicitly targets them.

## Reproducible Windows Setup

This workspace currently uses the parent virtual environment at `..\.venv`.

```powershell
cd "C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project"
py -3.12 -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install --upgrade pip
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe run_tunnel_analysis.py
```

If Microsoft Store Python injects user-site packages, `run_tunnel_analysis.py`
prunes `local-packages` before importing NumPy/SciPy.

## Quick Verification

Claude/agent sessions should use the unified verification gate first:

```powershell
.\agent_verify.ps1 quick
```

Use the stable smoke gate before committing changes:

```powershell
.\verify_quick.ps1
```

For Step 6 / T0-Tn deformation work, run the focused regression gate:

```powershell
.\verify_step6.ps1
```

or through the agent gate:

```powershell
.\agent_verify.ps1 step6
```

The script covers T0-reference detection, epoch registration, curved-tunnel
eccentricity, ground-truth deformation, 2D/3D section consistency, and the
end-to-end auto pipeline.

For AI/Headroom/RAG changes, use:

```powershell
.\agent_verify.ps1 ai
```

## Core Workflow

1. Load T0 reference and Tn monitoring scans.
2. Clean/downsample point clouds while preserving epoch alignment.
3. Register Tn to T0 when scans use different scanner setups.
4. Extract centerline and Frenet frames from the reference geometry.
5. Build cross-sections and compute T0/Tn deltas.
6. Show warnings only on affected chainage sections in 2D and 3D.

## 7-Step User Guide

For the simplified UI workflow, see `docs/USER_GUIDE_7_STEPS.md`.
For easy/low-risk maintenance tasks, see `docs/EASY_WORK_CHECKLIST.md`.
## Roadmap

See `PROJECT_ROADMAP.md` for the current 3-phase plan: core stability, benchmark hardening, and AI/document automation. Baseline expectations are tracked in `BENCHMARK_BASELINES.md`.

## Parameters Register

Use `docs/standards/STANDARD_PARAMETERS.md` as the live register for code parameters, standard claims, document provenance, and verification status.

## Reference Repositories

See `../REPO_INVENTORY.md` for the local reference repos, their remotes, relevance, and integration priority.

## Data Notes

- `data/blender_step6_t1_tn/` and `data/blender_test_suite/` are maintained
  synthetic benchmark datasets.
- `data/full_test/` is a larger end-to-end fixture.
- Generated logs, screenshots, and temporary point-cloud exports should not be
  committed unless they are promoted to a named benchmark fixture.

## Optional Integrations

- Headroom native compression runs through WSL `.venv-headroom`; Windows Python
  must keep a safe fallback.
- PaddleOCR is optional and should support reports/labels/documents, not core
  point-cloud deformation math.
- Docker compose starts Ollama/Chroma/headless services, not the desktop GUI.

