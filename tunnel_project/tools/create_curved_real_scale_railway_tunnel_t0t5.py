from __future__ import annotations
import argparse, json, socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'data' / 'curved_real_scale_railway_tunnel_t0t5'
BLEND = OUT_DIR / 'curved_real_scale_railway_tunnel_t0t5.blend'

BLENDER_CODE = r'''
import bpy, math, json, os
from mathutils import Vector
OUT_DIR = r"__OUT_DIR__"
BLEND = r"__BLEND__"
os.makedirs(OUT_DIR, exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
for _name in ['T0','T1','T2','T3','T4','T5']:
    _coll = bpy.data.collections.get(_name)
    if _coll is not None:
        bpy.data.collections.remove(_coll)

LENGTH = 120.0
CURVE_R = 420.0
HALF_WIDTH = 4.4
SIDE_H = 3.0
ARCH_R = 4.4
GAUGE = 1.435
EPOCHS = ['T0','T1','T2','T3','T4','T5']
SETTLEMENT = {'T0':0.0,'T1':-0.010,'T2':-0.022,'T3':-0.038,'T4':-0.058,'T5':-0.080}
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
for ep in EPOCHS:
    coll=bpy.data.collections.new(ep); bpy.context.scene.collection.children.link(coll)

def center(s):
    a=s/CURVE_R
    return Vector((CURVE_R*(1.0-math.cos(a)), CURVE_R*math.sin(a), 0.0))
def right_vec(s):
    a=s/CURVE_R
    return Vector((math.cos(a), -math.sin(a), 0.0)).normalized()
def world_point(s, local_x, z):
    return center(s) + right_vec(s)*local_x + Vector((0.0,0.0,z))
def add_to_epoch(obj, ep):
    try: bpy.context.collection.objects.unlink(obj)
    except Exception: pass
    bpy.data.collections[ep].objects.link(obj)
def settlement_z(ep, local_x, s, z):
    crown = max(0.0, (z - SIDE_H) / ARCH_R)
    g = math.exp(-0.5*((s-52.0)/13.0)**2)
    return SETTLEMENT[ep] * g * (crown ** 1.8)
def section_points():
    pts=[]
    for i in range(33):
        u=i/32.0; x=-HALF_WIDTH+2.0*HALF_WIDTH*u; z=-0.40*math.sin(math.pi*u); pts.append((x,z))
    for i in range(1,25): pts.append((HALF_WIDTH, i*SIDE_H/24.0))
    for i in range(1,64):
        a=i*math.pi/64.0; pts.append((HALF_WIDTH*math.cos(a), SIDE_H+ARCH_R*math.sin(a)))
    for i in range(23,0,-1): pts.append((-HALF_WIDTH, i*SIDE_H/24.0))
    return pts

def make_lining(ep):
    sec=section_points(); nsec=len(sec); svals=[i*LENGTH/240 for i in range(241)]
    verts=[]; faces=[]
    for s in svals:
        for lx,z in sec:
            verts.append(tuple(world_point(s,lx,z+settlement_z(ep,lx,s,z))))
    for iy in range(len(svals)-1):
        for j in range(nsec):
            faces.append((iy*nsec+j, iy*nsec+(j+1)%nsec, (iy+1)*nsec+(j+1)%nsec, (iy+1)*nsec+j))
    mesh=bpy.data.meshes.new(ep+'_lining_mesh'); mesh.from_pydata(verts, [], faces); mesh.update()
    obj=bpy.data.objects.new(ep+'_lining', mesh); bpy.context.collection.objects.link(obj); obj.data.materials.append(MAT_CONC); add_to_epoch(obj, ep)

def make_strip_mesh(name, ep, local_x, z, width, height, material, s_step=2.0):
    svals=[i*s_step for i in range(int(LENGTH/s_step)+1)]
    if svals[-1] < LENGTH: svals.append(LENGTH)
    verts=[]; faces=[]
    for s in svals:
        for dx,dz in [(-width/2,-height/2),(width/2,-height/2),(width/2,height/2),(-width/2,height/2)]:
            verts.append(tuple(world_point(s,local_x+dx,z+dz+settlement_z(ep,local_x,s,z))))
    for i in range(len(svals)-1):
        a=i*4; b=(i+1)*4
        faces += [(a,b,b+1,a+1),(a+1,b+1,b+2,a+2),(a+2,b+2,b+3,a+3),(a+3,b+3,b,a)]
    mesh=bpy.data.meshes.new(name+'_mesh'); mesh.from_pydata(verts, [], faces); mesh.update()
    obj=bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(obj); obj.data.materials.append(material); add_to_epoch(obj, ep)

def make_box_at(name, ep, s, local_x, z, sx, sy, sz, material):
    # Oriented small box with tangent/right/up axes.
    c=world_point(s,local_x,z); r=right_vec(s); t=Vector((math.sin(s/CURVE_R), math.cos(s/CURVE_R), 0.0)).normalized(); u=Vector((0,0,1))
    verts=[]
    for dx in [-sx/2,sx/2]:
      for dy in [-sy/2,sy/2]:
       for dz in [-sz/2,sz/2]: verts.append(tuple(c+r*dx+t*dy+u*dz))
    faces=[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]
    mesh=bpy.data.meshes.new(name+'_mesh'); mesh.from_pydata(verts, [], faces); mesh.update()
    obj=bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(obj); obj.data.materials.append(material); add_to_epoch(obj, ep)

def make_epoch(ep):
    make_lining(ep)
    for lx in [-GAUGE/2, GAUGE/2]:
        make_strip_mesh(f'{ep}_rail_{lx:+.2f}', ep, lx, 0.20, 0.12, 0.16, MAT_RAIL, 1.0)
    idx=0; s=0.5
    while s < LENGTH:
        make_box_at(f'{ep}_sleeper_{idx:03d}', ep, s, 0.0, 0.02, 2.6, 0.22, 0.16, MAT_SLEEPER); s += 0.65; idx += 1
    for lx in [-3.45,3.45]: make_strip_mesh(f'{ep}_walkway_{lx:+.1f}', ep, lx, 0.20, 1.25, 0.25, MAT_WALK, 2.0)
    for lx in [-2.65,2.65]: make_strip_mesh(f'{ep}_drain_channel_{lx:+.1f}', ep, lx, -0.18, 0.35, 0.18, MAT_PIPE, 2.0)
    for lx in [-4.05,4.05]:
        make_strip_mesh(f'{ep}_cable_tray_{lx:+.1f}', ep, lx, 3.05, 0.28, 0.22, MAT_CABLE, 2.0)
        make_strip_mesh(f'{ep}_water_pipe_{lx:+.1f}', ep, lx*0.98, 2.35, 0.20, 0.20, MAT_PIPE, 2.0)
        make_strip_mesh(f'{ep}_service_pipe_{lx:+.1f}', ep, lx*0.96, 4.05, 0.14, 0.14, MAT_PIPE, 2.0)
    for i,s in enumerate([10,25,40,55,70,85,100,115]): make_box_at(f'{ep}_light_{i:02d}', ep, s, 0.0, 6.85+settlement_z(ep,0,s,6.85), 0.55, 0.12, 0.10, MAT_LIGHT)
    for i,s in enumerate([12,35,58,82,106]): make_box_at(f'{ep}_registration_target_{i:02d}', ep, s, -3.9 if i%2==0 else 3.9, 2.0, 0.30, 0.05, 0.30, MAT_TARGET)
    if ep!='T0': make_box_at(f'{ep}_crown_settlement_marker', ep, 52, 0, 6.95+SETTLEMENT[ep], 0.75, 2.2, 0.05, MAT_DAMAGE)
for ep in EPOCHS: make_epoch(ep)
# centerline mesh guide
pts=[tuple(center(i*LENGTH/160)+Vector((0,0,-0.35))) for i in range(161)]
mesh=bpy.data.meshes.new('curved_centerline_mesh'); mesh.from_pydata(pts, [(i,i+1) for i in range(len(pts)-1)], []); mesh.update()
obj=bpy.data.objects.new('curved_centerline_R420m', mesh); bpy.context.collection.objects.link(obj)
bpy.ops.object.light_add(type='SUN', location=(20,-30,25)); bpy.context.object.name='Sun_curved_real_scale'
bpy.ops.object.camera_add(location=(35,-45,18), rotation=(math.radians(65),0,math.radians(38))); bpy.context.scene.camera=bpy.context.object
meta={'dataset':'curved_real_scale_railway_tunnel_t0t5','purpose':'Curved real-scale single railway tunnel, T0-T5 share one coordinate frame for centerline and settlement testing','dimensions_m':{'length':LENGTH,'curve_radius':CURVE_R,'inner_width':HALF_WIDTH*2,'crown_height':SIDE_H+ARCH_R,'track_gauge':GAUGE},'coordinate_policy':'No visual offsets: all epochs occupy the same curved tunnel','epochs':EPOCHS,'settlement_m':SETTLEMENT,'components':['curved lining','curved rails','sleepers','walkways','drainage channels','pipes','cable trays','lights','registration targets']}
with open(os.path.join(OUT_DIR,'scene_manifest.json'),'w',encoding='utf-8') as f: json.dump(meta,f,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print(json.dumps({'status':'ok','blend':BLEND,'manifest':os.path.join(OUT_DIR,'scene_manifest.json'),'meta':meta}, ensure_ascii=False))
'''

def send(code, host, port, timeout):
    payload={'type':'execute_code','params':{'code':code}}
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout); sock.connect((host,port)); sock.sendall(json.dumps(payload).encode())
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
    parser=argparse.ArgumentParser(); parser.add_argument('--host',default='localhost'); parser.add_argument('--port',type=int,default=9876); parser.add_argument('--timeout',type=float,default=1200)
    args=parser.parse_args(); OUT_DIR.mkdir(parents=True, exist_ok=True)
    code=BLENDER_CODE.replace('__OUT_DIR__', str(OUT_DIR).replace('\\','\\\\')).replace('__BLEND__', str(BLEND).replace('\\','\\\\'))
    (OUT_DIR/'create_curved_scene_code.py').write_text(code, encoding='utf-8')
    resp=send(code,args.host,args.port,args.timeout)
    if resp.get('status')!='success': print(json.dumps(resp, indent=2, ensure_ascii=False)); return 1
    print(json.dumps(resp.get('result', resp), indent=2, ensure_ascii=False)); print(f'Blend written to: {BLEND}'); return 0
if __name__=='__main__': raise SystemExit(main())
