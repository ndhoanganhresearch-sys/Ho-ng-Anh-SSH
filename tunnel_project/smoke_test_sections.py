# -*- coding: utf-8 -*-
"""Smoke tests for ParameterLayer.compute_all_sections (Step 5.7).

Run from the tunnel_project directory:
    python smoke_test_sections.py

This is the end-to-end section pass that builds 2D cross-sections and per-section
geometry (H/W, ovality, eccentricity, wall angles, clearance). It exercises the
2D code paths (e.g. _wall_angle) that the T1 PCA refactor broke with an Nx3
guard, so this test guards against that class of regression.
"""
import numpy as np

from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle


def _straight_tunnel(R=2.75, length=24.0, n_axial=200, seed=0):
    rng = np.random.default_rng(seed)
    y = np.linspace(0.0, length, n_axial)
    pts = []
    for yy in y:
        m = rng.integers(70, 120)
        ang = rng.uniform(0.0, 2 * np.pi, m)
        x = R * np.cos(ang) + rng.normal(0, 0.006, m)
        z = R * np.sin(ang) + R + rng.normal(0, 0.006, m)
        pts.append(np.column_stack([x, np.full(m, yy), z]))
    return np.vstack(pts).astype(np.float64)


def _ctx(pts):
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=pts))
    ctx.active_index = 0
    return ctx


def test_compute_all_sections_runs():
    geo, par = GeometricLayer(), ParameterExtractionLayer()
    ctx = _ctx(_straight_tunnel())
    cl, fr = geo.extract_centerline_bspline(ctx, section_count=60)
    ctx.centerline, ctx.frenet_frames = cl, fr
    ctx.tunnel_profile = par.detect_profile(ctx)
    secs = par.compute_all_sections(ctx, vl_box_w=5.0, vl_box_h=5.0, vl_cir_r=2.7)
    assert len(secs) == len(fr), (len(secs), len(fr))
    # Radius should be recovered near the true 2.75 m on a clean synthetic ring.
    radii = [s.radius_fit for s in secs if np.isfinite(s.radius_fit)]
    assert radii, "no finite radius_fit"
    med = float(np.median(radii))
    assert 2.4 <= med <= 3.1, f"median radius off: {med:.3f}"
    return f"{len(secs)} sections, median radius {med:.3f} m"


def test_wall_angle_2d_path():
    """Directly exercise the 2D _wall_angle helper (the Nx3 regression site)."""
    par = ParameterExtractionLayer()
    rng = np.random.default_rng(1)
    # Build a 2D section: vertical-ish walls + flat-ish floor.
    wall_l = np.column_stack([np.full(60, -2.6) + rng.normal(0, 0.02, 60),
                              np.linspace(0.5, 4.5, 60)])
    wall_r = np.column_stack([np.full(60, 2.6) + rng.normal(0, 0.02, 60),
                              np.linspace(0.5, 4.5, 60)])
    floor = np.column_stack([np.linspace(-2.6, 2.6, 60),
                             np.full(60, 0.2) + rng.normal(0, 0.02, 60)])
    pts2d = np.vstack([wall_l, wall_r, floor])
    aL = par._wall_angle(pts2d, side="left")
    aR = par._wall_angle(pts2d, side="right")
    assert np.isfinite(aL) and np.isfinite(aR), (aL, aR)
    assert 60.0 <= aL <= 90.0 and 60.0 <= aR <= 90.0, (aL, aR)
    return f"wall angles L={aL:.1f} R={aR:.1f}"


if __name__ == "__main__":
    for fn in (test_compute_all_sections_runs, test_wall_angle_2d_path):
        print(fn.__name__, "->", fn())
    print("SMOKE TEST PASSED")
