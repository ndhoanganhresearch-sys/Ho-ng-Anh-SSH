# -*- coding: utf-8 -*-
"""Smoke tests for wall-mounted cable detection (Stage C of auto_denoise).

Run from the tunnel_project directory:
    python smoke_test_wall_cable.py

Per-point shape features cannot separate a cable hugging the wall (verified on
labelled real data: cable linearity ~ wall linearity). Stage C detects such
cables by inward protrusion from the local wall envelope plus axial continuity.
These tests use a synthetic shell + a wall-hugging cable to confirm the cable
is flagged while the shell is preserved.
"""
import numpy as np

from tunnel_analysis.preprocessing import PreprocessingLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle


def _shell(n_axial=200, n_theta=220, radius=2.75, length=24.0, seed=0):
    rng = np.random.default_rng(seed)
    y = np.linspace(0.0, length, n_axial)
    th = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    yy, tt = np.meshgrid(y, th)
    rr = radius + rng.normal(0.0, 0.008, yy.shape)
    return np.column_stack([(rr * np.cos(tt)).ravel(), yy.ravel(), (rr * np.sin(tt)).ravel()])


def _wall_cable(radius=2.75, inset=0.10, angle_deg=130.0, n=2500, length=23.0, seed=1):
    """Cable just inside the wall (radius = R - inset), fixed angle, running
    along the axis with a thin tangential/radial spread."""
    rng = np.random.default_rng(seed)
    ang = np.deg2rad(angle_deg)
    y = np.linspace(1.0, length, n)
    rc = (radius - inset) + rng.normal(0, 0.01, n)
    tang = rng.normal(0, 0.015, n)
    x = rc * np.cos(ang) - tang * np.sin(ang)
    z = rc * np.sin(ang) + tang * np.cos(ang)
    return np.column_stack([x, y, z])


def _ctx(points):
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=points))
    ctx.active_index = 0
    return ctx


def test_detect_wall_protrusion_flags_cable():
    shell = _shell()
    cable = _wall_cable()
    pts = np.vstack([shell, cable]).astype(np.float64)
    is_cable_truth = np.concatenate([np.zeros(len(shell), bool), np.ones(len(cable), bool)])

    candidate = np.ones(len(pts), bool)
    mask = PreprocessingLayer._detect_wall_protrusion(pts, candidate, protrusion_thr=0.05)

    recall = mask[is_cable_truth].mean()
    shell_false = mask[~is_cable_truth].mean()
    assert recall >= 0.7, f"cable recall too low: {recall:.2f}"
    assert shell_false <= 0.05, f"too much shell flagged: {shell_false:.2f}"
    return float(recall), float(shell_false)


def test_auto_denoise_removes_wall_cable():
    shell = _shell(seed=3)
    cable = _wall_cable(seed=4)
    pts = np.vstack([shell, cable]).astype(np.float64)
    ctx = _ctx(pts)
    clean, stats = PreprocessingLayer().auto_denoise(ctx)

    from scipy.spatial import cKDTree
    d, _ = cKDTree(clean).query(cable, k=1)
    cable_removed = 1.0 - (d < 1e-9).sum() / len(cable)
    d2, _ = cKDTree(clean).query(shell, k=1)
    shell_kept = (d2 < 1e-9).sum() / len(shell)
    # Functional guarantee: the wall cable is gone and the shell preserved.
    # (Which stage removes it can vary; Stage C is proven separately in
    # test_detect_wall_protrusion_flags_cable.)
    assert cable_removed >= 0.7, f"wall cable not removed: {cable_removed:.2f}"
    assert shell_kept >= 0.85, f"shell over-removed: {shell_kept:.2f}"
    return cable_removed, shell_kept


def test_stage_c_can_be_disabled():
    shell = _shell(seed=5)
    cable = _wall_cable(seed=6)
    ctx = _ctx(np.vstack([shell, cable]).astype(np.float64))
    _, stats = PreprocessingLayer().auto_denoise(ctx, wall_protrusion_thr=0.0)
    assert stats.get("n_wall_cable", 0) == 0, "Stage C should be off at thr=0"
    return True


if __name__ == "__main__":
    rec, sf = test_detect_wall_protrusion_flags_cable()
    cr, sk = test_auto_denoise_removes_wall_cable()
    off = test_stage_c_can_be_disabled()
    print("SMOKE TEST PASSED")
    print(f"detector: cable recall={rec:.2f}  shell false-flag={sf:.3f}")
    print(f"auto_denoise: wall cable removed={cr:.2f}  shell kept={sk:.2f}")
    print(f"Stage C disable flag works: {off}")
