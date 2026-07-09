#!/usr/bin/env python3
"""Test actual memory behavior of _read_las with largest real file."""
import sys
import tracemalloc
from pathlib import Path

# Use the actual module
sys.path.insert(0, str(Path(__file__).parent))

from tunnel_analysis.io_layer import _read_las

# Monitor memory
tracemalloc.start()

# Test with the largest file in the project: 8M points
test_file = 'data/T0/rec-1-2_1.las'
print(f"Testing _read_las() with {test_file}")
print(f"File size: {Path(test_file).stat().st_size / 1e9:.2f} GB")

snapshot_before = tracemalloc.take_snapshot()

try:
    bundle = _read_las(test_file, max_points=5_000_000)
    print(f"\nBundle loaded:")
    print(f"  Original count: {bundle.metadata['original_count']:,}")
    print(f"  Final count: {bundle.metadata['point_count']:,}")
    print(f"  Subsampled: {bundle.metadata['subsampled']}")
    print(f"  Subsample step: {bundle.metadata['subsample_step']}")

except Exception as e:
    print(f"\nERROR during load: {e}")
    traceback.print_exc()

snapshot_after = tracemalloc.take_snapshot()

# Show memory delta
top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')
print("\n" + "=" * 70)
print("TOP MEMORY CHANGES during _read_las():")
print("=" * 70)
for stat in top_stats[:10]:
    print(stat)

current, peak = tracemalloc.get_traced_memory()
print(f"\nCurrent memory: {current / 1e9:.2f} GB")
print(f"Peak memory: {peak / 1e9:.2f} GB")
