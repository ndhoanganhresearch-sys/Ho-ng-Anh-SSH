"""Smoke tests for py4dgeo (M3C2) and small_gicp integrations.

Run from the tunnel_project directory:
    python smoke_test_advanced_integrations.py

Covers:
- TimeSeriesLayer.m3c2_distances detects a known surface displacement.
- M3C2 cloud-to-cloud fallback path works when py4dgeo is absent.
- RegistrationLayer._icp (small_gicp path) recovers a known rigid transform.
"""
import numpy as np

from tunnel_analysis import timeseries as ts_mod
from tunnel_analysis import registration as reg_mod
from tunnel_analysis.timeseries import TimeSeriesLayer
from tunnel_analysis.registration import RegistrationLayer


def _tunnel_wall(n_axial=120, n_theta=60, radius=3.0, length=20.0):
    y = np.linspace(0.0, length, n_axial)
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    yy, tt = np.meshgrid(y, theta)
    x = radius * np.cos(tt)
    z = radius * np.sin(tt) + radius
    return np.column_stack([x.ravel(), yy.ravel(), z.ravel()]).astype(np.float64)


def _flat_floor(nx=120, ny=120, size=10.0):
    """Horizontal plane (normal ~ +Z) so a Z-shift maps directly to M3C2 distance."""
    xs = np.linspace(0.0, size, nx)
    ys = np.linspace(0.0, size, ny)
    xx, yy = np.meshgrid(xs, ys)
    zz = np.zeros_like(xx)
    return np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()]).astype(np.float64)


def test_m3c2_detects_displacement():
    epoch0 = _flat_floor()
    epoch1 = epoch0.copy()
    epoch1[:, 2] += 0.01  # 10 mm shift along the surface normal (Z)

    layer = TimeSeriesLayer()
    out = layer.m3c2_distances(epoch0, epoch1, cyl_radius=0.5, normal_radius=0.6)

    assert out["method"] == "M3C2", f"expected M3C2 path, got {out['method']}"
    median_mm = float(np.nanmedian(out["distance_mm"]))
    assert 8.0 <= abs(median_mm) <= 12.0, f"median displacement off: {median_mm} mm"
    assert out["distance_mm"].shape == out["lod_mm"].shape
    return median_mm


def test_m3c2_fallback(monkeypatched_py4dgeo=True):
    epoch0 = _flat_floor()
    epoch1 = epoch0.copy()
    epoch1[:, 2] += 0.01

    saved = ts_mod.py4dgeo
    try:
        ts_mod.py4dgeo = None  # force fallback
        layer = TimeSeriesLayer()
        out = layer.m3c2_distances(epoch0, epoch1)
    finally:
        ts_mod.py4dgeo = saved

    assert out["method"] == "C2C-fallback", f"expected fallback, got {out['method']}"
    median_mm = float(np.nanmedian(out["distance_mm"]))
    assert 8.0 <= abs(median_mm) <= 12.0, f"fallback median off: {median_mm} mm"
    return median_mm


def _rigid(angle_deg=1.5, translation=(0.06, -0.04, 0.05)):
    a = np.deg2rad(angle_deg)
    c, s = np.cos(a), np.sin(a)
    T = np.eye(4)
    T[:3, :3] = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    T[:3, 3] = np.asarray(translation, dtype=float)
    return T


def test_gicp_recovers_transform():
    if reg_mod.small_gicp is None:
        print("small_gicp not installed; skipping GICP test")
        return None

    tgt = _tunnel_wall()
    # Small residual transform: mirrors the fine-registration regime where
    # _icp runs only after a coarse anchor translation has aligned stations.
    T = _rigid()
    ones = np.ones((tgt.shape[0], 1))
    src = (T @ np.hstack([tgt, ones]).T).T[:, :3]  # source is target moved by T

    layer = RegistrationLayer()
    reg, rmse_mm = layer._icp_gicp(src, tgt)

    assert reg.shape == src.shape
    assert rmse_mm < 5.0, f"GICP RMSE too high: {rmse_mm} mm"
    return rmse_mm


def test_spatiotemporal_series():
    epoch0 = _flat_floor()
    epochs = [epoch0]
    for k in (1, 2, 3):
        e = epoch0.copy()
        e[:, 2] -= 0.003 * k  # progressive 3 mm/step settlement
        epochs.append(e)

    layer = TimeSeriesLayer()
    out = layer.spatiotemporal_series(
        epochs, labels=["T1", "T2", "T3"], cyl_radius=0.5, normal_radius=0.6
    )

    assert out["labels"] == ["T1", "T2", "T3"]
    assert out["distance_matrix_mm"].shape[0] == 3
    expected = np.array([-3.0, -6.0, -9.0])
    assert np.allclose(out["median_mm"], expected, atol=0.5), out["median_mm"]
    return out["median_mm"].tolist()


def test_m3c2_small_cloud_uses_fallback():
    # Below the 10-point threshold the M3C2 path is skipped -> C2C fallback.
    epoch0 = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
    epoch1 = epoch0.copy()
    epoch1[:, 2] += 0.005

    layer = TimeSeriesLayer()
    out = layer.m3c2_distances(epoch0, epoch1)
    assert out["method"] == "C2C-fallback", f"expected fallback, got {out['method']}"
    assert np.all(~out["significant"]), "fallback must report no significance"
    return out["method"]


def test_spatiotemporal_requires_two_epochs():
    layer = TimeSeriesLayer()
    raised = False
    try:
        layer.spatiotemporal_series([_flat_floor()])
    except RuntimeError:
        raised = True
    assert raised, "spatiotemporal_series must require >= 2 epochs"
    return True


if __name__ == "__main__":
    m3c2_mm = test_m3c2_detects_displacement()
    fallback_mm = test_m3c2_fallback()
    gicp_mm = test_gicp_recovers_transform()
    series_mm = test_spatiotemporal_series()
    small_cloud_method = test_m3c2_small_cloud_uses_fallback()
    two_epoch_guard = test_spatiotemporal_requires_two_epochs()
    print("SMOKE TEST PASSED")
    print(f"M3C2 median displacement: {m3c2_mm:.4f} mm")
    print(f"C2C fallback median displacement: {fallback_mm:.4f} mm")
    if gicp_mm is None:
        print("GICP test: skipped (small_gicp missing)")
    else:
        print(f"GICP recovered RMSE: {gicp_mm:.4f} mm")
    print(f"Spatiotemporal series (mm): {[round(x, 2) for x in series_mm]}")
    print(f"Small-cloud path: {small_cloud_method}")
    print(f"Two-epoch guard: {two_epoch_guard}")
