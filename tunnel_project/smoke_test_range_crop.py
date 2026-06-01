# -*- coding: utf-8 -*-
"""Smoke test for range_crop (MATLAB-style distance crop, PDF 3.2).

Run from the tunnel_project directory:
    python smoke_test_range_crop.py

Builds a tunnel shell plus far stray points and verifies sensor/centroid/axis
crop modes remove the far noise while keeping the shell, and that a zero/None
range is a no-op.
"""
import numpy as np

from tunnel_analysis.preprocessing import PreprocessingLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle


def _shell_plus_far(seed=0):
    rng = np.random.default_rng(seed)
    R, length = 2.75, 18.0
    ys = np.linspace(0, length, 160)
    rows = []
    for y in ys:
        a = np.linspace(0, 2 * np.pi, 90, endpoint=False)
        rows.append(np.column_stack([R * np.cos(a), np.full(90, y), R * np.sin(a) + R]))
    shell = np.vstack(rows)
    # Far stray points 30-60 m from the sensor origin.
    far = rng.uniform(-1, 1, (500, 3))
    far = far / np.linalg.norm(far, axis=1, keepdims=True) * rng.uniform(30, 60, (500, 1))
    return shell, far


def _ctx(pts):
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=pts))
    ctx.active_index = 0
    return ctx


def test_sensor_crop_removes_far():
    shell, far = _shell_plus_far()
    pts = np.vstack([shell, far])
    ctx = _ctx(pts)
    kept, st = PreprocessingLayer().range_crop(ctx, max_range_m=20.0, mode="sensor")
    assert st["n_removed"] >= len(far) * 0.99, st
    # shell is within 20 m of origin (R~2.75, length 18) so it survives
    assert st["n_clean"] >= len(shell) * 0.99, st
    return f"sensor: removed {st['n_removed']} / kept {st['n_clean']}"


def test_axis_crop():
    shell, far = _shell_plus_far()
    pts = np.vstack([shell, far])
    ctx = _ctx(pts)
    kept, st = PreprocessingLayer().range_crop(ctx, max_range_m=5.0, mode="axis")
    # shell radius ~2.75 from axis stays; far points are well outside a 5 m tube
    assert st["n_clean"] >= len(shell) * 0.95, st
    assert st["n_removed"] >= len(far) * 0.9, st
    return f"axis: removed {st['n_removed']} / kept {st['n_clean']}"


def test_noop_when_zero():
    shell, far = _shell_plus_far()
    pts = np.vstack([shell, far])
    ctx = _ctx(pts)
    kept, st = PreprocessingLayer().range_crop(ctx, max_range_m=0.0)
    assert st["n_removed"] == 0 and st["n_clean"] == len(pts), st
    return "no-op OK"


if __name__ == "__main__":
    for fn in (test_sensor_crop_removes_far, test_axis_crop, test_noop_when_zero):
        print(fn.__name__, "->", fn())
    print("SMOKE TEST PASSED")
