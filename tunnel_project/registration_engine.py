"""
SSL Smart Tunnel Monitoring System - Registration and 4D Deformation Engine.

This module implements the Layer 4 registration core used by TunnelApp:

- Multi-station Faro Focus scan management.
- Intensity-based target detection.
- Sequential stitching: Station N -> Station N-1 -> Station 1 global origin.
- SVD rigid registration with RMSE reporting.
- Optional point-to-plane ICP refinement with Open3D.
- Temporal overlap deformation analysis for T0, T1, T2... point clouds.

The code is intentionally GUI-independent and optimized for a 32 GB RAM
workstation by using voxel downsampling and bounded display/analysis samples.
"""

from __future__ import annotations

import csv
import math
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

try:
    import laspy
except ImportError:  # pragma: no cover - handled at runtime
    laspy = None

try:
    import open3d as o3d
except ImportError:  # pragma: no cover - handled at runtime
    o3d = None

try:
    from scipy.spatial import cKDTree
except ImportError:  # pragma: no cover - handled at runtime
    cKDTree = None


StatusCallback = Optional[Callable[[str], None]]
ProgressCallback = Optional[Callable[[float], None]]


def _status(callback: StatusCallback, message: str) -> None:
    if callback is not None:
        try:
            callback(message)
        except Exception:
            pass


def _progress(callback: ProgressCallback, value: float) -> None:
    if callback is not None:
        try:
            callback(float(max(0.0, min(100.0, value))))
        except Exception:
            pass


def require_open3d() -> None:
    if o3d is None:
        raise RuntimeError("Open3D is required for point-cloud processing.")


def require_laspy() -> None:
    if laspy is None:
        raise RuntimeError("laspy is required to read LAS/LAZ files.")


def require_scipy() -> None:
    if cKDTree is None:
        raise RuntimeError("scipy is required for KD-tree distance queries.")


def validate_xyz(points: np.ndarray, name: str = "points") -> np.ndarray:
    arr = np.asarray(points, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"{name} must be an array with shape (N, 3).")
    if len(arr) == 0:
        raise ValueError(f"{name} is empty.")
    finite_mask = np.isfinite(arr).all(axis=1)
    if not finite_mask.all():
        arr = arr[finite_mask]
    if len(arr) == 0:
        raise ValueError(f"{name} contains no finite points.")
    return arr


def normalize_colors(colors: Optional[np.ndarray]) -> Optional[np.ndarray]:
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
    if math.isclose(cmax, cmin):
        return np.zeros_like(arr)
    return np.clip((arr - cmin) / (cmax - cmin), 0.0, 1.0)


def make_point_cloud(points: np.ndarray, colors: Optional[np.ndarray] = None) -> "o3d.geometry.PointCloud":
    require_open3d()
    xyz = validate_xyz(points)
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    safe_colors = normalize_colors(colors)
    if safe_colors is not None and len(safe_colors) == len(xyz):
        pcd.colors = o3d.utility.Vector3dVector(safe_colors)
    return pcd


def transform_points(points: np.ndarray, transform: np.ndarray) -> np.ndarray:
    xyz = validate_xyz(points)
    T = validate_transform(transform)
    homogeneous = np.ones((len(xyz), 4), dtype=np.float64)
    homogeneous[:, :3] = xyz
    return (T @ homogeneous.T).T[:, :3]


def validate_transform(transform: np.ndarray) -> np.ndarray:
    T = np.asarray(transform, dtype=np.float64)
    if T.shape != (4, 4):
        raise ValueError("Transformation matrix must have shape (4, 4).")
    if not np.all(np.isfinite(T)):
        raise ValueError("Transformation matrix contains non-finite values.")
    if not np.allclose(T[3], np.array([0.0, 0.0, 0.0, 1.0]), atol=1e-8):
        raise ValueError("Transformation bottom row must be [0, 0, 0, 1].")
    det = float(np.linalg.det(T[:3, :3]))
    if not np.isfinite(det) or abs(abs(det) - 1.0) > 0.05:
        raise ValueError(f"Invalid rotation determinant: {det:.6f}.")
    return T


def voxel_downsample_points(
    points: np.ndarray,
    voxel_size: float,
    colors: Optional[np.ndarray] = None,
    max_points: Optional[int] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Downsample by Open3D voxel grid, with optional random cap for visualization.
    """
    xyz = validate_xyz(points)
    if voxel_size <= 0:
        sampled = xyz.copy()
        sampled_colors = normalize_colors(colors)
    else:
        require_open3d()
        pcd = make_point_cloud(xyz, colors)
        down = pcd.voxel_down_sample(float(voxel_size))
        sampled = np.asarray(down.points)
        sampled_colors = np.asarray(down.colors) if down.has_colors() else None
    if max_points is not None and len(sampled) > max_points:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(sampled), int(max_points), replace=False)
        sampled = sampled[idx]
        if sampled_colors is not None and len(sampled_colors) >= int(max_points):
            sampled_colors = sampled_colors[idx]
    return sampled, sampled_colors


def statistical_outlier_filter(
    points: np.ndarray,
    nb_neighbors: int = 24,
    std_ratio: float = 2.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Open3D statistical outlier removal for tunnel environmental noise.

    Returns filtered points and kept indices into the input point array.
    """
    require_open3d()
    xyz = validate_xyz(points)
    if len(xyz) < max(10, nb_neighbors):
        return xyz.copy(), np.arange(len(xyz), dtype=int)
    pcd = make_point_cloud(xyz)
    _, indices = pcd.remove_statistical_outlier(
        nb_neighbors=int(nb_neighbors),
        std_ratio=float(std_ratio),
    )
    kept = np.asarray(indices, dtype=int)
    return xyz[kept], kept


def load_point_cloud_file(
    filepath: str,
    max_points: Optional[int] = None,
    status_cb: StatusCallback = None,
) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], Dict[str, object]]:
    """
    Load LAS/LAZ/PLY into numpy arrays.

    Returns (xyz, intensity, colors, metadata).
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Point-cloud file not found: {filepath}")
    ext = path.suffix.lower()
    _status(status_cb, f"Loading {path.name}...")

    if ext in {".las", ".laz"}:
        require_laspy()
        with laspy.open(str(path)) as handle:
            las = handle.read()
        xyz = np.vstack((las.x, las.y, las.z)).T.astype(np.float64)
        intensity = None
        if hasattr(las, "intensity"):
            intensity = np.asarray(las.intensity, dtype=np.float64)
        colors = None
        if all(hasattr(las, attr) for attr in ("red", "green", "blue")):
            colors = np.vstack((las.red, las.green, las.blue)).T.astype(np.float64)
            colors = normalize_colors(colors)
        metadata = {
            "filepath": str(path),
            "name": path.name,
            "format": ext,
            "point_count": int(len(xyz)),
            "bounds_min": xyz.min(axis=0).tolist() if len(xyz) else [0, 0, 0],
            "bounds_max": xyz.max(axis=0).tolist() if len(xyz) else [0, 0, 0],
            "has_intensity": intensity is not None,
            "has_colors": colors is not None,
        }
    elif ext == ".ply":
        require_open3d()
        pcd = o3d.io.read_point_cloud(str(path))
        if not pcd.has_points():
            raise ValueError(f"PLY file contains no points: {filepath}")
        xyz = np.asarray(pcd.points, dtype=np.float64)
        intensity = None
        colors = np.asarray(pcd.colors, dtype=np.float64) if pcd.has_colors() else None
        metadata = {
            "filepath": str(path),
            "name": path.name,
            "format": ext,
            "point_count": int(len(xyz)),
            "bounds_min": xyz.min(axis=0).tolist(),
            "bounds_max": xyz.max(axis=0).tolist(),
            "has_intensity": False,
            "has_colors": colors is not None,
        }
    else:
        raise ValueError(f"Unsupported point-cloud format: {ext}")

    xyz = validate_xyz(xyz, name=path.name)
    if max_points is not None and len(xyz) > max_points:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(xyz), int(max_points), replace=False)
        xyz = xyz[idx]
        if intensity is not None:
            intensity = intensity[idx]
        if colors is not None:
            colors = colors[idx]
        metadata["sampled_point_count"] = int(len(xyz))

    return xyz, intensity, colors, metadata


@dataclass
class Target:
    target_id: str
    centroid: np.ndarray
    point_count: int
    mean_intensity: float = 0.0
    radius_m: float = 0.0

    def as_dict(self) -> Dict[str, object]:
        return {
            "target_id": self.target_id,
            "x": float(self.centroid[0]),
            "y": float(self.centroid[1]),
            "z": float(self.centroid[2]),
            "point_count": int(self.point_count),
            "mean_intensity": float(self.mean_intensity),
            "radius_m": float(self.radius_m),
        }


@dataclass
class StationData:
    station_id: str
    filepath: str
    timestamp: str = "T0"
    points: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    intensity: Optional[np.ndarray] = None
    colors: Optional[np.ndarray] = None
    targets: List[Target] = field(default_factory=list)
    transform_global: np.ndarray = field(default_factory=lambda: np.eye(4, dtype=np.float64))
    metadata: Dict[str, object] = field(default_factory=dict)

    def global_points(self) -> np.ndarray:
        return transform_points(self.points, self.transform_global)


@dataclass
class RegistrationLink:
    source_station_id: str
    target_station_id: str
    common_target_count: int
    svd_transform: np.ndarray
    icp_transform: np.ndarray
    relative_transform: np.ndarray
    accumulated_transform: np.ndarray
    rmse_svd_m: float
    rmse_final_m: float
    fitness: float = 0.0
    method: str = "SVD+PointToPlaneICP"

    def as_dict(self) -> Dict[str, object]:
        return {
            "source_station_id": self.source_station_id,
            "target_station_id": self.target_station_id,
            "common_target_count": int(self.common_target_count),
            "rmse_svd_mm": float(self.rmse_svd_m * 1000.0),
            "rmse_final_mm": float(self.rmse_final_m * 1000.0),
            "fitness": float(self.fitness),
            "method": self.method,
        }


@dataclass
class DeformationResult:
    timestamp: str
    reference_timestamp: str
    current_station_id: str
    reference_station_id: str
    method: str
    points: np.ndarray
    delta_mm: np.ndarray
    signed_delta_mm: np.ndarray
    colors: np.ndarray
    statistics: Dict[str, float]
    chainage_bins: np.ndarray
    crown_settlement_mm: np.ndarray
    convergence_mm: np.ndarray

    def as_summary(self) -> Dict[str, object]:
        result = {
            "timestamp": self.timestamp,
            "reference_timestamp": self.reference_timestamp,
            "current_station_id": self.current_station_id,
            "reference_station_id": self.reference_station_id,
            "method": self.method,
        }
        result.update(self.statistics)
        return result


def compute_svd_transform(source_points: np.ndarray, target_points: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Kabsch/SVD rigid transform mapping source_points into target_points.
    """
    src = validate_xyz(source_points, "source target points")
    dst = validate_xyz(target_points, "target target points")
    if len(src) != len(dst):
        raise ValueError("Source and target correspondence counts must match.")
    if len(src) < 3:
        raise ValueError("At least 3 common targets are required for SVD registration.")

    src_centroid = src.mean(axis=0)
    dst_centroid = dst.mean(axis=0)
    src_centered = src - src_centroid
    dst_centered = dst - dst_centroid

    H = src_centered.T @ dst_centered
    try:
        U, _, Vt = np.linalg.svd(H)
    except np.linalg.LinAlgError as exc:
        raise RuntimeError(f"SVD failed during target registration: {exc}") from exc

    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1.0
        R = Vt.T @ U.T
    t = dst_centroid - R @ src_centroid

    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = R
    T[:3, 3] = t
    transformed = transform_points(src, T)
    rmse = float(np.sqrt(np.mean(np.sum((transformed - dst) ** 2, axis=1))))
    return T, rmse


def nearest_neighbor_rmse(
    source_points: np.ndarray,
    target_points: np.ndarray,
    max_distance: Optional[float] = None,
) -> float:
    require_scipy()
    src = validate_xyz(source_points, "source points")
    dst = validate_xyz(target_points, "target points")
    tree = cKDTree(dst)
    distances, _ = tree.query(src, k=1)
    if max_distance is not None:
        distances = distances[distances <= max_distance]
    if len(distances) == 0:
        return float("inf")
    return float(np.sqrt(np.mean(distances**2)))


def detect_intensity_targets(
    points: np.ndarray,
    intensity: Optional[np.ndarray],
    percentile: float = 99.3,
    min_cluster_points: int = 20,
    eps: float = 0.18,
    max_targets: int = 30,
    status_cb: StatusCallback = None,
) -> List[Target]:
    """
    Detect reflective targets from high-intensity points and DBSCAN clusters.
    """
    require_open3d()
    xyz = validate_xyz(points)
    if intensity is None:
        raise ValueError("Intensity channel is required for target detection.")
    inten = np.asarray(intensity, dtype=np.float64)
    if len(inten) != len(xyz):
        raise ValueError("Intensity array length does not match point count.")
    if len(xyz) < min_cluster_points:
        raise ValueError("Not enough points to detect targets.")

    finite = np.isfinite(inten)
    if not finite.any():
        raise ValueError("Intensity channel contains no finite values.")
    threshold = float(np.percentile(inten[finite], percentile))
    high_mask = finite & (inten >= threshold)
    if high_mask.sum() < min_cluster_points:
        threshold = float(np.percentile(inten[finite], max(90.0, percentile - 5.0)))
        high_mask = finite & (inten >= threshold)
    if high_mask.sum() < min_cluster_points:
        raise ValueError("No high-intensity target candidates were found.")

    candidates = xyz[high_mask]
    candidate_intensity = inten[high_mask]
    pcd = make_point_cloud(candidates)
    _status(status_cb, f"Clustering {len(candidates):,} high-intensity target points...")
    labels = np.asarray(
        pcd.cluster_dbscan(eps=float(eps), min_points=int(min_cluster_points), print_progress=False),
        dtype=int,
    )
    target_candidates: List[Tuple[np.ndarray, int, float, float]] = []
    for label in sorted(set(labels.tolist())):
        if label < 0:
            continue
        mask = labels == label
        cluster = candidates[mask]
        if len(cluster) < min_cluster_points:
            continue
        centroid = cluster.mean(axis=0)
        radius = float(np.max(np.linalg.norm(cluster - centroid, axis=1)))
        mean_intensity = float(candidate_intensity[mask].mean())
        target_candidates.append((centroid, int(len(cluster)), mean_intensity, radius))

    target_candidates.sort(key=lambda item: (-item[2], item[0][1], item[0][0]))
    target_candidates = target_candidates[: int(max_targets)]
    target_candidates.sort(key=lambda item: (item[0][1], item[0][0], item[0][2]))
    return [
        Target(
            target_id=f"T{index:03d}",
            centroid=centroid,
            point_count=point_count,
            mean_intensity=mean_intensity,
            radius_m=radius,
        )
        for index, (centroid, point_count, mean_intensity, radius) in enumerate(target_candidates, start=1)
    ]


def match_targets_by_id(source: Sequence[Target], target: Sequence[Target]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    source_map = {item.target_id: item for item in source}
    target_map = {item.target_id: item for item in target}
    common = sorted(set(source_map).intersection(target_map))
    if len(common) < 3:
        raise ValueError("At least 3 common target IDs are required.")
    src_pts = np.vstack([source_map[key].centroid for key in common])
    dst_pts = np.vstack([target_map[key].centroid for key in common])
    return src_pts, dst_pts, common


def match_targets_by_geometry(
    source: Sequence[Target],
    target: Sequence[Target],
    max_pairs: int = 12,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Automatic correspondence fallback.

    Targets are sorted along the dominant station axis and paired in order. This
    is reliable when common targets are placed sequentially along the tunnel.
    For critical work, operators should verify/edit target IDs before SVD.
    """
    if len(source) < 3 or len(target) < 3:
        raise ValueError("At least 3 targets per station are required.")
    count = min(len(source), len(target), int(max_pairs))
    src_sorted = sorted(source, key=lambda item: (item.centroid[1], item.centroid[0], item.centroid[2]))[:count]
    dst_sorted = sorted(target, key=lambda item: (item.centroid[1], item.centroid[0], item.centroid[2]))[:count]
    src_pts = np.vstack([item.centroid for item in src_sorted])
    dst_pts = np.vstack([item.centroid for item in dst_sorted])
    labels = [f"{src_sorted[i].target_id}->{dst_sorted[i].target_id}" for i in range(count)]
    return src_pts, dst_pts, labels


def point_to_plane_icp(
    source_points: np.ndarray,
    target_points: np.ndarray,
    initial_transform: Optional[np.ndarray] = None,
    voxel_size: float = 0.05,
    max_correspondence_distance: float = 0.30,
    max_iteration: int = 80,
    status_cb: StatusCallback = None,
) -> Tuple[np.ndarray, float, float]:
    """
    Refine source -> target transformation by point-to-plane ICP.
    """
    require_open3d()
    src = validate_xyz(source_points, "source cloud")
    dst = validate_xyz(target_points, "target cloud")
    init = np.eye(4, dtype=np.float64) if initial_transform is None else validate_transform(initial_transform)

    if len(src) < 50 or len(dst) < 50:
        rmse = nearest_neighbor_rmse(transform_points(src, init), dst)
        return init, rmse, 0.0

    _status(status_cb, "Preparing downsampled clouds for point-to-plane ICP...")
    source_pcd = make_point_cloud(src).voxel_down_sample(float(voxel_size))
    target_pcd = make_point_cloud(dst).voxel_down_sample(float(voxel_size))
    if len(source_pcd.points) < 30 or len(target_pcd.points) < 30:
        rmse = nearest_neighbor_rmse(transform_points(src, init), dst)
        return init, rmse, 0.0

    radius = max(float(voxel_size) * 3.0, 0.05)
    source_pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=30))
    target_pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=30))

    criteria = o3d.pipelines.registration.ICPConvergenceCriteria(
        relative_fitness=1e-7,
        relative_rmse=1e-7,
        max_iteration=int(max_iteration),
    )
    try:
        result = o3d.pipelines.registration.registration_icp(
            source_pcd,
            target_pcd,
            float(max_correspondence_distance),
            init,
            o3d.pipelines.registration.TransformationEstimationPointToPlane(),
            criteria,
        )
    except Exception as exc:
        _status(status_cb, f"ICP failed, using SVD transform only: {exc}")
        rmse = nearest_neighbor_rmse(transform_points(src, init), dst, max_distance=max_correspondence_distance)
        return init, rmse, 0.0

    T = np.asarray(result.transformation, dtype=np.float64)
    transformed = transform_points(src, T)
    rmse = nearest_neighbor_rmse(transformed, dst, max_distance=max_correspondence_distance)
    return T, rmse, float(result.fitness)


class StationManager:
    """
    Multi-station sequential registration manager.

    The manager stores every station in local coordinates and records a global
    accumulated transform that maps each station into Station 1 coordinates.
    """

    def __init__(
        self,
        voxel_size_registration: float = 0.05,
        voxel_size_visualization: float = 0.10,
        max_registration_points: int = 300_000,
        rmse_warning_m: float = 0.005,
    ) -> None:
        self.voxel_size_registration = float(voxel_size_registration)
        self.voxel_size_visualization = float(voxel_size_visualization)
        self.max_registration_points = int(max_registration_points)
        self.rmse_warning_m = float(rmse_warning_m)
        self.stations: List[StationData] = []
        self.registration_links: List[RegistrationLink] = []
        self.deformation_results: List[DeformationResult] = []
        self.lock = threading.RLock()

    def clear(self) -> None:
        with self.lock:
            self.stations.clear()
            self.registration_links.clear()
            self.deformation_results.clear()

    def add_station(
        self,
        filepath: str,
        station_id: Optional[str] = None,
        timestamp: str = "T0",
        max_points: Optional[int] = None,
        status_cb: StatusCallback = None,
    ) -> StationData:
        with self.lock:
            sid = station_id or f"S{len(self.stations) + 1:03d}"
        xyz, intensity, colors, metadata = load_point_cloud_file(filepath, max_points=max_points, status_cb=status_cb)
        station = StationData(
            station_id=sid,
            filepath=str(filepath),
            timestamp=timestamp,
            points=xyz,
            intensity=intensity,
            colors=colors,
            metadata=metadata,
        )
        with self.lock:
            if not self.stations:
                station.transform_global = np.eye(4, dtype=np.float64)
            self.stations.append(station)
        return station

    def load_stations(
        self,
        filepaths: Sequence[str],
        timestamp: str = "T0",
        max_points: Optional[int] = None,
        status_cb: StatusCallback = None,
        progress_cb: ProgressCallback = None,
    ) -> List[StationData]:
        loaded = []
        count = len(filepaths)
        if count == 0:
            raise ValueError("No station files selected.")
        for index, filepath in enumerate(filepaths, start=1):
            _status(status_cb, f"Loading station {index}/{count}: {Path(filepath).name}")
            loaded.append(
                self.add_station(
                    filepath=filepath,
                    station_id=f"S{len(self.stations) + 1:03d}",
                    timestamp=timestamp,
                    max_points=max_points,
                    status_cb=status_cb,
                )
            )
            _progress(progress_cb, index / count * 100.0)
        return loaded

    def detect_targets_for_station(
        self,
        station: StationData,
        percentile: float = 99.3,
        min_cluster_points: int = 20,
        eps: float = 0.18,
        max_targets: int = 30,
        status_cb: StatusCallback = None,
    ) -> List[Target]:
        targets = detect_intensity_targets(
            station.points,
            station.intensity,
            percentile=percentile,
            min_cluster_points=min_cluster_points,
            eps=eps,
            max_targets=max_targets,
            status_cb=status_cb,
        )
        with self.lock:
            station.targets = targets
        return targets

    def detect_targets_all(
        self,
        percentile: float = 99.3,
        min_cluster_points: int = 20,
        eps: float = 0.18,
        max_targets: int = 30,
        status_cb: StatusCallback = None,
        progress_cb: ProgressCallback = None,
    ) -> Dict[str, List[Target]]:
        with self.lock:
            stations = list(self.stations)
        if not stations:
            raise ValueError("No stations are loaded.")
        result: Dict[str, List[Target]] = {}
        for index, station in enumerate(stations, start=1):
            _status(status_cb, f"Detecting targets for {station.station_id}...")
            try:
                result[station.station_id] = self.detect_targets_for_station(
                    station,
                    percentile=percentile,
                    min_cluster_points=min_cluster_points,
                    eps=eps,
                    max_targets=max_targets,
                    status_cb=status_cb,
                )
            except Exception as exc:
                _status(status_cb, f"{station.station_id}: target detection failed: {exc}")
                result[station.station_id] = []
            _progress(progress_cb, index / len(stations) * 100.0)
        return result

    def import_targets_csv(self, station: StationData, csv_path: str) -> List[Target]:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Target CSV not found: {csv_path}")
        loaded_targets: List[Target] = []
        with open(path, "r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            required = {"target_id", "x", "y", "z"}
            if not required.issubset(set(reader.fieldnames or [])):
                raise ValueError("Target CSV must contain target_id,x,y,z columns.")
            for row in reader:
                try:
                    centroid = np.array([float(row["x"]), float(row["y"]), float(row["z"])], dtype=np.float64)
                    loaded_targets.append(
                        Target(
                            target_id=str(row["target_id"]),
                            centroid=centroid,
                            point_count=int(float(row.get("point_count", 0) or 0)),
                            mean_intensity=float(row.get("mean_intensity", 0.0) or 0.0),
                            radius_m=float(row.get("radius_m", 0.0) or 0.0),
                        )
                    )
                except Exception as exc:
                    raise ValueError(f"Invalid target row in {csv_path}: {row}") from exc
        if len(loaded_targets) < 3:
            raise ValueError("Target CSV must contain at least 3 targets.")
        with self.lock:
            station.targets = loaded_targets
        return loaded_targets

    def export_targets_csv(self, station: StationData, csv_path: str) -> str:
        if not station.targets:
            raise ValueError(f"{station.station_id} has no targets to export.")
        with open(csv_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["target_id", "x", "y", "z", "point_count", "mean_intensity", "radius_m"],
            )
            writer.writeheader()
            for target in station.targets:
                writer.writerow(target.as_dict())
        return csv_path

    def _registration_cloud_pair(self, current: StationData, previous: StationData) -> Tuple[np.ndarray, np.ndarray]:
        current_down, _ = voxel_downsample_points(
            current.points,
            self.voxel_size_registration,
            max_points=self.max_registration_points,
        )
        previous_down, _ = voxel_downsample_points(
            previous.points,
            self.voxel_size_registration,
            max_points=self.max_registration_points,
        )
        return current_down, previous_down

    def register_pair(
        self,
        current: StationData,
        previous: StationData,
        use_icp: bool = True,
        prefer_target_ids: bool = False,
        status_cb: StatusCallback = None,
    ) -> RegistrationLink:
        has_target_correspondences = len(current.targets) >= 3 and len(previous.targets) >= 3
        current_down: Optional[np.ndarray] = None
        previous_down: Optional[np.ndarray] = None

        if has_target_correspondences:
            _status(status_cb, f"SVD target registration: {current.station_id} -> {previous.station_id}")
            if prefer_target_ids:
                source_targets, target_targets, labels = match_targets_by_id(current.targets, previous.targets)
            else:
                try:
                    source_targets, target_targets, labels = match_targets_by_id(current.targets, previous.targets)
                except Exception:
                    source_targets, target_targets, labels = match_targets_by_geometry(current.targets, previous.targets)

            svd_transform, rmse_svd = compute_svd_transform(source_targets, target_targets)
            method = "SVD"
        elif use_icp:
            _status(
                status_cb,
                (
                    f"No common targets for {current.station_id} -> {previous.station_id}; "
                    "using ICP-only synchronization."
                ),
            )
            labels = []
            svd_transform = np.eye(4, dtype=np.float64)
            current_down, previous_down = self._registration_cloud_pair(current, previous)
            rmse_svd = nearest_neighbor_rmse(
                current_down,
                previous_down,
                max_distance=max(self.voxel_size_registration * 6.0, 0.20),
            )
            method = "PointToPlaneICP"
        else:
            raise ValueError(
                f"{current.station_id} and {previous.station_id} need at least 3 common targets, "
                "or ICP must be enabled for target-free registration."
            )

        relative_transform = svd_transform
        rmse_final = rmse_svd
        fitness = 0.0

        if use_icp:
            if current_down is None or previous_down is None:
                current_down, previous_down = self._registration_cloud_pair(current, previous)
            try:
                relative_transform, rmse_final, fitness = point_to_plane_icp(
                    current_down,
                    previous_down,
                    initial_transform=svd_transform,
                    voxel_size=self.voxel_size_registration,
                    max_correspondence_distance=max(self.voxel_size_registration * 6.0, 0.20),
                    status_cb=status_cb,
                )
                method = "SVD+PointToPlaneICP" if has_target_correspondences else "PointToPlaneICP"
            except Exception as exc:
                _status(status_cb, f"ICP refinement skipped: {exc}")
                method = "SVD" if has_target_correspondences else "IdentityFallback"

        with self.lock:
            accumulated = previous.transform_global @ relative_transform
            current.transform_global = accumulated
        link = RegistrationLink(
            source_station_id=current.station_id,
            target_station_id=previous.station_id,
            common_target_count=len(labels),
            svd_transform=svd_transform,
            icp_transform=relative_transform,
            relative_transform=relative_transform,
            accumulated_transform=accumulated,
            rmse_svd_m=float(rmse_svd),
            rmse_final_m=float(rmse_final),
            fitness=float(fitness),
            method=method,
        )
        return link

    def register_sequential(
        self,
        use_icp: bool = True,
        prefer_target_ids: bool = False,
        status_cb: StatusCallback = None,
        progress_cb: ProgressCallback = None,
    ) -> List[RegistrationLink]:
        with self.lock:
            stations = list(self.stations)
        if len(stations) < 2:
            raise ValueError("At least two stations are required for sequential registration.")

        with self.lock:
            stations[0].transform_global = np.eye(4, dtype=np.float64)
        links: List[RegistrationLink] = []
        total_links = len(stations) - 1
        for index in range(1, len(stations)):
            previous = stations[index - 1]
            current = stations[index]
            link = self.register_pair(
                current=current,
                previous=previous,
                use_icp=use_icp,
                prefer_target_ids=prefer_target_ids,
                status_cb=status_cb,
            )
            links.append(link)
            rmse_mm = link.rmse_final_m * 1000.0
            if link.rmse_final_m > self.rmse_warning_m:
                limit_mm = self.rmse_warning_m * 1000.0
                _status(status_cb, f"Warning: {current.station_id} RMSE {rmse_mm:.2f} mm exceeds {limit_mm:.1f} mm target.")
            else:
                _status(status_cb, f"{current.station_id} registered. RMSE {rmse_mm:.2f} mm.")
            _progress(progress_cb, index / total_links * 100.0)

        with self.lock:
            self.registration_links = links
        return links

    def get_station(self, station_id: str) -> StationData:
        with self.lock:
            for station in self.stations:
                if station.station_id == station_id:
                    return station
        raise KeyError(f"Station not found: {station_id}")

    def merged_global_cloud(
        self,
        voxel_size: Optional[float] = None,
        max_points: Optional[int] = None,
        station_ids: Optional[Iterable[str]] = None,
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        with self.lock:
            stations = list(self.stations)
        selected = set(station_ids) if station_ids is not None else None
        point_blocks: List[np.ndarray] = []
        color_blocks: List[np.ndarray] = []
        has_all_colors = True
        for station in stations:
            if selected is not None and station.station_id not in selected:
                continue
            global_points = station.global_points()
            point_blocks.append(global_points)
            if station.colors is not None and len(station.colors) == len(station.points):
                color_blocks.append(normalize_colors(station.colors))
            else:
                has_all_colors = False
        if not point_blocks:
            raise ValueError("No station points are available.")
        merged = np.vstack(point_blocks)
        colors = np.vstack(color_blocks) if has_all_colors and color_blocks else None
        return voxel_downsample_points(
            merged,
            self.voxel_size_visualization if voxel_size is None else voxel_size,
            colors=colors,
            max_points=max_points,
        )

    def stations_by_timestamp(self) -> Dict[str, List[StationData]]:
        grouped: Dict[str, List[StationData]] = {}
        with self.lock:
            for station in self.stations:
                grouped.setdefault(station.timestamp, []).append(station)
        return grouped

    def _timestamp_cloud(self, timestamp: str, voxel_size: float, max_points: Optional[int]) -> Tuple[np.ndarray, List[StationData]]:
        stations = self.stations_by_timestamp().get(timestamp, [])
        if not stations:
            raise ValueError(f"No stations found for timestamp {timestamp}.")
        point_blocks = [station.global_points() for station in stations]
        merged = np.vstack(point_blocks)
        down, _ = voxel_downsample_points(merged, voxel_size, max_points=max_points)
        return down, stations

    def compute_temporal_overlap(
        self,
        reference_timestamp: str = "T0",
        current_timestamp: Optional[str] = None,
        method: str = "c2c",
        voxel_size: float = 0.05,
        max_points: int = 500_000,
        warning_mm: float = 3.0,
        status_cb: StatusCallback = None,
        progress_cb: ProgressCallback = None,
    ) -> List[DeformationResult]:
        """
        Compute temporal deformation against a reference timestamp.

        method:
            c2c: unsigned cloud-to-cloud nearest-neighbor distance.
            normal: signed distance along reference local PCA normal.
        """
        require_scipy()
        grouped = self.stations_by_timestamp()
        if reference_timestamp not in grouped:
            raise ValueError(f"Reference timestamp not found: {reference_timestamp}.")
        timestamps = [current_timestamp] if current_timestamp else [ts for ts in sorted(grouped) if ts != reference_timestamp]
        if not timestamps:
            raise ValueError("No current timestamp is available for temporal comparison.")

        _status(status_cb, f"Preparing reference cloud {reference_timestamp}...")
        reference_cloud, reference_stations = self._timestamp_cloud(reference_timestamp, voxel_size, max_points)
        reference_tree = cKDTree(reference_cloud)
        results: List[DeformationResult] = []

        for index, ts in enumerate(timestamps, start=1):
            _status(status_cb, f"Computing temporal overlap: {ts} vs {reference_timestamp}")
            current_cloud, current_stations = self._timestamp_cloud(ts, voxel_size, max_points)
            distances_m, nearest_idx = reference_tree.query(current_cloud, k=1)
            signed_mm = distances_m * 1000.0
            used_method = method.lower()

            if used_method in {"normal", "m3c2", "normal-based"}:
                signed_mm = self._signed_normal_distances(current_cloud, reference_cloud, nearest_idx) * 1000.0
                delta_mm = np.abs(signed_mm)
                used_method = "normal"
            else:
                delta_mm = distances_m * 1000.0
                used_method = "c2c"

            colors = self._deformation_colors(delta_mm, warning_mm=warning_mm)
            bins, crown, convergence = self._compute_time_series_metrics(current_cloud, signed_mm)
            stats = self._deformation_statistics(delta_mm, signed_mm, warning_mm)

            result = DeformationResult(
                timestamp=ts,
                reference_timestamp=reference_timestamp,
                current_station_id="+".join(station.station_id for station in current_stations),
                reference_station_id="+".join(station.station_id for station in reference_stations),
                method=used_method,
                points=current_cloud,
                delta_mm=delta_mm,
                signed_delta_mm=signed_mm,
                colors=colors,
                statistics=stats,
                chainage_bins=bins,
                crown_settlement_mm=crown,
                convergence_mm=convergence,
            )
            results.append(result)
            _progress(progress_cb, index / len(timestamps) * 100.0)

        with self.lock:
            self.deformation_results = results
        return results

    def _signed_normal_distances(
        self,
        current_cloud: np.ndarray,
        reference_cloud: np.ndarray,
        nearest_idx: np.ndarray,
        neighborhood: int = 20,
    ) -> np.ndarray:
        require_scipy()
        ref = validate_xyz(reference_cloud, "reference cloud")
        cur = validate_xyz(current_cloud, "current cloud")
        tree = cKDTree(ref)
        signed = np.zeros(len(cur), dtype=np.float64)
        for i, point in enumerate(cur):
            ref_point = ref[int(nearest_idx[i])]
            _, idx = tree.query(ref_point, k=min(neighborhood, len(ref)))
            local = ref[np.atleast_1d(idx)]
            if len(local) < 3:
                normal = point - ref_point
                norm = np.linalg.norm(normal)
                normal = normal / norm if norm > 1e-12 else np.array([0.0, 0.0, 1.0])
            else:
                centered = local - local.mean(axis=0)
                try:
                    _, _, vh = np.linalg.svd(centered, full_matrices=False)
                    normal = vh[-1]
                except np.linalg.LinAlgError:
                    normal = np.array([0.0, 0.0, 1.0])
            signed[i] = float(np.dot(point - ref_point, normal))
        return signed

    def _deformation_colors(self, delta_mm: np.ndarray, warning_mm: float = 3.0) -> np.ndarray:
        values = np.asarray(delta_mm, dtype=np.float64)
        colors = np.zeros((len(values), 3), dtype=np.float64)
        caution = max(1.0, warning_mm / 3.0)
        green = values < caution
        yellow = (values >= caution) & (values < warning_mm)
        red = values >= warning_mm
        colors[green] = np.array([0.0, 0.75, 0.20])
        colors[yellow] = np.array([1.0, 0.85, 0.0])
        colors[red] = np.array([1.0, 0.05, 0.02])
        return colors

    def _deformation_statistics(self, delta_mm: np.ndarray, signed_mm: np.ndarray, warning_mm: float) -> Dict[str, float]:
        values = np.asarray(delta_mm, dtype=np.float64)
        signed = np.asarray(signed_mm, dtype=np.float64)
        caution_mm = max(1.0, float(warning_mm) / 3.0)
        if len(values) == 0:
            return {
                "point_count": 0,
                "mean_delta_mm": 0.0,
                "max_delta_mm": 0.0,
                "p95_delta_mm": 0.0,
                "std_delta_mm": 0.0,
                "stable_point_pct": 0.0,
                "caution_point_pct": 0.0,
                "warning_point_pct": 0.0,
                "mean_signed_delta_mm": 0.0,
            }
        return {
            "point_count": int(len(values)),
            "mean_delta_mm": float(np.mean(values)),
            "max_delta_mm": float(np.max(values)),
            "p95_delta_mm": float(np.percentile(values, 95)),
            "std_delta_mm": float(np.std(values)),
            "stable_point_pct": float(np.mean(values < caution_mm) * 100.0),
            "caution_point_pct": float(np.mean((values >= caution_mm) & (values < warning_mm)) * 100.0),
            "warning_point_pct": float(np.mean(values >= warning_mm) * 100.0),
            "mean_signed_delta_mm": float(np.mean(signed)),
        }

    def _compute_time_series_metrics(
        self,
        points: np.ndarray,
        signed_delta_mm: np.ndarray,
        bin_size_m: float = 1.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        xyz = validate_xyz(points)
        signed = np.asarray(signed_delta_mm, dtype=np.float64)
        if len(xyz) != len(signed):
            raise ValueError("signed_delta_mm length must match points.")
        y_min = float(np.min(xyz[:, 1]))
        y_max = float(np.max(xyz[:, 1]))
        if math.isclose(y_min, y_max):
            return np.array([y_min]), np.array([float(np.mean(signed))]), np.array([0.0])
        edges = np.arange(y_min, y_max + bin_size_m, bin_size_m)
        centers: List[float] = []
        crown: List[float] = []
        convergence: List[float] = []
        for start, end in zip(edges[:-1], edges[1:]):
            mask = (xyz[:, 1] >= start) & (xyz[:, 1] < end)
            if mask.sum() < 10:
                continue
            section = xyz[mask]
            section_delta = signed[mask]
            z_threshold = np.percentile(section[:, 2], 85)
            crown_mask = section[:, 2] >= z_threshold
            x_center = np.median(section[:, 0])
            left_mask = section[:, 0] < x_center
            right_mask = section[:, 0] >= x_center
            centers.append((start + end) * 0.5)
            crown.append(float(np.mean(section_delta[crown_mask])) if crown_mask.any() else float(np.mean(section_delta)))
            if left_mask.any() and right_mask.any():
                left = float(np.mean(section_delta[left_mask]))
                right = float(np.mean(section_delta[right_mask]))
                convergence.append(float(abs(left) + abs(right)))
            else:
                convergence.append(0.0)
        if not centers:
            return np.array([]), np.array([]), np.array([])
        return np.asarray(centers), np.asarray(crown), np.asarray(convergence)

    def compare_with_ground_truth(
        self,
        estimated_points: np.ndarray,
        ground_truth_points: np.ndarray,
        max_distance: Optional[float] = None,
    ) -> Dict[str, float]:
        rmse_m = nearest_neighbor_rmse(estimated_points, ground_truth_points, max_distance=max_distance)
        return {
            "rmse_m": float(rmse_m),
            "rmse_mm": float(rmse_m * 1000.0),
            "within_5mm": bool(rmse_m <= 0.005),
        }

    def registration_table(self) -> List[Dict[str, object]]:
        with self.lock:
            return [link.as_dict() for link in self.registration_links]

    def deformation_table(self) -> List[Dict[str, object]]:
        with self.lock:
            return [result.as_summary() for result in self.deformation_results]


__all__ = [
    "StationManager",
    "StationData",
    "Target",
    "RegistrationLink",
    "DeformationResult",
    "compute_svd_transform",
    "detect_intensity_targets",
    "load_point_cloud_file",
    "nearest_neighbor_rmse",
    "point_to_plane_icp",
    "statistical_outlier_filter",
    "transform_points",
    "voxel_downsample_points",
]
