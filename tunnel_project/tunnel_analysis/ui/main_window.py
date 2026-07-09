import os
from ..common import *
from ..models import PointCloudBundle, PipelineContext
from ..io_layer import BaseLayer
from ..preprocessing import PreprocessingLayer
from ..registration import RegistrationLayer
from ..geometry import GeometricLayer
from ..segmentation import SegmentationLayer
from ..parameters import ParameterExtractionLayer
from ..timeseries import TimeSeriesLayer
from ..section_warnings import SECTION_DELTA_CAUTION_MM, SECTION_DELTA_CRITICAL_MM
from ..digital_twin import DigitalTwinAILayer
from ..worker import PipelineWorker
from ..exporter import TunnelExporter
from ..pdf_reporter import TunnelPDFReporter
from ..ifc_exporter import TunnelIFCExporter
from ..target_detector import TargetDetector, Target
from ..rag_ai import TunnelRAGAssistant
from .widgets import (CollapsibleSection, MatplotlibSectionWidget, PolarDeformationPlotWidget,
                      LinePlotWidget, SummaryDashboardWidget, ChainageRulerWidget,
                      MultiEpochTimeSeriesWidget, M3C2MapWidget,
                      classify_sections, section_warning_status, section_warning_text)
from .i18n_v4 import tr as _tr
from .dialogs import TaskProgressDialog, _RoughAlignDialog, _TargetDetectDialog
from translations import get_available_languages
from language_switcher import LanguageSwitcher

# -- GUI feature scope -------------------------------------------------------
# When True, the sidebar exposes the simplified 7-step workflow. Advanced
# diagnostics are hidden (not deleted). Keep button names/numbers unchanged;
# manage visibility via CORE_STEP_CODES and the ui/show_advanced_buttons setting.
CORE_FEATURES_ONLY = True
# Default for fresh installs. Users can override from the sidebar checkbox.
SHOW_ADVANCED_BUTTONS = False
# Max points sent to the 3D viewport in one mesh. Rendering every point of a
# multi-million-point tunnel scan stalls VTK (the KeyboardInterrupt seen during
# render_window.Render()); decimating for DISPLAY only keeps interaction smooth
# while analysis still runs on the full cloud.
DISPLAY_MAX_POINTS = 600_000

# Sidebar sub-actions kept in core mode, keyed by the step code at the start
# of each button label (e.g. "4.3b"). Edit this set to fine-tune the scope.
CORE_STEP_CODES = {
    "1.1", "1.3", "1.9b",                             # acquire + demo T0~T5 (1.9 folder loader stays advanced-only)
    "2.1", "2.5",                                     # preprocessing (2.5 = all-in-one denoise)
    "3.0",                                            # times auto-align (includes anchor+ICP and reports RMSE)
    "4.3b",                                           # B-spline centerline (builds its own section frames; 4.4 hidden)
    "5.1", "5.2", "5.5", "5.6",                       # deformation parameters (5.3/5.8 3D maps hidden — redundant)
    "6.1", "6.2", "6.3", "6.6",                           # 4D: 6.1 trend, 6.2 M3C2, 6.3 sections, 6.6 export
    "7.1", "7.2",                                     # BIM export (IFC tunnel structure, no components) + AI assistant
    "8.1", "8.2", "8.3", "8.5",                       # export results: CSV / Excel / PDF report / AI work order
}

# Button visibility is documented in docs/UI_BUTTON_REGISTRY.md. Do not
# renumber visible labels here: the user wants existing button names preserved.

# Output tabs hidden in core mode, matched by their English source title.
NON_CORE_TAB_TITLES = {"Polar Deformation"}


class TunnelAnalysisWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self._window_title_src = "Tunnel Analysis v4.0 (r1) - CBNU Smart Structure Lab"
        self.setWindowTitle(self._window_title_src)
        self.resize(1720, 1000)
        self.setAcceptDrops(True)   # drag & drop point-cloud files from Explorer

        self.context   = PipelineContext()
        self.base_mod  = BaseLayer()
        self.pre_mod   = PreprocessingLayer()
        self.reg_mod   = RegistrationLayer()
        self.geo_mod   = GeometricLayer()
        self.seg_mod   = SegmentationLayer()
        self.par_mod   = ParameterExtractionLayer()
        self.ts_mod    = TimeSeriesLayer()
        self.dt_mod    = DigitalTwinAILayer()
        self.exp_mod   = TunnelExporter()
        self.pdf_mod   = TunnelPDFReporter()
        self.ifc_mod   = TunnelIFCExporter()
        self.tgt_mod   = TargetDetector()
        self._targets: List[Target] = []   # all detected targets
        self._manual_pick_mode: bool = False   # manual picking active
        self.rag_mod   = TunnelRAGAssistant()
        self._multi_epoch_series: Optional[Dict] = None
        self._forecast_data: Optional[Dict] = None
        # Initialize RAG in background
        import threading
        threading.Thread(target=self._init_rag, daemon=True).start()

        self.plotter:        Optional[QtInteractor]   = None
        self.worker_thread: Optional[QtCore.QThread] = None
        self.worker:        Optional[PipelineWorker] = None
        self._all_sub_btns: List[QtWidgets.QPushButton] = []
        self._station_colors = [
            "#EF4444", "#3B82F6", "#10B981", "#F59E0B",
            "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16",
        ]
        self._show_viewport_text_overlays = False
        self._show_warning_text_labels = False
        self._noise_pts:    Optional[np.ndarray] = None  # current noise candidates
        self._kept_pts:     Optional[np.ndarray] = None  # current kept candidates
        self._noise_panel:  Optional[QtWidgets.QWidget] = None
        self._noise_visible: bool = True   # show/hide red noise points in 3D
        self._noise_actor = None           # PyVista actor for removed noise
        self._task_dialog = None           # TaskProgressDialog while a worker runs
        self._task_start_ms: int = 0       # QDateTime msecs when current task began
        self._auto_running: bool = False  # True while AUTO PIPELINE is driving steps
        self._ai_tab_idx:   int = 0   # overwritten in _build_ui via addTab return value
        self._section_tab_idx: int = 0  # overwritten in _build_ui via addTab return value
        self._sections: List[CollapsibleSection] = []
        self._hdr_title_src = "Tunnel Analysis v4.0"
        self._hdr_desc_src  = "Select a structural analysis workflow from the sidebar."

        self.settings = QtCore.QSettings("SSL", "TunnelMonitoring")
        saved = self.settings.value("ui/language", "en")
        self.current_language = saved if saved in get_available_languages() else "en"
        self._show_advanced_buttons = str(
            self.settings.value("ui/show_advanced_buttons", "true" if SHOW_ADVANCED_BUTTONS else "false")
        ).lower() in ("1", "true", "yes", "on")

        self._build_ui()
        self._apply_theme()
        self._init_pyvista()
        self._retranslate_v4()

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        self.setCentralWidget(central)
        root.addWidget(self._build_sidebar())

        right = QtWidgets.QWidget(); rlay = QtWidgets.QVBoxLayout(right)
        rlay.setContentsMargins(14, 12, 14, 12); rlay.setSpacing(10)
        root.addWidget(right, 1)

        self.header = QtWidgets.QFrame(); self.header.setObjectName("Header")
        hlay = QtWidgets.QVBoxLayout(self.header); hlay.setContentsMargins(14, 10, 14, 10)
        self.task_title = QtWidgets.QLabel("Tunnel Analysis v4.0")
        self.task_title.setObjectName("TaskTitle")
        self.task_desc  = QtWidgets.QLabel("Select a structural analysis workflow from the sidebar.")
        self.task_desc.setWordWrap(True); self.task_desc.setObjectName("TaskDescription")
        hlay.addWidget(self.task_title); hlay.addWidget(self.task_desc)
        rlay.addWidget(self.header)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal); rlay.addWidget(splitter, 1)

        # ── Chainage ruler — always visible below the 3D viewport ───────────
        # Shows the full tunnel chainage with CRITICAL (red ▼) / CAUTION (amber ▼)
        # markers so dangerous sections are visible from any tab.
        self._chainage_ruler = ChainageRulerWidget()
        self._chainage_ruler.jumped.connect(self._slot_chainage_ruler_jump)
        rlay.addWidget(self._chainage_ruler)

        self.vp_frame  = QtWidgets.QFrame(); self.vp_frame.setObjectName("ViewportFrame")
        self.vp_layout = QtWidgets.QVBoxLayout(self.vp_frame)
        self.vp_layout.setContentsMargins(0, 0, 0, 0); self.vp_layout.setSpacing(0)
        splitter.addWidget(self.vp_frame)

        self.right_tabs = QtWidgets.QTabWidget()
        self.right_tabs.setMinimumWidth(460); splitter.addWidget(self.right_tabs)
        splitter.setSizes([1100, 620])

        self.results_text = QtWidgets.QPlainTextEdit(); self.results_text.setReadOnly(True)
        self.right_tabs.addTab(self.results_text, "Results Log")

        # ── Analysis Summary Dashboard ──────────────────────────────────────
        # Created here (early) so it can be embedded into the 2D section tab.
        # NOT added to right_tabs as a standalone tab — see the 2D section block.
        self.dashboard_widget = SummaryDashboardWidget()
        self._dashboard_tab_idx = 0   # will be updated when the section tab is added

        # Parameters table: unit-aware values grouped by theme with a status
        # column (OK/CAUTION/CRITICAL), fed by _fill_param_table via _show_params.
        self.param_table = QtWidgets.QTableWidget(0, 4)
        self.param_table.setHorizontalHeaderLabels(["Parameter", "Value", "Unit", "Status"])
        self.param_table.horizontalHeader().setStretchLastSection(True)
        self.param_table.verticalHeader().setVisible(False)
        self.param_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.right_tabs.addTab(self.param_table, "Parameters")

        self.meta_table = QtWidgets.QTableWidget(0, 2)
        self.meta_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.meta_table.horizontalHeader().setStretchLastSection(True)
        self.right_tabs.addTab(self.meta_table, "Scan Database")

        # Station tree panel (Faro SCENE style)
        self._station_panel = QtWidgets.QWidget()
        st_lay = QtWidgets.QVBoxLayout(self._station_panel)
        st_lay.setContentsMargins(0, 0, 0, 0); st_lay.setSpacing(0)

        # Toolbar
        st_tb = QtWidgets.QFrame()
        st_tb.setStyleSheet("QFrame{background:#0F4C81;padding:4px;}")
        st_tb_lay = QtWidgets.QHBoxLayout(st_tb)
        st_tb_lay.setContentsMargins(8, 4, 8, 4); st_tb_lay.setSpacing(4)
        self._station_title_lbl = QtWidgets.QLabel("Structure")
        self._station_title_lbl.setStyleSheet("color:white;font-weight:bold;font-size:10pt;background:transparent;")
        self._btn_add_station = QtWidgets.QPushButton("+")
        self._btn_add_station.setToolTip("Add scan station")
        self._btn_add_station.setFixedSize(24, 24)
        self._btn_add_station.setStyleSheet(
            "QPushButton{background:#1D4ED8;color:white;border-radius:4px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#2563EB;}")
        self._btn_add_station.clicked.connect(self._slot_1_3_add_scan)
        st_tb_lay.addWidget(self._station_title_lbl, 1)
        st_tb_lay.addWidget(self._btn_add_station)
        st_lay.addWidget(st_tb)

        # Tree widget
        self._station_tree = QtWidgets.QTreeWidget()
        self._station_tree.setHeaderHidden(True)
        self._station_tree.setColumnCount(1)
        self._station_tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._station_tree.setStyleSheet("""
            QTreeWidget {
                border: none; background: #FAFAFA;
                font-size: 9.5pt; font-family: 'Segoe UI';
            }
            QTreeWidget::item {
                padding: 4px 2px; border-bottom: 1px solid #F1F5F9;
                min-height: 28px;
            }
            QTreeWidget::item:selected {
                background: #DBEAFE; color: #1D4ED8;
            }
            QTreeWidget::item:hover {
                background: #EFF6FF;
            }
        """)
        self._station_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._station_tree.customContextMenuRequested.connect(self._station_context_menu)
        self._station_tree.currentItemChanged.connect(self._on_station_tree_changed)
        self._station_tree.itemChanged.connect(self._on_station_item_changed)
        st_lay.addWidget(self._station_tree, 1)

        # Bottom toolbar
        st_bot = QtWidgets.QFrame()
        st_bot.setStyleSheet(
            "QFrame{background:#F1F5F9;border-top-width:1px;border-top-style:solid;"
            "border-top-color:#E2E8F0;padding:2px;}")
        st_bot_lay = QtWidgets.QHBoxLayout(st_bot)
        st_bot_lay.setContentsMargins(6, 2, 6, 2); st_bot_lay.setSpacing(4)
        self._btn_delete_selected_stations = QtWidgets.QPushButton("Delete Selected")
        self._btn_delete_selected_stations.setStyleSheet(
            "QPushButton{background:#FFF7ED;color:#C2410C;border:1px solid #FDBA74;"
            "border-radius:4px;padding:3px 8px;font-weight:600;font-size:8.5pt;}"
            "QPushButton:hover{background:#FFEDD5;}")
        self._btn_delete_selected_stations.clicked.connect(self._delete_selected_stations)
        self._btn_clear_stations = QtWidgets.QPushButton("Clear All")
        self._btn_clear_stations.setStyleSheet(
            "QPushButton{background:#FEE2E2;color:#DC2626;border:1px solid #FCA5A5;"
            "border-radius:4px;padding:3px 8px;font-weight:600;font-size:8.5pt;}"
            "QPushButton:hover{background:#FECACA;}")
        self._btn_clear_stations.clicked.connect(self._clear_all_stations)
        st_bot_lay.addStretch()
        st_bot_lay.addWidget(self._btn_delete_selected_stations)
        st_bot_lay.addWidget(self._btn_clear_stations)
        st_lay.addWidget(st_bot)

        self.right_tabs.addTab(self._station_panel, "Stations")

        # Target Manager panel (Faro SCENE style)
        self._target_panel = QtWidgets.QWidget()
        tgt_lay = QtWidgets.QVBoxLayout(self._target_panel)
        tgt_lay.setContentsMargins(0, 0, 0, 0); tgt_lay.setSpacing(0)

        # Header toolbar
        tgt_tb = QtWidgets.QFrame()
        tgt_tb.setStyleSheet("QFrame{background:#065F46;padding:4px;}")
        tgt_tb_lay = QtWidgets.QHBoxLayout(tgt_tb)
        tgt_tb_lay.setContentsMargins(8, 4, 8, 4); tgt_tb_lay.setSpacing(4)
        self._target_title_lbl = QtWidgets.QLabel("Target Manager")
        self._target_title_lbl.setStyleSheet("color:white;font-weight:bold;font-size:10pt;background:transparent;")
        self._btn_target_detect = QtWidgets.QPushButton("Auto Detect")
        self._btn_target_detect.setStyleSheet(
            "QPushButton{background:#047857;color:white;border-radius:4px;"
            "padding:3px 10px;font-weight:700;border:none;font-size:9pt;}"
            "QPushButton:hover{background:#059669;}")
        self._btn_target_manual = QtWidgets.QPushButton("+ Manual")
        self._btn_target_manual.setStyleSheet(
            "QPushButton{background:#1D4ED8;color:white;border-radius:4px;"
            "padding:3px 10px;font-weight:700;border:none;font-size:9pt;}"
            "QPushButton:hover{background:#2563EB;}")
        self._btn_target_match = QtWidgets.QPushButton("Auto Match")
        self._btn_target_match.setStyleSheet(
            "QPushButton{background:#7C3AED;color:white;border-radius:4px;"
            "padding:3px 10px;font-weight:700;border:none;font-size:9pt;}"
            "QPushButton:hover{background:#6D28D9;}")
        self._btn_target_register = QtWidgets.QPushButton("Register")
        self._btn_target_register.setStyleSheet(
            "QPushButton{background:#DC2626;color:white;border-radius:4px;"
            "padding:3px 10px;font-weight:700;border:none;font-size:9pt;}"
            "QPushButton:hover{background:#B91C1C;}")
        self._btn_target_detect.clicked.connect(self._slot_target_detect)
        self._btn_target_manual.clicked.connect(self._slot_target_manual)
        self._btn_target_match.clicked.connect(self._slot_target_match)
        self._btn_target_register.clicked.connect(self._slot_target_register)
        tgt_tb_lay.addWidget(self._target_title_lbl, 1)
        tgt_tb_lay.addWidget(self._btn_target_detect)
        tgt_tb_lay.addWidget(self._btn_target_manual)
        tgt_tb_lay.addWidget(self._btn_target_match)
        tgt_tb_lay.addWidget(self._btn_target_register)
        tgt_lay.addWidget(tgt_tb)

        # Second row: multi-station target workflow
        tgt_tb2 = QtWidgets.QFrame()
        tgt_tb2.setStyleSheet("QFrame{background:#064E3B;padding:2px;}")
        tgt_tb2_lay = QtWidgets.QHBoxLayout(tgt_tb2)
        tgt_tb2_lay.setContentsMargins(8, 3, 8, 3); tgt_tb2_lay.setSpacing(4)
        self._btn_target_detect_all = QtWidgets.QPushButton("Detect All Stations")
        self._btn_target_detect_all.setStyleSheet(
            "QPushButton{background:#0F766E;color:white;border-radius:4px;"
            "padding:3px 10px;font-weight:700;border:none;font-size:9pt;}"
            "QPushButton:hover{background:#0D9488;}")
        self._btn_target_detect_all.setToolTip(
            "Auto-detect targets (sphere / checkerboard / intensity) in ALL loaded scan stations")
        self._btn_target_merge = QtWidgets.QPushButton("Merge Stations")
        self._btn_target_merge.setStyleSheet(
            "QPushButton{background:#B45309;color:white;border-radius:4px;"
            "padding:3px 10px;font-weight:700;border:none;font-size:9pt;}"
            "QPushButton:hover{background:#D97706;}")
        self._btn_target_merge.setToolTip(
            "Chain-register all stations using matched targets (SVD + ICP refinement)")
        self._btn_target_detect_all.clicked.connect(self._slot_target_detect_all)
        self._btn_target_merge.clicked.connect(self._slot_target_merge_chain)
        tgt_tb2_lay.addWidget(self._btn_target_detect_all, 1)
        tgt_tb2_lay.addWidget(self._btn_target_merge, 1)
        tgt_lay.addWidget(tgt_tb2)

        # Target table
        self._target_table = QtWidgets.QTableWidget(0, 7)
        self._target_table_headers_src = ["Name", "Type", "Scan", "X", "Y", "Z", "Conf"]
        self._target_table.setHorizontalHeaderLabels(
            self._target_table_headers_src)
        self._target_table.horizontalHeader().setStretchLastSection(True)
        self._target_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._target_table.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self._target_table.setStyleSheet(
            "QTableWidget{border:none;background:#FAFAFA;font-size:9pt;}"
            "QTableWidget::item{padding:3px 6px;}"
            "QTableWidget::item:selected{background:#DBEAFE;color:#1D4ED8;}"
            "QHeaderView::section{background:#065F46;color:white;padding:4px;"
            "font-weight:600;font-size:8.5pt;border:none;}")
        self._target_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._target_table.customContextMenuRequested.connect(self._target_context_menu)
        self._target_table.cellClicked.connect(self._on_target_selected)
        tgt_lay.addWidget(self._target_table, 1)

        # Status bar
        self._tgt_status = QtWidgets.QLabel("No targets detected.")
        self._tgt_status.setStyleSheet(
            "color:#065F46;font-size:8.5pt;padding:4px 8px;"
            "background:#ECFDF5;border-top:1px solid #A7F3D0;")
        tgt_lay.addWidget(self._tgt_status)
        self.right_tabs.addTab(self._target_panel, "Targets")
        self._station_visibility = {}  # idx -> bool

        self.ts_plot = LinePlotWidget()
        self._ts_tab_idx = self.right_tabs.addTab(self.ts_plot, "Time-Series Plot")

        self.multi_epoch_widget = MultiEpochTimeSeriesWidget()
        if hasattr(self.multi_epoch_widget, "measured_points_visibility_changed"):
            self.multi_epoch_widget.measured_points_visibility_changed.connect(
                self._set_step6_measured_points_visible)
        self._multi_epoch_tab_idx = self.right_tabs.addTab(self.multi_epoch_widget, "Multi-Times Trend")

        self.m3c2_map_widget = M3C2MapWidget()
        self._m3c2_tab_idx = self.right_tabs.addTab(self.m3c2_map_widget, "M3C2 Map (2D)")

        self.section_widget = MatplotlibSectionWidget()

        self.polar_plot = PolarDeformationPlotWidget()
        self.right_tabs.addTab(self.polar_plot, "Polar Deformation")

        ai_panel = QtWidgets.QWidget(); ai_lay = QtWidgets.QVBoxLayout(ai_panel)
        ai_lay.setContentsMargins(8, 8, 8, 8); ai_lay.setSpacing(6)
        self.ai_prompt = QtWidgets.QPlainTextEdit()
        self.ai_prompt.setPlaceholderText(_tr("Enter a structural engineering question for the local AI assistant (Llama 3)...", self.current_language))
        self.ai_prompt.setMaximumHeight(90)
        self.ai_send = QtWidgets.QPushButton(_tr("Query AI Assistant", self.current_language))
        self.ai_send.clicked.connect(self._slot_7_2_query_ai)
        self.ai_resp = QtWidgets.QPlainTextEdit(); self.ai_resp.setReadOnly(True)
        self._ai_query_lbl = QtWidgets.QLabel(_tr("Engineering query:", self.current_language))
        ai_lay.addWidget(self._ai_query_lbl); ai_lay.addWidget(self.ai_prompt)
        ai_lay.addWidget(self.ai_send)
        self._ai_report_lbl = QtWidgets.QLabel(_tr("AI analysis report:", self.current_language))
        ai_lay.addWidget(self._ai_report_lbl); ai_lay.addWidget(self.ai_resp, 1)
        self._ai_tab_idx = self.right_tabs.addTab(ai_panel, "AI Engineering Assistant")

        # ── Last two tabs: 2D Cross-Section then Summary Dashboard ──────────
        # Placed adjacent at the end so the user reviews the 2D section and the
        # overall summary side-by-side in the tab bar (2D = second-to-last,
        # Summary Dashboard = very last).
        self._section_tab_idx = self.right_tabs.addTab(
            self.section_widget, _tr("2D Cross-Section", self.current_language))
        self._dashboard_tab_idx = self.right_tabs.addTab(
            self.dashboard_widget, _tr("Summary Dashboard", self.current_language))

        if CORE_FEATURES_ONLY:
            self._hide_non_core_tabs()

        self.sb_pts  = QtWidgets.QLabel("Points: --")
        self.sb_rmse = QtWidgets.QLabel("RMSE: --")
        self.sb_msg  = QtWidgets.QLabel(_tr("Ready", self.current_language))
        self.sb_prog = QtWidgets.QProgressBar(); self.sb_prog.setRange(0, 100)
        self.statusBar().addWidget(self.sb_pts)
        self.statusBar().addWidget(self.sb_rmse)
        self.statusBar().addWidget(self.sb_msg, 1)
        self.statusBar().addPermanentWidget(self.sb_prog)

    def _build_sidebar(self) -> QtWidgets.QFrame:
        sb = QtWidgets.QFrame(); sb.setObjectName("Sidebar"); sb.setFixedWidth(375)
        out = QtWidgets.QVBoxLayout(sb); out.setContentsMargins(10, 14, 10, 14); out.setSpacing(6)

        self._title_lbl = QtWidgets.QLabel("TUNNEL ANALYSIS"); self._title_lbl.setObjectName("ProductTitle")
        self._subtitle_lbl = QtWidgets.QLabel("v4.0 r1 - CBNU Smart Structure Lab"); self._subtitle_lbl.setObjectName("LabSubtitle")
        out.addWidget(self._title_lbl); out.addWidget(self._subtitle_lbl)

        self.language_switcher = LanguageSwitcher(initial_language=self.current_language)
        self.language_switcher.language_changed.connect(self.change_language)
        out.addWidget(self.language_switcher)

        sep = QtWidgets.QFrame(); sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setObjectName("Separator"); out.addWidget(sep)

        pf_frame = QtWidgets.QGroupBox("Tunnel Profile Type"); self._pf_frame = pf_frame
        pf_frame.setStyleSheet("QGroupBox{color:#334155;border:1px solid #CBD5E1;border-radius:5px;margin-top:6px;padding:4px;}")
        pf_lay = QtWidgets.QHBoxLayout(pf_frame)
        self._profile_combo = QtWidgets.QComboBox()
        self._profile_combo.addItems(TUNNEL_PROFILES)
        # Track whether the user manually picked a profile, so the one-time
        # auto-detect (in _slot_5_7_sections) does not override a deliberate
        # choice. _profile_setting_programmatically guards programmatic updates
        # from being mistaken for a user action.
        self._profile_user_set = False
        self._profile_setting_programmatically = False
        self._profile_combo.currentTextChanged.connect(self._on_profile_changed)
        pf_lay.addWidget(self._profile_combo); out.addWidget(pf_frame)
        if CORE_FEATURES_ONLY:
            # Profile is auto-detected per run (see ParameterExtractionLayer.
            # detect_profile), so the manual selector is hidden in core mode.
            pf_frame.setVisible(False)

        vl_frame = QtWidgets.QGroupBox("Vehicle Clearance Limit (m)"); self._vl_frame = vl_frame
        vl_frame.setStyleSheet("QGroupBox{color:#334155;border:1px solid #CBD5E1;border-radius:5px;margin-top:6px;padding:4px;}")
        vl_lay = QtWidgets.QFormLayout(vl_frame)
        self._sp_vl_w = QtWidgets.QDoubleSpinBox(); self._sp_vl_w.setValue(VL_BOX_W)
        self._sp_vl_h = QtWidgets.QDoubleSpinBox(); self._sp_vl_h.setValue(VL_BOX_H)
        self._sp_vl_r = QtWidgets.QDoubleSpinBox(); self._sp_vl_r.setValue(VL_CIR_R)
        self._lbl_vl_w = QtWidgets.QLabel("Half clear width W:")
        self._lbl_vl_h = QtWidgets.QLabel("Clear height H:")
        self._lbl_vl_r = QtWidgets.QLabel("Circular clearance radius R:")
        vl_lay.addRow(self._lbl_vl_w, self._sp_vl_w)
        vl_lay.addRow(self._lbl_vl_h, self._sp_vl_h)
        vl_lay.addRow(self._lbl_vl_r, self._sp_vl_r)
        out.addWidget(vl_frame)

        # Analysis resolution: define the number of cross-sections either
        # directly (count) or by axial spacing in metres (count is then derived
        # from the measured tunnel length). Both feed section_count into the
        # centerline + 5.7 section pass (= centerline control points / frames).
        sc_frame = QtWidgets.QGroupBox("Analysis Resolution"); self._sc_frame = sc_frame
        sc_frame.setStyleSheet("QGroupBox{color:#334155;border:1px solid #CBD5E1;border-radius:5px;margin-top:6px;padding:4px;}")
        sc_lay = QtWidgets.QFormLayout(sc_frame)
        self._cmb_res_mode = QtWidgets.QComboBox()
        self._cmb_res_mode.addItems(["By count", "By spacing (m)"])
        self._lbl_res_mode = QtWidgets.QLabel("Resolution mode:")
        sc_lay.addRow(self._lbl_res_mode, self._cmb_res_mode)
        self._sp_sections = QtWidgets.QSpinBox()
        self._sp_sections.setRange(8, 400)
        self._sp_sections.setSingleStep(10)
        self._sp_sections.setValue(80)
        self._sp_sections.setToolTip("Number of cross-sections along the tunnel (centerline control points). Higher = finer detail, slower.")
        self._lbl_sections = QtWidgets.QLabel("Number of sections:")
        sc_lay.addRow(self._lbl_sections, self._sp_sections)
        self._sp_spacing = QtWidgets.QDoubleSpinBox()
        self._sp_spacing.setRange(0.1, 20.0)
        self._sp_spacing.setSingleStep(0.25)
        self._sp_spacing.setDecimals(2)
        self._sp_spacing.setValue(0.75)
        self._sp_spacing.setSuffix(" m")
        self._sp_spacing.setToolTip("Target axial distance between cross-sections. The section count is derived from the measured tunnel length.")
        self._lbl_spacing = QtWidgets.QLabel("Section spacing:")
        sc_lay.addRow(self._lbl_spacing, self._sp_spacing)
        self._cmb_res_mode.currentIndexChanged.connect(self._on_res_mode_changed)
        self._on_res_mode_changed(0)
        out.addWidget(sc_frame)
        if CORE_FEATURES_ONLY:
            # Manual vehicle-clearance entry is hidden in core mode; the gauge
            # is derived automatically from the measured tunnel radius
            # (see _auto_set_clearance) so it no longer false-alarms.
            vl_frame.setVisible(False)

        # ── Auto Pipeline button ──────────────────────────────────────
        auto_btn = QtWidgets.QPushButton("AUTO PIPELINE  (1-click full analysis)")
        auto_btn.setObjectName("AutoPipelineBtn")
        auto_btn.setMinimumHeight(42)
        auto_btn.setStyleSheet("""
            QPushButton#AutoPipelineBtn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #0F4C81, stop:1 #1D4ED8);
                color: white; font-size: 11pt; font-weight: 800;
                border-radius: 8px; border: none; padding: 8px 12px;
                letter-spacing: 0.5px;
            }
            QPushButton#AutoPipelineBtn:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1D4ED8, stop:1 #2563EB);
            }
            QPushButton#AutoPipelineBtn:disabled {
                background: #94A3B8; color: #E2E8F0;
            }
        """)
        auto_btn.clicked.connect(self._slot_auto_pipeline)
        out.addWidget(auto_btn)
        self._auto_btn = auto_btn
        reset_btn = QtWidgets.QPushButton("Reset Pipeline"); self._reset_btn = reset_btn
        reset_btn.setMinimumHeight(30)
        reset_btn.setStyleSheet(
            "QPushButton{background:#FEE2E2;color:#DC2626;border:1px solid #FCA5A5;"
            "border-radius:6px;padding:4px;font-weight:600;font-size:9pt;}"
            "QPushButton:hover{background:#FECACA;}")
        reset_btn.clicked.connect(self._slot_reset_pipeline)
        out.addWidget(reset_btn)

        adv_cb = QtWidgets.QCheckBox("Show Advanced")
        adv_cb.setChecked(self._show_advanced_buttons)
        adv_cb.setToolTip("Show advanced/debug buttons after restarting the tool.")
        adv_cb.toggled.connect(self._on_advanced_buttons_toggled)
        out.addWidget(adv_cb)
        self._advanced_buttons_cb = adv_cb

        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        out.addWidget(scroll, 1)
        sc = QtWidgets.QWidget(); sl = QtWidgets.QVBoxLayout(sc)
        sl.setContentsMargins(0, 0, 0, 0); sl.setSpacing(4); scroll.setWidget(sc)

        SECTIONS = [
            (1, "LiDAR data acquisition", "Base", [
                ("1.1  Import / add scan station(s)", self._slot_1_1_import),
                ("1.9  Load epoch folder T0→Tn", self._slot_1_9_epoch_folder),
                ("1.9b Load demo T0~T5 (time_series_deformation)", self._slot_1_9_demo_timeseries),
                ("1.2  Initialize 3D viewport", self._slot_1_2_viewport),
                ("1.4  Register & merge all stations", self._slot_1_4_merge),
                ("1.8  Load T0 and Tn times", self._slot_1_8_times),
                ("1.5  Rough alignment (manual)", self._slot_1_5_rough),
                ("1.6  Chain register & merge", self._slot_1_6_chain),
                ("1.7  Registration error heatmap", self._slot_1_7_reg_error),
            ]),
            (2, "Preprocessing and noise filtering", "Pre.", [
                ("2.0  Range crop (drop far points)", self._slot_2_0_range_crop),
                ("2.1  Voxel downsampling", self._slot_2_1_voxel),
                ("2.5  Clean noise (auto: cables, lights, people, wall cables)", self._slot_2_5_auto_denoise),
                ("2.2  Statistical outlier removal", self._slot_2_2_sor),
                ("2.3  Extract tunnel lining shell", self._slot_2_3_lining),
                ("2.3b Extract lining by label (FY387/STSD)", self._slot_2_3b_lining_label),
                ("2.4  Semantic noise removal (PDF 3.2)", self._slot_2_4_semantic),
                ("2.6  Extract lining (density-variation)", self._slot_2_6_density_lining),
            ]),
            (3, "Registration and synchronization", "Reg.", [
                ("3.0  Auto-align T0/Tn times (target or ICP)", self._slot_3_0_register_times),
                ("3.1  Anchor translation", self._slot_3_1_anchor),
                ("3.2  Fine surface ICP", self._slot_3_2_icp),
                ("3.3  Calculate RMSE", self._slot_3_3_rmse),
            ]),
            (4, "Geometric coordinate system", "Geo.", [
                ("4.1  Extract PCA centerline", self._slot_4_1_centerline),
                ("4.2  Iterative centerline refinement", self._slot_4_2_iterative),
                ("4.3  Smooth B-Spline centerline", self._slot_4_3_bspline),
                ("4.3b B-Spline C2 centerline (PDF 3.4)", self._slot_4_3b_bspline),
                ("4.4  Generate gravity-aligned N-B sections", self._slot_4_4_frenet),
                ("4.5  Detect ring seams", self._slot_4_5_seams),
                ("4.5b Intensity ring seam detection (PDF 3.3)", self._slot_4_5b_intensity_seams),
            ]),
            (5, "Parameter extraction", "Param.", [
                ("5.1  Crown settlement dv", self._slot_5_1_settlement),
                ("5.2  Horizontal convergence dh", self._slot_5_2_convergence),
                ("5.3  3D deformation heatmap", self._slot_5_3_heatmap),
                ("5.3b Hausdorff heatmap T0→Tn (PDF 3.5)", self._slot_5_3b_hausdorff),
                ("5.4  Polar radial deformation dr", self._slot_5_4_polar),
                ("5.5  Ovality epsilon", self._slot_5_5_ovality),
                ("5.6  Section eccentricity e", self._slot_5_6_eccentricity),
                ("5.8  Deformation / clearance 3D warning map", self._slot_5_8_clearance_3d),
            ]),
            (6, "Time-series analysis", "T-S", [
                ("6.1  Deformation trend + forecast T0→Tn", self._slot_6_2_plot),
                ("6.2  M3C2 deformation map T0→Tn", self._slot_6_3_m3c2),
                ("6.3  Plot 2D Technical Section T0/Tn", self._slot_6_3_sections),
            ]),
            (7, "BIM, reporting and AI", "BIM/Out", [
                ("7.1  Export IFC tunnel structure", self._slot_7_1_ifc),
                ("7.1b Export IFC4X3 (IfcAlignment)", self._slot_7_1b_ifc_alignment),
                ("7.1c Export IFC + components (cables/lights)", self._slot_7_1c_ifc_components),
                ("6.6  Export time-series report (Excel/PDF)", self._slot_6_6_export_timeseries),
                ("8.1  Export section CSV", self._slot_8_1_csv),
                ("8.2  Export Excel report", self._slot_8_2_excel),
                ("8.3  Export PDF report", self._slot_8_3_pdf),
                ("8.5  Generate AI work order (PDF)", self._slot_8_5_work_order),
                ("7.2  Query structural AI assistant", self._slot_7_2_query_ai),
            ]),
            (8, "Web dashboard", "Web", [
                ("8.4  Open web dashboard", self._slot_8_4_web),
            ]),
        ]
        for step, title_s, tag, buttons in SECTIONS:
            if CORE_FEATURES_ONLY and not self._show_advanced_buttons:
                # Keep only Public buttons in the simple 7-step UI.  Button
                # labels are preserved exactly; Advanced buttons are hidden,
                # not deleted. See docs/UI_BUTTON_REGISTRY.md.
                buttons = [(label, slot) for label, slot in buttons
                           if label.split()[0] in CORE_STEP_CODES]
                if not buttons:
                    continue
            sec = CollapsibleSection(title_s, step, tag)
            for label, slot in buttons:
                btn = sec.add_sub_button(label, slot); self._all_sub_btns.append(btn)
            sl.addWidget(sec)
            self._sections.append(sec)

        sl.addStretch()
        self.pt_label   = QtWidgets.QLabel("Points: --")
        self.rmse_label = QtWidgets.QLabel("RMSE: --")
        out.addWidget(self.pt_label); out.addWidget(self.rmse_label)
        return sb

    def _on_profile_changed(self, text: str) -> None:
        self.context.tunnel_profile = text
        # A change the user made by hand pins the choice; programmatic updates
        # (the auto-detect default) do not.
        if not self._profile_setting_programmatically:
            self._profile_user_set = True

    def _on_advanced_buttons_toggled(self, checked: bool) -> None:
        self._show_advanced_buttons = bool(checked)
        self.settings.setValue("ui/show_advanced_buttons", "true" if checked else "false")
        self._log(
            _tr("Advanced buttons setting saved. Restart the tool to apply sidebar changes.", self.current_language)
        )
        QtWidgets.QMessageBox.information(
            self,
            _tr("Advanced Buttons", self.current_language),
            _tr("Advanced buttons setting saved. Restart the tool to apply sidebar changes.", self.current_language),
        )

    def _hide_non_core_tabs(self) -> None:
        """Hide advanced output tabs while keeping their widgets and tab
        indices intact (so hard-coded setCurrentIndex calls stay valid)."""
        for i in range(self.right_tabs.count()):
            if self.right_tabs.tabText(i) in NON_CORE_TAB_TITLES:
                self.right_tabs.setTabVisible(i, False)

    def _init_pyvista(self) -> None:
        while self.vp_layout.count():
            item = self.vp_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        global pv
        if pv is None:
            # `pv` is lazy-loaded in common.make_vertex_cloud; the `import *`
            # binding here stays None until then, so trigger the real import
            # ourselves rather than reporting a false "not installed".
            try:
                import pyvista as _pv
                pv = _pv
                try: pv.global_theme.silence_errors = True
                except Exception: pass
            except ImportError:
                self._vp_msg("PyVista is not installed."); return
        try:
            # auto_update=False disables pyvistaqt's background render timer
            # (default 5 fps). On large clouds / weak GPUs that timer keeps
            # re-issuing render_window.Render() and pins the GPU, making the
            # app appear to hang (the repeated KeyboardInterrupt seen in
            # render). We render on-demand after each _render_* call instead.
            global QtInteractor
            if QtInteractor is None:
                try:
                    import vtk
                    vtk.vtkObject.GlobalWarningDisplayOff()
                    if hasattr(vtk, "vtkLogger"):
                        vtk.vtkLogger.SetStderrVerbosity(vtk.vtkLogger.VERBOSITY_OFF)
                except Exception:
                    pass
                from pyvistaqt import QtInteractor as _QtInteractor
                QtInteractor = _QtInteractor
            self.plotter = QtInteractor(self.vp_frame, auto_update=False); self.plotter.set_background("#FFFFFF")
            self.vp_layout.addWidget(self.plotter, 1); self.plotter.add_axes(color="#111827")
            self.plotter.show_bounds(color="#94A3B8", grid="front", location="outer", font_size=8)
            self.plotter.render()
        except Exception as exc: self.plotter = None; self._vp_msg(f"Failed to initialize PyVista: {exc}")

    def _vp_msg(self, msg: str) -> None:
        lbl = QtWidgets.QLabel(msg); lbl.setAlignment(QtCore.Qt.AlignCenter)
        lbl.setWordWrap(True); lbl.setObjectName("ViewportMessage")
        self.vp_layout.addWidget(lbl, 1)

    def _estimate_eta_seconds(self, key: str) -> float:
        """Rough ETA from the active workload size and the task type, used to
        drive the progress dialog's countdown. Heuristic, not exact."""
        pts = self.context.working_points
        n = int(len(pts)) if pts is not None else 0
        if n == 0 and self.context.active_scan is not None:
            n = int(len(self.context.active_scan.points))
        million = n / 1.0e6
        # Per-million-point cost (seconds) by task family; tuned conservatively.
        rate = 2.0
        if key in ("2.5_auto_denoise",):                 rate = 60.0
        elif key in ("2.6_density_lining",):             rate = 25.0
        elif key in ("2.2_sor", "2.3_lining", "2.4_semantic"): rate = 12.0
        elif key.startswith(("3.", "1.4", "1.6")):       rate = 15.0
        elif key.startswith(("5.", "6.")):               rate = 10.0
        return max(0.6, million * rate)

    def _start_worker(self, key: str, cb: Callable[[], object]) -> None:
        if self.worker_thread is not None: self._log(_tr("A workflow task is already running.", self.current_language)); return
        self._btns_enabled(False); self.sb_prog.setValue(10); self.sb_msg.setText(_tr("Running task: {key} ...", self.current_language).format(key=key))
        self._show_task_dialog(key)
        self.worker_thread = QtCore.QThread(self)
        self.worker = PipelineWorker(key, cb); self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_finished); self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.worker_thread.quit); self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater); self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self._clear_worker); self.worker_thread.start()

    @QtCore.Slot()
    def _clear_worker(self) -> None:
        self.worker_thread = None; self.worker = None; self._btns_enabled(True); self.sb_prog.setValue(0)

    def _show_task_dialog(self, key: str) -> None:
        """Show the elapsed-time / ETA progress dialog for EVERY manual feature
        (the 1.5 s threshold was removed on request, so even quick tasks show a
        timer). Still skipped during AUTO mode — the sidebar button reports
        per-step progress there and 7 popups would just flash."""
        self._close_task_dialog()
        if self._auto_running:
            return
        eta = self._estimate_eta_seconds(key)
        title = _tr("Processing: {key}", self.current_language).format(key=key)
        try:
            self._task_dialog = TaskProgressDialog(
                title, eta, lambda s: _tr(s, self.current_language), self)
            self._task_dialog.show()
        except Exception as exc:
            self._task_dialog = None
            self._log(f"Progress dialog unavailable: {exc}")

    def _close_task_dialog(self, completed: bool = False) -> None:
        dlg = self._task_dialog
        self._task_dialog = None
        if dlg is None:
            return
        try:
            if completed:
                dlg.finish()
            else:
                dlg.close()
        except Exception:
            pass

    def _btns_enabled(self, en: bool) -> None:
        for b in self._all_sub_btns: b.setEnabled(en)

    @QtCore.Slot(str, object)
    def _on_finished(self, key: str, result: object) -> None:
        self.sb_prog.setValue(100); self.sb_msg.setText(_tr("Task completed: {key}", self.current_language).format(key=key)); self._close_task_dialog(completed=True); self._dispatch(key, result); self._check_auto_pipeline(key)

    @QtCore.Slot(str, str)
    def _on_failed(self, key: str, msg: str) -> None:
        self.sb_prog.setValue(0); self.sb_msg.setText(_tr("Task failed: {key}", self.current_language).format(key=key)); self._close_task_dialog()
        self._log(f"[SYSTEM ERROR] {key}: {msg}")
        if self._auto_running:
            self._auto_running = False
            if hasattr(self, "_auto_btn"):
                self._auto_btn.setEnabled(True)
                self._auto_btn.setText(_tr("AUTO PIPELINE  (1-click full analysis)", self.current_language))
            self._log(_tr("AUTO PIPELINE aborted: step {key} failed.", self.current_language).format(key=key))
        QtWidgets.QMessageBox.critical(self, _tr("Task error: {key}", self.current_language).format(key=key), msg)

    def _offer_open_exported_file(self, path: str, label: str = "Export") -> None:
        """Ask the user whether to open an exported file."""
        if not path:
            return
        try:
            from pathlib import Path as _Path
            file_path = _Path(str(path))
            if not file_path.exists():
                return
            lang = self.current_language
            reply = QtWidgets.QMessageBox.question(
                self,
                _tr("Export complete", lang),
                _tr("{label} exported successfully:\n{path}\n\nOpen this file now?", lang).format(
                    label=label, path=str(file_path)),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes,
            )
            if reply == QtWidgets.QMessageBox.Yes:
                import os
                os.startfile(str(file_path))
        except Exception as exc:
            self._log(f"Open exported file failed: {exc}")

    def _dispatch(self, key: str, result: object) -> None:
        if key == "1.1_import":
            b: PointCloudBundle = result
            self.context.scans.append(b); self.context.active_index = len(self.context.scans) - 1
            self._render_bundle(b, "1.1 Data Acquisition"); self._update_meta(b)
            n = len(b.points); self.pt_label.setText(f"Points: {n:,}"); self.sb_pts.setText(f"Points: {n:,}")
            self._log(f"Loaded point cloud successfully from: {b.path}")
            self._refresh_station_list()
            self._render_station_markers()

        elif key == "1.3_add_scan":
            b: PointCloudBundle = result
            self.context.scans.append(b)
            self._log(f"Station {len(self.context.scans)} loaded: {b.path} ({len(b.points):,} pts)")
            self._update_meta(b)
            self._refresh_station_list()
            self._render_station_markers()
        elif key == "1.3_add_batch":
            scans = result
            for b in scans:
                self.context.scans.append(b)
                self._log(f"Station {len(self.context.scans)} loaded: {b.path} ({len(b.points):,} pts)")
            if scans:
                last = scans[-1]
                self.context.active_index = len(self.context.scans) - 1
                self._render_bundle(last, "Scan Stations Loaded")
                self._update_meta(last)
                n = len(last.points)
                self.pt_label.setText(f"Points: {n:,}")
                self.sb_pts.setText(f"Points: {n:,}")
            self._refresh_station_list()
            self._render_station_markers()
            self._log(_tr("Loaded {n} scan station(s).", self.current_language).format(n=len(scans)))
        elif key == "1.9_epoch_folder":
            scans = result
            self._activate_epoch_scans(scans)
        elif key == "target_detect":
            new_targets: List[Target] = result
            self._targets.extend(new_targets)
            self._refresh_target_table()
            self._render_target_markers()
            n_sph = sum(1 for t in new_targets if t.type == "sphere")
            n_flt = sum(1 for t in new_targets if t.type == "flat")
            n_chk = sum(1 for t in new_targets if t.type == "checkerboard")
            n_int = sum(1 for t in new_targets if t.type == "intensity")
            n_man = sum(1 for t in new_targets if t.type == "manual")
            # Switch to Targets tab
            for i in range(self.right_tabs.count()):
                if self.right_tabs.tabText(i) == "Targets":
                    self.right_tabs.setCurrentIndex(i); break
            # Show result dialog
            if len(new_targets) == 0:
                _lang = self.current_language
                QtWidgets.QMessageBox.warning(self, _tr("Target Detection", _lang),
                    _tr("No targets found.", _lang) + chr(10) + chr(10) +
                    _tr("Try adjusting parameters:", _lang) + chr(10) +
                    _tr("- Lower intensity percentile (e.g. 90%)", _lang) + chr(10) +
                    _tr("- Lower min cluster points (e.g. 10)", _lang) + chr(10) +
                    _tr("- Lower min contrast ratio (e.g. 1.2)", _lang) + chr(10) +
                    _tr("- Check if file has intensity/color data", _lang))
                self._log(_tr("Target detection: 0 targets found.", self.current_language))
            else:
                _lang = self.current_language
                lines = [_tr("Found {n} target(s):", _lang).format(n=len(new_targets))]
                if n_sph: lines.append(_tr("  Sphere:       {n}", _lang).format(n=n_sph))
                if n_chk: lines.append(_tr("  Checkerboard: {n}", _lang).format(n=n_chk))
                if n_int: lines.append(_tr("  Intensity:    {n}", _lang).format(n=n_int))
                if n_man: lines.append(_tr("  Manual:       {n}", _lang).format(n=n_man))
                lines.append("")
                lines.append(_tr("Targets are shown in the table and marked on 3D viewport.", _lang))
                QtWidgets.QMessageBox.information(self, _tr("Target Detection Complete", _lang),
                    chr(10).join(lines))
                self._log(f"Target detection: {len(new_targets)} found "
                          f"(sphere={n_sph}, checkerboard={n_chk}, intensity={n_int})")
                for t in new_targets:
                    self._log(f"  [{t.type}] {t.name} conf={t.confidence:.2f} n={t.n_points}")
        elif key == "target_register":
            T, rmse, residuals, reg_pts = result
            if reg_pts is not None:
                self.context.registered_points = reg_pts
                self._render_pts(reg_pts, "Target-based Registration", "#10B981")
                self.pt_label.setText(f"Points: {len(reg_pts):,}")
            self._log(f"Target-based registration: RMSE = {rmse:.3f} mm")
            for sid, tid, res in residuals:
                status = "OK" if res < 2.0 else "CAUTION" if res < 5.0 else "POOR"
                self._log(f"  {sid} <-> {tid}: {res:.3f} mm [{status}]")

        elif key == "target_detect_all":
            new_targets: List[Target] = result
            self._targets.clear()
            self._targets.extend(new_targets)
            self._refresh_target_table()
            self._render_target_markers()
            for i in range(self.right_tabs.count()):
                if self.right_tabs.tabText(i) == "Targets":
                    self.right_tabs.setCurrentIndex(i); break
            n_stations = len(set(t.scan_idx for t in new_targets)) if new_targets else 0
            self._log(f"Detect All: {len(new_targets)} targets in {n_stations} station(s):")
            for s in range(n_stations):
                st = [t for t in new_targets if t.scan_idx == s]
                n_sph = sum(1 for t in st if t.type == "sphere")
                n_flt = sum(1 for t in st if t.type in ("flat", "checkerboard"))
                n_ity = sum(1 for t in st if t.type == "intensity")
                self._log(f"  Station {s+1}: {len(st)} targets  (sphere={n_sph} flat={n_flt} intensity={n_ity})")
            if not new_targets:
                self._log("  No targets found. Check scan intensity data.")

        elif key == "target_merge_chain":
            merged_pts, rmse_list = result
            self.context.registered_points = merged_pts
            self._render_pts(merged_pts, f"Target Chain: {len(rmse_list)} stations", "#10B981")
            self.pt_label.setText(f"Points: {len(merged_pts):,}")
            self.sb_pts.setText(f"Points: {len(merged_pts):,}")
            avg_rmse = (sum(rmse_list[1:]) / max(1, len(rmse_list) - 1)) if len(rmse_list) > 1 else 0.0
            rt = f"{avg_rmse:.3f} mm"
            self.rmse_label.setText(f"RMSE: {rt}")
            self.sb_rmse.setText(f"RMSE: {rt}")
            self._log(f"Target chain registration: {len(rmse_list)} stations merged. Avg RMSE: {rt}")
            self._log(f"  Station 1: reference (0.000 mm)")
            for i, r in enumerate(rmse_list[1:], start=2):
                status = "OK" if r < 2.0 else "CAUTION" if r < 5.0 else "POOR"
                self._log(f"  Station {i}: RMSE = {r:.3f} mm [{status}]")

        elif key == "1.6_chain":
            pts, rmse_list = result
            self.context.registered_points = pts
            self._render_pts(pts, f"Chain Registered: {len(self.context.scans)} stations", "#10B981")
            self.sb_pts.setText(f"Points: {len(pts):,}")
            self.pt_label.setText(f"Points: {len(pts):,}")
            self._log(f"Chain registration complete: {len(pts):,} total points")
            for i, rmse in enumerate(rmse_list):
                status = "OK" if rmse < 2.0 else "CAUTION" if rmse < 5.0 else "POOR"
                self._log(f"  Station {i+1}: RMSE = {rmse:.3f} mm [{status}]")
        elif key == "1.7_reg_error":
            pts, dist_mm, colors = result
            pts, dist_mm = self._decimate_for_display(pts, dist_mm)
            mesh = make_vertex_cloud(pts)
            if dist_mm is not None and len(dist_mm) == mesh.n_points:
                mesh["RegError_mm"] = dist_mm
            if self.plotter is not None:
                self.plotter.clear(); self.plotter.set_background("#FFFFFF")
                self.plotter.add_mesh(mesh, scalars="RegError_mm", cmap="RdYlGn_r",
                    style="points", point_size=2.8, render_points_as_spheres=False,
                    reset_camera=True, clim=[0, 5],
                    scalar_bar_args={"title": "Reg Error (mm)"})
                self.plotter.add_text("Registration Error Heatmap",
                    position="upper_left", font_size=11, color="#111827", name="ttl")
                self.plotter.add_axes(color="#111827")
                self.plotter.reset_camera(); self.plotter.render()
            self._log(f"Registration error: median={float(__import__('numpy').median(dist_mm)):.2f}mm max={float(__import__('numpy').max(dist_mm)):.2f}mm")
        elif key == "1.4_merge":
            pts, rmse_list = result
            self.context.registered_points = pts
            self._render_pts(pts, f"Merged {len(self.context.scans)} scan stations", "#10B981")
            self.sb_pts.setText(f"Points: {len(pts):,}")
            self.pt_label.setText(f"Points: {len(pts):,}")
            self._log(f"Merged {len(self.context.scans)} stations: {len(pts):,} total points")
            for i, rmse in enumerate(rmse_list):
                self._log(f"  Station {i+1}: RMSE = {rmse:.3f} mm")
        elif key == "2.0_range_crop":
            pts, stats = result
            pts = np.asarray(pts, dtype=np.float64); self.context.normalized_points = pts
            self._render_pts(pts, "2.0 Range Crop", "#0EA5E9")
            self.sb_pts.setText(f"Points: {len(pts):,}")
            self._log(f"Range crop ({stats.get('mode')}, {stats.get('max_range_m')} m): "
                      f"kept {stats.get('n_clean'):,}/{stats.get('n_raw'):,}, "
                      f"removed {stats.get('n_removed'):,} (max dist {stats.get('max_distance_seen',0):.1f} m).")

        elif key == "2.1_voxel":
            pts, centroid = result; self.context.normalized_points = pts
            raw_n = len(self.context.active_scan.points) if self.context.active_scan else len(pts)
            if len(self.context.scans) >= 2:
                # Keep all stations (T0+Tn) visible; active uses the voxelized cloud.
                self._render_all_stations(active_pts=pts, title="2.1 Voxel Grid Filter (all stations)")
            else:
                self._render_pts(pts, "2.1 Voxel Grid Filter", "#3B82F6")
            self.pt_label.setText(f"Points: {len(pts):,}"); self.sb_pts.setText(f"Points: {len(pts):,}")
            self._log(f"Voxel downsampling complete: {len(pts):,}/{raw_n:,} points retained; centroid shifted to local origin {np.round(centroid, 3).tolist()}.")

        elif key == "2.2_sor":
            if isinstance(result, tuple) and len(result) == 3:
                pts, col, stats = result
            else:
                pts, col = result; stats = {"n_raw": len(pts), "n_clean": len(pts), "n_removed": 0, "outlier_pts": np.empty((0, 3))}
            self._kept_pts  = np.asarray(pts, dtype=np.float64)
            self._noise_pts = np.asarray(stats.get("outlier_pts", np.empty((0, 3))), dtype=np.float64)
            if self.context.active_scan and col is not None: self.context.active_scan.colors_raw = col
            n_raw = stats.get('n_raw', len(pts)); n_rem = stats.get('n_removed', 0)
            if self._auto_running:
                # AUTO mode: apply the cleaned cloud immediately, no manual review.
                self.context.normalized_points = self._kept_pts
                self._render_pts(self._kept_pts, "2.2 SOR — Noise removed (auto)", "#0EA5E9")
                self.pt_label.setText(f"Points: {len(pts):,}"); self.sb_pts.setText(f"Points: {len(pts):,}")
                self._log(f"SOR (auto): {n_raw:,} raw -> {len(pts):,} kept, {n_rem:,} noise removed.")
                self._noise_pts = None; self._kept_pts = None
                return
            self._render_filter_result(self._kept_pts, self._noise_pts, "2.2 SOR — Review noise (red) before confirming")
            self.pt_label.setText(f"Points: {len(pts):,}"); self.sb_pts.setText(f"Points: {len(pts):,}")
            self._log(f"SOR proposal: {n_raw:,} raw -> {len(pts):,} kept, {n_rem:,} noise detected (red).")
            self._log(_tr("Review noise in 3D viewport, then use the noise panel to confirm or adjust.", self.current_language))
            self.sb_msg.setText(_tr("SOR: {n_rem} noise points detected (red) | {n_kept} kept (blue)", self.current_language).format(n_rem=f"{n_rem:,}", n_kept=f"{len(pts):,}"))
            self._show_noise_panel()

        elif key == "2.4_semantic":
            pts, stats = result
            self.context.normalized_points = pts
            noise_pts = np.asarray(stats.get("noise_pts", np.empty((0,3))), dtype=np.float64)
            self.context.denoise_stats = self._extract_denoise_counts(stats)
            self.context.component_points = stats.get("component_points", {}) or {}
            self._render_filter_result(np.asarray(pts, dtype=np.float64), noise_pts,
                "2.4 Semantic Noise Removal | kept=blue, removed=red")
            self.pt_label.setText(f"Points: {len(pts):,}")
            self.sb_pts.setText(f"Points: {len(pts):,}")
            self._log(f"Semantic removal: {stats.get('n_clean',len(pts)):,}/{stats.get('n_raw',len(pts)):,} kept")
            self._log(f"  Cable={stats.get('n_cable',0)} Light={stats.get('n_light',0)} Person={stats.get('n_person',0)}")
        elif key == "2.3_lining":
            pts = np.asarray(result, dtype=np.float64); self.context.normalized_points = pts
            self._render_pts(pts, "2.3 Isolated Tunnel Lining", "#6366F1"); self._log(f"Tunnel lining extraction complete: {len(pts):,} points retained.")

        elif key == "2.3b_lining_label":
            pts, stats = result
            pts = np.asarray(pts, dtype=np.float64); self.context.normalized_points = pts
            self._render_pts(pts, "2.3b Lining by Label", "#6366F1")
            self.sb_pts.setText(f"Points: {len(pts):,}")
            if stats.get("method") == "geometric_fallback":
                self._log(f"Lining by label: no per-point labels, used geometric fallback ({stats.get('n_clean',len(pts)):,} pts).")
            else:
                self._log(f"Lining by label: kept {stats.get('n_clean',len(pts)):,}/{stats.get('n_raw',len(pts)):,} pts, classes {stats.get('structure_labels')} (auto_detected={stats.get('auto_detected')}).")

        elif key == "2.5_auto_denoise":
            pts, stats = result
            pts = np.asarray(pts, dtype=np.float64)
            self.context.normalized_points = pts
            self.context.denoise_stats = self._extract_denoise_counts(stats)
            self.context.component_points = stats.get("component_points", {}) or {}
            noise_pts = np.asarray(stats.get("noise_pts", np.empty((0, 3))), dtype=np.float64)
            if self._auto_running:
                self._render_pts(pts, "2.5 Auto Denoise - Clean lining (auto)", "#0EA5E9")
            elif len(self.context.scans) >= 2:
                # Keep T0+Tn both visible AND still show the removed noise (red)
                # for the active station so denoising stays inspectable.
                self._render_all_stations(active_pts=pts,
                    title="2.2 Auto Denoise (all stations) | removed = red")
                if noise_pts is not None and len(noise_pts) > 0:
                    try:
                        nd = noise_pts
                        if len(nd) > DISPLAY_MAX_POINTS:
                            nd = nd[::int(np.ceil(len(nd) / DISPLAY_MAX_POINTS))]
                        self.plotter.add_mesh(make_vertex_cloud(nd), color="#DC2626",
                            style="points", point_size=3.0, render_points_as_spheres=True,
                            name="removed", reset_camera=False)
                        self.plotter.render()
                    except Exception:
                        pass
            else:
                self._render_filter_result(pts, noise_pts,
                    "2.5 Auto Denoise | lining=blue, removed=red")
            self.pt_label.setText(f"Points: {len(pts):,}")
            self.sb_pts.setText(f"Points: {len(pts):,}")
            self._log(f"Auto denoise: {stats.get('n_clean', len(pts)):,}/{stats.get('n_raw', len(pts)):,} kept, {stats.get('n_removed', 0):,} removed.")
            self._log(f"  Cable={stats.get('n_cable', 0)} Light={stats.get('n_light', 0)} Person/Vehicle={stats.get('n_person', 0)} Radial={stats.get('n_radial', 0)}")

        elif key == "times_register":
            # AUTO PIPELINE step 2b: align Tn onto T0 (different scanner setups).
            if result is None:
                self._log("Times alignment: single scan — skipped (no T0/Tn to align).")
            else:
                self.context.registered_points = np.asarray(result["points"], dtype=np.float64)
                method_vi = ("điểm mốc cố định" if result["method"] == "target"
                             else "ICP cắt tỉa (trimmed)")
                self._log(f"Căn chỉnh T0/Tn: phương pháp = {method_vi}  |  "
                          f"RMSE = {result['rmse_mm']:.2f} mm")
                if result["method"] == "target":
                    self._log(f"  {result['n_targets']} điểm mốc khớp — biến dạng KHÔNG bị triệt tiêu.")
                else:
                    self._log("  Không thấy mốc → trimmed ICP (khớp trên vùng ổn định, giữ biến dạng cục bộ).")
                self.sb_rmse.setText(f"RMSE: {result['rmse_mm']:.2f} mm")
                # Manual run: show the aligned monitoring cloud overlaid on T0.
                if not self._auto_running:
                    try:
                        self._render_pts(self.context.registered_points,
                                         "3.0 Tn aligned to T0 (registered)", "#10B981")
                    except Exception:
                        pass

        elif key == "2.6_density_lining":
            pts, stats = result
            pts = np.asarray(pts, dtype=np.float64)
            self.context.normalized_points = pts
            noise_pts = np.asarray(stats.get("noise_pts", np.empty((0, 3))), dtype=np.float64)
            if self._auto_running:
                self._render_pts(pts, "2.6 Lining (density-variation)", "#6366F1")
            else:
                self._render_filter_result(pts, noise_pts,
                    "2.6 Lining density-variation | lining=blue, removed=red")
            self.pt_label.setText(f"Points: {len(pts):,}")
            self.sb_pts.setText(f"Points: {len(pts):,}")
            self._log(f"Density-variation lining: {stats.get('n_clean', len(pts)):,}/{stats.get('n_raw', len(pts)):,} kept, {stats.get('n_removed', 0):,} interior points removed.")

        elif key == "3.1_anchor":
            pts = np.asarray(result, dtype=np.float64); self.context.registered_points = pts
            self._render_pts(pts, "3.1 Target Anchor Matrix Applied", "#10B981"); self._log(_tr("Target anchor translation matrix applied.", self.current_language))

        elif key == "3.2_icp":
            pts, rmse = result; self.context.registered_points = np.asarray(pts, dtype=np.float64)
            self.context.rmse_mm = rmse; self._render_pts(self.context.registered_points, "3.2 Fine ICP Iterations", "#059669")
            rt = f"{rmse:.3f} mm" if np.isfinite(rmse) else "N/A"
            self.rmse_label.setText(f"RMSE: {rt}"); self.sb_rmse.setText(f"RMSE: {rt}")
            self._log(f"Surface ICP registration complete. Relative RMSE: {rt}")

        elif key == "3.3_rmse":
            rmse = float(result); self.context.rmse_mm = rmse
            rt = f"{rmse:.3f} mm" if np.isfinite(rmse) else "N/A"
            self.rmse_label.setText(f"RMSE: {rt}"); self.sb_rmse.setText(f"RMSE: {rt}")
            self._log(f"Surface model RMSE computed: {rt}")

        elif key == "4.1_centerline":
            cl, fr = result; self.context.centerline = cl; self.context.frenet_frames = fr
            self._render_cl(cl, fr); self._log(f"PCA centerline extracted: {len(cl)} chainage control points.")

        elif key == "4.2_iterative":
            cl, fr, iters = result; self.context.centerline = cl; self.context.frenet_frames = fr
            self._render_cl(cl, fr); self._log(f"Yi (2020) iterative centerline refinement completed after {iters} section-fitting iterations.")

        elif key == "4.3b_bspline":
            cl, fr = result
            self.context.centerline = cl; self.context.frenet_frames = fr
            self._render_cl(cl, fr)
            self._log(f"B-Spline C2 centerline (PDF 3.4): {len(cl)} points, {len(fr)} Frenet frames.")
        elif key == "4.3_bspline":
            sm = np.asarray(result, dtype=np.float64); self.context.centerline_smooth = sm
            if self.plotter:
                self.plotter.add_lines(sm, color="#F59E0B", width=4, connected=True, name="cl_sm")
                self.plotter.render()
            self._log(f"B-Spline centerline smoothing complete: {len(sm)} points (display overlay only; analysis still uses the 4.1/4.3b centerline).")

        elif key == "4.4_frenet":
            self.context.frenet_frames = result
            cl = self.context.centerline
            if cl is not None and len(result):
                # Show the gravity-aligned T/N/B frames on the 3D viewport so
                # the step is visibly doing something (previously it only logged).
                self._render_cl(np.asarray(cl, dtype=np.float64), result)
            self._log(f"Gravity-aligned section frames generated successfully: {len(result)} N-B frames.")
            self._log(_tr("Blue=T (axis), Green=N (lateral), Orange=B (vertical/up).", self.current_language))

        elif key == "4.5b_intensity_seams":
            d = result
            n = len(d.get("chainage_m", []))
            self._log(f"Intensity ring seam detection (PDF 3.3): {n} seams detected.")
            if n:
                self._log(f"  Seam chainages (m): {[round(float(x),2) for x in d['chainage_m']]}")
        elif key == "4.5_seams":
            d: Dict = result; self._log(f"Ring seam detection complete: {d['ring_count']} lining rings segmented, {d['total_seams']} seam boundaries identified.")

        elif key in ("5.1_settlement", "5.2_convergence", "5.5_ovality", "5.6_eccentricity"):
            self.context.parameters.update(result); self._show_params(result)

        elif key == "auto_params":
            # AUTO PIPELINE step 6/6: all four deformation metrics combined.
            self.context.parameters.update(result)
            self._show_params(result)

        elif key == "5.3b_hausdorff":
            pts, dist_mm, colors = result
            self.context.heatmap_scalars = dist_mm
            pts, dist_mm = self._decimate_for_display(pts, dist_mm)
            mesh = __import__("tunnel_analysis.common", fromlist=["make_vertex_cloud"]).make_vertex_cloud(pts)
            if dist_mm is not None and len(dist_mm) == mesh.n_points:
                mesh["Hausdorff_mm"] = dist_mm
            if self.plotter is not None:
                self.plotter.clear(); self.plotter.set_background("#FFFFFF")
                self.plotter.add_mesh(mesh, scalars="Hausdorff_mm", cmap="RdYlGn_r",
                    style="points", point_size=2.8, render_points_as_spheres=False,
                    reset_camera=True, scalar_bar_args={"title": "Distance T0→Tn (mm)"})
                self.plotter.add_text("Hausdorff Heatmap T0→Tn", position="upper_left",
                    font_size=11, color="#111827", name="ttl")
                self.plotter.add_axes(color="#111827"); self.plotter.reset_camera(); self.plotter.render()
            self._log(f"Hausdorff heatmap: median={float(__import__('numpy').median(dist_mm)):.2f}mm max={float(__import__('numpy').max(dist_mm)):.2f}mm")
            self.right_tabs.setCurrentIndex(0)
        elif key == "5.3_heatmap":
            pts, sc = result; self.context.heatmap_scalars = sc; self._render_heatmap(np.asarray(pts, dtype=np.float64), sc)

        elif key == "5.4_polar":
            centers, angles, dmap = result
            self.context.polar_centers = centers; self.context.polar_angles = angles; self.context.polar_map = dmap
            finite = dmap[np.isfinite(dmap)]
            mx = float(np.nanmax(finite)) if finite.size else float("nan")
            mn = float(np.nanmin(finite)) if finite.size else float("nan")
            self.context.parameters.update({"polar_max_outward_mm": mx, "polar_max_inward_mm": mn})
            self.polar_plot.update_data(angles, dmap); self.right_tabs.setCurrentIndex(4)
            self._log(f"Polar radial deformation map generated: max outward={mx:+.2f} mm, max inward={mn:+.2f} mm")

        elif key == "5.8_clearance_3d":
            pts, status_mask, counts = result
            n_caution = int(counts.get("caution_points", 0))
            n_critical = int(counts.get("critical_points", 0))
            n_sections_warn = int(counts.get("warning_sections", 0))
            # Keep ALL warning points (the important highlight); decimate only
            # the gray base cloud for display.
            caution_pts_full = pts[status_mask == 1] if len(status_mask) else np.empty((0, 3))
            critical_pts_full = pts[status_mask == 2] if len(status_mask) else np.empty((0, 3))
            base_pts, _ = self._decimate_for_display(pts)
            mesh = make_vertex_cloud(base_pts)
            if self.plotter is not None:
                self.plotter.clear(); self.plotter.set_background("#FFFFFF")
                self.plotter.add_mesh(mesh, scalars=None, style="points",
                    point_size=2.5, render_points_as_spheres=False,
                    reset_camera=True, color="#94A3B8")
                if len(caution_pts_full):
                    caution_mesh = make_vertex_cloud(caution_pts_full)
                    self.plotter.add_mesh(caution_mesh, color="#D97706",
                        style="points", point_size=5.0,
                        render_points_as_spheres=True,
                        reset_camera=False, name="deformation_caution")
                if len(critical_pts_full):
                    critical_mesh = make_vertex_cloud(critical_pts_full)
                    self.plotter.add_mesh(critical_mesh, color="#DC2626",
                        style="points", point_size=7.0,
                        render_points_as_spheres=True,
                        reset_camera=False, name="deformation_critical")
                self.plotter.add_text(
                    f"Deformation warnings: {n_sections_warn} sections | critical={n_critical} pts | caution={n_caution} pts",
                    position="upper_left", font_size=11,
                    color="#DC2626" if n_critical > 0 else ("#D97706" if n_caution > 0 else "#047857"),
                    name="ttl")
                self.plotter.add_axes(color="#111827")
                self.plotter.reset_camera(); self.plotter.render()
            self._log(f"Deformation/clearance 3D map: warnings={n_sections_warn}, critical_points={n_critical}, caution_points={n_caution}")
            if n_critical > 0 or n_caution > 0:
                from PySide6.QtWidgets import QMessageBox
                _lang = self.current_language
                QMessageBox.warning(self, _tr("Deformation Warning", _lang),
                    f"{n_sections_warn} warning section(s) detected." + chr(10) +
                    f"Critical points: {n_critical:,}" + chr(10) +
                    f"Caution points: {n_caution:,}" + chr(10) +
                    "Red = critical deformation/clearance, amber = caution.")
        elif key == "6.3_sections_auto":
            if isinstance(result, dict):
                cl = result.get("centerline")
                fr = result.get("frenet_frames")
                if cl is not None and fr:
                    self.context.centerline = cl
                    self.context.frenet_frames = fr
                    try:
                        self._render_cl(cl, fr)
                    except Exception:
                        pass
                    self._log(f"Step 6.3 auto-prepared centerline: {len(cl)} points, {len(fr)} frames.")
                result = result.get("sections", [])
            self._dispatch("5.7_sections", result)
            return

        elif key == "5.7_sections":
            sections: List[SectionGeometry] = result; self.context.sections = sections
            # Reflect the profile actually used (auto-detected in the worker /
            # auto-pipeline) back into the dropdown so the UI shows the truth.
            if hasattr(self, "_profile_combo") and self.context.tunnel_profile:
                self._profile_setting_programmatically = True
                self._profile_combo.setCurrentText(self.context.tunnel_profile)
                self._profile_setting_programmatically = False
            self._section_ref_sections = []
            self._section_epoch_sections = []   # filled below when >2 times loaded
            self.section_widget.set_sections(sections, profile=self.context.tunnel_profile, vl_box_w=self._sp_vl_w.value(), vl_box_h=self._sp_vl_h.value(), vl_cir_r=self._sp_vl_r.value(), render_mode="Field Robust")
            try: self.section_widget.section_changed.disconnect()
            except Exception: pass
            self.section_widget.section_changed.connect(self._highlight_section)
            # Set T0 reference sections if available
            if len(self.context.scans) >= 2 and hasattr(self.section_widget, "set_ref_sections"):
                try:
                    from ..models import PipelineContext as _PC
                    ctx0 = _PC(scans=[self.context.scans[0]], active_index=0,
                               normalized_points=self.context.scans[0].points,
                               centerline=self.context.centerline,
                               frenet_frames=self.context.frenet_frames,
                               tunnel_profile=self.context.tunnel_profile)
                    ref_secs = self.par_mod.compute_all_sections(ctx0,
                        vl_box_w=self._sp_vl_w.value(),
                        vl_box_h=self._sp_vl_h.value(),
                        vl_cir_r=self._sp_vl_r.value())
                    self._section_ref_sections = ref_secs
                    self.section_widget.set_ref_sections(ref_secs)
                    self._log(_tr("T0 reference sections loaded for overlay.", self.current_language))
                except Exception as e:
                    self._log(f"T0 overlay: {e}")
            # Multi-times coloured overlay: when more than two times are loaded
            # (T0~Tn), compute each times's sections on the same centerline so the
            # 2D view can draw one coloured outline per times. Runs synchronously
            # like the T0 reference above; fine for the clean fixtures, may take a
            # moment on large real clouds.
            if len(self.context.scans) > 2 and hasattr(self.section_widget, "set_epoch_sections"):
                try:
                    from ..models import PipelineContext as _PC
                    times_secs = []; times_lbls = []
                    for i, sc in enumerate(self.context.scans):
                        ctx_i = _PC(scans=[sc], active_index=0,
                                    normalized_points=sc.points,
                                    centerline=self.context.centerline,
                                    frenet_frames=self.context.frenet_frames,
                                    tunnel_profile=self.context.tunnel_profile)
                        secs_i = self.par_mod.compute_all_sections(ctx_i,
                            vl_box_w=self._sp_vl_w.value(),
                            vl_box_h=self._sp_vl_h.value(),
                            vl_cir_r=self._sp_vl_r.value())
                        times_secs.append(secs_i)
                        times_lbls.append(os.path.splitext(os.path.basename(sc.path or f"T{i}"))[0])
                    self.section_widget.set_section_render_mode("Field Robust")
                    self.section_widget.set_epoch_sections(times_secs, times_lbls)
                    self._section_epoch_sections = times_secs   # for ruler/dashboard/3D
                    # The overlay draws regardless of the (hidden) control row.
                    # When the controls are visible, also tick the box so its
                    # state matches what's drawn.
                    if getattr(self.section_widget, "_show_deform_controls", True):
                        self.section_widget._chk_overlay.setChecked(True)
                    self._log(_tr("Multi-times overlay loaded: {n} times.", self.current_language).format(n=len(times_secs)))
                except Exception as e:
                    self._log(f"Multi-times overlay: {e}")
            self.right_tabs.setCurrentIndex(self._section_tab_idx)
            self._sync_step6_measured_point()
            current_section_idx = int(getattr(self.section_widget, "_idx", 0)) if sections else 0
            if sections:
                current_section_idx = max(0, min(current_section_idx, len(sections) - 1))
                self._highlight_section(current_section_idx)
            # Push section data to dashboard (section alerts list). When >2
            # times are loaded, pass them so statuses reflect the worst times
            # vs T0 (consistent with the 2D warning track).
            ref_secs = getattr(self, "_section_ref_sections", []) or []
            times_secs_all = getattr(self, "_section_epoch_sections", []) or None
            self.dashboard_widget.update_sections(
                sections, ref_secs, profile=self.context.tunnel_profile or "Circle",
                epoch_sections=times_secs_all)
            # Update chainage ruler — warning triangles always visible below viewport.
            if hasattr(self, "_chainage_ruler"):
                _ruler_ref = getattr(self, "_section_ref_sections", []) or []
                self._chainage_ruler.set_sections(sections, _ruler_ref,
                                                   epoch_sections=times_secs_all)
                if hasattr(self, "_trend_hotspots"):
                    self._chainage_ruler.set_hotspots(getattr(self, "_trend_hotspots", []))
                if sections:
                    self._chainage_ruler.set_current(sections[current_section_idx].chainage)
            # Update 3D status HUD now that sections are known.
            self._update_3d_status_hud(self.context.parameters)
            # Overlay coloured warning rings on 3D viewport.
            self._render_warning_markers(sections, ref_secs)
            valid = [s for s in sections if s.pts_2d is not None]
            self._log(_tr("--- 2D technical cross-section analysis ---", self.current_language))
            self._log(f"  Total section slices analyzed along the alignment: {len(sections)}")
            if valid:
                w1s = [s.W1 for s in valid if np.isfinite(s.W1)]
                h1s = [s.H1 for s in valid if np.isfinite(s.H1)]
                if w1s: self._log(f"  Average clear section width W1: {np.mean(w1s):.3f} m")
                if h1s: self._log(f"  Average clear section height H1: {np.mean(h1s):.3f} m")
                ref_secs = getattr(self, "_section_ref_sections", []) or []
                warned = []
                section_statuses = self._classify_section_warning_series(valid, ref_secs)
                for sec, (status, issues) in zip(valid, section_statuses):
                    if status != "OK":
                        warned.append((status, sec.chainage, section_warning_text(issues)))
                if warned:
                    n_crit = sum(1 for status, _, _ in warned if status == "CRITICAL")
                    n_caut = sum(1 for status, _, _ in warned if status == "CAUTION")
                    self._log(f"  DEFORMATION WARNINGS: critical={n_crit}, caution={n_caut}")
                    for status, ch, text in warned[:10]:
                        self._log(f"    [{status}] Ch {ch:.2f}m: {text}")
            self._log("------------------------------------------------")

        elif key in ("1.8_times", "6.1_times"):
            t0, tn = result
            self._activate_times(t0, tn)
            self._log(_tr("T0/Tn times loaded. T0 is reference; Tn is active for Steps 2-5.", self.current_language))

        elif key in ("6.1_plot", "6.2_plot"):  # 6.2_plot legacy alias
            # Combined trend + forecast: worker returns {"series", "forecast"};
            # accept a bare series dict too (back-compat).
            forecast = None
            if isinstance(result, dict) and "series" in result:
                forecast = result.get("forecast")
                result = result.get("series")
            if isinstance(result, dict) and "median_mm" in result:
                self.context.time_series_result = result
                labels = result.get("labels", [])
                method = result.get("method", "time-series")
                median = np.asarray(result.get("median_mm", []), dtype=np.float64)
                p95 = np.asarray(result.get("p95_abs_mm", []), dtype=np.float64)
                crown = np.asarray(result.get("crown_settlement_mm", []), dtype=np.float64)
                if crown.size == len(labels) + 1:
                    plot_series = np.abs(crown)
                    plot_labels = ["T0"] + list(labels)
                    title = f"T0 to Tn crown settlement trend [{method}] at Ch {result.get('crown_chainage_m', 52.0):g}m (mm)"
                else:
                    plot_series = np.concatenate([[0.0], p95]) if len(p95) else np.asarray([], dtype=np.float64)
                    plot_labels = ["T0"] + list(labels) if len(plot_series) == len(labels) + 1 else []
                    title = f"T0 to Tn deformation trend [{method}] fallback overall movement p95 (mm)"
                self.context.time_series_plot = plot_series
                self.ts_plot.set_values(plot_series, title, plot_labels)
                if len(p95):
                    crown_log = np.round(crown, 2).tolist() if crown.size else []
                    self._log(f"Time-series trend [{method}]: times={list(labels)} crown_settlement_mm={crown_log}")
                    if result.get("crown_chainage_m") is not None:
                        self._log(
                            f"  Crown probe chainage: {float(result.get('crown_chainage_m')):.1f} m"
                            f" (source={result.get('crown_chainage_source', 'n/a')})"
                        )
                    self._log_step6_status_banner(result, forecast)
                    self._report_timeseries_extras(result, labels)
                    self._trend_hotspots = self._trend_hotspots_from_series(result)
                    hotspots = self._sync_step6_measured_point()
                    if hotspots:
                        preview = ", ".join(f"{h['label']}@Ch{h['chainage_m']:.1f}m/{h['position']}" for h in hotspots[:4])
                        h = self._active_step6_hotspot
                        metric_name = "crown" if h.get("metric") == "crown_settlement_mm" else "p95"
                        self._log(f"  Step 6 linked hotspot: {h['label']} @ Ch {h['chainage_m']:.2f}m / {h['position']} / {metric_name} {h['value_mm']:.1f}mm")
                        self._log(f"  Same marker appears on trend note, chainage ruler, M3C2 map, and 2D section: {preview}")
                self._forecast_data = forecast
                if forecast and forecast.get("ok"):
                    self._log("  " + forecast.get("summary", ""))
                # Keep latest trend for export (pair T0/Tn and multi-epoch).
                self._multi_epoch_series = result
                if len(labels) >= 2:
                    self.multi_epoch_widget.set_series(result, forecast)
                    self.right_tabs.setCurrentIndex(self._multi_epoch_tab_idx)
                else:
                    self.right_tabs.setCurrentIndex(self._ts_tab_idx)
            else:
                series = np.asarray(result, dtype=np.float64); self.context.time_series_plot = series
                self.ts_plot.set_values(series, "Crown-height trend across chainage (mm)")
                self.right_tabs.setCurrentIndex(self._ts_tab_idx)

        elif key in ("6.2_m3c2", "6.3_m3c2"):  # 6.3_m3c2 legacy alias
            res = result
            self.context.m3c2_result = res
            pts = np.asarray(res["corepoints"], dtype=np.float64)
            dist_mm = np.asarray(res["distance_mm"], dtype=np.float64)
            self.context.heatmap_scalars = dist_mm
            pts, dist_mm = self._decimate_for_display(pts, dist_mm)
            # Damage highlight on the 3D structure: faint grey base, then caution
            # (amber) and critical (red) points on top so damaged zones pop out
            # instead of a uniform rainbow cloud.
            if self.plotter is not None:
                self.plotter.clear(); self.plotter.set_background("#FFFFFF")
                mag = np.abs(dist_mm)
                crit_m = mag >= 25.0
                caut_m = (mag >= 10.0) & ~crit_m
                ok_m = ~(crit_m | caut_m)
                if np.any(ok_m):
                    self.plotter.add_mesh(make_vertex_cloud(pts[ok_m]), color="#CBD5E1",
                        style="points", point_size=4.0, render_points_as_spheres=True,
                        reset_camera=True, name="m3c2_ok")
                if np.any(caut_m):
                    self.plotter.add_mesh(make_vertex_cloud(pts[caut_m]), color="#F59E0B",
                        style="points", point_size=9.0, render_points_as_spheres=True,
                        name="m3c2_caut")
                if np.any(crit_m):
                    self.plotter.add_mesh(make_vertex_cloud(pts[crit_m]), color="#DC2626",
                        style="points", point_size=12.0, render_points_as_spheres=True,
                        name="m3c2_crit")
                compare_label = getattr(self, "_m3c2_compare_label", "T0\u2192Tn")
                self.plotter.add_text(
                    f"M3C2 Damage Map {compare_label}  [{res['method']}]  "
                    f"(amber>=10mm, red>=25mm)",
                    position="upper_left", font_size=11, color="#1E293B", name="ttl")
                self.plotter.add_axes(color="#1E293B"); self.plotter.reset_camera()
                self.plotter.view_xy(); self.plotter.render()
            finite = dist_mm[np.isfinite(dist_mm)]
            med = float(np.median(finite)) if finite.size else float("nan")
            mx = float(np.nanmax(np.abs(finite))) if finite.size else float("nan")
            sig = res.get("significant")
            n_sig = int(np.count_nonzero(sig)) if sig is not None else 0
            n_tot = int(dist_mm.size)
            lod = res.get("lod_mm")
            lod_med = float(np.nanmedian(lod)) if lod is not None and np.isfinite(lod).any() else float("nan")
            self._log(f"M3C2 [{res['method']}]: median={med:+.2f}mm max|d|={mx:.2f}mm "
                      f"significant={n_sig}/{n_tot} (LoD median={lod_med:.2f}mm)")
            # 2D developed map (chainage x angle, coloured by displacement) so
            # M3C2 has a flat result chart like the 2D section view.
            try:
                cp = np.asarray(res["corepoints"], dtype=np.float64)
                dm = np.asarray(res["distance_mm"], dtype=np.float64)
                ch, ang, labels2d = self._m3c2_developed_coords(cp)
                is_plan = labels2d is not None and labels2d[0].startswith("X")
                zones = ([] if is_plan
                         else self._m3c2_damage_zones(ch, ang, dm, res.get("significant")))
                self.m3c2_map_widget.set_map(ch, ang, dm, zones=zones,
                                             method=f"{res['method']} {compare_label}", axis_labels=labels2d,
                                             link_hotspots=getattr(self, "_trend_hotspots", []))
                self.right_tabs.setCurrentIndex(self._m3c2_tab_idx)
                if zones:
                    self._log(f"  Damage zones (>=10mm): {len(zones)} — worst: "
                              + "; ".join(f"{z['position']} @ Ch{z['chainage']:.1f}m "
                                          f"{z['peak_mm']:+.0f}mm [{z['severity']}]"
                                          for z in zones[:3]))
                else:
                    self._log("  No damage zones >=10mm detected.")
            except Exception as e:
                self._log(f"  M3C2 2D map skipped: {e}")
                self.right_tabs.setCurrentIndex(0)

        elif key == "6.5_forecast":
            self._forecast_data = result
            self.multi_epoch_widget.set_series(self._multi_epoch_series, result)
            self.right_tabs.setCurrentIndex(self._multi_epoch_tab_idx)
            cc = result.get("caution_crossing_epoch")
            cr = result.get("critical_crossing_epoch")
            r2 = result.get("r_squared")
            metric = result.get("metric", "")
            metric_name = "crown settlement" if metric == "crown_settlement_abs_mm" else metric
            self._log(f"Forecast [{metric_name}]: warning crossing={cc}, danger crossing={cr}, R²={r2:.4f}" if r2 else f"Forecast [{metric_name}] computed.")

        elif key == "6.6_export_ts":
            xlsx = result.get("xlsx") if isinstance(result, dict) else str(result)
            pdf = result.get("pdf") if isinstance(result, dict) else None
            self._log(f"Time-series Excel exported: {xlsx}")
            if pdf:
                self._log(f"Time-series PDF: {pdf}")
            self._offer_open_exported_file(xlsx, "Excel")

        elif key == "8.1_csv":
            path = str(result)
            self._log(f"CSV exported: {path}")
            self._offer_open_exported_file(path, "CSV")
        elif key == "8.4_web":
            url = result
            self._log(f"Web dashboard launched: {url}")
        elif key == "8.3_pdf":
            path = str(result)
            self._log(f"PDF report exported: {path}")
            self._offer_open_exported_file(path, "PDF")
        elif key == "8.5_workorder":
            path = str(result["path"])
            self._log(f"AI work order exported: {path}  "
                      f"(CRITICAL={result['n_critical']}, CAUTION={result['n_caution']}, "
                      f"items={result['n_items']})")
            self._offer_open_exported_file(path, "Work order PDF")
        elif key == "8.2_excel":
            path = str(result)
            self._log(f"Excel report exported: {path}")
            self._offer_open_exported_file(path, "Excel")
        elif key == "7.1_ifc":
            if isinstance(result, dict):
                path = str(result.get("path", ""))
                title = result.get("title", "IFC")
                schema = result.get("schema", "IFC")
                sections = result.get("sections", 0)
                components = result.get("components", 0)
                self._log(f"{title} exported: {path}  (schema={schema}, sections={sections}, components={components})")
            else:
                path = str(result)
                title = "IFC"
                self._log(f"IFC exported: {path}")
            self.ai_resp.setPlainText(path); self.right_tabs.setCurrentIndex(self._ai_tab_idx)
            self._offer_open_exported_file(path, title)

        elif key == "7.2_ai":
            self.ai_resp.setPlainText(str(result)); self.right_tabs.setCurrentIndex(self._ai_tab_idx)

    def _slot_1_1_import(self) -> None:
        self._hdr("LiDAR Data Acquisition", "Load one or more LAS/LAZ/PLY point-cloud scan stations.")
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, _tr("Load Scan Station(s)", self.current_language), "",
            "Point Clouds (*.las *.laz *.ply *.txt *.xyz *.pts *.csv *.asc);;All Files (*.*)")
        self._load_scan_files(files, single_key="1.1_import", batch_key="1.3_add_batch")

    def _load_scan_files(self, files, single_key: str = "1.3_add_scan", batch_key: str = "1.3_add_batch") -> None:
        files = sorted([f for f in (files or []) if f])
        if not files:
            return
        max_pts = self._ask_max_points(files[0])
        if max_pts is None:
            return
        if len(files) == 1:
            self._start_worker(single_key, lambda: self.base_mod.load_scan(files[0], max_points=max_pts))
            return
        self._log(f"Loading {len(files)} scan stations: {[os.path.basename(f) for f in files]}")
        from ..io_layer import BaseLayer
        def _load_batch():
            bl = BaseLayer()
            return [bl.load_scan(f, max_points=max_pts) for f in files]
        self._start_worker(batch_key, _load_batch)

    # ------------------------------------------------------------------ #
    # Drag & drop: drop a point-cloud file from Explorer to load it.
    # First file -> import (1.1); subsequent files -> add station (1.3).
    # ------------------------------------------------------------------ #
    _PC_EXTS = (".las", ".laz", ".ply", ".txt", ".xyz", ".pts", ".csv", ".asc")

    @classmethod
    def _is_pc_file(cls, fp: str) -> bool:
        return bool(fp) and fp.lower().endswith(cls._PC_EXTS)

    def dragEnterEvent(self, e) -> None:
        md = e.mimeData()
        if md.hasUrls() and any(self._is_pc_file(u.toLocalFile()) for u in md.urls()):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e) -> None:
        paths = [u.toLocalFile() for u in e.mimeData().urls() if self._is_pc_file(u.toLocalFile())]
        if not paths:
            e.ignore(); return
        e.acceptProposedAction()
        if self.worker_thread is not None:
            self._log(_tr("Busy: wait for the current task to finish before dropping a file.", self.current_language))
            return
        import pathlib
        name = pathlib.Path(paths[0]).name
        if len(self.context.scans) == 0:
            self._hdr("LiDAR Data Acquisition (drag & drop)",
                      "Loaded by drag & drop: " + name)
            self._load_scan_files(paths, single_key="1.1_import", batch_key="1.3_add_batch")
        else:
            self._hdr("Add Scan Station (drag & drop)",
                      "Added by drag & drop: " + name)
            self._load_scan_files(paths)

    def _slot_1_8_times(self) -> None:
        self._hdr("Load T0/Tn Times", "Load reference T0 and monitoring Tn at the start of the pipeline.")
        fp0, _ = QtWidgets.QFileDialog.getOpenFileName(self, _tr("Load reference times T0", self.current_language), "", "Point Clouds (*.las *.laz *.ply *.txt *.xyz *.pts *.csv *.asc);;All Files (*.*)")
        if not fp0: return
        fpn, _ = QtWidgets.QFileDialog.getOpenFileName(self, _tr("Load monitoring times Tn", self.current_language), "", "Point Clouds (*.las *.laz *.ply *.txt *.xyz *.pts *.csv *.asc);;All Files (*.*)")
        if not fpn: return
        self._start_worker("1.8_times", lambda: self.ts_mod.load_times(fp0, fpn))

    def _slot_1_9_epoch_folder(self) -> None:
        self._hdr("Load Epoch Folder T0→Tn",
                  "Load all point-cloud epochs named T0, T1, ... from one folder for Step 6 time-series.")
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, _tr("Load epoch folder T0→Tn", self.current_language), "")
        if not folder:
            return
        from ..io_layer import BaseLayer
        files, skipped = BaseLayer.discover_epoch_files(folder)
        if skipped:
            preview = ", ".join(skipped[:8])
            more = f" (+{len(skipped) - 8} more)" if len(skipped) > 8 else ""
            self._log(f"Epoch folder skipped non-epoch/duplicate files: {preview}{more}")
        if len(files) < 2:
            self._log("Epoch folder needs at least T0 and one monitoring epoch named T<number>.")
            return
        if not os.path.basename(files[0]).lower().startswith("t0."):
            self._log("Epoch folder must include T0 as the first reference epoch.")
            return
        max_pts = self._ask_max_points(files[0])
        if max_pts is None:
            return
        self._log(f"Loading epoch folder: {[os.path.basename(f) for f in files]}")
        def _load_epochs():
            bl = BaseLayer()
            scans = []
            for idx, fp in enumerate(files):
                bundle = bl.load_scan(fp, max_points=max_pts)
                bundle.metadata = dict(bundle.metadata or {})
                bundle.metadata["epoch_label"] = f"T{idx}"
                bundle.metadata["epoch_role"] = "T0 reference" if idx == 0 else "monitoring epoch"
                scans.append(bundle)
            return scans
        self._start_worker("1.9_epoch_folder", _load_epochs)

    def _slot_1_9_demo_timeseries(self) -> None:
        """One-click load of the built-in T0~T5 deformation demo folder."""
        self._hdr("Load Demo T0~T5",
                  "Load data/time_series_deformation (registered T0~T5) for Step 6 demo.")
        demo_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "time_series_deformation"))
        if not os.path.isdir(demo_dir):
            self._log(f"Demo folder not found: {demo_dir}")
            return
        from ..io_layer import BaseLayer
        files, skipped = BaseLayer.discover_epoch_files(demo_dir)
        if skipped:
            self._log(f"Demo folder skipped: {', '.join(skipped[:6])}")
        if len(files) < 2 or not os.path.basename(files[0]).lower().startswith("t0."):
            self._log("Demo folder must contain T0 and at least one Tn epoch.")
            return
        max_pts = 120_000
        self._log(f"Loading demo epochs: {[os.path.basename(f) for f in files]} (max_points={max_pts})")
        def _load_demo():
            bl = BaseLayer()
            scans = []
            for idx, fp in enumerate(files):
                bundle = bl.load_scan(fp, max_points=max_pts)
                bundle.metadata = dict(bundle.metadata or {})
                bundle.metadata["epoch_label"] = f"T{idx}"
                bundle.metadata["epoch_role"] = "T0 reference" if idx == 0 else "monitoring epoch"
                bundle.metadata["demo_dataset"] = "time_series_deformation"
                scans.append(bundle)
            return scans
        self._start_worker("1.9_epoch_folder", _load_demo)

    def _activate_times(self, t0: PointCloudBundle, tn: PointCloudBundle) -> None:
        t0.metadata = dict(t0.metadata or {})
        tn.metadata = dict(tn.metadata or {})
        t0.metadata["epoch_role"] = "T0 reference"
        tn.metadata["epoch_role"] = "Tn active"
        self.context.scans = [t0, tn]
        self.context.active_index = 1
        self.context.normalized_points = tn.points
        self.context.registered_points = None
        self.context.centerline = None
        self.context.centerline_smooth = None
        self.context.frenet_frames = []
        self.context.parameters.clear()
        self.context.heatmap_scalars = None
        self.context.time_series_plot = None
        self.context.m3c2_result = None
        if hasattr(self.context, "time_series_result"):
            self.context.time_series_result = None
        self.context.polar_map = None
        self.context.polar_angles = None
        self.context.polar_centers = None
        self.context.sections = []
        self.context.denoise_stats.clear()
        self.context.component_points.clear()
        self._render_bundle(tn, "Tn Active Times (T0 reference loaded)")
        self._update_meta(tn)
        self.pt_label.setText(f"Points: {len(tn.points):,}")
        self.sb_pts.setText(f"Points: {len(tn.points):,}")
        self._refresh_station_list()
        self._render_station_markers()

    def _activate_epoch_scans(self, scans: list[PointCloudBundle]) -> None:
        if len(scans) < 2:
            self._log("Epoch folder load returned fewer than 2 scans.")
            return
        self.context.scans = list(scans)
        self.context.active_index = len(scans) - 1
        active = scans[-1]
        self.context.normalized_points = active.points
        self.context.registered_points = None
        self.context.centerline = None
        self.context.centerline_smooth = None
        self.context.frenet_frames = []
        self.context.parameters.clear()
        self.context.heatmap_scalars = None
        self.context.time_series_plot = None
        self.context.m3c2_result = None
        if hasattr(self.context, "time_series_result"):
            self.context.time_series_result = None
        self.context.polar_map = None
        self.context.polar_angles = None
        self.context.polar_centers = None
        self.context.sections = []
        self.context.denoise_stats.clear()
        self.context.component_points.clear()
        labels = [str((scan.metadata or {}).get("epoch_label") or f"T{i}") for i, scan in enumerate(scans)]
        for i, scan in enumerate(scans):
            self._log(f"Epoch {labels[i]} loaded: {scan.path} ({len(scan.points):,} pts)")
        self._render_bundle(active, f"{labels[-1]} Active Epoch ({labels[0]} reference loaded)")
        self._update_meta(active)
        self.pt_label.setText(f"Points: {len(active.points):,}")
        self.sb_pts.setText(f"Points: {len(active.points):,}")
        self._refresh_station_list()
        self._render_station_markers()
        self._log(f"Loaded {len(scans)} epochs for Step 6 time-series: {labels}")

    def _ask_max_points(self, fp: str):
        """Check file size and ask user for subsampling if needed."""
        total = self.base_mod.get_point_count(fp)
        from tunnel_analysis.io_layer import MAX_POINTS_DEFAULT
        if total <= 0 or total <= MAX_POINTS_DEFAULT:
            return MAX_POINTS_DEFAULT
        import pathlib
        fname = pathlib.Path(fp).name
        lang = self.current_language
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(_tr("Large File - Loading Options", lang))
        dlg.setMinimumWidth(440)
        lay = QtWidgets.QVBoxLayout(dlg)
        lbl = QtWidgets.QLabel(
            _tr("Large file: ", lang) + fname + chr(10) +
            _tr("Total points: ", lang) + str(total) + chr(10) + chr(10) +
            _tr("Loading all points may cause memory issues.", lang) + chr(10) +
            _tr("Choose loading option:", lang))
        lbl.setStyleSheet("font-size:10pt;color:#0F172A;")
        lay.addWidget(lbl)
        grp = QtWidgets.QButtonGroup(dlg)
        opts = [
            (_tr("5M points (recommended, fast)", lang), 5_000_000),
            (_tr("10M points (more detail)", lang), 10_000_000),
            (_tr("20M points (needs 2GB+ RAM)", lang), 20_000_000),
            (_tr("ALL {n} points (may crash)", lang).format(n=f"{total:,}"), total),
        ]
        radios = []
        for label, val in opts:
            rb = QtWidgets.QRadioButton(label)
            grp.addButton(rb); lay.addWidget(rb)
            radios.append((rb, val))
        radios[0][0].setChecked(True)
        custom_lay = QtWidgets.QHBoxLayout()
        rb_custom = QtWidgets.QRadioButton(_tr("Custom:", lang))
        grp.addButton(rb_custom)
        spin = QtWidgets.QSpinBox()
        spin.setRange(100_000, total); spin.setValue(5_000_000)
        spin.setSingleStep(1_000_000); spin.setSuffix(" pts")
        custom_lay.addWidget(rb_custom); custom_lay.addWidget(spin, 1)
        lay.addLayout(custom_lay)
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return None
        for rb, val in radios:
            if rb.isChecked(): return val
        return spin.value()

    def _slot_1_5_rough(self) -> None:
        """Open rough alignment dialog for manual pre-alignment."""
        self._hdr("Rough Alignment", "Manually adjust position/rotation before ICP.")
        if len(self.context.scans) < 2:
            self._log(_tr("Load at least 2 scan stations first.", self.current_language)); return
        dlg = _RoughAlignDialog(self.context, self.reg_mod, self, self.plotter)
        dlg.exec()
        if dlg.result() == QtWidgets.QDialog.Accepted:
            self.context.normalized_points = dlg.aligned_pts
            self._render_pts(dlg.aligned_pts, "Rough Alignment Applied", "#F59E0B")
            self._log(f"Rough alignment applied: offset={dlg.offset} rot={dlg.rotation}")

    def _slot_1_6_chain(self) -> None:
        self._hdr("Chain Register & Merge",
                  "Sequential chain registration S1->S2->S3 (reduces drift).")
        if len(self.context.scans) < 2:
            self._log(_tr("Load at least 2 scan stations first.", self.current_language)); return
        self._log(f"Chain registering {len(self.context.scans)} stations...")
        self._start_worker("1.6_chain",
            lambda: self.reg_mod.register_and_merge_chain(self.context))

    def _slot_1_7_reg_error(self) -> None:
        self._hdr("Registration Error Heatmap",
                  "Visualize registration error between merged cloud and reference.")
        if self.context.registered_points is None or len(self.context.scans) < 2:
            self._log(_tr("Run registration first.", self.current_language)); return
        def _task():
            import numpy as _np
            from scipy.spatial import cKDTree as _kd
            pts = self.context.registered_points
            ref = self.context.scans[0].points
            tree = _kd(ref)
            d, _ = tree.query(pts, k=1, workers=-1)
            dist_mm = d * 1e3
            GREEN  = _np.array([0.18, 0.80, 0.44], dtype=_np.float32)
            YELLOW = _np.array([0.95, 0.77, 0.06], dtype=_np.float32)
            RED    = _np.array([0.86, 0.15, 0.15], dtype=_np.float32)
            colors = _np.empty((len(pts), 3), dtype=_np.float32)
            t1 = _np.clip(dist_mm / 2.0, 0, 1).astype(_np.float32)
            t2 = _np.clip((dist_mm - 2.0) / 3.0, 0, 1).astype(_np.float32)
            for ch in range(3):
                colors[:, ch] = GREEN[ch]*(1-t1) + YELLOW[ch]*t1*(1-t2) + RED[ch]*t1*t2
            return pts, dist_mm, colors
        self._start_worker("1.7_reg_error", _task)

    def _slot_1_3_add_scan(self) -> None:
        self._hdr("Add Scan Station", "Load additional scan station(s) to merge with existing scans.")
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, _tr("Load Scan Station", self.current_language), "",
            "Point Clouds (*.las *.laz *.ply *.txt *.xyz *.pts *.csv *.asc);;All Files (*.*)")
        self._load_scan_files(files)

    def _slot_1_4_merge(self) -> None:
        self._hdr("Register & Merge Stations",
                  "Register all scan stations to reference and merge into one point cloud.")
        if len(self.context.scans) < 2:
            self._log(_tr("Load at least 2 scan stations first (1.1 + 1.3).", self.current_language)); return
        self._log(f"Registering {len(self.context.scans)} stations...")
        self._start_worker("1.4_merge", lambda: self.reg_mod.register_and_merge(self.context))

    def _slot_1_2_viewport(self) -> None:
        self._hdr("Initialize 3D Viewport", "Prepare the PyVista inspection viewport with a light technical theme.")
        if self.plotter:
            self.plotter.clear(); self.plotter.set_background("#FFFFFF"); self.plotter.add_axes(color="#111827")
            self.plotter.show_bounds(color="#94A3B8", grid="front", location="outer", font_size=8); self.plotter.render()
        self._log(_tr("3D viewport initialized and refreshed.", self.current_language))

    def _slot_2_0_range_crop(self) -> None:
        self._hdr("Range Crop", "Drop points farther than the range limit from the scan origin (MATLAB-style pre-filter).")
        self._start_worker("2.0_range_crop",
            lambda: self.pre_mod.range_crop(self.context, max_range_m=20.0, mode="sensor"))

    def _slot_2_1_voxel(self) -> None:
        self._hdr("Voxel Downsampling", "Homogenize point density using a voxel grid while preserving tunnel geometry.")
        self._start_worker("2.1_voxel", lambda: self.pre_mod.voxel_downsample(self.context))

    def _slot_2_2_sor(self) -> None:
        self._hdr("Statistical Outlier Removal", "Remove environmental noise using distance-statistics filtering.")
        self._start_worker("2.2_sor", lambda: self.pre_mod.statistical_outlier_removal_run(self.context))

    def _slot_2_5_auto_denoise(self) -> None:
        self._hdr("Auto Denoise (Smart, No Manual)",
                  "Automatically remove cables, lights, signal devices, vehicles and people "
                  "using morphological classification + distance statistics. No manual picking.")
        self._start_worker("2.5_auto_denoise", lambda: self.pre_mod.auto_denoise(self.context))

    def _slot_2_6_density_lining(self) -> None:
        self._hdr("Extract Lining (Density-Variation)",
                  "Isolate the lining shell by local radial density drop-off "
                  "(SAM4Tun Algorithm 2). Removes interior bore clutter automatically.")
        self._start_worker("2.6_density_lining",
            lambda: self.pre_mod.extract_lining_density_variation(self.context))

    def _slot_2_4_semantic(self) -> None:
        self._hdr("Semantic Noise Removal (PDF 3.2)",
                  "Remove cables, lights and people using geometric feature classification.")
        self._start_worker("2.4_semantic",
            lambda: self.pre_mod.semantic_noise_removal(self.context))

    def _slot_2_3_lining(self) -> None:
        self._hdr("Tunnel Lining Extraction", "Isolate the structural tunnel lining surface for downstream analysis.")
        self._start_worker("2.3_lining", lambda: self.pre_mod.extract_tunnel_lining(self.context))

    def _slot_2_3b_lining_label(self) -> None:
        self._hdr("Lining Extraction by Label", "Keep structural lining classes from the per-point semantic label (FY387/STSD); interior objects are dropped. Auto-detects lining classes by shell radius when none are specified.")
        self._start_worker("2.3b_lining_label", lambda: self.pre_mod.extract_lining_by_label(self.context))

    def _slot_3_0_register_times(self) -> None:
        self._hdr("Auto-align T0/Tn times",
                  "Đưa lần đo Tn về cùng hệ tọa độ với T0. Tự dùng điểm mốc cố định "
                  "(không triệt tiêu biến dạng) nếu phát hiện ≥3 mốc, nếu không thì trimmed ICP.")
        if len(self.context.scans) < 2:
            self._log("Cần ≥2 lần đo (T0 + Tn) để căn chỉnh. Dùng '1.8 Load T0 and Tn times' trước.")
            return
        self._start_worker("times_register", lambda: self.reg_mod.register_times(self.context))

    def _slot_3_1_anchor(self) -> None:
        self._hdr("Target Anchor Translation", "Apply the initial target-based translation alignment.")
        self._start_worker("3.1_anchor", lambda: self.reg_mod.anchor_translation(self.context))

    def _slot_3_2_icp(self) -> None:
        self._hdr("Surface ICP Registration", "Refine station alignment with surface-based ICP and report RMSE.")
        self._start_worker("3.2_icp", lambda: self.reg_mod.run_surface_icp(self.context))

    def _slot_3_3_rmse(self) -> None:
        self._hdr("Registration RMSE Check", "Evaluate registration quality using nearest-surface residuals.")
        self._start_worker("3.3_rmse", lambda: self.reg_mod.calculate_rmse(self.context))

    def _init_rag(self) -> None:
        msg = self.rag_mod.initialize()
        # Use QTimer to log after UI is fully built
        try:
            QtCore.QTimer.singleShot(500, lambda: self._log(f"[RAG] {msg}"))
        except Exception:
            pass

    def _slot_auto_pipeline(self) -> None:
        """Run full analysis pipeline in sequence: voxel -> SOR -> lining -> centerline -> params -> sections."""
        if self.context.active_scan is None:
            QtWidgets.QMessageBox.warning(self, _tr("Auto Pipeline", self.current_language),
                _tr("Please load a point cloud first (Step 1.1).", self.current_language))
            return
        self._hdr("Auto Pipeline", "Running full analysis pipeline automatically...")
        self._log("=" * 50)
        self._log(_tr("AUTO PIPELINE STARTED", self.current_language))
        self._log("=" * 50)
        if hasattr(self, "_auto_btn"):
            self._auto_btn.setEnabled(False)
            self._auto_btn.setText(_tr("Running pipeline...", self.current_language))
        self._auto_running = True
        self._auto_step = 0
        # Snapshot widget-derived values on the GUI thread. Every step below runs
        # in a worker thread (PipelineWorker), where reading QWidgets is unsafe.
        section_count = self._resolve_section_count()
        vl_w, vl_h, vl_r = self._sp_vl_w.value(), self._sp_vl_h.value(), self._sp_vl_r.value()
        self._auto_steps = [
            ("2.1_voxel",       lambda: self.pre_mod.voxel_downsample(self.context),
             "Step 1/6: Voxel downsampling..."),
            ("2.5_auto_denoise", lambda: self.pre_mod.auto_denoise(self.context),
             "Step 2/6: Smart noise removal (cables, lights, people, wall cables)..."),
            ("times_register",  lambda: self._auto_register_times(),
             "Step 2b: Align T0/Tn times (auto target/ICP)..."),
            ("4.1_centerline",  lambda: self.geo_mod.extract_centerline(self.context, section_count=section_count),
             "Step 3/6: Centerline extraction..."),
            ("4.3b_bspline",    lambda: self.geo_mod.extract_centerline_bspline(self.context, section_count=section_count),
             "Step 4/6: B-spline centerline..."),
            ("5.7_sections",    lambda: self._auto_sections_task(vl_w, vl_h, vl_r),
             "Step 5/6: 2D section analysis (auto profile + clearance)..."),
            ("auto_params",     lambda: self._auto_extract_params(),
             "Step 6/6: Parameter extraction..."),
        ]
        self._run_next_auto_step()

    def _auto_sections_task(self, vl_w, vl_h, vl_r):
        """AUTO PIPELINE 2D-section step: pick the profile and clearance gauge
        automatically (pure NumPy, safe in the worker thread), then compute
        all sections. The (vl_w, vl_h, vl_r) fallback gauge is captured on the
        GUI thread by the caller; never read the spinboxes here.
        """
        self.context.tunnel_profile = self.par_mod.detect_profile(self.context)
        g = self._compute_auto_gauge()
        if g:
            w, h, r = g
        else:
            w, h, r = vl_w, vl_h, vl_r
        return self.par_mod.compute_all_sections(self.context, vl_box_w=w, vl_box_h=h, vl_cir_r=r)

    def _auto_register_times(self):
        """AUTO PIPELINE times-alignment step.

        When 2+ times are loaded (T0 + Tn from different scanner setups), align
        Tn onto T0 so deformation is measured in a common frame. Auto-uses fixed
        markers when present (no deformation absorption), else trimmed ICP.
        Returns None (no-op) for a single scan so single-times runs are
        unaffected.
        """
        if len(self.context.scans) < 2:
            return None
        return self.reg_mod.register_times(self.context)

    def _auto_extract_params(self) -> Dict:
        par = self.par_mod
        result = {}
        result.update(par.calc_arch_settlement(self.context))
        result.update(par.calc_horizontal_convergence(self.context))
        result.update(par.calc_ovality(self.context))
        result.update(par.calc_eccentricity(self.context))
        return result

    def _run_next_auto_step(self) -> None:
        if self._auto_step >= len(self._auto_steps):
            self._on_auto_pipeline_done()
            return
        key, task, msg = self._auto_steps[self._auto_step]
        total = len(self._auto_steps)
        pct = int(self._auto_step / total * 100)
        self.sb_prog.setValue(pct)
        step_label = f"[{self._auto_step+1}/{total}] " + _tr(msg, self.current_language)
        self._log(step_label)
        self.sb_msg.setText(step_label)
        if hasattr(self, "_auto_btn"):
            self._auto_btn.setText(_tr("Running... {pct}%  ({cur}/{total})", self.current_language).format(pct=pct, cur=self._auto_step+1, total=total))
        self._start_worker(key, task)

    def _on_auto_pipeline_done(self) -> None:
        self._auto_running = False
        if hasattr(self, "_auto_btn"):
            self._auto_btn.setEnabled(True)
            self._auto_btn.setText(_tr("AUTO PIPELINE  (1-click full analysis)", self.current_language))
        self._log("=" * 50)
        self._log(_tr("AUTO PIPELINE COMPLETE", self.current_language))
        p = self.context.parameters
        if p:
            self._log(_tr("--- Results Summary ---", self.current_language))
            for k, v in p.items():
                label, text, status = format_parameter(k, v)
                tag = f"  [{status}]" if status and status != "OK" else ""
                self._log(f"  {label}: {text}{tag}")
        n_viol = sum(1 for s in self.context.sections if s.clearance_violation)
        if n_viol:
            self._log(f"  WARNING: {n_viol} clearance violation(s) detected!")
        self._log("=" * 50)
        self.right_tabs.setCurrentIndex(self._section_tab_idx)
        _lang = self.current_language
        QtWidgets.QMessageBox.information(self, _tr("Auto Pipeline Complete", _lang),
            _tr("Pipeline finished successfully!", _lang) + "\n\n" +
            _tr("Sections analyzed: {n}", _lang).format(n=len(self.context.sections)) + "\n" +
            _tr("Clearance violations: {n}", _lang).format(n=n_viol) + "\n\n" +
            _tr("Check the 2D Cross-Section tab for results.", _lang))

    def _slot_target_detect(self) -> None:
        """Auto-detect targets with configurable parameters."""
        if self.context.active_scan is None:
            self._log(_tr("Load a scan first.", self.current_language)); return
        dlg = _TargetDetectDialog(self.context.active_scan, self)
        if dlg.exec() != QtWidgets.QDialog.Accepted: return
        params = dlg.get_params()
        scan_idx = self.context.active_index
        self._log(f"Detecting targets in {len(self.context.active_scan.points):,} pts (max 300K for speed)...")
        def _task():
            import numpy as _np
            from tunnel_analysis.models import PointCloudBundle as _PCB
            # Subsample to max 300K pts for fast detection
            scan = self.context.active_scan
            pts = scan.points
            intensity = scan.intensity
            MAX_DET = 100_000
            if len(pts) > MAX_DET:
                step = max(1, len(pts) // MAX_DET)
                pts_d = pts[::step]
                int_d = intensity[::step] if intensity is not None else None
            else:
                pts_d = pts; int_d = intensity
            b_det = _PCB(points=pts_d, intensity=int_d, path=scan.path)
            return self.tgt_mod.detect_all(
                b_det, scan_idx=scan_idx,
                detect_sphere=params["detect_sphere"],
                detect_flat=params["detect_flat"],
                detect_intensity=params["detect_intensity"],
                sphere_radius_range=params["sphere_radius_range"],
                intensity_percentile=params["intensity_percentile"],
                min_cluster_pts=params["min_cluster_pts"],
                cell_size_range=params.get("cell_size_range", (0.05, 0.30)),
                min_contrast_ratio=params.get("min_contrast_ratio", 2.0))
        self._start_worker("target_detect", _task)

    def _slot_target_manual(self) -> None:
        """Toggle manual target picking mode."""
        if self.plotter is None:
            self._log(_tr("Load a point cloud first.", self.current_language)); return
        if self._manual_pick_mode:
            self._stop_manual_pick()
        else:
            self._start_manual_pick()

    def _start_manual_pick(self) -> None:
        """Start manual target picking mode."""
        self._manual_pick_mode = True
        self._hdr("Manual Target Picking",
                  "Click on target location in 3D viewport. Tool will auto-refine position.")
        # Update button appearance
        for i in range(self.right_tabs.count()):
            if self.right_tabs.tabText(i) == "Targets":
                self.right_tabs.setCurrentIndex(i); break
        # Show instruction overlay
        if self.plotter:
            self.plotter.add_text(
                "PICK MODE: Click on target location" + chr(10) + "Press [+ Manual] again to exit",
                position="lower_left", font_size=10,
                color="#F59E0B", name="pick_instruction")
            self.plotter.render()
        try:
            self.plotter.enable_point_picking(
                callback=self._on_manual_target_pick,
                show_message=False, color="#F59E0B",
                point_size=14, use_picker=True,
                pickable_window=False)
        except Exception as e:
            self._log(f"Pick mode error: {e}")
        self.sb_msg.setText(
            _tr("PICK MODE active — Click on target in 3D viewport | Click [+ Manual] again to exit", self.current_language))
        self._log(_tr("Manual pick mode started. Click on target locations in 3D viewport.", self.current_language))

    def _stop_manual_pick(self) -> None:
        """Stop manual target picking mode."""
        self._manual_pick_mode = False
        if self.plotter:
            try:
                self.plotter.remove_actor("pick_instruction")
                self.plotter.disable_picking()
            except Exception:
                pass
            self.plotter.render()
        self.sb_msg.setText(_tr("Pick mode stopped.", self.current_language))
        self._log(f"Manual pick mode stopped. Total targets: {len(self._targets)}")

    def _on_manual_target_pick(self, point) -> None:
        """Handle manual target pick with auto-refinement."""
        if point is None: return
        pts = self.context.working_points
        if pts is None: return
        pick_pt = np.asarray(point, dtype=np.float64)
        n_manual = sum(1 for x in self._targets if x.type == "manual") + 1
        name = "M" + str(n_manual).zfill(2)

        # Auto-refine: fit local plane and find centroid
        refined_center, normal, residual_mm = self._refine_target_position(pick_pt, pts)

        t = Target(
            type="manual",
            name=name,
            center=refined_center,
            normal=normal,
            confidence=1.0,
            n_points=0,
            residual_mm=residual_mm,
            scan_idx=self.context.active_index)
        self._targets.append(t)
        self._refresh_target_table()

        # Show marker immediately
        if self.plotter:
            try:
                self.plotter.add_point_labels(
                    [refined_center], [name],
                    font_size=12, text_color="#F59E0B",
                    bold=True, show_points=True,
                    point_color="#F59E0B", point_size=18,
                    name="tgt_" + t.id, reset_camera=False)
                # Flash effect - temporary large sphere
                import pyvista as _pv
                sp = _pv.Sphere(radius=0.05, center=refined_center)
                self.plotter.add_mesh(sp, color="#F59E0B", opacity=0.6,
                    name="tgt_flash_" + t.id, reset_camera=False)
                self.plotter.render()
            except Exception:
                pass

        self._log(f"Target {name} placed at {np.round(refined_center,3).tolist()} "
                  f"(residual={residual_mm:.1f}mm)")

    def _refine_target_position(
        self, pick_pt: np.ndarray, pts: np.ndarray,
        search_r: float = 0.25
    ) -> Tuple[np.ndarray, Optional[np.ndarray], float]:
        """Refine picked point to local plane centroid."""
        if cKDTree is None:
            return pick_pt, None, 0.0
        try:
            from scipy.spatial import cKDTree as _kd
            tree = _kd(pts)
            local_idx = tree.query_ball_point(pick_pt, search_r)
            if len(local_idx) < 10:
                return pick_pt, None, 0.0
            lp = pts[local_idx]
            # Fit plane
            result = self.tgt_mod._fit_plane(lp, tol=0.015)
            if result is None:
                return lp.mean(axis=0), None, 0.0
            normal, centroid, thickness, inliers = result
            return centroid, normal, thickness * 1e3
        except Exception:
            return pick_pt, None, 0.0

    def _slot_target_match(self) -> None:
        """Auto-match targets between consecutive scan stations (handles N stations)."""
        n_scans = len(self.context.scans)
        if n_scans < 2:
            self._log(_tr("Need at least 2 scan stations.", self.current_language)); return
        if not self._targets:
            self._log("No targets detected. Run 'Detect All Stations' first."); return
        total_matches = 0
        for i in range(n_scans - 1):
            src_t = [t for t in self._targets if t.scan_idx == i]
            tgt_t = [t for t in self._targets if t.scan_idx == i + 1]
            if not src_t or not tgt_t:
                self._log(f"  No targets in S{i+1} or S{i+2}. Run 'Detect All Stations' first.")
                continue
            matches = self.tgt_mod.match_targets(src_t, tgt_t, max_dist=5.0)
            total_matches += len(matches)
            for st, tt, d in matches:
                self._log(f"  S{i+1}.{st.name} <-> S{i+2}.{tt.name}  dist={d:.3f}m")
        self._refresh_target_table()
        self._log(f"Auto Match: {total_matches} pairs across {n_scans-1} station pair(s).")

    def _slot_target_register(self) -> None:
        """Register scans using matched targets."""
        src_t = [t for t in self._targets if t.scan_idx == 0 and t.matched_id]
        tgt_t = [t for t in self._targets if t.scan_idx == 1 and t.matched_id]
        if len(src_t) < 3:
            self._log(_tr("Need >= 3 matched target pairs. Run Auto Match first.", self.current_language)); return
        def _task():
            T, rmse, residuals = self.tgt_mod.register_by_targets(src_t, tgt_t)
            pts = self.context.working_points
            if pts is not None:
                reg_pts = self.tgt_mod.apply_transform(pts, T)
            else:
                reg_pts = None
            return T, rmse, residuals, reg_pts
        self._start_worker("target_register", _task)

    def _slot_target_detect_all(self) -> None:
        """Detect targets in ALL loaded scan stations at once."""
        if not self.context.scans:
            self._log("Load scan stations first."); return
        n = len(self.context.scans)
        self._log(f"Detecting targets in {n} scan station(s) ...")
        self._targets.clear()
        self._refresh_target_table()
        def _task():
            import numpy as _np
            from tunnel_analysis.models import PointCloudBundle as _PCB
            all_targets = []
            MAX_DET = 100_000
            for i, scan in enumerate(self.context.scans):
                pts = scan.points
                intensity = scan.intensity
                if len(pts) > MAX_DET:
                    step = max(1, len(pts) // MAX_DET)
                    pts_d = pts[::step]
                    int_d = intensity[::step] if intensity is not None else None
                else:
                    pts_d = pts; int_d = intensity
                b_det = _PCB(points=pts_d, intensity=int_d, path=scan.path)
                found = self.tgt_mod.detect_all(
                    b_det, scan_idx=i,
                    detect_sphere=True, detect_flat=True, detect_intensity=True)
                all_targets.extend(found)
            return all_targets
        self._start_worker("target_detect_all", _task)

    def _slot_target_merge_chain(self) -> None:
        """Chain-register all scan stations using matched targets + ICP refinement."""
        n_scans = len(self.context.scans)
        if n_scans < 2:
            self._log("Need at least 2 scan stations."); return
        n_matched = sum(1 for t in self._targets if t.matched_id)
        if n_matched < 6:
            self._log(
                "Not enough matched targets (need >= 6). "
                "Run 'Detect All Stations' → 'Auto Match' first."); return
        self._hdr("Target-based Chain Registration",
                  "SVD from targets per station pair, refined with surface ICP.")
        targets_snap = list(self._targets)
        scans_snap   = list(self.context.scans)
        reg_mod      = self.reg_mod
        tgt_mod      = self.tgt_mod

        def _task():
            import numpy as _np

            # acc_transforms[i] = 4×4 that maps station i → station 0 frame.
            # Station 0 is already the reference (identity).
            acc_transforms = [_np.eye(4, dtype=_np.float64)]
            merged_clouds  = [validate_xyz(scans_snap[0].points)]
            rmse_list      = [0.0]

            for i in range(len(scans_snap) - 1):
                src_t_all = [t for t in targets_snap if t.scan_idx == i]
                nxt_t_all = [t for t in targets_snap if t.scan_idx == i + 1]

                src_pts   = validate_xyz(scans_snap[i + 1].points)
                # Use the FULL growing merged cloud as ICP reference so that
                # the later station benefits from all earlier aligned scans.
                ref_cloud = _np.vstack(merged_clouds)

                # ── Fresh centroid-aligned matching for this pair ──────────
                for t in src_t_all: t.matched_id = ""
                for t in nxt_t_all: t.matched_id = ""
                if src_t_all and nxt_t_all:
                    tgt_mod.match_targets(src_t_all, nxt_t_all,
                                          max_dist=2.0, centroid_align=True)

                nxt_by_id = {t.id: t for t in nxt_t_all}
                m_src = [t for t in src_t_all if t.matched_id in nxt_by_id]
                m_tgt = [nxt_by_id[t.matched_id] for t in m_src]

                if len(m_src) >= 3:
                    # sc = station i targets (in their original local frame)
                    # tc = station i+1 targets (in their original local frame)
                    # _horn_svd(tc, sc) → T_rel that maps station i+1 → station i
                    sc = _np.array([t.center for t in m_src], dtype=_np.float64)
                    tc = _np.array([t.center for t in m_tgt], dtype=_np.float64)
                    T_rel, _ = tgt_mod._horn_svd(tc, sc)

                    # Accumulated transform: station i+1 → station 0.
                    # acc_transforms[i] maps station i → station 0.
                    # T_rel maps station i+1 → station i.
                    # ∴  acc_transforms[i] @ T_rel  maps station i+1 → station 0.
                    T_to_global = acc_transforms[i] @ T_rel
                    ones = _np.ones((len(src_pts), 1))
                    src_coarse = (T_to_global @ _np.hstack([src_pts, ones]).T).T[:, :3]
                else:
                    # Fall back to intensity anchor + GROR coarse align
                    src_coarse  = reg_mod._coarse_align(
                        src_pts, ref_cloud,
                        src_intensity=scans_snap[i + 1].intensity,
                        tgt_intensity=scans_snap[i].intensity)
                    T_to_global = acc_transforms[i]

                # ── ICP fine refinement against growing merged cloud ───────
                try:
                    src_reg, rmse = reg_mod._icp(src_coarse, ref_cloud)
                except Exception:
                    src_reg = src_coarse
                    try:
                        from scipy.spatial import cKDTree as _kd
                        step = max(1, len(src_reg) // 100_000)
                        d, _ = _kd(ref_cloud).query(src_reg[::step], k=1, workers=-1)
                        rmse = float(_np.sqrt(_np.mean(d ** 2))) * 1000.0
                    except Exception:
                        rmse = 0.0

                acc_transforms.append(T_to_global)
                merged_clouds.append(src_reg)
                rmse_list.append(rmse)

            merged = _np.vstack(merged_clouds)
            return validate_xyz(merged), rmse_list

        self._start_worker("target_merge_chain", _task)

    def _refresh_target_table(self) -> None:
        """Update target table widget."""
        if not hasattr(self, "_target_table"): return
        self._target_table.setRowCount(0)
        type_colors = {
            "sphere": "#1D4ED8", "flat": "#047857",
            "intensity": "#D97706", "manual": "#DC2626"}
        for t in self._targets:
            row = self._target_table.rowCount()
            self._target_table.insertRow(row)
            c = t.center if t.center is not None else np.zeros(3)
            matched = " *" if t.matched_id else ""
            vals = [
                t.name + matched, t.type,
                "S" + str(t.scan_idx + 1),
                f"{c[0]:.3f}", f"{c[1]:.3f}", f"{c[2]:.3f}",
                f"{t.confidence:.2f}"]
            for col, val in enumerate(vals):
                item = QtWidgets.QTableWidgetItem(val)
                item.setData(QtCore.Qt.UserRole, t.id)
                color = type_colors.get(t.type, "#111827")
                if col <= 1:
                    item.setForeground(QtGui.QColor(color))
                    item.setFont(QtGui.QFont("Segoe UI", 9, QtGui.QFont.Bold))
                self._target_table.setItem(row, col, item)
        n = len(self._targets)
        n_matched = sum(1 for t in self._targets if t.matched_id)
        if hasattr(self, "_tgt_status"):
            self._tgt_status.setText(
                f"{n} targets  |  {n_matched} matched  |  "
                f"sphere:{sum(1 for t in self._targets if t.type=='sphere')}  "
                f"flat:{sum(1 for t in self._targets if t.type=='flat')}  "
                f"intensity:{sum(1 for t in self._targets if t.type=='intensity')}  "
                f"manual:{sum(1 for t in self._targets if t.type=='manual')}")

    def _render_target_markers(self) -> None:
        """Render target markers on 3D viewport."""
        if self.plotter is None: return
        try: self.plotter.remove_actor("target_markers")
        except Exception: pass
        if not self._targets: return
        type_colors = {
            "sphere": "#1D4ED8", "flat": "#047857",
            "intensity": "#D97706", "manual": "#DC2626"}
        for t in self._targets:
            if t.center is None: continue
            color = type_colors.get(t.type, "#888888")
            label = t.name + (" *" if t.matched_id else "")
            try:
                self.plotter.add_point_labels(
                    [t.center], [label],
                    font_size=10, text_color=color,
                    bold=True, show_points=True,
                    point_color=color, point_size=16,
                    name="tgt_" + t.id, reset_camera=False)
            except Exception:
                pass
        self.plotter.render()

    def _on_target_selected(self, row: int, col: int) -> None:
        """Focus camera on selected target."""
        item = self._target_table.item(row, 0)
        if item is None: return
        tid = item.data(QtCore.Qt.UserRole)
        t = next((x for x in self._targets if x.id == tid), None)
        if t is None or t.center is None: return
        if self.plotter:
            self.plotter.camera.focal_point = t.center.tolist()
            self.plotter.render()

    def _target_context_menu(self, pos) -> None:
        """Right-click menu for target table."""
        row = self._target_table.rowAt(pos.y())
        if row < 0: return
        item = self._target_table.item(row, 0)
        if item is None: return
        tid = item.data(QtCore.Qt.UserRole)
        t = next((x for x in self._targets if x.id == tid), None)
        if t is None: return
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#FFFFFF;border:1px solid #E2E8F0;border-radius:4px;padding:4px;}"
            "QMenu::item{padding:6px 20px;color:#111827;font-size:9pt;}"
            "QMenu::item:selected{background:#DBEAFE;color:#1D4ED8;}")
        act_focus = menu.addAction("Focus Camera")
        act_focus.triggered.connect(lambda: self._on_target_selected(row, 0))
        act_rename = menu.addAction("Rename...")
        act_rename.triggered.connect(lambda: self._rename_target(t))
        act_unmatch = menu.addAction("Unmatch")
        act_unmatch.triggered.connect(lambda: self._unmatch_target(t))
        menu.addSeparator()
        act_del = menu.addAction("Delete")
        act_del.triggered.connect(lambda: self._delete_target(t))
        menu.exec(self._target_table.viewport().mapToGlobal(pos))

    def _rename_target(self, t: Target) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename Target", "Name:", text=t.name)
        if ok and name.strip():
            t.name = name.strip()
            self._refresh_target_table()

    def _unmatch_target(self, t: Target) -> None:
        paired = next((x for x in self._targets if x.id == t.matched_id), None)
        if paired: paired.matched_id = ""
        t.matched_id = ""
        self._refresh_target_table()
        self._log(f"Target {t.name} unmatched.")

    def _delete_target(self, t: Target) -> None:
        self._targets = [x for x in self._targets if x.id != t.id]
        try: self.plotter.remove_actor("tgt_" + t.id)
        except Exception: pass
        self._refresh_target_table()
        self._log(f"Target {t.name} deleted.")

    def _slot_copy_clipboard(self) -> None:
        """Copy current results to clipboard as text."""
        lines = []
        p = self.context.parameters
        if p:
            lines.append("=== Tunnel Analysis Results ===")
            for k, v in p.items():
                label, text, status = format_parameter(k, v)
                tag = f"  [{status}]" if status and status != "OK" else ""
                lines.append(f"  {label}: {text}{tag}")
        if self.context.sections:
            lines.append(f"Sections analyzed: {len(self.context.sections)}")
            n_viol = sum(1 for s in self.context.sections if s.clearance_violation)
            lines.append(f"Clearance violations: {n_viol}")
            lines.append("")
            lines.append("Chainage(m) | H1(m) | W1(m) | Ovality(%) | Ecc(mm)")
            lines.append("-" * 55)
            for s in self.context.sections:
                h1 = f"{s.H1:.3f}" if np.isfinite(s.H1) else "-"
                w1 = f"{s.W1:.3f}" if np.isfinite(s.W1) else "-"
                ov = f"{s.ovality:.2f}" if np.isfinite(s.ovality) else "-"
                ec = f"{s.eccentricity:.1f}" if np.isfinite(s.eccentricity) else "-"
                lines.append(f"{s.chainage:.2f}       | {h1}   | {w1}   | {ov}       | {ec}")
        if not lines:
            self._log(_tr("No results to copy. Run analysis first.", self.current_language)); return
        text = chr(10).join(lines)
        QtWidgets.QApplication.clipboard().setText(text)
        self._log(f"Results copied to clipboard ({len(lines)} lines).")
        QtWidgets.QMessageBox.information(self, _tr("Copied", self.current_language),
            _tr("Results copied to clipboard ({n} lines).", self.current_language).format(n=len(lines)))

    def _slot_reset_pipeline(self) -> None:
        """Reset pipeline — clear all results, keep raw scans."""
        _lang = self.current_language
        reply = QtWidgets.QMessageBox.question(self, _tr("Reset Pipeline", _lang),
            _tr("Clear all analysis results?", _lang) + chr(10) +
            _tr("(Raw scan data will be kept)", _lang),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply != QtWidgets.QMessageBox.Yes: return
        self.context.normalized_points  = None
        self.context.registered_points  = None
        self.context.centerline         = None
        self.context.centerline_smooth  = None
        self.context.frenet_frames      = []
        self.context.parameters         = {}
        self.context.heatmap_scalars    = None
        self.context.sections           = []
        self.context.polar_map          = None
        self.context.polar_angles       = None
        self.context.polar_centers      = None
        self._targets                   = []
        self._noise_pts                 = None
        self._kept_pts                  = None
        if hasattr(self, "_noise_panel") and self._noise_panel:
            self._noise_panel.deleteLater()
            self._noise_panel = None
        if self.plotter:
            try:
                self.plotter.clear()
                self.plotter.set_background("#FFFFFF")
                self.plotter.render()
            except Exception: pass
        self.results_text.clear()
        self.dashboard_widget.clear()
        # Remove 3D warning markers
        if self.plotter:
            for _nm in ("warn_markers_crit", "warn_markers_caut"):
                try: self.plotter.remove_actor(_nm)
                except Exception: pass
        self.pt_label.setText("Points: --")
        self.sb_pts.setText("Points: --")
        self.sb_msg.setText(_tr("Pipeline reset. Raw scans preserved.", self.current_language))
        self.sb_prog.setValue(0)
        self._refresh_target_table()
        self._log(_tr("Pipeline reset complete. Raw scans preserved.", self.current_language))

    def _slot_4_3b_bspline(self) -> None:
        self._hdr("B-Spline C2 Centerline (PDF 3.4)", "Sliding-window curvature detection + B-spline C2 fit.")
        self._start_worker("4.3b_bspline", lambda: self.geo_mod.extract_centerline_bspline(self.context, section_count=self._resolve_section_count()))

    def _slot_4_5b_intensity_seams(self) -> None:
        self._hdr("Intensity Ring Seam Detection (PDF 3.3)", "Detect ring seams from LiDAR intensity derivative.")
        if self.context.active_scan is None or self.context.active_scan.intensity is None:
            self._log(_tr("Intensity data required. Load a scan with intensity channel first.", self.current_language)); return
        self._start_worker("4.5b_intensity_seams", lambda: self.seg_mod.detect_ring_seams_by_intensity(self.context))

    def _slot_5_3b_hausdorff(self) -> None:
        self._hdr("Hausdorff Heatmap T0→Tn (PDF 3.5)", "Surface distance heatmap between reference and current scan.")
        if len(self.context.scans) < 2:
            self._log(_tr("Load at least 2 scans (T0 and Tn) first.", self.current_language)); return
        ref = self.context.scans[0].points
        self._start_worker("5.3b_hausdorff", lambda: self.par_mod.generate_hausdorff_heatmap(self.context, ref))

    def _slot_4_1_centerline(self) -> None:
        self._hdr("PCA Centerline Extraction", "Extract initial tunnel centerline control points from the working cloud.")
        self._start_worker("4.1_centerline", lambda: self.geo_mod.extract_centerline(self.context, section_count=self._resolve_section_count()))

    def _slot_4_2_iterative(self) -> None:
        self._hdr("Iterative Centerline Refinement", "Refine the tunnel axis using orthogonal section fitting.")
        if self.context.centerline is None: self._log(_tr("Run Step 4.1 first.", self.current_language)); return
        cl = self.context.centerline
        self._start_worker("4.2_iterative", lambda: self.geo_mod.extract_centerline_iterative(self.context, design_axis=cl, section_count=self._resolve_section_count(), mu=0.03, max_iter=20))

    def _slot_4_3_bspline(self) -> None:
        self._hdr("B-Spline Centerline Smoothing", "Generate a smooth differentiable tunnel axis for sectioning.")
        if self.context.centerline is None: self._log(_tr("Run Step 4.1 first.", self.current_language)); return
        cl = self.context.centerline; self._start_worker("4.3_bspline", lambda: self.geo_mod.smooth_bspline(cl))

    def _slot_4_4_frenet(self) -> None:
        self._hdr("Gravity-Aligned Section Frames", "Generate Frenet N-B section frames for orthogonal cross-sections.")
        if not self.context.frenet_frames: self._log(_tr("Run Step 4.1 first.", self.current_language)); return
        fr = self.context.frenet_frames; self._start_worker("4.4_frenet", lambda: self.geo_mod.generate_frenet_planes(fr))

    def _slot_4_5_seams(self) -> None:
        self._hdr("Ring Seam Detection", "Segment tunnel rings and identify seam transition locations.")
        if not self.context.frenet_frames: self._log(_tr("Run Step 4.1 first.", self.current_language)); return
        def _task():
            rings = self.seg_mod.segment_rings(self.context); cl = self.context.centerline; frs = self.context.frenet_frames
            n = min(len(rings), len(cl) if cl is not None else 0, len(frs))
            total = sum(len(self.seg_mod.detect_seam_boundaries(rings[i], cl[i], frs[i], k_clusters=6)) for i in range(n))
            return {"ring_count": len(rings), "total_seams": total}
        self._start_worker("4.5_seams", _task)

    def _slot_5_1_settlement(self) -> None:
        self._hdr("Crown Settlement", "Extract vertical displacement indicators at the tunnel crown.")
        self._start_worker("5.1_settlement", lambda: self.par_mod.calc_arch_settlement(self.context))

    def _slot_5_2_convergence(self) -> None:
        self._hdr("Horizontal Convergence", "Estimate lateral wall convergence across each tunnel section.")
        self._start_worker("5.2_convergence", lambda: self.par_mod.calc_horizontal_convergence(self.context))

    def _slot_5_3_heatmap(self) -> None:
        self._hdr("3D Deformation Heatmap", "Visualize deformation magnitudes on the tunnel point cloud.")
        self._start_worker("5.3_heatmap", lambda: self.par_mod.generate_heatmap(self.context))

    def _slot_5_4_polar(self) -> None:
        self._hdr("Polar Radial Deformation", "Map radial deformation by angle around each section.")
        if not self.context.frenet_frames or self.context.working_points is None: self._log(_tr("Complete Steps 2 and 4 before running this analysis.", self.current_language)); return
        self._start_worker("5.4_polar", lambda: self.par_mod.generate_polar_deformation_map(self.context, design_radius_m=3.0, num_bins=72))

    def _slot_5_5_ovality(self) -> None:
        self._hdr("Section Ovality", "Calculate ovality as a geometric distortion indicator.")
        self._start_worker("5.5_ovality", lambda: self.par_mod.calc_ovality(self.context))

    def _slot_5_6_eccentricity(self) -> None:
        self._hdr("Section Eccentricity", "Calculate measured center offset relative to the design center.")
        self._start_worker("5.6_eccentricity", lambda: self.par_mod.calc_eccentricity(self.context))

    def _slot_5_8_clearance_3d(self) -> None:
        self._hdr("Deformation / Clearance 3D Warning Map",
                  "Highlight sections with deformation or clearance warnings on the 3D viewport.")
        if not self.context.sections:
            self._log(_tr("Run Step 6.3 first.", self.current_language)); return
        sections = list(self.context.sections)
        ref_sections = list(getattr(self, "_section_ref_sections", []) or [])
        section_statuses = self._classify_section_warning_series(sections, ref_sections)
        def _task():
            import numpy as _np
            pts = self.context.working_points
            if pts is None: raise RuntimeError("No point cloud.")
            pts = validate_xyz(pts)
            warning_centers = []
            warning_levels = []
            for sec, (status, _issues) in zip(sections, section_statuses):
                if status != "OK" and sec.center_3d is not None:
                    warning_centers.append(sec.center_3d)
                    warning_levels.append(2 if status == "CRITICAL" else 1)
            status_mask = _np.zeros(len(pts), dtype=_np.uint8)
            if not warning_centers:
                return pts, status_mask, {"warning_sections": 0, "critical_points": 0, "caution_points": 0}
            # Mark points near warning section centers
            from scipy.spatial import cKDTree as _kd
            warn_arr = _np.asarray(warning_centers, dtype=_np.float64)
            levels = _np.asarray(warning_levels, dtype=_np.uint8)
            tree = _kd(warn_arr)
            d, idx = tree.query(pts, k=1, workers=-1)
            near = d < 0.5
            status_mask[near] = levels[idx[near]]
            return pts, status_mask, {
                "warning_sections": int(len(warning_centers)),
                "critical_points": int(_np.count_nonzero(status_mask == 2)),
                "caution_points": int(_np.count_nonzero(status_mask == 1)),
            }
        self._start_worker("5.8_clearance_3d", _task)

    def _classify_section_warning_series(self, sections, ref_sections=None):
        """Find local deformation anomalies instead of flagging the whole tunnel."""
        ref_sections = ref_sections or []
        n = len(sections)
        statuses = [["OK", []] for _ in sections]

        def add(i, level, label, value, unit):
            cur = statuses[i][0]
            if level == "CRITICAL" or cur == "OK":
                statuses[i][0] = level
            elif level == "CAUTION" and cur != "CRITICAL":
                statuses[i][0] = level
            statuses[i][1].append((level, label, value, unit))

        def local_flags(values, caution_abs, critical_abs, floor, label, unit):
            arr = np.asarray(values, dtype=np.float64)
            mag = np.abs(arr)
            finite = np.isfinite(mag)
            if not finite.any():
                return
            vals = mag[finite]
            med = float(np.nanmedian(vals))
            mad = float(np.nanmedian(np.abs(vals - med)))
            robust_sigma = 1.4826 * mad
            local_thr = med + max(3.0 * robust_sigma, floor)
            # If variation is tiny, avoid painting the whole tunnel for a global
            # bias in centerline/fit. Only distinct local peaks pass this gate.
            for i, v in enumerate(mag):
                if not np.isfinite(v):
                    continue
                is_local = n < 6 or v >= local_thr
                if v >= critical_abs and is_local:
                    add(i, "CRITICAL", label, arr[i], unit)
                elif v >= caution_abs and is_local:
                    add(i, "CAUTION", label, arr[i], unit)

        for i, sec in enumerate(sections):
            if sec.clearance_violation:
                val = sec.min_clearance_dist * 1e3 if np.isfinite(sec.min_clearance_dist) else float("nan")
                add(i, "CRITICAL", "clearance", val, "mm")

        if ref_sections:
            for label, attr in (("dW", "W1"), ("dH", "H1"), ("dR", "radius_fit")):
                deltas = []
                for i, sec in enumerate(sections):
                    ref = ref_sections[i] if i < len(ref_sections) else None
                    a = getattr(sec, attr, float("nan"))
                    b = getattr(ref, attr, float("nan")) if ref is not None else float("nan")
                    deltas.append((a - b) * 1e3 if np.isfinite(a) and np.isfinite(b) else float("nan"))
                local_flags(deltas, 10.0, 25.0, 10.0, label, "mm")
            d_oval = []
            d_ecc = []
            for i, sec in enumerate(sections):
                ref = ref_sections[i] if i < len(ref_sections) else None
                if ref is not None and np.isfinite(sec.ovality) and np.isfinite(ref.ovality):
                    d_oval.append(sec.ovality - ref.ovality)
                else:
                    d_oval.append(float("nan"))
                if ref is not None and np.isfinite(sec.eccentricity) and np.isfinite(ref.eccentricity):
                    d_ecc.append(sec.eccentricity - ref.eccentricity)
                else:
                    d_ecc.append(float("nan"))
            local_flags(d_oval, 0.5, 1.0, 0.35, "dOval", "%")
            local_flags(d_ecc, 10.0, 25.0, 15.0, "dEcc", "mm")
        else:
            local_flags([s.ovality for s in sections], 0.5, 1.0, 0.35, "ovality", "%")
            local_flags([s.eccentricity for s in sections], 10.0, 25.0, 15.0, "eccentricity", "mm")
        return [(status, issues) for status, issues in statuses]

    def _on_res_mode_changed(self, index):
        """Toggle the count vs spacing inputs for the resolution mode."""
        by_spacing = index == 1
        self._sp_sections.setVisible(not by_spacing)
        self._lbl_sections.setVisible(not by_spacing)
        self._sp_spacing.setVisible(by_spacing)
        self._lbl_spacing.setVisible(by_spacing)

    def _measured_axis_length(self):
        """Length of the working cloud along its dominant axis (m), or None."""
        pts = self.context.working_points
        if pts is None:
            return None
        try:
            p = validate_xyz(pts)
            _c, axis, _e1, _e2 = principal_axes(p)
            proj = (p - p.mean(axis=0)) @ axis
            return float(proj.max() - proj.min())
        except Exception:
            return None

    def _resolve_section_count(self):
        """Section count from the active resolution mode.

        By count: the spinbox value directly. By spacing: derived from the
        measured tunnel length / spacing, clamped to the spinbox range; falls
        back to the count value when the length cannot be measured yet.
        """
        if self._cmb_res_mode.currentIndex() == 1:
            length = self._measured_axis_length()
            spacing = float(self._sp_spacing.value())
            if length and spacing > 1e-6:
                n = int(round(length / spacing)) + 1
                n = max(self._sp_sections.minimum(), min(self._sp_sections.maximum(), n))
                return n
        return int(self._sp_sections.value())
    def _compute_auto_gauge(self):
        """Return (w, h, r) clearance gauge from the measured bore radius, or
        None. Pure NumPy (no GUI), so it is safe to call from a worker thread.

        A fixed default gauge (R=4.0 m) is larger than this tunnel (~2.75 m),
        so every lining point read as a violation. Estimate the bore radius
        (median radial distance to the PCA axis) and place the gauge just
        inside it (95%).
        """
        pts = self.context.working_points
        if pts is None:
            return None
        try:
            c, axis, _e1, _e2 = principal_axes(pts)
            p = validate_xyz(pts)
            d = p - c
            r = np.linalg.norm(d - np.outer(d @ axis, axis), axis=1)
            # The clearance gauge must sit just INSIDE the innermost lining
            # surface, not at the median radius (which is mid-wall and would
            # flag ~half the lining). Use a low percentile of the radial
            # distribution minus a small safety margin.
            r_inner = float(np.percentile(r, 2))
            if not np.isfinite(r_inner) or r_inner <= 0.1:
                return None
            gauge = max(0.3, r_inner - 0.20)   # 20 cm inside the bore
            return gauge, 2.0 * gauge, gauge   # (w, h, r)
        except Exception:
            return None

    def _auto_set_clearance(self) -> None:
        """GUI-thread helper: update the (hidden) clearance spinboxes from the
        measured radius so the 5.7 button uses an automatic envelope.
        """
        if not CORE_FEATURES_ONLY:
            return
        g = self._compute_auto_gauge()
        if g is None:
            return
        w, h, r = g
        self._sp_vl_w.setValue(w); self._sp_vl_h.setValue(h); self._sp_vl_r.setValue(r)
        self._log(_tr("Auto clearance gauge set from measured radius: R={r:.2f} m", self.current_language).format(r=r))

    def _slot_5_7_sections(self) -> None:
        self._hdr("Plot 2D Technical Section", "Display flat 2D engineering cross-sections with vehicle clearance limits.")
        if not self.context.frenet_frames or self.context.working_points is None: self._log(_tr("Complete Steps 2 and 4 before running this analysis.", self.current_language)); return
        if CORE_FEATURES_ONLY:
            self.context.tunnel_profile = self.par_mod.detect_profile(self.context)
            self._log(_tr("Auto-detected tunnel profile: {p}", self.current_language).format(p=self.context.tunnel_profile))
        elif not self._profile_user_set:
            # Full mode: auto-detect once and pre-select the dropdown so the
            # default matches the real shape (Circle/Box/Box 2-cell/U-type).
            # The user can still override; a manual pick disables this.
            detected = self.par_mod.detect_profile(self.context)
            self._profile_setting_programmatically = True
            self._profile_combo.setCurrentText(detected)
            self._profile_setting_programmatically = False
            self.context.tunnel_profile = detected
            self._log(_tr("Auto-detected tunnel profile: {p}", self.current_language).format(p=detected)
                      + "  (" + _tr("override in 'Tunnel Profile Type'", self.current_language) + ")")
        else:
            self.context.tunnel_profile = self._profile_combo.currentText()
        self._auto_set_clearance()
        # Read widget values on the GUI thread; the lambda runs in a worker
        # thread where touching QWidgets is undefined behaviour.
        vl_w, vl_h, vl_r = self._sp_vl_w.value(), self._sp_vl_h.value(), self._sp_vl_r.value()
        self._start_worker("5.7_sections", lambda: self.par_mod.compute_all_sections(self.context, vl_box_w=vl_w, vl_box_h=vl_h, vl_cir_r=vl_r))

    def _step63_sections_auto_task(self, section_count, vl_w, vl_h, vl_r):
        """Prepare missing state then compute 2D sections for the standalone 6.3 button.

        Auto Pipeline already creates working_points + centerline before 5.7.
        Manual 6.3 should be equally forgiving: use the loaded scan when no
        preprocessed working cloud exists, build a B-spline centerline when
        needed, then compute the same Field Robust sections.
        """
        if self.context.working_points is None:
            if self.context.scans:
                self.context.active_index = len(self.context.scans) - 1
                self.context.normalized_points = self.context.scans[-1].points
            else:
                raise RuntimeError("Load at least one scan before Step 6.3.")
        if not self.context.frenet_frames or self.context.centerline is None:
            cl, fr = self.geo_mod.extract_centerline_bspline(self.context, section_count=section_count)
            self.context.centerline = cl
            self.context.frenet_frames = fr
        else:
            cl, fr = self.context.centerline, self.context.frenet_frames
        if CORE_FEATURES_ONLY:
            self.context.tunnel_profile = self.par_mod.detect_profile(self.context)
        g = self._compute_auto_gauge()
        if g:
            vl_w, vl_h, vl_r = g
        sections = self.par_mod.compute_all_sections(
            self.context, vl_box_w=vl_w, vl_box_h=vl_h, vl_cir_r=vl_r)
        return {"centerline": cl, "frenet_frames": fr, "sections": sections}

    def _slot_6_3_sections(self) -> None:
        self._hdr("2D Technical Section T0/Tn",
                  "Display clean robust T0~Tn section outlines without interior noise spikes.")
        if hasattr(self.section_widget, "set_section_render_mode"):
            self.section_widget.set_section_render_mode("Field Robust")
        self._sync_step6_measured_point()

        sections = getattr(self.context, "sections", None) or []
        if not sections:
            self._log(_tr("No 2D sections yet; Step 6.3 will auto-prepare centerline and sections.", self.current_language))
            section_count = self._resolve_section_count()
            vl_w, vl_h, vl_r = self._sp_vl_w.value(), self._sp_vl_h.value(), self._sp_vl_r.value()
            self._start_worker("6.3_sections_auto",
                lambda: self._step63_sections_auto_task(section_count, vl_w, vl_h, vl_r))
            return

        self.right_tabs.setCurrentIndex(self._section_tab_idx)
        hotspots = self._sync_step6_measured_point()
        if hotspots:
            self._log("Step 6 status: Trend ready | 2D ready | Measured points ready | M3C2 optional | Export ready")
            self._log(_tr("Step 6.3 shows clean robust T0~Tn section outlines. Crown marker and trend use the same Step 6 location.", self.current_language))
        else:
            self._log("Step 6 status: 2D ready, but measured crown markers need Step 6 trend first.")

    def _slot_6_1_times(self) -> None:
        self._hdr("Load Time-Series Times", "Load reference and monitoring point-cloud times for deformation comparison.")
        fp0, _ = QtWidgets.QFileDialog.getOpenFileName(self, _tr("Load reference times T0", self.current_language), "", "Point Clouds (*.las *.laz *.ply *.txt *.xyz *.pts *.csv *.asc);;All Files (*.*)")
        if not fp0: return
        fpn, _ = QtWidgets.QFileDialog.getOpenFileName(self, _tr("Load monitoring times", self.current_language), "", "Point Clouds (*.las *.laz *.ply *.txt *.xyz *.pts *.csv *.asc);;All Files (*.*)")
        if not fpn: return
        self._start_worker("6.1_times", lambda: self.ts_mod.load_times(fp0, fpn))

    def _report_timeseries_extras(self, series: dict, labels) -> None:
        """Log Step 6 crown-first values and write the simple CSV report."""
        import os as _os
        labels = list(labels)
        crown = np.asarray(series.get("crown_settlement_mm", []), dtype=np.float64)
        if crown.size == len(labels) + 1:
            crown = crown[1:]
        p95 = np.asarray(series.get("p95_abs_mm", []), dtype=np.float64)
        if crown.size:
            new_crown = np.diff(np.concatenate([[0.0], crown]))
            self._log(f"  Crown settlement: {np.round(crown, 2).tolist()} mm")
            self._log(f"  New crown move: {np.round(new_crown, 2).tolist()} mm")
        warn_epochs = []
        danger_epochs = []
        for i, lbl in enumerate(labels):
            val = abs(float(crown[i])) if i < crown.size and np.isfinite(crown[i]) else (float(p95[i]) if i < p95.size else 0.0)
            if val >= 25.0:
                danger_epochs.append(lbl)
            elif val >= 10.0:
                warn_epochs.append(lbl)
        if warn_epochs or danger_epochs:
            self._log(f"  Step 6 result by crown: warning={warn_epochs}, danger={danger_epochs}")
        gt = None
        try:
            s0 = self.context.scans[0] if self.context.scans else None
            if s0 is not None and getattr(s0, "path", None):
                gt_path = _os.path.join(_os.path.dirname(s0.path), "ground_truth.csv")
                if _os.path.exists(gt_path):
                    gt = self.ts_mod.compare_to_ground_truth(series, gt_path)
                    self._log("  " + gt["summary"])
        except Exception as e:
            self._log(f"  Ground-truth validation skipped: {e}")
        try:
            self._export_timeseries_csv(series, labels, gt)
        except Exception as e:
            self._log(f"  Time-series CSV export skipped: {e}")

    def _export_timeseries_csv(self, series: dict, labels, gt: dict = None) -> None:
        """Write a simple Step 6 table next to the loaded data."""
        import os as _os, csv as _csv
        s0 = self.context.scans[0] if self.context.scans else None
        out_dir = (_os.path.dirname(s0.path) if (s0 is not None and getattr(s0, "path", None))
                   else _os.getcwd())
        out_path = _os.path.join(out_dir, "timeseries_report.csv")
        def arr(key):
            return np.asarray(series.get(key, []), dtype=np.float64).ravel()
        def value_at(values, idx):
            return float(values[idx]) if idx < values.size and np.isfinite(values[idx]) else None

        median = arr("median_mm")
        p95 = arr("p95_abs_mm")
        max_abs = arr("max_abs_mm")
        inc_p95 = arr("incremental_p95_abs_mm")
        velocity = arr("velocity_mm_per_epoch")
        acceleration = arr("acceleration_mm_per_epoch2")
        crown = np.asarray(series.get("crown_settlement_mm", []), dtype=np.float64)
        if crown.size == len(labels) + 1:
            crown = crown[1:]
        try:
            location_txt = f"Ch {float(series.get('crown_chainage_m', float('nan'))):.1f}m"
        except Exception:
            location_txt = "Ch --"
        measured_point_txt = _tr("Tunnel crown", self.current_language)
        caution = 10.0
        critical = 25.0
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            w = _csv.writer(f)
            w.writerow(["main_metric", "Crown settlement + deformation summary"])
            w.writerow(["measured_point", measured_point_txt])
            w.writerow(["location", location_txt])
            w.writerow([])
            w.writerow(["epoch", "location", "measured_point", "crown_settlement_mm",
                        "new_crown_move_mm", "median_displacement_mm",
                        "cumulative_p95_abs_mm", "cumulative_max_abs_mm",
                        "incremental_p95_abs_mm", "velocity_mm_per_epoch",
                        "acceleration_mm_per_epoch2", "result"])
            prev_crown = 0.0
            for i, lbl in enumerate(labels):
                crown_val = value_at(crown, i)
                new_move = crown_val - prev_crown if crown_val is not None else None
                p95_val = value_at(p95, i)
                score = abs(crown_val) if crown_val is not None else (p95_val or 0.0)
                if score >= critical:
                    result = "Danger"
                elif score >= caution:
                    result = "Warning"
                else:
                    result = "OK"
                def fmt(value):
                    return f"{value:+.2f}" if value is not None else ""
                w.writerow([lbl,
                    location_txt,
                    measured_point_txt,
                    fmt(crown_val),
                    fmt(new_move),
                    fmt(value_at(median, i)),
                    fmt(p95_val),
                    fmt(value_at(max_abs, i)),
                    fmt(value_at(inc_p95, i)),
                    fmt(value_at(velocity, i)),
                    fmt(value_at(acceleration, i)),
                    result])
                if crown_val is not None:
                    prev_crown = crown_val
        self._log(f"  Time-series report saved: {out_path}")

    def _slot_6_2_plot(self) -> None:
        self._hdr("Deformation Trend + Forecast",
                  "Compute the multi-times deformation trend and, with 3+ times, "
                  "extrapolate the caution/critical threshold crossing.")
        if len(self.context.scans) < 2:
            self._log(_tr("Load at least 2 scans (T0 and Tn) first.", self.current_language)); return
        if self.context.registered_points is None and len(self.context.scans) >= 2:
            self._log(_tr("Tip: run 3.0 Auto-align first if T0/Tn scanner poses differ.", self.current_language))
        import os as _os

        # If T0~Tn are loaded, use all times. For a normal two-scan workflow,
        # use the current working/registered Tn so the plot reflects alignment.
        def _epoch_label(scan, fallback: str) -> str:
            meta = getattr(scan, 'metadata', None) or {}
            label = str(meta.get('epoch_label') or '').strip()
            if label:
                return label
            return _os.path.splitext(_os.path.basename(getattr(scan, 'path', None) or fallback))[0]

        if len(self.context.scans) > 2:
            times = [np.asarray(scan.points, dtype=np.float64) for scan in self.context.scans]
            labels = [_epoch_label(scan, f'T{i}') for i, scan in enumerate(self.context.scans[1:], start=1)]
            mode = 'multi-epoch'
        else:
            tn_pts = self.context.working_points if self.context.working_points is not None else self.context.scans[1].points
            times = [np.asarray(self.context.scans[0].points, dtype=np.float64), np.asarray(tn_pts, dtype=np.float64)]
            labels = [_epoch_label(self.context.scans[1], 'Tn')]
            mode = 'pair fallback'

        shown_labels = ["T0"] + list(labels)
        self._log(f"Time-series mode: {mode}; x-axis labels={shown_labels}")

        # Combined trend + forecast: compute the series, then (3+ times)
        # extrapolate threshold crossing in the same worker.
        self._start_worker("6.1_plot",
            lambda: self._compute_trend_and_forecast(times, labels))

    def _compute_trend_and_forecast(self, times, labels) -> dict:
        """Worker body for Step 6.1: spatiotemporal trend + optional forecast."""
        series = self.ts_mod.spatiotemporal_series(
            times, labels=labels, cyl_radius=0.5, normal_radius=0.6)
        try:
            preferred = None
            try:
                preferred = self._preferred_crown_chainage_m()
            except Exception:
                preferred = None
            # Prefer axis-aligned chainage for general tunnels; avoid forced curve radius.
            pick = self.ts_mod.suggest_crown_chainage(
                times,
                chainage_window_m=5.0,
                lateral_window_m=12.0,
                crown_percentile=98.0,
                curve_radius_m=None,
                preferred_chainage_m=preferred,
            )
            crown = self.ts_mod.crown_settlement_series(
                times, labels=["T0"] + list(labels),
                chainage_m=float(pick.get("chainage_m", 0.0)),
                chainage_window_m=5.0, lateral_window_m=12.0,
                crown_percentile=98.0, curve_radius_m=None)
            series["crown_settlement_mm"] = crown.get("crown_settlement_mm")
            crown_abs = np.abs(np.asarray(crown.get("crown_settlement_mm", []), dtype=np.float64))
            series["crown_settlement_abs_mm"] = crown_abs[1:] if crown_abs.size == len(labels) + 1 else crown_abs
            series["crown_zone_points"] = crown.get("zone_points")
            series["crown_chainage_m"] = crown.get("chainage_m")
            series["crown_metric"] = crown.get("metric")
            series["crown_chainage_source"] = pick.get("source")
            series["crown_chainage_search_settlement_mm"] = pick.get("settlement_mm")
        except Exception as exc:
            series["crown_warning"] = str(exc)
        forecast = None
        try:
            if len(labels) >= 3:
                # Forecast on the SAME metric the trend chart plots.
                forecast_metric = "crown_settlement_abs_mm" if len(series.get("crown_settlement_abs_mm", [])) == len(labels) else "p95_abs_mm"
                forecast = self.ts_mod.forecast_threshold_crossing(
                    series,
                    caution_mm=SECTION_DELTA_CAUTION_MM,
                    critical_mm=SECTION_DELTA_CRITICAL_MM,
                    degree=2,
                    metric=forecast_metric)
        except Exception:
            forecast = None
        return {"series": series, "forecast": forecast}

    def _sync_step6_measured_point(self) -> list:
        """Keep every Step 6 view pointing at the same measured crown point."""
        hotspots = list(getattr(self, "_trend_hotspots", []) or [])
        series = getattr(self.context, "time_series_result", None)
        if not hotspots and isinstance(series, dict):
            hotspots = self._trend_hotspots_from_series(series)
            self._trend_hotspots = hotspots
        self._active_step6_hotspot = max(
            hotspots,
            key=lambda h: abs(float(h.get("p95_abs_mm", h.get("value_mm", 0.0))))
        ) if hotspots else None
        if hasattr(self.section_widget, "set_trend_hotspots"):
            self.section_widget.set_trend_hotspots(hotspots)
        if hasattr(self.section_widget, "set_measured_points_visible"):
            visible = True
            labels = None
            if hasattr(self.multi_epoch_widget, "measured_points_visible"):
                visible = self.multi_epoch_widget.measured_points_visible()
            if hasattr(self.multi_epoch_widget, "visible_measured_labels"):
                labels = self.multi_epoch_widget.visible_measured_labels()
            self.section_widget.set_measured_points_visible(visible, labels=labels)
        if hasattr(self.multi_epoch_widget, "set_link_hotspot"):
            self.multi_epoch_widget.set_link_hotspot(self._active_step6_hotspot)
        if hasattr(self, "_chainage_ruler"):
            self._chainage_ruler.set_hotspots(hotspots)
        return hotspots

    def _set_step6_measured_points_visible(self, visible: bool) -> None:
        if hasattr(self.section_widget, "set_measured_points_visible"):
            labels = None
            if hasattr(self.multi_epoch_widget, "visible_measured_labels"):
                labels = self.multi_epoch_widget.visible_measured_labels()
            self.section_widget.set_measured_points_visible(bool(visible), labels=labels)
        if visible:
            self._sync_step6_measured_point()


    def _preferred_crown_chainage_m(self):
        """Optional crown chainage hint from active hotspot or ground_truth.csv."""
        h = getattr(self, "_active_step6_hotspot", None)
        if isinstance(h, dict) and h.get("position") == "Crown":
            try:
                val = float(h.get("chainage_m"))
                if np.isfinite(val):
                    return val
            except Exception:
                pass
        try:
            import os as _os
            import csv as _csv
            s0 = self.context.scans[0] if self.context.scans else None
            if s0 is None or not getattr(s0, "path", None):
                return None
            gt_path = _os.path.join(_os.path.dirname(s0.path), "ground_truth.csv")
            if not _os.path.exists(gt_path):
                return None
            best = None
            with open(gt_path, "r", encoding="utf-8", newline="") as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    dtype = str(row.get("deformation_type") or row.get("type") or "").lower()
                    if "crown" not in dtype:
                        continue
                    ch = float(row.get("chainage_m") or row.get("chainage") or "nan")
                    mag = abs(float(row.get("deformation_mm") or row.get("value_mm") or row.get("mm") or 0.0))
                    if not np.isfinite(ch):
                        continue
                    if best is None or mag > best[0]:
                        best = (mag, ch)
            return None if best is None else float(best[1])
        except Exception:
            return None

    def _log_step6_status_banner(self, series: dict = None, forecast=None) -> None:
        """One short status block so Step 6 results are easy to read."""
        series = series or getattr(self.context, "time_series_result", None) or {}
        labels = list(series.get("labels", []) or [])
        crown_ch = series.get("crown_chainage_m")
        crown_src = series.get("crown_chainage_source")
        crown = np.asarray(series.get("crown_settlement_mm", []), dtype=np.float64)
        p95 = np.asarray(series.get("p95_abs_mm", []), dtype=np.float64)
        metric = "crown"
        value = float("nan")
        if crown.size:
            value = float(crown[np.nanargmax(np.abs(crown))]) if np.any(np.isfinite(crown)) else float("nan")
        elif p95.size:
            metric = "p95"
            value = float(np.nanmax(p95)) if np.any(np.isfinite(p95)) else float("nan")
        # Section warning counts if 2D sections already computed.
        n_caut = n_crit = 0
        try:
            sections = list(getattr(self.context, "sections", []) or [])
            ref = getattr(self, "_section_ref_sections", None)
            if sections:
                for st, _iss in classify_sections(sections, ref, epoch_sections=getattr(self, "_section_epoch_sections", None)):
                    if st == "CRITICAL":
                        n_crit += 1
                    elif st == "CAUTION":
                        n_caut += 1
        except Exception:
            pass
        parts = [
            f"epochs={len(labels) + 1 if labels else len(getattr(self.context, 'scans', []) or [])}",
            f"metric={metric}",
        ]
        if np.isfinite(value):
            parts.append(f"peak={value:+.1f}mm")
        if crown_ch is not None and np.isfinite(float(crown_ch)):
            src = f"/{crown_src}" if crown_src else ""
            parts.append(f"crown_ch={float(crown_ch):.1f}m{src}")
        if n_crit or n_caut:
            parts.append(f"sections=CRIT{n_crit}/CAUT{n_caut}")
        parts.append(f"thresholds={SECTION_DELTA_CAUTION_MM:g}/{SECTION_DELTA_CRITICAL_MM:g}mm")
        if forecast and forecast.get("ok"):
            parts.append("forecast=ready")
        msg = "Step 6 status: " + " | ".join(parts)
        self._log(msg)
        try:
            self.sb_msg.setText(msg)
        except Exception:
            pass
        # Push crown peak into Summary Dashboard cards.
        try:
            if hasattr(self, "dashboard_widget") and hasattr(self.dashboard_widget, "update_step6_summary"):
                self.dashboard_widget.update_step6_summary(series, forecast)
                # Jump to dashboard so the summary is visible immediately.
                if hasattr(self, "_dashboard_tab_idx"):
                    self.right_tabs.setCurrentIndex(self._dashboard_tab_idx)
        except Exception as exc:
            self._log(f"  Dashboard Step 6 summary skipped: {exc}")

    def _trend_hotspots_from_series(self, series: dict) -> list:
        """Markers for the Step 6 trend.

        When crown settlement is available, markers intentionally point to the
        crown chainage so the trend chart, table, M3C2 map, and 2D section all
        describe the same engineering location. Falls back to the older p95
        representative corepoint only when no crown metric exists.
        """
        try:
            labels = list(series.get("labels", []))
            crown = np.asarray(series.get("crown_settlement_mm", []), dtype=np.float64)
            if crown.size == len(labels) + 1:
                chainage = float(series.get("crown_chainage_m", float("nan")))
                hotspots = []
                for i, lbl in enumerate(labels):
                    signed = float(crown[i + 1])
                    hotspots.append({
                        "label": lbl,
                        "chainage_m": chainage,
                        "angle_deg": 90.0,
                        "position": "Crown",
                        "value_mm": signed,
                        "p95_abs_mm": abs(signed),
                        "metric": "crown_settlement_mm",
                    })
                return hotspots

            corepoints = np.asarray(series.get("corepoints", []), dtype=np.float64)
            matrix = np.asarray(series.get("distance_matrix_mm", []), dtype=np.float64)
            p95 = np.asarray(series.get("p95_abs_mm", []), dtype=np.float64)
            if corepoints.ndim != 2 or corepoints.shape[1] != 3 or matrix.ndim != 2:
                return []
            if matrix.shape[1] != corepoints.shape[0] or not self.context.frenet_frames:
                return []
            chainage, angle, _ = self._m3c2_developed_coords(corepoints)
            hotspots = []
            for i, row in enumerate(matrix):
                mag = np.abs(np.asarray(row, dtype=np.float64))
                finite = np.isfinite(mag) & np.isfinite(chainage) & np.isfinite(angle)
                if not np.any(finite):
                    continue
                target = float(p95[i]) if i < len(p95) and np.isfinite(p95[i]) else float(np.nanpercentile(mag[finite], 95))
                idxs = np.flatnonzero(finite)
                j = idxs[int(np.nanargmin(np.abs(mag[idxs] - target)))]
                hotspots.append({
                    "label": labels[i] if i < len(labels) else f"T{i + 1}",
                    "chainage_m": float(chainage[j]),
                    "angle_deg": float(angle[j]),
                    "position": self._m3c2_position_label(float(angle[j])),
                    "value_mm": float(row[j]),
                    "p95_abs_mm": target,
                    "metric": "p95_abs_mm",
                })
            return hotspots
        except Exception as exc:
            self._log(f"Trend hotspot markers skipped: {exc}")
            return []

    def _m3c2_developed_coords(self, pts):
        """Project corepoints to (chainage_m, angle_deg) for the 2D developed
        M3C2 map. Nearest Frenet frame gives the chainage (cumulative arc length)
        and the local N-B angle. Falls back to a plan view (X, Y) with no frames.
        Returns (chainage, angle_deg, (x_label, y_label))."""
        pts = np.asarray(pts, dtype=np.float64)
        frames = self.context.frenet_frames
        if not frames:
            return pts[:, 0], pts[:, 1], ("X (m)", "Y (m)")
        centers = np.array([f["center"] for f in frames], dtype=np.float64)
        Narr = np.array([f["N"] for f in frames], dtype=np.float64)
        Barr = np.array([f["B"] for f in frames], dtype=np.float64)
        seg = np.linalg.norm(np.diff(centers, axis=0), axis=1)
        s = np.concatenate([[0.0], np.cumsum(seg)])
        # Nearest frame per point via the (N,M) squared-distance identity.
        d2 = ((pts ** 2).sum(1)[:, None] + (centers ** 2).sum(1)[None, :]
              - 2.0 * (pts @ centers.T))
        idx = np.argmin(d2, axis=1)
        rel = pts - centers[idx]
        n_comp = np.einsum("ij,ij->i", rel, Narr[idx])
        b_comp = np.einsum("ij,ij->i", rel, Barr[idx])
        angle = np.degrees(np.arctan2(b_comp, n_comp))
        return s[idx], angle, ("Chainage (m)", "Circumferential angle (deg)")

    @staticmethod
    def _m3c2_position_label(angle_deg: float) -> str:
        """Circumferential structure name from the developed angle (N-B plane).
        +90deg = crown (top), -90 = invert (floor), 0/±180 = side walls."""
        a = float(angle_deg)
        if 45.0 <= a < 135.0:
            return "Crown"
        if -135.0 <= a < -45.0:
            return "Invert"
        if -45.0 <= a < 45.0:
            return "Wall (R)"
        return "Wall (L)"

    def _m3c2_damage_zones(self, chainage, angle, dist, significant=None,
                           caution: float = 10.0, critical: float = 25.0):
        """Group over-threshold M3C2 points into damage zones keyed by (1 m
        chainage bin, circumferential structure). Keeps the worst (largest |d|)
        point per zone. Returns a severity-sorted list of dicts."""
        ch = np.asarray(chainage, dtype=np.float64)
        ang = np.asarray(angle, dtype=np.float64)
        d = np.asarray(dist, dtype=np.float64)
        mag = np.abs(d)
        if significant is not None and np.size(significant) == d.size:
            sig = np.asarray(significant, dtype=bool)
        else:
            sig = np.ones(d.size, dtype=bool)   # no LoD -> magnitude only
        keep = np.isfinite(d) & np.isfinite(ch) & np.isfinite(ang) & sig & (mag >= caution)
        groups: dict = {}
        for i in np.flatnonzero(keep):
            pos = self._m3c2_position_label(ang[i])
            key = (round(float(ch[i])), pos)
            cur = groups.get(key)
            if cur is None or abs(d[i]) > abs(cur["peak_mm"]):
                groups[key] = {"chainage": float(ch[i]), "position": pos,
                               "peak_mm": float(d[i]), "angle": float(ang[i])}
        zones = list(groups.values())
        for z in zones:
            z["severity"] = "CRITICAL" if abs(z["peak_mm"]) >= critical else "CAUTION"
        zones.sort(key=lambda z: abs(z["peak_mm"]), reverse=True)
        return zones

    def _slot_6_3_m3c2(self) -> None:
        self._hdr("M3C2 Deformation Map",
                  "Supplementary map only. Crown settlement / section warnings remain the main Step 6 result.")
        self._sync_step6_measured_point()
        if len(self.context.scans) < 2:
            self._log(_tr("Load at least 2 scans (T0 and Tn) first.", self.current_language)); return
        self._log(_tr("M3C2 is supplementary. If map looks near zero, trust 6.1 trend and 6.3 sections first.", self.current_language))
        import os as _os
        epoch0 = self.context.scans[0].points
        if len(self.context.scans) > 2:
            compare_scan = self.context.scans[-1]
            epoch1 = compare_scan.points
            compare_name = _os.path.splitext(_os.path.basename(compare_scan.path or f"T{len(self.context.scans)-1}"))[0]
        else:
            compare_scan = self.context.scans[1]
            epoch1 = self.context.working_points if self.context.working_points is not None else compare_scan.points
            compare_name = _os.path.splitext(_os.path.basename(compare_scan.path or "Tn"))[0]
        self._m3c2_compare_label = f"T0\u2192{compare_name}"
        self._log(f"  M3C2 compare: {self._m3c2_compare_label} (supplementary; crown settlement remains the Step 6 result).")
        self._start_worker("6.2_m3c2",
            lambda: self.ts_mod.m3c2_distances(epoch0, epoch1, cyl_radius=0.5, normal_radius=0.6))

    def _slot_6_5_forecast(self) -> None:
        self._hdr("Crown Settlement Forecast",
                  "Forecast warning/danger crossing using the Step 6 crown settlement metric.")
        self._sync_step6_measured_point()
        if not hasattr(self, "_multi_epoch_series") or self._multi_epoch_series is None:
            self._log(_tr("Run Step 6 trend with 3+ times first, then Step 6.5.", self.current_language))
            return
        series = self._multi_epoch_series
        labels = list(series.get("labels", []))
        crown_abs = np.asarray(series.get("crown_settlement_abs_mm", []), dtype=np.float64)
        metric = "crown_settlement_abs_mm" if crown_abs.size == len(labels) else "p95_abs_mm"
        self._log(f"  Forecast metric: {'crown settlement' if metric == 'crown_settlement_abs_mm' else 'overall movement p95'}")
        self._start_worker("6.5_forecast", lambda: self.ts_mod.forecast_threshold_crossing(
            series,
            caution_mm=SECTION_DELTA_CAUTION_MM,
            critical_mm=SECTION_DELTA_CRITICAL_MM,
            degree=2, metric=metric))

    def _slot_6_6_export_timeseries(self) -> None:
        self._hdr("Export Time-Series Report",
                  "Export the Step 6 crown settlement table, chart, and forecast to Excel and PDF.")
        self._sync_step6_measured_point()
        series = getattr(self, "_multi_epoch_series", None)
        if not series or not series.get("labels"):
            series = getattr(self.context, "time_series_result", None)
        if not series or not series.get("labels"):
            self._log(_tr("Run 6.1 Deformation trend first (works for T0/Tn pair or multi-epoch folder).", self.current_language)); return
        n_epochs = len(series.get("labels", []))
        if n_epochs < 2:
            self._log(_tr("Pair export mode: T0/Tn table will be written. Load 1.9 folder (3+ times) for full multi-epoch forecast columns.", self.current_language))
        import os as _os
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, _tr("Save Time-Series Report", self.current_language),
            "tunnel_timeseries_report.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        # Ground-truth (auto-detect ground_truth.csv next to the loaded times)
        # and the latest forecast (if Step 6.5 was run) enrich the report.
        gt = None
        try:
            s0 = self.context.scans[0] if self.context.scans else None
            if s0 is not None and getattr(s0, "path", None):
                gt_path = _os.path.join(_os.path.dirname(s0.path), "ground_truth.csv")
                if _os.path.exists(gt_path):
                    gt = self.ts_mod.compare_to_ground_truth(series, gt_path)
        except Exception as e:
            self._log(f"  GT validation skipped: {e}")
        forecast = getattr(self, "_forecast_data", None)
        pdf_path = _os.path.splitext(path)[0] + ".pdf"
        self._start_worker("6.6_export_ts", lambda: self._do_export_timeseries(
            series, path, pdf_path, gt, forecast))

    def _do_export_timeseries(self, series, xlsx_path, pdf_path, gt, forecast):
        """Worker body: write Excel + PDF, return both paths."""
        xlsx = self.exp_mod.export_timeseries_excel(series, xlsx_path, gt=gt, forecast=forecast)
        pdf = None
        try:
            pdf = self.pdf_mod.export_timeseries_pdf(series, pdf_path, gt=gt, forecast=forecast)
        except Exception as e:
            pdf = f"(PDF skipped: {e})"
        return {"xlsx": xlsx, "pdf": pdf}

    def _slot_8_1_csv(self) -> None:
        self._hdr("Export CSV", "Export section parameters to CSV file.")
        if not self.context.sections and not self.context.parameters:
            self._log(_tr("Run parameter extraction first (Step 5).", self.current_language)); return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, _tr("Save CSV", self.current_language), "tunnel_report.csv", "CSV Files (*.csv)")
        if not path: return
        self._start_worker("8.1_csv", lambda: self.exp_mod.export_csv(self.context, path))

    def _slot_8_2_excel(self) -> None:
        self._hdr("Export Excel Report", "Export full analysis report with charts and warnings.")
        if not self.context.sections and not self.context.parameters:
            self._log(_tr("Run parameter extraction first (Step 5).", self.current_language)); return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, _tr("Save Excel Report", self.current_language), "tunnel_report.xlsx", "Excel Files (*.xlsx)")
        if not path: return
        scan = self.context.active_scan
        proj = scan.path if scan and scan.path else "Tunnel Analysis"
        self._start_worker("8.2_excel", lambda: self.exp_mod.export_excel(
            self.context, path, project_name=proj, engineer="CBNU Smart Structure Lab"))

    def _slot_8_4_web(self) -> None:
        self._hdr("Web Dashboard", "Launch interactive web dashboard in browser.")
        import threading, webbrowser
        from ..web_dashboard import build_app
        def _launch():
            try:
                app = build_app(self.context)
                port = 8050
                url = f"http://127.0.0.1:{port}"
                threading.Timer(1.5, lambda: webbrowser.open(url)).start()
                app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
                return url
            except Exception as e:
                raise RuntimeError(f"Dashboard error: {e}")
        t = threading.Thread(target=_launch, daemon=True)
        t.start()
        self._log(_tr("Web dashboard starting at http://127.0.0.1:8050 ...", self.current_language))
        import time; time.sleep(1.5)
        import webbrowser; webbrowser.open("http://127.0.0.1:8050")

    def _slot_8_3_pdf(self) -> None:
        self._hdr("Export PDF Report", "Generate professional PDF inspection report.")
        if not self.context.sections and not self.context.parameters:
            self._log(_tr("Run parameter extraction first (Step 5).", self.current_language)); return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, _tr("Save PDF Report", self.current_language), "tunnel_report.pdf", "PDF Files (*.pdf)")
        if not path: return
        scan = self.context.active_scan
        proj = scan.path if scan and scan.path else "Tunnel Analysis"
        self._start_worker("8.3_pdf", lambda: self.pdf_mod.export_pdf(
            self.context, path, project_name=proj, engineer="CBNU Smart Structure Lab"))

    def _slot_8_5_work_order(self) -> None:
        self._hdr("AI Work Order",
                  "Generate a prioritized maintenance work order (PDF) from flagged sections.")
        if not self.context.sections:
            self._log(_tr("Run parameter extraction first (Step 5).", self.current_language)); return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, _tr("Save Work Order", self.current_language),
            "tunnel_work_order.pdf", "PDF Files (*.pdf)")
        if not path: return
        scan = self.context.active_scan
        proj = scan.path if scan and scan.path else "Tunnel Analysis"
        sections = self.context.sections
        ref_secs = list(getattr(self, "_section_ref_sections", []) or [])
        times_secs_all = getattr(self, "_section_epoch_sections", []) or None

        def _task():
            # classify_sections is the single source of truth shared with the
            # ruler / 2D track / dashboard; inject it so rag_ai stays headless.
            statuses = classify_sections(sections, ref_secs or None,
                                         epoch_sections=times_secs_all)
            order = self.rag_mod.generate_work_order(
                self.context, statuses, project_name=str(proj))
            out = self.pdf_mod.export_work_order_pdf(
                self.context, order, path, project_name=str(proj))
            return {"path": out, "n_critical": order.get("n_critical", 0),
                    "n_caution": order.get("n_caution", 0),
                    "n_items": len(order.get("items", []))}

        self._start_worker("8.5_workorder", _task)

    @staticmethod
    def _step7_ifc_preflight(context, out_path: str = None,
                             include_components: bool = False) -> tuple[bool, str]:
        """Validate Step 7 IFC inputs without touching Qt state."""
        sections = list(getattr(context, "sections", []) or [])
        centerline = getattr(context, "centerline", None)
        has_centerline = centerline is not None and len(centerline) >= 2
        if not sections:
            return False, "Run Step 6.3 (or Step 5.7 in advanced mode) first to compute 2D tunnel sections before IFC export."
        if not has_centerline and len(sections) < 2:
            return False, "Run Step 4.3b to build the tunnel centerline, or compute at least two sections for lining export."
        if include_components and not (getattr(context, "component_points", None) or {}):
            return False, "Run auto-denoise (Step 2.5) first to detect cables/lights/people before IFC + Components export."
        if out_path:
            try:
                from pathlib import Path as _Path
                path = _Path(out_path)
                if path.suffix.lower() != ".ifc":
                    return False, "Save path must end with .ifc."
                if not str(path.parent):
                    return False, "Save path parent directory is invalid."
            except Exception as exc:
                return False, f"Invalid IFC save path: {exc}"
        return True, "OK"

    @staticmethod
    def _count_component_points(component_points) -> int:
        """Count component point rows defensively for Step 7 logging."""
        total = 0
        for value in (component_points or {}).values():
            try:
                total += len(value)
            except Exception:
                continue
        return int(total)

    def _preflight_step7_ifc(self, include_components: bool = False,
                             path: str = None) -> tuple[bool, str]:
        return self._step7_ifc_preflight(self.context, path, include_components)

    def _start_ifc_export(self, path: str, schema: str = "IFC4",
                          include_components: bool = False,
                          title: str = "IFC4") -> None:
        ok, msg = self._preflight_step7_ifc(include_components=include_components, path=path)
        if not ok:
            self._log(_tr(msg, self.current_language))
            return
        scan = self.context.active_scan
        proj = scan.path if scan and scan.path else "Tunnel Analysis"
        ref_secs = list(getattr(self, "_section_ref_sections", []) or [])
        n_sections = len(getattr(self.context, "sections", []) or [])
        n_components = self._count_component_points(getattr(self.context, "component_points", {}) or {})
        self._log(f"Starting {title} export: schema={schema}, sections={n_sections}, components={n_components}, path={path}")

        def _task():
            out = self.ifc_mod.export_ifc(
                self.context, path, project_name=proj, engineer="CBNU Smart Structure Lab",
                schema=schema, include_components=include_components,
                ref_sections=ref_secs)
            return {"path": out, "schema": schema, "title": title,
                    "sections": n_sections, "components": n_components}

        self._start_worker("7.1_ifc", _task)

    def _slot_7_1_ifc(self) -> None:
        self._hdr("IFC/BIM Export (IFC4)", "Export tunnel geometry and parameters to IFC4 format.")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, _tr("Save IFC Model", self.current_language), "tunnel_model.ifc", "IFC Files (*.ifc)")
        if not path: return
        self._start_ifc_export(path, schema="IFC4", include_components=False, title="IFC4")

    def _slot_7_1b_ifc_alignment(self) -> None:
        self._hdr("IFC4X3 Export (IfcAlignment)", "Export with the centerline as an IfcAlignment (infrastructure linear-referencing standard).")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, _tr("Save IFC4X3 Model", self.current_language), "tunnel_model_4x3.ifc", "IFC Files (*.ifc)")
        if not path: return
        self._start_ifc_export(path, schema="IFC4X3_ADD2", include_components=False, title="IFC4X3 Alignment")

    def _slot_7_1c_ifc_components(self) -> None:
        self._hdr("IFC Export + Components", "Export IFC including detected cables/lights/people as coloured proxies (run auto-denoise first).")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, _tr("Save IFC Model with Components", self.current_language), "tunnel_model_components.ifc", "IFC Files (*.ifc)")
        if not path: return
        self._start_ifc_export(path, schema="IFC4", include_components=True, title="IFC + Components")

    def _slot_7_2_query_ai(self) -> None:
        self._hdr("AI Engineering Assistant (RAG)", "Query local LLM with safety standards knowledge base.")
        raw_prompt = self.ai_prompt.toPlainText().strip()
        prompt = raw_prompt or "Summary mode: summarize the tunnel inspection results, identify critical/caution locations, recommend next steps, and state that this is decision support only."
        if not raw_prompt:
            self._log("AI assistant: empty prompt -> summary mode.")
        self.right_tabs.setCurrentIndex(self._ai_tab_idx)
        self._start_worker("7.2_ai", lambda: self.rag_mod.query(prompt, self.context))

    def _check_auto_pipeline(self, key: str) -> None:
        """After each worker finishes, check if we are in auto pipeline mode."""
        if not self._auto_running:
            return
        if not hasattr(self, "_auto_steps") or not hasattr(self, "_auto_step"):
            return
        if self._auto_step >= len(self._auto_steps):
            return
        current_key = self._auto_steps[self._auto_step][0]
        if key == current_key:
            self._auto_step += 1
            QtCore.QTimer.singleShot(200, self._run_next_auto_step)

    def _refresh_station_list(self) -> None:
        """Update station tree widget (Faro SCENE style)."""
        if not hasattr(self, "_station_tree"): return
        self._station_tree.clear()
        root = QtWidgets.QTreeWidgetItem(self._station_tree, ["Project"])
        root.setIcon(0, self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        root.setExpanded(True)
        scans_grp = QtWidgets.QTreeWidgetItem(root, ["Scans"])
        scans_grp.setIcon(0, self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView))
        scans_grp.setExpanded(True)
        for i, sc in enumerate(self.context.scans):
            import pathlib
            color = self._station_colors[i % len(self._station_colors)]
            fname = pathlib.Path(sc.path).name if sc.path else ("scan_" + str(i+1))
            role = str((sc.metadata or {}).get("epoch_role", ""))
            prefix = role if role else "S" + str(i+1)
            label = prefix + "  " + fname
            item = QtWidgets.QTreeWidgetItem(scans_grp, [label])
            item.setCheckState(0, QtCore.Qt.Checked)
            item.setData(0, QtCore.Qt.UserRole, i)
            pix = QtGui.QPixmap(16, 16)
            pix.fill(QtGui.QColor(color))
            item.setIcon(0, QtGui.QIcon(pix))
            item.setFont(0, QtGui.QFont("Segoe UI", 9))
            tip = role if role else "Station " + str(i+1)
            if i == 0 and not role: tip = tip + " (Reference)"
            tip = tip + chr(10) + str(len(sc.points)) + " points"
            if sc.path: tip = tip + chr(10) + str(sc.path)
            item.setToolTip(0, tip)
            if i == 0:
                item.setForeground(0, QtGui.QColor("#DC2626"))
                item.setFont(0, QtGui.QFont("Segoe UI", 9, QtGui.QFont.Bold))
        self._station_tree.expandAll()
        for i in range(self.right_tabs.count()):
            if self.right_tabs.tabText(i) == "Stations":
                self.right_tabs.setCurrentIndex(i)
                break


    def _render_all_stations(self, active_pts=None, title: str = None) -> None:
        """Render EVERY scan station as a coloured cloud (keeps T0+Tn both
        visible through preprocessing). The active scan uses ``active_pts`` (the
        just-processed cloud) when given, others use their raw points.
        """
        if self.plotter is None or not self.context.scans:
            return
        self.plotter.clear(); self.plotter.set_background("#FFFFFF")
        for i, sc in enumerate(self.context.scans):
            try:
                if i == self.context.active_index and active_pts is not None:
                    pts = validate_xyz(active_pts)
                else:
                    pts = validate_xyz(sc.points)
                n = len(pts)
                if n > DISPLAY_MAX_POINTS:
                    pts = pts[::int(np.ceil(n / DISPLAY_MAX_POINTS))]
                color = self._station_colors[i % len(self._station_colors)]
                self.plotter.add_mesh(make_vertex_cloud(pts), color=color,
                    style="points", point_size=2.2, render_points_as_spheres=False,
                    name=f"station_pts_{i}", reset_camera=False)
                center = pts.mean(axis=0)
                lbl = "S" + str(i + 1) + (" (Ref/T0)" if i == 0 else "")
                self.plotter.add_point_labels([center], [lbl], font_size=11,
                    text_color=color, bold=True, show_points=True,
                    point_color=color, point_size=12,
                    name=f"station_label_{i}", reset_camera=False)
            except Exception as e:
                self._log(f"Station {i+1} render: {e}")
        if title:
            try:
                self.plotter.add_text(title, position="upper_left", font_size=11,
                                      color="#111827", name="ttl")
            except Exception:
                pass
        self.plotter.add_axes(color="#111827")
        self.plotter.reset_camera(); self.plotter.render()

    def _render_station_markers(self) -> None:
        """Render colored sphere + label for each scan station on 3D viewport."""
        if self.plotter is None: return
        # Remove old markers
        for i in range(20):
            try: self.plotter.remove_actor(f"station_marker_{i}")
            except Exception: pass
            try: self.plotter.remove_actor(f"station_label_{i}")
            except Exception: pass
        for i, sc in enumerate(self.context.scans):
            try:
                pts = validate_xyz(sc.points)
                center = pts.mean(axis=0)
                color = self._station_colors[i % len(self._station_colors)]
                # Small dot marker at centroid
                label = "S" + str(i+1) + (" (Ref)" if i == 0 else "")
                self.plotter.add_point_labels(
                    [center], [label],
                    font_size=11, text_color=color,
                    bold=True, show_points=True,
                    point_color=color, point_size=12,
                    name="station_label_" + str(i),
                    reset_camera=False)
            except Exception as e:
                self._log(f"Station marker {i+1}: {e}")
        self.plotter.render()

    def _on_station_item_changed(self, item, column) -> None:
        """Handle checkbox toggle for station visibility."""
        idx = item.data(0, QtCore.Qt.UserRole)
        if idx is None: return
        if self.plotter is None: return
        is_visible = item.checkState(0) == QtCore.Qt.Checked
        try:
            if not is_visible:
                # Hide: remove point cloud actor
                self.plotter.remove_actor(f"station_pts_{idx}")
                self.plotter.remove_actor(f"station_marker_{idx}")
                self.plotter.remove_actor(f"station_label_{idx}")
                self.plotter.remove_actor(f"station_highlight_pts")
            else:
                # Show: re-render station
                sc = self.context.scans[idx]
                color = self._station_colors[idx % len(self._station_colors)]
                pts = validate_xyz(sc.points)
                step = max(1, len(pts) // 80000)
                mesh = make_vertex_cloud(pts[::step])
                self.plotter.add_mesh(mesh, color=color, style="points",
                    point_size=2.0, name=f"station_pts_{idx}", reset_camera=False)
                center = pts.mean(axis=0)
                label = "S" + str(idx+1) + (" (Ref)" if idx == 0 else "")
                self.plotter.add_point_labels(
                    [center], [label],
                    font_size=12, text_color=color,
                    bold=True, show_points=True,
                    point_color=color, point_size=14,
                    name=f"station_label_{idx}", reset_camera=False)
            self.plotter.render()
        except Exception as e:
            self._log(f"Visibility: {e}")

    def _on_station_tree_changed(self, current, previous) -> None:
        """Handle station tree selection change."""
        if current is None: return
        idx = current.data(0, QtCore.Qt.UserRole)
        if idx is None: return
        self._on_station_selected(idx)

    def _on_station_selected(self, idx: int) -> None:
        """Highlight selected station on 3D viewport."""
        if idx < 0 or idx >= len(self.context.scans): return
        if self.plotter is None: return
        sc = self.context.scans[idx]
        color = self._station_colors[idx % len(self._station_colors)]

        # Remove previous highlight
        try: self.plotter.remove_actor("station_highlight")
        except Exception: pass
        try: self.plotter.remove_actor("station_highlight_pts")
        except Exception: pass

        try:
            pts = validate_xyz(sc.points)
            center = pts.mean(axis=0)
            import pyvista as _pv

            # 1. Highlight point cloud with bright color
            step = max(1, len(pts) // 80000)
            mesh = make_vertex_cloud(pts[::step])
            self.plotter.add_mesh(mesh, color=color, style="points",
                point_size=3.5, opacity=0.9, name="station_highlight_pts",
                reset_camera=False)

            # 2. Large glowing sphere at centroid
            # No sphere - just highlight with point labels

            # 3. Camera focus on selected station
            self.plotter.camera.focal_point = center.tolist()
            self.plotter.camera.position = (
                center[0] + r * 8,
                center[1] + r * 8,
                center[2] + r * 6)
            self.plotter.render()

            # 4. Update status bar
            name = f"Station {idx+1}"
            if sc.path:
                import pathlib
                name += f" — {pathlib.Path(sc.path).name}"
            self.sb_msg.setText(_tr("Selected: {name}  |  {n} pts  |  Color: {color}", self.current_language).format(name=name, n=f"{len(pts):,}", color=color))
        except Exception as e:
            self._log(f"Station highlight error: {e}")

    def _station_context_menu(self, pos) -> None:
        """Right-click context menu for station tree (Faro SCENE style)."""
        item = self._station_tree.itemAt(pos)
        if item is None: return
        idx = item.data(0, QtCore.Qt.UserRole)
        if idx is None: return

        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
            QMenu{background:#FFFFFF;border:1px solid #E2E8F0;border-radius:4px;padding:4px;}
            QMenu::item{padding:6px 24px;color:#111827;font-size:9.5pt;}
            QMenu::item:selected{background:#DBEAFE;color:#1D4ED8;}
            QMenu::separator{height:1px;background:#E2E8F0;margin:4px 0;}
        """)

        # Visible toggle
        is_visible = item.checkState(0) == QtCore.Qt.Checked
        act_vis = menu.addAction("Hide" if is_visible else "Show")
        act_vis.triggered.connect(lambda: self._toggle_station_visibility(item, idx))

        menu.addSeparator()

        # Set as reference
        act_ref = menu.addAction("Set as Reference (S1)")
        act_ref.triggered.connect(lambda: self._set_station_reference(idx))

        # Focus camera
        act_focus = menu.addAction("Focus Camera Here")
        act_focus.triggered.connect(lambda: self._on_station_selected(idx))

        menu.addSeparator()

        # Rename
        act_rename = menu.addAction("Rename...")
        act_rename.triggered.connect(lambda: self._rename_station(item, idx))

        # Properties
        act_prop = menu.addAction("Properties...")
        act_prop.triggered.connect(lambda: self._show_station_properties(idx))

        menu.addSeparator()

        # Delete
        selected = self._selected_station_indices()
        multi_delete = len(selected) > 1 and idx in selected
        act_del = menu.addAction("Delete Selected Stations" if multi_delete else "Delete Station")
        act_del.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_TrashIcon))
        act_del.triggered.connect(lambda: self._delete_stations(selected) if multi_delete else self._delete_station(idx))

        menu.exec(self._station_tree.viewport().mapToGlobal(pos))

    def _toggle_station_visibility(self, item, idx: int) -> None:
        """Toggle station visibility on 3D viewport."""
        is_checked = item.checkState(0) == QtCore.Qt.Checked
        new_state = QtCore.Qt.Unchecked if is_checked else QtCore.Qt.Checked
        item.setCheckState(0, new_state)
        if self.plotter is None: return
        try:
            if new_state == QtCore.Qt.Unchecked:
                self.plotter.remove_actor(f"station_pts_{idx}")
                self.plotter.remove_actor(f"station_marker_{idx}")
                self.plotter.remove_actor(f"station_label_{idx}")
            else:
                sc = self.context.scans[idx]
                color = self._station_colors[idx % len(self._station_colors)]
                pts = validate_xyz(sc.points)
                step = max(1, len(pts) // 80000)
                mesh = make_vertex_cloud(pts[::step])
                self.plotter.add_mesh(mesh, color=color, style="points",
                    point_size=2.0, name=f"station_pts_{idx}", reset_camera=False)
            self.plotter.render()
        except Exception as e:
            self._log(f"Visibility toggle: {e}")

    def _set_station_reference(self, idx: int) -> None:
        """Move selected station to position 0 (reference)."""
        if idx == 0: self._log(_tr("Already reference station.", self.current_language)); return
        sc = self.context.scans.pop(idx)
        self.context.scans.insert(0, sc)
        self.context.active_index = 0
        self._refresh_station_list()
        self._render_station_markers()
        self._log(f"Station {idx+1} set as reference (S1).")

    def _rename_station(self, item, idx: int) -> None:
        """Rename station via input dialog."""
        sc = self.context.scans[idx]
        import pathlib
        current = pathlib.Path(sc.path).stem if sc.path else f"Station_{idx+1}"
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename Station", "Station name:", text=current)
        if ok and new_name.strip():
            if sc.path:
                sc.metadata["display_name"] = new_name.strip()
            item.setText(0, f"S{idx+1}  {new_name.strip()}")
            self._log(f"Station {idx+1} renamed to: {new_name.strip()}")

    def _show_station_properties(self, idx: int) -> None:
        """Show station properties dialog."""
        sc = self.context.scans[idx]
        import pathlib
        _lang = self.current_language
        lines = [
            _tr("Station: {n}", _lang).format(n=idx+1) + (_tr(" (Reference)", _lang) if idx == 0 else ""),
            _tr("File: {path}", _lang).format(path=sc.path or 'N/A'),
            _tr("Points: {n}", _lang).format(n=f"{len(sc.points):,}"),
            _tr("Has intensity: {v}", _lang).format(v=sc.intensity is not None),
            _tr("Has colors: {v}", _lang).format(v=sc.colors_raw is not None),
        ]
        if sc.metadata:
            for k, v in sc.metadata.items():
                lines.append(f"{k}: {v}")
        QtWidgets.QMessageBox.information(
            self, _tr("Station {n} Properties", _lang).format(n=idx+1),
            chr(10).join(lines))

    def _selected_station_indices(self) -> list[int]:
        """Return selected station indices from the station tree."""
        if not hasattr(self, "_station_tree"):
            return []
        indices = []
        for item in self._station_tree.selectedItems():
            idx = item.data(0, QtCore.Qt.UserRole)
            if isinstance(idx, int) and 0 <= idx < len(self.context.scans):
                indices.append(idx)
        return sorted(set(indices))

    def _delete_station(self, idx: int) -> None:
        """Delete a scan station."""
        selected = self._selected_station_indices()
        if len(selected) > 1 and idx in selected:
            self._delete_stations(selected)
            return
        _lang = self.current_language
        reply = QtWidgets.QMessageBox.question(
            self, _tr("Delete Station", _lang),
            _tr("Delete Station {n}?", _lang).format(n=idx+1),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply != QtWidgets.QMessageBox.Yes: return
        self.context.scans.pop(idx)
        if self.context.active_index >= len(self.context.scans):
            self.context.active_index = len(self.context.scans) - 1
        self._refresh_station_list()
        self._render_station_markers()
        self._log(f"Station {idx+1} deleted.")

    def _delete_selected_stations(self) -> None:
        """Delete all selected scan stations."""
        indices = self._selected_station_indices()
        if not indices:
            self._log("No scan stations selected.")
            return
        self._delete_stations(indices)

    def _delete_stations(self, indices: list[int]) -> None:
        """Delete multiple scan stations by index."""
        indices = sorted(set(i for i in indices if 0 <= i < len(self.context.scans)))
        if not indices:
            return
        _lang = self.current_language
        if len(indices) == 1:
            message = _tr("Delete Station {n}?", _lang).format(n=indices[0] + 1)
        else:
            labels = ", ".join("S" + str(i + 1) for i in indices)
            message = f"Delete {len(indices)} selected scan stations?\n{labels}"
        reply = QtWidgets.QMessageBox.question(
            self, _tr("Delete Station", _lang), message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply != QtWidgets.QMessageBox.Yes:
            return

        old_active = self.context.active_index
        for idx in sorted(indices, reverse=True):
            self.context.scans.pop(idx)

        if not self.context.scans:
            self.context.active_index = -1
            self.context.normalized_points = None
            self.context.registered_points = None
        elif old_active in indices:
            self.context.active_index = min(indices[0], len(self.context.scans) - 1)
        else:
            shift = sum(1 for idx in indices if idx < old_active)
            self.context.active_index = max(0, old_active - shift)

        self._refresh_station_list()
        self._render_station_markers()
        if len(indices) == 1:
            self._log(f"Station {indices[0]+1} deleted.")
        else:
            self._log(f"Deleted {len(indices)} scan stations: " + ", ".join("S" + str(i + 1) for i in indices))

    def _clear_all_stations(self) -> None:
        """Clear all loaded scan stations."""
        _lang = self.current_language
        reply = QtWidgets.QMessageBox.question(
            self, _tr("Clear All Stations", _lang),
            _tr("Remove all loaded scan stations?", _lang),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply != QtWidgets.QMessageBox.Yes: return
        self.context.scans.clear()
        self.context.active_index = -1
        self.context.normalized_points = None
        self.context.registered_points = None
        if hasattr(self, "_station_list"):
            self._station_list.clear()
        for i in range(20):
            try: self.plotter.remove_actor(f"station_marker_{i}")
            except Exception: pass
            try: self.plotter.remove_actor(f"station_label_{i}")
            except Exception: pass
        if self.plotter: self.plotter.render()
        self._log(_tr("All scan stations cleared.", self.current_language))

    def _highlight_section(self, idx: int) -> None:
        """Highlight current section plane on 3D viewport."""
        if self.plotter is None: return
        sections = self.context.sections
        frames   = self.context.frenet_frames
        cl       = self.context.centerline
        if not sections or not frames or cl is None: return
        if idx < 0 or idx >= len(sections): return

        sg  = sections[idx]
        fr  = frames[min(idx, len(frames) - 1)]
        C   = np.asarray(fr["center"], dtype=np.float64)
        N   = np.asarray(fr["N"],      dtype=np.float64)
        B   = np.asarray(fr["B"],      dtype=np.float64)

        # Remove previous section marker
        try: self.plotter.remove_actor("sec_plane"); self.plotter.remove_actor("sec_center")
        except Exception: pass

        # Update chainage ruler current-position indicator.
        if hasattr(self, "_chainage_ruler"):
            self._chainage_ruler.set_current(sg.chainage)

        # Draw section disc
        import pyvista as _pv
        radius = float(sg.radius_fit) if np.isfinite(sg.radius_fit) else 4.0
        disc = _pv.Disc(center=C, normal=fr["T"], inner=0, outer=radius * 1.05, r_res=1, c_res=60)
        self.plotter.add_mesh(disc, color="#F59E0B", opacity=0.35, style="surface",
                              name="sec_plane", reset_camera=False)

        # Draw center point
        sphere = _pv.Sphere(radius=radius * 0.04, center=C)
        self.plotter.add_mesh(sphere, color="#EF4444", name="sec_center", reset_camera=False)

        # Draw N and B axes
        for vec, col, nm in [(N, "#16A34A", "sec_N"), (B, "#2563EB", "sec_B")]:
            ln = np.vstack([C, C + vec * radius * 0.6])
            try: self.plotter.remove_actor(nm)
            except Exception: pass
            self.plotter.add_lines(ln, color=col, width=3, connected=True, name=nm)

        self.plotter.render()

    def _update_3d_status_hud(self, params: dict = None) -> None:
        """Overlay a compact status HUD on the 3D viewport.

        Shows overall tunnel health, key metric values, and section summary
        directly on the 3D plotter so the user never has to switch tabs to
        see the most important numbers.
        """
        if self.plotter is None:
            return
        # Remove only our own HUD actor. Use a single actor so it can never
        # collide with the step-title text ("ttl") at upper_left.
        try:
            self.plotter.remove_actor("_hud_panel")
        except Exception:
            pass
        if not getattr(self, "_show_viewport_text_overlays", False):
            try:
                self.plotter.render()
            except Exception:
                pass
            return

        from ..common import classify_parameter
        _SINGLE_SCAN = {"single_scan_global", "single_scan_per_section"}
        p = params or {}

        # ── Overall status ────────────────────────────────────────────────
        sections = self.context.sections or []
        ref_secs = getattr(self, "_section_ref_sections", []) or []
        n_sec = len(sections)

        if sections:
            sec_statuses = classify_sections(sections, ref_secs,
                epoch_sections=getattr(self, "_section_epoch_sections", None) or None)
            n_crit = sum(1 for s, _ in sec_statuses if s == "CRITICAL")
            n_caut = sum(1 for s, _ in sec_statuses if s == "CAUTION")
        else:
            n_crit = n_caut = 0

        # The whole panel is coloured by the overall severity so the status
        # line stands out without needing a separate (colliding) actor.
        lang = self.current_language
        if n_crit > 0:
            status_txt = _tr("[!] CRITICAL -- {n} critical section(s)", lang).format(n=n_crit)
            panel_color = "red"
        elif n_caut > 0:
            status_txt = _tr("[*] CAUTION -- {n} section(s) need monitoring", lang).format(n=n_caut)
            panel_color = "yellow"
        elif n_sec > 0:
            status_txt = _tr("[OK] SAFE -- {n} normal section(s)", lang).format(n=n_sec)
            panel_color = "#34D399"
        else:
            status_txt = _tr("No section data yet", lang)
            panel_color = "white"

        # Build one combined panel (status + metrics) at upper_right.
        lines = [status_txt, "-" * max(len(status_txt), 24)]

        ecc = p.get("eccentricity_mean_mm")
        if ecc is not None and np.isfinite(float(ecc)):
            st = classify_parameter("eccentricity_mean_mm", ecc)
            marker = "(!)" if st == "CRITICAL" else "(*)" if st == "CAUTION" else "   "
            lines.append(f"{marker} {_tr('Eccentricity', lang)}: {float(ecc):+.1f} mm")

        cr = p.get("crown_settlement_mm")
        cr_ref = p.get("settlement_reference", "")
        if cr is not None and np.isfinite(float(cr)) and cr_ref not in _SINGLE_SCAN:
            st = classify_parameter("crown_settlement_mm", cr)
            marker = "(!)" if st == "CRITICAL" else "(*)" if st == "CAUTION" else "   "
            lines.append(f"{marker} {_tr('Crown Settlement', lang)}: {float(cr):+.1f} mm")
        elif cr_ref in _SINGLE_SCAN:
            lines.append(f"   {_tr('Crown Settlement', lang)}: {_tr('Requires T0', lang)}")

        oval = p.get("ovality_mean_pct")
        if oval is not None and np.isfinite(float(oval)):
            st = classify_parameter("ovality_mean_pct", oval)
            marker = "(!)" if st == "CRITICAL" else "(*)" if st == "CAUTION" else "   "
            lines.append(f"{marker} {_tr('Ovality', lang)}: {float(oval):.3f} %")

        if n_sec:
            rmse = p.get("rmse_mm")
            rmse_txt = f"{rmse:.1f}" if isinstance(rmse, (int, float)) else "--"
            lines.append(f"   {_tr('Sections:', lang)} {n_sec}  |  RMSE: {rmse_txt}")

        try:
            self.plotter.add_text(
                "\n".join(lines),
                position="upper_right",
                font_size=9,
                color=panel_color,
                font="courier",
                name="_hud_panel",
                shadow=True,
            )
        except Exception:
            pass

        try:
            self.plotter.render()
        except Exception:
            pass

    def _slot_chainage_ruler_jump(self, idx: int) -> None:
        """Jump to section *idx* when user clicks on the chainage ruler."""
        sections = self.context.sections
        if not sections or idx < 0 or idx >= len(sections):
            return
        # Switch to the 2D cross-section tab so the section is visible.
        if hasattr(self, "_section_tab_idx"):
            self.right_tabs.setCurrentIndex(self._section_tab_idx)
        # Move the section slider/spinbox inside MatplotlibSectionWidget.
        if hasattr(self, "section_widget") and hasattr(self.section_widget, "set_section_index"):
            self.section_widget.set_section_index(idx)
        else:
            # Fallback: drive the existing highlight logic directly.
            self._highlight_section(idx)

    def _render_warning_markers(self, sections, ref_sections=None) -> None:
        """Place coloured flag-pole markers (sphere + stem + label) above each
        CRITICAL/CAUTION section on the 3D viewport.  Much more visible than
        thin discs: poles extend 1.5–2 m above the tunnel roof so they are
        easy to spot even from a distance.  Click on the legend to toggle."""
        if self.plotter is None: return
        frames = self.context.frenet_frames
        if not frames or not sections: return

        # Clear old markers (stems, balls, labels for both levels)
        for nm in ("warn_stem_crit", "warn_stem_caut",
                   "warn_ball_crit", "warn_ball_caut",
                   "warn_lbl_crit",  "warn_lbl_caut"):
            try: self.plotter.remove_actor(nm)
            except Exception: pass

        # Accumulate per-level geometry.
        # Use classify_sections() — same classifier as ruler/2D-track/dashboard.
        sec_statuses = classify_sections(sections, ref_sections or [],
            epoch_sections=getattr(self, "_section_epoch_sections", None) or None)

        data: dict = {
            "CRITICAL": {"stems": [], "tops": [], "labels": [], "color": "#DC2626"},
            "CAUTION":  {"stems": [], "tops": [], "labels": [], "color": "#D97706"},
        }

        for i, (status, issues) in enumerate(sec_statuses):
            if status not in data: continue
            sg = sections[i]
            fr = frames[min(i, len(frames) - 1)]
            C  = np.asarray(fr["center"], dtype=np.float64)
            B  = np.asarray(fr["B"],      dtype=np.float64)   # vertical-up axis
            r  = float(getattr(sg, "radius_fit", 4.0))
            if not np.isfinite(r) or r <= 0: r = 4.0

            # Pole top = roof of tunnel + 1.5 m headroom
            pole_top = C + B * (r + 1.5)

            d = data[status]
            d["stems"].extend([C, pole_top])
            d["tops"].append(pole_top)
            issue_txt = section_warning_text(issues, limit=2) if issues else status
            d["labels"].append(f"Ch {sg.chainage:.1f}m\n{issue_txt}")

        import pyvista as _pv

        def _build_lines(pts_flat: list) -> "_pv.PolyData":
            """Build a PolyData with one line segment per pair of points."""
            arr = np.array(pts_flat, dtype=np.float64).reshape(-1, 2, 3)
            n   = len(arr)
            all_pts = arr.reshape(-1, 3)
            cells   = np.array([[2, i*2, i*2+1] for i in range(n)], dtype=np.int64).ravel()
            pd = _pv.PolyData()
            pd.points = all_pts
            pd.lines  = cells
            return pd

        n_crit = len(data["CRITICAL"]["tops"])
        n_caut = len(data["CAUTION"]["tops"])

        for lvl, s_nm, b_nm, l_nm in [
            ("CRITICAL", "warn_stem_crit", "warn_ball_crit", "warn_lbl_crit"),
            ("CAUTION",  "warn_stem_caut", "warn_ball_caut", "warn_lbl_caut"),
        ]:
            d = data[lvl]
            if not d["tops"]: continue
            color = d["color"]

            # Stem lines — thick and solid
            stems_pd = _build_lines(d["stems"])
            self.plotter.add_mesh(stems_pd, color=color, line_width=5,
                                  name=s_nm, reset_camera=False)

            # Spheres at pole tips
            balls = _pv.MultiBlock(
                [_pv.Sphere(radius=0.45, center=t) for t in d["tops"]])
            self.plotter.add_mesh(balls.combine(), color=color,
                                  name=b_nm, reset_camera=False)

            # Text labels are optional; keep poles/spheres visible but hide
            # labels by default to avoid red/green text cluttering the viewport.
            if getattr(self, "_show_warning_text_labels", False):
                try:
                    self.plotter.add_point_labels(
                        np.array(d["tops"], dtype=np.float64), d["labels"],
                        font_size=10, text_color="white",
                        shape_color=color, shape_opacity=0.88,
                        show_points=False, always_visible=True,
                        name=l_nm, reset_camera=False)
                except Exception:
                    pass   # add_point_labels API varies; silently skip labels

        if n_crit or n_caut:
            self.plotter.render()
            self._log(
                f"3D warning flags: {n_crit} critical (red pole), "
                f"{n_caut} caution (amber pole) — visible above tunnel roof")

    def _render_bundle(self, b: PointCloudBundle, title: str) -> None:
        mesh = b.cloud or make_vertex_cloud(b.points, b.intensity, b.colors_raw); self._render_mesh(mesh, title)

    def _show_noise_panel(self) -> None:
        """Show interactive noise review panel above viewport."""
        if self._noise_panel:
            self._noise_panel.deleteLater()
        panel = QtWidgets.QFrame()
        panel.setStyleSheet(
            "QFrame{background:#FEF3C7;border:2px solid #D97706;"
            "border-radius:8px;padding:4px;}")
        lay = QtWidgets.QHBoxLayout(panel)
        lay.setContentsMargins(10, 6, 10, 6); lay.setSpacing(8)
        lbl = QtWidgets.QLabel(
            f"Noise review: {len(self._noise_pts):,} noise points (red) | "
            f"{len(self._kept_pts):,} kept (blue)")
        lbl.setStyleSheet("color:#92400E;font-weight:700;font-size:9.5pt;")
        btn_style_green = (
            "QPushButton{background:#047857;color:white;border-radius:5px;"
            "padding:5px 14px;font-weight:700;border:none;}"
            "QPushButton:hover{background:#065F46;}")
        btn_style_red = (
            "QPushButton{background:#DC2626;color:white;border-radius:5px;"
            "padding:5px 14px;font-weight:700;border:none;}"
            "QPushButton:hover{background:#B91C1C;}")
        btn_style_blue = (
            "QPushButton{background:#1D4ED8;color:white;border-radius:5px;"
            "padding:5px 14px;font-weight:700;border:none;}"
            "QPushButton:hover{background:#1E40AF;}")
        btn_style_gray = (
            "QPushButton{background:#64748B;color:white;border-radius:5px;"
            "padding:5px 14px;font-weight:700;border:none;}"
            "QPushButton:hover{background:#475569;}")
        btn_confirm = QtWidgets.QPushButton("✓ Confirm Remove")
        btn_add     = QtWidgets.QPushButton("+ Select More Noise")
        btn_restore = QtWidgets.QPushButton("↩ Restore Point")
        btn_cancel  = QtWidgets.QPushButton("✗ Keep All")
        btn_confirm.setStyleSheet(btn_style_green)
        btn_add.setStyleSheet(btn_style_red)
        btn_restore.setStyleSheet(btn_style_blue)
        btn_cancel.setStyleSheet(btn_style_gray)
        btn_confirm.setToolTip("Remove all red noise points and keep blue points")
        btn_add.setToolTip("Click points in 3D viewport to mark as noise")
        btn_restore.setToolTip("Click red points to restore them")
        btn_cancel.setToolTip("Cancel — keep all points including noise")
        btn_confirm.clicked.connect(self._confirm_noise_removal)
        btn_add.clicked.connect(self._start_add_noise_selection)
        btn_restore.clicked.connect(self._start_restore_selection)
        btn_cancel.clicked.connect(self._cancel_noise_removal)
        lay.addWidget(lbl, 1)
        # Manual noise picking (click points to mark/restore) is an advanced
        # action; hide it in core mode and keep the automatic confirm/cancel.
        if not CORE_FEATURES_ONLY:
            lay.addWidget(btn_add)
            lay.addWidget(btn_restore)
        else:
            btn_add.hide(); btn_restore.hide()
        lay.addWidget(btn_confirm)
        lay.addWidget(btn_cancel)
        self._noise_panel = panel
        # Insert panel above viewport
        self.vp_layout.insertWidget(0, panel)

    def _confirm_noise_removal(self) -> None:
        """Apply noise removal — keep only kept_pts."""
        if self._kept_pts is None: return
        self.context.normalized_points = self._kept_pts
        self._render_pts(self._kept_pts, "2.2 Noise Removed — Clean Point Cloud", "#0EA5E9")
        self.pt_label.setText(f"Points: {len(self._kept_pts):,}")
        self.sb_pts.setText(f"Points: {len(self._kept_pts):,}")
        self._log(f"Noise removal confirmed: {len(self._kept_pts):,} clean points retained.")
        if self._noise_pts is not None:
            self._log(f"Removed: {len(self._noise_pts):,} noise points.")
        self._noise_pts = None
        self._hide_noise_panel()

    def _cancel_noise_removal(self) -> None:
        """Cancel — keep all points including noise."""
        if self.context.active_scan:
            all_pts = validate_xyz(self.context.active_scan.points)
            self.context.normalized_points = all_pts
            self._render_pts(all_pts, "2.2 Cancelled — All Points Kept", "#64748B")
            self.pt_label.setText(f"Points: {len(all_pts):,}")
            self.sb_pts.setText(f"Points: {len(all_pts):,}")
        self._log(_tr("Noise removal cancelled — all points kept.", self.current_language))
        self._noise_pts = None; self._kept_pts = None
        self._hide_noise_panel()

    def _start_add_noise_selection(self) -> None:
        """Enable picking mode — click points to mark as noise."""
        if self.plotter is None: return
        self._log(_tr("Click on points in 3D viewport to mark as noise. Click again to deselect.", self.current_language))
        try:
            self.plotter.enable_point_picking(
                callback=self._on_pick_noise,
                show_message=True,
                color="#DC2626",
                point_size=10,
                use_picker=True,
                pickable_window=False)
            self.sb_msg.setText(_tr("Pick mode: click points to mark as noise. Press Q to exit.", self.current_language))
        except Exception as e:
            self._log(f"Pick mode: {e}")

    def _start_restore_selection(self) -> None:
        """Enable picking mode — click red points to restore them."""
        if self.plotter is None: return
        self._log(_tr("Click on red noise points to restore them.", self.current_language))
        try:
            self.plotter.enable_point_picking(
                callback=self._on_pick_restore,
                show_message=True,
                color="#2563EB",
                point_size=10,
                use_picker=True,
                pickable_window=False)
            self.sb_msg.setText(_tr("Pick mode: click red points to restore. Press Q to exit.", self.current_language))
        except Exception as e:
            self._log(f"Pick mode: {e}")

    def _on_pick_noise(self, point) -> None:
        """Mark picked point as noise."""
        if self._kept_pts is None or point is None: return
        pt = np.asarray(point, dtype=np.float64)
        dists = np.linalg.norm(self._kept_pts - pt, axis=1)
        idx = int(np.argmin(dists))
        if dists[idx] > 0.5: return  # too far
        new_noise = self._kept_pts[idx:idx+1]
        self._kept_pts  = np.delete(self._kept_pts, idx, axis=0)
        self._noise_pts = np.vstack([self._noise_pts, new_noise]) if self._noise_pts is not None and len(self._noise_pts) else new_noise
        self._render_filter_result(self._kept_pts, self._noise_pts,
                                    "2.2 SOR — Review noise (red) before confirming")
        # Update panel label
        if self._noise_panel:
            lbl = self._noise_panel.findChild(QtWidgets.QLabel)
            if lbl:
                lbl.setText(f"Noise review: {len(self._noise_pts):,} noise (red) | {len(self._kept_pts):,} kept (blue)")

    def _on_pick_restore(self, point) -> None:
        """Restore picked noise point back to kept."""
        if self._noise_pts is None or point is None: return
        pt = np.asarray(point, dtype=np.float64)
        dists = np.linalg.norm(self._noise_pts - pt, axis=1)
        idx = int(np.argmin(dists))
        if dists[idx] > 0.5: return
        restored = self._noise_pts[idx:idx+1]
        self._noise_pts = np.delete(self._noise_pts, idx, axis=0)
        self._kept_pts  = np.vstack([self._kept_pts, restored]) if self._kept_pts is not None and len(self._kept_pts) else restored
        self._render_filter_result(self._kept_pts, self._noise_pts,
                                    "2.2 SOR — Review noise (red) before confirming")
        if self._noise_panel:
            lbl = self._noise_panel.findChild(QtWidgets.QLabel)
            if lbl:
                lbl.setText(f"Noise review: {len(self._noise_pts):,} noise (red) | {len(self._kept_pts):,} kept (blue)")

    def _hide_noise_panel(self) -> None:
        if self._noise_panel:
            self._noise_panel.deleteLater()
            self._noise_panel = None

    def _render_filter_result(self, kept_pts: np.ndarray, removed_pts: np.ndarray, title: str) -> None:
        if self.plotter is None:
            return
        self._clear_noise_overlay()
        self.plotter.clear(); self.plotter.set_background("#FFFFFF")
        self._noise_actor = None
        if len(kept_pts):
            kept_d, _ = self._decimate_for_display(kept_pts)
            kept = make_vertex_cloud(kept_d)
            self.plotter.add_mesh(kept, color="#0EA5E9", style="points", point_size=2.4,
                                  render_points_as_spheres=False, reset_camera=True)
        if len(removed_pts):
            # Spheres are expensive; decimate the red overlay too when huge.
            removed_d, _ = self._decimate_for_display(removed_pts)
            removed = make_vertex_cloud(removed_d)
            self._noise_actor = self.plotter.add_mesh(
                removed, color="#DC2626", style="points", point_size=5.0,
                render_points_as_spheres=True, reset_camera=False, name="noise_pts")
            self._noise_actor.SetVisibility(self._noise_visible)
            self.plotter.add_text(f"Removed noise/outliers: {len(removed_pts):,} red points",
                                  position="lower_left", font_size=10, color="#DC2626", name="removed")
            self._add_noise_toggle_widget()
        self.plotter.add_text(title + " | kept=blue, removed=red", position="upper_left",
                              font_size=11, color="#111827", name="ttl")
        self.plotter.add_axes(color="#111827")
        self.plotter.show_bounds(color="#94A3B8", grid="front", location="outer", font_size=8)
        self.plotter.camera.parallel_projection = True
        self.plotter.reset_camera(); self.plotter.render()

    def _clear_noise_overlay(self) -> None:
        """Remove the noise toggle checkbox/label and actor when leaving a
        filter view (plotter.clear() does not drop button widgets)."""
        self._noise_actor = None
        if self.plotter is None:
            return
        try:
            self.plotter.clear_button_widgets()
        except Exception:
            pass
        try:
            self.plotter.remove_actor("noise_toggle_lbl")
        except Exception:
            pass

    def _add_noise_toggle_widget(self) -> None:
        """Add an in-viewport checkbox to show/hide the red noise points."""
        if self.plotter is None:
            return
        try:
            self.plotter.add_checkbox_button_widget(
                self._toggle_noise_visibility,
                value=self._noise_visible,
                position=(10.0, 10.0), size=28,
                color_on="#DC2626", color_off="#94A3B8", border_size=2)
            self.plotter.add_text(_tr("Show noise", self.current_language), position=(44, 12),
                                  font_size=9, color="#111827", name="noise_toggle_lbl")
        except Exception as exc:
            self._log(f"Noise toggle widget unavailable: {exc}")

    def _toggle_noise_visibility(self, state: bool) -> None:
        """Show/hide red noise points without re-rendering the whole scene."""
        self._noise_visible = bool(state)
        if self._noise_actor is not None:
            try:
                self._noise_actor.SetVisibility(self._noise_visible)
                self.plotter.render()
            except Exception:
                pass
        self._log(_tr("Noise points shown.", self.current_language) if self._noise_visible
                  else _tr("Noise points hidden.", self.current_language))

    def _render_pts(self, pts: np.ndarray, title: str, color: str = "#2563EB") -> None:
        self._render_mesh(make_vertex_cloud(pts), title, color=color)

    @staticmethod
    def _decimate_for_display(pts, scalars=None):
        """Stride pts (and matching scalars) down to DISPLAY_MAX_POINTS.

        Used by the scalar heatmap renderers so a multi-million-point cloud
        does not stall VTK. Returns (pts_d, scalars_d) with scalars kept aligned
        (or None when not provided / length mismatch).
        """
        pts = np.asarray(pts, dtype=np.float64)
        n = len(pts)
        if scalars is not None:
            scalars = np.asarray(scalars)
            if len(scalars) != n:
                scalars = None
        if n > DISPLAY_MAX_POINTS:
            step = int(np.ceil(n / DISPLAY_MAX_POINTS))
            pts = pts[::step]
            if scalars is not None:
                scalars = scalars[::step]
        return pts, scalars
    def _render_mesh(self, mesh: "pv.PolyData", title: str, color: str = None) -> None:
        if self.plotter is None: return
        self._clear_noise_overlay()
        # Decimate for display only (see DISPLAY_MAX_POINTS); analysis is
        # unaffected. Strided so the subsample stays spatially representative.
        pts_all = np.asarray(mesh.points, dtype=np.float64)
        rgb = mesh.get_array("RGB") if "RGB" in mesh.array_names else None
        inten = mesh.get_array("Intensity") if "Intensity" in mesh.array_names else None
        n = len(pts_all)
        if n > DISPLAY_MAX_POINTS:
            step = int(np.ceil(n / DISPLAY_MAX_POINTS))
            pts_all = pts_all[::step]
            if rgb is not None: rgb = rgb[::step]
            if inten is not None: inten = inten[::step]
        clean = make_vertex_cloud(pts_all, intensity=inten, colors_raw=rgb.astype(np.float64)/255.0 if rgb is not None else None)
        self.plotter.clear(); self.plotter.set_background("#FFFFFF")
        kw = dict(style="points", point_size=2.4, render_points_as_spheres=False, reset_camera=True)
        if "RGB" in clean.array_names and color is None: self.plotter.add_mesh(clean, scalars="RGB", rgb=True, **kw)
        elif "Intensity" in clean.array_names and color is None: self.plotter.add_mesh(clean, scalars="Intensity", cmap="viridis", **kw)
        else: self.plotter.add_mesh(clean, color=color or "#1D4ED8", **kw)
        if getattr(self, "_show_viewport_text_overlays", False):
            self.plotter.add_text(title, position="upper_left", font_size=11, color="#111827", name="ttl")
            if len(self.context.scans) >= 2:
                times_hint = _tr("Showing Tn (active) | T0 loaded as reference", self.current_language)
                self.plotter.add_text(times_hint, position="upper_edge", font_size=9, color="#6366F1", name="times_hint")
        self.plotter.add_axes(color="#111827"); self.plotter.show_bounds(color="#94A3B8", grid="front", location="outer", font_size=8)
        self.plotter.camera.parallel_projection = True; self.plotter.reset_camera(); self.plotter.render()

    def _render_cl(self, cl: np.ndarray, fr: List[Dict]) -> None:
        pts = self.context.working_points
        if pts is not None: self._render_pts(pts, "4.x Centerline Frame Calibration", "#CBD5E1")
        if self.plotter is None: return
        self.plotter.add_lines(cl, color="#E11D48", width=5, connected=True, name="cl")
        skip = max(1, len(fr) // 18)
        for i, frame in enumerate(fr[::skip]):
            c = frame["center"]
            for k, col in (("T", "#2563EB"), ("N", "#16A34A"), ("B", "#EA580C")):
                ln = np.vstack([c, c + frame[k] * 0.6]); self.plotter.add_lines(ln, color=col, width=2, connected=True, name=f"f{k}{i}")
        self.plotter.render()

    def _render_heatmap(self, pts: np.ndarray, sc: np.ndarray) -> None:
        pts, sc = self._decimate_for_display(pts, sc)
        mesh = make_vertex_cloud(pts)
        if sc is not None and len(sc) == mesh.n_points: mesh["Delta_mm"] = sc
        if self.plotter is None: return
        self._clear_noise_overlay()
        self.plotter.clear(); self.plotter.set_background("#FFFFFF")
        self.plotter.add_mesh(mesh, scalars="Delta_mm", cmap="turbo", style="points", point_size=2.8, render_points_as_spheres=False, reset_camera=True, scalar_bar_args={"title": "Delta (mm)"})
        self.plotter.add_text("Heatmap - Vertical Displacement (Z-Axis Deviation)", position="upper_left", font_size=11, color="#111827", name="ttl")
        self.plotter.add_axes(color="#111827"); self.plotter.reset_camera(); self.plotter.render()

    def _hdr(self, title: str, desc: str) -> None:
        self._hdr_title_src = title; self._hdr_desc_src = desc
        lang = self.current_language
        self.task_title.setText(_tr(title, lang)); self.task_desc.setText(_tr(desc, lang))

    # Group extracted-parameter keys by theme for display.
    _PARAM_GROUPS = [
        ("Deformation", ["crown_settlement_mm", "crown_settlement_max_mm",
                         "lateral_convergence_mm", "lateral_convergence_max_mm",
                         "polar_max_outward_mm", "polar_max_inward_mm"]),
        ("Geometry", ["ovality_mean_pct", "ovality_max_pct",
                      "eccentricity_mean_mm", "eccentricity_max_mm", "eccentricity_min_mm",
                      "crown_B_mean_m", "total_height_mm", "width_Tn_m", "width_Tn_mean_m"]),
        ("Context", ["reference", "settlement_reference", "convergence_reference", "eccentricity_reference", "n_sections"]),
    ]

    def _grouped_params(self, params):
        """Yield (group_name, [(key, value), ...]) in theme order, then extras."""
        seen = set()
        for name, keys in self._PARAM_GROUPS:
            rows = [(k, params[k]) for k in keys if k in params]
            seen.update(k for k in keys if k in params)
            if rows:
                yield name, rows
        extras = [(k, v) for k, v in params.items() if k not in seen]
        if extras:
            yield "Other", extras

    @staticmethod
    def _split_value_unit(text):
        """Split "12.34 mm" -> ("12.34", "mm"); strings without a unit return
        (text, ""). Keeps the value column right-alignable and the unit separate."""
        parts = str(text).split(' ', 1)
        if len(parts) == 2 and parts[1] in ('mm', 'm', '%', '\u00b0'):
            return parts[0], parts[1]
        return str(text), ''

    def _fill_param_table(self, params):
        """Populate the Parameters tab: grouped rows, unit-aware, status-coloured."""
        tbl = self.param_table
        tbl.setRowCount(0)
        status_fill = {
            "OK": QtGui.QColor(_GRN), "CAUTION": QtGui.QColor(_YEL),
            "CRITICAL": QtGui.QColor(_RED),
        }
        for group, rows in self._grouped_params(params):
            # Group header row (spanning).
            r = tbl.rowCount(); tbl.insertRow(r)
            hdr = QtWidgets.QTableWidgetItem(group)
            f = hdr.font(); f.setBold(True); hdr.setFont(f)
            hdr.setBackground(QtGui.QColor(_GRID) if '_GRID' in globals() else QtGui.QColor('#E5E7EB'))
            tbl.setItem(r, 0, hdr)
            tbl.setSpan(r, 0, 1, 4)
            for k, v in rows:
                label, text, status = format_parameter(k, v)
                value, unit = self._split_value_unit(text)
                r = tbl.rowCount(); tbl.insertRow(r)
                tbl.setItem(r, 0, QtWidgets.QTableWidgetItem(label))
                vi = QtWidgets.QTableWidgetItem(value)
                vi.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                tbl.setItem(r, 1, vi)
                tbl.setItem(r, 2, QtWidgets.QTableWidgetItem(unit))
                si = QtWidgets.QTableWidgetItem(status)
                si.setTextAlignment(QtCore.Qt.AlignCenter)
                if status in status_fill:
                    si.setForeground(QtGui.QColor('#FFFFFF'))
                    si.setBackground(status_fill[status])
                tbl.setItem(r, 3, si)
        tbl.resizeColumnsToContents()
    @staticmethod
    def _extract_denoise_counts(stats):
        """Pull integer component counts from an auto_denoise/semantic stats
        dict (cable/light/person/wall-cable/radial + totals), dropping the bulky
        noise_pts array, so they can be stored on the context and exported.
        """
        keys = ("n_raw", "n_clean", "n_removed", "n_cable", "n_light",
                "n_person", "n_wall_cable", "n_radial")
        out = {}
        for k in keys:
            v = stats.get(k)
            if isinstance(v, (int, float)):
                out[k] = int(v)
        return out
    def _show_params(self, params: Dict[str, float]) -> None:
        # Text log: grouped, unit-aware, with status flags (handles strings).
        self.results_text.appendPlainText("--- Parameters Extracted ---")
        for group, rows in self._grouped_params(params):
            self.results_text.appendPlainText(f"[{group}]")
            for k, v in rows:
                label, text, status = format_parameter(k, v)
                tag = f"  [{status}]" if status and status != "OK" else ""
                self.results_text.appendPlainText(f"  {label}: {text}{tag}")
        self.results_text.appendPlainText("----------------------------")
        self._fill_param_table(params)
        # Push to Summary Dashboard — also flag single-scan keys so the dashboard
        # can show "Cần T0" instead of a misleading absolute-geometry value.
        self.dashboard_widget.update_params(params)
        _SINGLE_SCAN = {"single_scan_global", "single_scan_per_section"}
        _single_keys: set = set()
        if params.get("settlement_reference")  in _SINGLE_SCAN:
            _single_keys.update({"crown_settlement_mm", "crown_settlement_max_mm"})
        if params.get("convergence_reference") in _SINGLE_SCAN:
            _single_keys.update({"lateral_convergence_mm", "lateral_convergence_max_mm"})
        self.dashboard_widget.set_reference_flags(_single_keys)
        # Switch to the combined Mặt Cắt + Tổng Quan tab.
        self.right_tabs.setCurrentIndex(self._dashboard_tab_idx)
        # Update 3D HUD with the new status information.
        self._update_3d_status_hud(params)

    def _update_meta(self, b: PointCloudBundle) -> None:
        rows = list(b.metadata.items()); self.meta_table.setRowCount(len(rows))
        for i, (k, v) in enumerate(rows):
            self.meta_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(k))); self.meta_table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(v)))
        self.right_tabs.setCurrentIndex(1)

    def _log(self, msg: str) -> None:
        self.results_text.appendPlainText(str(msg))

    @QtCore.Slot(str)
    def change_language(self, language_code: str) -> None:
        """Switch UI language, sync the button and persist the choice."""
        if language_code not in get_available_languages():
            return
        self.current_language = language_code
        if self.language_switcher.get_current_language() != language_code:
            self.language_switcher.set_language(language_code)
        self._retranslate_v4()
        self.settings.setValue("ui/language", language_code)

    def _retranslate_v4(self) -> None:
        """Apply the active language to the main static UI (English fallback)."""
        lang = self.current_language
        step_word = _tr("Step", lang)
        self.setWindowTitle(_tr(self._window_title_src, lang))

        # Sidebar header
        self._title_lbl.setText(_tr("TUNNEL ANALYSIS", lang))
        self._subtitle_lbl.setText(_tr("v4.0 r1 - CBNU Smart Structure Lab", lang))
        self._pf_frame.setTitle(_tr("Tunnel Profile Type", lang))
        self._vl_frame.setTitle(_tr("Vehicle Clearance Limit (m)", lang))
        self._lbl_vl_w.setText(_tr("Half clear width W:", lang))
        self._lbl_vl_h.setText(_tr("Clear height H:", lang))
        self._lbl_vl_r.setText(_tr("Circular clearance radius R:", lang))
        self._sc_frame.setTitle(_tr("Analysis Resolution", lang))
        self._lbl_res_mode.setText(_tr("Resolution mode:", lang))
        self._lbl_sections.setText(_tr("Number of sections:", lang))
        self._lbl_spacing.setText(_tr("Section spacing:", lang))
        self._cmb_res_mode.setItemText(0, _tr("By count", lang))
        self._cmb_res_mode.setItemText(1, _tr("By spacing (m)", lang))
        self._sp_sections.setToolTip(_tr("Number of cross-sections along the tunnel (centerline control points). Higher = finer detail, slower.", lang))
        self._sp_spacing.setToolTip(_tr("Target axial distance between cross-sections. The section count is derived from the measured tunnel length.", lang))
        self._auto_btn.setText(_tr("AUTO PIPELINE  (1-click full analysis)", lang))
        self._reset_btn.setText(_tr("Reset Pipeline", lang))
        if hasattr(self, "_advanced_buttons_cb"):
            self._advanced_buttons_cb.setText(_tr("Show Advanced", lang))
            self._advanced_buttons_cb.setToolTip(_tr("Show advanced/debug buttons after restarting the tool.", lang))

        if hasattr(self, "_station_title_lbl"):
            self._station_title_lbl.setText(_tr("Structure", lang))
            self._btn_add_station.setToolTip(_tr("Add scan station", lang))
            if hasattr(self, "_btn_delete_selected_stations"):
                self._btn_delete_selected_stations.setText(_tr("Delete Selected", lang))
            self._btn_clear_stations.setText(_tr("Clear All", lang))
        if hasattr(self, "_target_title_lbl"):
            self._target_title_lbl.setText(_tr("Target Manager", lang))
            self._btn_target_detect.setText(_tr("Auto Detect", lang))
            self._btn_target_manual.setText("+ " + _tr("Manual", lang))
            self._btn_target_match.setText(_tr("Auto Match", lang))
            self._btn_target_register.setText(_tr("Register", lang))
            if self._tgt_status.text() in ("No targets detected.", _tr("No targets detected.", "vi"), _tr("No targets detected.", "ko")):
                self._tgt_status.setText(_tr("No targets detected.", lang))

        # Collapsible section titles + sub-button labels
        for sec in self._sections:
            sec.set_translation(_tr(sec.title_source, lang), step_word)
            sec.retranslate_buttons(lambda t: _tr(t, lang))

        if hasattr(self, "section_widget") and hasattr(self.section_widget, "retranslate"):
            self.section_widget.retranslate(lambda t: _tr(t, lang))
        if hasattr(self, "dashboard_widget") and hasattr(self.dashboard_widget, "retranslate"):
            self.dashboard_widget.retranslate(lambda t: _tr(t, lang))
        if hasattr(self, "polar_plot") and hasattr(self.polar_plot, "retranslate"):
            self.polar_plot.retranslate(lambda t: _tr(t, lang))
        if hasattr(self, "ts_plot") and hasattr(self.ts_plot, "retranslate"):
            self.ts_plot.retranslate(lambda t: _tr(t, lang))

        # Header task title/description (retranslate from stored English source)
        self.task_title.setText(_tr(self._hdr_title_src, lang))
        self.task_desc.setText(_tr(self._hdr_desc_src, lang))

        # Right-panel tab titles
        tab_titles = ["Results Log", "Summary Dashboard", "Parameters",
                      "Scan Database", "Stations", "Targets",
                      "Time-Series Plot", "2D Cross-Section", "Polar Deformation",
                      "AI Engineering Assistant"]
        for i in range(self.right_tabs.count()):
            cur = self.right_tabs.tabText(i)
            for src_title in tab_titles:
                if cur == src_title or cur in (_tr(src_title, "vi"), _tr(src_title, "ko")):
                    self.right_tabs.setTabText(i, _tr(src_title, lang))
                    break

        self.param_table.setHorizontalHeaderLabels([
            _tr("Parameter", lang), _tr("Value", lang),
            _tr("Unit", lang), _tr("Status", lang)])
        self.meta_table.setHorizontalHeaderLabels([
            _tr("Property", lang), _tr("Value", lang)])
        if hasattr(self, "_target_table") and hasattr(self, "_target_table_headers_src"):
            self._target_table.setHorizontalHeaderLabels(
                [_tr(h, lang) for h in self._target_table_headers_src])

        if hasattr(self, "sb_pts") and self.sb_pts.text() in ("Points: --", _tr("Points: --", "vi"), _tr("Points: --", "ko")):
            self.sb_pts.setText(_tr("Points: --", lang))
        if hasattr(self, "sb_rmse") and self.sb_rmse.text() in ("RMSE: --", _tr("RMSE: --", "vi"), _tr("RMSE: --", "ko")):
            self.sb_rmse.setText(_tr("RMSE: --", lang))

        # AI assistant panel
        self.ai_prompt.setPlaceholderText(_tr("Enter a structural engineering question for the local AI assistant (Llama 3)...", lang))
        self.ai_send.setText(_tr("Query AI Assistant", lang))
        self._ai_query_lbl.setText(_tr("Engineering query:", lang))
        self._ai_report_lbl.setText(_tr("AI analysis report:", lang))

    def _apply_theme(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #F1F5F9; color: #111827; font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; }
            #Sidebar { background: #FFFFFF; border-right-width: 1px; border-right-style: solid; border-right-color: #E2E8F0; }
            #ProductTitle { color: #0F4C81; font-size: 15pt; font-weight: 800; letter-spacing: 0.5px; }
            #LabSubtitle  { color: #64748B; font-size: 9pt; padding-bottom: 4px; }
            #Separator    { color: #E2E8F0; margin: 4px 0; }
            QScrollArea   { background: transparent; border: none; }
            QToolButton#SectionToggle { background: #EEF4FA; border: 1px solid #D1DCEB; border-radius: 6px; padding: 6px 10px; font-weight: 600; color: #1E3A5F; text-align: left; }
            QToolButton#SectionToggle:hover   { background: #DBEAFE; border-color: #3B82F6; }
            QToolButton#SectionToggle:checked { background: #BFDBFE; border-color: #1D4ED8; }
            QWidget#SectionContent { background: #F8FAFC; border-left-width: 2px; border-left-style: solid; border-left-color: #BFDBFE; margin-left: 10px; }
            QPushButton#SubButton { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 5px; padding: 6px 10px; text-align: left; color: #334155; font-size: 9.5pt; }
            QPushButton#SubButton:hover    { background: #EFF6FF; border-color: #3B82F6; color: #1D4ED8; }
            QPushButton#SubButton:disabled { background: #F1F5F9; color: #94A3B8; border-color: #E2E8F0; }
            QPushButton { background: #EEF4FA; border: 1px solid #CBD6E2; border-radius: 6px; padding: 8px 12px; font-weight: 600; }
            QPushButton:hover { background: #DBEAFE; border-color: #2563EB; }
            #Header, #ViewportFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }
            #TaskTitle       { color: #0F172A; font-size: 14pt; font-weight: 700; }
            #TaskDescription { color: #475569; }
            QTabWidget::pane, QPlainTextEdit, QTableWidget { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 4px; }
            QTabBar::tab { background: #E2E8F0; color: #1E293B; padding: 7px 14px; margin-right: 2px;
                           border: 1px solid #CBD5E1; border-top-left-radius: 6px; border-top-right-radius: 6px;
                           font-weight: 600; }
            QTabBar::tab:selected { background: #FFFFFF; color: #0F4C81; border-bottom-color: #FFFFFF; }
            QTabBar::tab:hover:!selected { background: #DBEAFE; color: #1D4ED8; }
            QTabBar::scroller { width: 18px; }
            QHeaderView::section { background: #EEF4FA; color: #1E293B; border: 1px solid #E2E8F0; padding: 5px; }
            QProgressBar { background: #EEF4FA; border: 1px solid #CBD5E1; border-radius: 4px; text-align: center; min-width: 140px; }
            QProgressBar::chunk { background: #2563EB; border-radius: 4px; }
            QDoubleSpinBox, QComboBox { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px; color: #111827; }
        """)


    def closeEvent(self, event) -> None:
        """Clean up timers and threads before closing."""
        try:
            self._close_task_dialog()
        except Exception: pass
        try:
            self.settings.setValue("ui/language", self.current_language)
        except Exception: pass
        try:
            if hasattr(self, "_anim_timer") and self.section_widget:
                self.section_widget._anim_timer.stop()
        except Exception: pass
        try:
            if self.worker_thread and self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait(3000)
        except Exception: pass
        # Finalize the embedded VTK/pyvistaqt interactor BEFORE the Qt event
        # loop tears down, otherwise its internal render timer outlives the
        # event dispatcher ("QObject::startTimer: ... already been destroyed").
        try:
            if self.plotter is not None:
                try:
                    self.plotter.disable_picking()
                except Exception:
                    pass
                try:
                    self.plotter.clear_button_widgets()
                except Exception:
                    pass
                self.plotter.close()
                self.plotter = None
        except Exception: pass
        event.accept()


def main() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Tunnel Analysis v4.0")
    win = TunnelAnalysisWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
