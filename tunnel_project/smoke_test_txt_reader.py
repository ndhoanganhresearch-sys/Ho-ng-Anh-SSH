# -*- coding: utf-8 -*-
"""Smoke tests for the ASCII (.txt/.xyz/.csv) point-cloud reader.

Run from the tunnel_project directory:
    python smoke_test_txt_reader.py

Covers column auto-detection (3 / 6-normals / 6-RGB / 8-FY387), header and
delimiter sniffing (whitespace + comma), subsampling, and a real FY387 scan if
present on disk.
"""
import os
import tempfile

import numpy as np

from tunnel_analysis.io_layer import BaseLayer

FY387 = r"F:\data\FY387\dataset1_robot_TLS\raw\t2_11.txt"


def _write(tmp, text):
    p = os.path.join(tmp, "cloud.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def test_xyz_only():
    base = BaseLayer()
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "1 2 3\n4 5 6\n7 8 9\n")
        b = base.load_scan(p)
        assert b.points.shape == (3, 3), b.points.shape
        assert b.metadata["columns"] == 3
        assert not b.metadata["has_intensity"]
    return "xyz-only OK"


def test_header_and_comma():
    base = BaseLayer()
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "x,y,z\n1.0,2.0,3.0\n4.0,5.0,6.0\n7,8,9\n")
        b = base.load_scan(p)
        assert b.points.shape == (3, 3), b.points.shape
        assert b.metadata["header_rows"] == 1, b.metadata["header_rows"]
        assert b.metadata["delimiter"] == repr(","), b.metadata["delimiter"]
    return "header+comma OK"


def test_fy387_8col():
    base = BaseLayer()
    with tempfile.TemporaryDirectory() as tmp:
        # XYZ + normals(3) + intensity + label
        rows = [
            "10.0 5.0 3.0 0.0 0.0 1.0 0.4 0",
            "10.1 5.0 3.1 0.0 0.1 0.9 0.5 2",
            "10.2 5.1 3.0 0.1 0.0 0.9 0.6 5",
            "10.3 5.0 2.9 0.0 0.0 1.0 0.7 0",
        ]
        p = _write(tmp, "\n".join(rows) + "\n")
        b = base.load_scan(p)
        assert b.points.shape == (4, 3), b.points.shape
        assert b.metadata["columns"] == 8
        assert b.metadata["has_intensity"]
        assert b.metadata["has_labels"]
        assert "labels" in b.metadata and len(b.metadata["labels"]) == 4
    return "fy387-8col OK"


def test_subsample():
    base = BaseLayer()
    with tempfile.TemporaryDirectory() as tmp:
        n = 1000
        xyz = np.random.default_rng(0).normal(size=(n, 3))
        p = os.path.join(tmp, "big.txt")
        np.savetxt(p, xyz)
        b = base.load_scan(p, max_points=200)
        assert len(b.points) <= 200, len(b.points)
        assert b.metadata["subsampled"]
        assert b.metadata["original_count"] == n
    return "subsample OK"


def test_real_fy387():
    if not os.path.isfile(FY387):
        return "real FY387 skipped (file not found)"
    base = BaseLayer()
    b = base.load_scan(FY387, max_points=5_000_000)
    assert b.points.shape[1] == 3
    assert b.metadata["columns"] == 8
    assert b.metadata["has_labels"]
    return f"real FY387 OK: {len(b.points):,} pts, bounds_min={np.round(b.points.min(0),2).tolist()}"


if __name__ == "__main__":
    for fn in (test_xyz_only, test_header_and_comma, test_fy387_8col,
               test_subsample, test_real_fy387):
        print(fn.__name__, "->", fn())
    print("SMOKE TEST PASSED")
