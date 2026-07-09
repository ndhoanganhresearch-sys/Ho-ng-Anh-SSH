"""Cross-check Step 6 deformation with py4dgeo M3C2.

This script is intentionally standalone and optional. It does not change the
main app pipeline; it only reads two point clouds and writes summary metrics.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "blender_lidar_t0t5"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "py4dgeo_m3c2_crosscheck.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an optional py4dgeo M3C2 cross-check on T0/Tn clouds."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Dataset directory containing T0/Tn text clouds.",
    )
    parser.add_argument(
        "--epoch",
        default="T5",
        help="Monitoring epoch to compare against T0, e.g. T1..T5.",
    )
    parser.add_argument(
        "--full-cloud",
        action="store_true",
        help="Use T0.txt/Tn.txt instead of smaller T0_raycast.txt/Tn_raycast.txt.",
    )
    parser.add_argument(
        "--max-corepoints",
        type=int,
        default=5000,
        help="Maximum number of T0 core points sampled for M3C2.",
    )
    parser.add_argument(
        "--normal-radii",
        type=float,
        nargs="+",
        default=[0.5, 1.0, 2.0],
        help="Multiscale normal radii in cloud units.",
    )
    parser.add_argument(
        "--cyl-radius",
        type=float,
        default=0.4,
        help="M3C2 cylinder radius in cloud units.",
    )
    parser.add_argument(
        "--max-distance",
        type=float,
        default=1.0,
        help="Maximum point search distance in cloud units.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="CSV summary output path.",
    )
    return parser.parse_args()


def require_py4dgeo():
    try:
        import py4dgeo
    except ImportError as exc:
        raise SystemExit(
            "py4dgeo is not installed in this Python environment. "
            "Install it first, then rerun this optional cross-check."
        ) from exc
    return py4dgeo


def cloud_path(dataset: Path, epoch: str, full_cloud: bool) -> Path:
    suffix = ".txt" if full_cloud else "_raycast.txt"
    return dataset / f"{epoch}{suffix}"


def load_xyz(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Point cloud not found: {path}")
    cloud = np.loadtxt(path, usecols=(0, 1, 2), dtype=np.float64)
    if cloud.ndim != 2 or cloud.shape[1] != 3:
        raise ValueError(f"Expected an Nx3 point cloud in {path}, got {cloud.shape}")
    return np.ascontiguousarray(cloud)


def sample_corepoints(cloud: np.ndarray, max_corepoints: int) -> np.ndarray:
    if max_corepoints <= 0 or cloud.shape[0] <= max_corepoints:
        return cloud
    indices = np.linspace(0, cloud.shape[0] - 1, max_corepoints, dtype=np.int64)
    return np.ascontiguousarray(cloud[indices])


def finite_stats(values: np.ndarray) -> dict[str, float | int]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {
            "valid_count": 0,
            "mean_mm": float("nan"),
            "median_mm": float("nan"),
            "p95_abs_mm": float("nan"),
            "max_abs_mm": float("nan"),
        }

    finite_mm = finite * 1000.0
    return {
        "valid_count": int(finite.size),
        "mean_mm": float(np.mean(finite_mm)),
        "median_mm": float(np.median(finite_mm)),
        "p95_abs_mm": float(np.percentile(np.abs(finite_mm), 95)),
        "max_abs_mm": float(np.max(np.abs(finite_mm))),
    }


def validation_summary(dataset: Path, epoch: str) -> dict[str, float | str]:
    path = dataset / "series_validation.csv"
    if not path.exists():
        return {"validation_source": "missing"}

    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("epoch") == epoch:
                rows.append(row)

    if not rows:
        return {"validation_source": "no_epoch"}

    errors = [abs(float(row["error_mm"])) for row in rows]
    return {
        "validation_source": str(path.relative_to(PROJECT_ROOT)),
        "validation_metric_count": len(errors),
        "validation_mean_abs_error_mm": float(np.mean(errors)),
        "validation_max_abs_error_mm": float(np.max(errors)),
    }


def write_summary(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(summary.keys())
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow(summary)


def main() -> int:
    args = parse_args()
    py4dgeo = require_py4dgeo()

    dataset = args.dataset.resolve()
    reference_path = cloud_path(dataset, "T0", args.full_cloud)
    monitoring_path = cloud_path(dataset, args.epoch, args.full_cloud)

    reference_cloud = load_xyz(reference_path)
    monitoring_cloud = load_xyz(monitoring_path)
    corepoints = sample_corepoints(reference_cloud, args.max_corepoints)

    reference_epoch = py4dgeo.Epoch(reference_cloud)
    monitoring_epoch = py4dgeo.Epoch(monitoring_cloud)
    m3c2 = py4dgeo.M3C2(
        epochs=(reference_epoch, monitoring_epoch),
        corepoints=corepoints,
        normal_radii=args.normal_radii,
        cyl_radius=args.cyl_radius,
        max_distance=args.max_distance,
    )
    distances, uncertainties = m3c2.run()

    summary: dict[str, object] = {
        "dataset": str(dataset.relative_to(PROJECT_ROOT))
        if dataset.is_relative_to(PROJECT_ROOT)
        else str(dataset),
        "reference_epoch": "T0",
        "monitoring_epoch": args.epoch,
        "reference_file": reference_path.name,
        "monitoring_file": monitoring_path.name,
        "reference_points": int(reference_cloud.shape[0]),
        "monitoring_points": int(monitoring_cloud.shape[0]),
        "corepoints": int(corepoints.shape[0]),
        "normal_radii": ";".join(str(radius) for radius in args.normal_radii),
        "cyl_radius": args.cyl_radius,
        "max_distance": args.max_distance,
    }
    summary.update(finite_stats(distances))
    if uncertainties is not None:
        if getattr(uncertainties, "dtype", None) is not None and uncertainties.dtype.names:
            if "lodetection" in uncertainties.dtype.names:
                uncertainty_values = uncertainties["lodetection"]
            else:
                uncertainty_values = uncertainties[uncertainties.dtype.names[0]]
        else:
            uncertainty_values = uncertainties
        summary["uncertainty_p95_mm"] = finite_stats(uncertainty_values)["p95_abs_mm"]
    summary.update(validation_summary(dataset, args.epoch))

    output_path = args.output.resolve()
    write_summary(output_path, summary)

    print("py4dgeo M3C2 cross-check complete")
    print(f"  dataset: {dataset}")
    print(f"  pair: T0 -> {args.epoch}")
    print(f"  corepoints: {corepoints.shape[0]}")
    print(f"  p95_abs_mm: {summary['p95_abs_mm']:.3f}")
    print(f"  max_abs_mm: {summary['max_abs_mm']:.3f}")
    print(f"  output: {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
