"""Optional Headroom integration for local AI prompts.

Headroom is used as a local context-compression layer before prompts are sent
to Ollama. The dependency is optional at runtime: if ``headroom-ai`` is not
installed or compression fails, callers receive the original prompt.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class HeadroomPrompt:
    prompt: str
    note: str = "Headroom: unavailable"
    enabled: bool = False


def _flatten_messages(messages: list[dict[str, Any]]) -> str:
    parts = []
    for msg in messages:
        role = str(msg.get("role", "user")).upper()
        content = msg.get("content", "")
        if isinstance(content, list):
            content = "\n".join(str(part) for part in content)
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts).strip()


def optimize_prompt(system_context: str, user_prompt: str, *, model: str = "llama3") -> HeadroomPrompt:
    """Compress AI context with Headroom when available.

    The user's actual query is protected; Headroom is mainly allowed to compress
    the large system/context block built from tunnel parameters and standards.
    """
    messages = [
        {"role": "system", "content": system_context},
        {"role": "user", "content": user_prompt},
    ]
    original = _flatten_messages(messages)
    if os.environ.get("TUNNEL_HEADROOM_DISABLED", "").lower() in {"1", "true", "yes"}:
        return HeadroomPrompt(original, "Headroom: disabled by TUNNEL_HEADROOM_DISABLED", False)

    try:
        from headroom import CompressConfig, compress
    except Exception:
        return HeadroomPrompt(original, "Headroom: not installed (pip install headroom-ai)", False)

    try:
        config = CompressConfig(
            compress_user_messages=False,
            compress_system_messages=True,
            protect_recent=1,
            protect_analysis_context=True,
            target_ratio=0.65,
            min_tokens_to_compress=700,
        )
        result = compress(messages, model=model, config=config)
        prompt = _flatten_messages(result.messages)
        if result.tokens_before > 0:
            note = (
                f"Headroom: {result.tokens_before}->{result.tokens_after} tokens "
                f"saved={result.tokens_saved} ratio={result.compression_ratio:.2%}"
            )
        else:
            note = "Headroom: no compression applied"
        return HeadroomPrompt(prompt or original, note, True)
    except Exception as exc:
        return HeadroomPrompt(original, f"Headroom: compression skipped ({exc})", False)
