"""Optional PaddleOCR integration for document and image text extraction.

The tunnel analysis core does not depend on PaddleOCR. This adapter keeps OCR
features optional so the desktop app and analysis pipeline continue to work on
machines where PaddleOCR is not installed or where model downloads are blocked.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# PaddlePaddle 3.x CPU inference can fail on Windows with oneDNN/PIR conversion.
# Disable MKL-DNN before importing PaddleOCR; users can override externally.
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_use_onednn", "0")


@dataclass
class OCRBlock:
    text: str
    confidence: float | None = None
    bbox: Any = None


@dataclass
class OCRResult:
    text: str = ""
    blocks: list[OCRBlock] = field(default_factory=list)
    markdown: str | None = None
    data: Any = None
    note: str = "PaddleOCR: unavailable"
    enabled: bool = False


def _missing_result() -> OCRResult:
    return OCRResult(
        note=(
            "PaddleOCR: not installed "
            "(pip install paddleocr; add extras such as paddleocr[doc-parser] when needed)"
        ),
        enabled=False,
    )


def _path_result_error(path: str | Path) -> OCRResult | None:
    if not Path(path).exists():
        return OCRResult(note=f"PaddleOCR: file not found: {path}", enabled=False)
    return None


def _flatten_texts(value: Any) -> list[OCRBlock]:
    """Best-effort extraction across PaddleOCR result shapes.

    PaddleOCR has changed output formats across versions and pipelines. This
    function intentionally accepts common dict/list/object result shapes instead
    of binding the app to one exact release.
    """
    blocks: list[OCRBlock] = []

    def visit(node: Any) -> None:
        if node is None:
            return
        if isinstance(node, str):
            if node.strip():
                blocks.append(OCRBlock(node.strip()))
            return
        if isinstance(node, dict):
            rec_texts = node.get("rec_texts")
            if isinstance(rec_texts, list):
                rec_scores = node.get("rec_scores") or []
                rec_polys = node.get("rec_polys") or node.get("rec_boxes") or []
                for i, rec_text in enumerate(rec_texts):
                    if not rec_text:
                        continue
                    score = rec_scores[i] if i < len(rec_scores) else None
                    bbox = rec_polys[i] if i < len(rec_polys) else None
                    try:
                        score = None if score is None else float(score)
                    except Exception:
                        score = None
                    blocks.append(OCRBlock(str(rec_text), score, bbox))
            text = node.get("text") or node.get("rec_text") or node.get("transcription")
            score = node.get("score") or node.get("confidence") or node.get("rec_score")
            bbox = node.get("bbox") or node.get("points") or node.get("dt_polys")
            if text:
                try:
                    score = None if score is None else float(score)
                except Exception:
                    score = None
                blocks.append(OCRBlock(str(text), score, bbox))
            for key in ("res", "data", "items", "lines", "blocks", "ocr_res"):
                if key in node:
                    visit(node[key])
            return
        if isinstance(node, (list, tuple)):
            if len(node) == 2 and isinstance(node[1], (list, tuple)) and node[1]:
                maybe_text = node[1][0]
                maybe_score = node[1][1] if len(node[1]) > 1 else None
                if isinstance(maybe_text, str):
                    try:
                        maybe_score = None if maybe_score is None else float(maybe_score)
                    except Exception:
                        maybe_score = None
                    blocks.append(OCRBlock(maybe_text, maybe_score, node[0]))
                    return
            for item in node:
                visit(item)
            return
        for attr in ("json", "res", "data", "ocr_res"):
            if hasattr(node, attr):
                try:
                    visit(getattr(node, attr))
                except Exception:
                    pass

    visit(value)
    return blocks


def extract_text_from_image(image_path: str | Path, *, lang: str = "en") -> OCRResult:
    """Extract plain OCR text from an image using PaddleOCR when available."""
    path_error = _path_result_error(image_path)
    if path_error:
        return path_error
    try:
        from paddleocr import PaddleOCR
    except Exception:
        return _missing_result()

    try:
        engine = PaddleOCR(lang=lang, use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)
        if hasattr(engine, "ocr"):
            raw = engine.ocr(str(image_path))
        else:
            raw = engine.predict(str(image_path))
        blocks = _flatten_texts(raw)
        text = "\n".join(block.text for block in blocks).strip()
        return OCRResult(text=text, blocks=blocks, data=raw, note=f"PaddleOCR: {len(blocks)} text blocks", enabled=True)
    except Exception as exc:
        return OCRResult(note=f"PaddleOCR: OCR skipped ({exc})", enabled=False)


def extract_markdown_from_document(path: str | Path, *, lang: str = "en") -> OCRResult:
    """Extract Markdown/text from a PDF or document image when doc parsers exist.

    For full PDF/layout parsing, install PaddleOCR's document parser extras. The
    function falls back to plain text extraction for image-like inputs.
    """
    path_error = _path_result_error(path)
    if path_error:
        return path_error
    try:
        from paddleocr import PPStructureV3
    except Exception:
        return extract_text_from_image(path, lang=lang)

    try:
        parser = PPStructureV3(lang=lang)
        raw = parser.predict(str(path)) if hasattr(parser, "predict") else parser(str(path))
        blocks = _flatten_texts(raw)
        markdown = None
        for item in raw if isinstance(raw, list) else [raw]:
            if isinstance(item, dict):
                markdown = markdown or item.get("markdown") or item.get("md")
        text = "\n".join(block.text for block in blocks).strip()
        return OCRResult(
            text=text,
            blocks=blocks,
            markdown=markdown,
            data=raw,
            note=f"PaddleOCR: document parsed, {len(blocks)} text blocks",
            enabled=True,
        )
    except Exception as exc:
        return OCRResult(note=f"PaddleOCR: document parsing skipped ({exc})", enabled=False)
