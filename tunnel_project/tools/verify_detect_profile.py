"""Verify detect_profile() against the labelled data/sample_pcd dataset."""
import os
import numpy as np
from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer

BASE = os.path.join(os.path.dirname(__file__), "data", "sample_pcd")
SAMPLES = {
    "circle_tunnel_dw.las":          "Circle",
    "box_tunnel_dw.las":             "Box",
    "box2_tunnel_dw.las":            "Box 2-cell",
    "u-type_tunnel_0k630 cut_1.las": "U-type",
    "u-type_wall_dw.las":            "U-type",
}
MAX_PTS = 300_000


class Ctx:
    centerline = None
    registered_points = None
    frenet_frames = None
    def __init__(self, pts): self._p = pts
    @property
    def working_points(self): return self._p


def load(path):
    import laspy
    las = laspy.read(path)
    pts = np.vstack([las.x, las.y, las.z]).T.astype(np.float64)
    if len(pts) > MAX_PTS:
        idx = np.random.RandomState(0).choice(len(pts), MAX_PTS, replace=False)
        pts = pts[idx]
    return pts


def main():
    g = GeometricLayer(); par = ParameterExtractionLayer()
    ok = 0
    for fname, truth in SAMPLES.items():
        ctx = Ctx(load(os.path.join(BASE, fname)))
        cl, frames = g.extract_centerline(ctx, section_count=80)
        ctx.centerline = cl; ctx.frenet_frames = frames
        pred = par.detect_profile(ctx)
        good = (pred == truth)
        ok += good
        print(f"  {fname:34s} truth={truth:11s} pred={pred:11s} {'OK' if good else 'XX MISMATCH'}")
    print(f"\n{ok}/{len(SAMPLES)} correct")
    assert ok == len(SAMPLES), "Some profiles misclassified"
    print("ALL PROFILES CLASSIFIED CORRECTLY")


if __name__ == "__main__":
    main()
