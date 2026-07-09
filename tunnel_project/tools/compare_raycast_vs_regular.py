r"""Compare Blender raycast epochs against regular-surface ground truth.

The raycast dataset simulates TLS visibility, noise, clutter, and scanner pose
bias. The regular dataset samples the same lining deformation model directly on
a dense surface grid. This script measures the same deformation windows in both
datasets and writes a compact evidence table.

Run from ``tunnel_project``::

    ..\.venv\Scripts\python.exe tools\compare_raycast_vs_regular.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RAYCAST_DIR = ROOT / "data" / "blender_lidar_t0t5_realistic"
REGULAR_DIR = ROOT / "data" / "blender_lidar_t0t5_realistic_regular"
OUT_DIR = ROOT / "data" / "blender_lidar_t0t5_realistic_comparison"
EPOCHS = ["T1", "T2", "T3", "T4", "T5"]
CURVE_R = 420.0
S_WINDOW_M = 3.0
ANGLE_WINDOW_DEG = 18.0

METRICS = {
    "crown_settlement_mm": {"chainage_m": 24.0, "theta_deg": 90.0},
    "sidewall_convergence_mm": {"chainage_m": 50.0, "theta_deg": 0.0},
    "local_damage_mm": {"chainage_m": 72.0, "theta_deg": 58.0},
}


def load_lining(path: Path) -> np.ndarray:
    arr = np.loadtxt(path, comments="#")
    if arr.ndim != 2 or arr.shape[1] < 3:
        raise ValueError(f"Invalid point file: {path}")
    if arr.shape[1] >= 8:
        arr = arr[arr[:, 7].astype(int) == 1]
    return arr[:, :3]


def frame(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    y = points[:, 1]
    s = CURVE_R * np.arcsin(np.clip(y / CURVE_R, -1.0, 1.0))
    cx = CURVE_R * (1.0 - np.cos(s / CURVE_R))
    lateral = points[:, 0] - cx
    up = points[:, 2] - 0.002 * s
    theta = np.degrees(np.arctan2(up, lateral))
    return s, lateral, up, theta


def angle_delta_deg(theta: np.ndarray, theta0: float) -> np.ndarray:
    return np.abs((theta - theta0 + 180.0) % 360.0 - 180.0)


def zone(points: np.ndarray, chainage_m: float, theta_deg: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    s, lateral, up, theta = frame(points)
    mask = (np.abs(s - chainage_m) <= S_WINDOW_M) & (angle_delta_deg(theta, theta_deg) <= ANGLE_WINDOW_DEG)
    return lateral[mask], up[mask], mask


def measure(t0: np.ndarray, tn: np.ndarray, metric: str, chainage_m: float, theta_deg: float) -> tuple[float, int, int]:
    lat0, up0, mask0 = zone(t0, chainage_m, theta_deg)
    latn, upn, maskn = zone(tn, chainage_m, theta_deg)
    if len(lat0) == 0 or len(latn) == 0:
        return math.nan, int(mask0.sum()), int(maskn.sum())
    if metric == "crown_settlement_mm":
        measured = (upn.mean() - up0.mean()) * 1000.0
    elif metric == "sidewall_convergence_mm":
        measured = (np.abs(latn).mean() - np.abs(lat0).mean()) * 1000.0
    elif metric == "local_damage_mm":
        r0 = np.hypot(lat0, up0).mean()
        rn = np.hypot(latn, upn).mean()
        measured = (rn - r0) * 1000.0
    else:
        raise KeyError(metric)
    return float(measured), int(mask0.sum()), int(maskn.sum())


def read_ground_truth(path: Path) -> dict[str, dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        return {row["epoch"]: {k: float(v) for k, v in row.items() if k != "epoch"} for row in rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raycast", default=str(RAYCAST_DIR))
    parser.add_argument("--regular", default=str(REGULAR_DIR))
    parser.add_argument("--out", default=str(OUT_DIR))
    args = parser.parse_args()

    raycast_dir = Path(args.raycast).resolve()
    regular_dir = Path(args.regular).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    gt = read_ground_truth(raycast_dir / "ground_truth.csv")
    raycast_t0 = load_lining(raycast_dir / "T0.txt")
    regular_t0 = load_lining(regular_dir / "T0_regular.txt")

    rows = []
    for epoch in EPOCHS:
        raycast_tn = load_lining(raycast_dir / f"{epoch}.txt")
        regular_tn = load_lining(regular_dir / f"{epoch}_regular.txt")
        for metric, spec in METRICS.items():
            raycast_mm, raycast_t0_count, raycast_tn_count = measure(raycast_t0, raycast_tn, metric, **spec)
            regular_mm, regular_t0_count, regular_tn_count = measure(regular_t0, regular_tn, metric, **spec)
            gt_mm = gt[epoch][metric]
            rows.append({
                "epoch": epoch,
                "metric": metric,
                "chainage_m": spec["chainage_m"],
                "theta_deg": spec["theta_deg"],
                "ground_truth_mm": round(gt_mm, 3),
                "regular_measured_mm": round(regular_mm, 3),
                "raycast_measured_mm": round(raycast_mm, 3),
                "regular_error_to_gt_mm": round(abs(regular_mm - gt_mm), 3),
                "raycast_error_to_gt_mm": round(abs(raycast_mm - gt_mm), 3),
                "raycast_error_to_regular_mm": round(abs(raycast_mm - regular_mm), 3),
                "raycast_t0_zone_points": raycast_t0_count,
                "raycast_tn_zone_points": raycast_tn_count,
                "regular_t0_zone_points": regular_t0_count,
                "regular_tn_zone_points": regular_tn_count,
            })

    csv_path = out_dir / "comparison_metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    raycast_mae = float(np.mean([row["raycast_error_to_gt_mm"] for row in rows]))
    regular_mae = float(np.mean([row["regular_error_to_gt_mm"] for row in rows]))
    raycast_vs_regular_mae = float(np.mean([row["raycast_error_to_regular_mm"] for row in rows]))
    summary = {
        "raycast_dir": str(raycast_dir),
        "regular_dir": str(regular_dir),
        "rows": len(rows),
        "regular_mae_to_gt_mm": round(regular_mae, 3),
        "raycast_mae_to_gt_mm": round(raycast_mae, 3),
        "raycast_mae_to_regular_mm": round(raycast_vs_regular_mae, 3),
        "window": {"chainage_m": S_WINDOW_M, "angle_deg": ANGLE_WINDOW_DEG},
    }
    (out_dir / "comparison_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Raycast vs Regular Comparison",
        "",
        f"- Regular MAE to GT: {regular_mae:.2f} mm",
        f"- Raycast MAE to GT: {raycast_mae:.2f} mm",
        f"- Raycast MAE to regular: {raycast_vs_regular_mae:.2f} mm",
        f"- Window: +/-{S_WINDOW_M:.1f} m, +/-{ANGLE_WINDOW_DEG:.0f} deg",
        "",
        "| Epoch | Metric | GT | Regular | Raycast | Raycast-GT Err | Raycast-Regular Err |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['epoch']} | {row['metric']} | {row['ground_truth_mm']:+.1f} | "
            f"{row['regular_measured_mm']:+.1f} | {row['raycast_measured_mm']:+.1f} | "
            f"{row['raycast_error_to_gt_mm']:.1f} | {row['raycast_error_to_regular_mm']:.1f} |"
        )
    (out_dir / "comparison_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"wrote: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
