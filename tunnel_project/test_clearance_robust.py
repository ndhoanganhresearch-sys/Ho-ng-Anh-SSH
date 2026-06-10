"""Regression test for robust (percentile-1) clearance flagging.

Locks the root-cause fix: _extract_section_geometry flags a clearance
violation on the 1st-percentile signed distance, so a single stray inner point
(noise / portal ring gap / fixture) no longer condemns a whole section, while a
genuine intrusion affecting >=1% of points still flags.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from tunnel_analysis.parameters import ParameterExtractionLayer

PASS = 0
FAIL = 0

def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}  {extra}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}  {extra}")

def ring(n, r, cx=0.0, cz=0.0):
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([cx + r * np.cos(th), cz + r * np.sin(th)])

par = ParameterExtractionLayer()
GR = 2.5   # circular clearance gauge radius (m); bore ring at 2.75 m

def geom(pts):
    return par._extract_section_geometry(
        np.asarray(pts, dtype=np.float64),
        np.zeros(len(pts), dtype=int), "Circle", 3.0, 4.5, GR)

base = ring(500, 2.75)   # clean bore: every point 0.25 m outside the gauge

# 1) clean ring -> no violation
g0 = geom(base)
check("clean ring -> no violation", not g0["clearance_violation"],
      f"min={g0['min_clearance_dist']:.3f}")

# 2) single stray inner point (1/501 < 1%) -> NOT flagged (robust)
g1 = geom(np.vstack([base, [[1.0, 0.0]]]))
check("single stray inner point -> NOT flagged", not g1["clearance_violation"],
      f"min={g1['min_clearance_dist']:.3f}")

# 3) a few stray inner points (3/503 ~0.6% < 1%) -> still NOT flagged
g3 = geom(np.vstack([base, ring(3, 1.0)]))
check("3 stray points (<1%) -> NOT flagged", not g3["clearance_violation"],
      f"min={g3['min_clearance_dist']:.3f}")

# 4) genuine intrusion (30/530 ~5.7% > 1%) -> flagged CRITICAL
g4 = geom(np.vstack([base, ring(30, 1.0)]))
check("real intrusion (>1%) -> flagged", g4["clearance_violation"],
      f"min={g4['min_clearance_dist']:.3f}")
check("flagged min_clearance_dist is negative", g4["min_clearance_dist"] < 0.0)

print(f"\nPASS={PASS}  FAIL={FAIL}")
if FAIL == 0:
    print("ROBUST CLEARANCE OK")
sys.exit(1 if FAIL else 0)