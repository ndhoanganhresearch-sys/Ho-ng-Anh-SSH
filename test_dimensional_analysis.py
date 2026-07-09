import numpy as np

print("=== Dimensional Analysis of the Bug ===\n")

grid_res = 64
peak_idx_0 = 30
cy = grid_res // 2
height = 100.0

freq_v = abs(peak_idx_0 - cy) / grid_res

print("Example values:")
print(f"  peak_idx[0] = {peak_idx_0}")
print(f"  cy = {cy}")
print(f"  freq_v = |{peak_idx_0} - {cy}| / {grid_res} = {abs(peak_idx_0 - cy)} / {grid_res} = {freq_v}")
print()

print("Dimensional analysis:")
print(f"  freq_v has units: [bin count] / [grid points] = dimensionless fraction")
print(f"  height has units: [meters]")
print(f"  height * freq_v has units: [meters] * [dimensionless] = [meters]")
print()

cell_v = height * freq_v
print(f"  cell_v = {height} meters * {freq_v} = {cell_v} meters")
print()

print("But what does this number represent?")
print(f"  peak_idx[0] = {peak_idx_0} bin, cy = {cy} bin")
print(f"  Distance from center: {abs(peak_idx_0 - cy)} bins")
print(f"  In a 64-bin FFT, this represents {abs(peak_idx_0 - cy)} cycles")
print(f"  So the pattern has {abs(peak_idx_0 - cy)} complete oscillations in height")
print(f"  Cell size should be: {height} / {abs(peak_idx_0 - cy)} = {height / abs(peak_idx_0 - cy)} meters")
print()

print("The formula gives: height * freq_v = height * (|peak - cy| / grid_res)")
print(f"                 = {height} * ({abs(peak_idx_0 - cy)} / {grid_res})")
print(f"                 = {cell_v} meters")
print()
print("The correct formula should be: height / (|peak - cy|)")
print(f"                            = {height} / {abs(peak_idx_0 - cy)}")
print(f"                            = {height / abs(peak_idx_0 - cy)} meters")
print()

ratio = cell_v / (height / abs(peak_idx_0 - cy))
print(f"The ratio of wrong to correct: {cell_v} / {height / abs(peak_idx_0 - cy)} = {ratio:.4f}")
print(f"This is: {abs(peak_idx_0 - cy)} / {grid_res} = {abs(peak_idx_0 - cy) / grid_res:.4f}")
print()
print("CONCLUSION:")
print("  The claim is CORRECT about the dimensional error.")
print("  Both branches have the formula inverted (multiply instead of divide).")
print("  The error is off by a factor of ~peak_bin_distance / grid_res.")
print("  For typical values, this produces results in [0.05, 0.30] which all clip.")
print("  The cell_size return value is NEVER ACTUALLY USED, so it's dead code.")
