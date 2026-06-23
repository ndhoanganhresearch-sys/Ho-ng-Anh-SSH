import laspy

# Load and verify the synthetic LAS file
las_path = r"data\blender_lidar_t0t5\tunnel_synthetic_raycast.las"
las = laspy.read(las_path)

print(f"Synthetic LAS verification:")
print(f"  Points: {len(las.points)}")
print(f"  X range: {las.x.min():.3f} to {las.x.max():.3f} m")
print(f"  Y range: {las.y.min():.3f} to {las.y.max():.3f} m")
print(f"  Z range: {las.z.min():.3f} to {las.z.max():.3f} m")
print(f"  File: {las_path}")
print()
print("Ready to test with tunnel_analysis tool!")
