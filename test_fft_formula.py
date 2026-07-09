import numpy as np

# Simulate a simple checkerboard pattern to test the FFT cell size formula
print("=== FFT Cell Size Formula Analysis ===\n")

# Test case 1: Perfect horizontal checkerboard (4x4 cells)
print("Test 1: Horizontal checkerboard (4 cells across)")
grid_res = 64
grid = np.zeros((grid_res, grid_res))

# Create 4 horizontal stripes
cells_u = 4  # 4 cells across width
stripe_width = grid_res // cells_u
for i in range(grid_res):
    for j in range(grid_res):
        if (j // stripe_width) % 2 == 0:
            grid[i, j] = 1.0

# Compute FFT
fft_result = np.abs(np.fft.fft2(grid - 0.5))
fft_shift = np.fft.fftshift(fft_result)
fft_shift[grid_res//2, grid_res//2] = 0  # Remove DC

# Find peak
peak_idx = np.unravel_index(fft_shift.argmax(), fft_shift.shape)
cy, cx = grid_res // 2, grid_res // 2

print(f"Grid shape: {grid_res}x{grid_res}")
print(f"Peak FFT index: row={peak_idx[0]}, col={peak_idx[1]}")
print(f"Center: row={cy}, col={cx}")

freq_u = abs(peak_idx[1] - cx) / grid_res
freq_v = abs(peak_idx[0] - cy) / grid_res
print(f"freq_u (normalized frequency in u-dir): {freq_u:.4f}")
print(f"freq_v (normalized frequency in v-dir): {freq_v:.4f}")
print(f"max(freq_u, freq_v): {max(freq_u, freq_v):.4f}")

# Physical dimensions
width = 100.0  # meters
height = 100.0  # meters
cell_physical = width / cells_u  # Should be 25 m per cell

freq = max(freq_u, freq_v, 1e-6)

# Current formula from code
cell_u_formula = (width * freq) if freq_u > freq_v else (height * freq)
print(f"\nCurrent formula (line 591): cell_size = {cell_u_formula:.6f} m")
print(f"Expected cell size: {cell_physical:.6f} m")
print(f"Error factor: {cell_u_formula / cell_physical:.2f}x")

peak_bin_u = abs(peak_idx[1] - cx)
peak_bin_v = abs(peak_idx[0] - cy)
print(f"\nPeak bin distance from center: u={peak_bin_u}, v={peak_bin_v}")

if peak_bin_u > 0:
    # The peak bin distance tells us the frequency
    # For a 4-cell checkerboard in 64 bins, FFT peak should be at bin 4
    cycles_in_u = peak_bin_u
    cell_correct_u = width / cycles_in_u
    print(f"\nIf peak_bin_u={peak_bin_u} represents {cycles_in_u} cycles per width:")
    print(f"  Correct cell size: cell = width / cycles = {width} / {cycles_in_u} = {cell_correct_u:.6f} m")
    print(f"  Ratio (current/correct): {cell_u_formula / cell_correct_u:.2f}x")

# Now test case 2: Same pattern but rotated (dominant in v direction)
print("\n" + "="*60)
print("Test 2: Vertical checkerboard (4 cells down, dominant freq in v)")
grid2 = np.zeros((grid_res, grid_res))
stripe_height = grid_res // cells_u
for i in range(grid_res):
    for j in range(grid_res):
        if (i // stripe_height) % 2 == 0:
            grid2[i, j] = 1.0

# Compute FFT
fft_result2 = np.abs(np.fft.fft2(grid2 - 0.5))
fft_shift2 = np.fft.fftshift(fft_result2)
fft_shift2[grid_res//2, grid_res//2] = 0  # Remove DC

# Find peak
peak_idx2 = np.unravel_index(fft_shift2.argmax(), fft_shift2.shape)

print(f"Peak FFT index: row={peak_idx2[0]}, col={peak_idx2[1]}")
print(f"Center: row={cy}, col={cx}")

freq_u2 = abs(peak_idx2[1] - cx) / grid_res
freq_v2 = abs(peak_idx2[0] - cy) / grid_res
print(f"freq_u (normalized frequency in u-dir): {freq_u2:.4f}")
print(f"freq_v (normalized frequency in v-dir): {freq_v2:.4f}")

freq2 = max(freq_u2, freq_v2, 1e-6)

# Current formula from code - when freq_v > freq_u, uses height * freq
cell_u_formula2 = (width * freq2) if freq_u2 > freq_v2 else (height * freq2)
print(f"\nCurrent formula (line 591): cell_size = {cell_u_formula2:.6f} m")
print(f"Expected cell size: {cell_physical:.6f} m")
print(f"Error factor: {cell_u_formula2 / cell_physical:.2f}x")

peak_bin_u2 = abs(peak_idx2[1] - cx)
peak_bin_v2 = abs(peak_idx2[0] - cy)
print(f"\nPeak bin distance from center: u={peak_bin_u2}, v={peak_bin_v2}")

# This is the else branch where the claim says there's a bug
if peak_bin_v2 > 0:
    cycles_in_v = peak_bin_v2
    cell_correct_v = height / cycles_in_v
    print(f"\nIf peak_bin_v={peak_bin_v2} represents {cycles_in_v} cycles per height:")
    print(f"  Correct cell size: cell = height / cycles = {height} / {cycles_in_v} = {cell_correct_v:.6f} m")
    print(f"  Ratio (current/correct): {cell_u_formula2 / cell_correct_v:.2f}x")
    print(f"\n*** This is the else-branch that the claim says is BUGGY ***")
    print(f"    Current formula multiplies by freq instead of dividing")
    print(f"    Current gives {cell_u_formula2:.6f}m, should be {cell_correct_v:.6f}m")
