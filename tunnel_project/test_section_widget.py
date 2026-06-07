# -*- coding: utf-8 -*-
"""Verify MatplotlibSectionWidget lands on the first drawable (non-sparse) section."""
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PySide6 import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
from tunnel_analysis.models import SectionGeometry
from tunnel_analysis.ui.widgets import MatplotlibSectionWidget

P = F = 0
def ck(n, c, i=""):
    global P, F
    print(("  [PASS] " if c else "  [FAIL] ") + n + ("  " + i if i else ""))
    P += (1 if c else 0); F += (0 if c else 1)

def ring(R=3.0, n=120):
    a = np.linspace(0, 2 * np.pi, n)
    return np.column_stack([R * np.cos(a), R * np.sin(a)])

# sections 0,1 empty (occlusion); 2 has points; 3 empty; 4 has points; 5 empty
secs = []
for i in range(6):
    sg = SectionGeometry(chainage=float(i * 5))
    if i in (2, 4):
        sg.pts_2d = ring(); sg.radius_fit = 3.0; sg.W1 = 6.0; sg.H1 = 5.0
        sg.ovality = 0.1; sg.eccentricity = 2.0
    else:
        sg.pts_2d = None   # sparse/occluded slice
    secs.append(sg)

print("=== set_sections jumps to first drawable ===")
w = MatplotlibSectionWidget()
w.set_sections(secs, profile="Circle", vl_box_w=6, vl_box_h=6, vl_cir_r=3)
ck("idx lands on first drawable (2)", w._idx == 2, f"idx={w._idx}")
ck("_first_drawable_index static finds 2",
   MatplotlibSectionWidget._first_drawable_index(secs) == 2)

print("=== all-empty falls back to 0 ===")
empty = [SectionGeometry(chainage=float(i)) for i in range(3)]
ck("all-empty -> idx 0", MatplotlibSectionWidget._first_drawable_index(empty) == 0)

print("=== no sections -> idx 0 ===")
ck("none -> 0", MatplotlibSectionWidget._first_drawable_index([]) == 0)

print(f"\nPASS={P} FAIL={F}")
sys.exit(F)
