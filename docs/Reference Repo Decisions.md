# Reference Repo Decisions

#reference #decision #integration #roadmap

## Purpose

Track how reference repositories should influence the project without mixing unverified code into production.

## Decision Table

| Reference | Use Now | Role | Next Decision |
| --- | --- | --- | --- |
| `_ref_FY387_calc` | Yes | Deformation workflow and benchmark inspiration | Keep as benchmark/method reference |
| `_ref_GROR` | Limited | Robust registration concept | Prototype only if Step 6 registration error is high |
| `_ref_SAM4Tun` | No production integration | Segmentation concept | Create segmentation experiment note first |
| `_ref_Cloud2BIM` | Limited | BIM/IFC output concept | Use after deformation benchmark is stable |
| `_ref_PowerLine` | No | Cable/noise inspiration | Revisit only for denoise benchmark |
| `_ref_trending/MinerU` | Yes | Document/RAG tooling | Safe for document ingestion |
| `_ref_trending/codebase-memory-mcp` | Not yet | Future MCP memory | Isolated smoke test before `.mcp.json` changes |
| `_ref_trending/lingbot-map` | Not yet | 3D mapping idea | Prototype only |
| `_ref_trending/cupy` | Blocked | GPU acceleration | Wait for Windows CUDA/import issue resolution |

## Current Recommendation

Prioritize **Step 6 validation** before integrating new algorithmic references.

## Links

- [[Step 6 Deformation]]
- [[Step 6 Benchmark Table]]
- [[Research Claims]]
- [[REPO_INTEGRATION_STATUS]]
