# -*- coding: utf-8 -*-
r"""Tests for the 2D section tab controls: Info button and Visual-scale spinbox.

Reproduces and guards two reported issues:
  A. Info button raised NameError (ref_sg undefined after an earlier refactor).
  B. "Phóng đại nhìn" (Visual scale) silently did nothing without a T0
     reference -> now the deform controls are disabled (with tooltip) until a
     T0 epoch is loaded, and DO amplify the Tn-vs-T0 deviation when present.

Run from tunnel_project:
    ..\.venv\Scripts\python.exe test_section_controls.py
"""
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PySide6 import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

# Make modal dialogs non-blocking for the headless test.
QtWidgets.QDialog.exec = lambda self: 0

from tunnel_analysis.models import SectionGeometry
from tunnel_analysis.ui.widgets import MatplotlibSectionWidget

PASS = FAIL = 0
def ck(name, cond, info=""):
    global PASS, FAIL
    print(("  [PASS] " if cond else "  [FAIL] ") + name + ("  -> " + info if info else ""))
    PASS += (1 if cond else 0); FAIL += (0 if cond else 1)

def ring(R=3.0, n=200, jitter=0.0):
    a = np.linspace(0, 2*np.pi, n, endpoint=False)
    r = R + (jitter * np.sin(2*a) if jitter else 0.0)
    return np.column_stack([r*np.cos(a), r*np.sin(a)])

def mksec(ch, pts2d, R=3.0, W1=6.0, H1=5.0, oval=0.1, ecc=2.0):
    sg = SectionGeometry(chainage=ch)
    sg.pts_2d = pts2d; sg.radius_fit = R; sg.W1 = W1; sg.H1 = H1
    sg.H2 = 3.0; sg.H3 = 2.0; sg.W2 = 5.8
    sg.wall_angle_L = 89.0; sg.wall_angle_R = 89.0
    sg.ovality = oval; sg.eccentricity = ecc
    sg.min_clearance_dist = 0.4
    return sg

# ══════════════════════════════════════════════════════════════════════════
print("\n=== Test A: Info button — no NameError (single scan) ===")
w = MatplotlibSectionWidget()
secs = [mksec(float(c*5), ring()) for c in range(6)]
w.set_sections(secs, profile="Circle", vl_box_w=6, vl_box_h=6, vl_cir_r=3)
try:
    w._show_info_dialog()      # exec patched -> returns immediately
    ck("Info dialog opens (single scan)", True)
except Exception as e:
    ck("Info dialog opens (single scan)", False, f"{type(e).__name__}: {e}")

print("=== Test A2: Info button — with T0 reference (comparison rows) ===")
ref = [mksec(float(c*5), ring(R=3.02), R=3.02, W1=6.04, H1=5.03) for c in range(6)]
w.set_ref_sections(ref)
try:
    w._show_info_dialog()
    ck("Info dialog opens (T0 vs Tn)", True)
except Exception as e:
    ck("Info dialog opens (T0 vs Tn)", False, f"{type(e).__name__}: {e}")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== Test B: Visual-scale controls enabled only with T0 ===")
w2 = MatplotlibSectionWidget()
w2.set_sections([mksec(float(c*5), ring()) for c in range(6)],
                profile="Circle", vl_box_w=6, vl_box_h=6, vl_cir_r=3)
ck("visual-scale DISABLED without T0", not w2._sp_deform_scale.isEnabled())
ck("animation DISABLED without T0", not w2._btn_anim.isEnabled())
w2.set_ref_sections([mksec(float(c*5), ring(R=3.02), R=3.02) for c in range(6)])
ck("visual-scale ENABLED with T0", w2._sp_deform_scale.isEnabled())
ck("animation ENABLED with T0", w2._btn_anim.isEnabled())

# ══════════════════════════════════════════════════════════════════════════
print("\n=== Test C: Visual scale actually amplifies Tn-vs-T0 deviation ===")
# Tn ring is 50mm LARGER than T0 (uniform outward deviation).
t0_pts = ring(R=3.00)
tn_pts = ring(R=3.05)              # +50mm radial deviation vs T0
ref_sg = mksec(10.0, t0_pts, R=3.00)
w3 = MatplotlibSectionWidget()
w3._sp_deform_scale.setValue(1.0)
base, amp0 = w3._amplify_points_for_display(tn_pts, ref_sg, alpha=1.0)
w3._sp_deform_scale.setValue(10.0)
amp, amp1 = w3._amplify_points_for_display(tn_pts, ref_sg, alpha=1.0)
dev_base = np.hypot(base[:, 0], base[:, 1]).mean() - 3.00   # ~0.05 m
dev_amp  = np.hypot(amp[:, 0],  amp[:, 1]).mean()  - 3.00   # ~0.05*10 = 0.5 m
ck("scale=1 leaves points unchanged", not amp0 and abs(dev_base - 0.05) < 0.005,
   f"dev={dev_base*1000:.0f}mm")
ck("scale=10 amplifies deviation ~10x", amp1 and abs(dev_amp - 0.5) < 0.06,
   f"dev {dev_base*1000:.0f}mm -> {dev_amp*1000:.0f}mm")

print(f"\n{'='*60}")
print(f"  PASS={PASS}  FAIL={FAIL}  TOTAL={PASS+FAIL}")
print("  " + ("Section controls OK" if FAIL == 0 else f"{FAIL} FAILED"))
sys.exit(FAIL)
