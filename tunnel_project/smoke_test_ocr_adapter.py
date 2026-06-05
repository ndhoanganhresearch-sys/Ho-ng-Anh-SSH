"""Smoke test for optional PaddleOCR adapter behavior."""
from tunnel_analysis.ocr_adapter import _flatten_texts, extract_text_from_image


def main() -> None:
    nested = [
        [[[0, 0], [1, 0], [1, 1], [0, 1]], ("Tunnel Section A", 0.98)],
        {"rec_text": "Chainage 12+345", "rec_score": 0.91},
    ]
    blocks = _flatten_texts(nested)
    assert [b.text for b in blocks] == ["Tunnel Section A", "Chainage 12+345"]
    missing = extract_text_from_image("__missing_ocr_fixture__.png")
    assert not missing.enabled
    assert "file not found" in missing.note
    print("SMOKE TEST PASSED")
    print(missing.note)


if __name__ == "__main__":
    main()
