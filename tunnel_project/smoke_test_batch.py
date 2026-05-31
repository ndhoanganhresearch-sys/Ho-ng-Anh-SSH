# -*- coding: utf-8 -*-
"""Smoke test for the headless batch pipeline (tunnel_analysis.batch).

Run from the tunnel_project directory:
    python smoke_test_batch.py

Writes a synthetic straight-tunnel .txt, runs run_pipeline end-to-end, and
checks a CSV is produced with the expected per-section columns and a sane
fitted radius. Verifies both count and spacing resolution modes. Cleans up.
"""
import csv
import os
import tempfile

import numpy as np

from tunnel_analysis.batch import run_pipeline


def _write_tunnel(path, R=2.75, length=20.0, n_axial=220, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for y in np.linspace(0.0, length, n_axial):
        m = rng.integers(80, 130)
        a = rng.uniform(0.0, 2 * np.pi, m)
        x = R * np.cos(a) + rng.normal(0, 0.006, m)
        z = R * np.sin(a) + R + rng.normal(0, 0.006, m)
        rows.append(np.column_stack([x, np.full(m, y), z]))
    np.savetxt(path, np.vstack(rows), fmt="%.5f")


def test_batch_count_mode():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "tunnel.txt")
        _write_tunnel(src)
        result = run_pipeline(src, out_dir=tmp, section_count=50, denoise=False)
        assert os.path.isfile(result["csv"]), "CSV not written"
        assert result["n_sections"] == 50, result["n_sections"]
        with open(result["csv"], newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        assert "chainage_m" in rows[0] and "radius_fit_m" in rows[0]
        radii = [float(r["radius_fit_m"]) for r in rows if r["radius_fit_m"]]
        med = float(np.median(radii))
        assert 2.4 <= med <= 3.1, f"median radius off: {med:.3f}"
        return f"count mode: {result['n_sections']} sections, median R {med:.3f} m"


def test_batch_spacing_mode():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "tunnel.txt")
        _write_tunnel(src, length=20.0)
        result = run_pipeline(src, out_dir=tmp, spacing_m=1.0, denoise=False)
        # ~20 m / 1.0 m + 1 -> ~21 sections
        assert 15 <= result["n_sections"] <= 25, result["n_sections"]
        assert os.path.isfile(result["csv"])
        return f"spacing mode: {result['n_sections']} sections"


if __name__ == "__main__":
    for fn in (test_batch_count_mode, test_batch_spacing_mode):
        print(fn.__name__, "->", fn())
    print("SMOKE TEST PASSED")
