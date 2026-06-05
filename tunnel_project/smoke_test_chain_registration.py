# -*- coding: utf-8 -*-
"""smoke_test_chain_registration.py

Regression tests for two bugs fixed in tunnel_analysis:

BUG 1  register_and_merge_chain -- tgt_intensity mismatch
  tgt_intensity was always context.scans[0].intensity even when current_ref
  had advanced to a later station (i >= 2).
  Fix: use context.scans[i-1].intensity so the intensity indices match the
  points currently in current_ref.

BUG 2  range_crop -- working_points not updated
  range_crop updated normalized_points but not the active backing field of
  the working_points property. When registered_points was already set the
  cropped cloud was silently ignored by downstream steps.
  Fix: update whichever of registered_points/normalized_points is active.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

# Stub optional heavy deps so the test runs headless without Open3D / laspy.
for _mod in ("open3d", "laspy", "pyvista", "pyvistaqt", "small_gicp", "py4dgeo"):
    if _mod not in sys.modules:
        sys.modules[_mod] = None

try:
    from scipy.spatial import cKDTree  # noqa: F401
except ImportError:
    pass

from tunnel_analysis.models import PipelineContext, PointCloudBundle
from tunnel_analysis.registration import RegistrationLayer
from tunnel_analysis.preprocessing import PreprocessingLayer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ring(y, radius=3.0, n=60):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([radius * np.cos(t), np.full(n, y), radius * np.sin(t) + radius])


def _tunnel_cloud(y_values, target=None, tgt_int=65535.0, wall_int=1000.0):
    """Build a tunnel wall cloud for given Y positions, plus one target cluster."""
    wall = np.vstack([_ring(y) for y in y_values])
    iwall = np.full(len(wall), wall_int)
    if target is not None:
        rng = np.random.default_rng(7)
        cluster = target[None, :] + rng.uniform(-0.003, 0.003, (5, 3))
        icluster = np.full(5, tgt_int)
        pts = np.vstack([wall, cluster])
        intensity = np.concatenate([iwall, icluster])
    else:
        pts, intensity = wall, iwall
    return pts.astype(np.float64), intensity.astype(np.float64)


# ---------------------------------------------------------------------------
# Test 1a: chain registration with IDENTICAL scans -> RMSE must be 0
# ---------------------------------------------------------------------------

def test_chain_identical_scans():
    """When all scans are identical the chain must produce RMSE=0 for each step.

    This is the minimal correctness check: any anchor shift on identical clouds
    must be zero, and NN-RMSE of src against itself is zero.  A nonzero result
    would indicate the anchor is picking a wrong point and shifting the cloud.
    """
    TARGET = np.array([2.5, 5.0, 6.0])
    ys = np.linspace(0, 10, 20)
    pts, intensity = _tunnel_cloud(ys, target=TARGET)

    ctx = PipelineContext()
    ctx.scans = [
        PointCloudBundle(points=pts.copy(), intensity=intensity.copy()),
        PointCloudBundle(points=pts.copy(), intensity=intensity.copy()),
        PointCloudBundle(points=pts.copy(), intensity=intensity.copy()),
    ]
    ctx.active_index = 0

    reg = RegistrationLayer()
    merged, rmse_list = reg.register_and_merge_chain(ctx)

    assert merged.shape[1] == 3, "merged cloud must be Nx3"
    assert len(rmse_list) == 3

    for i, rmse in enumerate(rmse_list):
        assert rmse < 1e-6, "scan[%d] RMSE=%.4f mm -- must be 0 for identical scans" % (i, rmse)

    print("PASSED  chain registration: identical scans -> RMSE=0")
    for i, r in enumerate(rmse_list):
        print("  scan[%d] RMSE = %.6f mm" % (i, r))


# ---------------------------------------------------------------------------
# Test 1b: anchor uses correct intensity array (direct unit test)
# ---------------------------------------------------------------------------

def test_anchor_uses_correct_intensity_array():
    """The tgt_intensity fix: _coarse_align must use scans[i-1].intensity.

    We call _coarse_align directly with two different intensity arrays and
    verify that the returned shift matches the expected anchor difference.
    Target A is the highest-intensity point in intensity_a.
    Target B is the highest-intensity point in intensity_b.
    The anchor shift must be anchor(tgt, intensity_a) - anchor(src, src_int).
    """
    rng = np.random.default_rng(42)
    n = 200

    # Generic cloud (no real structure needed for anchor test)
    cloud = rng.uniform(-5, 5, (n, 3)).astype(np.float64)

    # Two different high-intensity points at known positions
    TARGET_A = np.array([10.0, 0.0, 0.0])
    TARGET_B = np.array([0.0, 10.0, 0.0])

    cloud_with_a = np.vstack([cloud, TARGET_A[None, :]])
    cloud_with_b = np.vstack([cloud, TARGET_B[None, :]])

    int_a = np.concatenate([np.ones(n) * 500.0, [65535.0]])  # A is brightest
    int_b = np.concatenate([np.ones(n) * 500.0, [65535.0]])  # B is brightest

    reg = RegistrationLayer()

    # With intensity_a as tgt: anchor(tgt) = TARGET_A
    shifted_a = reg._coarse_align(cloud_with_b, cloud_with_a,
                                  src_intensity=int_b, tgt_intensity=int_a)
    # Expected shift = TARGET_A - TARGET_B = [10, -10, 0]
    # So cloud_with_b should shift by +[10, -10, 0]
    expected_anchor = TARGET_A - TARGET_B
    actual_shift = shifted_a[-1] - cloud_with_b[-1]  # check shift on the target point
    np.testing.assert_allclose(actual_shift, expected_anchor, atol=0.01,
        err_msg="shift with tgt_intensity=int_a must use TARGET_A as anchor")

    # With intensity_b as tgt: anchor(tgt) = TARGET_B
    shifted_b = reg._coarse_align(cloud_with_b, cloud_with_b,
                                  src_intensity=int_b, tgt_intensity=int_b)
    # Same cloud src and tgt -> shift = TARGET_B - TARGET_B = [0,0,0]
    actual_shift_b = shifted_b[-1] - cloud_with_b[-1]
    np.testing.assert_allclose(actual_shift_b, np.zeros(3), atol=0.01,
        err_msg="shift with identical clouds must be zero")

    print("PASSED  _coarse_align uses correct tgt_intensity")


# ---------------------------------------------------------------------------
# Test 2: range_crop working_points propagation
# ---------------------------------------------------------------------------

def test_range_crop_updates_working_points():
    """range_crop must update the active backing field of working_points."""
    rng = np.random.default_rng(1)
    pts = rng.uniform(-30, 30, (500, 3)).astype(np.float64)

    ctx = PipelineContext()
    ctx.scans = [PointCloudBundle(points=pts)]
    ctx.active_index = 0

    pre = PreprocessingLayer()

    # Path A: normalized_points is the active field (no registered_points)
    _, stats_a = pre.range_crop(ctx, max_range_m=10.0, mode="sensor")
    wp_a = ctx.working_points
    n_a = stats_a["n_clean"]
    assert wp_a is not None
    assert len(wp_a) == n_a, "[Path A] working_points=%d, expected %d" % (len(wp_a), n_a)

    # Path B: registered_points is set -- range_crop must update it
    ctx.registered_points = pts.copy()
    _, stats_b = pre.range_crop(ctx, max_range_m=5.0, mode="sensor")
    wp_b = ctx.working_points
    n_b = stats_b["n_clean"]
    assert wp_b is not None
    assert len(wp_b) == n_b, "[Path B] working_points=%d, expected %d" % (len(wp_b), n_b)
    n_reg = len(ctx.registered_points)
    assert n_reg == n_b, "[Path B] registered_points=%d, expected %d" % (n_reg, n_b)

    print("PASSED  range_crop updates working_points")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_chain_identical_scans()
    test_anchor_uses_correct_intensity_array()
    test_range_crop_updates_working_points()
    print("\nAll regression tests passed.")
