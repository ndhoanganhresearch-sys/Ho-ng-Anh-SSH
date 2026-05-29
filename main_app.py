"""
SSL Smart Tunnel Monitoring System - Main GUI.

The GUI is intentionally thin:

- Builds the project tabs from PROJECT_CONTEXT.md / SSL master context.
- Embeds a PyVistaQt QtInteractor directly in the Overview tab.
- Loads LAS/LAZ/PLY scans through registration_engine.py.
- Sends centered/global points into view_manager.py for high-speed rendering.
- Toggles optional PyVista layers from the sidebar.

Run:
    python main_app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

os.environ["VTK_TK_WIDGET_PATH"] = ""
os.environ["VTK_DISABLE_TK_WIDGET"] = "1"
os.environ["QT_API"] = "pyside6"
os.environ.setdefault("MPLBACKEND", "QtAgg")

import numpy as np
import pyvista

if hasattr(pyvista, "set_qt_api"):
    try:
        pyvista.set_qt_api("pyside6")
    except Exception:
        pass

from PySide6 import QtCore, QtWidgets
from pyvistaqt import QtInteractor

from registration_engine import StationData, StationManager
from view_manager import ViewConfig, ViewManager

try:
    pyvista.set_jupyter_backend("static")
except Exception:
    pass


TAB_NAMES = [
    "Overview",
    "Registration",
    "RANSAC",
    "Centerline",
    "Section",
    "Rings",
    "Time-Series",
    "Frenet",
    "Heatmap",
    "Results",
    "AI Chat",
]


class ImportWorker(QtCore.QObject):
    """Load raw point-cloud station data in a Qt worker thread."""

    status = QtCore.Signal(str, float)
    finished = QtCore.Signal(object, object)
    failed = QtCore.Signal(str, object)

    def __init__(
        self,
        file_paths: Sequence[str],
        manager: StationManager,
        timestamp: str,
        auto_detect_targets: bool = True,
    ) -> None:
        super().__init__()
        self.file_paths = list(file_paths)
        self.manager = manager
        self.timestamp = timestamp
        self.auto_detect_targets = bool(auto_detect_targets)

    def emit_status(self, message: str, progress: float) -> None:
        self.status.emit(str(message), float(progress))

    def status_callback_for(self, progress: float) -> Callable[[str], None]:
        fixed_progress = float(progress)

        def callback(message: str) -> None:
            self.emit_status(message, fixed_progress)

        return callback

    @QtCore.Slot()
    def run(self) -> None:
        try:
            loaded: List[StationData] = []
            count = len(self.file_paths)
            if count == 0:
                raise ValueError("No point-cloud files selected.")

            for index, file_path in enumerate(self.file_paths, start=1):
                base_progress = 5.0 + (index - 1) / count * 80.0
                self.status.emit(f"Loading station {index}/{count}: {Path(file_path).name}", base_progress)
                station = self.manager.add_station(
                    filepath=file_path,
                    timestamp=self.timestamp,
                    max_points=None,
                    status_cb=self.status_callback_for(base_progress),
                )
                loaded.append(station)

                if self.auto_detect_targets and station.intensity is not None:
                    try:
                        self.status.emit(f"Detecting intensity targets for {station.station_id}...", base_progress + 8.0)
                        self.manager.detect_targets_for_station(
                            station,
                            status_cb=self.status_callback_for(base_progress + 12.0),
                        )
                    except Exception as exc:
                        self.status.emit(f"{station.station_id}: target detection skipped ({exc})", base_progress + 12.0)
                elif self.auto_detect_targets:
                    self.status.emit(f"{station.station_id}: no intensity channel for target detection.", base_progress + 12.0)

                self.status.emit(f"{station.station_id} imported.", 5.0 + index / count * 90.0)

            self.finished.emit(self.manager, loaded)
        except Exception as exc:
            self.failed.emit("Import LAS failed", exc)


class RegistrationWorker(QtCore.QObject):
    """Run registration in a Qt worker thread and return renderable arrays."""

    status = QtCore.Signal(str, float)
    finished = QtCore.Signal(object, object)
    failed = QtCore.Signal(str, object)

    def __init__(self, manager: StationManager) -> None:
        super().__init__()
        self.manager = manager

    @QtCore.Slot()
    def run(self) -> None:
        try:
            links = self.manager.register_sequential(
                use_icp=True,
                status_cb=lambda message: self.status.emit(str(message), -1.0),
                progress_cb=lambda value: self.status.emit("Running sequential SVD/ICP stitching...", float(value)),
            )
            merged, _ = self.manager.merged_global_cloud(voxel_size=0.05, max_points=900_000)
            self.finished.emit(links, merged)
        except Exception as exc:
            self.failed.emit("Registration failed", exc)


class MainWindow(QtWidgets.QMainWindow):
    """Main SSL tunnel monitoring desktop application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SSL Smart Tunnel Monitoring System - Osong Tunnel 4D LiDAR")
        self.resize(1500, 920)

        self.station_manager = StationManager(
            voxel_size_registration=0.05,
            voxel_size_visualization=0.10,
            max_registration_points=300_000,
        )
        self.current_station: Optional[StationData] = None
        self.current_points: Optional[np.ndarray] = None
        self.current_intensity: Optional[np.ndarray] = None
        self.current_colors: Optional[np.ndarray] = None
        self.current_delta_mm: Optional[np.ndarray] = None
        self.plotter: Optional[QtInteractor] = None
        self.view_manager: Optional[ViewManager] = None
        self._startup_status = "Ready"
        self.import_thread: Optional[QtCore.QThread] = None
        self.import_worker: Optional[ImportWorker] = None
        self.registration_thread: Optional[QtCore.QThread] = None
        self.registration_worker: Optional[RegistrationWorker] = None

        self.layer_actors: Dict[str, object] = {}
        self.layer_state: Dict[str, bool] = {
            "centerline": False,
            "heatmap": False,
            "ai_detections": False,
        }

        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        root_layout = QtWidgets.QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(central)

        self.sidebar = self._build_sidebar()
        root_layout.addWidget(self.sidebar)

        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        root_layout.addWidget(right, 1)

        self.tabs = QtWidgets.QTabWidget()
        right_layout.addWidget(self.tabs, 1)

        self.tab_widgets: Dict[str, QtWidgets.QWidget] = {}
        for tab_name in TAB_NAMES:
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(widget)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(8)
            self.tabs.addTab(widget, tab_name)
            self.tab_widgets[tab_name] = widget

        self._build_overview_tab()
        self._build_registration_tab()
        self._build_ransac_tab()
        self._build_centerline_tab()
        self._build_section_tab()
        self._build_rings_tab()
        self._build_timeseries_tab()
        self._build_frenet_tab()
        self._build_heatmap_tab()
        self._build_results_tab()
        self._build_ai_chat_tab()

        self.status_bar = self.statusBar()
        self.status_label = QtWidgets.QLabel(self._startup_status)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setMaximumWidth(240)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_bar.addWidget(self.status_label, 1)
        self.status_bar.addPermanentWidget(self.progress)

    def _build_sidebar(self) -> QtWidgets.QWidget:
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(270)
        layout = QtWidgets.QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("SSL 4D-LiDAR")
        title.setObjectName("SidebarTitle")
        subtitle = QtWidgets.QLabel("Osong Tunnel Monitoring")
        subtitle.setObjectName("SidebarSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.import_btn = QtWidgets.QPushButton("Import LAS / PLY")
        self.import_btn.clicked.connect(self.import_las)
        layout.addWidget(self.import_btn)

        import_box = QtWidgets.QGroupBox("Import Settings")
        import_layout = QtWidgets.QVBoxLayout(import_box)
        timestamp_row = QtWidgets.QHBoxLayout()
        timestamp_row.addWidget(QtWidgets.QLabel("Timestamp"))
        self.timestamp_edit = QtWidgets.QLineEdit("T0")
        self.timestamp_edit.setMaxLength(24)
        timestamp_row.addWidget(self.timestamp_edit, 1)
        import_layout.addLayout(timestamp_row)
        self.auto_target_check = QtWidgets.QCheckBox("Auto detect intensity targets")
        self.auto_target_check.setChecked(True)
        import_layout.addWidget(self.auto_target_check)
        layout.addWidget(import_box)

        self.register_btn = QtWidgets.QPushButton("Sequential Register")
        self.register_btn.clicked.connect(self.register_stations)
        layout.addWidget(self.register_btn)

        self.deformation_btn = QtWidgets.QPushButton("Tn vs T0 Heatmap")
        self.deformation_btn.clicked.connect(self.compute_deformation_heatmap)
        layout.addWidget(self.deformation_btn)

        layer_box = QtWidgets.QGroupBox("Viewer Layers")
        layer_layout = QtWidgets.QVBoxLayout(layer_box)
        self.centerline_check = QtWidgets.QCheckBox("Centerline")
        self.heatmap_check = QtWidgets.QCheckBox("Heatmap")
        self.ai_check = QtWidgets.QCheckBox("AI Detections")
        self.centerline_check.toggled.connect(lambda checked: self.toggle_layer("centerline", checked))
        self.heatmap_check.toggled.connect(lambda checked: self.toggle_layer("heatmap", checked))
        self.ai_check.toggled.connect(lambda checked: self.toggle_layer("ai_detections", checked))
        layer_layout.addWidget(self.centerline_check)
        layer_layout.addWidget(self.heatmap_check)
        layer_layout.addWidget(self.ai_check)
        layout.addWidget(layer_box)

        view_box = QtWidgets.QGroupBox("View")
        view_layout = QtWidgets.QVBoxLayout(view_box)
        reset_btn = QtWidgets.QPushButton("Reset Camera")
        reset_btn.clicked.connect(self.reset_camera)
        screenshot_btn = QtWidgets.QPushButton("Screenshot")
        screenshot_btn.clicked.connect(self.save_screenshot)
        view_layout.addWidget(reset_btn)
        view_layout.addWidget(screenshot_btn)
        layout.addWidget(view_box)

        layout.addStretch(1)
        self.point_count_label = QtWidgets.QLabel("Points: -")
        self.rmse_label = QtWidgets.QLabel("RMSE: -")
        layout.addWidget(self.point_count_label)
        layout.addWidget(self.rmse_label)
        return sidebar

    def _build_overview_tab(self) -> None:
        self.tab_overview = self.tab_widgets["Overview"]
        self.tab_overview_layout = self.tab_overview.layout()
        self.tab_overview_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_overview_layout.setSpacing(0)

        self.overview_frame = QtWidgets.QFrame(self.tab_overview)
        self.overview_frame.setObjectName("OverviewViewportFrame")
        self.overview_frame_layout = QtWidgets.QVBoxLayout(self.overview_frame)
        self.overview_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.overview_frame_layout.setSpacing(0)
        self.tab_overview_layout.addWidget(self.overview_frame, 1)

        self.init_pyvista()

    def init_pyvista(self) -> None:
        """Create the embedded PyVista widget once and attach it to Overview."""
        if self.plotter is not None:
            return

        self._clear_overview_frame()
        try:
            self.plotter = QtInteractor(self.overview_frame)
            self.plotter.setObjectName("OverviewPyVista")
            self.plotter.set_background("white")
            self.overview_frame_layout.addWidget(self.plotter, 1)

            self.view_manager = ViewManager(
                plotter=self.plotter,
                config=ViewConfig(
                    title="SSL Tunnel Overview",
                    background="#FFFFFF",
                    foreground="#111827",
                    colormap="viridis",
                    render_budget_points=650_000,
                    hard_cap_points=900_000,
                    default_voxel_size=0.05,
                ),
            )
            self.plotter.render()
            self._startup_status = "PyVista initialized"
        except Exception as exc:
            self.plotter = None
            self.view_manager = None
            self._show_pyvista_init_error(exc)

    def _ensure_pyvista(self) -> bool:
        if self.plotter is None:
            self.init_pyvista()
        return self.plotter is not None and self.view_manager is not None

    def _clear_overview_frame(self) -> None:
        while self.overview_frame_layout.count():
            item = self.overview_frame_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _show_pyvista_init_error(self, exc: Exception) -> None:
        message = (
            "PyVista widget was not initialized.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            "If the error mentions a DLL such as vtkRenderingTk.dll, install or repair "
            "Microsoft Visual C++ Redistributable 2015-2022 x64, then reinstall VTK/PyVista.\n\n"
            "Recommended install:\n"
            "python -m pip install --upgrade pyvista vtk pyvistaqt qtpy PySide6"
        )
        label = QtWidgets.QLabel(message, self.overview_frame)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        label.setObjectName("PyVistaInitError")
        self.overview_frame_layout.addWidget(label, 1)
        self._startup_status = "PyVista initialization failed"
        if hasattr(self, "status_label"):
            self.status_label.setText(self._startup_status)

    def _build_registration_tab(self) -> None:
        layout = self.tab_widgets["Registration"].layout()
        self.station_table = QtWidgets.QTableWidget(0, 5)
        self.station_table.setHorizontalHeaderLabels(["Station", "Timestamp", "Points", "Targets", "File"])
        self.station_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.station_table)

    def _build_ransac_tab(self) -> None:
        layout = self.tab_widgets["RANSAC"].layout()
        layout.addWidget(QtWidgets.QLabel("RANSAC segmentation controls will use tunnel_utils.py."))

    def _build_centerline_tab(self) -> None:
        layout = self.tab_widgets["Centerline"].layout()
        layout.addWidget(QtWidgets.QLabel("Centerline layer is previewed in the Overview PyVista viewer."))

    def _build_section_tab(self) -> None:
        layout = self.tab_widgets["Section"].layout()
        layout.addWidget(QtWidgets.QLabel("Cross-section slicing workspace."))

    def _build_rings_tab(self) -> None:
        layout = self.tab_widgets["Rings"].layout()
        layout.addWidget(QtWidgets.QLabel("Concrete segment ring analysis workspace."))

    def _build_timeseries_tab(self) -> None:
        layout = self.tab_widgets["Time-Series"].layout()
        layout.addWidget(QtWidgets.QLabel("4D time-series settlement and convergence charts."))

    def _build_frenet_tab(self) -> None:
        layout = self.tab_widgets["Frenet"].layout()
        layout.addWidget(QtWidgets.QLabel("Frenet frame analysis is rendered as a PyVista overlay in Overview."))

    def _build_heatmap_tab(self) -> None:
        layout = self.tab_widgets["Heatmap"].layout()
        layout.addWidget(QtWidgets.QLabel("Heatmap layer is previewed in the Overview PyVista viewer."))

    def _build_results_tab(self) -> None:
        layout = self.tab_widgets["Results"].layout()
        self.results_text = QtWidgets.QPlainTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)

    def _build_ai_chat_tab(self) -> None:
        layout = self.tab_widgets["AI Chat"].layout()
        self.ai_text = QtWidgets.QPlainTextEdit()
        self.ai_text.setPlaceholderText("AI tunnel-data assistant workspace.")
        layout.addWidget(self.ai_text)

    @QtCore.Slot()
    def import_las(self) -> None:
        if self.import_thread is not None:
            return
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Import Faro Focus Point Clouds",
            "",
            "Point Clouds (*.las *.laz *.ply);;All Files (*.*)",
        )
        if not file_paths:
            return

        self.set_status("Loading raw point cloud with laspy / vertex-only parser...", 10)
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.import_btn.setEnabled(False)
        self.register_btn.setEnabled(False)
        self.deformation_btn.setEnabled(False)

        timestamp = self.timestamp_edit.text().strip() or "T0"
        self.import_thread = QtCore.QThread(self)
        self.import_worker = ImportWorker(
            file_paths=file_paths,
            manager=self.station_manager,
            timestamp=timestamp,
            auto_detect_targets=self.auto_target_check.isChecked(),
        )
        self.import_worker.moveToThread(self.import_thread)
        self.import_thread.started.connect(self.import_worker.run)
        self.import_worker.status.connect(self._set_worker_status)
        self.import_worker.finished.connect(self._on_import_finished)
        self.import_worker.failed.connect(self._on_worker_failed)
        self.import_worker.finished.connect(self.import_thread.quit)
        self.import_worker.failed.connect(self.import_thread.quit)
        self.import_thread.finished.connect(self.import_worker.deleteLater)
        self.import_thread.finished.connect(self.import_thread.deleteLater)
        self.import_thread.finished.connect(self._finish_import_thread)
        self.import_thread.start()

    @QtCore.Slot(str, float)
    def _set_worker_status(self, message: str, progress: float) -> None:
        self.set_status(message, None if progress < 0 else progress)

    @QtCore.Slot(object, object)
    def _on_import_finished(self, manager: StationManager, stations: object) -> None:
        try:
            loaded_stations = list(stations)
            if not loaded_stations:
                raise RuntimeError("No stations were imported.")

            self.station_manager = manager
            station = loaded_stations[-1]
            self.current_station = station

            centered_points = self._center_station_coordinates(station)
            self.current_points = centered_points
            self.current_intensity = station.intensity
            self.current_colors = station.colors
            self.current_delta_mm = None

            self.set_status("Rendering vertex-only PyVista overview...", 70)
            if not self._ensure_pyvista():
                raise RuntimeError("PyVista widget was not initialized.")
            self.view_manager.update_view(
                centered_points,
                intensity=self.current_intensity,
                colors=self.current_colors,
                title=f"Overview - {Path(station.filepath).name}",
                reset_camera=True,
            )
            self._refresh_all_layers()
            self._refresh_station_table()
            self.point_count_label.setText(
                f"Points: {len(station.points):,} raw / {self.view_manager.rendered_point_count:,} rendered"
            )
            self.log_result(f"Imported {len(loaded_stations)} station(s) as timestamp {station.timestamp}")
            for imported in loaded_stations:
                self.log_result(
                    f"{imported.station_id}: {Path(imported.filepath).name}, "
                    f"{len(imported.points):,} points, {len(imported.targets)} targets"
                )
            self.log_result(f"Rendered latest station: {self.view_manager.rendered_point_count:,} points")
            self.set_status(f"Import complete: {len(self.station_manager.stations)} station(s) loaded", 100)
        except Exception as exc:
            self.show_error("Import LAS failed", exc)

    @QtCore.Slot(str, object)
    def _on_worker_failed(self, title: str, exc: Exception) -> None:
        self.show_error(title, exc)

    @QtCore.Slot()
    def _finish_import_thread(self) -> None:
        QtWidgets.QApplication.restoreOverrideCursor()
        self.import_btn.setEnabled(True)
        self.register_btn.setEnabled(True)
        self.deformation_btn.setEnabled(True)
        self.import_thread = None
        self.import_worker = None

    def _center_station_coordinates(self, station: StationData) -> np.ndarray:
        """
        Convert station data into a centered coordinate frame for stable viewing.

        StationManager keeps S001 as the global origin for registration. For a
        single imported station, centering the loaded cloud improves VTK camera
        precision and prevents large survey coordinates from causing jitter.
        """

        global_points = station.global_points()
        center = np.mean(global_points, axis=0)
        centered = global_points - center
        station.metadata["viewer_center_offset"] = center.tolist()
        return centered

    @QtCore.Slot()
    def register_stations(self) -> None:
        if self.registration_thread is not None:
            return
        if len(self.station_manager.stations) < 2:
            QtWidgets.QMessageBox.information(self, "Registration", "Load at least two stations before stitching.")
            return
        self.set_status("Running sequential SVD/ICP stitching...", 10)
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.import_btn.setEnabled(False)
        self.register_btn.setEnabled(False)
        self.deformation_btn.setEnabled(False)
        self.registration_thread = QtCore.QThread(self)
        self.registration_worker = RegistrationWorker(self.station_manager)
        self.registration_worker.moveToThread(self.registration_thread)
        self.registration_thread.started.connect(self.registration_worker.run)
        self.registration_worker.status.connect(self._set_worker_status)
        self.registration_worker.finished.connect(self._on_registration_finished)
        self.registration_worker.failed.connect(self._on_worker_failed)
        self.registration_worker.finished.connect(self.registration_thread.quit)
        self.registration_worker.failed.connect(self.registration_thread.quit)
        self.registration_thread.finished.connect(self.registration_worker.deleteLater)
        self.registration_thread.finished.connect(self.registration_thread.deleteLater)
        self.registration_thread.finished.connect(self._finish_registration_thread)
        self.registration_thread.start()

    @QtCore.Slot(object, object)
    def _on_registration_finished(self, links: object, merged: object) -> None:
        try:
            for link in links:
                rmse_mm = link.rmse_final_m * 1000.0
                self.log_result(
                    f"{link.source_station_id} -> {link.target_station_id}: "
                    f"{link.method}, RMSE {rmse_mm:.2f} mm"
                )
            merged = merged - np.mean(merged, axis=0)
            self.current_points = merged
            self.current_intensity = None
            self.current_colors = None
            self.current_delta_mm = None
            if not self._ensure_pyvista():
                raise RuntimeError("PyVista widget was not initialized.")
            self.view_manager.update_view(merged, title="Registered Global Cloud", reset_camera=True)
            self._refresh_all_layers()
            self.rmse_label.setText(f"RMSE: {links[-1].rmse_final_m * 1000.0:.2f} mm")
            self.set_status("Registration complete", 100)
        except Exception as exc:
            self.show_error("Registration failed", exc)

    @QtCore.Slot()
    def _finish_registration_thread(self) -> None:
        QtWidgets.QApplication.restoreOverrideCursor()
        self.import_btn.setEnabled(True)
        self.register_btn.setEnabled(True)
        self.deformation_btn.setEnabled(True)
        self.registration_thread = None
        self.registration_worker = None

    @QtCore.Slot()
    def compute_deformation_heatmap(self) -> None:
        grouped = self.station_manager.stations_by_timestamp()
        if len(grouped) < 2:
            QtWidgets.QMessageBox.information(
                self,
                "Deformation Heatmap",
                "Load at least two timestamps, for example T0 and T1.",
            )
            return

        reference_timestamp = "T0" if "T0" in grouped else sorted(grouped)[0]
        current_candidates = [timestamp for timestamp in sorted(grouped) if timestamp != reference_timestamp]
        if not current_candidates:
            QtWidgets.QMessageBox.information(
                self,
                "Deformation Heatmap",
                "No current timestamp is available for comparison.",
            )
            return
        current_timestamp = current_candidates[-1]

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.import_btn.setEnabled(False)
        self.register_btn.setEnabled(False)
        self.deformation_btn.setEnabled(False)
        try:
            self.set_status(f"Computing {current_timestamp} vs {reference_timestamp} deformation heatmap...", 10)
            results = self.station_manager.compute_temporal_overlap(
                reference_timestamp=reference_timestamp,
                current_timestamp=current_timestamp,
                method="c2c",
                voxel_size=0.05,
                max_points=350_000,
                warning_mm=3.0,
                status_cb=lambda message: self.set_status(str(message), None),
                progress_cb=lambda value: self.set_status("Computing deformation heatmap...", float(value)),
            )
            if not results:
                raise RuntimeError("No deformation result was produced.")
            result = results[-1]
            centered = result.points - np.mean(result.points, axis=0)
            self.current_points = centered
            self.current_intensity = result.delta_mm
            self.current_colors = None
            self.current_delta_mm = result.delta_mm

            if not self._ensure_pyvista():
                raise RuntimeError("PyVista widget was not initialized.")
            self.view_manager.show_deformation_heatmap(
                centered,
                result.delta_mm,
                title=f"Deformation Heatmap - {current_timestamp} vs {reference_timestamp}",
                warning_mm=3.0,
            )
            self._refresh_all_layers()
            self.tabs.setCurrentWidget(self.tab_widgets["Overview"])

            stats = result.statistics
            self.point_count_label.setText(
                f"Heatmap: {int(stats['point_count']):,} pts, warning {stats['warning_point_pct']:.1f}%"
            )
            self.rmse_label.setText(f"P95 delta: {stats['p95_delta_mm']:.2f} mm")
            self.log_result(
                f"Deformation {current_timestamp} vs {reference_timestamp}: "
                f"mean {stats['mean_delta_mm']:.2f} mm, "
                f"p95 {stats['p95_delta_mm']:.2f} mm, "
                f"max {stats['max_delta_mm']:.2f} mm, "
                f"warning {stats['warning_point_pct']:.1f}%"
            )
            self.log_result(
                f"Threshold bands: stable {stats['stable_point_pct']:.1f}%, "
                f"caution {stats['caution_point_pct']:.1f}%, warning {stats['warning_point_pct']:.1f}%"
            )
            self.set_status("Deformation heatmap complete", 100)
        except Exception as exc:
            self.show_error("Deformation heatmap failed", exc)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.import_btn.setEnabled(True)
            self.register_btn.setEnabled(True)
            self.deformation_btn.setEnabled(True)

    def toggle_layer(self, layer_name: str, checked: bool) -> None:
        self.layer_state[layer_name] = bool(checked)
        if not self._ensure_pyvista():
            return
        if self.current_points is None:
            return
        if checked:
            self._add_layer(layer_name)
        else:
            self._remove_layer(layer_name)
        self.plotter.render()

    def _refresh_all_layers(self) -> None:
        if not self._ensure_pyvista():
            return
        for layer_name in list(self.layer_actors):
            self._remove_layer(layer_name)
        for layer_name, enabled in self.layer_state.items():
            if enabled:
                self._add_layer(layer_name)
        self.plotter.render()

    def _add_layer(self, layer_name: str) -> None:
        if self.current_points is None:
            return
        self._remove_layer(layer_name)
        if layer_name == "centerline":
            self.layer_actors[layer_name] = self._add_centerline_layer()
        elif layer_name == "heatmap":
            self.layer_actors[layer_name] = self._add_heatmap_layer()
        elif layer_name == "ai_detections":
            self.layer_actors[layer_name] = self._add_ai_detection_layer()

    def _remove_layer(self, layer_name: str) -> None:
        if not self._ensure_pyvista():
            return
        actor = self.layer_actors.pop(layer_name, None)
        if actor is not None:
            self.plotter.remove_actor(actor, reset_camera=False, render=False)

    def _add_centerline_layer(self):
        points = self.current_points
        if points is None or len(points) < 10:
            return None
        sample = points[:: max(1, len(points) // 250_000)]
        order_axis = int(np.argmax(np.ptp(sample, axis=0)))
        order = np.argsort(sample[:, order_axis])
        sorted_points = sample[order]

        bin_count = min(160, max(20, len(sorted_points) // 2000))
        chunks = np.array_split(sorted_points, bin_count)
        centers = np.array([chunk.mean(axis=0) for chunk in chunks if len(chunk) > 20], dtype=np.float64)
        if len(centers) < 2:
            return None
        spline = self.plotter.add_lines(
            centers,
            color="#FFB300",
            width=4,
            label="Centerline",
            connected=True,
        )
        return spline

    def _add_heatmap_layer(self):
        points = self.current_points
        if points is None or len(points) == 0:
            return None
        sample_step = max(1, len(points) // 350_000)
        sampled = points[::sample_step]
        if self.current_delta_mm is not None and len(self.current_delta_mm) == len(points):
            sampled_delta = self.current_delta_mm[::sample_step]
            mesh = self.view_manager.point_cloud_mesh(
                sampled,
                scalars=None,
                colors=self._deformation_band_colors(sampled_delta),
                downsample=False,
            )
            return self.plotter.add_mesh(
                mesh,
                scalars="RGB",
                rgb=True,
                style="points",
                point_size=3,
                render_points_as_spheres=False,
                opacity=0.78,
                reset_camera=False,
                label="Deformation Heatmap",
            )

        z = sampled[:, 2]
        delta_like = (z - np.median(z)) * 1000.0
        mesh = self.view_manager.point_cloud_mesh(
            sampled,
            scalars=delta_like,
            colors=None,
            downsample=False,
        )
        return self.plotter.add_mesh(
            mesh,
            scalars="scalars",
            cmap="viridis",
            style="points",
            point_size=3,
            render_points_as_spheres=False,
            opacity=0.72,
            reset_camera=True,
            scalar_bar_args={"title": "Delta-like (mm)"},
        )

    def _deformation_band_colors(self, delta_mm: np.ndarray, warning_mm: float = 3.0) -> np.ndarray:
        values = np.asarray(delta_mm, dtype=np.float64).reshape(-1)
        caution_mm = max(1.0, float(warning_mm) / 3.0)
        colors = np.zeros((len(values), 3), dtype=np.float64)
        colors[values < caution_mm] = np.array([0.0, 0.75, 0.20])
        colors[(values >= caution_mm) & (values < warning_mm)] = np.array([1.0, 0.85, 0.0])
        colors[values >= warning_mm] = np.array([1.0, 0.05, 0.02])
        return colors

    def _add_ai_detection_layer(self):
        points = self.current_points
        if points is None or len(points) == 0:
            return None
        sample = points[:: max(1, len(points) // 200_000)]
        z_limit = np.percentile(sample[:, 2], 98.5)
        candidates = sample[sample[:, 2] >= z_limit]
        if len(candidates) == 0:
            return None
        if len(candidates) > 300:
            candidates = candidates[:: max(1, len(candidates) // 300)]
        mesh = self.view_manager.point_cloud_mesh(
            candidates,
            scalars=None,
            colors=None,
            downsample=False,
        )
        return self.plotter.add_mesh(
            mesh,
            color="#FF4F4F",
            style="points",
            point_size=8,
            render_points_as_spheres=True,
            reset_camera=False,
            label="AI Detections",
        )

    def reset_camera(self) -> None:
        if not self._ensure_pyvista():
            return
        self.plotter.set_scale(1.0, 1.0, 1.0)
        self.plotter.reset_camera()
        self.plotter.render()

    def save_screenshot(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save PyVista Screenshot",
            "ssl_tunnel_view.png",
            "PNG Image (*.png)",
        )
        if not file_path:
            return
        if not self._ensure_pyvista():
            self.show_error("Screenshot failed", RuntimeError("PyVista widget was not initialized."))
            return
        self.plotter.screenshot(file_path)
        self.set_status(f"Screenshot saved: {file_path}", 100)

    def _refresh_station_table(self) -> None:
        stations = list(self.station_manager.stations)
        self.station_table.setRowCount(len(stations))
        for row, station in enumerate(stations):
            values = [
                station.station_id,
                station.timestamp,
                f"{len(station.points):,}",
                str(len(station.targets)),
                Path(station.filepath).name,
            ]
            for col, value in enumerate(values):
                self.station_table.setItem(row, col, QtWidgets.QTableWidgetItem(value))

    def set_status(self, message: str, progress: Optional[float] = None) -> None:
        self.status_label.setText(str(message))
        if progress is not None:
            self.progress.setValue(int(max(0, min(100, progress))))
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, 20)

    def log_result(self, message: str) -> None:
        self.results_text.appendPlainText(str(message))

    def show_error(self, title: str, exc: Exception) -> None:
        self.set_status(f"{title}: {exc}", 0)
        QtWidgets.QMessageBox.critical(self, title, str(exc))

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #F4F8FC;
                color: #111827;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 10pt;
            }
            #Sidebar {
                background: #FFFFFF;
                border-right: 1px solid #C9D6E2;
            }
            #SidebarTitle {
                color: #0067C0;
                font-size: 18pt;
                font-weight: 700;
            }
            #SidebarSubtitle {
                color: #475569;
                font-size: 10pt;
            }
            QPushButton {
                background: #EEF4FA;
                color: #111827;
                border: 1px solid #C9D6E2;
                border-radius: 4px;
                padding: 8px 10px;
            }
            QPushButton:hover {
                background: #E8F2FF;
                border-color: #0067C0;
            }
            QTabWidget::pane {
                border: 1px solid #C9D6E2;
            }
            QTabBar::tab {
                background: #EEF4FA;
                color: #475569;
                padding: 8px 14px;
                border: 1px solid #C9D6E2;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #0067C0;
                border-bottom-color: #0067C0;
            }
            QGroupBox {
                border: 1px solid #C9D6E2;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 12px;
                color: #111827;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                color: #138A52;
            }
            QPlainTextEdit, QTableWidget {
                background: #FFFFFF;
                border: 1px solid #C9D6E2;
                color: #111827;
            }
            QProgressBar {
                border: 1px solid #C9D6E2;
                border-radius: 3px;
                text-align: center;
                background: #EEF4FA;
            }
            QProgressBar::chunk {
                background: #0067C0;
            }
            """
        )

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override name
        if hasattr(self, "plotter") and self.plotter is not None:
            self.plotter.close()
        event.accept()


def main() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
