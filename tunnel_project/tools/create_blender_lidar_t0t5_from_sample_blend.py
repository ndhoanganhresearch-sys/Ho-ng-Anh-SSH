r"""Create T0-T5 LiDAR epochs from data/sample_pcd/Tunel.blend.

This generator uses the existing sample tunnel Blender file as the source
geometry, then applies progressive epoch deformation and raycasts the scene.

Run from tunnel_project while Blender MCP listens on localhost:9876:
    ..\.venv\Scripts\python.exe tools\create_blender_lidar_t0t5_from_sample_blend.py
"""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_BLEND = ROOT / "data" / "sample_pcd" / "Tunel.blend"
OUT_DIR = ROOT / "data" / "blender_lidar_t0t5_sample_based"

BLENDER_CODE = r'''
import bpy
import csv
import json
import math
import random
from pathlib import Path
from mathutils import Vector

SAMPLE_BLEND = Path(r"__SAMPLE_BLEND__")
OUT_DIR = Path(r"__OUT_DIR__")
OUT_DIR.mkdir(parents=True, exist_ok=True)
random.seed(20260629)

EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
CROWN_MM = {"T0": 0.0, "T1": -4.0, "T2": -9.0, "T3": -16.0, "T4": -24.0, "T5": -35.0}
CONV_MM = {"T0": 0.0, "T1": -1.0, "T2": -4.0, "T3": -8.0, "T4": -14.0, "T5": -22.0}
LOCAL_MM = {"T0": 0.0, "T1": 0.0, "T2": 0.0, "T3": -8.0, "T4": -16.0, "T5": -28.0}
POSE_BIAS = {
    "T0": (0.000, 0.000, 0.000, 0.000),
    "T1": (0.003, -0.006, 0.001, 0.010),
    "T2": (-0.005, 0.004, -0.001, -0.012),
    "T3": (0.007, 0.006, 0.002, 0.018),
    "T4": (-0.009, -0.008, 0.003, -0.025),
    "T5": (0.012, -0.010, 0.004, 0.030),
}
LABEL_BY_NAME = {
    "Cylinder": 1,
    "Cylinder.003": 1,
    "Cylinder.001": 2,
    "Cylinder.002": 4,
    "Cylinder.005": 4,
    "Cylinder.006": 5,
    "Cylinder.007": 5,
    "Circle": 8,
    "Plane.001": 6,
    "Sphere.001": 7,
}
KEY_BY_LABEL = {1: "lining", 2: "rail_or_track", 4: "cable_or_pipe", 5: "fixture", 6: "walkway_or_panel", 7: "target", 8: "equipment"}
INTENSITY_BY_LABEL = {1: 0.50, 2: 0.72, 4: 0.28, 5: 0.82, 6: 0.45, 7: 0.95, 8: 0.55}
HEADER = "x y z nx ny nz intensity label"
AZ_STEP_DEG = 0.35
EL_STEP_DEG = 0.35
EL_MIN_DEG = -45.0
EL_MAX_DEG = 82.0
MAX_RANGE_M = 14.0


def scene_bounds():
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or not obj.data.vertices:
            continue
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            mins.x = min(mins.x, w.x); mins.y = min(mins.y, w.y); mins.z = min(mins.z, w.z)
            maxs.x = max(maxs.x, w.x); maxs.y = max(maxs.y, w.y); maxs.z = max(maxs.z, w.z)
    return mins, maxs


def assign_labels():
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        label = LABEL_BY_NAME.get(obj.name, 8)
        obj["label"] = label
        obj["material_key"] = KEY_BY_LABEL.get(label, "equipment")


def deform_sample_tunnel(epoch, bounds):
    if epoch == "T0":
        return
    mins, maxs = bounds
    y0, y1 = mins.y, maxs.y
    length = y1 - y0
    cx = (mins.x + maxs.x) * 0.5
    cz = (mins.z + maxs.z) * 0.5
    crown_m = CROWN_MM[epoch] / 1000.0
    conv_m = CONV_MM[epoch] / 1000.0
    local_m = LOCAL_MM[epoch] / 1000.0
    crown_y = y0 + 0.30 * length
    conv_y = y0 + 0.58 * length
    local_y = y0 + 0.78 * length
    lining_names = {"Cylinder", "Cylinder.003"}
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.name not in lining_names:
            continue
        mw = obj.matrix_world
        inv = mw.inverted()
        for vert in obj.data.vertices:
            w = mw @ vert.co
            theta = math.atan2(w.z - cz, w.x - cx)
            crown_w = math.exp(-0.5 * ((w.y - crown_y) / (0.10 * length)) ** 2) * max(0.0, math.sin(theta)) ** 1.6
            conv_w = math.exp(-0.5 * ((w.y - conv_y) / (0.12 * length)) ** 2) * abs(math.cos(theta)) ** 1.4
            local_w = math.exp(-0.5 * ((w.y - local_y) / (0.055 * length)) ** 2) * math.exp(-0.5 * ((theta - math.radians(62.0)) / 0.25) ** 2)
            w.x += -math.copysign(abs(conv_m) * conv_w, w.x - cx)
            w.z += crown_m * crown_w + local_m * local_w
            vert.co = inv @ w
        obj.data.update()


def station_positions(bounds, epoch):
    mins, maxs = bounds
    x = (mins.x + maxs.x) * 0.5
    z = mins.z + 0.35 * (maxs.z - mins.z)
    y0, y1 = mins.y, maxs.y
    length = y1 - y0
    bias_x, bias_y, bias_z, yaw_deg = POSE_BIAS[epoch]
    stations = []
    for frac in [0.08, 0.28, 0.48, 0.68, 0.88]:
        stations.append((Vector((x + bias_x, y0 + frac * length + bias_y, z + bias_z)), math.radians(yaw_deg)))
    return stations


def rotate_z(vec, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return Vector((c * vec.x - s * vec.y, s * vec.x + c * vec.y, vec.z))


def raycast_epoch(epoch, bounds):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rows = []
    hit_counts = {}
    az_values = [i * AZ_STEP_DEG for i in range(int(360.0 / AZ_STEP_DEG))]
    el_values = []
    elev = EL_MIN_DEG
    while elev <= EL_MAX_DEG + 1e-9:
        el_values.append(elev)
        elev += EL_STEP_DEG
    station_counts = []
    for idx, (origin, yaw) in enumerate(station_positions(bounds, epoch)):
        local_hits = 0
        for az in az_values:
            ca, sa = math.cos(math.radians(az)), math.sin(math.radians(az))
            for el in el_values:
                ce, se = math.cos(math.radians(el)), math.sin(math.radians(el))
                direction = rotate_z(Vector((ca * ce, sa * ce, se)), yaw).normalized()
                hit, loc, normal, face_index, obj, matrix = bpy.context.scene.ray_cast(depsgraph, origin, direction, distance=MAX_RANGE_M)
                if not hit or obj is None:
                    continue
                label = int(obj.get("label", 8))
                dist = (loc - origin).length
                incidence = max(0.03, abs(direction.dot(normal.normalized())))
                if incidence < 0.08 and random.random() < 0.60:
                    continue
                sigma = 0.0009 + 0.00005 * dist + 0.0012 * (1.0 - incidence)
                noisy = loc + direction * random.gauss(0.0, sigma)
                intensity = INTENSITY_BY_LABEL.get(label, 0.45) * incidence ** 0.45 / (1.0 + 0.015 * dist * dist)
                intensity = max(0.01, min(1.0, intensity + random.gauss(0.0, 0.025)))
                rows.append([noisy.x, noisy.y, noisy.z, normal.x, normal.y, normal.z, intensity, label])
                hit_counts[str(label)] = hit_counts.get(str(label), 0) + 1
                local_hits += 1
        station_counts.append({"station": idx, "hits": local_hits})
    return rows, hit_counts, station_counts


def save_epoch(epoch, rows, hit_counts, station_counts, bounds):
    txt = OUT_DIR / f"{epoch}.txt"
    with txt.open("w", encoding="utf-8") as f:
        f.write("# " + HEADER + "\n")
        for r in rows:
            f.write("%.5f %.5f %.5f %.6f %.6f %.6f %.6f %d\n" % tuple(r))
    meta = {
        "epoch": epoch,
        "file": txt.name,
        "points": len(rows),
        "hit_counts_by_label": hit_counts,
        "station_counts": station_counts,
        "pose_bias_m_yaw_deg": POSE_BIAS[epoch],
        "deformation_mm": {
            "crown_settlement": CROWN_MM[epoch],
            "sidewall_convergence": CONV_MM[epoch],
            "local_damage": LOCAL_MM[epoch],
        },
        "source_bounds_min": [bounds[0].x, bounds[0].y, bounds[0].z],
        "source_bounds_max": [bounds[1].x, bounds[1].y, bounds[1].z],
    }
    (OUT_DIR / f"{epoch}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def write_tables():
    with (OUT_DIR / "ground_truth.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "crown_settlement_mm", "sidewall_convergence_mm", "local_damage_mm"])
        for e in EPOCHS:
            w.writerow([e, CROWN_MM[e], CONV_MM[e], LOCAL_MM[e]])
    with (OUT_DIR / "baseline_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "crown_delta_mm", "sidewall_delta_mm", "local_delta_mm"])
        for e in EPOCHS[1:]:
            w.writerow([f"T0-{e}", CROWN_MM[e], CONV_MM[e], LOCAL_MM[e]])
    with (OUT_DIR / "incremental_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "crown_increment_mm", "sidewall_increment_mm", "local_increment_mm"])
        for a, b in zip(EPOCHS[:-1], EPOCHS[1:]):
            w.writerow([f"{a}-{b}", CROWN_MM[b]-CROWN_MM[a], CONV_MM[b]-CONV_MM[a], LOCAL_MM[b]-LOCAL_MM[a]])


def write_readme():
    text = """# Blender LiDAR T0-T5 Sample-Based Dataset

This dataset is generated from `data/sample_pcd/Tunel.blend`, not from a procedural tunnel.

## Source

- Blender source: `data/sample_pcd/Tunel.blend`
- Epochs: `T0` to `T5`
- Columns: `x y z nx ny nz intensity label`

## Labels

1 lining, 2 rail/track, 4 cable/pipe, 5 fixture, 6 walkway/panel, 7 target, 8 equipment/other.

## Ground truth deformation

- Crown settlement: 0 to -35 mm
- Sidewall convergence: 0 to -22 mm
- Local damage: starts at T3 and reaches -28 mm at T5

## Suggested workflow

1. Load `T0.las` as reference.
2. Add `T1.las` to `T5.las`.
3. Run registration because T1-T5 include small pose bias.
4. Run Step 6 time-series/M3C2 analysis.
"""
    (OUT_DIR / "README.md").write_text(text, encoding="utf-8")


def main():
    epoch_metas = []
    for epoch in EPOCHS:
        print("Opening source and generating", epoch)
        bpy.ops.wm.open_mainfile(filepath=str(SAMPLE_BLEND))
        assign_labels()
        bounds = scene_bounds()
        deform_sample_tunnel(epoch, bounds)
        rows, hit_counts, station_counts = raycast_epoch(epoch, bounds)
        epoch_metas.append(save_epoch(epoch, rows, hit_counts, station_counts, bounds))
    write_tables()
    write_readme()
    bpy.ops.wm.open_mainfile(filepath=str(SAMPLE_BLEND))
    assign_labels()
    deform_sample_tunnel("T5", scene_bounds())
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "sample_based_T5_scene.blend"))
    manifest = {
        "dataset": "blender_lidar_t0t5_sample_based",
        "created_by": "tools/create_blender_lidar_t0t5_from_sample_blend.py",
        "source_blend": str(SAMPLE_BLEND),
        "purpose": "T0-T5 time-series LiDAR dataset based on the provided sample tunnel Blender file.",
        "columns": HEADER,
        "labels": LABEL_BY_NAME,
        "epochs": epoch_metas,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "out_dir": str(OUT_DIR), "epochs": len(epoch_metas)}, indent=2))

main()
'''


def send_blender_command(command_type: str, params: dict, host: str, port: int, timeout: float = 1800.0) -> dict:
    payload = {"type": command_type, "params": params}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.sendall(json.dumps(payload).encode("utf-8"))
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(8192)
            if not chunk:
                break
            chunks.append(chunk)
            data = b"".join(chunks)
            try:
                return json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                continue
    raise RuntimeError("No complete JSON response received from Blender MCP")


def convert_txt_epochs_to_las(out_dir: Path) -> None:
    try:
        import laspy
        import numpy as np
    except Exception as exc:
        print(f"LAS export skipped: {exc}")
        return
    for txt_path in sorted(out_dir.glob("T[0-5].txt")):
        arr = np.loadtxt(txt_path, comments="#")
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        points = arr[:, :3]
        header = laspy.LasHeader(point_format=3, version="1.2")
        header.scales = np.array([1e-4, 1e-4, 1e-4])
        header.offsets = points.min(axis=0)
        las = laspy.LasData(header)
        las.x, las.y, las.z = points[:, 0], points[:, 1], points[:, 2]
        las.intensity = np.clip(arr[:, 6] * 65535, 0, 65535).astype(np.uint16)
        las.classification = arr[:, 7].astype(np.uint8)
        gray = np.clip(arr[:, 6] * 65535, 0, 65535).astype(np.uint16)
        las.red = gray; las.green = gray; las.blue = gray
        las.write(str(txt_path.with_suffix(".las")))
        print(f"LAS written: {txt_path.with_suffix('.las')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--out", default=str(OUT_DIR))
    parser.add_argument("--source", default=str(SAMPLE_BLEND))
    parser.add_argument("--skip-las", action="store_true")
    args = parser.parse_args()
    out_dir = Path(args.out).resolve()
    source = Path(args.source).resolve()
    code = BLENDER_CODE.replace("__OUT_DIR__", str(out_dir).replace("\\", "\\\\")).replace("__SAMPLE_BLEND__", str(source).replace("\\", "\\\\"))
    response = send_blender_command("execute_code", {"code": code}, args.host, args.port)
    if response.get("status") != "success":
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps(response.get("result", response), indent=2, ensure_ascii=False))
    if not args.skip_las:
        convert_txt_epochs_to_las(out_dir)
    print(f"Dataset written to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
