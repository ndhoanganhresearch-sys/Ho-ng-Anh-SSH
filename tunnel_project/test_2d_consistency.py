# -*- coding: utf-8 -*-
"""Verify the 2D section banner/title agrees with ruler / 3D / dashboard.

Reproduces the reported bug: a section whose absolute |dEcc| crosses the
25 mm threshold but is NOT a local anomaly was shown CRITICAL in 2D while the
ruler/3D markers showed nothing. After the fix, the 2D widget reads the SAME
classify_sections() result as every other view, so they must agree.
"""
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PySide6 import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
from tunnel_analysis.models import SectionGeometry
from tunnel_analysis.ui.widgets import (MatplotlibSectionWidget, classify_sections)

P = F = 0
def ck(n, c, i=""):
    global P, F
    print(("  [PASS] " if c else "  [FAIL] ") + n + ("  " + i if i else ""))
    P += (1 if c else 0); F += (0 if c else 1)

def ring(R=3.0, n=120):
    a = np.linspace(0, 2 * np.pi, n)
    return np.column_stack([R * np.cos(a), R * np.sin(a)])

def mksec(ch, ecc=0.0, radius=3.0):
    sg = SectionGeometry(chainage=ch)
    sg.pts_2d = ring(radius); sg.radius_fit = radius
    sg.W1 = 6.0; sg.H1 = 5.0; sg.ovality = 0.1; sg.eccentricity = ecc
    return sg

# ── Build a tunnel where EVERY section has ~25mm eccentricity vs T0 ─────────
# (uniform systematic offset, NOT a local defect). Old code: all CRITICAL.
# New code (robust local stats): none flagged because none is a local anomaly.
print("=== Uniform 25mm eccentricity offset (systematic, not local) ===")
tn  = [mksec(float(c), ecc=50.0) for c in range(0, 110, 10)]   # Tn ecc ~50
t0  = [mksec(float(c), ecc=25.0) for c in range(0, 110, 10)]   # T0 ecc ~25 -> dEcc ~25 everywhere

w = MatplotlibSectionWidget()
w.set_sections(tn, profile="Circle", vl_box_w=6, vl_box_h=6, vl_cir_r=3)
w.set_ref_sections(t0)

shared = classify_sections(tn, t0)
# The widget's cached statuses must equal the shared classifier output.
ck("widget cached statuses == classify_sections",
   [s for s, _ in w._section_statuses] == [s for s, _ in shared],
   f"widget={[s for s,_ in w._section_statuses][:5]}...")

# For every section, the 2D banner status (_status_for_idx) must equal what
# the ruler/3D/dashboard would draw (classify_sections at that index).
mismatches = 0
for i in range(len(tn)):
    twoD = w._status_for_idx(i)[0]
    other = shared[i][0]
    if twoD != other:
        mismatches += 1
ck("2D status matches shared classifier for ALL sections",
   mismatches == 0, f"{mismatches} mismatches")

# ── Now a TRUE local spike: one section much worse than the rest ────────────
print("=== One local eccentricity spike (true defect) ===")
tn2 = [mksec(float(c), ecc=20.0) for c in range(0, 110, 10)]
tn2[5] = mksec(50.0, ecc=120.0)      # big local spike at idx 5
t02 = [mksec(float(c), ecc=18.0) for c in range(0, 110, 10)]

w2 = MatplotlibSectionWidget()
w2.set_sections(tn2, profile="Circle", vl_box_w=6, vl_box_h=6, vl_cir_r=3)
w2.set_ref_sections(t02)
shared2 = classify_sections(tn2, t02)

ck("local spike flagged in shared classifier",
   shared2[5][0] in ("CRITICAL", "CAUTION"), f"idx5={shared2[5][0]}")
ck("2D banner agrees on the spike section",
   w2._status_for_idx(5)[0] == shared2[5][0],
   f"2D={w2._status_for_idx(5)[0]} shared={shared2[5][0]}")
# And all sections still consistent
mism2 = sum(1 for i in range(len(tn2))
            if w2._status_for_idx(i)[0] != shared2[i][0])
ck("all sections consistent (spike case)", mism2 == 0, f"{mism2} mismatches")

print(f"\n{'='*55}")
print(f"  PASS={P}  FAIL={F}")
if F == 0:
    print("  2D/ruler/3D consistency VERIFIED")
sys.exit(F)
