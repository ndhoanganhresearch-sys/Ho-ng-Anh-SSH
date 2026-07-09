#!/usr/bin/env python3
import laspy

files = [
    'data/T0/rec-1-2_1.las',
    'data/sample_pcd/circle_tunnel_dw.las',
    'data/full_test/T0_full.las',
    'data/time_series_deformation/T0.las',
]

for f in files:
    try:
        las = laspy.open(f)
        count = las.header.point_count
        las.close()
        print(f"{f}: {count:,} points")
    except Exception as e:
        print(f"{f}: ERROR - {e}")
