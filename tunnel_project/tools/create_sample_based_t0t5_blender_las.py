r"""Create T0-T5 Step 6 data from a real sample point cloud and build a Blender scene.

This is the corrected generator for Step 6 testing:
- T0 is based on an existing sample point cloud from data/sample_pcd.
- T1-T5 are deformed copies of the same sample points.
- LAS/TXT keep the sample coverage; no raycasting is used.
- Blender MCP builds six point-cloud tunnel objects from the generated data.

Run from tunnel_project while Blender MCP listens on localhost:9876:
    ..\.venv\Scripts\python.exe tools\create_sample_based_t0t5_blender_las.py
"""

from __future__ import annotations

import argparse
import csv
import json
import socket
from pathlib import Path

import laspy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "sample_pcd" / "u-type_tunnel_0k630 cut_1.las"
DEFAULT_OUT = ROOT / "data" / "sample_based_blender_t0t5_step6"

EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
CROWN_MM = {"T0": 0.0, "T1": -4.0, "T2": -9.0, "T3": -16.0, "T4": -25.0, "T5": -36.0}
CONV_MM = {"T0": 0.0, "T1": -1.0, "T2": -4.0, "T3": -9.0, "T4": -15.0, "T5": -24.0}
LOCAL_MM = {"T0": 0.0, "T1": 0.0, "T2": 0.0, "T3": -8.0, "T4": -17.0, "T5": -30.0}
POSE_BIAS = {
    "T0": (0.000, 0.000, 0.000),
    "T1": (0.002, -0.003, 0.001),
    "T2": (-0.003, 0.002, -0.001),
    "T3": (0.004, 0.004, 0.001),
    "T4": (-0.005, -0.004, 0.002),
    "T5": (0.006, -0.005, 0.002),
}

BLENDER_CODE = r'''
import bpy
import json
from pathlib import Path

OUT_DIR = Path(r"__OUT_DIR__")
EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
COLORS = [(0.55,0.55,0.55,1), (0.25,0.55,0.90,1), (0.25,0.75,0.45,1), (0.95,0.65,0.25,1), (0.95,0.35,0.25,1), (0.75,0.20,0.20,1)]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

for idx, epoch in enumerate(EPOCHS):
    preview_path = OUT_DIR / f"{epoch}_preview.xyz"
    verts = []
    with preview_path.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip() or line.startswith('#'):
                continue
            x, y, z = map(float, line.split()[:3])
            verts.append((x + idx * 12.0, y, z))
    mesh = bpy.data.meshes.new(f"{epoch}_sample_pointcloud_mesh")
    mesh.from_pydata(verts, [], [])
    mesh.update()
    obj = bpy.data.objects.new(f"{epoch}_from_sample_pcd", mesh)
    bpy.context.collection.objects.link(obj)
    mat = bpy.data.materials.new(f"{epoch}_mat")
    mat.diffuse_color = COLORS[idx]
    obj.data.materials.append(mat)
    obj.show_name = True

bpy.ops.object.light_add(type='SUN', location=(20, -30, 25))
bpy.context.object.name = 'Sun_sample_based_T0T5'
bpy.ops.object.camera_add(location=(38, -38, 18), rotation=(1.2, 0, 0.72))
bpy.context.scene.camera = bpy.context.object
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / 'sample_based_blender_t0t5_step6.blend'))
print(json.dumps({'status': 'ok', 'blend': str(OUT_DIR / 'sample_based_blender_t0t5_step6.blend'), 'objects': len(EPOCHS)}, indent=2))
'''


def robust_center(points: np.ndarray) -> tuple[float, float]:
    return float(np.median(points[:, 0])), float(np.median(points[:, 2]))


def deform_points(points: np.ndarray, epoch: str, rng: np.random.Generator) -> np.ndarray:
    if epoch == "T0":
        return points.copy()
    out = points.copy()
    x0, z0 = robust_center(points)
    y_min = float(points[:, 1].min())
    y_span = max(1e-9, float(np.ptp(points[:, 1])))
    y_norm = (points[:, 1] - y_min) / y_span
    theta = np.arctan2(points[:, 2] - z0, points[:, 0] - x0)

    crown = CROWN_MM[epoch] / 1000.0
    conv = CONV_MM[epoch] / 1000.0
    local = LOCAL_MM[epoch] / 1000.0

    crown_w = np.exp(-0.5 * ((y_norm - 0.30) / 0.105) ** 2) * np.maximum(0.0, np.sin(theta)) ** 1.6
    side_w = np.exp(-0.5 * ((y_norm - 0.58) / 0.125) ** 2) * np.abs(np.cos(theta)) ** 1.3
    local_angle = np.arctan2(np.sin(theta - np.deg2rad(62.0)), np.cos(theta - np.deg2rad(62.0)))
    local_w = np.exp(-0.5 * ((y_norm - 0.78) / 0.060) ** 2) * np.exp(-0.5 * (local_angle / 0.25) ** 2)

    out[:, 2] += crown * crown_w + local * local_w
    out[:, 0] += -np.sign(points[:, 0] - x0) * abs(conv) * side_w
    out += rng.normal(0.0, 0.0005, out.shape)
    out += np.asarray(POSE_BIAS[epoch], dtype=np.float64)
    return out


def estimate_normals(points: np.ndarray) -> np.ndarray:
    x0, z0 = robust_center(points)
    normals = np.column_stack([points[:, 0] - x0, np.zeros(len(points)), points[:, 2] - z0])
    norm = np.linalg.norm(normals, axis=1)
    ok = norm > 1e-9
    normals[ok] /= norm[ok, None]
    normals[~ok] = np.array([0.0, 0.0, 1.0])
    return normals


def write_las(path: Path, points: np.ndarray, intensity: np.ndarray, labels: np.ndarray, source_header) -> None:
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = source_header.scales
    header.offsets = points.min(axis=0)
    las = laspy.LasData(header)
    las.x, las.y, las.z = points[:, 0], points[:, 1], points[:, 2]
    las.intensity = intensity.astype(np.uint16)
    las.classification = labels.astype(np.uint8)
    gray = np.clip(intensity, 0, 65535).astype(np.uint16)
    las.red = gray
    las.green = gray
    las.blue = gray
    las.write(str(path))


def write_txt(path: Path, points: np.ndarray, normals: np.ndarray, intensity: np.ndarray, labels: np.ndarray) -> None:
    arr = np.column_stack([points, normals, intensity.astype(np.float64) / 65535.0, labels])
    np.savetxt(
        path,
        arr,
        fmt=["%.5f", "%.5f", "%.5f", "%.6f", "%.6f", "%.6f", "%.6f", "%d"],
        header="x y z nx ny nz intensity label",
        comments="# ",
    )


def write_preview(path: Path, points: np.ndarray, max_points: int) -> None:
    step = max(1, int(np.ceil(len(points) / max_points)))
    preview = points[::step]
    np.savetxt(path, preview[:, :3], fmt="%.5f %.5f %.5f")


def send_blender_command(command_type: str, params: dict, host: str, port: int, timeout: float = 600.0) -> dict:
    payload = {"type": command_type, "params": params}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.sendall(json.dumps(payload).encode("utf-8"))
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(8192)
            if not chunk:
                break
            chunks.append(chunk)
            data = b"".join(chunks)
            try:
                return json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                continue
    raise RuntimeError("No complete JSON response received from Blender MCP")


def write_tables(out_dir: Path) -> None:
    with (out_dir / "ground_truth.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "crown_settlement_mm", "sidewall_convergence_mm", "local_damage_mm"])
        for epoch in EPOCHS:
            w.writerow([epoch, CROWN_MM[epoch], CONV_MM[epoch], LOCAL_MM[epoch]])
    with (out_dir / "baseline_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "crown_delta_mm", "sidewall_delta_mm", "local_delta_mm"])
        for epoch in EPOCHS[1:]:
            w.writerow([f"T0-{epoch}", CROWN_MM[epoch], CONV_MM[epoch], LOCAL_MM[epoch]])
    with (out_dir / "incremental_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "crown_increment_mm", "sidewall_increment_mm", "local_increment_mm"])
        for a, b in zip(EPOCHS[:-1], EPOCHS[1:]):
            w.writerow([f"{a}-{b}", CROWN_MM[b] - CROWN_MM[a], CONV_MM[b] - CONV_MM[a], LOCAL_MM[b] - LOCAL_MM[a]])


def write_readme(out_dir: Path, source: Path, points: int, preview_points: int) -> None:
    text = f"""# Sample-Based Blender T0-T5 Step 6 Dataset

This is based on the real sample point cloud, not a procedural tunnel.

## Source

- Source point cloud: `{source}`
- Points per LAS epoch: `{points:,}`
- Blender preview points per epoch: up to `{preview_points:,}`

## Method

1. Use the sample point cloud as T0.
2. Create T1-T5 by applying controlled Step 6 deformation to the same sample points.
3. Export LAS/TXT for the tool.
4. Use Blender MCP to create six point-cloud tunnel objects from preview samples for visual inspection.
5. No raycasting is used.

## Ground truth

- Crown settlement: 0 to -36 mm
- Sidewall convergence: 0 to -24 mm
- Local damage: starts at T3 and reaches -30 mm

## Test

Load `T0.las` as reference, add `T1.las` to `T5.las`, then run Step 6.
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--max-points", type=int, default=0, help="Optional downsample for LAS; 0 keeps all source points")
    parser.add_argument("--preview-points", type=int, default=80_000, help="Max points per epoch imported into Blender scene")
    parser.add_argument("--skip-blender", action="store_true")
    args = parser.parse_args()

    source = Path(args.source)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    las = laspy.read(source)
    points = np.column_stack([np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)]).astype(np.float64)
    intensity = np.asarray(las.intensity, dtype=np.uint16)
    if int(intensity.max()) == 0:
        z_scaled = (points[:, 2] - points[:, 2].min()) / max(1e-9, np.ptp(points[:, 2]))
        intensity = np.clip((0.35 + 0.45 * z_scaled) * 65535, 0, 65535).astype(np.uint16)
    labels = np.ones(len(points), dtype=np.uint8)

    if args.max_points and len(points) > args.max_points:
        step = int(np.ceil(len(points) / args.max_points))
        idx = np.arange(0, len(points), step)
        points = points[idx]
        intensity = intensity[idx]
        labels = labels[idx]

    rng = np.random.default_rng(20260629)
    epoch_meta = []
    for epoch in EPOCHS:
        epoch_points = deform_points(points, epoch, rng)
        normals = estimate_normals(epoch_points)
        write_las(out_dir / f"{epoch}.las", epoch_points, intensity, labels, las.header)
        write_txt(out_dir / f"{epoch}.txt", epoch_points, normals, intensity, labels)
        write_preview(out_dir / f"{epoch}_preview.xyz", epoch_points, args.preview_points)
        meta = {
            "epoch": epoch,
            "las_file": f"{epoch}.las",
            "txt_file": f"{epoch}.txt",
            "preview_file": f"{epoch}_preview.xyz",
            "points": int(len(epoch_points)),
            "source": str(source),
            "bounds_min": epoch_points.min(axis=0).tolist(),
            "bounds_max": epoch_points.max(axis=0).tolist(),
            "deformation_mm": {
                "crown_settlement": CROWN_MM[epoch],
                "sidewall_convergence": CONV_MM[epoch],
                "local_damage": LOCAL_MM[epoch],
            },
        }
        (out_dir / f"{epoch}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        epoch_meta.append(meta)

    write_tables(out_dir)
    write_readme(out_dir, source, len(points), args.preview_points)
    manifest = {
        "dataset": out_dir.name,
        "created_by": "tools/create_sample_based_t0t5_blender_las.py",
        "source": str(source),
        "method": "sample point cloud deformation + Blender MCP preview scene; no raycasting",
        "points_per_epoch": int(len(points)),
        "las_files": [f"T{i}.las" for i in range(6)],
        "txt_files": [f"T{i}.txt" for i in range(6)],
        "preview_files": [f"T{i}_preview.xyz" for i in range(6)],
        "epochs": epoch_meta,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if not args.skip_blender:
        code = BLENDER_CODE.replace("__OUT_DIR__", str(out_dir.resolve()).replace("\\", "\\\\"))
        response = send_blender_command("execute_code", {"code": code}, args.host, args.port)
        if response.get("status") != "success":
            print(json.dumps(response, indent=2, ensure_ascii=False))
            return 1
        print(json.dumps(response.get("result", response), indent=2, ensure_ascii=False))

    print(f"Dataset written to: {out_dir}")
    print(f"Points per LAS epoch: {len(points):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
