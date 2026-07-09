
import bpy
import json
import math
import os
from mathutils import Vector

OUT_DIR = r"C:\\Users\\ssl\\Desktop\\Code Python\\data python cusor\\tunnel_project\\data\\current_blend_curved_lining_clean"
TARGET_POINTS = int("60000")
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
