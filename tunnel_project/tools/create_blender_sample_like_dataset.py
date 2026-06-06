r"""Create a Blender-backed OS1/OS6-style tunnel sample dataset.

The real files under data/sample_pcd are large field-like point clouds with
columns ``x y z r g b``. This generator creates a smaller synthetic pair with
similar naming, global coordinates, colors, clutter, and T0/Tn deformation so
the app can test loading, denoising, centerline extraction, and Step 6 without
committing hundreds of megabytes.

Run from tunnel_project while Blender MCP is listening on localhost:9876:
    ..\.venv\Scripts\python.exe tools\create_blender_sample_like_dataset.py
"""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "blender_sample_like"

BLENDER_CODE = r'''
import bpy
import json
import math
import random
from pathlib import Path

OUT_DIR = Path(r"__OUT_DIR__")
OUT_DIR.mkdir(parents=True, exist_ok=True)

random.seed(20260607)

HEADER = "XYZ[0][m] XYZ[1][m] XYZ[2][m] True Color[0][] True Color[1][] True Color[2][]"

# Global-coordinate style: close to the field sample scale, not local origin.
BASE_X = 748.8
BASE_Y = -367.0
BASE_Z = 3.1
LENGTH = 72.0
RADIUS = 2.85
N_AXIAL = 720
N_THETA = 240
NOISE_M = 0.006

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat

def centerline(s):
    # A mild real-site-like curve and grade.
    x = BASE_X + 0.75 * math.sin((s / LENGTH) * math.pi * 1.2)
    y = BASE_Y + s
    z = BASE_Z + 0.0025 * s
    return x, y, z

def deformation(s, theta):
    # Local deformation around the middle of the tunnel.
    g = math.exp(-0.5 * ((s - 38.0) / 6.0) ** 2)
    crown = max(0.0, math.sin(theta))
    invert = max(0.0, -math.sin(theta))
    side = abs(math.cos(theta))
    dr = -0.045 * side * g
    dz = (-0.070 * crown + 0.012 * invert) * g
    return dr, dz

def shade(theta, s):
    base = 185 + 26 * math.sin(theta) + 12 * math.sin(s * 0.35)
    jitter = random.gauss(0.0, 6.0)
    v = max(70, min(255, int(base + jitter)))
    return v

def make_scan(kind):
    rows = []
    for i in range(N_AXIAL):
        s = LENGTH * i / (N_AXIAL - 1)
        cx, cy, cz = centerline(s)
        for j in range(N_THETA):
            theta = 2.0 * math.pi * j / N_THETA
            # Occlude a lower-left band to resemble incomplete field scans.
            if 18.0 < s < 57.0 and 210.0 < (math.degrees(theta) % 360.0) < 250.0:
                if random.random() < 0.80:
                    continue
            dr = dz = 0.0
            if kind == 'OS6':
                dr, dz = deformation(s, theta)
            n = random.gauss(0.0, NOISE_M)
            r = RADIUS + dr + n
            x = cx + r * math.cos(theta)
            y = cy + random.gauss(0.0, 0.004)
            z = cz + RADIUS * math.sin(theta) + dz + n * math.sin(theta)
            v = shade(theta, s)
            rows.append([x, y, z, v, v, v])

    # Add cable/tray-like linear clutter near the crown.
    for k in range(900):
        s = LENGTH * k / 899.0
        cx, cy, cz = centerline(s)
        x = cx + 0.38 + random.gauss(0.0, 0.012)
        y = cy + random.gauss(0.0, 0.006)
        z = cz + 2.15 + 0.04 * math.sin(s * 0.8) + random.gauss(0.0, 0.012)
        rows.append([x, y, z, 45, 45, 45])

    # Add removable random outliers and survey clutter.
    for _ in range(1800):
        s = random.uniform(0.0, LENGTH)
        cx, cy, cz = centerline(s)
        theta = random.uniform(0.0, 2.0 * math.pi)
        r = random.choice([random.uniform(3.4, 5.0), random.uniform(0.2, 1.3)])
        rows.append([
            cx + r * math.cos(theta),
            cy + random.gauss(0.0, 0.02),
            cz + r * math.sin(theta),
            random.randint(120, 255), random.randint(120, 255), random.randint(120, 255),
        ])

    if kind == 'OS6':
        # Small scanner/global registration bias to mimic a second station/epoch.
        for row in rows:
            row[0] += 0.018
            row[1] -= 0.011
            row[2] += 0.006

    return rows

def write_txt(path, rows, with_header):
    with open(path, 'w', encoding='utf-8') as f:
        if with_header:
            f.write(HEADER + '\n')
        for x, y, z, r, g, b in rows:
            f.write(f"{x:.5f} {y:.5f} {z:.5f} {int(r)} {int(g)} {int(b)}\n")

def make_point_mesh(name, rows, mat, max_points=12000):
    step = max(1, len(rows) // max_points)
    verts = [(row[0], row[1], row[2]) for row in rows[::step]]
    mesh = bpy.data.meshes.new(name + '_mesh')
    mesh.from_pydata(verts, [], [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj

def add_scene_guides():
    mat_marker = material('sample_like_chainage_markers', (1.0, 0.86, 0.10, 1.0))
    for s in [0, 18, 36, 54, 72]:
        cx, cy, cz = centerline(s)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.18, location=(cx, cy, cz + 3.25))
        obj = bpy.context.object
        obj.name = f'chainage_s_{s:02.0f}m'
        obj.data.materials.append(mat_marker)

    bpy.ops.object.light_add(type='SUN', location=(BASE_X + 10, BASE_Y - 20, BASE_Z + 20))
    bpy.context.object.name = 'Sun_sample_like_dataset'
    bpy.ops.object.camera_add(
        location=(BASE_X + 10, BASE_Y - 32, BASE_Z + 10),
        rotation=(math.radians(75), 0, math.radians(13)),
    )
    bpy.context.scene.camera = bpy.context.object

clear_scene()
mat_os1 = material('OS1_reference_gray_blue', (0.25, 0.52, 0.90, 1.0))
mat_os6 = material('OS6_deformed_gray_orange', (1.0, 0.55, 0.18, 1.0))

os1 = make_scan('OS1')
os6 = make_scan('OS6')

os1_path = OUT_DIR / 'OS1_blender_tunnel_entire_10cm.txt'
os6_path = OUT_DIR / 'OS6_blender_tunnel_entire_10cm.txt'
write_txt(os1_path, os1, with_header=False)
write_txt(os6_path, os6, with_header=True)

obj1 = make_point_mesh('OS1_reference_sample_like', os1, mat_os1)
obj2 = make_point_mesh('OS6_deformed_sample_like', os6, mat_os6)
obj2.location.x += 7.0
add_scene_guides()

manifest = {
    'dataset': 'blender_sample_like',
    'created_by': 'tools/create_blender_sample_like_dataset.py',
    'purpose': 'OS1/OS6-style field sample surrogate for load, denoise, centerline, section, and Step 6 testing.',
    'units': 'meters',
    'columns': 'x y z r g b',
    'coordinates': {'base_x': BASE_X, 'base_y': BASE_Y, 'base_z': BASE_Z, 'axis': 'Y/chainage'},
    'files': [
        {'name': os1_path.name, 'role': 'T0/reference', 'header': False, 'points': len(os1)},
        {'name': os6_path.name, 'role': 'Tn/deformed', 'header': True, 'points': len(os6)},
    ],
    'ground_truth': {
        'local_deformation_center_chainage_m': 38.0,
        'local_deformation_sigma_m': 6.0,
        'crown_settlement_mm': -70.0,
        'sidewall_convergence_per_side_mm': -45.0,
        'scanner_bias_m': {'x': 0.018, 'y': -0.011, 'z': 0.006},
        'expected_warning': True,
        'expected_warning_chainage_m': [28.0, 48.0],
        'contains_cable_like_clutter': True,
        'contains_random_outliers': True,
        'contains_occlusion_band': True,
    },
}
with open(OUT_DIR / 'manifest.json', 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2)

readme = f"""# Blender Sample-Like Dataset

Synthetic OS1/OS6-style tunnel point clouds generated in Blender.

Files:

- `{os1_path.name}`: reference/T0 scan, no header, columns `x y z r g b`.
- `{os6_path.name}`: monitoring/Tn scan, one header line like the real OS6 sample, columns `x y z r g b`.
- `manifest.json`: point counts and expected deformation/clutter behavior.
- `blender_sample_like.blend`: visual scene with reference/deformed clouds and chainage markers.

The dataset uses global coordinates near the real sample scale (`x~748`, `y~-367`, `z~3`) and includes a curved/graded tunnel lining, partial occlusion, cable-like clutter, random outliers, and a local deformation around chainage 38 m.
"""
with open(OUT_DIR / 'README.md', 'w', encoding='utf-8') as f:
    f.write(readme)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / 'blender_sample_like.blend'))

print(json.dumps({'status': 'ok', 'out_dir': str(OUT_DIR), 'os1_points': len(os1), 'os6_points': len(os6)}, indent=2))
'''


def send_blender_command(command_type: str, params: dict, host: str, port: int, timeout: float = 240.0) -> dict:
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
    raise RuntimeError("No complete JSON response received from Blender")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost", help="Blender MCP addon host")
    parser.add_argument("--port", type=int, default=9876, help="Blender MCP addon port")
    parser.add_argument("--out", default=str(OUT_DIR), help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    code = BLENDER_CODE.replace("__OUT_DIR__", str(out_dir).replace("\\", "\\\\"))
    response = send_blender_command("execute_code", {"code": code}, args.host, args.port)
    if response.get("status") != "success":
        print(json.dumps(response, indent=2))
        return 1
    print(json.dumps(response.get("result", response), indent=2))
    print(f"Dataset written to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
