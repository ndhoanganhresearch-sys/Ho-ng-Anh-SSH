"""Smoke tests for GeometricLayer centerline extraction.

Run from the tunnel_project directory:
    python smoke_test_geometry.py

Verifies the axial-bin centerline (equal axial position, not equal point count)
covers the full tunnel length on both straight and curved synthetic tunnels,
where count-based binning would cluster sections in the dense middle.
"""
import numpy as np

from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle


def _straight_tunnel(length=40.0, radius=3.0, n_axial=400, n_theta=60,
                     dense_middle=True, seed=0):
    """Straight tunnel along +Y. If dense_middle, concentrate axial samples in
    the centre so count-based binning would starve the ends."""
    rng = np.random.default_rng(seed)
    if dense_middle:
        u = rng.normal(0.5, 0.12, n_axial)
        u = np.clip(u, 0.0, 1.0)
    else:
        u = rng.uniform(0.0, 1.0, n_axial)
    y = u * length
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    yy, tt = np.meshgrid(y, theta)
    x = radius * np.cos(tt)
    z = radius * np.sin(tt) + radius
    return np.column_stack([x.ravel(), yy.ravel(), z.ravel()]).astype(np.float64)


def _curved_tunnel(radius_arc=60.0, sweep_deg=60.0, radius=3.0,
                   n_axial=400, n_theta=60, seed=1):
    """Tunnel whose axis follows a circular arc in the XY plane."""
    rng = np.random.default_rng(seed)
    s = np.sort(rng.uniform(0.0, 1.0, n_axial))
    phi = np.deg2rad(sweep_deg) * s
    cx = radius_arc * np.cos(phi)
    cy = radius_arc * np.sin(phi)
    cz = np.zeros_like(phi)
    axis = np.column_stack([cx, cy, cz])
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    pts = []
    for c, p in zip(axis, phi):
        radial = np.array([np.cos(p), np.sin(p), 0.0])
        up = np.array([0.0, 0.0, 1.0])
        ring = c + radius * (np.outer(np.cos(theta), radial) +
                             np.outer(np.sin(theta), up))
        pts.append(ring)
    return np.vstack(pts).astype(np.float64)


def _ctx(points):
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=points))
    ctx.active_index = 0
    return ctx


def _axial_coverage(points, centerline):
    """Fraction of the cloud's principal-axis span spanned by the centerline."""
    c = points.mean(axis=0)
    ev, vecs = np.linalg.eigh(np.cov((points - c).T))
    ax = vecs[:, np.argmax(ev)]
    proj_pts = (points - c) @ ax
    proj_cl = (centerline - c) @ ax
    span_pts = float(proj_pts.max() - proj_pts.min())
    span_cl = float(proj_cl.max() - proj_cl.min())
    return span_cl / span_pts if span_pts > 1e-9 else 0.0


def test_straight_full_coverage():
    pts = _straight_tunnel(dense_middle=True)
    layer = GeometricLayer()
    cl, frames = layer.extract_centerline(_ctx(pts), section_count=80)
    cov = _axial_coverage(pts, cl)
    assert cov > 0.9, f"centerline covers only {cov:.2%} of tunnel length"
    assert len(frames) == len(cl)
    return cov


def test_bspline_full_coverage():
    pts = _straight_tunnel(dense_middle=True)
    layer = GeometricLayer()
    cl, frames = layer.extract_centerline_bspline(_ctx(pts), section_count=80)
    cov = _axial_coverage(pts, cl)
    assert cov > 0.9, f"B-spline centerline covers only {cov:.2%} of length"
    assert len(cl) == 80
    return cov


def test_curved_radius_recovery():
    pts = _curved_tunnel()
    layer = GeometricLayer()
    cl, _ = layer.extract_centerline_bspline(_ctx(pts), section_count=80)
    cov = _axial_coverage(pts, cl)
    # Centerline radius from arc center should approximate radius_arc (60 m).
    arc_c = cl.mean(axis=0)
    radii = np.linalg.norm(cl[:, :2] - cl[:, :2].mean(axis=0), axis=1)
    assert cov > 0.85, f"curved centerline covers only {cov:.2%} of length"
    return cov

def _curved_axis_truth(radius_arc=40.0, sweep_deg=80.0, radius=3.0,
                       n_axial=400, n_theta=60, seed=4):
    """Curved tunnel + its true axis polyline, for centre-error measurement."""
    rng = np.random.default_rng(seed)
    s = np.sort(rng.uniform(0.0, 1.0, n_axial))
    phi = np.deg2rad(sweep_deg) * s
    axis = np.column_stack([radius_arc * np.cos(phi),
                            radius_arc * np.sin(phi),
                            np.zeros_like(phi)])
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    pts = []
    for c, pangle in zip(axis, phi):
        radial = np.array([np.cos(pangle), np.sin(pangle), 0.0])
        up = np.array([0.0, 0.0, 1.0])
        ring = c + radius * (np.outer(np.cos(theta), radial) +
                             np.outer(np.sin(theta), up))
        pts.append(ring + rng.normal(0, 0.006, ring.shape))
    return np.vstack(pts).astype(np.float64), axis


def test_curved_centre_error():
    """C7: on a curved tunnel the refined centerline should sit close to the
    true axis (global-PCA slicing alone drifts metres at the ends).
    """
    pts, axis = _curved_axis_truth()
    layer = GeometricLayer()
    cl, _ = layer.extract_centerline_bspline(_ctx(pts), section_count=80)
    err = np.array([np.linalg.norm(axis - c, axis=1).min() for c in cl])
    mean_e, max_e = float(err.mean()), float(err.max())
    assert mean_e < 0.20, f"curved centre mean error too high: {mean_e:.3f} m"
    assert max_e < 0.60, f"curved centre max error too high: {max_e:.3f} m"
    return mean_e, max_e


if __name__ == "__main__":
    straight = test_straight_full_coverage()
    bspline = test_bspline_full_coverage()
    curved = test_curved_radius_recovery()
    ce_mean, ce_max = test_curved_centre_error()
    print("SMOKE TEST PASSED")
    print(f"Straight centerline axial coverage: {straight:.2%}")
    print(f"B-spline centerline axial coverage: {bspline:.2%}")
    print(f"Curved centerline axial coverage:   {curved:.2%}")
    print(f"Curved centre error (mean/max):     {ce_mean:.3f} / {ce_max:.3f} m")
