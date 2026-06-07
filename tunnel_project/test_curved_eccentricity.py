# -*- coding: utf-8 -*-
r"""Regression test for the curved-tunnel eccentricity fix + centerline guard.

Locks in this session's geometry work so a future change cannot silently
regress it:
  1. On a CURVED, perfectly-centred tunnel (single scan, no T0) the
     eccentricity reads SMALL — the detrend (calc_eccentricity fallback) removes
     the centreline-tracking bias that otherwise inflated it to ~450 mm.
  2. extract_centerline_bspline's tangent-refinement GUARD keeps the axis at
     least as good as the bootstrap (never diverges far from the tube centre).

Self-contained (generates its own curved tunnel) — no external dataset needed.

Run from tunnel_project:
    ..\.venv\Scripts\python.exe test_curved_eccentricity.py
"""
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
import warnings; warnings.filterwarnings("ignore")

from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle

P = F = 0
def ck(n, c, i=""):
    global P, F
    print(("  [PASS] " if c else "  [FAIL] ") + n + ("  -> " + i if i else ""))
    P += (1 if c else 0); F += (0 if c else 1)


def curved_tunnel(R=3.0, length=400.0, r_curve=1500.0, n_axial=300, m_ring=90, seed=0):
    """Perfectly CENTRED tunnel on a gentle horizontal arc (rings centred on the
    true curved axis — so any reported eccentricity is a measurement artifact)."""
    rng = np.random.default_rng(seed)
    ss = np.linspace(0, length, n_axial)
    pts = []
    for s in ss:
        th = s / r_curve
        C = np.array([r_curve * (1 - np.cos(th)), r_curve * np.sin(th), 0.0])
        T = np.array([np.sin(th), np.cos(th), 0.0]); T /= np.linalg.norm(T)
        up = np.array([0.0, 0.0, 1.0])
        B = up - (T @ up) * T; B /= np.linalg.norm(B)
        N = np.cross(T, B)
        a = np.linspace(0, 2 * np.pi, m_ring, endpoint=False) + rng.uniform(-0.02, 0.02, m_ring)
        rr = R + rng.normal(0, 0.004, m_ring)
        ring = C + (rr * np.cos(a))[:, None] * N + (rr * np.sin(a))[:, None] * B
        pts.append(ring)
    return np.vstack(pts)


print("\n=== Curved, centred tunnel — eccentricity must NOT be inflated ===")
pts = curved_tunnel()
geo = GeometricLayer(); par = ParameterExtractionLayer()
ctx = PipelineContext(); ctx.scans = [PointCloudBundle(points=pts)]; ctx.active_index = 0
cl, fr = geo.extract_centerline_bspline(ctx, section_count=120)
ctx.centerline, ctx.frenet_frames = cl, fr

ck("tunnel is detected as curved", geo._is_curved(cl))

r = par.calc_eccentricity(ctx)
mean_ecc = r["eccentricity_mean_mm"]
print(f"      eccentricity mean = {mean_ecc:.1f} mm  (raw/undetrended would be ~450mm)")
ck("eccentricity mean stays small (< 80mm, was ~450mm)", mean_ecc < 80.0,
   f"mean={mean_ecc:.1f}mm")

print("\n=== Centerline refine-guard: axis never worse than bootstrap ===")
# Bootstrap (PCA bins + B-spline, no refine) offset vs the final (guarded) axis.
orig = geo._is_curved
geo._is_curved = lambda *a, **k: False           # force no-refine bootstrap
clb, _ = geo.extract_centerline_bspline(ctx, section_count=120)
geo._is_curved = orig
off_boot = geo._axis_offset_metric(pts, clb)
off_final = geo._axis_offset_metric(pts, cl)
print(f"      axis-centre offset: bootstrap={off_boot*1000:.0f}mm  guarded={off_final*1000:.0f}mm")
ck("guarded axis not worse than bootstrap (+5mm tol)",
   off_final <= off_boot + 0.005, f"boot={off_boot*1000:.0f} final={off_final*1000:.0f}")

print(f"\n{'='*60}")
print(f"  PASS={P}  FAIL={F}")
print("  " + ("CURVED ECCENTRICITY REGRESSION OK" if F == 0 else f"{F} FAILED"))
sys.exit(F)
