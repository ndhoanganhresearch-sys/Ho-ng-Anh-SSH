# -*- coding: utf-8 -*-
"""Smoke-test the multi-epoch coloured cross-section overlay (T0~Tn)."""
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

def ring(R=3.0, settle_mm=0.0, n=240):
    """Circle of radius R with the crown pulled down by settle_mm (deformation)."""
    a = np.linspace(0, 2 * np.pi, n)
    r = np.full(n, R)
    # crown band near +90deg shrinks radius (settlement), in metres
    crown = np.exp(-((a - np.pi / 2) ** 2) / (2 * 0.4 ** 2))
    r = r - crown * (settle_mm / 1000.0)
    return np.column_stack([r * np.cos(a), r * np.sin(a)])

def make_epoch(settle_mm):
    secs = []
    for i in range(4):
        sg = SectionGeometry(chainage=float(i * 5))
        defo = settle_mm if i == 1 else 0.0   # section 1 carries the deformation
        sg.pts_2d = ring(settle_mm=defo)
        sg.radius_fit = 3.0; sg.W1 = 6.0
        # crown settlement lowers the section height H1 (drives the dH warning)
        sg.H1 = 5.0 - defo / 1000.0
        sg.ovality = 0.1; sg.eccentricity = 2.0
        sg.labels = np.zeros(len(sg.pts_2d), dtype=np.int32)
        sg.clearance_violation = False
        secs.append(sg)
    return secs

# Six epochs T0~T5 with growing crown settlement (0..45 mm).
epochs = [make_epoch(s) for s in (0, 9, 18, 27, 36, 45)]
labels = [f"T{i}" for i in range(6)]

print("=== multi-epoch overlay draws without error ===")
w = MatplotlibSectionWidget()
# Tn (latest) is the active section set; T0~T5 are the overlay epochs.
w.set_sections(epochs[-1], profile="Circle", vl_box_w=6, vl_box_h=6, vl_cir_r=3)
w.set_epoch_sections(epochs, labels)
ck("epoch sections stored", len(w._epoch_sections) == 6, f"n={len(w._epoch_sections)}")
ck("overlay control enabled with epochs", w._chk_overlay.isEnabled())

# Controls hidden by default + checkbox unchecked: overlay must STILL draw
# (decoupled from the control row).
ck("controls hidden by default", w._show_deform_controls is False)
ck("checkbox unchecked by default", not w._chk_overlay.isChecked())
w._refresh()
_leg0 = w._ax.get_legend()
_leg0_txt = [t.get_text() for t in _leg0.get_texts()] if _leg0 else []
ck("overlay draws with controls hidden", all(l in _leg0_txt for l in labels),
   f"legend={_leg0_txt}")

w._chk_overlay.setChecked(True)
# Boost visual scale so amplification path runs.
w._sp_deform_scale.setValue(20.0)
try:
    w._refresh()   # exercises _draw_section -> _draw_epoch_outlines
    drew = True
except Exception as e:
    drew = False
    print("    EXC:", repr(e))
ck("refresh with multi-epoch overlay ran", drew)

# Clean plot: legend lists ONLY the epochs (numbers live in the Info dialog),
# i.e. no deviation-band entries.
leg = w._ax.get_legend()
leg_txt = [t.get_text() for t in leg.get_texts()] if leg else []
ck("legend lists epoch labels", all(l in leg_txt for l in labels), f"legend={leg_txt}")
ck("legend has no deviation bands (clean plot)",
   not any(">" in t or "mm" in t for t in leg_txt), f"legend={leg_txt}")
# Basic dimension schematic (W/H) stays on the plot even with the overlay.
ax_texts = [t.get_text() for t in w._ax.texts]
ck("basic dimensions kept on plot (W1/H1)",
   any("W1=" in t for t in ax_texts) and any("H1=" in t for t in ax_texts),
   f"texts={[t for t in ax_texts if '=' in t][:4]}")

print("=== Info per-epoch deviation math (_radial_profile) ===")
# This mirrors what the Info dialog computes: peak radial deviation vs T0.
edges = np.linspace(-np.pi, np.pi, 181)
p0 = w._radial_profile(ring(settle_mm=0.0), edges)
pn = w._radial_profile(ring(settle_mm=45.0), edges)
dev = pn - p0
peak = float(dev[np.nanargmax(np.abs(dev))]) * 1e3
ck("peak deviation ~ -45mm (true geometry)", abs(peak + 45.0) < 8.0, f"peak={peak}")
flat = w._radial_profile(ring(settle_mm=0.0), edges) - p0
ck("flat section peaks near 0", abs(float(np.nanmax(np.abs(flat))) * 1e3) < 2.0)

print("=== worst-epoch warning classification (option A) ===")
from tunnel_analysis.section_warnings import classify_sections
# Single-epoch view: comparing T1 vs T0 — section 1 deforms only 9mm -> OK.
st_t1 = classify_sections(epochs[1], epochs[0])
ck("T1-vs-T0 alone: deformed section still OK (9mm < 10)",
   st_t1[1][0] == "OK", f"status={st_t1[1][0]}")
# Worst across all epochs: T5 drops H1 by 45mm -> CRITICAL at section 1.
st_worst = classify_sections(epochs[0], epochs[0], epoch_sections=epochs)
ck("worst-epoch flags deformed section CRITICAL",
   st_worst[1][0] == "CRITICAL", f"status={st_worst[1][0]}")
ck("worst-epoch leaves calm sections OK",
   st_worst[0][0] == "OK" and st_worst[2][0] == "OK",
   f"s0={st_worst[0][0]} s2={st_worst[2][0]}")
# The widget cache (used by 2D track/banner) must agree.
ck("widget cached status uses worst epoch",
   w._section_statuses[1][0] == "CRITICAL", f"cache={w._section_statuses[1][0]}")

print("=== _radial_outline basics ===")
out = MatplotlibSectionWidget._radial_outline(ring())
ck("outline returned", out is not None)
if out is not None:
    ox, oz = out
    ck("outline is a closed loop", abs(ox[0] - ox[-1]) < 1e-9 and abs(oz[0] - oz[-1]) < 1e-9)
    ck("outline radius ~ 3.0 m", abs(float(np.median(np.hypot(ox, oz))) - 3.0) < 0.05)
ck("too-few-points -> None", MatplotlibSectionWidget._radial_outline(np.zeros((3, 2))) is None)

print("=== M3C2 2D developed map widget ===")
from tunnel_analysis.ui.widgets import M3C2MapWidget
mw = M3C2MapWidget()
ck("M3C2 widget canvas created", mw._canvas is not None)
# Synthetic developed map: chainage 0..40, angle -180..180, displacement.
N = 500
chain = np.random.RandomState(0).uniform(0, 40, N)
angle = np.random.RandomState(1).uniform(-180, 180, N)
disp = -20.0 * np.exp(-((chain - 20) ** 2) / 50.0)   # crown-like dip near ch20
zones = [
    {"chainage": 20.0, "position": "Crown", "peak_mm": -30.0, "severity": "CRITICAL", "angle": 90.0},
    {"chainage": 45.0, "position": "Wall (R)", "peak_mm": -14.0, "severity": "CAUTION", "angle": 0.0},
]
try:
    mw.set_map(chain, angle, disp, zones=zones, method="M3C2")
    drew_m3c2 = True
except Exception as e:
    drew_m3c2 = False; print("    EXC:", repr(e))
ck("M3C2 damage map renders without error", drew_m3c2)
ck("M3C2 map produced an axes with a colorbar", len(mw._fig.axes) >= 2)
ck("damage-zone table populated", mw._table.rowCount() == 2,
   f"rows={mw._table.rowCount()}")

print(f"\nPASS={P} FAIL={F}")
if F == 0:
    print("MULTI-EPOCH OVERLAY SMOKE PASSED")
sys.exit(1 if F else 0)
