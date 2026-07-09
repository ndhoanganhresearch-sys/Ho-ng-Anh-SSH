r"""Create non-raycast regular surface ground truth for the realistic tunnel model.

This mirrors the geometry/deformation model in
`create_blender_lidar_t0t5_realistic.py` but runs in normal Python and samples a
regular grid on the lining surface. Use it as the dense reference surface when
comparing against Blender raycast/TLS outputs.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import laspy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "blender_lidar_t0t5_realistic_regular"
EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
LENGTH = 96.0
CURVE_R = 420.0
RADIUS = 4.25
N_SECTIONS = 193
N_THETA = 256
HEADER = "x y z nx ny nz intensity label"
CROWN_MM = {"T0": 0.0, "T1": -5.0, "T2": -12.0, "T3": -21.0, "T4": -32.0, "T5": -48.0}
CONV_MM = {"T0": 0.0, "T1": -2.0, "T2": -8.0, "T3": -16.0, "T4": -27.0, "T5": -40.0}
LOCAL_MM = {"T0": 0.0, "T1": 0.0, "T2": 0.0, "T3": -14.0, "T4": -27.0, "T5": -43.0}
JOINT_MM = {"T0": 0.0, "T1": 1.5, "T2": 3.0, "T3": 5.0, "T4": 7.0, "T5": 9.0}


def centerline(s: float) -> np.ndarray:
    a = s / CURVE_R
    return np.array([CURVE_R * (1.0 - math.cos(a)), CURVE_R * math.sin(a), 0.002 * s], dtype=np.float64)


def tangent(s: float) -> np.ndarray:
    a = s / CURVE_R
    t = np.array([math.sin(a), math.cos(a), 0.002], dtype=np.float64)
    return t / np.linalg.norm(t)


def normal_right(s: float) -> np.ndarray:
    n = np.cross(tangent(s), np.array([0.0, 0.0, 1.0], dtype=np.float64))
    return n / np.linalg.norm(n)


def theta_delta(theta: float, theta0: float) -> float:
    return math.atan2(math.sin(theta - theta0), math.cos(theta - theta0))


def deformation(epoch: str, s: float, theta: float) -> tuple[float, float, float]:
    crown = CROWN_MM[epoch] / 1000.0
    conv = CONV_MM[epoch] / 1000.0
    local = LOCAL_MM[epoch] / 1000.0
    joint = JOINT_MM[epoch] / 1000.0
    crown_w = math.exp(-0.5 * ((s - 24.0) / 8.0) ** 2) * max(0.0, math.sin(theta)) ** 1.7
    conv_w = math.exp(-0.5 * ((s - 50.0) / 9.0) ** 2) * abs(math.cos(theta)) ** 1.4
    local_w = math.exp(-0.5 * ((s - 72.0) / 3.2) ** 2) * math.exp(-0.5 * (theta_delta(theta, math.radians(58.0)) / 0.22) ** 2)
    ring_w = math.exp(-0.5 * ((s - 60.0) / 11.0) ** 2) * (1.0 if int(s / 2.0) % 3 == 0 else 0.25)
    dx = -math.copysign(abs(conv) * conv_w, math.cos(theta))
    dz = crown * crown_w + local * local_w * math.sin(math.radians(58.0))
    dr = local * local_w + joint * ring_w * 0.35 * math.sin(theta * 2.0)
    return dx, dz, dr


def sample_epoch(epoch: str) -> np.ndarray:
    rows = []
    for s in np.linspace(0.0, LENGTH, N_SECTIONS):
        nr = normal_right(float(s))
        c = centerline(float(s))
        for theta in np.linspace(0.0, 2.0 * math.pi, N_THETA, endpoint=False):
            dx, dz, dr = deformation(epoch, float(s), float(theta))
            ring_groove = -0.018 if abs((s % 2.0) - 0.03) < 0.03 else 0.0
            seg_phase = math.degrees(theta) % 60.0
            seg_groove = -0.010 if min(seg_phase, 60.0 - seg_phase) < 1.1 else 0.0
            rough = 0.006 * math.sin(0.9 * s + 3.0 * theta) + 0.003 * math.sin(3.1 * s - 2.0 * theta)
            radius = RADIUS + dr + ring_groove + seg_groove + rough
            x_local = radius * math.cos(theta) + dx
            z_local = radius * math.sin(theta) + dz
            p = c + nr * x_local + np.array([0.0, 0.0, z_local], dtype=np.float64)
            n_local = nr * math.cos(theta) + np.array([0.0, 0.0, math.sin(theta)], dtype=np.float64)
            n_local = n_local / np.linalg.norm(n_local)
            intensity = 0.46 + 0.16 * max(0.0, n_local[2])
            rows.append([p[0], p[1], p[2], n_local[0], n_local[1], n_local[2], max(0.05, min(1.0, intensity)), 1])
    return np.asarray(rows, dtype=np.float64)


def write_las(txt_path: Path, arr: np.ndarray) -> None:
    pts = arr[:, :3]
    intensity = np.clip(arr[:, 6] * 65535, 0, 65535).astype(np.uint16)
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = np.array([1e-4, 1e-4, 1e-4])
    header.offsets = pts.min(axis=0)
    las = laspy.LasData(header)
    las.x = pts[:, 0]
    las.y = pts[:, 1]
    las.z = pts[:, 2]
    las.intensity = intensity
    las.classification = arr[:, 7].astype(np.uint8)
    las.red = intensity
    las.green = intensity
    las.blue = intensity
    las.write(str(txt_path.with_suffix(".las")))


def write_tables(out_dir: Path) -> None:
    with (out_dir / "ground_truth.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "crown_settlement_mm", "sidewall_convergence_mm", "local_damage_mm", "joint_offset_mm"])
        for epoch in EPOCHS:
            writer.writerow([epoch, CROWN_MM[epoch], CONV_MM[epoch], LOCAL_MM[epoch], JOINT_MM[epoch]])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(OUT_DIR))
    parser.add_argument("--skip-las", action="store_true")
    args = parser.parse_args()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    metas = []
    for epoch in EPOCHS:
        arr = sample_epoch(epoch)
        txt = out_dir / f"{epoch}_regular.txt"
        np.savetxt(txt, arr, fmt="%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.0f", header=HEADER, comments="# ")
        if not args.skip_las:
            write_las(txt, arr)
        metas.append({"time": epoch, "txt": txt.name, "las": txt.with_suffix(".las").name, "points": int(len(arr))})
    write_tables(out_dir)
    manifest = {
        "dataset": out_dir.name,
        "created_by": "tools/create_realistic_regular_groundtruth.py",
        "purpose": "Non-raycast regular surface ground truth for comparison with Blender raycast/TLS output.",
        "columns": HEADER,
        "curve_radius_m": CURVE_R,
        "length_m": LENGTH,
        "radius_m": RADIUS,
        "times": metas,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "out_dir": str(out_dir), "times": len(metas), "points_per_time": metas[0]["points"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
