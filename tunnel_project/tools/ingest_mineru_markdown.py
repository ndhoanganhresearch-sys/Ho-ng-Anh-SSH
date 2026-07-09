"""Index MinerU Markdown output into the tunnel RAG collection."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tunnel_analysis.rag_ai import TunnelRAGAssistant


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown", type=Path, help="MinerU Markdown file to index")
    parser.add_argument("--source", default=None, help="Human-readable source name")
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=150)
    args = parser.parse_args()

    assistant = TunnelRAGAssistant()
    message = assistant.ingest_markdown(
        str(args.markdown),
        source=args.source,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    print(message)
    return 0 if message.startswith("Indexed ") else 1


if __name__ == "__main__":
    raise SystemExit(main())
