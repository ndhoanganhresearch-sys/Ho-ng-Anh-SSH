from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.timeseries import TimeSeriesLayer

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "curved_real_scale_railway_tunnel_t0t5"
REGULAR = BASE / "clean_lining_dataset" / "las_export"
RAYCAST = BASE / "field_like_raycast_dataset" / "clean_lining_dataset" / "las_export"
OUT = BASE / "raycast_vs_regular_comparison"
EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
GT_MM = {"T0": 0.0, "T1": -10.0, "T2": -22.0, "T3": -38.0, "T4": -58.0, "T5": -80.0}


def load_epochs(folder: Path) -> list[np.ndarray]:
    loader = BaseLayer()
    return [loader.load_scan(str(folder / f"{epoch}.las")).points for epoch in EPOCHS]


def pct_error(measured: float, gt: float) -> float:
    if abs(gt) < 1e-9:
        return 0.0 if abs(measured) < 1e-9 else math.nan
    return (measured - gt) / abs(gt) * 100.0


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ts = TimeSeriesLayer()
    regular = ts.crown_settlement_series(load_epochs(REGULAR), labels=EPOCHS, chainage_m=52.0)
    raycast = ts.crown_settlement_series(load_epochs(RAYCAST), labels=EPOCHS, chainage_m=52.0)

    rows = []
    for i, epoch in enumerate(EPOCHS):
        gt = GT_MM[epoch]
        reg = float(np.asarray(regular["crown_settlement_mm"])[i])
        ray = float(np.asarray(raycast["crown_settlement_mm"])[i])
        rows.append({
            "epoch": epoch,
            "chainage_m": 52.0,
            "ground_truth_mm": round(gt, 3),
            "tool_regular_crown_mm": round(reg, 3),
            "tool_raycast_crown_mm": round(ray, 3),
            "regular_error_mm": round(reg - gt, 3),
            "raycast_error_mm": round(ray - gt, 3),
            "regular_error_pct": round(pct_error(reg, gt), 3),
            "raycast_error_pct": round(pct_error(ray, gt), 3),
            "regular_zone_points": int(np.asarray(regular["zone_points"])[i]),
            "raycast_zone_points": int(np.asarray(raycast["zone_points"])[i]),
        })

    csv_path = OUT / "crown_settlement_tool_metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    nonzero = [row for row in rows if row["epoch"] != "T0"]
    summary = {
        "metric": regular["metric"],
        "chainage_m": regular["chainage_m"],
        "chainage_window_m": regular["chainage_window_m"],
        "lateral_window_m": regular["lateral_window_m"],
        "crown_percentile": regular["crown_percentile"],
        "regular_mae_mm": round(float(np.mean([abs(row["regular_error_mm"]) for row in nonzero])), 3),
        "raycast_mae_mm": round(float(np.mean([abs(row["raycast_error_mm"]) for row in nonzero])), 3),
        "regular_mape_pct": round(float(np.mean([abs(row["regular_error_pct"]) for row in nonzero])), 3),
        "raycast_mape_pct": round(float(np.mean([abs(row["raycast_error_pct"]) for row in nonzero])), 3),
    }
    (OUT / "crown_settlement_tool_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Crown Settlement Tool Check",
        "",
        "This uses the tool core crown-local metric for settlement at the tunnel crown, not whole-cloud p95.",
        "",
        f"- Regular MAE: {summary['regular_mae_mm']:.2f} mm ({summary['regular_mape_pct']:.2f}%)",
        f"- Raycast MAE: {summary['raycast_mae_mm']:.2f} mm ({summary['raycast_mape_pct']:.2f}%)",
        "",
        "| Epoch | GT mm | Regular crown | Raycast crown | Regular err % | Raycast err % |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['epoch']} | {row['ground_truth_mm']:+.1f} | {row['tool_regular_crown_mm']:+.1f} | "
            f"{row['tool_raycast_crown_mm']:+.1f} | {row['regular_error_pct']:+.1f}% | {row['raycast_error_pct']:+.1f}% |"
        )
    (OUT / "crown_settlement_tool_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
