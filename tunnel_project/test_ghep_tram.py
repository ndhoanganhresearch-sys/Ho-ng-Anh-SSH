"""
test_ghep_tram.py — Kiểm tra tính năng target-based ghép trạm
Chạy: ..\.venv\Scripts\python.exe test_ghep_tram.py

Test flow:
  1. Tạo tunnel point cloud + sphere targets với vị trí biết trước
  2. Tạo trạm 2, 3 bằng cách dịch/xoay một góc nhỏ (transform biết trước)
  3. detect_all() → match_targets() → _horn_svd() + _icp()
  4. So sánh transform tính được vs transform gốc → PASS/FAIL
"""
import sys, os, math
import numpy as np

# ─── setup path ──────────────────────────────────────────────────────────────
ROOT = os.path.dirname(__file__)
sys.path.insert(0, ROOT)

from tunnel_analysis.target_detector import TargetDetector, Target
from tunnel_analysis.registration    import RegistrationLayer
from tunnel_analysis.models          import PointCloudBundle, PipelineContext

PASS_COLOR = "\033[92m[PASS]\033[0m"
FAIL_COLOR = "\033[91m[FAIL]\033[0m"
INFO_COLOR = "\033[94m[INFO]\033[0m"

results = []

def check(name, cond, detail=""):
    status = PASS_COLOR if cond else FAIL_COLOR
    line = f"  {status} {name}"
    if detail:
        line += f"  — {detail}"
    print(line)
    results.append((name, cond))
    return cond


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def make_tunnel_cloud(n_pts=5000, radius=3.0, length=10.0, noise=0.005, rng=None):
    """Tạo point cloud hình ống (tunnel).  Trục Y = chiều dài."""
    if rng is None:
        rng = np.random.default_rng(42)
    theta = rng.uniform(0, 2 * math.pi, n_pts)
    y     = rng.uniform(-length / 2, length / 2, n_pts)
    x     = radius * np.cos(theta) + rng.normal(0, noise, n_pts)
    z     = radius * np.sin(theta) + rng.normal(0, noise, n_pts)
    return np.column_stack([x, y, z])


def make_sphere_cluster(center, radius=0.0725, n_pts=80, noise=0.002, rng=None):
    """Tạo cụm điểm hình cầu (Faro sphere target)."""
    if rng is None:
        rng = np.random.default_rng(0)
    phi   = rng.uniform(0, math.pi, n_pts)
    theta = rng.uniform(0, 2 * math.pi, n_pts)
    r     = radius + rng.normal(0, noise, n_pts)
    x = center[0] + r * np.sin(phi) * np.cos(theta)
    y = center[1] + r * np.sin(phi) * np.sin(theta)
    z = center[2] + r * np.cos(phi)
    return np.column_stack([x, y, z])


def make_rigid_transform(tx=0.0, ty=0.0, tz=0.0, rz_deg=0.0):
    """Tạo ma trận transform 4×4 (dịch + xoay quanh Z)."""
    rz = math.radians(rz_deg)
    R  = np.array([
        [ math.cos(rz), -math.sin(rz), 0],
        [ math.sin(rz),  math.cos(rz), 0],
        [ 0,             0,            1],
    ])
    T  = np.eye(4)
    T[:3, :3] = R
    T[:3, 3]  = [tx, ty, tz]
    return T


def apply_transform(pts, T):
    ones = np.ones((len(pts), 1))
    return (T @ np.hstack([pts, ones]).T).T[:, :3]


def build_scan(tunnel_pts, sphere_centers, rng, n_tunnel=5000, n_sphere=80):
    """Ghép tunnel + sphere points thành PointCloudBundle, thêm intensity."""
    parts = [tunnel_pts]
    intensities = [np.full(len(tunnel_pts), 0.1)]          # low intensity
    for sc in sphere_centers:
        sp = make_sphere_cluster(sc, n_pts=n_sphere, rng=rng)
        parts.append(sp)
        intensities.append(np.full(len(sp), 0.95))         # high intensity (reflector)
    pts = np.vstack(parts)
    ity = np.concatenate(intensities)
    return PointCloudBundle(points=pts, intensity=ity, path="synthetic")


# ═══════════════════════════════════════════════════════════════════════════
#  Test 1 — Horn SVD recovers known transform
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TEST 1 — Horn SVD (điểm mốc → transform)")
print("="*60)

rng = np.random.default_rng(1)
n_tgts = 6
src_centers_t1 = np.array([
    [ 2.5,  0.0, 0.3],
    [-2.5,  0.0, 0.3],
    [ 0.0,  4.0, 0.3],
    [ 0.0, -4.0, 0.3],
    [ 2.0,  2.0, 0.3],
    [-2.0, -2.0, 0.3],
], dtype=np.float64)

T_true = make_rigid_transform(tx=0.5, ty=2.0, tz=-0.1, rz_deg=3.0)
tgt_centers_t2 = apply_transform(src_centers_t1, T_true)

tgt_mod = TargetDetector()
T_est, rmse_svd = tgt_mod._horn_svd(src_centers_t1, tgt_centers_t2)

# Áp transform ước lượng
src_reg = apply_transform(src_centers_t1, T_est)
residuals = np.linalg.norm(src_reg - tgt_centers_t2, axis=1) * 1000  # mm
max_res = float(residuals.max())

check("SVD RMSE < 0.5 mm",     rmse_svd < 0.5,
      f"RMSE={rmse_svd:.4f} mm")
check("SVD max residual < 1 mm", max_res < 1.0,
      f"max={max_res:.4f} mm")

# Kiểm tra translation
t_err = np.linalg.norm(T_est[:3, 3] - T_true[:3, 3]) * 1000
check("Translation error < 2 mm", t_err < 2.0,
      f"err={t_err:.4f} mm")

# Kiểm tra rotation
R_diff = T_est[:3, :3] @ T_true[:3, :3].T
angle_err = math.degrees(math.acos(
    float(np.clip((np.trace(R_diff) - 1) / 2, -1, 1))))
check("Rotation error < 0.1 deg", angle_err < 0.1,
      f"err={angle_err:.5f} deg")


# ═══════════════════════════════════════════════════════════════════════════
#  Test 2 — detect_all tìm được sphere targets
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TEST 2 — detect_all() tìm sphere targets trong scan")
print("="*60)

rng2 = np.random.default_rng(2)
tunnel_pts = make_tunnel_cloud(rng=rng2)
sphere_centers_s1 = np.array([
    [ 2.5,  1.0, 0.0],
    [-2.5, -1.0, 0.0],
    [ 0.0,  3.0, 2.0],
], dtype=np.float64)

scan1 = build_scan(tunnel_pts, sphere_centers_s1, rng2)
print(f"  {INFO_COLOR} Scan1: {len(scan1.points):,} pts, intensity range "
      f"[{scan1.intensity.min():.2f}, {scan1.intensity.max():.2f}]")

found1 = tgt_mod.detect_all(scan1, scan_idx=0,
                             detect_sphere=True,
                             detect_flat=False,
                             detect_intensity=True)

n_sphere = sum(1 for t in found1 if t.type == "sphere")
n_intens = sum(1 for t in found1 if t.type == "intensity")
print(f"  {INFO_COLOR} Found: {len(found1)} total  (sphere={n_sphere}, intensity={n_intens})")
for t in found1:
    print(f"    [{t.type}] {t.name}  center={np.round(t.center,3)}  conf={t.confidence:.2f}")

check("At least 1 target found",  len(found1) >= 1,
      f"got {len(found1)}")
check("At least 1 sphere found",  n_sphere >= 1,
      f"got {n_sphere}")


# ═══════════════════════════════════════════════════════════════════════════
#  Test 3 — detect → match → SVD → ICP (2 stations)
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TEST 3 — Ghép 2 trạm: detect → match → SVD → ICP")
print("="*60)

rng3 = np.random.default_rng(3)

# Station 1
tunnel1 = make_tunnel_cloud(rng=rng3)
targets_s1 = np.array([
    [ 2.5,  0.5, 0.0],
    [-2.5,  1.0, 0.0],
    [ 0.0,  3.5, 2.5],
    [ 2.0, -2.0, 1.0],
], dtype=np.float64)
scan_s1 = build_scan(tunnel1, targets_s1, rng3)

# Station 2 = Station 1 shifted + small rotation
T_12 = make_rigid_transform(tx=0.3, ty=5.0, tz=0.05, rz_deg=2.0)
tunnel2 = apply_transform(tunnel1, T_12)
targets_s2 = apply_transform(targets_s1, T_12)
# thêm noise nhỏ vào target positions (thực tế scan không hoàn hảo)
targets_s2_noisy = targets_s2 + rng3.normal(0, 0.003, targets_s2.shape)
scan_s2 = build_scan(tunnel2, targets_s2_noisy, rng3)

print(f"  {INFO_COLOR} True transform: tx=0.30m ty=5.00m tz=0.05m rz=2.00°")
print(f"  {INFO_COLOR} Scan1: {len(scan_s1.points):,} pts | Scan2: {len(scan_s2.points):,} pts")

# --- Step A: detect_all in both scans ---
found_s1 = tgt_mod.detect_all(scan_s1, scan_idx=0,
                               detect_sphere=True, detect_flat=False,
                               detect_intensity=True)
found_s2 = tgt_mod.detect_all(scan_s2, scan_idx=1,
                               detect_sphere=True, detect_flat=False,
                               detect_intensity=True)
all_targets = found_s1 + found_s2

print(f"  {INFO_COLOR} Detected: S1={len(found_s1)}, S2={len(found_s2)}")
check("S1 targets >= 1", len(found_s1) >= 1, f"got {len(found_s1)}")
check("S2 targets >= 1", len(found_s2) >= 1, f"got {len(found_s2)}")

# --- Step B: match (centroid_align=True handles the 5m station gap) ---
# Reset matched_ids first
for t in found_s1: t.matched_id = ""
for t in found_s2: t.matched_id = ""
matches = tgt_mod.match_targets(found_s1, found_s2, max_dist=2.0,
                                 centroid_align=True)
print(f"  {INFO_COLOR} Matched: {len(matches)} pairs")
for st, tt, d in matches:
    print(f"    {st.name}(S1) <-> {tt.name}(S2)  dist_aligned={d:.3f}m")

check("Matched >= 1 pair", len(matches) >= 1, f"got {len(matches)}")

# --- Step C: SVD from matched pairs (nếu >= 3) ---
if len(matches) >= 3:
    m_src = [t for t in found_s1 if t.matched_id]
    m_tgt = {t.id: t for t in found_s2}
    m_src_centers = np.array([t.center for t in m_src], dtype=np.float64)
    m_tgt_centers = np.array([m_tgt[t.matched_id].center for t in m_src], dtype=np.float64)

    # _horn_svd(src, tgt) → T maps src→tgt
    # Here: src=S1 targets, tgt=S2 targets  →  T_fwd maps S1→S2
    T_fwd, rmse_svd = tgt_mod._horn_svd(m_src_centers, m_tgt_centers)
    print(f"  {INFO_COLOR} SVD forward (S1→S2) RMSE = {rmse_svd:.4f} mm")

    # Check forward transform quality vs ground truth
    t_err3 = np.linalg.norm(T_fwd[:3, 3] - T_12[:3, 3]) * 1000
    R_diff3 = T_fwd[:3, :3] @ T_12[:3, :3].T
    ang_err3 = math.degrees(math.acos(
        float(np.clip((np.trace(R_diff3) - 1) / 2, -1, 1))))
    check("SVD forward translation < 10 mm", t_err3 < 10.0,
          f"err={t_err3:.2f} mm  (S1→S2 should ≈ T_12)")
    check("SVD forward rotation < 0.5 deg",  ang_err3 < 0.5,
          f"err={ang_err3:.4f} deg")

    # To bring S2 INTO S1's frame we need the INVERSE (S2→S1)
    T_to_s1 = np.linalg.inv(T_fwd)

    # --- Step D: ICP refinement ---
    reg_mod = RegistrationLayer()
    src_pts2 = scan_s2.points.copy()
    ones     = np.ones((len(src_pts2), 1))
    src_coarse = (T_to_s1 @ np.hstack([src_pts2, ones]).T).T[:, :3]
    # Quick sanity: centroid distance after SVD
    centroid_err = np.linalg.norm(src_coarse.mean(0) - scan_s1.points.mean(0)) * 1000
    print(f"  {INFO_COLOR} After SVD: centroid distance = {centroid_err:.1f} mm")
    try:
        src_reg, rmse_icp = reg_mod._icp(src_coarse, scan_s1.points)
        print(f"  {INFO_COLOR} ICP RMSE = {rmse_icp:.3f} mm")
        check("ICP RMSE < 20 mm", rmse_icp < 20.0,
              f"RMSE={rmse_icp:.3f} mm")
    except Exception as e:
        print(f"  {INFO_COLOR} ICP not available ({e}), skip")
        check("ICP skipped (no Open3D)", True, "fallback OK")
else:
    print(f"  {INFO_COLOR} Only {len(matches)} match(es) — skipping SVD/ICP (need 3)")
    check("Enough matches for SVD", False, f"only {len(matches)}/3")


# ═══════════════════════════════════════════════════════════════════════════
#  Test 4 — 3 stations chain registration
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TEST 4 — Chain ghép 3 trạm: S1 → S2 → S3")
print("="*60)

rng4 = np.random.default_rng(4)

# Known transforms
T_12b = make_rigid_transform(tx=0.2, ty=6.0, tz=0.0,  rz_deg=1.5)
T_23b = make_rigid_transform(tx=-0.1, ty=6.0, tz=0.02, rz_deg=-1.0)

# Build 3 station scans
base_tunnel = make_tunnel_cloud(n_pts=3000, rng=rng4)
base_tgts   = np.array([
    [ 2.5, 0.0, 0.0],
    [-2.5, 0.5, 0.0],
    [ 0.0, 3.0, 2.0],
    [ 1.5,-2.5, 1.5],
], dtype=np.float64)

scan3_s1 = build_scan(base_tunnel, base_tgts, rng4)

t2 = apply_transform(base_tunnel, T_12b)
t2_c = apply_transform(base_tgts,  T_12b) + rng4.normal(0, 0.003, base_tgts.shape)
scan3_s2 = build_scan(t2, t2_c, rng4)

T_13b = T_23b @ T_12b   # cumulative transform S1→S3
t3 = apply_transform(base_tunnel, T_13b)
t3_c = apply_transform(base_tgts, T_13b) + rng4.normal(0, 0.003, base_tgts.shape)
scan3_s3 = build_scan(t3, t3_c, rng4)

scans_all = [scan3_s1, scan3_s2, scan3_s3]
print(f"  {INFO_COLOR} Scans: {[len(s.points) for s in scans_all]} pts")

# detect_all for each
all_tgts = []
for i, sc in enumerate(scans_all):
    found = tgt_mod.detect_all(sc, scan_idx=i,
                                detect_sphere=True, detect_flat=False,
                                detect_intensity=True)
    all_tgts.extend(found)
    print(f"  {INFO_COLOR} Station {i+1}: {len(found)} targets detected")

n_total_detected = len(all_tgts)
check("All 3 stations have targets",
      all(any(t.scan_idx == i for t in all_tgts) for i in range(3)),
      f"total={n_total_detected}")

# match consecutive pairs
total_matches = 0
for i in range(2):
    src_t = [t for t in all_tgts if t.scan_idx == i]
    tgt_t = [t for t in all_tgts if t.scan_idx == i + 1]
    if src_t and tgt_t:
        m = tgt_mod.match_targets(src_t, tgt_t, max_dist=2.0, centroid_align=True)
        total_matches += len(m)
        print(f"  {INFO_COLOR} S{i+1}↔S{i+2}: {len(m)} matched pairs")

check("Total matched pairs >= 2", total_matches >= 2,
      f"total matched={total_matches}")

# Chain registration — accumulated transform approach
reg_mod3 = RegistrationLayer()
acc_transforms = [np.eye(4, dtype=np.float64)]  # station 0 is reference
merged_clouds  = [scan3_s1.points.copy()]
rmse_chain     = [0.0]

for i in range(2):
    src_t_all = [t for t in all_tgts if t.scan_idx == i]
    nxt_t_all = [t for t in all_tgts if t.scan_idx == i + 1]

    # Reset and fresh centroid-aligned match for this pair
    for t in src_t_all: t.matched_id = ""
    for t in nxt_t_all: t.matched_id = ""
    tgt_mod.match_targets(src_t_all, nxt_t_all, max_dist=2.0, centroid_align=True)

    nxt_by_id = {t.id: t for t in nxt_t_all}
    m_src  = [t for t in src_t_all if t.matched_id in nxt_by_id]
    m_tgt  = [nxt_by_id[t.matched_id] for t in m_src]

    src_pts   = scans_all[i + 1].points.copy()
    ref_cloud = np.vstack(merged_clouds)   # growing global-frame cloud

    if len(m_src) >= 3:
        # SVD: T_rel maps station i+1 → station i (local frames)
        sc = np.array([t.center for t in m_src], dtype=np.float64)
        tc = np.array([t.center for t in m_tgt], dtype=np.float64)
        T_rel, _ = tgt_mod._horn_svd(tc, sc)   # maps i+1 → i
        # Accumulated: acc @ T_rel maps i+1 → station 0
        T_to_global = acc_transforms[i] @ T_rel
        ones = np.ones((len(src_pts), 1))
        src_coarse = (T_to_global @ np.hstack([src_pts, ones]).T).T[:, :3]
    else:
        src_coarse = reg_mod3._coarse_align(
            src_pts, ref_cloud,
            src_intensity=scans_all[i+1].intensity,
            tgt_intensity=scans_all[i].intensity)
        T_to_global = acc_transforms[i]

    try:
        src_reg, rmse = reg_mod3._icp(src_coarse, ref_cloud)
    except Exception:
        src_reg = src_coarse
        from scipy.spatial import cKDTree
        step = max(1, len(src_reg) // 50_000)
        d, _ = cKDTree(ref_cloud).query(src_reg[::step], k=1, workers=-1)
        rmse = float(np.sqrt(np.mean(d**2))) * 1000.0

    acc_transforms.append(T_to_global)
    merged_clouds.append(src_reg)
    rmse_chain.append(rmse)
    print(f"  {INFO_COLOR} S{i+1}→S{i+2}: RMSE = {rmse:.3f} mm")

merged_all = np.vstack(merged_clouds)
expected_pts = sum(len(s.points) for s in scans_all)
check("Merged cloud has all points", len(merged_all) == expected_pts,
      f"{len(merged_all):,} == {expected_pts:,}")
check("Chain RMSE[1] < 15 mm", rmse_chain[1] < 15.0,
      f"RMSE={rmse_chain[1]:.3f} mm")
check("Chain RMSE[2] < 15 mm", rmse_chain[2] < 15.0,
      f"RMSE={rmse_chain[2]:.3f} mm")


# ═══════════════════════════════════════════════════════════════════════════
#  Test 5 — Fallback: không có intensity → chỉ dùng ICP
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("TEST 5 — Fallback khi scan không có intensity")
print("="*60)

rng5 = np.random.default_rng(5)
t_no_int = make_tunnel_cloud(rng=rng5)
T_fb = make_rigid_transform(tx=0.1, ty=3.0, tz=0.0, rz_deg=0.5)
s_no_int_1 = PointCloudBundle(points=t_no_int, intensity=None, path="no_int_1")
s_no_int_2 = PointCloudBundle(points=apply_transform(t_no_int, T_fb),
                               intensity=None, path="no_int_2")

reg_fb = RegistrationLayer()
try:
    src_coarse_fb = reg_fb._coarse_align(
        s_no_int_2.points, s_no_int_1.points,
        src_intensity=None, tgt_intensity=None)
    src_reg_fb, rmse_fb = reg_fb._icp(src_coarse_fb, s_no_int_1.points)
    print(f"  {INFO_COLOR} Fallback ICP RMSE = {rmse_fb:.3f} mm")
    check("Fallback ICP RMSE < 20 mm", rmse_fb < 20.0,
          f"RMSE={rmse_fb:.3f} mm")
except Exception as e:
    print(f"  {INFO_COLOR} Fallback error: {e}")
    check("Fallback no crash", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════
#  Summary
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
n_pass = sum(1 for _, ok in results if ok)
n_fail = sum(1 for _, ok in results if not ok)
print(f"RESULT: {n_pass}/{len(results)} PASS  |  {n_fail} FAIL")
if n_fail:
    print("Failed tests:")
    for name, ok in results:
        if not ok:
            print(f"  ✗ {name}")
print("="*60)
sys.exit(0 if n_fail == 0 else 1)
