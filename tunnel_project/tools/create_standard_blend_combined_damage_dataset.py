r"""Create combined-damage/interior point clouds from the standard T0-T5 blend.

Source: data/tunnel_t0t5_blend/Tunel_T0_T5_standard.blend and las_export/T*.npy.
The source blend is opened through Blender MCP, interiors/spalling markers are added,
and a derived point-cloud dataset is written without changing the standard source.
"""
from __future__ import annotations
import argparse, json, socket
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "data" / "tunnel_t0t5_blend"
SRC_BLEND = SRC_DIR / "Tunel_T0_T5_standard.blend"
OUT_DIR = ROOT / "data" / "tunnel_t0t5_blend_combined_damage_interior"
TIMES = ["T0", "T1", "T2", "T3", "T4", "T5"]
LABELS = {"lining": 1, "rail": 2, "sleeper": 3, "walkway": 4, "cable_tray": 5, "pipe": 6, "light": 7, "equipment": 8, "target": 9, "sign": 10, "spalling": 20, "crack": 21, "leak": 22}
DAMAGE = {"none": 0, "crown_settlement": 1, "sidewall_convergence": 2, "spalling": 3, "crack": 4, "leak": 5}
INTENSITY = {"lining": .50, "rail": .82, "sleeper": .34, "walkway": .42, "cable_tray": .22, "pipe": .36, "light": .92, "equipment": .55, "target": .98, "sign": .75, "spalling": .30, "crack": .14, "leak": .62}
CROWN = {"T0": 0, "T1": -5, "T2": -12, "T3": -20, "T4": -30, "T5": -45}
LOCAL = {"T0": 0, "T1": 0, "T2": 0, "T3": -15, "T4": -25, "T5": -40}
SPALL = {"T0": 0, "T1": 0, "T2": -8, "T3": -20, "T4": -34, "T5": -48}
CRACK = {"T0": 0, "T1": 0, "T2": 2, "T3": 5, "T4": 8, "T5": 12}
HEADER = "x y z nx ny nz intensity label damage_type"

BLENDER_CODE = r"""
import bpy, math, json
from pathlib import Path
SRC_BLEND = Path(r"__SRC_BLEND__")
OUT_BLEND = Path(r"__OUT_BLEND__")
bpy.ops.wm.open_mainfile(filepath=str(SRC_BLEND))
def mat(n,c):
    m=bpy.data.materials.get(n) or bpy.data.materials.new(n); m.diffuse_color=c; return m
ms={
 'rail':mat('derived_rail',(.12,.12,.13,1)), 'sleeper':mat('derived_sleeper',(.22,.16,.11,1)),
 'walkway':mat('derived_walkway',(.38,.36,.33,1)), 'cable':mat('derived_cable_tray',(.03,.03,.03,1)),
 'pipe':mat('derived_pipe',(.18,.20,.22,1)), 'light':mat('derived_light',(1,.92,.45,1)),
 'equip':mat('derived_equipment',(.18,.24,.30,1)), 'target':mat('derived_target',(.96,.96,.9,1)),
 'sign':mat('derived_sign',(.95,.75,.18,1)), 'spall':mat('derived_spalling',(.20,.12,.10,1)),
 'crack':mat('derived_crack',(.02,.02,.02,1)), 'leak':mat('derived_leak',(.1,.35,.55,1))}
def cube(n,loc,scale,m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o=bpy.context.view_layer.objects.active; o.name=n; o.dimensions=scale; bpy.ops.object.transform_apply(location=False, rotation=False, scale=True); o.data.materials.append(m); return o
def cyl(n,loc,r,depth,m,rot=(0,0,0),verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot); o=bpy.context.view_layer.objects.active; o.name=n; o.data.materials.append(m); return o
def add_visual_components(prefix, ox):
    for x in (-.22,.22): cube(prefix+'_rail',(ox+x,39,.08),(.035,78,.045),ms['rail'])
    for y in [i*1.2 for i in range(1,66)]: cube(prefix+'_sleeper',(ox,y,.02),(.70,.12,.045),ms['sleeper'])
    for x in (-.78,.78): cube(prefix+'_maintenance_ledge',(ox+x,39,.10),(.16,76,.055),ms['walkway'])
    for x in (-.84,.84): cube(prefix+'_cable_tray',(ox+x,39,.62),(.045,74,.055),ms['cable']); cyl(prefix+'_service_pipe',(ox+x*.96,39,.92),.022,74,ms['pipe'],(math.radians(90),0,0),12)
    for x,z in [(-.70,.03),(.70,.03)]: cyl(prefix+'_drainage_pipe',(ox+x,39,z),.026,74,ms['pipe'],(math.radians(90),0,0),12)
    for z in (.72,.82,.92): cyl(prefix+'_cable_bundle',(ox+.86,39,z),.012,74,ms['cable'],(math.radians(90),0,0),8)
    for y in range(8,75,12): cube(prefix+'_light_bracket',(ox,y,1.48),(.26,.035,.030),ms['cable']); cyl(prefix+'_low_profile_light',(ox,y,1.56),.038,.075,ms['light']); cube(prefix+'_junction_box',(ox-.78,y+1.2,.42),(.10,.22,.18),ms['equip'])
    for x in (-.72,.72): cyl(prefix+'_handrail_top',(ox+x,39,.45),.013,76,ms['pipe'],(math.radians(90),0,0),8); cyl(prefix+'_handrail_mid',(ox+x,39,.30),.010,76,ms['pipe'],(math.radians(90),0,0),8)
    for y in range(6,78,6):
        for x in (-.72,.72): cyl(prefix+'_handrail_post',(ox+x,y,.18),.010,.30,ms['pipe'],(0,0,0),8)
    for x in (-.68,.68): cube(prefix+'_drainage_channel',(ox+x,39,.01),(.08,76,.025),ms['pipe'])
    for y in range(10,75,16): cube(prefix+'_signal_cabinet',(ox+.76,y,.40),(.10,.22,.22),ms['equip']); cube(prefix+'_chainage_plate',(ox-.86,y,.70),(.020,.18,.10),ms['sign'])
    for y in range(14,75,20): cyl(prefix+'_fire_extinguisher',(ox-.76,y,.32),.025,.18,ms['sign'],(0,0,0),12)
    for y in (20,44,68): cube(prefix+'_small_sign',(ox+.86,y,.78),(.020,.26,.14),ms['sign'])
    for y in (12,30,48,66):
        for x in (-.56,.56): bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=.040, location=(ox+x,y,1.18)); bpy.context.view_layer.objects.active.name=prefix+'_registration_target'; bpy.context.view_layer.objects.active.data.materials.append(ms['target'])
    for y in [58+i*.45 for i in range(9)]: cube(prefix+'_spalling_marker',(ox+.48,y,1.12),(.065,.12,.030),ms['spall'])
    for y in [34+i*.75 for i in range(10)]: cube(prefix+'_crack_marker',(ox-.52,y,1.05),(.014,.12,.018),ms['crack'])
    for y in [40+i*.65 for i in range(10)]: cube(prefix+'_leak_marker',(ox+.38,y,1.32),(.018,.10,.030),ms['leak'])
for name in ['T0_lining','T1_lining','T2_lining','T3_lining','T4_lining','T5_lining']:
    obj=bpy.data.objects.get(name)
    if obj: add_visual_components(name.replace('_lining',''), obj.location.x)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
print(json.dumps({'status':'ok','opened':str(SRC_BLEND),'saved':str(OUT_BLEND)}))
"""

def gaussian(y, center, sigma):
    return np.exp(-0.5 * ((y - center) / sigma) ** 2)

def normals_from_points(points: np.ndarray) -> np.ndarray:
    center = np.array([0.0, 0.0, 0.823])
    radial = points - center
    radial[:, 1] = 0.0
    norm = np.linalg.norm(radial, axis=1)
    norm[norm == 0] = 1.0
    return radial / norm[:, None]

def lining_rows(time: str) -> np.ndarray:
    points = np.load(SRC_DIR / "las_export" / f"{time}.npy")
    normals = normals_from_points(points)
    y = points[:, 1]
    theta = np.arctan2(points[:, 2] - 0.823, points[:, 0])
    damage = np.zeros(len(points), dtype=np.float64)
    labels = np.full(len(points), LABELS["lining"], dtype=np.float64)
    crown_mask = (CROWN[time] != 0) & (gaussian(y, 40.0, 18.0) * np.maximum(0, np.sin(theta)) > 0.18)
    local_mask = (LOCAL[time] != 0) & (gaussian(y, 60.0, 3.0) * np.exp(-0.5 * ((theta - np.deg2rad(62.0)) / 0.25) ** 2) > 0.22)
    spall_mask = (SPALL[time] != 0) & (gaussian(y, 58.0, 2.8) * np.exp(-0.5 * ((theta - np.deg2rad(50.0)) / 0.18) ** 2) > 0.18)
    crack_mask = (CRACK[time] != 0) & (gaussian(y, 36.0, 6.0) * np.exp(-0.5 * ((theta - np.deg2rad(132.0)) / 0.07) ** 2) > 0.28)
    leak_mask = (time in {"T3", "T4", "T5"}) & (gaussian(y, 42.0, 5.0) * np.exp(-0.5 * ((theta - np.deg2rad(72.0)) / 0.10) ** 2) > 0.25)
    damage[crown_mask] = DAMAGE["crown_settlement"]
    damage[local_mask] = DAMAGE["sidewall_convergence"]
    damage[spall_mask] = DAMAGE["spalling"]; labels[spall_mask] = LABELS["spalling"]
    damage[crack_mask] = DAMAGE["crack"]; labels[crack_mask] = LABELS["crack"]
    damage[leak_mask] = DAMAGE["leak"]; labels[leak_mask] = LABELS["leak"]
    intensity = np.full(len(points), INTENSITY["lining"], dtype=np.float64)
    intensity[labels == LABELS["spalling"]] = INTENSITY["spalling"]
    intensity[labels == LABELS["crack"]] = INTENSITY["crack"]
    intensity[labels == LABELS["leak"]] = INTENSITY["leak"]
    return np.column_stack([points, normals, intensity, labels, damage])

def box_points(label: str, center, size, counts):
    cx, cy, cz = center; sx, sy, sz = size; nx, ny, nz = counts
    xs = np.linspace(cx - sx/2, cx + sx/2, nx); ys = np.linspace(cy - sy/2, cy + sy/2, ny); zs = np.linspace(cz - sz/2, cz + sz/2, nz)
    pts = np.array([[x, y, z] for x in xs for y in ys for z in zs], dtype=float)
    normals = np.tile([0, 0, 1], (len(pts), 1))
    return np.column_stack([pts, normals, np.full(len(pts), INTENSITY[label]), np.full(len(pts), LABELS[label]), np.zeros(len(pts))])

def cyl_y_points(label: str, center, radius, length, ns=100, nt=10):
    cx, cy, cz = center
    rows = []
    for y in np.linspace(cy - length/2, cy + length/2, ns):
        for t in np.linspace(0, 2*np.pi, nt, endpoint=False):
            rows.append([cx + radius*np.cos(t), y, cz + radius*np.sin(t), np.cos(t), 0, np.sin(t), INTENSITY[label], LABELS[label], 0])
    return np.asarray(rows, dtype=float)

def interior_rows() -> np.ndarray:
    rows = []
    for x in (-.53, .53): rows.append(box_points("rail", (x, 39, -1.46), (.07, 78, .09), (3, 220, 3)))
    for yy in np.arange(1.2, 78.1, 1.2): rows.append(box_points("sleeper", (0, yy, -1.56), (1.55, .14, .08), (12, 2, 2)))
    for x in (-2.32, 2.32): rows.append(box_points("walkway", (x, 39, -1.24), (.38, 76, .10), (5, 150, 2)))
    for x in (-2.42, 2.42): rows.append(box_points("cable_tray", (x, 39, .62), (.10, 74, .10), (3, 120, 3))); rows.append(cyl_y_points("pipe", (x*.94, 39, 1.28), .045, 74, 90, 10))
    for x,z in [(-2.18,-1.47),(2.18,-1.47)]: rows.append(cyl_y_points("pipe", (x, 39, z), .055, 74, 90, 10))
    for z in (.88, 1.02, 1.16): rows.append(cyl_y_points("cable_tray", (2.34, 39, z), .025, 74, 90, 8))
    for yy in range(8, 75, 12): rows.append(cyl_y_points("light", (0, yy, 2.92), .07, .12, 2, 16)); rows.append(box_points("equipment", (-2.36, yy+1.2, -.35), (.20, .28, .34), (3, 3, 5))); rows.append(box_points("cable_tray", (0, yy, 2.82), (.42, .045, .045), (7, 2, 2))); rows.append(box_points("rail", (-.53, yy, -1.39), (.20, .05, .035), (4, 2, 2))); rows.append(box_points("rail", (.53, yy, -1.39), (.20, .05, .035), (4, 2, 2)))
    for x in (-2.10, 2.10): rows.append(cyl_y_points("pipe", (x, 39, -.72), .025, 76, 120, 8)); rows.append(cyl_y_points("pipe", (x, 39, -.98), .018, 76, 120, 8))
    for yy in range(6, 78, 6):
        for x in (-2.10, 2.10): rows.append(box_points("pipe", (x, yy, -1.06), (.045, .045, .54), (2, 2, 8)))
    for x in (-2.02, 2.02): rows.append(box_points("pipe", (x, 39, -1.61), (.18, 76, .045), (4, 150, 2)))
    for yy in range(10, 75, 16): rows.append(box_points("equipment", (2.28, yy, -.72), (.22, .26, .42), (3, 3, 5))); rows.append(box_points("sign", (-2.48, yy, .35), (.035, .24, .16), (2, 5, 3)))
    for yy in range(14, 75, 20): rows.append(cyl_y_points("sign", (-2.18, yy, -.88), .045, .30, 2, 14))
    for yy in (20, 44, 68): rows.append(box_points("sign", (2.46, yy, .72), (.035, .38, .24), (2, 7, 4)))
    return np.vstack(rows)

def write_outputs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    interior = interior_rows()
    metas = []
    for time in TIMES:
        rows = np.vstack([lining_rows(time), interior])
        np.savetxt(OUT_DIR / f"{time}.txt", rows, fmt="%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.0f %.0f", header=HEADER, comments="# ")
        meta = {"time": time, "file": f"{time}.txt", "points": int(len(rows)), "source_npy": str(SRC_DIR / "las_export" / f"{time}.npy"), "crown_settlement_mm": CROWN[time], "local_damage_mm": LOCAL[time], "spalling_depth_mm": SPALL[time], "crack_opening_mm": CRACK[time]}
        (OUT_DIR / f"{time}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        metas.append(meta)
    (OUT_DIR / "manifest.json").write_text(json.dumps({"dataset": OUT_DIR.name, "created_by": "tools/create_standard_blend_combined_damage_dataset.py", "source_blend": str(SRC_BLEND), "source_point_clouds": str(SRC_DIR / "las_export"), "columns": HEADER, "labels": LABELS, "damage_types": DAMAGE, "realistic_components": ["narrow gauge rails", "sleepers", "track fasteners", "maintenance ledges", "handrails", "drainage channels", "side drainage pipes", "service pipes", "cable trays", "cable bundles", "low-profile lights", "light brackets", "junction boxes", "signal cabinets", "chainage plates", "safety signs", "registration targets"], "times": metas}, indent=2), encoding="utf-8")
    with (OUT_DIR / "ground_truth.csv").open("w", encoding="utf-8") as f:
        f.write("time,damage_type,chainage_m,theta_deg,value_mm,description\n")
        for t in TIMES:
            f.write(f"{t},crown_settlement,40,90,{CROWN[t]},standard blend crown settlement\n")
            f.write(f"{t},local_damage,60,62,{LOCAL[t]},standard blend local right-shoulder dent\n")
            f.write(f"{t},spalling,58,50,{SPALL[t]},added spalling/delamination label on standard geometry\n")
            f.write(f"{t},crack,36,132,{CRACK[t]},added crack label on standard geometry\n")
    (OUT_DIR / "README.md").write_text(f"# Standard Blend Combined Damage + Interior Dataset\n\nDerived from `{SRC_BLEND}` and `{SRC_DIR / 'las_export'}`. The original standard blend is not modified. Use `T0.txt` as reference and `T1.txt`...`T5.txt` as monitoring times.\n", encoding="utf-8")

def send_blender_command(command_type: str, params: dict, host: str, port: int, timeout: float = 900.0) -> dict:
    payload = {"type": command_type, "params": params}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout); sock.connect((host, port)); sock.sendall(json.dumps(payload).encode("utf-8"))
        chunks = []
        while True:
            chunk = sock.recv(8192)
            if not chunk: break
            chunks.append(chunk); data = b"".join(chunks)
            try: return json.loads(data.decode("utf-8"))
            except json.JSONDecodeError: pass
    raise RuntimeError("No complete JSON response received from Blender MCP")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost"); parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--skip-blender", action="store_true")
    args = parser.parse_args()
    write_outputs()
    if not args.skip_blender:
        out_blend = OUT_DIR / "Tunel_T0_T5_standard_combined_damage_interior.blend"
        code = BLENDER_CODE.replace("__SRC_BLEND__", str(SRC_BLEND).replace("\\", "\\\\")).replace("__OUT_BLEND__", str(out_blend).replace("\\", "\\\\"))
        response = send_blender_command("execute_code", {"code": code}, args.host, args.port)
        if response.get("status") != "success": print(json.dumps(response, indent=2, ensure_ascii=False)); return 1
        print(json.dumps(response.get("result", response), indent=2, ensure_ascii=False))
    print(f"Dataset written to: {OUT_DIR}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
