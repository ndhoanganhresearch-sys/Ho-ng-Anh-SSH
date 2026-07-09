# Standard Parameters Register

This register is the working source for comparing project parameters against external standards and internal engineering assumptions. Keep it updated whenever a parameter changes, a new source is found, or a claim becomes verified.

## Status Legend

- `verified` = directly supported by a source document and traceable to a page/section.
- `unverified` = currently used in code or reports, but no direct source match has been confirmed yet.
- `project default` = internal app default or engineering assumption, not claimed as a standard.
- `needs review` = likely relevant, but the current source or mapping is incomplete.

## Register

| Area | Parameter | Current Value | Unit | Code Location | Source Claim in Code | Document Source | Page / Section | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Clearance | Box width | 3.0 | m | `tunnel_analysis/common.py:100`, `tunnel_analysis/rag_ai.py:49` | Korean railway clearance envelope | Not yet verified in a local standard PDF | Not found | unverified | Treat as project default until a proper clearance standard is linked. |
| Clearance | Box height | 4.5 | m | `tunnel_analysis/common.py:101`, `tunnel_analysis/rag_ai.py:49` | Korean railway clearance envelope | Not yet verified in a local standard PDF | Not found | unverified | Same as above. |
| Clearance | Circle radius | 4.0 | m | `tunnel_analysis/common.py:102` | Internal app default | None yet | None | project default | App geometry constant, not a direct standard claim. |
| Settlement | Crown settlement caution | 10 | mm | `tunnel_analysis/common.py:280`, `tunnel_analysis/rag_ai.py:18` | KR C-08080 summary | Current KR C-08080 PDF does not show this tunnel threshold | Not found | unverified | Must not be cited as confirmed by current PDF. |
| Settlement | Crown settlement critical | 25 | mm | `tunnel_analysis/common.py:280`, `tunnel_analysis/rag_ai.py:18` | KR C-08080 summary | Current KR C-08080 PDF does not show this tunnel threshold | Not found | unverified | Same as above. |
| Convergence | Lateral convergence caution | 15 | mm | `tunnel_analysis/common.py:281`, `tunnel_analysis/rag_ai.py:22` | Tunnel safety summary | Current KR C-08080 PDF shows bridge longitudinal displacement, not tunnel convergence | KR C-08080 p.14-15, sec. 5.1.3 (bridge) | needs review | Possible conceptual mismatch. |
| Convergence | Lateral convergence critical | 30 | mm | `tunnel_analysis/common.py:281`, `tunnel_analysis/rag_ai.py:23` | Tunnel safety summary | Current KR C-08080 PDF shows `±30 mm` for bridge longitudinal displacement | KR C-08080 p.14-15, sec. 5.1.3 (bridge) | needs review | Do not reuse as tunnel convergence until matched to tunnel document. |
| Ovality | Caution | 0.5 | % | `tunnel_analysis/common.py:282`, `tunnel_analysis/rag_ai.py:26` | KDS 27 25 00 summary | Not yet verified in a local standard PDF | Not found | unverified | Needs a proper KDS tunnel source. |
| Ovality | Critical | 1.0 | % | `tunnel_analysis/common.py:282`, `tunnel_analysis/rag_ai.py:26` | KDS 27 25 00 summary | Not yet verified in a local standard PDF | Not found | unverified | Needs a proper KDS tunnel source. |
| Eccentricity | Caution | 10 | mm | `tunnel_analysis/common.py:283`, `tunnel_analysis/rag_ai.py:38` | KDS 27 25 00 summary | Current KR C-08080 PDF shows `10 mm` in bridge end displacement context | KR C-08080 p.15, sec. 5.1.4 (bridge) | needs review | Source context does not match tunnel eccentricity. |
| Eccentricity | Critical | 25 | mm | `tunnel_analysis/common.py:283`, `tunnel_analysis/rag_ai.py:38` | KDS 27 25 00 summary | Not yet verified in a local standard PDF | Not found | unverified | Needs a proper KDS tunnel source. |
| Clearance | Minimum clearance | always maintained | rule | `tunnel_analysis/rag_ai.py:47` | Korean Railway Act Article 26 | Not yet verified locally | Not found | unverified | Keep as a safety statement until a primary legal/source citation is linked. |
| QC | Registration RMSE target | < 2 | mm | `tunnel_analysis/rag_ai.py` | AI summary | Not yet verified locally | Not found | unverified | Treat as engineering target, not standard claim. |
| QC | Heatmap stable band | < 1 | mm | `tunnel_analysis/rag_ai.py` | AI summary | Not yet verified locally | Not found | project default | Useful visualization rule, not a standard requirement. |
| QC | Heatmap caution band | 1-3 | mm | `tunnel_analysis/rag_ai.py` | AI summary | Not yet verified locally | Not found | project default | Useful visualization rule, not a standard requirement. |
| QC | Heatmap critical band | > 3 | mm | `tunnel_analysis/rag_ai.py` | AI summary | Not yet verified locally | Not found | project default | Useful visualization rule, not a standard requirement. |
| Algorithm | Outlier removal band | mu +/- 2.5 sigma | rule | `tunnel_analysis/rag_ai.py` | algorithm note | None yet | None | project default | Internal preprocessing setting. |
| Algorithm | Voxel size quick preview | 0.10 | m | `tunnel_analysis/rag_ai.py` | algorithm note | None yet | None | project default | Internal preprocessing setting. |
| Algorithm | Voxel size precision | 0.02 | m | `tunnel_analysis/rag_ai.py` | algorithm note | None yet | None | project default | Internal preprocessing setting. |
| Algorithm | Voxel size high-density | 0.05 | m | `tunnel_analysis/rag_ai.py` | algorithm note | None yet | None | project default | Internal preprocessing setting. |

## Confirmed Local Source Files

- `docs/standards/korean/KR_C-08080_221212_Rev3.pdf`
- `docs/standards/korean/SOURCES.md`

## Maintenance Rules

1. If a parameter is copied into code from a document, add the document page/section here.
2. If a parameter is only an engineering assumption, mark it `project default`.
3. If a code comment or RAG snippet claims a standard but no document match exists, mark it `unverified`.
4. When a parameter changes, update this register first, then update code and tests.
5. Keep this file short enough to review before every parameter-related change.