# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
from pathlib import Path

import laspy
import numpy as np

from tunnel_analysis.timeseries import TimeSeriesLayer


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "time_series_deformation"
EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def load_las(epoch: str) -> np.ndarray:
    las = laspy.read(DATA / f"{epoch}.las")
    return np.column_stack([las.x, las.y, las.z])


def load_ground_truth() -> dict[tuple[str, str], float]:
    with (DATA / "ground_truth.csv").open(newline="", encoding="utf-8") as fh:
        return {
            (row["epoch"], row["deformation_type"]): float(row["value_mm"])
            for row in csv.DictReader(fh)
        }


def band(points: np.ndarray, chainage: float, width: float = 1.0) -> np.ndarray:
    return np.abs(points[:, 1] - chainage) <= width


def crown_z_delta(t0: np.ndarray, tn: np.ndarray, chainage: float = 20.0) -> float:
    mask = band(t0, chainage)
    top = t0[:, 2] > np.percentile(t0[mask, 2], 82)
    mask = mask & top
    return float(np.median((tn[mask, 2] - t0[mask, 2]) * 1000.0))


def sidewall_total_convergence_delta(t0: np.ndarray, tn: np.ndarray, chainage: float = 45.0) -> float:
    mask = band(t0, chainage)
    w0 = np.percentile(t0[mask, 0], 97) - np.percentile(t0[mask, 0], 3)
    wn = np.percentile(tn[mask, 0], 97) - np.percentile(tn[mask, 0], 3)
    return float((wn - w0) * 1000.0)


def local_damage_delta(t0: np.ndarray, tn: np.ndarray, chainage: float = 65.0) -> float:
    mask = band(t0, chainage, width=0.75)
    local_z = t0[:, 2] - 0.001 * t0[:, 1]
    theta = np.arctan2(local_z, t0[:, 0] - 0.15 * np.sin(t0[:, 1] / 80.0 * np.pi))
    theta0 = np.deg2rad(55.0)
    angular = np.abs(np.arctan2(np.sin(theta - theta0), np.cos(theta - theta0))) <= 0.22
    mask = mask & angular
    radial0 = np.hypot(t0[mask, 0], t0[mask, 2] - 0.001 * t0[mask, 1])
    radialn = np.hypot(tn[mask, 0], tn[mask, 2] - 0.001 * tn[mask, 1])
    return float(np.median((radialn - radial0) * 1000.0))


def assert_metric(name: str, measured: list[float], expected: list[float], tolerance_mm: float) -> None:
    errors = [abs(m - e) for m, e in zip(measured, expected)]
    mae = float(np.mean(errors))
    max_error = float(np.max(errors))
    print(f"{name}: measured={np.round(measured, 1).tolist()} expected={np.round(expected, 1).tolist()} MAE={mae:.1f}mm max={max_error:.1f}mm")
    check(max_error <= tolerance_mm, f"{name} matches ground_truth.csv within {tolerance_mm:g}mm")


def main() -> int:
    check(DATA.exists(), "time_series_deformation dataset exists")
    gt = load_ground_truth()
    points = [load_las(epoch) for epoch in EPOCHS]

    ts = TimeSeriesLayer()
    series = ts.spatiotemporal_series(points, labels=EPOCHS[1:], max_corepoints=4000)
    gt_check = ts.compare_to_ground_truth(series, str(DATA / "ground_truth.csv"), metric="p95_abs_mm")
    print(gt_check["summary"])
    check(gt_check["n"] == 5, "Step 6 p95 trend matched all monitoring epochs")
    check(gt_check["mae_mm"] <= 9.0, "Step 6 p95_abs_mm MAE is within 9mm of GT peak")
    check(gt_check["max_abs_error_mm"] <= 13.0, "Step 6 p95_abs_mm max error is within 13mm of GT peak")

    t0 = points[0]
    by_epoch = dict(zip(EPOCHS, points))
    crown = [crown_z_delta(t0, by_epoch[epoch]) for epoch in EPOCHS]
    crown_gt = [gt[(epoch, "crown_settlement")] for epoch in EPOCHS]
    assert_metric("crown_settlement", crown, crown_gt, tolerance_mm=4.0)

    sidewall = [sidewall_total_convergence_delta(t0, by_epoch[epoch]) for epoch in EPOCHS]
    sidewall_gt_total = [2.0 * gt[(epoch, "sidewall_convergence")] for epoch in EPOCHS]
    assert_metric("sidewall_total_convergence", sidewall, sidewall_gt_total, tolerance_mm=8.0)

    damage = [local_damage_delta(t0, by_epoch[epoch]) for epoch in EPOCHS]
    damage_gt = [gt[(epoch, "local_damage")] for epoch in EPOCHS]
    assert_metric("local_damage", damage, damage_gt, tolerance_mm=7.0)

    check(all(abs(crown[i]) <= abs(crown[i + 1]) + 1.0 for i in range(len(crown) - 1)), "crown settlement grows monotonically")
    check(abs(damage[2]) < 5.0 and damage[3] < -8.0, "local damage appears from T3")
    print("STEP 6 TIME-SERIES GROUND-TRUTH SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
