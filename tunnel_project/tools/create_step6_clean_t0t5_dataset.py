r"""Create a clean synthetic T0-T5 deformation dataset for Step 6.

Scope:
- no raycasting;
- no scanner simulation;
- all epochs are pre-registered in the same coordinate system;
- deformation includes upper/crown deflection and local damage;
- outputs LAS/TXT, ground-truth CSVs, manifest, README, and optional Blender preview.

Run from tunnel_project:
    ..\.venv\Scripts\python.exe tools\create_step6_clean_t0t5_dataset.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import socket
from pathlib import Path

import laspy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "step6_clean_t0t5_deformation"
EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
LENGTH_M = 80.0
RADIUS_M = 3.0
N_CHAINAGE = 620
N_THETA = 256
LABEL_LINING = 1

UPPER_DEFLECTION_MM = {"T0": 0.0, "T1": -5.0, "T2": -12.0, "T3": -20.0, "T4": -30.0, "T5": -45.0}
LOCAL_DAMAGE_MM = {"T0": 0.0, "T1": 0.0, "T2": 0.0, "T3": -15.0, "T4": -25.0, "T5": -40.0}

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
    verts = []
    faces = []
    meta = json.loads((OUT_DIR / f"{epoch}_mesh.json").read_text(encoding='utf-8'))
    n_chain = meta['n_chainage']
    n_theta = meta['n_theta']
    with (OUT_DIR / f"{epoch}_vertices.xyz").open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            x, y, z = map(float, line.split()[:3])
            verts.append((x + idx * 8.0, y, z))
    for i in range(n_chain - 1):
        for j in range(n_theta):
            a = i * n_theta + j
            b = i * n_theta + (j + 1) % n_theta
            c = (i + 1) * n_theta + (j + 1) % n_theta
            d = (i + 1) * n_theta + j
            faces.append((a, b, c, d))
    mesh = bpy.data.meshes.new(f"{epoch}_clean_step6_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"{epoch}_clean_step6_tunnel", mesh)
    bpy.context.collection.objects.link(obj)
    mat = bpy.data.materials.new(f"{epoch}_material")
    mat.diffuse_color = COLORS[idx]
    obj.data.materials.append(mat)
    obj.show_name = True
    bpy.ops.object.text_add(location=(idx * 8.0, -4.0, 4.0), rotation=(1.2, 0, 0))
    txt = bpy.context.view_layer.objects.active
    txt.name = f"{epoch}_label"
    txt.data.body = epoch
    txt.data.size = 0.8

bpy.ops.object.light_add(type='SUN', location=(20, -30, 30))
bpy.context.view_layer.objects.active.name = 'Sun_clean_step6'
bpy.ops.object.camera_add(location=(24, -38, 16), rotation=(1.18, 0, 0.45))
bpy.context.scene.camera = bpy.context.view_layer.objects.active
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / 'step6_clean_t0t5_preview.blend'))
print(json.dumps({'status': 'ok', 'blend': str(OUT_DIR / 'step6_clean_t0t5_preview.blend')}, indent=2))
'''


def centerline(chainage: np.ndarray) -> np.ndarray:
    x = 0.12 * np.sin(2.0 * np.pi * chainage / LENGTH_M)
    y = chainage
    z = 0.0015 * chainage
    return np.column_stack([x, y, z])


def angle_delta(theta: np.ndarray, theta0: float) -> np.ndarray:
    return np.arctan2(np.sin(theta - theta0), np.cos(theta - theta0))


def base_surface() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    chainages = np.linspace(0.0, LENGTH_M, N_CHAINAGE)
    thetas = np.linspace(0.0, 2.0 * np.pi, N_THETA, endpoint=False)
    cc, tt = np.meshgrid(chainages, thetas, indexing="ij")
    # Fixed construction texture exists in all epochs, so it is not deformation.
    texture = 0.004 * np.sin(2.0 * np.pi * cc / 2.0) + 0.002 * np.sin(6.0 * tt)
    radius = RADIUS_M + texture
    c = centerline(cc.ravel())
    x = c[:, 0] + radius.ravel() * np.cos(tt.ravel())
    y = c[:, 1]
    z = c[:, 2] + radius.ravel() * np.sin(tt.ravel())
    pts = np.column_stack([x, y, z]).astype(np.float64)
    normals = np.column_stack([np.cos(tt.ravel()), np.zeros(tt.size), np.sin(tt.ravel())]).astype(np.float64)
    return pts, normals, cc.ravel(), tt.ravel()


def apply_deformation(points: np.ndarray, chainage: np.ndarray, theta: np.ndarray, epoch: str) -> np.ndarray:
    out = points.copy()
    upper_mm = UPPER_DEFLECTION_MM[epoch]
    local_mm = LOCAL_DAMAGE_MM[epoch]
    upper_w = np.exp(-0.5 * ((chainage - 20.0) / 4.0) ** 2) * np.maximum(0.0, np.sin(theta)) ** 1.6
    local_w = np.exp(-0.5 * ((chainage - 65.0) / 1.8) ** 2) * np.exp(-0.5 * (angle_delta(theta, np.deg2rad(55.0)) / 0.22) ** 2)
    out[:, 2] += (upper_mm / 1000.0) * upper_w
    out[:, 0] += (local_mm / 1000.0) * local_w * np.cos(np.deg2rad(55.0))
    out[:, 2] += (local_mm / 1000.0) * local_w * np.sin(np.deg2rad(55.0))
    return out


def intensity_from_theta(theta: np.ndarray) -> np.ndarray:
    values = 0.45 + 0.22 * np.maximum(0.0, np.sin(theta)) + 0.05 * np.cos(3.0 * theta)
    return np.clip(values * 65535, 0, 65535).astype(np.uint16)


def write_las(path: Path, points: np.ndarray, intensity: np.ndarray) -> None:
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = np.array([1e-4, 1e-4, 1e-4])
    header.offsets = points.min(axis=0)
    las = laspy.LasData(header)
    las.x = points[:, 0]
    las.y = points[:, 1]
    las.z = points[:, 2]
    las.intensity = intensity
    las.classification = np.full(len(points), LABEL_LINING, dtype=np.uint8)
    las.red = intensity
    las.green = intensity
    las.blue = intensity
    las.write(str(path))


def write_txt(path: Path, points: np.ndarray, normals: np.ndarray, intensity: np.ndarray) -> None:
    arr = np.column_stack([points, normals, intensity.astype(np.float64) / 65535.0, np.full(len(points), LABEL_LINING)])
    np.savetxt(path, arr, fmt=["%.5f", "%.5f", "%.5f", "%.6f", "%.6f", "%.6f", "%.6f", "%d"], header="x y z nx ny nz intensity label", comments="# ")


def write_tables(out_dir: Path) -> None:
    with (out_dir / "ground_truth.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["epoch", "upper_deflection_mm", "local_damage_mm"])
        for epoch in EPOCHS:
            writer.writerow([epoch, UPPER_DEFLECTION_MM[epoch], LOCAL_DAMAGE_MM[epoch]])
    with (out_dir / "baseline_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pair", "upper_delta_mm", "local_delta_mm"])
        for epoch in EPOCHS[1:]:
            writer.writerow([f"T0-{epoch}", UPPER_DEFLECTION_MM[epoch], LOCAL_DAMAGE_MM[epoch]])
    with (out_dir / "incremental_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pair", "upper_increment_mm", "local_increment_mm"])
        for a, b in zip(EPOCHS[:-1], EPOCHS[1:]):
            writer.writerow([f"{a}-{b}", UPPER_DEFLECTION_MM[b] - UPPER_DEFLECTION_MM[a], LOCAL_DAMAGE_MM[b] - LOCAL_DAMAGE_MM[a]])


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


def build_blender_preview(out_dir: Path, host: str, port: int) -> None:
    code = BLENDER_CODE.replace("__OUT_DIR__", str(out_dir.resolve()).replace("\\", "\\\\"))
    response = send_blender_command("execute_code", {"code": code}, host, port)
    if response.get("status") != "success":
        raise RuntimeError(json.dumps(response, indent=2, ensure_ascii=False))
    print(json.dumps(response.get("result", response), indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(OUT_DIR))
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--skip-blender", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    base_points, normals, chainage, theta = base_surface()
    intensity = intensity_from_theta(theta)
    epoch_meta = []
    for epoch in EPOCHS:
        points = apply_deformation(base_points, chainage, theta, epoch)
        write_las(out_dir / f"{epoch}.las", points, intensity)
        write_txt(out_dir / f"{epoch}.txt", points, normals, intensity)
        np.savetxt(out_dir / f"{epoch}_vertices.xyz", points[:, :3], fmt="%.5f %.5f %.5f")
        (out_dir / f"{epoch}_mesh.json").write_text(json.dumps({"n_chainage": N_CHAINAGE, "n_theta": N_THETA}, indent=2), encoding="utf-8")
        meta = {
            "epoch": epoch,
            "las_file": f"{epoch}.las",
            "txt_file": f"{epoch}.txt",
            "points": int(len(points)),
            "deformation_mm": {
                "upper_deflection_chainage_20m": UPPER_DEFLECTION_MM[epoch],
                "local_damage_chainage_65m": LOCAL_DAMAGE_MM[epoch],
            },
            "registration": {"status": "pre-registered", "transform": "identity"},
        }
        (out_dir / f"{epoch}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        epoch_meta.append(meta)

    write_tables(out_dir)
    manifest = {
        "dataset": out_dir.name,
        "created_by": "tools/create_step6_clean_t0t5_dataset.py",
        "purpose": "Clean synthetic dataset for Step 6 time-series deformation testing",
        "method": "direct mesh/point generation; no raycasting; identity registration",
        "length_m": LENGTH_M,
        "radius_m": RADIUS_M,
        "points_per_epoch": int(len(base_points)),
        "epochs": epoch_meta,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    readme = f"""# Step 6 Clean T0-T5 Deformation Dataset

Clean synthetic dataset for Step 6 only.

- No raycasting.
- No scanner simulation.
- T0-T5 are already registered in the same coordinate system.
- Deformation includes upper/crown deflection and local damage.

## Ground truth

- Upper deflection at chainage 20 m: 0 -> -45 mm.
- Local damage at chainage 65 m: starts at T3 and reaches -40 mm.

## Files

- `T0.las` ... `T5.las`: LAS point clouds for the tool.
- `T0.txt` ... `T5.txt`: debug text files.
- `ground_truth.csv`, `baseline_pairs.csv`, `incremental_pairs.csv`, `manifest.json`.
- `step6_clean_t0t5_preview.blend`: optional Blender preview scene.

## Suggested workflow

Load `T0.las` as reference, add `T1.las` to `T5.las`, then run Step 6 trend/M3C2/technical section.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    if not args.skip_blender:
        build_blender_preview(out_dir, args.host, args.port)

    print(f"Dataset written to: {out_dir}")
    print(f"Points per epoch: {len(base_points):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
