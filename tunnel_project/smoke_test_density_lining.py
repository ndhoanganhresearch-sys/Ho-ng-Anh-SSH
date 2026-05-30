"""Smoke tests for PreprocessingLayer.extract_lining_density_variation.

Run from the tunnel_project directory:
    python smoke_test_density_lining.py

Re-implements SAM4Tun's Algorithm 2 (local density-difference denoising,
zxy239/SAM4Tun). Builds a synthetic tunnel shell plus interior fixtures
(cable run, equipment blob) and verifies the lining is kept while the
interior bore points are removed by the radial density drop-off.
"""
import numpy as np

from tunnel_analysis.preprocessing import PreprocessingLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle


def _shell(n_axial=160, n_theta=180, radius=2.75, length=24.0, seed=0):
    rng = np.random.default_rng(seed)
    y = np.linspace(0.0, length, n_axial)
    th = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    yy, tt = np.meshgrid(y, th)
    rr = radius + rng.normal(0.0, 0.01, yy.shape)  # thin dense lining shell
    x = rr * np.cos(tt)
    z = rr * np.sin(tt)
    return np.column_stack([x.ravel(), yy.ravel(), z.ravel()]).astype(np.float64)


def _interior_cable(length=22.0, n=500, r_in=1.2, ang=1.4, seed=1):
    """A cable run well inside the bore (small radius)."""
    rng = np.random.default_rng(seed)
    y = np.linspace(1.0, length, n)
    x = np.full(n, r_in * np.cos(ang)) + rng.normal(0, 0.01, n)
    z = np.full(n, r_in * np.sin(ang)) + rng.normal(0, 0.01, n)
    return np.column_stack([x, y, z])


def _interior_blob(center=(0.0, 12.0, -1.0), n=400, rad=0.25, seed=2):
    rng = np.random.default_rng(seed)
    p = rng.normal(0, rad, (n, 3))
    return p + np.asarray(center)


def _ctx(points):
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=points))
    ctx.active_index = 0
    return ctx


def _radius_to_axis(pts):
    c = pts.mean(0)
    ev, vecs = np.linalg.eigh(np.cov((pts - c).T))
    ax = vecs[:, np.argmax(ev)]
    diff = pts - c
    return np.linalg.norm(diff - (diff @ ax)[:, None] * ax, axis=1)


def test_density_keeps_shell_removes_interior():
    shell = _shell()
    interior = np.vstack([_interior_cable(), _interior_blob()])
    raw = np.vstack([shell, interior])
    ctx = _ctx(raw)

    clean, stats = PreprocessingLayer().extract_lining_density_variation(ctx)

    assert stats["method"] == "density-variation"
    assert stats["n_removed"] > 0, "nothing removed"
    # Cleaned cloud should keep almost all of the lining shell.
    assert stats["n_clean"] >= 0.9 * len(shell), \
        f"shell over-removed: kept {stats['n_clean']} vs shell {len(shell)}"

    # Direct recall/retention against the known interior vs shell points.
    from scipy.spatial import cKDTree
    tree = cKDTree(clean)
    d_int, _ = tree.query(interior, k=1)
    interior_removed = 1.0 - int(np.sum(d_int < 1e-9)) / len(interior)
    d_sh, _ = tree.query(shell, k=1)
    shell_retention = int(np.sum(d_sh < 1e-9)) / len(shell)
    assert interior_removed >= 0.8, f"interior recall too low: {interior_removed:.2f}"
    assert shell_retention >= 0.9, f"shell retention too low: {shell_retention:.2f}"
    assert ctx.normalized_points is not None and len(ctx.normalized_points) == stats["n_clean"]
    stats = dict(stats)
    stats["interior_removed"] = interior_removed
    stats["shell_retention"] = shell_retention
    return stats


def test_density_tiny_cloud_guard():
    pts = np.random.default_rng(0).normal(size=(20, 3))
    ctx = _ctx(pts)
    clean, stats = PreprocessingLayer().extract_lining_density_variation(ctx)
    assert stats["n_removed"] == 0 and len(clean) == 20
    return stats["method"]


if __name__ == "__main__":
    stats = test_density_keeps_shell_removes_interior()
    guard = test_density_tiny_cloud_guard()
    print("SMOKE TEST PASSED")
    print(f"Raw={stats['n_raw']:,}  clean={stats['n_clean']:,}  removed={stats['n_removed']:,}")
    print(f"Interior removed recall={stats['interior_removed']:.2f}  shell retention={stats['shell_retention']:.2f}")
    print(f"Tiny-cloud guard method: {guard}")
