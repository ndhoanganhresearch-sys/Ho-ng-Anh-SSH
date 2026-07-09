
import bpy
import csv
import json
import math
import random
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path(r"C:\\Users\\ssl\\Desktop\\Code Python\\data python cusor\\tunnel_project\\data\\blender_lidar_t0t5_realistic")
OUT_DIR.mkdir(parents=True, exist_ok=True)
random.seed(20260629)

EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
LENGTH = 96.0
CURVE_R = 420.0
RADIUS = 4.25
N_SECTIONS = 193
N_THETA = 128
STATION_S = [8.0, 28.0, 48.0, 68.0, 88.0]
STATION_Z = -1.05
AZ_STEP_DEG = 0.45
EL_STEP_DEG = 0.45
EL_MIN_DEG = -38.0
EL_MAX_DEG = 82.0
MAX_RANGE_M = 44.0
HEADER = "x y z nx ny nz intensity label"
LABELS = {"lining": 1, "rail": 2, "sleeper": 3, "cable_tray": 4, "light": 5, "walkway": 6, "target": 7, "equipment": 8}
MATERIAL_INTENSITY = {"lining": 0.46, "rail": 0.78, "sleeper": 0.36, "cable_tray": 0.24, "light": 0.88, "walkway": 0.42, "target": 0.96, "equipment": 0.52}
POSE_BIAS = {
    "T0": (0.000, 0.000, 0.000, 0.000),
    "T1": (0.006, -0.004, 0.002, 0.010),
    "T2": (-0.010, 0.005, -0.002, -0.018),
    "T3": (0.014, 0.008, 0.004, 0.026),
    "T4": (-0.018, -0.011, 0.006, -0.032),
    "T5": (0.022, -0.014, 0.008, 0.040),
}
CROWN_MM = {"T0": 0.0, "T1": -5.0, "T2": -12.0, "T3": -21.0, "T4": -32.0, "T5": -48.0}
CONV_MM = {"T0": 0.0, "T1": -2.0, "T2": -8.0, "T3": -16.0, "T4": -27.0, "T5": -40.0}
LOCAL_MM = {"T0": 0.0, "T1": 0.0, "T2": 0.0, "T3": -14.0, "T4": -27.0, "T5": -43.0}
JOINT_MM = {"T0": 0.0, "T1": 1.5, "T2": 3.0, "T3": 5.0, "T4": 7.0, "T5": 9.0}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def make_mat(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def centerline(s):
    a = s / CURVE_R
    return Vector((CURVE_R * (1.0 - math.cos(a)), CURVE_R * math.sin(a), 0.002 * s))


def tangent(s):
    a = s / CURVE_R
    return Vector((math.sin(a), math.cos(a), 0.002)).normalized()


def normal_right(s):
    return tangent(s).cross(Vector((0.0, 0.0, 1.0))).normalized()


def frame_point(s, x_local, z_local):
    return centerline(s) + normal_right(s) * x_local + Vector((0.0, 0.0, z_local))


def theta_delta(theta, theta0):
    return math.atan2(math.sin(theta - theta0), math.cos(theta - theta0))


def deformation(epoch, s, theta):
    crown = CROWN_MM[epoch] / 1000.0
    conv = CONV_MM[epoch] / 1000.0
    local = LOCAL_MM[epoch] / 1000.0
    joint = JOINT_MM[epoch] / 1000.0
    crown_w = math.exp(-0.5 * ((s - 24.0) / 8.0) ** 2) * max(0.0, math.sin(theta)) ** 1.7
    conv_w = math.exp(-0.5 * ((s - 50.0) / 9.0) ** 2) * abs(math.cos(theta)) ** 1.4
    local_w = math.exp(-0.5 * ((s - 72.0) / 3.2) ** 2) * math.exp(-0.5 * (theta_delta(theta, math.radians(58.0)) / 0.22) ** 2)
    ring_w = math.exp(-0.5 * ((s - 60.0) / 11.0) ** 2) * (1.0 if int(s / 2.0) % 3 == 0 else 0.25)
    dx = -math.copysign(abs(conv) * conv_w, math.cos(theta))
    dz = crown * crown_w + local * local_w * math.sin(math.radians(58.0))
    dr = local * local_w + joint * ring_w * 0.35 * math.sin(theta * 2.0)
    return dx, dz, dr


def build_lining(epoch, mats):
    verts = []
    faces = []
    for i in range(N_SECTIONS):
        s = LENGTH * i / (N_SECTIONS - 1)
        for j in range(N_THETA):
            theta = 2.0 * math.pi * j / N_THETA
            dx, dz, dr = deformation(epoch, s, theta)
            ring_groove = -0.018 if abs((s % 2.0) - 0.03) < 0.03 else 0.0
            seg_phase = math.degrees(theta) % 60.0
            seg_groove = -0.010 if min(seg_phase, 60.0 - seg_phase) < 1.1 else 0.0
            rough = 0.006 * math.sin(0.9 * s + 3.0 * theta) + 0.003 * math.sin(3.1 * s - 2.0 * theta)
            radius = RADIUS + dr + ring_groove + seg_groove + rough
            verts.append(frame_point(s, radius * math.cos(theta) + dx, radius * math.sin(theta) + dz))
    for i in range(N_SECTIONS - 1):
        for j in range(N_THETA):
            a = i * N_THETA + j
            b = i * N_THETA + (j + 1) % N_THETA
            c = (i + 1) * N_THETA + (j + 1) % N_THETA
            d = (i + 1) * N_THETA + j
            faces.append((a, b, c, d))
    mesh = bpy.data.meshes.new(f"Tunnel_Lining_{epoch}")
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"Tunnel_Lining_{epoch}", mesh)
    obj["label"] = LABELS["lining"]
    obj["material_key"] = "lining"
    obj.data.materials.append(mats["lining"])
    bpy.context.collection.objects.link(obj)


def add_cube(name, location, scale, mat, label, material_key):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    obj["label"] = label
    obj["material_key"] = material_key
    return obj


def add_cylinder_between(name, p0, p1, radius, mat, label, material_key, vertices=12):
    mid = (p0 + p1) * 0.5
    direction = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=direction.length, location=mid)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(mat)
    obj["label"] = label
    obj["material_key"] = material_key
    return obj


def build_static_objects(mats):
    for s0 in [0, 24, 48, 72]:
        add_cylinder_between(f"Rail_L_{s0}", frame_point(s0, -0.72, -3.58), frame_point(min(LENGTH, s0 + 24), -0.72, -3.58), 0.035, mats["rail"], LABELS["rail"], "rail")
        add_cylinder_between(f"Rail_R_{s0}", frame_point(s0, 0.72, -3.58), frame_point(min(LENGTH, s0 + 24), 0.72, -3.58), 0.035, mats["rail"], LABELS["rail"], "rail")
    for k in range(80):
        add_cube(f"Sleeper_{k:03d}", frame_point(1.0 + k * 1.2, 0.0, -3.72), (1.95, 0.16, 0.10), mats["sleeper"], LABELS["sleeper"], "sleeper")
    for side, x in [("L", -3.95), ("R", 3.95)]:
        for s0 in [0, 32, 64]:
            add_cylinder_between(f"CableTray_{side}_{s0}", frame_point(s0, x, 1.20), frame_point(min(LENGTH, s0 + 32), x, 1.25), 0.055, mats["cable_tray"], LABELS["cable_tray"], "cable_tray", vertices=10)
    for k, s in enumerate([10, 22, 34, 46, 58, 70, 82, 94]):
        add_cube(f"Light_{k:02d}", frame_point(s, 0.0, 3.55), (0.55, 0.18, 0.10), mats["light"], LABELS["light"], "light")
    for s0 in [0, 24, 48, 72]:
        add_cube(f"Walkway_{s0}", frame_point(s0 + 12, 3.12, -3.25), (0.85, 24.0, 0.16), mats["walkway"], LABELS["walkway"], "walkway")
        add_cube(f"Drain_{s0}", frame_point(s0 + 12, -3.15, -3.62), (0.32, 24.0, 0.12), mats["walkway"], LABELS["walkway"], "walkway")
    for k, s in enumerate([14, 38, 62, 86]):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.145, location=frame_point(s, -3.55, 0.55))
        obj = bpy.context.object
        obj.name = f"TargetSphere_{k:02d}"
        obj.data.materials.append(mats["target"])
        obj["label"] = LABELS["target"]
        obj["material_key"] = "target"
    for k, s in enumerate([31, 67]):
        add_cube(f"EquipmentBox_{k:02d}", frame_point(s, 3.62, -1.20), (0.50, 0.75, 0.80), mats["equipment"], LABELS["equipment"], "equipment")


def station_pose(epoch, s):
    bias_x, bias_y, bias_z, yaw_deg = POSE_BIAS[epoch]
    return frame_point(s + bias_y, bias_x, STATION_Z + bias_z), math.radians(yaw_deg)


def rotate_z(vec, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return Vector((c * vec.x - s * vec.y, s * vec.x + c * vec.y, vec.z))


def raycast_epoch(epoch):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rows = []
    hit_counts = {str(v): 0 for v in LABELS.values()}
    station_counts = []
    az_values = [i * AZ_STEP_DEG for i in range(int(360.0 / AZ_STEP_DEG))]
    el_values = []
    elev = EL_MIN_DEG
    while elev <= EL_MAX_DEG + 1e-9:
        el_values.append(elev)
        elev += EL_STEP_DEG
    for station_index, station_chainage in enumerate(STATION_S):
        origin, yaw = station_pose(epoch, station_chainage)
        local_hits = 0
        for az in az_values:
            caz, saz = math.cos(math.radians(az)), math.sin(math.radians(az))
            for elev in el_values:
                ce, se = math.cos(math.radians(elev)), math.sin(math.radians(elev))
                direction = rotate_z(Vector((caz * ce, saz * ce, se)), yaw).normalized()
                hit, loc, normal, face_index, obj, matrix = bpy.context.scene.ray_cast(depsgraph, origin, direction, distance=MAX_RANGE_M)
                if not hit or obj is None:
                    continue
                material_key = obj.get("material_key", "lining")
                label = int(obj.get("label", LABELS["lining"]))
                distance = (loc - origin).length
                incidence = max(0.02, abs(direction.dot(normal.normalized())))
                if incidence < 0.10 and random.random() < 0.55:
                    continue
                if distance > 35.0 and random.random() < 0.18:
                    continue
                sigma = 0.0015 + 0.000055 * distance + 0.0018 * (1.0 - incidence)
                noisy_loc = loc + direction * random.gauss(0.0, sigma)
                intensity = MATERIAL_INTENSITY.get(material_key, 0.45) * incidence ** 0.45 / (1.0 + 0.018 * distance * distance)
                intensity = max(0.02, min(1.0, intensity + random.gauss(0.0, 0.025)))
                rows.append([noisy_loc.x, noisy_loc.y, noisy_loc.z, normal.x, normal.y, normal.z, intensity, label])
                hit_counts[str(label)] = hit_counts.get(str(label), 0) + 1
                local_hits += 1
        station_counts.append({"station": station_index, "chainage_m": station_chainage, "hits": local_hits})
    return rows, hit_counts, station_counts


def save_epoch(epoch, rows, hit_counts, station_counts):
    txt = OUT_DIR / f"{epoch}.txt"
    with txt.open("w", encoding="utf-8") as f:
        f.write("# " + HEADER + "\n")
        for row in rows:
            f.write("%.5f %.5f %.5f %.6f %.6f %.6f %.6f %d\n" % tuple(row))
    meta = {
        "epoch": epoch,
        "file": txt.name,
        "points": len(rows),
        "hit_counts_by_label": hit_counts,
        "station_counts": station_counts,
        "pose_bias_m_yaw_deg": POSE_BIAS[epoch],
        "deformation_mm": {
            "crown_settlement_chainage_24m": CROWN_MM[epoch],
            "sidewall_convergence_chainage_50m": CONV_MM[epoch],
            "local_damage_chainage_72m": LOCAL_MM[epoch],
            "ring_joint_offset_chainage_60m": JOINT_MM[epoch],
        },
    }
    with (OUT_DIR / f"{epoch}.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


def write_tables():
    with (OUT_DIR / "ground_truth.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["epoch", "crown_settlement_mm", "sidewall_convergence_mm", "local_damage_mm", "ring_joint_offset_mm"])
        for epoch in EPOCHS:
            writer.writerow([epoch, CROWN_MM[epoch], CONV_MM[epoch], LOCAL_MM[epoch], JOINT_MM[epoch]])
    with (OUT_DIR / "baseline_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pair", "crown_delta_mm", "sidewall_delta_mm", "local_delta_mm", "joint_delta_mm"])
        for epoch in EPOCHS[1:]:
            writer.writerow([f"T0-{epoch}", CROWN_MM[epoch], CONV_MM[epoch], LOCAL_MM[epoch], JOINT_MM[epoch]])
    with (OUT_DIR / "incremental_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pair", "crown_increment_mm", "sidewall_increment_mm", "local_increment_mm", "joint_increment_mm"])
        for previous_epoch, epoch in zip(EPOCHS[:-1], EPOCHS[1:]):
            writer.writerow([f"{previous_epoch}-{epoch}", CROWN_MM[epoch] - CROWN_MM[previous_epoch], CONV_MM[epoch] - CONV_MM[previous_epoch], LOCAL_MM[epoch] - LOCAL_MM[previous_epoch], JOINT_MM[epoch] - JOINT_MM[previous_epoch]])


def write_readme():
    readme = """# Blender LiDAR T0-T5 Realistic Dataset

Dataset realistic hơn cho Step 6/time-series deformation, tạo bằng Blender MCP.

## Điểm khác so với dataset công thức

- Hầm cong có lining dạng ring/segment và joint groove.
- Có rail, sleeper, walkway, drainage, cable tray, lights, equipment box, target sphere.
- Raycasting TLS từ 5 trạm, có occlusion thật theo tia.
- T1-T5 có scanner pose bias nhỏ, nên registration không còn identity tuyệt đối.
- Noise phụ thuộc khoảng cách, góc tới bề mặt và beam dropout.
- Intensity phụ thuộc vật liệu và khoảng cách.

## Biến dạng ground truth

| Dạng biến dạng | Chainage | T0 | T1 | T2 | T3 | T4 | T5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Crown settlement | 24 m | 0 | -5 | -12 | -21 | -32 | -48 mm |
| Sidewall convergence | 50 m | 0 | -2 | -8 | -16 | -27 | -40 mm |
| Local damage | 72 m | 0 | 0 | 0 | -14 | -27 | -43 mm |
| Ring joint offset | 60 m | 0 | 1.5 | 3 | 5 | 7 | 9 mm |

## File

- `T0.txt` ... `T5.txt`: point cloud columns `x y z nx ny nz intensity label`.
- `T0.las` ... `T5.las`: LAS export generated by the wrapper after Blender finishes.
- `T0.json` ... `T5.json`: metadata từng epoch.
- `ground_truth.csv`: biến dạng tuyệt đối theo epoch.
- `baseline_pairs.csv`: biến dạng tích lũy T0->Tn.
- `incremental_pairs.csv`: biến dạng gia tăng Tn->Tn+1.
- `manifest.json`: metadata tổng.
- `blender_lidar_t0t5_realistic.blend`: scene Blender đã lưu.

## Label

1 lining, 2 rail, 3 sleeper, 4 cable_tray, 5 light, 6 walkway, 7 target, 8 equipment.

## Cách dùng

1. Load `T0.txt` làm reference.
2. Add `T1.txt` đến `T5.txt` để test chuỗi thời gian.
3. Chạy denoise để loại cable/equipment nếu cần.
4. Chạy registration vì T1-T5 có pose bias nhỏ.
5. Chạy Step 6 để kiểm tra trend, M3C2 heatmap và cảnh báo.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def create_epoch_scene(epoch, mats):
    clear_scene()
    build_lining(epoch, mats)
    build_static_objects(mats)
    bpy.ops.object.light_add(type="SUN", location=(10, -20, 20))
    bpy.context.object.name = "Sun"
    bpy.ops.object.camera_add(location=(16, -34, 14), rotation=(math.radians(70), 0, math.radians(24)))
    bpy.context.scene.camera = bpy.context.object


def main():
    mats = {
        "lining": make_mat("concrete_lining", (0.55, 0.55, 0.52, 1.0)),
        "rail": make_mat("steel_rail", (0.15, 0.15, 0.16, 1.0)),
        "sleeper": make_mat("dark_sleeper", (0.22, 0.19, 0.16, 1.0)),
        "cable_tray": make_mat("black_cable_tray", (0.03, 0.03, 0.03, 1.0)),
        "light": make_mat("bright_light", (1.0, 0.92, 0.55, 1.0)),
        "walkway": make_mat("walkway_concrete", (0.38, 0.36, 0.34, 1.0)),
        "target": make_mat("white_target", (0.95, 0.95, 0.90, 1.0)),
        "equipment": make_mat("equipment_box", (0.18, 0.24, 0.30, 1.0)),
    }
    epoch_metas = []
    for epoch in EPOCHS:
        print("Generating", epoch)
        create_epoch_scene(epoch, mats)
        rows, hit_counts, station_counts = raycast_epoch(epoch)
        epoch_metas.append(save_epoch(epoch, rows, hit_counts, station_counts))
    write_tables()
    create_epoch_scene("T5", mats)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "blender_lidar_t0t5_realistic.blend"))
    manifest = {
        "dataset": "blender_lidar_t0t5_realistic",
        "created_by": "tools/create_blender_lidar_t0t5_realistic.py",
        "purpose": "Realistic Blender/MCP T0-T5 LiDAR dataset for registration, denoise, time-series deformation, M3C2, and demo video.",
        "units": "meters",
        "columns": HEADER,
        "axis": "curved tunnel; chainage is arc length",
        "length_m": LENGTH,
        "radius_m": RADIUS,
        "curve_radius_m": CURVE_R,
        "scanner": {
            "type": "simulated TLS raycast",
            "stations_chainage_m": STATION_S,
            "azimuth_step_deg": AZ_STEP_DEG,
            "elevation_step_deg": EL_STEP_DEG,
            "elevation_range_deg": [EL_MIN_DEG, EL_MAX_DEG],
            "max_range_m": MAX_RANGE_M,
            "noise_model": "0.0015 + 0.000055*range + 0.0018*(1-incidence)",
            "pose_bias": POSE_BIAS,
        },
        "labels": LABELS,
        "deformation_specs": {
            "crown_settlement_chainage_m": 24.0,
            "sidewall_convergence_chainage_m": 50.0,
            "local_damage_chainage_m": 72.0,
            "ring_joint_offset_chainage_m": 60.0,
        },
        "epochs": epoch_metas,
    }
    with (OUT_DIR / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    write_readme()
    print(json.dumps({"status": "ok", "out_dir": str(OUT_DIR), "epochs": len(epoch_metas)}, indent=2))

main()
