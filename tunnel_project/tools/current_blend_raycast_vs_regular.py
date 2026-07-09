r"""Raycast the currently-open Blender MCP scene and compare with regular mesh samples.

This does not create a new Blender scene. It uses the file currently open in
Blender, raycasts visible geometry through the MCP bridge, samples the selected
lining mesh directly, and reports nearest-surface distances for raycast lining
hits.

Run from ``tunnel_project`` while Blender MCP is listening on localhost:9876::

    ..\.venv\Scripts\python.exe tools\current_blend_raycast_vs_regular.py
"""
from __future__ import annotations

import argparse
import csv
import json
import socket
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "current_blend_raycast_regular"


BLENDER_CODE = r'''
import bpy
import json
import math
import os
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT_DIR = r"__OUT_DIR__"
RAY_STEP_DEG = __RAY_STEP_DEG__
MAX_RANGE_M = __MAX_RANGE_M__
os.makedirs(OUT_DIR, exist_ok=True)

LABELS = {
    "lining": 1,
    "rail": 2,
    "sleeper": 3,
    "cable": 4,
    "light": 5,
    "walkway": 6,
    "target": 7,
    "equipment": 8,
    "other": 9,
}

def label_for(name):
    n = name.lower()
    if "lining" in n or "tunnel" in n:
        return LABELS["lining"]
    if "rail" in n:
        return LABELS["rail"]
    if "sleeper" in n:
        return LABELS["sleeper"]
    if "cable" in n or "tray" in n:
        return LABELS["cable"]
    if "light" in n:
        return LABELS["light"]
    if "walkway" in n or "drain" in n:
        return LABELS["walkway"]
    if "target" in n or "sphere" in n:
        return LABELS["target"]
    if "equipment" in n or "box" in n:
        return LABELS["equipment"]
    return LABELS["other"]

mesh_objects = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.visible_get()]
if not mesh_objects:
    raise RuntimeError("No visible mesh objects in current Blender scene")

lining_candidates = [o for o in mesh_objects if "lining" in o.name.lower() or "tunnel" in o.name.lower()]
lining = max(lining_candidates or mesh_objects, key=lambda o: len(o.data.vertices))

depsgraph = bpy.context.evaluated_depsgraph_get()
bbox = [lining.matrix_world @ Vector(corner) for corner in lining.bound_box]
min_x = min(p.x for p in bbox); max_x = max(p.x for p in bbox)
min_y = min(p.y for p in bbox); max_y = max(p.y for p in bbox)
min_z = min(p.z for p in bbox); max_z = max(p.z for p in bbox)
center_x = 0.5 * (min_x + max_x)
center_z = 0.5 * (min_z + max_z)
span_y = max_y - min_y
station_ys = [min_y + span_y * f for f in (0.08, 0.29, 0.50, 0.71, 0.92)]
stations = [Vector((center_x, y, center_z - 1.3)) for y in station_ys]

regular_rows = []
mesh = lining.evaluated_get(depsgraph).to_mesh()
mw = lining.matrix_world
normal_matrix = mw.to_3x3().inverted().transposed()
for vertex in mesh.vertices:
    point = mw @ vertex.co
    normal = (normal_matrix @ vertex.normal).normalized()
    regular_rows.append([point.x, point.y, point.z, normal.x, normal.y, normal.z, 0.8, 1])
for poly in mesh.polygons:
    center = mw @ poly.center
    normal = (normal_matrix @ poly.normal).normalized()
    regular_rows.append([center.x, center.y, center.z, normal.x, normal.y, normal.z, 0.8, 1])
    verts = [mesh.vertices[i].co.copy() for i in poly.vertices]
    for i, v0 in enumerate(verts):
        v1 = verts[(i + 1) % len(verts)]
        midpoint = mw @ ((v0 + v1) * 0.5)
        regular_rows.append([midpoint.x, midpoint.y, midpoint.z, normal.x, normal.y, normal.z, 0.8, 1])
lining.evaluated_get(depsgraph).to_mesh_clear()

raycast_rows = []
hit_counts = {}
az_steps = int(360.0 / RAY_STEP_DEG)
el0, el1 = -38.0, 82.0
el_steps = int((el1 - el0) / RAY_STEP_DEG) + 1
for station_index, origin in enumerate(stations):
    for ia in range(az_steps):
        az = math.radians(ia * RAY_STEP_DEG)
        caz, saz = math.cos(az), math.sin(az)
        for ie in range(el_steps):
            el = math.radians(el0 + ie * RAY_STEP_DEG)
            direction = Vector((math.cos(el) * caz, math.cos(el) * saz, math.sin(el))).normalized()
            hit, loc, normal, face_index, obj, matrix = bpy.context.scene.ray_cast(depsgraph, origin, direction, distance=MAX_RANGE_M)
            if not hit or obj is None:
                continue
            label = label_for(obj.name)
            distance = (loc - origin).length
            intensity = max(0.05, min(1.0, 1.0 / (1.0 + 0.015 * distance * distance)))
            raycast_rows.append([loc.x, loc.y, loc.z, normal.x, normal.y, normal.z, intensity, label])
            hit_counts[str(label)] = hit_counts.get(str(label), 0) + 1

bvh = BVHTree.FromObject(lining, depsgraph)
surface_distances_mm = []
for row in raycast_rows:
    if int(row[7]) != LABELS["lining"]:
        continue
    nearest = bvh.find_nearest(Vector((row[0], row[1], row[2])))
    if nearest and nearest[0] is not None:
        surface_distances_mm.append(nearest[3] * 1000.0)

def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[index]

exact_surface_summary = {
    "mae_mm": sum(surface_distances_mm) / len(surface_distances_mm) if surface_distances_mm else None,
    "median_mm": percentile(surface_distances_mm, 50.0),
    "p95_mm": percentile(surface_distances_mm, 95.0),
    "max_mm": max(surface_distances_mm) if surface_distances_mm else None,
}

header = "x y z nx ny nz intensity label"
def write_rows(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        f.write("# " + header + "\n")
        for row in rows:
            f.write("%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.0f\n" % tuple(row))

write_rows(os.path.join(OUT_DIR, "current_regular.txt"), regular_rows)
write_rows(os.path.join(OUT_DIR, "current_raycast.txt"), raycast_rows)

manifest = {
    "source_blend": bpy.data.filepath,
    "lining_object": lining.name,
    "ray_step_deg": RAY_STEP_DEG,
    "max_range_m": MAX_RANGE_M,
    "stations": [[round(v, 6) for v in s] for s in stations],
    "regular_points": len(regular_rows),
    "raycast_points": len(raycast_rows),
    "hit_counts_by_label": hit_counts,
    "raycast_to_exact_lining_surface": exact_surface_summary,
    "labels": LABELS,
}
with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
print(json.dumps(manifest, ensure_ascii=False))
'''


def send_blender_code(code: str, host: str, port: int, timeout: float) -> dict:
    payload = {"type": "execute_code", "params": {"code": code}}
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
            text = b"".join(chunks).decode("utf-8")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue
    raise RuntimeError("No complete JSON response received from Blender MCP")


def load_points(path: Path) -> np.ndarray:
    arr = np.loadtxt(path, comments="#")
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr


def nearest_distances_mm(source: np.ndarray, target: np.ndarray, chunk_size: int = 4096) -> np.ndarray:
    try:
        from scipy.spatial import cKDTree
    except Exception:
        cKDTree = None
    if cKDTree is not None:
        tree = cKDTree(target[:, :3])
        distances, _ = tree.query(source[:, :3], k=1, workers=-1)
        return distances * 1000.0

    distances = []
    target_xyz = target[:, :3]
    for start in range(0, len(source), chunk_size):
        src = source[start:start + chunk_size, :3]
        diff = src[:, None, :] - target_xyz[None, :, :]
        dist2 = np.einsum("ijk,ijk->ij", diff, diff)
        distances.append(np.sqrt(dist2.min(axis=1)) * 1000.0)
    return np.concatenate(distances) if distances else np.array([], dtype=float)


def write_las(txt_path: Path) -> None:
    try:
        import laspy
    except Exception:
        return
    arr = load_points(txt_path)
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
    las.red = intensity
    las.green = intensity
    las.blue = intensity
    las.write(str(txt_path.with_suffix(".las")))


def compare_outputs(out_dir: Path) -> dict:
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    regular = load_points(out_dir / "current_regular.txt")
    raycast = load_points(out_dir / "current_raycast.txt")
    raycast_lining = raycast[raycast[:, 7].astype(int) == 1]
    if len(raycast_lining) == 0:
        raise RuntimeError("Raycast produced no lining hits, cannot compare")
    distances = nearest_distances_mm(raycast_lining, regular)
    summary = {
        "source_blend": manifest.get("source_blend", ""),
        "lining_object": manifest.get("lining_object", ""),
        "regular_points": int(len(regular)),
        "raycast_points": int(len(raycast)),
        "raycast_lining_points": int(len(raycast_lining)),
        "exact_surface_mae_mm": round(float(manifest["raycast_to_exact_lining_surface"]["mae_mm"]), 6),
        "exact_surface_p95_mm": round(float(manifest["raycast_to_exact_lining_surface"]["p95_mm"]), 6),
        "nearest_regular_mae_mm": round(float(np.mean(distances)), 3),
        "nearest_regular_median_mm": round(float(np.median(distances)), 3),
        "nearest_regular_p95_mm": round(float(np.percentile(distances, 95)), 3),
        "nearest_regular_max_mm": round(float(np.max(distances)), 3),
    }
    with (out_dir / "comparison_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    with (out_dir / "comparison_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        for key, value in summary.items():
            writer.writerow([key, value])
    lines = [
        "# Current Blender Raycast vs Regular",
        "",
        f"- Source blend: {summary['source_blend']}",
        f"- Lining object: {summary['lining_object']}",
        f"- Regular mesh samples: {summary['regular_points']}",
        f"- Raycast total hits: {summary['raycast_points']}",
        f"- Raycast lining hits: {summary['raycast_lining_points']}",
        f"- Exact mesh-surface MAE: {summary['exact_surface_mae_mm']:.6f} mm",
        f"- Exact mesh-surface P95: {summary['exact_surface_p95_mm']:.6f} mm",
        f"- MAE to regular lining: {summary['nearest_regular_mae_mm']:.2f} mm",
        f"- Median to regular lining: {summary['nearest_regular_median_mm']:.2f} mm",
        f"- P95 to regular lining: {summary['nearest_regular_p95_mm']:.2f} mm",
        "",
        "Exact mesh-surface metrics compare raycast lining hits against the same current Blender mesh surface.",
        "Nearest regular metrics compare raycast lining hits against the exported regular point file, so they include regular sample spacing.",
    ]
    (out_dir / "comparison_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--out", default=str(OUT_DIR))
    parser.add_argument("--ray-step-deg", type=float, default=1.0)
    parser.add_argument("--max-range-m", type=float, default=55.0)
    parser.add_argument("--timeout", type=float, default=900.0)
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    code = (
        BLENDER_CODE
        .replace("__OUT_DIR__", str(out_dir).replace("\\", "\\\\"))
        .replace("__RAY_STEP_DEG__", repr(args.ray_step_deg))
        .replace("__MAX_RANGE_M__", repr(args.max_range_m))
    )
    (out_dir / "current_blend_mcp_code.py").write_text(code, encoding="utf-8")

    response = send_blender_code(code, args.host, args.port, args.timeout)
    if response.get("status") != "success":
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps(response.get("result", response), indent=2, ensure_ascii=False))

    for txt_name in ("current_regular.txt", "current_raycast.txt"):
        write_las(out_dir / txt_name)
    summary = compare_outputs(out_dir)
    print(json.dumps(summary, indent=2))
    print(f"wrote: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
