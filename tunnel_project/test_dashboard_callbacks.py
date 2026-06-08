"""Regression test for web_dashboard interactivity (item 1.3).

Locks the callback helper logic (pure, no browser needed) plus verifies
build_app actually registers the interactive callbacks:
  - _pick_section: by point index and by nearest-chainage fallback
  - _filter_sections: all / warnings / violations
  - _section_detail_panel: None -> hint, row -> card
  - build_app registers >= 2 callbacks
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from tunnel_analysis import web_dashboard as WD

PASS = 0
FAIL = 0

def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"[PASS] {name}  {extra}")
    else:
        FAIL += 1; print(f"[FAIL] {name}  {extra}")

# Synthetic prepared section rows (same shape build_app produces)
sec_data = [
    {"Chainage (m)": 0.0,  "H1 (m)": 6.0, "W1 (m)": 5.0, "Ovality (%)": 0.2,
     "Ecc (mm)": 3.0,  "R_fit (m)": 2.75, "Clearance": "OK"},
    {"Chainage (m)": 10.0, "H1 (m)": 6.0, "W1 (m)": 5.0, "Ovality (%)": 0.7,
     "Ecc (mm)": 5.0,  "R_fit (m)": 2.75, "Clearance": "OK"},          # warning (ovality)
    {"Chainage (m)": 20.0, "H1 (m)": 6.0, "W1 (m)": 5.0, "Ovality (%)": 0.1,
     "Ecc (mm)": 15.0, "R_fit (m)": 2.75, "Clearance": "OK"},          # warning (ecc)
    {"Chainage (m)": 30.0, "H1 (m)": 6.0, "W1 (m)": 5.0, "Ovality (%)": 0.1,
     "Ecc (mm)": 2.0,  "R_fit (m)": 2.75, "Clearance": "⚠ VIOLATION"}, # violation
]

# 1) _pick_section by explicit point index
row = WD._pick_section(sec_data, {"points": [{"pointIndex": 2, "x": 20.0}]})
check("pick by index -> chainage 20", row is not None and row["Chainage (m)"] == 20.0)

# 2) _pick_section nearest-chainage fallback (no index, x between points)
row = WD._pick_section(sec_data, {"points": [{"x": 9.0}]})
check("pick by nearest x=9 -> chainage 10", row is not None and row["Chainage (m)"] == 10.0)

# 3) _pick_section robustness
check("pick none on empty click", WD._pick_section(sec_data, None) is None)
check("pick none on no points", WD._pick_section(sec_data, {"points": []}) is None)
check("pick none on out-of-range index",
      WD._pick_section(sec_data, {"points": [{"pointIndex": 99}]}) is None)

# 4) _filter_sections
check("filter all -> 4 rows", len(WD._filter_sections(sec_data, "all")) == 4)
check("filter violations -> 1 row", len(WD._filter_sections(sec_data, "violations")) == 1)
# warnings: ovality>=0.5 (row1) + ecc>=10 (row2) + violation (row3) = 3
check("filter warnings -> 3 rows", len(WD._filter_sections(sec_data, "warnings")) == 3,
      f"got {len(WD._filter_sections(sec_data, 'warnings'))}")

# 5) _section_detail_panel
panel_none = WD._section_detail_panel(None)
check("detail(None) returns a component", panel_none is not None)
panel_row = WD._section_detail_panel(sec_data[3])
check("detail(row) returns a component", panel_row is not None)

# 6) build_app registers callbacks
try:
    from tunnel_analysis.models import PipelineContext
    ctx = PipelineContext()
    # minimal: no sections is fine; build_app should still wire callbacks
    app = WD.build_app(ctx)
    n_cb = len(getattr(app, "callback_map", {}))
    check("build_app registers >= 2 callbacks", n_cb >= 2, f"n_callbacks={n_cb}")
except Exception as e:
    check("build_app registers >= 2 callbacks", False, f"EXC: {type(e).__name__}: {e}")

print(f"\nPASS={PASS}  FAIL={FAIL}")
if FAIL == 0:
    print("DASHBOARD CALLBACKS OK")
sys.exit(1 if FAIL else 0)
