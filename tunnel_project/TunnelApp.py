"""
Tunnel Analysis Tool v2.1 - PySide6/PyVista edition
CBNU Smart Structure Lab | Osong Tunnel Project 2026-2028
"""

import csv
import json
import os
import sys
from pathlib import Path

os.environ["VTK_TK_WIDGET_PATH"] = ""
os.environ["VTK_DISABLE_TK_WIDGET"] = "1"
os.environ.setdefault("QT_API", "pyside6")

import numpy as np

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

import matplotlib

matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

try:
    import pyvista as pv
    from pyvistaqt import QtInteractor

    pv.global_theme.background = "#1E1E1E"
    HAS_PYVISTA = True
except Exception:
    pv = None
    QtInteractor = None
    HAS_PYVISTA = False

try:
    import laspy

    HAS_LASPY = True
except Exception:
    laspy = None
    HAS_LASPY = False

try:
    import open3d as o3d

    HAS_OPEN3D = True
except Exception:
    o3d = None
    HAS_OPEN3D = False

try:
    from scipy.interpolate import splev, splprep
    from scipy.ndimage import uniform_filter1d
    from scipy.signal import find_peaks
    from scipy.spatial import cKDTree

    HAS_SCIPY = True
except Exception:
    HAS_SCIPY = False

try:
    import requests

    HAS_REQUESTS = True
except Exception:
    requests = None
    HAS_REQUESTS = False

try:
    import ifcopenshell

    HAS_IFC = True
except Exception:
    ifcopenshell = None
    HAS_IFC = False


APP_TITLE = "Tunnel Analysis Pro - CBNU Smart Structure Lab"
OLLAMA_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "llama3"

COLORS = {
    "bg": "#101418",
    "panel": "#171B21",
    "panel_alt": "#20262E",
    "panel_high": "#242B34",
    "plot_bg": "#12161B",
    "viewport_bg": "#1E1E1E",
    "viewport_top": "#0B0E12",
    "border": "#303842",
    "border_soft": "#242A32",
    "text": "#E7EDF4",
    "muted": "#95A1AF",
    "accent": "#0067C0",
    "accent_hover": "#1A85E8",
    "accent_2": "#00A86B",
    "warning": "#E5A13A",
    "danger": "#D64B4B",
}


def as_float(text, default=0.0):
    try:
        return float(text)
    except Exception:
        return default


def as_int(text, default=0):
    try:
        return int(float(text))
    except Exception:
        return default


def normalize_colors(colors):
    if colors is None:
        return None
    c = np.asarray(colors, dtype=np.float64)
    if c.size == 0:
        return None
    cmin, cmax = np.nanmin(c), np.nanmax(c)
    if 0.0 <= cmin and cmax <= 1.0:
        return c
    if 0.0 <= cmin and cmax <= 255.0:
        return c / 255.0
    if 0.0 <= cmin and cmax <= 65535.0:
        return c / 65535.0
    return (c - cmin) / max(cmax - cmin, 1e-9)


def sanitize_point_arrays(xyz, colors=None):
    xyz = np.asarray(xyz, dtype=np.float64)
    if xyz.ndim != 2 or xyz.shape[1] < 3:
        raise ValueError("Point cloud must be an Nx3 XYZ array")
    xyz = np.ascontiguousarray(xyz[:, :3], dtype=np.float64)
    finite = np.isfinite(xyz).all(axis=1)
    xyz = xyz[finite]

    safe_colors = None
    if colors is not None:
        c = normalize_colors(colors)
        if c is not None and len(c) == len(finite):
            safe_colors = c[finite]
        elif c is not None and len(c) == len(xyz):
            safe_colors = c

    if len(xyz) == 0:
        raise ValueError("Point cloud contains no finite XYZ points")
    return xyz, safe_colors


PLY_DTYPES = {
    "char": "i1",
    "int8": "i1",
    "uchar": "u1",
    "uint8": "u1",
    "short": "i2",
    "int16": "i2",
    "ushort": "u2",
    "uint16": "u2",
    "int": "i4",
    "int32": "i4",
    "uint": "u4",
    "uint32": "u4",
    "float": "f4",
    "float32": "f4",
    "double": "f8",
    "float64": "f8",
}


def read_ply_vertices_only(filepath):
    with open(filepath, "rb") as handle:
        if handle.readline().strip() != b"ply":
            raise ValueError("Not a PLY file")

        fmt, nverts, props, element = None, 0, [], None
        while True:
            raw = handle.readline()
            if not raw:
                raise ValueError("PLY header is incomplete")
            line = raw.decode("ascii", errors="replace").strip()
            if line == "end_header":
                break
            if not line or line.startswith("comment"):
                continue
            parts = line.split()
            if parts[0] == "format" and len(parts) >= 2:
                fmt = parts[1]
            elif parts[0] == "element" and len(parts) >= 3:
                element = parts[1]
                if element == "vertex":
                    nverts = int(parts[2])
            elif parts[0] == "property" and element == "vertex":
                if len(parts) >= 5 and parts[1] == "list":
                    raise ValueError("PLY vertex list properties are not supported")
                props.append((parts[2], parts[1]))

        names = [name.lower() for name, _ in props]
        xyz_idx = [names.index(axis) for axis in ("x", "y", "z")]
        color_idx = None
        for cname in (("red", "green", "blue"), ("r", "g", "b")):
            if all(name in names for name in cname):
                color_idx = [names.index(name) for name in cname]
                break

        if fmt == "ascii":
            xyz = np.empty((nverts, 3), dtype=np.float64)
            colors = np.empty((nverts, 3), dtype=np.float64) if color_idx is not None else None
            for row in range(nverts):
                values = handle.readline().decode("ascii", errors="replace").split()
                xyz[row] = [float(values[i]) for i in xyz_idx]
                if colors is not None:
                    colors[row] = [float(values[i]) for i in color_idx]
            return sanitize_point_arrays(xyz, colors)

        if fmt not in {"binary_little_endian", "binary_big_endian"}:
            raise ValueError(f"Unsupported PLY format: {fmt}")
        endian = "<" if fmt == "binary_little_endian" else ">"
        dtype = np.dtype([(f"{i}_{name}", endian + PLY_DTYPES[kind]) for i, (name, kind) in enumerate(props)])
        data = np.fromfile(handle, dtype=dtype, count=nverts)
        fields = data.dtype.names or ()
        xyz = np.column_stack([data[fields[i]] for i in xyz_idx]).astype(np.float64)
        colors = None
        if color_idx is not None:
            colors = np.column_stack([data[fields[i]] for i in color_idx]).astype(np.float64)
        return sanitize_point_arrays(xyz, colors)


def load_point_cloud(filepath):
    ext = Path(filepath).suffix.lower()
    if ext in {".las", ".laz"}:
        if not HAS_LASPY:
            raise RuntimeError("Install laspy: pip install laspy")
        las = laspy.read(filepath)
        xyz_raw = np.vstack(
            (
                np.asarray(las.x, dtype=np.float64),
                np.asarray(las.y, dtype=np.float64),
                np.asarray(las.z, dtype=np.float64),
            )
        ).transpose()
        finite_xyz = np.isfinite(xyz_raw).all(axis=1)
        colors = None
        if hasattr(las, "red") and hasattr(las, "green") and hasattr(las, "blue"):
            colors = np.vstack((las.red, las.green, las.blue)).transpose()
        intensity = None
        if hasattr(las, "intensity"):
            intensity = np.asarray(las.intensity, dtype=np.float64)
        xyz, colors = sanitize_point_arrays(xyz_raw, colors)
        if intensity is not None:
            if len(intensity) == len(finite_xyz):
                intensity = intensity[finite_xyz]
            if len(intensity) != len(xyz):
                intensity = intensity[: len(xyz)]
        return xyz, colors, intensity

    if ext == ".ply":
        xyz, colors = read_ply_vertices_only(filepath)
        return xyz, colors, None

    if ext in {".txt", ".csv", ".xyz"}:
        data = np.loadtxt(filepath, delimiter="," if ext == ".csv" else None, usecols=(0, 1, 2))
        xyz, colors = sanitize_point_arrays(data, None)
        return xyz, colors, None

    raise ValueError(f"Unsupported point-cloud format: {ext}")


def vertex_cells(num_points):
    """Return VTK vertex cells as [[1, point_id], ...] with no faces/lines."""
    return np.hstack(
        [
            np.ones((num_points, 1), dtype=np.int64),
            np.arange(num_points, dtype=np.int64).reshape(-1, 1),
        ]
    ).astype(np.int64)


def pure_point_polydata(xyz, colors=None, scalars=None, scalar_name="Intensity"):
    if not HAS_PYVISTA:
        raise RuntimeError("Install pyvista and pyvistaqt")
    xyz, colors = sanitize_point_arrays(xyz, colors)

    # Always create a brand-new PolyData from raw XYZ only. Never pass file-level
    # cells/faces into VTK; Blender-exported faces can trigger vtkGenericCell
    # "Unsupported cell type" warnings.
    cloud = pv.PolyData(xyz)

    # Strip all arrays and cells generated during construction before assigning
    # the final clean coordinates and vertex-only topology.
    if hasattr(cloud, "clear_data"):
        cloud.clear_data()
    if hasattr(cloud, "clear_cells"):
        cloud.clear_cells()
    cloud.points = xyz

    for attr in ("faces", "lines", "strips"):
        try:
            setattr(cloud, attr, np.empty(0, dtype=np.int64))
        except Exception:
            pass
    if hasattr(cloud, "clear_cells"):
        cloud.clear_cells()

    num_points = xyz.shape[0]
    cells = vertex_cells(num_points)
    try:
        cloud.verts = cells
    except Exception:
        cloud.verts = cells.ravel()
    if cloud.n_cells != num_points:
        cloud.verts = pv.CellArray(cells.ravel())

    if colors is not None and len(colors) == num_points:
        cloud["RGB"] = (np.clip(colors, 0.0, 1.0) * 255).astype(np.uint8)
    if scalars is not None:
        vals = np.asarray(scalars, dtype=np.float64).reshape(-1)
        if len(vals) == num_points:
            cloud[scalar_name] = vals
    return cloud


def sample_indices(n, max_count):
    if n <= max_count:
        return np.arange(n)
    return np.random.default_rng(42).choice(n, max_count, replace=False)


def denoise_knn(xyz, colors=None, nb=30, ratio=1.0):
    if not HAS_OPEN3D:
        return xyz, colors
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz.astype(np.float64))
    _, indices = pcd.remove_statistical_outlier(nb_neighbors=nb, std_ratio=ratio)
    indices = np.asarray(indices, dtype=np.int64)
    return xyz[indices], colors[indices] if colors is not None and len(colors) == len(xyz) else colors


def grid_downsample(xyz, colors=None, voxel=0.02):
    if not HAS_OPEN3D:
        return xyz, colors
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz.astype(np.float64))
    if colors is not None and len(colors) == len(xyz):
        pcd.colors = o3d.utility.Vector3dVector(np.clip(colors, 0, 1))
    down = pcd.voxel_down_sample(voxel)
    out_xyz = np.asarray(down.points)
    out_colors = np.asarray(down.colors) if down.has_colors() else None
    return out_xyz, out_colors


def filter_by_distance(xyz, colors=None, max_dist=30.0):
    mask = np.linalg.norm(xyz - np.median(xyz, axis=0), axis=1) <= max_dist
    return xyz[mask], colors[mask] if colors is not None and len(colors) == len(xyz) else colors


def custom_ransac_planes(xyz, iterations=500, threshold=0.05, min_points=1000):
    rng = np.random.default_rng(7)
    remaining = xyz.copy()
    planes = []
    for _ in range(3):
        if len(remaining) < min_points:
            break
        best_inliers, best_plane = None, None
        for _ in range(iterations):
            ids = rng.choice(len(remaining), 3, replace=False)
            p1, p2, p3 = remaining[ids]
            normal = np.cross(p2 - p1, p3 - p1)
            norm = np.linalg.norm(normal)
            if norm < 1e-9:
                continue
            normal = normal / norm
            d = -np.dot(normal, p1)
            dist = np.abs(remaining @ normal + d)
            inliers = np.where(dist < threshold)[0]
            if best_inliers is None or len(inliers) > len(best_inliers):
                best_inliers = inliers
                best_plane = np.r_[normal, d]
        if best_inliers is None or len(best_inliers) < min_points:
            break
        planes.append((best_plane, remaining[best_inliers]))
        mask = np.ones(len(remaining), dtype=bool)
        mask[best_inliers] = False
        remaining = remaining[mask]
    return planes


def open3d_ransac_planes(xyz, threshold=0.05, min_points=1000):
    if not HAS_OPEN3D:
        return custom_ransac_planes(xyz, threshold=threshold, min_points=min_points)
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz.astype(np.float64))
    planes = []
    remaining = pcd
    for _ in range(3):
        if len(remaining.points) < min_points:
            break
        plane, inliers = remaining.segment_plane(distance_threshold=threshold, ransac_n=3, num_iterations=1000)
        if len(inliers) < min_points:
            break
        part = remaining.select_by_index(inliers)
        planes.append((np.asarray(plane, dtype=np.float64), np.asarray(part.points)))
        remaining = remaining.select_by_index(inliers, invert=True)
    return planes


def hybrid_anchor_icp(target_xyz, source_xyz, max_dist=0.15, max_iter=80):
    target_xyz, _ = sanitize_point_arrays(target_xyz, None)
    source_xyz, _ = sanitize_point_arrays(source_xyz, None)
    target_anchor = np.median(target_xyz, axis=0)
    source_anchor = np.median(source_xyz, axis=0)
    initial = np.eye(4)
    initial[:3, 3] = target_anchor - source_anchor

    if not HAS_OPEN3D:
        if not HAS_SCIPY:
            return initial, float("nan"), source_xyz + initial[:3, 3]
        tree = cKDTree(target_xyz)
        aligned = source_xyz + initial[:3, 3]
        distances, _ = tree.query(aligned, k=1)
        return initial, float(np.sqrt(np.mean(distances**2))), aligned

    src = o3d.geometry.PointCloud()
    src.points = o3d.utility.Vector3dVector(source_xyz.astype(np.float64))
    tgt = o3d.geometry.PointCloud()
    tgt.points = o3d.utility.Vector3dVector(target_xyz.astype(np.float64))
    voxel = max(max_dist * 0.5, 0.02)
    src = src.voxel_down_sample(voxel)
    tgt = tgt.voxel_down_sample(voxel)
    radius = max(max_dist * 3.0, 0.2)
    src.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=30))
    tgt.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=30))
    result = o3d.pipelines.registration.registration_icp(
        src,
        tgt,
        max_dist,
        initial,
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=max_iter),
    )
    aligned = apply_transformation(source_xyz, result.transformation)
    return result.transformation, float(result.inlier_rmse), aligned


def apply_transformation(xyz, transform):
    xyz_h = np.c_[xyz, np.ones(len(xyz))]
    return (transform @ xyz_h.T).T[:, :3]


def extract_centerline_bspline(xyz, num_samples=80, smooth=0.5):
    y_min, y_max = np.percentile(xyz[:, 1], [1, 99])
    bins = np.linspace(y_min, y_max, max(num_samples // 2, 20))
    centers = []
    for y0, y1 in zip(bins[:-1], bins[1:]):
        sec = xyz[(xyz[:, 1] >= y0) & (xyz[:, 1] < y1)]
        if len(sec) < 30:
            continue
        centers.append(np.median(sec, axis=0))
    centers = np.asarray(centers, dtype=np.float64)
    if len(centers) < 4 or not HAS_SCIPY:
        idx = np.argsort(xyz[:, 1])
        centers = xyz[idx][:: max(1, len(xyz) // num_samples)]
        return centers

    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(centers, axis=0), axis=1))]
    if d[-1] < 1e-9:
        return centers
    u = d / d[-1]
    k = min(3, len(centers) - 1)
    tck, _ = splprep([centers[:, 0], centers[:, 1], centers[:, 2]], u=u, s=smooth, k=k)
    us = np.linspace(0, 1, num_samples)
    smoothed = np.vstack(splev(us, tck)).T
    return smoothed


def extract_frenet_sections(xyz, num_sections=50, thickness=0.35):
    centerline = extract_centerline_bspline(xyz, num_samples=max(num_sections, 20), smooth=0.4)
    sections = []
    if len(centerline) < 3:
        return sections, centerline

    tangents = np.gradient(centerline, axis=0)
    world_up = np.array([0.0, 0.0, 1.0])
    last_n = np.array([1.0, 0.0, 0.0])

    for i in range(1, len(centerline) - 1):
        center = centerline[i]
        t = tangents[i]
        t = t / (np.linalg.norm(t) + 1e-12)
        n = np.cross(world_up, t)
        if np.linalg.norm(n) < 1e-6:
            n = last_n
        n = n / (np.linalg.norm(n) + 1e-12)
        b = np.cross(t, n)
        b = b / (np.linalg.norm(b) + 1e-12)
        last_n = n

        rel = xyz - center
        along = rel @ t
        mask = np.abs(along) <= thickness
        if mask.sum() < 20:
            continue
        local = rel[mask]
        points_2d = np.c_[local @ n, local @ b]
        sections.append(
            {
                "index": len(sections),
                "center": center,
                "T": t,
                "N": n,
                "B": b,
                "points_2d": points_2d,
                "points_3d": xyz[mask],
            }
        )
    return sections, centerline


def compute_deformation_params(section_2d, design_radius=None):
    if section_2d is None or len(section_2d) < 10:
        return {}
    x = section_2d[:, 0]
    z = section_2d[:, 1]
    center = np.array([np.median(x), np.median(z)])
    centered = section_2d - center
    r = np.linalg.norm(centered, axis=1)
    radius_ref = float(design_radius) if design_radius else float(np.percentile(r, 90))
    crown_z = float(np.percentile(z, 99))
    design_crown = center[1] + radius_ref
    left = np.percentile(x, 2)
    right = np.percentile(x, 98)
    current_width = right - left
    design_width = radius_ref * 2.0
    delta_v = (crown_z - design_crown) * 1000.0
    delta_h = (current_width - design_width) * 1000.0
    e = float(np.linalg.norm(center) * 1000.0)
    r95, r05 = np.percentile(r, [95, 5])
    epsilon = (r95 - r05) / max(r95, 1e-9) * 100.0
    return {
        "delta_v_mm": delta_v,
        "delta_h_mm": delta_h,
        "crown_settlement_mm": delta_v,
        "convergence_mm": abs(delta_h),
        "e_mm": e,
        "epsilon_%": epsilon,
        "eccentricity_mm": e,
        "ellipticity_%": epsilon,
    }


def compute_heatmap(target_xyz, aligned_xyz):
    if not HAS_SCIPY:
        raise RuntimeError("Install scipy for KD-tree heatmap")
    tree = cKDTree(aligned_xyz)
    distances, _ = tree.query(target_xyz, k=1)
    return distances


def detect_ring_boundaries(xyz, intensity=None, bin_size=0.1, derivative_threshold=0.15):
    y = xyz[:, 1]
    signal = intensity if intensity is not None and len(intensity) == len(xyz) else xyz[:, 2]
    bins = np.arange(y.min(), y.max(), bin_size)
    if len(bins) < 3:
        return np.array([])
    values, centers = [], []
    ids = np.digitize(y, bins)
    for i in range(1, len(bins)):
        mask = ids == i
        if mask.sum() > 20:
            centers.append(bins[i - 1])
            values.append(np.mean(signal[mask]))
    centers, values = np.asarray(centers), np.asarray(values)
    if len(centers) < 3 or not HAS_SCIPY:
        return np.array([])
    grad = np.gradient(uniform_filter1d(values, size=3), centers)
    valleys, _ = find_peaks(-grad, height=derivative_threshold, distance=max(1, int(0.5 / bin_size)))
    return centers[valleys]


def ai_suggest_parameters(xyz):
    span = np.ptp(xyz, axis=0)
    density = len(xyz) / max(np.prod(np.maximum(span, 0.1)), 1e-9)
    return {
        "min_wall_height": max(0.5, min(4.0, span[2] * 0.18)),
        "ransac_distance": 0.03 if density > 5000 else 0.06,
        "ground_angle": 12.0,
        "wall_angle": 65.0,
        "unit": max(0.5, min(2.0, span[1] / 80.0)),
        "num_sections": 50,
    }


class Worker(QThread):
    status = Signal(str)
    progress = Signal(int)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.fn(self.status.emit, self.progress.emit, *self.args, **self.kwargs)
            self.done.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class PlotTab(QWidget):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("PlotTab")
        self.figure = Figure(figsize=(6, 4), dpi=100, facecolor=COLORS["panel"])
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.canvas)
        self.empty(title)

    def empty(self, title):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        style_plot_axes(ax)
        ax.text(0.5, 0.5, title, ha="center", va="center", color=COLORS["muted"], transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        self.figure.tight_layout()
        self.canvas.draw_idle()


def style_plot_axes(ax):
    """Apply the desktop dark theme to Matplotlib tabs."""
    ax.figure.set_facecolor(COLORS["panel"])
    ax.set_facecolor(COLORS["plot_bg"])
    ax.title.set_color(COLORS["text"])
    ax.xaxis.label.set_color(COLORS["muted"])
    ax.yaxis.label.set_color(COLORS["muted"])
    ax.tick_params(colors=COLORS["muted"])
    for spine in getattr(ax, "spines", {}).values():
        spine.set_color(COLORS["border"])
    if hasattr(ax, "zaxis"):
        ax.zaxis.label.set_color(COLORS["muted"])
        try:
            ax.xaxis.set_pane_color((0.07, 0.09, 0.11, 1.0))
            ax.yaxis.set_pane_color((0.07, 0.09, 0.11, 1.0))
            ax.zaxis.set_pane_color((0.07, 0.09, 0.11, 1.0))
            for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
                axis._axinfo["grid"]["color"] = "#2D3540"
                axis._axinfo["tick"]["color"] = COLORS["muted"]
        except Exception:
            pass


class TunnelApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1520, 940)

        self.file_path = None
        self.xyz = None
        self.colors = None
        self.intensity = None
        self.cloud_mesh = None
        self.ransac_planes = []
        self.centerline = None
        self.frenet_sections = []
        self.deformation_results = []
        self.timeseries = {"T0": None, "Tn": None, "Tn_aligned": None, "transform": None, "rmse": None}
        self.anchor_transform = None
        self.anchor_aligned = None
        self.current_section = 0
        self.workers = []

        self.inputs = {}
        self.mode_open3d = None
        self.mode_custom = None
        self.status_points = QLabel("Points: 0")
        self.status_rmse = QLabel("RMSE: N/A")
        self.status_state = QLabel("Status: Ready")
        self.metric_file = QLabel("No active scan")
        self.metric_points = QLabel("0 pts")
        self.metric_mode = QLabel("Idle")
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(220)

        self.apply_style()
        self.build_ui()
        self.update_status("Ready")

    def apply_style(self):
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{
                background: {COLORS['bg']};
                color: {COLORS['text']};
                font-family: "Segoe UI", "Roboto", Arial, sans-serif;
                font-size: 9pt;
            }}
            QFrame#Sidebar {{
                background: {COLORS['panel']};
                border-right: 1px solid {COLORS['border']};
            }}
            QLabel#AppTitle {{
                color: {COLORS['text']};
                font-size: 16pt;
                font-weight: 800;
                letter-spacing: 0px;
            }}
            QLabel#AppSubtitle {{
                color: {COLORS['muted']};
                font-size: 8.5pt;
            }}
            QLabel#MetricCard {{
                background: {COLORS['panel_alt']};
                border: 1px solid {COLORS['border_soft']};
                border-radius: 8px;
                padding: 8px 10px;
                color: {COLORS['text']};
                font-weight: 600;
            }}
            QSplitter::handle {{
                background: {COLORS['border_soft']};
                margin: 0px 1px;
            }}
            QSplitter::handle:hover {{
                background: {COLORS['accent']};
            }}
            QGroupBox {{
                background: {COLORS['panel']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 18px;
                padding: 10px;
                font-weight: 700;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: {COLORS['text']};
                background: {COLORS['panel']};
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['panel_high']}, stop:1 {COLORS['panel_alt']});
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 10px;
                color: {COLORS['text']};
                text-align: left;
            }}
            QPushButton:hover {{
                background: #2B3542;
                border-color: {COLORS['accent_hover']};
            }}
            QPushButton:pressed {{
                background: #1B222B;
                border-color: {COLORS['accent']};
            }}
            QPushButton#WorkflowButton, QPushButton#PrimaryButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['accent_hover']}, stop:1 {COLORS['accent']});
                border: 1px solid #2B92EF;
                color: white;
                font-weight: 700;
            }}
            QPushButton#WorkflowButton:hover, QPushButton#PrimaryButton:hover {{
                background: #0067C0;
                border-color: #5AB0FF;
            }}
            QPushButton#DangerButton {{
                background: {COLORS['danger']};
                color: white;
                border: 0;
                font-weight: 700;
            }}
            QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {{
                background: #0F1318;
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 6px;
                color: {COLORS['text']};
                selection-background-color: {COLORS['accent']};
            }}
            QRadioButton, QCheckBox {{
                color: {COLORS['muted']};
                padding: 3px;
            }}
            QTreeWidget {{
                background: #12171D;
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                outline: 0;
                padding: 6px;
                alternate-background-color: #151B22;
            }}
            QTreeWidget::item {{
                min-height: 30px;
                padding: 4px;
                border-radius: 6px;
                color: {COLORS['text']};
            }}
            QTreeWidget::item:selected {{
                background: #243041;
                color: {COLORS['text']};
            }}
            QTreeWidget::branch {{
                background: transparent;
            }}
            QHeaderView::section {{
                background: #11161C;
                color: {COLORS['muted']};
                border: 0;
                border-bottom: 1px solid {COLORS['border']};
                padding: 6px;
                font-weight: 700;
            }}
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                background: {COLORS['panel']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background: #141A21;
                color: {COLORS['muted']};
                padding: 9px 15px;
                border: 1px solid {COLORS['border']};
                border-bottom: 0;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {COLORS['panel_high']};
                color: {COLORS['text']};
                border-color: {COLORS['accent']};
            }}
            QTableWidget {{
                background: #11161C;
                alternate-background-color: #151B22;
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QProgressBar {{
                background: #0F1318;
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                height: 14px;
                text-align: center;
                color: {COLORS['muted']};
            }}
            QProgressBar::chunk {{
                background: {COLORS['accent']};
                border-radius: 6px;
            }}
            QStatusBar {{
                background: #0C1014;
                color: {COLORS['muted']};
                border-top: 1px solid {COLORS['border']};
            }}
            QToolBar {{
                background: #0C1014;
                border: 0;
                border-bottom: 1px solid {COLORS['border']};
                spacing: 8px;
                padding: 6px;
            }}
            QToolButton {{
                background: {COLORS['panel_alt']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text']};
                padding: 6px 10px;
            }}
            QToolButton:hover {{
                background: #2B3542;
                border-color: {COLORS['accent_hover']};
            }}
            """
        )

    def build_ui(self):
        central = QWidget()
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(central)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("MainSplitter")
        splitter.setHandleWidth(7)
        splitter.setChildrenCollapsible(False)
        root_layout.addWidget(splitter)

        self.sidebar = self.build_sidebar()
        splitter.addWidget(self.sidebar)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([380, 1140])

        self.build_tabs()
        self.build_statusbar()

        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        act_import = QAction("Import", self)
        act_import.triggered.connect(self.import_file)
        toolbar.addAction(act_import)
        act_preview = QAction("Preview 3D", self)
        act_preview.triggered.connect(self.preview_3d)
        toolbar.addAction(act_preview)

    def build_sidebar(self):
        frame = QFrame()
        frame.setObjectName("Sidebar")
        frame.setMinimumWidth(310)
        frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        title = QLabel("Tunnel Analysis Pro")
        title.setObjectName("AppTitle")
        outer.addWidget(title)
        subtitle = QLabel("CBNU Smart Structure Lab | Osong Tunnel")
        subtitle.setObjectName("AppSubtitle")
        outer.addWidget(subtitle)

        metric_row = QHBoxLayout()
        metric_row.setSpacing(8)
        for label in (self.metric_points, self.metric_mode):
            label.setObjectName("MetricCard")
            label.setMinimumHeight(38)
            label.setWordWrap(True)
            metric_row.addWidget(label)
        outer.addLayout(metric_row)
        self.metric_file.setObjectName("MetricCard")
        self.metric_file.setMinimumHeight(38)
        self.metric_file.setWordWrap(True)
        outer.addWidget(self.metric_file)

        workflow = self.create_workflow_tree()
        outer.addWidget(workflow, 1)

        params_group = self.group("Technical Parameters")
        params_grid = QGridLayout(params_group)
        params_grid.setHorizontalSpacing(10)
        params_grid.setVerticalSpacing(8)
        self.add_field(params_grid, 0, "Voxel (m)", "voxel_size", "0.02")
        self.add_field(params_grid, 1, "RANSAC Distance (m)", "ransac_distance", "0.05")
        self.add_field(params_grid, 2, "Ground Angle (deg)", "ground_angle", "12.0")
        self.add_field(params_grid, 3, "Wall Angle (deg)", "wall_angle", "65.0")
        self.add_field(params_grid, 4, "Min Wall Height (m)", "min_wall_height", "0.5")
        self.add_field(params_grid, 5, "Y start (m)", "y_start", "0.0")
        self.add_field(params_grid, 6, "Unit (m)", "unit", "1.0")
        self.add_field(params_grid, 7, "Num Sections", "num_sections", "50")
        self.mode_open3d = QRadioButton("Open3D RANSAC")
        self.mode_custom = QRadioButton("Custom RANSAC")
        self.mode_open3d.setChecked(True)
        params_grid.addWidget(self.mode_open3d, 8, 0)
        params_grid.addWidget(self.mode_custom, 8, 1)
        ai_btn = QPushButton("AI Suggest Parameters")
        ai_btn.setObjectName("PrimaryButton")
        ai_btn.clicked.connect(self.ai_suggest_parameters)
        params_grid.addWidget(ai_btn, 9, 0, 1, 2)
        outer.addWidget(params_group)
        return frame

    def create_workflow_tree(self):
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setColumnCount(1)
        tree.setRootIsDecorated(True)
        tree.setIndentation(18)
        tree.setUniformRowHeights(False)
        tree.setAnimated(True)
        tree.setAlternatingRowColors(True)
        tree.setSelectionMode(QAbstractItemView.SingleSelection)
        tree.setMinimumHeight(500)

        steps = [
            (
                "Step 1  Data Acquisition (Base)",
                [
                    ("Import LAS", self.action_import_faro_las_ply, True),
                    ("Init Viewport", self.action_initialize_3d_viewport, False),
                ],
            ),
            (
                "Step 2  Preprocessing (Pre)",
                [
                    ("Downsample", self.action_voxel_downsampling, False),
                    ("Noise Filter", self.action_statistical_outlier_removal, False),
                    ("Extract Lining", self.action_extract_tunnel_lining, False),
                ],
            ),
            (
                "Step 3  Registration (Geo)",
                [
                    ("Anchor (1 Target)", self.action_anchor_translation, False),
                    ("Run ICP", self.action_run_surface_icp, True),
                    ("RMSE Check", self.action_calculate_rmse, False),
                ],
            ),
            (
                "Step 4  Coordinate System (Geo)",
                [
                    ("Centerline", self.action_extract_centerline, False),
                    ("Smooth B-Spline", self.action_smooth_with_bspline, False),
                    ("Frenet Planes", self.action_generate_frenet_nb_planes, False),
                ],
            ),
            (
                "Step 5  Parameter Extraction (Geo)",
                [
                    ("Settlement", self.action_calculate_arch_settlement, False),
                    ("Convergence", self.action_calculate_horizontal_convergence, False),
                    ("Heatmap", self.action_generate_3d_heatmap, True),
                ],
            ),
            (
                "Step 6  Time-series Performance (Geo)",
                [
                    ("Compare T0-Tn", self.action_load_t0_tn, False),
                    ("Export Report", self.action_export_report, False),
                ],
            ),
            (
                "Step 7  Digital Twin (BIM/AI)",
                [
                    ("Export IFC", self.action_export_ifc_bim, False),
                    ("Local AI Chat", self.action_query_local_ai, False),
                ],
            ),
        ]

        for step_title, actions in steps:
            self.add_workflow_step(tree, step_title, actions)
        tree.expandAll()
        return tree

    def add_workflow_step(self, tree, title, actions):
        step_item = QTreeWidgetItem(tree, [title])
        step_item.setExpanded(True)
        step_item.setFlags(step_item.flags() & ~Qt.ItemIsSelectable)
        step_item.setSizeHint(0, QSize(260, 34))
        for text, slot, primary in actions:
            item = QTreeWidgetItem(step_item, [""])
            item.setSizeHint(0, QSize(260, 42))
            button = QPushButton(text)
            button.setCursor(Qt.PointingHandCursor)
            button.setObjectName("WorkflowButton" if primary else "")
            button.clicked.connect(slot)
            tree.setItemWidget(item, 0, button)

    def build_tabs(self):
        self.overview_tab = QWidget()
        overview_layout = QVBoxLayout(self.overview_tab)
        overview_layout.setContentsMargins(8, 8, 8, 8)
        if HAS_PYVISTA:
            self.plotter = QtInteractor(self.overview_tab)
            self.configure_plotter()
            overview_layout.addWidget(self.plotter)
        else:
            self.plotter = None
            msg = QLabel("PyVista / pyvistaqt is required. Install: pip install pyvista pyvistaqt vtk PySide6")
            msg.setAlignment(Qt.AlignCenter)
            overview_layout.addWidget(msg)
        self.tabs.addTab(self.overview_tab, "3D Viewport")

        self.plot_tabs = {}
        for name in ["RANSAC", "Centerline", "Section", "Rings", "Time-Series", "Frenet", "Heatmap", "Registration"]:
            tab = PlotTab(f"{name}\nRun analysis to view results")
            self.plot_tabs[name] = tab
            self.tabs.addTab(tab, name)

        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabs.addTab(self.results_table, "Results")

        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask the Local LLM about tunnel deformation, registration, BIM export...")
        send = QPushButton("Send")
        send.clicked.connect(self.send_chat)
        self.chat_input.returnPressed.connect(self.send_chat)
        row = QHBoxLayout()
        row.addWidget(self.chat_input)
        row.addWidget(send)
        ai_layout.addWidget(self.chat_display)
        ai_layout.addLayout(row)
        self.tabs.addTab(ai_tab, "AI Chat")

    def configure_plotter(self):
        if self.plotter is None:
            return
        try:
            pv.global_theme.background = COLORS["viewport_bg"]
            pv.global_theme.font.color = COLORS["text"]
            pv.global_theme.color = COLORS["text"]
        except Exception:
            pass
        self.apply_viewport_theme(reset=False)

    def apply_viewport_theme(self, reset=True):
        if self.plotter is None:
            return
        if reset:
            self.plotter.clear()
        try:
            self.plotter.set_background(COLORS["viewport_bg"], top=COLORS["viewport_top"])
        except Exception:
            self.plotter.set_background(COLORS["viewport_bg"])
        try:
            self.plotter.enable_eye_dome_lighting()
        except Exception:
            pass
        try:
            self.plotter.add_axes(
                line_width=2,
                labels_off=False,
                color=COLORS["text"],
                xlabel="X",
                ylabel="Y",
                zlabel="Z",
            )
        except Exception:
            pass

    def build_statusbar(self):
        bar = QStatusBar()
        self.setStatusBar(bar)
        bar.addWidget(self.status_points)
        bar.addWidget(self.status_rmse)
        bar.addWidget(self.status_state, 1)
        bar.addPermanentWidget(self.progress)

    def group(self, title):
        return QGroupBox(title)

    def add_button(self, layout, text, slot, object_name=None):
        btn = QPushButton(text)
        if object_name:
            btn.setObjectName(object_name)
        btn.clicked.connect(slot)
        layout.addWidget(btn)
        return btn

    def add_field(self, grid, row, label, key, value):
        grid.addWidget(QLabel(label), row, 0)
        edit = QLineEdit(value)
        self.inputs[key] = edit
        grid.addWidget(edit, row, 1)

    def update_status(self, state=None, rmse=None):
        points = len(self.xyz) if self.xyz is not None else 0
        self.status_points.setText(f"Points: {points:,}")
        if hasattr(self, "metric_points"):
            self.metric_points.setText(f"{points:,} pts")
        if hasattr(self, "metric_mode"):
            self.metric_mode.setText(state or "Ready")
        if hasattr(self, "metric_file"):
            filename = Path(self.file_path).name if self.file_path else "No active scan"
            self.metric_file.setText(filename)
        if rmse is not None:
            self.status_rmse.setText(f"RMSE: {rmse * 1000:.2f} mm")
        self.status_state.setText(f"Status: {state or 'Ready'}")

    def set_progress(self, value):
        self.progress.setValue(int(value))

    def log(self, message):
        self.chat_display.append(message)
        self.update_status(message)

    def params(self):
        return {
            "min_wall_height": as_float(self.inputs["min_wall_height"].text(), 0.5),
            "voxel_size": as_float(self.inputs["voxel_size"].text(), 0.02),
            "ransac_distance": as_float(self.inputs["ransac_distance"].text(), 0.05),
            "ground_angle": as_float(self.inputs["ground_angle"].text(), 12.0),
            "wall_angle": as_float(self.inputs["wall_angle"].text(), 65.0),
            "y_start": as_float(self.inputs["y_start"].text(), 0.0),
            "unit": as_float(self.inputs["unit"].text(), 1.0),
            "num_sections": max(3, as_int(self.inputs["num_sections"].text(), 50)),
        }

    def run_worker(self, fn, on_done, *args, **kwargs):
        worker = Worker(fn, *args, **kwargs)
        worker.status.connect(self.update_status)
        worker.progress.connect(self.set_progress)
        worker.failed.connect(self.on_worker_failed)
        worker.done.connect(on_done)
        worker.finished.connect(lambda: self.cleanup_worker(worker))
        self.workers.append(worker)
        worker.start()

    def cleanup_worker(self, worker):
        if worker in self.workers:
            self.workers.remove(worker)

    def on_worker_failed(self, message):
        self.set_progress(0)
        self.update_status(f"Error: {message}")
        QMessageBox.critical(self, "Tunnel Analysis Error", message)

    def require_xyz(self):
        if self.xyz is None:
            QMessageBox.warning(self, "Missing data", "Import FARO LAS/PLY first.")
            return False
        return True

    def require_timeseries(self):
        if self.timeseries["T0"] is None or self.timeseries["Tn"] is None:
            QMessageBox.information(self, "Missing time-series", "Load both T0 and Tn first.")
            return False
        return True

    def action_import_faro_las_ply(self):
        """1.1 Import FARO LAS/PLY: safe raw XYZ loader with vertices-only PolyData."""
        self.import_file()

    def action_initialize_3d_viewport(self):
        """1.2 Reset viewport and initialize a clean raw PolyData if data is loaded."""
        if self.plotter is not None:
            self.apply_viewport_theme(reset=True)
        if self.xyz is not None and HAS_PYVISTA:
            self.cloud_mesh = pure_point_polydata(self.xyz, self.colors, self.intensity)
            self.update_overview()
            self.update_status("3D viewport initialized from clean raw PolyData")
        else:
            self.update_status("3D viewport initialized")
        self.tabs.setCurrentWidget(self.overview_tab)

    def action_voxel_downsampling(self):
        """2.1 Voxel downsampling (Open3D voxel_down_sample)."""
        if not self.require_xyz():
            return
        voxel = self.params()["voxel_size"]

        def task(status, progress):
            status(f"Step 2.1: voxel downsampling at {voxel:.3f} m")
            progress(20)
            xyz, colors = grid_downsample(self.xyz, self.colors, voxel=voxel)
            progress(85)
            mesh = pure_point_polydata(xyz, colors, None) if HAS_PYVISTA else None
            progress(100)
            return xyz, colors, mesh

        self.run_worker(task, self.on_preprocess_done)

    def action_statistical_outlier_removal(self):
        """2.2 Statistical outlier removal (Open3D remove_statistical_outlier)."""
        if not self.require_xyz():
            return

        def task(status, progress):
            status("Step 2.2: statistical outlier removal")
            progress(20)
            xyz, colors = denoise_knn(self.xyz, self.colors, nb=30, ratio=1.0)
            progress(85)
            mesh = pure_point_polydata(xyz, colors, None) if HAS_PYVISTA else None
            progress(100)
            return xyz, colors, mesh

        self.run_worker(task, self.on_preprocess_done)

    def action_extract_tunnel_lining(self):
        """2.3 Tunnel lining extraction via RANSAC plane segmentation."""
        self.run_ransac()

    def action_anchor_translation(self):
        """3.1 Translate Tn by one target/anchor centroid before ICP."""
        if not self.require_timeseries():
            return
        target_anchor = np.median(self.timeseries["T0"], axis=0)
        source_anchor = np.median(self.timeseries["Tn"], axis=0)
        shift = target_anchor - source_anchor
        transform = np.eye(4)
        transform[:3, 3] = shift
        self.anchor_transform = transform
        self.anchor_aligned = self.timeseries["Tn"] + shift
        self.timeseries["Tn_aligned"] = self.anchor_aligned
        self.timeseries["transform"] = transform
        self.plot_registration_clouds("Anchor Translation", self.anchor_aligned, rmse=None)
        self.update_status(f"Anchor translation applied: dx={shift[0]:.4f}, dy={shift[1]:.4f}, dz={shift[2]:.4f}")

    def action_run_surface_icp(self):
        """3.2 Run surface ICP refinement. Replace this slot body with custom ICP if needed."""
        self.step3_registration()

    def action_calculate_rmse(self):
        """3.3 Calculate RMSE between T0 and aligned Tn."""
        if not self.require_timeseries():
            return
        aligned = self.timeseries.get("Tn_aligned")
        if aligned is None:
            aligned = self.anchor_aligned
        if aligned is None:
            QMessageBox.information(self, "Missing alignment", "Run Anchor Translation or Surface ICP first.")
            return
        if not HAS_SCIPY:
            QMessageBox.warning(self, "Missing scipy", "Install scipy to calculate KD-tree RMSE.")
            return
        tree = cKDTree(self.timeseries["T0"])
        distances, _ = tree.query(aligned, k=1)
        rmse = float(np.sqrt(np.mean(distances**2)))
        self.timeseries["rmse"] = rmse
        self.update_status("RMSE calculated", rmse=rmse)

    def action_extract_centerline(self):
        """4.1 Extract raw centerline control points."""
        if not self.require_xyz():
            return
        self.centerline = extract_centerline_bspline(self.xyz, num_samples=self.params()["num_sections"], smooth=0.0)
        self.plot_centerline()
        self.tabs.setCurrentWidget(self.plot_tabs["Centerline"])
        self.update_status("Centerline extracted")

    def action_smooth_with_bspline(self):
        """4.2 Smooth centerline with B-spline."""
        if not self.require_xyz():
            return
        self.centerline = extract_centerline_bspline(self.xyz, num_samples=self.params()["num_sections"], smooth=0.4)
        self.plot_centerline()
        self.tabs.setCurrentWidget(self.plot_tabs["Centerline"])
        self.update_status("Centerline smoothed with B-spline")

    def action_generate_frenet_nb_planes(self):
        """4.3 Generate Frenet N-B orthogonal section planes."""
        self.run_frenet()

    def action_calculate_arch_settlement(self):
        """5.1 Calculate arch settlement values. Algorithm hook lives in compute_deformation_params."""
        if not self.frenet_sections:
            QMessageBox.information(self, "Missing Frenet planes", "Run Step 4.3 first.")
            return
        self.deformation_results = [compute_deformation_params(sec["points_2d"]) for sec in self.frenet_sections]
        self.fill_results_table()
        mean_v = np.mean([r.get("delta_v_mm", 0.0) for r in self.deformation_results])
        self.update_status(f"Arch settlement calculated: mean {mean_v:.3f} mm")
        self.tabs.setCurrentWidget(self.results_table)

    def action_calculate_horizontal_convergence(self):
        """5.2 Calculate horizontal convergence values."""
        if not self.frenet_sections:
            QMessageBox.information(self, "Missing Frenet planes", "Run Step 4.3 first.")
            return
        self.deformation_results = [compute_deformation_params(sec["points_2d"]) for sec in self.frenet_sections]
        self.fill_results_table()
        mean_h = np.mean([r.get("delta_h_mm", 0.0) for r in self.deformation_results])
        self.update_status(f"Horizontal convergence calculated: mean {mean_h:.3f} mm")
        self.tabs.setCurrentWidget(self.results_table)

    def action_generate_3d_heatmap(self):
        """5.3 Generate 3D heatmap from T0 and aligned Tn."""
        if self.timeseries["T0"] is None or self.timeseries["Tn_aligned"] is None:
            QMessageBox.information(self, "Missing aligned scans", "Load T0/Tn and run Step 3.1 or 3.2 first.")
            return
        self.plot_heatmap()

    def action_load_t0_tn(self):
        """6.1 Load T0 and Tn scans independently through the safe XYZ loader."""
        self.load_timeseries_pair()

    def action_plot_deformation_chart(self):
        """6.2 Plot deformation chart."""
        self.step6_timeseries()

    def action_export_report(self):
        """6.2 Export engineering result table as CSV report."""
        if self.deformation_results:
            self.export_csv()
            return
        self.step6_timeseries()

    def action_export_ifc_bim(self):
        """7.1 Export IFC4 BIM (centerline + section psets), JSON fallback."""
        self.export_ifc()

    def action_query_local_ai(self):
        """7.2 Open Local AI chat panel."""
        self.open_ai_tab()

    def step1_data_acquisition(self):
        self.import_file()

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import point cloud", "", "Point Cloud (*.las *.laz *.ply *.txt *.csv *.xyz)")
        if not path:
            return
        self.file_path = path

        def task(status, progress):
            status("Step 1: reading raw XYZ and building clean PolyData")
            progress(15)
            xyz, colors, intensity = load_point_cloud(path)
            progress(70)
            mesh = pure_point_polydata(xyz, colors, intensity) if HAS_PYVISTA else None
            progress(100)
            return xyz, colors, intensity, mesh

        self.run_worker(task, self.on_import_done)

    def on_import_done(self, result):
        self.xyz, self.colors, self.intensity, self.cloud_mesh = result
        self.update_overview()
        self.plot_overview_matplotlib()
        self.update_status(f"Loaded {Path(self.file_path).name}")
        self.set_progress(100)

    def update_overview(self):
        if not self.plotter or self.cloud_mesh is None:
            return
        self.apply_viewport_theme(reset=True)
        scalar_bar_args = {
            "title": "Intensity / Deformation",
            "title_font_size": 12,
            "label_font_size": 10,
            "color": COLORS["text"],
            "shadow": False,
        }
        if "RGB" in self.cloud_mesh.array_names:
            self.plotter.add_mesh(
                self.cloud_mesh,
                scalars="RGB",
                rgb=True,
                style="points",
                point_size=2,
                render_points_as_spheres=False,
                reset_camera=True,
            )
        elif "Intensity" in self.cloud_mesh.array_names:
            self.plotter.add_mesh(
                self.cloud_mesh,
                scalars="Intensity",
                cmap="viridis",
                style="points",
                point_size=2,
                render_points_as_spheres=False,
                reset_camera=True,
                scalar_bar_args=scalar_bar_args,
            )
        else:
            self.plotter.add_mesh(
                self.cloud_mesh,
                style="points",
                color="#7EC8FF",
                point_size=2,
                render_points_as_spheres=False,
                reset_camera=True,
            )
        try:
            self.plotter.show_bounds(
                grid="front",
                location="outer",
                all_edges=False,
                color="#5B6B7D",
                font_size=8,
            )
            self.plotter.add_text(
                "Tunnel Lining Point Cloud",
                position="upper_left",
                font_size=10,
                color=COLORS["text"],
                name="viewport_title",
            )
        except Exception:
            pass
        self.plotter.reset_camera()
        self.plotter.render()
        self.tabs.setCurrentWidget(self.overview_tab)

    def plot_overview_matplotlib(self):
        if self.xyz is None:
            return
        tab = self.plot_tabs["Centerline"]
        tab.figure.clear()
        ax = tab.figure.add_subplot(111, projection="3d")
        style_plot_axes(ax)
        idx = sample_indices(len(self.xyz), 25000)
        c = self.colors[idx] if self.colors is not None and len(self.colors) == len(self.xyz) else self.xyz[idx, 2]
        ax.scatter(self.xyz[idx, 0], self.xyz[idx, 1], self.xyz[idx, 2], c=c, cmap="viridis", s=1, alpha=0.75)
        ax.set_title("Imported Point Cloud Overview")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
        ax.set_zlabel("Z (m)")
        tab.figure.tight_layout()
        tab.canvas.draw_idle()

    def preview_3d(self):
        self.update_overview()
        self.tabs.setCurrentWidget(self.overview_tab)

    def step2_preprocessing(self):
        self.remove_noise()

    def remove_noise(self):
        if self.xyz is None:
            QMessageBox.warning(self, "Missing data", "Import point cloud first.")
            return

        def task(status, progress):
            status("Step 2: statistical outlier removal")
            progress(20)
            xyz, colors = denoise_knn(self.xyz, self.colors, nb=30, ratio=1.0)
            progress(55)
            xyz, colors = filter_by_distance(xyz, colors, max_dist=30.0)
            progress(75)
            xyz, colors = grid_downsample(xyz, colors, voxel=0.02)
            progress(90)
            mesh = pure_point_polydata(xyz, colors, None) if HAS_PYVISTA else None
            progress(100)
            return xyz, colors, mesh

        self.run_worker(task, self.on_preprocess_done)

    def on_preprocess_done(self, result):
        self.xyz, self.colors, self.cloud_mesh = result
        self.update_overview()
        self.update_status("Preprocessing & QC complete")

    def run_ransac(self):
        if self.xyz is None:
            QMessageBox.warning(self, "Missing data", "Import point cloud first.")
            return
        params = self.params()

        def task(status, progress):
            status("Running RANSAC segmentation")
            progress(15)
            if self.mode_open3d.isChecked():
                planes = open3d_ransac_planes(self.xyz, threshold=params["ransac_distance"])
            else:
                planes = custom_ransac_planes(self.xyz, threshold=params["ransac_distance"])
            progress(100)
            return planes

        self.run_worker(task, self.on_ransac_done)

    def on_ransac_done(self, planes):
        self.ransac_planes = planes
        tab = self.plot_tabs["RANSAC"]
        tab.figure.clear()
        ax = tab.figure.add_subplot(111, projection="3d")
        style_plot_axes(ax)
        palette = ["#00A86B", "#D64B4B", "#2B92EF"]
        for i, (_, pts) in enumerate(planes):
            idx = sample_indices(len(pts), 8000)
            ax.scatter(pts[idx, 0], pts[idx, 1], pts[idx, 2], s=1, color=palette[i % len(palette)], label=f"Plane {i+1}")
        ax.set_title(f"RANSAC Segmentation ({len(planes)} planes)")
        ax.legend()
        tab.figure.tight_layout()
        tab.canvas.draw_idle()
        self.tabs.setCurrentWidget(tab)
        self.update_status(f"RANSAC complete: {len(planes)} planes")

    def step3_registration(self):
        if self.timeseries["T0"] is None or self.timeseries["Tn"] is None:
            QMessageBox.information(self, "Load time-series", "Use Time-Series > Load T0 and Load Tn first.")
            return

        def task(status, progress):
            status("Step 3: 1-target anchor translation + point-to-plane ICP")
            progress(15)
            transform, rmse, aligned = hybrid_anchor_icp(self.timeseries["T0"], self.timeseries["Tn"])
            progress(100)
            return transform, rmse, aligned

        self.run_worker(task, self.on_registration_done)

    def on_registration_done(self, result):
        transform, rmse, aligned = result
        self.timeseries["transform"] = transform
        self.timeseries["rmse"] = rmse
        self.timeseries["Tn_aligned"] = aligned
        self.plot_registration_clouds("Hybrid Registration", aligned, rmse=rmse)
        self.update_status("Registration complete", rmse=rmse)

    def plot_registration_clouds(self, title, aligned, rmse=None):
        if self.timeseries["T0"] is None or aligned is None:
            return
        tab = self.plot_tabs["Registration"]
        tab.figure.clear()
        ax = tab.figure.add_subplot(111, projection="3d")
        style_plot_axes(ax)
        t0 = self.timeseries["T0"]
        idx0 = sample_indices(len(t0), 10000)
        idx1 = sample_indices(len(aligned), 10000)
        ax.scatter(t0[idx0, 0], t0[idx0, 1], t0[idx0, 2], s=1, color=COLORS["accent"], alpha=0.55, label="T0 target")
        ax.scatter(aligned[idx1, 0], aligned[idx1, 1], aligned[idx1, 2], s=1, color=COLORS["accent_2"], alpha=0.55, label="Tn aligned")
        suffix = "" if rmse is None else f" - RMSE {rmse*1000:.2f} mm"
        ax.set_title(f"{title}{suffix}")
        ax.legend()
        tab.figure.tight_layout()
        tab.canvas.draw_idle()
        self.tabs.setCurrentWidget(tab)

    def step4_coordinate_system(self):
        self.run_frenet()

    def run_frenet(self):
        if self.xyz is None:
            QMessageBox.warning(self, "Missing data", "Import point cloud first.")
            return
        params = self.params()

        def task(status, progress):
            status("Step 4: B-spline centerline and Frenet-Serret frames")
            progress(20)
            sections, centerline = extract_frenet_sections(self.xyz, num_sections=params["num_sections"])
            progress(100)
            return sections, centerline

        self.run_worker(task, self.on_frenet_done)

    def on_frenet_done(self, result):
        self.frenet_sections, self.centerline = result
        self.plot_centerline()
        self.plot_frenet_section(0)
        self.update_status(f"Frenet-Serret ready: {len(self.frenet_sections)} sections")

    def plot_centerline(self):
        if self.centerline is None or self.xyz is None:
            return
        tab = self.plot_tabs["Centerline"]
        tab.figure.clear()
        ax = tab.figure.add_subplot(111, projection="3d")
        style_plot_axes(ax)
        idx = sample_indices(len(self.xyz), 15000)
        ax.scatter(self.xyz[idx, 0], self.xyz[idx, 1], self.xyz[idx, 2], s=1, color="#6F7D8C", alpha=0.35)
        ax.plot(self.centerline[:, 0], self.centerline[:, 1], self.centerline[:, 2], color=COLORS["danger"], linewidth=2.5)
        ax.set_title("B-spline Centerline")
        tab.figure.tight_layout()
        tab.canvas.draw_idle()

    def plot_frenet_section(self, index):
        if not self.frenet_sections:
            return
        index = max(0, min(index, len(self.frenet_sections) - 1))
        self.current_section = index
        section = self.frenet_sections[index]
        pts = section["points_2d"]
        for tab_name, title in (
            ("Section", "Orthogonal Tunnel Section"),
            ("Frenet", "Frenet N-B Section"),
        ):
            tab = self.plot_tabs[tab_name]
            tab.figure.clear()
            ax = tab.figure.add_subplot(111)
            style_plot_axes(ax)
            ax.scatter(pts[:, 0], pts[:, 1], s=2, color=COLORS["accent"], alpha=0.65)
            ax.axhline(0, color="#657386", linewidth=0.8)
            ax.axvline(0, color="#657386", linewidth=0.8)
            ax.set_aspect("equal")
            ax.set_title(f"{title} {index + 1}/{len(self.frenet_sections)}")
            ax.set_xlabel("N axis (m)")
            ax.set_ylabel("B axis (m)")
            tab.figure.tight_layout()
            tab.canvas.draw_idle()
        self.tabs.setCurrentWidget(self.plot_tabs["Frenet"])

    def step5_parameter_extraction(self):
        if not self.frenet_sections:
            QMessageBox.information(self, "Run Step 4", "Run Geometric Coordinate System first.")
            return
        self.deformation_results = [compute_deformation_params(sec["points_2d"]) for sec in self.frenet_sections]
        self.fill_results_table()
        self.update_status("Auto parameter extraction complete")
        self.tabs.setCurrentWidget(self.results_table)

    def fill_results_table(self):
        headers = ["Section", "delta_v_mm", "delta_h_mm", "e_mm", "epsilon_%", "crown_settlement_mm", "convergence_mm"]
        self.results_table.clear()
        self.results_table.setRowCount(len(self.deformation_results))
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        for row, result in enumerate(self.deformation_results):
            values = [row + 1] + [result.get(h, 0.0) for h in headers[1:]]
            for col, value in enumerate(values):
                if isinstance(value, float):
                    text = f"{value:.3f}"
                else:
                    text = str(value)
                self.results_table.setItem(row, col, QTableWidgetItem(text))

    def step6_timeseries(self):
        if self.timeseries["T0"] is not None and self.timeseries["Tn_aligned"] is not None:
            self.plot_heatmap()
            return
        if not self.deformation_results:
            QMessageBox.information(self, "Missing data", "Run Step 5 or complete T0/Tn registration first.")
            return
        tab = self.plot_tabs["Time-Series"]
        tab.figure.clear()
        ax = tab.figure.add_subplot(111)
        style_plot_axes(ax)
        x = np.arange(len(self.deformation_results))
        ax.plot(x, [r.get("delta_v_mm", 0) for r in self.deformation_results], color=COLORS["warning"], label="delta_v")
        ax.plot(x, [r.get("delta_h_mm", 0) for r in self.deformation_results], color=COLORS["accent_2"], label="delta_h")
        ax.set_title("Time-series / Section Performance")
        ax.set_xlabel("Station / Section")
        ax.set_ylabel("Deformation (mm)")
        ax.grid(True, alpha=0.25)
        ax.legend()
        tab.figure.tight_layout()
        tab.canvas.draw_idle()
        self.tabs.setCurrentWidget(tab)
        self.update_status("Time-series performance plot ready")

    def plot_heatmap(self):
        t0 = self.timeseries["T0"]
        aligned = self.timeseries["Tn_aligned"]
        idx = sample_indices(len(t0), 50000)
        distances = compute_heatmap(t0[idx], aligned)
        tab = self.plot_tabs["Heatmap"]
        tab.figure.clear()
        ax = tab.figure.add_subplot(111, projection="3d")
        style_plot_axes(ax)
        sc = ax.scatter(t0[idx, 0], t0[idx, 1], t0[idx, 2], c=distances * 1000, cmap="RdYlGn_r", s=1, vmin=0, vmax=10)
        tab.figure.colorbar(sc, ax=ax, label="Distance (mm)")
        ax.set_title(f"Heatmap - max {distances.max()*1000:.2f} mm")
        tab.figure.tight_layout()
        tab.canvas.draw_idle()
        self.tabs.setCurrentWidget(tab)
        self.render_heatmap_viewport(t0[idx], distances * 1000.0)

    def render_heatmap_viewport(self, xyz, deformation_mm):
        if not HAS_PYVISTA or self.plotter is None:
            return
        try:
            mesh = pure_point_polydata(xyz, scalars=deformation_mm, scalar_name="Deformation_mm")
        except Exception as exc:
            self.update_status(f"Heatmap viewport skipped: {exc}")
            return
        self.cloud_mesh = mesh
        self.apply_viewport_theme(reset=True)
        self.plotter.add_mesh(
            mesh,
            scalars="Deformation_mm",
            cmap="turbo",
            style="points",
            point_size=3,
            render_points_as_spheres=False,
            reset_camera=True,
            clim=[0, max(10.0, float(np.nanpercentile(deformation_mm, 98)))],
            scalar_bar_args={
                "title": "Deformation (mm)",
                "title_font_size": 13,
                "label_font_size": 10,
                "color": COLORS["text"],
            },
        )
        try:
            self.plotter.show_bounds(
                grid="front",
                location="outer",
                all_edges=False,
                color="#5B6B7D",
                font_size=8,
            )
            self.plotter.add_text(
                "3D Deformation Heatmap",
                position="upper_left",
                font_size=10,
                color=COLORS["text"],
                name="viewport_title",
            )
        except Exception:
            pass
        self.plotter.reset_camera()
        self.plotter.render()
        self.tabs.setCurrentWidget(self.overview_tab)

    def step7_digital_twin_ai(self):
        self.open_ai_tab()
        self.chat_display.append("Step 7 ready: IFC BIM export and Local LLM analysis.")

    def load_timeseries(self, key):
        path, _ = QFileDialog.getOpenFileName(self, f"Load {key}", "", "Point Cloud (*.las *.laz *.ply *.txt *.csv *.xyz)")
        if not path:
            return

        def task(status, progress):
            status(f"Loading {key} as clean vertices-only point cloud")
            progress(20)
            xyz, _, _ = load_point_cloud(path)
            progress(100)
            return xyz

        self.run_worker(task, lambda xyz: self.on_timeseries_loaded(key, xyz))

    def load_timeseries_pair(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Load T0 and Tn", "", "Point Cloud (*.las *.laz *.ply *.txt *.csv *.xyz)")
        if not paths:
            return
        if len(paths) < 2:
            QMessageBox.information(self, "Need two scans", "Select two files: first T0, second Tn.")
            return

        t0_path, tn_path = paths[0], paths[1]

        def task(status, progress):
            status("Step 6.1: loading T0 through safe XYZ loader")
            progress(20)
            t0, _, _ = load_point_cloud(t0_path)
            status("Step 6.1: loading Tn through safe XYZ loader")
            progress(60)
            tn, _, _ = load_point_cloud(tn_path)
            progress(100)
            return t0, tn

        self.run_worker(task, self.on_timeseries_pair_loaded)

    def on_timeseries_pair_loaded(self, result):
        t0, tn = result
        self.timeseries["T0"] = t0
        self.timeseries["Tn"] = tn
        self.timeseries["Tn_aligned"] = None
        self.timeseries["transform"] = None
        self.timeseries["rmse"] = None
        self.update_status(f"T0/Tn loaded: {len(t0):,} / {len(tn):,} points")

    def on_timeseries_loaded(self, key, xyz):
        self.timeseries[key] = xyz
        self.update_status(f"{key} loaded: {len(xyz):,} points")

    def detect_rings(self):
        if self.xyz is None:
            return
        rings = detect_ring_boundaries(self.xyz, self.intensity)
        tab = self.plot_tabs["Rings"]
        tab.figure.clear()
        ax = tab.figure.add_subplot(111)
        style_plot_axes(ax)
        ax.plot(rings, np.arange(len(rings)), "o-", color=COLORS["accent"])
        ax.set_title(f"Ring Seams ({len(rings)} detected)")
        ax.set_xlabel("Y / Chainage (m)")
        ax.set_ylabel("Ring index")
        tab.figure.tight_layout()
        tab.canvas.draw_idle()
        self.tabs.setCurrentWidget(tab)

    def ai_suggest_parameters(self):
        if self.xyz is None:
            QMessageBox.warning(self, "Missing data", "Import point cloud first.")
            return
        params = ai_suggest_parameters(self.xyz)
        self.inputs["min_wall_height"].setText(f"{params['min_wall_height']:.2f}")
        self.inputs["ransac_distance"].setText(f"{params['ransac_distance']:.3f}")
        self.inputs["ground_angle"].setText(f"{params['ground_angle']:.1f}")
        self.inputs["wall_angle"].setText(f"{params['wall_angle']:.1f}")
        self.inputs["unit"].setText(f"{params['unit']:.2f}")
        self.inputs["num_sections"].setText(str(params["num_sections"]))
        self.update_status("AI-suggested parameters applied")

    def export_csv(self):
        if not self.deformation_results:
            QMessageBox.warning(self, "No results", "Run Step 5 first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "tunnel_results.csv", "CSV (*.csv)")
        if not path:
            return
        headers = list(self.deformation_results[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Section"] + headers)
            for i, result in enumerate(self.deformation_results):
                writer.writerow([i + 1] + [result.get(h, "") for h in headers])
        self.update_status(f"CSV exported: {Path(path).name}")

    def export_ifc(self):
        default_name = "osong_tunnel.ifc" if HAS_IFC else "osong_tunnel.json"
        flt = "IFC (*.ifc)" if HAS_IFC else "JSON (*.json)"
        path, _ = QFileDialog.getSaveFileName(self, "Export IFC/BIM", default_name, flt)
        if not path:
            return
        if HAS_IFC:
            try:
                self._write_ifc(path)
            except Exception as exc:  # fall back to JSON so the user still gets data
                fallback = str(Path(path).with_suffix(".json"))
                self._write_bim_json(fallback)
                self.update_status(f"IFC export failed ({exc}); wrote JSON: {Path(fallback).name}")
                return
            self.update_status(f"IFC4 BIM export written: {Path(path).name}")
        else:
            self._write_bim_json(path)
            self.update_status(f"BIM JSON export written (install ifcopenshell for IFC4): {Path(path).name}")

    def _write_bim_json(self, path):
        payload = {
            "app": APP_TITLE,
            "source": self.file_path,
            "sections": len(self.frenet_sections),
            "deformation_results": self.deformation_results,
        }
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2))

    def _write_ifc(self, path):
        """Write a valid IFC4 model: project hierarchy, centerline polyline,
        and one proxy element per cross-section carrying deformation psets."""
        import ifcopenshell
        import ifcopenshell.api

        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        ifc = ifcopenshell.file(schema="IFC4")

        project = ifcopenshell.api.run("root.create_entity", ifc,
                                       ifc_class="IfcProject", name="Osong Tunnel")
        ifcopenshell.api.run("unit.assign_unit", ifc)
        ctx3d = ifcopenshell.api.run("context.add_context", ifc, context_type="Model")
        body_ctx = ifcopenshell.api.run("context.add_context", ifc,
                                        context_type="Model",
                                        context_identifier="Body",
                                        target_view="MODEL_VIEW", parent=ctx3d)

        site = ifcopenshell.api.run("root.create_entity", ifc,
                                    ifc_class="IfcSite", name="Osong Test Site")
        building = ifcopenshell.api.run("root.create_entity", ifc,
                                        ifc_class="IfcBuilding", name="Tunnel Structure")
        storey = ifcopenshell.api.run("root.create_entity", ifc,
                                      ifc_class="IfcBuildingStorey", name="Tunnel Level")
        ifcopenshell.api.run("aggregate.assign_object", ifc,
                             products=[site], relating_object=project)
        ifcopenshell.api.run("aggregate.assign_object", ifc,
                             products=[building], relating_object=site)
        ifcopenshell.api.run("aggregate.assign_object", ifc,
                             products=[storey], relating_object=building)

        cl = self.centerline
        if cl is not None and len(cl) >= 2:
            annotation = ifcopenshell.api.run("root.create_entity", ifc,
                                              ifc_class="IfcAnnotation",
                                              name="Tunnel Centerline")
            pts_3d = [ifc.createIfcCartesianPoint(
                (float(p[0]), float(p[1]), float(p[2]))) for p in np.asarray(cl)]
            polyline = ifc.createIfcPolyline(pts_3d)
            shape = ifc.createIfcShapeRepresentation(body_ctx, "Axis", "Curve3D", [polyline])
            annotation.Representation = ifc.createIfcProductDefinitionShape(None, None, [shape])
            ifcopenshell.api.run("spatial.assign_container", ifc,
                                 products=[annotation], relating_structure=storey)

        results = self.deformation_results or []
        for i, sec in enumerate(self.frenet_sections):
            center = sec.get("center")
            if center is None:
                continue
            elem = ifcopenshell.api.run("root.create_entity", ifc,
                                        ifc_class="IfcBuildingElementProxy",
                                        name=f"Section_{i + 1:03d}")
            chainage = float(np.asarray(center)[1])
            props = {"Index": int(i + 1), "Chainage_m": chainage}
            if i < len(results):
                res = results[i]
                for src_key, ifc_key in (
                    ("crown_settlement_mm", "CrownSettlement_mm"),
                    ("convergence_mm", "Convergence_mm"),
                    ("eccentricity_mm", "Eccentricity_mm"),
                    ("ellipticity_%", "Ellipticity_pct"),
                ):
                    val = res.get(src_key)
                    if isinstance(val, (int, float)) and np.isfinite(float(val)):
                        props[ifc_key] = float(val)
            pset = ifcopenshell.api.run("pset.add_pset", ifc,
                                        product=elem, name="TunnelSectionProperties")
            ifcopenshell.api.run("pset.edit_pset", ifc, pset=pset, properties=props)
            ifcopenshell.api.run("spatial.assign_container", ifc,
                                 products=[elem], relating_structure=storey)

        ifc.write(str(out))
        return str(out)

    def open_ai_tab(self):
        self.tabs.setCurrentIndex(self.tabs.indexOf(self.chat_display.parentWidget()))
        self.chat_display.append("AI Assistant ready.")

    def send_chat(self):
        question = self.chat_input.text().strip()
        if not question:
            return
        self.chat_input.clear()
        self.chat_display.append(f"You: {question}")
        if not HAS_REQUESTS:
            self.chat_display.append("AI: install requests and run Ollama locally to enable Local LLM chat.")
            return
        context = [
            f"File: {Path(self.file_path).name if self.file_path else 'none'}",
            f"Points: {len(self.xyz) if self.xyz is not None else 0}",
            f"Sections: {len(self.frenet_sections)}",
            f"RMSE: {self.timeseries.get('rmse')}",
        ]
        prompt = "\n".join(context) + f"\nQuestion: {question}"
        try:
            response = requests.post(OLLAMA_URL, json={"model": LOCAL_MODEL, "prompt": prompt, "stream": False}, timeout=20)
            response.raise_for_status()
            self.chat_display.append(f"AI: {response.json().get('response', '')}")
        except Exception as exc:
            self.chat_display.append(f"AI error: {exc}")

    def closeEvent(self, event):
        try:
            if self.plotter is not None:
                self.plotter.close()
        except Exception:
            pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    win = TunnelApp()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
