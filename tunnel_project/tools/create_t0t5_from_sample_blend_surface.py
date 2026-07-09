r"""Create T0-T5 LAS point clouds from data/sample_pcd/Tunel.blend.

This generator is based directly on the sample Blender file. It does not use
raycasting and does not create a procedural tunnel. For each epoch, it opens
Tunel.blend, applies controlled deformation to the tunnel lining mesh, samples
mesh surfaces into a dense point cloud, writes TXT, then converts to LAS.

Run from tunnel_project while Blender MCP listens on localhost:9876:
    ..\.venv\Scripts\python.exe tools\create_t0t5_from_sample_blend_surface.py
"""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

import laspy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "sample_pcd" / "Tunel.blend"
DEFAULT_OUT = ROOT / "data" / "sample_blend_surface_t0t5_step6"

BLENDER_CODE = r'''
import bpy
import csv
import json
import math
import random
from pathlib import Path
from mathutils import Vector

SOURCE_BLEND = Path(r"__SOURCE_BLEND__")
OUT_DIR = Path(r"__OUT_DIR__")
OUT_DIR.mkdir(parents=True, exist_ok=True)
random.seed(20260629)

EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
POINTS_PER_EPOCH = int(__POINTS_PER_EPOCH__)
PREVIEW_POINTS = int(__PREVIEW_POINTS__)
CROWN_MM = {"T0": 0.0, "T1": -4.0, "T2": -9.0, "T3": -16.0, "T4": -25.0, "T5": -36.0}
CONV_MM = {"T0": 0.0, "T1": -1.0, "T2": -4.0, "T3": -9.0, "T4": -15.0, "T5": -24.0}
LOCAL_MM = {"T0": 0.0, "T1": 0.0, "T2": 0.0, "T3": -8.0, "T4": -17.0, "T5": -30.0}
LABEL_BY_NAME = {
    "Cylinder": 1,
    "Cylinder.003": 1,
    "Cylinder.001": 2,
    "Cylinder.002": 4,
    "Cylinder.005": 4,
    "Cylinder.006": 5,
    "Cylinder.007": 5,
    "Circle": 8,
    "Plane.001": 6,
    "Sphere.001": 7,
}
INTENSITY_BY_LABEL = {1: 0.55, 2: 0.75, 4: 0.30, 5: 0.82, 6: 0.48, 7: 0.95, 8: 0.58}
LINING_OBJECTS = {"Cylinder", "Cylinder.003"}
HEADER = "x y z nx ny nz intensity label"


def scene_bounds(objects):
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for obj in objects:
        if obj.type != 'MESH' or not obj.data.vertices:
            continue
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            mins.x = min(mins.x, w.x); mins.y = min(mins.y, w.y); mins.z = min(mins.z, w.z)
            maxs.x = max(maxs.x, w.x); maxs.y = max(maxs.y, w.y); maxs.z = max(maxs.z, w.z)
    return mins, maxs


def deform_lining(epoch, bounds):
    if epoch == 'T0':
        return
    mins, maxs = bounds
    y0, y1 = mins.y, maxs.y
    length = max(1e-9, y1 - y0)
    cx = (mins.x + maxs.x) * 0.5
    cz = (mins.z + maxs.z) * 0.5
    crown = CROWN_MM[epoch] / 1000.0
    conv = CONV_MM[epoch] / 1000.0
    local = LOCAL_MM[epoch] / 1000.0
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or obj.name not in LINING_OBJECTS:
            continue
        mw = obj.matrix_world
        inv = mw.inverted()
        for vert in obj.data.vertices:
            w = mw @ vert.co
            yn = (w.y - y0) / length
            theta = math.atan2(w.z - cz, w.x - cx)
            crown_w = math.exp(-0.5 * ((yn - 0.30) / 0.10) ** 2) * max(0.0, math.sin(theta)) ** 1.6
            side_w = math.exp(-0.5 * ((yn - 0.58) / 0.13) ** 2) * abs(math.cos(theta)) ** 1.4
            local_w = math.exp(-0.5 * ((yn - 0.78) / 0.060) ** 2) * math.exp(-0.5 * ((math.atan2(math.sin(theta - math.radians(62)), math.cos(theta - math.radians(62)))) / 0.25) ** 2)
            w.z += crown * crown_w + local * local_w
            w.x += -math.copysign(abs(conv) * side_w, w.x - cx)
            vert.co = inv @ w
        obj.data.update()


def mesh_triangles(obj):
    mw = obj.matrix_world
    mesh = obj.data
    label = LABEL_BY_NAME.get(obj.name, 8)
    tris = []
    for poly in mesh.polygons:
        if len(poly.vertices) < 3:
            continue
        verts = [mw @ mesh.vertices[i].co for i in poly.vertices]
        normal = (mw.to_3x3() @ poly.normal).normalized()
        for i in range(1, len(verts) - 1):
            a, b, c = verts[0], verts[i], verts[i + 1]
            area = 0.5 * (b - a).cross(c - a).length
            if area > 1e-12:
                tris.append((a, b, c, normal, label, area))
    return tris


def sample_triangles(tris, n_points, seed):
    rng = random.Random(seed)
    total_area = sum(t[5] for t in tris)
    if total_area <= 0:
        return []
    rows = []
    cumulative = []
    acc = 0.0
    for t in tris:
        acc += t[5]
        cumulative.append(acc)
    # Weighted stochastic sampling gives dense surface coverage without ray gaps.
    for _ in range(n_points):
        r = rng.random() * total_area
        lo, hi = 0, len(cumulative) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cumulative[mid] < r:
                lo = mid + 1
            else:
                hi = mid
        a, b, c, normal, label, area = tris[lo]
        u = rng.random()
        v = rng.random()
        if u + v > 1.0:
            u = 1.0 - u
            v = 1.0 - v
        p = a + (b - a) * u + (c - a) * v
        # Very small surface noise only to avoid perfectly repeated samples.
        p = p + normal * rng.gauss(0.0, 0.00025)
        base_i = INTENSITY_BY_LABEL.get(label, 0.5)
        intensity = max(0.03, min(1.0, base_i + rng.gauss(0.0, 0.025)))
        rows.append((p.x, p.y, p.z, normal.x, normal.y, normal.z, intensity, label))
    return rows


def write_epoch(epoch, rows, bounds):
    txt = OUT_DIR / f"{epoch}.txt"
    with txt.open('w', encoding='utf-8') as f:
        f.write('# ' + HEADER + '\n')
        for row in rows:
            f.write('%.5f %.5f %.5f %.6f %.6f %.6f %.6f %d\n' % row)
    # Preview for Blender scene; smaller than full TXT.
    preview = OUT_DIR / f"{epoch}_preview.xyz"
    step = max(1, int(math.ceil(len(rows) / PREVIEW_POINTS)))
    with preview.open('w', encoding='utf-8') as f:
        for row in rows[::step]:
            f.write('%.5f %.5f %.5f\n' % (row[0], row[1], row[2]))
    meta = {
        'epoch': epoch,
        'txt_file': txt.name,
        'preview_file': preview.name,
        'points': len(rows),
        'bounds_min': [bounds[0].x, bounds[0].y, bounds[0].z],
        'bounds_max': [bounds[1].x, bounds[1].y, bounds[1].z],
        'deformation_mm': {
            'crown_settlement': CROWN_MM[epoch],
            'sidewall_convergence': CONV_MM[epoch],
            'local_damage': LOCAL_MM[epoch],
        },
    }
    (OUT_DIR / f"{epoch}.json").write_text(json.dumps(meta, indent=2), encoding='utf-8')
    return meta


def write_tables():
    with (OUT_DIR / 'ground_truth.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['epoch', 'crown_settlement_mm', 'sidewall_convergence_mm', 'local_damage_mm'])
        for e in EPOCHS:
            w.writerow([e, CROWN_MM[e], CONV_MM[e], LOCAL_MM[e]])
    with (OUT_DIR / 'baseline_pairs.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['pair', 'crown_delta_mm', 'sidewall_delta_mm', 'local_delta_mm'])
        for e in EPOCHS[1:]:
            w.writerow([f'T0-{e}', CROWN_MM[e], CONV_MM[e], LOCAL_MM[e]])
    with (OUT_DIR / 'incremental_pairs.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['pair', 'crown_increment_mm', 'sidewall_increment_mm', 'local_increment_mm'])
        for a, b in zip(EPOCHS[:-1], EPOCHS[1:]):
            w.writerow([f'{a}-{b}', CROWN_MM[b] - CROWN_MM[a], CONV_MM[b] - CONV_MM[a], LOCAL_MM[b] - LOCAL_MM[a]])


def build_preview_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    colors = [(0.55,0.55,0.55,1), (0.25,0.55,0.90,1), (0.25,0.75,0.45,1), (0.95,0.65,0.25,1), (0.95,0.35,0.25,1), (0.75,0.20,0.20,1)]
    for idx, epoch in enumerate(EPOCHS):
        verts = []
        with (OUT_DIR / f'{epoch}_preview.xyz').open('r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                x, y, z = map(float, line.split()[:3])
                verts.append((x + idx * 8.0, y, z))
        mesh = bpy.data.meshes.new(f'{epoch}_sample_blend_surface_preview_mesh')
        mesh.from_pydata(verts, [], [])
        mesh.update()
        obj = bpy.data.objects.new(f'{epoch}_from_Tunel_blend_surface', mesh)
        bpy.context.collection.objects.link(obj)
        mat = bpy.data.materials.new(f'{epoch}_mat')
        mat.diffuse_color = colors[idx]
        obj.data.materials.append(mat)
        obj.show_name = True
    bpy.ops.object.light_add(type='SUN', location=(20, -30, 30))
    bpy.ops.object.camera_add(location=(28, -45, 18), rotation=(1.2, 0, 0.62))
    bpy.context.scene.camera = bpy.context.view_layer.objects.active
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / 'sample_blend_surface_t0t5_preview.blend'))


def main():
    metas = []
    source_bounds = None
    for i, epoch in enumerate(EPOCHS):
        print('Opening sample blend for', epoch)
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))
        objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and len(obj.data.polygons) > 0]
        source_bounds = scene_bounds(objects)
        deform_lining(epoch, source_bounds)
        objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and len(obj.data.polygons) > 0]
        bounds = scene_bounds(objects)
        tris = []
        for obj in objects:
            tris.extend(mesh_triangles(obj))
        rows = sample_triangles(tris, POINTS_PER_EPOCH, 20260629 + i)
        metas.append(write_epoch(epoch, rows, bounds))
    write_tables()
    manifest = {
        'dataset': 'sample_blend_surface_t0t5_step6',
        'created_by': 'tools/create_t0t5_from_sample_blend_surface.py',
        'source_blend': str(SOURCE_BLEND),
        'method': 'surface sampling from sample Tunel.blend meshes; no raycasting; no procedural tunnel',
        'points_per_epoch': POINTS_PER_EPOCH,
        'epochs': metas,
    }
    (OUT_DIR / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    readme = f"""# Sample Blend Surface T0-T5 Step 6 Dataset

Source: `{SOURCE_BLEND}`

This dataset is based directly on the sample Blender file `Tunel.blend`.
It samples mesh surfaces directly. It does not use raycasting and does not create a procedural tunnel.

Use `T0.las` as reference and add `T1.las` to `T5.las` for Step 6 testing.
"""
    (OUT_DIR / 'README.md').write_text(readme, encoding='utf-8')
    build_preview_scene()
    print(json.dumps({'status': 'ok', 'out_dir': str(OUT_DIR), 'points_per_epoch': POINTS_PER_EPOCH}, indent=2))

main()
'''


def send_blender_command(command_type: str, params: dict, host: str, port: int, timeout: float = 1200.0) -> dict:
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
        las.x, las.y, las.z = points[:, 0], points[:, 1], points[:, 2]
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
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--points", type=int, default=500_000)
    parser.add_argument("--preview-points", type=int, default=80_000)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--skip-las", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    source = Path(args.source).resolve()
    code = (
        BLENDER_CODE
        .replace("__OUT_DIR__", str(out_dir).replace("\\", "\\\\"))
        .replace("__SOURCE_BLEND__", str(source).replace("\\", "\\\\"))
        .replace("__POINTS_PER_EPOCH__", str(int(args.points)))
        .replace("__PREVIEW_POINTS__", str(int(args.preview_points)))
    )
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

