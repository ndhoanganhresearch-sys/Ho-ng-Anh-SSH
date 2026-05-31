# -*- coding: utf-8 -*-
"""Smoke tests for label-based lining extraction (FY387 / STSD).

Run from the tunnel_project directory:
    python smoke_test_lining_by_label.py

Verifies:
- explicit structure_labels keep exactly those classes,
- auto-detect keeps shell classes and drops an interior blob,
- geometric fallback when no labels are present,
- a real FY387 scan if available on disk.
"""
import os
import numpy as np

from tunnel_analysis.preprocessing import PreprocessingLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle

FY387 = r"F:\data\FY387\dataset1_robot_TLS\raw\t2_11.txt"


def _ctx_with_labels(xyz, labels):
    ctx = PipelineContext()
    b = PointCloudBundle(points=np.asarray(xyz, float))
    if labels is not None:
        b.metadata["labels"] = np.asarray(labels)
    ctx.scans.append(b)
    ctx.active_index = 0
    return ctx


def _shell_plus_blob(seed=0):
    rng = np.random.default_rng(seed)
    n_axial, n_theta, R, length = 120, 100, 2.75, 20.0
    y = np.linspace(0, length, n_axial)
    th = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    yy, tt = np.meshgrid(y, th)
    shell = np.column_stack([(R * np.cos(tt)).ravel(), yy.ravel(),
                             (R * np.sin(tt)).ravel() + R])
    blob = rng.normal(0, 0.2, (600, 3)) + np.array([0.0, 10.0, R])  # interior, near axis
    xyz = np.vstack([shell, blob])
    labels = np.concatenate([np.full(len(shell), 2), np.full(len(blob), 9)])
    return xyz, labels, len(shell)


def test_explicit_labels():
    pre = PreprocessingLayer()
    xyz, labels, n_shell = _shell_plus_blob()
    ctx = _ctx_with_labels(xyz, labels)
    kept, stats = pre.extract_lining_by_label(ctx, structure_labels={2})
    assert stats["method"] == "label"
    assert stats["n_clean"] == n_shell, (stats["n_clean"], n_shell)
    assert not stats["auto_detected"]
    return stats


def test_auto_detect():
    pre = PreprocessingLayer()
    xyz, labels, n_shell = _shell_plus_blob()
    ctx = _ctx_with_labels(xyz, labels)
    kept, stats = pre.extract_lining_by_label(ctx)  # auto
    assert stats["auto_detected"]
    assert 2 in stats["structure_labels"], stats
    assert 9 not in stats["structure_labels"], stats
    assert abs(stats["n_clean"] - n_shell) < n_shell * 0.02
    return stats


def test_geometric_fallback():
    pre = PreprocessingLayer()
    xyz, labels, _ = _shell_plus_blob()
    ctx = _ctx_with_labels(xyz, None)  # no labels
    kept, stats = pre.extract_lining_by_label(ctx)
    assert stats["method"] == "geometric_fallback", stats
    assert stats["n_clean"] > 0
    return stats


def test_real_fy387():
    if not os.path.isfile(FY387):
        return "skipped (file not found)"
    from tunnel_analysis.io_layer import BaseLayer
    ctx = PipelineContext()
    ctx.scans.append(BaseLayer().load_scan(FY387))
    ctx.active_index = 0
    pre = PreprocessingLayer()
    kept, stats = pre.extract_lining_by_label(ctx)  # auto-detect
    assert stats["method"] == "label"
    assert stats["n_clean"] > 0
    return (f"auto labels={stats['structure_labels']} "
            f"kept={stats['n_clean']:,}/{stats['n_raw']:,} "
            f"inband={stats.get('inband_by_label')}")


if __name__ == "__main__":
    for fn in (test_explicit_labels, test_auto_detect,
               test_geometric_fallback, test_real_fy387):
        print(fn.__name__, "->", fn())
    print("SMOKE TEST PASSED")
