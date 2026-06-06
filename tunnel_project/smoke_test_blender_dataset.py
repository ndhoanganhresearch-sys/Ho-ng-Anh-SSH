# -*- coding: utf-8 -*-
r"""Smoke test for the Blender-generated tunnel dataset.

Run from tunnel_project:
    ..\.venv\Scripts\python.exe smoke_test_blender_dataset.py
"""

from __future__ import annotations

import json
from pathlib import Path

from tunnel_analysis.io_layer import BaseLayer


ROOT = Path(__file__).resolve().parent
DATASET_DIR = ROOT / "data" / "blender_test_suite"
REQUIRED_CASES = {
    "case_01_clean_reference",
    "case_02_local_deformation",
    "case_03_noise_and_cables",
    "case_04_clearance_intrusion",
    "case_05_curved_centerline",
    "case_06_occlusion_sparse",
}


def main() -> int:
    manifest_path = DATASET_DIR / "manifest.json"
    assert manifest_path.exists(), f"missing manifest: {manifest_path}"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    case_ids = {case["case_id"] for case in manifest["cases"]}
    missing = REQUIRED_CASES - case_ids
    assert not missing, f"missing cases: {sorted(missing)}"

    loader = BaseLayer()
    loaded = []
    for case_id in sorted(REQUIRED_CASES):
        case_dir = DATASET_DIR / case_id
        for name in ["T0.txt", "Tn.txt", "T0_labels.txt", "Tn_labels.txt"]:
            path = case_dir / name
            assert path.exists(), f"missing file: {path}"
            bundle = loader.load_scan(str(path))
            assert len(bundle.points) > 1000, f"too few points in {path}: {len(bundle.points)}"
            if name.endswith("_labels.txt"):
                assert bundle.metadata.get("has_labels"), f"labels not detected: {path}"
            loaded.append((case_id, name, len(bundle.points)))

        gt = json.loads((case_dir / "ground_truth.json").read_text(encoding="utf-8"))
        assert gt["case_id"] == case_id
        assert gt["recommended_tests"], f"no recommended tests for {case_id}"

    print("SMOKE TEST PASSED")
    print(f"dataset={manifest['dataset']} cases={len(case_ids)} files_loaded={len(loaded)}")
    for case_id, name, npts in loaded[:6]:
        print(f"  {case_id}/{name}: {npts:,} points")
    print("  ...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
