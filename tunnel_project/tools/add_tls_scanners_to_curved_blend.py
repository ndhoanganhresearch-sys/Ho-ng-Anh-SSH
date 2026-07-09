from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLEND_PATH = ROOT / "data" / "curved_real_scale_railway_tunnel_t0t5" / "curved_real_scale_railway_tunnel_t0t5.blend"

BLENDER_CODE = r'''
import bpy, json, math, os
from mathutils import Vector

BLEND_PATH = r"__BLEND_PATH__"
CURVE_R = 420.0
STATIONS = [8.0, 25.0, 42.0, 59.0, 76.0, 93.0, 110.0]

if BLEND_PATH and os.path.exists(BLEND_PATH) and os.path.abspath(bpy.data.filepath) != os.path.abspath(BLEND_PATH):
    bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)

def mat(name, color):
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
    material.diffuse_color = color
    return material

MAT_BODY = mat('tls_scanner_body_dark_gray', (0.08, 0.09, 0.10, 1.0))
MAT_HEAD = mat('tls_scanner_head_blue', (0.05, 0.28, 0.80, 1.0))
MAT_TRIPOD = mat('tls_scanner_tripod_black', (0.02, 0.02, 0.025, 1.0))
MAT_BEAM = mat('tls_scanner_ray_fan_green', (0.10, 0.85, 0.35, 1.0))

def center(s):
    return Vector((CURVE_R * (1.0 - math.cos(s / CURVE_R)), CURVE_R * math.sin(s / CURVE_R), 0.0))

def right_vec(s):
    return Vector((math.cos(s / CURVE_R), -math.sin(s / CURVE_R), 0.0)).normalized()

def tangent_vec(s):
    return Vector((math.sin(s / CURVE_R), math.cos(s / CURVE_R), 0.0)).normalized()

def station_pose(sid, s):
    side_sway = 0.18 * math.sin(0.7 * sid)
    origin = center(s) + right_vec(s) * side_sway + Vector((0.0, 0.0, 1.45))
    return origin, tangent_vec(s), right_vec(s)

def link_to_collection(obj, collection):
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
    collection.objects.link(obj)

def make_cylinder(name, radius, depth, location, material, collection):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name + '_mesh'
    obj.data.materials.append(material)
    link_to_collection(obj, collection)
    return obj

def make_cube_between(name, p0, p1, thickness, material, collection):
    mid = (p0 + p1) * 0.5
    length = (p1 - p0).length
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=mid)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = (thickness, thickness, length)
    obj.data.materials.append(material)
    direction = (p1 - p0).normalized()
    obj.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
    link_to_collection(obj, collection)
    bpy.context.view_layer.update()
    return obj

def make_text(name, body, location, collection):
    bpy.ops.object.text_add(location=location, rotation=(math.radians(75), 0, math.radians(0)))
    obj = bpy.context.object
    obj.name = name
    obj.data.body = body
    obj.data.size = 0.45
    obj.data.align_x = 'CENTER'
    obj.data.align_y = 'CENTER'
    link_to_collection(obj, collection)
    return obj

old = bpy.data.collections.get('TLS_scanner_stations')
if old is not None:
    for obj in list(old.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(old)

collection = bpy.data.collections.new('TLS_scanner_stations')
bpy.context.scene.collection.children.link(collection)

created = []
for sid, s in enumerate(STATIONS):
    origin, tangent, right = station_pose(sid, s)
    base = origin - Vector((0, 0, 1.10))
    head = origin

    make_cylinder(f'TLS_station_{sid:02d}_tripod_center', 0.035, 1.10, base + Vector((0, 0, 0.55)), MAT_TRIPOD, collection)
    for leg_id, angle in enumerate([0, 120, 240]):
        local = right * math.cos(math.radians(angle)) + tangent * math.sin(math.radians(angle))
        foot = base + local * 0.55 - Vector((0, 0, 0.35))
        make_cube_between(f'TLS_station_{sid:02d}_tripod_leg_{leg_id}', base + Vector((0, 0, 0.30)), foot, 0.035, MAT_TRIPOD, collection)

    body = make_cylinder(f'TLS_station_{sid:02d}_scanner_body_Ch{s:.0f}m', 0.20, 0.28, head, MAT_BODY, collection)
    body.rotation_euler[1] = math.radians(90)
    make_cylinder(f'TLS_station_{sid:02d}_scanner_head_Ch{s:.0f}m', 0.13, 0.18, head + Vector((0, 0, 0.22)), MAT_HEAD, collection)

    for beam_id, az in enumerate([-55, -25, 0, 25, 55]):
        direction = (tangent * math.cos(math.radians(az)) + right * math.sin(math.radians(az)) + Vector((0, 0, 0.08))).normalized()
        make_cube_between(f'TLS_station_{sid:02d}_ray_direction_{beam_id}', head + Vector((0, 0, 0.22)), head + Vector((0, 0, 0.22)) + direction * 2.0, 0.012, MAT_BEAM, collection)

    make_text(f'TLS_station_{sid:02d}_label', f'TLS {sid}  Ch {s:.0f}m', head + Vector((0, 0, 0.75)), collection)
    created.append({'station_id': sid, 'chainage_m': s, 'x': origin.x, 'y': origin.y, 'z': origin.z})

bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
print(json.dumps({'status': 'ok', 'blend': BLEND_PATH, 'collection': 'TLS_scanner_stations', 'stations': created}, ensure_ascii=False))
'''


def send(code: str, host: str, port: int, timeout: float) -> dict:
    payload = {"type": "execute_code", "params": {"code": code}}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.sendall(json.dumps(payload).encode("utf-8"))
        chunks: list[bytes] = []
        while True:
            data = sock.recv(8192)
            if not data:
                break
            chunks.append(data)
            text = b"".join(chunks).decode("utf-8")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
    raise RuntimeError("No complete JSON response received from Blender MCP")


def main() -> int:
    parser = argparse.ArgumentParser(description="Add visible TLS scanner stations to the curved Blender tunnel.")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()

    code = BLENDER_CODE.replace("__BLEND_PATH__", str(BLEND_PATH).replace("\\", "\\\\"))
    response = send(code, args.host, args.port, args.timeout)
    if response.get("status") != "success":
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps(response.get("result", response), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
