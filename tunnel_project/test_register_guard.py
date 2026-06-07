# -*- coding: utf-8 -*-
r"""Regression test for register_epochs() divergence guard.

On a long, near-symmetric tunnel a naive full-cloud ICP can slide along the
axis and end up FAR worse than the input (observed: 233 m). register_epochs
evaluates {as-is, coarse, trimmed-ICP} and keeps the smallest-RMSE result, so
it must NEVER return something worse than doing nothing. This locks that in.

Run from tunnel_project:
    ..\.venv\Scripts\python.exe test_register_guard.py
"""
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
import warnings; warnings.filterwarnings("ignore")

from tunnel_analysis.registration import RegistrationLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle

P = F = 0
def ck(n, c, i=""):
    global P, F
    print(("  [PASS] " if c else "  [FAIL] ") + n + ("  -> " + i if i else ""))
    P += (1 if c else 0); F += (0 if c else 1)

RNG = np.random.default_rng(11)

def long_tunnel(R=3.0, length=150.0, n_axial=300, m=80):
    ys = np.linspace(0, length, n_axial)
    pts = []
    for y in ys:
        a = np.linspace(0, 2*np.pi, m, endpoint=False) + RNG.uniform(-0.03, 0.03, m)
        x = R*np.cos(a) + RNG.normal(0, 0.004, m)
        z = R*np.sin(a) + RNG.normal(0, 0.004, m)
        pts.append(np.column_stack([x, np.full(m, y), z]))
    return np.vstack(pts)

reg = RegistrationLayer()

print("\n=== Already-aligned long tunnel: ICP must not slide ===")
T0 = long_tunnel()
Tn = long_tunnel(R=3.0)             # independent sampling, same frame
ctx = PipelineContext(); ctx.scans = [PointCloudBundle(points=T0),
                                      PointCloudBundle(points=Tn)]; ctx.active_index = 1
rmse_in = reg._rmse(Tn, T0)
res = reg.register_epochs(ctx)
gap = np.linalg.norm(T0.mean(0) - res["points"].mean(0))
print(f"      rmse in={rmse_in:.1f}mm -> out={res['rmse_mm']:.1f}mm  gap={gap:.2f}m  method={res['method']}")
ck("result RMSE never worse than input (guard)", res["rmse_mm"] <= rmse_in + 1.0,
   f"in={rmse_in:.1f} out={res['rmse_mm']:.1f}")
ck("axis did NOT slide (gap < 2m, was the 233m failure mode)", gap < 2.0,
   f"gap={gap:.2f}m")

print("\n=== Tn displaced laterally: guard still never worse ===")
T0b = long_tunnel()
Tnb = long_tunnel() + np.array([1.5, 0.0, 0.8])   # lateral + vertical shift
ctx2 = PipelineContext(); ctx2.scans = [PointCloudBundle(points=T0b),
                                        PointCloudBundle(points=Tnb)]; ctx2.active_index = 1
rmse_in2 = reg._rmse(Tnb, T0b)
res2 = reg.register_epochs(ctx2)
print(f"      rmse in={rmse_in2:.1f}mm -> out={res2['rmse_mm']:.1f}mm")
ck("result RMSE never worse than input (lateral shift)",
   res2["rmse_mm"] <= rmse_in2 + 1.0, f"in={rmse_in2:.1f} out={res2['rmse_mm']:.1f}")
ck("registered_points returned", res2["points"] is not None and len(res2["points"]) == len(Tnb))

print(f"\n{'='*60}")
print(f"  PASS={P}  FAIL={F}")
print("  " + ("REGISTER GUARD REGRESSION OK" if F == 0 else f"{F} FAILED"))
sys.exit(F)
