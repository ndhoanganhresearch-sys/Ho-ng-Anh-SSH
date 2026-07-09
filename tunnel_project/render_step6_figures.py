"""Headless render of REAL Step 6 outputs for the explainer deck.

Runs the actual TimeSeriesLayer core on the time_series_deformation dataset
(T0..T5), then renders figures with matplotlib (and a PyVista off-screen 3D
shot if the GL stack allows). Prints a JSON block with the real numbers so the
deck builder can feed native charts.
"""
import os, sys, json, warnings
os.environ.setdefault("PYTHONUTF8", "1")
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm

LANG = "en" if "--en" in sys.argv else "vi"
SUF = "_en" if LANG == "en" else ""
TXT = {
    "vi": {
        "cbar": "Chuyển vị M3C2 (mm)  —  âm = lún/hội tụ vào",
        "xlab": "Chainage dọc trục hầm (m)",
        "ylab": "Góc quanh vành (°)  90=đỉnh · 270=đáy",
        "title": "Bản đồ biến dạng M3C2 thật (trải phẳng): T0 → Tn",
    },
    "en": {
        "cbar": "M3C2 displacement (mm)  —  negative = inward",
        "xlab": "Chainage along tunnel axis (m)",
        "ylab": "Angle around ring (°)  90=crown · 270=invert",
        "title": "Real M3C2 deformation map (unrolled): T0 → Tn",
    },
}[LANG]

from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.timeseries import TimeSeriesLayer

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "step6_figures")
OUT = os.path.abspath(OUT)
os.makedirs(OUT, exist_ok=True)
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "time_series_deformation")

NAVY = "#0F2A43"; TEAL = "#0E8C80"; MUTED = "#64748B"; CRIT = "#D7263D"; CAUT = "#E0A100"

bl = BaseLayer()
labels = ["T0", "T1", "T2", "T3", "T4", "T5"]
epochs = [np.asarray(bl.load_scan(os.path.join(DATA, f"{t}.las")).points, dtype=np.float64) for t in labels]
print(f"[load] epochs: {[e.shape[0] for e in epochs]}", file=sys.stderr)

ts = TimeSeriesLayer()

# ---- Real multi-epoch trend (M3C2 each Tn vs T0) ----
series = ts.spatiotemporal_series(epochs, labels=labels[1:], cyl_radius=0.5, normal_radius=0.6)
method = series["method"]
med = [0.0] + [float(x) for x in series["median_mm"]]
p95 = [0.0] + [float(x) for x in series["p95_abs_mm"]]
mx  = [0.0] + [float(x) for x in series["max_abs_mm"]]
print(f"[trend] method={method} max_abs={['%.1f'%v for v in mx]}", file=sys.stderr)

# ---- Real forecast on the max_abs series ----
fc = ts.forecast_threshold_crossing(series, metric="max_abs_mm",
                                    caution_mm=10.0, critical_mm=25.0, degree=2)

# ---- Real M3C2 map T0 -> T5 ----
m3 = ts.m3c2_distances(epochs[0], epochs[5], cyl_radius=0.5, normal_radius=0.6)
cp = np.asarray(m3["corepoints"], dtype=np.float64)
dist = np.asarray(m3["distance_mm"], dtype=np.float64)
finite = np.isfinite(dist)
cp_f, dist_f = cp[finite], dist[finite]

# Unroll: detect the long (chainage) axis, use angle around the ring for Y.
ext = cp_f.max(axis=0) - cp_f.min(axis=0)
ax_long = int(np.argmax(ext))
o1, o2 = [i for i in range(3) if i != ax_long]
chain = cp_f[:, ax_long] - cp_f[:, ax_long].min()
ca, cb_ = cp_f[:, o1].mean(), cp_f[:, o2].mean()
ang = (np.degrees(np.arctan2(cp_f[:, o2] - cb_, cp_f[:, o1] - ca)) + 360.0) % 360.0

# ===== Figure A: unrolled M3C2 deformation map (chainage x angle) =====
figA, axA = plt.subplots(figsize=(8.6, 3.4), dpi=150)
vmax = float(np.nanpercentile(np.abs(dist_f), 99)) or 1.0
sc = axA.scatter(chain, ang, c=dist_f, cmap="RdBu_r", s=4, vmin=-vmax, vmax=vmax, linewidths=0)
cb = figA.colorbar(sc, ax=axA, pad=0.01)
cb.set_label(TXT["cbar"], fontsize=9, color=NAVY)
cb.ax.tick_params(labelsize=8)
axA.set_xlabel(TXT["xlab"], fontsize=9, color=NAVY)
axA.set_ylabel(TXT["ylab"], fontsize=9, color=NAVY)
axA.set_yticks([0, 90, 180, 270, 360])
axA.set_title(f"{TXT['title']}  —  {cp_f.shape[0]:,} corepoints, method={method}",
              fontsize=10, color=NAVY, weight="bold")
axA.tick_params(labelsize=8, colors=MUTED)
for sp in axA.spines.values(): sp.set_color("#D8E0E8")
figA.tight_layout()
pA = os.path.join(OUT, f"m3c2_map{SUF}.png"); figA.savefig(pA, bbox_inches="tight"); plt.close(figA)
print(f"[fig] {pA}", file=sys.stderr)

# ===== Figure B: 3D point cloud coloured by displacement (PyVista off-screen) =====
p3d = None
try:
    import pyvista as pv
    pv.OFF_SCREEN = True
    pl = pv.Plotter(off_screen=True, window_size=[1200, 620])
    pl.set_background("white")
    cloud = pv.PolyData(cp_f)
    cloud["mm"] = dist_f
    pl.add_mesh(cloud, scalars="mm", cmap="RdBu_r", clim=[-vmax, vmax],
                point_size=3, render_points_as_spheres=False,
                scalar_bar_args={"title": "M3C2 (mm)", "color": "black"})
    pl.view_isometric()
    pl.camera.zoom(1.3)
    p3d = os.path.join(OUT, f"m3c2_3d{SUF}.png")
    pl.screenshot(p3d)
    pl.close()
    print(f"[fig] {p3d}", file=sys.stderr)
except Exception as e:
    print(f"[fig] 3D skipped: {str(e)[:120]}", file=sys.stderr)
    p3d = None

result = {
    "method": method,
    "labels": labels,
    "median_mm": med,
    "p95_abs_mm": p95,
    "max_abs_mm": mx,
    "forecast": {
        "ok": bool(fc["ok"]),
        "metric": fc["metric"],
        "rate_per_unit": fc["rate_per_unit"],
        "r_squared": fc["r_squared"],
        "t_caution": fc["t_caution"], "t_critical": fc["t_critical"],
        "low_confidence": fc["low_confidence"],
        "summary": fc["summary"],
    },
    "m3c2": {
        "n_corepoints": int(cp_f.shape[0]),
        "min_mm": float(np.nanmin(dist_f)),
        "max_mm": float(np.nanmax(dist_f)),
        "p99abs_mm": vmax,
    },
    "fig_map": pA,
    "fig_3d": p3d,
}
print("===JSON===")
print(json.dumps(result, indent=2, ensure_ascii=False))
