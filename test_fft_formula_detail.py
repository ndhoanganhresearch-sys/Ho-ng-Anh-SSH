import numpy as np

print("=== Detailed FFT Frequency Analysis ===\n")

grid_res = 64
cells_in_domain = 4
width = 100.0

# Create checkerboard
grid = np.zeros((grid_res, grid_res))
stripe_width = grid_res // cells_in_domain
for i in range(grid_res):
    for j in range(grid_res):
        if (j // stripe_width) % 2 == 0:
            grid[i, j] = 1.0

# FFT
fft_result = np.abs(np.fft.fft2(grid - 0.5))
fft_shift = np.fft.fftshift(fft_result)
fft_shift[grid_res//2, grid_res//2] = 0

peak_idx = np.unravel_index(fft_shift.argmax(), fft_shift.shape)
cy, cx = grid_res // 2, grid_res // 2

peak_bin_u = abs(peak_idx[1] - cx)

print(f"Pattern: {cells_in_domain} cells across width={width}m")
print(f"Grid resolution: {grid_res}x{grid_res}")
print(f"Stripe width in grid pixels: {stripe_width}")
print(f"Peak FFT bin distance from center: {peak_bin_u}")

# Physical interpretation
print("\n=== What the FFT peak bin means ===")
print(f"Peak bin {peak_bin_u} in a {grid_res}-point FFT represents")
print(f"a frequency component of {peak_bin_u} cycles across {grid_res} grid points.")
print(f"Scaled to physical: {peak_bin_u} cycles across width={width}m")
print(f"Therefore: cell_size = width / cycles = {width} / {peak_bin_u} = {width/peak_bin_u}m")

print("\n=== What the current formula does ===")
freq_u = peak_bin_u / grid_res  # This is normalized frequency
print(f"freq_u = peak_bin_u / grid_res = {peak_bin_u} / {grid_res} = {freq_u}")
cell_current = width * freq_u
print(f"cell_size = width * freq_u = {width} * {freq_u} = {cell_current}m")

print("\n=== Analysis of the formula ===")
print(f"The issue: freq_u is a normalized frequency (cycles/grid_res)")
print(f"But width is in physical units (meters)")
print(f"Multiplying them gives: meters * (cycles/grid) = meter-cycles/grid")
print(f"This is NOT a cell size!")
print()
print(f"Correct approach:")
print(f"  peak_bin_u = number of complete cycles in the grid")
print(f"  cell_size = width / peak_bin_u")
print()
print(f"Alternative (using normalized freq):")
print(f"  freq_normalized = peak_bin_u / grid_res")
print(f"  cycles_per_meter = freq_normalized * grid_res / width = peak_bin_u / width")
print(f"  cell_size = 1 / cycles_per_meter = width / peak_bin_u")

print("\n=== So is the bug claim correct? ===")
print("The claim says the else-branch uses wrong units/formula.")
print("But our test shows BOTH branches are wrong.")
print("The formula width * freq should be width / peak_bin")
print("or equivalently: width * (grid_res / peak_bin) / grid_res = width / peak_bin")
