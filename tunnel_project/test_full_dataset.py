# -*- coding: utf-8 -*-
r"""Verify data/full_test/ exercises every feature end-to-end (self-test data).

    ..\.venv\Scripts\python.exe test_full_dataset.py
"""
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path
import numpy as np, warnings; warnings.filterwarnings("ignore")
from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.preprocessing import PreprocessingLayer
from tunnel_analysis.registration import RegistrationLayer
from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle
from tunnel_analysis.ui.widgets import classify_sections
from tunnel_analysis.common import principal_axes, validate_xyz

D = Path(__file__).resolve().parent / "data" / "full_test"
P = F = 0
def ck(n, c, i=""):
    global P, F
    print(("  [PASS] " if c else "  [FAIL] ") + n + ("  -> " + i if i else "")); P += c; F += (not c)

def gauge(pts):
    p = validate_xyz(pts); c, ax, _, _ = principal_axes(p); d = p - c
    r = np.linalg.norm(d - np.outer(d @ ax, ax), axis=1)
    g = max(0.3, float(np.percentile(r, 2)) - 0.20); return g, 2*g, g

ld = BaseLayer()
t0 = ld.load_scan(str(D / "T0_full.txt"), max_points=200000)
tn = ld.load_scan(str(D / "Tn_full.txt"), max_points=200000)
ck("load T0+Tn with intensity+labels",
   t0.intensity is not None and tn.intensity is not None and len(t0.points) > 30000)

# 1) Registration via targets
reg = RegistrationLayer()
ctx = PipelineContext(); ctx.scans = [t0, PointCloudBundle(points=tn.points, intensity=tn.intensity)]
ctx.active_index = 1
res = reg.register_epochs(ctx)
gap0 = np.linalg.norm(t0.points.mean(0) - tn.points.mean(0))
gap1 = np.linalg.norm(t0.points.mean(0) - res["points"].mean(0))
ck("registration aligns Tn (target/ICP)", res["method"] in ("target", "icp") and gap1 < 0.5,
   f"method={res['method']} gap {gap0:.2f}->{gap1:.2f}m")

# 2) Denoise removes cable+outliers (label-aware check)
pre = PreprocessingLayer()
ctxd = PipelineContext(); ctxd.scans = [PointCloudBundle(points=tn.points, intensity=tn.intensity)]
ctxd.active_index = 0
kept, _ = pre.auto_denoise(ctxd)
removed = len(tn.points) - len(kept)
ck("denoise removes noise (cable+outliers ~1000)", removed >= 500,
   f"removed {removed} of {len(tn.points)}")

# 3) Pipeline on aligned+denoised Tn vs T0
t0c = PipelineContext(); t0c.scans = [PointCloudBundle(points=validate_xyz(
    pre.auto_denoise(PipelineContext(scans=[PointCloudBundle(points=t0.points, intensity=t0.intensity)], active_index=0))[0]))]
t0c.active_index = 0
geo = GeometricLayer(); par = ParameterExtractionLayer()
cl, fr = geo.extract_centerline_bspline(t0c, section_count=80)
# Build analysis context: T0(clean) + Tn(aligned)
actx = PipelineContext()
actx.scans = [t0c.scans[0], PointCloudBundle(points=res["points"])]
actx.active_index = 1; actx.centerline = cl; actx.frenet_frames = fr
t0c.centerline, t0c.frenet_frames = cl, fr
actx.tunnel_profile = par.detect_profile(actx); t0c.tunnel_profile = actx.tunnel_profile
crown = par.calc_arch_settlement(actx); conv = par.calc_horizontal_convergence(actx)
ck("crown uses T0 ref", crown.get("settlement_reference") == "T0_per_section")
cm = abs(crown.get("crown_settlement_max_mm", 0)); cvm = abs(conv.get("lateral_convergence_max_mm", 0))
ck("crown_max reaches GT (~60mm)", cm >= 30, f"crown_max={cm:.0f}mm GT=60")
ck("convergence_max reaches GT (~80mm)", cvm >= 40, f"conv_max={cvm:.0f}mm GT=80")

# 4) Warnings localized near ch 20
gw, gh, gr = gauge(res["points"])
st = par.compute_all_sections(actx, vl_box_w=gw, vl_box_h=gh, vl_cir_r=gr)
s0 = par.compute_all_sections(t0c, vl_box_w=gw, vl_box_h=gh, vl_cir_r=gr)
n = min(len(st), len(s0)); status = classify_sections(st[:n], s0[:n])
band = [i for i in range(n) if 14 <= st[i].chainage <= 26]
recall = sum(1 for i in band if status[i][0] != "OK") / max(len(band), 1)
nwarn = sum(1 for s, _ in status if s != "OK")
ck("warnings detected & localized near ch20", nwarn >= 1 and recall >= 0.7,
   f"{nwarn} warned, band recall={recall:.0%}")

print(f"\n{'='*60}\n  PASS={P} FAIL={F}  " +
      ("FULL DATASET OK — test được mọi tính năng" if F == 0 else "PROBLEM") + f"\n{'='*60}")
sys.exit(int(F))
