# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent.parent / "data" / "time_series_deformation"

RADIUS = 3.0
LENGTH = 80.0
GRADE = 0.001
RING_DS = 0.50
POINTS_PER_RING = 96
NOISE_M = 0.002
LABEL_LINING = 1

EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]

CROWN_MM = {
    "T0": 0.0,
    "T1": -5.0,
    "T2": -12.0,
    "T3": -20.0,
    "T4": -30.0,
    "T5": -45.0,
}
CONVERGENCE_MM = {
    "T0": 0.0,
    "T1": 0.0,
    "T2": -5.0,
    "T3": -12.0,
    "T4": -22.0,
    "T5": -35.0,
}
LOCAL_DAMAGE_MM = {
    "T0": 0.0,
    "T1": 0.0,
    "T2": 0.0,
    "T3": -15.0,
    "T4": -25.0,
    "T5": -40.0,
}

DEFORMATION_SPECS = [
    {
        "type": "crown_settlement",
        "chainage_m": 20.0,
        "sigma_m": 3.0,
        "theta_deg": 90.0,
        "values_mm": CROWN_MM,
        "description": "Progressive upper/crown deflection",
    },
    {
        "type": "sidewall_convergence",
        "chainage_m": 45.0,
        "sigma_m": 3.0,
        "theta_deg": 0.0,
        "values_mm": CONVERGENCE_MM,
        "description": "Progressive bilateral sidewall convergence",
    },
    {
        "type": "local_damage",
        "chainage_m": 65.0,
        "sigma_m": 1.2,
        "theta_deg": 55.0,
        "values_mm": LOCAL_DAMAGE_MM,
        "description": "Small localized lining damage patch",
    },
]


def centerline(chainage: np.ndarray) -> np.ndarray:
    return np.column_stack([
        0.15 * np.sin(chainage / LENGTH * np.pi),
        chainage,
        GRADE * chainage,
    ])


def angle_delta(a: np.ndarray, b: float) -> np.ndarray:
    return np.arctan2(np.sin(a - b), np.cos(a - b))


def base_lining() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(20260613)
    chainages = np.arange(0.0, LENGTH + RING_DS, RING_DS)
    pts = []
    theta_values = []
    chainage_values = []
    for chainage in chainages:
        theta = np.linspace(0.0, 2.0 * np.pi, POINTS_PER_RING, endpoint=False)
        theta = theta + rng.normal(0.0, 0.0035, POINTS_PER_RING)
        radius = RADIUS + rng.normal(0.0, NOISE_M, POINTS_PER_RING)
        center = centerline(np.array([chainage]))[0]
        x = center[0] + radius * np.cos(theta)
        y = center[1] + rng.normal(0.0, 0.001, POINTS_PER_RING)
        z = center[2] + radius * np.sin(theta)
        pts.append(np.column_stack([x, y, z]))
        theta_values.append(theta)
        chainage_values.append(np.full(POINTS_PER_RING, chainage))
    return np.vstack(pts), np.concatenate(chainage_values), np.concatenate(theta_values)


def apply_deformation(points: np.ndarray, chainage: np.ndarray, theta: np.ndarray, epoch: str) -> np.ndarray:
    deformed = points.copy()
    for spec in DEFORMATION_SPECS:
        value_mm = float(spec["values_mm"][epoch])
        if abs(value_mm) < 1e-12:
            continue
        chain_w = np.exp(-0.5 * ((chainage - spec["chainage_m"]) / spec["sigma_m"]) ** 2)
        theta0 = np.deg2rad(float(spec["theta_deg"]))
        if spec["type"] == "crown_settlement":
            theta_w = np.maximum(0.0, np.sin(theta))
            move = value_mm / 1000.0 * chain_w * theta_w
            deformed[:, 2] += move
        elif spec["type"] == "sidewall_convergence":
            side_w = np.abs(np.cos(theta))
            move = abs(value_mm) / 1000.0 * chain_w * side_w
            deformed[:, 0] -= np.sign(np.cos(theta)) * move
        elif spec["type"] == "local_damage":
            theta_w = np.exp(-0.5 * (angle_delta(theta, theta0) / 0.28) ** 2)
            move = value_mm / 1000.0 * chain_w * theta_w
            deformed[:, 0] += move * np.cos(theta0)
            deformed[:, 2] += move * np.sin(theta0)
    return deformed


def save_txt(path: Path, pts: np.ndarray, intensity: np.ndarray, label: np.ndarray) -> None:
    arr = np.column_stack([pts, np.zeros((len(pts), 3)), intensity, label])
    np.savetxt(path, arr, fmt=["%.4f"] * 7 + ["%d"], header="x y z nx ny nz intensity label", comments="# ")


def save_las(path: Path, pts: np.ndarray, intensity: np.ndarray, label: np.ndarray) -> None:
    import laspy

    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = np.array([1e-3, 1e-3, 1e-3])
    header.offsets = pts.min(axis=0)
    las = laspy.LasData(header=header)
    las.x, las.y, las.z = pts[:, 0], pts[:, 1], pts[:, 2]
    las.intensity = np.clip(intensity * 65535, 0, 65535).astype(np.uint16)
    color = np.full(len(pts), 43000, dtype=np.uint16)
    las.red, las.green, las.blue = color, color, color
    las.classification = np.asarray(label, dtype=np.uint8)
    las.write(str(path))


def write_ground_truth(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for epoch in EPOCHS:
        for spec in DEFORMATION_SPECS:
            rows.append({
                "epoch": epoch,
                "chainage_m": spec["chainage_m"],
                "deformation_type": spec["type"],
                "value_mm": spec["values_mm"][epoch],
                "sigma_m": spec["sigma_m"],
                "theta_deg": spec["theta_deg"],
                "description": spec["description"],
            })
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_pair_tables(out: Path) -> None:
    baseline = []
    incremental = []
    for i, epoch in enumerate(EPOCHS[1:], start=1):
        prev = EPOCHS[i - 1]
        baseline.append({
            "pair": f"T0-{epoch}",
            "crown_accumulated_mm": CROWN_MM[epoch] - CROWN_MM["T0"],
            "convergence_accumulated_mm": CONVERGENCE_MM[epoch] - CONVERGENCE_MM["T0"],
            "local_damage_accumulated_mm": LOCAL_DAMAGE_MM[epoch] - LOCAL_DAMAGE_MM["T0"],
        })
        incremental.append({
            "pair": f"{prev}-{epoch}",
            "crown_delta_mm": CROWN_MM[epoch] - CROWN_MM[prev],
            "convergence_delta_mm": CONVERGENCE_MM[epoch] - CONVERGENCE_MM[prev],
            "local_damage_delta_mm": LOCAL_DAMAGE_MM[epoch] - LOCAL_DAMAGE_MM[prev],
        })
    for name, rows in [("baseline_pairs.csv", baseline), ("incremental_pairs.csv", incremental)]:
        with (out / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base, chainage, theta = base_lining()
    intensity = np.full(len(base), 0.12)
    label = np.full(len(base), LABEL_LINING)

    files = []
    for epoch in EPOCHS:
        pts = apply_deformation(base, chainage, theta, epoch)
        save_txt(OUT / f"{epoch}.txt", pts, intensity, label)
        save_las(OUT / f"{epoch}.las", pts, intensity, label)
        files.append({"epoch": epoch, "las": f"{epoch}.las", "txt": f"{epoch}.txt", "points": int(len(pts))})

    gt_rows = write_ground_truth(OUT / "ground_truth.csv")
    write_pair_tables(OUT)

    manifest = {
        "dataset": "time_series_deformation",
        "purpose": "Clean registered T0-T5 synthetic tunnel deformation dataset for time-series analysis.",
        "units": "meters; deformation values in ground_truth.csv are millimeters",
        "registration": {"synthetic_registered": True, "transform": "identity", "rmse_mm": 0.0},
        "tunnel": {"length_m": LENGTH, "radius_m": RADIUS, "ring_spacing_m": RING_DS, "points_per_ring": POINTS_PER_RING},
        "epochs": EPOCHS,
        "files": files,
        "deformation_specs": DEFORMATION_SPECS,
        "outputs": ["ground_truth.csv", "baseline_pairs.csv", "incremental_pairs.csv"],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Time-Series Deformation Dataset T0-T5\n\n"
        "Clean synthetic dataset for validating time-series deformation analysis. All epochs are already registered.\n\n"
        "## Files\n"
        "- `T0.las` ... `T5.las`: six monitoring epochs.\n"
        "- `ground_truth.csv`: absolute deformation value at each epoch.\n"
        "- `baseline_pairs.csv`: accumulated deformation from T0 to Tn.\n"
        "- `incremental_pairs.csv`: deformation increment from Tn to Tn+1.\n"
        "- `manifest.json`: machine-readable metadata.\n\n"
        "## Ground Truth\n"
        "- Crown settlement at chainage 20 m grows from 0 to -45 mm.\n"
        "- Sidewall convergence at chainage 45 m grows from 0 to -35 mm.\n"
        "- Local damage at chainage 65 m appears from T3 and grows to -40 mm.\n\n"
        "## Suggested Tool Workflow\n"
        "1. Load a pair such as `T0.las` and `T5.las`.\n"
        "2. Registration may be skipped or treated as identity for this clean dataset.\n"
        "3. Run parameter/section/deformation analysis.\n"
        "4. Compare output with `ground_truth.csv`.\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(OUT), "epochs": len(EPOCHS), "points_per_epoch": int(len(base)), "ground_truth_rows": len(gt_rows)}, indent=2))


if __name__ == "__main__":
    main()
