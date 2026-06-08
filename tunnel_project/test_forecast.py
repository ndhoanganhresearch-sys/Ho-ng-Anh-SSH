"""Regression test for TimeSeriesLayer.forecast_threshold_crossing.

Locks the predictive-maintenance trend extrapolation (item 1.2):
  - linear growth -> correct rate + crossing time
  - explicit times (months) honoured
  - already-exceeded threshold -> crossing == now
  - flat/recovering trend -> no crossing predicted
  - too few epochs -> ok=False
  - quadratic acceleration crosses earlier than linear
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from tunnel_analysis.timeseries import TimeSeriesLayer

PASS = 0
FAIL = 0

def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"[PASS] {name}  {extra}")
    else:
        FAIL += 1; print(f"[FAIL] {name}  {extra}")

ts = TimeSeriesLayer()

# 1) Linear growth: 5,10,15,20 mm at t=1,2,3,4 -> rate 5 mm/unit
#    crosses CAUTION(10) at t=2 (already passed), CRITICAL(25) at t=5 -> dt=1
series = {"labels": ["T1", "T2", "T3", "T4"],
          "p95_abs_mm": np.array([5.0, 10.0, 15.0, 20.0])}
r = ts.forecast_threshold_crossing(series, caution_mm=10.0, critical_mm=25.0)
check("linear ok", r["ok"])
check("linear rate ~5mm/unit", abs(r["rate_per_unit"] - 5.0) < 1e-6,
      f"rate={r['rate_per_unit']:.3f}")
check("linear R^2 ~1", r["r_squared"] > 0.999, f"r2={r['r_squared']:.4f}")
check("linear CRITICAL crosses at t=5 (dt=1)",
      r["t_critical"] is not None and abs(r["t_critical"] - 5.0) < 1e-6
      and abs(r["dt_critical"] - 1.0) < 1e-6,
      f"t_crit={r['t_critical']}")
check("linear CAUTION already exceeded (v_last=20>=10)",
      abs(r["t_caution"] - 4.0) < 1e-6, f"t_caut={r['t_caution']}")

# 2) Explicit times in months: same values at months 2,4,6,8 -> rate 2.5/mo
series2 = {"labels": ["T1", "T2", "T3", "T4"],
           "p95_abs_mm": np.array([5.0, 10.0, 15.0, 20.0])}
r2 = ts.forecast_threshold_crossing(series2, times=[2, 4, 6, 8],
                                    caution_mm=10.0, critical_mm=25.0)
check("months rate ~2.5mm/mo", abs(r2["rate_per_unit"] - 2.5) < 1e-6,
      f"rate={r2['rate_per_unit']:.3f}")
check("months CRITICAL at month 10 (dt=2)",
      abs(r2["t_critical"] - 10.0) < 1e-6 and abs(r2["dt_critical"] - 2.0) < 1e-6,
      f"t_crit={r2['t_critical']}")

# 3) Flat trend: 3,3,3,3 -> no crossing toward 10
series3 = {"labels": ["T1", "T2", "T3", "T4"],
           "p95_abs_mm": np.array([3.0, 3.0, 3.0, 3.0])}
r3 = ts.forecast_threshold_crossing(series3, caution_mm=10.0, critical_mm=25.0)
check("flat -> no CAUTION crossing", r3["t_caution"] is None)
check("flat -> no CRITICAL crossing", r3["t_critical"] is None)

# 4) Recovering (decreasing): 9,7,5,3 -> no future crossing
series4 = {"labels": ["T1", "T2", "T3", "T4"],
           "p95_abs_mm": np.array([9.0, 7.0, 5.0, 3.0])}
r4 = ts.forecast_threshold_crossing(series4, caution_mm=10.0, critical_mm=25.0)
check("recovering -> negative rate", r4["rate_per_unit"] < 0)
check("recovering -> no CAUTION crossing", r4["t_caution"] is None)

# 5) Too few epochs -> ok False
series5 = {"labels": ["T1", "T2"], "p95_abs_mm": np.array([5.0, 10.0])}
r5 = ts.forecast_threshold_crossing(series5)
check("2 epochs -> ok False", r5["ok"] is False)

# 6) Quadratic acceleration crosses earlier than linear fit on same data
#    values accelerate: 2,6,12,20 (second diff +2) toward CRITICAL 25
series6 = {"labels": ["T1", "T2", "T3", "T4"],
           "p95_abs_mm": np.array([2.0, 6.0, 12.0, 20.0])}
lin = ts.forecast_threshold_crossing(series6, degree=1, critical_mm=25.0)
quad = ts.forecast_threshold_crossing(series6, degree=2, critical_mm=25.0)
check("quad fits better (higher R^2)", quad["r_squared"] >= lin["r_squared"] - 1e-9,
      f"lin={lin['r_squared']:.3f} quad={quad['r_squared']:.3f}")
check("quad crosses CRITICAL no later than linear",
      quad["t_critical"] is not None and lin["t_critical"] is not None
      and quad["t_critical"] <= lin["t_critical"] + 1e-6,
      f"lin t={lin['t_critical']:.2f} quad t={quad['t_critical']:.2f}")

# 7) summary is a non-empty string
check("summary populated", isinstance(r["summary"], str) and len(r["summary"]) > 0,
      r["summary"][:60])

print(f"\nPASS={PASS}  FAIL={FAIL}")
if FAIL == 0:
    print("FORECAST THRESHOLD CROSSING OK")
sys.exit(1 if FAIL else 0)
