# Validation Evidence Register

Last updated: 2026-06-12 | Commit: 84c02cc

| Claim Area | Required Artifact | Status | Evidence File |
|---|---|---|---|
| Auto-denoise | Benchmark + passport | DONE | `benchmark_report.json`, `passports/auto_denoise_blender_001.md` |
| Registration RMSE | RMSE table (GICP vs Open3D) | DONE | `benchmark_results_20260612.md` Section 2, `passports/registration_benchmark_001.md` |
| Frenet vs world-frame | Ovality comparison table | DONE | `frenet_vs_worldframe.json`, `passports/frenet_vs_worldframe_001.md` |
| Deformation detection | T0/Tn warning sections | DONE | `benchmark_report.json` case_02 + Step6 smoke 18/18 |
| Clearance | Precision/recall vs labels | DONE | `benchmark_report.json` case_04: P=1.0, R=1.0 |
| Centerline accuracy | Radius error on reference | DONE | `benchmark_report.json` case_01: 4.00002m |
| IFC export | Valid file + components | DONE | smoke_test_ifc_export: 40 sections, IFC4X3 alignment |
| PDF report | Generated file + valid header | DONE | smoke_test_pdf_reporter: 117KB |
| Pipeline timing | Per-stage breakdown | DONE | `benchmark_results_20260612.md` Section 3 |
| RAG retrieval accuracy | Test set + ground-truth | MISSING | Need QA test set with expected answers |
| KR/KDS compliance | Clause-level mapping | PARTIAL | Thresholds in code but clauses UNVERIFIED |

## Summary

- 9/11 evidence items: DONE
- 1/11: MISSING (RAG)
- 1/11: PARTIAL (KR/KDS)

## Non-Blocking Gaps

The RAG and KR/KDS gaps do NOT block methodology sections (3-10). They only block:
- Section 11 (Validation) — RAG accuracy claim
- Any sentence claiming "in compliance with KR C-08080" — use softer wording per standards_mapping recommendation
