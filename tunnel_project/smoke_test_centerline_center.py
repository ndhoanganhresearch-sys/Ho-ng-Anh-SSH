# -*- coding: utf-8 -*-
"""Smoke tests for robust slice-centre + centerline on uneven rings.

Run from the tunnel_project directory:
    python smoke_test_centerline_center.py

Real tunnel scans sample rings unevenly (dense walls, sparse/missing floor),
so the mass centroid (mean) of a slice is pulled off the geometric centre,
producing a zig-zag centreline. GeometricLayer._slice_center fits a circle to
recover the geometric centre. These tests build a partial (unevenly sampled)
ring where the mean is provably wrong and check the fit recovers the true
centre, then verify a full synthetic tunnel yields a straight, low-wander axis.
"""
import numpy as np

from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle


def test_slice_center_beats_mean_on_partial_ring():
    geo = GeometricLayer()
    axis = np.array([0.0, 1.0, 0.0])           # tunnel axis = +Y
    R = 2.75
    true_center = np.array([10.0, 5.0, 3.0])   # offset from origin
    # Sample only 200deg of the ring (floor missing) -> centroid is biased.
    ang = np.linspace(np.deg2rad(20), np.deg2rad(220), 400)
    ring = true_center + np.column_stack([R * np.cos(ang),
                                          np.zeros_like(ang),
                                          R * np.sin(ang)])
    ring += np.random.default_rng(0).normal(0, 0.005, ring.shape)

    mean_c = ring.mean(axis=0)
    fit_c = geo._slice_center(ring, axis)
    err_mean = np.linalg.norm(mean_c - true_center)
    err_fit = np.linalg.norm(fit_c - true_center)
    assert err_fit < err_mean, f"fit ({err_fit:.3f}) not better than mean ({err_mean:.3f})"
    assert err_fit < 0.10, f"fit centre error too high: {err_fit:.3f} m"
    return err_mean, err_fit


def test_centerline_low_lateral_wander():
    # Straight synthetic tunnel along +Y with uneven angular sampling.
    rng = np.random.default_rng(1)
    R, length = 2.75, 20.0
    ys = np.linspace(0, length, 200)
    pts = []
    for y in ys:
        # random subset of angles each ring (uneven sampling)
        m = rng.integers(60, 120)
        ang = rng.uniform(0, 2 * np.pi, m)
        x = R * np.cos(ang) + rng.normal(0, 0.006, m)
        z = R * np.sin(ang) + 3.0 + rng.normal(0, 0.006, m)
        pts.append(np.column_stack([x, np.full(m, y), z]))
    pts = np.vstack(pts)

    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=pts))
    ctx.active_index = 0
    cl, fr = geo_extract(ctx)

    # lateral wander perpendicular to the dominant axis should be small
    c = cl.mean(0)
    ev, vec = np.linalg.eigh(np.cov((cl - c).T))
    o = np.argsort(ev)[::-1]
    e1 = vec[:, o[1]]; e2 = vec[:, o[2]]
    lat = np.column_stack([(cl - c) @ e1, (cl - c) @ e2])
    wander = max(np.ptp(lat[:, 0]), np.ptp(lat[:, 1]))
    assert wander < 0.5, f"centerline lateral wander too high: {wander:.2f} m"
    return wander


def geo_extract(ctx):
    return GeometricLayer().extract_centerline(ctx, section_count=60)


if __name__ == "__main__":
    em, ef = test_slice_center_beats_mean_on_partial_ring()
    wander = test_centerline_low_lateral_wander()
    print("SMOKE TEST PASSED")
    print(f"partial ring centre error: mean={em:.3f} m  fit={ef:.3f} m")
    print(f"centerline lateral wander (straight tunnel): {wander:.3f} m")
