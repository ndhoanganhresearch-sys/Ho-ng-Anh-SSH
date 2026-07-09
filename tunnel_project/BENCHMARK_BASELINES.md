# Benchmark Baselines

This file records the best-known regression and benchmark expectations for fixtures that protect project decisions. Update it only when a measured change intentionally replaces a baseline.

For auto-denoise-specific metrics, gates, and current Blender benchmark results, see `benchmarks/auto_denoise/AUTO_DENOISE_BENCHMARKS.md`.

## How To Use

- Run the nearest test before changing an algorithm.
- Record the old result, candidate result, command, and commit/context when promoting a change.
- Do not claim an algorithm is better unless this file or a benchmark report shows measured evidence.
- Keep generated data out of commits unless it is promoted to a named fixture with provenance notes.

## Golden Fixtures

| Area | Fixture/Test | Protected Behavior | Gate |
| --- | --- | --- | --- |
| Clearance portal guard | `test_clearance_portal_guard.py` | Long-tunnel portal sections are ignored for incomplete-ring clearance false positives; mid-tunnel and short-run violations still flag. | `..\.venv\Scripts\python.exe test_clearance_portal_guard.py` |
| Robust clearance | `test_clearance_robust.py` | A single or sub-1% inner stray point does not condemn a section; genuine >=1% intrusion still flags. | `..\.venv\Scripts\python.exe test_clearance_robust.py` |
| T0 reference | `test_t0_reference.py` | Step 6 uses T0 as reference and preserves expected comparison semantics. | `.\agent_verify.ps1 step6` |
| Epoch registration | `test_register_epochs.py`, `test_register_guard.py` | Tn alignment does not erase local deformation and does not make long-tunnel divergence worse. | `.\agent_verify.ps1 step6` |
| Curved tunnel eccentricity | `test_curved_eccentricity.py` | Curved clean tunnel avoids false high eccentricity from centerline bias. | `.\agent_verify.ps1 step6` |
| Ground-truth deformation | `test_deformation_groundtruth.py`, `test_step6_evaluation.py` | Local deformation warnings match known synthetic/ground-truth behavior. | `.\agent_verify.ps1 step6` |
| 2D/3D consistency | `test_2d_consistency.py`, `test_section_controls.py`, `test_section_widget.py` | Warning sections stay consistent between section logic and UI controls. | `.\agent_verify.ps1 step6` |
| Box fixtures | `smoke_test_box_four_spots.py`, `smoke_test_box_icp_shift.py` | Box-shaped profiles and shifted scanner setups remain detectable after profile/registration changes. | `.\agent_verify.ps1 box` |

## Current Locked Baselines

### Box Four Spots (restored 2026-07-09)

- Fixture: `data/box_four_spots` (restored from git HEAD)
- Command: `..\.venv\Scripts\python.exe smoke_test_box_four_spots.py`
- Result: `BOX FOUR SPOTS SMOKE PASSED`
- Measured note: `profile=Box crown_max=43.4mm conv_max=36.3mm ecc_max=88.6mm`
- Gate: `.\agent_verify.ps1 box`

### Box ICP Shift (restored 2026-07-09)

- Fixture: `data/box_icp_shift` (restored from git HEAD)
- Command: `..\.venv\Scripts\python.exe smoke_test_box_icp_shift.py`
- Result: `BOX ICP SHIFT SMOKE PASSED`
- Measured note: `method=icp rmse=0.0mm gap=7.71m->0.03m`
- Gate: `.\agent_verify.ps1 box`

### Clearance Portal Guard

- Command: `..\.venv\Scripts\python.exe test_clearance_portal_guard.py`
- Expected: `CLEARANCE PORTAL GUARD OK`
- Checks: 6 pass, 0 fail
- Decision protected: portal mouth sections in long tunnels should not trigger false global clearance-critical reports, while mid-tunnel clearance violations remain critical.

### Robust Clearance Percentile

- Command: `..\.venv\Scripts\python.exe test_clearance_robust.py`
- Expected: `ROBUST CLEARANCE OK`
- Checks: 5 pass, 0 fail
- Decision protected: clearance is flagged using a robust 1st-percentile signed distance so isolated inner noise does not create a false section-level clearance violation.

## Promotion Checklist

Before replacing a baseline:

1. Save the old command and result.
2. Run the candidate command/result on the same fixture.
3. Explain why the candidate is better or safer.
4. Add or update a regression test if the change protects a project decision.
5. Update `PROJECT_DECISIONS.md` when the decision changes.
6. Run the relevant `agent_verify.ps1` gate before handoff.