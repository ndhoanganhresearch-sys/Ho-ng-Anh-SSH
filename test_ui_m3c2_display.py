#!/usr/bin/env python3
"""Test if M3C2 display in UI works correctly on time_series_deformation."""
import sys
sys.path.insert(0, r"C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project")

import numpy as np
from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.timeseries import TimeSeriesLayer
from tunnel_analysis.ui.widgets import make_vertex_cloud

# Load T0 and T5
bl = BaseLayer()
t0 = bl.load_scan(r"C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project\data\time_series_deformation\T0.las").points
t5 = bl.load_scan(r"C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project\data\time_series_deformation\T5.las").points

# Run M3C2
ts = TimeSeriesLayer()
result = ts.m3c2_distances(t0, t5, cyl_radius=0.5, normal_radius=0.6)

print(f"M3C2 Result:")
print(f"  Method: {result['method']}")
print(f"  Corepoints: {result['corepoints'].shape}")

# Simulate display decimation (from main_window.py)
DISPLAY_MAX_POINTS = 600_000
pts = np.asarray(result["corepoints"], dtype=np.float64)
dist_mm = np.asarray(result["distance_mm"], dtype=np.float64)

n = len(pts)
if n > DISPLAY_MAX_POINTS:
    step = int(np.ceil(n / DISPLAY_MAX_POINTS))
    pts = pts[::step]
    dist_mm = dist_mm[::step]
    print(f"  After decimation: {pts.shape} (step={step})")
else:
    print(f"  No decimation needed (n={n} <= {DISPLAY_MAX_POINTS})")

# Try to create mesh (same as UI)
try:
    mesh = make_vertex_cloud(pts)
    print(f"  Mesh created: {mesh.n_points} points")

    # Check if scalars align
    if dist_mm is not None and len(dist_mm) == mesh.n_points:
        mesh["M3C2_mm"] = dist_mm
        print(f"  Scalars assigned successfully")
        print(f"    Scalar range: [{np.nanmin(dist_mm):.2f}, {np.nanmax(dist_mm):.2f}]mm")
        print(f"    NaN count: {np.isnan(dist_mm).sum()}")
    else:
        print(f"  MISMATCH: scalars={len(dist_mm)} vs mesh.n_points={mesh.n_points}")
except Exception as e:
    print(f"  ERROR creating mesh: {e}")

# Compute color scale (same as UI line 1326-1327)
lim = float(np.nanmax(np.abs(dist_mm))) if dist_mm.size else 1.0
lim = max(lim, 1e-6)
print(f"\nColor scale limits: [-{lim:.2f}, {lim:.2f}]mm")
print(f"Note: If lim is too small, heatmap won't show visible gradation")
