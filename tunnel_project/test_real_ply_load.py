"""
Load real PLY files from the project's test data using the actual io_layer code.
"""

from pathlib import Path
from tunnel_analysis.io_layer import BaseLayer

# Find the real PLY files in the project
data_dir = Path("data/test_pcd")
ply_files = list(data_dir.glob("*.ply"))

print(f"Found {len(ply_files)} PLY files:")
for f in ply_files:
    print(f"  {f}")

loader = BaseLayer()

for ply_file in ply_files[:2]:  # Test first two
    print(f"\nLoading {ply_file}...")
    try:
        bundle = loader.load_scan(str(ply_file))
        print(f"  Success!")
        print(f"  Points: {bundle.points.shape}")
        print(f"  Point count: {bundle.metadata['point_count']}")
        print(f"  Bounds min: {bundle.metadata['bounds_min']}")
        print(f"  Bounds max: {bundle.metadata['bounds_max']}")
        print(f"  First point: {bundle.points[0]}")
        print(f"  Last point: {bundle.points[-1]}")

        # Check for NaN/Inf corruption
        import numpy as np
        non_finite = ~np.isfinite(bundle.points).all(axis=1)
        if non_finite.any():
            print(f"  WARNING: {non_finite.sum()} non-finite points!")
        else:
            print(f"  All points are finite")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
