"""Create a short centered box-tunnel dataset with four spaced defects.

Outputs data/box_four_spots/:
  - T0_box_short.txt / .las
  - Tn_box_short.txt / .las
  - manifest.json, README.md

The cross-section aspect follows data/sample_pcd/box_tunnel_dw.las more closely
(wider than tall) so detect_profile() classifies it as Box. Coordinates stay
near the origin and LAS offsets are zero to avoid offset/centering artifacts.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import laspy
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "box_four_spots"
RNG = np.random.default_rng(7)

LENGTH = 120.0
WIDTH = 6.4
HEIGHT = 4.1
HALF_W = WIDTH / 2
HALF_H = HEIGHT / 2
RING_COUNT = 121
EDGE_COUNT = 72

RING_Y = np.linspace(-LENGTH / 2, LENGTH / 2, RING_COUNT)
EDGE_X = np.linspace(-HALF_W, HALF_W, EDGE_COUNT)
EDGE_Z = np.linspace(-HALF_H, HALF_H, EDGE_COUNT)

TARGET_CHAINAGES = [-50.0, -25.0, 0.0, 25.0, 50.0]
TARGET_RADIUS = 0.0725

DEFECTS = [
    {"chainage_m": -30.0, "type": "crown settlement", "crown_mm": -45.0},
    {"chainage_m": -10.0, "type": "sidewall convergence", "per_side_mm": -35.0},
    {"chainage_m": 14.0, "type": "noise (cable + outliers)", "cable_pts": 96, "outlier_pts": 24},
    {"chainage_m": 34.0, "type": "clearance intrusion", "intruder_pts": 20, "intruder_offset_m": [1.09, 34.0, 1.60]},
]


def _gauss(y: float, center: float, sigma: float) -> float:
    return math.exp(-0.5 * ((y - center) / sigma) ** 2)


def box_ring(y: float, deform: bool = False) -> np.ndarray:
    pts = []
    for x in EDGE_X:
        pts.append([x, y, -HALF_H])
    for z in EDGE_Z[1:]:
        pts.append([HALF_W, y, z])
    for x in EDGE_X[-2::-1]:
        pts.append([x, y, HALF_H])
    for z in EDGE_Z[-2:0:-1]:
        pts.append([-HALF_W, y, z])
    pts = np.asarray(pts, dtype=np.float64)
    pts += RNG.normal(0, 0.0025, pts.shape)

    if not deform:
        return pts

    g1 = _gauss(y, -30.0, 5.0)
    g2 = _gauss(y, -10.0, 5.0)
    g4 = _gauss(y, 34.0, 4.5)

    crown_mask = pts[:, 2] > 0.7 * HALF_H
    pts[crown_mask, 2] += -0.045 * g1

    left_mask = pts[:, 0] < -0.7 * HALF_W
    right_mask = pts[:, 0] > 0.7 * HALF_W
    pts[left_mask, 0] -= 0.018 * g2
    pts[right_mask, 0] += 0.018 * g2

    invert_mask = pts[:, 2] < -0.7 * HALF_H
    pts[invert_mask, 2] += 0.012 * g4
    return pts


def hazard_clutter() -> np.ndarray:
    # Added once, not per ring, so the monitoring cloud stays centered.
    cable_x = np.linspace(-1.2, 1.2, 96)
    cable = np.column_stack([cable_x, np.full_like(cable_x, 14.0), np.full_like(cable_x, HALF_H * 0.52)])
    cable += RNG.normal(0, 0.02, cable.shape)
    outliers = np.column_stack([
        RNG.uniform(-1.8, 1.8, 24),
        RNG.uniform(13.0, 15.0, 24),
        RNG.uniform(-1.4, 1.4, 24),
    ])
    intruder = np.array([HALF_W * 0.17, 34.0, HALF_H * 0.78])
    intruders = intruder + RNG.normal(0, 0.025, (20, 3))
    return np.vstack([cable, outliers, intruders])


def target_spheres() -> np.ndarray:
    pts = []
    # Fibonacci-like sphere samples, fixed targets in both epochs.
    n = 720
    k = np.arange(n, dtype=np.float64)
    phi = np.arccos(1.0 - 2.0 * (k + 0.5) / n)
    theta = np.pi * (1.0 + 5.0 ** 0.5) * k
    sphere = np.column_stack([
        TARGET_RADIUS * np.cos(theta) * np.sin(phi),
        TARGET_RADIUS * np.sin(theta) * np.sin(phi),
        TARGET_RADIUS * np.cos(phi),
    ])
    for y in TARGET_CHAINAGES:
        center = np.array([18.0, y, 0.0])
        pts.append(center + sphere + RNG.normal(0, 0.001, sphere.shape))
    return np.vstack(pts)


def colors_for(n: int, base=(180, 190, 200)) -> np.ndarray:
    cols = np.tile(np.array(base, dtype=np.int16), (n, 1))
    jitter = RNG.integers(-12, 13, size=(n, 3))
    return np.clip(cols + jitter, 0, 255).astype(np.uint8)


def save_txt(path: Path, pts: np.ndarray, cols: np.ndarray) -> None:
    arr = np.column_stack([pts, cols])
    np.savetxt(path, arr, fmt=["%.5f", "%.5f", "%.5f", "%d", "%d", "%d"])


def save_las(path: Path, pts: np.ndarray, cols: np.ndarray, intensity: np.ndarray | None = None) -> None:
    hdr = laspy.LasHeader(point_format=2, version="1.2")
    hdr.scales = np.array([1e-5, 1e-5, 1e-5])
    hdr.offsets = np.array([0.0, 0.0, 0.0])
    las = laspy.LasData(header=hdr)
    las.x = pts[:, 0]
    las.y = pts[:, 1]
    las.z = pts[:, 2]
    if intensity is None:
        intensity = np.full(len(pts), 100, dtype=np.uint16)
    las.intensity = intensity.astype(np.uint16)
    las.red = cols[:, 0].astype(np.uint16) * 256
    las.green = cols[:, 1].astype(np.uint16) * 256
    las.blue = cols[:, 2].astype(np.uint16) * 256
    las.write(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = np.vstack([box_ring(float(y), deform=False) for y in RING_Y])
    tn = np.vstack([np.vstack([box_ring(float(y), deform=True) for y in RING_Y]), hazard_clutter()])

    cols0 = colors_for(len(t0))
    cols1 = colors_for(len(tn), base=(190, 170, 150))
    inten0 = np.full(len(t0), 100, dtype=np.uint16)
    inten1 = np.full(len(tn), 100, dtype=np.uint16)

    save_txt(OUT / "T0_box_short.txt", t0, cols0)
    save_txt(OUT / "Tn_box_short.txt", tn, cols1)
    save_las(OUT / "T0_box_short.las", t0, cols0, inten0)
    save_las(OUT / "Tn_box_short.las", tn, cols1, inten1)

    manifest = {
        "dataset": "box_four_spots",
        "created_by": "tools/create_box_four_spots_dataset.py",
        "purpose": "Short centered box-tunnel dataset with 4 evenly spaced defect spots for full-feature testing.",
        "units": "meters",
        "columns": "x y z r g b",
        "geometry": {
            "shape": "box",
            "centered": True,
            "width_m": WIDTH,
            "height_m": HEIGHT,
            "length_m": LENGTH,
            "axis": "Y / chainage",
        },
        "defect_spots": DEFECTS,
        "files": [
            {"name": "T0_box_short.las / .txt", "role": "reference (clean)", "points": int(len(t0))},
            {"name": "Tn_box_short.las / .txt", "role": "monitoring (4 defects)", "points": int(len(tn))},
        ],
        "las": {"version": "1.2", "point_format": 2, "scales": [1e-5, 1e-5, 1e-5], "offsets": [0.0, 0.0, 0.0]},
        "notes": [
            "Coordinates are centered near the origin to avoid LAS offset/precision issues.",
            "T0 and Tn exercise import, cleaning, sections, Step 6, warnings, and export; use full_test for target registration.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Box Short Test Dataset\n\n"
        "Centered box-shaped tunnel dataset with 4 evenly spaced defect spots.\n\n"
        "- Use `T0_box_short.las` / `.txt` as reference.\n"
        "- Use `Tn_box_short.las` / `.txt` as monitoring.\n"
        "- Coordinates are centered near the origin and LAS offsets are zero.\n"
        "- Designed to exercise import, clean-noise, sections, Step 6, warnings, and export. Use `full_test` for target registration.\n",
        encoding="utf-8",
    )
    print(f"saved {OUT}")
    print(f"T0={len(t0)} Tn={len(tn)}")
    print(f"T0 mean={t0.mean(axis=0)} Tn mean={tn.mean(axis=0)}")
    print(f"T0 span={np.ptp(t0, axis=0)} Tn span={np.ptp(tn, axis=0)}")


if __name__ == "__main__":
    main()
