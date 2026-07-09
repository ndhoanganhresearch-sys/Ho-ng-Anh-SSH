# Paper Workspace — SSL Smart Tunnel Monitoring System

Target journals: CACAIE, Automation in Construction, Advanced Engineering Informatics.

## Quick Start for Writing

1. Check `SECTION_TRACKER.md` — see which section to write next and its status.
2. Read `reviews/WRITING_RULES.md` — mandatory style rules for every section.
3. Read `CODE_TO_PAPER_MAP.md` — find which module/function/parameter to reference.
4. Verify parameters in source code before writing (code changes, paper must match).
5. Write section in `drafts/sections/section_XX_name.md`.
6. Generate DOCX via script in `templates/create_section_XX.js`.
7. Output to `drafts/sections/Section_XX_Name_vN.docx`.

## Folder Structure

```
paper/
  README.md                  # This file
  SECTION_TRACKER.md         # Section-by-section writing status + evidence readiness
  CODE_TO_PAPER_MAP.md       # Module -> paper claim mapping table
  generate_working_docx.py   # Script to regenerate full working DOCX
  drafts/
    intro/                   # Introduction versions (v1-v5)
      Intro_SSL_Tunnel_v5.docx       # LATEST intro (ARS-reviewed, lab-style)
      Intro_SSL_Tunnel_v5_extracted.md # Plain-text extraction of v5
    sections/                # Per-section drafts (new, to be populated)
    main_paper_working.md    # Full manuscript working draft (softened claims)
  reviews/
    WRITING_RULES.md         # Mandatory writing rules (10 sections, 13-item checklist)
    Intro_SSL_Tunnel_v3_review.md  # Review notes for intro v3
  templates/
    create_intro_v5.js       # docx-js script for intro v5 generation
  generated/
    PAPER_DRAFT_V2.md        # Earlier full manuscript (has placeholders, strong claims)
    PAPER_SSL_Tunnel_V2.docx # Word export of V2
    SSL_Tunnel_main_paper_working.docx  # Word export of working draft
    RESEARCH_WORKFLOW.md     # Research pipeline definition
    MATERIAL_PASSPORT.md     # Evidence template
    PAPER_REVIEW_CHECKLIST.md # Submission readiness checklist
    ACADEMIC_SETUP_REVIEW.md # Repo readiness audit (scored 3-8/10)
  evidence/
    benchmark_reports/       # Frozen benchmark data for manuscript claims
      VALIDATION_EVIDENCE_TODO.md  # Which claims have evidence, which don't
    figures/                 # Publication-quality figures
    tables/                  # Final result tables
    passports/               # Material passports (one per figure/table/claim)
      auto_denoise_blender_001.md  # Denoising benchmark passport (partial)
    standards_mapping/       # Metric -> KR/KDS clause mapping
      KR_KDS_metric_mapping.md     # Placeholder — must fill before compliance claims
  references/                # Literature and standards PDFs
  external_archive/          # Lab journal papers, CVPR papers (style references)
```

## Key Rules

1. Never claim "in compliance with KR C-08080 / KDS 27 25 00" until `evidence/standards_mapping/KR_KDS_metric_mapping.md` has exact clauses and thresholds.
2. Never cite a code parameter without verifying it in current source code.
3. Every quantitative claim in the paper needs a material passport in `evidence/passports/`.
4. All sections follow `reviews/WRITING_RULES.md` — no exceptions.
5. Evidence blocking a section is tracked in `SECTION_TRACKER.md`.

## Current Status (2026-06-12)

- Introduction: v5 done (ARS-reviewed, lab-style matched, 20 references)
- Methodology sections 2-10: not started
- Evidence package: partial (denoising only), 5 claims blocked
- Standards mapping: placeholder only

## Source Sync

Original external writing folder: `C:\Users\ssl\Desktop\3 tháng viết báo\draf\`

The Desktop folder is the user's primary editing location. Files are copied here for version control integration. The Desktop folder was not deleted or modified.
