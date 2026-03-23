"""
Standalone Point Cloud Analysis Tool - LOCAL AI EDITION (Ollama) - v4.6
Author: Nguyen Duy Hoang Anh - Smart Structure Lab (CBNU)
Objective: Osong Tunnel LiDAR Data Processing (2026-2028)

Changelog:
  v4.1 - Tunnel Length Calculation (Y-range + PCA)
  v4.2 - Preset Profiles, Friendly errors, Save/Load custom preset
  v4.3 - Centerline Extraction (Task 2026)
  v4.6 - Tab Interface UX overhaul
         · Tab 1 📁 Import   — file loading, preview, file info
         · Tab 2 ⚙️ Analysis  — preset, parameters, mode, run
         · Tab 3 🛤️ Centerline — extraction, 2D/3D view, export
         · Tab 4 📊 Results   — 3D view, mesh, slicing, length, export
         · Persistent status bar + progress shared across all tabs
         · AI Assistant docked at bottom (always visible)
"""
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
import threading
import os
import csv
import json
import requests
import re
import numpy as np
import laspy
import open3d as o3d
import sv_ttk

try:
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button as MplButton
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import alphashape
    ALPHASHAPE_AVAILABLE = True
except ImportError:
    ALPHASHAPE_AVAILABLE = False

# ──────────────────────────────────────────────────────────
OLLAMA_URL  = "http://localhost:11434/api/generate"
LOCAL_MODEL = "llama3"

PRESET_PROFILES = {
    "🏔️ NATM Tunnel (Osong)": {
        "description": "NATM soft-ground tunnel optimized for Osong project (CBNU 2026-2028).",
        "MIN_WALL_HEIGHT": 5.0, "RANSAC_DISTANCE": 0.10,
        "GROUND_ANGLE": 15.0,  "WALL_ANGLE": 75.0,
    },
    "🚇 Metro Tunnel": {
        "description": "Urban metro / subway tunnel. Circular or horseshoe, ~6-10 m diameter.",
        "MIN_WALL_HEIGHT": 4.0, "RANSAC_DISTANCE": 0.08,
        "GROUND_ANGLE": 12.0,  "WALL_ANGLE": 70.0,
    },
    "🛣️ Highway Tunnel": {
        "description": "Road highway tunnel. Wide arched section, ~10-14 m wide.",
        "MIN_WALL_HEIGHT": 5.0, "RANSAC_DISTANCE": 0.10,
        "GROUND_ANGLE": 15.0,  "WALL_ANGLE": 75.0,
    },
    "🚆 Railway Tunnel": {
        "description": "Single or double-track railway. Narrow, tall arch profile.",
        "MIN_WALL_HEIGHT": 5.5, "RANSAC_DISTANCE": 0.09,
        "GROUND_ANGLE": 10.0,  "WALL_ANGLE": 72.0,
    },
    "⛏️ Mine Shaft": {
        "description": "Mining tunnel / shaft. Irregular walls, low clearance.",
        "MIN_WALL_HEIGHT": 2.0, "RANSAC_DISTANCE": 0.15,
        "GROUND_ANGLE": 20.0,  "WALL_ANGLE": 60.0,
    },
    "🏗️ Box Culvert": {
        "description": "Rectangular concrete box culvert. Flat roof/floor, vertical walls.",
        "MIN_WALL_HEIGHT": 2.5, "RANSAC_DISTANCE": 0.05,
        "GROUND_ANGLE": 8.0,   "WALL_ANGLE": 80.0,
    },
    "⚙️ Custom": {
        "description": "Enter parameters manually. You can save as a custom preset.",
        "MIN_WALL_HEIGHT": None, "RANSAC_DISTANCE": None,
        "GROUND_ANGLE": None,   "WALL_ANGLE": None,
    },
}

FRIENDLY_ERRORS = {
    "only 0 walls":  "❌ No tunnel walls detected.\n→ Try lowering Wall Angle (e.g. 60°).",
    "only 1 walls":  "❌ Only 1 wall found.\n→ Lower Min Wall Height or adjust Wall Angle.",
    "empty":         "❌ LAS file appears empty.\n→ Check file validity.",
    "segment_plane": "❌ RANSAC failed.\n→ Increase RANSAC Distance (e.g. 0.15 m).",
}

def friendly_error(msg):
    ml = str(msg).lower()
    for k, v in FRIENDLY_ERRORS.items():
        if k in ml: return v
    return f"❌ Unexpected error:\n{msg}"


# ──────────────────────────────────────────────────────────
# CORE ALGORITHMS (unchanged from v4.3)
# ──────────────────────────────────────────────────────────

class InteractivePlot:
    def __init__(self, g, w1, w2, y, design=None, show_alpha=False):
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror("Error", "Matplotlib required."); return
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.title0 = f"Cross-section at Y ≈ {y:.2f} m"
        self.ax.set_title(self.title0)
        self._draw(g, w1, w2, design, show_alpha)
        self.ax.set_xlabel("X (m)"); self.ax.set_ylabel("Z (m)")
        self.ax.grid(True); self.ax.axis("equal"); self.ax.legend()
        self.mode = None; self.pts = []
        self.fig.canvas.mpl_connect("button_press_event", self._click)
        ax_b = self.fig.add_axes([0.7, 0.01, 0.15, 0.05])
        MplButton(ax_b, "Measure Distance").on_clicked(
            lambda _: self._set_mode("distance"))
        plt.show()

    def _draw(self, g, w1, w2, design, show_alpha):
        if w1.size > 0 and w2.size > 0:
            l, r = (w1, w2) if w1[:, 0].mean() < w2[:, 0].mean() else (w2, w1)
        else:
            l, r = w1, w2
        if g.size  > 0: self.ax.scatter(g[:, 0],  g[:, 2],  s=2, color="saddlebrown", label="Ground")
        if design is not None and len(design) > 1:
            if l.size > 0: self.ax.scatter(l[:, 0], l[:, 2], s=2, color="darkgray", label="Actual Wall")
            if r.size > 0: self.ax.scatter(r[:, 0], r[:, 2], s=2, color="darkgray")
            self.ax.plot(design[:, 0], design[:, 1], "g--", lw=2, label="Design Profile")
        else:
            if l.size > 0: self.ax.scatter(l[:, 0], l[:, 2], s=2, color="blue", label="Left Wall")
            if r.size > 0: self.ax.scatter(r[:, 0], r[:, 2], s=2, color="red",  label="Right Wall")
        if show_alpha and ALPHASHAPE_AVAILABLE:
            pts2d = [p[:, [0, 2]] for p in [g, l, r] if p.size > 0]
            if pts2d:
                pts2d = np.vstack(pts2d)
                if len(pts2d) > 3:
                    try:
                        ag = alphashape.alphashape(pts2d, 0.5)
                        if hasattr(ag, "exterior"):
                            x, y = ag.exterior.coords.xy
                            self.ax.plot(x, y, color="gold", lw=2, label="AlphaShape")
                    except Exception: pass

    def _set_mode(self, mode):
        self.mode = mode; self.pts = []
        self.ax.set_title("Click 2 points to measure", color="green")
        self.fig.canvas.draw_idle()

    def _click(self, event):
        if not self.mode or event.inaxes != self.ax or event.button != 1: return
        ix, iy = event.xdata, event.ydata
        if ix is None: return
        self.pts.append((ix, iy))
        self.ax.plot(ix, iy, "gx", ms=10); self.fig.canvas.draw_idle()
        if len(self.pts) == 2:
            p1, p2 = self.pts
            dx = abs(p1[0]-p2[0]); dz = abs(p1[1]-p2[1]); d = np.sqrt(dx**2+dz**2)
            self.ax.plot([p1[0],p2[0]], [p1[1],p2[1]], "g--", lw=1.5)
            self.ax.text(np.mean([p1[0],p2[0]]), np.mean([p1[1],p2[1]]),
                         f" H:{dx:.2f}m\n V:{dz:.2f}m\n D:{d:.2f}m",
                         color="lime", bbox=dict(fc="black", alpha=0.5))
            self.mode = None; self.pts = []
            self.ax.set_title(self.title0, color="black")
            self.fig.canvas.draw_idle()


def analyze_point_cloud(path, params, sts, prg):
    try:
        sts("Loading LAS..."); prg(5)
        with laspy.open(path) as f: las = f.read()
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(np.vstack((las.x, las.y, las.z)).T)
        if not pcd.has_points(): raise ValueError("LAS file is empty.")
        sts("RANSAC analysis..."); prg(15)
        gps, wps = [], []; rem = pcd; za = np.array([0,0,1])
        it = 0
        while len(rem.points) > 5000 and it < 15:
            it += 1; prg(15 + it/15*80)
            try: plane, idx = rem.segment_plane(params["RANSAC_DISTANCE"], 3, 1000)
            except Exception: continue
            if len(idx) < 1000: break
            curr = rem.select_by_index(idx); rem = rem.select_by_index(idx, invert=True)
            ang = np.rad2deg(np.arccos(np.clip(abs(np.dot(plane[:3], za)), -1, 1)))
            if ang < params["GROUND_ANGLE"]: gps.append(curr)
            elif ang > params["WALL_ANGLE"]:
                try:
                    if curr.get_axis_aligned_bounding_box().get_extent()[2] > params["MIN_WALL_HEIGHT"]:
                        wps.append(curr)
                except Exception: continue
        if len(wps) < 2: raise Exception(f"Found only {len(wps)} walls.")
        wps.sort(key=lambda p: len(p.points), reverse=True)
        gc = o3d.geometry.PointCloud()
        if gps: gc.points = o3d.utility.Vector3dVector(
            np.vstack([np.asarray(g.points) for g in gps if g.has_points()]))
        sts("✅ Analysis complete."); prg(100)
        return {"ground": gc, "wall1": wps[0], "wall2": wps[1]}
    except Exception as e: prg(0); sts(friendly_error(e)); return None


def extract_centerline(path, interval=1.0, sts=None, prg=None):
    if sts: sts("Centerline: loading...")
    if prg: prg(5)
    with laspy.open(path) as f: las = f.read()
    pts = np.vstack((las.x, las.y, las.z)).T
    if sts: sts("Centerline: PCA axis...")
    if prg: prg(15)
    mean = pts.mean(axis=0)
    _, evecs = np.linalg.eigh(np.cov((pts-mean).T))
    axis = evecs[:, -1]
    proj = (pts-mean) @ axis
    if sts: sts("Centerline: slicing...")
    if prg: prg(30)
    p0, p1 = proj.min(), proj.max()
    half = interval / 2.0
    centroids = []
    positions = np.arange(p0, p1, interval)
    for i, pos in enumerate(positions):
        sl = pts[np.abs(proj-pos) <= half]
        if len(sl) >= 10: centroids.append(sl.mean(axis=0))
        if prg: prg(30 + int(i/len(positions)*40))
    if len(centroids) < 3:
        raise ValueError("Not enough slices. Try smaller interval.")
    raw = np.array(centroids)
    if sts: sts("Centerline: smoothing...")
    if prg: prg(72)
    w = max(3, min(11, len(raw)//10))
    if w % 2 == 0: w += 1
    k = np.ones(w)/w
    sm = np.column_stack([np.convolve(raw[:,i], k, mode="same") for i in range(3)])
    hw = w//2; sm[:hw] = raw[:hw]; sm[-hw:] = raw[-hw:]
    if sts: sts("Centerline: curvature...")
    if prg: prg(85)
    n = len(sm); curv = np.zeros(n)
    for i in range(1, n-1):
        v1 = sm[i]-sm[i-1]; v2 = sm[i+1]-sm[i]
        l1 = np.linalg.norm(v1); l2 = np.linalg.norm(v2)
        if l1 < 1e-9 or l2 < 1e-9: continue
        curv[i] = np.arccos(np.clip(np.dot(v1,v2)/(l1*l2),-1,1)) / (0.5*(l1+l2)+1e-9)
    curv[0] = curv[1]; curv[-1] = curv[-2]
    THR = 0.01
    types = ["curved" if k >= THR else "straight" for k in curv]
    lens = np.linalg.norm(np.diff(sm, axis=0), axis=1)
    ns = types.count("straight"); nc = types.count("curved")
    stats = {
        "total_length_m": round(float(lens.sum()), 3),
        "num_points": n, "slice_interval_m": interval,
        "straight_pts": ns, "curved_pts": nc,
        "straight_pct": round(100*ns/n, 1), "curved_pct": round(100*nc/n, 1),
        "max_curvature": round(float(curv.max()), 6),
        "mean_curvature": round(float(curv.mean()), 6),
        "smooth_window": w, "main_axis": axis.tolist(),
    }
    if prg: prg(100)
    if sts: sts("✅ Centerline complete.")
    return {"centerline": sm, "curvatures": curv, "section_types": types, "stats": stats}


def plot_centerline_2d(result, fname=""):
    if not MATPLOTLIB_AVAILABLE: return
    cl = result["centerline"]; curv = result["curvatures"]
    types = result["section_types"]; s = result["stats"]
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle(f"Centerline Analysis — {fname}", fontsize=13)
    ax = axes[0]
    sc = ax.scatter(cl[:,0], cl[:,1], c=curv, cmap="RdYlGn_r", s=8, zorder=3)
    ax.plot(cl[:,0], cl[:,1], color="gray", lw=0.6, alpha=0.5)
    for i, t in enumerate(types):
        if t == "curved": ax.scatter(cl[i,0], cl[i,1], color="red", s=20, zorder=4)
    ax.set_xlabel("X (m)"); ax.set_ylabel("Y (m)")
    ax.set_title("Plan View (colour = curvature)")
    ax.set_aspect("equal"); ax.grid(True, alpha=0.3)
    plt.colorbar(sc, ax=ax, label="Curvature (rad/m)")
    from matplotlib.lines import Line2D
    ax.legend(handles=[
        Line2D([0],[0], marker="o", color="w", markerfacecolor="green", ms=8, label="Straight"),
        Line2D([0],[0], marker="o", color="w", markerfacecolor="red",   ms=8, label="Curved"),
    ])
    ax2 = axes[1]; ax2.axis("off")
    rows = [["Total length", f"{s['total_length_m']} m"],
            ["Points", str(s['num_points'])],
            ["Slice interval", f"{s['slice_interval_m']} m"],
            ["Straight", f"{s['straight_pts']} pts ({s['straight_pct']}%)"],
            ["Curved",   f"{s['curved_pts']} pts ({s['curved_pct']}%)"],
            ["Max curvature",  f"{s['max_curvature']} rad/m"],
            ["Mean curvature", f"{s['mean_curvature']} rad/m"]]
    tbl = ax2.table(cellText=rows, colLabels=["Parameter","Value"],
                    cellLoc="left", loc="center", colWidths=[0.5,0.5])
    tbl.auto_set_font_size(False); tbl.set_fontsize(11); tbl.scale(1, 2)
    ax2.set_title("Statistics", pad=20)
    plt.tight_layout(); plt.show()


def plot_centerline_3d(result, fname=""):
    if not MATPLOTLIB_AVAILABLE: return
    cl = result["centerline"]; curv = result["curvatures"]
    fig = plt.figure(figsize=(12, 8))
    ax  = fig.add_subplot(111, projection="3d")
    ax.set_title(f"3D Centerline — {fname}")
    norm = plt.Normalize(curv.min(), curv.max()); cmap = plt.cm.RdYlGn_r
    for i in range(len(cl)-1):
        ax.plot(cl[i:i+2,0], cl[i:i+2,1], cl[i:i+2,2], color=cmap(norm(curv[i])), lw=2)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm); sm.set_array([])
    fig.colorbar(sm, ax=ax, label="Curvature (rad/m)", shrink=0.5)
    ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
    plt.tight_layout(); plt.show()


# ──────────────────────────────────────────────────────────
# MAIN APP  — TAB INTERFACE  (v4.6)
# ──────────────────────────────────────────────────────────

class AnalysisApp:
    def __init__(self, master):
        self.master = master
        master.title("Point Cloud Analysis Tool  v4.6  |  CBNU Smart Structure Lab")
        sv_ttk.set_theme("dark")
        w, h = 860, 780
        sw, sh = master.winfo_screenwidth(), master.winfo_screenheight()
        master.geometry(f"{w}x{h}+{int(sw/2-w/2)}+{int(sh/2-h/2)}")

        # ── State ──────────────────────────────────────────
        self.file_path           = None
        self.analysis_results    = None
        self.design_profile      = None
        self.last_slice_data     = None
        self.centerline_result   = None
        self.tunnel_mesh         = None   # stores Poisson mesh for damage detection
        self.las_header_info     = {}
        self.current_params      = {}
        self.params              = {}
        self.status_text         = tk.StringVar(value="Ready — import a .LAS file to begin.")
        self.show_alpha_var      = tk.BooleanVar(value=False)
        self.analysis_mode       = tk.StringVar(value="tunnel")
        self.selected_preset     = tk.StringVar(value=list(PRESET_PROFILES.keys())[0])
        self.cl_interval_var     = tk.StringVar(value="1.0")

        self._build_ui()
        self.apply_preset()

    # ══════════════════════════════════════════════════════
    # UI BUILDER
    # ══════════════════════════════════════════════════════

    def _build_ui(self):
        root = self.master

        # ── Notebook (tabs) ───────────────────────────────
        nb = ttk.Notebook(root)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))

        t1 = ttk.Frame(nb, padding=12); nb.add(t1, text="  📁  Import  ")
        t2 = ttk.Frame(nb, padding=12); nb.add(t2, text="  ⚙️  Analysis  ")
        t3 = ttk.Frame(nb, padding=12); nb.add(t3, text="  🛤️  Centerline  ")
        t4 = ttk.Frame(nb, padding=12); nb.add(t4, text="  📊  Results  ")

        self._tab_import(t1)
        self._tab_analysis(t2)
        self._tab_centerline(t3)
        self._tab_results(t4)

        # ── AI Assistant (always visible) ─────────────────
        ai_f = ttk.LabelFrame(root, text="🤖  AI Assistant  (Offline — Ollama)", padding=8)
        ai_f.pack(fill=tk.X, padx=8, pady=4)
        self.ent_ai = ttk.Entry(ai_f, font=("Segoe UI", 10))
        self.ent_ai.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ent_ai.bind("<Return>", self.ai_agent)
        ttk.Button(ai_f, text="Send ↗", command=self.ai_agent).pack(side=tk.LEFT, padx=6)

        # ── Status + Progress (always visible) ────────────
        bot = ttk.Frame(root); bot.pack(fill=tk.X, padx=8, pady=(0, 6))
        ttk.Label(bot, textvariable=self.status_text,
                  font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.prog = ttk.Progressbar(bot, mode="determinate", length=200)
        self.prog.pack(side=tk.RIGHT, padx=(8, 0))

    # ──────────────────────────────────────────────────────
    # TAB 1 — IMPORT
    # ──────────────────────────────────────────────────────
    def _tab_import(self, f):
        ttk.Label(f, text="Step 1 — Load your .LAS file",
                  font=("Segoe UI", 13, "bold")).pack(anchor=tk.W, pady=(0, 12))

        btn_row = ttk.Frame(f); btn_row.pack(fill=tk.X, pady=4)
        ttk.Button(btn_row, text="📁  Import .LAS File",
                   command=self.browse_las).pack(side=tk.LEFT, padx=(0,8), ipady=6, ipadx=10)
        self.btn_prev = ttk.Button(btn_row, text="👁️  Preview 3D",
                                   command=self.preview_3d, state=tk.DISABLED)
        self.btn_prev.pack(side=tk.LEFT, ipady=6, ipadx=6)

        ttk.Separator(f, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)

        ttk.Label(f, text="Design Profile (optional)",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(f, text="Import a CSV with X,Z columns to compare against the scanned tunnel.",
                  foreground="#888", font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(2, 6))
        ttk.Button(f, text="📐  Import Design Profile (CSV)",
                   command=self.import_profile).pack(anchor=tk.W, ipady=4)

        ttk.Separator(f, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)

        ttk.Label(f, text="File Information",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.txt_info = scrolledtext.ScrolledText(
            f, height=10, state=tk.DISABLED, font=("Consolas", 9))
        self.txt_info.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    # ──────────────────────────────────────────────────────
    # TAB 2 — ANALYSIS
    # ──────────────────────────────────────────────────────
    def _tab_analysis(self, f):
        ttk.Label(f, text="Step 2 — Configure & Run Analysis",
                  font=("Segoe UI", 13, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # Preset
        pre = ttk.LabelFrame(f, text="⚡ Preset Profile", padding=10)
        pre.pack(fill=tk.X, pady=(0, 8))
        pr1 = ttk.Frame(pre); pr1.pack(fill=tk.X)
        ttk.Label(pr1, text="Profile:").pack(side=tk.LEFT, padx=(0, 8))
        self.cmb_preset = ttk.Combobox(pr1, textvariable=self.selected_preset,
                                        values=list(PRESET_PROFILES.keys()),
                                        state="readonly", width=26)
        self.cmb_preset.pack(side=tk.LEFT)
        self.cmb_preset.bind("<<ComboboxSelected>>", lambda _: self.on_preset_changed())
        ttk.Button(pr1, text="✅ Apply", command=self.apply_preset).pack(side=tk.LEFT, padx=6)
        ttk.Button(pr1, text="💾 Save", command=self.save_custom_preset).pack(side=tk.LEFT, padx=2)
        ttk.Button(pr1, text="📂 Load", command=self.load_custom_preset).pack(side=tk.LEFT, padx=2)
        self.lbl_desc = ttk.Label(pre, text="", wraplength=780,
                                   foreground="#90caf9", font=("Segoe UI", 9, "italic"))
        self.lbl_desc.pack(anchor=tk.W, pady=(6, 0))

        # Parameters
        pg = ttk.LabelFrame(f, text="⚙️ Parameters", padding=10)
        pg.pack(fill=tk.X, pady=(0, 8))
        defs = {
            "MIN_WALL_HEIGHT": ("Min Wall Height (m):", "5.0",  "Min height for a plane to be a wall."),
            "RANSAC_DISTANCE": ("RANSAC Distance (m):", "0.1",  "Max point-to-plane distance."),
            "GROUND_ANGLE":    ("Ground Angle (°):",    "15.0", "Normal angle < this → ground."),
            "WALL_ANGLE":      ("Wall Angle (°):",      "75.0", "Normal angle > this → wall."),
        }
        for i, (k, (lbl, val, tip)) in enumerate(defs.items()):
            ttk.Label(pg, text=lbl).grid(row=i, column=0, sticky=tk.W, padx=5, pady=3)
            e = ttk.Entry(pg, width=9)
            e.grid(row=i, column=1, sticky=tk.W, padx=5)
            e.insert(0, val); self.params[k] = e
            ttk.Label(pg, text=tip, foreground="#777",
                      font=("Segoe UI", 8)).grid(row=i, column=2, sticky=tk.W, padx=10)
        self.btn_ai_sug = ttk.Button(pg, text="🤖 AI Suggest",
                                      command=self.ai_suggest, state=tk.DISABLED)
        self.btn_ai_sug.grid(row=len(defs), column=0, columnspan=3,
                              sticky=tk.W, padx=5, pady=8)

        # Mode
        mg = ttk.LabelFrame(f, text="🔬 Analysis Mode", padding=10)
        mg.pack(fill=tk.X, pady=(0, 8))
        ttk.Radiobutton(mg, text="Tunnel Mode — Extract Ground & Walls",
                        variable=self.analysis_mode, value="tunnel").pack(anchor=tk.W)
        ttk.Radiobutton(mg, text="Damage Mode — Detect anomalies / damage",
                        variable=self.analysis_mode, value="damage").pack(anchor=tk.W)

        # Run button
        self.btn_run = ttk.Button(f, text="▶   Start Analysis",
                                   command=self.start_analysis, state=tk.DISABLED)
        self.btn_run.pack(fill=tk.X, ipady=10, pady=(4, 0))

    # ──────────────────────────────────────────────────────
    # TAB 3 — CENTERLINE
    # ──────────────────────────────────────────────────────
    def _tab_centerline(self, f):
        ttk.Label(f, text="Step 3 — Extract Tunnel Centerline",
                  font=("Segoe UI", 13, "bold")).pack(anchor=tk.W, pady=(0, 4))
        ttk.Label(f,
                  text="Automatically extracts the tunnel axis, detects straight/curved sections,\n"
                       "and computes curvature at each point along the centerline.",
                  foreground="#888", font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(0, 12))

        # Controls
        ctrl = ttk.LabelFrame(f, text="Controls", padding=10)
        ctrl.pack(fill=tk.X, pady=(0, 8))
        cr = ttk.Frame(ctrl); cr.pack(fill=tk.X)
        ttk.Label(cr, text="Slice interval (m):").pack(side=tk.LEFT)
        ttk.Entry(cr, textvariable=self.cl_interval_var, width=6).pack(
            side=tk.LEFT, padx=(4, 16))
        self.btn_cl_run = ttk.Button(cr, text="🔍  Extract Centerline",
                                      command=self.run_centerline, state=tk.DISABLED)
        self.btn_cl_run.pack(side=tk.LEFT, ipady=4, ipadx=6)

        ttk.Label(ctrl, text="Tip: smaller interval = more detail but slower. 1.0 m is recommended.",
                  foreground="#666", font=("Segoe UI", 8)).pack(anchor=tk.W, pady=(6, 0))

        # View & Export
        ve = ttk.LabelFrame(f, text="View & Export", padding=10)
        ve.pack(fill=tk.X, pady=(0, 8))
        vr = ttk.Frame(ve); vr.pack(fill=tk.X)
        self.btn_cl_2d  = ttk.Button(vr, text="📈  Plan View (2D)",
                                      command=self.show_centerline_2d, state=tk.DISABLED)
        self.btn_cl_2d.pack(side=tk.LEFT, padx=(0,6), ipady=4)
        self.btn_cl_3d  = ttk.Button(vr, text="🧊  3D View",
                                      command=self.show_centerline_3d, state=tk.DISABLED)
        self.btn_cl_3d.pack(side=tk.LEFT, padx=(0,6), ipady=4)
        self.btn_cl_exp = ttk.Button(vr, text="📥  Export CSV",
                                      command=self.export_centerline, state=tk.DISABLED)
        self.btn_cl_exp.pack(side=tk.LEFT, ipady=4)

        # Results
        rg = ttk.LabelFrame(f, text="Results", padding=10)
        rg.pack(fill=tk.X)

        def metric(parent, label, row, col, color):
            ttk.Label(parent, text=label, foreground="#888",
                      font=("Segoe UI", 8)).grid(row=row*2, column=col, sticky=tk.W, padx=8)
            var = tk.StringVar(value="—")
            ttk.Label(parent, textvariable=var,
                      font=("Consolas", 12, "bold"),
                      foreground=color).grid(row=row*2+1, column=col, sticky=tk.W, padx=8, pady=(0,8))
            return var

        self.var_cl_len      = metric(rg, "Centerline length",  0, 0, "#ce93d8")
        self.var_cl_pts      = metric(rg, "Points extracted",   0, 1, "#ce93d8")
        self.var_cl_straight = metric(rg, "Straight sections",  1, 0, "#a5d6a7")
        self.var_cl_curved   = metric(rg, "Curved sections",    1, 1, "#ef9a9a")
        self.var_cl_maxcurv  = metric(rg, "Max curvature",      2, 0, "#ffcc80")
        self.var_cl_meancurv = metric(rg, "Mean curvature",     2, 1, "#ffcc80")

    # ──────────────────────────────────────────────────────
    # TAB 4 — RESULTS
    # ──────────────────────────────────────────────────────
    def _tab_results(self, f):
        ttk.Label(f, text="Step 4 — View & Export Results",
                  font=("Segoe UI", 13, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # 3D & Mesh
        vg = ttk.LabelFrame(f, text="3D Visualization", padding=10)
        vg.pack(fill=tk.X, pady=(0, 8))
        vr = ttk.Frame(vg); vr.pack(fill=tk.X)
        self.btn_3d   = ttk.Button(vr, text="🧊  Show 3D Result",
                                    command=self.show_3d, state=tk.DISABLED)
        self.btn_3d.pack(side=tk.LEFT, padx=(0,6), ipady=5, ipadx=8)
        self.btn_mesh = ttk.Button(vr, text="🔷  Create Mesh",
                                    command=self.create_mesh, state=tk.DISABLED)
        self.btn_mesh.pack(side=tk.LEFT, ipady=5, ipadx=8)
        self.btn_ai_rep = ttk.Button(vr, text="🤖  AI Report",
                                      command=self.ai_report, state=tk.DISABLED)
        self.btn_ai_rep.pack(side=tk.LEFT, padx=6, ipady=5)

        # Tunnel Length
        lg = ttk.LabelFrame(f, text="📏 Tunnel Length", padding=10)
        lg.pack(fill=tk.X, pady=(0, 8))
        lr = ttk.Frame(lg); lr.pack(fill=tk.X)
        self.btn_len_yr  = ttk.Button(lr, text="Method 1: Y-Range (Fast)",
                                       command=self.calc_length_yrange, state=tk.DISABLED)
        self.btn_len_yr.pack(side=tk.LEFT, padx=(0,6), ipady=4)
        self.btn_len_pca = ttk.Button(lr, text="Method 2: PCA (Accurate)",
                                       command=self.calc_length_pca, state=tk.DISABLED)
        self.btn_len_pca.pack(side=tk.LEFT, ipady=4)

        lres = ttk.Frame(lg); lres.pack(fill=tk.X, pady=(8,0))
        ttk.Label(lres, text="Y-Range:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.lbl_len_yr  = ttk.Label(lres, text="—", font=("Consolas",11,"bold"), foreground="#4fc3f7")
        self.lbl_len_yr.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(lres, text="PCA:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.lbl_len_pca = ttk.Label(lres, text="—", font=("Consolas",11,"bold"), foreground="#81c784")
        self.lbl_len_pca.grid(row=1, column=1, sticky=tk.W, padx=5)

        # 2D Slice
        sg = ttk.LabelFrame(f, text="📐 2D Cross-Section Slice", padding=10)
        sg.pack(fill=tk.X, pady=(0, 8))
        sr = ttk.Frame(sg); sr.pack(fill=tk.X)
        ttk.Label(sr, text="Slice Y-coord:").pack(side=tk.LEFT)
        self.ent_y = ttk.Entry(sr, width=8); self.ent_y.pack(side=tk.LEFT, padx=5)
        self.btn_2d  = ttk.Button(sr, text="📐  View Slice",
                                   command=lambda: self.view_slice(False), state=tk.DISABLED)
        self.btn_2d.pack(side=tk.LEFT, padx=(0,6), ipady=4)
        self.btn_cmp = ttk.Button(sr, text="📏  Compare Design",
                                   command=lambda: self.view_slice(True), state=tk.DISABLED)
        self.btn_cmp.pack(side=tk.LEFT, ipady=4)
        ttk.Checkbutton(sr, text="AlphaShape", variable=self.show_alpha_var).pack(
            side=tk.LEFT, padx=10)

        # Damage Detection from Mesh
        dg = ttk.LabelFrame(f, text="🔴 Damage Detection (Mesh-Based)", padding=10)
        dg.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(dg,
                  text="Build the Poisson mesh first, then detect damaged areas by\n"
                       "comparing actual mesh vs smoothed reference surface.",
                  foreground="#888", font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(0, 6))
        dr = ttk.Frame(dg); dr.pack(fill=tk.X)
        ttk.Label(dr, text="Deviation threshold (m):").pack(side=tk.LEFT)
        self.ent_dmg_thr = ttk.Entry(dr, width=7)
        self.ent_dmg_thr.insert(0, "0.05")
        self.ent_dmg_thr.pack(side=tk.LEFT, padx=(4, 12))
        self.btn_dmg = ttk.Button(dr, text="🔴  Detect Damage from Mesh",
                                   command=self.detect_damage_from_mesh,
                                   state=tk.DISABLED)
        self.btn_dmg.pack(side=tk.LEFT, ipady=4, ipadx=6)
        ttk.Label(dg,
                  text="Tip: threshold = min deviation (m) to flag as damage. "
                       "0.03–0.10 m typical for tunnel inspection.",
                  foreground="#555", font=("Segoe UI", 8)).pack(anchor=tk.W, pady=(6, 0))

        # Export
        eg = ttk.LabelFrame(f, text="📥 Export", padding=10)
        eg.pack(fill=tk.X)
        er = ttk.Frame(eg); er.pack(fill=tk.X)
        self.btn_exp = ttk.Button(er, text="📥  Export Slice CSV",
                                   command=self.export_slice, state=tk.DISABLED)
        self.btn_exp.pack(side=tk.LEFT, ipady=4)

    # ══════════════════════════════════════════════════════
    # PRESET
    # ══════════════════════════════════════════════════════

    def on_preset_changed(self):
        name = self.selected_preset.get()
        self.lbl_desc.config(
            text=f"ℹ  {PRESET_PROFILES.get(name,{}).get('description','')}")

    def apply_preset(self):
        name = self.selected_preset.get()
        p    = PRESET_PROFILES.get(name, {})
        self.lbl_desc.config(text=f"ℹ  {p.get('description','')}")
        for k in ["MIN_WALL_HEIGHT","RANSAC_DISTANCE","GROUND_ANGLE","WALL_ANGLE"]:
            v = p.get(k)
            if v is not None and k in self.params:
                self.params[k].delete(0, tk.END); self.params[k].insert(0, str(v))
        if name != "⚙️ Custom": self.safe_sts(f"✅ Preset: {name}")

    def save_custom_preset(self):
        try: cur = {k: float(e.get()) for k, e in self.params.items()}
        except ValueError: messagebox.showerror("Error","Enter valid numbers."); return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                             filetypes=[("JSON","*.json")])
        if not path: return
        with open(path,"w") as f:
            json.dump({"name": os.path.splitext(os.path.basename(path))[0],
                       "description":"Custom preset.", **cur}, f, indent=2)
        self.safe_sts(f"💾 Saved: {os.path.basename(path)}")

    def load_custom_preset(self):
        path = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not path: return
        try:
            with open(path) as f: d = json.load(f)
            name = f"📄 {d.get('name', os.path.basename(path))}"
            PRESET_PROFILES[name] = d
            self.cmb_preset.config(values=list(PRESET_PROFILES.keys()))
            self.selected_preset.set(name); self.apply_preset()
        except Exception as e: messagebox.showerror("Error", str(e))

    # ══════════════════════════════════════════════════════
    # FILE IMPORT
    # ══════════════════════════════════════════════════════

    def browse_las(self):
        p = filedialog.askopenfilename(
            filetypes=[("LAS","*.las"),("All","*.*")])
        if not p: return
        self.file_path = p
        self.btn_run.config(state=tk.NORMAL)
        self.btn_prev.config(state=tk.NORMAL)
        self.btn_cl_run.config(state=tk.NORMAL)
        self.btn_len_yr.config(state=tk.NORMAL)
        self.btn_len_pca.config(state=tk.NORMAL)
        self.btn_ai_sug.config(state=tk.NORMAL)
        try:
            with laspy.open(p) as f:
                h = f.header
                self.las_header_info = {"pts": h.point_count,
                                        "ymin": h.y_min, "ymax": h.y_max}
                self.ent_y.delete(0, tk.END)
                self.ent_y.insert(0, f"{(h.y_min+h.y_max)/2:.2f}")
                self._upd_info(
                    f"File   : {os.path.basename(p)}\n"
                    f"Points : {h.point_count:,}\n"
                    f"Y-Range: {h.y_min:.2f} m  →  {h.y_max:.2f} m\n"
                    f"Preset : {self.selected_preset.get()}\n\n"
                    f"✅ File loaded. Go to ⚙️ Analysis tab to run."
                )
                self.safe_sts(f"Loaded: {os.path.basename(p)}")
        except Exception as e: self._upd_info(f"Header error: {e}")

    def import_profile(self):
        p = filedialog.askopenfilename(filetypes=[("CSV","*.csv")])
        if not p: return
        try:
            pts = []
            with open(p,"r",encoding="utf-8") as f:
                for r in csv.reader(f):
                    if len(r) >= 2:
                        try: pts.append([float(r[0]), float(r[1])])
                        except ValueError: continue
            arr = np.array(pts)
            if arr.ndim != 2 or arr.shape[1] != 2:
                raise ValueError("Invalid format")
            self.design_profile = arr
            self._upd_info(f"Design profile: {len(arr)} points imported.")
            if self.analysis_results: self.btn_cmp.config(state=tk.NORMAL)
        except Exception as e: messagebox.showerror("Error", str(e))

    def preview_3d(self):
        def task():
            try:
                self.safe_sts("Generating preview...")
                self.btn_prev.config(state=tk.DISABLED)
                with laspy.open(self.file_path) as f: las = f.read()
                pcd = o3d.geometry.PointCloud()
                pcd.points = o3d.utility.Vector3dVector(
                    np.vstack((las.x, las.y, las.z)).T)
                if len(pcd.points) > 500000:
                    pcd = pcd.voxel_down_sample(0.1)
                pts = np.asarray(pcd.points)
                if len(pts) > 0:
                    z = pts[:,2]; zn = (z-z.min())/(z.max()-z.min()+1e-6)
                    c = np.zeros((len(pts),3))
                    c[:,0]=zn; c[:,1]=0.5; c[:,2]=1-zn
                    pcd.colors = o3d.utility.Vector3dVector(c)
                self.safe_sts("Ready.")
                self._o3d([pcd], "Raw Preview")
            except Exception as e: self.safe_sts(f"Preview error: {e}")
            finally: self.master.after(0, lambda: self.btn_prev.config(state=tk.NORMAL))
        threading.Thread(target=task, daemon=True).start()

    # ══════════════════════════════════════════════════════
    # ANALYSIS
    # ══════════════════════════════════════════════════════

    def start_analysis(self):
        try: self.current_params = {k: float(e.get()) for k,e in self.params.items()}
        except ValueError:
            messagebox.showerror("Error","Parameters must be numbers."); return
        self.btn_run.config(state=tk.DISABLED); self.analysis_results = None
        func = self._run_tunnel if self.analysis_mode.get()=="tunnel" else self._run_damage
        threading.Thread(target=func, args=(self.current_params,), daemon=True).start()

    def _run_tunnel(self, p):
        res = analyze_point_cloud(self.file_path, p, self.safe_sts, self.safe_prog)
        if res:
            self.analysis_results = res
            self.master.after(0, self._enable_result_btns)
            self.master.after(0, self._upd_info,
                f"✅ Tunnel analysis complete.\n"
                f"  Ground points : {len(np.asarray(res['ground'].points)):,}\n"
                f"  Wall 1 points : {len(np.asarray(res['wall1'].points)):,}\n"
                f"  Wall 2 points : {len(np.asarray(res['wall2'].points)):,}\n\n"
                f"→ Go to 📊 Results tab to view output."
            )
        self.master.after(0, lambda: self.btn_run.config(state=tk.NORMAL))

    def _run_damage(self, p):
        try:
            self.safe_sts("Damage Mode..."); self.safe_prog(10)
            with laspy.open(self.file_path) as f: las = f.read()
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(
                np.vstack((las.x, las.y, las.z)).T)
            _, inliers = pcd.segment_plane(p["RANSAC_DISTANCE"], 3, 1000)
            main = pcd.select_by_index(inliers)
            dmg  = pcd.select_by_index(inliers, invert=True)
            bbox = None
            info = f"Damage points: {len(dmg.points):,}"
            if dmg.has_points():
                bbox = dmg.get_axis_aligned_bounding_box(); bbox.color=(1,0,0)
                e = bbox.get_extent()
                info += f"\nDimensions: {e[0]:.2f} × {e[1]:.2f} × {e[2]:.2f} m"
            self.analysis_results = {"main_surface":main,"damage_points":dmg,"damage_bbox":bbox}
            self.safe_prog(100); self.safe_sts("✅ Damage analysis complete.")
            self.master.after(0, self._upd_info, info + "\n\n→ Go to 📊 Results tab.")
            self.master.after(0, self._enable_result_btns)
        except Exception as e: self.safe_sts(friendly_error(e))
        finally: self.master.after(0, lambda: self.btn_run.config(state=tk.NORMAL))

    def _enable_result_btns(self):
        self.btn_3d.config(state=tk.NORMAL)
        self.btn_mesh.config(state=tk.NORMAL)
        self.btn_ai_rep.config(state=tk.NORMAL)
        if self.analysis_results and "ground" in self.analysis_results:
            self.btn_2d.config(state=tk.NORMAL)
            self.btn_exp.config(state=tk.NORMAL)
        if self.design_profile and self.analysis_results and \
                "ground" in self.analysis_results:
            self.btn_cmp.config(state=tk.NORMAL)

    # ══════════════════════════════════════════════════════
    # CENTERLINE
    # ══════════════════════════════════════════════════════

    def run_centerline(self):
        if not self.file_path:
            messagebox.showwarning("Warning","Import a file first."); return
        try:
            iv = float(self.cl_interval_var.get())
            if iv <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error","Slice interval must be a positive number."); return

        def task():
            try:
                self.btn_cl_run.config(state=tk.DISABLED)
                res = extract_centerline(self.file_path, iv,
                                         sts=self.safe_sts, prg=self.safe_prog)
                self.centerline_result = res
                s = res["stats"]
                self.master.after(0, self.var_cl_len.set,
                                  f"{s['total_length_m']} m")
                self.master.after(0, self.var_cl_pts.set,      str(s['num_points']))
                self.master.after(0, self.var_cl_straight.set,
                                  f"{s['straight_pts']} pts ({s['straight_pct']}%)")
                self.master.after(0, self.var_cl_curved.set,
                                  f"{s['curved_pts']} pts ({s['curved_pct']}%)")
                self.master.after(0, self.var_cl_maxcurv.set,
                                  f"{s['max_curvature']} rad/m")
                self.master.after(0, self.var_cl_meancurv.set,
                                  f"{s['mean_curvature']} rad/m")
                for btn in [self.btn_cl_2d, self.btn_cl_3d, self.btn_cl_exp]:
                    self.master.after(0, btn.config, {"state": tk.NORMAL})
                self.master.after(1000, lambda: self.safe_prog(0))
            except Exception as e:
                self.safe_sts(f"Centerline failed: {e}")
            finally:
                self.master.after(0, lambda: self.btn_cl_run.config(state=tk.NORMAL))
        threading.Thread(target=task, daemon=True).start()

    def show_centerline_2d(self):
        if not self.centerline_result: return
        fname = os.path.basename(self.file_path) if self.file_path else ""
        threading.Thread(target=plot_centerline_2d,
                         args=(self.centerline_result, fname), daemon=True).start()

    def show_centerline_3d(self):
        if not self.centerline_result: return
        fname = os.path.basename(self.file_path) if self.file_path else ""
        threading.Thread(target=plot_centerline_3d,
                         args=(self.centerline_result, fname), daemon=True).start()

    def export_centerline(self):
        if not self.centerline_result: return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV","*.csv")])
        if not path: return
        cl = self.centerline_result["centerline"]
        curv = self.centerline_result["curvatures"]
        types = self.centerline_result["section_types"]
        with open(path,"w",newline="",encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Index","X","Y","Z","Curvature_rad_per_m","Section_Type"])
            for i,(pt,k,t) in enumerate(zip(cl,curv,types)):
                w.writerow([i, round(pt[0],4), round(pt[1],4),
                             round(pt[2],4), round(float(k),6), t])
        self.safe_sts(f"✅ Centerline exported: {os.path.basename(path)}")

    # ══════════════════════════════════════════════════════
    # RESULTS
    # ══════════════════════════════════════════════════════

    def _o3d(self, geoms, title):
        def t():
            vis = o3d.visualization.Visualizer()
            vis.create_window(title, 1280, 720)
            for g in geoms: vis.add_geometry(g)
            vis.run(); vis.destroy_window()
        threading.Thread(target=t, daemon=True).start()

    def show_3d(self):
        if not self.analysis_results: return
        res = self.analysis_results
        if "ground" in res:
            geoms = [res["ground"].paint_uniform_color([.5,.5,.5]),
                     res["wall1"].paint_uniform_color([1,0,0]),
                     res["wall2"].paint_uniform_color([0,0,1])]
        else:
            geoms = [res["main_surface"].paint_uniform_color([.8,.8,.8]),
                     res["damage_points"].paint_uniform_color([1,0,0])]
            if res.get("damage_bbox"): geoms.append(res["damage_bbox"])
        self._o3d(geoms, "3D Results")

    def create_mesh(self):
        """
        Robust Poisson Surface Reconstruction  (v4.6)
        Handles sparse / uneven point clouds like the Osong scan.

        Pipeline:
          1. Merge segments
          2. Statistical outlier removal  -> clean noise spikes
          3. Voxel downsample 0.04 m     -> uniform density
          4. Poisson-disk upsample       -> fill sparse regions
          5. Normal estimation (large radius for sparse cloud)
          6. orient_normals_consistent_tangent_plane
          7. Poisson depth=11            -> fills large gaps
          8. Trim bottom 10% density     -> removes boundary artefacts
          9. Paint by Z-height, store for damage detection
        """
        def task():
            try:
                # 1. Merge
                self.safe_sts("Mesh: merging segments..."); self.safe_prog(5)
                pcd = o3d.geometry.PointCloud()
                res = self.analysis_results
                if "ground" in res:
                    pcd += res["ground"]; pcd += res["wall1"]; pcd += res["wall2"]
                else:
                    pcd += res["main_surface"]; pcd += res["damage_points"]
                n_raw = len(pcd.points)
                self.safe_sts(f"Mesh: {n_raw:,} raw points"); self.safe_prog(10)

                # 2. Statistical outlier removal
                self.safe_sts("Mesh: removing outliers..."); self.safe_prog(15)
                pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)

                # 3. Voxel downsample
                self.safe_sts("Mesh: voxel downsample 0.04 m..."); self.safe_prog(22)
                pcd = pcd.voxel_down_sample(voxel_size=0.04)
                self.safe_sts(f"Mesh: {len(pcd.points):,} pts after downsample"); self.safe_prog(28)

                # 4. Poisson-disk upsample to fill sparse areas
                target_pts = 500_000
                if len(pcd.points) < target_pts:
                    self.safe_sts("Mesh: upsampling sparse regions..."); self.safe_prog(35)
                    pcd.estimate_normals(
                        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.5, max_nn=50))
                    try:
                        tmp_mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=8)
                        pcd = tmp_mesh.sample_points_poisson_disk(number_of_points=target_pts)
                        self.safe_sts(f"Mesh: upsampled to {len(pcd.points):,} pts"); self.safe_prog(45)
                    except Exception:
                        self.safe_sts("Mesh: upsample skipped, continuing..."); self.safe_prog(45)
                else:
                    self.safe_prog(45)

                # 5. Normal estimation with large radius
                self.safe_sts("Mesh: estimating normals (r=0.5 m)..."); self.safe_prog(52)
                pcd.estimate_normals(
                    search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.5, max_nn=50))

                # 6. Consistent tangent-plane orientation (robust for asymmetric clouds)
                self.safe_sts("Mesh: orienting normals (tangent plane)..."); self.safe_prog(60)
                pcd.orient_normals_consistent_tangent_plane(k=20)

                # 7. Poisson depth=11
                self.safe_sts("Mesh: Poisson reconstruction depth=11..."); self.safe_prog(68)
                mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                    pcd, depth=11, width=0, scale=1.1, linear_fit=False)

                # 8. Trim low-density boundary artefacts (bottom 10%)
                self.safe_sts("Mesh: trimming boundary artefacts..."); self.safe_prog(82)
                dens = np.asarray(densities)
                keep = dens > np.percentile(dens, 10)
                mesh.remove_vertices_by_mask(~keep)
                mesh.compute_vertex_normals()
                n_tri = len(mesh.triangles)
                self.tunnel_mesh = mesh

                # 9. Paint by Z-height
                self.safe_sts("Mesh: painting..."); self.safe_prog(92)
                verts = np.asarray(mesh.vertices)
                if len(verts) > 0:
                    z = verts[:, 2]
                    zn = (z - z.min()) / (z.max() - z.min() + 1e-6)
                    c = np.zeros((len(verts), 3))
                    c[:, 0] = 0.15 + 0.7 * zn
                    c[:, 1] = 0.55 - 0.3 * zn
                    c[:, 2] = 0.95 - 0.7 * zn
                    mesh.vertex_colors = o3d.utility.Vector3dVector(c)

                self.safe_sts(f"Mesh ready - {n_tri:,} triangles | {len(verts):,} vertices"); self.safe_prog(100)
                self.master.after(0, lambda: self.btn_dmg.config(state=tk.NORMAL))
                self._o3d([mesh], "3D Poisson Mesh (v4.6 depth=11)")

            except Exception as e:
                self.safe_sts(f"Mesh error: {e}")
            finally:
                self.master.after(1500, lambda: self.safe_prog(0))

        threading.Thread(target=task, daemon=True).start()

    def detect_damage_from_mesh(self):
        """
        Mesh-based damage detection.

        Method: compute a smooth 'ideal' reference surface by applying
        Laplacian smoothing to the Poisson mesh, then measure the
        vertex-to-vertex deviation between actual mesh and reference.
        Vertices with deviation above threshold are flagged as damaged.

        This is far more reliable than looking for missing points in the
        raw cloud, because Poisson already fills gaps — so real damage
        shows up as local geometric deviation, not absence of data.
        """
        if not hasattr(self, "tunnel_mesh") or self.tunnel_mesh is None:
            messagebox.showwarning("Warning",
                "Build the Poisson mesh first (🔷 Create Mesh)."); return

        # Read threshold from UI
        try:
            thr = float(self.ent_dmg_thr.get())
            if thr <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error",
                "Damage threshold must be a positive number (e.g. 0.05)."); return

        def task():
            try:
                self.btn_dmg.config(state=tk.DISABLED)
                self.safe_sts("Damage: smoothing reference surface..."); self.safe_prog(20)

                mesh = self.tunnel_mesh
                # Laplacian smoothing → ideal reference (no damage)
                ref_mesh = mesh.filter_smooth_laplacian(number_of_iterations=20)
                ref_mesh.compute_vertex_normals()

                actual_pts = np.asarray(mesh.vertices)
                ref_pts    = np.asarray(ref_mesh.vertices)

                self.safe_sts("Damage: computing deviation..."); self.safe_prog(50)

                # Per-vertex deviation between actual and smoothed reference
                deviation = np.linalg.norm(actual_pts - ref_pts, axis=1)

                # Classify damaged vertices
                damaged_mask = deviation > thr
                n_dmg  = int(damaged_mask.sum())
                n_tot  = len(deviation)
                pct    = round(100 * n_dmg / n_tot, 2)
                max_dev  = round(float(deviation.max()), 4)
                mean_dev = round(float(deviation.mean()), 4)

                self.safe_sts("Damage: colorizing mesh..."); self.safe_prog(75)

                # Colour mesh: green=OK, red=damaged, gradient in between
                norm_dev = deviation / (deviation.max() + 1e-9)
                colors = np.zeros((n_tot, 3))
                colors[:, 0] = norm_dev          # red channel ↑ with damage
                colors[:, 1] = 1.0 - norm_dev    # green channel ↓ with damage
                colors[:, 2] = 0.1
                dmg_mesh = o3d.geometry.TriangleMesh(mesh)
                dmg_mesh.vertex_colors = o3d.utility.Vector3dVector(colors)

                # Bounding boxes around damaged clusters
                dmg_pts_xyz = actual_pts[damaged_mask]
                geoms = [dmg_mesh]
                if len(dmg_pts_xyz) > 0:
                    dmg_pcd = o3d.geometry.PointCloud()
                    dmg_pcd.points = o3d.utility.Vector3dVector(dmg_pts_xyz)
                    # DBSCAN clustering → one bbox per damage cluster
                    labels = np.array(dmg_pcd.cluster_dbscan(
                        eps=0.3, min_points=10, print_progress=False))
                    n_clusters = labels.max() + 1 if labels.max() >= 0 else 0
                    for cid in range(n_clusters):
                        cluster_pts = dmg_pts_xyz[labels == cid]
                        if len(cluster_pts) < 5: continue
                        cp = o3d.geometry.PointCloud()
                        cp.points = o3d.utility.Vector3dVector(cluster_pts)
                        bb = cp.get_axis_aligned_bounding_box()
                        bb.color = (1, 0, 0)
                        geoms.append(bb)
                else:
                    n_clusters = 0

                self.safe_prog(100)
                summary = (
                    f"[Mesh-Based Damage Detection]\n"
                    f"  Threshold        = {thr} m\n"
                    f"  Total vertices   = {n_tot:,}\n"
                    f"  Damaged vertices = {n_dmg:,}  ({pct}%)\n"
                    f"  Damage clusters  = {n_clusters}\n"
                    f"  Max deviation    = {max_dev} m\n"
                    f"  Mean deviation   = {mean_dev} m\n\n"
                    f"  🟢 Green = OK  |  🔴 Red = Damaged\n"
                    f"  Red bounding boxes mark each damage cluster."
                )
                self.master.after(0, self._upd_info, summary)
                self.safe_sts(
                    f"✅ Damage: {n_dmg:,} vertices ({pct}%) | "
                    f"{n_clusters} clusters | max dev {max_dev} m")
                self._o3d(geoms, "Damage Detection — Mesh Deviation")

            except Exception as e:
                self.safe_sts(f"Damage detection error: {e}")
            finally:
                self.master.after(0, lambda: self.btn_dmg.config(state=tk.NORMAL))
                self.master.after(1500, lambda: self.safe_prog(0))

        threading.Thread(target=task, daemon=True).start()

    def calc_length_yrange(self):
        if not self.las_header_info: return
        L = self.las_header_info["ymax"] - self.las_header_info["ymin"]
        self.lbl_len_yr.config(text=f"{L:.3f} m")
        self.safe_sts(f"Y-Range length: {L:.3f} m")

    def calc_length_pca(self):
        if not self.file_path: return
        def task():
            try:
                self.btn_len_pca.config(state=tk.DISABLED); self.safe_prog(10)
                with laspy.open(self.file_path) as f: las = f.read()
                pts = np.vstack((las.x, las.y, las.z)).T
                if len(pts) > 200000:
                    pts = pts[np.random.choice(len(pts), 200000, replace=False)]
                m = pts.mean(axis=0); c = pts - m
                _, ev = np.linalg.eigh(np.cov(c.T))
                ax = ev[:, -1]; pr = c @ ax
                L = float(pr.max() - pr.min())
                self.safe_prog(100)
                self.master.after(0, self.lbl_len_pca.config, {"text": f"{L:.3f} m"})
                self.safe_sts(f"PCA length: {L:.3f} m")
            except Exception as e: self.safe_sts(f"PCA error: {e}")
            finally:
                self.master.after(0, lambda: self.btn_len_pca.config(state=tk.NORMAL))
                self.master.after(1000, lambda: self.safe_prog(0))
        threading.Thread(target=task, daemon=True).start()

    def view_slice(self, use_design):
        if not self.analysis_results or "ground" not in self.analysis_results:
            messagebox.showinfo("Info","Run Tunnel Mode analysis first."); return
        try: y = float(self.ent_y.get())
        except ValueError:
            messagebox.showerror("Error","Y must be a number."); return
        tol = 0.5; res = self.analysis_results
        g  = np.asarray(res["ground"].points); g  = g[np.abs(g[:,1]-y)<=tol]
        w1 = np.asarray(res["wall1"].points);  w1 = w1[np.abs(w1[:,1]-y)<=tol]
        w2 = np.asarray(res["wall2"].points);  w2 = w2[np.abs(w2[:,1]-y)<=tol]
        self.last_slice_data = {"y":y,"g":g,"w1":w1,"w2":w2}
        InteractivePlot(g, w1, w2, y,
                        self.design_profile if use_design else None,
                        self.show_alpha_var.get())

    def export_slice(self):
        if not self.last_slice_data:
            messagebox.showinfo("Info","View a slice first."); return
        p = filedialog.asksaveasfilename(defaultextension=".csv",
                                          filetypes=[("CSV","*.csv")])
        if p:
            d = self.last_slice_data
            with open(p,"w",newline="") as f:
                w = csv.writer(f); w.writerow(["X","Z","Type"])
                for pt in d["g"]:  w.writerow([pt[0], pt[2], "Ground"])
                for pt in d["w1"]: w.writerow([pt[0], pt[2], "Wall1"])
                for pt in d["w2"]: w.writerow([pt[0], pt[2], "Wall2"])
            self.safe_sts(f"✅ Exported: {os.path.basename(p)}")

    # ══════════════════════════════════════════════════════
    # AI FEATURES
    # ══════════════════════════════════════════════════════

    def _ollama(self, prompt, system="You are a Civil Engineering AI assistant."):
        try:
            r = requests.post(OLLAMA_URL,
                              json={"model":LOCAL_MODEL,"prompt":prompt,
                                    "system":system,"stream":False}, timeout=90)
            return r.json().get("response","") if r.status_code==200 \
                   else f"HTTP {r.status_code}"
        except requests.exceptions.ConnectionError: return "ERROR_NO_CONNECTION"
        except Exception as e: return f"Error: {e}"

    def ai_suggest(self):
        def task():
            self.safe_sts("🤖 AI suggesting parameters...")
            self.btn_ai_sug.config(state=tk.DISABLED)
            pts = self.las_header_info.get("pts", 0)
            m   = self.analysis_mode.get()
            res = self._ollama(
                f"Suggest RANSAC parameters for {pts} points, {m} mode.\n"
                f"Output ONLY:\nRANSAC_DISTANCE: [v]\nGROUND_ANGLE: [v]\n"
                f"WALL_ANGLE: [v]\nMIN_WALL_HEIGHT: [v]")
            if res == "ERROR_NO_CONNECTION":
                self.safe_sts("❌ Ollama not running. Run: ollama run llama3")
            else:
                count = 0
                for line in res.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip().upper()
                        v = re.sub(r"[^\d.]", "", v.strip())
                        if k in self.params and v:
                            self.master.after(0, self.params[k].delete, 0, tk.END)
                            self.master.after(0, self.params[k].insert, 0, v)
                            count += 1
                self.safe_sts(f"✅ AI applied {count} suggestions.")
            self.master.after(0, lambda: self.btn_ai_sug.config(state=tk.NORMAL))
        threading.Thread(target=task, daemon=True).start()

    def ai_report(self):
        def task():
            self.safe_sts("🤖 Generating report...")
            self.btn_ai_rep.config(state=tk.DISABLED)
            pts  = self.las_header_info.get("pts", 0)
            m    = self.analysis_mode.get()
            pre  = self.selected_preset.get()
            cll  = self.centerline_result["stats"]["total_length_m"] \
                   if self.centerline_result else "N/A"
            res = self._ollama(
                f"Technical summary for Point Cloud Analysis.\n"
                f"Mode:{m} Preset:{pre} Points:{pts} Centerline:{cll}m\n"
                f"Params:{self.current_params}",
                system="Bullet points only. No prose.")
            if res != "ERROR_NO_CONNECTION":
                self.master.after(0, self._report_win, res)
                self.safe_sts("✅ Report ready.")
            else:
                self.safe_sts("❌ Ollama error.")
            self.master.after(0, lambda: self.btn_ai_rep.config(state=tk.NORMAL))
        threading.Thread(target=task, daemon=True).start()

    def ai_agent(self, event=None):
        cmd = self.ent_ai.get(); self.ent_ai.delete(0, tk.END)
        if not cmd: return
        def task():
            self.safe_sts("🤖 Processing...")
            res = self._ollama(
                f"Command:'{cmd}'. Map to ONE of:\n"
                f"['start_analysis','view_slice','show_3d','create_mesh',"
                f"'calc_length_yrange','calc_length_pca','run_centerline',"
                f"'show_centerline_2d','show_centerline_3d','export_centerline']\n"
                f"Output ONLY the function name.",
                system="Output function names only.")
            fn = re.sub(r"[^a-z_0-9]", "", res.strip().lower())
            dispatch = {
                "start_analysis":    self.start_analysis,
                "view_slice":        lambda: self.view_slice(False),
                "show_3d":           self.show_3d,
                "create_mesh":       self.create_mesh,
                "calc_length_yrange":self.calc_length_yrange,
                "calc_length_pca":   self.calc_length_pca,
                "run_centerline":    self.run_centerline,
                "show_centerline_2d":self.show_centerline_2d,
                "show_centerline_3d":self.show_centerline_3d,
                "export_centerline": self.export_centerline,
            }
            matched = next((v for k,v in dispatch.items() if k in fn), None)
            if matched: self.master.after(0, matched)
            else:       self.safe_sts(f"❓ Could not understand: '{cmd}'")
        threading.Thread(target=task, daemon=True).start()

    def _report_win(self, txt):
        win = tk.Toplevel(self.master); win.title("AI Report"); win.geometry("640x460")
        t = scrolledtext.ScrolledText(win, font=("Segoe UI",10))
        t.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        t.insert(tk.END, txt); t.config(state=tk.DISABLED)

    # ══════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════

    def _upd_info(self, txt):
        self.txt_info.config(state=tk.NORMAL)
        self.txt_info.delete("1.0", tk.END)
        self.txt_info.insert(tk.END, txt)
        self.txt_info.config(state=tk.DISABLED)

    def safe_sts(self, m):  self.master.after(0, lambda: self.status_text.set(m))
    def safe_prog(self, v): self.master.after(0, lambda: self.prog.config(value=v))


if __name__ == "__main__":
    root = tk.Tk()
    AnalysisApp(root)
    root.mainloop()