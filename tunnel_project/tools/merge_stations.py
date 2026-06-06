"""merge_stations.py - Concatenate already-coregistered station/channel scans.

STSD and FY387 station files are already in a common global coordinate frame
(overlapping, continuous coordinates), so they do NOT need ICP registration -
they only need to be stitched together. This tool loads every channel file of a
group, voxel-downsamples each to bound memory/size, concatenates them into a
single uniform cloud, and writes one file ready to load in the GUI (step 1.1).

Usage:
    python merge_stations.py <folder> <prefix> <out_path> [voxel_m]

Examples:
    # STSD circular tunnel (round-1-12_1..4.las) -> one merged .las
    python merge_stations.py "F:\\data mẫu\\STSD v 1.1\\las" round-1-12 merged_round.las 0.03
    # STSD box tunnel
    python merge_stations.py "F:\\data mẫu\\STSD v 1.1\\las" rec-1-13 merged_rec.las 0.03
    # FY387 txt group
    python merge_stations.py "F:\\data mẫu\\FY387\\dataset1_robot_TLS\\raw" t2 merged_t2.las 0.02
"""
import os
import sys
import glob
import numpy as np


def _voxel_downsample_idx(xyz, voxel):
    """Return indices of one representative point per occupied voxel."""
    keys = np.floor(xyz / voxel).astype(np.int64)
    # unique rows -> first occurrence index
    _, idx = np.unique(keys, axis=0, return_index=True)
    return np.sort(idx)


def load_one(path):
    """Load XYZ (+ intensity, classification if present) from .las/.laz/.txt."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".las", ".laz"):
        import laspy
        las = laspy.read(path)
        xyz = np.vstack([las.x, las.y, las.z]).T.astype(np.float64)
        inten = np.asarray(las.intensity, float) if "intensity" in las.point_format.dimension_names else None
        cls = np.asarray(las.classification, float) if "classification" in las.point_format.dimension_names else None
        return xyz, inten, cls
    # txt: X Y Z [nx ny nz] [intensity] [label]
    arr = np.loadtxt(path)
    xyz = arr[:, :3].astype(np.float64)
    inten = arr[:, 6] if arr.shape[1] >= 7 else None
    cls = arr[:, 7] if arr.shape[1] >= 8 else None
    return xyz, inten, cls


def main():
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(1)
    folder, prefix, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    voxel = float(sys.argv[4]) if len(sys.argv) > 4 else 0.03

    pats = sorted(glob.glob(os.path.join(folder, f"{prefix}_*.las")) +
                  glob.glob(os.path.join(folder, f"{prefix}_*.laz")) +
                  glob.glob(os.path.join(folder, f"{prefix}_*.txt")))
    if not pats:
        print(f"No files matching {prefix}_* in {folder}"); sys.exit(1)
    print(f"Found {len(pats)} channel files for group '{prefix}':")
    for p in pats:
        print("   ", os.path.basename(p))

    all_xyz, all_i, all_c = [], [], []
    have_i, have_c = True, True
    for p in pats:
        xyz, inten, cls = load_one(p)
        keep = _voxel_downsample_idx(xyz, voxel)
        all_xyz.append(xyz[keep])
        all_i.append(inten[keep] if inten is not None else None)
        all_c.append(cls[keep] if cls is not None else None)
        have_i = have_i and inten is not None
        have_c = have_c and cls is not None
        print(f"   {os.path.basename(p)}: {len(xyz):,} -> {len(keep):,} pts (voxel {voxel} m)")

    xyz = np.vstack(all_xyz)
    print(f"\nMerged: {len(xyz):,} points")
    print(f"  bbox X[{xyz[:,0].min():.2f},{xyz[:,0].max():.2f}] "
          f"Y[{xyz[:,1].min():.2f},{xyz[:,1].max():.2f}] "
          f"Z[{xyz[:,2].min():.2f},{xyz[:,2].max():.2f}]")

    import laspy
    hdr = laspy.LasHeader(point_format=3)
    hdr.offsets = xyz.min(axis=0)
    hdr.scales = np.array([0.001, 0.001, 0.001])
    las = laspy.LasData(hdr)
    las.x, las.y, las.z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    if have_i:
        inten = np.concatenate([a for a in all_i])
        las.intensity = np.clip(inten, 0, 65535).astype(np.uint16)
    if have_c:
        cls = np.concatenate([a for a in all_c])
        las.classification = np.clip(cls, 0, 31).astype(np.uint8)
    las.write(out_path)
    print(f"\n[OK] Wrote {out_path}  ({len(xyz):,} pts)")
    print("Load this single file in the GUI via '1.1 Import LAS/PLY data'.")


if __name__ == "__main__":
    main()
