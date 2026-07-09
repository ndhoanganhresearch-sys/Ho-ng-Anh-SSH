#!/usr/bin/env python3
"""Trace memory at each step of laspy.read()."""
import tracemalloc
import laspy
import numpy as np
from pathlib import Path

test_file = 'data/T0/rec-1-2_1.las'
print(f"File: {test_file} ({Path(test_file).stat().st_size / 1e9:.2f} GB)")

tracemalloc.start()

# STEP 1: laspy.read() - the claim is this loads entire file
print("\n[STEP 1] Calling laspy.read()...")
snapshot1 = tracemalloc.take_snapshot()

las = laspy.read(test_file)

snapshot2 = tracemalloc.take_snapshot()
current_mem, peak_mem = tracemalloc.get_traced_memory()
delta = [(s.size_diff / 1e6) for s in snapshot2.compare_to(snapshot1, 'lineno') if s.size_diff > 0]
print(f"  Memory after laspy.read(): {current_mem / 1e9:.2f} GB peak {peak_mem / 1e9:.2f} GB")
print(f"  Top allocations (MiB): {delta[:3]}")

# STEP 2: Check what we got
print(f"\n[STEP 2] Inspecting las object...")
print(f"  Type: {type(las)}")
print(f"  len(las.x): {len(las.x)}")
print(f"  Type of las.x: {type(las.x)}")

# STEP 3: Now index it (the claim says subsample happens AFTER full load)
print(f"\n[STEP 3] Creating subsample index...")
step = max(1, len(las.x) // 5_000_000)
idx = np.arange(0, len(las.x), step)
print(f"  Step: {step}, Index length: {len(idx)}")

snapshot3 = tracemalloc.take_snapshot()
print(f"  Memory after indexing: {tracemalloc.get_traced_memory()[0] / 1e9:.2f} GB")

# STEP 4: Now subsample (lines 30-35 of io_layer.py)
print(f"\n[STEP 4] Subsampling arrays via indexing...")
x = np.asarray(las.x)[idx]
y = np.asarray(las.y)[idx]
z = np.asarray(las.z)[idx]

snapshot4 = tracemalloc.take_snapshot()
print(f"  Memory after subsampling: {tracemalloc.get_traced_memory()[0] / 1e9:.2f} GB")
print(f"  Final x shape: {x.shape}, dtype: {x.dtype}")

# Show all the top memory consumers
current, peak = tracemalloc.get_traced_memory()
print(f"\n[FINAL] Memory usage:")
print(f"  Current: {current / 1e9:.2f} GB")
print(f"  Peak: {peak / 1e9:.2f} GB")
