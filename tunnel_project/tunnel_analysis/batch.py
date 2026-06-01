# -*- coding: utf-8 -*-
"""Headless batch pipeline: run a point-cloud file end-to-end to CSV/Excel.

Mirrors the GUI auto-pipeline (voxel -> auto-denoise -> centerline -> sections
-> parameters) without Qt, so any supported file (.txt/.xyz/.pts/.csv/.asc/
.las/.laz/.ply) produces the same per-section table and summary parameters that
the app exports. Pure NumPy/SciPy core; only the optional Excel export needs
openpyxl.

CLI:
    python -m tunnel_analysis.batch INPUT [-o OUTDIR] [--sections N]
        [--spacing M] [--label-lining] [--no-denoise] [--voxel V] [--excel]
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List, Optional

import numpy as np

from .common import format_parameter
from .models import PipelineContext, PointCloudBundle
from .io_layer import BaseLayer
from .preprocessing import PreprocessingLayer
from .geometry import GeometricLayer
from .parameters import ParameterExtractionLayer
from .exporter import TunnelExporter


def _log(cb, msg):
    if cb is not None:
        cb(msg)

def _denoise_counts(stats):
    """Integer component counts from an auto_denoise stats dict, dropping the
    bulky noise_pts array, for storage on the context / IFC export."""
    keys = ("n_raw", "n_clean", "n_removed", "n_cable", "n_light",
            "n_person", "n_wall_cable", "n_radial")
    return {k: int(stats[k]) for k in keys
            if isinstance(stats.get(k), (int, float))}


def run_pipeline(
    input_path: str,
    out_dir: Optional[str] = None,
    section_count: int = 80,
    spacing_m: Optional[float] = None,
    range_crop_m: float = 0.0,
    voxel_size: float = 0.0,
    denoise: bool = True,
    label_lining: bool = False,
    vl_box_w: float = 5.0,
    vl_box_h: float = 5.0,
    vl_cir_r: float = 2.7,
    write_excel: bool = False,
    write_ifc: bool = False,
    ifc_schema: str = "IFC4",
    ifc_components: bool = False,
    status_cb=None,
) -> Dict[str, object]:
    """Run the full analysis on one file and write CSV (and optional Excel).

    Returns a dict with output paths, section count, and summary parameters.
    section_count is used directly unless spacing_m is given, in which case the
    count is derived from the measured tunnel length / spacing.
    """
    base = BaseLayer()
    pre = PreprocessingLayer()
    geo = GeometricLayer()
    par = ParameterExtractionLayer()

    _log(status_cb, f"Loading {input_path}")
    bundle = base.load_scan(input_path)
    ctx = PipelineContext()
    ctx.scans.append(bundle)
    ctx.active_index = 0

    # Optional range crop first (MATLAB-style: drop far scanner noise cheaply).
    if range_crop_m and range_crop_m > 0:
        _log(status_cb, f"Range crop at {range_crop_m} m (sensor)")
        kept, rstats = pre.range_crop(ctx, max_range_m=float(range_crop_m), mode="sensor")
        ctx.normalized_points = kept
        _log(status_cb, f"  range crop: {rstats.get('n_clean')}/{rstats.get('n_raw')} kept")

    # Optional voxel downsample (keeps memory bounded on big scans).
    if voxel_size and voxel_size > 0:
        _log(status_cb, f"Voxel downsampling at {voxel_size} m")
        dn, _c = pre.voxel_downsample(ctx, voxel_size=float(voxel_size))
        ctx.normalized_points = dn

    # Lining isolation: label-based when requested and available, else denoise.
    if label_lining:
        _log(status_cb, "Extracting lining by label")
        kept, stats = pre.extract_lining_by_label(ctx)
        ctx.normalized_points = kept
        _log(status_cb, f"  lining: {stats.get('method')} -> {stats.get('n_clean')} pts")
    elif denoise:
        _log(status_cb, "Auto-denoising (cables/lights/people/wall cables)")
        clean, stats = pre.auto_denoise(ctx)
        ctx.normalized_points = clean
        # Persist component counts so the IFC export records detected
        # cables/lights/etc (TunnelComponents pset), matching the GUI flow.
        ctx.denoise_stats = _denoise_counts(stats)
        ctx.component_points = stats.get("component_points", {}) or {}
        _log(status_cb, f"  denoise: {stats.get('n_clean')}/{stats.get('n_raw')} kept "
              f"(cable={stats.get('n_cable', 0)}, light={stats.get('n_light', 0)}, "
              f"person={stats.get('n_person', 0)}, wall_cable={stats.get('n_wall_cable', 0)})")

    # Resolve section count from spacing if requested.
    if spacing_m and spacing_m > 1e-6:
        length = _axis_length(ctx)
        if length:
            section_count = max(8, min(400, int(round(length / spacing_m)) + 1))
            _log(status_cb, f"Spacing {spacing_m} m over {length:.2f} m -> {section_count} sections")

    _log(status_cb, f"Extracting B-spline centerline ({section_count} sections)")
    cl, fr = geo.extract_centerline_bspline(ctx, section_count=section_count)
    ctx.centerline = cl
    ctx.frenet_frames = fr

    ctx.tunnel_profile = par.detect_profile(ctx)
    _log(status_cb, f"Profile: {ctx.tunnel_profile}")

    _log(status_cb, "Computing cross-sections")
    ctx.sections = par.compute_all_sections(
        ctx, vl_box_w=vl_box_w, vl_box_h=vl_box_h, vl_cir_r=vl_cir_r)

    _log(status_cb, "Extracting parameters")
    params: Dict[str, float] = {}
    params.update(par.calc_arch_settlement(ctx))
    params.update(par.calc_horizontal_convergence(ctx))
    params.update(par.calc_ovality(ctx))
    params.update(par.calc_eccentricity(ctx))
    ctx.parameters.update(params)

    # Output paths.
    stem = os.path.splitext(os.path.basename(input_path))[0]
    out_dir = out_dir or os.path.dirname(os.path.abspath(input_path))
    os.makedirs(out_dir, exist_ok=True)
    exporter = TunnelExporter()
    csv_path = os.path.join(out_dir, f"{stem}_sections.csv")
    exporter.export_csv(ctx, csv_path)
    _log(status_cb, f"Wrote {csv_path}")

    xlsx_path = None
    if write_excel:
        xlsx_path = os.path.join(out_dir, f"{stem}_report.xlsx")
        try:
            exporter.export_excel(ctx, xlsx_path)
            _log(status_cb, f"Wrote {xlsx_path}")
        except Exception as exc:
            _log(status_cb, f"Excel export skipped: {exc}")
            xlsx_path = None

    ifc_path = None
    if write_ifc:
        ifc_path = os.path.join(out_dir, f"{stem}_model.ifc")
        try:
            from .ifc_exporter import TunnelIFCExporter
            TunnelIFCExporter().export_ifc(ctx, ifc_path, project_name=stem, schema=ifc_schema, include_components=ifc_components)
            _log(status_cb, f"Wrote {ifc_path}")
        except Exception as exc:
            _log(status_cb, f"IFC export skipped: {exc}")
            ifc_path = None

    return {
        "input": input_path,
        "csv": csv_path,
        "excel": xlsx_path,
        "ifc": ifc_path,
        "n_sections": len(ctx.sections),
        "profile": ctx.tunnel_profile,
        "parameters": params,
    }


def _axis_length(ctx: PipelineContext) -> Optional[float]:
    from .common import principal_axes, validate_xyz
    pts = ctx.working_points
    if pts is None:
        return None
    try:
        p = validate_xyz(pts)
        _c, axis, _e1, _e2 = principal_axes(p)
        proj = (p - p.mean(axis=0)) @ axis
        return float(proj.max() - proj.min())
    except Exception:
        return None


def _print_summary(result: Dict[str, object]) -> None:
    print(f"\nInput   : {result['input']}")
    print(f"Profile : {result['profile']}")
    print(f"Sections: {result['n_sections']}")
    print(f"CSV     : {result['csv']}")
    if result.get("excel"):
        print(f"Excel   : {result['excel']}")
    if result.get("ifc"):
        print(f"IFC     : {result['ifc']}")
    print("Parameters:")
    for k, v in result["parameters"].items():
        label, text, status = format_parameter(k, v)
        tag = f"  [{status}]" if status and status != "OK" else ""
        print(f"  {label}: {text}{tag}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="tunnel_analysis.batch",
        description="Headless tunnel analysis: file -> CSV/Excel.")
    ap.add_argument("input", help="point-cloud file (.txt/.xyz/.las/.ply/...)")
    ap.add_argument("-o", "--out-dir", default=None, help="output directory")
    ap.add_argument("--sections", type=int, default=80, help="number of cross-sections")
    ap.add_argument("--spacing", type=float, default=None, help="section spacing (m); overrides --sections")
    ap.add_argument("--range-crop", type=float, default=0.0, help="drop points farther than this many metres from the scan origin; 0 = off")
    ap.add_argument("--voxel", type=float, default=0.0, help="voxel size (m); 0 = off")
    ap.add_argument("--no-denoise", action="store_true", help="skip auto-denoise")
    ap.add_argument("--label-lining", action="store_true", help="isolate lining by per-point label")
    ap.add_argument("--excel", action="store_true", help="also write an Excel report")
    ap.add_argument("--ifc", action="store_true", help="also write an IFC4 BIM model")
    ap.add_argument("--ifc-schema", default="IFC4", choices=["IFC4", "IFC4X3_ADD2"], help="IFC schema; IFC4X3_ADD2 exports the centerline as IfcAlignment")
    ap.add_argument("--ifc-components", action="store_true", help="also export detected cables/lights/people as coloured IFC proxies")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 2

    result = run_pipeline(
        args.input,
        out_dir=args.out_dir,
        section_count=args.sections,
        spacing_m=args.spacing,
        range_crop_m=args.range_crop,
        voxel_size=args.voxel,
        denoise=not args.no_denoise,
        label_lining=args.label_lining,
        write_excel=args.excel,
        write_ifc=args.ifc,
        ifc_schema=args.ifc_schema,
        ifc_components=args.ifc_components,
        status_cb=lambda m: print(f"[batch] {m}"),
    )
    _print_summary(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
