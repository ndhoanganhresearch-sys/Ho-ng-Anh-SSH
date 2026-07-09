"""Convert sampled epoch point clouds (local coords, identity-registered) to LAS."""
import os
import numpy as np
import laspy

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "las_export")
EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]

for ep in EPOCHS:
    pts = np.load(os.path.join(SRC, f"{ep}.npy")).astype(np.float64)
    header = laspy.LasHeader(point_format=3, version="1.4")
    header.scales = np.array([0.0001, 0.0001, 0.0001])  # 0.1 mm precision
    header.offsets = pts.min(axis=0)
    las = laspy.LasData(header)
    las.x = pts[:, 0]
    las.y = pts[:, 1]
    las.z = pts[:, 2]
    out = os.path.join(SRC, f"{ep}.las")
    las.write(out)
    print(f"{ep}.las  n={len(pts)}  "
          f"X[{pts[:,0].min():.3f},{pts[:,0].max():.3f}] "
          f"Y[{pts[:,1].min():.2f},{pts[:,1].max():.2f}] "
          f"Z[{pts[:,2].min():.3f},{pts[:,2].max():.3f}]")

print("LAS export done ->", SRC)
