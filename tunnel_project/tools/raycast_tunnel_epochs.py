"""
Raycast Tunnel Epochs - Blender LiDAR simulator for the REAL curved tunnel.

Generates a synthetic point cloud for one epoch (T0..T5) by deforming the real
`Tunnel_Lining` mesh (in memory, never saved) and raycasting it from the 3 TLS
stations that the blender_lidar_t0t5 dataset uses. T0 = clean reference.

This is the SINGLE raycast engine for Phase A (clean T0) and Phase B (deformed Tn):
because the same code path and same stations are used for every epoch, the
"scanner must match T0 byte-for-byte" risk is structurally eliminated.

Geometry/model is aligned to data/blender_lidar_t0t5/manifest.json:
  - Curved alignment: centerline cx=R(1-cos(s/R)), cy=R sin(s/R), R=500 m
  - chainage s = arc length along the curve (NOT raw Y)
  - radius ~4.25 m arch; crown direction local +Z (horizontal curve)
  - 3 TLS stations at arc-length 10/40/70 m, tripod z=-1.3 m
  - range noise sigma(d) = 0.002 + 0.00006*d  (manifest scanner.noise_model)
  - deformation specs (chainage/sigma/theta/values per epoch) from manifest

Run INSIDE Blender (needs bpy), e.g.:
  blender -b data/blender_lidar_t0t5/tunnel_lidar_scene.blend ^
          -P tools/raycast_tunnel_epochs.py -- --epoch T5
Or via the Blender MCP bridge (execute_blender_code) with EPOCH set below.

Output (data/blender_lidar_t0t5/):
  - <EPOCH>_raycast.txt   (x y z intensity label)  label 1 = lining
  - <EPOCH>_raycast.json  (metadata + ground-truth prescription)

The on-disk .blend is reopened at the end so the deformation is discarded.
"""

import bpy
import bmesh
import math
import random
import json
import os
import sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
EPOCH = "T5"  # override with `-- --epoch T3`; T0 = clean reference

# Resolve --epoch from CLI args after `--`
if "--" in sys.argv:
    extra = sys.argv[sys.argv.index("--") + 1:]
    if "--epoch" in extra:
        EPOCH = extra[extra.index("--epoch") + 1]

DATA = os.path.join("data", "blender_lidar_t0t5")
BLEND = os.path.join(DATA, "tunnel_lidar_scene.blend")
LINING = "Tunnel_Lining"

R = 500.0                  # horizontal alignment radius (m)
STATION_S = [10.0, 40.0, 70.0]
STATION_Z = -1.3           # tripod height in scene Z
DA = DE = 1.0              # azimuth / elevation step (deg); 0.5 to match dataset density
EL0, EL1 = -25.0, 90.0     # elevation sweep (deg)
MAXR = 60.0                # max range (m)
SEED = 0                   # fixed so T0/Tn share the same ray noise sequence

# Deformation specs (mm), straight from manifest.json deformation_specs.
# Each: chainage_m, sigma_m (Gaussian along arc-length), theta_deg (cross-section
# angle, 90=crown, 0/180=sidewalls), and per-epoch magnitude.
DEFORMATION_SPECS = [
    {"type": "crown_settlement",     "chainage": 20.0, "sigma": 3.0, "theta": 90.0,
     "values": {"T0": 0, "T1": -5, "T2": -12, "T3": -20, "T4": -30, "T5": -45}},
    {"type": "sidewall_convergence", "chainage": 45.0, "sigma": 3.0, "theta": 0.0,
     "values": {"T0": 0, "T1": 0,  "T2": -5,  "T3": -12, "T4": -22, "T5": -35}},
    {"type": "local_damage",         "chainage": 65.0, "sigma": 1.2, "theta": 55.0,
     "values": {"T0": 0, "T1": 0,  "T2": 0,   "T3": -15, "T4": -25, "T5": -40}},
]
LOCAL_ANG_SIGMA_DEG = 15.0  # angular spread of the local-damage patch


def center(s):
    """Centerline point at arc-length s on the horizontal curve (cz = 0)."""
    phi = s / R
    return Vector((R * (1 - math.cos(phi)), R * math.sin(phi), 0.0))


def make_deformer(epoch):
    """Return a function world->world applying this epoch's deformation."""
    crown = next(d for d in DEFORMATION_SPECS if d["type"] == "crown_settlement")
    side = next(d for d in DEFORMATION_SPECS if d["type"] == "sidewall_convergence")
    local = next(d for d in DEFORMATION_SPECS if d["type"] == "local_damage")
    cm = crown["values"][epoch] / 1000.0
    sm = side["values"][epoch] / 1000.0
    lm = local["values"][epoch] / 1000.0
    ang_sigma = math.radians(LOCAL_ANG_SIGMA_DEG)

    def deform(w):
        x, y, z = w.x, w.y, w.z
        s = R * math.asin(max(-1.0, min(1.0, y / R)))   # arc-length from Y
        cx = center(s).x
        lat, up = x - cx, z
        r = math.hypot(lat, up) or 1e-9
        theta = math.atan2(up, lat)
        dx = dz = 0.0
        # crown settlement: down in Z, peaked at crown (sin theta), Gaussian in s
        g = math.exp(-((s - crown["chainage"]) ** 2) / (2 * crown["sigma"] ** 2))
        dz += cm * g * max(0.0, math.sin(theta))
        # sidewall convergence: inward laterally, both walls (|cos theta|)
        g = math.exp(-((s - side["chainage"]) ** 2) / (2 * side["sigma"] ** 2))
        dx += sm * g * abs(math.cos(theta)) * (1.0 if lat >= 0 else -1.0)
        # local damage: radial inward, narrow Gaussian in s and in angle
        g = math.exp(-((s - local["chainage"]) ** 2) / (2 * local["sigma"] ** 2))
        dth = math.radians(math.degrees(theta) - local["theta"])
        wa = math.exp(-(dth ** 2) / (2 * ang_sigma ** 2))
        dx += lm * g * wa * (lat / r)
        dz += lm * g * wa * (up / r)
        return Vector((x + dx, y, z + dz))

    return deform


def lining_bvh(obj):
    """BVHTree (world space) from the object's current mesh data."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()
    return bvh


def raycast(bvh, path):
    stations = [center(s) + Vector((0, 0, STATION_Z)) for s in STATION_S]
    random.seed(SEED)
    hits = 0
    with open(path, "w") as f:
        for st in stations:
            az = 0.0
            while az < 360.0:
                ca, sa = math.cos(math.radians(az)), math.sin(math.radians(az))
                el = EL0
                while el <= EL1:
                    ce, se = math.cos(math.radians(el)), math.sin(math.radians(el))
                    d = Vector((ca * ce, sa * ce, se))
                    loc, nor, idx, dist = bvh.ray_cast(st, d, MAXR)
                    if loc is not None:
                        sigma = 0.002 + 0.00006 * dist
                        loc2 = loc + d * random.gauss(0, sigma)
                        inten = round(max(0.0, min(1.0,
                                   0.5 * abs(nor.dot(d)) * (1.0 / (1.0 + 0.02 * dist)))), 4)
                        f.write("%.6f %.6f %.6f %.4f 1\n" % (loc2.x, loc2.y, loc2.z, inten))
                        hits += 1
                    el += DE
                az += DA
    return hits


def write_metadata(path, epoch, hits):
    prescription = {}
    for d in DEFORMATION_SPECS:
        prescription[d["type"]] = {
            "value_mm": d["values"][epoch],
            "chainage_m": d["chainage"],
            "sigma_m": d["sigma"],
            "theta_deg": d["theta"],
        }
    meta = {
        "source": "raycast_tunnel_epochs (real curved tunnel, BVHTree on Tunnel_Lining)",
        "epoch": epoch,
        "mesh_source": "tunnel_lidar_scene.blend",
        "alignment": "horizontal curve R=%.0f m; chainage = arc length" % R,
        "radius_m": 4.25,
        "stations_arc_length_m": STATION_S,
        "station_z": STATION_Z,
        "ray_grid_deg": {"azimuth_step": DA, "elevation_step": DE, "elevation_range": [EL0, EL1]},
        "noise_model": "sigma_m = 0.002 + 0.00006 * distance_m",
        "point_count": hits,
        "labels": {"1": "tunnel lining"},
        "deformation_prescribed": prescription,
        "ground_truth_file": "ground_truth.csv",
        "registration_status": "identity (same 3 stations for every epoch)",
    }
    with open(path, "w") as f:
        json.dump(meta, f, indent=2)


def main():
    print("\n" + "=" * 70)
    print("RAYCAST TUNNEL EPOCH:", EPOCH)
    print("=" * 70)
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    obj = bpy.data.objects[LINING]

    if EPOCH != "T0":
        deform = make_deformer(EPOCH)
        mw, mwi = obj.matrix_world, obj.matrix_world.inverted()
        moved = 0
        for v in obj.data.vertices:
            w = mw @ v.co
            nw = deform(w)
            if (nw - w).length > 1e-6:
                moved += 1
            v.co = mwi @ nw
        obj.data.update()
        print("  deformed verts:", moved)

    out_txt = os.path.join(DATA, "%s_raycast.txt" % EPOCH)
    out_json = os.path.join(DATA, "%s_raycast.json" % EPOCH)
    hits = raycast(lining_bvh(obj), out_txt)
    write_metadata(out_json, EPOCH, hits)
    print("  hits:", hits)
    print("  ->", out_txt)
    print("  ->", out_json)

    # discard in-memory deformation
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    print("  clean .blend restored")
    print("=" * 70)


main()
