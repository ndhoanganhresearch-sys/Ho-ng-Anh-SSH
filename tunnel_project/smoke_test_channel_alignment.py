# -*- coding: utf-8 -*-
"""Smoke tests for T2: intensity/label stay aligned to working_points.

Run from the tunnel_project directory:
    python smoke_test_channel_alignment.py

After subsetting (SOR/lining) or resampling (voxel), context.working_intensity()
and context.working_labels() must re-attach the raw scan channel by nearest
neighbour instead of dropping it on a length mismatch.
"""
import numpy as np

from tunnel_analysis.models import PipelineContext, PointCloudBundle


def _scan():
    rng = np.random.default_rng(0)
    n_axial, n_theta, R, length = 80, 60, 2.75, 16.0
    y = np.linspace(0, length, n_axial)
    th = np.linspace(0, 2*np.pi, n_theta, endpoint=False)
    yy, tt = np.meshgrid(y, th)
    xyz = np.column_stack([(R*np.cos(tt)).ravel(), yy.ravel(), (R*np.sin(tt)).ravel()+R])
    # intensity = a smooth function of axial position; label = floor(y)
    inten = (xyz[:, 1] * 7.0).astype(np.float64)
    labels = np.floor(xyz[:, 1]).astype(np.int64)
    return xyz, inten, labels


def _ctx(xyz, inten, labels):
    ctx = PipelineContext()
    b = PointCloudBundle(points=xyz, intensity=inten)
    b.metadata["labels"] = labels
    ctx.scans.append(b)
    ctx.active_index = 0
    return ctx


def test_identity_when_no_filtering():
    xyz, inten, labels = _scan()
    ctx = _ctx(xyz, inten, labels)
    assert np.allclose(ctx.working_intensity(), inten)
    assert np.array_equal(ctx.working_labels(), labels)
    return "identity OK"


def test_subset_alignment():
    """Simulate SOR/lining: keep a random subset as normalized_points."""
    xyz, inten, labels = _scan()
    ctx = _ctx(xyz, inten, labels)
    rng = np.random.default_rng(1)
    keep = rng.choice(len(xyz), size=len(xyz)//2, replace=False)
    ctx.normalized_points = xyz[keep]
    wi = ctx.working_intensity()
    wl = ctx.working_labels()
    assert wi is not None and len(wi) == len(keep)
    # exact subset -> nearest neighbour distance 0 -> exact channel values
    assert np.allclose(wi, inten[keep]), np.abs(wi - inten[keep]).max()
    assert np.array_equal(wl, labels[keep])
    return "subset OK"


def test_voxel_resample_alignment():
    """Simulate voxel: new points near originals (not exact)."""
    xyz, inten, labels = _scan()
    ctx = _ctx(xyz, inten, labels)
    rng = np.random.default_rng(2)
    idx = rng.choice(len(xyz), size=len(xyz)//3, replace=False)
    ctx.normalized_points = xyz[idx] + rng.normal(0, 0.003, (len(idx), 3))
    wi = ctx.working_intensity()
    wl = ctx.working_labels()
    assert wi is not None and len(wi) == len(idx)
    # small jitter -> nearest neighbour is the original point -> close values
    assert np.allclose(wi, inten[idx], atol=1.0), np.abs(wi - inten[idx]).max()
    assert np.array_equal(wl, labels[idx])
    return "voxel-resample OK"


def test_no_channel_returns_none():
    xyz, _, _ = _scan()
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=xyz))  # no intensity, no labels
    ctx.active_index = 0
    assert ctx.working_intensity() is None
    assert ctx.working_labels() is None
    return "none-channel OK"


if __name__ == "__main__":
    for fn in (test_identity_when_no_filtering, test_subset_alignment,
               test_voxel_resample_alignment, test_no_channel_returns_none):
        print(fn.__name__, "->", fn())
    print("SMOKE TEST PASSED")
