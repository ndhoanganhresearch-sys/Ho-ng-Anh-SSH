from __future__ import annotations
import argparse, json, socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "real_scale_railway_tunnel_t0t5"
BLEND = OUT_DIR / "real_scale_railway_tunnel_t0t5.blend"

BLENDER_CODE = r'''
import bpy, math, json, os
from mathutils import Vector
OUT_DIR = r"__OUT_DIR__"
BLEND = r"__BLEND__"
os.makedirs(OUT_DIR, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for _name in ['T0','T1','T2','T3','T4','T5']:
    _coll = bpy.data.collections.get(_name)
    if _coll is not None:
        bpy.data.collections.remove(_coll)

LENGTH = 120.0
HALF_WIDTH = 4.4
SIDE_H = 3.0
ARCH_R = 4.4
GAUGE = 1.435
EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
SETTLEMENT = {"T0":0.0,"T1":-0.010,"T2":-0.022,"T3":-0.038,"T4":-0.058,"T5":-0.080}

materials = {}
def mat(name, color):
    if name not in materials:
        m=bpy.data.materials.new(name); m.diffuse_color=color; materials[name]=m
    return materials[name]
MAT_CONC=mat('cast_in_place_concrete_lining',(0.56,0.56,0.52,1))
MAT_RAIL=mat('steel_rail_dark',(0.08,0.08,0.09,1))
MAT_SLEEPER=mat('concrete_sleepers',(0.42,0.39,0.34,1))
MAT_WALK=mat('maintenance_walkway',(0.30,0.32,0.33,1))
MAT_CABLE=mat('cable_tray_orange',(0.95,0.45,0.05,1))
MAT_PIPE=mat('water_drainage_pipe_blue',(0.05,0.23,0.65,1))
MAT_LIGHT=mat('tunnel_lights',(1.0,0.88,0.32,1))
MAT_TARGET=mat('survey_targets',(0.95,0.1,0.1,1))
MAT_DAMAGE=mat('settlement_zone_marker',(1.0,0.05,0.05,1))

# Collections: each epoch is same coordinate frame, not offset for visualization.
for ep in EPOCHS:
    bpy.data.collections.new(ep)
    bpy.context.scene.collection.children.link(bpy.data.collections[ep])

def add_to_epoch(obj, ep):
    bpy.context.collection.objects.unlink(obj)
    bpy.data.collections[ep].objects.link(obj)

def settlement_z(ep, x, y, z):
    crown = max(0.0, (z - SIDE_H) / ARCH_R)
    g = math.exp(-0.5*((y-52.0)/13.0)**2)
    return SETTLEMENT[ep] * g * (crown ** 1.8)

def section_points(ep):
    """Smooth railway-tunnel inner profile: invert + sidewalls + arch."""
    pts=[]
    # Smooth invert from left floor to right floor through a shallow center low point.
    for i in range(33):
        u = i / 32.0
        x = -HALF_WIDTH + 2.0 * HALF_WIDTH * u
        z = -0.40 * math.sin(math.pi * u)
        pts.append((x, z))
    # Right sidewall, sampled enough to avoid jagged section outlines.
    for i in range(1, 25):
        z = i * SIDE_H / 24.0
        pts.append((HALF_WIDTH, z))
    # Crown arch from right springline to left springline.
    for i in range(1, 64):
        a = i * math.pi / 64.0
        x = HALF_WIDTH * math.cos(a)
        z = SIDE_H + ARCH_R * math.sin(a)
        pts.append((x, z))
    # Left sidewall back down to invert start.
    for i in range(23, 0, -1):
        z = i * SIDE_H / 24.0
        pts.append((-HALF_WIDTH, z))
    return pts

def make_lining(ep):
    sec=section_points(ep)
    nsec=len(sec)
    yvals=[i*LENGTH/240 for i in range(241)]
    verts=[]
    for y in yvals:
        for x,z in sec:
            zz=z+settlement_z(ep,x,y,z)
            verts.append((x,y,zz))
    faces=[]
    for iy in range(len(yvals)-1):
        for j in range(nsec):
            a=iy*nsec+j; b=iy*nsec+(j+1)%nsec; c=(iy+1)*nsec+(j+1)%nsec; d=(iy+1)*nsec+j
            faces.append((a,b,c,d))
    mesh=bpy.data.meshes.new(ep+'_lining_mesh'); mesh.from_pydata(verts, [], faces); mesh.update()
    obj=bpy.data.objects.new(ep+'_lining', mesh); bpy.context.collection.objects.link(obj)
    obj.data.materials.append(MAT_CONC); add_to_epoch(obj, ep)
    return obj

def cube_obj(name, loc, scale, material, ep):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj=bpy.context.object; obj.name=name
    obj.dimensions=scale; bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material); add_to_epoch(obj, ep); return obj

def cyl_obj(name, loc, radius, depth, material, ep, rotation=(0,0,0), vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj=bpy.context.object; obj.name=name; obj.data.materials.append(material); add_to_epoch(obj, ep); return obj

def make_epoch(ep):
    make_lining(ep)
    # Rails, UIC-ish 1435mm gauge, continuous along tunnel.
    for side,x in [('L',-GAUGE/2),('R',GAUGE/2)]:
        cube_obj(f'{ep}_rail_{side}', (x, LENGTH/2, 0.12), (0.09, LENGTH, 0.16), MAT_RAIL, ep)
        cube_obj(f'{ep}_rail_head_{side}', (x, LENGTH/2, 0.23), (0.14, LENGTH, 0.08), MAT_RAIL, ep)
    # Sleepers every 0.65m.
    idx=0; y=0.5
    while y < LENGTH:
        cube_obj(f'{ep}_sleeper_{idx:03d}', (0,y,0.02), (2.6,0.22,0.16), MAT_SLEEPER, ep)
        y += 0.65; idx += 1
    # Walkways and drainage channels.
    cube_obj(f'{ep}_walkway_L', (-3.45,LENGTH/2,0.20), (1.25,LENGTH,0.25), MAT_WALK, ep)
    cube_obj(f'{ep}_walkway_R', (3.45,LENGTH/2,0.20), (1.25,LENGTH,0.25), MAT_WALK, ep)
    cube_obj(f'{ep}_drain_channel_L', (-2.65,LENGTH/2,-0.18), (0.35,LENGTH,0.18), MAT_PIPE, ep)
    cube_obj(f'{ep}_drain_channel_R', (2.65,LENGTH/2,-0.18), (0.35,LENGTH,0.18), MAT_PIPE, ep)
    # Cable trays and water/service pipes along both sidewalls.
    for side,x in [('L',-4.05),('R',4.05)]:
        cube_obj(f'{ep}_cable_tray_{side}', (x,LENGTH/2,3.05), (0.28,LENGTH,0.22), MAT_CABLE, ep)
        cyl_obj(f'{ep}_water_pipe_{side}', (x*0.98,LENGTH/2,2.35), 0.10, LENGTH, MAT_PIPE, ep, rotation=(math.pi/2,0,0), vertices=24)
        cyl_obj(f'{ep}_service_pipe_{side}', (x*0.96,LENGTH/2,4.05), 0.07, LENGTH, MAT_PIPE, ep, rotation=(math.pi/2,0,0), vertices=20)
    # Lights and survey targets.
    for i,y in enumerate([10,25,40,55,70,85,100,115]):
        cube_obj(f'{ep}_light_{i:02d}', (0,y,6.85+settlement_z(ep,0,y,6.85)), (0.55,0.12,0.10), MAT_LIGHT, ep)
    for i,y in enumerate([12,35,58,82,106]):
        cyl_obj(f'{ep}_registration_target_{i:02d}', (-3.9 if i%2==0 else 3.9,y,2.0), 0.16, 0.04, MAT_TARGET, ep, rotation=(0,math.pi/2,0), vertices=32)
    # Visible settlement marker near crown for later visual QA, follows epoch deformation.
    if ep != 'T0':
        cube_obj(f'{ep}_crown_settlement_marker', (0,52,6.95+SETTLEMENT[ep]), (0.75,2.2,0.05), MAT_DAMAGE, ep)

for ep in EPOCHS:
    make_epoch(ep)

# Keep only T0 and T5 visible in viewport by default; all epochs remain in same coordinates.
for ep in EPOCHS:
    coll=bpy.data.collections[ep]
    coll.hide_viewport = False
    coll.hide_render = ep not in ['T0','T5']

# Add centerline, camera, lights.
mesh=bpy.data.meshes.new('centerline_mesh'); pts=[(0,i*LENGTH/80,0.02) for i in range(81)]
mesh.from_pydata(pts, [(i,i+1) for i in range(80)], []); mesh.update()
obj=bpy.data.objects.new('same_coordinate_centerline', mesh); bpy.context.collection.objects.link(obj)
bpy.ops.object.light_add(type='SUN', location=(0,-15,18)); bpy.context.object.name='Sun_real_scale'
bpy.ops.object.camera_add(location=(12,-28,12), rotation=(math.radians(63),0,math.radians(26)))
bpy.context.scene.camera=bpy.context.object

meta={
 'dataset':'real_scale_railway_tunnel_t0t5',
 'purpose':'Real-scale single railway tunnel, T0-T5 share one coordinate frame for settlement monitoring',
 'dimensions_m':{'length':LENGTH,'inner_width':HALF_WIDTH*2,'sidewall_height':SIDE_H,'crown_height':SIDE_H+ARCH_R,'track_gauge':GAUGE},
 'coordinate_policy':'No visual offsets: all epochs occupy the same tunnel location',
 'epochs':EPOCHS,
 'settlement_m':SETTLEMENT,
 'components':['lining','standard gauge rails','sleepers','walkways','drainage channels','water/service pipes','cable trays','lights','registration targets']
}
with open(os.path.join(OUT_DIR,'scene_manifest.json'),'w',encoding='utf-8') as f: json.dump(meta,f,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print(json.dumps({'status':'ok','blend':BLEND,'manifest':os.path.join(OUT_DIR,'scene_manifest.json'),'meta':meta}, ensure_ascii=False))
'''

def send(code: str, host: str, port: int, timeout: float) -> dict:
    payload={"type":"execute_code","params":{"code":code}}
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout); sock.connect((host,port)); sock.sendall(json.dumps(payload).encode('utf-8'))
        chunks=[]
        while True:
            b=sock.recv(8192)
            if not b: break
            chunks.append(b)
            txt=b''.join(chunks).decode('utf-8')
            try: return json.loads(txt)
            except json.JSONDecodeError: pass
    raise RuntimeError('No complete JSON response received from Blender MCP')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=9876)
    parser.add_argument('--timeout', type=float, default=900)
    args=parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    code=BLENDER_CODE.replace('__OUT_DIR__', str(OUT_DIR).replace('\\','\\\\')).replace('__BLEND__', str(BLEND).replace('\\','\\\\'))
    (OUT_DIR/'create_real_scale_scene_code.py').write_text(code, encoding='utf-8')
    resp=send(code,args.host,args.port,args.timeout)
    if resp.get('status')!='success':
        print(json.dumps(resp, indent=2, ensure_ascii=False)); return 1
    print(json.dumps(resp.get('result', resp), indent=2, ensure_ascii=False))
    print(f'Blend written to: {BLEND}')
    return 0
if __name__=='__main__': raise SystemExit(main())


