import json
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'full_test'

BLENDER_CODE = r'''
import bpy
import json
import math
from pathlib import Path

OUT = Path(r"__OUT__")
T0 = OUT / 'T0_full.txt'
TN = OUT / 'Tn_full.txt'

LABELS = {1: 'lining', 2: 'outlier', 3: 'cable', 9: 'target'}

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def mat(name, rgba):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m

def read_points(path, max_points=12000):
    pts = []
    labels = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            parts = line.split()
            if len(parts) < 8:
                continue
            pts.append((float(parts[0]), float(parts[1]), float(parts[2])))
            labels.append(int(float(parts[7])))
    if not pts:
        return [], []
    step = max(1, len(pts) // max_points)
    return pts[::step], labels[::step]

def make_cloud(name, pts, labels, material_map, x_offset=0.0):
    groups = {}
    for p, lab in zip(pts, labels):
        groups.setdefault(lab, []).append((p[0] + x_offset, p[1], p[2]))
    objects = []
    for lab, verts in groups.items():
        mesh = bpy.data.meshes.new(f'{name}_{LABELS.get(lab, lab)}_mesh')
        mesh.from_pydata(verts, [], [])
        mesh.update()
        obj = bpy.data.objects.new(f'{name}_{LABELS.get(lab, lab)}', mesh)
        obj.data.materials.append(material_map.get(lab, material_map[1]))
        bpy.context.collection.objects.link(obj)
        objects.append(obj)
    return objects

def make_marker(name, loc, radius, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj

def add_chainage_markers(material):
    for ch in [0, 200, 450, 700, 900, 1000]:
        y = ch - 500
        make_marker(f'chainage_{ch}m', (-9.0, y, 0.0), 1.2, material)

def add_defect_labels():
    font_curve = None
    labels = [
        (200, 'crown settlement -60 mm'),
        (450, 'sidewall convergence -50 mm/side'),
        (700, 'noise: cable + outlier blob'),
        (900, 'combined crown -45 + convergence -45'),
    ]
    for ch, txt in labels:
        bpy.ops.object.text_add(location=(-15.0, ch - 500, 8.0), rotation=(math.radians(70), 0, math.radians(90)))
        obj = bpy.context.object
        obj.name = f'label_{ch}m'
        obj.data.body = f'Ch {ch} m\n{txt}'
        obj.data.align_x = 'CENTER'
        obj.data.size = 4.0

clear_scene()
mat_t0 = mat('T0_reference_blue', (0.05, 0.35, 1.0, 1.0))
mat_tn = mat('Tn_monitoring_orange', (1.0, 0.42, 0.05, 1.0))
mat_noise = mat('Noise_red', (1.0, 0.0, 0.0, 1.0))
mat_cable = mat('Cable_black', (0.02, 0.02, 0.02, 1.0))
mat_target = mat('Targets_yellow', (1.0, 0.9, 0.05, 1.0))
mat_marker = mat('Chainage_green', (0.0, 0.8, 0.3, 1.0))

t0_pts, t0_lab = read_points(T0, 12000)
tn_pts, tn_lab = read_points(TN, 12000)
make_cloud('T0_full_left', t0_pts, t0_lab, {1: mat_t0, 2: mat_noise, 3: mat_cable, 9: mat_target}, x_offset=-8.0)
make_cloud('Tn_full_right', tn_pts, tn_lab, {1: mat_tn, 2: mat_noise, 3: mat_cable, 9: mat_target}, x_offset=8.0)
add_chainage_markers(mat_marker)
add_defect_labels()

bpy.ops.object.light_add(type='SUN', location=(0, -200, 80))
bpy.context.object.name = 'Sun_full_test'
bpy.context.object.data.energy = 2.0
bpy.ops.object.camera_add(location=(95, -680, 115), rotation=(math.radians(74), 0, math.radians(9)))
bpy.context.scene.camera = bpy.context.object
bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'full_test_blender_scene.blend'))
print(json.dumps({'status': 'ok', 'blend': str(OUT / 'full_test_blender_scene.blend'), 't0_sampled': len(t0_pts), 'tn_sampled': len(tn_pts)}, indent=2))
'''

def send(command_type, params, host='localhost', port=9876, timeout=240):
    payload = {'type': command_type, 'params': params}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.sendall(json.dumps(payload).encode('utf-8'))
        chunks = []
        while True:
            chunk = sock.recv(8192)
            if not chunk:
                break
            chunks.append(chunk)
            try:
                return json.loads(b''.join(chunks).decode('utf-8'))
            except json.JSONDecodeError:
                pass
    raise RuntimeError('No complete JSON response')

code = BLENDER_CODE.replace('__OUT__', str(OUT).replace('\\', '\\\\'))
resp = send('execute_code', {'code': code})
print(json.dumps(resp, indent=2))
if resp.get('status') != 'success':
    raise SystemExit(1)

