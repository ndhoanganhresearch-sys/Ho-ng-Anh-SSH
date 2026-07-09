# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import socket
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent.parent / "data" / "auto_align_short"

RADIUS = 3.0
LENGTH = 36.0
RING_DS = 0.45
POINTS_PER_RING = 72
TARGET_CH = [6.0, 18.0, 30.0]
LABEL_LINING = 1
LABEL_OUTLIER = 2
LABEL_CABLE = 3
LABEL_CLEARANCE = 4
LABEL_TARGET = 9

TN_YAW_DEG = 4.0
TN_SHIFT = np.array([0.55, -0.35, 0.18])

STEP6_HAZARDS = [
    {"chainage_m": 7.0, "kind": "crown_settlement", "mm": -45.0, "theta_deg": 90.0},
    {"chainage_m": 15.5, "kind": "left_wall_convergence", "mm": -38.0, "theta_deg": 180.0},
    {"chainage_m": 24.0, "kind": "right_wall_convergence", "mm": -38.0, "theta_deg": 0.0},
    {"chainage_m": 32.5, "kind": "invert_heave", "mm": 35.0, "theta_deg": 270.0},
]
HAZARD_SIGMA_CHAINAGE_M = 0.75
HAZARD_SIGMA_THETA_RAD = 0.34


def centerline(s: np.ndarray) -> np.ndarray:
    return np.column_stack([np.zeros_like(s), s, 0.0015 * s])


def build_lining(seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    chainages = np.arange(0.0, LENGTH + RING_DS, RING_DS)
    points = []
    for chainage in chainages:
        angle = np.linspace(0, 2 * np.pi, POINTS_PER_RING, endpoint=False)
        angle += rng.normal(0.0, 0.004, POINTS_PER_RING)
        radius = RADIUS + rng.normal(0.0, 0.003, POINTS_PER_RING)
        x = radius * np.cos(angle)
        y = np.full_like(x, chainage)
        z = 0.0015 * chainage + radius * np.sin(angle)
        points.append(np.column_stack([x, y, z]))
    pts = np.vstack(points)
    intensity = np.full(len(pts), 0.12)
    label = np.full(len(pts), LABEL_LINING)
    return pts, intensity, label


def sphere(center: np.ndarray, seed: int, radius: float = 0.085, n: int = 120) -> np.ndarray:
    rng = np.random.default_rng(seed)
    phi = rng.uniform(0, 2 * np.pi, n)
    costheta = rng.uniform(-1, 1, n)
    theta = np.arccos(costheta)
    r = radius + rng.normal(0, 0.0015, n)
    return center + np.column_stack([
        r * np.sin(theta) * np.cos(phi),
        r * np.sin(theta) * np.sin(phi),
        r * np.cos(theta),
    ])


def add_targets(seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    parts = []
    for index, chainage in enumerate(TARGET_CH):
        center = np.array([1.65 * (-1 if index % 2 else 1), chainage, 0.0015 * chainage + 1.35])
        parts.append(sphere(center, seed * 100 + index))
    pts = np.vstack(parts)
    intensity = np.full(len(pts), 0.95)
    label = np.full(len(pts), LABEL_TARGET)
    return pts, intensity, label


def angle_delta(a: np.ndarray, b: float) -> np.ndarray:
    return np.arctan2(np.sin(a - b), np.cos(a - b))


def apply_step6_hazards(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    deformed = points.copy()
    y = points[:, 1]
    local_z = points[:, 2] - 0.0015 * y
    theta = np.arctan2(local_z, points[:, 0])
    hazard_score = np.zeros(len(points), dtype=float)
    for hazard in STEP6_HAZARDS:
        theta0 = math.radians(hazard["theta_deg"])
        chain_w = np.exp(-0.5 * ((y - hazard["chainage_m"]) / HAZARD_SIGMA_CHAINAGE_M) ** 2)
        theta_w = np.exp(-0.5 * (angle_delta(theta, theta0) / HAZARD_SIGMA_THETA_RAD) ** 2)
        weight = chain_w * theta_w
        hazard_score = np.maximum(hazard_score, weight)
        move_m = hazard["mm"] / 1000.0 * weight
        if hazard["kind"] == "crown_settlement":
            deformed[:, 2] += move_m
        elif hazard["kind"] == "invert_heave":
            deformed[:, 2] -= move_m
        elif hazard["kind"] == "left_wall_convergence":
            deformed[:, 0] -= move_m
        elif hazard["kind"] == "right_wall_convergence":
            deformed[:, 0] += move_m
    return deformed, hazard_score > 0.62


def add_clearance_hazards(seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    parts = []
    for index, hazard in enumerate(STEP6_HAZARDS):
        chainage = hazard["chainage_m"]
        theta = math.radians(hazard["theta_deg"])
        center = np.array([
            1.72 * math.cos(theta),
            chainage,
            0.0015 * chainage + 1.72 * math.sin(theta),
        ])
        parts.append(center + rng.normal(0.0, [0.045, 0.10, 0.045], (18, 3)))
    pts = np.vstack(parts)
    intensity = np.full(len(pts), 0.88)
    label = np.full(len(pts), LABEL_CLEARANCE)
    return pts, intensity, label


def add_small_noise(seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    blob_centers = [
        np.array([-1.2, 12.0, 1.0]),
        np.array([1.35, 24.0, -0.75]),
        np.array([0.25, 31.0, 1.9]),
    ]
    blobs = [center + rng.normal(0, 0.09, (45, 3)) for center in blob_centers]

    chainage = np.linspace(8.0, 32.0, 180)
    cable = np.column_stack([
        0.45 * np.sin(chainage * 0.45),
        chainage,
        2.55 + 0.0015 * chainage + 0.06 * np.cos(chainage * 0.35),
    ])
    cable += rng.normal(0, 0.012, cable.shape)

    random_count = 90
    scattered = np.column_stack([
        rng.uniform(-2.4, 2.4, random_count),
        rng.uniform(3.0, LENGTH - 3.0, random_count),
        rng.uniform(-2.1, 2.3, random_count),
    ])

    pts = np.vstack(blobs + [cable, scattered])
    intensity = np.concatenate([
        rng.uniform(0.04, 0.30, sum(len(blob) for blob in blobs)),
        np.full(len(cable), 0.32),
        rng.uniform(0.03, 0.38, len(scattered)),
    ])
    label = np.concatenate([
        np.full(sum(len(blob) for blob in blobs), LABEL_OUTLIER),
        np.full(len(cable), LABEL_CABLE),
        np.full(len(scattered), LABEL_OUTLIER),
    ])
    return pts, intensity, label


def rigid(yaw_deg: float, shift: np.ndarray) -> np.ndarray:
    yaw = math.radians(yaw_deg)
    rot = np.array([
        [math.cos(yaw), -math.sin(yaw), 0.0],
        [math.sin(yaw), math.cos(yaw), 0.0],
        [0.0, 0.0, 1.0],
    ])
    matrix = np.eye(4)
    matrix[:3, :3] = rot
    matrix[:3, 3] = shift
    return matrix


def apply(matrix: np.ndarray, points: np.ndarray) -> np.ndarray:
    homo = np.column_stack([points, np.ones(len(points))])
    return (matrix @ homo.T).T[:, :3]


def save_txt(path: Path, pts: np.ndarray, intensity: np.ndarray, label: np.ndarray) -> None:
    arr = np.column_stack([pts, np.zeros((len(pts), 3)), intensity, label])
    np.savetxt(path, arr, fmt=["%.4f"] * 7 + ["%d"], header="x y z nx ny nz intensity label", comments="# ")


def save_las(path: Path, pts: np.ndarray, intensity: np.ndarray, label: np.ndarray) -> None:
    import laspy

    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = np.array([1e-3, 1e-3, 1e-3])
    header.offsets = pts.min(axis=0)
    las = laspy.LasData(header=header)
    las.x, las.y, las.z = pts[:, 0], pts[:, 1], pts[:, 2]
    las.intensity = np.clip(intensity * 65535, 0, 65535).astype(np.uint16)
    color = np.full(len(pts), 42000, dtype=np.uint16)
    las.red, las.green, las.blue = color, color, color
    las.classification = np.asarray(label, dtype=np.uint8)
    las.write(str(path))


def send_blender(code: str) -> dict:
    payload = json.dumps({"type": "execute_code", "params": {"code": code}}).encode("utf-8")
    with socket.create_connection(("127.0.0.1", 9876), timeout=20) as sock:
        sock.sendall(payload)
        sock.shutdown(socket.SHUT_WR)
        data = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
    if not data:
        return {"status": "no_response", "note": "Blender executed but returned an empty socket response"}
    return json.loads(data.decode("utf-8"))


def create_blender_scene() -> dict:
    code = f'''
import bpy, json
from pathlib import Path

out = Path(r"{OUT}")

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def mat(name, color):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    return material

def read_points(path):
    pts, labels = [], []
    with open(path, 'r', encoding='utf-8') as handle:
        for line in handle:
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            part = line.split()
            if len(part) < 8:
                continue
            pts.append((float(part[0]), float(part[1]), float(part[2])))
            labels.append(int(float(part[7])))
    return pts, labels

def cloud(name, pts, labels, materials, offset_x=0.0):
    groups = {{}}
    for point, label in zip(pts, labels):
        groups.setdefault(label, []).append((point[0] + offset_x, point[1], point[2]))
    for label, verts in groups.items():
        mesh = bpy.data.meshes.new(f'{{name}}_{{label}}_mesh')
        mesh.from_pydata(verts, [], [])
        mesh.update()
        obj = bpy.data.objects.new(f'{{name}}_label_{{label}}', mesh)
        obj.data.materials.append(materials.get(label, materials[1]))
        bpy.context.collection.objects.link(obj)

def add_text(name, text, loc):
    bpy.ops.object.text_add(location=loc, rotation=(1.2, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.body = text
    obj.data.size = 0.55
    return obj

clear()
materials = {{
    1: mat('lining_gray', (0.55, 0.58, 0.62, 1)),
    2: mat('outlier_red', (1.0, 0.15, 0.08, 1)),
    3: mat('cable_orange', (1.0, 0.48, 0.05, 1)),
    4: mat('clearance_purple', (0.65, 0.10, 1.0, 1)),
    9: mat('target_yellow', (1.0, 0.85, 0.05, 1)),
}}
t0, l0 = read_points(out / 'T0_short.txt')
tn, ln = read_points(out / 'Tn_short_shifted.txt')
cloud('T0_reference', t0, l0, materials, -4.8)
cloud('Tn_shifted_before_auto_align', tn, ln, materials, 4.8)
add_text('title', 'Short Auto Align Test: left=T0, right=Tn shifted', (-8, -2, 4.2))
add_text('offset_note', 'Tn offset: yaw {TN_YAW_DEG} deg, shift {TN_SHIFT.tolist()} m', (-8, 4, 3.6))
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'auto_align_short_scene.blend'))
print(json.dumps({{'status': 'ok', 'blend': str(out / 'auto_align_short_scene.blend'), 't0_points': len(t0), 'tn_points': len(tn)}}))
'''
    return send_blender(code)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    lining, lining_i, lining_l = build_lining(seed=10)
    targets, targets_i, targets_l = add_targets(seed=11)
    t0 = np.vstack([lining, targets])
    t0_i = np.concatenate([lining_i, targets_i])
    t0_l = np.concatenate([lining_l, targets_l])

    deformed_lining, hazard_mask = apply_step6_hazards(lining)
    clearance, clearance_i, clearance_l = add_clearance_hazards(seed=13)
    noise, noise_i, noise_l = add_small_noise(seed=12)
    tn_world = np.vstack([deformed_lining, targets.copy(), clearance, noise])
    tn_i = np.concatenate([lining_i, targets_i, clearance_i, noise_i])
    tn_l = np.concatenate([lining_l, targets_l, clearance_l, noise_l])
    matrix = rigid(TN_YAW_DEG, TN_SHIFT)
    tn_shifted = apply(matrix, tn_world)

    save_txt(OUT / "T0_short.txt", t0, t0_i, t0_l)
    save_txt(OUT / "Tn_short_shifted.txt", tn_shifted, tn_i, tn_l)
    save_las(OUT / "T0_short.las", t0, t0_i, t0_l)
    save_las(OUT / "Tn_short_shifted.las", tn_shifted, tn_i, tn_l)

    manifest = {
        "dataset": "auto_align_short",
        "purpose": "Short and easy-to-see pair for testing auto align and denoise.",
        "units": "meters",
        "columns_txt": "x y z nx ny nz intensity label",
        "labels": {"1": "lining", "2": "outlier", "3": "cable", "4": "step6 clearance/hazard", "9": "sphere target"},
        "tunnel": {"length_m": LENGTH, "radius_m": RADIUS, "ring_spacing_m": RING_DS},
        "target_chainages_m": TARGET_CH,
        "tn_known_offset": {"yaw_deg": TN_YAW_DEG, "shift_xyz_m": TN_SHIFT.tolist()},
        "step6_hazards": {
            "count": len(STEP6_HAZARDS),
            "chainages_m": [h["chainage_m"] for h in STEP6_HAZARDS],
            "types": [h["kind"] for h in STEP6_HAZARDS],
            "clearance_points": int((tn_l == LABEL_CLEARANCE).sum()),
            "affected_lining_points_estimate": int(hazard_mask.sum()),
        },
        "denoise_noise": {
            "outlier_blob_count": 3,
            "outlier_blob_points": 135,
            "scattered_outlier_points": 90,
            "cable_points": 180,
            "total_noise_points": int((tn_l == LABEL_OUTLIER).sum() + (tn_l == LABEL_CABLE).sum()),
        },
        "files": ["T0_short.las", "Tn_short_shifted.las", "auto_align_short_scene.blend"],
        "workflow": [
            "Import T0_short.las as T0/reference.",
            "Import Tn_short_shifted.las as Tn/current scan.",
            "Run auto align; Tn should move back close to T0.",
            "Run denoise; red outliers and orange cable points should be removed.",
            "Run Step 6; only four evenly spaced hazard locations should be highlighted.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Auto Align Short Test\n\n"
        "Bo du lieu ngan, de nhin, dung de test auto-align, denoise va tinh nang 6.\n\n"
        "- `T0_short.las`: ban moc/reference.\n"
        "- `Tn_short_shifted.las`: ban Tn da co y lech yaw 4 do va dich [0.55, -0.35, 0.18] m.\n"
        "- Nhieu de test denoise: 3 cum outlier, 90 diem rai rac, 180 diem cable gan vom.\n"
        "- Nguy hiem Step 6: 4 vi tri it diem, nam deu tai chainage 7.0, 15.5, 24.0, 32.5 m.\n"
        "- `auto_align_short_scene.blend`: scene Blender MCP, T0 ben trai va Tn lech ben phai de de quan sat.\n"
        "- Co 3 sphere targets tai chainage 6 m, 18 m, 30 m de auto-align bat diem chuan.\n",
        encoding="utf-8",
    )

    blender = create_blender_scene()
    print(json.dumps({"out": str(OUT), "t0_points": len(t0), "tn_points": len(tn_shifted), "blender": blender}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
