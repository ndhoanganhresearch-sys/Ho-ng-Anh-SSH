# -*- coding: utf-8 -*-
r"""Tests for RegistrationLayer.register_epochs (T0/Tn epoch alignment).

Field problem: T0 and Tn scanned from DIFFERENT setups -> different coordinate
frames. register_epochs must bring Tn into T0's frame so deformation can be
measured, WITHOUT absorbing the deformation into the rigid transform.

Covers:
  A. ICP fallback (no markers): recovers a known rigid transform.
  B. Target-based: detects fixed markers and aligns via rigid SVD.
  C. Deformation preserved: a known crown settlement survives registration
     (is NOT absorbed away).

Run from tunnel_project:
    ..\.venv\Scripts\python.exe test_register_epochs.py
"""
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
import warnings; warnings.filterwarnings("ignore")

from tunnel_analysis.registration import RegistrationLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle

PASS = FAIL = 0
def ck(name, cond, info=""):
    global PASS, FAIL
    print(("  [PASS] " if cond else "  [FAIL] ") + name + ("  -> " + info if info else ""))
    PASS += (1 if cond else 0); FAIL += (0 if cond else 1)

RNG = np.random.default_rng(7)


def tunnel(R=3.0, L=30.0, n_axial=120, m=140, deform_mm=0.0, sigma_y=4.0):
    """Ring tunnel along Y. Optional crown settlement (Gaussian at center)."""
    ys = np.linspace(0, L, n_axial)
    pts = []
    for y in ys:
        a = np.linspace(0, 2*np.pi, m, endpoint=False) + RNG.uniform(-0.03, 0.03, m)
        x = R*np.cos(a); z = R*np.sin(a)
        if deform_mm != 0.0:
            g = np.exp(-0.5*((y - L/2)/sigma_y)**2)
            crown_w = np.maximum(0.0, np.sin(a))          # top of ring
            z = z + (deform_mm/1000.0) * crown_w * g       # settle crown down (deform_mm<0)
        noise = RNG.normal(0, 0.004, m)
        x = x + noise*np.cos(a); z = z + noise*np.sin(a)
        pts.append(np.column_stack([x, np.full(m, y), z]))
    return np.vstack(pts).astype(np.float64)


def rigid(yaw_deg=6.0, t=(2.0, -1.5, 0.7)):
    """A rigid 4x4 simulating a different scanner setup (yaw + translation)."""
    a = np.deg2rad(yaw_deg)
    R = np.array([[np.cos(a), 0, np.sin(a)],
                  [0, 1, 0],
                  [-np.sin(a), 0, np.cos(a)]], dtype=np.float64)
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = np.asarray(t, dtype=np.float64)
    return T


def apply(T, pts):
    ones = np.ones((len(pts), 1))
    return (T @ np.hstack([pts, ones]).T).T[:, :3]


def sphere_shell(center, radius=0.0725, n=90, noise=0.002):
    """Points on a sphere SURFACE (Faro sphere target) — detectable by detect_sphere."""
    u = RNG.uniform(0, 1, n); v = RNG.uniform(0, 1, n)
    th = 2*np.pi*u; ph = np.arccos(2*v - 1)
    d = np.column_stack([np.sin(ph)*np.cos(th), np.sin(ph)*np.sin(th), np.cos(ph)])
    return center + d*radius + RNG.normal(0, noise, (n, 3))


def add_markers(pts, centers, n_each=90, hi=0.95, lo=0.10):
    """Append sphere-shell reflector targets; return (points, intensity)."""
    base_int = np.full(len(pts), lo)
    extra_pts = []; extra_int = []
    for c in centers:
        sp = sphere_shell(np.asarray(c, dtype=np.float64), n=n_each)
        extra_pts.append(sp); extra_int.append(np.full(len(sp), hi))
    allp = np.vstack([pts] + extra_pts)
    alli = np.concatenate([base_int] + extra_int)
    return allp.astype(np.float64), alli.astype(np.float64)


def crown_delta_max(reg):
    """Quick crown-settlement estimate via the existing pipeline."""
    from tunnel_analysis.geometry import GeometricLayer
    from tunnel_analysis.parameters import ParameterExtractionLayer
    return None  # (full crown check done in test C via ParameterExtractionLayer)


# ══════════════════════════════════════════════════════════════════════════
print("\n=== Test A: ICP fallback recovers a known rigid transform ===")
T0 = tunnel()
Tn_pts = apply(rigid(), T0)            # Tn in a DIFFERENT frame (no deformation)
ctx = PipelineContext()
ctx.scans = [PointCloudBundle(points=T0), PointCloudBundle(points=Tn_pts)]
ctx.active_index = 1
reg = RegistrationLayer()
resA = reg.register_epochs(ctx)
ck("method = icp (no markers)", resA["method"] == "icp", f"method={resA['method']}")
ck("aligned RMSE small (< 30mm)", resA["rmse_mm"] < 30.0, f"rmse={resA['rmse_mm']:.1f}mm")
ck("registered_points stored on context", ctx.registered_points is not None)
ck("point count preserved", len(resA["points"]) == len(Tn_pts))

# ══════════════════════════════════════════════════════════════════════════
print("\n=== Test B: target-based registration via fixed markers ===")
# Markers in FREE SPACE (well inside the R=3.0 wall) so the sphere clusters
# don't blend into the dense lining; sparse tunnel like the ghép-trạm test.
markers = [(0.0, 5.0, 2.0), (1.5, 11.0, -1.0), (-1.5, 17.0, 1.2),
           (0.0, 23.0, -2.0), (1.0, 27.0, 1.5)]
T0b_pts, T0b_int = add_markers(tunnel(n_axial=60, m=80), markers)
Trig = rigid(yaw_deg=5.0, t=(1.5, 0.8, -0.6))
# markers move WITH the cloud (they are physically fixed in the tunnel)
Tnb_pts = apply(Trig, T0b_pts)          # transform the whole marked cloud
Tnb_int = T0b_int                        # intensity travels with points
ctxB = PipelineContext()
sb = PointCloudBundle(points=T0b_pts); sb.intensity = T0b_int
mb = PointCloudBundle(points=Tnb_pts); mb.intensity = Tnb_int
ctxB.scans = [sb, mb]; ctxB.active_index = 1
resB = reg.register_epochs(ctxB, min_targets=3)
print(f"      method={resB['method']}  n_targets={resB['n_targets']}  rmse={resB['rmse_mm']:.1f}mm")
ck("target method used (markers detected & matched >=3)",
   resB["method"] == "target" and resB["n_targets"] >= 3,
   f"method={resB['method']} n={resB['n_targets']}")
ck("aligned RMSE small (< 40mm)", resB["rmse_mm"] < 40.0, f"rmse={resB['rmse_mm']:.1f}mm")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== Test C: LOCALIZED deformation preserved (trimmed ICP) ===")
# Trimmed ICP can isolate a LOCALIZED defect (minority of points). A broad
# deformation that mimics rigid motion needs fixed targets (Test B) instead.
from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
GT_CROWN = -60.0  # mm settlement, localized
T0c = tunnel()
Tnc_def = tunnel(deform_mm=GT_CROWN, sigma_y=1.5)   # LOCALIZED (narrow band)
Tnc_pts = apply(rigid(yaw_deg=4.0, t=(1.0, -0.5, 0.4)), Tnc_def)  # + different frame
ctxC = PipelineContext()
ctxC.scans = [PointCloudBundle(points=T0c), PointCloudBundle(points=Tnc_pts)]
ctxC.active_index = 1
resC = reg.register_epochs(ctxC)            # aligns Tn -> T0 frame (stores registered_points)
ck("registration done (icp)", resC["method"] == "icp")

# Now measure crown settlement on the ALIGNED Tn vs T0 using the real pipeline.
geo, par = GeometricLayer(), ParameterExtractionLayer()
c0 = PipelineContext(); c0.scans = [ctxC.scans[0]]; c0.active_index = 0
cl, fr = geo.extract_centerline_bspline(c0, section_count=60)
ctxC.centerline, ctxC.frenet_frames = cl, fr
crown = par.calc_arch_settlement(ctxC)       # uses working_points = registered_points (aligned Tn)
crown_max = abs(crown.get("crown_settlement_max_mm", 0.0))
ck("settlement still measurable after registration (>=30mm of 60mm GT)",
   crown_max >= 30.0,
   f"crown_max={crown_max:.1f}mm  GT={abs(GT_CROWN)}mm (NOT absorbed to ~0)")

print(f"\n{'='*60}")
print(f"  PASS={PASS}  FAIL={FAIL}  TOTAL={PASS+FAIL}")
print("  " + ("register_epochs OK" if FAIL == 0 else f"{FAIL} FAILED"))
sys.exit(FAIL)
