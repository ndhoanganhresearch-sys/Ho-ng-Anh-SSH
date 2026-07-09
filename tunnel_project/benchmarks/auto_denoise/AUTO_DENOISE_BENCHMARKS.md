# Auto-Denoise Benchmark Table

This file tracks benchmark evidence for the automatic noise-removal feature. Use it before changing `PreprocessingLayer.auto_denoise()` or related cable/light/person/wall-cable filtering logic.

## Current Benchmark Summary

| Benchmark | Dataset / Fixture | Command | Metric | Pass Gate | Current Result | Status | Source Report |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Blender noise and cables | `data/blender_test_suite/case_03_noise_and_cables` | `..\.venv\Scripts\python.exe benchmark_blender_dataset.py` | Noise recall | `>= 0.40` | `0.8264` | PASS | `data/blender_test_suite/benchmark_report.json` |
| Blender noise and cables | `data/blender_test_suite/case_03_noise_and_cables` | `..\.venv\Scripts\python.exe benchmark_blender_dataset.py` | Lining retention | `>= 0.75` | `0.9999` | PASS | `data/blender_test_suite/benchmark_report.json` |
| Blender noise and cables | `data/blender_test_suite/case_03_noise_and_cables` | `..\.venv\Scripts\python.exe benchmark_blender_dataset.py` | Raw points | informational | `8,068` | INFO | `data/blender_test_suite/benchmark_report.json` |
| Blender noise and cables | `data/blender_test_suite/case_03_noise_and_cables` | `..\.venv\Scripts\python.exe benchmark_blender_dataset.py` | Clean points | informational | `7,191` | INFO | `data/blender_test_suite/benchmark_report.json` |
| Blender noise and cables | `data/blender_test_suite/case_03_noise_and_cables` | `..\.venv\Scripts\python.exe benchmark_blender_dataset.py` | Removed points | informational | `877` | INFO | `data/blender_test_suite/benchmark_report.json` |
| Auto-denoise smoke | Synthetic shell + clutter/cable fixtures | `..\.venv\Scripts\python.exe smoke_test_auto_denoise.py` | Cable recall | `>= 0.70` | run command to refresh | TRACKED | `smoke_test_auto_denoise.py` |
| Auto-denoise smoke | Synthetic shell + clutter/cable fixtures | `..\.venv\Scripts\python.exe smoke_test_auto_denoise.py` | Lining retention | `>= 0.90` | run command to refresh | TRACKED | `smoke_test_auto_denoise.py` |
| STSD labelled LAS | External STSD labelled tunnel LAS files | `..\.venv\Scripts\python.exe validate_auto_denoise_stsd.py <segment.las>` | Noise precision / recall / F1 / lining retention | dataset-dependent | no local STSD result stored | OPTIONAL | `validate_auto_denoise_stsd.py` |

## Latest Blender Report Detail

From `data/blender_test_suite/benchmark_report.json`, case `case_03_noise_and_cables`:

| Field | Value |
| --- | --- |
| `n_raw` | `8,068` |
| `n_clean` | `7,191` |
| `n_removed` | `877` |
| `n_radial` | `877` |
| `n_cable` | `0` |
| `n_light` | `0` |
| `n_person` | `0` |
| `n_wall_cable` | `0` |
| `label_noise_recall` | `0.8264150943396227` |
| `label_lining_retention` | `0.999857305936073` |
| `labels_present` | `1, 2, 3` |

## Interpretation

- The current Blender benchmark removes about `82.64%` of labelled removable noise.
- The current Blender benchmark preserves about `99.99%` of labelled tunnel lining.
- This is well above the current project gates of `0.40` noise recall and `0.75` lining retention.
- The detected removal in this fixture is counted mostly as `n_radial`, not semantic `n_cable` / `n_light` / `n_person`.

## Relevant Files

| File | Purpose |
| --- | --- |
| `tunnel_analysis/preprocessing.py` | Implements auto-denoise and related filtering logic. |
| `benchmark_blender_dataset.py` | Runs Blender synthetic benchmark and writes JSON report. |
| `data/blender_test_suite/benchmark_report.json` | Current saved benchmark report. |
| `smoke_test_auto_denoise.py` | Synthetic smoke tests for clutter/cable removal and lining preservation. |
| `validate_auto_denoise_stsd.py` | CLI benchmark for external STSD labelled LAS files. |
| `tunnel_analysis/datasets/stsd.py` | STSD adapter and precision/recall/F1 scoring logic. |
| `BENCHMARK_WORKFLOW.md` | Project-wide benchmark promotion rules. |

## Promotion Rule For Auto-Denoise Changes

Before promoting a denoise change:

1. Run `..\.venv\Scripts\python.exe smoke_test_auto_denoise.py`.
2. Run `..\.venv\Scripts\python.exe benchmark_blender_dataset.py`.
3. Compare `label_noise_recall` and `label_lining_retention` against this table.
4. If using external labelled STSD data, run `validate_auto_denoise_stsd.py` and record precision, recall, F1, and lining retention.
5. Update this file and `BENCHMARK_BASELINES.md` only if the change intentionally replaces the baseline.