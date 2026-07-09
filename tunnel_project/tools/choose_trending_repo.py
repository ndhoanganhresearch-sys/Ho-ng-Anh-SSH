"""Choose which trending reference repo fits a task description."""
from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class RepoRule:
    name: str
    path: str
    keywords: tuple[str, ...]
    readiness: int
    risk_fit: int
    verification_fit: int
    direct_action: str
    reference_action: str


RULES = [
    RepoRule(
        name="MinerU",
        path="../_ref_trending/MinerU",
        keywords=(
            "pdf", "docx", "pptx", "xlsx", "document", "markdown", "json",
            "ocr", "paper", "report", "standard", "standards", "rag", "parse",
            "extract", "tai lieu", "bao cao", "tieu chuan", "van ban",
        ),
        readiness=3,
        risk_fit=3,
        verification_fit=3,
        direct_action="Run MinerU in its isolated venv, export Markdown/JSON, then ingest Markdown into RAG if needed.",
        reference_action="Use MinerU docs/examples to design document conversion only.",
    ),
    RepoRule(
        name="codebase-memory-mcp",
        path="../_ref_trending/codebase-memory-mcp",
        keywords=(
            "codebase", "mcp", "index", "memory", "call graph", "function",
            "class", "architecture", "large repo", "search code", "agent",
            "relationship", "quan he", "kien truc", "tim code",
        ),
        readiness=2,
        risk_fit=3,
        verification_fit=2,
        direct_action="Evaluate the installed wrapper/MCP in isolation before editing `.mcp.json`.",
        reference_action="Use as a reference for code-index workflow; keep current manual rg flow.",
    ),
    RepoRule(
        name="lingbot-map",
        path="../_ref_trending/lingbot-map",
        keywords=(
            "3d reconstruction", "streaming", "mapping", "scene", "reconstruct",
            "map", "sequential", "frames", "point cloud reconstruction", "geometry",
            "tai dung", "ban do", "quet",
        ),
        readiness=2,
        risk_fit=2,
        verification_fit=2,
        direct_action="Inspect algorithms and prototype outside production before porting small ideas.",
        reference_action="Read as algorithm reference for 3D reconstruction/mapping tasks.",
    ),
    RepoRule(
        name="CuPy",
        path="../_ref_trending/cupy",
        keywords=(
            "gpu", "cuda", "cupy", "speed", "accelerate", "performance",
            "numpy", "scipy", "matrix", "distance", "fft", "benchmark",
            "tang toc", "hieu nang",
        ),
        readiness=1,
        risk_fit=2,
        verification_fit=3,
        direct_action="Fix CuPy import/CUDA DLL issue first, then benchmark a tiny isolated kernel.",
        reference_action="Use as future acceleration option; do not change production NumPy code yet.",
    ),
]


def relevance_score(task: str, rule: RepoRule) -> int:
    text = task.lower()
    hits = sum(1 for keyword in rule.keywords if keyword in text)
    if hits >= 3:
        return 3
    if hits == 2:
        return 2
    if hits == 1:
        return 1
    return 0


def decision(score: int) -> str:
    if score >= 10:
        return "use directly"
    if score >= 7:
        return "use as isolated tool/reference"
    if score >= 4:
        return "inspect only if blocked"
    return "do not use"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", help="Short task description")
    args = parser.parse_args()

    rows = []
    for rule in RULES:
        relevance = relevance_score(args.task, rule)
        score = relevance + rule.readiness + rule.risk_fit + rule.verification_fit
        rows.append((score, relevance, rule))

    rows.sort(key=lambda row: (row[0], row[1]), reverse=True)
    best_score, _, best_rule = rows[0]

    print(f"Task: {args.task}")
    print(f"Best: {best_rule.name} ({decision(best_score)}, score={best_score}/12)")
    print(f"Path: {best_rule.path}")
    print("Action:", best_rule.direct_action if best_score >= 10 else best_rule.reference_action)
    print("\nScores:")
    for score, relevance, rule in rows:
        print(
            f"- {rule.name}: {score}/12 "
            f"(relevance={relevance}, readiness={rule.readiness}, "
            f"risk_fit={rule.risk_fit}, verification_fit={rule.verification_fit}) "
            f"=> {decision(score)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
