"""
Phase A: Raycast Clean Tunnel Reference (T0)

Creates T0.las - baseline point cloud from clean tunnel mesh.
Applies TLSynth methodology with distance-dependent noise.

Usage:
  python phase_a_raycast.py

Output:
  - data/blender_lidar_t0t5/T0.las (364 points)
  - data/blender_lidar_t0t5/T0.json (metadata)
"""

import bpy
import bmesh
import json
import os
from mathutils.bvhtree import BVHTree
from mathutils import Vector
import random

print("\n" + "=" * 70)
print("PHASE A: RAYCAST CLEAN TUNNEL REFERENCE (T0)")
print("=" * 70)

# === CONFIG ===
BLENDER_FILE = r"data\blender_lidar_t0t5\tunnel_lidar_scene.blend"
OUTPUT_DIR = r"data\blender_lidar_t0t5"
TUNNEL_LINING = "Tunnel_Lining"
SCANNER_LOCATION = Vector([0, 10, 3])  # meters
SCANNER_RADIUS = 0.1  # meters
SPHERE_SUBDIVISIONS = (32, 16)  # lat x lon = ~512 rays

# Noise model (TLSynth §3.2)
NOISE_BASE_MM = 5  # baseline 5mm
NOISE_SLOPE = 2    # 2mm per 10m distance

os.makedirs(OUTPUT_DIR, exist_ok=True)

# === STEP 1: Load Blender file ===
print("\n[1/4] Loading Blender scene...")
try:
    bpy.ops.wm.open_mainfile(filepath=BLENDER_FILE)
    print(f"  ✓ Loaded: {BLENDER_FILE}")
except Exception as e:
    print(f"  ✗ Error loading file: {e}")
    exit(1)

# === STEP 2: Create scanner sphere ===
print("\n[2/4] Setting up scanner sphere...")
try:
    # Create UV sphere
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=SCANNER_RADIUS,
        location=SCANNER_LOCATION
    )
    scanner = bpy.context.active_object
    scanner.name = "Scanner_Raycast"

    # Count rays (vertices)
    ray_count = len(scanner.data.vertices)
    print(f"  ✓ Scanner created: {scanner.name}")
    print(f"    Location: {tuple(SCANNER_LOCATION)}")
    print(f"    Rays (vertices): {ray_count}")
except Exception as e:
    print(f"  ✗ Error creating scanner: {e}")
    exit(1)

# === STEP 3: Raycast to tunnel ===
print("\n[3/4] Raycasting to tunnel lining...")
try:
    # Get tunnel mesh
    tunnel = bpy.data.objects.get(TUNNEL_LINING)
    if not tunnel:
        print(f"  ✗ Tunnel mesh '{TUNNEL_LINING}' not found!")
        exit(1)

    print(f"    Target: {tunnel.name}")
    print(f"    Vertices: {len(tunnel.data.vertices)}")

    # Get evaluated mesh for raycasting
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
        # World position
        world_pos = scanner.matrix_world @ v.co

        # Ray direction: outward from scanner center
        direction = (world_pos - SCANNER_LOCATION).normalized()

        # Raycast
        hit_loc, hit_norm, hit_idx, hit_dist = bvh.ray_cast(world_pos, direction)

        if hit_loc:
            hit_count += 1

            # Add distance-dependent noise (TLSynth §3.2)
            noise_mm = NOISE_BASE_MM + (hit_dist / 10.0) * NOISE_SLOPE
            noise_m = noise_mm / 1000.0

            # Gaussian noise
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
    if points_distance:
        print(f"    Distance range: {min(points_distance):.3f}m - {max(points_distance):.3f}m")
    print(f"    Noise applied: {NOISE_BASE_MM}mm + {NOISE_SLOPE}mm per 10m")

except Exception as e:
    print(f"  ✗ Error during raycasting: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# === STEP 4: Export to LAS ===
print("\n[4/4] Exporting to LAS format...")
try:
    import laspy

    # Create LAS file
    las = laspy.create()
    las.x = [p[0] for p in points_hit]
    las.y = [p[1] for p in points_hit]
    las.z = [p[2] for p in points_hit]

    # Write
    las_path = os.path.join(OUTPUT_DIR, "T0.las")
    las.write(las_path)

    print(f"  ✓ LAS file created!")
    print(f"    Path: {las_path}")
    print(f"    Points: {len(points_hit)}")
    print(f"    X: {min(p[0] for p in points_hit):.3f} to {max(p[0] for p in points_hit):.3f} m")
    print(f"    Y: {min(p[1] for p in points_hit):.3f} to {max(p[1] for p in points_hit):.3f} m")
    print(f"    Z: {min(p[2] for p in points_hit):.3f} to {max(p[2] for p in points_hit):.3f} m")

    # Save metadata
    metadata = {
        "source": "raycasting_TLSynth_protocol_phase_a",
        "mesh_source": "tunnel_lidar_scene.blend (clean)",
        "scanner_location": list(SCANNER_LOCATION),
        "scanner_sphere_subdivisions": f"{SPHERE_SUBDIVISIONS[0]}x{SPHERE_SUBDIVISIONS[1]}",
        "noise_model": f"{NOISE_BASE_MM}mm + {NOISE_SLOPE}mm per 10m distance",
        "point_count": len(points_hit),
        "radius_design": 3.0,
        "deformation_prescribed": "none (reference)",
        "registration_status": "identity (no transformation)",
        "created_date": "2026-06-23",
        "validated": False
    }

    json_path = os.path.join(OUTPUT_DIR, "T0.json")
    with open(json_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"  ✓ Metadata saved: T0.json")

except ImportError:
    print("  ✗ laspy not found in Blender Python")
    print("     Use tunnel_project Python instead:")
    print("     python convert_raycast_to_las.py")
    exit(1)
except Exception as e:
    print(f"  ✗ Error exporting: {e}")
    exit(1)

# === DONE ===
print("\n" + "=" * 70)
print("✓ PHASE A COMPLETE!")
print("=" * 70)
print(f"\nOutput files:")
print(f"  - {os.path.join(OUTPUT_DIR, 'T0.las')}")
print(f"  - {os.path.join(OUTPUT_DIR, 'T0.json')}")
print(f"\nNext: PHASE B - Inject deformation")
print("=" * 70 + "\n")
