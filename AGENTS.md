# AGENTS.md - Codex instructions

Scope: entire workspace rooted at this directory.

## Karpathy-style coding discipline

Use the spirit of `multica-ai/andrej-karpathy-skills`: simple code, surgical changes, and verifiable outcomes.

- Think before coding: state assumptions when the request is ambiguous; ask before risky changes.
- Simplicity first: do not add abstractions, configuration, or features that were not requested.
- Surgical changes: touch only files and lines needed for the task; do not refactor unrelated code.
- Match existing style: keep naming, formatting, and structure consistent with nearby code.
- Goal-driven execution: for multi-step work, define success criteria and verify with the closest relevant test/build/smoke check.
- Diff discipline: every changed line should trace to the user request; mention unrelated issues instead of fixing them.

## Project workflow

- Follow `CLAUDE.md` for project-specific workflow, paths, verification commands, MCP usage, and research-gap guidance.
- Do not revert user changes or benchmark artifacts unless explicitly asked.
- Keep final handoffs concise: changed files, verification run, remaining risks, and next step.
