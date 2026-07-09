
import bpy
import json
import math
import os
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT_DIR = r"C:\\Users\\ssl\\Desktop\\Code Python\\data python cusor\\tunnel_project\\data\\current_blend_raycast_regular"
RAY_STEP_DEG = 1.0
MAX_RANGE_M = 55.0
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
