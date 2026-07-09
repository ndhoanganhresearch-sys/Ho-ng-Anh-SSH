r"""Create a curved version of the standard combined tunnel dataset.

This script bends both the point clouds and a Blender visual scene along a
horizontal circular arc. The source dataset is left untouched.
"""
from __future__ import annotations
import argparse, json, socket
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "data" / "tunnel_t0t5_blend_combined_damage_interior"
OUT_DIR = ROOT / "data" / "tunnel_t0t5_blend_curved_interior"
TIMES = ["T0", "T1", "T2", "T3", "T4", "T5"]
RADIUS_M = 420.0
HEADER = "x y z nx ny nz intensity label damage_type"

BLENDER_CODE = r"""
import bpy, json, math
from pathlib import Path
import numpy as np
OUT_DIR=Path(r"__OUT_DIR__")
RADIUS=float("__RADIUS__")
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
mat_cache={}
def mat_for(label):
    colors={1:(.55,.55,.52,1),2:(.12,.12,.13,1),3:(.22,.16,.11,1),4:(.38,.36,.33,1),5:(.03,.03,.03,1),6:(.18,.20,.22,1),7:(1,.92,.45,1),8:(.18,.24,.30,1),9:(.96,.96,.9,1),10:(.95,.75,.18,1),20:(.20,.12,.10,1),21:(.02,.02,.02,1),22:(.1,.35,.55,1)}
    if label not in mat_cache:
        m=bpy.data.materials.new('label_'+str(label)); m.diffuse_color=colors.get(label,(.7,.7,.7,1)); mat_cache[label]=m
    return mat_cache[label]
def make_cloud(time, x_offset):
    arr=np.loadtxt(OUT_DIR / (time+'.txt'), comments='#')
    step=max(1, len(arr)//18000)
    arr=arr[::step]
    by_label={}
    for row in arr:
        by_label.setdefault(int(row[7]), []).append((float(row[0])+x_offset,float(row[1]),float(row[2])))
    for label, pts in by_label.items():
        mesh=bpy.data.meshes.new(time+'_label_'+str(label)+'_mesh')
        mesh.from_pydata(pts, [], [])
        mesh.update()
        obj=bpy.data.objects.new(time+'_label_'+str(label), mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(mat_for(label))
        obj.show_name=False
for idx,time in enumerate(['T0','T1','T2','T3','T4','T5']):
    make_cloud(time, idx*10.0)
# Draw centerline arc guide for T0 coordinate frame.
pts=[]
for y in np.linspace(0,80,120):
    phi=y/RADIUS; pts.append((RADIUS*(1-math.cos(phi)), y, -1.72))
mesh=bpy.data.meshes.new('curved_centerline_mesh'); mesh.from_pydata(pts, [(i,i+1) for i in range(len(pts)-1)], []); mesh.update()
obj=bpy.data.objects.new('curved_centerline_R420m', mesh); bpy.context.collection.objects.link(obj)
bpy.ops.object.light_add(type='SUN', location=(8,-12,12))
bpy.ops.object.camera_add(location=(18,-42,15), rotation=(math.radians(70),0,math.radians(22)))
bpy.context.scene.camera=bpy.context.view_layer.objects.active
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / 'tunnel_t0t5_blend_curved_interior.blend'))
print(json.dumps({'status':'ok','blend':str(OUT_DIR / 'tunnel_t0t5_blend_curved_interior.blend')}))
"""

def bend_points(points: np.ndarray, y_min: float, radius: float) -> np.ndarray:
    x = points[:, 0]
    y = points[:, 1] - y_min
    z = points[:, 2]
    phi = y / radius
    center_x = radius * (1.0 - np.cos(phi))
    center_y = radius * np.sin(phi)
    nx = np.cos(phi)
    ny = -np.sin(phi)
    bx = center_x + x * nx
    by = center_y + x * ny
    return np.column_stack([bx, by, z])

def bend_normals(normals: np.ndarray, y: np.ndarray, y_min: float, radius: float) -> np.ndarray:
    phi = (y - y_min) / radius
    nx = normals[:, 0] * np.cos(phi) + normals[:, 1] * np.sin(phi)
    ny = -normals[:, 0] * np.sin(phi) + normals[:, 1] * np.cos(phi)
    return np.column_stack([nx, ny, normals[:, 2]])

def write_curved(radius: float) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metas=[]
    y_min_global=None
    src_arrays={}
    for time in TIMES:
        arr=np.loadtxt(SRC_DIR / f"{time}.txt", comments="#")
        src_arrays[time]=arr
        y_min_global = arr[:,1].min() if y_min_global is None else min(y_min_global, arr[:,1].min())
    for time, arr in src_arrays.items():
        out=arr.copy()
        out[:,:3]=bend_points(arr[:,:3], y_min_global, radius)
        out[:,3:6]=bend_normals(arr[:,3:6], arr[:,1], y_min_global, radius)
        np.savetxt(OUT_DIR / f"{time}.txt", out, fmt="%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.0f %.0f", header=HEADER, comments="# ")
        meta=json.loads((SRC_DIR / f"{time}.json").read_text(encoding="utf-8"))
        meta.update({"file": f"{time}.txt", "source_file": str(SRC_DIR / f"{time}.txt"), "curve_radius_m": radius, "curve_model": "horizontal circular arc; chainage y mapped to phi=(y-y_min)/R"})
        (OUT_DIR / f"{time}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        metas.append(meta)
    src_manifest=json.loads((SRC_DIR / "manifest.json").read_text(encoding="utf-8"))
    manifest={"dataset": OUT_DIR.name, "created_by": "tools/create_curved_interior_dataset.py", "source_dataset": str(SRC_DIR), "curve_radius_m": radius, "columns": HEADER, "labels": src_manifest.get("labels", {}), "damage_types": src_manifest.get("damage_types", {}), "realistic_components": src_manifest.get("realistic_components", []), "times": metas}
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if (SRC_DIR / "ground_truth.csv").exists():
        (OUT_DIR / "ground_truth.csv").write_text((SRC_DIR / "ground_truth.csv").read_text(encoding="utf-8"), encoding="utf-8")
    (OUT_DIR / "README.md").write_text(f"# Curved Tunnel Interior Dataset\n\nDerived from `{SRC_DIR}` and bent along a horizontal circular arc with radius `{radius}` m. Point clouds and normals are curved; labels and damage types are preserved.\n", encoding="utf-8")

def send_blender_command(command_type: str, params: dict, host: str, port: int, timeout: float = 900.0) -> dict:
    payload={"type": command_type, "params": params}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout); sock.connect((host, port)); sock.sendall(json.dumps(payload).encode("utf-8"))
        chunks=[]
        while True:
            b=sock.recv(8192)
            if not b: break
            chunks.append(b)
            try: return json.loads(b"".join(chunks).decode("utf-8"))
            except json.JSONDecodeError: pass
    raise RuntimeError("No complete JSON response received from Blender MCP")

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radius", type=float, default=RADIUS_M)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--skip-blender", action="store_true")
    args=parser.parse_args()
    write_curved(args.radius)
    if not args.skip_blender:
        code=BLENDER_CODE.replace("__OUT_DIR__", str(OUT_DIR).replace("\\", "\\\\")).replace("__RADIUS__", str(args.radius))
        resp=send_blender_command("execute_code", {"code": code}, args.host, args.port)
        if resp.get("status") != "success": print(json.dumps(resp, indent=2, ensure_ascii=False)); return 1
        print(json.dumps(resp.get("result", resp), indent=2, ensure_ascii=False))
    print(f"Curved dataset written to: {OUT_DIR}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
