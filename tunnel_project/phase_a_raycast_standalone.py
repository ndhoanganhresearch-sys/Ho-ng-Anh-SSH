"""
Phase A Standalone: Raycast Clean Tunnel (T0)
No Blender required - just Python + pre-saved Blender data
"""

import json
import os
import random
import laspy
from mathutils.bvhtree import BVHTree
from mathutils import Vector
import bmesh
import bpy

print("\n" + "=" * 70)
print("PHASE A: RAYCAST CLEAN TUNNEL REFERENCE (T0)")
print("=" * 70)

# Config
BLENDER_FILE = r"data\blender_lidar_t0t5\tunnel_lidar_scene.blend"
OUTPUT_DIR = r"data\blender_lidar_t0t5"
TUNNEL_LINING = "Tunnel_Lining"
SCANNER_LOCATION = Vector([0, 10, 3])
NOISE_BASE_MM = 5
NOISE_SLOPE = 2

os.makedirs(OUTPUT_DIR, exist_ok=True)

# === STEP 1: Load Blender file ===
print("\n[1/4] Loading Blender file...")
try:
    bpy.ops.wm.open_mainfile(filepath=BLENDER_FILE)
    print(f"  ✓ Opened: {BLENDER_FILE}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    exit(1)

# === STEP 2: Create scanner sphere ===
print("\n[2/4] Creating scanner sphere...")
try:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=SCANNER_LOCATION)
    scanner = bpy.context.active_object
    scanner.name = "Scanner_Raycast"

    ray_count = len(scanner.data.vertices)
    print(f"  ✓ Scanner: {scanner.name}")
    print(f"    Location: {tuple(SCANNER_LOCATION)}")
    print(f"    Rays: {ray_count}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    exit(1)

# === STEP 3: Raycast ===
print("\n[3/4] Raycasting to tunnel lining...")
try:
    tunnel = bpy.data.objects.get(TUNNEL_LINING)
    if not tunnel:
        print(f"  ✗ {TUNNEL_LINING} not found!")
        exit(1)

    print(f"    Target: {tunnel.name}")
    print(f"    Vertices: {len(tunnel.data.vertices)}")

    # Get evaluated mesh
    depsgraph = bpy.context.evaluated_depsgraph_get()
    tunnel_eval = tunnel.evaluated_get(depsgraph)

    # Create BVH tree
    bm = bmesh.new()
    bm.from_mesh(tunnel_eval.data)
    bvh = BVHTree.FromBMesh(bm)

    # Raycast
    points_hit = []
    points_distance = []
    hit_count = 0

    for v in scanner.data.vertices:
        world_pos = scanner.matrix_world @ v.co
        direction = (world_pos - SCANNER_LOCATION).normalized()

        hit_loc, _, _, hit_dist = bvh.ray_cast(world_pos, direction)

        if hit_loc:
            hit_count += 1
            noise_mm = NOISE_BASE_MM + (hit_dist / 10.0) * NOISE_SLOPE
            noise_m = noise_mm / 1000.0

            noise_vec = Vector([
                random.gauss(0, noise_m),
                random.gauss(0, noise_m),
                random.gauss(0, noise_m)
            ])

            noisy_point = hit_loc + noise_vec
            points_hit.append(noisy_point)
            points_distance.append(hit_dist)

    bm.free()

    print(f"  ✓ Raycast complete!")
    print(f"    Rays cast: {ray_count}")
    print(f"    Hits: {hit_count} ({100*hit_count/ray_count:.1f}%)")
    print(f"    Distance: {min(points_distance):.3f}m - {max(points_distance):.3f}m")
    print(f"    Noise: {NOISE_BASE_MM}mm + {NOISE_SLOPE}mm per 10m")

except Exception as e:
    print(f"  ✗ Error during raycasting: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# === STEP 4: Export LAS ===
print("\n[4/4] Exporting to LAS format...")
try:
    las = laspy.create()
    las.x = [p[0] for p in points_hit]
    las.y = [p[1] for p in points_hit]
    las.z = [p[2] for p in points_hit]

    las_path = os.path.join(OUTPUT_DIR, "T0.las")
    las.write(las_path)

    print(f"  ✓ LAS file created: T0.las")
    print(f"    Points: {len(points_hit)}")
    print(f"    X: {min(p[0] for p in points_hit):.3f} to {max(p[0] for p in points_hit):.3f} m")
    print(f"    Y: {min(p[1] for p in points_hit):.3f} to {max(p[1] for p in points_hit):.3f} m")
    print(f"    Z: {min(p[2] for p in points_hit):.3f} to {max(p[2] for p in points_hit):.3f} m")

    # Save metadata
    metadata = {
        "source": "raycasting_TLSynth_protocol_phase_a",
        "mesh_source": "tunnel_lidar_scene.blend (clean)",
        "scanner_location": list(SCANNER_LOCATION),
        "noise_model": f"{NOISE_BASE_MM}mm + {NOISE_SLOPE}mm per 10m",
        "point_count": len(points_hit),
        "radius_design": 3.0,
        "deformation_prescribed": "none (reference)",
        "registration_status": "identity",
        "created_date": "2026-06-23",
        "validated": False
    }

    json_path = os.path.join(OUTPUT_DIR, "T0.json")
    with open(json_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"  ✓ Metadata saved: T0.json")

except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 70)
print("PHASE A COMPLETE!")
print("=" * 70)
print(f"\nOutput files created:")
print(f"  ✓ {os.path.join(OUTPUT_DIR, 'T0.las')}")
print(f"  ✓ {os.path.join(OUTPUT_DIR, 'T0.json')}")
print(f"\nNext: Phase B - Inject deformation")
print("=" * 70 + "\n")
