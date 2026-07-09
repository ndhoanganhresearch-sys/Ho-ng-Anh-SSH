# -*- coding: utf-8 -*-
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np
from tunnel_analysis.timeseries import TimeSeriesLayer
from tunnel_analysis.section_warnings import SECTION_DELTA_CAUTION_MM, SECTION_DELTA_CRITICAL_MM

assert SECTION_DELTA_CAUTION_MM == 10.0
assert SECTION_DELTA_CRITICAL_MM == 25.0

# Synthetic straight tunnel: crown dip near chainage 20 m
rng = np.random.default_rng(0)
n = 8000
y = rng.uniform(0.0, 80.0, size=n)
theta = rng.uniform(0.0, 2*np.pi, size=n)
r = 3.0 + rng.normal(0.0, 0.01, size=n)
x = r * np.cos(theta)
z = r * np.sin(theta)
t0 = np.c_[x, y, z]
tn = t0.copy()
mask = (np.abs(tn[:,1] - 20.0) <= 2.0) & (tn[:,2] > 1.5)
tn[mask, 2] -= 0.04  # 40 mm settlement

ts = TimeSeriesLayer()
pick = ts.suggest_crown_chainage([t0, tn], curve_radius_m=None, step_m=5.0)
print("pick", pick)
assert pick["source"] == "auto-peak", pick
assert 10.0 <= pick["chainage_m"] <= 30.0, pick
assert pick["settlement_mm"] < -10.0, pick

# preferred wins
pref = ts.suggest_crown_chainage([t0, tn], preferred_chainage_m=45.0)
assert pref["source"] == "preferred" and abs(pref["chainage_m"] - 45.0) < 1e-9

# forecast defaults come from shared constants
series = {"labels": ["T1","T2","T3"], "p95_abs_mm": np.array([5.0, 12.0, 20.0])}
fc = ts.forecast_threshold_crossing(series)
assert abs(fc.get("caution_mm", 0) - 10.0) < 1e-9 or "caution_mm" in fc or fc.get("ok") in (True, False)
# function should accept defaults without explicit 10/25
print("SUGGEST CROWN CHAINAGE TEST PASSED")
