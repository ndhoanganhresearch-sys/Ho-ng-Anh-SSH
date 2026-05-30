"""Smoke tests for PreprocessingLayer.auto_denoise (fully automatic denoising).

Run from the tunnel_project directory:
    python smoke_test_auto_denoise.py

Builds a synthetic tunnel lining and injects non-structural objects (a cable
line, a light fixture cluster, a person-sized cluster, and stray interior
points), then verifies auto_denoise removes the clutter while preserving the
lining, with no manual interaction.
"""
import numpy as np

from tunnel_analysis.preprocessing import PreprocessingLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle


def _tunnel_shell(n_axial=120, n_theta=80, radius=3.0, length=20.0, seed=0):
    rng = np.random.default_rng(seed)
    y = np.linspace(0.0, length, n_axial)
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    yy, tt = np.meshgrid(y, theta)
    x = radius * np.cos(tt)
    z = radius * np.sin(tt) + radius
    pts = np.column_stack([x.ravel(), yy.ravel(), z.ravel()]).astype(np.float64)
    pts += rng.normal(0.0, 0.004, pts.shape)  # scan noise on the lining
    return pts


def _cable(length=18.0, n=300, height=5.4, seed=1):
    """Thin near-horizontal line along the tunnel axis (high linearity)."""
    rng = np.random.default_rng(seed)
    y = np.linspace(1.0, length, n)
    x = np.full(n, 0.15) + rng.normal(0, 0.004, n)
    z = np.full(n, height) + rng.normal(0, 0.004, n)
    return np.column_stack([x, y, z])


def _light(center=(0.0, 10.0, 5.8), n=180, r=0.12, seed=2):
    """Small isolated blob (high sphericity)."""
    rng = np.random.default_rng(seed)
    p = rng.normal(0, r, (n, 3))
    return p + np.asarray(center)


def _person(center=(1.6, 6.0, 0.0), n=400, seed=3):
    """Upright person-sized cluster (~1.7 m tall, < 0.8 m wide)."""
    rng = np.random.default_rng(seed)
    x = rng.normal(center[0], 0.18, n)
    y = rng.normal(center[1], 0.18, n)
    z = rng.uniform(0.0, 1.7, n) + center[2]
    return np.column_stack([x, y, z])


def _ctx(points):
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=points))
    ctx.active_index = 0
    return ctx


def _radial_spread(pts):
    """Std of radial distance to the PCA axis (lining is tight, clutter widens it)."""
    c = pts.mean(0)
    ev, vecs = np.linalg.eigh(np.cov((pts - c).T))
    ax = vecs[:, np.argmax(ev)]
    diff = pts - c
    ri = np.linalg.norm(diff - (diff @ ax)[:, None] * ax, axis=1)
    return float(np.std(ri))


def test_auto_denoise_removes_clutter_keeps_lining():
    shell = _tunnel_shell()
    clutter = np.vstack([_cable(), _light(), _person()])
    raw = np.vstack([shell, clutter])
    ctx = _ctx(raw)

    layer = PreprocessingLayer()
    clean, stats = layer.auto_denoise(ctx)

    assert stats["n_raw"] == len(raw)
    assert stats["n_removed"] > 0, "nothing was removed"
    # Most clutter should be gone; lining mostly preserved.
    assert stats["n_removed"] >= 0.6 * len(clutter), \
        f"removed only {stats['n_removed']} of {len(clutter)} clutter points"
    assert stats["n_clean"] >= 0.8 * len(shell), \
        f"kept only {stats['n_clean']} vs lining {len(shell)} (over-aggressive)"
    # Cleaned cloud should be a tighter ring than the raw cloud.
    assert _radial_spread(clean) < _radial_spread(raw), "radial spread not reduced"
    # Context updated in place for the next pipeline stage.
    assert ctx.normalized_points is not None and len(ctx.normalized_points) == stats["n_clean"]
    return stats


def test_auto_denoise_handles_tiny_cloud():
    pts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float64)
    ctx = _ctx(pts)
    clean, stats = PreprocessingLayer().auto_denoise(ctx)
    assert stats["n_removed"] == 0 and len(clean) == 3
    return True


def test_auto_denoise_clean_input_keeps_most():
    shell = _tunnel_shell(seed=7)
    ctx = _ctx(shell)
    clean, stats = PreprocessingLayer().auto_denoise(ctx)
    # A clean lining should lose only a small fraction to statistical trimming.
    assert stats["n_clean"] >= 0.9 * len(shell), \
        f"clean lining over-trimmed: kept {stats['n_clean']}/{len(shell)}"
    return stats["n_clean"], len(shell)


def test_cable_precision_recall():
    """Cable cluster should be removed without taking the lining with it."""
    shell = _tunnel_shell(seed=11)
    cable = _cable(seed=12)
    raw = np.vstack([shell, cable])
    ctx = _ctx(raw)
    layer = PreprocessingLayer()
    clean, stats = layer.auto_denoise(ctx)

    # Recall: most cable points gone. Approximate by counting how many of the
    # cable points survive in the cleaned cloud (nearest-neighbour match).
    from scipy.spatial import cKDTree
    tree = cKDTree(clean)
    d, _ = tree.query(cable, k=1)
    cable_surviving = int(np.sum(d < 1e-6))
    recall = 1.0 - cable_surviving / len(cable)

    d2, _ = cKDTree(clean).query(shell, k=1)
    shell_surviving = int(np.sum(d2 < 1e-6))
    lining_retention = shell_surviving / len(shell)

    assert recall >= 0.7, f"cable recall too low: {recall:.2f}"
    assert lining_retention >= 0.9, f"lining over-removed: {lining_retention:.2f}"
    return recall, lining_retention


def test_demantke_features_discriminate():
    """Demantke linearity must rank a line above a plane patch."""
    rng = np.random.default_rng(20)
    # Linear cluster along X.
    line = np.column_stack([np.linspace(0, 2, 60),
                            rng.normal(0, 0.003, 60),
                            rng.normal(0, 0.003, 60)])
    # Planar patch in XY.
    gx, gy = np.meshgrid(np.linspace(0, 1, 12), np.linspace(0, 1, 12))
    plane = np.column_stack([gx.ravel(), gy.ravel(),
                             rng.normal(0, 0.003, gx.size)])

    def linearity(pts):
        ev = np.sort(np.linalg.eigvalsh(np.cov(pts.T)))[::-1]
        s1, s2, s3 = np.sqrt(np.clip(ev, 0, None))
        s1 = s1 if s1 > 1e-12 else 1e-12
        return (s1 - s2) / s1

    lin_line = linearity(line)
    lin_plane = linearity(plane)
    assert lin_line > 0.8, f"line linearity too low: {lin_line:.2f}"
    assert lin_plane < 0.5, f"plane linearity too high: {lin_plane:.2f}"
    assert lin_line > lin_plane
    return lin_line, lin_plane


if __name__ == "__main__":
    stats = test_auto_denoise_removes_clutter_keeps_lining()
    tiny = test_auto_denoise_handles_tiny_cloud()
    kept, shell_n = test_auto_denoise_clean_input_keeps_most()
    recall, retention = test_cable_precision_recall()
    lin_line, lin_plane = test_demantke_features_discriminate()
    print("SMOKE TEST PASSED")
    print(f"Raw={stats['n_raw']:,}  clean={stats['n_clean']:,}  removed={stats['n_removed']:,}")
    print(f"  cable={stats['n_cable']}  light={stats['n_light']}  person={stats['n_person']}  radial={stats['n_radial']}")
    print(f"Tiny-cloud guard: {tiny}")
    print(f"Clean-input retention: {kept:,}/{shell_n:,}")
    print(f"Cable recall={recall:.2f}  lining retention={retention:.2f}")
    print(f"Demantke linearity: line={lin_line:.2f}  plane={lin_plane:.2f}")
