# -*- coding: utf-8 -*-
"""Step 6 improvements: incremental series, rate/acceleration, GT validation.

Runs on the clean time_series_deformation T0~T5 fixture (registered, noise-free).
"""
import os, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from tunnel_analysis.timeseries import TimeSeriesLayer

DATA = os.path.join("data", "time_series_deformation")
P = F = 0
def ck(n, c, i=""):
    global P, F
    print(("  [PASS] " if c else "  [FAIL] ") + n + ("  " + i if i else ""))
    P += (1 if c else 0); F += (0 if c else 1)

# Load T0~T5 (xyz only) from the debug txt files (skip '#' header).
epochs = []
for k in range(6):
    pts = np.loadtxt(os.path.join(DATA, f"T{k}.txt"), comments="#", usecols=(0, 1, 2))
    epochs.append(np.asarray(pts, dtype=np.float64))
labels = [f"T{k}" for k in range(1, 6)]
print(f"Loaded {len(epochs)} epochs, {epochs[0].shape[0]} pts each")

ts = TimeSeriesLayer()
series = ts.spatiotemporal_series(epochs, labels=labels,
                                  cyl_radius=0.5, normal_radius=0.6)
print(f"method={series['method']}  p95={np.round(series['p95_abs_mm'],1)}  "
      f"max={np.round(series['max_abs_mm'],1)}")

print("=== incremental series ===")
inc = series["incremental_matrix_mm"]
cum = series["distance_matrix_mm"]
ck("incremental cumsum reconstructs cumulative (exact)",
   np.allclose(np.cumsum(inc, axis=0), cum, atol=1e-6))
ck("incremental keys present",
   all(k in series for k in ("incremental_p95_abs_mm", "incremental_median_mm")))
ck("deformation actually present (incremental nonzero)",
   float(np.nanmax(series["incremental_p95_abs_mm"])) > 1.0,
   f"max inc p95={np.nanmax(series['incremental_p95_abs_mm']):.1f}mm")

print("=== rate (velocity) + acceleration ===")
vel = np.asarray(series["velocity_mm_per_epoch"])
acc = np.asarray(series["acceleration_mm_per_epoch2"])
ck("velocity/acceleration length matches epochs",
   vel.size == len(labels) and acc.size == len(labels))
ck("all finite", np.isfinite(vel).all() and np.isfinite(acc).all())
ck("deformation still growing at last epoch (velocity>0)", vel[-1] > 0, f"v={vel[-1]:.1f}")
ck("accelerating flag computed", isinstance(series["accelerating"], list)
   and len(series["accelerating"]) == len(labels))

print("=== ground-truth validation ===")
gt = ts.compare_to_ground_truth(series, os.path.join(DATA, "ground_truth.csv"))
print("  " + gt["summary"])
for r in gt["per_epoch"]:
    print(f"    {r['epoch']}: GT={r['gt_peak_mm']:+.0f}mm  measured={r['measured_mm']:.0f}mm  "
          f"err={r['error_mm']:+.0f}mm")
ck("matched all 5 monitoring epochs", gt["n"] == 5, f"n={gt['n']}")
ck("MAE within tolerance (<20mm)", np.isfinite(gt["mae_mm"]) and gt["mae_mm"] < 20.0,
   f"MAE={gt['mae_mm']:.1f}mm")
ck("T5 peak recovered near GT 45mm (25..70)",
   25.0 <= gt["per_epoch"][-1]["measured_mm"] <= 70.0,
   f"measured={gt['per_epoch'][-1]['measured_mm']:.0f}mm")

print("=== forecast threshold crossing (keys for widget) ===")
fc = ts.forecast_threshold_crossing(series, caution_mm=10.0, critical_mm=25.0,
                                    degree=2, metric="max_abs_mm")
ck("forecast ok", fc.get("ok") is True, fc.get("reason", ""))
ck("widget alias keys present",
   all(k in fc for k in ("caution_crossing_epoch", "critical_crossing_epoch",
                         "forecast_epochs", "forecast_values")))
ck("forecast curve has points", len(fc.get("forecast_epochs", [])) > 1)

print("=== Excel + PDF export ===")
import tempfile
outdir = tempfile.mkdtemp(prefix="ts_export_")
from tunnel_analysis.exporter import TunnelExporter
xlsx = os.path.join(outdir, "ts.xlsx")
try:
    p = TunnelExporter().export_timeseries_excel(series, xlsx, gt=gt, forecast=fc)
    ck("Excel written", os.path.exists(p) and os.path.getsize(p) > 0, p)
except Exception as e:
    ck("Excel written", False, repr(e))
try:
    from tunnel_analysis.pdf_reporter import TunnelPDFReporter
    pdf = os.path.join(outdir, "ts.pdf")
    p2 = TunnelPDFReporter().export_timeseries_pdf(series, pdf, gt=gt, forecast=fc)
    ck("PDF written", os.path.exists(p2) and os.path.getsize(p2) > 0, p2)
except Exception as e:
    ck("PDF written (reportlab optional)", False, repr(e))

print(f"\nPASS={P} FAIL={F}")
if F == 0:
    print("STEP 6 IMPROVEMENTS TEST PASSED")
sys.exit(1 if F else 0)
