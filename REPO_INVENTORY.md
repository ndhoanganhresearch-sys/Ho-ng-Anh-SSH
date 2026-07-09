# Repo Inventory

This file tracks the main project repository and local reference repositories stored in this workspace. Use it to decide which external code is only for research, which ideas can be adapted, and which repos should not be mixed into the production app.

For per-repo integration depth, already-used ideas, and unused parts, see REPO_INTEGRATION_STATUS.md.

## Management Rules

- Keep `_ref_*` repositories read-only unless there is an explicit research task.
- Do not copy code from a reference repo into `tunnel_project/` without recording what was copied and why.
- Prefer extracting ideas, algorithms, test cases, or benchmark methods over importing whole projects.
- Before using any reference implementation, check license, dependencies, data requirements, and whether it matches the tunnel workflow.
- Update this file when a new repo is cloned, removed, or promoted into project work.

## Local Repositories

| Role | Local Path | Remote | Branch | Current Commit | Purpose | Relevance To Tunnel Project | Recommended Use | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Main project | `.` | `git@github.com:ndhoanganhresearch-sys/Ho-ng-Anh-SSH.git` | `feature/m3c2-gicp-integration` | `587cd94` - Stabilize box profile and 2D display | Main SSL Tunnel Analysis workspace | Source of truth for app, tests, docs, standards, benchmarks | Develop here only | active |
| Reference | `_ref_Cloud2BIM` | `https://github.com/VaclavNezerka/Cloud2BIM.git` | `master` | `3bb000d` - Update README.md | Scan-to-BIM conversion from point clouds to parametric elements | Useful for BIM/IFC export ideas and point-cloud-to-entity workflows | Study architecture and geometry extraction ideas; do not import wholesale | read-only reference |
| Reference | `_ref_FY387_calc` | `https://github.com/FY387/Deformation-calculation-of-metro-tunnels-based-on-point-clouds.git` | `main` | `42d8a36` - Update README.md | Metro tunnel deformation datasets and calculation workflow | Highly relevant for T0/Tn deformation, benchmark design, dataset comparison | Use as research/benchmark reference; track data provenance carefully | read-only reference |
| Reference | `_ref_GROR` | `https://github.com/WPC-WHU/GROR.git` | `main` | `6f75206` - Update README.md | Robust point-cloud registration via outlier removal on correspondence graph | Relevant to registration robustness and outlier-heavy tunnel scans | Study algorithmic ideas for registration benchmark; avoid dependency unless justified | read-only reference |
| Reference | `_ref_PowerLine` | `https://github.com/lyuhaitao/PowerLineDetection.git` | `master` | `bc3282d` - Update README.md | Power-line detection notebook | Low direct relevance; possible analogy for line/cable detection | Low priority; only inspect if cable detection needs a quick reference | read-only reference |
| Reference | `_ref_SAM4Tun` | `https://github.com/zxy239/SAM4Tun.git` | `main` | `3426c1b` - README.md | No-training tunnel lining point-cloud component segmentation using SAM and projection | Very relevant for tunnel lining segmentation, component localization, and panoramic projection | Study for segmentation workflow and 2D projection ideas; keep notebooks separate | read-only reference with local scratch files |

## Trending Tooling Repositories

These repos live under `_ref_trending/`. Use `tunnel_project/docs/TRENDING_REPO_DECISION_GUIDE.md` and
`tunnel_project/tools/choose_trending_repo.py` to decide when they apply.

| Local Path | Remote | Current Commit | Purpose | Recommended Use | Status |
| --- | --- | --- | --- | --- | --- |
| `_ref_trending/MinerU` | `https://github.com/opendatalab/MinerU.git` | `3e60291` | Document parsing to Markdown/JSON | Use directly for document/RAG tooling through isolated venv | installed and smoke-tested |
| `_ref_trending/codebase-memory-mcp` | `https://github.com/DeusData/codebase-memory-mcp.git` | `b075f05` | Codebase-memory MCP/code index | Evaluate in isolation before adding to `.mcp.json` | installed, not MCP-wired |
| `_ref_trending/lingbot-map` | `https://github.com/Robbyant/lingbot-map.git` | `7ae0781` | Streaming 3D reconstruction reference | Use as algorithm reference/prototype source only | installed reference |
| `_ref_trending/cupy` | `https://github.com/cupy/cupy.git` | `ea2f997` | GPU NumPy/SciPy acceleration source | Use only after fixing Windows CUDA import and benchmarking | package installed, import blocked |

## Priority For Current Project

1. `_ref_FY387_calc` - strongest match for tunnel deformation and datasets.
2. `_ref_SAM4Tun` - strong match for tunnel lining segmentation and component localization.
3. `_ref_GROR` - useful for robust registration ideas.
4. `_ref_Cloud2BIM` - useful for BIM/IFC/Scan-to-BIM concepts.
5. `_ref_PowerLine` - low priority unless cable/line detection becomes important.
6. `_ref_trending/MinerU` - high priority for document-to-RAG workflows, not core point-cloud math.
7. `_ref_trending/codebase-memory-mcp` - evaluate when code navigation/MCP memory becomes the bottleneck.
8. `_ref_trending/lingbot-map` - inspect only for 3D reconstruction/mapping tasks.
9. `_ref_trending/cupy` - revisit for performance tasks after CUDA import is fixed.

## Integration Candidates

| Candidate | What To Extract | Target Area In Project | Verification Required |
| --- | --- | --- | --- |
| FY387 workflow | Dataset structure, deformation metrics, comparison protocol | `BENCHMARK_BASELINES.md`, Step 6 tests, paper benchmarks | Add provenance, run `agent_verify.ps1 step6`, compare against current baselines |
| SAM4Tun | Tunnel unfolding, segment prompts, component-level segmentation flow | `tunnel_analysis/segmentation.py`, visualization/reporting | Add focused smoke test and avoid changing core deformation math first |
| GROR | Outlier-robust registration strategy | `tunnel_analysis/registration.py` | Benchmark against current register_epochs and ICP guard tests |
| Cloud2BIM | Point-cloud-to-parametric/BIM concepts | `tunnel_analysis/ifc_exporter.py`, BIM reporting | Run IFC smoke tests and visual review exported model |
| PowerLineDetection | Cable/line detection heuristics | clean-noise/cable filtering only if needed | Compare denoise metrics before promoting |

## Local Cleanliness Notes

- `_ref_SAM4Tun` currently has untracked scratch files: `_nb.py`, `_nbcode.py`, `_nbmd.py`, `_nbtail.py`.
- Main repo currently has active local changes and new docs/artifacts; check `git status --short` before committing.
- Reference clones should not be modified during app development tasks.

## External Repos Mentioned But Not Cloned

| Repo | Why It Was Mentioned | Current Action |
| --- | --- | --- |
| `666ghj/BettaFish` | Multi-agent public-opinion analysis and report generation architecture | Not cloned; study only if improving report/agent workflow |
| `RyanCodrai/turbovec` | Potential lightweight vector index for RAG | Not cloned; evaluate only if current RAG search becomes a bottleneck |
| `lfnovo/open-notebook` | NotebookLM-style document/RAG workflow | Not cloned; use as product/UX inspiration only |

## Update Checklist

When adding a new reference repo:

1. Clone under `_ref_<name>` unless it is part of production code.
2. Record remote, branch, commit, purpose, and relevance in this file.
3. Add a short note to `PROJECT_ROADMAP.md` only if it changes priorities.
4. Keep generated data and notebooks out of commits unless intentionally promoted.
