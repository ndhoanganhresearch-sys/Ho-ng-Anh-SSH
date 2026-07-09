r"""Create six Blender tunnel meshes T0-T5 and export them to LAS.

Purpose: Step 6 deformation/time-series testing only.
This generator does NOT use raycasting. Blender creates six deformed tunnel
meshes, exports their vertices as dense point clouds, and this wrapper converts
those TXT point clouds to LAS.

Run from tunnel_project while Blender MCP listens on localhost:9876:
    ..\.venv\Scripts\python.exe tools\create_blender_mesh_t0t5_las.py
"""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

import laspy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "blender_mesh_t0t5_step6"

BLENDER_CODE = r'''
import bpy
import csv
import json
import math
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path(r"__OUT_DIR__")
OUT_DIR.mkdir(parents=True, exist_ok=True)

EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
LENGTH = 80.0
RADIUS = 3.0
N_CHAINAGE = 520
N_THETA = 320
CHAINAGES = [i * LENGTH / (N_CHAINAGE - 1) for i in range(N_CHAINAGE)]
THETAS = [2.0 * math.pi * j / N_THETA for j in range(N_THETA)]
CROWN_MM = {"T0": 0.0, "T1": -5.0, "T2": -12.0, "T3": -20.0, "T4": -30.0, "T5": -45.0}
CONV_MM = {"T0": 0.0, "T1": 0.0, "T2": -5.0, "T3": -12.0, "T4": -22.0, "T5": -35.0}
LOCAL_MM = {"T0": 0.0, "T1": 0.0, "T2": 0.0, "T3": -15.0, "T4": -25.0, "T5": -40.0}
HEADER = "x y z nx ny nz intensity label"
LABEL_LINING = 1


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def centerline(s):
    # Mild curve/grade so Step 6 sees a tunnel-like longitudinal geometry.
    x = 0.20 * math.sin(2.0 * math.pi * s / LENGTH)
    y = s
    z = 0.0015 * s
    return Vector((x, y, z))


def angle_delta(a, b):
    return math.atan2(math.sin(a - b), math.cos(a - b))


def deformation(epoch, s, theta):
    crown = CROWN_MM[epoch] / 1000.0
    conv = CONV_MM[epoch] / 1000.0
    local = LOCAL_MM[epoch] / 1000.0

    crown_w = math.exp(-0.5 * ((s - 20.0) / 4.0) ** 2) * max(0.0, math.sin(theta)) ** 1.5
    side_w = math.exp(-0.5 * ((s - 45.0) / 4.5) ** 2) * abs(math.cos(theta)) ** 1.4
    local_w = math.exp(-0.5 * ((s - 65.0) / 1.8) ** 2) * math.exp(-0.5 * (angle_delta(theta, math.radians(55.0)) / 0.22) ** 2)

    dx = -math.copysign(abs(conv) * side_w, math.cos(theta))
    dz = crown * crown_w + local * local_w * math.sin(math.radians(55.0))
    dr = local * local_w
    return dx, dz, dr


def point_and_normal(epoch, s, theta):
    c = centerline(s)
    dx, dz, dr = deformation(epoch, s, theta)
    # Segment/ring texture is small and present in every epoch, so it does not
    # dominate deformation ground truth but makes the Blender model less flat.
    ring = 0.004 * math.sin(2.0 * math.pi * s / 2.0)
    seg = 0.0025 * math.sin(6.0 * theta)
    r = RADIUS + ring + seg + dr
    x = c.x + r * math.cos(theta) + dx
    y = c.y
    z = c.z + r * math.sin(theta) + dz
    n = Vector((math.cos(theta), 0.0, math.sin(theta))).normalized()
    return Vector((x, y, z)), n


def build_epoch(epoch, mat, x_offset):
    verts = []
    normals = []
    rows = []
    for s in CHAINAGES:
        for theta in THETAS:
            p, n = point_and_normal(epoch, s, theta)
            p_vis = Vector((p.x + x_offset, p.y, p.z))
            verts.append(tuple(p_vis))
            normals.append(tuple(n))
            intensity = 0.45 + 0.25 * max(0.0, n.z) + 0.08 * math.cos(theta * 3.0)
            rows.append([p.x, p.y, p.z, n.x, n.y, n.z, max(0.05, min(1.0, intensity)), LABEL_LINING])
    faces = []
    for i in range(N_CHAINAGE - 1):
        for j in range(N_THETA):
            a = i * N_THETA + j
            b = i * N_THETA + (j + 1) % N_THETA
            c = (i + 1) * N_THETA + (j + 1) % N_THETA
            d = (i + 1) * N_THETA + j
            faces.append((a, b, c, d))
    mesh = bpy.data.meshes.new(f"Tunnel_{epoch}_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"Tunnel_{epoch}", mesh)
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)

    txt = OUT_DIR / f"{epoch}.txt"
    with txt.open("w", encoding="utf-8") as f:
        f.write("# " + HEADER + "\n")
        for row in rows:
            f.write("%.5f %.5f %.5f %.6f %.6f %.6f %.6f %d\n" % tuple(row))
    return {
        "epoch": epoch,
        "txt_file": txt.name,
        "points": len(rows),
        "deformation_mm": {
            "crown_settlement_chainage_20m": CROWN_MM[epoch],
            "sidewall_convergence_chainage_45m": CONV_MM[epoch],
            "local_damage_chainage_65m": LOCAL_MM[epoch],
        },
    }


def write_tables():
    with (OUT_DIR / "ground_truth.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "crown_settlement_mm", "sidewall_convergence_mm", "local_damage_mm"])
        for e in EPOCHS:
            w.writerow([e, CROWN_MM[e], CONV_MM[e], LOCAL_MM[e]])
    with (OUT_DIR / "baseline_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "crown_delta_mm", "sidewall_delta_mm", "local_delta_mm"])
        for e in EPOCHS[1:]:
            w.writerow([f"T0-{e}", CROWN_MM[e], CONV_MM[e], LOCAL_MM[e]])
    with (OUT_DIR / "incremental_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "crown_increment_mm", "sidewall_increment_mm", "local_increment_mm"])
        for a, b in zip(EPOCHS[:-1], EPOCHS[1:]):
            w.writerow([f"{a}-{b}", CROWN_MM[b] - CROWN_MM[a], CONV_MM[b] - CONV_MM[a], LOCAL_MM[b] - LOCAL_MM[a]])


def write_readme():
    text = """# Blender Mesh T0-T5 Step 6 Dataset

Six tunnel meshes are created in Blender through MCP, then their mesh vertices are exported as point clouds and converted to LAS by the wrapper script.

This dataset is for Step 6 testing only. It does not use raycasting.

## Files

- `T0.las` ... `T5.las`: LAS point clouds for the tool.
- `T0.txt` ... `T5.txt`: debug text point clouds with columns `x y z nx ny nz intensity label`.
- `blender_mesh_t0t5_step6.blend`: Blender scene containing six tunnel meshes arranged side by side for visual inspection.
- `ground_truth.csv`, `baseline_pairs.csv`, `incremental_pairs.csv`, `manifest.json`.

## Ground truth

- Crown settlement at chainage 20 m: 0 to -45 mm.
- Sidewall convergence at chainage 45 m: 0 to -35 mm.
- Local damage at chainage 65 m: starts at T3 and reaches -40 mm.

## Suggested test

Load `T0.las` as reference, add `T1.las` to `T5.las`, then run Step 6 trend/M3C2/technical section.
"""
    (OUT_DIR / "README.md").write_text(text, encoding="utf-8")


def main():
    clear_scene()
    mats = []
    colors = [(0.55, 0.55, 0.52, 1), (0.50, 0.58, 0.68, 1), (0.52, 0.65, 0.52, 1), (0.70, 0.58, 0.45, 1), (0.72, 0.48, 0.48, 1), (0.78, 0.38, 0.38, 1)]
    for i, c in enumerate(colors):
        mats.append(material(f"epoch_mat_{i}", c))
    metas = []
    for idx, epoch in enumerate(EPOCHS):
        metas.append(build_epoch(epoch, mats[idx], idx * 8.0))
    write_tables()
    write_readme()
    bpy.ops.object.light_add(type="SUN", location=(20, -30, 30))
    bpy.ops.object.camera_add(location=(24, -36, 16), rotation=(math.radians(68), 0, math.radians(28)))
    bpy.context.scene.camera = bpy.context.object
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "blender_mesh_t0t5_step6.blend"))
    manifest = {
        "dataset": "blender_mesh_t0t5_step6",
        "created_by": "tools/create_blender_mesh_t0t5_las.py",
        "method": "Blender mesh vertices exported to LAS; no raycasting",
        "length_m": LENGTH,
        "radius_m": RADIUS,
        "points_per_epoch": N_CHAINAGE * N_THETA,
        "columns": HEADER,
        "epochs": metas,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "out_dir": str(OUT_DIR), "points_per_epoch": N_CHAINAGE * N_THETA}, indent=2))

main()
'''


def send_blender_command(command_type: str, params: dict, host: str, port: int, timeout: float = 900.0) -> dict:
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


def convert_txt_to_las(out_dir: Path) -> None:
    for txt_path in sorted(out_dir.glob("T[0-5].txt")):
        arr = np.loadtxt(txt_path, comments="#")
        points = arr[:, :3]
        intensity = np.clip(arr[:, 6] * 65535, 0, 65535).astype(np.uint16)
        labels = arr[:, 7].astype(np.uint8)
        header = laspy.LasHeader(point_format=3, version="1.2")
        header.scales = np.array([1e-4, 1e-4, 1e-4])
        header.offsets = points.min(axis=0)
        las = laspy.LasData(header)
        las.x = points[:, 0]
        las.y = points[:, 1]
        las.z = points[:, 2]
        las.intensity = intensity
        las.classification = labels
        gray = intensity
        las.red = gray
        las.green = gray
        las.blue = gray
        las.write(str(txt_path.with_suffix(".las")))
        print(f"LAS written: {txt_path.with_suffix('.las')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--out", default=str(OUT_DIR))
    parser.add_argument("--skip-las", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    code = BLENDER_CODE.replace("__OUT_DIR__", str(out_dir).replace("\\", "\\\\"))
    response = send_blender_command("execute_code", {"code": code}, args.host, args.port)
    if response.get("status") != "success":
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps(response.get("result", response), indent=2, ensure_ascii=False))
    if not args.skip_las:
        convert_txt_to_las(out_dir)
    print(f"Dataset written to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
