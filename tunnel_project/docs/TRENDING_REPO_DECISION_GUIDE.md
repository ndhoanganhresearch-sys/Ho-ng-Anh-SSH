# Trending Repo Decision Guide

This guide tells the agent when to use the newly cloned trending repositories in
`../_ref_trending/`. Treat these repositories as reference/tooling first. Do not
copy code into production unless a task explicitly needs it and the change is
benchmarked or smoke-tested.

## Repositories

| Repo | Local path | Use for | Current integration |
| --- | --- | --- | --- |
| MinerU | `../_ref_trending/MinerU` | Convert PDF/DOCX/PPTX/XLSX/image documents to Markdown/JSON for RAG, paper review, standards extraction, report QA | Installed in `../_ref_trending/.venv_mineru`; tested on `Intro_SSL_Tunnel_v3_review.docx`; output indexed into RAG |
| codebase-memory-mcp | `../_ref_trending/codebase-memory-mcp` | Codebase indexing, structural code search, agent memory, cross-module navigation | Python wrapper installed in `../_ref_trending/.venv_codebase_memory`; not yet wired into `.mcp.json` |
| lingbot-map | `../_ref_trending/lingbot-map` | Streaming 3D reconstruction and mapping ideas | Installed in `../_ref_trending/.venv_lingbot`; reference only |
| CuPy | `../_ref_trending/cupy` | GPU acceleration for NumPy-heavy kernels | `cupy-cuda13x` installed in `../_ref_trending/.venv_cupy`, but import is blocked by Windows policy/CUDA DLL resolution |

## Decision Score

For any task, compute this simple score for each repo:

`score = relevance + readiness + risk_fit + verification_fit`

Each component is `0-3`:

- `relevance`: task directly matches the repo's domain.
- `readiness`: repo/tool is already installed and can run locally.
- `risk_fit`: using it will not disturb production code or core T0/Tn math.
- `verification_fit`: there is a clear smoke test or benchmark.

Decision:

- `10-12`: use the repo/tool directly.
- `7-9`: use it as reference or isolated tooling only.
- `4-6`: inspect only if the task is blocked.
- `0-3`: do not use it.

## Task Routing

| Task type | Repo to use | Action | Verify |
| --- | --- | --- | --- |
| Parse standards, paper, report, PDF, DOCX, PPTX, XLSX | MinerU | Run MinerU in isolated venv, export Markdown/JSON, then ingest Markdown into RAG if useful | Confirm Markdown exists; run RAG retrieval smoke test |
| Add project documents to local RAG | MinerU + project RAG | Convert source document if needed, then run `tools/ingest_mineru_markdown.py` | Query Chroma collection and confirm retrieved source metadata |
| Understand large unfamiliar module relationships | codebase-memory-mcp | Prefer MCP/code-index evaluation before broad manual grep | Keep `.mcp.json` unchanged until tested; verify index/query works |
| Improve agent code navigation or reduce token-heavy file scans | codebase-memory-mcp | Configure as optional MCP only after isolated test | Confirm MCP starts and answers structural queries |
| Improve 3D reconstruction/mapping from sequential scans | lingbot-map | Study architecture and algorithms; port only small ideas | Create a synthetic scene/scan smoke test before production changes |
| Improve visualization or mapping concepts | lingbot-map | Reference only; avoid dependency unless benchmarked | Visual smoke test or Blender/PyVista review |
| Speed up NumPy-heavy computations | CuPy | First fix CuPy import, then prototype a tiny kernel outside production | Compare CPU vs GPU timing and numeric equality |
| M3C2, deformation, section extraction, registration correctness | Existing project + `_ref_FY387_calc`/`_ref_GROR` | Do not start with trending repos | Run `agent_verify.ps1 step6` or closest targeted tests |

## Default Choices

1. If the task mentions documents, standards, paper, OCR, RAG input, or report text, use MinerU first.
2. If the task asks the agent to understand many files or map code relationships, consider codebase-memory-mcp.
3. If the task is about 3D reconstruction or streaming mapping, inspect lingbot-map.
4. If the task is about speed and NumPy/GPU, consider CuPy only after the import issue is fixed.
5. If the task touches tunnel deformation math, registration, or section warnings, keep using the existing project workflow and benchmark refs first.

## Commands

MinerU parse example:

```powershell
..\_ref_trending\.venv_mineru\Scripts\mineru.exe -p "input.docx" -o "outputs\mineru_input" -b pipeline -m auto
```

RAG ingest example:

```powershell
..\.venv\Scripts\python.exe tools\ingest_mineru_markdown.py "..\outputs\rag_inputs\mineru_intro_docx\Intro_SSL_Tunnel_v3_review.md" --source "Intro SSL Tunnel"
```

Decision helper example:

```powershell
..\.venv\Scripts\python.exe tools\choose_trending_repo.py "parse Korean railway standards PDF into RAG"
```

