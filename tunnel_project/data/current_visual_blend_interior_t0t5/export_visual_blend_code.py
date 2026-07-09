
import bpy
import json
import mathutils
import os

OUT_DIR = r"C:\\Users\\ssl\\Desktop\\Code Python\\data python cusor\\tunnel_project\\data\\current_visual_blend_interior_t0t5"
os.makedirs(OUT_DIR, exist_ok=True)

LABELS = {"lining": 1, "rail": 2, "sleeper": 3, "walkway": 4, "cable_tray": 5, "pipe": 6, "light": 7, "equipment": 8, "target": 9, "sign": 10, "spalling": 20, "crack": 21, "leak": 22}
DAMAGE_TYPES = {"none": 0, "crown_settlement": 1, "sidewall_convergence": 2, "spalling": 3, "crack": 4, "leak": 5}
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
