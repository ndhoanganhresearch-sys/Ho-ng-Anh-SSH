'Shared imports, constants, and utilities.'
import json
import math
import os
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

# ------------------------------------------------------------------------------
os.environ.setdefault("QT_API", "pyside6")
os.environ.setdefault("MPLBACKEND", "QtAgg")
os.environ["VTK_TK_WIDGET_PATH"] = ""
os.environ["VTK_DISABLE_TK_WIDGET"] = "1"

import numpy as np

# ------------------------------------------------------------------------------
try:
    import laspy
except ImportError:
    laspy = None

try:
    import open3d as o3d
except ImportError:
    o3d = None

try:
    from scipy.spatial import cKDTree
except ImportError:
    cKDTree = None

try:
    import small_gicp
except ImportError:
    small_gicp = None

try:
    import py4dgeo
except ImportError:
    py4dgeo = None

try:
    import pyvista as pv
    if hasattr(pv, "set_qt_api"):
        try:
            pv.set_qt_api("pyside6")
        except Exception:
            pass
except ImportError:
    pv = None

# Qt is required for the GUI, but the numeric analysis core (geometry,
# registration, timeseries, ...) is pure NumPy/SciPy and must stay importable
# headless for testing and batch processing. Defer the hard failure to the GUI
# entry point (see tunnel_analysis.main) instead of aborting on import.
QT_IMPORT_ERROR: Optional[str] = None
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from pyvistaqt import QtInteractor
except ImportError as _exc:
    QtCore = QtGui = QtWidgets = QtInteractor = None  # type: ignore[assignment]
    QT_IMPORT_ERROR = (
        "PySide6 / pyvistaqt required.\n"
        "pip install PySide6 pyvista pyvistaqt vtk laspy open3d scipy matplotlib"
    )

try:
    import matplotlib
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.figure import Figure
    if QtCore is not None:
        # Embed plots in the Qt GUI when the toolkit is available.
        matplotlib.use("QtAgg")
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    else:
        # Headless (tests, batch reporting): render off-screen with Agg.
        matplotlib.use("Agg")
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    _MPL_OK = True
except ImportError:
    plt = None  # type: ignore[assignment]
    mpatches = None  # type: ignore[assignment]
    FigureCanvas = None  # type: ignore[assignment]
    Figure = None  # type: ignore[assignment]
    _MPL_OK = False


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

TUNNEL_PROFILES = ["Circle", "Box", "Box 2-cell", "U-type"]

VL_BOX_W  = 3.0   
VL_BOX_H  = 4.5   
VL_CIR_R  = 4.0   

# Light theme palette
_BG   = "#FFFFFF"
_FG   = "#111827"
_GRID = "#E2E8F0"
_ACC1 = "#1D4ED8"
_ACC2 = "#047857"
_ACC3 = "#C2410C"
_RED  = "#DC2626"
_YEL  = "#D97706"
_GRN  = "#047857"
_DIM  = "#475569"   


# ------------------------------------------------------------------------------
# Module-level utilities
# ------------------------------------------------------------------------------

def _unit(v: np.ndarray, fallback: Optional[np.ndarray] = None) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n < 1e-10:
        if fallback is not None:
            return fallback
        raise ValueError(f"Cannot normalise near-zero vector: {v}")
    return v / n

def principal_axes(pts: np.ndarray):
    """Centroid and principal axes of a point set via PCA (shared T1 helper).

    Returns (centroid, axis, e1, e2) where axis/e1/e2 are unit eigenvectors of
    the covariance ordered by DESCENDING eigenvalue: axis is the dominant
    (longitudinal) direction, e1/e2 span the orthogonal cross-section plane.
    Centralises the np.linalg.eigh(np.cov(...)) pattern that was duplicated
    across geometry/preprocessing/segmentation/parameters/clearance so every
    module estimates the tunnel axis identically.
    """
    p = validate_xyz(pts)
    c = p.mean(axis=0)
    ev, vecs = np.linalg.eigh(np.cov((p - c).T))
    order = np.argsort(ev)[::-1]
    axis = vecs[:, order[0]]
    e1 = vecs[:, order[1]]
    e2 = vecs[:, order[2]]
    axis = axis / (np.linalg.norm(axis) + 1e-12)
    e1 = e1 / (np.linalg.norm(e1) + 1e-12)
    e2 = e2 / (np.linalg.norm(e2) + 1e-12)
    return c, axis, e1, e2

def fit_ellipse_fitzgibbon(x: np.ndarray, y: np.ndarray) -> Optional[Tuple[float, float, float, float, float]]:
    """Fit an ellipse by Fitzgibbon Direct Least-Squares (PDF section 3.2).

    Solves the constrained conic fit Ax^2 + Bxy + Cy^2 + Dx + Ey + F = 0 under
    the ellipticity constraint 4AC - B^2 = 1 using the numerically stable
    Halir & Flusser (1998) decomposition of Fitzgibbon's generalized eigenvalue
    problem. Returns geometric parameters (cx, cy, a_semi, b_semi, theta) with
    a_semi >= b_semi, or None if the points do not admit a valid ellipse.
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    y = np.asarray(y, dtype=np.float64).ravel()
    if len(x) < 5 or len(x) != len(y):
        return None

    # Center and scale for numerical conditioning; undo it after fitting.
    mx = float(np.mean(x)); my = float(np.mean(y))
    xs = x - mx; ys = y - my
    scale = float(np.sqrt(np.mean(xs * xs + ys * ys)))
    if scale < 1e-12:
        return None
    xs = xs / scale; ys = ys / scale

    D1 = np.column_stack((xs * xs, xs * ys, ys * ys))   # quadratic monomials
    D2 = np.column_stack((xs, ys, np.ones_like(xs)))    # linear monomials
    S1 = D1.T @ D1
    S2 = D1.T @ D2
    S3 = D2.T @ D2
    try:
        S3_inv = np.linalg.inv(S3)
    except np.linalg.LinAlgError:
        return None
    Tm = -S3_inv @ S2.T
    M0 = S1 + S2 @ Tm
    # Apply inverse of the constraint matrix C (rows reordered/scaled).
    M = np.vstack((M0[2] / 2.0, -M0[1], M0[0] / 2.0))
    try:
        _, evec = np.linalg.eig(M)
    except np.linalg.LinAlgError:
        return None
    cond = 4.0 * evec[0] * evec[2] - evec[1] ** 2
    valid = np.where(cond > 0)[0]
    if len(valid) == 0:
        return None
    a1 = np.real(evec[:, valid[0]])
    a2 = Tm @ a1
    A, B, C = a1
    D, E, F = a2

    # Convert algebraic coefficients to geometric parameters by translating the
    # conic to its center, then taking eigenvalues of the quadratic form.
    Q = np.array([[A, B / 2.0], [B / 2.0, C]], dtype=np.float64)
    try:
        center = np.linalg.solve(np.array([[2 * A, B], [B, 2 * C]]), np.array([-D, -E]))
    except np.linalg.LinAlgError:
        return None
    cxs, cys = float(center[0]), float(center[1])
    f_prime = A * cxs * cxs + B * cxs * cys + C * cys * cys + D * cxs + E * cys + F
    eigvals = np.linalg.eigvalsh(Q)
    if np.any(eigvals == 0) or f_prime == 0:
        return None
    axes_sq = -f_prime / eigvals
    if np.any(axes_sq <= 0):
        return None
    axes = np.sqrt(axes_sq)
    a_semi = float(np.max(axes)) * scale
    b_semi = float(np.min(axes)) * scale
    theta = 0.5 * float(np.arctan2(B, A - C))
    cx = cxs * scale + mx
    cy = cys * scale + my
    return (cx, cy, a_semi, b_semi, theta)

def validate_xyz(pts: np.ndarray, name: str = "points") -> np.ndarray:
    arr = np.asarray(pts, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"{name} must be Nx3, got {arr.shape}.")
    arr = arr[np.isfinite(arr).all(axis=1)]
    if len(arr) == 0:
        raise ValueError(f"{name}: no finite points.")
    return arr

def _normalize_rgb(colors: Optional[np.ndarray]) -> Optional[np.ndarray]:
    if colors is None: return None
    arr = np.asarray(colors, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3: return None
    cmax = float(np.nanmax(arr))
    if cmax > 255.0: return np.clip(arr / 65535.0, 0.0, 1.0).astype(np.float32)
    if cmax > 1.0: return np.clip(arr / 255.0, 0.0, 1.0).astype(np.float32)
    return np.clip(arr, 0.0, 1.0).astype(np.float32)

def make_vertex_cloud(
    pts: np.ndarray,
    intensity: Optional[np.ndarray] = None,
    colors_raw: Optional[np.ndarray] = None,
) -> "pv.PolyData":
    if pv is None: raise RuntimeError("PyVista not installed.")
    xyz = np.ascontiguousarray(validate_xyz(pts)[:, :3], dtype=np.float64)
    n = len(xyz)
    cloud = pv.PolyData()
    cloud.points = xyz
    verts = np.empty(n * 2, dtype=np.int64)
    verts[0::2] = 1
    verts[1::2] = np.arange(n, dtype=np.int64)
    cloud.verts = verts
    if intensity is not None:
        vals = np.asarray(intensity, dtype=np.float64).ravel()
        if len(vals) == n: cloud["Intensity"] = vals
    rgb = _normalize_rgb(colors_raw)
    if rgb is not None and len(rgb) == n:
        cloud["RGB"] = (rgb * 255).astype(np.uint8)
    return cloud


# ------------------------------------------------------------------------------
# Parameter presentation (shared by Results log, auto summary, and table)
# ------------------------------------------------------------------------------

# Caution/critical thresholds. Keyed by the canonical metric name; mean/max
# variants reuse the same band (per PDF proposal; mirrors exporter.THRESHOLDS).
PARAM_THRESHOLDS = {
    "crown_settlement_mm":    {"caution": 10.0, "critical": 25.0},
    "lateral_convergence_mm": {"caution": 15.0, "critical": 30.0},
    "ovality_pct":            {"caution": 0.5,  "critical": 1.0},
    "eccentricity_mm":        {"caution": 10.0, "critical": 25.0},
}

# Human-readable labels for the raw metric keys produced by ParameterLayer.
PARAM_LABELS = {
    "crown_settlement_mm":      "Crown settlement (mean)",
    "crown_settlement_max_mm":  "Crown settlement (max)",
    "crown_B_mean_m":           "Crown height (mean)",
    "total_height_mm":          "Total height",
    "lateral_convergence_mm":     "Lateral convergence (mean)",
    "lateral_convergence_max_mm": "Lateral convergence (max)",
    "width_Tn_m":                 "Section width",
    "width_Tn_mean_m":            "Section width (mean)",
    "ovality_mean_pct":         "Ovality (mean)",
    "ovality_max_pct":          "Ovality (max)",
    "eccentricity_mean_mm":     "Eccentricity (mean)",
    "eccentricity_max_mm":      "Eccentricity (max)",
    "eccentricity_min_mm":      "Eccentricity (min)",
    "polar_max_outward_mm":     "Polar deformation (outward)",
    "polar_max_inward_mm":      "Polar deformation (inward)",
    "n_sections":               "Sections analysed",
    "reference":                "Reference",
}

# Map a metric key to its threshold band, collapsing mean/max/min variants.
_PARAM_THRESHOLD_ALIAS = {
    "crown_settlement_mm": "crown_settlement_mm",
    "crown_settlement_max_mm": "crown_settlement_mm",
    "lateral_convergence_mm": "lateral_convergence_mm",
    "lateral_convergence_max_mm": "lateral_convergence_mm",
    "ovality_mean_pct": "ovality_pct",
    "ovality_max_pct": "ovality_pct",
    "eccentricity_mean_mm": "eccentricity_mm",
    "eccentricity_max_mm": "eccentricity_mm",
}

# References that are absolute geometry (single scan), not true T0 deformation.
_SINGLE_SCAN_REFS = {"single_scan_global", "single_scan_per_section"}


def classify_parameter(key, value):
    """Return "OK" / "CAUTION" / "CRITICAL" / "" for a metric against its band.

    Uses the absolute value so negative settlement/convergence is judged by
    magnitude. Returns "" when the key has no defined threshold or the value
    is not a finite number.
    """
    base = _PARAM_THRESHOLD_ALIAS.get(key)
    if base is None:
        return ""
    band = PARAM_THRESHOLDS.get(base)
    if band is None:
        return ""
    try:
        v = abs(float(value))
    except (TypeError, ValueError):
        return ""
    if not np.isfinite(v):
        return ""
    if v >= band["critical"]:
        return "CRITICAL"
    if v >= band["caution"]:
        return "CAUTION"
    return "OK"


def format_parameter(key, value):
    """Format a single extracted parameter for display.

    Returns (label, text, status):
      - label: human-readable name (falls back to the raw key),
      - text: value formatted by unit suffix (_mm/_pct/_m/_deg/n_*), strings
        kept verbatim, NaN shown as "n/a",
      - status: classify_parameter(...) result (may be empty).
    """
    label = PARAM_LABELS.get(key, key)
    status = classify_parameter(key, value)
    if isinstance(value, str):
        text = value
        if key == "reference" and value in _SINGLE_SCAN_REFS:
            text = value + " (absolute geometry, not T0 deformation)"
        return label, text, status
    try:
        v = float(value)
    except (TypeError, ValueError):
        return label, str(value), status
    if not np.isfinite(v):
        return label, "n/a", status
    if key.startswith("n_") or key.endswith("_count") or key == "n_sections":
        return label, f"{int(round(v))}", status
    if key.endswith("_mm"):
        return label, f"{v:.2f} mm", status
    if key.endswith("_pct"):
        return label, f"{v:.3f} %", status
    if key.endswith("_deg"):
        return label, f"{v:.2f}°", status
    if key.endswith("_m"):
        return label, f"{v:.3f} m", status
    return label, f"{v:.4f}", status

__all__ = [
    "json", "math", "os", "sys", "warnings",
    "dataclass", "field", "Path", "Callable", "Dict", "List", "Optional", "Tuple",
    "np", "laspy", "o3d", "cKDTree", "small_gicp", "py4dgeo", "pv", "QtCore", "QtGui", "QtWidgets", "QtInteractor",
    "QT_IMPORT_ERROR",
    "matplotlib", "plt", "mpatches", "FigureCanvas", "Figure", "_MPL_OK",
    "TUNNEL_PROFILES", "VL_BOX_W", "VL_BOX_H", "VL_CIR_R",
    "_BG", "_FG", "_GRID", "_ACC1", "_ACC2", "_ACC3", "_RED", "_YEL", "_GRN", "_DIM",
    "_unit", "principal_axes", "validate_xyz", "_normalize_rgb", "make_vertex_cloud", "fit_ellipse_fitzgibbon",
    "format_parameter", "classify_parameter", "PARAM_THRESHOLDS", "PARAM_LABELS",
]


