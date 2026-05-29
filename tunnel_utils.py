"""
SSL Smart Tunnel Monitoring System - Point cloud utility layer.

This module owns reusable, GUI-independent preprocessing operations:

- LAS/PLY point-cloud loading.
- XYZ validation and color normalization.
- Voxel downsampling for large Faro Focus scans.
- Statistical/radius noise removal.
- RANSAC plane segmentation helpers.

Keep this file free of Tkinter/PyQt/PyVista UI code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

try:
    import laspy
except ImportError:  # pragma: no cover - handled at runtime
    laspy = None

try:
    import open3d as o3d
except ImportError:  # pragma: no cover - handled at runtime
    o3d = None


@dataclass(frozen=True)
class PointCloudData:
    """Small transport object used between GUI, utilities, and viewers."""

    points: np.ndarray
    colors: Optional[np.ndarray] = None
    intensity: Optional[np.ndarray] = None
    source_path: Optional[str] = None


def require_open3d() -> None:
    if o3d is None:
        raise RuntimeError("Open3D is required. Install with: pip install open3d")


def require_laspy() -> None:
    if laspy is None:
        raise RuntimeError("laspy is required for LAS/LAZ files. Install with: pip install laspy")


def validate_xyz(points: np.ndarray, name: str = "points") -> np.ndarray:
    """Return a finite Nx3 float64 array."""

    arr = np.asarray(points, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"{name} must have shape (N, 3).")
    finite = np.isfinite(arr).all(axis=1)
    arr = arr[finite]
    if len(arr) == 0:
        raise ValueError(f"{name} contains no finite XYZ points.")
    return arr


def normalize_colors(colors: Optional[np.ndarray]) -> Optional[np.ndarray]:
    """Normalize RGB colors to Open3D/PyVista friendly range [0, 1]."""

    if colors is None:
        return None
    arr = np.asarray(colors, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3 or len(arr) == 0:
        return None
    cmin = float(np.nanmin(arr))
    cmax = float(np.nanmax(arr))
    if 0.0 <= cmin and cmax <= 1.0:
        return np.clip(arr, 0.0, 1.0)
    if 0.0 <= cmin and cmax <= 255.0:
        return np.clip(arr / 255.0, 0.0, 1.0)
    if 0.0 <= cmin and cmax <= 65535.0:
        return np.clip(arr / 65535.0, 0.0, 1.0)
    if np.isclose(cmin, cmax):
        return np.zeros_like(arr)
    return np.clip((arr - cmin) / (cmax - cmin), 0.0, 1.0)


def make_open3d_cloud(points: np.ndarray, colors: Optional[np.ndarray] = None) -> "o3d.geometry.PointCloud":
    """Build an Open3D point cloud from numpy arrays."""

    require_open3d()
    xyz = validate_xyz(points)
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(xyz)
    rgb = normalize_colors(colors)
    if rgb is not None and len(rgb) == len(xyz):
        cloud.colors = o3d.utility.Vector3dVector(rgb)
    return cloud


def load_point_cloud(path: str | Path) -> PointCloudData:
    """Load LAS/LAZ/PLY/PCD/XYZ-like point-cloud files into numpy arrays."""

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(str(source))

    suffix = source.suffix.lower()
    if suffix in {".las", ".laz"}:
        require_laspy()
        las = laspy.read(str(source))
        points = np.column_stack((las.x, las.y, las.z)).astype(np.float64)
        colors = None
        if all(hasattr(las, channel) for channel in ("red", "green", "blue")):
            colors = np.column_stack((las.red, las.green, las.blue)).astype(np.float64)
            colors = normalize_colors(colors)
        intensity = np.asarray(las.intensity, dtype=np.float64) if hasattr(las, "intensity") else None
        return PointCloudData(validate_xyz(points), colors, intensity, str(source))

    require_open3d()
    cloud = o3d.io.read_point_cloud(str(source))
    if not cloud.has_points():
        raise ValueError(f"Point cloud is empty: {source}")
    points = np.asarray(cloud.points, dtype=np.float64)
    colors = np.asarray(cloud.colors, dtype=np.float64) if cloud.has_colors() else None
    return PointCloudData(validate_xyz(points), normalize_colors(colors), None, str(source))


def voxel_downsample(
    points: np.ndarray,
    colors: Optional[np.ndarray] = None,
    voxel_size: float = 0.05,
    max_points: Optional[int] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Downsample a cloud for registration or interactive visualization."""

    if voxel_size <= 0:
        xyz = validate_xyz(points)
        rgb = normalize_colors(colors)
    else:
        cloud = make_open3d_cloud(points, colors)
        down = cloud.voxel_down_sample(float(voxel_size))
        xyz = np.asarray(down.points, dtype=np.float64)
        rgb = np.asarray(down.colors, dtype=np.float64) if down.has_colors() else None

    if max_points is not None and len(xyz) > max_points:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(xyz), int(max_points), replace=False)
        if rgb is not None and len(rgb) == len(xyz):
            rgb = rgb[idx]
        xyz = xyz[idx]
    return xyz, rgb


def statistical_outlier_removal(
    points: np.ndarray,
    colors: Optional[np.ndarray] = None,
    nb_neighbors: int = 30,
    std_ratio: float = 1.0,
) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
    """Remove isolated scan noise using Open3D statistical outlier removal."""

    cloud = make_open3d_cloud(points, colors)
    filtered, indices = cloud.remove_statistical_outlier(
        nb_neighbors=int(nb_neighbors),
        std_ratio=float(std_ratio),
    )
    kept = np.asarray(indices, dtype=np.int64)
    out_points = np.asarray(filtered.points, dtype=np.float64)
    out_colors = np.asarray(filtered.colors, dtype=np.float64) if filtered.has_colors() else None
    return out_points, out_colors, kept


def radius_outlier_removal(
    points: np.ndarray,
    colors: Optional[np.ndarray] = None,
    nb_points: int = 12,
    radius: float = 0.15,
) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
    """Remove points without enough neighbors inside a local radius."""

    cloud = make_open3d_cloud(points, colors)
    filtered, indices = cloud.remove_radius_outlier(
        nb_points=int(nb_points),
        radius=float(radius),
    )
    kept = np.asarray(indices, dtype=np.int64)
    out_points = np.asarray(filtered.points, dtype=np.float64)
    out_colors = np.asarray(filtered.colors, dtype=np.float64) if filtered.has_colors() else None
    return out_points, out_colors, kept


def ransac_plane_segmentation(
    points: np.ndarray,
    distance_threshold: float = 0.05,
    ransac_n: int = 3,
    num_iterations: int = 1000,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Segment one dominant plane.

    Returns:
        plane_model: [a, b, c, d] for ax + by + cz + d = 0.
        inlier_points: Points belonging to the plane.
        outlier_points: Remaining points.
    """

    cloud = make_open3d_cloud(points)
    plane_model, inliers = cloud.segment_plane(
        distance_threshold=float(distance_threshold),
        ransac_n=int(ransac_n),
        num_iterations=int(num_iterations),
    )
    inlier_cloud = cloud.select_by_index(inliers)
    outlier_cloud = cloud.select_by_index(inliers, invert=True)
    return (
        np.asarray(plane_model, dtype=np.float64),
        np.asarray(inlier_cloud.points, dtype=np.float64),
        np.asarray(outlier_cloud.points, dtype=np.float64),
    )


__all__ = [
    "PointCloudData",
    "load_point_cloud",
    "make_open3d_cloud",
    "normalize_colors",
    "radius_outlier_removal",
    "ransac_plane_segmentation",
    "statistical_outlier_removal",
    "validate_xyz",
    "voxel_downsample",
]
