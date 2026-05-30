"""Benchmark: small_gicp (parallel GICP) vs Open3D point-to-plane ICP.

Loads a real LAS scan, applies a known small rigid transform, then times and
scores recovery for both backends. Run from tunnel_project/:

    python benchmark_registration.py [path_to_las]

Defaults to data/T0/box_tunnel_dw.las.
"""
import os
import sys
import time

import numpy as np

from tunnel_analysis.common import o3d, laspy, small_gicp
from tunnel_analysis.registration import RegistrationLayer


def load_points(path: str, max_points: int = 400_000) -> np.ndarray:
    las = laspy.read(path)
    pts = np.vstack([las.x, las.y, las.z]).T.astype(np.float64)
    pts = pts - pts.mean(axis=0)
    if pts.shape[0] > max_points:
        idx = np.random.default_rng(0).choice(pts.shape[0], max_points, replace=False)
        pts = pts[idx]
    return np.ascontiguousarray(pts)


def rigid(angle_deg=1.2, translation=(0.05, -0.04, 0.03)) -> np.ndarray:
    a = np.deg2rad(angle_deg)
    c, s = np.cos(a), np.sin(a)
    T = np.eye(4)
    T[:3, :3] = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    T[:3, 3] = np.asarray(translation, dtype=float)
    return T


def time_call(fn, repeats=3):
    best = float("inf")
    out = None
    for _ in range(repeats):
        t0 = time.perf_counter()
        out = fn()
        best = min(best, time.perf_counter() - t0)
    return out, best


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data", "T0", "box_tunnel_dw.las")
    if not os.path.exists(path):
        print(f"LAS not found: {path}")
        return
    print(f"Loading {path} ...")
    tgt = load_points(path)
    T = rigid()
    ones = np.ones((tgt.shape[0], 1))
    src = (T @ np.hstack([tgt, ones]).T).T[:, :3]
    print(f"Points: {tgt.shape[0]:,}  | applied transform: 1.2 deg yaw + ~7 cm translation")

    layer = RegistrationLayer()

    if small_gicp is not None:
        (reg_g, rmse_g), t_g = time_call(lambda: layer._icp_gicp(src, tgt))
        print(f"small_gicp GICP : RMSE={rmse_g:7.3f} mm | best={t_g*1000:8.1f} ms")
    else:
        print("small_gicp not installed.")

    if o3d is not None:
        # Force Open3D path by temporarily disabling small_gicp inside the module.
        import tunnel_analysis.registration as regmod
        saved = regmod.small_gicp
        regmod.small_gicp = None
        try:
            (reg_o, rmse_o), t_o = time_call(lambda: layer._icp(src, tgt))
        finally:
            regmod.small_gicp = saved
        print(f"Open3D P2Plane  : RMSE={rmse_o:7.3f} mm | best={t_o*1000:8.1f} ms")

    if small_gicp is not None and o3d is not None:
        speedup = t_o / t_g if t_g > 0 else float("nan")
        print(f"Speedup (Open3D / GICP): {speedup:.2f}x")


if __name__ == "__main__":
    main()
