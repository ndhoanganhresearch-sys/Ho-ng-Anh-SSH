# -*- coding: utf-8 -*-
"""Smoke test for the short centered box dataset with 4 spaced defects."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle
from tunnel_analysis.ui.widgets import classify_sections

DATA = Path(__file__).resolve().parent / "data" / "box_four_spots"

loader = BaseLayer()
t0 = loader.load_scan(str(DATA / "T0_box_short.txt"), max_points=100_000)
tn = loader.load_scan(str(DATA / "Tn_box_short.txt"), max_points=100_000)

assert t0.points.shape[0] == 34364, t0.points.shape
assert tn.points.shape[0] == 34504, tn.points.shape

geo = GeometricLayer()
par = ParameterExtractionLayer()
ctx = PipelineContext()
ctx.scans = [PointCloudBundle(points=t0.points), PointCloudBundle(points=tn.points)]
ctx.active_index = 1

# Profile and centerline from the reference epoch.
ctx0 = PipelineContext()
ctx0.scans = [PointCloudBundle(points=t0.points)]
ctx0.active_index = 0
cl, fr = geo.extract_centerline_bspline(ctx0, section_count=60)
ctx.centerline, ctx.frenet_frames = cl, fr
ctx0.centerline, ctx0.frenet_frames = cl, fr

profile = par.detect_profile(ctx0)
assert profile in ("Box", "Box 2-cell"), profile
ctx.tunnel_profile = profile
ctx0.tunnel_profile = profile

# T0/Tn are already in the same centered frame for this short dataset.

# Step 6 parameters should show real deformation.
crown = par.calc_arch_settlement(ctx)
conv = par.calc_horizontal_convergence(ctx)
ecc = par.calc_eccentricity(ctx)
assert crown["settlement_reference"] == "T0_per_section", crown
assert conv["convergence_reference"] == "T0_per_section", conv
assert ecc["eccentricity_reference"] == "T0_comparison", ecc
assert abs(crown["crown_settlement_max_mm"]) > 10.0, crown
assert abs(conv["lateral_convergence_max_mm"]) > 10.0, conv
assert ecc["eccentricity_max_mm"] > 5.0, ecc

sections_t0 = par.compute_all_sections(ctx0, vl_box_w=4.4, vl_box_h=4.8, vl_cir_r=3.0)
sections_tn = par.compute_all_sections(ctx, vl_box_w=4.4, vl_box_h=4.8, vl_cir_r=3.0)
assert len(sections_t0) == len(sections_tn) == 60
assert sum(s.pts_2d is not None for s in sections_tn) >= 45
statuses = classify_sections(sections_tn, sections_t0)
assert any(status != "OK" for status, _ in statuses), statuses[:5]
assert any(status == "CRITICAL" for status, _ in statuses), statuses[:5]

print("BOX FOUR SPOTS SMOKE PASSED")
print(f"profile={profile} crown_max={crown['crown_settlement_max_mm']:.1f}mm conv_max={conv['lateral_convergence_max_mm']:.1f}mm ecc_max={ecc['eccentricity_max_mm']:.1f}mm")
