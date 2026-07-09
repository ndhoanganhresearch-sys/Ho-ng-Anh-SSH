r"""Create a standard T0-T5 Blender scene from data/sample_pcd/Tunel.blend.

This creates the Blender artifact first, before LAS export:
- opens the sample Tunel.blend;
- duplicates the sample scene into six epoch collections T0-T5;
- applies controlled deformation only to tunnel lining meshes per epoch;
- arranges epochs side-by-side for visual inspection;
- adds materials, labels, lights, and camera;
- saves a clean .blend file.

No LAS export and no raycasting are performed here.

Run from tunnel_project while Blender MCP listens on localhost:9876:
    ..\.venv\Scripts\python.exe tools\create_standard_t0t5_blend_from_sample.py
"""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "sample_pcd" / "Tunel.blend"
DEFAULT_OUT = ROOT / "data" / "sample_blend_standard_t0t5" / "Tunel_T0_T5_standard.blend"

BLENDER_CODE = r'''
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

SOURCE_BLEND = Path(r"__SOURCE_BLEND__")
OUT_BLEND = Path(r"__OUT_BLEND__")
OUT_BLEND.parent.mkdir(parents=True, exist_ok=True)

EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
CROWN_MM = {"T0": 0.0, "T1": -4.0, "T2": -9.0, "T3": -16.0, "T4": -25.0, "T5": -36.0}
CONV_MM = {"T0": 0.0, "T1": -1.0, "T2": -4.0, "T3": -9.0, "T4": -15.0, "T5": -24.0}
LOCAL_MM = {"T0": 0.0, "T1": 0.0, "T2": 0.0, "T3": -8.0, "T4": -17.0, "T5": -30.0}
EPOCH_COLORS = {
    "T0": (0.55, 0.55, 0.55, 1.0),
    "T1": (0.25, 0.55, 0.90, 1.0),
    "T2": (0.25, 0.75, 0.45, 1.0),
    "T3": (0.95, 0.65, 0.25, 1.0),
    "T4": (0.95, 0.35, 0.25, 1.0),
    "T5": (0.75, 0.20, 0.20, 1.0),
}
LINING_OBJECTS = {"Cylinder", "Cylinder.003"}
EPOCH_SPACING_X = 5.5


def scene_mesh_objects():
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and len(obj.data.vertices) > 0]


def scene_bounds(objects):
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for obj in objects:
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            mins.x = min(mins.x, w.x)
            mins.y = min(mins.y, w.y)
            mins.z = min(mins.z, w.z)
            maxs.x = max(maxs.x, w.x)
            maxs.y = max(maxs.y, w.y)
            maxs.z = max(maxs.z, w.z)
    return mins, maxs


def make_material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def duplicate_object_to_collection(obj, collection, epoch, x_offset, epoch_mat, support_mat):
    new_mesh = obj.data.copy()
    new_obj = obj.copy()
    new_obj.data = new_mesh
    new_obj.animation_data_clear()
    new_obj.name = f"{epoch}_{obj.name}"
    new_obj.location.x += x_offset
    new_obj["source_object"] = obj.name
    new_obj["epoch"] = epoch
    new_obj["role"] = "lining" if obj.name in LINING_OBJECTS else "sample_context"
    new_obj.data.materials.clear()
    new_obj.data.materials.append(epoch_mat if obj.name in LINING_OBJECTS else support_mat)
    collection.objects.link(new_obj)
    return new_obj


def deform_epoch_objects(epoch, objects, source_bounds):
    if epoch == "T0":
        return
    mins, maxs = source_bounds
    y0, y1 = mins.y, maxs.y
    length = max(1e-9, y1 - y0)
    cx = (mins.x + maxs.x) * 0.5
    cz = (mins.z + maxs.z) * 0.5
    crown = CROWN_MM[epoch] / 1000.0
    conv = CONV_MM[epoch] / 1000.0
    local = LOCAL_MM[epoch] / 1000.0
    for obj in objects:
        if obj.get("source_object") not in LINING_OBJECTS:
            continue
        mw = obj.matrix_world.copy()
        inv = mw.inverted()
        # Use world coordinates minus epoch layout offset, so deformation is based
        # on the original Tunel.blend coordinate system.
        x_offset = obj.location.x
        for vert in obj.data.vertices:
            w = mw @ vert.co
            original_x = w.x - x_offset
            yn = (w.y - y0) / length
            theta = math.atan2(w.z - cz, original_x - cx)
            crown_w = math.exp(-0.5 * ((yn - 0.30) / 0.10) ** 2) * max(0.0, math.sin(theta)) ** 1.6
            side_w = math.exp(-0.5 * ((yn - 0.58) / 0.13) ** 2) * abs(math.cos(theta)) ** 1.4
            local_angle = math.atan2(math.sin(theta - math.radians(62.0)), math.cos(theta - math.radians(62.0)))
            local_w = math.exp(-0.5 * ((yn - 0.78) / 0.060) ** 2) * math.exp(-0.5 * (local_angle / 0.25) ** 2)
            w.z += crown * crown_w + local * local_w
            w.x += -math.copysign(abs(conv) * side_w, original_x - cx)
            vert.co = inv @ w
        obj.data.update()


def add_epoch_label(epoch, x_offset, source_bounds, collection):
    mins, maxs = source_bounds
    bpy.ops.object.text_add(location=(x_offset + (mins.x + maxs.x) * 0.5, mins.y - 3.0, maxs.z + 0.8), rotation=(math.radians(75), 0, 0))
    txt = bpy.context.view_layer.objects.active
    txt.name = f"{epoch}_label"
    txt.data.body = f"{epoch}  crown={CROWN_MM[epoch]:.0f}mm  conv={CONV_MM[epoch]:.0f}mm  local={LOCAL_MM[epoch]:.0f}mm"
    txt.data.align_x = "CENTER"
    txt.data.size = 0.55
    # Move text from master collection to epoch collection.
    for col in list(txt.users_collection):
        col.objects.unlink(txt)
    collection.objects.link(txt)


def main():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))
    source_objects = scene_mesh_objects()
    source_bounds = scene_bounds(source_objects)

    # Keep source scene hidden in a reference collection for traceability.
    source_col = bpy.data.collections.new("SOURCE_Tunel_blend_hidden")
    bpy.context.scene.collection.children.link(source_col)
    for obj in source_objects:
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        source_col.objects.link(obj)
        obj.hide_viewport = True
        obj.hide_render = True

    support_mat = make_material("sample_context_dark_gray", (0.18, 0.18, 0.18, 1.0))
    epoch_summaries = []
    for idx, epoch in enumerate(EPOCHS):
        collection = bpy.data.collections.new(f"{epoch}_sample_blend_epoch")
        bpy.context.scene.collection.children.link(collection)
        epoch_mat = make_material(f"{epoch}_lining_material", EPOCH_COLORS[epoch])
        x_offset = idx * EPOCH_SPACING_X
        epoch_objects = [duplicate_object_to_collection(obj, collection, epoch, x_offset, epoch_mat, support_mat) for obj in source_objects]
        deform_epoch_objects(epoch, epoch_objects, source_bounds)
        add_epoch_label(epoch, x_offset, source_bounds, collection)
        epoch_summaries.append({
            "epoch": epoch,
            "collection": collection.name,
            "objects": len(epoch_objects),
            "x_offset": x_offset,
            "deformation_mm": {
                "crown_settlement": CROWN_MM[epoch],
                "sidewall_convergence": CONV_MM[epoch],
                "local_damage": LOCAL_MM[epoch],
            },
        })

    # Add guide axes / lighting / camera.
    bpy.ops.object.light_add(type="SUN", location=(18, -30, 25))
    bpy.context.view_layer.objects.active.name = "Sun_standard_T0_T5"
    bpy.ops.object.camera_add(location=(20, -45, 18), rotation=(math.radians(68), 0, math.radians(25)))
    bpy.context.scene.camera = bpy.context.view_layer.objects.active

    meta = {
        "source_blend": str(SOURCE_BLEND),
        "output_blend": str(OUT_BLEND),
        "method": "duplicate sample Tunel.blend meshes into T0-T5 epoch collections and deform lining meshes only",
        "source_bounds_min": [source_bounds[0].x, source_bounds[0].y, source_bounds[0].z],
        "source_bounds_max": [source_bounds[1].x, source_bounds[1].y, source_bounds[1].z],
        "epochs": epoch_summaries,
    }
    (OUT_BLEND.parent / "Tunel_T0_T5_standard_manifest.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
    print(json.dumps({"status": "ok", "blend": str(OUT_BLEND), "epochs": len(EPOCHS), "source_objects": len(source_objects)}, indent=2))

main()
'''


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    args = parser.parse_args()

    source = Path(args.source).resolve()
    out = Path(args.out).resolve()
    code = (
        BLENDER_CODE
        .replace("__SOURCE_BLEND__", str(source).replace("\\", "\\\\"))
        .replace("__OUT_BLEND__", str(out).replace("\\", "\\\\"))
    )
    response = send_blender_command("execute_code", {"code": code}, args.host, args.port)
    if response.get("status") != "success":
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps(response.get("result", response), indent=2, ensure_ascii=False))
    print(f"Standard blend written to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

