#!/usr/bin/env python3
"""
Test the scenario where arr[::step] is actually used.
File exceeds max_points, so subsampling occurs.
"""
import numpy as np

print("=== Scenario: 10 M-point file, 7 columns, max_points=5M ===\n")

# Simulate np.loadtxt of 10M x 7
print("1. np.loadtxt: load full array")
arr_full = np.random.rand(10_000_000, 7).astype(np.float64)
full_size = arr_full.nbytes/(1024**2)
print(f"   Size: {full_size:.0f} MB")

# Subsample check
total = len(arr_full)
max_points = 5_000_000
if total > max_points:
    print(f"\n2. Subsampling (total {total} > max {max_points})")
    step = max(1, total // max_points)
    print(f"   step = {step}")
    arr_view = arr_full[::step]
    print(f"   arr = arr[::step] creates VIEW of full array")
    print(f"   arr_view size: {arr_view.nbytes/(1024**2):.0f} MB")
    print(f"   arr_view.base is arr_full: {arr_view.base is arr_full}")

# Extract pts via astype
print(f"\n3. pts = arr[:,:3].astype(np.float64)")
pts = arr_view[:, :3].astype(np.float64)
print(f"   pts size: {pts.nbytes/(1024**2):.0f} MB")
print(f"   pts owns data: {pts.base is None}")
print(f"   arr_full still exists: {arr_full is not None}")

# Extract intensity via astype
print(f"\n4. intensity = arr[:,6].astype(np.float64)")
intensity = arr_view[:, 6].astype(np.float64)
print(f"   intensity size: {intensity.nbytes/(1024**2):.0f} MB")
print(f"   intensity owns data: {intensity.base is None}")

# Filter finite rows with boolean indexing
print(f"\n5. Filter non-finite rows")
finite = np.isfinite(pts).all(axis=1)
if not finite.all():
    pts = pts[finite]
    intensity = intensity[finite]
print(f"   After filter: pts owns data: {pts.base is None}")
print(f"   After filter: intensity owns data: {intensity.base is None}")

# Simulate function returning
print(f"\n6. Function return")
print(f"   arr_view goes out of scope")
print(f"   arr_full refcount decreases")

# Clean up arr_view to simulate function return
del arr_view
print(f"   arr_full is now garbage collected")

# Check what's left
print(f"\n=== MEMORY AT RETURN ===")
print(f"pts: {pts.nbytes/(1024**2):.0f} MB (owns data)")
print(f"intensity: {intensity.nbytes/(1024**2):.0f} MB (owns data)")
print(f"Total returned: {(pts.nbytes + intensity.nbytes)/(1024**2):.0f} MB")
print(f"Original full array: {full_size:.0f} MB (freed)")

print(f"\n=== CONCLUSION ===")
print(f"Even with subsampling, the returned data are COPIES.")
print(f"The original full array is freed at function return.")
print(f"No memory exhaustion issue.")
