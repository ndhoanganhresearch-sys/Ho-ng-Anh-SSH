# -*- coding: utf-8 -*-
r"""Benchmark: Frenet-frame vs world-frame cross-section extraction.

Compares ovality measurements from two slicing approaches on the curved
tunnel dataset (case_05_curved_centerline) to quantify the bias introduced
by axis-aligned (world-frame) slicing.

Run from tunnel_project:
    ..\.venv\Scripts\python.exe benchmark_frenet_vs_worldframe.py
"""
import json
import time
from pathlib import Path

import numpy as np

from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.common import principal_axes, validate_xyz

ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "paper" / "evidence" / "benchmark_reports" / "frenet_vs_worldframe.json"

DESIGN_RADIUS = 4.0
SECTION_COUNT = 48


def make_ctx(pts):
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=pts))
    ctx.active_index = 0
    return ctx


def frenet_sections(pts):
    """Extract sections using Frenet-frame (gravity-anchored) slicing."""
    ctx = make_ctx(pts)
    geo = GeometricLayer()
    par = ParameterExtractionLayer()
    cl, fr = geo.extract_centerline_bspline(ctx, section_count=SECTION_COUNT)
    ctx.centerline = cl
    ctx.frenet_frames = fr
    ctx.tunnel_profile = par.detect_profile(ctx)
    sections = par.compute_all_sections(ctx, vl_box_w=5.0, vl_box_h=5.0, vl_cir_r=2.2)
    return sections, cl


def worldframe_sections(pts):
    """Extract sections using world-frame (axis-aligned) slicing.

    Slices perpendicular to the global PCA axis instead of the local
    Frenet tangent. This is the conventional approach that introduces
    oblique cuts on curved tunnels.
    """
    ctx = make_ctx(pts)
    par = ParameterExtractionLayer()

    pts_v = validate_xyz(pts)
    c, ax, e1, e2 = principal_axes(pts_v)
    proj = (pts_v - c) @ ax
    pmin, pmax = float(proj.min()), float(proj.max())

    centers = np.linspace(pmin, pmax, SECTION_COUNT)
    epsilon = (pmax - pmin) / SECTION_COUNT * 0.55
    epsilon = max(0.05, min(0.5, epsilon))

    frames = []
    T = ax / np.linalg.norm(ax)
    N = e1 / np.linalg.norm(e1)
    B = e2 / np.linalg.norm(e2)

    for i, t_pos in enumerate(centers):
        center_3d = c + t_pos * ax
        frames.append({"center": center_3d, "T": T, "N": N, "B": B})

    ctx.centerline = np.array([f["center"] for f in frames])
    ctx.frenet_frames = frames
    ctx.tunnel_profile = par.detect_profile(ctx)
    sections = par.compute_all_sections(
        ctx, vl_box_w=5.0, vl_box_h=5.0, vl_cir_r=2.2, epsilon=epsilon
    )
    return sections, ctx.centerline


def section_metrics(sections):
    radii = []
    ovalities = []
    eccentricities = []
    for s in sections:
        if s.pts_2d is not None and len(s.pts_2d) >= 12:
            if np.isfinite(s.radius_fit):
                radii.append(float(s.radius_fit))
            if s.ovality is not None and np.isfinite(s.ovality):
                ovalities.append(float(s.ovality))
            if s.eccentricity is not None and np.isfinite(s.eccentricity):
                eccentricities.append(float(s.eccentricity))
    return {
        "n_valid": len(radii),
        "radii": radii,
        "ovalities": ovalities,
        "eccentricities": eccentricities,
        "median_radius": float(np.median(radii)) if radii else float("nan"),
        "mean_radius": float(np.mean(radii)) if radii else float("nan"),
        "std_radius": float(np.std(radii)) if radii else float("nan"),
        "radius_error_pct": float(abs(np.median(radii) - DESIGN_RADIUS) / DESIGN_RADIUS * 100) if radii else float("nan"),
        "median_ovality": float(np.median(ovalities)) if ovalities else float("nan"),
        "mean_ovality": float(np.mean(ovalities)) if ovalities else float("nan"),
        "max_ovality": float(np.max(ovalities)) if ovalities else float("nan"),
        "median_eccentricity": float(np.median(eccentricities)) if eccentricities else float("nan"),
    }


def main():
    datasets = [
        ("case_05_curved_centerline", ROOT / "data" / "blender_test_suite" / "case_05_curved_centerline"),
        ("case_01_clean_reference", ROOT / "data" / "blender_test_suite" / "case_01_clean_reference"),
    ]

    report = {"benchmark": "frenet_vs_worldframe", "design_radius_m": DESIGN_RADIUS, "cases": {}}

    for name, case_dir in datasets:
        t0_path = case_dir / "T0.txt"
        if not t0_path.exists():
            print(f"SKIP {name}: {t0_path} not found")
            continue

        print(f"\n{'='*64}")
        print(f"CASE: {name}")
        print(f"{'='*64}")

        pts = BaseLayer().load_scan(str(t0_path)).points

        t0 = time.perf_counter()
        frenet_secs, frenet_cl = frenet_sections(pts)
        t_frenet = time.perf_counter() - t0

        t0 = time.perf_counter()
        world_secs, world_cl = worldframe_sections(pts)
        t_world = time.perf_counter() - t0

        fm = section_metrics(frenet_secs)
        wm = section_metrics(world_secs)

        print(f"\n{'Metric':<30} {'Frenet':>12} {'World-frame':>12} {'Diff':>12}")
        print("-" * 68)
        print(f"{'Valid sections':<30} {fm['n_valid']:>12d} {wm['n_valid']:>12d}")
        print(f"{'Median radius (m)':<30} {fm['median_radius']:>12.5f} {wm['median_radius']:>12.5f} {abs(fm['median_radius']-wm['median_radius']):>12.5f}")
        print(f"{'Radius error (%)':<30} {fm['radius_error_pct']:>12.4f} {wm['radius_error_pct']:>12.4f}")
        print(f"{'Median ovality (%)':<30} {fm['median_ovality']:>12.4f} {wm['median_ovality']:>12.4f} {abs(fm['median_ovality']-wm['median_ovality']):>12.4f}")
        print(f"{'Mean ovality (%)':<30} {fm['mean_ovality']:>12.4f} {wm['mean_ovality']:>12.4f}")
        print(f"{'Max ovality (%)':<30} {fm['max_ovality']:>12.4f} {wm['max_ovality']:>12.4f}")
        print(f"{'Median eccentricity (m)':<30} {fm['median_eccentricity']:>12.5f} {wm['median_eccentricity']:>12.5f}")
        print(f"{'Std radius (m)':<30} {fm['std_radius']:>12.5f} {wm['std_radius']:>12.5f}")
        print(f"{'Time (s)':<30} {t_frenet:>12.3f} {t_world:>12.3f}")

        if fm['median_ovality'] > 0 and wm['median_ovality'] > 0:
            bias = (wm['median_ovality'] - fm['median_ovality']) / fm['median_ovality'] * 100
            print(f"\n  Ovality bias (world-frame vs Frenet): {bias:+.1f}%")
            if wm['median_ovality'] > fm['median_ovality']:
                print(f"  World-frame OVERESTIMATES ovality by {wm['median_ovality'] - fm['median_ovality']:.4f}%")

        report["cases"][name] = {
            "frenet": {**fm, "time_s": t_frenet},
            "worldframe": {**wm, "time_s": t_world},
        }
        del report["cases"][name]["frenet"]["radii"]
        del report["cases"][name]["frenet"]["ovalities"]
        del report["cases"][name]["frenet"]["eccentricities"]
        del report["cases"][name]["worldframe"]["radii"]
        del report["cases"][name]["worldframe"]["ovalities"]
        del report["cases"][name]["worldframe"]["eccentricities"]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
