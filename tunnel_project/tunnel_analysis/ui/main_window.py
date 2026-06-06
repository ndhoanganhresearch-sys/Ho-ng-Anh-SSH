from ..common import *
from ..models import PointCloudBundle, PipelineContext
from ..io_layer import BaseLayer
from ..preprocessing import PreprocessingLayer
from ..registration import RegistrationLayer
from ..geometry import GeometricLayer
from ..segmentation import SegmentationLayer
from ..parameters import ParameterExtractionLayer
from ..timeseries import TimeSeriesLayer
from ..digital_twin import DigitalTwinAILayer
from ..worker import PipelineWorker
from ..exporter import TunnelExporter
from ..pdf_reporter import TunnelPDFReporter
from ..ifc_exporter import TunnelIFCExporter
from ..target_detector import TargetDetector, Target
from ..rag_ai import TunnelRAGAssistant
from .widgets import (CollapsibleSection, MatplotlibSectionWidget, PolarDeformationPlotWidget,
                      LinePlotWidget, SummaryDashboardWidget,
                      section_warning_status, section_warning_text)
from .i18n_v4 import tr as _tr
from translations import get_available_languages
from language_switcher import LanguageSwitcher

# -- GUI feature scope -------------------------------------------------------
# When True, the sidebar and output tabs expose only the core end-to-end
# tunnel deformation workflow. Experimental "(PDF 3.x)" variants, redundant
# duplicate methods and advanced diagnostics are hidden (not deleted) to keep
# the interface focused. Set to False to restore the full feature set.
CORE_FEATURES_ONLY = True
# Max points sent to the 3D viewport in one mesh. Rendering every point of a
# multi-million-point tunnel scan stalls VTK (the KeyboardInterrupt seen during
# render_window.Render()); decimating for DISPLAY only keeps interaction smooth
# while analysis still runs on the full cloud.
DISPLAY_MAX_POINTS = 600_000

# Sidebar sub-actions kept in core mode, keyed by the step code at the start
# of each button label (e.g. "4.3b"). Edit this set to fine-tune the scope.
CORE_STEP_CODES = {
    "1.1", "1.2", "1.3", "1.4", "1.8",                # acquire + merge stations / epochs
    "2.1", "2.5",                                     # preprocessing (2.5 = all-in-one denoise)
    "3.1", "3.2", "3.3",                              # registration + RMSE
    "4.1", "4.3b", "4.4",                             # centerline + section frames
    "5.1", "5.2", "5.3", "5.5", "5.6", "5.8",          # deformation parameters
    "6.1", "6.2", "6.3",                              # 4D time-series
    "7.1", "7.1b", "7.1c", "7.2",                     # BIM export (IFC4 + IFC4X3 + components) + AI assistant
}

# Output tabs hidden in core mode, matched by their English source title.
NON_CORE_TAB_TITLES = {"Polar Deformation"}


class TaskProgressDialog(QtWidgets.QDialog):
    """Modeless progress dialog for long-running pipeline tasks.

    Shows a progress bar, elapsed time and an estimated countdown so the user
    knows roughly how long processing will take. Progress is ETA-driven: the
    pipeline callbacks run as one opaque call in the worker thread (no inner
    progress signal), so we animate towards an estimate from the workload size
    and smoothly finish when the task actually completes.
    """

    def __init__(self, title: str, eta_seconds: float, translate, parent=None):
        super().__init__(parent)
        self._tr = translate
        self.setWindowTitle(title)
        self.setModal(False)
        self.setMinimumWidth(380)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self._eta_ms = max(int(eta_seconds * 1000), 500)
        self._elapsed = QtCore.QElapsedTimer()
        self._elapsed.start()
        self._finishing = False

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        self._task_lbl = QtWidgets.QLabel(title)
        self._task_lbl.setStyleSheet("font-weight:700;color:#0F4C81;font-size:10.5pt;")
        self._task_lbl.setWordWrap(True)
        lay.addWidget(self._task_lbl)

        self._bar = QtWidgets.QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(True)
        self._bar.setStyleSheet(
            "QProgressBar{border:1px solid #CBD5E1;border-radius:6px;height:18px;"
            "text-align:center;background:#F1F5F9;}"
            "QProgressBar::chunk{background:#1D4ED8;border-radius:5px;}")
        lay.addWidget(self._bar)

        self._time_lbl = QtWidgets.QLabel()
        self._time_lbl.setStyleSheet("color:#475569;font-size:9pt;")
        lay.addWidget(self._time_lbl)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._tick()

    @staticmethod
    def _fmt(ms: int) -> str:
        s = max(0, ms) / 1000.0
        if s < 60:
            return f"{s:0.1f}s"
        m, s = divmod(int(s), 60)
        return f"{m}m {s:02d}s"

    def _tick(self) -> None:
        elapsed = self._elapsed.elapsed()
        if self._finishing:
            return
        # Asymptotic approach to 95% so the bar never claims completion early.
        frac = 1.0 - 0.5 ** (elapsed / max(self._eta_ms, 1))
        pct = int(min(frac, 0.95) * 100)
        self._bar.setValue(pct)
        remaining = max(self._eta_ms - elapsed, 0)
        self._time_lbl.setText(
            self._tr("Elapsed: {e}  |  Estimated remaining: {r}").format(
                e=self._fmt(elapsed), r=self._fmt(remaining))
            if remaining > 0 else
            self._tr("Elapsed: {e}  |  Finishing...").format(e=self._fmt(elapsed)))

    def finish(self) -> None:
        """Snap to 100% and close (called when the task actually completes)."""
        self._finishing = True
        self._timer.stop()
        self._bar.setValue(100)
        elapsed = self._elapsed.elapsed()
        self._time_lbl.setText(self._tr("Completed in {e}").format(e=self._fmt(elapsed)))
        QtCore.QTimer.singleShot(250, self.accept)



class TunnelAnalysisWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tunnel Analysis v4.0 (r1) - CBNU Smart Structure Lab")
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
        # Single-glance overview: colour-coded metric cards (crown / convergence
        # / eccentricity / ovality), overall status banner, and a top-8 section
        # alert list.  Updated automatically whenever _show_params() or the
        # 5.7_sections dispatch fires.
        self.dashboard_widget = SummaryDashboardWidget()
        self._dashboard_tab_idx = self.right_tabs.addTab(
            self.dashboard_widget, "Summary Dashboard")

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
        st_title = QtWidgets.QLabel("Structure")
        st_title.setStyleSheet("color:white;font-weight:bold;font-size:10pt;background:transparent;")
        btn_add_st = QtWidgets.QPushButton("+")
        btn_add_st.setToolTip("Add scan station")
        btn_add_st.setFixedSize(24, 24)
        btn_add_st.setStyleSheet(
            "QPushButton{background:#1D4ED8;color:white;border-radius:4px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#2563EB;}")
        btn_add_st.clicked.connect(self._slot_1_3_add_scan)
        st_tb_lay.addWidget(st_title, 1)
        st_tb_lay.addWidget(btn_add_st)
        st_lay.addWidget(st_tb)

        # Tree widget
        self._station_tree = QtWidgets.QTreeWidget()
        self._station_tree.setHeaderHidden(True)
        self._station_tree.setColumnCount(1)
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
        st_bot.setStyleSheet("QFrame{background:#F1F5F9;border-top:1px solid #E2E8F0;padding:2px;}")
        st_bot_lay = QtWidgets.QHBoxLayout(st_bot)
        st_bot_lay.setContentsMargins(6, 2, 6, 2); st_bot_lay.setSpacing(4)
        btn_clear = QtWidgets.QPushButton("Clear All")
        btn_clear.setStyleSheet(
            "QPushButton{background:#FEE2E2;color:#DC2626;border:1px solid #FCA5A5;"
            "border-radius:4px;padding:3px 8px;font-weight:600;font-size:8.5pt;}"
            "QPushButton:hover{background:#FECACA;}")
        btn_clear.clicked.connect(self._clear_all_stations)
        st_bot_lay.addStretch()
        st_bot_lay.addWidget(btn_clear)
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
        tgt_title = QtWidgets.QLabel("Target Manager")
        tgt_title.setStyleSheet("color:white;font-weight:bold;font-size:10pt;background:transparent;")
        btn_detect = QtWidgets.QPushButton("Auto Detect")
        btn_detect.setStyleSheet(
            "QPushButton{background:#047857;color:white;border-radius:4px;"
            "padding:3px 10px;font-weight:700;border:none;font-size:9pt;}"
            "QPushButton:hover{background:#059669;}")
        btn_manual = QtWidgets.QPushButton("+ Manual")
        btn_manual.setStyleSheet(
            "QPushButton{background:#1D4ED8;color:white;border-radius:4px;"
            "padding:3px 10px;font-weight:700;border:none;font-size:9pt;}"
            "QPushButton:hover{background:#2563EB;}")
        btn_match = QtWidgets.QPushButton("Auto Match")
        btn_match.setStyleSheet(
            "QPushButton{background:#7C3AED;color:white;border-radius:4px;"
            "padding:3px 10px;font-weight:700;border:none;font-size:9pt;}"
            "QPushButton:hover{background:#6D28D9;}")
        btn_reg = QtWidgets.QPushButton("Register")
        btn_reg.setStyleSheet(
            "QPushButton{background:#DC2626;color:white;border-radius:4px;"
            "padding:3px 10px;font-weight:700;border:none;font-size:9pt;}"
            "QPushButton:hover{background:#B91C1C;}")
        btn_detect.clicked.connect(self._slot_target_detect)
        btn_manual.clicked.connect(self._slot_target_manual)
        btn_match.clicked.connect(self._slot_target_match)
        btn_reg.clicked.connect(self._slot_target_register)
        tgt_tb_lay.addWidget(tgt_title, 1)
        tgt_tb_lay.addWidget(btn_detect)
        tgt_tb_lay.addWidget(btn_manual)
        tgt_tb_lay.addWidget(btn_match)
        tgt_tb_lay.addWidget(btn_reg)
        tgt_lay.addWidget(tgt_tb)

        # Target table
        self._target_table = QtWidgets.QTableWidget(0, 7)
        self._target_table.setHorizontalHeaderLabels(
            ["Name", "Type", "Scan", "X", "Y", "Z", "Conf"])
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

        self.section_widget = MatplotlibSectionWidget()
        self._section_tab_idx = self.right_tabs.addTab(self.section_widget, "2D Cross-Section")

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

        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        out.addWidget(scroll, 1)
        sc = QtWidgets.QWidget(); sl = QtWidgets.QVBoxLayout(sc)
        sl.setContentsMargins(0, 0, 0, 0); sl.setSpacing(4); scroll.setWidget(sc)

        SECTIONS = [
            (1, "LiDAR data acquisition", "Base", [
                ("1.1  Import LAS / PLY data", self._slot_1_1_import),
                ("1.2  Initialize 3D viewport", self._slot_1_2_viewport),
                ("1.3  Add scan station (+)", self._slot_1_3_add_scan),
                ("1.4  Register & merge all stations", self._slot_1_4_merge),
                ("1.8  Load T0 and Tn epochs", self._slot_1_8_epochs),
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
                ("6.1  Plot deformation trend T0→Tn", self._slot_6_2_plot),
                ("6.2  M3C2 deformation map T0→Tn", self._slot_6_3_m3c2),
                ("6.3  Plot 2D Technical Section T0/Tn", self._slot_5_7_sections),
            ]),
            (7, "BIM and AI", "BIM/AI", [
                ("7.1  Export IFC package", self._slot_7_1_ifc),
                ("7.1b Export IFC4X3 (IfcAlignment)", self._slot_7_1b_ifc_alignment),
                ("7.1c Export IFC + components (cables/lights)", self._slot_7_1c_ifc_components),
                ("7.2  Query structural AI assistant", self._slot_7_2_query_ai),
            ]),
            (8, "Export and reporting", "Out.", [
                ("8.1  Export section CSV", self._slot_8_1_csv),
                ("8.2  Export Excel report", self._slot_8_2_excel),
                ("8.3  Export PDF report", self._slot_8_3_pdf),
                ("8.4  Open web dashboard", self._slot_8_4_web),
            ]),
        ]
        for step, title_s, tag, buttons in SECTIONS:
            if CORE_FEATURES_ONLY:
                buttons = [(label, slot) for (label, slot) in buttons
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
        if pv is None: self._vp_msg("PyVista is not installed."); return
        try:
            # auto_update=False disables pyvistaqt's background render timer
            # (default 5 fps). On large clouds / weak GPUs that timer keeps
            # re-issuing render_window.Render() and pins the GPU, making the
            # app appear to hang (the repeated KeyboardInterrupt seen in
            # render). We render on-demand after each _render_* call instead.
            self.plotter = QtInteractor(self.vp_frame, auto_update=False); self.plotter.set_background("#F8FAFC")
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
        """Show a progress dialog only if the task is likely to run a while,
        so quick operations don't flash a dialog. Skipped during AUTO mode
        (the sidebar button already reports per-step progress)."""
        self._close_task_dialog()
        if self._auto_running:
            return
        eta = self._estimate_eta_seconds(key)
        if eta < 1.5:
            return
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
                self.plotter.clear(); self.plotter.set_background("#F8FAFC")
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
            else:
                self._render_filter_result(pts, noise_pts,
                    "2.5 Auto Denoise | lining=blue, removed=red")
            self.pt_label.setText(f"Points: {len(pts):,}")
            self.sb_pts.setText(f"Points: {len(pts):,}")
            self._log(f"Auto denoise: {stats.get('n_clean', len(pts)):,}/{stats.get('n_raw', len(pts)):,} kept, {stats.get('n_removed', 0):,} removed.")
            self._log(f"  Cable={stats.get('n_cable', 0)} Light={stats.get('n_light', 0)} Person/Vehicle={stats.get('n_person', 0)} Radial={stats.get('n_radial', 0)}")

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
                self.plotter.clear(); self.plotter.set_background("#F8FAFC")
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
                self.plotter.clear(); self.plotter.set_background("#F8FAFC")
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
        elif key == "5.7_sections":
            sections: List[SectionGeometry] = result; self.context.sections = sections
            # Reflect the profile actually used (auto-detected in the worker /
            # auto-pipeline) back into the dropdown so the UI shows the truth.
            if hasattr(self, "_profile_combo") and self.context.tunnel_profile:
                self._profile_setting_programmatically = True
                self._profile_combo.setCurrentText(self.context.tunnel_profile)
                self._profile_setting_programmatically = False
            self._section_ref_sections = []
            self.section_widget.set_sections(sections, profile=self.context.tunnel_profile, vl_box_w=self._sp_vl_w.value(), vl_box_h=self._sp_vl_h.value(), vl_cir_r=self._sp_vl_r.value())
            try: self.section_widget.section_changed.disconnect()
            except Exception: pass
            self.section_widget.section_changed.connect(self._highlight_section)
            self._highlight_section(0)
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
            self.right_tabs.setCurrentIndex(self._section_tab_idx)
            # Push section data to dashboard (section alerts list).
            ref_secs = getattr(self, "_section_ref_sections", []) or []
            self.dashboard_widget.update_sections(
                sections, ref_secs, profile=self.context.tunnel_profile or "Circle")
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

        elif key in ("1.8_epochs", "6.1_epochs"):
            t0, tn = result
            self._activate_epochs(t0, tn)
            self._log(_tr("T0/Tn epochs loaded. T0 is reference; Tn is active for Steps 2-5.", self.current_language))

        elif key == "6.2_plot":
            if isinstance(result, dict) and "median_mm" in result:
                self.context.time_series_result = result
                series = np.asarray(result["median_mm"], dtype=np.float64)
                self.context.time_series_plot = series
                labels = result.get("labels", [])
                method = result.get("method", "time-series")
                self.ts_plot.set_values(series, f"T0→Tn deformation trend [{method}] median displacement (mm)")
                p95 = np.asarray(result.get("p95_abs_mm", []), dtype=np.float64)
                if len(series):
                    self._log(f"Time-series trend [{method}]: epochs={list(labels)} median_mm={np.round(series, 2).tolist()} p95_abs_mm={np.round(p95, 2).tolist()}")
            else:
                series = np.asarray(result, dtype=np.float64); self.context.time_series_plot = series
                self.ts_plot.set_values(series, "Crown-height trend across chainage (mm)")
            self.right_tabs.setCurrentIndex(self._ts_tab_idx)

        elif key == "6.3_m3c2":
            res = result
            self.context.m3c2_result = res
            pts = np.asarray(res["corepoints"], dtype=np.float64)
            dist_mm = np.asarray(res["distance_mm"], dtype=np.float64)
            self.context.heatmap_scalars = dist_mm
            pts, dist_mm = self._decimate_for_display(pts, dist_mm)
            mesh = make_vertex_cloud(pts)
            if dist_mm is not None and len(dist_mm) == mesh.n_points:
                mesh["M3C2_mm"] = dist_mm
            if self.plotter is not None:
                lim = float(np.nanmax(np.abs(dist_mm))) if dist_mm.size else 1.0
                lim = max(lim, 1e-6)
                self.plotter.clear(); self.plotter.set_background("#F8FAFC")
                self.plotter.add_mesh(mesh, scalars="M3C2_mm", cmap="RdBu_r",
                    style="points", point_size=2.8, render_points_as_spheres=False,
                    reset_camera=True, clim=[-lim, lim],
                    scalar_bar_args={"title": "M3C2 displacement (mm)"})
                self.plotter.add_text(f"M3C2 Deformation Map T0\u2192Tn  [{res['method']}]",
                    position="upper_left", font_size=11, color="#111827", name="ttl")
                self.plotter.add_axes(color="#111827"); self.plotter.reset_camera(); self.plotter.render()
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
            self.right_tabs.setCurrentIndex(0)

        elif key == "8.1_csv":
            path = result
            self._log(f"CSV exported: {path}")
            import subprocess; subprocess.Popen(["explorer", "/select,", path])
        elif key == "8.4_web":
            url = result
            self._log(f"Web dashboard launched: {url}")
        elif key == "8.3_pdf":
            path = result
            self._log(f"PDF report exported: {path}")
            import subprocess; subprocess.Popen(["explorer", "/select,", path])
        elif key == "8.2_excel":
            path = result
            self._log(f"Excel report exported: {path}")
            import subprocess; subprocess.Popen(["explorer", "/select,", path])
        elif key == "7.1_ifc":
            self.ai_resp.setPlainText(json.dumps(result, indent=2)); self.right_tabs.setCurrentIndex(self._ai_tab_idx)

        elif key == "7.2_ai":
            self.ai_resp.setPlainText(str(result)); self.right_tabs.setCurrentIndex(self._ai_tab_idx)

    def _slot_1_1_import(self) -> None:
        self._hdr("LiDAR Data Acquisition", "Load LAS/LAZ/PLY point-cloud data into the project database.")
        fp, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load tunnel point-cloud data", "", "Point Clouds (*.las *.laz *.ply *.txt *.xyz *.pts *.csv *.asc);;All Files (*.*)")
        if not fp: return
        max_pts = self._ask_max_points(fp)
        if max_pts is None: return
        self._start_worker("1.1_import", lambda: self.base_mod.load_scan(fp, max_points=max_pts))

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
        fp = paths[0]
        import pathlib
        name = pathlib.Path(fp).name
        if len(paths) > 1:
            self._log(f"Multiple files dropped; loading '{name}'. Drop the rest one at a time to add stations.")
        max_pts = self._ask_max_points(fp)
        if max_pts is None:
            return
        if len(self.context.scans) == 0:
            self._hdr("LiDAR Data Acquisition (drag & drop)",
                      "Loaded by drag & drop: " + name)
            self._start_worker("1.1_import", lambda: self.base_mod.load_scan(fp, max_points=max_pts))
        else:
            self._hdr("Add Scan Station (drag & drop)",
                      "Added by drag & drop: " + name)
            self._start_worker("1.3_add_scan", lambda: self.base_mod.load_scan(fp, max_points=max_pts))

    def _slot_1_8_epochs(self) -> None:
        self._hdr("Load T0/Tn Epochs", "Load reference T0 and monitoring Tn at the start of the pipeline.")
        fp0, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load reference epoch T0", "", "Point Clouds (*.las *.laz *.ply *.txt *.xyz *.pts *.csv *.asc);;All Files (*.*)")
        if not fp0: return
        fpn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load monitoring epoch Tn", "", "Point Clouds (*.las *.laz *.ply *.txt *.xyz *.pts *.csv *.asc);;All Files (*.*)")
        if not fpn: return
        self._start_worker("1.8_epochs", lambda: self.ts_mod.load_epochs(fp0, fpn))

    def _activate_epochs(self, t0: PointCloudBundle, tn: PointCloudBundle) -> None:
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
        self._render_bundle(tn, "Tn Active Epoch (T0 reference loaded)")
        self._update_meta(tn)
        self.pt_label.setText(f"Points: {len(tn.points):,}")
        self.sb_pts.setText(f"Points: {len(tn.points):,}")
        self._refresh_station_list()
        self._render_station_markers()

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
        self._hdr("Add Scan Station", "Load additional scan station to merge with existing scans.")
        fp, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Scan Station", "",
            "Point Clouds (*.las *.laz *.ply *.txt *.xyz *.pts *.csv *.asc);;All Files (*.*)")
        if not fp: return
        max_pts = self._ask_max_points(fp)
        if max_pts is None: return
        self._start_worker("1.3_add_scan", lambda: self.base_mod.load_scan(fp, max_points=max_pts))

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
            self.plotter.clear(); self.plotter.set_background("#F8FAFC"); self.plotter.add_axes(color="#111827")
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
        self._auto_steps = [
            ("2.1_voxel",       lambda: self.pre_mod.voxel_downsample(self.context),
             "Step 1/6: Voxel downsampling..."),
            ("2.5_auto_denoise", lambda: self.pre_mod.auto_denoise(self.context),
             "Step 2/6: Smart noise removal (cables, lights, people, wall cables)..."),
            ("4.1_centerline",  lambda: self.geo_mod.extract_centerline(self.context, section_count=self._resolve_section_count()),
             "Step 3/6: Centerline extraction..."),
            ("4.3b_bspline",    lambda: self.geo_mod.extract_centerline_bspline(self.context, section_count=self._resolve_section_count()),
             "Step 4/6: B-spline centerline..."),
            ("5.7_sections",    lambda: self._auto_sections_task(),
             "Step 5/6: 2D section analysis (auto profile + clearance)..."),
            ("auto_params",     lambda: self._auto_extract_params(),
             "Step 6/6: Parameter extraction..."),
        ]
        self._run_next_auto_step()

    def _auto_sections_task(self):
        """AUTO PIPELINE 2D-section step: pick the profile and clearance gauge
        automatically (pure NumPy, safe in the worker thread), then compute
        all sections.
        """
        self.context.tunnel_profile = self.par_mod.detect_profile(self.context)
        g = self._compute_auto_gauge()
        if g:
            w, h, r = g
        else:
            w, h, r = self._sp_vl_w.value(), self._sp_vl_h.value(), self._sp_vl_r.value()
        return self.par_mod.compute_all_sections(self.context, vl_box_w=w, vl_box_h=h, vl_cir_r=r)

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
        """Auto-match targets between scan stations."""
        if len(self.context.scans) < 2:
            self._log(_tr("Need at least 2 scan stations.", self.current_language)); return
        src_t = [t for t in self._targets if t.scan_idx == 0]
        tgt_t = [t for t in self._targets if t.scan_idx == 1]
        if not src_t or not tgt_t:
            self._log(_tr("Detect targets in both stations first.", self.current_language)); return
        matches = self.tgt_mod.match_targets(src_t, tgt_t, max_dist=5.0)
        self._refresh_target_table()
        self._log(f"Auto-matched {len(matches)} target pairs:")
        for st, tt, d in matches:
            self._log(f"  {st.name} <-> {tt.name}  dist={d:.3f}m")

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
                self.plotter.set_background("#F8FAFC")
                self.plotter.render()
            except Exception: pass
        self.results_text.clear()
        self.dashboard_widget.clear()
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
        self._start_worker("5.7_sections", lambda: self.par_mod.compute_all_sections(self.context, vl_box_w=self._sp_vl_w.value(), vl_box_h=self._sp_vl_h.value(), vl_cir_r=self._sp_vl_r.value()))

    def _slot_6_1_epochs(self) -> None:
        self._hdr("Load Time-Series Epochs", "Load reference and monitoring point-cloud epochs for deformation comparison.")
        fp0, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load reference epoch T0", "", "Point Clouds (*.las *.laz *.ply *.txt *.xyz *.pts *.csv *.asc);;All Files (*.*)")
        if not fp0: return
        fpn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load monitoring epoch", "", "Point Clouds (*.las *.laz *.ply *.txt *.xyz *.pts *.csv *.asc);;All Files (*.*)")
        if not fpn: return
        self._start_worker("6.1_epochs", lambda: self.ts_mod.load_epochs(fp0, fpn))

    def _slot_6_2_plot(self) -> None:
        self._hdr("Deformation Trend Chart", "Plot deformation trend metrics along the chainage line.")
        if len(self.context.scans) < 2:
            self._log(_tr("Load at least 2 scans (T0 and Tn) first.", self.current_language)); return
        import os as _os
        tn_pts = self.context.working_points if self.context.working_points is not None else self.context.scans[1].points
        epochs = [np.asarray(self.context.scans[0].points, dtype=np.float64), np.asarray(tn_pts, dtype=np.float64)]
        labels = [_os.path.splitext(_os.path.basename(self.context.scans[1].path or "Tn"))[0]]
        self._start_worker("6.2_plot", lambda: self.ts_mod.spatiotemporal_series(
            epochs, labels=labels, cyl_radius=0.5, normal_radius=0.6))

    def _slot_6_3_m3c2(self) -> None:
        self._hdr("M3C2 Deformation Map T0\u2192Tn",
                  "Compute multiscale surface displacement (M3C2) with level-of-detection between epochs.")
        if len(self.context.scans) < 2:
            self._log(_tr("Load at least 2 scans (T0 and Tn) first.", self.current_language)); return
        epoch0 = self.context.scans[0].points
        epoch1 = self.context.working_points if self.context.working_points is not None else self.context.scans[1].points
        self._start_worker("6.3_m3c2",
            lambda: self.ts_mod.m3c2_distances(epoch0, epoch1, cyl_radius=0.5, normal_radius=0.6))

    def _slot_8_1_csv(self) -> None:
        self._hdr("Export CSV", "Export section parameters to CSV file.")
        if not self.context.sections and not self.context.parameters:
            self._log(_tr("Run parameter extraction first (Step 5).", self.current_language)); return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save CSV", "tunnel_report.csv", "CSV Files (*.csv)")
        if not path: return
        self._start_worker("8.1_csv", lambda: self.exp_mod.export_csv(self.context, path))

    def _slot_8_2_excel(self) -> None:
        self._hdr("Export Excel Report", "Export full analysis report with charts and warnings.")
        if not self.context.sections and not self.context.parameters:
            self._log(_tr("Run parameter extraction first (Step 5).", self.current_language)); return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Excel Report", "tunnel_report.xlsx", "Excel Files (*.xlsx)")
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
            self, "Save PDF Report", "tunnel_report.pdf", "PDF Files (*.pdf)")
        if not path: return
        scan = self.context.active_scan
        proj = scan.path if scan and scan.path else "Tunnel Analysis"
        self._start_worker("8.3_pdf", lambda: self.pdf_mod.export_pdf(
            self.context, path, project_name=proj, engineer="CBNU Smart Structure Lab"))

    def _slot_7_1_ifc(self) -> None:
        self._hdr("IFC/BIM Export (IFC4)", "Export tunnel geometry and parameters to IFC4 format.")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save IFC Model", "tunnel_model.ifc", "IFC Files (*.ifc)")
        if not path: return
        scan = self.context.active_scan
        proj = scan.path if scan and scan.path else "Tunnel Analysis"
        self._start_worker("7.1_ifc", lambda: self.ifc_mod.export_ifc(
            self.context, path, project_name=proj, engineer="CBNU Smart Structure Lab"))

    def _slot_7_1b_ifc_alignment(self) -> None:
        self._hdr("IFC4X3 Export (IfcAlignment)", "Export with the centerline as an IfcAlignment (infrastructure linear-referencing standard).")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save IFC4X3 Model", "tunnel_model_4x3.ifc", "IFC Files (*.ifc)")
        if not path: return
        scan = self.context.active_scan
        proj = scan.path if scan and scan.path else "Tunnel Analysis"
        self._start_worker("7.1_ifc", lambda: self.ifc_mod.export_ifc(
            self.context, path, project_name=proj, engineer="CBNU Smart Structure Lab",
            schema="IFC4X3_ADD2"))

    def _slot_7_1c_ifc_components(self) -> None:
        self._hdr("IFC Export + Components", "Export IFC including detected cables/lights/people as coloured proxies (run auto-denoise first).")
        if not self.context.component_points:
            self._log(_tr("Run auto-denoise (Step 2.5) first to detect components.", self.current_language)); return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save IFC Model with Components", "tunnel_model_components.ifc", "IFC Files (*.ifc)")
        if not path: return
        scan = self.context.active_scan
        proj = scan.path if scan and scan.path else "Tunnel Analysis"
        self._start_worker("7.1_ifc", lambda: self.ifc_mod.export_ifc(
            self.context, path, project_name=proj, engineer="CBNU Smart Structure Lab",
            include_components=True))

    def _slot_7_2_query_ai(self) -> None:
        self._hdr("AI Engineering Assistant (RAG)", "Query local LLM with safety standards knowledge base.")
        prompt = self.ai_prompt.toPlainText().strip() or "Summarize the tunnel inspection results and identify locations that require engineering attention."
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
        act_del = menu.addAction("Delete Station")
        act_del.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_TrashIcon))
        act_del.triggered.connect(lambda: self._delete_station(idx))

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

    def _delete_station(self, idx: int) -> None:
        """Delete a scan station."""
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
        self.plotter.clear(); self.plotter.set_background("#F8FAFC")
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
        self.plotter.clear(); self.plotter.set_background("#F8FAFC")
        kw = dict(style="points", point_size=2.4, render_points_as_spheres=False, reset_camera=True)
        if "RGB" in clean.array_names and color is None: self.plotter.add_mesh(clean, scalars="RGB", rgb=True, **kw)
        elif "Intensity" in clean.array_names and color is None: self.plotter.add_mesh(clean, scalars="Intensity", cmap="viridis", **kw)
        else: self.plotter.add_mesh(clean, color=color or "#1D4ED8", **kw)
        self.plotter.add_text(title, position="upper_left", font_size=11, color="#111827", name="ttl")
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
        self.plotter.clear(); self.plotter.set_background("#F8FAFC")
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
        # Push to Summary Dashboard (auto-switch to it for quick review).
        self.dashboard_widget.update_params(params)
        self.right_tabs.setCurrentIndex(self._dashboard_tab_idx)

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
        self._auto_btn.setText(_tr("AUTO PIPELINE  (1-click full analysis)", lang))
        self._reset_btn.setText(_tr("Reset Pipeline", lang))

        # Collapsible section titles + sub-button labels
        for sec in self._sections:
            sec.set_translation(_tr(sec.title_source, lang), step_word)
            sec.retranslate_buttons(lambda t: _tr(t, lang))

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

        # AI assistant panel
        self.ai_prompt.setPlaceholderText(_tr("Enter a structural engineering question for the local AI assistant (Llama 3)...", lang))
        self.ai_send.setText(_tr("Query AI Assistant", lang))
        self._ai_query_lbl.setText(_tr("Engineering query:", lang))
        self._ai_report_lbl.setText(_tr("AI analysis report:", lang))

    def _apply_theme(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #F1F5F9; color: #111827; font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; }
            #Sidebar { background: #FFFFFF; border-right: 1px solid #E2E8F0; }
            #ProductTitle { color: #0F4C81; font-size: 15pt; font-weight: 800; letter-spacing: 0.5px; }
            #LabSubtitle  { color: #64748B; font-size: 9pt; padding-bottom: 4px; }
            #Separator    { color: #E2E8F0; margin: 4px 0; }
            QScrollArea   { background: transparent; border: none; }
            QToolButton#SectionToggle { background: #EEF4FA; border: 1px solid #D1DCEB; border-radius: 6px; padding: 6px 10px; font-weight: 600; color: #1E3A5F; text-align: left; }
            QToolButton#SectionToggle:hover   { background: #DBEAFE; border-color: #3B82F6; }
            QToolButton#SectionToggle:checked { background: #BFDBFE; border-color: #1D4ED8; }
            QWidget#SectionContent { background: #F8FAFC; border-left: 2px solid #BFDBFE; margin-left: 10px; }
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


class _RoughAlignDialog(QtWidgets.QDialog):
    def __init__(self, context, reg_mod, parent=None, plotter=None):
        super().__init__(parent)
        self._lang = getattr(parent, "current_language", "en")
        self.setWindowTitle(_tr("Rough Alignment", self._lang))
        self.setMinimumWidth(480)
        self.context = context; self.reg_mod = reg_mod
        self.plotter = plotter; self.offset = [0.0,0.0,0.0]
        self.rotation = [0.0,0.0,0.0]; self.aligned_pts = None
        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(10); lay.setContentsMargins(16,16,16,16)
        hdr = QtWidgets.QLabel(_tr("Adjust scan station position before ICP", self._lang))
        hdr.setStyleSheet("color:#0F172A;font-weight:bold;font-size:10pt;")
        lay.addWidget(hdr)
        st_lay = QtWidgets.QHBoxLayout()
        st_lay.addWidget(QtWidgets.QLabel(_tr("Active station:", self._lang)))
        self._station_combo = QtWidgets.QComboBox()
        for i, sc in enumerate(self.context.scans):
            name = _tr("Station", self._lang) + " " + str(i+1)
            if sc.path:
                import pathlib
                name += " - " + pathlib.Path(sc.path).name
            self._station_combo.addItem(name)
        self._station_combo.setCurrentIndex(len(self.context.scans)-1)
        st_lay.addWidget(self._station_combo, 1); lay.addLayout(st_lay)
        grp = QtWidgets.QGroupBox(_tr("Translation (m) & Rotation (deg)", self._lang))
        grp.setStyleSheet("QGroupBox{font-weight:600;color:#0F4C81;border:1px solid #CBD5E1;border-radius:6px;margin-top:8px;padding:8px;}")
        form = QtWidgets.QFormLayout(grp)
        self._sliders = {}
        params = [("dx",_tr("dX (m)",self._lang),-20,20,0),("dy",_tr("dY (m)",self._lang),-20,20,0),("dz",_tr("dZ (m)",self._lang),-20,20,0),
                  ("rx",_tr("Rot X",self._lang),-180,180,0),("ry",_tr("Rot Y",self._lang),-180,180,0),("rz",_tr("Rot Z",self._lang),-180,180,0)]
        for key,label,mn,mx,val in params:
            row = QtWidgets.QHBoxLayout()
            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setRange(int(mn*100),int(mx*100)); slider.setValue(int(val*100))
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(mn,mx); spin.setValue(val); spin.setFixedWidth(90)
            slider.valueChanged.connect(lambda v,s=spin: s.setValue(v/100.0))
            spin.valueChanged.connect(lambda v,sl=slider: sl.setValue(int(v*100)))
            spin.valueChanged.connect(self._on_param_changed)
            row.addWidget(slider,1); row.addWidget(spin)
            self._sliders[key] = (slider,spin)
            form.addRow(label, row)
        lay.addWidget(grp)
        self._rmse_lbl = QtWidgets.QLabel("RMSE: --")
        self._rmse_lbl.setStyleSheet("color:#0F4C81;font-weight:bold;font-size:10pt;padding:6px;background:#EFF6FF;border-radius:4px;")
        lay.addWidget(self._rmse_lbl)
        btn_lay = QtWidgets.QHBoxLayout()
        btn_reset = QtWidgets.QPushButton(_tr("Reset", self._lang))
        btn_icp   = QtWidgets.QPushButton(_tr("Run ICP", self._lang))
        btn_ok    = QtWidgets.QPushButton(_tr("Apply & Close", self._lang))
        btn_cancel= QtWidgets.QPushButton(_tr("Cancel", self._lang))
        for btn,color in [(btn_reset,"#64748B"),(btn_icp,"#7C3AED"),(btn_ok,"#047857"),(btn_cancel,"#DC2626")]:
            btn.setStyleSheet(f"QPushButton{{background:{color};color:white;border-radius:5px;padding:7px 16px;font-weight:700;border:none;}}")
        btn_reset.clicked.connect(self._reset); btn_icp.clicked.connect(self._run_icp)
        btn_ok.clicked.connect(self.accept); btn_cancel.clicked.connect(self.reject)
        btn_lay.addWidget(btn_reset); btn_lay.addWidget(btn_icp)
        btn_lay.addStretch(); btn_lay.addWidget(btn_ok); btn_lay.addWidget(btn_cancel)
        lay.addLayout(btn_lay)
        self._on_param_changed()

    def _get_params(self):
        return ([self._sliders[k][1].value() for k in ["dx","dy","dz"]],
                [self._sliders[k][1].value() for k in ["rx","ry","rz"]])

    def _on_param_changed(self):
        offset, rotation = self._get_params()
        self.offset = offset; self.rotation = rotation
        idx = self._station_combo.currentIndex()
        if idx < 0 or idx >= len(self.context.scans): return
        pts = validate_xyz(self.context.scans[idx].points)
        self.aligned_pts = self.reg_mod.apply_manual_transform(pts, tuple(offset), tuple(rotation))
        if self.aligned_pts is not None and len(self.context.scans) > 0:
            ref_idx = max(0, idx-1)
            ref = validate_xyz(self.context.scans[ref_idx].points)
            rmse = self.reg_mod._rmse(self.aligned_pts, ref)
            color = "#047857" if rmse < 2.0 else "#D97706" if rmse < 5.0 else "#DC2626"
            status = _tr("GOOD", self._lang) if rmse < 2.0 else _tr("CAUTION", self._lang) if rmse < 5.0 else _tr("POOR", self._lang)
            self._rmse_lbl.setText(_tr("RMSE vs Station {n}: {rmse} mm  [{status}]", self._lang).format(n=ref_idx+1, rmse=f"{rmse:.3f}", status=status))
            self._rmse_lbl.setStyleSheet(f"color:{color};font-weight:bold;font-size:10pt;padding:6px;background:#F8FAFC;border-radius:4px;border:1px solid {color};")

    def _run_icp(self):
        if self.aligned_pts is None: return
        idx = self._station_combo.currentIndex()
        ref_idx = max(0, idx-1)
        ref = validate_xyz(self.context.scans[ref_idx].points)
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            reg, rmse = self.reg_mod._icp(self.aligned_pts, ref)
            self.aligned_pts = reg
            color = "#047857" if rmse < 2.0 else "#D97706" if rmse < 5.0 else "#DC2626"
            status = _tr("GOOD", self._lang) if rmse < 2.0 else _tr("CAUTION", self._lang) if rmse < 5.0 else _tr("POOR", self._lang)
            self._rmse_lbl.setText(_tr("After ICP: {rmse} mm  [{status}]", self._lang).format(rmse=f"{rmse:.3f}", status=status))
            self._rmse_lbl.setStyleSheet(f"color:{color};font-weight:bold;font-size:10pt;padding:6px;background:#F8FAFC;border-radius:4px;border:1px solid {color};")
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

    def _reset(self):
        for key, (slider, spin) in self._sliders.items():
            spin.setValue(0.0)


class _TargetDetectDialog(QtWidgets.QDialog):
    def __init__(self, bundle, parent=None):
        super().__init__(parent)
        self._lang = getattr(parent, "current_language", "en")
        self.setWindowTitle(_tr("Target Detection Settings", self._lang))
        self.setMinimumWidth(420)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(10); lay.setContentsMargins(16,16,16,16)
        has_int = bundle.intensity is not None and float(bundle.intensity.max()) > 0
        n_pts = len(bundle.points)
        info = QtWidgets.QLabel(_tr("Points: ", self._lang) + str(n_pts) + chr(10) + _tr("Has intensity/color: ", self._lang) + str(has_int))
        info.setStyleSheet("background:#F0FDF4;border:1px solid #86EFAC;border-radius:4px;padding:6px;color:#166534;font-size:9pt;")
        lay.addWidget(info)
        if not has_int:
            warn = QtWidgets.QLabel(_tr("No intensity/color data - sphere and flat detection only.", self._lang))
            warn.setStyleSheet("background:#FEF3C7;border:1px solid #FCD34D;border-radius:4px;padding:6px;color:#92400E;font-size:9pt;")
            lay.addWidget(warn)
        grp = QtWidgets.QGroupBox(_tr("Detection Types", self._lang))
        grp.setStyleSheet("QGroupBox{font-weight:600;color:#065F46;border:1px solid #A7F3D0;border-radius:6px;margin-top:8px;padding:8px;}")
        g_lay = QtWidgets.QVBoxLayout(grp)
        self._chk_sphere = QtWidgets.QCheckBox(_tr("Sphere targets (RANSAC sphere fitting)", self._lang))
        self._chk_flat   = QtWidgets.QCheckBox(_tr("Flat / Checkerboard targets (plane + FFT)", self._lang))
        self._chk_int    = QtWidgets.QCheckBox(_tr("Intensity / Color targets (high-reflectance)", self._lang))
        self._chk_sphere.setChecked(True)
        self._chk_flat.setChecked(True)
        self._chk_int.setChecked(has_int)
        self._chk_int.setEnabled(has_int)
        for chk in [self._chk_sphere, self._chk_flat, self._chk_int]:
            g_lay.addWidget(chk)
        lay.addWidget(grp)
        prm = QtWidgets.QGroupBox(_tr("Parameters", self._lang))
        prm.setStyleSheet("QGroupBox{font-weight:600;color:#065F46;border:1px solid #A7F3D0;border-radius:6px;margin-top:8px;padding:8px;}")
        p_lay = QtWidgets.QFormLayout(prm)
        self._sp_r_min = QtWidgets.QDoubleSpinBox()
        self._sp_r_min.setRange(0.01,0.5); self._sp_r_min.setValue(0.05); self._sp_r_min.setSuffix(" m")
        self._sp_r_max = QtWidgets.QDoubleSpinBox()
        self._sp_r_max.setRange(0.05,1.0); self._sp_r_max.setValue(0.25); self._sp_r_max.setSuffix(" m")
        self._sp_cell_min = QtWidgets.QDoubleSpinBox()
        self._sp_cell_min.setRange(0.02,0.5); self._sp_cell_min.setValue(0.03); self._sp_cell_min.setSuffix(" m")
        self._sp_cell_max = QtWidgets.QDoubleSpinBox()
        self._sp_cell_max.setRange(0.05,1.0); self._sp_cell_max.setValue(0.50); self._sp_cell_max.setSuffix(" m")
        self._sp_contrast = QtWidgets.QDoubleSpinBox()
        self._sp_contrast.setRange(1.1,10.0); self._sp_contrast.setValue(1.3); self._sp_contrast.setSingleStep(0.1)
        self._sp_int_pct = QtWidgets.QDoubleSpinBox()
        self._sp_int_pct.setRange(80.0,99.9); self._sp_int_pct.setValue(97.0); self._sp_int_pct.setSuffix(" %")
        self._sp_min_pts = QtWidgets.QSpinBox()
        self._sp_min_pts.setRange(5,500); self._sp_min_pts.setValue(20); self._sp_min_pts.setSuffix(" pts")
        p_lay.addRow(_tr("Sphere radius min:", self._lang), self._sp_r_min)
        p_lay.addRow(_tr("Sphere radius max:", self._lang), self._sp_r_max)
        p_lay.addRow(_tr("Checker cell min:", self._lang), self._sp_cell_min)
        p_lay.addRow(_tr("Checker cell max:", self._lang), self._sp_cell_max)
        p_lay.addRow(_tr("Min contrast ratio:", self._lang), self._sp_contrast)
        p_lay.addRow(_tr("Intensity percentile:", self._lang), self._sp_int_pct)
        p_lay.addRow(_tr("Min cluster points:", self._lang), self._sp_min_pts)
        lay.addWidget(prm)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_params(self):
        return {
            "detect_sphere":        self._chk_sphere.isChecked(),
            "detect_flat":          self._chk_flat.isChecked(),
            "detect_intensity":     self._chk_int.isChecked(),
            "sphere_radius_range":  (self._sp_r_min.value(), self._sp_r_max.value()),
            "intensity_percentile": self._sp_int_pct.value(),
            "min_cluster_pts":      self._sp_min_pts.value(),
            "cell_size_range":      (self._sp_cell_min.value(), self._sp_cell_max.value()),
            "min_contrast_ratio":   self._sp_contrast.value(),
        }


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
