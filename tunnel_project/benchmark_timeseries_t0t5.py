# -*- coding: utf-8 -*-
r"""Benchmark: Time-Series Deformation T0–T5

Runs the full pipeline on the time_series_deformation dataset:
  1. Load all 6 epochs (T0–T5), skip registration (synthetic, already aligned)
  2. Extract centerline + Frenet frames from T0
  3. For each baseline pair (T0 vs Tn): parameter analysis + deformation quantification
  4. For each incremental pair (Tn vs Tn+1): same analysis
  5. Compare with ground_truth.csv
  6. Multi-epoch spatiotemporal series + threshold forecast
  7. Visualize: crown/convergence trend, per-section polar map, M3C2 heatmap

Run from tunnel_project:
    ..\.venv\Scripts\python.exe benchmark_timeseries_t0t5.py
"""
import sys, os, json, time, csv
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import numpy as np
import warnings; warnings.filterwarnings("ignore")

from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.timeseries import TimeSeriesLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle
from tunnel_analysis.common import validate_xyz

# ── paths ──
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "time_series_deformation"
OUT  = ROOT / "output" / "timeseries_benchmark"
OUT.mkdir(parents=True, exist_ok=True)

EPOCH_NAMES = [f"T{i}" for i in range(6)]
PASS = FAIL = 0

def ck(name, cond, info=""):
    global PASS, FAIL
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {name}" + (f"  -> {info}" if info else ""))
    if cond: PASS += 1
    else:    FAIL += 1

def step(msg):
    print(f"\n{'─'*60}\n  {msg}\n{'─'*60}")


# ══════════════════════════════════════════════════════════════
print("=" * 70)
print("  TIME-SERIES DEFORMATION BENCHMARK  T0 – T5")
print("=" * 70)
t_global = time.perf_counter()

# ── Load ground truth ──
gt_rows = []
with open(DATA / "ground_truth.csv", newline="") as f:
    for row in csv.DictReader(f):
        row["value_mm"] = float(row["value_mm"])
        row["chainage_m"] = float(row["chainage_m"])
        gt_rows.append(row)

def gt_value(epoch, dtype):
    for r in gt_rows:
        if r["epoch"] == epoch and r["deformation_type"] == dtype:
            return r["value_mm"]
    return 0.0


# ═══════════════════════════════════════════════════════════════
# STEP 1: Load all 6 epochs
# ═══════════════════════════════════════════════════════════════
step("1. Load all epochs T0–T5")
loader = BaseLayer()
epochs_bundles = {}
epochs_points  = {}
for name in EPOCH_NAMES:
    fp = DATA / f"{name}.las"
    b = loader.load_scan(str(fp), max_points=200_000)
    epochs_bundles[name] = b
    epochs_points[name]  = validate_xyz(b.points)
    print(f"    {name}: {b.points.shape[0]:,} points")
ck("all 6 epochs loaded", len(epochs_points) == 6)


# ═══════════════════════════════════════════════════════════════
# STEP 2: Centerline + Frenet frames from T0
# ═══════════════════════════════════════════════════════════════
step("2. Extract centerline + Frenet frames from T0")
geo = GeometricLayer()
par = ParameterExtractionLayer()

ctx_t0 = PipelineContext()
ctx_t0.scans = [PointCloudBundle(points=epochs_points["T0"])]
ctx_t0.active_index = 0
cl, fr = geo.extract_centerline_bspline(ctx_t0, section_count=80)
ctx_t0.centerline = cl
ctx_t0.frenet_frames = fr
ctx_t0.tunnel_profile = par.detect_profile(ctx_t0)
ck("centerline extracted", cl is not None, f"{len(fr)} frames")
ck("profile detected", ctx_t0.tunnel_profile == "Circle", f"{ctx_t0.tunnel_profile}")

# Section epsilon for later reference
eps = par._section_epsilon(ctx_t0)
print(f"    section epsilon = {eps:.4f} m")

# Design radius from manifest
with open(DATA / "manifest.json") as f:
    manifest = json.load(f)
design_r = manifest["tunnel"]["radius_m"]
print(f"    design radius = {design_r} m")


# ═══════════════════════════════════════════════════════════════
# STEP 3: Baseline pairs — T0 vs T1, T0 vs T2, ..., T0 vs T5
# ═══════════════════════════════════════════════════════════════
step("3. Baseline analysis: T0 vs Tn (accumulated deformation)")

baseline_results = {}
for n in range(1, 6):
    tn_name = f"T{n}"
    print(f"\n  ── T0 vs {tn_name} ──")

    ctx = PipelineContext()
    ctx.scans = [
        PointCloudBundle(points=epochs_points["T0"]),
        PointCloudBundle(points=epochs_points[tn_name]),
    ]
    ctx.active_index = 1
    ctx.registered_points = epochs_points[tn_name]  # already aligned
    ctx.centerline = cl
    ctx.frenet_frames = fr
    ctx.tunnel_profile = ctx_t0.tunnel_profile
    ctx.design_radius = design_r

    # Compute deformation parameters
    crown = par.calc_arch_settlement(ctx)
    conv  = par.calc_horizontal_convergence(ctx)
    oval  = par.calc_ovality(ctx)
    ecc   = par.calc_eccentricity(ctx)

    # Heatmap + polar map
    heat_pts, heat_mm = par.generate_heatmap(ctx)
    try:
        centers, angles, polar = par.generate_polar_deformation_map(ctx, design_radius_m=design_r)
        ctx.polar_map = polar
        ctx.polar_angles = angles
        ctx.polar_centers = centers
    except Exception as e:
        print(f"    [WARN] polar map: {e}")
        polar = None

    # Ground truth comparison
    gt_crown = gt_value(tn_name, "crown_settlement")
    gt_conv  = gt_value(tn_name, "sidewall_convergence")
    gt_local = gt_value(tn_name, "local_damage")

    crown_max = crown.get("crown_settlement_max_mm", 0.0)
    conv_max  = conv.get("lateral_convergence_max_mm", 0.0)

    result = {
        "pair": f"T0-{tn_name}",
        "crown_max_mm": round(crown_max, 2),
        "crown_mean_mm": round(crown.get("crown_settlement_mm", 0.0), 2),
        "crown_ref": crown.get("settlement_reference", "?"),
        "convergence_max_mm": round(conv_max, 2),
        "convergence_mean_mm": round(conv.get("lateral_convergence_mm", 0.0), 2),
        "convergence_ref": conv.get("convergence_reference", "?"),
        "ovality_mean_pct": round(oval.get("ovality_mean_pct", 0.0), 4),
        "eccentricity_mean_mm": round(ecc.get("eccentricity_mean_mm", 0.0), 2),
        "gt_crown_mm": gt_crown,
        "gt_convergence_mm": gt_conv,
        "gt_local_mm": gt_local,
        "heatmap_p95_mm": round(float(np.nanpercentile(np.abs(heat_mm), 95)), 2),
        "heatmap_max_mm": round(float(np.nanmax(np.abs(heat_mm))), 2),
    }
    baseline_results[tn_name] = result

    print(f"    Crown max:  {crown_max:+.2f} mm  (GT: {gt_crown:+.1f} mm)")
    print(f"    Conv max:   {conv_max:+.2f} mm  (GT: {gt_conv:+.1f} mm)")
    print(f"    Heatmap p95: {result['heatmap_p95_mm']:.2f} mm, max: {result['heatmap_max_mm']:.2f} mm")
    print(f"    Ovality:    {result['ovality_mean_pct']:.4f}%")
    print(f"    Ecc:        {result['eccentricity_mean_mm']:.2f} mm")

    ck(f"{tn_name} crown uses T0 ref", crown.get("settlement_reference") == "T0_per_section")
    if abs(gt_crown) > 1.0:
        ck(f"{tn_name} crown detected (>50% of GT)", crown_max > abs(gt_crown) * 0.5,
           f"measured={crown_max:.1f} GT={gt_crown:.1f}")


# ═══════════════════════════════════════════════════════════════
# STEP 4: Incremental pairs — T0→T1, T1→T2, ..., T4→T5
# ═══════════════════════════════════════════════════════════════
step("4. Incremental analysis: Tn vs Tn+1")

incremental_results = {}
for n in range(5):
    t_ref = f"T{n}"
    t_mon = f"T{n+1}"
    print(f"\n  ── {t_ref} vs {t_mon} ──")

    ctx = PipelineContext()
    ctx.scans = [
        PointCloudBundle(points=epochs_points[t_ref]),
        PointCloudBundle(points=epochs_points[t_mon]),
    ]
    ctx.active_index = 1
    ctx.registered_points = epochs_points[t_mon]
    ctx.centerline = cl
    ctx.frenet_frames = fr
    ctx.tunnel_profile = ctx_t0.tunnel_profile
    ctx.design_radius = design_r

    crown = par.calc_arch_settlement(ctx)
    conv  = par.calc_horizontal_convergence(ctx)

    crown_max = crown.get("crown_settlement_max_mm", 0.0)
    conv_max  = conv.get("lateral_convergence_max_mm", 0.0)

    result = {
        "pair": f"{t_ref}-{t_mon}",
        "crown_max_mm": round(crown_max, 2),
        "crown_mean_mm": round(crown.get("crown_settlement_mm", 0.0), 2),
        "convergence_max_mm": round(conv_max, 2),
        "convergence_mean_mm": round(conv.get("lateral_convergence_mm", 0.0), 2),
    }
    incremental_results[f"{t_ref}-{t_mon}"] = result
    print(f"    Crown delta max:  {crown_max:+.2f} mm")
    print(f"    Conv delta max:   {conv_max:+.2f} mm")


# ═══════════════════════════════════════════════════════════════
# STEP 5: M3C2 / C2C multi-epoch spatiotemporal series
# ═══════════════════════════════════════════════════════════════
step("5. Multi-epoch spatiotemporal series (M3C2 / C2C)")

ts = TimeSeriesLayer()
all_pts = [epochs_points[f"T{i}"] for i in range(6)]
series = ts.spatiotemporal_series(
    all_pts,
    labels=[f"T{i}" for i in range(1, 6)],
    cyl_radius=0.3,
    normal_radius=0.3,
    max_corepoints=15_000,
)
print(f"    Method: {series['method']}")
print(f"    Corepoints: {series['corepoints'].shape[0]:,}")
for i, lbl in enumerate(series["labels"]):
    med = series["median_mm"][i]
    p95 = series["p95_abs_mm"][i]
    print(f"    {lbl}: median={med:+.2f} mm, p95_abs={p95:.2f} mm")

ck("spatiotemporal series computed", series["distance_matrix_mm"].shape[0] == 5)


# ═══════════════════════════════════════════════════════════════
# STEP 6: Threshold forecast
# ═══════════════════════════════════════════════════════════════
step("6. Threshold crossing forecast")

forecast = ts.forecast_threshold_crossing(
    series,
    times=[1, 2, 3, 4, 5],
    caution_mm=10.0,
    critical_mm=25.0,
    degree=2,
    min_epochs=3,
)
print(f"    Rate:        {forecast.get('rate_per_unit', 0):.2f} mm/epoch")
print(f"    R²:          {forecast.get('r_squared', 0):.4f}")
print(f"    T_caution:   {forecast.get('t_caution')}")
print(f"    T_critical:  {forecast.get('t_critical')}")
print(f"    Low confidence: {forecast.get('low_confidence', False)}")
ck("forecast computed", forecast.get("rate_per_unit") is not None)


# ═══════════════════════════════════════════════════════════════
# STEP 7: Visualization
# ═══════════════════════════════════════════════════════════════
step("7. Generate visualizations")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("    [WARN] matplotlib not available, skipping plots")

if HAS_MPL:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Time-Series Deformation Benchmark  T0 → T5", fontsize=14, fontweight="bold")

    # ── 7a: Crown settlement trend (baseline) ──
    ax = axes[0, 0]
    epochs_x = list(range(6))
    gt_crown_vals = [gt_value(f"T{i}", "crown_settlement") for i in range(6)]
    measured_crown = [0.0] + [baseline_results[f"T{i}"]["crown_max_mm"] for i in range(1, 6)]
    ax.plot(epochs_x, gt_crown_vals, "r--o", label="Ground Truth (crown)", linewidth=2)
    ax.plot(epochs_x, [-v for v in measured_crown], "b-s", label="Measured (crown max)", linewidth=2)
    ax.axhline(-10, color="orange", linestyle=":", alpha=0.7, label="Caution (10mm)")
    ax.axhline(-25, color="red", linestyle=":", alpha=0.7, label="Critical (25mm)")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Settlement (mm)")
    ax.set_title("Crown Settlement: GT vs Measured")
    ax.set_xticks(epochs_x)
    ax.set_xticklabels(EPOCH_NAMES)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── 7b: Convergence trend (baseline) ──
    ax = axes[0, 1]
    gt_conv_vals = [gt_value(f"T{i}", "sidewall_convergence") for i in range(6)]
    measured_conv = [0.0] + [baseline_results[f"T{i}"]["convergence_max_mm"] for i in range(1, 6)]
    ax.plot(epochs_x, gt_conv_vals, "r--o", label="Ground Truth (convergence)", linewidth=2)
    ax.plot(epochs_x, [-v for v in measured_conv], "g-s", label="Measured (conv max)", linewidth=2)
    ax.axhline(-15, color="orange", linestyle=":", alpha=0.7, label="Caution (15mm)")
    ax.axhline(-30, color="red", linestyle=":", alpha=0.7, label="Critical (30mm)")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Convergence (mm)")
    ax.set_title("Sidewall Convergence: GT vs Measured")
    ax.set_xticks(epochs_x)
    ax.set_xticklabels(EPOCH_NAMES)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── 7c: M3C2 p95 trend ──
    ax = axes[1, 0]
    p95_vals = series["p95_abs_mm"]
    median_vals = series["median_mm"]
    ax.bar(range(1, 6), p95_vals, alpha=0.6, color="steelblue", label="p95 abs (mm)")
    ax.plot(range(1, 6), np.abs(median_vals), "ro-", label="|median| (mm)", linewidth=2)
    ax.set_xlabel("Epoch (vs T0)")
    ax.set_ylabel("Displacement (mm)")
    ax.set_title(f"M3C2 Displacement Trend ({series['method']})")
    ax.set_xticks(range(1, 6))
    ax.set_xticklabels([f"T{i}" for i in range(1, 6)])
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── 7d: Incremental crown deltas ──
    ax = axes[1, 1]
    pairs = [f"T{n}-T{n+1}" for n in range(5)]
    inc_crown = [incremental_results[p]["crown_max_mm"] for p in pairs]
    inc_conv  = [incremental_results[p]["convergence_max_mm"] for p in pairs]
    x = np.arange(5)
    w = 0.35
    ax.bar(x - w/2, inc_crown, w, label="Crown delta (mm)", color="steelblue")
    ax.bar(x + w/2, inc_conv,  w, label="Conv delta (mm)", color="seagreen")
    ax.set_xlabel("Pair")
    ax.set_ylabel("Incremental deformation (mm)")
    ax.set_title("Incremental Deformation per Epoch Step")
    ax.set_xticks(x)
    ax.set_xticklabels(pairs, fontsize=8)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = OUT / "timeseries_benchmark_overview.png"
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)
    print(f"    Saved: {fig_path}")
    ck("overview figure saved", fig_path.exists())

    # ── 7e: Per-section crown profile at each epoch ──
    fig2, ax2 = plt.subplots(figsize=(12, 5))
    chainages = [fr["center"][1] for fr in fr]  # Y = chainage for straight tunnel
    for n in range(6):
        tn_name = f"T{n}"
        pts = epochs_points[tn_name]
        crowns = []
        for frame in ctx_t0.frenet_frames:
            C, T_vec, B_vec = frame["center"], frame["T"], frame["B"]
            mask = np.abs((pts - C) @ T_vec) < eps
            sl = pts[mask]
            if len(sl) < 5:
                crowns.append(np.nan)
            else:
                crowns.append(float(np.percentile((sl - C) @ B_vec, 99)) * 1e3)
        style = "-" if n == 0 else "--"
        ax2.plot(chainages, crowns, style, label=tn_name, linewidth=1.5 if n == 0 else 1.0)

    # Mark GT deformation locations
    for spec in manifest["deformation_specs"]:
        ch = spec["chainage_m"]
        ax2.axvline(ch, color="red", linestyle=":", alpha=0.4)
        ax2.text(ch, ax2.get_ylim()[1], f'{spec["type"]}\n@{ch}m',
                 fontsize=7, ha="center", va="top", color="red")

    ax2.set_xlabel("Chainage (m)")
    ax2.set_ylabel("Crown height (mm)")
    ax2.set_title("Crown Profile per Epoch — Section-by-Section")
    ax2.legend(fontsize=8, ncol=6)
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    fig2_path = OUT / "crown_profile_per_epoch.png"
    fig2.savefig(fig2_path, dpi=150)
    plt.close(fig2)
    print(f"    Saved: {fig2_path}")

    # ── 7f: M3C2 heatmap for T0 vs T5 ──
    fig3, ax3 = plt.subplots(figsize=(12, 4))
    # Run M3C2 for T0 vs T5
    m3c2_t5 = ts.m3c2_distances(
        epochs_points["T0"], epochs_points["T5"],
        cyl_radius=0.3, normal_radius=0.3, max_corepoints=15_000,
    )
    cp = m3c2_t5["corepoints"]
    dist = m3c2_t5["distance_mm"]
    valid = np.isfinite(dist)
    sc = ax3.scatter(cp[valid, 1], cp[valid, 2], c=dist[valid], cmap="RdBu_r",
                     s=2, vmin=-50, vmax=50)
    plt.colorbar(sc, ax=ax3, label="Displacement (mm)")
    ax3.set_xlabel("Y — chainage (m)")
    ax3.set_ylabel("Z (m)")
    ax3.set_title(f"M3C2 Displacement Map: T0 vs T5 ({m3c2_t5['method']})")
    ax3.set_aspect("equal")
    plt.tight_layout()
    fig3_path = OUT / "m3c2_heatmap_T0_T5.png"
    fig3.savefig(fig3_path, dpi=150)
    plt.close(fig3)
    print(f"    Saved: {fig3_path}")


# ═══════════════════════════════════════════════════════════════
# STEP 8: Save results JSON
# ═══════════════════════════════════════════════════════════════
step("8. Save benchmark results")

report = {
    "dataset": "time_series_deformation",
    "epochs": 6,
    "design_radius_m": design_r,
    "tunnel_length_m": manifest["tunnel"]["length_m"],
    "method": series["method"],
    "baseline_pairs": baseline_results,
    "incremental_pairs": incremental_results,
    "spatiotemporal": {
        "labels": series["labels"],
        "median_mm": series["median_mm"].tolist(),
        "p95_abs_mm": series["p95_abs_mm"].tolist(),
    },
    "forecast": {
        "rate_per_unit": forecast.get("rate_per_unit"),
        "r_squared": forecast.get("r_squared"),
        "t_caution": forecast.get("t_caution"),
        "t_critical": forecast.get("t_critical"),
        "low_confidence": forecast.get("low_confidence"),
    },
}

report_path = OUT / "timeseries_benchmark_report.json"
with open(report_path, "w") as f:
    json.dump(report, f, indent=2, default=str)
print(f"    Saved: {report_path}")
ck("report saved", report_path.exists())


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
elapsed = time.perf_counter() - t_global
print(f"\n{'='*70}")
print(f"  DONE  {PASS} passed / {FAIL} failed  ({elapsed:.1f}s)")
print(f"{'='*70}")

if FAIL > 0:
    print("\n  *** SOME CHECKS FAILED — review output above ***")
    sys.exit(1)
