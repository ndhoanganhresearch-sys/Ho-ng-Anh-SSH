# Academic Paper Setup Review

Reviewed: 2026-06-12
Repo: `tunnel_project`

## Verdict

The repository is partially set up for writing an academic paper from the project. It has a good research workflow, paper drafts, a paper checklist, standards documents, benchmark tracking, and implemented code modules that match many manuscript claims. However, it is not yet fully paper-ready because the evidence package is incomplete and the current draft still contains placeholders and over-strong claims.

## What is already good

- `RESEARCH_WORKFLOW.md` defines a sensible paper pipeline: research question, literature matrix, benchmark protocol, material passport, and review checklist.
- `MATERIAL_PASSPORT.md` provides a strong evidence template for every figure/table/claim.
- `PAPER_REVIEW_CHECKLIST.md` correctly blocks unsupported claims, missing commit hashes, missing dataset IDs, and unreproducible figures.
- `PAPER_DRAFT.md`, `PAPER_DRAFT_V2.md`, and generated DOCX files exist, so the repo already has a manuscript-generation path.
- `generate_paper_v2.py` can convert the Markdown paper draft into a Word document.
- `docs/standards/` contains Korean standards PDFs/OCR/text/register files, useful for standards-based claims.
- Code modules implement many claimed components: auto-denoise, Frenet/section geometry, parameters, M3C2/time-series, IFC export, PDF reporting, RAG/AI assistant, and UI hooks.
- `benchmarks/auto_denoise/` contains a real benchmark table with metrics and commands.

## Gaps before the paper is ready

- `PAPER_DRAFT_V2.md` still contains placeholders in the experimental validation section: `[N]`, `[location]`, `[scanner model]`, `[X]`, `[Y]`, `[Z]`, `[W]`.
- Only auto-denoise has a clearly organized benchmark evidence folder. Registration, Frenet slicing, M3C2/change detection, IFC export, PDF reporting, and RAG assessment do not yet have equivalent benchmark/evidence folders.
- The paper claims “validated,” “full compliance,” “engineering-grade,” and “direct handover” more strongly than the current evidence package supports.
- Material passports appear to be a template only; there are no completed passports tied to specific figures, tables, datasets, commands, and commit hashes.
- The standards documents exist locally, but the manuscript still needs clause-level mapping: metric -> KR/KDS clause -> threshold -> implementation field -> test evidence.
- Some references and incident claims need verification before submission.
- Generated DOCX exists, but journal-ready reproducibility is still weak unless benchmark reports, figures, commands, and commit hashes are frozen.

## Readiness Score

- Code-to-paper alignment: 7/10
- Research workflow setup: 8/10
- Evidence/reproducibility package: 4/10
- Manuscript readiness: 5/10
- Submission readiness: 3/10

## Recommended next actions

1. Create `paper_evidence/` with subfolders for `figures/`, `tables/`, `passports/`, `benchmark_reports/`, and `standards_mapping/`.
2. Fill one material passport per planned result figure/table.
3. Replace all placeholders in `PAPER_DRAFT_V2.md` with benchmark-backed values or remove the claim.
4. Add benchmark summaries for registration, Frenet-frame section extraction, deformation/change detection, and report/IFC output.
5. Create a standards mapping table for KR C-08080 and KDS 27 25 00.
6. Verify references and remove any unverified incident claims.
7. Rephrase the paper as an end-to-end prototype with benchmark evidence, not a fully certified engineering system unless formal validation exists.

## Bottom line

The repo is well prepared as a development-to-paper workspace, but not yet fully prepared as a defensible academic submission package. It has the right scaffolding; the main missing piece is completed, reproducible evidence tied to the manuscript claims.
