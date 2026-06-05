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

## Open Decisions To Reconfirm Before Major Changes

- Which clean-noise benchmark version is currently the best measured baseline.
- Exact deformation threshold for warnings in millimeters.
- Which datasets are authoritative for MATLAB-vs-tool comparison.
- Whether memory/learn mode in Headroom should be enabled after code-aware proxy proves stable.
