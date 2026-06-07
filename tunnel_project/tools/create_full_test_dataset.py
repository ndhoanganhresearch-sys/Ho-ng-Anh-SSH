# -*- coding: utf-8 -*-
r"""Create ONE T0 + Tn pair: a CURVED ~1 km tunnel with only 4 clear defect
spots spread along it. Pure NumPy — NO Blender.

Covers every core feature, but kept easy to read:
  • curved 1 km centerline (gentle horizontal arc + slight grade)
  • 5 sphere targets spread along it ............... registration / station merge
  • exactly 4 defect spots, well separated:
        ch ~200 m : crown settlement  (deformation)
        ch ~450 m : sidewall convergence (deformation)
        ch ~700 m : noise — short cable + 1 outlier blob (filtering)
        ch ~900 m : combined crown+convergence (deformation/ovality)
  • Tn slightly displaced (translation + tiny yaw) ... epoch / station alignment

Outputs (data/full_test/): T0_full.las/.txt, Tn_full.las/.txt, manifest, README
8-col txt: x y z nx ny nz intensity label   (label 1=lining,2=outlier,3=cable)
.las: point format 3, intensity(uint16), classification=label

Run:  ..\.venv\Scripts\python.exe tools/create_full_test_dataset.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "data" / "full_test"

R         = 3.0          # tunnel radius (m)
LENGTH    = 1000.0       # ~1 km along the curved centerline
R_CURVE   = 2500.0       # horizontal curve radius (gentle, ~23 deg over 1 km)
GRADE     = 0.004        # 0.4 % vertical grade
RING_DS   = 0.6          # ring spacing along the centerline (m)
M_RING    = 90           # points per ring
LINING_I, TARGET_I, CABLE_I = 0.10, 0.95, 0.30
L_LINING, L_OUTLIER, L_CABLE = 1, 2, 3

# Sphere targets at these chainages (placed in free space inside the bore).
TARGET_CH = [120.0, 320.0, 520.0, 720.0, 920.0]

# The 4 deformation defect spots (chainage, crown mm, per-side mm, sigma m).
DEFORM_SPOTS = [
    {"s": 200.0, "crown": -60.0, "side": -10.0, "sigma": 10.0},   # crown settlement
    {"s": 450.0, "crown": -10.0, "side": -50.0, "sigma": 10.0},   # convergence
    {"s": 900.0, "crown": -45.0, "side": -45.0, "sigma": 10.0},   # combined
]
NOISE_CH = 700.0   # 4th spot: cable + outlier blob (no deformation)


# ── Curved centerline + moving frame ────────────────────────────────────────
def centerline(s):
    """Horizontal circular arc (turns toward +X) + slight grade. s = arc length."""
    th = s / R_CURVE
    x = R_CURVE * (1.0 - np.cos(th))
    y = R_CURVE * np.sin(th)
    z = GRADE * s
    return np.stack([x, y, z], axis=-1)


def frame(s):
    """Tangent T, side-normal N (horizontal), up-normal B at arc length s."""
    th = s / R_CURVE
    T = np.stack([np.sin(th), np.cos(th), np.full_like(th, GRADE)], axis=-1)
    T = T / np.linalg.norm(T, axis=-1, keepdims=True)
    up = np.array([0.0, 0.0, 1.0])
    B = up - (T @ up)[..., None] * T          # vertical-ish, perpendicular to T
    B = B / np.linalg.norm(B, axis=-1, keepdims=True)
    N = np.cross(T, B)                          # horizontal side
    return T, N, B


def deform_at(s, a):
    """Return (d_along_N, d_along_B) deformation (m) at chainage s, ring angle a."""
    dN = np.zeros_like(a); dB = np.zeros_like(a)
    for sp in DEFORM_SPOTS:
        g = np.exp(-0.5 * ((s - sp["s"]) / sp["sigma"]) ** 2)
        crown_w = np.maximum(0.0, np.sin(a))           # top
        side_w  = np.abs(np.cos(a))                    # walls
        dB += (sp["crown"] / 1000.0) * crown_w * g     # crown settles (down = -B dir via negative)
        dN += -np.sign(np.cos(a)) * abs(sp["side"]) / 1000.0 * side_w * g
    return dN, dB


def build_lining(deform: bool, seed: int):
    rng = np.random.default_rng(seed)
    ss = np.arange(0.0, LENGTH + RING_DS, RING_DS)
    C = centerline(ss); T, N, B = frame(ss)
    pts = []
    for k, s in enumerate(ss):
        a = np.linspace(0, 2*np.pi, M_RING, endpoint=False) + rng.uniform(-0.02, 0.02, M_RING)
        rr = R + rng.normal(0, 0.004, M_RING)
        dN = np.zeros(M_RING); dB = np.zeros(M_RING)
        if deform:
            dN, dB = deform_at(s, a)
        coordN = rr * np.cos(a) + dN
        coordB = rr * np.sin(a) + dB
        ring = C[k] + coordN[:, None] * N[k] + coordB[:, None] * B[k]
        pts.append(ring)
    p = np.vstack(pts)
    return p, np.full(len(p), LINING_I), np.full(len(p), L_LINING)


def target_world_positions():
    """Sphere-target centers in free space (offset ~2 m from the centerline)."""
    ss = np.array(TARGET_CH)
    C = centerline(ss); _T, N, B = frame(ss)
    phis = [0.4, 2.3, 4.0, 1.0, 3.4]      # varied around the section
    return [C[i] + 2.0 * (np.cos(phis[i]) * N[i] + np.sin(phis[i]) * B[i])
            for i in range(len(ss))]


def sphere(center, n=90, seed=0):
    rng = np.random.default_rng(seed)
    u = rng.uniform(0, 1, n); v = rng.uniform(0, 1, n)
    th = 2*np.pi*u; ph = np.arccos(2*v - 1)
    d = np.column_stack([np.sin(ph)*np.cos(th), np.sin(ph)*np.sin(th), np.cos(ph)])
    return center + d*0.0725 + rng.normal(0, 0.002, (n, 3))


def add_targets(seed):
    parts, ii, ll = [], [], []
    for i, c in enumerate(target_world_positions()):
        sp = sphere(c, seed=seed*100 + i); parts.append(sp)
        ii.append(np.full(len(sp), TARGET_I)); ll.append(np.full(len(sp), L_LINING))
    return np.vstack(parts), np.concatenate(ii), np.concatenate(ll)


def noise_spot(seed):
    """4th spot: a short crown cable + one outlier blob near chainage NOISE_CH."""
    rng = np.random.default_rng(seed)
    ss = np.linspace(NOISE_CH - 6, NOISE_CH + 6, 140)
    C = centerline(ss); _T, N, B = frame(ss)
    cable = C + (R - 0.15) * B + rng.normal(0, 0.015, (len(ss), 3))   # below crown
    # one compact outlier blob just inside the bore
    Cb = centerline(np.array([NOISE_CH]))[0]; _t, Nb, Bb = frame(np.array([NOISE_CH]))
    blob_center = Cb + 1.4 * Nb[0] - 0.6 * Bb[0]
    blob = blob_center + rng.normal(0, 0.12, (30, 3))
    p = np.vstack([cable, blob])
    inten = np.concatenate([np.full(len(cable), CABLE_I), rng.uniform(0.05, 0.4, len(blob))])
    lab = np.concatenate([np.full(len(cable), L_CABLE), np.full(len(blob), L_OUTLIER)])
    return p, inten, lab


def rigid(yaw_deg, t):
    a = np.deg2rad(yaw_deg)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    M = np.eye(4); M[:3, :3] = Rz; M[:3, 3] = np.asarray(t, float); return M


def apply(M, p):
    return (M @ np.hstack([p, np.ones((len(p), 1))]).T).T[:, :3]


def save_txt(path, pts, inten, lab):
    arr = np.column_stack([pts, np.zeros((len(pts), 3)), inten, lab])
    np.savetxt(path, arr, fmt=["%.4f"]*7 + ["%d"],
               header="x y z nx ny nz intensity label", comments="# ")


def save_las(path, pts, inten, lab):
    try:
        import laspy
    except Exception as e:
        print(f"  (.las skipped: {e})"); return
    hdr = laspy.LasHeader(point_format=3, version="1.2")
    hdr.scales = np.array([1e-3, 1e-3, 1e-3]); hdr.offsets = pts.min(0)
    las = laspy.LasData(header=hdr)
    las.x, las.y, las.z = pts[:, 0], pts[:, 1], pts[:, 2]
    las.intensity = np.clip(inten * 65535.0, 0, 65535).astype(np.uint16)
    g = np.full(len(pts), 40000, dtype=np.uint16)
    las.red, las.green, las.blue = g, g, g
    las.classification = np.asarray(lab, dtype=np.uint8)
    las.write(str(path))


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # T0 — clean reference
    lp, li, ll = build_lining(deform=False, seed=1)
    tp, ti, tl = add_targets(seed=1)
    t0 = np.vstack([lp, tp]); t0_i = np.concatenate([li, ti]); t0_l = np.concatenate([ll, tl])

    # Tn — deformed at 3 spots + noise spot + same targets, slightly displaced
    lp2, li2, ll2 = build_lining(deform=True, seed=2)
    tp2, ti2, tl2 = add_targets(seed=2)
    npc, npi, npl = noise_spot(seed=3)
    tn_world = np.vstack([lp2, tp2, npc])
    tn_i = np.concatenate([li2, ti2, npi]); tn_l = np.concatenate([ll2, tl2, npl])
    # SAME geodetic frame as T0 — a 1 km drive is monitored against shared
    # survey control, so epochs are already co-registered; the only difference
    # is the real deformation (+ noise). No artificial offset that would make a
    # long near-symmetric tunnel slide under ICP. (Use the small straight
    # dataset / targets for registration-specific testing.)
    tn = tn_world

    save_txt(OUT / "T0_full.txt", t0, t0_i, t0_l)
    save_txt(OUT / "Tn_full.txt", tn, tn_i, tn_l)
    save_las(OUT / "T0_full.las", t0, t0_i, t0_l)
    save_las(OUT / "Tn_full.las", tn, tn_i, tn_l)

    n_cable = int((tn_l == L_CABLE).sum()); n_out = int((tn_l == L_OUTLIER).sum())
    manifest = {
        "dataset": "full_test",
        "created_by": "tools/create_full_test_dataset.py (pure NumPy, no Blender)",
        "purpose": "Curved ~1 km tunnel, 4 clear defect spots — self-test everything.",
        "units": "meters", "columns": "x y z nx ny nz intensity label",
        "labels": {"1": "lining", "2": "outlier", "3": "cable"},
        "tunnel": {"radius_m": R, "length_m": LENGTH, "curve_radius_m": R_CURVE,
                   "grade": GRADE, "ring_spacing_m": RING_DS, "shape": "curved (horizontal arc + grade)"},
        "targets": {"count": len(TARGET_CH), "chainages_m": TARGET_CH,
                    "type": "sphere 0.0725 m, intensity 0.95"},
        "defect_spots": [
            {"chainage_m": 200, "type": "crown settlement", "crown_mm": -60},
            {"chainage_m": 450, "type": "sidewall convergence", "per_side_mm": -50},
            {"chainage_m": 700, "type": "noise (cable + outlier blob)", "cable_pts": n_cable, "outlier_pts": n_out},
            {"chainage_m": 900, "type": "combined crown+convergence", "crown_mm": -45, "per_side_mm": -45},
        ],
        "tn_frame_offset": {"note": "same geodetic frame as T0 (survey-controlled); no offset"},
        "files": [
            {"name": "T0_full.las / .txt", "role": "reference (clean)", "points": int(len(t0))},
            {"name": "Tn_full.las / .txt", "role": "monitoring (4 defects + displaced)", "points": int(len(tn))},
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Full Test Dataset — curved ~1 km tunnel, 4 defect spots\n\n"
        "Pure-NumPy synthetic. Load `T0_full.las` + `Tn_full.las` (or .txt) to self-test.\n\n"
        f"- Curved {LENGTH:.0f} m tunnel (arc radius {R_CURVE:.0f} m, grade {GRADE*100:.1f}%)\n"
        f"- {len(TARGET_CH)} sphere targets at ch {TARGET_CH} m (registration)\n\n"
        "## 4 defect spots (well separated)\n"
        "| Chainage | Defect |\n|---|---|\n"
        "| ~200 m | crown settlement −60 mm |\n"
        "| ~450 m | sidewall convergence −50 mm/side |\n"
        f"| ~700 m | noise: cable ({n_cable} pts) + outlier blob ({n_out} pts) |\n"
        "| ~900 m | combined crown −45 + convergence −45 mm |\n\n"
        "## Workflow\n"
        "1. **1.1 Import** → `T0_full.las`\n"
        "2. **1.2 Add scan station** → `Tn_full.las`\n"
        "3. **3.1 Auto-align T0/Tn** (targets)\n"
        "4. **2.2 Clean noise** → removes the ch-700 cable + blob\n"
        "5. **AUTO PIPELINE** → centerline (curved), sections, deformation, warnings\n"
        "   Expect warnings at ch ~200, ~450, ~900 m.\n"
        "6. **7.x** → export CSV / Excel / PDF.\n",
        encoding="utf-8")

    print(f"Wrote {OUT}")
    print(f"  T0_full: {len(t0):,} pts   Tn_full: {len(tn):,} pts")
    print(f"  curved {LENGTH:.0f} m (arc R={R_CURVE:.0f} m), {len(TARGET_CH)} targets")
    print(f"  4 defect spots: crown@200, converg@450, noise@700, combined@900 (cable {n_cable}, outliers {n_out})")


if __name__ == "__main__":
    main()
