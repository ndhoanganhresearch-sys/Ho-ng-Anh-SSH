"""Smoke-test for ChainageRulerWidget — runs headless (offscreen QApplication)."""
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
from PySide6 import QtWidgets, QtCore

# Bootstrap QApplication before importing any widget
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from tunnel_analysis.ui.widgets import ChainageRulerWidget, section_warning_status
from tunnel_analysis.models import SectionGeometry

# ── helpers ────────────────────────────────────────────────────────────────

def make_section(chainage: float, radius: float = 3.0) -> SectionGeometry:
    sg = SectionGeometry(chainage=chainage, pts_2d=None)
    sg.radius_fit = radius
    sg.crown_settlement = 0.0
    sg.convergence      = 0.0
    sg.ovality          = 0.0
    sg.eccentricity     = 0.0
    sg.W1 = sg.H1 = 0.0
    return sg


def make_warn_section(chainage: float, radius_delta_m: float = -0.10) -> SectionGeometry:
    """Section with CRITICAL warning: radius shrank by |radius_delta_m|.

    section_warning_status compares (sg.radius_fit - ref_sg.radius_fit)*1e3 mm.
    Default -0.10 m = -100 mm, which exceeds CRITICAL threshold (25 mm).
    """
    sg = make_section(chainage, radius=3.0 + radius_delta_m)
    return sg


PASS = 0; FAIL = 0

def check(name, cond, info=""):
    global PASS, FAIL
    if cond:
        print(f"  [PASS] {name}")
        PASS += 1
    else:
        print(f"  [FAIL] {name}  {info}")
        FAIL += 1

# ══════════════════════════════════════════════════════════════════════════
print("\n── Test 1: ChainageRulerWidget construction ──────────────────────")
ruler = ChainageRulerWidget()
ruler.resize(800, 50)
check("widget created",      ruler is not None)
check("fixed height 50px",   ruler.height() == 50)
check("no initial sections", ruler._min_ch == ruler._max_ch == 0.0)
check("no marks initially",  len(ruler._marks) == 0)

# ══════════════════════════════════════════════════════════════════════════
print("\n── Test 2: set_sections() with clean (OK) sections ────────────────")
sections = [make_section(float(c)) for c in range(0, 110, 10)]
ruler.set_sections(sections)
check("min_ch = 0",           ruler._min_ch == 0.0)
check("max_ch = 100",         ruler._max_ch == 100.0)
check("11 fracs",             len(ruler._fracs) == 11)
check("frac[0] = 0.0",        abs(ruler._fracs[0] - 0.0) < 1e-9)
check("frac[-1] = 1.0",       abs(ruler._fracs[-1] - 1.0) < 1e-9)
check("no warning marks",     len(ruler._marks) == 0, f"got {ruler._marks}")
check("11 seg_colors",        len(ruler._seg_colors) == 11)

# ══════════════════════════════════════════════════════════════════════════
print("\n── Test 3: set_sections() with CRITICAL warning ────────────────────")
sections_warn = [make_section(float(c)) for c in range(0, 110, 10)]
# Inject CRITICAL at chainage 50 (index 5): radius shrunk 100 mm vs ref (ref=3.0m)
sections_warn[5] = make_warn_section(50.0, radius_delta_m=-0.10)

ref_sections = [make_section(float(c)) for c in range(0, 110, 10)]
ruler.set_sections(sections_warn, ref_sections)
check("still 11 fracs",       len(ruler._fracs) == 11)
# At least 1 warning mark
check("≥1 warning mark",      len(ruler._marks) >= 1, f"got {ruler._marks}")
# Find the CRITICAL mark
crit = [m for m in ruler._marks if m[1] == "#DC2626"]
check("CRITICAL mark present", len(crit) >= 1, f"marks={ruler._marks}")
if crit:
    frac_crit = crit[0][0]
    check("CRITICAL frac ≈ 0.5",   abs(frac_crit - 0.5) < 0.02,
          f"frac={frac_crit:.4f}")

# ══════════════════════════════════════════════════════════════════════════
print("\n── Test 4: set_current() updates _cur_frac ─────────────────────────")
ruler.set_sections([make_section(float(c)) for c in range(0, 200, 10)])
ruler.set_current(0.0)
check("cur_frac at start = 0",   abs(ruler._cur_frac - 0.0) < 1e-9)
ruler.set_current(100.0)
check("cur_frac at mid = 0.526", abs(ruler._cur_frac - 100/190) < 0.01,
      f"got {ruler._cur_frac:.4f}")
ruler.set_current(190.0)
check("cur_frac at end = 1",     abs(ruler._cur_frac - 1.0) < 1e-9)

# ══════════════════════════════════════════════════════════════════════════
print("\n── Test 5: jumped signal fires on click ────────────────────────────")
ruler.set_sections([make_section(float(c)) for c in range(0, 110, 10)])
ruler.resize(800, 50)

jumped_indices = []
ruler.jumped.connect(lambda idx: jumped_indices.append(idx))

# Simulate click at x=ML (left margin) → should pick index 0
from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtCore import QPointF, QPoint

ev = QMouseEvent(
    QtCore.QEvent.MouseButtonPress,
    QPointF(ruler._ML + 2, 25),   # click just inside left track edge
    QPointF(ruler._ML + 2, 25),   # screenPos (global) — same is fine offscreen
    Qt.LeftButton,
    Qt.LeftButton,
    Qt.NoModifier,
)
ruler.mousePressEvent(ev)
check("jumped signal emitted",  len(jumped_indices) == 1,
      f"indices={jumped_indices}")
if jumped_indices:
    check("jumped to idx 0",    jumped_indices[0] == 0,
          f"jumped_to={jumped_indices[0]}")

# Click near the right edge → should jump to last section (idx 10)
jumped_indices.clear()
ev2 = QMouseEvent(
    QtCore.QEvent.MouseButtonPress,
    QPointF(800 - ruler._MR - 3, 25),
    QPointF(800 - ruler._MR - 3, 25),
    Qt.LeftButton, Qt.LeftButton, Qt.NoModifier,
)
ruler.mousePressEvent(ev2)
check("right-click emitted",    len(jumped_indices) == 1)
if jumped_indices:
    check("jumped to last idx", jumped_indices[0] == 10,
          f"jumped_to={jumped_indices[0]}")

# ══════════════════════════════════════════════════════════════════════════
print("\n── Test 6: clear() resets everything ───────────────────────────────")
ruler.clear()
check("sections empty",       len(ruler._sections) == 0)
check("marks empty",          len(ruler._marks) == 0)
check("cur_frac reset",       ruler._cur_frac == -1.0)

# ══════════════════════════════════════════════════════════════════════════
print("\n── Test 7: paintEvent executes without crash ────────────────────────")
ruler.set_sections(
    [make_warn_section(float(c), -0.15 if c == 40 else -0.03) for c in range(0, 110, 10)],
    [make_section(float(c)) for c in range(0, 110, 10)]
)
ruler.set_current(40.0)
try:
    from PySide6.QtGui import QPixmap
    pm = QPixmap(800, 50)
    ruler.render(pm)   # render(QPaintDevice) — correct PySide6 API
    check("paintEvent no exception", True)
except Exception as exc:
    check("paintEvent no exception", False, str(exc))

# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*55}")
print(f"  PASS={PASS}  FAIL={FAIL}  TOTAL={PASS+FAIL}")
if FAIL == 0:
    print("  🎉 All tests PASSED — ChainageRulerWidget OK")
else:
    print("  ❌ Some tests FAILED")
sys.exit(FAIL)
