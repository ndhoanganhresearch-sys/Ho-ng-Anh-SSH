from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "data" / "curved_real_scale_railway_tunnel_t0t5"
REGULAR_DIR = BASE_DIR / "clean_lining_dataset"
RAYCAST_DIR = BASE_DIR / "field_like_raycast_dataset" / "clean_lining_dataset"
OUT_DIR = BASE_DIR / "raycast_vs_regular_comparison"
EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
GROUND_TRUTH_MM = {"T0": 0.0, "T1": -10.0, "T2": -22.0, "T3": -38.0, "T4": -58.0, "T5": -80.0}
CURVE_R = 420.0
CHAINAGE_M = 52.0
CHAINAGE_WINDOW_M = 5.0
LATERAL_WINDOW_M = 12.0
CROWN_PERCENTILE = 98.0


def load_points(dataset_dir: Path, epoch: str) -> np.ndarray:
    las_path = dataset_dir / "las_export" / f"{epoch}.las"
    if las_path.exists():
        import laspy

        las = laspy.read(str(las_path))
        return np.column_stack([las.x, las.y, las.z]).astype(float)
    txt_path = dataset_dir / f"{epoch}.txt"
    if txt_path.exists():
        arr = np.loadtxt(txt_path, comments="#")
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        return arr[:, :3].astype(float)
    raise FileNotFoundError(f"Missing {epoch}.las/.txt in {dataset_dir}")


def curved_local(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]
    angle = np.arctan2(y, CURVE_R - x)
    chainage = CURVE_R * angle
    cx = CURVE_R * (1.0 - np.cos(angle))
    cy = CURVE_R * np.sin(angle)
    right_x = np.cos(angle)
    right_y = -np.sin(angle)
    lateral = (x - cx) * right_x + (y - cy) * right_y
    return chainage, lateral, z


def crown_value(points: np.ndarray) -> tuple[float, int]:
    chainage, lateral, z = curved_local(points)
    mask = (np.abs(chainage - CHAINAGE_M) <= CHAINAGE_WINDOW_M) & (np.abs(lateral) <= LATERAL_WINDOW_M)
    zone = z[mask]
    if zone.size < 20:
        return math.nan, int(zone.size)
    return float(np.percentile(zone, CROWN_PERCENTILE)), int(zone.size)


def measure_series(dataset_dir: Path) -> dict[str, dict[str, float]]:
    baseline_value, baseline_count = crown_value(load_points(dataset_dir, "T0"))
    out = {"T0": {"crown_z_m": baseline_value, "settlement_mm": 0.0, "zone_points": baseline_count}}
    for epoch in EPOCHS[1:]:
        value, count = crown_value(load_points(dataset_dir, epoch))
        out[epoch] = {
            "crown_z_m": value,
            "settlement_mm": (value - baseline_value) * 1000.0,
            "zone_points": count,
        }
    return out


def trend_ok(values: list[float]) -> bool:
    finite = [v for v in values if math.isfinite(v)]
    return len(finite) == len(values) and all(finite[i] <= finite[i - 1] + 8.0 for i in range(1, len(finite)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare curved tunnel regular clean dataset against field-like raycast clean dataset.")
    parser.add_argument("--regular", default=str(REGULAR_DIR))
    parser.add_argument("--raycast", default=str(RAYCAST_DIR))
    parser.add_argument("--out", default=str(OUT_DIR))
    args = parser.parse_args()

    regular_dir = Path(args.regular).resolve()
    raycast_dir = Path(args.raycast).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    regular = measure_series(regular_dir)
    raycast = measure_series(raycast_dir)

    rows = []
    for epoch in EPOCHS:
        gt = GROUND_TRUTH_MM[epoch]
        regular_mm = regular[epoch]["settlement_mm"]
        raycast_mm = raycast[epoch]["settlement_mm"]
        rows.append({
            "epoch": epoch,
            "chainage_m": CHAINAGE_M,
            "ground_truth_mm": round(gt, 3),
            "regular_measured_mm": round(regular_mm, 3),
            "raycast_measured_mm": round(raycast_mm, 3),
            "regular_error_mm": round(regular_mm - gt, 3),
            "raycast_error_mm": round(raycast_mm - gt, 3),
            "raycast_vs_regular_mm": round(raycast_mm - regular_mm, 3),
            "regular_zone_points": int(regular[epoch]["zone_points"]),
            "raycast_zone_points": int(raycast[epoch]["zone_points"]),
        })

    csv_path = out_dir / "comparison_metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    regular_abs_errors = [abs(row["regular_error_mm"]) for row in rows]
    raycast_abs_errors = [abs(row["raycast_error_mm"]) for row in rows]
    raycast_vs_regular = [abs(row["raycast_vs_regular_mm"]) for row in rows]
    summary = {
        "regular_dir": str(regular_dir),
        "raycast_dir": str(raycast_dir),
        "output_dir": str(out_dir),
        "method": "Curved centerline chainage zone, p98 crown z value relative to T0",
        "chainage_m": CHAINAGE_M,
        "chainage_window_m": CHAINAGE_WINDOW_M,
        "lateral_window_m": LATERAL_WINDOW_M,
        "regular_mae_to_gt_mm": round(float(np.mean(regular_abs_errors)), 3),
        "raycast_mae_to_gt_mm": round(float(np.mean(raycast_abs_errors)), 3),
        "raycast_mae_to_regular_mm": round(float(np.mean(raycast_vs_regular)), 3),
        "regular_trend_ok": trend_ok([row["regular_measured_mm"] for row in rows]),
        "raycast_trend_ok": trend_ok([row["raycast_measured_mm"] for row in rows]),
        "epochs": EPOCHS,
    }
    (out_dir / "comparison_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Curved Regular vs Raycast Comparison",
        "",
        "This benchmark compares clean mesh-sampled lining points against field-like TLS raycast lining points.",
        "",
        f"- Regular MAE to ground truth: {summary['regular_mae_to_gt_mm']:.2f} mm",
        f"- Raycast MAE to ground truth: {summary['raycast_mae_to_gt_mm']:.2f} mm",
        f"- Raycast MAE to regular: {summary['raycast_mae_to_regular_mm']:.2f} mm",
        f"- Crown check chainage: {CHAINAGE_M:.1f} m on curved centerline R={CURVE_R:.0f} m",
        "",
        "| Epoch | GT mm | Regular mm | Raycast mm | Regular err | Raycast err | Raycast-Regular |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['epoch']} | {row['ground_truth_mm']:+.1f} | {row['regular_measured_mm']:+.1f} | "
            f"{row['raycast_measured_mm']:+.1f} | {row['regular_error_mm']:+.1f} | "
            f"{row['raycast_error_mm']:+.1f} | {row['raycast_vs_regular_mm']:+.1f} |"
        )
    (out_dir / "comparison_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"wrote: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
