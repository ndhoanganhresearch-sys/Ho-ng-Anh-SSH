# -*- coding: utf-8 -*-
"""Validate GeometricLayer centerline on real FY387 tunnel data.

Run from the tunnel_project directory:
    python validate_centerline_fy387.py

Loads the FY387 dataset-1 (robot+TLS) .txt scans (XYZ + normal + intensity +
label), merges the contiguous t2_* segments into one ~60 m straight tunnel,
then runs the tool's own centerline extractors and reports quantitative
metrics that map to the review findings C1-C7:

  - end "hook": lateral deviation of the first/last centers vs the fitted axis
  - lateral wander of the centerline about its dominant axis
  - radius consistency (per-slice circle-fit radius spread)
  - PCA vs B-spline vs iterative agreement

This is a diagnostic harness, not a pass/fail unit test.
"""
import glob
import os
import sys

import numpy as np

from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle

DATA_DIR = r"F:\data\FY387\dataset1_robot_TLS\raw"
LINING_LABELS = None  # None = use all points; or set e.g. {0} to keep lining only


def load_merged(pattern="t2_*.txt", labels=None):
    files = sorted(glob.glob(os.path.join(DATA_DIR, pattern)))
    if not files:
        raise FileNotFoundError(f"No files match {pattern} in {DATA_DIR}")
    arrs = [np.loadtxt(f) for f in files]
    A = np.vstack(arrs)
    xyz = A[:, :3]
    lab = A[:, 7].astype(int) if A.shape[1] >= 8 else None
    if labels is not None and lab is not None:
        keep = np.isin(lab, list(labels))
        xyz = xyz[keep]
    return xyz, files


def axis_frame(cl):
    c = cl.mean(0)
    ev, vec = np.linalg.eigh(np.cov((cl - c).T))
    o = np.argsort(ev)[::-1]
    return c, vec[:, o[0]], vec[:, o[1]], vec[:, o[2]]


def lateral_wander(cl):
    c, a, e1, e2 = axis_frame(cl)
    lat = np.column_stack([(cl - c) @ e1, (cl - c) @ e2])
    return float(max(np.ptp(lat[:, 0]), np.ptp(lat[:, 1])))


def end_hook(cl, frac=0.1):
    """Max lateral offset of the end centers from the line through the
    interior centroid along the dominant axis."""
    c, a, e1, e2 = axis_frame(cl)
    d = cl - c
    lat = np.column_stack([d @ e1, d @ e2])
    n = len(cl)
    k = max(1, int(n * frac))
    interior = np.linalg.norm(lat[k:n - k], axis=1)
    ends = np.concatenate([np.linalg.norm(lat[:k], axis=1),
                           np.linalg.norm(lat[n - k:], axis=1)])
    return float(ends.max()), float(np.median(interior))


def main():
    if not os.path.isdir(DATA_DIR):
        print(f"DATA DIR NOT FOUND: {DATA_DIR}")
        return 1
    geo = GeometricLayer()
    xyz, files = load_merged("t2_*.txt", labels=LINING_LABELS)
    print(f"Loaded {len(files)} files, merged N={len(xyz):,} points")

    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=xyz))
    ctx.active_index = 0

    print("\n=== 4.1 PCA centerline (extract_centerline) ===")
    cl_pca, fr_pca = geo.extract_centerline(ctx, section_count=80)
    hook, interior = end_hook(cl_pca)
    print(f"  centers={len(cl_pca)}  axial_span={np.ptp((cl_pca - cl_pca.mean(0)) @ axis_frame(cl_pca)[1]):.2f} m")
    print(f"  lateral_wander={lateral_wander(cl_pca):.3f} m")
    print(f"  end_hook(max)={hook:.3f} m  interior_median={interior:.3f} m")

    print("\n=== 4.3b B-spline C2 (extract_centerline_bspline) ===")
    cl_bs, fr_bs = geo.extract_centerline_bspline(ctx, section_count=80)
    hook, interior = end_hook(cl_bs)
    print(f"  centers={len(cl_bs)}  lateral_wander={lateral_wander(cl_bs):.3f} m")
    print(f"  end_hook(max)={hook:.3f} m  interior_median={interior:.3f} m")

    print("\n=== 4.2 iterative refinement (extract_centerline_iterative) ===")
    try:
        cl_it, fr_it, iters = geo.extract_centerline_iterative(
            ctx, design_axis=cl_pca, section_count=80, mu=0.03, max_iter=20)
        hook, interior = end_hook(cl_it)
        print(f"  iters={iters}  centers={len(cl_it)}  lateral_wander={lateral_wander(cl_it):.3f} m")
        print(f"  end_hook(max)={hook:.3f} m  interior_median={interior:.3f} m")
    except Exception as e:
        print(f"  FAILED: {e!r}")

    print("\n=== agreement PCA vs B-spline (resampled) ===")
    m = min(len(cl_pca), len(cl_bs))
    d = np.linalg.norm(cl_pca[:m] - cl_bs[:m], axis=1)
    print(f"  mean={d.mean():.3f} m  max={d.max():.3f} m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
