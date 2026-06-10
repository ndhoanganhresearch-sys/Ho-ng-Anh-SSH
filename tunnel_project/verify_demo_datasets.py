# -*- coding: utf-8 -*-
r"""Verify data/demo_circle and data/demo_box exercise the pipeline correctly.

    ..\.venv\Scripts\python.exe verify_demo_datasets.py
"""
import os
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path
import warnings
import numpy as np
warnings.filterwarnings("ignore")

from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.preprocessing import PreprocessingLayer
from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle
from tunnel_analysis.ui.widgets import classify_sections
from tunnel_analysis.common import principal_axes, validate_xyz

D = Path(__file__).resolve().parent / "data"
P = F = 0


def ck(n, c, i=""):
    global P, F
    print(("  [PASS] " if c else "  [FAIL] ") + n + ("  -> " + i if i else ""))
    P += int(bool(c)); F += int(not c)


def circ_gauge(pts):
    p = validate_xyz(pts); c, ax, _, _ = principal_axes(p); d = p - c
    r = np.linalg.norm(d - np.outer(d @ ax, ax), axis=1)
    g = max(0.3, float(np.percentile(r, 2)) - 0.20)
    return g, 2 * g, g


def _lining(path):
    """Load only the lining (classification==1) so T0/Tn share an identical
    base sampling — isolates the injected defects from denoise asymmetry. The
    auto-denoise algorithm itself is tested separately (test_full_dataset)."""
    import laspy
    las = laspy.read(str(path))
    pts = np.vstack([las.x, las.y, las.z]).T
    cls = np.asarray(las.classification)
    return validate_xyz(pts[cls == 1])


def run_pipeline(t0_path, tn_path, section_count, box=False):
    t0p = _lining(t0_path); tnp = _lining(tn_path)
    geo, par = GeometricLayer(), ParameterExtractionLayer()
    t0c = PipelineContext(); t0c.scans = [PointCloudBundle(points=t0p)]; t0c.active_index = 0
    cl, fr = geo.extract_centerline_bspline(t0c, section_count=section_count)
    t0c.centerline, t0c.frenet_frames = cl, fr
    actx = PipelineContext(); actx.scans = [PointCloudBundle(points=t0p), PointCloudBundle(points=tnp)]
    actx.active_index = 1; actx.centerline, actx.frenet_frames = cl, fr
    prof = par.detect_profile(actx)
    actx.tunnel_profile = t0c.tunnel_profile = prof
    crown = par.calc_arch_settlement(actx)
    conv = par.calc_horizontal_convergence(actx)
    if box:
        gw, gh, gr = 3.5, 5.0, 3.5
    else:
        gw, gh, gr = circ_gauge(t0p)   # design envelope from the clean reference
    st = par.compute_all_sections(actx, vl_box_w=gw, vl_box_h=gh, vl_cir_r=gr)
    s0 = par.compute_all_sections(t0c, vl_box_w=gw, vl_box_h=gh, vl_cir_r=gr)
    n = min(len(st), len(s0))
    status = classify_sections(st[:n], s0[:n])
    return dict(prof=prof, crown=crown, conv=conv, st=st[:n], s0=s0[:n],
                status=status, t0n=len(t0p), tnn=len(tnp))


def _y(sec):
    return float(sec.center_3d[1]) if sec.center_3d is not None else float("nan")


def warned_near_y(st, status, y, tol=3.0):
    """Sections whose physical axis position (center Y) is near y AND warned.
    Uses physical location, not the chainage label, because the centerline's
    chainage direction is PCA-arbitrary (may run high->low Y)."""
    return [i for i in range(len(st))
            if abs(_y(st[i]) - y) <= tol and status[i][0] != "OK"]


def warning_clusters(status, gap=2):
    """Count contiguous runs of warned sections = distinct defect ZONES (so a
    few wide gaussian defects read as a few clusters, not many scattered hits)."""
    warned = [i for i, (s, _) in enumerate(status) if s != "OK"]
    if not warned:
        return 0
    clusters = 1
    for a, b in zip(warned, warned[1:]):
        if b - a > gap:
            clusters += 1
    return clusters


print("=" * 64)
print("DEMO CIRCLE (data/demo_circle)")
print("=" * 64)
r = run_pipeline(D / "demo_circle/T0_circle.las", D / "demo_circle/Tn_circle.las", 100)
ck("loads + denoise (lining kept)", r["t0n"] > 15000 and r["tnn"] > 15000, f"t0={r['t0n']} tn={r['tnn']}")
ck("profile detected = Circle", str(r["prof"]).lower().startswith("circle"), f"prof={r['prof']}")
ck("crown settlement vs T0", r["crown"].get("settlement_reference") == "T0_per_section",
   f"ref={r['crown'].get('settlement_reference')}")
cm = abs(r["crown"].get("crown_settlement_max_mm", 0))
cv = abs(r["conv"].get("lateral_convergence_max_mm", 0))
ck("crown_max reaches GT (~28mm)", cm >= 18, f"crown_max={cm:.0f}mm GT=28")
ck("convergence_max reaches GT (~44mm both walls)", cv >= 18, f"conv_max={cv:.0f}mm GT~44")
w_settle = warned_near_y(r["st"], r["status"], 18.0)
w_conv = warned_near_y(r["st"], r["status"], 38.0)
ck("warning near settlement (Y~18m)", len(w_settle) >= 1, f"Y={ [round(_y(r['st'][i]),1) for i in w_settle] }")
ck("warning near convergence (Y~38m)", len(w_conv) >= 1, f"Y={ [round(_y(r['st'][i]),1) for i in w_conv] }")
clr = [i for i in range(len(r["st"])) if r["st"][i].clearance_violation]
clr_y = [round(_y(r["st"][i]), 1) for i in clr]
ck("clearance intrusion detected near Y~50m", any(46 <= _y(r["st"][i]) <= 54 for i in clr),
   f"clearance Y={clr_y}")
nwarn = sum(1 for s, _ in r["status"] if s != "OK")
nclus = warning_clusters(r["status"])
ck("defects are FEW, clustered zones (not scattered)", 1 <= nclus <= 5,
   f"{nclus} warning zones, {nwarn}/{len(r['st'])} sections")

print("\n" + "=" * 64)
print("DEMO BOX (data/demo_box)")
print("=" * 64)
rb = run_pipeline(D / "demo_box/T0_box.las", D / "demo_box/Tn_box.las", 80, box=True)
ck("loads box", rb["t0n"] > 15000, f"t0={rb['t0n']}")
ck("profile detected = Box", "box" in str(rb["prof"]).lower(), f"prof={rb['prof']}")
ck("box pipeline runs (sections built)", len(rb["st"]) >= 40, f"sections={len(rb['st'])}")
w_bconv = warned_near_y(rb["st"], rb["status"], 25.0)
ck("box convergence warning near Y~25m", len(w_bconv) >= 1,
   f"Y={ [round(_y(rb['st'][i]),1) for i in w_bconv] }")

print(f"\n{'='*64}\n  PASS={P}  FAIL={F}  " +
      ("DEMO DATASETS OK" if F == 0 else "PROBLEM — needs fixing") + f"\n{'='*64}")
sys.exit(int(F))
