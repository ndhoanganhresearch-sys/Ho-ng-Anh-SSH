import numpy as np

print("=== Effect of Clipping on Wrong Formula ===\n")

# Scenario: A 4-cell checkerboard (expecting cell_size = 25m)
# but the formula gives 3.125m before clipping

grid_res = 64
peak_bin = 2  # From our earlier test
width = 100.0
cell_size_range = (0.05, 0.30)

# What the formula produces
freq = peak_bin / grid_res  # 2 / 64 = 0.03125
cell_u = width * freq  # 100 * 0.03125 = 3.125

print(f"Pattern: peak_bin={peak_bin}, width={width}m")
print(f"Frequency (normalized): freq = {peak_bin} / {grid_res} = {freq}")
print(f"Computed cell_u = {width} * {freq} = {cell_u}m")
print(f"Cell size range: {cell_size_range}")
print(f"After clipping: cell_size = np.clip({cell_u}, {cell_size_range[0]}, {cell_size_range[1]})")
cell_clipped = np.clip(cell_u, cell_size_range[0], cell_size_range[1])
print(f"Result: {cell_clipped}m")
print()
print(f"Expected correct cell size: {width / peak_bin}m")
print()
print("PROBLEM: The formula produces 3.125m")
print("         The clipping range is (0.05, 0.30)")
print("         Since 0.05 < 3.125, the value is OUTSIDE the clipping range!")
print(f"         It gets clipped to max: {cell_clipped}m")
print()
print("The claim says: 'always clipped to cell_size_range[1] and therefore useless'")
print(f"Our calculation shows: 3.125m is > 0.30, so yes it clips to 0.30m")
print("But expected was 50m (before any clipping would apply)")
print()
print("Wait, that doesn't match. Let me recalculate...")
print()
print("Actually for the checkerboard with 4 cells in 100m:")
print(f"  Expected: 100m / 4 = 25m per cell")
print(f"  Formula gives: 3.125m")
print(f"  3.125m is within range [0.05, 0.30]? {0.05 <= 3.125 <= 0.30}")
print()
print("Hmm, 3.125 > 0.30, so it WOULD clip to 0.30")
print()
print("Let me try a different grid_res to understand the pattern...")
for test_grid_res in [32, 64, 128]:
    freq_test = peak_bin / test_grid_res
    cell_test = width * freq_test
    clipped = np.clip(cell_test, cell_size_range[0], cell_size_range[1])
    print(f"grid_res={test_grid_res}: freq={freq_test:.6f}, cell_u={cell_test:.6f}, clipped={clipped:.6f}")
