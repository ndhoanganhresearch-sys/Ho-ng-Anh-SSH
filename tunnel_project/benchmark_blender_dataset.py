# -*- coding: utf-8 -*-
r"""Benchmark the Blender-generated tunnel dataset against core tool features.

Run from tunnel_project:
    ..\.venv\Scripts\python.exe benchmark_blender_dataset.py
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial import cKDTree

from tunnel_analysis.clearance import ClearanceLayer
from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.preprocessing import PreprocessingLayer


ROOT = Path(__file__).resolve().parent
DATASET_DIR = ROOT / "data" / "blender_test_suite"
REPORT_PATH = DATASET_DIR / "benchmark_report.json"


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def load_points(path: Path):
    return BaseLayer().load_scan(str(path))


def make_ctx(t0: np.ndarray | None, tn: np.ndarray) -> PipelineContext:
    ctx = PipelineContext()
    if t0 is not None:
        ctx.scans.append(PointCloudBundle(points=t0))
        ctx.scans.append(PointCloudBundle(points=tn))
        ctx.active_index = 1
    else:
        ctx.scans.append(PointCloudBundle(points=tn))
        ctx.active_index = 0
    return ctx


def add_geometry(ctx: PipelineContext, section_count: int = 48) -> dict[str, Any]:
    geo = GeometricLayer()
    par = ParameterExtractionLayer()
    t0_ctx = PipelineContext()
    t0_ctx.scans.append(ctx.scans[0])
    t0_ctx.active_index = 0
    cl, fr = geo.extract_centerline_bspline(t0_ctx, section_count=section_count)
    ctx.centerline = cl
    ctx.frenet_frames = fr
    ctx.tunnel_profile = par.detect_profile(ctx)
    sections = par.compute_all_sections(ctx, vl_box_w=5.0, vl_box_h=5.0, vl_cir_r=2.2)
    radii = np.array([s.radius_fit for s in sections if np.isfinite(s.radius_fit)], dtype=float)
    return {
        "centerline_points": int(len(cl)),
        "frames": int(len(fr)),
        "sections": int(len(sections)),
        "profile": ctx.tunnel_profile,
        "median_radius_m": float(np.nanmedian(radii)) if len(radii) else math.nan,
    }


def c2c_stats(t0: np.ndarray, tn: np.ndarray) -> dict[str, float]:
    d, _ = cKDTree(t0).query(tn, k=1, workers=-1)
    return {
        "rmse_mm": float(np.sqrt(np.mean(d * d)) * 1000.0),
        "mean_mm": float(np.mean(d) * 1000.0),
        "p95_mm": float(np.percentile(d, 95) * 1000.0),
        "max_mm": float(np.max(d) * 1000.0),
    }


def deformation_case(case_dir: Path) -> dict[str, Any]:
    t0 = load_points(case_dir / "T0.txt").points
    tn = load_points(case_dir / "Tn.txt").points
    ctx = make_ctx(t0, tn)
    geometry = add_geometry(ctx)
    par = ParameterExtractionLayer()
    heat_pts, heat_mm = par.generate_heatmap(ctx)
    centers, angles, polar = par.generate_polar_deformation_map(ctx, design_radius_m=4.0, num_bins=72)
    c2c = c2c_stats(t0, tn)
    warning_mask = np.nanmax(np.abs(polar), axis=1) >= 40.0
    warning_centers_y = centers[warning_mask, 1].tolist()
    return {
        "geometry": geometry,
        "c2c": c2c,
        "heatmap_points": int(len(heat_pts)),
        "heatmap_p95_mm": float(np.percentile(heat_mm, 95)),
        "polar_sections": int(len(centers)),
        "polar_max_abs_mm": float(np.nanmax(np.abs(polar))),
        "warning_sections_40mm": int(np.sum(warning_mask)),
        "warning_chainage_y_minmax": [float(min(warning_centers_y)), float(max(warning_centers_y))] if warning_centers_y else [],
    }


def centerline_case(case_dir: Path) -> dict[str, Any]:
    t0 = load_points(case_dir / "T0.txt").points
    tn = load_points(case_dir / "Tn.txt").points
    ctx = make_ctx(t0, tn)
    geometry = add_geometry(ctx)
    cl = ctx.centerline
    assert cl is not None
    span = cl.max(axis=0) - cl.min(axis=0)
    return {"geometry": geometry, "centerline_span_xyz_m": [float(x) for x in span]}


def denoise_case(case_dir: Path) -> dict[str, Any]:
    bundle = load_points(case_dir / "Tn_labels.txt")
    labels = np.asarray(bundle.metadata["labels"], dtype=int)
    ctx = make_ctx(None, bundle.points)
    clean, stats = PreprocessingLayer().auto_denoise(ctx)
    tree = cKDTree(clean)
    d, _ = tree.query(bundle.points, k=1, workers=-1)
    kept = d < 1e-8
    structure = labels == 1
    removable = np.isin(labels, [2, 3])
    noise_recall = float(np.sum((~kept) & removable) / max(1, np.sum(removable)))
    lining_retention = float(np.sum(kept & structure) / max(1, np.sum(structure)))
    return {
        "stats": json_safe({k: v for k, v in stats.items() if not str(k).endswith("pts") and not isinstance(v, np.ndarray)}),
        "label_noise_recall": noise_recall,
        "label_lining_retention": lining_retention,
        "raw_points": int(len(bundle.points)),
        "clean_points": int(len(clean)),
        "labels_present": sorted(int(x) for x in np.unique(labels)),
    }


def clearance_case(case_dir: Path) -> dict[str, Any]:
    bundle = load_points(case_dir / "Tn_labels.txt")
    labels = np.asarray(bundle.metadata["labels"], dtype=int)
    ctx = make_ctx(None, bundle.points)
    res = ClearanceLayer().evaluate(ctx, gauge_radius=2.2, section_len=1.0)
    pred = np.asarray(res["intruding_mask"], dtype=bool)
    truth = labels == 4
    tp = int(np.sum(pred & truth))
    fp = int(np.sum(pred & ~truth))
    fn = int(np.sum(~pred & truth))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "n_intruding": int(res["n_intruding"]),
        "max_intrusion_mm": float(res["max_intrusion_mm"]),
        "severity": res["severity"],
        "sections": int(len(res["sections"])),
        "sections_with_intrusion": int(sum(1 for sec in res["sections"] if sec["n_intruding"] > 0)),
        "precision_vs_label": precision,
        "recall_vs_label": recall,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def assert_gate(name: str, condition: bool, details: str, failures: list[str]) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}: {details}")
    if not condition:
        failures.append(f"{name}: {details}")


def main() -> int:
    start = time.perf_counter()
    manifest = json.loads((DATASET_DIR / "manifest.json").read_text(encoding="utf-8"))
    report: dict[str, Any] = {"dataset": manifest["dataset"], "cases": {}, "gates": []}
    failures: list[str] = []

    print("== Blender Dataset Benchmark ==")
    print(f"dataset_dir={DATASET_DIR}")

    # Load gate already covers every file and label metadata.
    for case in manifest["cases"]:
        cid = case["case_id"]
        cdir = DATASET_DIR / cid
        for filename in ["T0.txt", "Tn.txt", "T0_labels.txt", "Tn_labels.txt"]:
            bundle = load_points(cdir / filename)
            assert_gate(
                f"load {cid}/{filename}",
                len(bundle.points) > 1000,
                f"points={len(bundle.points):,}",
                failures,
            )

    clean = deformation_case(DATASET_DIR / "case_01_clean_reference")
    report["cases"]["case_01_clean_reference"] = clean
    assert_gate("clean baseline c2c", clean["c2c"]["p95_mm"] < 20.0, f"p95={clean['c2c']['p95_mm']:.2f}mm", failures)
    assert_gate("clean baseline sections", clean["geometry"]["sections"] >= 40, f"sections={clean['geometry']['sections']}", failures)

    deform = deformation_case(DATASET_DIR / "case_02_local_deformation")
    report["cases"]["case_02_local_deformation"] = deform
    assert_gate("local deformation magnitude", deform["polar_max_abs_mm"] >= 60.0, f"polar_max={deform['polar_max_abs_mm']:.1f}mm", failures)
    assert_gate("local warning sections", 1 <= deform["warning_sections_40mm"] <= 20, f"warning_sections={deform['warning_sections_40mm']}", failures)

    noise = denoise_case(DATASET_DIR / "case_03_noise_and_cables")
    report["cases"]["case_03_noise_and_cables"] = noise
    assert_gate("denoise noise recall", noise["label_noise_recall"] >= 0.40, f"recall={noise['label_noise_recall']:.2f}", failures)
    assert_gate("denoise lining retention", noise["label_lining_retention"] >= 0.75, f"retention={noise['label_lining_retention']:.2f}", failures)

    clearance = clearance_case(DATASET_DIR / "case_04_clearance_intrusion")
    report["cases"]["case_04_clearance_intrusion"] = clearance
    assert_gate("clearance violation", clearance["severity"] in {"warning", "critical"} and clearance["n_intruding"] > 0, f"severity={clearance['severity']} n={clearance['n_intruding']}", failures)
    assert_gate("clearance recall", clearance["recall_vs_label"] >= 0.90, f"recall={clearance['recall_vs_label']:.2f}", failures)

    curved = centerline_case(DATASET_DIR / "case_05_curved_centerline")
    report["cases"]["case_05_curved_centerline"] = curved
    assert_gate("curved centerline sections", curved["geometry"]["sections"] >= 40, f"sections={curved['geometry']['sections']}", failures)
    assert_gate("curved centerline x-span", curved["centerline_span_xyz_m"][0] >= 0.8, f"x_span={curved['centerline_span_xyz_m'][0]:.2f}m", failures)

    sparse = centerline_case(DATASET_DIR / "case_06_occlusion_sparse")
    report["cases"]["case_06_occlusion_sparse"] = sparse
    assert_gate("sparse sections", sparse["geometry"]["sections"] >= 35, f"sections={sparse['geometry']['sections']}", failures)
    assert_gate("sparse radius finite", 3.0 <= sparse["geometry"]["median_radius_m"] <= 4.5, f"median_radius={sparse['geometry']['median_radius_m']:.2f}m", failures)

    report["runtime_seconds"] = round(time.perf_counter() - start, 3)
    report["failures"] = failures
    REPORT_PATH.write_text(json.dumps(json_safe(report), indent=2), encoding="utf-8")

    print(f"report={REPORT_PATH}")
    if failures:
        print(f"RESULT: FAIL ({len(failures)} failures)")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("RESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
