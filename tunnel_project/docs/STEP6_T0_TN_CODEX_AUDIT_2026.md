# Step 6 / T0-Tn Codex Audit - 2026-07-02

## Scope

Audited the Step 6 deformation workflow around T0/Tn registration, centerline-based sectioning, deformation metrics, section warnings, and the closest verification gate.

Primary files checked:

- `tunnel_analysis/registration.py`
- `tunnel_analysis/parameters.py`
- `tunnel_analysis/section_warnings.py`
- `verify_step6.ps1`
- Step 6 regression/smoke tests listed by `verify_step6.ps1`

## Verification Result

Command run from `tunnel_project/`:

```powershell
.\agent_verify.ps1 step6
```

Result: PASS.

The gate completed all 10 checks:

1. `test_t0_reference.py`
2. `test_register_epochs.py`
3. `test_curved_eccentricity.py`
4. `test_deformation_groundtruth.py`
5. `test_step6_evaluation.py`
6. `test_pipeline_end_to_end.py`
7. `test_2d_consistency.py`
8. `test_section_controls.py`
9. `test_section_widget.py`
10. `smoke_test_step6_t1_tn_dataset.py`

## What Looks Strong

- T0 detection is guarded for both normal epoch mode and the edge case where `active_index == 0` but monitoring points are already in the working buffers.
- `register_epochs` has both target-based and ICP fallback paths, and the existing tests check that localized deformation is not fully absorbed.
- Curved tunnel eccentricity has a regression guard so centerline bias does not become a false high eccentricity signal.
- Warning classification is centralized in `section_warnings.py`, and 2D/ruler/3D consistency is tested.
- Ground-truth synthetic deformation checks compare crown, convergence, and eccentricity magnitudes against expected millimeter-scale values.

## Highest-Value Next Actions

1. Done: `test_step6_evaluation.py` now reports warning precision and false-positive chainage span, not only recall. Current dataset checks confirm the ground-truth band is flagged while making broad warning spread visible.
2. Add an explicit clearance-intrusion assertion once the intended clearance detector behavior is defined. `test_step6_evaluation.py` prints `clearance violations: 0 sections` while the manifest says intrusion is present, but the test currently does not fail on it.
3. Add a registration stress test with asymmetric local deformation plus clutter. Existing registration tests cover rigid recovery and localized deformation preservation; a harder case would better protect against ICP absorbing deformation under nonuniform clutter.
4. Add a short benchmark note for `_ref_GROR` before any integration. Keep it as a comparison candidate only until current ICP/trimmed ICP has a measured weakness on local fixtures.
5. Add a small audit table mapping each warning type to its source metric, threshold, and UI consumer. This will make future threshold changes safer because dashboard, 2D track, ruler, and work-order output share the same classifier.

## Current Recommendation

Do not refactor Step 6 now. The verified path is healthy. The remaining best next code change is to clarify and assert the intended clearance-intrusion behavior, because the manifest contains a clearance intrusion but the current evaluation reports zero clearance-violation sections.
