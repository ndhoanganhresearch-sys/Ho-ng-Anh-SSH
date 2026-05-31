# -*- coding: utf-8 -*-
"""Smoke test: multi-station merge coarse alignment recovers yaw (PDF 3.3).

Run from the tunnel_project directory:
    python smoke_test_merge_coarse.py

Builds a featured tunnel cloud and a second 'station' that is the same cloud
rotated by a known yaw + translated. The new _coarse_align (GROR rotation +
translation) must let ICP converge to a low RMSE, whereas the old anchor-only
init (translation only) leaves the yaw and yields a large RMSE. Skips cleanly
if Open3D is unavailable.
"""
import importlib.util

import numpy as np

from tunnel_analysis.registration import RegistrationLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle

_HAS_O3D = importlib.util.find_spec("open3d") is not None


def _featured_tunnel(seed=0):
    """Tunnel shell + a few off-axis 'targets' so FPFH has structure to match."""
    rng = np.random.default_rng(seed)
    R, length = 2.75, 18.0
    ys = np.linspace(0, length, 160)
    pts = []
    for y in ys:
        ang = np.linspace(0, 2 * np.pi, 90, endpoint=False)
        x = R * np.cos(ang); z = R * np.sin(ang) + R
        pts.append(np.column_stack([x, np.full_like(ang, y), z]))
    shell = np.vstack(pts)
    # Distinct protrusions (boxes) to give the feature matcher something to lock.
    blobs = []
    for cx, cz, cy in [(-2.0, 0.4, 4.0), (2.0, 0.5, 9.0), (0.0, 5.0, 13.0)]:
        b = rng.uniform(-0.3, 0.3, (300, 3)) + np.array([cx, cy, cz])
        blobs.append(b)
    return np.vstack([shell] + blobs).astype(np.float64) + rng.normal(0, 0.004, (len(shell) + 900, 3))


def _yaw(pts, deg, t):
    a = np.deg2rad(deg)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    return pts @ Rz.T + np.asarray(t)


def _rmse(a, b):
    from scipy.spatial import cKDTree
    d, _ = cKDTree(b).query(a, k=1, workers=-1)
    return float(np.sqrt(np.mean(d ** 2))) * 1000.0


def test_coarse_align_recovers_yaw():
    if not _HAS_O3D:
        return "skipped (open3d missing)"
    reg = RegistrationLayer()
    tgt = _featured_tunnel(0)
    src = _yaw(tgt, deg=12.0, t=[0.4, 0.2, 0.05])  # station 2: yaw + shift

    # New coarse path (rotation + translation) then ICP.
    coarse = reg._coarse_align(src, tgt)
    coarse_reg, coarse_rmse = reg._icp(coarse, tgt)

    # Old anchor-only path (translation only) then ICP, for comparison.
    shift = reg._anchor(tgt, None) - reg._anchor(src, None)
    anchor_reg, anchor_rmse = reg._icp(src + shift, tgt)

    assert coarse_rmse < anchor_rmse, f"coarse ({coarse_rmse:.1f}) !< anchor ({anchor_rmse:.1f}) mm"
    assert coarse_rmse < 50.0, f"coarse RMSE too high: {coarse_rmse:.1f} mm"
    return f"coarse={coarse_rmse:.2f} mm  anchor-only={anchor_rmse:.2f} mm"


def test_merge_two_stations():
    if not _HAS_O3D:
        return "skipped (open3d missing)"
    reg = RegistrationLayer()
    tgt = _featured_tunnel(0)
    src = _yaw(tgt, deg=10.0, t=[0.3, 0.0, 0.0])
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=tgt))
    ctx.scans.append(PointCloudBundle(points=src))
    ctx.active_index = 0
    merged, rmse_list = reg.merge_scans(ctx)
    assert merged.shape[0] == len(tgt) + len(src), merged.shape
    assert rmse_list[1] < 50.0, f"merge RMSE too high: {rmse_list[1]:.1f} mm"
    return f"merged {merged.shape[0]} pts, station-2 RMSE {rmse_list[1]:.2f} mm"


if __name__ == "__main__":
    for fn in (test_coarse_align_recovers_yaw, test_merge_two_stations):
        print(fn.__name__, "->", fn())
    print("SMOKE TEST PASSED")
