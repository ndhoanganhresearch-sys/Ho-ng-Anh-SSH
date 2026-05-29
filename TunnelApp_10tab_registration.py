"""
SSL Smart Tunnel Monitoring System - Integrated 10-tab GUI.

Author: Nguyen Duy Hoang Anh - Smart Structure Lab, CBNU
Project: Osong Tunnel 4D-LiDAR Monitoring System

This application integrates the 5-layer tunnel-monitoring workflow with the
multi-station registration engine:

1. Overview
2. Registration
3. RANSAC
4. Centerline
5. Section
6. Rings
7. Time-Series
8. Heatmap
9. Results
10. AI Chat
"""

from __future__ import annotations

import csv
import json
import os
import threading
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

try:
    import open3d as o3d
except ImportError:  # pragma: no cover - handled at runtime
    o3d = None

try:
    import requests
except ImportError:  # pragma: no cover - handled at runtime
    requests = None

try:
    from scipy.spatial import cKDTree
except ImportError:  # pragma: no cover - handled at runtime
    cKDTree = None

try:
    from complete_5_layer_system import CompleteTunnelMonitoringSystem
except Exception:  # pragma: no cover - existing module is optional in GUI
    CompleteTunnelMonitoringSystem = None

from registration_engine import (
    DeformationResult,
    StationData,
    StationManager,
    statistical_outlier_filter,
    voxel_downsample_points,
)


APP_TITLE = "SSL Smart Tunnel Monitoring System - Osong 4D-LiDAR"
OLLAMA_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "llama3"
MAX_DISPLAY_POINTS = 80_000


COLORS = {
    "bg": "#101820",
    "panel": "#172430",
    "panel2": "#203140",
    "text": "#EAF2F8",
    "muted": "#9FB4C4",
    "accent": "#28C7FA",
    "accent2": "#37D67A",
    "warning": "#F5B642",
    "danger": "#FF5C5C",
    "plot": "#F7FAFC",
}


def safe_float(value: str, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: str, default: int) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def set_tunnel_aspect(ax) -> None:
    try:
        ax.set_box_aspect([1, 10, 1])
    except Exception:
        pass


def sample_points(points: np.ndarray, max_points: int = MAX_DISPLAY_POINTS) -> np.ndarray:
    xyz = np.asarray(points, dtype=np.float64)
    if len(xyz) <= max_points:
        return xyz
    rng = np.random.default_rng(42)
    idx = rng.choice(len(xyz), max_points, replace=False)
    return xyz[idx]


def sample_points_with_colors(
    points: np.ndarray,
    colors: Optional[np.ndarray],
    max_points: int = MAX_DISPLAY_POINTS,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    xyz = np.asarray(points, dtype=np.float64)
    color_array = None if colors is None else np.asarray(colors, dtype=np.float64)
    if len(xyz) <= max_points:
        if color_array is not None and len(color_array) == len(xyz):
            return xyz, color_array
        return xyz, None
    rng = np.random.default_rng(42)
    idx = rng.choice(len(xyz), max_points, replace=False)
    if color_array is not None and len(color_array) == len(xyz):
        return xyz[idx], color_array[idx]
    return xyz[idx], None


def compute_simple_centerline(points: np.ndarray, interval_m: float = 1.0) -> np.ndarray:
    xyz = np.asarray(points, dtype=np.float64)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or len(xyz) < 10:
        return np.empty((0, 3), dtype=np.float64)
    y_min = float(np.min(xyz[:, 1]))
    y_max = float(np.max(xyz[:, 1]))
    if np.isclose(y_min, y_max):
        return np.array([xyz.mean(axis=0)], dtype=np.float64)
    centers = []
    edges = np.arange(y_min, y_max + interval_m, interval_m)
    for start, end in zip(edges[:-1], edges[1:]):
        mask = (xyz[:, 1] >= start) & (xyz[:, 1] < end)
        if mask.sum() >= 20:
            centers.append(xyz[mask].mean(axis=0))
    if not centers:
        return np.empty((0, 3), dtype=np.float64)
    return np.vstack(centers)


def compute_ring_statistics(points: np.ndarray, ring_length_m: float = 1.5) -> List[Dict[str, float]]:
    xyz = np.asarray(points, dtype=np.float64)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or len(xyz) == 0:
        return []
    y_min = float(np.min(xyz[:, 1]))
    y_max = float(np.max(xyz[:, 1]))
    edges = np.arange(y_min, y_max + ring_length_m, ring_length_m)
    rows: List[Dict[str, float]] = []
    for index, (start, end) in enumerate(zip(edges[:-1], edges[1:]), start=1):
        mask = (xyz[:, 1] >= start) & (xyz[:, 1] < end)
        section = xyz[mask]
        if len(section) < 20:
            continue
        width = float(section[:, 0].max() - section[:, 0].min())
        height = float(section[:, 2].max() - section[:, 2].min())
        rows.append(
            {
                "ring": index,
                "chainage_start_m": float(start),
                "chainage_end_m": float(end),
                "point_count": int(len(section)),
                "width_m": width,
                "height_m": height,
                "crown_z_m": float(section[:, 2].max()),
            }
        )
    return rows


class TunnelApp:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title(APP_TITLE)
        self.master.configure(bg=COLORS["bg"])
        self.master.geometry("1500x930")
        self.master.minsize(1250, 780)

        self.manager = StationManager(
            voxel_size_registration=0.05,
            voxel_size_visualization=0.10,
            max_registration_points=300_000,
            rmse_warning_m=0.005,
        )
        self.monitor = CompleteTunnelMonitoringSystem() if CompleteTunnelMonitoringSystem else None
        self.running = False
        self.latest_global_points: Optional[np.ndarray] = None
        self.latest_global_colors: Optional[np.ndarray] = None
        self.latest_centerline: Optional[np.ndarray] = None
        self.latest_rings: List[Dict[str, float]] = []

        self.status_text = tk.StringVar(value="Ready.")
        self.timestamp_var = tk.StringVar(value="T0")
        self.reference_timestamp_var = tk.StringVar(value="T0")
        self.current_timestamp_var = tk.StringVar(value="T1")
        self.voxel_visual_var = tk.StringVar(value="0.10")
        self.voxel_registration_var = tk.StringVar(value="0.05")
        self.target_percentile_var = tk.StringVar(value="99.3")
        self.target_eps_var = tk.StringVar(value="0.18")
        self.target_min_points_var = tk.StringVar(value="20")
        self.section_chainage_var = tk.StringVar(value="0.0")
        self.section_thickness_var = tk.StringVar(value="0.30")
        self.ring_length_var = tk.StringVar(value="1.50")
        self.temporal_method_var = tk.StringVar(value="c2c")

        self.figures: Dict[str, Figure] = {}
        self.canvases: Dict[str, FigureCanvasTkAgg] = {}
        self.frames: Dict[str, tk.Frame] = {}
        self.trees: Dict[str, ttk.Treeview] = {}

        self._setup_style()
        self._build_ui()

    def _setup_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=COLORS["panel2"],
            foreground=COLORS["muted"],
            padding=(15, 8),
            font=("Segoe UI", 9),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", COLORS["panel"])],
            foreground=[("selected", COLORS["accent"])],
        )
        style.configure("Treeview", background="#F8FBFD", fieldbackground="#F8FBFD", rowheight=24)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("TProgressbar", troughcolor=COLORS["panel2"], background=COLORS["accent"])

    def _build_ui(self) -> None:
        header = tk.Frame(self.master, bg="#0B131A", height=58)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text="SSL Smart Tunnel Monitoring System",
            bg="#0B131A",
            fg=COLORS["accent"],
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left", padx=18)
        tk.Label(
            header,
            text="Osong Tunnel | 5-Layer 4D-LiDAR | CBNU Smart Structure Lab",
            bg="#0B131A",
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
        ).pack(side="right", padx=18)

        body = tk.Frame(self.master, bg=COLORS["bg"])
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)
        self._build_tabs(body)
        self._build_statusbar()

    def _build_sidebar(self, parent: tk.Frame) -> None:
        outer = tk.Frame(parent, bg=COLORS["panel"], width=330)
        outer.pack(side="left", fill="y", padx=(8, 4), pady=8)
        outer.pack_propagate(False)

        canvas = tk.Canvas(outer, bg=COLORS["panel"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self.sidebar = tk.Frame(canvas, bg=COLORS["panel"])
        self.sidebar.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.sidebar, anchor="nw", width=310)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._side_title("Project")
        self._side_text("Layer 1 Physical\nLayer 2 Preprocessing\nLayer 3 Geometric\nLayer 4 Evaluation\nLayer 5 AI/BIM")
        self._separator()

        self._side_title("Station Loading")
        self._labeled_entry("Timestamp", self.timestamp_var)
        self._labeled_entry("Visual voxel (m)", self.voxel_visual_var)
        self._button("Load Stations", self.load_stations, COLORS["accent"])
        self._button("Refresh Overview", self.refresh_overview, COLORS["panel2"])
        self._separator()

        self._side_title("Targets")
        self._labeled_entry("Intensity percentile", self.target_percentile_var)
        self._labeled_entry("Cluster eps (m)", self.target_eps_var)
        self._labeled_entry("Min cluster points", self.target_min_points_var)
        self._button("Detect Targets", self.detect_targets, COLORS["accent2"])
        self._separator()

        self._side_title("Registration")
        self._labeled_entry("Registration voxel (m)", self.voxel_registration_var)
        self._button("Sequential Registration", self.run_registration, "#2D8CFF")
        self._button("Export Target CSV", self.export_targets, COLORS["panel2"])
        self._separator()

        self._side_title("4D Analysis")
        self._labeled_entry("Reference time", self.reference_timestamp_var)
        self._labeled_entry("Current time", self.current_timestamp_var)
        self._combo("Method", self.temporal_method_var, ["c2c", "normal"])
        self._button("Run 4D Analysis", self.run_4d_analysis, COLORS["warning"], fg="#111111")
        self._separator()

        self._side_title("Sections")
        self._labeled_entry("Chainage Y (m)", self.section_chainage_var)
        self._labeled_entry("Thickness (m)", self.section_thickness_var)
        self._button("Update Section", self.update_section_tab, COLORS["panel2"])
        self._labeled_entry("Ring length (m)", self.ring_length_var)
        self._button("Analyze Rings", self.update_rings_tab, COLORS["panel2"])
        self._separator()

        self._side_title("Pipeline")
        self._button("Run Existing 5-Layer", self.run_existing_5_layer, "#7B61FF")
        self._button("Export Results CSV", self.export_results_csv, COLORS["panel2"])

    def _build_tabs(self, parent: tk.Frame) -> None:
        right = tk.Frame(parent, bg=COLORS["bg"])
        right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)

        self._add_plot_tab("Overview")
        self._add_table_tab("Registration")
        self._add_plot_tab("RANSAC")
        self._add_plot_tab("Centerline")
        self._add_plot_tab("Section")
        self._add_table_tab("Rings")
        self._add_plot_tab("Time-Series")
        self._add_plot_tab("Heatmap")
        self._add_table_tab("Results")
        self._add_ai_tab("AI Chat")

    def _build_statusbar(self) -> None:
        bar = tk.Frame(self.master, bg="#0B131A", height=30)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Label(
            bar,
            textvariable=self.status_text,
            bg="#0B131A",
            fg=COLORS["muted"],
            font=("Consolas", 9),
            anchor="w",
        ).pack(side="left", fill="x", expand=True, padx=10)
        self.progress = ttk.Progressbar(bar, mode="determinate", length=280)
        self.progress.pack(side="right", padx=10, pady=5)

    def _add_plot_tab(self, name: str) -> None:
        frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(frame, text=f"  {name}  ")
        figure = Figure(figsize=(9, 6), dpi=100, facecolor=COLORS["plot"])
        canvas = FigureCanvasTkAgg(figure, master=frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar_frame = tk.Frame(frame, bg=COLORS["panel"])
        toolbar_frame.pack(fill="x")
        NavigationToolbar2Tk(canvas, toolbar_frame)
        self.frames[name] = frame
        self.figures[name] = figure
        self.canvases[name] = canvas
        self._draw_empty_plot(name, f"{name}\nLoad stations to begin.")

    def _add_table_tab(self, name: str) -> None:
        frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(frame, text=f"  {name}  ")
        tree = ttk.Treeview(frame, show="headings")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")
        self.frames[name] = frame
        self.trees[name] = tree
        self._set_tree_rows(name, [])

    def _add_ai_tab(self, name: str) -> None:
        frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(frame, text=f"  {name}  ")
        self.ai_display = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            bg="#F8FBFD",
            fg="#111820",
            font=("Segoe UI", 10),
            relief="flat",
        )
        self.ai_display.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        input_frame = tk.Frame(frame, bg=COLORS["bg"])
        input_frame.pack(fill="x", padx=8, pady=(0, 8))
        self.ai_input = tk.Entry(input_frame, font=("Segoe UI", 10))
        self.ai_input.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.ai_input.bind("<Return>", lambda event: self.send_ai_message())
        self._button_in(input_frame, "Send", self.send_ai_message, COLORS["accent"]).pack(side="right")
        self.frames[name] = frame
        self.ai_display.insert(tk.END, "AI assistant ready. Run registration or 4D analysis to add context.\n\n")

    def _side_title(self, text: str) -> None:
        tk.Label(
            self.sidebar,
            text=text,
            bg=COLORS["panel"],
            fg=COLORS["accent"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 4))

    def _side_text(self, text: str) -> None:
        tk.Label(
            self.sidebar,
            text=text,
            justify="left",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=12)

    def _separator(self) -> None:
        tk.Frame(self.sidebar, bg="#314454", height=1).pack(fill="x", padx=10, pady=8)

    def _labeled_entry(self, label: str, variable: tk.StringVar) -> None:
        tk.Label(
            self.sidebar,
            text=label,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=12, pady=(4, 1))
        entry = tk.Entry(
            self.sidebar,
            textvariable=variable,
            bg="#EAF2F8",
            fg="#111820",
            relief="flat",
            font=("Segoe UI", 9),
        )
        entry.pack(fill="x", padx=12, pady=(0, 4), ipady=4)

    def _combo(self, label: str, variable: tk.StringVar, values: List[str]) -> None:
        tk.Label(
            self.sidebar,
            text=label,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=12, pady=(4, 1))
        combo = ttk.Combobox(self.sidebar, textvariable=variable, values=values, state="readonly")
        combo.pack(fill="x", padx=12, pady=(0, 4))

    def _button(self, text: str, command, bg: str, fg: str = "#FFFFFF") -> None:
        self._button_in(self.sidebar, text, command, bg, fg).pack(fill="x", padx=12, pady=3)

    def _button_in(self, parent, text: str, command, bg: str, fg: str = "#FFFFFF") -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=COLORS["accent"],
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            pady=7,
        )

    def set_status(self, message: str) -> None:
        self.master.after(0, lambda: self.status_text.set(message))

    def set_progress(self, value: float) -> None:
        self.master.after(0, lambda: self.progress.configure(value=max(0.0, min(100.0, float(value)))))

    def run_threaded(self, label: str, func) -> None:
        if self.running:
            messagebox.showwarning("Busy", "A processing task is already running.")
            return
        self.running = True
        self.set_status(label)
        self.set_progress(0)

        def worker() -> None:
            try:
                func()
            except Exception as exc:
                tb = traceback.format_exc()
                self.set_status(f"Error: {exc}")
                self.master.after(0, lambda: messagebox.showerror("Processing error", f"{exc}\n\n{tb}"))
                self.set_progress(0)
            finally:
                self.running = False

        threading.Thread(target=worker, daemon=True).start()

    def load_stations(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select Faro Focus station scans",
            filetypes=[("Point clouds", "*.las *.laz *.ply"), ("All files", "*.*")],
        )
        if not paths:
            return
        timestamp = self.timestamp_var.get().strip() or "T0"

        def task() -> None:
            self.manager.voxel_size_visualization = safe_float(self.voxel_visual_var.get(), 0.10)
            self.manager.voxel_size_registration = safe_float(self.voxel_registration_var.get(), 0.05)
            self.manager.load_stations(
                list(paths),
                timestamp=timestamp,
                status_cb=self.set_status,
                progress_cb=self.set_progress,
            )
            self.refresh_overview()
            self.refresh_registration_table()
            self.set_status(f"Loaded {len(paths)} station(s) for {timestamp}.")
            self.set_progress(100)

        self.run_threaded("Loading stations...", task)

    def refresh_overview(self) -> None:
        def task() -> None:
            if not self.manager.stations:
                raise ValueError("No stations are loaded.")
            voxel = safe_float(self.voxel_visual_var.get(), 0.10)
            points, colors = self.manager.merged_global_cloud(voxel_size=voxel, max_points=MAX_DISPLAY_POINTS)
            self.latest_global_points = points
            self.latest_global_colors = colors
            self.master.after(0, lambda: self.draw_overview(points, colors))
            self.master.after(0, self.update_centerline_tab)
            self.master.after(0, self.update_section_tab)
            self.master.after(0, self.update_rings_tab)
            self.set_status(f"Overview refreshed with {len(points):,} displayed points.")
            self.set_progress(100)

        if self.running:
            task()
        else:
            self.run_threaded("Refreshing overview...", task)

    def detect_targets(self) -> None:
        def task() -> None:
            percentile = safe_float(self.target_percentile_var.get(), 99.3)
            eps = safe_float(self.target_eps_var.get(), 0.18)
            min_points = safe_int(self.target_min_points_var.get(), 20)
            self.manager.detect_targets_all(
                percentile=percentile,
                min_cluster_points=min_points,
                eps=eps,
                status_cb=self.set_status,
                progress_cb=self.set_progress,
            )
            self.refresh_registration_table()
            self.set_status("Target detection complete.")
            self.set_progress(100)

        self.run_threaded("Detecting intensity targets...", task)

    def run_registration(self) -> None:
        def task() -> None:
            if len(self.manager.stations) < 2:
                raise ValueError("Load at least two stations before registration.")
            for station in self.manager.stations:
                if len(station.targets) < 3:
                    raise ValueError(f"{station.station_id} has fewer than 3 targets. Run Detect Targets first.")
            self.manager.voxel_size_registration = safe_float(self.voxel_registration_var.get(), 0.05)
            self.manager.register_sequential(
                use_icp=True,
                prefer_target_ids=False,
                status_cb=self.set_status,
                progress_cb=self.set_progress,
            )
            self.refresh_registration_table()
            self.refresh_overview()
            self.set_status("Sequential registration complete.")
            self.set_progress(100)

        self.run_threaded("Running sequential registration...", task)

    def run_4d_analysis(self) -> None:
        def task() -> None:
            reference = self.reference_timestamp_var.get().strip() or "T0"
            current = self.current_timestamp_var.get().strip() or None
            method = self.temporal_method_var.get().strip() or "c2c"
            results = self.manager.compute_temporal_overlap(
                reference_timestamp=reference,
                current_timestamp=current,
                method=method,
                voxel_size=safe_float(self.voxel_registration_var.get(), 0.05),
                max_points=500_000,
                warning_mm=3.0,
                status_cb=self.set_status,
                progress_cb=self.set_progress,
            )
            self.master.after(0, lambda: self.draw_time_series(results))
            self.master.after(0, lambda: self.draw_heatmap(results[-1]))
            self.master.after(0, self.refresh_results_table)
            self.set_status(f"4D deformation analysis complete: {len(results)} comparison(s).")
            self.set_progress(100)

        self.run_threaded("Running 4D temporal overlap analysis...", task)

    def run_existing_5_layer(self) -> None:
        if self.monitor is None:
            messagebox.showwarning("Unavailable", "complete_5_layer_system.py could not be imported.")
            return
        if not self.manager.stations:
            messagebox.showwarning("No data", "Load at least one station first.")
            return
        station = self.manager.stations[0]

        def task() -> None:
            self.set_status("Running existing 5-layer pipeline on first loaded station...")
            result = self.monitor.run_complete_pipeline(
                current_filepath=station.filepath,
                export_ifc=False,
                export_csv=True,
                output_dir=str(Path(station.filepath).parent),
            )
            deformation = result.get("layer4", {}).get("deformation_results", [])
            self.master.after(0, lambda: self._set_tree_rows("Results", deformation))
            self.set_status("Existing 5-layer pipeline complete.")
            self.set_progress(100)

        self.run_threaded("Running existing 5-layer pipeline...", task)

    def export_targets(self) -> None:
        if not self.manager.stations:
            messagebox.showwarning("No stations", "Load stations first.")
            return
        folder = filedialog.askdirectory(title="Select folder for target CSV files")
        if not folder:
            return
        exported = []
        for station in self.manager.stations:
            if not station.targets:
                continue
            path = os.path.join(folder, f"{station.station_id}_targets.csv")
            try:
                exported.append(self.manager.export_targets_csv(station, path))
            except Exception as exc:
                messagebox.showerror("Export error", str(exc))
                return
        messagebox.showinfo("Export complete", f"Exported {len(exported)} target CSV file(s).")

    def export_results_csv(self) -> None:
        rows = self.manager.registration_table() + self.manager.deformation_table()
        if not rows and self.latest_rings:
            rows = self.latest_rings
        if not rows:
            messagebox.showwarning("No results", "No result rows are available for export.")
            return
        path = filedialog.asksaveasfilename(
            title="Export results CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        keys: List[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        messagebox.showinfo("Export complete", f"Results exported to:\n{path}")

    def draw_overview(self, points: np.ndarray, colors: Optional[np.ndarray]) -> None:
        fig = self.figures["Overview"]
        fig.clf()
        ax = fig.add_subplot(111, projection="3d")
        xyz, sampled_colors = sample_points_with_colors(points, colors)
        c = sampled_colors if sampled_colors is not None else xyz[:, 2]
        ax.scatter(xyz[:, 0], xyz[:, 1], xyz[:, 2], c=c, s=1, cmap="viridis", alpha=0.75, rasterized=True)
        ax.set_title("Global Tunnel Overview - Station 1 Coordinate System")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y / Chainage (m)")
        ax.set_zlabel("Z (m)")
        set_tunnel_aspect(ax)
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        self.canvases["Overview"].draw()

    def update_centerline_tab(self) -> None:
        points = self.latest_global_points
        if points is None or len(points) == 0:
            self._draw_empty_plot("Centerline", "Centerline\nNo global point cloud available.")
            return
        centerline = compute_simple_centerline(points, interval_m=1.0)
        self.latest_centerline = centerline
        fig = self.figures["Centerline"]
        fig.clf()
        ax = fig.add_subplot(111, projection="3d")
        xyz = sample_points(points, 40_000)
        ax.scatter(xyz[:, 0], xyz[:, 1], xyz[:, 2], c="#9FB4C4", s=0.5, alpha=0.25, rasterized=True)
        if len(centerline):
            ax.plot(centerline[:, 0], centerline[:, 1], centerline[:, 2], color="#FF3131", linewidth=2.5)
            ax.scatter(centerline[:, 0], centerline[:, 1], centerline[:, 2], color="#FF3131", s=10)
        ax.set_title("Measured Centerline - Simple Chainage Centroids")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y / Chainage (m)")
        ax.set_zlabel("Z (m)")
        set_tunnel_aspect(ax)
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        self.canvases["Centerline"].draw()

    def update_section_tab(self) -> None:
        points = self.latest_global_points
        if points is None or len(points) == 0:
            self._draw_empty_plot("Section", "Section\nNo global point cloud available.")
            return
        chainage = safe_float(self.section_chainage_var.get(), float(np.median(points[:, 1])))
        thickness = max(0.02, safe_float(self.section_thickness_var.get(), 0.30))
        mask = np.abs(points[:, 1] - chainage) <= thickness * 0.5
        section = points[mask]
        fig = self.figures["Section"]
        fig.clf()
        ax = fig.add_subplot(111)
        if len(section) == 0:
            ax.text(0.5, 0.5, "No points in selected section.", ha="center", va="center", transform=ax.transAxes)
        else:
            sample = sample_points(section, 40_000)
            ax.scatter(sample[:, 0], sample[:, 2], c=sample[:, 2], cmap="turbo", s=2, alpha=0.8, rasterized=True)
            ax.set_aspect("equal", adjustable="box")
        ax.set_title(f"Cross Section at Y={chainage:.2f} m, thickness={thickness:.2f} m")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Z (m)")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        self.canvases["Section"].draw()

    def update_rings_tab(self) -> None:
        points = self.latest_global_points
        if points is None or len(points) == 0:
            self._set_tree_rows("Rings", [])
            return
        ring_length = max(0.10, safe_float(self.ring_length_var.get(), 1.50))
        self.latest_rings = compute_ring_statistics(points, ring_length_m=ring_length)
        self._set_tree_rows("Rings", self.latest_rings)

    def update_ransac_tab(self) -> None:
        if o3d is None:
            self._draw_empty_plot("RANSAC", "RANSAC\nOpen3D is not installed.")
            return
        points = self.latest_global_points
        if points is None or len(points) < 100:
            self._draw_empty_plot("RANSAC", "RANSAC\nNo global point cloud available.")
            return
        try:
            filtered, _ = statistical_outlier_filter(points, nb_neighbors=20, std_ratio=2.0)
            xyz, _ = voxel_downsample_points(filtered, voxel_size=0.08, max_points=120_000)
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(xyz)
            remaining = pcd
            planes = []
            for _ in range(4):
                if len(remaining.points) < 1000:
                    break
                plane_model, inliers = remaining.segment_plane(
                    distance_threshold=0.06,
                    ransac_n=3,
                    num_iterations=800,
                )
                if len(inliers) < 500:
                    break
                plane_cloud = remaining.select_by_index(inliers)
                planes.append(np.asarray(plane_cloud.points))
                remaining = remaining.select_by_index(inliers, invert=True)
            fig = self.figures["RANSAC"]
            fig.clf()
            ax = fig.add_subplot(111, projection="3d")
            palette = ["#37D67A", "#28C7FA", "#F5B642", "#FF5C5C"]
            for i, cloud in enumerate(planes):
                s = sample_points(cloud, 25_000)
                ax.scatter(s[:, 0], s[:, 1], s[:, 2], c=palette[i % len(palette)], s=1.2, alpha=0.75)
            rem = sample_points(np.asarray(remaining.points), 30_000)
            if len(rem):
                ax.scatter(rem[:, 0], rem[:, 1], rem[:, 2], c="#B8C7D3", s=0.5, alpha=0.20)
            ax.set_title(f"RANSAC Segmentation - {len(planes)} dominant surfaces")
            ax.set_xlabel("X (m)")
            ax.set_ylabel("Y / Chainage (m)")
            ax.set_zlabel("Z (m)")
            set_tunnel_aspect(ax)
            ax.grid(True, alpha=0.25)
            fig.tight_layout()
            self.canvases["RANSAC"].draw()
        except Exception as exc:
            self._draw_empty_plot("RANSAC", f"RANSAC failed:\n{exc}")

    def draw_time_series(self, results: List[DeformationResult]) -> None:
        fig = self.figures["Time-Series"]
        fig.clf()
        ax = fig.add_subplot(111)
        plotted = False
        for result in results:
            if len(result.chainage_bins) == 0:
                continue
            ax.plot(
                result.chainage_bins,
                result.crown_settlement_mm,
                marker="o",
                linewidth=1.6,
                label=f"Crown {result.timestamp}",
            )
            ax.plot(
                result.chainage_bins,
                result.convergence_mm,
                marker="s",
                linewidth=1.6,
                label=f"Convergence {result.timestamp}",
            )
            plotted = True
        if not plotted:
            ax.text(0.5, 0.5, "No time-series bins were generated.", ha="center", va="center", transform=ax.transAxes)
        ax.axhline(3.0, color="red", linestyle="--", linewidth=1.0, label="3 mm warning")
        ax.set_title("4D Deformation Time-Series")
        ax.set_xlabel("Y / Chainage (m)")
        ax.set_ylabel("Delta (mm)")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
        fig.tight_layout()
        self.canvases["Time-Series"].draw()

    def draw_heatmap(self, result: DeformationResult) -> None:
        fig = self.figures["Heatmap"]
        fig.clf()
        ax = fig.add_subplot(111, projection="3d")
        xyz = result.points
        colors = result.colors
        if len(xyz) > MAX_DISPLAY_POINTS:
            rng = np.random.default_rng(42)
            idx = rng.choice(len(xyz), MAX_DISPLAY_POINTS, replace=False)
            xyz = xyz[idx]
            colors = colors[idx]
        ax.scatter(xyz[:, 0], xyz[:, 1], xyz[:, 2], c=colors, s=1.4, alpha=0.8, rasterized=True)
        ax.set_title(
            f"4D Deformation Heatmap {result.timestamp} vs {result.reference_timestamp} "
            f"({result.method.upper()})"
        )
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y / Chainage (m)")
        ax.set_zlabel("Z (m)")
        set_tunnel_aspect(ax)
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        self.canvases["Heatmap"].draw()

    def refresh_registration_table(self) -> None:
        rows: List[Dict[str, object]] = []
        for station in self.manager.stations:
            rows.append(
                {
                    "station_id": station.station_id,
                    "timestamp": station.timestamp,
                    "file": Path(station.filepath).name,
                    "points": int(len(station.points)),
                    "targets": int(len(station.targets)),
                    "tx": float(station.transform_global[0, 3]),
                    "ty": float(station.transform_global[1, 3]),
                    "tz": float(station.transform_global[2, 3]),
                }
            )
        for link in self.manager.registration_table():
            rows.append(link)
        self.master.after(0, lambda: self._set_tree_rows("Registration", rows))

    def refresh_results_table(self) -> None:
        rows: List[Dict[str, object]] = []
        rows.extend(self.manager.registration_table())
        rows.extend(self.manager.deformation_table())
        self._set_tree_rows("Results", rows)

    def _set_tree_rows(self, name: str, rows: List[Dict[str, object]]) -> None:
        tree = self.trees[name]
        tree.delete(*tree.get_children())
        if not rows:
            tree["columns"] = ["message"]
            tree.heading("message", text="Message")
            tree.column("message", width=500, anchor="w")
            tree.insert("", "end", values=(f"No {name.lower()} data available.",))
            return
        columns: List[str] = []
        for row in rows:
            for key in row.keys():
                if key not in columns:
                    columns.append(key)
        tree["columns"] = columns
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=max(100, min(220, len(col) * 11)), anchor="center")
        for row in rows:
            values = []
            for col in columns:
                value = row.get(col, "")
                if isinstance(value, float):
                    values.append(f"{value:.4f}")
                else:
                    values.append(value)
            tree.insert("", "end", values=values)

    def _draw_empty_plot(self, name: str, message: str) -> None:
        fig = self.figures[name]
        fig.clf()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes, fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.tight_layout()
        self.canvases[name].draw()

    def send_ai_message(self) -> None:
        text = self.ai_input.get().strip()
        if not text:
            return
        self.ai_input.delete(0, tk.END)
        self.ai_display.insert(tk.END, f"You: {text}\n")
        self.ai_display.see(tk.END)

        def task() -> None:
            context = self._build_ai_context()
            if requests is None:
                reply = "The requests package is not installed, so Ollama cannot be queried."
            else:
                try:
                    payload = {
                        "model": LOCAL_MODEL,
                        "prompt": (
                            "You are a civil engineering AI assistant for the SSL Osong Tunnel "
                            "4D-LiDAR monitoring system. Answer from the provided data.\n\n"
                            f"Context:\n{context}\n\nQuestion:\n{text}"
                        ),
                        "stream": False,
                    }
                    response = requests.post(OLLAMA_URL, json=payload, timeout=60)
                    response.raise_for_status()
                    reply = response.json().get("response", "").strip() or "No response text returned."
                except Exception as exc:
                    reply = f"Ollama request failed: {exc}"
            self.master.after(0, lambda: self.ai_display.insert(tk.END, f"AI: {reply}\n\n"))
            self.master.after(0, lambda: self.ai_display.see(tk.END))

        threading.Thread(target=task, daemon=True).start()

    def _build_ai_context(self) -> str:
        context = {
            "station_count": len(self.manager.stations),
            "stations": [
                {
                    "station_id": station.station_id,
                    "timestamp": station.timestamp,
                    "file": Path(station.filepath).name,
                    "points": int(len(station.points)),
                    "targets": int(len(station.targets)),
                }
                for station in self.manager.stations
            ],
            "registration": self.manager.registration_table(),
            "deformation": self.manager.deformation_table(),
            "rings_preview": self.latest_rings[:10],
        }
        return json.dumps(context, indent=2)


def main() -> None:
    root = tk.Tk()
    app = TunnelApp(root)

    def on_tab_changed(event) -> None:
        selected = event.widget.tab(event.widget.select(), "text").strip()
        if selected == "RANSAC":
            app.update_ransac_tab()
        elif selected == "Centerline":
            app.update_centerline_tab()
        elif selected == "Section":
            app.update_section_tab()
        elif selected == "Rings":
            app.update_rings_tab()

    app.notebook.bind("<<NotebookTabChanged>>", on_tab_changed)
    root.mainloop()


if __name__ == "__main__":
    main()
