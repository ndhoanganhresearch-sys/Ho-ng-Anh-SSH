import json
import laspy

# Load JSON points from Blender raycast
json_path = r"data\blender_lidar_t0t5\tunnel_synthetic_raycast.json"
with open(json_path) as f:
    data = json.load(f)

points = data["points"]

# Create LAS file
las = laspy.create()
las.x = [p[0] for p in points]
las.y = [p[1] for p in points]
las.z = [p[2] for p in points]

# Write
las_path = json_path.replace(".json", ".las")
las.write(las_path)

print("LAS file created!")
print(f"  Path: {las_path}")
print(f"  Points: {len(points)}")
print(f"  X: {min(p[0] for p in points):.3f} to {max(p[0] for p in points):.3f}")
print(f"  Y: {min(p[1] for p in points):.3f} to {max(p[1] for p in points):.3f}")
print(f"  Z: {min(p[2] for p in points):.3f} to {max(p[2] for p in points):.3f}")
