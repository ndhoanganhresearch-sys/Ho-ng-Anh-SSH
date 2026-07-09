"""Validate the existing tool pipeline on the synthetic T0~T5 dataset.

This is GLUE ONLY: it drives the tool's own layers (BaseLayer, GeometricLayer,
ParameterExtractionLayer) on each incremental pair Tn -> Tn+1 and compares the
measured deformation against data/time_series_deformation/incremental_pairs.csv.
No analysis logic is re-implemented; the per-chainage crown/width/radial probes
mirror the slicing in calc_arch_settlement / calc_horizontal_convergence so the
numbers are read at the exact chainage where each ground-truth defect lives.

Run from tunnel_project/:
    ..\\.venv\\Scripts\\python.exe validate_t0t5.py
"""
import os
import sys
import csv
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.models import PipelineContext
from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer

DATA = os.path.join(HERE, "data", "time_series_deformation")
PAIRS = [("T0", "T1"), ("T1", "T2"), ("T2", "T3"), ("T3", "T4"), ("T4", "T5")]
TARGET_CHAINAGE = {"crown": 20.0, "convergence": 45.0, "local": 65.0}

base = BaseLayer()
geo = GeometricLayer()
par = ParameterExtractionLayer()


def load(ep):
    return base.load_scan(os.path.join(DATA, ep + ".las"))


def read_gt():
    gt = {}
    with open(os.path.join(DATA, "incremental_pairs.csv")) as f:
        for row in csv.DictReader(f):
            gt[row["pair"]] = {
                "crown": float(row["crown_delta_mm"]),
                "convergence": float(row["convergence_delta_mm"]),
                "local": float(row["local_damage_delta_mm"]),
            }
    return gt


def frame_chainages(cl):
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(cl, axis=0), axis=1))])


def section_proj(pts, fr, eps):
    """Project a section slab onto (N, B). B oriented up so crown = +B."""
    C, T, N, B = fr["center"], fr["T"], fr["N"], fr["B"]
    if B[2] < 0:
        B = -B
    m = np.abs((pts - C) @ T) < eps
    sl = pts[m]
    if len(sl) < 8:
        return None
    d = sl - C
    return d @ N, d @ B


def radial_profile(npj, bpj, nbins=72):
    r = np.hypot(npj, bpj)
    ang = np.arctan2(bpj, npj)
    edges = np.linspace(-np.pi, np.pi, nbins + 1)
    idx = np.clip(np.digitize(ang, edges) - 1, 0, nbins - 1)
    out = np.full(nbins, np.nan)
    for k in range(nbins):
        rk = r[idx == k]
        if len(rk) >= 3:
            out[k] = np.median(rk)
    return out


def main():
    gt = read_gt()
    rows = []
    agg = []
    for a, b in PAIRS:
        ba, bb = load(a), load(b)
        ctx = PipelineContext()
        ctx.scans = [ba, bb]          # scans[0] = Tn reference, scans[1] = Tn+1 monitoring
        ctx.active_index = 1
        cl, fr = geo.extract_centerline_bspline(ctx, section_count=80)
        ctx.centerline, ctx.frenet_frames = cl, fr
        try:
            ctx.tunnel_profile = par.detect_profile(ctx)
        except Exception:
            ctx.tunnel_profile = "Circle"
        eps = par._section_epsilon(ctx)
        ch = frame_chainages(cl)
        pa = np.asarray(ba.points, float)
        pb = np.asarray(bb.points, float)

        L = float(ch[-1])

        def at(target):
            return int(np.argmin(np.abs(ch - target)))

        def crown_at(i):
            pra, prb = section_proj(pa, fr[i], eps), section_proj(pb, fr[i], eps)
            if not (pra and prb):
                return np.nan
            return (np.percentile(prb[1], 99) - np.percentile(pra[1], 99)) * 1e3

        def conv_width_at(i):
            pra, prb = section_proj(pa, fr[i], eps), section_proj(pb, fr[i], eps)
            if not (pra and prb):
                return np.nan
            wa = np.percentile(pra[0], 99) - np.percentile(pra[0], 1)
            wb = np.percentile(prb[0], 99) - np.percentile(prb[0], 1)
            return (wb - wa) * 1e3

        def local_at(i):
            pra, prb = section_proj(pa, fr[i], eps), section_proj(pb, fr[i], eps)
            if not (pra and prb):
                return np.nan
            dr = (radial_profile(*prb) - radial_profile(*pra)) * 1e3
            return np.nanmin(dr) if np.any(np.isfinite(dr)) else np.nan

        def best(fn, target):
            # centerline orientation is arbitrary, so the defect at physical
            # chainage t may map to (L - t). Evaluate both ends, keep the most
            # extreme (most negative) response = where the defect actually is.
            cands = [v for v in (fn(at(target)), fn(at(L - target))) if np.isfinite(v)]
            return min(cands) if cands else np.nan

        crown = best(crown_at, TARGET_CHAINAGE["crown"])
        conv_width = best(conv_width_at, TARGET_CHAINAGE["convergence"])
        conv = conv_width / 2.0 if np.isfinite(conv_width) else np.nan  # per-wall, comparable to GT bilateral
        local = best(local_at, TARGET_CHAINAGE["local"])

        g = gt[f"{a}-{b}"]
        for name, val in [("crown", crown), ("convergence", conv), ("local", local)]:
            rows.append((f"{a}-{b}", name, val, g[name], val - g[name]))

        # cross-check with the tool's OWN aggregate API (Tn vs Tn+1)
        cs = par.calc_arch_settlement(ctx).get("crown_settlement_max_mm", float("nan"))
        cv = par.calc_horizontal_convergence(ctx).get("lateral_convergence_max_mm", float("nan"))
        agg.append((f"{a}-{b}", cs, cv))

    print("\n=== Per-chainage validation vs incremental_pairs.csv ===")
    print(f"{'pair':7} {'metric':12} {'tool_mm':>9} {'GT_mm':>8} {'err_mm':>8}")
    for pr, name, val, gtv, err in rows:
        vs = f"{val:9.2f}" if np.isfinite(val) else f"{'nan':>9}"
        es = f"{err:8.2f}" if np.isfinite(err) else f"{'nan':>8}"
        print(f"{pr:7} {name:12} {vs} {gtv:8.2f} {es}")

    errs = [abs(e) for *_, e in rows if np.isfinite(e)]
    if errs:
        print(f"\nMean |error| = {np.mean(errs):.2f} mm   Max |error| = {np.max(errs):.2f} mm")

    print("\n=== Tool aggregate API cross-check (calc_arch_settlement / calc_horizontal_convergence) ===")
    print(f"{'pair':7} {'crown_max_mm':>13} {'conv_max_mm':>12}")
    for pr, cs, cv in agg:
        print(f"{pr:7} {cs:13.2f} {cv:12.2f}")


if __name__ == "__main__":
    main()
