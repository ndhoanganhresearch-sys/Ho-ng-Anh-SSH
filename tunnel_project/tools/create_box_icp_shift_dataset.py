from pathlib import Path
import json
import math

import laspy
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "box_icp_shift"
RNG = np.random.default_rng(21)

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

YAW_DEG = 9.0
SHIFT = np.array([1.8, 7.5, 0.55])
NOISE = 0.003


def _rot_z(deg: float) -> np.ndarray:
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)

R = _rot_z(YAW_DEG)


def box_ring(y: float) -> np.ndarray:
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
    pts += RNG.normal(0, NOISE, pts.shape)
    return pts


def apply_rigid(pts: np.ndarray) -> np.ndarray:
    return (pts @ R.T) + SHIFT


def colors_for(n: int, base=(180, 190, 200)) -> np.ndarray:
    cols = np.tile(np.array(base, dtype=np.int16), (n, 1))
    jitter = RNG.integers(-12, 13, size=(n, 3))
    return np.clip(cols + jitter, 0, 255).astype(np.uint8)


def save_txt(path: Path, pts: np.ndarray, cols: np.ndarray) -> None:
    np.savetxt(path, np.column_stack([pts, cols]), fmt=["%.5f", "%.5f", "%.5f", "%d", "%d", "%d"])


def save_las(path: Path, pts: np.ndarray, cols: np.ndarray) -> None:
    hdr = laspy.LasHeader(point_format=2, version="1.2")
    hdr.scales = np.array([1e-5, 1e-5, 1e-5])
    hdr.offsets = np.array([0.0, 0.0, 0.0])
    las = laspy.LasData(header=hdr)
    las.x, las.y, las.z = pts[:, 0], pts[:, 1], pts[:, 2]
    las.intensity = np.full(len(pts), 100, dtype=np.uint16)
    las.red = cols[:, 0].astype(np.uint16) * 256
    las.green = cols[:, 1].astype(np.uint16) * 256
    las.blue = cols[:, 2].astype(np.uint16) * 256
    las.write(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = np.vstack([box_ring(float(y)) for y in RING_Y])
    tn = apply_rigid(t0.copy())

    # Add a few extra outliers only to Tn to stress ICP without breaking overlap.
    extra = np.column_stack([
        RNG.uniform(-1.8, 1.8, 120),
        RNG.uniform(-8.0, 8.0, 120),
        RNG.uniform(-1.5, 1.5, 120),
    ])
    tn = np.vstack([tn, extra])

    cols0 = colors_for(len(t0))
    cols1 = colors_for(len(tn), base=(190, 170, 150))
    save_txt(OUT / "T0_box_icp.txt", t0, cols0)
    save_txt(OUT / "Tn_box_icp.txt", tn, cols1)
    save_las(OUT / "T0_box_icp.las", t0, cols0)
    save_las(OUT / "Tn_box_icp.las", tn, cols1)

    manifest = {
        "dataset": "box_icp_shift",
        "created_by": "tools/create_box_icp_shift_dataset.py",
        "purpose": "Short centered box tunnel with a rigidly shifted Tn for ICP registration tests.",
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
        "icp_transform": {
            "yaw_deg": YAW_DEG,
            "shift_m": SHIFT.tolist(),
            "extra_outliers": 120,
        },
        "files": [
            {"name": "T0_box_icp.las / .txt", "role": "reference (clean)", "points": int(len(t0))},
            {"name": "Tn_box_icp.las / .txt", "role": "monitoring (rigidly shifted + outliers)", "points": int(len(tn))},
        ],
        "notes": [
            "LAS offsets are zero; the rigid shift is encoded in the Tn coordinates.",
            "This dataset is intended for ICP / register_epochs tests, not target-based matching.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Box ICP Shift Dataset\n\n"
        "Short centered box tunnel with a rigidly shifted Tn for ICP registration.\n\n"
        f"- Rigid transform: yaw {YAW_DEG} deg, shift {SHIFT.tolist()} m.\n"
        "- Use `T0_box_icp.las` / `.txt` as reference.\n"
        "- Use `Tn_box_icp.las` / `.txt` as monitoring.\n"
        "- LAS offsets are zero; the shift is in the point coordinates.\n"
        "- Designed to test ICP / register_epochs plus the rest of the pipeline.\n",
        encoding="utf-8",
    )
    print(f"saved {OUT}")
    print(f"T0={len(t0)} Tn={len(tn)}")
    print(f"T0 mean={t0.mean(axis=0)} Tn mean={tn.mean(axis=0)}")
    print(f"T0 span={np.ptp(t0, axis=0)} Tn span={np.ptp(tn, axis=0)}")


if __name__ == "__main__":
    main()
