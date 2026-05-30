# -*- coding: utf-8 -*-
"""Validation harness for auto_denoise against labelled tunnel point clouds.

Designed for the STSD benchmark (Cui et al., 2024 — "STSD: A large-scale
benchmark for semantic segmentation of subway tunnel point cloud"). STSD is
distributed on request via a Google Form, so the labelled LAS files are NOT
bundled here. Once you obtain a segment, run:

    python validate_auto_denoise_stsd.py path/to/segment.las

The harness treats the tunnel lining/structural classes as "keep" and every
other class (cables, lights, signal devices, vehicles, people, etc.) as
"remove", then reports precision/recall/F1 and lining retention for
PreprocessingLayer.auto_denoise.

Edit STRUCTURE_LABELS to match the STSD label ids you downloaded (the dataset
annotates 12 categories; see its README/Table 2 for the legend).
"""
import sys
from pathlib import Path

import numpy as np

from tunnel_analysis.preprocessing import PreprocessingLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle

# STSD label ids considered structural lining (KEEP). Adjust to the codes in
# the downloaded dataset; everything else counts as non-structural (REMOVE).
STRUCTURE_LABELS = {1, 2}  # placeholder: e.g. {lining, track-bed}


def load_las_with_labels(path):
    """Load XYZ + per-point class label from a LAS file.

    Looks for the label in a 'classification' field or a named extra dimension
    ('label'/'class'/'category'). Returns (xyz Nx3, labels N,)."""
    import laspy
    las = laspy.read(path)
    xyz = np.vstack([las.x, las.y, las.z]).T.astype(np.float64)
    labels = None
    for name in ("label", "class", "category", "Classification", "classification"):
        if name in las.point_format.dimension_names:
            labels = np.asarray(las[name]).astype(np.int64)
            break
    if labels is None and hasattr(las, "classification"):
        labels = np.asarray(las.classification).astype(np.int64)
    if labels is None:
        raise RuntimeError("No per-point label field found in LAS.")
    return xyz, labels


def evaluate(xyz, labels):
    keep_truth = np.isin(labels, list(STRUCTURE_LABELS))  # True = structural
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=xyz))
    ctx.active_index = 0

    clean, stats = PreprocessingLayer().auto_denoise(ctx)

    # Map cleaned points back to originals to derive a per-point keep mask.
    from scipy.spatial import cKDTree
    tree = cKDTree(clean)
    d, _ = tree.query(xyz, k=1)
    kept_pred = d < 1e-6  # True = auto_denoise kept this point

    # "Positive" = correctly identified as noise (removed).
    removed_pred = ~kept_pred
    removed_truth = ~keep_truth
    tp = int(np.sum(removed_pred & removed_truth))
    fp = int(np.sum(removed_pred & keep_truth))   # removed structural (bad)
    fn = int(np.sum(kept_pred & removed_truth))   # kept noise (missed)
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if precision and recall and np.isfinite(precision) and np.isfinite(recall) else float("nan"))
    lining_retention = (int(np.sum(kept_pred & keep_truth)) / int(np.sum(keep_truth))
                        if np.sum(keep_truth) else float("nan"))
    return {
        "n_points": len(xyz),
        "n_structural": int(np.sum(keep_truth)),
        "n_noise_truth": int(np.sum(removed_truth)),
        "n_removed": int(np.sum(removed_pred)),
        "noise_precision": precision,
        "noise_recall": recall,
        "noise_f1": f1,
        "lining_retention": lining_retention,
        "stats": stats,
    }


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        print("Usage: python validate_auto_denoise_stsd.py <segment.las> [more.las ...]")
        return 1
    for path in argv[1:]:
        if not Path(path).exists():
            print(f"[skip] not found: {path}")
            continue
        xyz, labels = load_las_with_labels(path)
        res = evaluate(xyz, labels)
        print("=" * 70)
        print(f"File: {path}")
        print(f"  points={res['n_points']:,}  structural={res['n_structural']:,}  "
              f"noise(gt)={res['n_noise_truth']:,}  removed={res['n_removed']:,}")
        print(f"  noise precision={res['noise_precision']:.3f}  "
              f"recall={res['noise_recall']:.3f}  F1={res['noise_f1']:.3f}")
        print(f"  lining retention={res['lining_retention']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
