r"""Create a lightweight copy of a T0-T5 LAS/TXT dataset for faster GUI tests.

Example:
    ..\.venv\Scripts\python.exe tools\make_lite_lidar_dataset.py \
        --src data\blender_lidar_t0t5_sample_based \
        --dst data\blender_lidar_t0t5_sample_based_lite \
        --max-points 200000
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import laspy
import numpy as np


def copy_if_exists(src: Path, dst: Path, name: str) -> None:
    path = src / name
    if path.exists():
        shutil.copy2(path, dst / name)


def downsample_epoch(src: Path, dst: Path, stem: str, max_points: int) -> dict:
    las = laspy.read(src / f"{stem}.las")
    total = len(las.x)
    step = max(1, int(np.ceil(total / max_points)))
    idx = np.arange(0, total, step)
    if len(idx) > max_points:
        idx = idx[:max_points]

    points = np.column_stack([np.asarray(las.x)[idx], np.asarray(las.y)[idx], np.asarray(las.z)[idx]])
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = las.header.scales
    header.offsets = points.min(axis=0)
    out = laspy.LasData(header)
    out.x, out.y, out.z = points[:, 0], points[:, 1], points[:, 2]
    out.intensity = np.asarray(las.intensity)[idx]
    out.classification = np.asarray(las.classification)[idx]
    if hasattr(las, "red"):
        out.red = np.asarray(las.red)[idx]
        out.green = np.asarray(las.green)[idx]
        out.blue = np.asarray(las.blue)[idx]
    out.write(str(dst / f"{stem}.las"))

    intensity = np.asarray(out.intensity, dtype=np.float64) / 65535.0
    labels = np.asarray(out.classification, dtype=np.uint8)
    arr = np.column_stack([points, np.zeros_like(points), intensity, labels])
    np.savetxt(
        dst / f"{stem}.txt",
        arr,
        fmt=["%.5f", "%.5f", "%.5f", "%.6f", "%.6f", "%.6f", "%.6f", "%d"],
        header="x y z nx ny nz intensity label",
        comments="# ",
    )

    labels_unique, counts = np.unique(labels, return_counts=True)
    meta = {}
    meta_path = src / f"{stem}.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update({
        "epoch": stem,
        "file": f"{stem}.txt",
        "las_file": f"{stem}.las",
        "points": int(len(idx)),
        "source_points": int(total),
        "downsample_step": int(step),
        "hit_counts_by_label": {str(int(k)): int(v) for k, v in zip(labels_unique, counts)},
    })
    (dst / f"{stem}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", default="data/blender_lidar_t0t5_sample_based")
    parser.add_argument("--dst", default="data/blender_lidar_t0t5_sample_based_lite")
    parser.add_argument("--max-points", type=int, default=200_000)
    args = parser.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)
    dst.mkdir(parents=True, exist_ok=True)

    for name in ["README.md", "ground_truth.csv", "baseline_pairs.csv", "incremental_pairs.csv"]:
        copy_if_exists(src, dst, name)

    epoch_metas = [downsample_epoch(src, dst, f"T{i}", args.max_points) for i in range(6)]

    manifest = {}
    manifest_path = src / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "dataset": dst.name,
        "source_dataset": str(src),
        "lite_max_points_per_epoch": int(args.max_points),
        "las_files": [f"T{i}.las" for i in range(6)],
        "txt_files": [f"T{i}.txt" for i in range(6)],
        "epochs": epoch_metas,
    })
    (dst / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    readme = dst / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
    else:
        text = "# Lite LiDAR Dataset\n"
    text += f"\n\n## Lite version\n\nDownsampled to about {args.max_points:,} points per epoch for faster GUI testing.\n"
    readme.write_text(text, encoding="utf-8")

    print(f"Lite dataset written to: {dst}")
    for meta in epoch_metas:
        print(meta["epoch"], meta["points"], "from", meta["source_points"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
