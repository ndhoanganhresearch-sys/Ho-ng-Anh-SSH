# -*- coding: utf-8 -*-
"""Smoke tests for the STSD benchmark adapter (tunnel_analysis.datasets.stsd).

Run from the tunnel_project directory:
    python smoke_test_stsd_adapter.py

STSD itself is distributed on request (Google Form), so these tests use a
synthetic labelled tunnel cloud to verify the scoring logic end-to-end:
- score_keep_mask computes correct precision/recall/F1 on a known mask.
- evaluate_methods runs the tool's denoisers and reports sane metrics, with
  the synthetic interior clutter (labelled non-structural) being removed.
"""
import numpy as np

from tunnel_analysis.datasets import stsd
from tunnel_analysis.models import PipelineContext, PointCloudBundle


def _labelled_tunnel(seed=0):
    """Build a shell (label 1 = structural) + interior cable/blob (label 5 = noise)."""
    rng = np.random.default_rng(seed)
    # Shell
    n_axial, n_theta, radius, length = 140, 120, 2.75, 22.0
    y = np.linspace(0.0, length, n_axial)
    th = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    yy, tt = np.meshgrid(y, th)
    rr = radius + rng.normal(0.0, 0.01, yy.shape)
    shell = np.column_stack([(rr * np.cos(tt)).ravel(), yy.ravel(), (rr * np.sin(tt)).ravel()])
    # Interior cable (small radius, fixed angle)
    yc = np.linspace(1.0, 21.0, 500)
    cable = np.column_stack([np.full(500, 1.1) + rng.normal(0, 0.01, 500),
                             yc,
                             np.full(500, 0.6) + rng.normal(0, 0.01, 500)])
    # Interior equipment blob
    blob = rng.normal(0, 0.25, (400, 3)) + np.array([0.0, 11.0, -1.0])

    xyz = np.vstack([shell, cable, blob]).astype(np.float64)
    labels = np.concatenate([
        np.full(len(shell), 1, dtype=np.int64),   # structural lining
        np.full(len(cable), 5, dtype=np.int64),   # cable = noise
        np.full(len(blob), 6, dtype=np.int64),    # equipment = noise
    ])
    return xyz, labels


def test_score_keep_mask_math():
    # 10 points: labels [1,1,1,1,1, 5,5,5,5,5]; structural = {1}.
    labels = np.array([1, 1, 1, 1, 1, 5, 5, 5, 5, 5], dtype=np.int64)
    # Prediction keeps all structural and removes 4 of 5 noise (1 missed).
    kept = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 1], dtype=bool)
    s = stsd.score_keep_mask(labels, kept, structure_labels={1})
    # tp=4 (noise removed), fp=0 (no structural removed), fn=1 (one noise kept)
    assert abs(s["noise_precision"] - 1.0) < 1e-9, s
    assert abs(s["noise_recall"] - 0.8) < 1e-9, s
    assert abs(s["lining_retention"] - 1.0) < 1e-9, s
    assert abs(s["noise_f1"] - (2 * 1.0 * 0.8 / 1.8)) < 1e-9, s
    return s


def test_evaluate_methods_on_synthetic():
    xyz, labels = _labelled_tunnel()
    # Structural label is 1; cable/blob (5,6) are noise.
    res = stsd.evaluate_methods(xyz, labels,
                                methods=["auto_denoise", "density_lining"],
                                structure_labels={1})
    for name, s in res.items():
        assert "error" not in s, f"{name} errored: {s.get('error')}"
        assert s["lining_retention"] >= 0.85, f"{name} over-removed lining: {s}"
        assert s["noise_recall"] >= 0.5, f"{name} missed too much noise: {s}"
    return res


if __name__ == "__main__":
    s = test_score_keep_mask_math()
    res = test_evaluate_methods_on_synthetic()
    print("SMOKE TEST PASSED")
    print(f"score math: precision={s['noise_precision']:.2f} recall={s['noise_recall']:.2f} f1={s['noise_f1']:.2f}")
    for name, m in res.items():
        print(f"{name:16s} precision={m['noise_precision']:.2f} recall={m['noise_recall']:.2f} "
              f"f1={m['noise_f1']:.2f} retention={m['lining_retention']:.2f}")
