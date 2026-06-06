"""
generate_test_pcd.py
Sinh T0 / Tn point cloud khớp format sample_pcd thực tế:
  - LAS 1.2, Point Format 2 (XYZ + intensity + RGB)
  - Scale 1e-5, giống box_tunnel_dw.las
  - Noise LiDAR thực tế σ = 5 mm
  - Có TXT X Y Z R G B khớp OS1_tunnel_entire(5cm).txt

Ground-truth deformation (tại y = 0, Gaussian σ = 8 m):
  Crown settlement  : -50 mm  (đỉnh lún xuống)
  Sidewall converge : -30 mm  (vách thu vào)
  Invert heave      : +10 mm  (đáy nâng lên)
"""

import numpy as np
import laspy
import os

RNG = np.random.default_rng(42)

# ── Tham số hầm ──────────────────────────────────────────────────────────────
RADIUS   = 4.0          # m  (đường kính 8 m)
LENGTH   = 50.0         # m  dọc trục Y
N_RINGS  = 80           # vòng chu vi
N_SEGS   = 300          # đoạn dọc hầm  → ~24 000 pts/layer, tổng ~600 k pts
NOISE_M  = 0.005        # σ nhiễu LiDAR = 5 mm

# ── Deformation ground truth ──────────────────────────────────────────────────
CROWN_MM    = -50.0     # mm lún đỉnh   (dương = nâng, âm = lún)
SIDEWALL_MM = -30.0     # mm vách thu vào (âm = thu)
INVERT_MM   =  10.0     # mm đáy nâng
SIGMA_Y     = 8.0       # m  Gaussian spread dọc hầm

OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "sample_pcd")
os.makedirs(OUT_DIR, exist_ok=True)


def make_tunnel_points(apply_deform: bool) -> np.ndarray:
    """Trả về array (N, 6): x y z r g b"""
    angles = np.linspace(0, 2 * np.pi, N_RINGS, endpoint=False)
    ys     = np.linspace(-LENGTH / 2, LENGTH / 2, N_SEGS)

    all_pts = []
    for y in ys:
        gauss = np.exp(-0.5 * (y / SIGMA_Y) ** 2)

        for a in angles:
            r_local = RADIUS

            if apply_deform:
                # Crown settlement (sin a = 1 ở đỉnh)
                crown_w  = max(0.0, np.sin(a))
                # Invert heave (sin a = -1 ở đáy)
                invert_w = max(0.0, -np.sin(a))
                # Sidewall convergence (|cos a| = 1 ở vách)
                side_w   = abs(np.cos(a))

                dz  = (CROWN_MM * crown_w + INVERT_MM * invert_w) * gauss / 1000.0
                dr_side = SIDEWALL_MM * side_w * gauss / 1000.0

                x = np.cos(a) * (RADIUS + dr_side)
                z = np.sin(a) * RADIUS + dz
            else:
                x = np.cos(a) * RADIUS
                z = np.sin(a) * RADIUS

            # Nhiễu LiDAR theo hướng pháp tuyến bề mặt (radial)
            noise = RNG.normal(0, NOISE_M)
            nx = np.cos(a)
            nz = np.sin(a)
            x += noise * nx
            z += noise * nz

            # Màu bê tông: xám nhạt + biến thiên nhỏ (~160-200 / 255)
            base = int(RNG.integers(155, 200))
            r8, g8, b8 = base, base - int(RNG.integers(0, 8)), base - int(RNG.integers(0, 12))

            all_pts.append([x, y, z, r8, g8, b8])

    return np.array(all_pts, dtype=np.float64)


def save_las(pts: np.ndarray, path: str):
    """LAS 1.2 Point Format 2 (XYZ + intensity + RGB), scale=1e-5"""
    hdr = laspy.LasHeader(point_format=2, version="1.2")
    hdr.scales  = np.array([1e-5, 1e-5, 1e-5])
    hdr.offsets = np.array([0.0, 0.0, 0.0])

    las = laspy.LasData(header=hdr)
    las.x = pts[:, 0]
    las.y = pts[:, 1]
    las.z = pts[:, 2]
    las.intensity      = np.zeros(len(pts), dtype=np.uint16)
    # RGB trong LAS là 16-bit (0-65535); scale từ 8-bit
    las.red   = (pts[:, 3].astype(np.uint16) * 256)
    las.green = (pts[:, 4].astype(np.uint16) * 256)
    las.blue  = (pts[:, 5].astype(np.uint16) * 256)
    las.write(path)
    print(f"  Saved LAS: {os.path.basename(path)}  ({len(pts):,} pts, {os.path.getsize(path)/1e6:.1f} MB)")


def save_txt(pts: np.ndarray, path: str):
    """Format giống OS1_tunnel_entire(5cm).txt: X Y Z R G B"""
    rows = []
    for p in pts[::4]:   # lấy mỗi 4 điểm 1 để file txt nhỏ hơn (~5 cm spacing)
        rows.append(f"{p[0]:.5f} {p[1]:.5f} {p[2]:.5f} {int(p[3])} {int(p[4])} {int(p[5])}")
    with open(path, "w") as f:
        f.write("\n".join(rows))
    print(f"  Saved TXT: {os.path.basename(path)}  ({len(rows):,} pts, {os.path.getsize(path)/1e6:.1f} MB)")


# ── Sinh T0 ──────────────────────────────────────────────────────────────────
print("Generating T0 (reference)...")
pts_t0 = make_tunnel_points(apply_deform=False)
save_las(pts_t0, os.path.join(OUT_DIR, "Tunnel_T0.las"))
save_txt(pts_t0, os.path.join(OUT_DIR, "Tunnel_T0_5cm.txt"))

# ── Sinh Tn ──────────────────────────────────────────────────────────────────
print("\nGenerating Tn (deformed)...")
pts_tn = make_tunnel_points(apply_deform=True)
save_las(pts_tn, os.path.join(OUT_DIR, "Tunnel_Tn.las"))
save_txt(pts_tn, os.path.join(OUT_DIR, "Tunnel_Tn_5cm.txt"))

# ── Ground truth report ───────────────────────────────────────────────────────
print("\n✅ Done! Ground truth deformation:")
print(f"   Crown settlement  (đỉnh, y=0) : {CROWN_MM:+.1f} mm")
print(f"   Sidewall converge (vách, y=0) : {SIDEWALL_MM:+.1f} mm")
print(f"   Invert heave      (đáy,  y=0) : {INVERT_MM:+.1f} mm")
print(f"   Gaussian σ dọc hầm            : {SIGMA_Y} m")
print(f"\n   Files saved to: {OUT_DIR}")
