"""Smoke tests for GROR-inspired robust registration (RegistrationLayer).

Run from the tunnel_project directory:
    python smoke_test_gror_registration.py

Verifies that:
- FPFH correspondences + pairwise-distance graph filtering recover a known
  rigid transform between two overlapping tunnel scans.
- The graph inlier filter rejects synthetic outlier correspondences.
- register_gror_like aligns a rotated/translated scan to the reference and
  reduces RMSE versus the unaligned cloud.
"""
import numpy as np

from tunnel_analysis.registration import RegistrationLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle


def _tunnel(n_axial=160, n_theta=60, radius=3.0, length=24.0, seed=0):
    rng = np.random.default_rng(seed)
    y = np.linspace(0.0, length, n_axial)
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    yy, tt = np.meshgrid(y, theta)
    x = radius * np.cos(tt)
    z = radius * np.sin(tt) + radius
    pts = np.column_stack([x.ravel(), yy.ravel(), z.ravel()]).astype(np.float64)
    pts += rng.normal(0.0, 0.003, pts.shape)  # mild scan noise
    return pts


def _rigid(angle_deg=6.0, axis="z", t=(0.5, -0.3, 0.2)):
    a = np.deg2rad(angle_deg)
    c, s = np.cos(a), np.sin(a)
    if axis == "z":
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)
    else:
        R = np.eye(3)
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = np.asarray(t, dtype=np.float64)
    return M


def _apply(M, pts):
    ones = np.ones((len(pts), 1))
    return (M @ np.hstack([pts, ones]).T).T[:, :3]


def _ctx(reference, moved):
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=reference))   # scan[0] = target/ref
    ctx.scans.append(PointCloudBundle(points=moved))       # scan[1] = active source
    ctx.active_index = 1
    return ctx


def _rmse_mm(a, b_tree_pts):
    from scipy.spatial import cKDTree
    d, _ = cKDTree(b_tree_pts).query(a, k=1, workers=-1)
    return float(np.sqrt(np.mean(d ** 2))) * 1000.0


def test_graph_filter_rejects_outliers():
    layer = RegistrationLayer()
    base = _tunnel(n_axial=40, n_theta=20, seed=1)
    idx = np.random.default_rng(2).choice(len(base), 30, replace=False)
    ps = base[idx]
    M = _rigid(angle_deg=5.0)
    pt = _apply(M, ps)  # perfect inlier correspondences
    # Corrupt 12 of them with random target points (outliers).
    rng = np.random.default_rng(3)
    bad = rng.choice(30, 12, replace=False)
    pt[bad] = base[rng.choice(len(base), 12)]
    inliers = layer._graph_reliable_inliers(ps, pt, dist_tol=2.0 * 0.05)
    # No corrupted correspondence should survive; enough clean ones should.
    assert not np.any(inliers[bad]), "outliers leaked through graph filter"
    assert int(inliers.sum()) >= 10, f"too few inliers kept: {inliers.sum()}"
    return int(inliers.sum())


def test_umeyama_recovers_transform():
    layer = RegistrationLayer()
    pts = _tunnel(n_axial=30, n_theta=20, seed=4)[:40]
    M = _rigid(angle_deg=7.0, t=(1.0, -0.5, 0.3))
    moved = _apply(M, pts)
    M_est = layer._umeyama(pts, moved)
    err = float(np.linalg.norm(M_est - M))
    assert err < 1e-6, f"Umeyama transform error too high: {err}"
    return err


def test_register_gror_like_reduces_rmse():
    reference = _tunnel(seed=10)
    M = _rigid(angle_deg=6.0, t=(0.6, -0.4, 0.25))
    moved = _apply(M, reference)  # same surface, displaced by a known pose
    ctx = _ctx(reference, moved)

    layer = RegistrationLayer()
    before = _rmse_mm(moved, reference)
    registered, rmse_mm = layer.register_gror_like(ctx)
    after = _rmse_mm(registered, reference)

    assert registered.shape == moved.shape
    assert after < before, f"RMSE not reduced: before={before:.1f} after={after:.1f}"
    assert after < 50.0, f"post-registration RMSE too high: {after:.1f} mm"
    return before, after, rmse_mm


if __name__ == "__main__":
    kept = test_graph_filter_rejects_outliers()
    umeyama_err = test_umeyama_recovers_transform()
    before, after, rmse_mm = test_register_gror_like_reduces_rmse()
    print("SMOKE TEST PASSED")
    print(f"Graph filter kept inliers: {kept}/30 (outliers rejected)")
    print(f"Umeyama transform error: {umeyama_err:.2e}")
    print(f"register_gror_like RMSE: before={before:.1f} mm -> after={after:.1f} mm")
    print(f"Reported ICP RMSE: {rmse_mm:.3f} mm")
