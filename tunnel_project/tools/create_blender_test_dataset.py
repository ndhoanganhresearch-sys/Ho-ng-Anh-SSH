"""Create a Blender-backed synthetic tunnel dataset for end-to-end testing.

The script talks to the Blender MCP addon socket at localhost:9876. Blender is
used as the scene generator and visual ground-truth container; exported TXT
files are plain point-cloud inputs that the tunnel tool can load directly.

Run from tunnel_project:
    python tools/create_blender_test_dataset.py
"""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "blender_test_suite"


BLENDER_CODE = r'''
import bpy
import json
import math
import os
import random
from pathlib import Path

OUT_DIR = Path(r"__OUT_DIR__")
OUT_DIR.mkdir(parents=True, exist_ok=True)

random.seed(20260606)

RADIUS = 4.0
LENGTH = 48.0
N_AXIAL = 73
N_THETA = 96
NOISE_M = 0.003

LABEL_STRUCTURE = 1
LABEL_NOISE = 2
LABEL_CABLE = 3
LABEL_CLEARANCE_INTRUDER = 4


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def center_at(y, curved=False, grade=False):
    if curved:
        x = 1.0 * math.sin((y / LENGTH) * math.pi * 1.4)
    else:
        x = 0.0
    z = 0.18 * y / LENGTH if grade else 0.0
    return x, y, z


def deform_offsets(y, theta, spec):
    if not spec:
        return 0.0, 0.0
    cy = spec.get('center_y', 0.0)
    sigma = spec.get('sigma_y', 5.0)
    g = math.exp(-0.5 * ((y - cy) / sigma) ** 2)
    s = math.sin(theta)
    c = math.cos(theta)
    crown_w = max(0.0, s)
    invert_w = max(0.0, -s)
    side_w = abs(c)
    dz = (spec.get('crown_mm', 0.0) * crown_w + spec.get('invert_mm', 0.0) * invert_w) * g / 1000.0
    dr = (spec.get('sidewall_mm', 0.0) * side_w) * g / 1000.0
    return dr, dz


def make_scan(case, variant, deform=None, noisy=False, clearance=False, curved=False, grade=False, occlusion=False):
    rows = []
    y0 = -LENGTH / 2.0
    for iy in range(N_AXIAL):
        y = y0 + LENGTH * iy / (N_AXIAL - 1)
        cx, yy, cz = center_at(y, curved=curved, grade=grade)
        for it in range(N_THETA):
            theta = 2.0 * math.pi * it / N_THETA
            if occlusion and -9.0 < y < 9.0 and 205.0 < math.degrees(theta) % 360.0 < 285.0:
                continue
            dr, dz = deform_offsets(y, theta, deform)
            r = RADIUS + dr
            n = random.gauss(0.0, NOISE_M if not noisy else 0.012)
            x = cx + (r + n) * math.cos(theta)
            z = cz + RADIUS * math.sin(theta) + dz + n * math.sin(theta)
            shade = 168 + int(24 * (0.5 + 0.5 * math.sin(theta)))
            rows.append([x, yy, z, shade, shade, shade, 0.0, LABEL_STRUCTURE])

    if noisy:
        # Random removable outliers around the tunnel and two false interior clusters.
        for _ in range(900):
            y = random.uniform(-LENGTH / 2.0, LENGTH / 2.0)
            theta = random.uniform(0.0, 2.0 * math.pi)
            r = random.choice([random.uniform(4.8, 7.0), random.uniform(0.6, 1.7)])
            cx, yy, cz = center_at(y, curved=curved, grade=grade)
            rows.append([cx + r * math.cos(theta), yy, cz + r * math.sin(theta), 255, 40, 200, 0.0, LABEL_NOISE])
        # Cable-like object near the crown that should be removable for lining analysis.
        for iy in range(160):
            y = -22.0 + 44.0 * iy / 159.0
            cx, yy, cz = center_at(y, curved=curved, grade=grade)
            rows.append([cx + 0.85, yy, cz + 3.35, 60, 60, 60, 0.0, LABEL_CABLE])

    if clearance:
        # Intruding service duct inside a 2.2 m gauge in the upper-right quadrant.
        for iy in range(180):
            y = -18.0 + 36.0 * iy / 179.0
            theta = math.radians(55.0)
            for k in range(6):
                local = -0.10 + 0.20 * k / 5.0
                cx, yy, cz = center_at(y, curved=curved, grade=grade)
                r = 1.65 + local
                rows.append([cx + r * math.cos(theta), yy, cz + r * math.sin(theta), 255, 30, 30, 0.0, LABEL_CLEARANCE_INTRUDER])

    return rows


def write_txt(path, rows, include_labels=False):
    with open(path, 'w', encoding='utf-8') as f:
        for row in rows:
            if include_labels:
                f.write(f"{row[0]:.5f} {row[1]:.5f} {row[2]:.5f} {int(row[3])} {int(row[4])} {int(row[5])} {row[6]:.1f} {int(row[7])}\n")
            else:
                f.write(f"{row[0]:.5f} {row[1]:.5f} {row[2]:.5f} {int(row[3])} {int(row[4])} {int(row[5])}\n")


def make_mesh(name, rows, mat, max_points=4500):
    step = max(1, len(rows) // max_points)
    verts = [(r[0], r[1], r[2]) for r in rows[::step]]
    mesh = bpy.data.meshes.new(name + '_mesh')
    mesh.from_pydata(verts, [], [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def add_section_markers():
    mat = material('chainage_marker_yellow', (1.0, 0.85, 0.1, 1.0))
    for y in [-18, -9, 0, 9, 18]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.12, location=(0, y, 4.55))
        obj = bpy.context.object
        obj.name = f'chainage_y_{y:+.0f}m'
        obj.data.materials.append(mat)


def add_camera_and_light():
    bpy.ops.object.light_add(type='SUN', location=(6, -10, 12))
    bpy.context.object.name = 'Sun_blender_dataset'
    bpy.ops.object.camera_add(location=(10, -54, 12), rotation=(math.radians(78), 0, math.radians(11)))
    bpy.context.scene.camera = bpy.context.object


clear_scene()
mat_t0 = material('T0_reference_blue', (0.1, 0.45, 1.0, 1.0))
mat_tn = material('Tn_candidate_orange', (1.0, 0.44, 0.08, 1.0))
mat_noise = material('Noise_or_intrusion_red', (1.0, 0.05, 0.05, 1.0))

local_deform = {'center_y': 0.0, 'sigma_y': 4.2, 'crown_mm': -80.0, 'sidewall_mm': -50.0, 'invert_mm': 15.0}
minor_deform = {'center_y': 12.0, 'sigma_y': 7.5, 'crown_mm': -25.0, 'sidewall_mm': -20.0, 'invert_mm': 5.0}

cases = [
    {
        'id': 'case_01_clean_reference',
        'purpose': 'Clean circular tunnel for load, centerline, section fitting, and no-warning baseline.',
        't0': {},
        'tn': {},
        'truth': {'expected_warning': False, 'max_deformation_mm': 0.0},
    },
    {
        'id': 'case_02_local_deformation',
        'purpose': 'Local T0/Tn deformation: crown settlement, sidewall convergence, and invert heave around chainage 0 m.',
        't0': {},
        'tn': {'deform': local_deform},
        'truth': {'expected_warning': True, 'warning_chainage_m': [-6.0, 6.0], **local_deform},
    },
    {
        'id': 'case_03_noise_and_cables',
        'purpose': 'Denoising stress test with random outliers, interior false clusters, and a crown cable.',
        't0': {},
        'tn': {'deform': minor_deform, 'noisy': True},
        'truth': {'expected_noise_labels': [LABEL_NOISE, LABEL_CABLE], 'structure_label': LABEL_STRUCTURE, **minor_deform},
    },
    {
        'id': 'case_04_clearance_intrusion',
        'purpose': 'Clearance/headroom test with a known intruding duct inside a 2.2 m gauge.',
        't0': {},
        'tn': {'clearance': True},
        'truth': {'expected_clearance_violation': True, 'gauge_radius_m': 2.2, 'intruder_label': LABEL_CLEARANCE_INTRUDER},
    },
    {
        'id': 'case_05_curved_centerline',
        'purpose': 'Curved and slightly graded tunnel for centerline, section frames, registration, and chainage ordering.',
        't0': {'curved': True, 'grade': True},
        'tn': {'curved': True, 'grade': True, 'deform': minor_deform},
        'truth': {'expected_curved_centerline': True, **minor_deform},
    },
    {
        'id': 'case_06_occlusion_sparse',
        'purpose': 'Sparse/occluded tunnel arc to test robust section fitting and UI section display.',
        't0': {'occlusion': True},
        'tn': {'occlusion': True, 'deform': local_deform},
        'truth': {'expected_occlusion': True, 'missing_arc_degrees': [205, 285], **local_deform},
    },
]

manifest = {
    'dataset': 'blender_test_suite',
    'created_by': 'tools/create_blender_test_dataset.py',
    'axis': 'Y longitudinal, X lateral, Z vertical',
    'units': 'meters; deformation truth in millimeters',
    'point_columns': 'x y z r g b, plus optional intensity label for *_labels.txt',
    'cases': [],
}

for idx, case in enumerate(cases):
    case_dir = OUT_DIR / case['id']
    case_dir.mkdir(parents=True, exist_ok=True)
    t0 = make_scan(case['id'], 'T0', **case['t0'])
    tn = make_scan(case['id'], 'Tn', **case['tn'])
    write_txt(case_dir / 'T0.txt', t0)
    write_txt(case_dir / 'Tn.txt', tn)
    write_txt(case_dir / 'T0_labels.txt', t0, include_labels=True)
    write_txt(case_dir / 'Tn_labels.txt', tn, include_labels=True)
    truth = {
        'case_id': case['id'],
        'purpose': case['purpose'],
        't0_points': len(t0),
        'tn_points': len(tn),
        'truth': case['truth'],
        'recommended_tests': [
            'load T0/Tn', 'centerline extraction', 'section generation',
            'deformation comparison', '2D/3D warning visualization'
        ],
    }
    if 'noise' in case['id']:
        truth['recommended_tests'].extend(['clean noise', 'label-aware denoise scoring'])
    if 'clearance' in case['id']:
        truth['recommended_tests'].extend(['clearance/headroom', 'warning sections'])
    with open(case_dir / 'ground_truth.json', 'w', encoding='utf-8') as f:
        json.dump(truth, f, indent=2)
    manifest['cases'].append(truth)

    # Keep scene readable: show selected representative cases, offset in X.
    if idx in [0, 1, 2, 3, 4, 5]:
        obj_t0 = make_mesh(case['id'] + '_T0', t0, mat_t0)
        obj_tn = make_mesh(case['id'] + '_Tn', tn, mat_tn)
        offset = idx * 10.5
        obj_t0.location.x -= 3.0
        obj_tn.location.x += offset
        obj_t0.location.y += 0.0
        obj_tn.location.y += 0.0

with open(OUT_DIR / 'manifest.json', 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2)

readme = (
    '# Blender Test Suite\n\n'
    'Synthetic tunnel point-cloud cases generated from Blender for testing the tunnel analysis tool. The `.blend` file keeps the visual scene; the `.txt` files are direct inputs for the Python tool.\n\n'
    'Each case contains:\n\n'
    '- T0.txt: reference scan, columns x y z r g b\n'
    '- Tn.txt: candidate scan, columns x y z r g b\n'
    '- T0_labels.txt / Tn_labels.txt: x y z r g b intensity label\n'
    '- ground_truth.json: expected deformation/noise/clearance behavior\n\n'
    'Use T0 as the reference scan and Tn as the compared scan. The longitudinal axis is Y, vertical is Z, and units are meters. Deformation truth is reported in millimeters.\n'
    '\n## Case Map\n\n'
    '| Case | Main purpose | Expected behavior |\n'
    '| --- | --- | --- |\n'
    '| case_01_clean_reference | Load, centerline, section fitting, clean no-warning baseline | T0 and Tn are effectively identical |\n'
    '| case_02_local_deformation | Step 6 T0/Tn deformation and 2D/3D local warning | Local warning around chainage -6 m to +6 m |\n'
    '| case_03_noise_and_cables | Clean-noise and label-aware denoise benchmark | Remove outliers/cable while preserving lining |\n'
    '| case_04_clearance_intrusion | Clearance/headroom warning | Intruding duct should violate a 2.2 m gauge |\n'
    '| case_05_curved_centerline | Curved centerline, section frames, registration, chainage order | Centerline should follow the curved tunnel |\n'
    '| case_06_occlusion_sparse | Sparse/occluded section robustness and UI fit | Sections should remain stable despite missing arc |\n'
    '\n## Recommended Verification\n\n'
    'Run `..\\.venv\\Scripts\\python.exe smoke_test_blender_dataset.py` from `tunnel_project` to verify the files can be loaded by the tool.\n'
)
with open(OUT_DIR / 'README.md', 'w', encoding='utf-8') as f:
    f.write(readme)

add_section_markers()
add_camera_and_light()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / 'blender_test_suite.blend'))

print(json.dumps({'status': 'ok', 'out_dir': str(OUT_DIR), 'cases': len(cases)}, indent=2))
'''


def send_blender_command(command_type: str, params: dict, host: str, port: int, timeout: float = 180.0) -> dict:
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
