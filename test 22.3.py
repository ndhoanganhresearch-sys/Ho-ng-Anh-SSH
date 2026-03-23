"""
Standalone Point Cloud Analysis Tool - LOCAL AI EDITION (Ollama) - v4.1 (English Version)
Author: Nguyen Duy Hoang Anh - Smart Structure Lab (CBNU)
Objective: Osong Tunnel LiDAR Data Processing (2026-2028)
Changelog v4.1: Added Tunnel Length Calculation (Y-range & PCA methods)
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

# Check for 2D plotting library
try:
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button as MplButton
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("WARNING: matplotlib not found.")

try:
    import alphashape
    ALPHASHAPE_AVAILABLE = True
except ImportError:
    ALPHASHAPE_AVAILABLE = False

# ==========================================================
# LOCAL AI CONFIGURATION (OLLAMA)
# ==========================================================
OLLAMA_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "llama3"  # Ensure you have run: ollama run llama3

# ==========================================================
# CORE PROCESSING CLASSES & FUNCTIONS
# ==========================================================

class InteractivePlot:
    def __init__(self, ground_pts, wall_1_pts, wall_2_pts, position_y, design_profile=None, show_actual_profile=False):
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror("Error", "Matplotlib is required.")
            return
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.original_title = f'Cross-section at Y ≈ {position_y:.2f}m'
        self.ax.set_title(self.original_title)
        self.draw_data(ground_pts, wall_1_pts, wall_2_pts, design_profile, show_actual_profile)
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Z (m)')
        self.ax.grid(True)
        self.ax.axis('equal')
        self.ax.legend()
        self.mode = None
        self.points = []
        self.cid = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        ax_dist = self.fig.add_axes([0.7, 0.01, 0.15, 0.05])
        self.btn_dist = MplButton(ax_dist, 'Measure Distance')
        self.btn_dist.on_clicked(lambda event: self.set_mode('distance'))
        plt.show()

    def draw_data(self, ground_pts, wall_1_pts, wall_2_pts, design_profile, show_actual_profile):
        if wall_1_pts.size > 0 and wall_2_pts.size > 0 and wall_1_pts[:, 0].mean() < wall_2_pts[:, 0].mean():
            l, r = wall_1_pts, wall_2_pts
        else:
            l, r = wall_2_pts, wall_1_pts
        if ground_pts.size > 0:
            self.ax.scatter(ground_pts[:, 0], ground_pts[:, 2], s=2, color='saddlebrown', label='Ground')
        if design_profile is not None and len(design_profile) > 1:
            self.ax.scatter(l[:, 0], l[:, 2], s=2, color='darkgray', label='Actual Wall')
            self.ax.scatter(r[:, 0], r[:, 2], s=2, color='darkgray')
            self.ax.plot(design_profile[:, 0], design_profile[:, 1], 'g--', lw=2, label='Design Profile')
        else:
            if l.size > 0:
                self.ax.scatter(l[:, 0], l[:, 2], s=2, color='blue', label='Left Wall')
            if r.size > 0:
                self.ax.scatter(r[:, 0], r[:, 2], s=2, color='red', label='Right Wall')
        if show_actual_profile and ALPHASHAPE_AVAILABLE:
            pts2d = []
            [pts2d.append(p[:, [0, 2]]) for p in [ground_pts, l, r] if p.size > 0]
            if pts2d:
                pts2d = np.vstack(pts2d)
                if len(pts2d) > 3:
                    try:
                        ag = alphashape.alphashape(pts2d, 0.5)
                        if hasattr(ag, 'exterior'):
                            x, y = ag.exterior.coords.xy
                            self.ax.plot(x, y, color='gold', lw=2, label='Boundary (AlphaShape)')
                    except Exception:
                        pass

    def set_mode(self, mode):
        self.mode = mode
        self.points = []
        self.ax.set_title("MEASUREMENT MODE: Click 2 points", fontsize=10, color='green')
        self.fig.canvas.draw_idle()

    def onclick(self, event):
        if not self.mode or event.inaxes != self.ax or event.button != 1:
            return
        ix, iy = event.xdata, event.ydata
        if ix is None or iy is None:
            return
        self.points.append((ix, iy))
        self.ax.plot(ix, iy, 'gx', ms=10)
        self.fig.canvas.draw_idle()
        if self.mode == 'distance' and len(self.points) == 2:
            p1, p2 = self.points[0], self.points[1]
            dx = abs(p1[0] - p2[0])
            dz = abs(p1[1] - p2[1])
            d = np.sqrt(dx**2 + dz**2)
            self.ax.plot([p1[0], p2[0]], [p1[1], p2[1]], 'g--', lw=1.5)
            self.ax.text(
                np.mean([p1[0], p2[0]]), np.mean([p1[1], p2[1]]),
                f' H:{dx:.2f}m\n V:{dz:.2f}m\n D:{d:.2f}m',
                color='lime', bbox=dict(fc='black', alpha=0.5)
            )
            self.mode = None
            self.points = []
            self.ax.set_title(self.original_title, color='black')
            self.fig.canvas.draw_idle()


def analyze_point_cloud(input_path, params, status_cb, progress_cb):
    try:
        status_cb("1. Loading LAS data...")
        progress_cb(5)
        with laspy.open(input_path) as f:
            las = f.read()
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(np.vstack((las.x, las.y, las.z)).T)
        if not pcd.has_points():
            raise ValueError("LAS file is empty.")
        status_cb("2. Analyzing tunnel structure (RANSAC)...")
        progress_cb(15)
        gps, wps = [], []
        rem = pcd
        z_axis = np.array([0, 0, 1])
        it = 0
        max_it = 15
        min_pts = 5000
        while len(rem.points) > min_pts and it < max_it:
            it += 1
            progress_cb(15 + (it / max_it) * 80)
            status_cb(f"2.{it}. Running RANSAC iter...")
            try:
                plane, idx = rem.segment_plane(params["RANSAC_DISTANCE"], 3, 1000)
            except Exception:
                continue
            if len(idx) < 1000:
                break
            curr = rem.select_by_index(idx)
            rem = rem.select_by_index(idx, invert=True)
            ang = np.rad2deg(np.arccos(np.clip(abs(np.dot(plane[:3], z_axis)), -1.0, 1.0)))
            if ang < params["GROUND_ANGLE"]:
                gps.append(curr)
            elif ang > params["WALL_ANGLE"]:
                try:
                    if curr.get_axis_aligned_bounding_box().get_extent()[2] > params["MIN_WALL_HEIGHT"]:
                        wps.append(curr)
                except Exception:
                    continue
        if len(wps) < 2:
            raise Exception(f"Found only {len(wps)} walls. Please adjust parameters.")
        wps.sort(key=lambda p: len(p.points), reverse=True)
        gc = o3d.geometry.PointCloud()
        if gps:
            gc.points = o3d.utility.Vector3dVector(
                np.vstack([np.asarray(gp.points) for gp in gps if gp.has_points()])
            )
        status_cb("3. Tunnel analysis complete.")
        progress_cb(100)
        return {"ground": gc, "wall1": wps[0], "wall2": wps[1]}
    except Exception as e:
        progress_cb(0)
        status_cb(f"Analysis failed: {e}")
        return None


# ==========================================================
# TUNNEL LENGTH CALCULATION
# ==========================================================

def calculate_tunnel_length_yrange(las_header_info):
    """
    Method 1: Simple Y-range from LAS header.
    Fast, works well for straight tunnels.
    Returns length in meters.
    """
    y_min = las_header_info.get("ymin", 0)
    y_max = las_header_info.get("ymax", 0)
    return y_max - y_min


def calculate_tunnel_length_pca(file_path, status_cb, progress_cb):
    """
    Method 2: PCA-based tunnel length.
    Projects all points onto the principal axis (longest direction).
    More accurate for curved or tilted tunnels.
    Returns (length, main_axis_vector).
    """
    status_cb("Loading point cloud for PCA...")
    progress_cb(10)

    with laspy.open(file_path) as f:
        las = f.read()

    pts = np.vstack((las.x, las.y, las.z)).T
    status_cb(f"Loaded {len(pts):,} points. Running PCA...")
    progress_cb(40)

    # Downsample for speed if large
    if len(pts) > 500000:
        idx = np.random.choice(len(pts), 500000, replace=False)
        pts = pts[idx]
        status_cb("Downsampled to 500,000 pts for PCA speed...")

    mean = pts.mean(axis=0)
    centered = pts - mean
    cov = np.cov(centered.T)
    progress_cb(70)

    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    # Largest eigenvalue = principal axis (tunnel direction)
    main_axis = eigenvectors[:, -1]

    projections = centered @ main_axis
    length = float(projections.max() - projections.min())
    progress_cb(100)
    return length, main_axis


# ==========================================================
# GRAPHICAL USER INTERFACE (GUI)
# ==========================================================

class AnalysisApp:
    def __init__(self, master):
        self.master = master
        master.title("Point Cloud Analysis Tool - Local AI v4.1")
        sv_ttk.set_theme("dark")
        w, h = 900, 860
        sw, sh = master.winfo_screenwidth(), master.winfo_screenheight()
        master.geometry(f'{w}x{h}+{int(sw/2-w/2)}+{int(sh/2-h/2)}')
        self.main_frame = ttk.Frame(master, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.file_path = None
        self.analysis_results = None
        self.design_profile = None
        self.last_slice_data = None
        self.params = {}
        self.status_text = tk.StringVar(value="Ready. Please import a .LAS file.")
        self.show_profile_var = tk.BooleanVar(value=False)
        self.las_header_info = {}
        self.current_analysis_params = {}
        self.analysis_mode = tk.StringVar(value="tunnel")
        self.create_widgets()

    def create_widgets(self):
        content = ttk.Frame(self.main_frame)
        content.pack(fill=tk.BOTH, expand=True)

        # --- Top control buttons ---
        ctrl = ttk.Frame(content)
        ctrl.pack(fill=tk.X, pady=5)
        ttk.Button(ctrl, text="📁 Import .LAS", command=self.browse_las).pack(side=tk.LEFT, padx=5, ipady=5)
        self.btn_prev = ttk.Button(ctrl, text="👁️ Preview Raw 3D", command=self.preview_3d, state=tk.DISABLED)
        self.btn_prev.pack(side=tk.LEFT, padx=5, ipady=5)
        ttk.Button(ctrl, text="📐 Import Profile (CSV)", command=self.import_profile).pack(side=tk.LEFT, padx=5, ipady=5)
        self.btn_run = ttk.Button(ctrl, text="▶ Start Analysis", command=self.start_analysis, state=tk.DISABLED)
        self.btn_run.pack(side=tk.LEFT, padx=5, ipady=5)

        # --- Parameters ---
        p_frame = ttk.LabelFrame(content, text="Configuration Parameters", padding="10")
        p_frame.pack(fill=tk.X, pady=10)
        plist = {
            "MIN_WALL_HEIGHT": ("Min Wall H (m):", "5.0"),
            "RANSAC_DISTANCE": ("RANSAC Dist (m):", "0.1"),
            "GROUND_ANGLE": ("Ground Angle (°):", "15.0"),
            "WALL_ANGLE": ("Wall Angle (°):", "75.0"),
        }
        for i, (k, (txt, val)) in enumerate(plist.items()):
            ttk.Label(p_frame, text=txt).grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            e = ttk.Entry(p_frame, width=10)
            e.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
            e.insert(0, val)
            self.params[k] = e
        self.btn_ai_sug = ttk.Button(p_frame, text="🤖 Local AI Suggest", command=self.ai_suggest, state=tk.DISABLED)
        self.btn_ai_sug.grid(row=len(plist), column=0, columnspan=2, pady=8)

        # --- Analysis Mode ---
        m_frame = ttk.LabelFrame(content, text="Analysis Mode", padding="10")
        m_frame.pack(fill=tk.X, pady=5)
        ttk.Radiobutton(m_frame, text="Tunnel Mode (Extract Ground & Walls)", variable=self.analysis_mode, value="tunnel").pack(anchor=tk.W)
        ttk.Radiobutton(m_frame, text="Damage Mode (Detect anomalies/damage)", variable=self.analysis_mode, value="damage").pack(anchor=tk.W)

        # --- Results & Export ---
        r_frame = ttk.LabelFrame(content, text="Results & Export", padding="10")
        r_frame.pack(fill=tk.X, pady=10)

        t_row = ttk.Frame(r_frame)
        t_row.pack(fill=tk.X, pady=(0, 5))
        self.btn_3d = ttk.Button(t_row, text="Show 3D", command=self.show_3d, state=tk.DISABLED)
        self.btn_3d.pack(side=tk.LEFT, padx=5)
        self.btn_mesh = ttk.Button(t_row, text="Create Mesh", command=self.create_mesh, state=tk.DISABLED)
        self.btn_mesh.pack(side=tk.LEFT, padx=5)
        self.btn_ai_rep = ttk.Button(t_row, text="🤖 AI Report", command=self.ai_report, state=tk.DISABLED)
        self.btn_ai_rep.pack(side=tk.LEFT, padx=5)
        self.btn_exp = ttk.Button(t_row, text="Export Coordinates (CSV)", command=self.export_slice, state=tk.DISABLED)
        self.btn_exp.pack(side=tk.RIGHT, padx=5)

        b_row = ttk.Frame(r_frame)
        b_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(b_row, text="Slice Y-coord:").pack(side=tk.LEFT)
        self.ent_y = ttk.Entry(b_row, width=8)
        self.ent_y.pack(side=tk.LEFT, padx=5)
        self.btn_2d = ttk.Button(b_row, text="View 2D Slice", command=lambda: self.view_slice(False), state=tk.DISABLED)
        self.btn_2d.pack(side=tk.LEFT, padx=5)
        self.btn_cmp = ttk.Button(b_row, text="Compare with Design", command=lambda: self.view_slice(True), state=tk.DISABLED)
        self.btn_cmp.pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(b_row, text="Show AlphaShape Boundary", variable=self.show_profile_var).pack(side=tk.LEFT, padx=10)

        # =====================================================
        # NEW: TUNNEL LENGTH SECTION
        # =====================================================
        len_frame = ttk.LabelFrame(content, text="📏 Tunnel Length Calculation", padding="10")
        len_frame.pack(fill=tk.X, pady=5)

        btn_row = ttk.Frame(len_frame)
        btn_row.pack(fill=tk.X)

        self.btn_len_simple = ttk.Button(
            btn_row, text="Quick Length (Y-range)",
            command=self.calc_length_simple, state=tk.DISABLED
        )
        self.btn_len_simple.pack(side=tk.LEFT, padx=5, ipady=4)

        self.btn_len_pca = ttk.Button(
            btn_row, text="Accurate Length (PCA)",
            command=self.calc_length_pca, state=tk.DISABLED
        )
        self.btn_len_pca.pack(side=tk.LEFT, padx=5, ipady=4)

        self.btn_len_both = ttk.Button(
            btn_row, text="📊 Compare Both Methods",
            command=self.calc_length_both, state=tk.DISABLED
        )
        self.btn_len_both.pack(side=tk.LEFT, padx=5, ipady=4)

        # Result display
        result_row = ttk.Frame(len_frame)
        result_row.pack(fill=tk.X, pady=(8, 0))

        ttk.Label(result_row, text="Y-range:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.lbl_len_yrange = ttk.Label(result_row, text="—", font=("Consolas", 11))
        self.lbl_len_yrange.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(result_row, text="PCA:").grid(row=0, column=2, sticky=tk.W, padx=15)
        self.lbl_len_pca = ttk.Label(result_row, text="—", font=("Consolas", 11))
        self.lbl_len_pca.grid(row=0, column=3, sticky=tk.W, padx=5)

        ttk.Label(result_row, text="Main axis:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=4)
        self.lbl_axis = ttk.Label(result_row, text="—", font=("Consolas", 9))
        self.lbl_axis.grid(row=1, column=1, columnspan=3, sticky=tk.W, padx=5)

        # =====================================================
        # Info log & status
        # =====================================================
        self.txt_info = scrolledtext.ScrolledText(content, height=5, state=tk.DISABLED, font=("Consolas", 9))
        self.txt_info.pack(fill=tk.BOTH, expand=True, pady=10)
        ttk.Label(self.main_frame, textvariable=self.status_text).pack(fill=tk.X, side=tk.BOTTOM, padx=5)
        self.prog = ttk.Progressbar(self.main_frame, mode='determinate')
        self.prog.pack(fill=tk.X, side=tk.BOTTOM, pady=5)

        # AI agent bar
        ai_f = ttk.LabelFrame(self.main_frame, text="🤖 AI Assistant (Offline Agent)", padding="10")
        ai_f.pack(fill=tk.X, side=tk.BOTTOM)
        self.ent_ai = ttk.Entry(ai_f)
        self.ent_ai.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ent_ai.bind("<Return>", self.ai_agent)
        self.btn_ai_cmd = ttk.Button(ai_f, text="Send Command", command=self.ai_agent)
        self.btn_ai_cmd.pack(side=tk.LEFT, padx=5)

    # ==========================================================
    # FILE I/O
    # ==========================================================
    def browse_las(self):
        p = filedialog.askopenfilename(filetypes=[("LAS", "*.las"), ("All", "*.*")])
        if not p:
            return
        self.file_path = p
        self.status_text.set(f"Loaded: {os.path.basename(p)}")
        self.btn_run.config(state=tk.NORMAL)
        self.btn_prev.config(state=tk.NORMAL)
        try:
            with laspy.open(p) as f:
                h = f.header
                self.las_header_info = {"pts": h.point_count, "ymin": h.y_min, "ymax": h.y_max}
                self.ent_y.delete(0, tk.END)
                self.ent_y.insert(0, f"{(h.y_min + h.y_max) / 2:.2f}")
                self.upd_info(
                    f"File: {os.path.basename(p)}\n"
                    f"Points: {h.point_count:,}\n"
                    f"Y-Range: [{h.y_min:.2f}m, {h.y_max:.2f}m]\n"
                    f"Estimated Y-range length: {h.y_max - h.y_min:.2f} m"
                )
                self.btn_ai_sug.config(state=tk.NORMAL)
                # Enable length buttons as soon as file is loaded
                self.btn_len_simple.config(state=tk.NORMAL)
                self.btn_len_pca.config(state=tk.NORMAL)
                self.btn_len_both.config(state=tk.NORMAL)
        except Exception as e:
            self.upd_info(f"Header Read Error: {e}")

    def import_profile(self):
        p = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if p:
            try:
                pts = []
                with open(p, 'r', encoding='utf-8') as f:
                    for r in csv.reader(f):
                        if len(r) >= 2:
                            try:
                                pts.append([float(r[0]), float(r[1])])
                            except ValueError:
                                continue
                arr = np.array(pts)
                if arr.ndim != 2 or arr.shape[1] != 2:
                    raise ValueError("Invalid coordinate format")
                self.design_profile = arr
                self.upd_info(f"Profile imported: {len(arr)} points")
                self.btn_cmp.config(state=tk.NORMAL if self.analysis_results else tk.DISABLED)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ==========================================================
    # TUNNEL LENGTH METHODS (NEW)
    # ==========================================================

    def calc_length_simple(self):
        """Quick length from Y-range header (instant, no file re-read)."""
        if not self.las_header_info:
            messagebox.showinfo("Info", "Please import a .LAS file first.")
            return
        length = calculate_tunnel_length_yrange(self.las_header_info)
        self.master.after(0, lambda: self.lbl_len_yrange.config(text=f"{length:.2f} m"))
        self.safe_sts(f"Y-range tunnel length: {length:.2f} m")
        self.upd_info(
            f"--- Tunnel Length (Y-range) ---\n"
            f"Y min : {self.las_header_info['ymin']:.2f} m\n"
            f"Y max : {self.las_header_info['ymax']:.2f} m\n"
            f"Length: {length:.2f} m\n"
            f"Note  : Accurate for straight tunnels only."
        )

    def calc_length_pca(self):
        """PCA-based length — runs in background thread."""
        if not self.file_path:
            messagebox.showinfo("Info", "Please import a .LAS file first.")
            return

        def task():
            try:
                self.master.after(0, lambda: self.btn_len_pca.config(state=tk.DISABLED))
                self.master.after(0, lambda: self.btn_len_both.config(state=tk.DISABLED))
                length, axis = calculate_tunnel_length_pca(self.file_path, self.safe_sts, self.safe_prog)
                axis_str = f"[{axis[0]:.4f}, {axis[1]:.4f}, {axis[2]:.4f}]"
                self.master.after(0, lambda: self.lbl_len_pca.config(text=f"{length:.2f} m"))
                self.master.after(0, lambda: self.lbl_axis.config(text=axis_str))
                self.safe_sts(f"PCA tunnel length: {length:.2f} m")
                self.master.after(0, self.upd_info,
                    f"--- Tunnel Length (PCA) ---\n"
                    f"Length    : {length:.2f} m\n"
                    f"Main axis : {axis_str}\n"
                    f"Note      : Accurate for straight & curved tunnels."
                )
            except Exception as e:
                self.safe_sts(f"PCA Error: {e}")
            finally:
                self.master.after(0, lambda: self.btn_len_pca.config(state=tk.NORMAL))
                self.master.after(0, lambda: self.btn_len_both.config(state=tk.NORMAL))
                self.master.after(1000, lambda: self.safe_prog(0))

        threading.Thread(target=task, daemon=True).start()

    def calc_length_both(self):
        """Calculate both methods and show comparison window."""
        if not self.file_path:
            messagebox.showinfo("Info", "Please import a .LAS file first.")
            return

        def task():
            try:
                self.master.after(0, lambda: self.btn_len_both.config(state=tk.DISABLED))
                self.master.after(0, lambda: self.btn_len_pca.config(state=tk.DISABLED))
                self.master.after(0, lambda: self.btn_len_simple.config(state=tk.DISABLED))

                # Method 1
                len_y = calculate_tunnel_length_yrange(self.las_header_info)
                self.master.after(0, lambda: self.lbl_len_yrange.config(text=f"{len_y:.2f} m"))

                # Method 2
                len_pca, axis = calculate_tunnel_length_pca(self.file_path, self.safe_sts, self.safe_prog)
                axis_str = f"[{axis[0]:.4f}, {axis[1]:.4f}, {axis[2]:.4f}]"
                self.master.after(0, lambda: self.lbl_len_pca.config(text=f"{len_pca:.2f} m"))
                self.master.after(0, lambda: self.lbl_axis.config(text=axis_str))

                diff = abs(len_y - len_pca)
                diff_pct = (diff / len_y * 100) if len_y > 0 else 0

                report = (
                    "╔══════════════════════════════════════╗\n"
                    "║      TUNNEL LENGTH COMPARISON        ║\n"
                    "╠══════════════════════════════════════╣\n"
                    f"║  Y-range method : {len_y:>10.2f} m       ║\n"
                    f"║  PCA method     : {len_pca:>10.2f} m       ║\n"
                    f"║  Difference     : {diff:>10.2f} m ({diff_pct:.1f}%)  ║\n"
                    "╠══════════════════════════════════════╣\n"
                    f"║  Main axis : {axis_str:<25}║\n"
                    "╠══════════════════════════════════════╣\n"
                )
                if diff_pct < 1.0:
                    report += "║  ✅ Tunnel is straight (< 1% diff)   ║\n"
                elif diff_pct < 5.0:
                    report += "║  ⚠️  Slight curve detected            ║\n"
                else:
                    report += "║  🔴 Curved tunnel - use PCA result   ║\n"
                report += "╚══════════════════════════════════════╝"

                self.master.after(0, self.show_length_window, report)
                self.master.after(0, self.upd_info, report)
                self.safe_sts(f"Comparison done. Y-range: {len_y:.2f}m | PCA: {len_pca:.2f}m")

            except Exception as e:
                self.safe_sts(f"Error: {e}")
            finally:
                self.master.after(0, lambda: self.btn_len_both.config(state=tk.NORMAL))
                self.master.after(0, lambda: self.btn_len_pca.config(state=tk.NORMAL))
                self.master.after(0, lambda: self.btn_len_simple.config(state=tk.NORMAL))
                self.master.after(1000, lambda: self.safe_prog(0))

        threading.Thread(target=task, daemon=True).start()

    def show_length_window(self, txt):
        """Popup window showing length comparison result."""
        win = tk.Toplevel(self.master)
        win.title("📏 Tunnel Length Result")
        win.geometry("460x280")
        t = scrolledtext.ScrolledText(win, font=("Consolas", 10))
        t.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        t.insert(tk.END, txt)
        t.config(state=tk.DISABLED)
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=5)

    # ==========================================================
    # 3D PREVIEW & ANALYSIS
    # ==========================================================
    def preview_3d(self):
        def task():
            try:
                self.safe_sts("Generating 3D preview...")
                self.master.after(0, lambda: self.btn_prev.config(state=tk.DISABLED))
                with laspy.open(self.file_path) as f:
                    las = f.read()
                pcd = o3d.geometry.PointCloud()
                pcd.points = o3d.utility.Vector3dVector(np.vstack((las.x, las.y, las.z)).T)
                if len(pcd.points) > 500000:
                    pcd = pcd.voxel_down_sample(0.1)
                pts = np.asarray(pcd.points)
                if len(pts) > 0:
                    z = pts[:, 2]
                    zn = (z - z.min()) / (z.max() - z.min() + 1e-6)
                    c = np.zeros((len(pts), 3))
                    c[:, 0] = zn
                    c[:, 1] = 0.5
                    c[:, 2] = 1.0 - zn
                    pcd.colors = o3d.utility.Vector3dVector(c)
                self.safe_sts("Ready.")
                self._run_o3d([pcd], "Raw Data Preview")
            except Exception as e:
                self.safe_sts(f"Error: {e}")
            finally:
                self.master.after(0, lambda: self.btn_prev.config(state=tk.NORMAL))
        threading.Thread(target=task, daemon=True).start()

    def start_analysis(self):
        try:
            self.current_analysis_params = {k: float(e.get()) for k, e in self.params.items()}
        except ValueError:
            messagebox.showerror("Error", "Please enter numerical values only.")
            return
        self.btn_run.config(state=tk.DISABLED)
        self.analysis_results = None
        func = self.run_tunnel if self.analysis_mode.get() == "tunnel" else self.run_damage
        threading.Thread(target=func, args=(self.current_analysis_params,), daemon=True).start()

    def run_tunnel(self, p):
        res = analyze_point_cloud(self.file_path, p, self.safe_sts, self.safe_prog)
        if res:
            self.analysis_results = res
            self.master.after(0, self.enable_btns)
        else:
            self.safe_sts("Tunnel analysis failed.")
        self.master.after(0, lambda: self.btn_run.config(state=tk.NORMAL))

    def run_damage(self, p):
        try:
            self.safe_sts("Processing Damage Mode...")
            self.safe_prog(10)
            with laspy.open(self.file_path) as f:
                las = f.read()
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(np.vstack((las.x, las.y, las.z)).T)
            plane, inliers = pcd.segment_plane(p["RANSAC_DISTANCE"], 3, 1000)
            main = pcd.select_by_index(inliers)
            dmg = pcd.select_by_index(inliers, invert=True)
            info = f"Found {len(dmg.points):,} damage/anomaly points."
            bbox = None
            if dmg.has_points():
                bbox = dmg.get_axis_aligned_bounding_box()
                bbox.color = (1, 0, 0)
                ext = bbox.get_extent()
                info += f"\nEstimated Dimensions: {ext[0]:.2f}x{ext[1]:.2f}x{ext[2]:.2f}m"
            self.analysis_results = {"main_surface": main, "damage_points": dmg, "damage_bbox": bbox}
            self.safe_sts("Analysis Complete.")
            self.safe_prog(100)
            self.master.after(0, self.upd_info, info)
            self.master.after(0, self.enable_btns)
        except Exception as e:
            self.safe_sts(f"Error: {e}")
        finally:
            self.master.after(0, lambda: self.btn_run.config(state=tk.NORMAL))

    def _run_o3d(self, geoms, title):
        def t():
            vis = o3d.visualization.Visualizer()
            vis.create_window(title, 1280, 720)
            for g in geoms:
                vis.add_geometry(g)
            vis.run()
            vis.destroy_window()
        threading.Thread(target=t, daemon=True).start()

    def show_3d(self):
        if not self.analysis_results:
            return
        res = self.analysis_results
        geoms = []
        if "ground" in res:
            geoms = [
                res['ground'].paint_uniform_color([.5, .5, .5]),
                res['wall1'].paint_uniform_color([1, 0, 0]),
                res['wall2'].paint_uniform_color([0, 0, 1])
            ]
        elif "main_surface" in res:
            geoms = [
                res['main_surface'].paint_uniform_color([.8, .8, .8]),
                res['damage_points'].paint_uniform_color([1, 0, 0])
            ]
            if res.get("damage_bbox"):
                geoms.append(res["damage_bbox"])
        self._run_o3d(geoms, "3D Results")

    def create_mesh(self):
        def task():
            try:
                self.safe_sts("Merging points & Downsampling...")
                self.safe_prog(20)
                pcd = o3d.geometry.PointCloud()
                res = self.analysis_results
                if "ground" in res:
                    pcd += res['ground']
                    pcd += res['wall1']
                    pcd += res['wall2']
                else:
                    pcd += res['main_surface']
                    pcd += res['damage_points']
                pcd = pcd.voxel_down_sample(0.1)
                self.safe_sts("Estimating normals...")
                self.safe_prog(50)
                pcd.estimate_normals()
                self.safe_sts("Reconstructing surface (Ball Pivoting)...")
                self.safe_prog(80)
                mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
                    pcd, o3d.utility.DoubleVector([0.1, 0.2])
                )
                self.safe_sts("Mesh Complete.")
                self.safe_prog(100)
                self._run_o3d([mesh], "3D Mesh Model")
            except Exception as e:
                self.safe_sts(f"Mesh Error: {e}")
            finally:
                self.master.after(1000, lambda: self.safe_prog(0))
        threading.Thread(target=task, daemon=True).start()

    def view_slice(self, use_profile):
        if "ground" not in self.analysis_results:
            messagebox.showinfo("Info", "Slicing is only available in Tunnel mode.")
            return
        try:
            y_str = self.ent_y.get().strip()
            if not y_str:
                messagebox.showerror("Error", "Please enter a Y coordinate.")
                return
            y = float(y_str)
        except ValueError:
            messagebox.showerror("Error", "Y coordinate must be a number.")
            return
        try:
            tol = 0.5
            res = self.analysis_results
            g = np.asarray(res['ground'].points)
            g = g[np.abs(g[:, 1] - y) <= tol]
            w1 = np.asarray(res['wall1'].points)
            w1 = w1[np.abs(w1[:, 1] - y) <= tol]
            w2 = np.asarray(res['wall2'].points)
            w2 = w2[np.abs(w2[:, 1] - y) <= tol]
            self.last_slice_data = {"y": y, "g": g, "w1": w1, "w2": w2}
            InteractivePlot(g, w1, w2, y, self.design_profile if use_profile else None, self.show_profile_var.get())
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def export_slice(self):
        if not self.last_slice_data:
            messagebox.showinfo("Info", "Please view a 2D slice first.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if p:
            with open(p, 'w', newline='') as f:
                w = csv.writer(f)
                d = self.last_slice_data
                w.writerow(['X', 'Z', 'Type'])
                for pt in d['g']:
                    w.writerow([pt[0], pt[2], 'Ground'])
                for pt in d['w1']:
                    w.writerow([pt[0], pt[2], 'Wall1'])
                for pt in d['w2']:
                    w.writerow([pt[0], pt[2], 'Wall2'])
            self.upd_info(f"Slice exported to: {p}")

    # ==========================================================
    # LOCAL AI FEATURES (OLLAMA)
    # ==========================================================
    def call_ollama(self, prompt, system="You are an AI assistant for Civil Engineering."):
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={"model": LOCAL_MODEL, "prompt": prompt, "system": system, "stream": False},
                timeout=90
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
            return f"Error HTTP {resp.status_code}"
        except requests.exceptions.ConnectionError:
            return "ERROR_NO_CONNECTION"
        except Exception as e:
            return f"Error: {e}"

    def ai_suggest(self):
        def task():
            self.safe_sts(f"🤖 Asking {LOCAL_MODEL} (Local)...")
            self.master.after(0, lambda: self.btn_ai_sug.config(state=tk.DISABLED))
            pts = self.las_header_info.get('pts', 0)
            m = self.analysis_mode.get()
            pmt = (
                f"Suggest RANSAC parameters for a LiDAR point cloud ({pts} points) for {m} analysis. "
                f"Output ONLY in this exact format, no other text:\n"
                f"RANSAC_DISTANCE: [value]\nGROUND_ANGLE: [value]\nWALL_ANGLE: [value]\nMIN_WALL_HEIGHT: [value]"
            )
            res = self.call_ollama(pmt)
            if res == "ERROR_NO_CONNECTION":
                self.safe_sts("Error: Ollama is not running! Open terminal and type 'ollama run llama3'")
            elif "Error" in res:
                self.safe_sts(res)
            else:
                count = 0
                for line in res.splitlines():
                    if ':' in line:
                        k, v = line.split(':', 1)
                        k = k.strip().upper()
                        v = re.sub(r'[^\d.]', '', v.strip())
                        if k in self.params and v:
                            self.master.after(0, self.params[k].delete, 0, tk.END)
                            self.master.after(0, self.params[k].insert, 0, v)
                            count += 1
                self.safe_sts(f"Applied {count} parameters suggested by AI.")
            self.master.after(0, lambda: self.btn_ai_sug.config(state=tk.NORMAL))
        threading.Thread(target=task, daemon=True).start()

    def ai_report(self):
        def task():
            self.safe_sts("🤖 Generating report (Offline)...")
            self.master.after(0, lambda: self.btn_ai_rep.config(state=tk.DISABLED))
            pts = self.las_header_info.get('pts', 0)
            m = self.analysis_mode.get()
            pmt = (
                f"Write a brief technical summary (bullet points only) for a Point Cloud Analysis. "
                f"Mode: {m}. Total points: {pts}. Parameters used: {self.current_analysis_params}."
            )
            res = self.call_ollama(pmt, system="You are a strict technical reporting bot. No prose.")
            if res == "ERROR_NO_CONNECTION":
                self.safe_sts("Ollama connection error.")
            else:
                self.master.after(0, self.show_report_window, res)
                self.safe_sts("AI Report generated successfully.")
            self.master.after(0, lambda: self.btn_ai_rep.config(state=tk.NORMAL))
        threading.Thread(target=task, daemon=True).start()

    def ai_agent(self, event=None):
        cmd = self.ent_ai.get()
        self.ent_ai.delete(0, tk.END)
        if not cmd:
            return

        def task():
            self.safe_sts("🤖 Parsing command...")
            self.master.after(0, lambda: self.btn_ai_cmd.config(state=tk.DISABLED))
            pmt = (
                f"User command: '{cmd}'. Map this to ONE of these functions: "
                f"['run_analysis', 'view_slice', 'show_3d', 'create_mesh', 'calc_tunnel_length']. "
                f"Output ONLY the function name. Example output: show_3d"
            )
            res = self.call_ollama(pmt, system="You output only function names. Nothing else.")
            if res == "ERROR_NO_CONNECTION":
                self.safe_sts("Ollama connection error.")
            else:
                func_name = re.sub(r'[^a-z_0-9]', '', res.strip().lower())
                self.safe_sts(f"🤖 AI calling: {func_name}")
                if "run_analysis" in func_name:
                    self.master.after(0, self.start_analysis)
                elif "view_slice" in func_name:
                    self.master.after(0, lambda: self.view_slice(False))
                elif "show_3d" in func_name:
                    self.master.after(0, self.show_3d)
                elif "create_mesh" in func_name:
                    self.master.after(0, self.create_mesh)
                elif "calc_tunnel_length" in func_name or "length" in func_name:
                    self.master.after(0, self.calc_length_both)
                else:
                    self.safe_sts(f"AI did not understand the command. ({res})")
            self.master.after(0, lambda: self.btn_ai_cmd.config(state=tk.NORMAL))
        threading.Thread(target=task, daemon=True).start()

    def show_report_window(self, txt):
        win = tk.Toplevel(self.master)
        win.title("Local AI Report")
        win.geometry("600x400")
        t = scrolledtext.ScrolledText(win, font=("Segoe UI", 10))
        t.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        t.insert(tk.END, txt)
        t.config(state=tk.DISABLED)

    def enable_btns(self):
        self.btn_3d.config(state=tk.NORMAL)
        self.btn_mesh.config(state=tk.NORMAL)
        self.btn_ai_rep.config(state=tk.NORMAL)
        if "ground" in self.analysis_results:
            self.btn_2d.config(state=tk.NORMAL)
            self.btn_exp.config(state=tk.NORMAL)
        if self.design_profile is not None and "ground" in self.analysis_results:
            self.btn_cmp.config(state=tk.NORMAL)

    def upd_info(self, txt):
        self.txt_info.config(state=tk.NORMAL)
        self.txt_info.delete("1.0", tk.END)
        self.txt_info.insert(tk.END, txt)
        self.txt_info.config(state=tk.DISABLED)

    def safe_sts(self, m):
        self.master.after(0, lambda: self.status_text.set(m))

    def safe_prog(self, v):
        self.master.after(0, lambda: self.prog.config(value=v))


if __name__ == '__main__':
    root = tk.Tk()
    app = AnalysisApp(root)
    root.mainloop()