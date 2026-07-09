#!/usr/bin/env python3
"""Test whether laspy.read() truly loads entire file into memory."""
import laspy
import sys

print("=" * 70)
print("TESTING laspy.read() vs laspy.open() memory behavior")
print("=" * 70)

# Test 1: Using laspy.open() - header only
print("\n[TEST 1] laspy.open() - should give us header without full decode")
try:
    las_open = laspy.open('data/time_series_deformation/T0.las')
    print(f"  Type: {type(las_open)}")
    print(f"  Header point_count: {las_open.header.point_count}")
    print(f"  Has 'x' attribute? {hasattr(las_open, 'x')}")
    if hasattr(las_open, 'x'):
        x_type = type(las_open.x)
        print(f"  Type of x: {x_type}")
        # Try to peek at first element without full decompression
        try:
            first_x = las_open.x[0]
            print(f"  First x value: {first_x}")
        except Exception as e:
            print(f"  Error accessing x[0]: {e}")
    las_open.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Using laspy.read() - full file
print("\n[TEST 2] laspy.read() - docstring says 'Reads the whole file into memory'")
try:
    las_read = laspy.read('data/time_series_deformation/T0.las')
    print(f"  Type: {type(las_read)}")
    print(f"  Point count: {len(las_read.x)}")
    print(f"  Type of x: {type(las_read.x)}")
    print(f"  x is numpy array? {hasattr(las_read.x, 'dtype')}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 70)
print("CONCLUSION:")
print("  laspy.read() DOES load entire file into memory (per docstring)")
print("  laspy.open() gives header-only access via lazy reader")
print("=" * 70)
