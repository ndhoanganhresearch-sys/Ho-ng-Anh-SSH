r"""Assemble the full SSL Tunnel manuscript from per-section Markdown files.

Reads paper/drafts/main_paper_full.md (which contains the title, abstract,
Section 1, the @@SECTION_NN@@ placeholders, and the reference list) and splices
in the canonical per-section sources from paper/drafts/sections/.

Output: paper/drafts/main_paper_full_assembled.md

Run from tunnel_project/:
    ..\.venv\Scripts\python.exe tools\assemble_paper.py
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent / "paper"
DRAFTS = PAPER / "drafts"
SECTIONS = DRAFTS / "sections"

SECTION_FILES = {
    "02": "section_02_related_work.md",
    "03": "section_03_system_architecture.md",
    "04": "section_04_preprocessing.md",
    "05": "section_05_registration.md",
    "06": "section_06_frenet_geometry.md",
    "07": "section_07_parameter_extraction.md",
    "08": "section_08_change_detection.md",
    "09": "section_09_rag_assistant.md",
    "10": "section_10_output_generation.md",
    "11": "section_11_validation.md",
    "12": "section_12_conclusion.md",
}


def main() -> None:
    template = (DRAFTS / "main_paper_full.md").read_text(encoding="utf-8")
    for num, fname in SECTION_FILES.items():
        body = (SECTIONS / fname).read_text(encoding="utf-8").strip()
        placeholder = f"@@SECTION_{num}@@"
        if placeholder not in template:
            raise SystemExit(f"Placeholder {placeholder} not found in template")
        template = template.replace(placeholder, body)

    # Drop the maintenance comment lines (HTML comments) for the assembled output.
    out_lines = [ln for ln in template.splitlines() if not ln.strip().startswith("<!--")]
    out = "\n".join(out_lines).strip() + "\n"

    out_path = DRAFTS / "main_paper_full_assembled.md"
    out_path.write_text(out, encoding="utf-8")

    words = len(out.split())
    print(f"Assembled manuscript: {out_path}")
    print(f"Approx word count: {words}")


if __name__ == "__main__":
    main()
