#!/usr/bin/env python3
"""
Test: Does _read_txt return views that hold references to the full array?
Claim: arr_full is held via arr after subsampling
Reality: All returned data are independent copies via .astype() and boolean indexing
"""
import numpy as np
import tempfile
import os
from tunnel_analysis.io_layer import BaseLayer

# Create test file
temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
try:
    n = 1_000_000
    for i in range(n):
        x, y, z = i, i*2, i*3
        nx, ny, nz = 0.707, 0.707, 0.0
        intensity = 100.0
        temp_file.write(f'{x} {y} {z} {nx} {ny} {nz} {intensity}\n')
    temp_file.close()

    print('Testing _read_txt with subsampling')
    print(f'File has {n} points')
    print()

    layer = BaseLayer()
    bundle = layer.load_scan(temp_file.name, max_points=500_000)

    print('Loaded bundle:')
    print(f'  points size: {bundle.points.nbytes/(1024**2):.1f}MB')
    print(f'  points owns data: {bundle.points.base is None}')
    print(f'  intensity size: {bundle.intensity.nbytes/(1024**2):.1f}MB')
    print(f'  intensity owns data: {bundle.intensity.base is None}')
    print(f'  original count: {bundle.metadata["original_count"]}')
    print(f'  subsampled: {bundle.metadata["subsampled"]}')
    print()

    if bundle.points.base is None and bundle.intensity.base is None:
        print('SUCCESS: All returned arrays own their own data')
        print('No reference to the full array is held')
    else:
        print('FAILURE: Arrays are views of the original')

finally:
    os.unlink(temp_file.name)
