# -*- coding: utf-8 -*-
r"""Smoke test for data/blender_sample_like.

Run from tunnel_project:
    ..\.venv\Scripts\python.exe smoke_test_blender_sample_like.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from tunnel_analysis.io_layer import BaseLayer


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "blender_sample_like"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def main() -> int:
    manifest_path = DATA / "manifest.json"
    check(manifest_path.exists(), "manifest exists")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    loader = BaseLayer()
    os1 = loader.load_scan(str(DATA / "OS1_blender_tunnel_entire_10cm.txt"), max_points=300_000)
    os6 = loader.load_scan(str(DATA / "OS6_blender_tunnel_entire_10cm.txt"), max_points=300_000)

    check(os1.points.shape[0] > 150_000, "OS1 point count > 150k")
    check(os6.points.shape[0] > 150_000, "OS6 point count > 150k")
    check(os1.metadata["header_rows"] == 0, "OS1 no-header format")
    check(os6.metadata["header_rows"] == 1, "OS6 one-header format")
    check(os1.metadata["has_colors"] and os6.metadata["has_colors"], "RGB columns detected")

    bmin = np.minimum(os1.points.min(axis=0), os6.points.min(axis=0))
    bmax = np.maximum(os1.points.max(axis=0), os6.points.max(axis=0))
    check(740.0 < bmin[0] < 746.0 and 752.0 < bmax[0] < 756.0, "global X bounds look sample-like")
    check(-368.0 < bmin[1] < -366.0 and -296.0 < bmax[1] < -294.0, "global Y bounds look sample-like")
    check(manifest["ground_truth"]["expected_warning"] is True, "manifest marks expected deformation warning")

    print("BLENDER SAMPLE-LIKE SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
