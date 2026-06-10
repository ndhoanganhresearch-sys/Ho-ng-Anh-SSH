"""Regression test for the clearance portal guard in classify_sections.

Locks the fix for the dashboard "OK banner vs CRITICAL sections" report:
incomplete rings at the two tunnel mouths over-report clearance intrusion, so
the outermost sections of a long tunnel are no longer flagged for clearance,
while mid-tunnel violations and short section runs stay flagged.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tunnel_analysis.models import SectionGeometry
from tunnel_analysis.ui.widgets import classify_sections

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

def mksec(ch, clr=False):
    return SectionGeometry(chainage=float(ch), ovality=0.05, eccentricity=1.0,
                           clearance_violation=clr, min_clearance_dist=-0.5 if clr else 0.3)

# ---- Long tunnel (n=80): portal_n = round(80*0.04) = 3 ----
n = 80
def long_with_violation_at(idx):
    secs = [mksec(c * 10.0) for c in range(n)]
    secs[idx] = mksec(idx * 10.0, clr=True)
    return classify_sections(secs)

st_portal_lo = long_with_violation_at(1)   # index 1 < 3 -> portal, skipped
st_portal_hi = long_with_violation_at(78)  # index 78 >= 80-3=77 -> portal, skipped
st_mid       = long_with_violation_at(40)  # mid-tunnel -> flagged

check("n=80 portal-start clearance NOT flagged", st_portal_lo[1][0] == "OK",
      f"got={st_portal_lo[1][0]}")
check("n=80 portal-end clearance NOT flagged", st_portal_hi[78][0] == "OK",
      f"got={st_portal_hi[78][0]}")
check("n=80 mid-tunnel clearance flagged CRITICAL", st_mid[40][0] == "CRITICAL",
      f"got={st_mid[40][0]}")
# section just inside the guard (index 3) is still flagged
st_edge = long_with_violation_at(3)
check("n=80 first non-portal (idx=3) still flagged", st_edge[3][0] == "CRITICAL",
      f"got={st_edge[3][0]}")

# ---- Short run (n=6 < 20): no guard, ends still flagged ----
short = [mksec(c * 10.0) for c in range(6)]
short[0] = mksec(0.0, clr=True)
st_short = classify_sections(short)
check("n=6 end clearance still flagged (no guard)", st_short[0][0] == "CRITICAL",
      f"got={st_short[0][0]}")
# matches existing consistency test: index 2 flagged
short2 = [mksec(c * 10.0) for c in range(6)]
short2[2] = mksec(20.0, clr=True)
check("n=6 index 2 clearance flagged", classify_sections(short2)[2][0] == "CRITICAL")

print(f"\nPASS={PASS}  FAIL={FAIL}")
if FAIL == 0:
    print("CLEARANCE PORTAL GUARD OK")
sys.exit(1 if FAIL else 0)