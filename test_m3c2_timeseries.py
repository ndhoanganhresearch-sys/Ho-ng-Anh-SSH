#!/usr/bin/env python3
"""Quick test: M3C2 on T0/T5 from time_series_deformation."""
import sys
sys.path.insert(0, r"C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project")

import numpy as np
from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.timeseries import TimeSeriesLayer
from tunnel_analysis.common import validate_xyz

# Load T0 and T5
bl = BaseLayer()
print("Loading T0...")
t0_bundle = bl.load_scan(r"C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project\data\time_series_deformation\T0.las")
print(f"  T0 shape: {t0_bundle.points.shape}")

print("Loading T5...")
t5_bundle = bl.load_scan(r"C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project\data\time_series_deformation\T5.las")
print(f"  T5 shape: {t5_bundle.points.shape}")

# Run M3C2
ts = TimeSeriesLayer()
print("\nRunning M3C2 (cyl_radius=0.5, normal_radius=0.6)...")
result = ts.m3c2_distances(
    t0_bundle.points,
    t5_bundle.points,
    cyl_radius=0.5,
    normal_radius=0.6
)

print(f"\nM3C2 Result:")
print(f"  Method: {result['method']}")
print(f"  Corepoints shape: {result['corepoints'].shape}")
print(f"  Distance_mm shape: {result['distance_mm'].shape}")
print(f"  Distance_mm stats:")
print(f"    min={np.nanmin(result['distance_mm']):.2f}mm")
print(f"    max={np.nanmax(result['distance_mm']):.2f}mm")
print(f"    median={np.nanmedian(result['distance_mm']):.2f}mm")
print(f"    mean={np.nanmean(result['distance_mm']):.2f}mm")
print(f"  NaN count: {np.isnan(result['distance_mm']).sum()} / {result['distance_mm'].size}")

if "lod_mm" in result and not np.all(np.isnan(result['lod_mm'])):
    print(f"  LoD stats:")
    print(f"    min={np.nanmin(result['lod_mm']):.2f}mm")
    print(f"    max={np.nanmax(result['lod_mm']):.2f}mm")
    print(f"    median={np.nanmedian(result['lod_mm']):.2f}mm")
    significant = result.get('significant', np.array([]))
    if significant is not None and len(significant) > 0:
        print(f"  Significant count: {np.count_nonzero(significant)} / {len(significant)}")
