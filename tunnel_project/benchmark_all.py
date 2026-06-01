# -*- coding: utf-8 -*-
"""benchmark_all.py - single-table benchmark of the tunnel pipeline.

Runs registration, denoise scoring, centerline accuracy, and per-stage timing
on one point-cloud file and prints one consolidated report.

Run from tunnel_project/ (use the .venv with small_gicp/open3d/py4dgeo):
    python benchmark_all.py INPUT.las [--structural 0] [--max-points 800000]

- registration: applies a known rigid transform and reports recovery RMSE (mm)
  + time for the GICP/ICP backend.
- timing: voxel -> denoise -> centerline -> sections, seconds each.
- centerline: per-section robust circle-fit residual (m) as a roundness proxy.
- denoise scoring: precision/recall/F1 + lining retention vs per-point labels
  (only if the file carries a label channel; pass --structural for the lining
  class id).
"""
import argparse
import os
import sys
import time

import numpy as np

from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.preprocessing import PreprocessingLayer
from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.registration import RegistrationLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle
from tunnel_analysis.common import principal_axes, validate_xyz


def _rigid(angle_deg=1.2, translation=(0.05, -0.04, 0.03)):
    a = np.deg2rad(angle_deg)
    c, s = np.cos(a), np.sin(a)
    T = np.eye(4)
    T[:3, :3] = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    T[:3, 3] = np.asarray(translation, dtype=float)
    return T


def bench_registration(pts):
    """Apply a known transform, recover with the ICP backend, report RMSE+time."""
    reg = RegistrationLayer()
    T = _rigid()
    moved = (T @ np.hstack([pts, np.ones((len(pts), 1))]).T).T[:, :3]
    t0 = time.perf_counter()
    _reg, rmse_mm = reg._icp(moved, pts)
    dt = time.perf_counter() - t0
    return {"rmse_mm": float(rmse_mm), "time_s": dt, "n": len(pts)}


def _circle_resid(p2):
    """LSQ circle residual median (m) on a 2D section, robust to clutter."""
    if len(p2) < 12:
        return float("nan")
    x, y = p2[:, 0], p2[:, 1]
    A = np.column_stack([x, y, np.ones(len(p2))])
    b = x * x + y * y
    try:
        sol, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    except Exception:
        return float("nan")
    cx, cy = sol[0] / 2.0, sol[1] / 2.0
    R = float(np.sqrt(max(sol[2] + cx * cx + cy * cy, 1e-9)))
    keep = np.ones(len(p2), dtype=bool)
    for _ in range(3):
        r = np.hypot(x - cx, y - cy)
        cur = np.abs(r - R)
        keep = cur <= max(0.1, float(np.median(cur)) * 1.5)
        if keep.sum() < 8:
            break
        xx, yy = x[keep], y[keep]
        A2 = np.column_stack([xx, yy, np.ones(len(xx))])
        s2, _, _, _ = np.linalg.lstsq(A2, xx * xx + yy * yy, rcond=None)
        cx, cy = s2[0] / 2.0, s2[1] / 2.0
        R = float(np.sqrt(max(s2[2] + cx * cx + cy * cy, 1e-9)))
    r = np.hypot(x - cx, y - cy)
    return float(np.median(np.abs(r[keep] - R))), R

def run(input_path, structural=None, max_points=800_000):
    base = BaseLayer(); pre = PreprocessingLayer()
    geo = GeometricLayer(); par = ParameterExtractionLayer()
    timing = {}
    rep = {"input": input_path, "timing": timing}

    t0 = time.perf_counter()
    bundle = base.load_scan(input_path, max_points=max_points)
    timing["load"] = time.perf_counter() - t0
    labels = bundle.metadata.get("labels") if bundle.metadata else None
    raw = validate_xyz(bundle.points)
    rep["n_points"] = len(raw)
    rep["has_labels"] = labels is not None

    # Registration recovery on the raw cloud (subsampled for speed).
    rsub = raw if len(raw) <= 400_000 else raw[np.random.default_rng(0).choice(len(raw), 400_000, replace=False)]
    try:
        rep["registration"] = bench_registration(rsub)
    except Exception as e:
        rep["registration"] = {"error": str(e)}

    ctx = PipelineContext(); ctx.scans.append(bundle); ctx.active_index = 0

    t0 = time.perf_counter()
    dn, _c = pre.voxel_downsample(ctx, voxel_size=0.05); ctx.normalized_points = dn
    timing["voxel"] = time.perf_counter() - t0
    rep["n_voxel"] = len(dn)

    t0 = time.perf_counter()
    clean, st = pre.auto_denoise(ctx); ctx.normalized_points = clean
    timing["denoise"] = time.perf_counter() - t0
    rep["denoise_removed"] = int(st.get("n_removed", 0))

    t0 = time.perf_counter()
    cl, fr = geo.extract_centerline_bspline(ctx, section_count=40)
    ctx.centerline = cl; ctx.frenet_frames = fr
    timing["centerline"] = time.perf_counter() - t0
    ctx.tunnel_profile = par.detect_profile(ctx)

    t0 = time.perf_counter()
    secs = par.compute_all_sections(ctx, vl_box_w=5.0, vl_box_h=5.0, vl_cir_r=2.7)
    ctx.sections = secs
    timing["sections"] = time.perf_counter() - t0

    # Centerline straightness + per-section roundness (residual).
    c = cl.mean(0); u, s, vt = np.linalg.svd(cl - c); ax = vt[0]
    t = (cl - c) @ ax; perp = np.linalg.norm(cl - c - np.outer(t, ax), axis=1)
    resids = []
    for sec in secs:
        if sec.pts_2d is not None and len(sec.pts_2d) >= 12:
            out = _circle_resid(np.asarray(sec.pts_2d))
            if isinstance(out, tuple):
                resids.append(out[0])
    rep["centerline"] = {
        "n_sections": len(secs),
        "length_m": float(t.max() - t.min()),
        "curvature_ratio": float(perp.max() / max(t.max() - t.min(), 1e-9)),
        "profile": ctx.tunnel_profile,
        "median_fit_resid_m": float(np.median(resids)) if resids else float("nan"),
    }

    # Denoise scoring vs labels (optional).
    if labels is not None:
        from tunnel_analysis.datasets import stsd
        sl = {int(structural)} if structural is not None else {int(np.bincount(np.asarray(labels).astype(int)).argmax())}
        try:
            sc = stsd.evaluate_methods(raw, np.asarray(labels).astype(int),
                                       methods=["auto_denoise", "sor", "tunnel_lining"],
                                       structure_labels=sl)
            rep["denoise_scoring"] = {"structural_label": sorted(sl), "methods": sc}
        except Exception as e:
            rep["denoise_scoring"] = {"error": str(e)}
    return rep

def print_report(rep):
    line = "=" * 64
    print(line)
    print("TUNNEL PIPELINE BENCHMARK")
    print(line)
    print(f"Input        : {rep['input']}")
    print(f"Points       : {rep['n_points']:,} (voxel -> {rep.get('n_voxel', 0):,})")
    print(f"Has labels   : {rep['has_labels']}")

    print("\n-- Stage timing (s) " + "-" * 44)
    tot = 0.0
    for k in ("load", "voxel", "denoise", "centerline", "sections"):
        v = rep["timing"].get(k)
        if v is not None:
            print(f"  {k:<12}: {v:8.2f}")
            tot += v
    print(f"  {'TOTAL':<12}: {tot:8.2f}")

    print("\n-- Registration (recovery of known transform) " + "-" * 17)
    r = rep.get("registration", {})
    if "error" in r:
        print(f"  ERROR: {r['error']}")
    else:
        print(f"  points={r['n']:,}  RMSE={r['rmse_mm']:.3f} mm  time={r['time_s']*1000:.1f} ms")

    print("\n-- Centerline / sections " + "-" * 38)
    c = rep.get("centerline", {})
    print(f"  sections={c.get('n_sections')}  length={c.get('length_m', float('nan')):.1f} m  "
          f"curvature_ratio={c.get('curvature_ratio', float('nan')):.4f}")
    print(f"  profile={c.get('profile')}  median circle-fit residual={c.get('median_fit_resid_m', float('nan')):.3f} m")

    print("\n-- Denoise scoring vs labels " + "-" * 34)
    ds = rep.get("denoise_scoring")
    if ds is None:
        print("  (skipped: no per-point labels)")
    elif "error" in ds:
        print(f"  ERROR: {ds['error']}")
    else:
        print(f"  structural label(s): {ds['structural_label']}")
        print(f"  {'method':<14} {'noiseP':>7} {'noiseR':>7} {'F1':>7} {'lining_keep':>12}")
        for name, sc in ds["methods"].items():
            if "error" in sc:
                print(f"  {name:<14} ERROR {sc['error']}"); continue
            print(f"  {name:<14} {sc['noise_precision']:7.2f} {sc['noise_recall']:7.2f} "
                  f"{sc['noise_f1']:7.2f} {sc['lining_retention']:12.2f}")
    print(line)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="benchmark_all", description="One-table tunnel pipeline benchmark.")
    ap.add_argument("input", help="point-cloud file (.las/.ply/.txt/...)")
    ap.add_argument("--structural", type=int, default=None,
                    help="structural (lining) label id for denoise scoring; default = most common label")
    ap.add_argument("--max-points", type=int, default=800_000)
    args = ap.parse_args(argv)
    if not os.path.isfile(args.input):
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 2
    rep = run(args.input, structural=args.structural, max_points=args.max_points)
    print_report(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
