# -*- coding: utf-8 -*-
r"""Step 6 evaluation on the REAL blender_step6_t1_tn datasets.

Runs the full Step-6 pipeline (centerline -> sections (Tn & T0) -> crown /
convergence / eccentricity -> classify_sections warning level + location) on
BOTH ground-truth datasets and checks against each manifest's ground_truth:

  version_01_subtle  -> expected CAUTION, crown ~-18mm, warn near ch [24,40]
  version_02_complex -> expected CRITICAL, crown ~-90mm, warn near ch [20,34]

Run from tunnel_project:
    ..\.venv\Scripts\python.exe test_step6_evaluation.py
"""
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.preprocessing import PreprocessingLayer
from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle
from tunnel_analysis.ui.widgets import classify_sections
from tunnel_analysis.common import principal_axes, validate_xyz

DATA = Path(__file__).resolve().parent / "data" / "blender_step6_t1_tn"


def denoise(points):
    """Replicate the pipeline's auto_denoise (removes cables/outliers/clutter)
    so the clearance gauge and section geometry are computed on clean lining."""
    pre = PreprocessingLayer()
    ctx = PipelineContext()
    ctx.scans = [PointCloudBundle(points=points)]
    ctx.active_index = 0
    try:
        kept, _stats = pre.auto_denoise(ctx)
        if kept is not None and len(kept) >= 100:
            return validate_xyz(kept)
    except Exception as e:
        print(f"  (denoise skipped: {e})")
    return validate_xyz(points)


def auto_gauge(points):
    """Replicate MainWindow._compute_auto_gauge: gauge 20cm inside the bore."""
    p = validate_xyz(points)
    c, axis, _e1, _e2 = principal_axes(p)
    d = p - c
    r = np.linalg.norm(d - np.outer(d @ axis, axis), axis=1)
    r_inner = float(np.percentile(r, 2))
    gauge = max(0.3, r_inner - 0.20)
    return gauge, 2.0 * gauge, gauge   # (w, h, r)

def in_any_band(chainage, bands):
    return any(lo <= chainage <= hi for lo, hi in bands)

PASS = FAIL = 0
def ck(name, cond, info=""):
    global PASS, FAIL
    print(("  [PASS] " if cond else "  [FAIL] ") + name + ("  -> " + info if info else ""))
    PASS += (1 if cond else 0); FAIL += (0 if cond else 1)


def run_version(folder, expected_level, gt_crown_mm, warn_band, secondary_band=None):
    print(f"\n{'='*70}\n  {folder}\n{'='*70}")
    case = DATA / folder
    manifest = json.loads((case / "manifest.json").read_text(encoding="utf-8"))
    gt = manifest["ground_truth"]

    loader = BaseLayer()
    files = manifest["files"]
    t0_raw = loader.load_scan(str(case / files[0]["name"]), max_points=200_000)
    tn_raw = loader.load_scan(str(case / files[1]["name"]), max_points=200_000)
    print(f"  raw: T0={t0_raw.points.shape[0]} pts  Tn={tn_raw.points.shape[0]} pts")

    # Pipeline order: denoise BOTH epochs before centerline/sections so clutter
    # (cables/outliers) does not corrupt the gauge or per-section geometry.
    t0 = PointCloudBundle(points=denoise(t0_raw.points))
    tn = PointCloudBundle(points=denoise(tn_raw.points))
    print(f"  clean: T0={t0.points.shape[0]} pts  Tn={tn.points.shape[0]} pts")

    geo, par = GeometricLayer(), ParameterExtractionLayer()

    # Context: scans[0]=T0, scans[1]=Tn, active=Tn
    ctx = PipelineContext()
    ctx.scans = [t0, tn]
    ctx.active_index = 1
    # Centerline/frames from T0
    ctx0 = PipelineContext(); ctx0.scans = [ctx.scans[0]]; ctx0.active_index = 0
    cl, fr = geo.extract_centerline_bspline(ctx0, section_count=80)
    ctx.centerline, ctx.frenet_frames = cl, fr
    ctx.tunnel_profile = par.detect_profile(ctx)
    # Give ctx0 the SAME centerline/frames so T0 sections align with Tn
    # (mirrors the app's 5.7 dispatch which builds ref from the same frames).
    ctx0.centerline, ctx0.frenet_frames = cl, fr
    ctx0.tunnel_profile = ctx.tunnel_profile

    # ── T0 reference detected? ──────────────────────────────────────────────
    ck("T0 reference detected", par._has_t0_reference(ctx))

    # ── Crown / convergence vs T0 ───────────────────────────────────────────
    crown = par.calc_arch_settlement(ctx)
    conv  = par.calc_horizontal_convergence(ctx)
    ck("crown uses T0 (not single_scan)",
       crown.get("settlement_reference") == "T0_per_section",
       f"ref={crown.get('settlement_reference')}")
    crown_max = crown.get("crown_settlement_max_mm", float("nan"))
    # Max crown settlement should reach roughly the GT magnitude (localized).
    ck(f"crown_max reaches GT magnitude (~{abs(gt_crown_mm)}mm)",
       abs(crown_max) >= abs(gt_crown_mm) * 0.5,
       f"crown_max={crown_max:.1f}mm  GT={gt_crown_mm}mm")

    # ── Sections for Tn and T0, then classify ───────────────────────────────
    # Use the auto clearance gauge (20 cm inside bore) like the app, otherwise
    # a fixed gauge equal to the bore radius flags every section as a violation.
    gw, gh, gr = auto_gauge(tn.points)
    print(f"  auto-gauge: r={gr:.2f}m (20cm inside bore)")
    secs_tn = par.compute_all_sections(ctx,  vl_box_w=gw, vl_box_h=gh, vl_cir_r=gr)
    secs_t0 = par.compute_all_sections(ctx0, vl_box_w=gw, vl_box_h=gh, vl_cir_r=gr)
    n = min(len(secs_tn), len(secs_t0))
    statuses = classify_sections(secs_tn[:n], secs_t0[:n])
    levels = [s for s, _ in statuses]
    n_crit = levels.count("CRITICAL"); n_caut = levels.count("CAUTION")
    print(f"  Sections: {n}  CRITICAL={n_crit}  CAUTION={n_caut}  OK={levels.count('OK')}")

    # ── Warning level matches manifest ──────────────────────────────────────
    if expected_level == "CRITICAL":
        ck("detects CRITICAL warning(s)", n_crit >= 1, f"{n_crit} critical")
    else:  # CAUTION
        ck("detects warning(s) (CAUTION or CRITICAL)",
           (n_crit + n_caut) >= 1, f"crit={n_crit} caut={n_caut}")

    # ── GT deformation band must be flagged (recall, not precision) ─────────
    # A severe deformation legitimately spans beyond its primary band (v02 also
    # has a secondary band and wide transition zones), so we check that the
    # known-deformed region IS flagged — i.e. recall over the GT band — rather
    # than demanding all warnings fall inside it.
    lo, hi = warn_band
    band_idx = [i for i in range(n) if lo <= secs_tn[i].chainage <= hi]
    band_warned = [i for i in band_idx if statuses[i][0] != "OK"]
    recall = (len(band_warned) / len(band_idx)) if band_idx else 0.0
    ck(f"GT band {warn_band} m is flagged (recall>=0.8)",
       recall >= 0.8,
       f"recall={recall:.0%} ({len(band_warned)}/{len(band_idx)} band sections warned)")

    # Track warning precision as a guard against overly broad warning spread.
    # The complex dataset has a secondary deformation band, so count both known
    # GT bands as true-positive warning locations.
    gt_bands = [warn_band]
    if secondary_band is not None:
        gt_bands.append(secondary_band)
    warned_idx = [i for i, (s, _) in enumerate(statuses) if s != "OK"]
    true_warning_idx = [i for i in warned_idx if in_any_band(secs_tn[i].chainage, gt_bands)]
    false_warning_idx = [i for i in warned_idx if i not in true_warning_idx]
    precision = (len(true_warning_idx) / len(warned_idx)) if warned_idx else 1.0
    if false_warning_idx:
        false_ch = [secs_tn[i].chainage for i in false_warning_idx]
        false_span = f" false_span={min(false_ch):.1f}-{max(false_ch):.1f}m"
    else:
        false_span = " false_span=none"
    ck("warning precision stays informative (>=0.5)",
       precision >= 0.5,
       f"precision={precision:.0%} ({len(true_warning_idx)}/{len(warned_idx)} warnings in GT bands); false={len(false_warning_idx)};{false_span}")

    # ── Clearance intrusion (v02 only) ──────────────────────────────────────
    if gt.get("clearance_intrusion"):
        n_clr = sum(1 for s in secs_tn if s.clearance_violation)
        print(f"  clearance violations: {n_clr} sections (GT: intrusion present)")


def main():
    run_version("version_01_subtle_deformation",
                expected_level="CAUTION", gt_crown_mm=-18.0, warn_band=(24.0, 40.0))
    run_version("version_02_complex_warning",
                expected_level="CRITICAL", gt_crown_mm=-90.0, warn_band=(20.0, 34.0),
                secondary_band=(41.0, 50.0))

    print(f"\n{'='*70}")
    print(f"  STEP 6 EVALUATION:  PASS={PASS}  FAIL={FAIL}  TOTAL={PASS+FAIL}")
    print("  " + ("ALL PASS - Step 6 evaluated correctly on real data"
                  if FAIL == 0 else f"{FAIL} CHECK(S) FAILED"))
    print('='*70)
    return FAIL


if __name__ == "__main__":
    sys.exit(main())
