# -*- coding: utf-8 -*-
r"""Create clean DEMO datasets that exercise every core feature with only a FEW,
clearly-visible defects. Pure NumPy (no Blender).

Two T0+Tn pairs are written:

  data/demo_circle/  : a gently curved CIRCLE tunnel (~60 m).
      Tn defects (few, easy to see):
        ch ~18 m : crown settlement  -28 mm
        ch ~38 m : sidewall convergence -22 mm/side (~44 mm width)
        ch ~50 m : local clearance intrusion (inward dent ~0.50 m)
      + a short crown cable near ch 30 (auto-denoise test)
      + 3 sphere targets (registration / target detect)
      + periodic ring-seam intensity drops (intensity ring-seam test)

  data/demo_box/     : a straight BOX tunnel (~50 m) to test box-profile detection.
      Tn defect: sidewall convergence -25 mm at ch ~25 m.

Key design points:
  * T0 and Tn share the SAME base sampling (same rng draws + axial jitter);
    Tn only ADDS the defects, so the deformation field is exactly the injected
    defect and nothing else (no sampling noise painting the whole tunnel).
  * Points are scattered continuously along the axis (axial jitter), not in
    thin discrete rings, so every cross-section slab is well populated and the
    profile detector / section extractor work reliably.

.las = point format 3, intensity(uint16), classification=label
(label 1=lining, 3=cable, 4=target).

Run:  ..\.venv\Scripts\python.exe tools/create_demo_datasets.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent / "data"
L_LINING, L_CABLE, L_TARGET = 1, 3, 4
I_LINING, I_SEAM, I_CABLE, I_TARGET = 0.14, 0.05, 0.30, 0.95
SEAM_SPACING = 1.2


def save_las(path, pts, inten, lab):
    import laspy
    hdr = laspy.LasHeader(point_format=3, version="1.2")
    hdr.scales = np.array([1e-3, 1e-3, 1e-3]); hdr.offsets = pts.min(0)
    las = laspy.LasData(header=hdr)
    las.x, las.y, las.z = pts[:, 0], pts[:, 1], pts[:, 2]
    las.intensity = np.clip(np.asarray(inten) * 65535.0, 0, 65535).astype(np.uint16)
    g = np.full(len(pts), 40000, dtype=np.uint16)
    las.red, las.green, las.blue = g, g, g
    las.classification = np.asarray(lab, dtype=np.uint8)
    las.write(str(path))


def sphere(center, n=120, r=0.0725, seed=0):
    rng = np.random.default_rng(seed)
    u = rng.uniform(0, 1, n); v = rng.uniform(0, 1, n)
    th = 2 * np.pi * u; ph = np.arccos(2 * v - 1)
    d = np.column_stack([np.sin(ph) * np.cos(th), np.sin(ph) * np.sin(th), np.cos(ph)])
    return center + d * r + rng.normal(0, 0.002, (n, 3))


def seam_intensity(s_arr):
    near = np.abs((s_arr % SEAM_SPACING) - SEAM_SPACING / 2) > (SEAM_SPACING / 2 - 0.06)
    return np.where(near, I_SEAM, I_LINING)


# ════════════════════════════ CIRCLE tunnel ════════════════════════════════
C_R, C_LEN, C_RCURVE, C_GRADE = 2.75, 60.0, 1.0e7, 0.0   # straight (robust axis/gauge)
C_RING_DS, C_M = 0.06, 150                   # dense (~2500 pts/m) so thin section slabs stay robust
C_AXIAL_JITTER = 0.10                        # continuous axial coverage
C_TARGET_CH = [12.0, 30.0, 48.0]
C_CABLE_CH = 30.0
C_DEFORM = [
    {"s": 18.0, "crown": -28.0, "side": -6.0, "sigma": 2.5},
    {"s": 38.0, "crown": -6.0, "side": -22.0, "sigma": 2.5},
]
C_DENT = {"s": 50.0, "depth": 0.50, "ang": 2.5, "half": 0.25, "sigma": 1.0}


def c_centerline(s):
    th = s / C_RCURVE
    return np.stack([C_RCURVE * (1 - np.cos(th)), C_RCURVE * np.sin(th), C_GRADE * s], axis=-1)


def c_frame(s):
    th = s / C_RCURVE
    T = np.stack([np.sin(th), np.cos(th), np.full_like(th, C_GRADE)], axis=-1)
    T = T / np.linalg.norm(T, axis=-1, keepdims=True)
    up = np.array([0.0, 0.0, 1.0])
    B = up - (T @ up)[..., None] * T
    B = B / np.linalg.norm(B, axis=-1, keepdims=True)
    return T, np.cross(T, B), B


def c_deform(s, a):
    dN = np.zeros_like(a); dB = np.zeros_like(a)
    for sp in C_DEFORM:
        g = np.exp(-0.5 * ((s - sp["s"]) / sp["sigma"]) ** 2)
        dB += (sp["crown"] / 1000.0) * np.maximum(0.0, np.sin(a)) * g
        dN += -np.sign(np.cos(a)) * abs(sp["side"]) / 1000.0 * np.abs(np.cos(a)) * g
    return dN, dB


def c_dent(s, a):
    g = np.exp(-0.5 * ((s - C_DENT["s"]) / C_DENT["sigma"]) ** 2)
    da = np.angle(np.exp(1j * (a - C_DENT["ang"])))
    return -C_DENT["depth"] * np.exp(-0.5 * (da / C_DENT["half"]) ** 2) * g


def build_circle_pair(seed=1):
    """Return (t0_pts, tn_pts, inten, lab) for the lining, sharing base sampling."""
    rng = np.random.default_rng(seed)
    ss = np.arange(0.0, C_LEN + C_RING_DS, C_RING_DS)
    C = c_centerline(ss); T, N, B = c_frame(ss)
    t0, tn, inten, lab = [], [], [], []
    for k, s in enumerate(ss):
        a = np.linspace(0, 2 * np.pi, C_M, endpoint=False) + rng.uniform(-0.02, 0.02, C_M)
        rr = C_R + rng.normal(0, 0.004, C_M)
        axial = rng.uniform(-C_AXIAL_JITTER, C_AXIAL_JITTER, C_M)   # shared, continuous
        base = C[k] + axial[:, None] * T[k]
        t0.append(base + (rr * np.cos(a))[:, None] * N[k] + (rr * np.sin(a))[:, None] * B[k])
        dN, dB = c_deform(s, a); rr_t = rr + c_dent(s, a)
        tn.append(base + (rr_t * np.cos(a) + dN)[:, None] * N[k] + (rr_t * np.sin(a) + dB)[:, None] * B[k])
        si = seam_intensity(s + axial)
        inten.append(si); lab.append(np.full(C_M, L_LINING))
    return np.vstack(t0), np.vstack(tn), np.concatenate(inten), np.concatenate(lab)


def circle_targets():
    ss = np.array(C_TARGET_CH); C = c_centerline(ss); _T, N, B = c_frame(ss)
    phis = [0.6, 2.4, 3.9]; parts = []
    for i in range(len(ss)):
        c = C[i] + 2.0 * (np.cos(phis[i]) * N[i] + np.sin(phis[i]) * B[i])
        parts.append(sphere(c, seed=900 + i))
    p = np.vstack(parts)
    return p, np.full(len(p), I_TARGET), np.full(len(p), L_TARGET)


def circle_cable(seed=3):
    rng = np.random.default_rng(seed)
    ss = np.linspace(C_CABLE_CH - 5, C_CABLE_CH + 5, 120)
    C = c_centerline(ss); _T, N, B = c_frame(ss)
    cab = C + (C_R - 0.18) * B + 0.25 * N + rng.normal(0, 0.012, (len(ss), 3))
    return cab, np.full(len(cab), I_CABLE), np.full(len(cab), L_CABLE)


# ════════════════════════════ BOX tunnel ═══════════════════════════════════
B_W, B_H, B_LEN = 8.5, 5.0, 50.0
B_RING_DS, B_PERIM = 0.08, 260
B_CONV = {"s": 25.0, "side": -25.0, "sigma": 3.0}


def build_box_pair(seed=11):
    rng = np.random.default_rng(seed)
    ss = np.arange(0.0, B_LEN + B_RING_DS, B_RING_DS)
    w, h, per = B_W / 2.0, B_H, B_PERIM
    seg = per // 4
    t0, tn, inten, lab = [], [], [], []
    for s in ss:
        # shared base perimeter sampling
        xf = rng.uniform(-w, w, seg); zf = np.zeros(seg)
        xc = rng.uniform(-w, w, seg); zc = np.full(seg, h)
        zl = rng.uniform(0, h, seg); zr = rng.uniform(0, h, per - 3 * seg)
        xl = np.full(seg, -w); xr = np.full(per - 3 * seg, w)
        x = np.concatenate([xf, xc, xl, xr]) + rng.normal(0, 0.004, per)
        z = np.concatenate([zf, zc, zl, zr]) + rng.normal(0, 0.004, per)
        axial = rng.uniform(-B_RING_DS * 0.6, B_RING_DS * 0.6, per)   # shared
        y = np.full(per, s) + axial
        t0.append(np.column_stack([x, y, z]))
        # Tn: walls converge inward (left x+conv, right x-conv)
        conv = abs(B_CONV["side"]) / 1000.0 * np.exp(-0.5 * ((s - B_CONV["s"]) / B_CONV["sigma"]) ** 2)
        xt = x.copy()
        left = x < -w + 0.05; right = x > w - 0.05
        xt[left] += conv; xt[right] -= conv
        tn.append(np.column_stack([xt, y, z]))
        inten.append(seam_intensity(s + axial)); lab.append(np.full(per, L_LINING))
    return np.vstack(t0), np.vstack(tn), np.concatenate(inten), np.concatenate(lab)


# ════════════════════════════ main ═════════════════════════════════════════
def _write(folder, t0, tn, meta):
    folder.mkdir(parents=True, exist_ok=True)
    save_las(folder / meta["t0_name"], *t0)
    save_las(folder / meta["tn_name"], *tn)
    (folder / "manifest.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main():
    # CIRCLE
    lt0, ltn, li, ll = build_circle_pair(seed=1)
    tg, tgi, tgl = circle_targets()
    cb, cbi, cbl = circle_cable()
    t0c = (np.vstack([lt0, tg]), np.concatenate([li, tgi]), np.concatenate([ll, tgl]))
    tnc = (np.vstack([ltn, tg, cb]), np.concatenate([li, tgi, cbi]), np.concatenate([ll, tgl, cbl]))
    _write(ROOT / "demo_circle", t0c, tnc, {
        "dataset": "demo_circle", "t0_name": "T0_circle.las", "tn_name": "Tn_circle.las",
        "shape": "circle (gently curved)", "radius_m": C_R, "length_m": C_LEN,
        "defects": [
            {"chainage_m": 18, "type": "crown settlement", "mm": -28},
            {"chainage_m": 38, "type": "sidewall convergence", "mm_per_side": -22},
            {"chainage_m": 50, "type": "clearance intrusion (inward dent)", "depth_m": C_DENT["depth"]},
            {"chainage_m": 30, "type": "noise: crown cable", "pts": int(len(cb))},
        ],
        "targets_ch_m": C_TARGET_CH, "labels": {"1": "lining", "3": "cable", "4": "target"},
    })
    # BOX
    bt0, btn, bi, bl = build_box_pair(seed=11)
    _write(ROOT / "demo_box", (bt0, bi, bl), (btn, bi, bl), {
        "dataset": "demo_box", "t0_name": "T0_box.las", "tn_name": "Tn_box.las",
        "shape": "box (straight)", "width_m": B_W, "height_m": B_H, "length_m": B_LEN,
        "defects": [{"chainage_m": 25, "type": "sidewall convergence", "mm_per_side": -25}],
        "labels": {"1": "lining"},
    })
    print("demo_circle:", len(t0c[0]), "->", len(tnc[0]), "pts")
    print("demo_box:   ", len(bt0), "->", len(btn), "pts")


if __name__ == "__main__":
    main()
