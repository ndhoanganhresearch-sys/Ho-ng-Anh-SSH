from __future__ import annotations
import argparse, json, socket
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'data' / 'curved_real_scale_railway_tunnel_t0t5' / 'field_like_raycast_dataset'
BLEND_PATH = ROOT / 'data' / 'curved_real_scale_railway_tunnel_t0t5' / 'curved_real_scale_railway_tunnel_t0t5.blend'
TIMES = ['T0','T1','T2','T3','T4','T5']
HEADER = 'x y z nx ny nz intensity label station_id range_m'
LABELS = {'lining':1,'rail':2,'sleeper':3,'walkway':4,'cable_tray':5,'pipe':6,'light':7,'equipment':8,'target':9,'sign':10,'damage':20}

BLENDER_CODE = r'''
import bpy, json, math, os, random
from mathutils import Vector
OUT_DIR = r"__OUT_DIR__"
BLEND_PATH = r"__BLEND_PATH__"
CURVE_R = 420.0
RAY_STEP = float("__RAY_STEP__")
MAX_RANGE = 55.0
TIMES = ['T0','T1','T2','T3','T4','T5']
LABELS = __LABELS_JSON__
HEADER = 'x y z nx ny nz intensity label station_id range_m'
os.makedirs(OUT_DIR, exist_ok=True)
if BLEND_PATH and os.path.exists(BLEND_PATH) and os.path.abspath(bpy.data.filepath) != os.path.abspath(BLEND_PATH):
    bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)
random.seed(42)

STATIONS = [8.0, 25.0, 42.0, 59.0, 76.0, 93.0, 110.0]
POSE_BIAS = {
    'T0': (0.000, 0.000, 0.000, 0.000),
    'T1': (0.004,-0.003, 0.001, 0.006),
    'T2': (-0.006,0.004,-0.001,-0.010),
    'T3': (0.008, 0.005, 0.002, 0.014),
    'T4': (-0.010,-0.006,0.003,-0.018),
    'T5': (0.012,-0.008,0.004,0.022),
}

def label_for(name):
    n = name.lower()
    if 'spalling' in n or 'crack' in n or 'leak' in n or 'settlement_marker' in n: return LABELS['damage']
    if 'lining' in n: return LABELS['lining']
    if 'rail' in n: return LABELS['rail']
    if 'sleeper' in n: return LABELS['sleeper']
    if 'walkway' in n: return LABELS['walkway']
    if 'cable' in n or 'tray' in n: return LABELS['cable_tray']
    if 'pipe' in n or 'drain' in n or 'handrail' in n: return LABELS['pipe']
    if 'light' in n: return LABELS['light']
    if 'target' in n: return LABELS['target']
    if 'sign' in n or 'plate' in n: return LABELS['sign']
    return LABELS['equipment']

def set_epoch_visible(epoch):
    for t in TIMES:
        coll = bpy.data.collections.get(t)
        if coll:
            hide = t != epoch
            coll.hide_viewport = hide
            for obj in coll.objects:
                obj.hide_viewport = hide
                obj.hide_set(hide)
    scanner_coll = bpy.data.collections.get('TLS_scanner_stations')
    if scanner_coll:
        scanner_coll.hide_viewport = True
        for obj in scanner_coll.objects:
            obj.hide_viewport = True
            obj.hide_set(True)
    bpy.context.view_layer.update()

def center(s):
    return Vector((CURVE_R * (1.0 - math.cos(s / CURVE_R)), CURVE_R * math.sin(s / CURVE_R), 0.0))

def right_vec(s):
    return Vector((math.cos(s / CURVE_R), -math.sin(s / CURVE_R), 0.0)).normalized()

def tangent_vec(s):
    return Vector((math.sin(s / CURVE_R), math.cos(s / CURVE_R), 0.0)).normalized()

def station_pose(epoch, sid, s):
    bx, by, bz, yaw = POSE_BIAS[epoch]
    side_sway = 0.18 * math.sin(0.7 * sid)
    origin = center(s + by) + right_vec(s) * (side_sway + bx) + Vector((0.0, 0.0, 1.45 + bz))
    yaw_world = math.atan2(tangent_vec(s).y, tangent_vec(s).x) + yaw
    return origin, yaw_world

def material_intensity(label, dist, incidence):
    base = {1:0.50, 2:0.82, 3:0.42, 4:0.48, 5:0.62, 6:0.58, 7:0.95, 8:0.55, 9:0.98, 10:0.88, 20:0.35}.get(label,0.5)
    return max(0.03, min(1.0, base * (0.62 + 0.38 * incidence) / (1.0 + 0.00045 * dist * dist)))

def raycast_epoch(epoch):
    set_epoch_visible(epoch)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rows=[]; counts={}; station_counts=[]
    az_steps = int(360.0 / RAY_STEP)
    el0, el1 = -35.0, 82.0
    el_steps = int((el1-el0) / RAY_STEP) + 1
    for sid, y in enumerate(STATIONS):
        origin, yaw = station_pose(epoch, sid, y)
        local_hits = 0
        for ia in range(az_steps):
            az = math.radians(ia * RAY_STEP) + yaw
            caz, saz = math.cos(az), math.sin(az)
            for ie in range(el_steps):
                el = math.radians(el0 + ie * RAY_STEP)
                direction = Vector((math.cos(el)*caz, math.cos(el)*saz, math.sin(el))).normalized()
                hit, loc, normal, face_index, obj, matrix = bpy.context.scene.ray_cast(depsgraph, origin, direction, distance=MAX_RANGE)
                if not hit or obj is None: continue
                dist = (loc-origin).length
                incidence = max(0.05, abs(direction.dot(normal.normalized())))
                # dropout: grazing angle and long range lose points, like real TLS.
                drop = 0.012 + 0.10 * max(0, 0.35 - incidence) + 0.00045 * dist
                if random.random() < drop: continue
                label = label_for(obj.name)
                sigma = 0.0015 + 0.00005 * dist + 0.0012 * (1.0 - incidence)
                noisy = loc + direction * random.gauss(0.0, sigma)
                intensity = material_intensity(label, dist, incidence) + random.gauss(0.0, 0.015)
                intensity = max(0.02, min(1.0, intensity))
                rows.append([noisy.x,noisy.y,noisy.z,normal.x,normal.y,normal.z,intensity,label,sid,dist])
                counts[str(label)] = counts.get(str(label),0)+1
                local_hits += 1
        station_counts.append({'station':sid,'chainage_m':y,'hits':local_hits})
    return rows, counts, station_counts

def write_rows(path, rows):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('# '+HEADER+'\n')
        for r in rows:
            f.write('%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.0f %.0f %.4f\n' % tuple(r))

metas=[]
for epoch in TIMES:
    print('Raycasting', epoch)
    rows, counts, station_counts = raycast_epoch(epoch)
    write_rows(os.path.join(OUT_DIR, epoch+'.txt'), rows)
    meta={'time':epoch,'txt':epoch+'.txt','points':len(rows),'label_counts':counts,'station_counts':station_counts}
    with open(os.path.join(OUT_DIR, epoch+'.json'), 'w', encoding='utf-8') as f: json.dump(meta, f, indent=2)
    metas.append(meta)
manifest={
    'dataset':'curved_field_like_raycast_dataset',
    'source_blend':bpy.data.filepath,
    'purpose':'Field-like TLS raycast dataset on curved railway tunnel for centerline and Step 6 validation',
    'columns':HEADER,
    'coordinate_policy':'T0-T5 share same tunnel coordinates; scanner pose has small epoch bias like real setup',
    'scanner':{'type':'simulated terrestrial laser scanner','stations_chainage_m':STATIONS,'centerline':'curved R=420m','ray_step_deg':RAY_STEP,'max_range_m':MAX_RANGE,'noise_model':'range + incidence dependent Gaussian; dropout for grazing/long range'},
    'labels':LABELS,
    'epochs':metas,
    'ground_truth_settlement_mm':{'T0':0,'T1':-10,'T2':-22,'T3':-38,'T4':-58,'T5':-80}
}
with open(os.path.join(OUT_DIR,'manifest.json'),'w',encoding='utf-8') as f: json.dump(manifest,f,indent=2)
with open(os.path.join(OUT_DIR,'README.md'),'w',encoding='utf-8') as f: f.write('# Curved Field-like Real Scale Railway Tunnel T0-T5\n\nRaw TLS-style raycast from 7 stations placed on the curved centerline. Use full dataset for denoise/registration stress; use `clean_lining_dataset` for Step 6 settlement measurement.\n')
print(json.dumps({'status':'ok','out_dir':OUT_DIR,'epochs':len(metas),'points':[m['points'] for m in metas]}, ensure_ascii=False))
'''

def send(code, host, port, timeout):
    payload={'type':'execute_code','params':{'code':code}}
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout); sock.connect((host,port)); sock.sendall(json.dumps(payload).encode('utf-8'))
        chunks=[]
        while True:
            b=sock.recv(8192)
            if not b: break
            chunks.append(b)
            text=b''.join(chunks).decode('utf-8')
            try: return json.loads(text)
            except json.JSONDecodeError: pass
    raise RuntimeError('No complete JSON response received from Blender MCP')

def convert_to_las(out_dir: Path):
    import laspy
    las_dir=out_dir/'las_export'; las_dir.mkdir(parents=True, exist_ok=True)
    for txt in sorted(out_dir.glob('T[0-5].txt')):
        arr=np.loadtxt(txt, comments='#')
        pts=arr[:,:3]; intensity=np.clip(arr[:,6]*65535,0,65535).astype(np.uint16)
        hdr=laspy.LasHeader(point_format=3, version='1.2'); hdr.scales=np.array([1e-4,1e-4,1e-4]); hdr.offsets=pts.min(axis=0)
        las=laspy.LasData(hdr); las.x=pts[:,0]; las.y=pts[:,1]; las.z=pts[:,2]
        las.intensity=intensity; las.classification=arr[:,7].astype(np.uint8); las.user_data=arr[:,8].astype(np.uint8)
        las.red=intensity; las.green=intensity; las.blue=intensity
        las.write(str(las_dir/(txt.stem+'.las')))

def create_clean_lining(out_dir: Path):
    import laspy
    clean=out_dir/'clean_lining_dataset'; las_dir=clean/'las_export'; clean.mkdir(exist_ok=True); las_dir.mkdir(exist_ok=True)
    exports=[]
    for txt in sorted(out_dir.glob('T[0-5].txt')):
        arr=np.loadtxt(txt, comments='#')
        lining=arr[arr[:,7].astype(int)==1].copy()
        out_txt=clean/txt.name
        np.savetxt(out_txt, lining, fmt='%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.0f %.0f %.4f', header=HEADER, comments='# ')
        pts=lining[:,:3]; intensity=np.clip(lining[:,6]*65535,0,65535).astype(np.uint16)
        hdr=laspy.LasHeader(point_format=3, version='1.2'); hdr.scales=np.array([1e-4,1e-4,1e-4]); hdr.offsets=pts.min(axis=0)
        las=laspy.LasData(hdr); las.x=pts[:,0]; las.y=pts[:,1]; las.z=pts[:,2]
        las.intensity=intensity; las.classification=lining[:,7].astype(np.uint8); las.user_data=lining[:,8].astype(np.uint8)
        las.red=intensity; las.green=intensity; las.blue=intensity
        las_path=las_dir/(txt.stem+'.las'); las.write(str(las_path))
        meta={'time':txt.stem,'txt':txt.name,'las':str(las_path),'points':int(len(lining)),'removed_non_lining_points':int(len(arr)-len(lining))}
        (clean/(txt.stem+'.json')).write_text(json.dumps(meta, indent=2), encoding='utf-8'); exports.append(meta)
    manifest=json.loads((out_dir/'manifest.json').read_text(encoding='utf-8'))
    manifest['dataset']='curved_field_like_raycast_clean_lining_dataset'; manifest['source_dataset']=str(out_dir); manifest['purpose']='Lining-only subset from field-like TLS raycast for Step 6 settlement measurement'; manifest['epochs']=exports
    (clean/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (clean/'README.md').write_text('# Curved Field-like Raycast Clean Lining T0-T5\n\nLining-only subset. Load T0.las as reference and T1-T5 as monitoring epochs for Step 6.\n', encoding='utf-8')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=9876)
    parser.add_argument('--out', default=str(OUT_DIR))
    parser.add_argument('--ray-step', type=float, default=1.2)
    parser.add_argument('--timeout', type=float, default=1800)
    args=parser.parse_args()
    out_dir=Path(args.out).resolve(); out_dir.mkdir(parents=True, exist_ok=True)
    code=BLENDER_CODE.replace('__OUT_DIR__', str(out_dir).replace('\\','\\\\')).replace('__BLEND_PATH__', str(BLEND_PATH).replace('\\','\\\\')).replace('__RAY_STEP__', str(args.ray_step)).replace('__LABELS_JSON__', json.dumps(LABELS))
    (out_dir/'raycast_blender_code.py').write_text(code, encoding='utf-8')
    resp=send(code,args.host,args.port,args.timeout)
    if resp.get('status')!='success': print(json.dumps(resp, indent=2, ensure_ascii=False)); return 1
    print(json.dumps(resp.get('result', resp), indent=2, ensure_ascii=False))
    convert_to_las(out_dir); create_clean_lining(out_dir)
    print(f'Curved raycast dataset written to: {out_dir}')
    return 0
if __name__=='__main__': raise SystemExit(main())
