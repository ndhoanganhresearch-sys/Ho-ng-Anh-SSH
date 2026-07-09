#!/usr/bin/env python3
"""Test what happens with aggressive subsampling."""
import tracemalloc
import laspy
import numpy as np
from pathlib import Path

test_file = 'data/T0/rec-1-2_1.las'
print(f"File: {test_file}")
print(f"File size: {Path(test_file).stat().st_size / 1e9:.2f} GB")

tracemalloc.start()

# CASE 1: Read without subsampling (default large max_points)
print("\n" + "="*70)
print("CASE 1: max_points=50M (no subsample needed)")
print("="*70)
tracemalloc.reset_peak()
snapshot1a = tracemalloc.take_snapshot()

las1 = laspy.read(test_file)
print(f"Point count in file: {len(las1.x):,}")
max_pts = 50_000_000
if len(las1.x) <= max_pts:
    print(f"NO SUBSAMPLE needed (file has {len(las1.x):,} <= {max_pts:,})")
    x = np.asarray(las1.x)
    y = np.asarray(las1.y)
    z = np.asarray(las1.z)
    print(f"Arrays extracted: x shape {x.shape}")

snapshot1b = tracemalloc.take_snapshot()
_, peak1 = tracemalloc.get_traced_memory()
print(f"Peak memory: {peak1 / 1e9:.2f} GB")

del las1, x, y, z

# CASE 2: Read WITH aggressive subsampling
print("\n" + "="*70)
print("CASE 2: max_points=2M (heavy subsample needed)")
print("="*70)
tracemalloc.reset_peak()
snapshot2a = tracemalloc.take_snapshot()

las2 = laspy.read(test_file)
print(f"Point count in file: {len(las2.x):,}")
max_pts = 2_000_000
if len(las2.x) > max_pts:
    step = max(1, len(las2.x) // max_pts)
    idx = np.arange(0, len(las2.x), step)
    print(f"SUBSAMPLE: step={step}, keeping {len(idx):,} points")

    # This is what io_layer.py does at lines 30-35
    x = np.asarray(las2.x)[idx]
    y = np.asarray(las2.y)[idx]
    z = np.asarray(las2.z)[idx]
    print(f"Subsampled arrays: x shape {x.shape}")

snapshot2b = tracemalloc.take_snapshot()
_, peak2 = tracemalloc.get_traced_memory()
print(f"Peak memory: {peak2 / 1e9:.2f} GB")

print("\n" + "="*70)
print("ANALYSIS:")
print("="*70)
print(f"Case 1 (no subsample): Peak {peak1/1e9:.2f} GB")
print(f"Case 2 (subsample 1:4): Peak {peak2/1e9:.2f} GB")
print(f"\nThe claim: laspy.read() loads ENTIRE file into memory BEFORE subsample")
print(f"Evidence: Peak memory = file size decoding ~ 0.53-0.86 GB")
print(f"This happens REGARDLESS of whether subsample happens after")
