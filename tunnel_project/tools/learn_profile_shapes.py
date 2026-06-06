"""learn_profile_shapes.py - Study the cross-section shapes in data/sample_pcd.

Uses the tool's own GeometricLayer (centerline + Frenet frames, with the
normal-based slice centre) to cut clean perpendicular sections, then measures
discriminative shape features per labelled sample so we can fix
ParameterExtractionLayer.detect_profile (which currently defaults to Circle).

Run:
    ..\\.venv\\Scripts\\python.exe learn_profile_shapes.py
"""
import os
import numpy as np

from tunnel_analysis.geometry import GeometricLayer

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
    """Minimal PipelineContext stand-in for GeometricLayer."""
    centerline = None
    registered_points = None
    def __init__(self, pts): self._p = pts
    @property
    def working_points(self): return self._p


def load_points(path, max_pts=MAX_PTS):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".las", ".laz"):
        import laspy
        las = laspy.read(path)
        pts = np.vstack([las.x, las.y, las.z]).T.astype(np.float64)
    else:
        with open(path) as fh:
            ws = ("," not in fh.readline())
        pts = np.loadtxt(path, usecols=(0, 1, 2), delimiter=None if ws else ",")
    if len(pts) > max_pts:
        idx = np.random.RandomState(0).choice(len(pts), max_pts, replace=False)
        pts = pts[idx]
    return pts


def section_features(p2):
    """Discriminative shape features for one perpendicular cross-section."""
    x, y = p2[:, 0], p2[:, 1]
    # circle fit (Kasa)
    A = np.column_stack([x, y, np.ones(len(p2))])
    b = x * x + y * y
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2.0, sol[1] / 2.0
    R = float(np.sqrt(max(sol[2] + cx * cx + cy * cy, 1e-9)))
    rad = np.hypot(x - cx, y - cy)
    circ_resid = float(np.sqrt(np.mean((rad - R) ** 2)) / R) if R > 1e-6 else np.nan

    w = float(x.max() - x.min()); h = float(y.max() - y.min())
    aspect = w / h if h > 1e-6 else np.nan

    # radial uniformity: circle ~uniform; box swings R..R*sqrt2 (corners)
    rad_n = rad / (np.median(rad) + 1e-9)
    corner_excess = float(np.percentile(rad_n, 95))     # box ~1.3-1.4, circle ~1.05
    rad_cv = float(rad.std() / (rad.mean() + 1e-9))      # box high, circle low

    # angular coverage of the closed ring (open U-type/partial => low)
    ang = np.arctan2(y - cy, x - cx)
    nb = 36
    sect = np.clip(((ang + np.pi) / (2 * np.pi) * nb).astype(int), 0, nb - 1)
    ang_cov = len(np.unique(sect)) / nb

    # straight-edge fraction: a box/u-type has long axis-aligned straight runs;
    # measure how many points sit near the bbox edges (within 8% of span).
    sx = 0.08 * w; sy = 0.08 * h
    near_edge = (
        (np.abs(x - x.min()) < sx) | (np.abs(x - x.max()) < sx) |
        (np.abs(y - y.min()) < sy) | (np.abs(y - y.max()) < sy)
    )
    edge_frac = float(near_edge.mean())

    # flat-crown test: among the top 20% by y, is y nearly constant (box) or
    # arched (circle/u)? Use vertical span of crown band vs its width.
    top = y > np.percentile(y, 80)
    if top.sum() > 10:
        crown_flat = float((y[top].max() - y[top].min()) / (w + 1e-9))
    else:
        crown_flat = np.nan

    # centre-divider test (Box vs Box 2-cell): a 2-cell box has a physical wall
    # down the middle, so the scan has points in a central vertical band away
    # from floor/crown. A single box / circle bore is hollow there.
    midx = 0.5 * (x.min() + x.max())
    cy_band = (y > np.percentile(y, 15)) & (y < np.percentile(y, 85))   # exclude floor/crown
    central = (np.abs(x - midx) < 0.10 * w) & cy_band
    center_band = float(central.sum() / max(1, cy_band.sum()))
    return dict(circ_resid=circ_resid, aspect=aspect, corner_excess=corner_excess,
                rad_cv=rad_cv, ang_cov=ang_cov, edge_frac=edge_frac,
                crown_flat=crown_flat, center_band=center_band, R=R, w=w, h=h)


def analyse(path):
    pts = load_points(path)
    g = GeometricLayer()
    cl, frames = g.extract_centerline(Ctx(pts), section_count=80)
    feats = []
    idxs = np.linspace(0, len(frames) - 1, min(16, len(frames))).astype(int)
    for i in idxs:
        fr = frames[int(i)]
        C, T, N, B = fr["center"], fr["T"], fr["N"], fr["B"]
        sl = pts[np.abs((pts - C) @ T) < 0.05]
        if len(sl) < 60:
            continue
        d = sl - C
        p2 = np.column_stack([d @ N, d @ B])
        feats.append(section_features(p2))
    if not feats:
        return None
    agg = {}
    for k in feats[0]:
        vals = [f[k] for f in feats if np.isfinite(f[k])]
        agg[k] = float(np.median(vals)) if vals else np.nan
    agg["n_sections"] = len(feats)
    return agg


def main():
    hdr = ("file", "label", "circ_res", "aspect", "corner", "rad_cv",
           "ang_cov", "edge_fr", "crownflat")
    print(f"{hdr[0]:34s} {hdr[1]:11s} " + " ".join(f"{h:>8s}" for h in hdr[2:]))
    print("-" * 110)
    rows = []
    for fname, label in SAMPLES.items():
        path = os.path.join(BASE, fname)
        if not os.path.exists(path):
            print(f"{fname:34s}  MISSING"); continue
        try:
            a = analyse(path)
        except Exception as e:
            print(f"{fname:34s}  ERROR: {e}"); continue
        if a is None:
            print(f"{fname:34s}  no sections"); continue
        rows.append((label, a))
        print(f"{fname:34s} {label:11s} "
              f"{a['circ_resid']:8.3f} {a['aspect']:8.2f} {a['corner_excess']:8.2f} "
              f"{a['rad_cv']:8.3f} {a['ang_cov']:8.2f} {a['edge_frac']:8.2f} "
              f"{a['crown_flat']:8.3f}")
    print("\n=== Per-shape feature medians (for detect_profile rules) ===")
    by = {}
    for label, a in rows:
        by.setdefault(label, []).append(a)
    for label, lst in by.items():
        m = {k: float(np.median([d[k] for d in lst])) for k in lst[0]}
        print(f"  {label:11s} aspect={m['aspect']:.2f} rad_cv={m['rad_cv']:.3f} "
              f"crown_flat={m['crown_flat']:.3f} edge_frac={m['edge_frac']:.2f} "
              f"center_band={m['center_band']:.3f}")


if __name__ == "__main__":
    main()
