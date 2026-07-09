r"""Export the currently-open visual Blender T0-T5 scene as full interior data.

This is intended for files like
``tunnel_t0t5_curved_visual_T5.blend`` that already contain objects named
``T0_lining``, ``T0_rail``, ..., ``T5_lining``.  The output follows the full
interior schema used by ``tunnel_t0t5_blend_combined_damage_interior``:

``x y z nx ny nz intensity label damage_type`` plus ``las_export/T*.las``.
"""
from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "current_visual_blend_interior_t0t5"
TIMES = ["T0", "T1", "T2", "T3", "T4", "T5"]
HEADER = "x y z nx ny nz intensity label damage_type"
LABELS = {
    "lining": 1,
    "rail": 2,
    "sleeper": 3,
    "walkway": 4,
    "cable_tray": 5,
    "pipe": 6,
    "light": 7,
    "equipment": 8,
    "target": 9,
    "sign": 10,
    "spalling": 20,
    "crack": 21,
    "leak": 22,
}
DAMAGE_TYPES = {
    "none": 0,
    "crown_settlement": 1,
    "sidewall_convergence": 2,
    "spalling": 3,
    "crack": 4,
    "leak": 5,
}


BLENDER_CODE = r'''
import bpy
import json
import mathutils
import os

OUT_DIR = r"__OUT_DIR__"
os.makedirs(OUT_DIR, exist_ok=True)

LABELS = __LABELS_JSON__
DAMAGE_TYPES = __DAMAGE_TYPES_JSON__
TIMES = ["T0", "T1", "T2", "T3", "T4", "T5"]

def classify(name):
    n = name.lower()
    if "spalling" in n:
        return LABELS["spalling"], DAMAGE_TYPES["spalling"], 0.35
    if "crack" in n:
        return LABELS["crack"], DAMAGE_TYPES["crack"], 0.10
    if "leak" in n:
        return LABELS["leak"], DAMAGE_TYPES["leak"], 0.75
    if "lining" in n or "tunnel" in n:
        return LABELS["lining"], DAMAGE_TYPES["none"], 0.50
    if "rail" in n:
        return LABELS["rail"], DAMAGE_TYPES["none"], 0.82
    if "sleeper" in n:
        return LABELS["sleeper"], DAMAGE_TYPES["none"], 0.45
    if "walkway" in n:
        return LABELS["walkway"], DAMAGE_TYPES["none"], 0.48
    if "cable" in n or "tray" in n:
        return LABELS["cable_tray"], DAMAGE_TYPES["none"], 0.62
    if "pipe" in n or "handrail" in n or "drain" in n:
        return LABELS["pipe"], DAMAGE_TYPES["none"], 0.58
    if "light" in n:
        return LABELS["light"], DAMAGE_TYPES["none"], 0.95
    if "target" in n:
        return LABELS["target"], DAMAGE_TYPES["none"], 0.98
    if "sign" in n or "plate" in n:
        return LABELS["sign"], DAMAGE_TYPES["none"], 0.90
    if "equipment" in n or "cabinet" in n or "box" in n or "extinguisher" in n:
        return LABELS["equipment"], DAMAGE_TYPES["none"], 0.55
    return LABELS["equipment"], DAMAGE_TYPES["none"], 0.50

def sample_object(obj, depsgraph):
    label, damage, intensity = classify(obj.name)
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    mw = obj.matrix_world
    normal_matrix = mw.to_3x3().inverted().transposed()
    rows = []
    for poly in mesh.polygons:
        normal = (normal_matrix @ poly.normal).normalized()
        samples = [poly.center]
        verts = [mesh.vertices[i].co.copy() for i in poly.vertices]
        if len(verts) <= 4:
            for i, v0 in enumerate(verts):
                samples.append((v0 + verts[(i + 1) % len(verts)]) * 0.5)
        for co in samples:
            p = mw @ co
            rows.append([p.x, p.y, p.z, normal.x, normal.y, normal.z, intensity, label, damage])
    eval_obj.to_mesh_clear()
    return rows

depsgraph = bpy.context.evaluated_depsgraph_get()
exports = {}
counts = {}
for time in TIMES:
    rows = []
    label_counts = {}
    objects = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.visible_get() and o.name.startswith(time + "_")]
    epoch_offset_x = 0.0
    lining_objects = [o for o in objects if "lining" in o.name.lower()]
    offset_source = lining_objects[0] if lining_objects else (objects[0] if objects else None)
    if offset_source is not None:
        xs = [(offset_source.matrix_world @ mathutils.Vector(corner)).x for corner in offset_source.bound_box]
        epoch_offset_x = 0.5 * (min(xs) + max(xs))
    for obj in objects:
        obj_rows = sample_object(obj, depsgraph)
        for row in obj_rows:
            row[0] -= epoch_offset_x
        rows.extend(obj_rows)
        if obj_rows:
            label = str(int(obj_rows[0][7]))
            label_counts[label] = label_counts.get(label, 0) + len(obj_rows)
    exports[time] = rows
    counts[time] = {"objects": len(objects), "points": len(rows), "label_counts": label_counts}

payload = {
    "source_blend": bpy.data.filepath,
    "exports": exports,
    "counts": counts,
}
with open(os.path.join(OUT_DIR, "current_visual_samples.json"), "w", encoding="utf-8") as f:
    json.dump(payload, f)
print(json.dumps({"source_blend": bpy.data.filepath, "counts": counts}, ensure_ascii=False))
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
    payload = json.loads((out_dir / "current_visual_samples.json").read_text(encoding="utf-8"))
    las_dir = out_dir / "las_export"
    las_dir.mkdir(parents=True, exist_ok=True)
    metas = []
    for time in TIMES:
        arr = np.asarray(payload["exports"].get(time, []), dtype=np.float64)
        if arr.size == 0:
            arr = np.empty((0, 9), dtype=np.float64)
        txt_path = out_dir / f"{time}.txt"
        np.savetxt(txt_path, arr, fmt="%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.0f %.0f", header=HEADER, comments="# ")
        las_path = las_dir / f"{time}.las"
        if len(arr):
            write_las(las_path, arr)
        label_counts = {str(int(label)): int((arr[:, 7] == label).sum()) for label in sorted(set(arr[:, 7].astype(int)))} if len(arr) else {}
        meta = {
            "time": time,
            "file": f"{time}.txt",
            "las": str(las_path) if len(arr) else "",
            "points": int(len(arr)),
            "objects": int(payload["counts"].get(time, {}).get("objects", 0)),
            "label_counts": label_counts,
        }
        (out_dir / f"{time}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        metas.append(meta)

    manifest = {
        "dataset": out_dir.name,
        "created_by": "tools/export_current_visual_blend_interior_t0t5.py",
        "source_blend": payload.get("source_blend", ""),
        "columns": HEADER,
        "labels": LABELS,
        "damage_types": DAMAGE_TYPES,
        "times": metas,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out_dir / "README.md").write_text(
        "# Current Visual Blend Interior T0-T5 Dataset\n\n"
        "Exported from the selected Blender visual scene. Keeps full interior objects grouped by T0-T5 prefixes.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--out", default=str(OUT_DIR))
    parser.add_argument("--timeout", type=float, default=600.0)
    args = parser.parse_args()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    code = BLENDER_CODE.replace("__OUT_DIR__", str(out_dir).replace("\\", "\\\\"))
    code = code.replace("__LABELS_JSON__", json.dumps(LABELS)).replace("__DAMAGE_TYPES_JSON__", json.dumps(DAMAGE_TYPES))
    (out_dir / "export_visual_blend_code.py").write_text(code, encoding="utf-8")
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

