# -*- coding: utf-8 -*-
r"""Create two Blender-backed T1/Tn datasets for Step 6 testing.

Run from tunnel_project while Blender MCP is listening on localhost:9876:
    ..\.venv\Scripts\python.exe tools\create_blender_step6_t1_tn_datasets.py
"""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "blender_step6_t1_tn"

BLENDER_CODE = r'''
import bpy
import json
import math
import random
from pathlib import Path

OUT_DIR = Path(r"__OUT_DIR__")
OUT_DIR.mkdir(parents=True, exist_ok=True)
random.seed(20260607)
HEADER = "x y z r g b"
RADIUS = 3.20
LENGTH = 64.0
N_AXIAL = 161
N_THETA = 160
NOISE_M = 0.0035
LABEL_STRUCTURE = 1
LABEL_OUTLIER = 2
LABEL_CABLE = 3
LABEL_CLEARANCE = 4

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat

def centerline(s):
    return 0.42 * math.sin((s / LENGTH) * math.pi * 1.15), s, 0.10 * s / LENGTH

def deformation(s, theta, kind):
    if kind == 'subtle':
        g = math.exp(-0.5 * ((s - 32.0) / 8.0) ** 2)
        return -0.012 * abs(math.cos(theta)) * g, -0.018 * max(0.0, math.sin(theta)) * g, 0.0
    if kind == 'complex':
        g1 = math.exp(-0.5 * ((s - 26.0) / 5.0) ** 2)
        g2 = math.exp(-0.5 * ((s - 45.0) / 4.0) ** 2)
        crown = max(0.0, math.sin(theta))
        invert = max(0.0, -math.sin(theta))
        side = abs(math.cos(theta))
        right = max(0.0, math.cos(theta))
        dr = (-0.065 * side * g1) + (-0.030 * right * g2)
        dz = (-0.090 * crown * g1) + (0.018 * invert * g1) - (0.035 * crown * g2)
        return dr, dz, -0.020 * right * g2
    return 0.0, 0.0, 0.0

def make_scan(version, epoch):
    rows = []
    kind = 'none' if epoch == 'T1' else version
    for i in range(N_AXIAL):
        s = LENGTH * i / (N_AXIAL - 1)
        cx, cy, cz = centerline(s)
        for j in range(N_THETA):
            theta = 2.0 * math.pi * j / N_THETA
            if version == 'complex' and 18.0 < s < 54.0 and 210.0 < math.degrees(theta) % 360.0 < 275.0 and random.random() < 0.70:
                continue
            dr, dz, dx = deformation(s, theta, kind)
            n = random.gauss(0.0, NOISE_M if version == 'subtle' else 0.005)
            r = RADIUS + dr + n
            x = cx + r * math.cos(theta) + dx
            y = cy + random.gauss(0.0, 0.0025)
            z = cz + RADIUS * math.sin(theta) + dz + n * math.sin(theta)
            shade = max(80, min(230, int(168 + 28 * math.sin(theta) + random.gauss(0, 4))))
            rows.append([x, y, z, shade, shade, shade, LABEL_STRUCTURE])
    if version == 'complex':
        for k in range(520):
            s = LENGTH * k / 519.0
            cx, cy, cz = centerline(s)
            rows.append([cx + 0.55 + random.gauss(0.0, 0.010), cy + random.gauss(0.0, 0.004), cz + 2.55 + 0.03 * math.sin(s * 0.6) + random.gauss(0.0, 0.010), 45, 45, 45, LABEL_CABLE])
        if epoch == 'Tn':
            for k in range(420):
                s = 23.0 + 14.0 * k / 419.0
                theta = math.radians(62.0)
                cx, cy, cz = centerline(s)
                rr = 1.72 + random.gauss(0.0, 0.025)
                rows.append([cx + rr * math.cos(theta), cy + random.gauss(0.0, 0.004), cz + rr * math.sin(theta), 255, 35, 35, LABEL_CLEARANCE])
        for _ in range(900):
            s = random.uniform(0.0, LENGTH)
            theta = random.uniform(0.0, 2.0 * math.pi)
            cx, cy, cz = centerline(s)
            rr = random.choice([random.uniform(3.8, 5.8), random.uniform(0.5, 1.4)])
            rows.append([cx + rr * math.cos(theta), cy + random.gauss(0.0, 0.020), cz + rr * math.sin(theta), 240, 70, 210, LABEL_OUTLIER])
    return rows

def write_txt(path, rows, header=False, labels=False):
    with open(path, 'w', encoding='utf-8') as f:
        if header:
            f.write((HEADER + (' label' if labels else '')) + '\n')
        for row in rows:
            if labels:
                f.write(f"{row[0]:.5f} {row[1]:.5f} {row[2]:.5f} {int(row[3])} {int(row[4])} {int(row[5])} {int(row[6])}\n")
            else:
                f.write(f"{row[0]:.5f} {row[1]:.5f} {row[2]:.5f} {int(row[3])} {int(row[4])} {int(row[5])}\n")

def make_mesh(name, rows, mat, x_offset=0.0, max_points=9000):
    step = max(1, len(rows) // max_points)
    verts = [(r[0] + x_offset, r[1], r[2]) for r in rows[::step]]
    mesh = bpy.data.meshes.new(name + '_mesh')
    mesh.from_pydata(verts, [], [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)

def write_readme(case_dir, name, t1_name, tn_name, labels_name, purpose):
    extra = f"- `{labels_name}`: labeled Tn helper file for denoise scoring.\n" if labels_name else ""
    text = f"""# {name}

{purpose}

Files:

- `{t1_name}`: reference epoch T1, columns `x y z r g b`.
- `{tn_name}`: monitoring epoch Tn, columns `x y z r g b`.
{extra}- `manifest.json`: expected deformation and warning coverage.

Use T1 as the Step 6 reference and Tn as the current/monitoring epoch.
"""
    with open(case_dir / 'README.md', 'w', encoding='utf-8') as f:
        f.write(text)

clear_scene()
mat_t1 = material('T1_reference_blue', (0.12, 0.44, 0.95, 1.0))
mat_tn = material('Tn_monitor_orange', (1.0, 0.46, 0.08, 1.0))
mat_mark = material('critical_chainage_red', (1.0, 0.05, 0.04, 1.0))
datasets = []
specs = [
    ('version_01_subtle_deformation', 'subtle', 'Small mm-level deformation for M3C2/C2C sensitivity and 2D Visual scale.'),
    ('version_02_complex_warning', 'complex', 'Local critical deformation with occlusion, clutter, outliers, and clearance intrusion.'),
]
for idx, (folder, kind, purpose) in enumerate(specs):
    case_dir = OUT_DIR / folder
    case_dir.mkdir(parents=True, exist_ok=True)
    t1 = make_scan(kind, 'T1')
    tn = make_scan(kind, 'Tn')
    t1_name = 'T1_step6_reference.txt'
    tn_name = 'Tn_step6_monitoring.txt'
    labels_name = 'Tn_step6_monitoring_labels.txt' if kind == 'complex' else None
    write_txt(case_dir / t1_name, t1, header=False, labels=False)
    write_txt(case_dir / tn_name, tn, header=(kind == 'complex'), labels=False)
    if labels_name:
        write_txt(case_dir / labels_name, tn, header=True, labels=True)
    if kind == 'subtle':
        truth = {'expected_warning': True, 'expected_level': 'CAUTION', 'expected_chainage_m': [24.0, 40.0], 'crown_settlement_mm': -18.0, 'sidewall_convergence_per_side_mm': -12.0, 'contains_noise': False, 'visual_scale_recommended': 20}
    else:
        truth = {'expected_warning': True, 'expected_level': 'CRITICAL', 'expected_chainage_m': [20.0, 34.0], 'secondary_warning_chainage_m': [41.0, 50.0], 'crown_settlement_mm': -90.0, 'sidewall_convergence_per_side_mm': -65.0, 'clearance_intrusion': True, 'contains_cable_like_clutter': True, 'contains_random_outliers': True, 'contains_occlusion_band': True, 'labels': {'structure': LABEL_STRUCTURE, 'outlier': LABEL_OUTLIER, 'cable': LABEL_CABLE, 'clearance': LABEL_CLEARANCE}, 'visual_scale_recommended': 10}
    manifest = {'dataset': folder, 'created_by': 'tools/create_blender_step6_t1_tn_datasets.py', 'purpose': purpose, 'units': 'meters', 'columns': 'x y z r g b', 'axis': 'Y / chainage', 'base_radius_m': RADIUS, 'length_m': LENGTH, 'files': [{'name': t1_name, 'role': 'T1/reference', 'header': False, 'points': len(t1)}, {'name': tn_name, 'role': 'Tn/monitoring', 'header': kind == 'complex', 'points': len(tn)}], 'ground_truth': truth, 'step6_parameters_under_test': ['dW', 'dH', 'dR', 'dOval', 'dEcc', 'clearance_min', 'M3C2/C2C distance_mm', 'Visual scale']}
    if labels_name:
        manifest['files'].append({'name': labels_name, 'role': 'Tn labels helper', 'header': True, 'points': len(tn), 'columns': 'x y z r g b label'})
    with open(case_dir / 'manifest.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    write_readme(case_dir, folder, t1_name, tn_name, labels_name, purpose)
    offset = idx * 8.5
    make_mesh(folder + '_T1_reference', t1, mat_t1, x_offset=offset)
    make_mesh(folder + '_Tn_monitoring', tn, mat_tn, x_offset=offset + 3.8)
    for s in truth.get('expected_chainage_m', []):
        cx, cy, cz = centerline(float(s))
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.16, location=(cx + offset + 5.8, cy, cz + RADIUS + 0.35))
        obj = bpy.context.object
        obj.name = f'{folder}_warning_ch_{s:.0f}m'
        obj.data.materials.append(mat_mark)
    datasets.append({'folder': folder, 't1_points': len(t1), 'tn_points': len(tn), 'truth': truth})
top_manifest = {'dataset': 'blender_step6_t1_tn', 'created_by': 'tools/create_blender_step6_t1_tn_datasets.py', 'purpose': 'Two T1/Tn Blender datasets for Step 6 trend, M3C2 heatmap, 2D overlay, warnings, and denoise checks.', 'versions': datasets}
with open(OUT_DIR / 'manifest.json', 'w', encoding='utf-8') as f:
    json.dump(top_manifest, f, indent=2)
with open(OUT_DIR / 'README.md', 'w', encoding='utf-8') as f:
    f.write("""# Blender Step 6 T1/Tn Datasets

This folder contains two Blender-generated epoch pairs for Step 6.

- `version_01_subtle_deformation`: small deformation that is hard to see without the 2D Visual scale control.
- `version_02_complex_warning`: local critical deformation plus occlusion, cable-like clutter, outliers, and a clearance intruder.

Load `T1_step6_reference.txt` as the reference epoch and `Tn_step6_monitoring.txt` as the monitoring epoch.
""")
bpy.ops.object.light_add(type='SUN', location=(8, -18, 14))
bpy.context.object.name = 'Sun_step6_t1_tn'
bpy.ops.object.camera_add(location=(17, -42, 13), rotation=(math.radians(76), 0, math.radians(20)))
bpy.context.scene.camera = bpy.context.object
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / 'blender_step6_t1_tn.blend'))
print(json.dumps({'status': 'ok', 'out_dir': str(OUT_DIR), 'versions': datasets}, indent=2))
'''

def send_blender_command(command_type: str, params: dict, host: str, port: int, timeout: float = 300.0) -> dict:
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
