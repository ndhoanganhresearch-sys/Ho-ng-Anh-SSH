r"""Export the currently-open Blender lining as a clean T0-T5 dataset.

The output schema matches ``data/tunnel_t0t5_blend_curved_lining_clean``:

- ``T0.txt`` ... ``T5.txt`` with 9 columns
  ``x y z nx ny nz intensity label damage_type``
- ``T0.json`` ... ``T5.json``
- ``las_export/T0.las`` ... ``las_export/T5.las``
- ``manifest.json``, ``README.md``, and ``timeseries_report.csv``

Run from ``tunnel_project`` while Blender MCP is connected to the file you want
to export::

    ..\.venv\Scripts\python.exe tools\export_current_blend_clean_t0t5.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import socket
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "current_blend_curved_lining_clean"
TIMES = ["T0", "T1", "T2", "T3", "T4", "T5"]
HEADER = "x y z nx ny nz intensity label damage_type"
CROWN_MM = {"T0": 0.0, "T1": -5.0, "T2": -12.0, "T3": -21.0, "T4": -32.0, "T5": -48.0}
LOCAL_MM = {"T0": 0.0, "T1": 0.0, "T2": -4.0, "T3": -10.0, "T4": -20.0, "T5": -36.0}


BLENDER_CODE = r'''
import bpy
import json
import math
import os
from mathutils import Vector

OUT_DIR = r"__OUT_DIR__"
TARGET_POINTS = int("__TARGET_POINTS__")
os.makedirs(OUT_DIR, exist_ok=True)

mesh_objects = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.visible_get()]
if not mesh_objects:
    raise RuntimeError("No visible mesh objects in current Blender scene")

lining_candidates = [o for o in mesh_objects if "lining" in o.name.lower() or "tunnel" in o.name.lower()]
lining = max(lining_candidates or mesh_objects, key=lambda o: len(o.data.polygons))
depsgraph = bpy.context.evaluated_depsgraph_get()
eval_obj = lining.evaluated_get(depsgraph)
mesh = eval_obj.to_mesh()
mw = lining.matrix_world
normal_matrix = mw.to_3x3().inverted().transposed()

rows = []
for poly in mesh.polygons:
    verts = [mesh.vertices[i].co.copy() for i in poly.vertices]
    normal = (normal_matrix @ poly.normal).normalized()
    samples = [poly.center]
    for i, v0 in enumerate(verts):
        samples.append((v0 + verts[(i + 1) % len(verts)]) * 0.5)
    for co in samples:
        p = mw @ co
        rows.append([p.x, p.y, p.z, normal.x, normal.y, normal.z])
eval_obj.to_mesh_clear()

if not rows:
    raise RuntimeError("Selected lining mesh has no sampleable polygons")

if len(rows) > TARGET_POINTS:
    step = len(rows) / float(TARGET_POINTS)
    rows = [rows[int(i * step)] for i in range(TARGET_POINTS)]
elif len(rows) < TARGET_POINTS:
    base = list(rows)
    i = 0
    while len(rows) < TARGET_POINTS:
        rows.append(base[i % len(base)])
        i += 1

payload = {
    "source_blend": bpy.data.filepath,
    "lining_object": lining.name,
    "columns": "x y z nx ny nz",
    "rows": rows,
}
with open(os.path.join(OUT_DIR, "current_lining_samples.json"), "w", encoding="utf-8") as f:
    json.dump(payload, f)
print(json.dumps({"source_blend": bpy.data.filepath, "lining_object": lining.name, "points": len(rows)}))
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


def chainage_frame(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    y_min = points[:, 1].min()
    y = points[:, 1] - y_min
    x = points[:, 0]
    z = points[:, 2]
    center_x = np.median(x)
    center_z = np.median(z)
    theta = np.arctan2(z - center_z, x - center_x)
    return y, x - center_x, z - center_z, theta


def deform_epoch(base: np.ndarray, time: str) -> np.ndarray:
    out = base.copy()
    chainage, lateral, up, theta = chainage_frame(base[:, :3])
    length = max(float(chainage.max()), 1.0)
    crown_chainage = 0.30 * length
    local_chainage = 0.75 * length
    crown = CROWN_MM[time] / 1000.0
    local = LOCAL_MM[time] / 1000.0
    crown_w = np.exp(-0.5 * ((chainage - crown_chainage) / max(5.0, 0.08 * length)) ** 2) * np.clip(np.sin(theta), 0.0, None) ** 1.7
    local_w = np.exp(-0.5 * ((chainage - local_chainage) / max(2.5, 0.04 * length)) ** 2)
    local_w *= np.exp(-0.5 * (((theta - math.radians(58.0) + math.pi) % (2 * math.pi) - math.pi) / 0.25) ** 2)
    out[:, 2] += crown * crown_w + local * local_w * math.sin(math.radians(58.0))
    radial = np.column_stack([np.cos(theta), np.zeros_like(theta), np.sin(theta)])
    out[:, :3] += radial * (local * local_w)[:, None]

    damage = np.zeros(len(out), dtype=np.float64)
    if time in {"T2", "T3", "T4", "T5"}:
        damage[(local_w > 0.35)] = 20
    if time in {"T2", "T3", "T4", "T5"}:
        crack_mask = (np.abs(chainage - local_chainage) < max(0.8, 0.015 * length)) & (np.abs(((theta - math.radians(100.0) + math.pi) % (2 * math.pi)) - math.pi) < 0.08)
        damage[crack_mask] = 21
    if time in {"T3", "T4", "T5"}:
        leak_mask = (np.abs(chainage - 0.58 * length) < max(1.2, 0.025 * length)) & (np.sin(theta) > 0.55)
        damage[leak_mask] = 22

    labels = np.where(damage > 0, damage, 1.0)
    intensity = 0.55 + 0.20 * np.clip(base[:, 5], 0.0, 1.0)
    return np.column_stack([out[:, :6], intensity, labels, damage])


def write_las(path: Path, arr: np.ndarray) -> None:
    import laspy
    points = arr[:, :3]
    intensity = np.clip(arr[:, 6] * 65535, 0, 65535).astype(np.uint16)
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = np.array([1e-4, 1e-4, 1e-4])
    header.offsets = points.min(axis=0)
    las = laspy.LasData(header)
    las.x = points[:, 0]
    las.y = points[:, 1]
    las.z = points[:, 2]
    las.intensity = intensity
    las.classification = arr[:, 7].astype(np.uint8)
    las.red = intensity
    las.green = intensity
    las.blue = intensity
    las.write(str(path))


def write_dataset(out_dir: Path) -> None:
    payload = json.loads((out_dir / "current_lining_samples.json").read_text(encoding="utf-8"))
    base = np.asarray(payload["rows"], dtype=np.float64)
    las_dir = out_dir / "las_export"
    las_dir.mkdir(parents=True, exist_ok=True)
    exports = []
    previous = None
    report_rows = []
    base_epoch = None
    for time in TIMES:
        arr = deform_epoch(base, time)
        if time == "T0":
            base_epoch = arr.copy()
        txt_path = out_dir / f"{time}.txt"
        np.savetxt(txt_path, arr, fmt="%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.0f %.0f", header=HEADER, comments="# ")
        las_path = las_dir / f"{time}.las"
        write_las(las_path, arr)
        kept = {str(int(label)): int((arr[:, 7] == label).sum()) for label in sorted(set(arr[:, 7].astype(int)))}
        meta = {
            "time": time,
            "txt": txt_path.name,
            "las": str(las_path),
            "points": int(len(arr)),
            "removed_interior_points": 0,
            "kept_labels": kept,
            "bounds_min": [round(float(v), 6) for v in arr[:, :3].min(axis=0)],
            "bounds_max": [round(float(v), 6) for v in arr[:, :3].max(axis=0)],
        }
        (out_dir / f"{time}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        exports.append(meta)
        if time != "T0":
            disp = np.linalg.norm(arr[:, :3] - base_epoch[:, :3], axis=1) * 1000.0
            inc = np.linalg.norm(arr[:, :3] - previous[:, :3], axis=1) * 1000.0 if previous is not None else disp
            report_rows.append({
                "times": time,
                "cumulative_p95_mm": round(float(np.percentile(disp, 95)), 2),
                "cumulative_max_mm": round(float(np.max(disp)), 2),
                "incremental_p95_mm": round(float(np.percentile(inc, 95)), 2),
                "rate_mm_per_epoch": round(float(np.percentile(inc, 95)), 2),
                "accel_mm_per_epoch2": "",
                "accelerating": "yes",
                "gt_peak_mm": "",
                "error_mm": "",
            })
        previous = arr.copy()

    with (out_dir / "timeseries_report.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["times", "cumulative_p95_mm", "cumulative_max_mm", "incremental_p95_mm", "rate_mm_per_epoch", "accel_mm_per_epoch2", "accelerating", "gt_peak_mm", "error_mm"])
        writer.writeheader()
        writer.writerows(report_rows)

    manifest = {
        "dataset": out_dir.name,
        "source_blend": payload.get("source_blend", ""),
        "lining_object": payload.get("lining_object", ""),
        "purpose": "Clean T0-T5 lining dataset exported from the currently open Blender MCP file.",
        "columns": HEADER,
        "kept_labels": {"1": "lining", "20": "spalling", "21": "crack", "22": "leak"},
        "removed_labels": {},
        "exports": exports,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out_dir / "README.md").write_text(
        "# Current Blend Curved Lining Clean Dataset\n\n"
        "Schema-compatible with `tunnel_t0t5_blend_curved_lining_clean`.\n"
        "Exported from the currently open Blender MCP file. Interior objects are not included; only the selected lining mesh is sampled.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--out", default=str(OUT_DIR))
    parser.add_argument("--target-points", type=int, default=60000)
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    code = BLENDER_CODE.replace("__OUT_DIR__", str(out_dir).replace("\\", "\\\\")).replace("__TARGET_POINTS__", str(args.target_points))
    (out_dir / "export_current_blend_code.py").write_text(code, encoding="utf-8")
    response = send_blender_code(code, args.host, args.port, args.timeout)
    if response.get("status") != "success":
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps(response.get("result", response), indent=2, ensure_ascii=False))
    write_dataset(out_dir)
    print(f"Dataset written to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
