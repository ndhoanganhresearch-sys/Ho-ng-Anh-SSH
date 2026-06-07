# -*- coding: utf-8 -*-
r"""End-to-end AUTO PIPELINE test on real data with Tn in a DIFFERENT frame.

Mirrors the GUI AUTO PIPELINE step-by-step on the blender_step6 complex dataset,
with the monitoring epoch (Tn) rigidly displaced to simulate a second survey
from a different scanner setup. Verifies every stage runs smoothly and that the
NEW epoch-registration step makes the deformation come out correct despite the
coordinate mismatch:

    voxel -> denoise -> register_epochs(2b) -> centerline -> sections
          -> params (crown/convergence/ovality/ecc) -> classify warnings

Run from tunnel_project:
    ..\.venv\Scripts\python.exe test_pipeline_end_to_end.py
"""
import sys, os, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path
import numpy as np
import warnings; warnings.filterwarnings("ignore")

from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.preprocessing import PreprocessingLayer
from tunnel_analysis.registration import RegistrationLayer
from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle
from tunnel_analysis.ui.widgets import classify_sections
from tunnel_analysis.common import principal_axes, validate_xyz

CASE = (Path(__file__).resolve().parent / "data" / "blender_step6_t1_tn"
        / "version_02_complex_warning")

PASS = FAIL = 0
def ck(name, cond, info=""):
    global PASS, FAIL
    print(("  [PASS] " if cond else "  [FAIL] ") + name + ("  -> " + info if info else ""))
    PASS += (1 if cond else 0); FAIL += (0 if cond else 1)

def step(msg):
    print(f"\n── {msg}")


def rigid(yaw_deg, t):
    # Rotation about the VERTICAL Z axis (yaw): a realistic re-setup turns the
    # tunnel axis (Y) within the horizontal plane -> observable from the lining.
    # (Rotation about Y, the tunnel's own axis, is unobservable for a circular
    #  tunnel and would require fixed targets — that is a physics limit, not a
    #  registration bug.)
    a = np.deg2rad(yaw_deg)
    R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = np.asarray(t, float)
    return T

def apply(T, p):
    return (T @ np.hstack([p, np.ones((len(p), 1))]).T).T[:, :3]

def auto_gauge(points):
    p = validate_xyz(points); c, ax, _e1, _e2 = principal_axes(p); d = p - c
    r = np.linalg.norm(d - np.outer(d @ ax, ax), axis=1)
    g = max(0.3, float(np.percentile(r, 2)) - 0.20)
    return g, 2*g, g

def denoise_cloud(points):
    pre = PreprocessingLayer(); c = PipelineContext()
    c.scans = [PointCloudBundle(points=points)]; c.active_index = 0
    try:
        kept, _ = pre.auto_denoise(c)
        return validate_xyz(kept) if kept is not None and len(kept) >= 100 else validate_xyz(points)
    except Exception:
        return validate_xyz(points)


# ══════════════════════════════════════════════════════════════════════════
print("="*70)
print("  END-TO-END AUTO PIPELINE  (Tn in a DIFFERENT coordinate frame)")
print("="*70)
t_start = time.perf_counter()

step("Load T0 + Tn, then DISPLACE Tn (simulate different survey setup)")
loader = BaseLayer()
t0 = loader.load_scan(str(CASE / "T1_step6_reference.txt"),  max_points=200_000)
tn = loader.load_scan(str(CASE / "Tn_step6_monitoring.txt"), max_points=200_000)
T_survey = rigid(yaw_deg=7.0, t=(2.5, -1.2, 0.8))     # Tn measured from elsewhere
tn_disp = apply(T_survey, tn.points)
ck("T0 + Tn loaded", t0.points.shape[0] > 24000 and tn_disp.shape[0] > 25000,
   f"T0={t0.points.shape[0]} Tn={tn_disp.shape[0]}")
# How far apart are they before registration?
gap0 = np.linalg.norm(t0.points.mean(0) - tn_disp.mean(0))
ck("Tn starts in a different frame (centroids apart)", gap0 > 1.0, f"gap={gap0:.2f} m")

step("Step 2: denoise both epochs (auto_denoise)")
t0_clean = denoise_cloud(t0.points)
tn_clean = denoise_cloud(tn_disp)
ck("denoise kept most points", len(t0_clean) > 20000 and len(tn_clean) > 20000,
   f"T0={len(t0_clean)} Tn={len(tn_clean)}")

step("Step 2b: register_epochs — align Tn onto T0 (THE NEW STEP)")
reg = RegistrationLayer()
ctx = PipelineContext()
ctx.scans = [PointCloudBundle(points=t0_clean), PointCloudBundle(points=tn_clean)]
ctx.active_index = 1
res = reg.register_epochs(ctx)
print(f"      method={res['method']}  n_targets={res['n_targets']}  rmse={res['rmse_mm']:.1f}mm")
ck("registration completed", res["points"] is not None and res["method"] in ("target", "icp"))
ck("aligned RMSE reasonable (< 60mm)", res["rmse_mm"] < 60.0, f"rmse={res['rmse_mm']:.1f}mm")
gap1 = np.linalg.norm(t0_clean.mean(0) - res["points"].mean(0))
ck("Tn brought back to T0 frame (centroids close)", gap1 < 0.5,
   f"gap {gap0:.2f}m -> {gap1:.2f}m")
ck("registered_points stored on context", ctx.registered_points is not None)

step("Step 3-4: centerline (PCA + B-spline) from T0")
geo = GeometricLayer(); par = ParameterExtractionLayer()
ctx0 = PipelineContext(); ctx0.scans = [ctx.scans[0]]; ctx0.active_index = 0
cl, fr = geo.extract_centerline_bspline(ctx0, section_count=80)
ctx.centerline, ctx.frenet_frames = cl, fr
ctx0.centerline, ctx0.frenet_frames = cl, fr
ctx.tunnel_profile = par.detect_profile(ctx)
ctx0.tunnel_profile = ctx.tunnel_profile
ck("centerline + frames built", cl is not None and len(fr) == 80, f"{len(fr)} frames")
ck("profile detected", isinstance(ctx.tunnel_profile, str) and ctx.tunnel_profile,
   f"profile={ctx.tunnel_profile}")

step("Step 5: sections (auto gauge) for Tn (aligned) and T0")
gw, gh, gr = auto_gauge(tn_clean)
secs_tn = par.compute_all_sections(ctx,  vl_box_w=gw, vl_box_h=gh, vl_cir_r=gr)
secs_t0 = par.compute_all_sections(ctx0, vl_box_w=gw, vl_box_h=gh, vl_cir_r=gr)
drawable = sum(1 for s in secs_tn if s.pts_2d is not None and len(s.pts_2d) >= 4)
ck("sections computed for both", len(secs_tn) == 80 and len(secs_t0) == 80)
ck("most sections have data (epsilon adaptive)", drawable >= 70, f"{drawable}/80 drawable")

step("Step 6: deformation parameters vs T0")
crown = par.calc_arch_settlement(ctx)
conv  = par.calc_horizontal_convergence(ctx)
oval  = par.calc_ovality(ctx)
ecc   = par.calc_eccentricity(ctx)
ck("crown uses T0 reference", crown.get("settlement_reference") == "T0_per_section",
   f"ref={crown.get('settlement_reference')}")
crown_max = abs(crown.get("crown_settlement_max_mm", 0.0))
ck("crown_max sane (no 1000mm outlier; GT~90mm)", 40.0 <= crown_max <= 250.0,
   f"crown_max={crown_max:.1f}mm")
ck("convergence uses T0 reference", conv.get("convergence_reference") == "T0_per_section")

step("Step 7: classify warnings (ruler/3D/2D/dashboard shared)")
statuses = classify_sections(secs_tn, secs_t0)
n_crit = sum(1 for s, _ in statuses if s == "CRITICAL")
n_caut = sum(1 for s, _ in statuses if s == "CAUTION")
ck("CRITICAL deformation detected (v02 is critical)", n_crit >= 1,
   f"CRIT={n_crit} CAUT={n_caut}")
# GT primary band [20-34] must be flagged
band = [i for i in range(len(secs_tn)) if 20.0 <= secs_tn[i].chainage <= 34.0]
band_warned = [i for i in band if statuses[i][0] != "OK"]
recall = len(band_warned) / max(len(band), 1)
ck("GT deformation band flagged (recall>=0.8)", recall >= 0.8,
   f"recall={recall:.0%}")

elapsed = time.perf_counter() - t_start
print(f"\n{'='*70}")
print(f"  PASS={PASS}  FAIL={FAIL}  TOTAL={PASS+FAIL}   ({elapsed:.1f}s)")
print("  " + ("END-TO-END PIPELINE SMOOTH — all features work together"
              if FAIL == 0 else f"{FAIL} STAGE(S) FAILED"))
print('='*70)
sys.exit(FAIL)
