r"""Create T0-T5 Step 6 data from a full tunnel-shaped sample point cloud.

Default source is the full circular tunnel sample:
    data/sample_pcd/circle_tunnel_dw.las

The script detects the tunnel longitudinal axis from the largest bounding-box
span, keeps Z as vertical, applies controlled deformation in local tunnel
coordinates, writes LAS/TXT, and optionally builds a Blender MCP preview scene.
No raycasting is used.
"""

from __future__ import annotations

import argparse
import csv
import json
import socket
from pathlib import Path

import laspy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "sample_pcd" / "circle_tunnel_dw.las"
DEFAULT_OUT = ROOT / "data" / "sample_tunnel_full_t0t5_step6"

EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
CROWN_MM = {"T0": 0.0, "T1": -5.0, "T2": -12.0, "T3": -20.0, "T4": -30.0, "T5": -45.0}
CONV_MM = {"T0": 0.0, "T1": 0.0, "T2": -5.0, "T3": -12.0, "T4": -22.0, "T5": -35.0}
LOCAL_MM = {"T0": 0.0, "T1": 0.0, "T2": 0.0, "T3": -15.0, "T4": -25.0, "T5": -40.0}
POSE_BIAS_MM = {"T0": (0.0, 0.0, 0.0), "T1": (1.0, -2.0, 0.5), "T2": (-1.5, 1.0, -0.5), "T3": (2.0, 2.0, 1.0), "T4": (-2.5, -2.0, 1.0), "T5": (3.0, -2.5, 1.5)}

BLENDER_CODE = r'''
import bpy
import json
from pathlib import Path
OUT_DIR = Path(r"__OUT_DIR__")
EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
COLORS = [(0.55,0.55,0.55,1), (0.25,0.55,0.90,1), (0.25,0.75,0.45,1), (0.95,0.65,0.25,1), (0.95,0.35,0.25,1), (0.75,0.20,0.20,1)]
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for idx, epoch in enumerate(EPOCHS):
    verts = []
    with (OUT_DIR / f"{epoch}_preview.xyz").open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip() or line.startswith('#'):
                continue
            x, y, z = map(float, line.split()[:3])
            verts.append((x, y + idx * 70.0, z))
    mesh = bpy.data.meshes.new(f"{epoch}_full_tunnel_preview_mesh")
    mesh.from_pydata(verts, [], [])
    mesh.update()
    obj = bpy.data.objects.new(f"{epoch}_from_full_tunnel_sample", mesh)
    bpy.context.collection.objects.link(obj)
    mat = bpy.data.materials.new(f"{epoch}_mat")
    mat.diffuse_color = COLORS[idx]
    obj.data.materials.append(mat)
    obj.show_name = True
bpy.ops.object.light_add(type='SUN', location=(80, -80, 80))
bpy.ops.object.camera_add(location=(120, -170, 80), rotation=(1.1, 0, 0.62))
bpy.context.scene.camera = bpy.context.object
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / 'full_tunnel_sample_t0t5_preview.blend'))
print(json.dumps({'status': 'ok', 'blend': str(OUT_DIR / 'full_tunnel_sample_t0t5_preview.blend')}, indent=2))
'''


def choose_axes(points: np.ndarray) -> tuple[int, int, int]:
    spans = np.ptp(points, axis=0)
    chain_axis = int(np.argmax(spans))
    vertical_axis = 2
    if chain_axis == vertical_axis:
        vertical_axis = int(np.argsort(spans)[1])
    lateral_axis = ({0, 1, 2} - {chain_axis, vertical_axis}).pop()
    return chain_axis, lateral_axis, vertical_axis


def downsample(points: np.ndarray, intensity: np.ndarray, max_points: int) -> tuple[np.ndarray, np.ndarray]:
    if max_points <= 0 or len(points) <= max_points:
        return points, intensity
    # Deterministic uniform stride preserves global tunnel coverage better than random for previews/tests.
    step = int(np.ceil(len(points) / max_points))
    idx = np.arange(0, len(points), step)
    if len(idx) > max_points:
        idx = idx[:max_points]
    return points[idx], intensity[idx]


def deform(points: np.ndarray, epoch: str, axes: tuple[int, int, int], rng: np.random.Generator) -> np.ndarray:
    if epoch == "T0":
        return points.copy()
    chain_axis, lateral_axis, vertical_axis = axes
    out = points.copy()
    chain = points[:, chain_axis]
    lateral = points[:, lateral_axis]
    vertical = points[:, vertical_axis]
    chain_min = float(chain.min())
    chain_span = max(1e-9, float(np.ptp(chain)))
    chain_norm = (chain - chain_min) / chain_span
    lat0 = float(np.median(lateral))
    z0 = float(np.median(vertical))
    theta = np.arctan2(vertical - z0, lateral - lat0)

    crown = CROWN_MM[epoch] / 1000.0
    conv = CONV_MM[epoch] / 1000.0
    local = LOCAL_MM[epoch] / 1000.0
    crown_w = np.exp(-0.5 * ((chain_norm - 0.28) / 0.085) ** 2) * np.maximum(0.0, np.sin(theta)) ** 1.7
    side_w = np.exp(-0.5 * ((chain_norm - 0.55) / 0.105) ** 2) * np.abs(np.cos(theta)) ** 1.4
    local_angle = np.arctan2(np.sin(theta - np.deg2rad(55.0)), np.cos(theta - np.deg2rad(55.0)))
    local_w = np.exp(-0.5 * ((chain_norm - 0.78) / 0.045) ** 2) * np.exp(-0.5 * (local_angle / 0.24) ** 2)

    out[:, vertical_axis] += crown * crown_w + local * local_w
    out[:, lateral_axis] += -np.sign(lateral - lat0) * abs(conv) * side_w
    out += rng.normal(0.0, 0.0007, out.shape)
    out += np.asarray(POSE_BIAS_MM[epoch], dtype=np.float64) / 1000.0
    return out


def normals(points: np.ndarray, axes: tuple[int, int, int]) -> np.ndarray:
    _, lateral_axis, vertical_axis = axes
    n = np.zeros_like(points)
    lat0 = float(np.median(points[:, lateral_axis]))
    z0 = float(np.median(points[:, vertical_axis]))
    n[:, lateral_axis] = points[:, lateral_axis] - lat0
    n[:, vertical_axis] = points[:, vertical_axis] - z0
    length = np.linalg.norm(n, axis=1)
    ok = length > 1e-9
    n[ok] /= length[ok, None]
    n[~ok, vertical_axis] = 1.0
    return n


def write_las(path: Path, points: np.ndarray, intensity: np.ndarray, source_header) -> None:
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = source_header.scales
    header.offsets = points.min(axis=0)
    las = laspy.LasData(header)
    las.x, las.y, las.z = points[:, 0], points[:, 1], points[:, 2]
    las.intensity = intensity.astype(np.uint16)
    las.classification = np.ones(len(points), dtype=np.uint8)
    gray = np.clip(intensity, 0, 65535).astype(np.uint16)
    las.red = gray
    las.green = gray
    las.blue = gray
    las.write(str(path))


def write_txt(path: Path, points: np.ndarray, normal: np.ndarray, intensity: np.ndarray) -> None:
    arr = np.column_stack([points, normal, intensity.astype(np.float64) / 65535.0, np.ones(len(points), dtype=np.uint8)])
    np.savetxt(path, arr, fmt=["%.5f", "%.5f", "%.5f", "%.6f", "%.6f", "%.6f", "%.6f", "%d"], header="x y z nx ny nz intensity label", comments="# ")


def write_preview(path: Path, points: np.ndarray, max_points: int) -> None:
    step = max(1, int(np.ceil(len(points) / max_points)))
    np.savetxt(path, points[::step, :3], fmt="%.5f %.5f %.5f")


def send_blender_command(command_type: str, params: dict, host: str, port: int, timeout: float = 600.0) -> dict:
    payload = {"type": command_type, "params": params}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.sendall(json.dumps(payload).encode("utf-8"))
        chunks = []
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


def write_tables(out_dir: Path) -> None:
    with (out_dir / "ground_truth.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "crown_settlement_mm", "sidewall_convergence_mm", "local_damage_mm"])
        for e in EPOCHS:
            w.writerow([e, CROWN_MM[e], CONV_MM[e], LOCAL_MM[e]])
    with (out_dir / "baseline_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "crown_delta_mm", "sidewall_delta_mm", "local_delta_mm"])
        for e in EPOCHS[1:]:
            w.writerow([f"T0-{e}", CROWN_MM[e], CONV_MM[e], LOCAL_MM[e]])
    with (out_dir / "incremental_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "crown_increment_mm", "sidewall_increment_mm", "local_increment_mm"])
        for a, b in zip(EPOCHS[:-1], EPOCHS[1:]):
            w.writerow([f"{a}-{b}", CROWN_MM[b] - CROWN_MM[a], CONV_MM[b] - CONV_MM[a], LOCAL_MM[b] - LOCAL_MM[a]])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--max-points", type=int, default=700_000, help="0 keeps all source points")
    parser.add_argument("--preview-points", type=int, default=80_000)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--skip-blender", action="store_true")
    args = parser.parse_args()

    source = Path(args.source)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    las = laspy.read(source)
    points = np.column_stack([np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)]).astype(np.float64)
    intensity = np.asarray(las.intensity, dtype=np.uint16)
    if int(intensity.max()) == 0:
        z_scaled = (points[:, 2] - points[:, 2].min()) / max(1e-9, np.ptp(points[:, 2]))
        intensity = np.clip((0.35 + 0.45 * z_scaled) * 65535, 0, 65535).astype(np.uint16)
    points, intensity = downsample(points, intensity, args.max_points)
    axes = choose_axes(points)
    rng = np.random.default_rng(20260629)

    metas = []
    for epoch in EPOCHS:
        pts = deform(points, epoch, axes, rng)
        n = normals(pts, axes)
        write_las(out_dir / f"{epoch}.las", pts, intensity, las.header)
        write_txt(out_dir / f"{epoch}.txt", pts, n, intensity)
        write_preview(out_dir / f"{epoch}_preview.xyz", pts, args.preview_points)
        meta = {"epoch": epoch, "points": int(len(pts)), "las_file": f"{epoch}.las", "txt_file": f"{epoch}.txt", "bounds_min": pts.min(0).tolist(), "bounds_max": pts.max(0).tolist(), "deformation_mm": {"crown_settlement": CROWN_MM[epoch], "sidewall_convergence": CONV_MM[epoch], "local_damage": LOCAL_MM[epoch]}}
        (out_dir / f"{epoch}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        metas.append(meta)

    write_tables(out_dir)
    manifest = {"dataset": out_dir.name, "created_by": "tools/create_t0t5_from_tunnel_sample_autoaxis.py", "source": str(source), "method": "full tunnel sample point cloud deformation; no raycasting", "axes": {"chain_axis": axes[0], "lateral_axis": axes[1], "vertical_axis": axes[2]}, "points_per_epoch": int(len(points)), "epochs": metas}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    readme = f"""# Full Tunnel Sample T0-T5 Step 6 Dataset

Source: `{source}`

This dataset is based on a full tunnel-shaped sample point cloud, not the small u-type cut and not a procedural tunnel. No raycasting is used.

Points per epoch: `{len(points):,}`

Axes: chain={axes[0]}, lateral={axes[1]}, vertical={axes[2]}

Use `T0.las` as reference and add `T1.las` to `T5.las` for Step 6 testing.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    if not args.skip_blender:
        code = BLENDER_CODE.replace("__OUT_DIR__", str(out_dir.resolve()).replace("\\", "\\\\"))
        response = send_blender_command("execute_code", {"code": code}, args.host, args.port)
        if response.get("status") != "success":
            print(json.dumps(response, indent=2, ensure_ascii=False))
            return 1
        print(json.dumps(response.get("result", response), indent=2, ensure_ascii=False))
    print(f"Dataset written to: {out_dir}")
    print(f"Source: {source}")
    print(f"Points per epoch: {len(points):,}")
    print(f"Axes chain/lateral/vertical: {axes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
