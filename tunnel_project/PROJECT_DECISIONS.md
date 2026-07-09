# Project Decisions

This file stores stable project decisions so Codex, Claude Code, and future agents do not rediscover or overwrite them accidentally.

## Current Workflow Decisions

- Step 8 is hidden in the current UI workflow.
- Plot 2D belongs below step 6.
- Step 6 should connect to the rest of the workflow through T0/Tn loaded at step 1.
- T0 is the reference version; Tn is compared against T0 for deformation and warnings.
- Deformation warnings should mark only the affected tunnel sections, not the whole tunnel.
- Deformation warning visibility must be checked in both 2D and 3D.
- For version comparison, use the first or best benchmarked version as the baseline and compare version 2 against it.
- Headroom native compression is installed in WSL at `.venv-headroom`; Windows Python has a safe optional adapter fallback.

## Locked Numeric / Dataset Decisions (from current code & benchmarks)

Documented from live code/benchmarks; do not change algorithm values in this note alone.

- Section warning thresholds (`tunnel_analysis/section_warnings.py`):
  - absolute section delta: CAUTION `10.0 mm`, CRITICAL `25.0 mm`
  - ovality: CAUTION `0.5%`, CRITICAL `1.0%`
  - eccentricity: CAUTION `10.0 mm`, CRITICAL `25.0 mm`
- Clean-noise baseline currently locked to Blender fixture `data/blender_test_suite/case_03_noise_and_cables`:
  - noise recall `0.8264`
  - lining retention `0.9999`
  - source: `benchmarks/auto_denoise/AUTO_DENOISE_BENCHMARKS.md` / `data/blender_test_suite/benchmark_report.json`
- Authoritative local datasets:
  - deformation correctness: `data/time_series_deformation`
  - Step 6 T1/Tn smoke pair: dataset used by `smoke_test_step6_t1_tn_dataset.py`
  - registration / local-defect box fixtures: `data/box_four_spots`, `data/box_icp_shift`
  - denoise: `data/blender_test_suite/case_03_noise_and_cables`

## Reference Repo Policy

- `_ref_*` and `_ref_trending/*` are read-only references.
- Do not call a reference "integrated" unless adapter code + test + provenance note exist in this project.
- Do not modify reference clones during normal app development tasks.

## Open Decisions To Reconfirm Before Major Changes

- MATLAB-vs-tool comparison dataset pair is still **not locked** (no authoritative external pair promoted yet).
- Whether memory/learn mode in Headroom should be enabled after code-aware proxy proves stable.
