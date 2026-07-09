# -*- coding: utf-8 -*-
"""Step 6 crown chainage should follow GT crown peak, not a hardcoded 52 m."""
import os
from pathlib import Path
import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.timeseries import TimeSeriesLayer

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "time_series_deformation"
assert DATA.exists(), DATA

loader = BaseLayer()
# Use T0 and T5 for strong crown signal at chainage 20 m.
files = [DATA / f"T{i}.las" for i in (0, 5)]
if not all(f.exists() for f in files):
    files = [DATA / f"T{i}.txt" for i in (0, 5)]
assert all(f.exists() for f in files), files

epochs = []
for fp in files:
    b = loader.load_scan(str(fp), max_points=80_000)
    epochs.append(np.asarray(b.points, dtype=np.float64))

ts = TimeSeriesLayer()
# Preferred from GT should win.
pref = ts.suggest_crown_chainage(epochs, preferred_chainage_m=20.0, curve_radius_m=None)
assert abs(pref["chainage_m"] - 20.0) < 1e-6, pref
assert pref["source"] == "preferred", pref

# Auto mode should land near crown GT chainage (~20 m), not 52 m.
auto = ts.suggest_crown_chainage(epochs, curve_radius_m=None, step_m=5.0)
print("auto pick", auto)
assert auto["source"] == "auto-peak", auto
assert 10.0 <= float(auto["chainage_m"]) <= 30.0, auto
assert float(auto["settlement_mm"]) < -15.0, auto

crown = ts.crown_settlement_series(
    epochs,
    labels=["T0", "T5"],
    chainage_m=float(auto["chainage_m"]),
    curve_radius_m=None,
)
sett = np.asarray(crown["crown_settlement_mm"], dtype=np.float64)
print("settlement", sett)
assert sett.size >= 2
assert sett[-1] < -15.0, sett

# Shared thresholds still exported from section_warnings defaults.
fc = ts.forecast_threshold_crossing({
    "labels": ["T1", "T2", "T3"],
    "p95_abs_mm": np.array([5.0, 15.0, 28.0], dtype=np.float64),
})
assert "summary" in fc
print("STEP6 CROWN CHAINAGE GT TEST PASSED")
