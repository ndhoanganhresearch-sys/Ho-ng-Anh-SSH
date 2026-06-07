# -*- coding: utf-8 -*-
r"""Generate a 2-station tunnel dataset WITH fixed sphere targets for testing
the target-based station-merging feature (Detect All -> Match -> Merge).

Pure NumPy — NO Blender needed. Each station is an independent sampling of the
SAME tunnel + the SAME 5 physical sphere targets, but station 2 is observed
from a DIFFERENT setup (rotation about the vertical Z axis + translation), so
its coordinate frame differs. Merging must bring station 2 onto station 1 via
the shared targets.

Output (data/station_merge_demo/):
  station_1.txt , station_2.txt   — 7-col: x y z nx ny nz intensity
                                     (targets = high intensity 0.95, lining 0.10)
  manifest.json , README.md

Run from tunnel_project:
    ..\.venv\Scripts\python.exe tools/create_station_merge_dataset.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "data" / "station_merge_demo"
RNG = np.random.default_rng(2024)

R       = 3.0      # tunnel radius (m)
LENGTH  = 30.0     # tunnel length along Y (m)
N_AXIAL = 160
M_RING  = 150
LINING_INTENSITY = 0.10
TARGET_INTENSITY = 0.95

# Fixed physical sphere targets (free space, inside the R=3 wall so the
# clusters stay distinct from the lining — mirrors the verified test setup).
TARGETS = np.array([
    [0.0,  5.0,  2.0],
    [1.5, 11.0, -1.0],
    [-1.5, 17.0, 1.2],
    [0.0, 23.0, -2.0],
    [1.0, 27.0,  1.5],
], dtype=np.float64)


def tunnel_points(seed):
    rng = np.random.default_rng(seed)
    ys = np.linspace(0.0, LENGTH, N_AXIAL)
    pts = []
    for y in ys:
        a = np.linspace(0, 2 * np.pi, M_RING, endpoint=False) + rng.uniform(-0.02, 0.02, M_RING)
        x = R * np.cos(a) + rng.normal(0, 0.004, M_RING)
        z = R * np.sin(a) + rng.normal(0, 0.004, M_RING)
        pts.append(np.column_stack([x, np.full(M_RING, y), z]))
    return np.vstack(pts)


def sphere_shell(center, radius=0.0725, n=90, seed=0):
    rng = np.random.default_rng(seed)
    u = rng.uniform(0, 1, n); v = rng.uniform(0, 1, n)
    th = 2 * np.pi * u; ph = np.arccos(2 * v - 1)
    d = np.column_stack([np.sin(ph) * np.cos(th), np.sin(ph) * np.sin(th), np.cos(ph)])
    return center + d * radius + rng.normal(0, 0.002, (n, 3))


def build_station(seed_offset):
    """Independent sampling of tunnel + the 5 fixed targets (in world frame)."""
    lining = tunnel_points(seed=seed_offset)
    parts = [lining]
    inten = [np.full(len(lining), LINING_INTENSITY)]
    for i, c in enumerate(TARGETS):
        sp = sphere_shell(c, n=90, seed=seed_offset * 100 + i)
        parts.append(sp)
        inten.append(np.full(len(sp), TARGET_INTENSITY))
    pts = np.vstack(parts)
    intensity = np.concatenate(inten)
    return pts, intensity


def rigid_z(yaw_deg, t):
    a = np.deg2rad(yaw_deg)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    T = np.eye(4); T[:3, :3] = Rz; T[:3, 3] = np.asarray(t, float)
    return T


def apply(T, p):
    return (T @ np.hstack([p, np.ones((len(p), 1))]).T).T[:, :3]


def save_txt(path, pts, intensity):
    # 7-col: x y z nx ny nz intensity  (normals = 0; loader reads col 7 as intensity)
    n = len(pts)
    arr = np.column_stack([pts, np.zeros((n, 3)), intensity])
    np.savetxt(path, arr, fmt="%.5f",
               header="x y z nx ny nz intensity", comments="# ")


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # Station 1 — reference frame.
    p1, i1 = build_station(seed_offset=1)

    # Station 2 — same tunnel + same physical targets, but observed from a
    # different setup: yaw 8 deg about Z + translation. Independent sampling.
    p2_world, i2 = build_station(seed_offset=2)
    T_setup = rigid_z(yaw_deg=8.0, t=(2.0, -1.3, 0.6))
    p2 = apply(T_setup, p2_world)

    save_txt(OUT / "station_1.txt", p1, i1)
    save_txt(OUT / "station_2.txt", p2, i2)

    manifest = {
        "dataset": "station_merge_demo",
        "created_by": "tools/create_station_merge_dataset.py (pure NumPy, no Blender)",
        "purpose": "Test target-based station merging: Detect All -> Match -> Merge.",
        "units": "meters",
        "columns": "x y z nx ny nz intensity",
        "tunnel": {"radius_m": R, "length_m": LENGTH, "axis": "Y"},
        "targets": {
            "count": int(len(TARGETS)),
            "type": "sphere (radius 0.0725 m, intensity 0.95)",
            "world_positions": TARGETS.tolist(),
        },
        "station_2_setup_transform": {
            "yaw_deg_about_Z": 8.0,
            "translation_m": [2.0, -1.3, 0.6],
            "note": "station_2 is in a DIFFERENT frame; merge aligns it onto station_1.",
        },
        "files": [
            {"name": "station_1.txt", "role": "reference station", "points": int(len(p1))},
            {"name": "station_2.txt", "role": "moving station (displaced)", "points": int(len(p2))},
        ],
        "how_to_test": [
            "1.1 Import station_1.txt",
            "1.3 Add scan station -> station_2.txt",
            "Targets panel: Detect All Stations -> Match -> Merge Stations",
            "Expect 5 matched targets and a clean merged cloud (RMSE ~ mm).",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Station Merge Demo (2 stations + 5 sphere targets)\n\n"
        "Pure-NumPy synthetic dataset for the target-based station-merging feature.\n\n"
        "- `station_1.txt` — reference station\n"
        "- `station_2.txt` — same tunnel + same physical targets, observed from a\n"
        "  different setup (yaw 8 deg about Z + translation 2.0/-1.3/0.6 m)\n\n"
        "Columns: `x y z nx ny nz intensity` (targets = intensity 0.95, lining 0.10).\n\n"
        "## How to test in the GUI\n"
        "1. **1.1 Import** -> `station_1.txt`\n"
        "2. **1.2 Add scan station** -> `station_2.txt`\n"
        "3. **Targets panel** -> Detect All Stations -> Match -> Merge Stations\n"
        "   Expect 5 matched sphere targets and a merged cloud aligned to mm.\n",
        encoding="utf-8")

    print(f"Wrote {OUT}")
    print(f"  station_1.txt: {len(p1):,} pts  (incl. {len(TARGETS)} targets)")
    print(f"  station_2.txt: {len(p2):,} pts  (displaced: yaw 8deg + translation)")
    print(f"  targets: {len(TARGETS)} sphere reflectors (intensity {TARGET_INTENSITY})")


if __name__ == "__main__":
    main()
