# -*- coding: utf-8 -*-
r"""Verify T0 reference is detected even when active_index == 0.

Reproduces the reported bug: user loaded T0 but crown/convergence said
"Cần T0" while eccentricity/sections compared fine. Root cause: crown &
convergence required active_index > 0, but the monitoring cloud lived in
normalized_points (after processing) with active_index == 0.

After the fix (_has_t0_reference), all metrics use the same reference logic.
"""
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path
import numpy as np
from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle

CASE = (Path(__file__).resolve().parent / "data" / "blender_step6_t1_tn"
        / "version_02_complex_warning")

P = F = 0
def ck(n, c, i=""):
    global P, F
    print(("  [PASS] " if c else "  [FAIL] ") + n + ("  " + i if i else ""))
    P += (1 if c else 0); F += (0 if c else 1)

loader = BaseLayer()
t0 = loader.load_scan(str(CASE / "T1_step6_reference.txt"),  max_points=200_000)
tn = loader.load_scan(str(CASE / "Tn_step6_monitoring.txt"), max_points=200_000)
geo, par = GeometricLayer(), ParameterExtractionLayer()

def make_ctx(active_index, use_normalized):
    ctx = PipelineContext()
    ctx.scans = [PointCloudBundle(points=t0.points),   # index 0 = T0 reference
                 PointCloudBundle(points=tn.points)]   # index 1 = Tn monitoring
    ctx.active_index = active_index
    if use_normalized:
        # Simulate post-processing: monitoring cloud stored in normalized_points
        ctx.normalized_points = tn.points
    cl, fr = geo.extract_centerline_bspline(ctx, section_count=60)
    ctx.centerline, ctx.frenet_frames = cl, fr
    ctx.tunnel_profile = par.detect_profile(ctx)
    return ctx

# ── Case 1: active_index=1 (epochs path) — baseline, must use T0 ────────────
print("=== Case 1: active_index=1 (normal epochs) ===")
c1 = make_ctx(active_index=1, use_normalized=False)
ck("_has_t0_reference True", par._has_t0_reference(c1))
s1 = par.calc_arch_settlement(c1)
ck("settlement uses T0", s1.get("settlement_reference") == "T0_per_section",
   f"ref={s1.get('settlement_reference')}")

# ── Case 2: active_index=0 + normalized_points (the BUG scenario) ───────────
print("=== Case 2: active_index=0 but processed monitoring cloud ===")
c2 = make_ctx(active_index=0, use_normalized=True)
ck("_has_t0_reference True (was False before fix)", par._has_t0_reference(c2))
s2 = par.calc_arch_settlement(c2)
ck("settlement uses T0 (NOT single_scan)",
   s2.get("settlement_reference") == "T0_per_section",
   f"ref={s2.get('settlement_reference')}")
cv2 = par.calc_horizontal_convergence(c2)
ck("convergence uses T0 (NOT single_scan)",
   cv2.get("convergence_reference") == "T0_per_section",
   f"ref={cv2.get('convergence_reference')}")

# ── Case 3: single scan only — must correctly say single_scan ───────────────
print("=== Case 3: only one scan (genuinely no T0) ===")
c3 = PipelineContext()
c3.scans = [PointCloudBundle(points=tn.points)]
c3.active_index = 0
cl, fr = geo.extract_centerline_bspline(c3, section_count=60)
c3.centerline, c3.frenet_frames = cl, fr
c3.tunnel_profile = par.detect_profile(c3)
ck("_has_t0_reference False (1 scan)", not par._has_t0_reference(c3))
s3 = par.calc_arch_settlement(c3)
ck("settlement = single_scan (correct)",
   str(s3.get("settlement_reference")).startswith("single_scan"),
   f"ref={s3.get('settlement_reference')}")

print(f"\n{'='*55}")
print(f"  PASS={P}  FAIL={F}")
if F == 0:
    print("  T0 reference detection FIXED & consistent")
sys.exit(F)
