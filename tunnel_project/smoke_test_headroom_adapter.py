"""Smoke test for optional Headroom prompt compression integration."""
from tunnel_analysis.headroom_adapter import optimize_prompt


def main() -> None:
    result = optimize_prompt("system context " * 200, "Assess tunnel condition.")
    assert result.prompt
    assert "Assess tunnel condition" in result.prompt
    assert result.note.startswith("Headroom:")
    print("SMOKE TEST PASSED")
    print(result.note)


if __name__ == "__main__":
    main()
