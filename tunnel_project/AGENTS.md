# Tunnel Project Agent Guide

This project is a Python tunnel point-cloud analysis tool. It includes a PyQt/PyVista UI, point-cloud preprocessing, centerline extraction, section analysis, registration, T0/Tn deformation comparison, warning visualization, IFC/PDF export, and local AI assistance.

## Operating Rules

- Keep changes scoped to the requested workflow. Do not refactor unrelated modules while fixing a feature.
- Never revert user changes or generated benchmark artifacts unless explicitly asked.
- Prefer existing local modules and smoke tests over new abstractions.
- Treat benchmark numbers as first-class evidence. Do not claim an algorithm is better without a measured comparison.
- Preserve the T0/Tn workflow: T0 is the reference version, Tn is the compared version, and warnings should be tied to local section/deformation evidence.
- For deformation warning work, verify both 2D and 3D visibility and ensure only affected sections are highlighted.
- For clean-noise work, compare against the current best baseline before promoting a new implementation.
- For UI changes, verify section/plot widgets fit the window and that step controls stay in their intended workflow order.
- Keep Headroom optional in Windows Python; full native Headroom compression currently runs through WSL `.venv-headroom`.
- Keep PaddleOCR optional; use it for reports, standards, labels, tables, and inspection images, not for point-cloud deformation math.

## Preferred Verification

Run focused checks first, then broader checks when shared behavior changes.

```powershell
..\.venv\Scripts\python.exe -m py_compile tunnel_analysis\headroom_adapter.py tunnel_analysis\rag_ai.py tunnel_analysis\digital_twin.py
..\.venv\Scripts\python.exe smoke_test_headroom_adapter.py
..\.venv\Scripts\python.exe smoke_test_advanced_integrations.py
```

For WSL Headroom verification:

```powershell
wsl --cd "C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project" .venv-headroom/bin/python smoke_test_headroom_adapter.py
powershell -NoProfile -Command "(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8787/livez -TimeoutSec 10).Content"
```

## Review Focus

- Python runtime errors, imports, and PyQt signal/slot issues.
- Threading and worker lifecycle in the UI.
- Deformation thresholds, unit conversion, section indexing, and 2D/3D mapping.
- Benchmark regressions in clean noise, registration, centerline, and T0/Tn comparison.
- Large point-cloud memory behavior on a 32 GB workstation.

## Selected ECC Influence

This guide selectively adapts ECC ideas: Python review discipline, benchmark optimization loops, build-error recovery, verification loops, and lightweight security hygiene. Do not run the full ECC installer or enable full hooks/MCP packs unless the user explicitly asks.
