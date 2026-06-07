# -*- coding: utf-8 -*-
r"""End-to-end pipeline run on real Blender data — validates recent fixes.

Runs the ACTUAL analysis pipeline (load -> centerline -> sections -> params)
on data/blender_step6_t1_tn/version_02_complex_warning and verifies:

  1. T0 comparison path: with 2 scans loaded, crown settlement uses
     'T0_per_section' (NOT 'single_scan_*') so the dashboard shows a real
     number instead of "Cần T0".
  2. Single-scan path: with only Tn loaded, settlement_reference is
     'single_scan_*' -> dashboard would correctly show "Cần T0".
  3. classify_sections() flags CRITICAL/CAUTION sections on the deformed
     monitoring scan (the ruler / 2D track / 3D markers / dashboard all share
     this classifier).

Run from tunnel_project:
    ..\.venv\Scripts\python.exe test_pipeline_run.py
"""
from __future__ import annotations

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
from tunnel_analysis.ui.widgets import classify_sections

ROOT = Path(__file__).resolve().parent
CASE = ROOT / "data" / "blender_step6_t1_tn" / "version_02_complex_warning"

PASS = FAIL = 0
def ck(name, cond, info=""):
    global PASS, FAIL
    sym = "[PASS]" if cond else "[FAIL]"
    if cond: PASS += 1
    else: FAIL += 1
    print(f"  {sym} {name}" + (f"  -> {info}" if info else ""))


def build_sections(points, ref_points=None, n_sections=60):
    """Run centerline + sections on `points`. Optionally add ref scan first."""
    geo, par = GeometricLayer(), ParameterExtractionLayer()
    ctx = PipelineContext()
    if ref_points is not None:
        ctx.scans.append(PointCloudBundle(points=ref_points))   # index 0 = T0/T1
        ctx.scans.append(PointCloudBundle(points=points))       # index 1 = Tn
        ctx.active_index = 1
    else:
        ctx.scans.append(PointCloudBundle(points=points))       # index 0 = single
        ctx.active_index = 0
    cl, fr = geo.extract_centerline_bspline(ctx, section_count=n_sections)
    ctx.centerline, ctx.frenet_frames = cl, fr
    ctx.tunnel_profile = par.detect_profile(ctx)
    secs = par.compute_all_sections(ctx, vl_box_w=6.0, vl_box_h=6.0, vl_cir_r=3.2)
    return ctx, par, secs


# ══════════════════════════════════════════════════════════════════════════
print("\n=== Loading real Blender data (version_02_complex_warning) ===")
loader = BaseLayer()
t1 = loader.load_scan(str(CASE / "T1_step6_reference.txt"),  max_points=200_000)
tn = loader.load_scan(str(CASE / "Tn_step6_monitoring.txt"), max_points=200_000)
ck("T1 reference loaded", t1.points.shape[0] > 24_000, f"{t1.points.shape[0]} pts")
ck("Tn monitoring loaded", tn.points.shape[0] > 25_000, f"{tn.points.shape[0]} pts")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== Case A: SINGLE SCAN (no T0) — should flag 'Cần T0' ===")
ctxA, parA, secsA = build_sections(tn.points, ref_points=None)
ck("sections built (single)", len(secsA) > 0, f"{len(secsA)} sections")
settA = parA.calc_arch_settlement(ctxA)
ref_kind = settA.get("settlement_reference", "")
ck("settlement_reference = single_scan*",
   ref_kind.startswith("single_scan"), f"ref={ref_kind}")
print(f"      -> dashboard card would show: '— Cần T0'  (crown raw="
      f"{settA.get('crown_settlement_mm', float('nan')):.1f} mm, KHÔNG hiển thị)")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== Case B: T0 COMPARISON (T1 + Tn) — should give real number ===")
ctxB, parB, secsB = build_sections(tn.points, ref_points=t1.points)
ck("sections built (Tn)", len(secsB) > 0, f"{len(secsB)} sections")
settB = parB.calc_arch_settlement(ctxB)
ref_kindB = settB.get("settlement_reference", "")
ck("settlement_reference = T0_per_section",
   ref_kindB == "T0_per_section", f"ref={ref_kindB}")
crown_mm = settB.get("crown_settlement_mm", float("nan"))
crown_max = settB.get("crown_settlement_max_mm", float("nan"))
ck("crown settlement is realistic (< 500 mm, not absolute coord)",
   abs(crown_mm) < 500.0, f"mean={crown_mm:.1f} mm  max={crown_max:.1f} mm")
print(f"      -> ground truth says crown ~ -90 mm; measured mean={crown_mm:.1f} "
      f"max={crown_max:.1f} mm")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== Case C: classify_sections() finds warnings on deformed scan ===")
# Build reference sections (T1) to compare against Tn sections.
ctxRef, parRef, secsRef = build_sections(t1.points, ref_points=None)
# Align by chainage count: classify_sections matches by index.
n = min(len(secsB), len(secsRef))
statuses = classify_sections(secsB[:n], secsRef[:n])
n_crit = sum(1 for s, _ in statuses if s == "CRITICAL")
n_caut = sum(1 for s, _ in statuses if s == "CAUTION")
n_ok   = sum(1 for s, _ in statuses if s == "OK")
ck("classify_sections returns per-section", len(statuses) == n, f"{len(statuses)} statuses")
ck("at least one warning detected (CRITICAL or CAUTION)",
   (n_crit + n_caut) >= 1, f"CRIT={n_crit} CAUT={n_caut} OK={n_ok}")
print(f"      -> ruler/2D/3D/dashboard would show: "
      f"{n_crit} đỏ (CRITICAL), {n_caut} vàng (CAUTION), {n_ok} OK")

# Show where the warnings are (chainage)
warned = [(secsB[i].chainage, s) for i, (s, _) in enumerate(statuses) if s != "OK"]
if warned:
    sample = warned[:6]
    print("      Vị trí cảnh báo (ch, mức): " +
          ", ".join(f"{c:.1f}m[{s[:4]}]" for c, s in sample) +
          (" ..." if len(warned) > 6 else ""))

# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"  PASS={PASS}  FAIL={FAIL}  TOTAL={PASS+FAIL}")
if FAIL == 0:
    print("  PIPELINE RUN PASSED — các fix hoạt động trên dữ liệu thật")
else:
    print("  PIPELINE RUN có lỗi")
sys.exit(FAIL)
