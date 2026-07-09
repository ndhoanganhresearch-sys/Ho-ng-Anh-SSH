
import bpy, json, math, os, random
from mathutils import Vector
OUT_DIR = r"C:\\Users\\ssl\\Desktop\\Code Python\\data python cusor\\tunnel_project\\data\\real_scale_railway_tunnel_t0t5\\field_like_raycast_dataset"
RAY_STEP = float("1.2")
MAX_RANGE = 55.0
TIMES = ['T0','T1','T2','T3','T4','T5']
LABELS = {"lining": 1, "rail": 2, "sleeper": 3, "walkway": 4, "cable_tray": 5, "pipe": 6, "light": 7, "equipment": 8, "target": 9, "sign": 10, "damage": 20}
HEADER = 'x y z nx ny nz intensity label station_id range_m'
os.makedirs(OUT_DIR, exist_ok=True)
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
    bpy.context.view_layer.update()

def station_pose(epoch, sid, y):
    bx, by, bz, yaw = POSE_BIAS[epoch]
    side_sway = 0.18 * math.sin(0.7 * sid)
    origin = Vector((side_sway + bx, y + by, 1.45 + bz))
    return origin, yaw

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
    'dataset':'field_like_raycast_dataset',
    'source_blend':bpy.data.filepath,
    'purpose':'Field-like TLS raycast dataset for Step 6 tunnel settlement validation',
    'columns':HEADER,
    'coordinate_policy':'T0-T5 share same tunnel coordinates; scanner pose has small epoch bias like real setup',
    'scanner':{'type':'simulated terrestrial laser scanner','stations_chainage_m':STATIONS,'ray_step_deg':RAY_STEP,'max_range_m':MAX_RANGE,'noise_model':'range + incidence dependent Gaussian; dropout for grazing/long range'},
    'labels':LABELS,
    'epochs':metas,
    'ground_truth_settlement_mm':{'T0':0,'T1':-10,'T2':-22,'T3':-38,'T4':-58,'T5':-80}
}
with open(os.path.join(OUT_DIR,'manifest.json'),'w',encoding='utf-8') as f: json.dump(manifest,f,indent=2)
with open(os.path.join(OUT_DIR,'README.md'),'w',encoding='utf-8') as f: f.write('# Field-like Real Scale Railway Tunnel T0-T5\n\nRaw TLS-style raycast from 7 stations. Use full dataset for denoise/registration stress; use `clean_lining_dataset` for Step 6 settlement measurement.\n')
print(json.dumps({'status':'ok','out_dir':OUT_DIR,'epochs':len(metas),'points':[m['points'] for m in metas]}, ensure_ascii=False))
