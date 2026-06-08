# -*- coding: utf-8 -*-
"""Smoke test for data/box_icp_shift ICP registration."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.registration import RegistrationLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle

DATA = Path(__file__).resolve().parent / "data" / "box_icp_shift"
loader = BaseLayer()
t0 = loader.load_scan(str(DATA / "T0_box_icp.txt"), max_points=100_000)
tn = loader.load_scan(str(DATA / "Tn_box_icp.txt"), max_points=100_000)

assert t0.points.shape[0] == 34364, t0.points.shape
assert tn.points.shape[0] == 34484, tn.points.shape

gap0 = float(np.linalg.norm(t0.points.mean(axis=0) - tn.points.mean(axis=0)))
assert gap0 > 5.0, gap0

ctx = PipelineContext()
ctx.scans = [PointCloudBundle(points=t0.points), PointCloudBundle(points=tn.points)]
ctx.active_index = 1
res = RegistrationLayer().register_epochs(ctx)
aligned = res["points"]
gap1 = float(np.linalg.norm(t0.points.mean(axis=0) - aligned.mean(axis=0)))

assert res["method"] in ("icp", "target"), res
assert np.isfinite(res["rmse_mm"]), res
assert gap1 < gap0 * 0.35, (gap0, gap1, res)
assert ctx.registered_points is not None

print("BOX ICP SHIFT SMOKE PASSED")
print(f"method={res['method']} rmse={res['rmse_mm']:.1f}mm gap={gap0:.2f}m->{gap1:.2f}m")
