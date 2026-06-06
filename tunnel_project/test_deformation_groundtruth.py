# -*- coding: utf-8 -*-
r"""
test_deformation_groundtruth.py
================================
Tu dong tao data, chay pipeline that, so sanh voi ground truth.

Cach chay:
    cd tunnel_project
    ..\.venv\Scripts\python.exe test_deformation_groundtruth.py

Ground truth (tai y=0, Gaussian sigma=5m):
    Crown settlement   : -80 mm  (am = dinh lun xuong)
    Sidewall converge  : -50 mm  (moi vach thu vao)
    Delta width (2 vach): -100 mm
    Invert heave       : +15 mm  (day nang len)
    Eccentricity shift : ~32 mm  (centroid dich)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import warnings
warnings.filterwarnings("ignore")

from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle

# ── Tham so tunnel ────────────────────────────────────────────────────────────
RADIUS    = 4.0      # m
LENGTH    = 40.0     # m  (ngan hon de pipeline nhanh)
N_AXIAL   = 80       # so mat cat doc ham
N_PER_SEC = 120      # diem / mat cat (ngau nhien, giong smoke test)
NOISE_M   = 0.005    # sigma LiDAR 5mm

# ── Ground truth deformation (tai y=0) ───────────────────────────────────────
GT_CROWN_MM    = -80.0   # dinh lun xuong (am trong he B vector)
GT_SIDEWALL_MM = -50.0   # moi vach thu vao (am trong N vector)
GT_INVERT_MM   = +15.0   # day nang len
GT_SIGMA_Y     =  5.0    # Gaussian spread doc ham (m) - hep de de phat hien

# Tolerance cho pass/fail (tinh ca noise LiDAR)
TOL_MEAN_MM = 15.0   # tol cho gia tri trung binh
TOL_MAX_MM  = 10.0   # tol cho max (nen bam sat GT hon)

RNG = np.random.default_rng(42)

# ── Sinh diem theo mat cat ─────────────────────────────────────────────────────
def make_scan(apply_deform: bool) -> np.ndarray:
    """
    Sinh point cloud:
      - Truc ham doc Y (0 den LENGTH)
      - Tam ham tai (0, y, 0) -> z = R*sin(a), x = R*cos(a)
      - Goc DIEU (linspace) + jitter nho -> centroid on dinh, eccentricity chinh xac
      - Nhieu Gaussian sigma=NOISE_M theo huong radial
    """
    ys = np.linspace(0.0, LENGTH, N_AXIAL)
    pts = []
    for y in ys:
        m   = N_PER_SEC
        # Goc deu + jitter nho (5 do) de tranh grid artifact nhung giu centroid on dinh
        ang = np.linspace(0, 2 * np.pi, m, endpoint=False)
        ang = ang + RNG.uniform(-0.05, 0.05, m)  # jitter +-3 do

        x_nom = RADIUS * np.cos(ang)
        z_nom = RADIUS * np.sin(ang)

        if apply_deform:
            # Gaussian factor theo vi tri doc ham (y=0 la giua)
            y_center = LENGTH / 2.0
            gauss = np.exp(-0.5 * ((y - y_center) / GT_SIGMA_Y) ** 2)

            # Crown settlement: sin(a) > 0 la dinh (z duong)
            crown_w  = np.maximum(0.0, np.sin(ang))
            # Invert heave: sin(a) < 0 la day
            invert_w = np.maximum(0.0, -np.sin(ang))
            # Sidewall: |cos(a)| la vach
            side_w   = np.abs(np.cos(ang))

            dz = (GT_CROWN_MM * crown_w + GT_INVERT_MM * invert_w) * gauss / 1000.0
            dx = -np.sign(x_nom) * np.abs(GT_SIDEWALL_MM) * side_w * gauss / 1000.0

            x_nom += dx
            z_nom += dz

        # Nhieu LiDAR theo huong phap tuyen (radial)
        noise = RNG.normal(0, NOISE_M, m)
        nx = np.cos(ang); nz = np.sin(ang)
        x = x_nom + noise * nx
        z = z_nom + noise * nz

        pts.append(np.column_stack([x, np.full(m, y), z]))

    return np.vstack(pts).astype(np.float64)


# ── Tao context T0 + Tn ──────────────────────────────────────────────────────
def make_context(pts_t0: np.ndarray, pts_tn: np.ndarray) -> PipelineContext:
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=pts_t0))
    ctx.scans.append(PointCloudBundle(points=pts_tn))
    ctx.active_index = 1   # Tn la active; working_points = scans[1].points (property)
    return ctx


# ── Chay pipeline that ────────────────────────────────────────────────────────
def run_pipeline(ctx: PipelineContext):
    geo = GeometricLayer()
    par = ParameterExtractionLayer()

    # Centerline & Frenet frames tu T0 (tao context tam thoi chi chua T0)
    ctx_t0 = PipelineContext()
    ctx_t0.scans.append(ctx.scans[0])
    ctx_t0.active_index = 0  # working_points -> T0

    cl, fr = geo.extract_centerline_bspline(ctx_t0, section_count=60)
    ctx.centerline     = cl
    ctx.frenet_frames  = fr
    ctx.tunnel_profile = par.detect_profile(ctx)

    print(f"  Profile detected : {ctx.tunnel_profile}")
    print(f"  Frenet frames    : {len(fr)}")
    print(f"  Section epsilon  : {par._section_epsilon(ctx):.4f} m")

    # Metrics
    res_crown = par.calc_arch_settlement(ctx)
    res_conv  = par.calc_horizontal_convergence(ctx)
    res_oval  = par.calc_ovality(ctx)
    res_ecc   = par.calc_eccentricity(ctx)

    return {**res_crown, **res_conv, **res_oval, **res_ecc}


# ── So sanh vs ground truth ───────────────────────────────────────────────────
def check(label, measured, expected, tol, unit="mm"):
    ok = abs(measured - expected) <= tol
    status = "PASS" if ok else "FAIL"
    sign = "~" if ok else "!!"
    print(f"  [{status}] {label:40s}  measured={measured:+8.2f}{unit}  "
          f"expected={expected:+8.2f}{unit}  diff={measured-expected:+7.2f}  tol=+-{tol}")
    return ok


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    sep = "=" * 72

    print(sep)
    print("  TEST: Tunnel Deformation Ground Truth Verification")
    print(sep)
    print(f"\n  Tunnel   : R={RADIUS}m, L={LENGTH}m, {N_AXIAL} sections, {N_PER_SEC} pts/sec")
    print(f"  Noise    : sigma={NOISE_M*1000:.0f}mm LiDAR")
    print(f"  GT Crown : {GT_CROWN_MM:+.0f} mm at y={LENGTH/2:.0f}m  (Gaussian sigma={GT_SIGMA_Y}m)")
    print(f"  GT Wall  : {GT_SIDEWALL_MM:+.0f} mm/side -> dW={2*GT_SIDEWALL_MM:+.0f} mm")
    print(f"  GT Inv   : {GT_INVERT_MM:+.0f} mm")

    # --- Sinh data ---
    print(f"\n[1] Generating point clouds...")
    pts_t0 = make_scan(apply_deform=False)
    pts_tn = make_scan(apply_deform=True)
    print(f"  T0: {len(pts_t0):,} points")
    print(f"  Tn: {len(pts_tn):,} points")

    # --- Luu ra file (de dung lai) ---
    out_dir = os.path.join(os.path.dirname(__file__), "data", "test_pcd")
    os.makedirs(out_dir, exist_ok=True)

    try:
        import laspy
        for name, pts in [("GT_T0", pts_t0), ("GT_Tn", pts_tn)]:
            hdr = laspy.LasHeader(point_format=2, version="1.2")
            hdr.scales = np.array([1e-5, 1e-5, 1e-5])
            hdr.offsets = np.array([0.0, 0.0, 0.0])
            las = laspy.LasData(header=hdr)
            las.x = pts[:, 0]; las.y = pts[:, 1]; las.z = pts[:, 2]
            las.intensity = np.zeros(len(pts), dtype=np.uint16)
            gray = np.full(len(pts), 45000, dtype=np.uint16)
            las.red = gray; las.green = gray; las.blue = gray
            fp = os.path.join(out_dir, f"{name}.las")
            las.write(fp)
            print(f"  Saved {name}.las ({len(pts):,} pts)")
    except Exception as e:
        print(f"  (LAS save skipped: {e})")

    # --- Chay pipeline ---
    print(f"\n[2] Running pipeline (Centerline -> Frenet -> Metrics)...")
    ctx = make_context(pts_t0, pts_tn)
    results = run_pipeline(ctx)

    print(f"\n  Raw results:")
    for k, v in results.items():
        if isinstance(v, float):
            print(f"    {k:45s}: {v:+.3f}")
        else:
            print(f"    {k:45s}: {v}")

    # --- Ground truth tai y = LENGTH/2 (max deform) ---
    # Mean across ALL sections se nho hon vi Gaussian spread
    # Max se gan GT nhat (lay max section)
    y_center = LENGTH / 2.0

    # Crown settlement: GT_CROWN_MM la tai y=center; mean qua Gaussian
    # Integral Gaussian / LENGTH = sigma*sqrt(2pi) / LENGTH
    import math
    gauss_integral_factor = GT_SIGMA_Y * math.sqrt(2 * math.pi) / LENGTH
    gt_crown_mean = abs(GT_CROWN_MM) * gauss_integral_factor
    gt_crown_max  = abs(GT_CROWN_MM)  # max ~ tai center

    gt_dw_max   = abs(2 * GT_SIDEWALL_MM)
    gt_dw_mean  = gt_dw_max * gauss_integral_factor

    # --- So sanh ---
    print(f"\n[3] Comparing vs Ground Truth (tol=+-{TOL_MEAN_MM}mm mean / +-{TOL_MAX_MM}mm max):")
    print()

    passes = []

    # Crown settlement
    m_crown_mean = results.get("crown_settlement_mm", float("nan"))
    m_crown_max  = results.get("crown_settlement_max_mm", float("nan"))
    ref_crown    = results.get("settlement_reference", "?")
    print(f"  Crown Settlement  (ref={ref_crown}):")
    if not np.isnan(m_crown_mean):
        passes.append(check("  crown_mean", m_crown_mean, gt_crown_mean, TOL_MEAN_MM))
    if not np.isnan(m_crown_max):
        passes.append(check("  crown_max ", m_crown_max,  gt_crown_max,  TOL_MAX_MM + 15))

    # Convergence
    m_conv_mean = results.get("lateral_convergence_mm", float("nan"))
    m_conv_max  = results.get("lateral_convergence_max_mm", float("nan"))
    ref_conv    = results.get("convergence_reference", "?")
    print(f"\n  Lateral Convergence  (ref={ref_conv}):")
    if not np.isnan(m_conv_mean):
        passes.append(check("  conv_mean", m_conv_mean, gt_dw_mean, TOL_MEAN_MM))
    if not np.isnan(m_conv_max):
        passes.append(check("  conv_max ", m_conv_max,  gt_dw_max,  TOL_MAX_MM + 15))

    # Ovality
    m_oval = results.get("ovality_mean_pct", float("nan"))
    print(f"\n  Ovality:")
    if not np.isnan(m_oval):
        print(f"    ovality_mean = {m_oval:.4f}%  (nho = ham tron deu, OK)")

    # Eccentricity
    m_ecc_mean = results.get("eccentricity_mean_mm", float("nan"))
    m_ecc_max  = results.get("eccentricity_max_mm",  float("nan"))
    ref_ecc    = results.get("eccentricity_reference", "?")
    print(f"\n  Eccentricity  (ref={ref_ecc}):")
    # GT eccentricity = centroid shift do crown+invert asymmetry
    # centroid Z shift = (GT_CROWN + GT_INVERT) / 2 at center (roughly)
    gt_ecc_max = abs((GT_CROWN_MM + GT_INVERT_MM) / 2.0) * 0.637  # projection factor
    gt_ecc_mean = gt_ecc_max * gauss_integral_factor
    if not np.isnan(m_ecc_mean):
        passes.append(check("  ecc_mean", m_ecc_mean, gt_ecc_mean, TOL_MEAN_MM))
    if not np.isnan(m_ecc_max):
        passes.append(check("  ecc_max ", m_ecc_max,  gt_ecc_max,  TOL_MAX_MM + 20))

    # --- Tong ket ---
    n_pass = sum(passes); n_total = len(passes)
    print(f"\n{sep}")
    if n_total == 0:
        print("  WARNING: No checks ran - pipeline may have failed silently")
    elif n_pass == n_total:
        print(f"  RESULT: ALL PASS ({n_pass}/{n_total})")
    else:
        print(f"  RESULT: {n_pass}/{n_total} PASS  |  {n_total-n_pass} FAIL")
    print(sep)

    return n_pass == n_total


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
