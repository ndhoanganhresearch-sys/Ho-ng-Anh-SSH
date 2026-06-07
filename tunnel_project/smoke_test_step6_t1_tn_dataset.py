# -*- coding: utf-8 -*-
r"""Smoke test for data/blender_step6_t1_tn.

Run from tunnel_project:
    ..\.venv\Scripts\python.exe smoke_test_step6_t1_tn_dataset.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from tunnel_analysis.io_layer import BaseLayer

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "blender_step6_t1_tn"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def load_pair(folder: str):
    case_dir = DATA / folder
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    loader = BaseLayer()
    t1 = loader.load_scan(str(case_dir / "T1_step6_reference.txt"), max_points=200_000)
    tn = loader.load_scan(str(case_dir / "Tn_step6_monitoring.txt"), max_points=200_000)
    return manifest, t1.points, tn.points


def nearest_delta_mm(t1: np.ndarray, tn: np.ndarray) -> np.ndarray:
    tree = cKDTree(tn[:, :3])
    distances, _ = tree.query(t1[:, :3], k=1, workers=-1)
    return distances * 1000.0


def center_band(points: np.ndarray, y0: float, width: float = 6.0) -> np.ndarray:
    mask = np.abs(points[:, 1] - y0) <= width
    return mask


def test_subtle() -> None:
    manifest, t1, tn = load_pair("version_01_subtle_deformation")
    check(t1.shape[0] == manifest["files"][0]["points"], "subtle T1 point count matches manifest")
    check(tn.shape[0] == manifest["files"][1]["points"], "subtle Tn point count matches manifest")
    check(t1.shape[0] > 25_000 and tn.shape[0] > 25_000, "subtle pair has enough points")
    d = nearest_delta_mm(t1, tn)
    mid = d[center_band(t1, 32.0)]
    ends = d[(t1[:, 1] < 8.0) | (t1[:, 1] > 56.0)]
    check(float(np.percentile(mid, 95)) > 10.0, "subtle center deformation is detectable")
    check(float(np.percentile(mid, 95)) < 35.0, "subtle deformation stays in small-mm range")
    check(float(np.percentile(mid, 95)) > float(np.percentile(ends, 95)) + 3.0, "subtle deformation is localized near center")
    check(manifest["ground_truth"]["visual_scale_recommended"] >= 20, "subtle version recommends high 2D visual scale")


def test_complex() -> None:
    manifest, t1, tn = load_pair("version_02_complex_warning")
    check(t1.shape[0] > 24_000 and tn.shape[0] > 25_000, "complex pair has enough points")
    check(manifest["ground_truth"]["expected_level"] == "CRITICAL", "complex version expects CRITICAL warnings")
    check(manifest["ground_truth"]["clearance_intrusion"] is True, "complex manifest includes clearance intrusion")
    check(manifest["ground_truth"]["contains_cable_like_clutter"] is True, "complex manifest includes cable clutter")
    d = nearest_delta_mm(t1, tn)
    main = d[center_band(t1, 26.0)]
    secondary = d[center_band(t1, 45.0)]
    ends = d[(t1[:, 1] < 8.0) | (t1[:, 1] > 56.0)]
    check(float(np.percentile(main, 95)) > 45.0, "complex main deformation exceeds critical-scale signal")
    check(float(np.percentile(secondary, 90)) > 20.0, "complex secondary deformation is detectable")
    check(float(np.percentile(main, 95)) > float(np.percentile(ends, 95)) + 20.0, "complex deformation is localized")
    labels_path = DATA / "version_02_complex_warning" / "Tn_step6_monitoring_labels.txt"
    check(labels_path.exists(), "complex labeled helper file exists")
    labels = np.loadtxt(labels_path, skiprows=1, usecols=[6], dtype=int)
    unique = set(int(v) for v in np.unique(labels))
    check({1, 2, 3, 4}.issubset(unique), "complex labels include structure/outlier/cable/clearance")


def main() -> int:
    top = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    check(top["dataset"] == "blender_step6_t1_tn", "top manifest exists")
    check(len(top["versions"]) == 2, "top manifest lists two versions")
    test_subtle()
    test_complex()
    print("STEP6 T1/TN DATASET SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
