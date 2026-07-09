# Standards Mapping — KR C-08080 / KDS 27 25 00

Last updated: 2026-06-12 | Commit: 84c02cc

## Rule

Do NOT write "in compliance with KR C-08080 / KDS 27 25 00" in the manuscript until every row below has Status = VERIFIED.

## Current Status: PARTIALLY VERIFIED

The thresholds below are implemented in the code but their mapping to specific standard clauses requires verification against the original Korean standard documents.

## Metric-to-Standard Mapping

| Paper Metric | Code Value (caution/critical) | Module | Claimed Standard | Clause | Status |
|---|---|---|---|---|---|
| Crown settlement | 10 / 25 mm | `common.py:280`, `rag_ai.py:18` | KR C-08080 | TBD | UNVERIFIED |
| Lateral convergence | 15 / 30 mm | `common.py:281`, `rag_ai.py:25` | KR C-08080 | TBD | UNVERIFIED |
| Ovality | 0.5 / 1.0 % | `common.py:282`, `section_warnings.py:66-67` | KDS 27 25 00 | TBD | UNVERIFIED |
| Eccentricity | 10 / 25 mm | `common.py:283`, `rag_ai.py:38` | KDS 27 25 00 | TBD | UNVERIFIED |
| Section delta (height/width/radius) | 10 / 25 mm | `section_warnings.py:16-17` | — | — | PROJECT DEFAULT |
| Clearance intrusion | 10 / 50 mm | `clearance.py:31-32` | — | — | PROJECT DEFAULT |

## Known Issues

1. **KR C-08080 Rev.3** as downloaded is a **railway bridge** standard (track-structure interaction), NOT a tunnel deformation standard. The tunnel-specific clauses may be in a different section or a companion document.
2. **KDS 27 25 00** PDF has not been located locally in the project. The standard exists but clause-level text has not been extracted.
3. All thresholds in `STANDARD_PARAMETERS.md` are marked `unverified` by the project itself.

## Recommended Paper Wording

Instead of "in compliance with KR C-08080", use:

> "The system implements configurable deformation thresholds informed by Korean railway safety standards (KR C-08080, KDS 27 25 00). Default values follow engineering practice for tunnel SHM: crown settlement caution at 10 mm / critical at 25 mm, lateral convergence caution at 15 mm / critical at 30 mm, ovality caution at 0.5% / critical at 1.0%."

This is factually accurate without claiming formal compliance.

## Action Items

- [ ] Obtain tunnel-specific sections of KR C-08080 (not bridge sections)
- [ ] Locate KDS 27 25 00 full document and extract tunnel deformation clauses
- [ ] Map each threshold to exact clause number
- [ ] Update this table with VERIFIED status
- [ ] Only then write "in compliance with" in the paper
