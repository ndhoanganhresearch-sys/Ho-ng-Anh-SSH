# Verification Checklist

Use this checklist after code changes. Keep verification proportional to the blast radius.

## Small Python Change

```powershell
..\.venv\Scripts\python.exe -m py_compile <changed_files>
```

Then run the nearest smoke test.

## AI / Headroom Change

```powershell
..\.venv\Scripts\python.exe -m py_compile tunnel_analysis\headroom_adapter.py tunnel_analysis\rag_ai.py tunnel_analysis\digital_twin.py
..\.venv\Scripts\python.exe smoke_test_headroom_adapter.py
wsl --cd "C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project" .venv-headroom/bin/python smoke_test_headroom_adapter.py
```

Expected WSL result should show real compression, for example token savings and a nonzero ratio.

## Deformation / T0-Tn Change

- Run the focused deformation or advanced integration smoke test.
- Verify warning counts and section indices.
- Inspect 2D and 3D views if UI behavior changed.
- Confirm only local affected sections are highlighted.

## Clean Noise Change

- Run the auto-denoise smoke test.
- Run STSD/labeled validation when available.
- Compare against the best measured baseline in `BENCHMARK_WORKFLOW.md` format.

## UI Change

- Launch the app if feasible.
- Check that section widgets fit the window.
- Check that plot buttons and workflow steps remain in the intended order.
- Avoid nested UI cards or oversized text in compact controls.

## Before Commit

```powershell
git status --short
git diff --stat
```

Summarize changed files, tests run, and remaining risks.
