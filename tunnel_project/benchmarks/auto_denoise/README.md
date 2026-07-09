# Auto-Denoise Benchmark Folder

This folder groups the benchmark evidence for the automatic noise-removal feature.

## Files

| File | Purpose |
| --- | --- |
| `AUTO_DENOISE_BENCHMARKS.md` | Human-readable benchmark table with metrics, gates, commands, and interpretation. |
| `AUTO_DENOISE_BENCHMARKS.xlsx` | Excel version for filtering, review, and reporting. |

## Source Data And Scripts

| Source | Location |
| --- | --- |
| Blender benchmark report | `../../data/blender_test_suite/benchmark_report.json` |
| Blender benchmark command | `../../benchmark_blender_dataset.py` |
| Auto-denoise smoke test | `../../smoke_test_auto_denoise.py` |
| STSD validation CLI | `../../validate_auto_denoise_stsd.py` |
| STSD scoring adapter | `../../tunnel_analysis/datasets/stsd.py` |

## Standard Commands

Run from `tunnel_project/`:

```powershell
..\.venv\Scripts\python.exe smoke_test_auto_denoise.py
..\.venv\Scripts\python.exe benchmark_blender_dataset.py
```

If labelled STSD LAS files are available:

```powershell
..\.venv\Scripts\python.exe validate_auto_denoise_stsd.py <segment.las>
```

## Current Headline Metrics

- Noise recall: `0.8264`
- Lining retention: `0.9999`
- Raw points: `8,068`
- Clean points: `7,191`
- Removed points: `877`

Update the Markdown and Excel files whenever the benchmark report changes intentionally.