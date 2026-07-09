r"""Create dense T0-T5 epochs by deforming a sample point cloud directly.

This is for GUI/Step 6 testing when Blender raycasting creates sparse coverage.
It preserves the source point density and topology: T0 is the original sample
point cloud, and T1-T5 are deterministic deformed copies with small noise and
pose bias metadata.

Default source:
    data/sample_pcd/u-type_tunnel_0k630 cut_1.las

Run from tunnel_project:
    ..\.venv\Scripts\python.exe tools\create_t0t5_from_sample_pointcloud_dense.py
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import laspy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "sample_pcd" / "u-type_tunnel_0k630 cut_1.las"
DEFAULT_OUT = ROOT / "data" / "sample_pcd_t0t5_dense"

EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
CROWN_MM = {"T0": 0.0, "T1": -4.0, "T2": -9.0, "T3": -16.0, "T4": -25.0, "T5": -36.0}
CONV_MM = {"T0": 0.0, "T1": -1.0, "T2": -4.0, "T3": -9.0, "T4": -15.0, "T5": -24.0}
LOCAL_MM = {"T0": 0.0, "T1": 0.0, "T2": 0.0, "T3": -8.0, "T4": -17.0, "T5": -30.0}
POSE_BIAS = {
    "T0": (0.000, 0.000, 0.000),
    "T1": (0.002, -0.003, 0.001),
    "T2": (-0.003, 0.002, -0.001),
    "T3": (0.004, 0.004, 0.001),
    "T4": (-0.005, -0.004, 0.002),
    "T5": (0.006, -0.005, 0.002),
}


def robust_center(points: np.ndarray) -> tuple[float, float]:
    return float(np.median(points[:, 0])), float(np.median(points[:, 2]))


def deformation(points: np.ndarray, epoch: str, rng: np.random.Generator) -> np.ndarray:
    if epoch == "T0":
        return points.copy()

    out = points.copy()
    x0, z0 = robust_center(points)
    y_min, y_max = float(points[:, 1].min()), float(points[:, 1].max())
    length = max(1e-6, y_max - y_min)
    y_norm = (points[:, 1] - y_min) / length
    theta = np.arctan2(points[:, 2] - z0, points[:, 0] - x0)

    crown = CROWN_MM[epoch] / 1000.0
    conv = CONV_MM[epoch] / 1000.0
    local = LOCAL_MM[epoch] / 1000.0

    crown_w = np.exp(-0.5 * ((y_norm - 0.30) / 0.105) ** 2) * np.maximum(0.0, np.sin(theta)) ** 1.6
    side_w = np.exp(-0.5 * ((y_norm - 0.58) / 0.125) ** 2) * np.abs(np.cos(theta)) ** 1.3
    local_w = np.exp(-0.5 * ((y_norm - 0.78) / 0.060) ** 2) * np.exp(-0.5 * ((np.arctan2(np.sin(theta - np.deg2rad(62.0)), np.cos(theta - np.deg2rad(62.0)))) / 0.25) ** 2)

    out[:, 2] += crown * crown_w + local * local_w
    out[:, 0] += -np.sign(points[:, 0] - x0) * abs(conv) * side_w

    # Tiny measurement noise only; keep geometry dense and stable.
    out += rng.normal(0.0, 0.0007, out.shape)
    out += np.asarray(POSE_BIAS[epoch], dtype=np.float64)
    return out


def estimate_normals_like(points: np.ndarray) -> np.ndarray:
    x0, z0 = robust_center(points)
    normals = np.zeros_like(points)
    radial = np.column_stack([points[:, 0] - x0, np.zeros(len(points)), points[:, 2] - z0])
    norm = np.linalg.norm(radial, axis=1)
    ok = norm > 1e-9
    normals[ok] = radial[ok] / norm[ok, None]
    return normals


def write_las(path: Path, points: np.ndarray, intensity: np.ndarray, labels: np.ndarray, source_header) -> None:
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = source_header.scales
    header.offsets = points.min(axis=0)
    las = laspy.LasData(header)
    las.x, las.y, las.z = points[:, 0], points[:, 1], points[:, 2]
    las.intensity = intensity.astype(np.uint16)
    las.classification = labels.astype(np.uint8)
    gray = np.clip(intensity, 0, 65535).astype(np.uint16)
    las.red = gray
    las.green = gray
    las.blue = gray
    las.write(str(path))


def write_txt(path: Path, points: np.ndarray, normals: np.ndarray, intensity: np.ndarray, labels: np.ndarray) -> None:
    arr = np.column_stack([points, normals, intensity.astype(np.float64) / 65535.0, labels])
    np.savetxt(
        path,
        arr,
        fmt=["%.5f", "%.5f", "%.5f", "%.6f", "%.6f", "%.6f", "%.6f", "%d"],
        header="x y z nx ny nz intensity label",
        comments="# ",
    )


def write_tables(out_dir: Path) -> None:
    with (out_dir / "ground_truth.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "crown_settlement_mm", "sidewall_convergence_mm", "local_damage_mm"])
        for epoch in EPOCHS:
            w.writerow([epoch, CROWN_MM[epoch], CONV_MM[epoch], LOCAL_MM[epoch]])
    with (out_dir / "baseline_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "crown_delta_mm", "sidewall_delta_mm", "local_delta_mm"])
        for epoch in EPOCHS[1:]:
            w.writerow([f"T0-{epoch}", CROWN_MM[epoch], CONV_MM[epoch], LOCAL_MM[epoch]])
    with (out_dir / "incremental_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "crown_increment_mm", "sidewall_increment_mm", "local_increment_mm"])
        for a, b in zip(EPOCHS[:-1], EPOCHS[1:]):
            w.writerow([f"{a}-{b}", CROWN_MM[b] - CROWN_MM[a], CONV_MM[b] - CONV_MM[a], LOCAL_MM[b] - LOCAL_MM[a]])


def write_readme(out_dir: Path, source: Path, points: int) -> None:
    text = f"""# Sample PCD T0-T5 Dense Dataset

This dataset preserves the point coverage of the sample point cloud and applies deterministic T0-T5 deformation directly to the points.

## Source

- `{source}`
- Points per epoch: `{points:,}`

## Why this dataset exists

The Blender raycast version can be too sparse for GUI/M3C2 testing. This dense version keeps the original sample coverage so the deformation map does not appear as a thin strip or with large missing areas.

## Ground truth deformation

- Crown settlement: 0 to -36 mm
- Sidewall convergence: 0 to -24 mm
- Local damage: starts at T3 and reaches -30 mm at T5

## Files

- `T0.las` ... `T5.las`: recommended for tool loading.
- `T0.txt` ... `T5.txt`: debug text with `x y z nx ny nz intensity label`.
- `ground_truth.csv`, `baseline_pairs.csv`, `incremental_pairs.csv`, `manifest.json`.

## Suggested workflow

1. Load `T0.las` as reference.
2. Add `T1.las` to `T5.las` for time-series testing.
3. Run Step 6 trend/M3C2. Registration can be run too because T1-T5 include small pose bias.
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--max-points", type=int, default=0, help="Optional deterministic stride downsample; 0 keeps all points")
    args = parser.parse_args()

    source = Path(args.source)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    las = laspy.read(source)
    points = np.column_stack([np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)]).astype(np.float64)
    intensity = np.asarray(las.intensity, dtype=np.uint16)
    if int(intensity.max()) == 0:
        z_scaled = (points[:, 2] - points[:, 2].min()) / max(1e-9, np.ptp(points[:, 2]))
        intensity = np.clip((0.35 + 0.45 * z_scaled) * 65535, 0, 65535).astype(np.uint16)
    labels = np.ones(len(points), dtype=np.uint8)

    if args.max_points and len(points) > args.max_points:
        step = int(np.ceil(len(points) / args.max_points))
        idx = np.arange(0, len(points), step)
        points = points[idx]
        intensity = intensity[idx]
        labels = labels[idx]

    rng = np.random.default_rng(20260629)
    normals0 = estimate_normals_like(points)
    epoch_meta = []
    for epoch in EPOCHS:
        pts_epoch = deformation(points, epoch, rng)
        normals = normals0 if epoch == "T0" else estimate_normals_like(pts_epoch)
        write_las(out_dir / f"{epoch}.las", pts_epoch, intensity, labels, las.header)
        write_txt(out_dir / f"{epoch}.txt", pts_epoch, normals, intensity, labels)
        meta = {
            "epoch": epoch,
            "las_file": f"{epoch}.las",
            "txt_file": f"{epoch}.txt",
            "points": int(len(pts_epoch)),
            "source": str(source),
            "bounds_min": pts_epoch.min(axis=0).tolist(),
            "bounds_max": pts_epoch.max(axis=0).tolist(),
            "deformation_mm": {
                "crown_settlement": CROWN_MM[epoch],
                "sidewall_convergence": CONV_MM[epoch],
                "local_damage": LOCAL_MM[epoch],
            },
            "pose_bias_m": POSE_BIAS[epoch],
        }
        (out_dir / f"{epoch}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        epoch_meta.append(meta)

    write_tables(out_dir)
    write_readme(out_dir, source, len(points))
    manifest = {
        "dataset": out_dir.name,
        "created_by": "tools/create_t0t5_from_sample_pointcloud_dense.py",
        "source": str(source),
        "method": "direct point-cloud deformation preserving source coverage",
        "points_per_epoch": int(len(points)),
        "las_files": [f"T{i}.las" for i in range(6)],
        "txt_files": [f"T{i}.txt" for i in range(6)],
        "epochs": epoch_meta,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Dataset written to: {out_dir}")
    print(f"Points per epoch: {len(points):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
