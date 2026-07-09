# Section Tracker — SSL Tunnel Paper

Tracks writing status of each manuscript section. Updated after each writing session.

## Section Status

> **Full first draft assembled 2026-06-16** via ARS `academic-paper full`. All methodology + results sections drafted from source-verified parameters. Output: `drafts/main_paper_full_assembled.md` (~8645 words) and `drafts/SSL_Tunnel_Full_Paper_v1.docx`. Per-section sources in `drafts/sections/`. **Section order follows the Introduction: §9 = RAG, §10 = Output Generation** (this table previously had them swapped).

| # | Section | Status | Draft File | Version | Notes |
|---|---------|--------|-----------|---------|-------|
| - | Title + Keywords | done | `Intro_SSL_Tunnel_v7.docx` | v7 | (tracker previously cited a v8 that does not exist on disk; latest intro file is v7) |
| - | Abstract | done | `Intro_SSL_Tunnel_v7.docx` | v7 | 300 words, "reduces ovality bias" |
| 1 | Introduction | done | `Intro_SSL_Tunnel_v7.docx` | v7 | ARS peer-reviewed (7.4/10 Minor Revision → fixes applied). v5→v6: chronology/overclaims. v6→v7: fire≠deterioration, hedging |
| 2 | Related Work | draft v1 | `sections/section_02_related_work.md` | v1 | 4 themes + capability comparison Table 1 |
| 3 | System Architecture | draft v1 | `sections/section_03_system_architecture.md` | v1 | Pipeline (batch.py) + PipelineContext (Table 2) + module table (Table 3) |
| 4 | Data Preprocessing & Denoising | draft v1 | `sections/section_04_preprocessing.md` | v1 | range_crop + voxel + auto_denoise 3 stages + 30% guard (Contribution 1). Eqs 1-3 |
| 5 | Multi-Scan Registration | draft v1 | `sections/section_05_registration.md` | v1 | Target(Horn SVD) + FPFH/GROR + small_gicp/Open3D P2Plane + TrICP 0.80 |
| 6 | Frenet-Frame Geometric Analysis | draft v1 | `sections/section_06_frenet_geometry.md` | v1 | B-spline (smooth 0.5) + Kasa + gravity Frenet + adaptive eps (Contribution 2). Eqs 4-7 |
| 7 | Parameter Extraction | draft v1 | `sections/section_07_parameter_extraction.md` | v1 | crown/convergence/ovality(Fitzgibbon)/eccentricity/clearance. Eqs 8-11 |
| 8 | Multi-Epoch Change Detection | draft v1 | `sections/section_08_change_detection.md` | v1 | py4dgeo M3C2 + LoD + section warnings (10/25 mm) + T0→Tn trend. Eqs 12-13 |
| 9 | RAG Engineering Assistant | draft v1 | `sections/section_09_rag_assistant.md` | v1 | ChromaDB + all-MiniLM + Ollama qwen2.5:3b + offline fallback (Contribution 3) |
| 10 | Output Generation | draft v1 | `sections/section_10_output_generation.md` | v1 | IFC4/IFC4X3 + ReportLab PDF + CSV/Excel |
| 11 | Experimental Validation | draft v1 | `sections/section_11_validation.md` | v1 | Blender suite (Table 4) + registration (Table 5) + Frenet vs world-frame (Table 6) + limitations |
| 12 | Conclusion | draft v1 | `sections/section_12_conclusion.md` | v1 | Mirrors abstract + future work |
| - | References | extended | `sections/section_99_references_added.md` | v1 | [1]-[19] from intro + [20]-[29] added (Fitzgibbon, Kåsa, FPFH, GROR, VGICP, Open3D, DBSCAN, SBERT, py4dgeo, IFC4X3) — web-verified, DOIs pending citation-check |

## Evidence Readiness per Claim

| Claim | Evidence Status | Blocking? |
|-------|----------------|-----------|
| Noise recall 0.826, lining retention 0.9999 | benchmark_report.json exists | No — needs commit hash + figure |
| Radius error 0.0005% | benchmark_report.json exists | No — needs figure |
| Clearance 100% P/R | benchmark_report.json exists | No — needs figure |
| Registration RMSE | GICP 0.198mm (straight), 0.224mm (pipeline) | No — confirmed |
| Frenet vs world-frame ovality bias | +171.5% on curved, -2.1% on straight | No — confirmed |
| M3C2 T0/Tn deformation | Step6 smoke: 18/18 pass, polar_max=83.5mm | No — confirmed |
| IFC4X3 valid export | smoke test: 40 sections, alignment OK | No — confirmed |
| RAG retrieval accuracy | missing | Yes — need test set |
| KR/KDS compliance | placeholder mapping only | Yes — need clause-level fill |

## Writing Order (recommended)

Priority by dependency — write methodology sections first (they don't need evidence), then results.

1. Section 3 — System Architecture (no evidence needed, diagram only)
2. Section 4 — Preprocessing + Denoising (evidence partial, can write method)
3. Section 5 — Registration (can write method, evidence blocking for results)
4. Section 6 — Frenet Geometry (can write method, evidence blocking for results)
5. Section 7 — Parameter Extraction (depends on Section 6)
6. Section 8 — M3C2 Change Detection (depends on Section 7)
7. Section 9 — Output Generation (can write independently)
8. Section 10 — RAG Assistant (can write independently)
9. Section 2 — Related Work (best written after methodology is stable)
10. Section 11 — Experimental Validation (last — needs all evidence)
11. Section 12 — Conclusion (last)

## Rules Reference

All sections must follow: `reviews/WRITING_RULES.md`

## File Naming Convention

- Markdown source: `drafts/sections/section_XX_name.md`
- DOCX generation script: `templates/create_section_XX.js`
- DOCX output: `drafts/sections/Section_XX_Name_vN.docx`
- Review notes: `reviews/section_XX_review.md`
