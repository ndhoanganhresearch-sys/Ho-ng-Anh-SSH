# -*- coding: utf-8 -*-
"""STSD benchmark adapter for evaluating tunnel denoising / lining extraction.

Source dataset: STSD - "A large-scale benchmark for semantic segmentation of
subway tunnel point cloud" (Cui et al., 2024, Tunnelling and Underground Space
Technology; repo lichking2017/STSD, https://github.com/lichking2017/STSD).

STSD is a *dataset*, distributed on request via a Google Form, not a code
library. This module is a thin, dependency-light adapter (laspy + NumPy/SciPy,
no torch/GPU) that lets the tool's own preprocessing methods be scored against
the dataset's per-point class labels. It treats the structural lining classes
as KEEP and every other class (cables, lights, signal devices, vehicles,
people, ...) as REMOVE, then reports noise precision/recall/F1 and lining
retention.

STSD annotates 12 categories; the exact integer ids depend on the release you
download. Set STRUCTURE_LABELS to the structural ids before scoring real data
(see the STSD README / Table 2 legend).
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from ..models import PipelineContext, PointCloudBundle

# STSD class ids treated as structural lining (KEEP). Placeholder values; adjust
# to the downloaded release's legend. Everything else counts as removable noise.
STRUCTURE_LABELS: set = {1, 2}

# Candidate per-point label field names found across LAS exports.
_LABEL_FIELDS = ("label", "class", "category", "Classification", "classification")


def load_stsd_las(path: str) -> Tuple[np.ndarray, np.ndarray]:
    """Load (xyz Nx3, labels N) from a labelled STSD LAS/LAZ file.

    Reads the per-point class from a named extra dimension or the standard
    ``classification`` field. Raises if no label channel is present.
    """
    try:
        import laspy
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("laspy required: pip install laspy") from exc

    las = laspy.read(path)
    xyz = np.vstack([las.x, las.y, las.z]).T.astype(np.float64)
    labels: Optional[np.ndarray] = None
    dim_names = set(las.point_format.dimension_names)
    for name in _LABEL_FIELDS:
        if name in dim_names:
            labels = np.asarray(las[name]).astype(np.int64)
            break
    if labels is None and hasattr(las, "classification"):
        labels = np.asarray(las.classification).astype(np.int64)
    if labels is None:
        raise RuntimeError(f"No per-point label field in {path} (tried {_LABEL_FIELDS}).")
    if len(labels) != len(xyz):
        raise RuntimeError("Label count does not match point count.")
    return xyz, labels


def _cleaned_points(result: object) -> np.ndarray:
    """Extract the cleaned XYZ array from a preprocessing method's return value.

    The tool's denoisers return either an ``ndarray`` (extract_tunnel_lining) or
    a tuple whose first element is the cleaned ``ndarray`` (auto_denoise,
    extract_lining_density_variation, statistical_outlier_removal_run, ...).
    """
    arr = result[0] if isinstance(result, tuple) else result
    return np.asarray(arr, dtype=np.float64)


def _keep_mask_from_clean(original: np.ndarray, clean: np.ndarray) -> np.ndarray:
    """Per-point boolean mask: True where an original point survived cleaning.

    Uses an exact nearest-neighbour match (distance ~ 0) because the denoisers
    subset points without moving them.
    """
    from scipy.spatial import cKDTree

    if len(clean) == 0:
        return np.zeros(len(original), dtype=bool)
    d, _ = cKDTree(clean).query(original, k=1, workers=-1)
    return d < 1e-9


def score_keep_mask(labels: np.ndarray, kept_pred: np.ndarray,
                    structure_labels: Optional[set] = None) -> Dict[str, float]:
    """Score a keep/remove prediction against STSD labels.

    Positive class = "noise removed". Returns precision/recall/F1 for noise
    detection plus structural-lining retention and raw counts.
    """
    structure_labels = structure_labels or STRUCTURE_LABELS
    keep_truth = np.isin(labels, list(structure_labels))   # True = structural
    removed_pred = ~kept_pred
    removed_truth = ~keep_truth

    tp = int(np.sum(removed_pred & removed_truth))   # noise correctly removed
    fp = int(np.sum(removed_pred & keep_truth))      # structural wrongly removed
    fn = int(np.sum(kept_pred & removed_truth))      # noise missed
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if precision and recall and np.isfinite(precision) and np.isfinite(recall)
          else float("nan"))
    n_struct = int(np.sum(keep_truth))
    retention = int(np.sum(kept_pred & keep_truth)) / n_struct if n_struct else float("nan")
    return {
        "n_points": int(len(labels)),
        "n_structural": n_struct,
        "n_noise_truth": int(np.sum(removed_truth)),
        "n_removed_pred": int(np.sum(removed_pred)),
        "noise_precision": precision,
        "noise_recall": recall,
        "noise_f1": f1,
        "lining_retention": retention,
    }


# Preprocessing methods that can be scored, keyed by short name.
def _default_methods() -> Dict[str, Callable]:
    from ..preprocessing import PreprocessingLayer
    layer = PreprocessingLayer()
    return {
        "auto_denoise": layer.auto_denoise,
        "density_lining": layer.extract_lining_density_variation,
        "sor": layer.statistical_outlier_removal_run,
        "tunnel_lining": layer.extract_tunnel_lining,
    }


def evaluate_methods(
    xyz: np.ndarray,
    labels: np.ndarray,
    methods: Optional[List[str]] = None,
    structure_labels: Optional[set] = None,
) -> Dict[str, Dict[str, float]]:
    """Run one or more preprocessing methods on a labelled cloud and score each.

    Returns ``{method_name: score_dict}``. A fresh PipelineContext is built per
    method so they are scored independently on the raw cloud.
    """
    available = _default_methods()
    names = methods or list(available.keys())
    out: Dict[str, Dict[str, float]] = {}
    for name in names:
        fn = available.get(name)
        if fn is None:
            out[name] = {"error": f"unknown method '{name}'"}
            continue
        ctx = PipelineContext()
        ctx.scans.append(PointCloudBundle(points=np.asarray(xyz, dtype=np.float64)))
        ctx.active_index = 0
        try:
            result = fn(ctx)
            clean = _cleaned_points(result)
            kept = _keep_mask_from_clean(xyz, clean)
            out[name] = score_keep_mask(labels, kept, structure_labels)
        except Exception as exc:  # keep scoring the other methods
            out[name] = {"error": str(exc)}
    return out
