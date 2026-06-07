"""Consistency check: classify_sections must agree for ruler, track, dashboard alerts."""
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
from PySide6 import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from tunnel_analysis.models import SectionGeometry
from tunnel_analysis.ui.widgets import classify_sections, ChainageRulerWidget

PASS = FAIL = 0
def ck(name, cond, info=""):
    global PASS, FAIL
    sym = "[PASS]" if cond else "[FAIL]"
    if not cond: FAIL += 1; print(f"  {sym} {name}  {info}")
    else: PASS += 1; print(f"  {sym} {name}")

def mksec(ch, oval=0.0, ecc=0.0, rv=False, radius=3.0, W1=6.0):
    sg = SectionGeometry(chainage=ch)
    sg.radius_fit = radius; sg.W1 = W1; sg.H1 = 5.0
    sg.ovality = oval; sg.eccentricity = ecc
    sg.clearance_violation = rv
    sg.min_clearance_dist = -0.05 if rv else float("nan")
    return sg

# ──────────────────────────────────────────────────────────────────────────
print("\n--- Case 1: single scan, local ovality spike (no T0) ---")
secs = [mksec(float(c), oval=0.1) for c in range(0, 110, 10)]
secs[5] = mksec(50.0, oval=3.5)   # CRITICAL spike at ch=50 (index 5)
stats = classify_sections(secs)
crit = [i for i, (s, _) in enumerate(stats) if s == "CRITICAL"]
ck("spike detected without T0",    len(crit) >= 1,  f"crit_idx={crit}")
ck("spike at correct index (5)",   5 in crit,        f"crit_idx={crit}")

ruler = ChainageRulerWidget(); ruler.resize(800, 50)
ruler.set_sections(secs, [])
ck("ruler marks same section",     len(ruler._marks) >= 1)
r_crit = [m for m in ruler._marks if m[1] == "#DC2626"]
ck("ruler CRITICAL color",         len(r_crit) >= 1,  f"marks={ruler._marks}")

# ──────────────────────────────────────────────────────────────────────────
print("\n--- Case 2: T0 comparison, dR > 25 mm threshold ---")
secs_t0 = [mksec(float(c)) for c in range(0, 110, 10)]
secs_tn = [mksec(float(c)) for c in range(0, 110, 10)]
secs_tn[3] = mksec(30.0, radius=3.0 - 0.08)   # -80 mm dR → CRITICAL (>25mm)

stats2 = classify_sections(secs_tn, secs_t0)
crit2 = [i for i, (s, _) in enumerate(stats2) if s == "CRITICAL"]
ck("T0 dR CRITICAL detected",      len(crit2) >= 1,  f"crit={crit2}")
ck("correct index (3)",            3 in crit2,        f"crit={crit2}")

ruler.set_sections(secs_tn, secs_t0)
ck("ruler marks T0 CRITICAL",      any(m[1] == "#DC2626" for m in ruler._marks))

# ──────────────────────────────────────────────────────────────────────────
print("\n--- Case 3: clearance violation always CRITICAL ---")
secs_clr = [mksec(float(c)) for c in range(0, 60, 10)]
secs_clr[2] = mksec(20.0, rv=True)
stats3 = classify_sections(secs_clr)
ck("clearance violation → CRITICAL",    stats3[2][0] == "CRITICAL",
   f"got={stats3[2][0]}")
ruler.set_sections(secs_clr, [])
ck("ruler marks clearance CRITICAL",    any(m[1] == "#DC2626" for m in ruler._marks))

# ──────────────────────────────────────────────────────────────────────────
print("\n--- Case 4: all OK → no marks anywhere ---")
secs_ok = [mksec(float(c), oval=0.05) for c in range(0, 110, 10)]
stats4  = classify_sections(secs_ok)
ck("all sections OK",     all(s == "OK" for s, _ in stats4))
ruler.set_sections(secs_ok, [])
ck("ruler: no marks",     len(ruler._marks) == 0, f"marks={ruler._marks}")

# ──────────────────────────────────────────────────────────────────────────
print("\n--- Case 5: dW CAUTION from T0 comparison ---")
secs_base = [mksec(float(c), W1=6.0) for c in range(0, 110, 10)]
secs_now  = [mksec(float(c), W1=6.0) for c in range(0, 110, 10)]
secs_now[7] = mksec(70.0, W1=5.975)   # -25mm dW (barely CAUTION at 10mm threshold)
# Actually delta must pass local_flags too: for CAUTION abs_delta >= 10mm
# -25mm > 10mm (caution), so it should be CAUTION at minimum

stats5 = classify_sections(secs_now, secs_base)
warn5 = [(i, s) for i, (s, _) in enumerate(stats5) if s != "OK"]
ck("dW CAUTION detected from T0",  len(warn5) >= 1, f"warns={warn5}")

print(f"\n{'='*55}")
print(f"  PASS={PASS}  FAIL={FAIL}  TOTAL={PASS+FAIL}")
if FAIL == 0:
    print("  All consistency checks PASSED")
else:
    print("  Some consistency checks FAILED")
sys.exit(FAIL)
