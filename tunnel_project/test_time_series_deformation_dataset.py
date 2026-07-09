# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import laspy

from tunnel_analysis.io_layer import BaseLayer

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


def band(points: np.ndarray, chainage: float, width: float = 1.0) -> np.ndarray:
    return np.abs(points[:, 1] - chainage) <= width


def crown_z_delta(t0: np.ndarray, tn: np.ndarray, chainage: float = 20.0) -> float:
    mask = band(t0, chainage)
    top = t0[:, 2] > np.percentile(t0[mask, 2], 82)
    mask = mask & top
    return float(np.median((tn[mask, 2] - t0[mask, 2]) * 1000.0))


def convergence_width_delta(t0: np.ndarray, tn: np.ndarray, chainage: float = 45.0) -> float:
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


def main() -> int:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    check(manifest["dataset"] == "time_series_deformation", "manifest dataset name")
    check(manifest["registration"]["synthetic_registered"] is True, "dataset is marked registered")
    check(manifest["epochs"] == EPOCHS, "manifest lists T0-T5")

    gt_rows = list(csv.DictReader((DATA / "ground_truth.csv").open(encoding="utf-8")))
    check(len(gt_rows) == 18, "ground truth has 6 epochs x 3 deformation rows")

    epoch_files, skipped = BaseLayer.discover_epoch_files(str(DATA))
    check([Path(fp).stem for fp in epoch_files] == EPOCHS, "epoch folder discovery sorts T0-T5")
    check("ground_truth.csv" in skipped, "epoch folder discovery reports skipped non-epoch files")

    points = {epoch: load_las(epoch) for epoch in EPOCHS}
    n0 = len(points["T0"])
    check(n0 > 10000, "T0 has enough points")
    check(all(len(points[epoch]) == n0 for epoch in EPOCHS), "all epochs have equal point count")

    crown = [crown_z_delta(points["T0"], points[epoch]) for epoch in EPOCHS]
    conv = [convergence_width_delta(points["T0"], points[epoch]) for epoch in EPOCHS]
    damage = [local_damage_delta(points["T0"], points[epoch]) for epoch in EPOCHS]

    check(abs(crown[0]) < 1.0, "T0 crown baseline is near zero")
    check(crown[-1] < -30.0, f"T5 crown settlement is detectable ({crown[-1]:.1f} mm)")
    check(all(crown[i] >= crown[i + 1] - 1.0 for i in range(len(crown) - 1)), "crown settlement grows monotonically")

    check(conv[-1] < -45.0, f"T5 width convergence is detectable ({conv[-1]:.1f} mm total width)")
    check(conv[1] > -5.0 and conv[2] < -5.0, "convergence starts around T2")

    check(abs(damage[2]) < 5.0, "local damage absent through T2")
    check(damage[3] < -8.0 and damage[-1] < -25.0, "local damage appears from T3 and grows")

    for name in ["baseline_pairs.csv", "incremental_pairs.csv", "README.md"]:
        check((DATA / name).exists(), f"{name} exists")

    print("TIME-SERIES DEFORMATION DATASET TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
