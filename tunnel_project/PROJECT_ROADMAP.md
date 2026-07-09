# SSL Tunnel Analysis Roadmap

This roadmap keeps the project focused on the highest-value path: stable T0/Tn deformation analysis first, benchmark hardening second, and AI/document automation third.

## Current North Star

Build a reproducible tunnel point-cloud inspection workflow that loads T0/Tn scans, aligns epochs, detects local deformation, shows evidence in 2D/3D, and produces auditable reports.

## Phase 1 - Core Stability

Goal: make the main engineering workflow reliable enough to trust before adding more features.

- Freeze `run_tunnel_analysis.py` -> `tunnel_analysis/` as the only maintained app path.
- Keep Step 6 / T0-Tn as the primary value path: registration, centerline, section deltas, warning mapping.
- Stabilize local warnings so only affected sections/chainage ranges are highlighted in both 2D and 3D.
- Protect known edge cases: curved tunnels, portal clearance, shifted scanner setups, local deformation spots.
- Keep UI changes small and verify widget fit, button order, and step dispatch after each workflow edit.

Exit criteria:

- `.\agent_verify.ps1 quick` passes.
- `.\agent_verify.ps1 step6` passes after deformation/registration/section changes.
- No active task depends on legacy `TunnelApp.py`, `main_app.py`, or `New folder/` prototypes.

## Phase 2 - Benchmark Hardening

Goal: make every algorithm improvement measurable and reversible.

- Create a small "golden fixture" list for local deformation, curved tunnel, clearance portal, box shift, and four-spots cases.
- Record best-known metrics for each fixture before promoting new algorithm changes.
- Require benchmark evidence before claiming improvements in denoising, registration, centerline, or deformation detection.
- Keep generated data out of commits unless it is promoted to a named benchmark fixture with a README/manifest.
- Add or update regression tests when a bug fix protects a real project decision.

Exit criteria:

- Each core algorithm area has at least one named regression or smoke test.
- Important benchmark fixtures have provenance notes, commands, and expected behavior.
- New changes can be compared against a known baseline instead of relying on visual judgment only.

## Phase 3 - AI And Document Automation

Goal: use AI where it adds engineering productivity without weakening the point-cloud math.

- Keep AI out of core deformation math unless a benchmark proves value.
- Use RAG for standards, reports, inspection notes, material passports, benchmark summaries, and work orders.
- Evaluate a lightweight vector-search backend only if current RAG search becomes slow or hard to maintain.
- Keep Headroom optional on Windows and verify native compression through WSL when touching that path.
- Use OCR for labels, drawings, reports, and inspection images, not as a dependency for core scan comparison.

Exit criteria:

- `.\agent_verify.ps1 ai` passes after Headroom/RAG/digital-twin edits.
- AI-generated reports cite project evidence: input files, benchmark results, thresholds, section IDs, and limitations.
- AI features improve review/reporting workflow without changing verified numerical results unexpectedly.

## Operating Rules For Claude Code

- Start every non-trivial task with investigation and a short plan.
- Fix root causes with minimal edits; do not refactor unrelated modules.
- Run the nearest verification gate before reporting completion.
- Summarize changed files, commands run, test results, and remaining risks.
- Update this roadmap only when project priorities actually change.

## Verification Gates

- `.\agent_verify.ps1 quick` : compile + core smokes/guards
- `.\agent_verify.ps1 step6` : T0/Tn deformation regression gate
- `.\agent_verify.ps1 box` : restored box fixture smokes
- `.\agent_verify.ps1 weekly` : quick + box
- `.\agent_verify.ps1 ai` : optional AI/headroom path

Publication work is frozen to Phase 1 preparation only until Phase 1 exit criteria are complete.

## Suggested Next Tasks

1. Commit `test_clearance_portal_guard.py` and `test_clearance_robust.py` as Phase 2 clearance regressions.
2. Expand `BENCHMARK_BASELINES.md` with measured numeric results for remaining golden fixtures.
3. Add CI or a local scheduled check that runs `agent_verify.ps1 quick` and the Step 6 gate before major commits.
4. Review legacy/prototype references and remove them from docs unless they are intentionally preserved.
5. Audit RAG/AI outputs so work orders and reports always include evidence and limitations.
