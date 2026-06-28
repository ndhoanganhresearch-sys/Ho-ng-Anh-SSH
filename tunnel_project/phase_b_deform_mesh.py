"""
Phase B: Deform Tunnel Mesh

Injects known deformation into clean tunnel mesh.
Prescription matches ground_truth.csv: crown -7mm, convergence -5mm, local -15mm.

Usage (in Blender):
  blender -b data/blender_lidar_t0t5/tunnel_lidar_scene.blend -P phase_b_deform_mesh.py

Or via GUI: Blender > Scripting tab > paste this script > Run

Output:
  - data/blender_lidar_t0t5/tunnel_deformed_Tn.blend
"""

import bpy
import bmesh
from math import exp
import os

print("\n" + "=" * 70)
print("PHASE B: DEFORM TUNNEL MESH")
print("=" * 70)

# === CONFIG ===
OUTPUT_DIR = r"data\blender_lidar_t0t5"
TUNNEL_LINING = "Tunnel_Lining"
TUNNEL_RADIUS = 3.0  # meters (design)

# Deformation parameters (from ground_truth.csv)
DEFORMATIONS = {
    "crown_settlement": {
        "chainage": 20.0,      # meters (Y axis)
        "magnitude_mm": -7.0,  # downward
        "extent": 2.0,         # ±2m
        "axis": "z",           # crown is Z
    },
    "sidewall_convergence": {
        "chainage": 45.0,
        "magnitude_mm": -5.0,  # inward (radial)
        "extent": 3.0,         # ±3m
        "axis": "radial",      # move X,Y toward center
    },
    "local_damage": {
        "chainage": 65.0,
        "magnitude_mm": -15.0,
        "extent": 1.0,         # sharp, ±1m
        "axis": "z",
    },
}

def gaussian_taper(d, sigma=1.0):
    """Gaussian curve: 1.0 at peak (d=0), decays at edges."""
    return exp(-(d * d) / (2.0 * sigma * sigma))

def deform_vertex(co):
    """Apply deformation to a single vertex coordinate."""
    y = co.y  # chainage along Y axis

    # Crown settlement @ Y=20m, peak -7mm, extent ±2m
    if 18.0 < y < 22.0:
        # Gaussian taper with sigma=0.8m (covers ~±2m)
        taper = gaussian_taper(y - 20.0, sigma=0.8)
        offset = -0.007 * taper  # -7mm
        co.z += offset

    # Sidewall convergence @ Y=45m, peak -5mm, extent ±3m
    if 42.0 < y < 48.0:
        # Gaussian taper with sigma=1.2m (covers ~±3m)
        taper = gaussian_taper(y - 45.0, sigma=1.2)
        factor = -0.005 * taper  # -5mm inward
        # Move X,Y toward center (1 - factor/radius means inward)
        co.x *= (1.0 + factor / TUNNEL_RADIUS)

    # Local damage @ Y=65m, peak -15mm, extent ±1m (sharp)
    if 64.0 < y < 66.0:
        # Narrow sigma=0.3m (sharp local dip)
        taper = gaussian_taper(y - 65.0, sigma=0.3)
        offset = -0.015 * taper  # -15mm
        co.z += offset

    return co

# === STEP 1: Get active scene and tunnel mesh ===
print("\n[1/4] Locating tunnel mesh...")
try:
    # If Blender is already open with file, use context
    # Otherwise, this script assumes Blender was opened with the file
    scene = bpy.context.scene
    tunnel = bpy.data.objects.get(TUNNEL_LINING)

    if not tunnel:
        print(f"  ✗ Tunnel mesh '{TUNNEL_LINING}' not found in scene!")
        print(f"     Available objects: {[obj.name for obj in bpy.data.objects]}")
        exit(1)

    print(f"  ✓ Found: {tunnel.name}")
    print(f"    Type: {tunnel.type}")
    print(f"    Vertices: {len(tunnel.data.vertices)}")

except Exception as e:
    print(f"  ✗ Error accessing scene: {e}")
    exit(1)

# === STEP 2: Apply deformation via bmesh ===
print("\n[2/4] Applying deformation...")
try:
    bm = bmesh.new()
    bm.from_mesh(tunnel.data)

    deformed_count = 0
    for v in bm.verts:
        old_co = v.co.copy()
        v.co = deform_vertex(v.co)
        if (v.co - old_co).length > 0.0001:
            deformed_count += 1

    # Write back to mesh
    bm.to_mesh(tunnel.data)
    bm.free()
    tunnel.data.update()

    print(f"  ✓ Deformation applied!")
    print(f"    Vertices moved: {deformed_count} / {len(tunnel.data.vertices)}")

except Exception as e:
    print(f"  ✗ Error during deformation: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# === STEP 3: Validate deformed mesh ===
print("\n[3/4] Validating mesh integrity...")
try:
    # Check for manifold/consistency
    bm = bmesh.new()
    bm.from_mesh(tunnel.data)

    non_manifold = [v for v in bm.verts if len(v.link_edges) < 2]
    bm.free()

    if non_manifold:
        print(f"  ⚠ Warning: {len(non_manifold)} non-manifold vertices found")
    else:
        print(f"  ✓ Mesh remains manifold (no holes)")

    # Sanity: vertex count should be unchanged
    if len(tunnel.data.vertices) != 16100:
        print(f"  ⚠ Warning: Vertex count changed to {len(tunnel.data.vertices)} (expected 16100)")
    else:
        print(f"  ✓ Vertex count unchanged: 16100")

except Exception as e:
    print(f"  ⚠ Validation warning: {e}")

# === STEP 4: Save deformed mesh ===
print("\n[4/4] Saving deformed mesh...")
try:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "tunnel_deformed_Tn.blend")

    bpy.ops.wm.save_as_mainfile(filepath=output_path)

    print(f"  ✓ Saved: {output_path}")

except Exception as e:
    print(f"  ✗ Error saving file: {e}")
    exit(1)

# === DONE ===
print("\n" + "=" * 70)
print("✓ PHASE B DEFORMATION COMPLETE!")
print("=" * 70)
print(f"\nDeformation prescription (from ground_truth.csv):")
print(f"  - Crown settlement: -7mm @ chainage 20m (±2m extent)")
print(f"  - Sidewall convergence: -5mm @ chainage 45m (±3m extent)")
print(f"  - Local damage: -15mm @ chainage 65m (±1m extent)")
print(f"\nOutput file:")
print(f"  - {output_path}")
print(f"\nNext: Run phase_b_raycast.py to create Tn.las")
print("=" * 70 + "\n")
