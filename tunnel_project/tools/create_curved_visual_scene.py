r"""Create a visually curved Blender scene from the straight interior dataset.

This is option 1: visual/demo only. It keeps the analysis point clouds in
`tunnel_t0t5_blend_combined_damage_interior` unchanged and saves a separate
curved `.blend` for inspection/presentation.
"""
from __future__ import annotations
import argparse, json, socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "data" / "tunnel_t0t5_blend_combined_damage_interior"
OUT_DIR = ROOT / "data" / "tunnel_t0t5_blend_curved_visual"
RADIUS_M = 260.0

BLENDER_CODE = r"""
import bpy, json, math
from pathlib import Path
import numpy as np
SRC_DIR=Path(r"__SRC_DIR__")
OUT_DIR=Path(r"__OUT_DIR__"); OUT_DIR.mkdir(parents=True, exist_ok=True)
R=float("__RADIUS__")
TIME='T5'
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
colors={1:(.55,.55,.52,1),2:(.12,.12,.13,1),3:(.22,.16,.11,1),4:(.38,.36,.33,1),5:(.03,.03,.03,1),6:(.18,.20,.22,1),7:(1,.92,.45,1),8:(.18,.24,.30,1),9:(.96,.96,.9,1),10:(.95,.75,.18,1),20:(.20,.12,.10,1),21:(.02,.02,.02,1),22:(.1,.35,.55,1)}
mat_cache={}
def mat(label):
    if label not in mat_cache:
        m=bpy.data.materials.new('label_'+str(label)); m.diffuse_color=colors.get(label,(.7,.7,.7,1)); mat_cache[label]=m
    return mat_cache[label]
def bend(points, y_min):
    x=points[:,0]; y=points[:,1]-y_min; z=points[:,2]
    phi=y/R
    bx=R*(1-np.cos(phi))+x*np.cos(phi)
    by=R*np.sin(phi)-x*np.sin(phi)
    return np.column_stack([bx,by,z])
arr=np.loadtxt(SRC_DIR/(TIME+'.txt'), comments='#')
y_min=float(arr[:,1].min())
cur=bend(arr[:,:3], y_min)
# Make lining denser and non-structural components lighter for viewport speed.
for label in sorted(set(arr[:,7].astype(int))):
    idx=np.where(arr[:,7].astype(int)==label)[0]
    step=max(1, len(idx)//22000) if label==1 else max(1, len(idx)//5000)
    idx=idx[::step]
    pts=[tuple(p) for p in cur[idx]]
    mesh=bpy.data.meshes.new('curved_visual_label_'+str(label)+'_mesh')
    mesh.from_pydata(pts, [], [])
    mesh.update()
    obj=bpy.data.objects.new('curved_T5_label_'+str(label), mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat(label))
# Centerline and chainage ticks.
line=[]; edges=[]
for i,y in enumerate(np.linspace(0,80,161)):
    phi=y/R; line.append((R*(1-math.cos(phi)), R*math.sin(phi), -1.72))
    if i: edges.append((i-1,i))
mesh=bpy.data.meshes.new('curved_centerline_mesh'); mesh.from_pydata(line, edges, []); mesh.update()
obj=bpy.data.objects.new('curved_centerline_R'+str(int(R))+'m', mesh); bpy.context.collection.objects.link(obj)
for ch in range(0,81,10):
    phi=ch/R; x=R*(1-math.cos(phi)); y=R*math.sin(phi)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x,y,-1.55)); tick=bpy.context.view_layer.objects.active; tick.name='chainage_%03dm'%ch; tick.dimensions=(.08,.08,.35); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True); tick.data.materials.append(mat(10))
bpy.ops.object.light_add(type='SUN', location=(8,-20,16))
bpy.ops.object.camera_add(location=(18,-38,14), rotation=(math.radians(70),0,math.radians(25)))
bpy.context.scene.camera=bpy.context.view_layer.objects.active
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR/'tunnel_t0t5_curved_visual_T5.blend'))
manifest={'dataset':'tunnel_t0t5_blend_curved_visual','purpose':'Visual-only curved Blender scene; source analysis point clouds unchanged','source_dataset':str(SRC_DIR),'visual_time':TIME,'curve_radius_m':R,'blend':'tunnel_t0t5_curved_visual_T5.blend'}
(OUT_DIR/'manifest.json').write_text(json.dumps(manifest,indent=2), encoding='utf-8')
(OUT_DIR/'README.md').write_text('# Curved Visual Tunnel Scene\n\nVisual-only curved Blender scene generated from T5 of the straight interior dataset. Analysis point clouds are not changed.\n', encoding='utf-8')
print(json.dumps({'status':'ok','out_dir':str(OUT_DIR),'blend':str(OUT_DIR/'tunnel_t0t5_curved_visual_T5.blend'),'radius_m':R}, indent=2))
"""

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
    args=parser.parse_args()
    code=BLENDER_CODE.replace("__SRC_DIR__", str(SRC_DIR).replace("\\", "\\\\")).replace("__OUT_DIR__", str(OUT_DIR).replace("\\", "\\\\")).replace("__RADIUS__", str(args.radius))
    resp=send_blender_command("execute_code", {"code": code}, args.host, args.port)
    if resp.get("status") != "success": print(json.dumps(resp, indent=2, ensure_ascii=False)); return 1
    print(json.dumps(resp.get("result", resp), indent=2, ensure_ascii=False))
    return 0
if __name__ == "__main__": raise SystemExit(main())
