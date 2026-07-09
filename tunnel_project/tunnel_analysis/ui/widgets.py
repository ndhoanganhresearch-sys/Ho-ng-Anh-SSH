from ..common import *
from ..models import SectionGeometry

# Section warning classification moved to tunnel_analysis.section_warnings
# (core, Qt-free) so headless code can use it without the UI. Re-exported here
# because every existing caller imports these names from ui.widgets.
from ..section_warnings import (SECTION_DELTA_CAUTION_MM, SECTION_DELTA_CRITICAL_MM,
                                _directed_delta_label, classify_sections,
                                section_warning_status, section_warning_text)


# Ruler/track widgets live in ui.ruler. Re-exported here so existing imports
# from tunnel_analysis.ui.widgets remain compatible during gradual UI split.
from .ruler import ChainageRulerWidget, _WarningTrack

class CollapsibleSection(QtWidgets.QWidget):
    def __init__(self, title: str, step: int, tag: str, parent=None):
        super().__init__(parent)
        self._btn = QtWidgets.QToolButton()
        self._btn.setCheckable(True); self._btn.setChecked(False)
        self._btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._btn.setArrowType(QtCore.Qt.RightArrow)
        self._btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self._btn.setMinimumHeight(44); self._btn.setObjectName("SectionToggle")
        self._title = title; self._step = step; self._tag = tag
        self._step_word = "Step"
        self._btn.setText(f"  {self._step_word} {step}: {title}  [{tag}]")
        self._btn.toggled.connect(self._toggle)
        self._body = QtWidgets.QWidget(); self._body.setObjectName("SectionContent")
        self._blay = QtWidgets.QVBoxLayout(self._body)
        self._blay.setContentsMargins(12,4,4,8); self._blay.setSpacing(4)
        self._body.setVisible(False)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(self._btn); root.addWidget(self._body)

    def _toggle(self, checked: bool) -> None:
        self._btn.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow)
        self._body.setVisible(checked)

    def set_translation(self, title: str, step_word: str = "Step") -> None:
        """Update the visible section title (keeps the immutable English source)."""
        self._step_word = step_word
        self._btn.setText(f"  {step_word} {self._step}: {title}  [{self._tag}]")

    def retranslate_buttons(self, translate: Callable[[str], str]) -> None:
        """Re-apply translated labels to sub-buttons (English source preserved)."""
        for b in self._body.findChildren(QtWidgets.QPushButton):
            src = b.property("source_label")
            if src:
                b.setText(f"  - {translate(src)}")

    @property
    def title_source(self) -> str:
        return self._title

    def add_sub_button(self, label: str, slot: Callable) -> QtWidgets.QPushButton:
        b = QtWidgets.QPushButton(f"  - {label}")
        b.setObjectName("SubButton"); b.setMinimumHeight(32)
        b.setCursor(QtCore.Qt.PointingHandCursor); b.clicked.connect(slot)
        b.setProperty("source_label", label)
        self._blay.addWidget(b); return b

    def all_sub_buttons(self) -> List[QtWidgets.QPushButton]:
        return self._body.findChildren(QtWidgets.QPushButton)


# Distinct colours for the multi-times (T0~Tn) cross-section overlay, ordered
# cool->warm so the latest/most-deformed times reads as the warmest line.
_EPOCH_COLORS = ["#378ADD", "#1D9E75", "#639922", "#EF9F27",
                 "#D85A30", "#E24B4A", "#8B5CF6", "#EC4899"]

# 2D-section deformation controls (T0/times overlay checkbox, Animate, Visual
# scale). Hidden by default to keep the cross-section tab clean; the slots and
# overlay code are kept intact. Flip to True to restore the control row.
SHOW_DEFORM_CONTROLS = False


class MatplotlibSectionWidget(QtWidgets.QWidget):

    section_changed = QtCore.Signal(int)  # emits current index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sections: List[SectionGeometry] = []
        self._idx: int = 0
        self._profile: str = "Circle"
        self._section_render_mode: str = "Field Robust"
        self._translate = lambda text: text
        self._vl_box_w  = VL_BOX_W
        self._vl_box_h  = VL_BOX_H
        self._vl_cir_r  = VL_CIR_R

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0); lay.setSpacing(4)

        # Navigation bar
        nav_frame = QtWidgets.QFrame()
        nav_frame.setStyleSheet("QFrame{background:#0F4C81;border-radius:6px;padding:2px;}")
        nav_frame.setMinimumHeight(44)
        nav = QtWidgets.QHBoxLayout(nav_frame)
        nav.setContentsMargins(6, 4, 6, 4); nav.setSpacing(6)
        btn_style = ("QPushButton{background:#1D4ED8;color:white;border-radius:5px;"
            "padding:4px 10px;font-weight:700;font-size:9.5pt;border:none;min-width:60px;}"
            "QPushButton:hover{background:#2563EB;}")
        expand_style = ("QPushButton{background:#047857;color:white;border-radius:5px;"
            "padding:4px 10px;font-weight:700;font-size:9.5pt;border:none;min-width:55px;}"
            "QPushButton:hover{background:#065F46;}")
        self._btn_prev = QtWidgets.QPushButton("\u25C0 Prev")
        self._btn_next = QtWidgets.QPushButton("Next \u25B6")
        self._btn_reset = QtWidgets.QPushButton("\u27F3 Zoom")
        self._btn_prev.setStyleSheet(btn_style)
        self._btn_next.setStyleSheet(btn_style)
        self._btn_reset.setStyleSheet(expand_style)
        self._btn_prev.setMinimumWidth(80)
        self._btn_next.setMinimumWidth(80)
        self._btn_reset.setMinimumWidth(110)
        self._btn_reset.setToolTip("Reset zoom (R)")
        self._btn_info = QtWidgets.QPushButton("\u24d8 Info")
        self._btn_info.setStyleSheet(expand_style)
        self._btn_info.setMinimumWidth(55)
        self._btn_info.setToolTip("Show section parameters")
        self._btn_measured = QtWidgets.QPushButton("🎯 Measured point")
        self._btn_measured.setStyleSheet(expand_style)
        self._btn_measured.setMinimumWidth(135)
        self._btn_measured.setEnabled(False)
        self._btn_measured.setToolTip("Jump to the Step 6 measured crown point")
        self._current_sg = None
        self._lbl_ch = QtWidgets.QLabel("Ch: --")
        self._lbl_ch.setAlignment(QtCore.Qt.AlignCenter)
        self._lbl_ch.setStyleSheet("color:white;font-weight:bold;font-size:10pt;background:transparent;min-width:100px;")
        self._btn_prev.clicked.connect(self._prev)
        self._btn_next.clicked.connect(self._next)
        self._lbl_ch.setAlignment(QtCore.Qt.AlignCenter)
        self._lbl_ch.setStyleSheet("color:white;font-weight:bold;font-size:10pt;background:transparent;min-width:100px;")
        self._btn_next.clicked.connect(self._next)
        self._btn_reset.clicked.connect(self._reset_zoom)
        self._btn_info.clicked.connect(self._show_info_dialog)
        self._btn_measured.clicked.connect(self._go_to_measured_point)
        nav.addWidget(self._btn_prev)
        nav.addWidget(self._lbl_ch, 1)
        nav.addWidget(self._btn_next)
        nav.addWidget(self._btn_reset)
        nav.addWidget(self._btn_measured)
        nav.addWidget(self._btn_info)
        lay.addWidget(nav_frame)

        # Section slider
        slider_frame = QtWidgets.QFrame()
        slider_frame.setStyleSheet(
            "QFrame{background:#F1F5F9;border-bottom-width:1px;border-bottom-style:solid;"
            "border-bottom-color:#E2E8F0;padding:2px;}")
        slider_lay = QtWidgets.QHBoxLayout(slider_frame)
        slider_lay.setContentsMargins(8, 2, 8, 2); slider_lay.setSpacing(6)
        self._lbl_slider_ch = QtWidgets.QLabel("Ch:")
        lbl_slider = self._lbl_slider_ch
        lbl_slider.setStyleSheet("color:#475569;font-size:8.5pt;")
        self._slider_ch = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._slider_ch.setRange(0, 0)
        self._slider_ch.setValue(0)
        self._slider_ch.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self._slider_ch.setStyleSheet(
            "QSlider::groove:horizontal{height:4px;background:#CBD5E1;border-radius:2px;}"
            "QSlider::handle:horizontal{width:14px;height:14px;background:#0F4C81;"
            "border-radius:7px;margin:-5px 0;}"
            "QSlider::handle:horizontal:hover{background:#1D4ED8;}")
        self._slider_ch.valueChanged.connect(self._on_slider_changed)
        self._lbl_slider_val = QtWidgets.QLabel("--")
        self._lbl_slider_val.setStyleSheet("color:#0F4C81;font-size:8.5pt;font-weight:600;min-width:60px;")
        slider_lay.addWidget(lbl_slider)
        slider_lay.addWidget(self._slider_ch, 1)
        slider_lay.addWidget(self._lbl_slider_val)
        lay.addWidget(slider_frame)

        # Warning track ??dots show warning-section positions along chainage
        self._warn_track = _WarningTrack()
        self._warn_track.jumped.connect(self._on_warn_jump)
        self._warn_track.setToolTip("Red = CRITICAL  |  Amber = CAUTION  |  Click to jump to section")
        lay.addWidget(self._warn_track)

        # Warning banner ??large coloured label for current section status
        self._warn_banner = QtWidgets.QLabel()
        self._warn_banner.setAlignment(QtCore.Qt.AlignCenter)
        self._warn_banner.setMinimumHeight(34)
        self._warn_banner.setVisible(False)
        lay.addWidget(self._warn_banner)

        if _MPL_OK:
            self._fig = Figure(figsize=(7.5, 6.5), facecolor=_BG)
            self._ax  = self._fig.add_subplot(111)
            self._canvas = FigureCanvas(self._fig)
            self._canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
            lay.addWidget(self._canvas, 1)
            # Matplotlib navigation toolbar (zoom/pan)
            from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
            self._toolbar = NavigationToolbar2QT(self._canvas, self)
            self._toolbar.setStyleSheet(
                "QToolBar{background:#1E3A5F;border-top:2px solid #0F4C81;spacing:2px;padding:2px 4px;}"
                "QToolButton{background:#2D5A8E;border:1px solid #3B7DD8;border-radius:4px;"
                "padding:4px 6px;margin:1px;color:white;font-size:9pt;min-width:26px;min-height:22px;}"
                "QToolButton:hover{background:#3B7DD8;border-color:#60A5FA;}"
                "QToolButton:checked{background:#1D4ED8;border-color:#93C5FD;}")
            self._toolbar.setIconSize(QtCore.QSize(16, 16))
            lay.addWidget(self._toolbar)
        else:
            self._mpl_missing_label = QtWidgets.QLabel("Matplotlib is required for 2D cross-section plotting.")
            lay.addWidget(self._mpl_missing_label)
        # Times overlay + animation controls
        ctrl = QtWidgets.QHBoxLayout(); ctrl.setSpacing(6)
        self._chk_overlay = QtWidgets.QCheckBox("Show T0 overlay")
        self._chk_overlay.setStyleSheet("color:#0F172A;font-size:9pt;font-weight:600;")
        self._chk_overlay.setToolTip("Overlay reference times T0 on current section")
        self._chk_overlay.toggled.connect(self._refresh)
        self._anim_label = "Animate"
        self._stop_label = "Stop"
        self._btn_anim = QtWidgets.QPushButton("Animate")
        self._btn_anim.setStyleSheet(
            "QPushButton{background:#7C3AED;color:white;border-radius:5px;"
            "padding:4px 12px;font-weight:700;font-size:9pt;border:none;}"
            "QPushButton:hover{background:#6D28D9;}"
            "QPushButton:checked{background:#5B21B6;}")
        self._btn_anim.setCheckable(True)
        self._btn_anim.setToolTip("Animate deformation T0 -> Tn")
        self._btn_anim.toggled.connect(self._toggle_animation)
        self._lbl_deform_scale = QtWidgets.QLabel("Visual scale")
        self._lbl_deform_scale.setStyleSheet("color:#334155;font-size:8.5pt;font-weight:600;")
        self._sp_deform_scale = QtWidgets.QDoubleSpinBox()
        self._sp_deform_scale.setRange(1.0, 100.0)
        self._sp_deform_scale.setDecimals(0)
        self._sp_deform_scale.setSingleStep(5.0)
        self._sp_deform_scale.setValue(10.0)
        self._sp_deform_scale.setSuffix("x")
        self._sp_deform_scale.setFixedWidth(72)
        self._sp_deform_scale.setToolTip("Visual-only deformation magnification for T0/Tn overlay and animation. Measurements stay real.")
        self._sp_deform_scale.valueChanged.connect(self._refresh)
        self._btn_scale_1x = QtWidgets.QPushButton("1x")
        self._btn_scale_10x = QtWidgets.QPushButton("10x")
        for _btn in (self._btn_scale_1x, self._btn_scale_10x):
            _btn.setFixedWidth(42)
            _btn.setStyleSheet("QPushButton{background:#EEF2FF;color:#3730A3;border:1px solid #C7D2FE;border-radius:4px;padding:3px 6px;font-weight:700;} QPushButton:hover{background:#E0E7FF;}")
        self._btn_scale_1x.setToolTip("Show real section deformation scale")
        self._btn_scale_10x.setToolTip("Chỉ phóng đại để nhìn rõ, số đo không đổi (visual x10).")
        self._btn_scale_1x.clicked.connect(lambda: self._set_visual_deformation_scale(1.0))
        self._btn_scale_10x.clicked.connect(lambda: self._set_visual_deformation_scale(10.0))
        self._anim_timer = QtCore.QTimer()
        self._anim_timer.setInterval(80)
        self._anim_timer.timeout.connect(self._anim_step)
        self._anim_alpha = 0.0; self._anim_dir = 1
        self._ref_sections: List[SectionGeometry] = []
        # Multi-times overlay: one section-list per loaded times (T0..Tn) plus a
        # parallel list of display labels. Drawn as coloured outlines when >2
        # times are loaded and the overlay checkbox is on. Empty in the normal
        # single/two-scan workflow.
        self._epoch_sections: List[List[SectionGeometry]] = []
        self._times_labels: List[str] = []
        self._trend_hotspots: list = []
        self._show_measured_points: bool = True
        self._measured_point_labels: set = set()
        # Per-section (status, issues) from classify_sections ??the SAME robust
        # intra-dataset classifier used by the chainage ruler, 3D markers and
        # dashboard. Computed in _update_warn_track so the 2D banner/title agree
        # with every other view (avoids "2D says CRITICAL but ruler shows OK").
        self._section_statuses: list = []
        ctrl.addWidget(self._chk_overlay)
        ctrl.addWidget(self._btn_anim)
        ctrl.addWidget(self._lbl_deform_scale)
        ctrl.addWidget(self._sp_deform_scale)
        ctrl.addWidget(self._btn_scale_1x)
        ctrl.addWidget(self._btn_scale_10x)
        ctrl.addStretch()
        lay.addLayout(ctrl)
        # Hide the whole deformation-control row by default (kept, not deleted).
        # When hidden the overlay stays off: the checkbox can't be toggled and
        # is never auto-checked, so _draw_section skips the overlay drawing.
        self._show_deform_controls = SHOW_DEFORM_CONTROLS
        if not self._show_deform_controls:
            for _w in (self._chk_overlay, self._btn_anim):
                _w.setVisible(False)
        self._info_label = QtWidgets.QLabel("Run Step 6.3 to display section parameters.")
        self._info_label.setWordWrap(True)
        self._info_label.setStyleSheet(
            "color:#475569; font-family:monospace; font-size:9pt; "
            "padding:4px 6px; background:#F8FAFC; border-top:1px solid #E2E8F0;")
        self._info_label.setMinimumHeight(24)
        self._info_label.setMaximumHeight(78)
        lay.addWidget(self._info_label, 0)
        self._draw_empty()

    def retranslate(self, translate: Callable[[str], str]) -> None:
        """Update static 2D-section widget labels when the app language changes."""
        self._anim_label = translate("Animate")
        self._stop_label = translate("Stop")
        self._translate = translate
        self._btn_prev.setText("\u25C0 " + translate("Prev"))
        self._btn_next.setText(translate("Next") + " \u25B6")
        self._btn_reset.setText("\u27F3 " + translate("Zoom"))
        self._btn_reset.setToolTip(translate("Reset zoom (R)"))
        self._btn_info.setText("\u24d8 " + translate("Info"))
        self._btn_info.setToolTip(translate("Show section parameters"))
        if self._lbl_ch.text() in ("Ch: --", translate("Ch: --")):
            self._lbl_ch.setText(translate("Ch: --"))
        self._lbl_slider_ch.setText(translate("Ch:"))
        self._chk_overlay.setText(translate("Show T0 overlay"))
        self._chk_overlay.setToolTip(translate("Overlay reference times T0 on current section"))
        self._btn_anim.setText(self._stop_label if self._btn_anim.isChecked() else self._anim_label)
        self._btn_anim.setToolTip(translate("Animate deformation T0 -> Tn"))
        self._lbl_deform_scale.setText(translate("Visual scale"))
        self._sp_deform_scale.setToolTip(translate("Visual-only deformation magnification for T0/Tn overlay and animation. Measurements stay real."))
        if hasattr(self, "_mpl_missing_label"):
            self._mpl_missing_label.setText(translate("Matplotlib is required for 2D cross-section plotting."))
        if not self._sections:
            self._info_label.setText(translate("Run Step 6.3 to display section parameters."))

    def set_ref_sections(self, sections) -> None:
        self._ref_sections = sections
        self._update_warn_track()
        self._update_deform_controls_enabled()

    def set_epoch_sections(self, epoch_sections, labels) -> None:
        """Register per-times section lists (T0..Tn) for the coloured overlay.

        Each item in epoch_sections is a full per-chainage section list for one
        times, aligned by index with the current Tn sections. When set, the
        overlay checkbox draws one coloured outline per times at the active
        chainage instead of the single T0 reference scatter.
        """
        self._epoch_sections = epoch_sections or []
        self._times_labels = labels or []
        self._update_deform_controls_enabled()
        self._update_warn_track()   # recompute worst-per-section across times
        self._refresh()
        self._refresh()

    # ------------------------------------------------------------------
    def _on_warn_jump(self, idx: int) -> None:
        """Jump to a warning section when the user clicks its dot on the track."""
        if 0 <= idx < len(self._sections):
            self._idx = idx
            if hasattr(self, "_slider_ch"):
                self._slider_ch.setValue(idx)
            self._refresh()

    def set_trend_hotspots(self, hotspots) -> None:
        """Set p95 trend hotspot markers from the multi-times chart.

        Each hotspot is a dict with chainage_m, angle_deg, label and value_mm.
        They are visual hints only: the trend point is a percentile aggregate,
        so the marker shows a representative corepoint nearest that percentile.
        """
        self._trend_hotspots = list(hotspots or [])
        if hasattr(self, "_btn_measured"):
            self._btn_measured.setEnabled(bool(self._trend_hotspots))
        self._jump_to_active_hotspot()
        self._refresh()

    def set_measured_points_visible(self, visible: bool, labels=None) -> None:
        self._show_measured_points = bool(visible)
        self._measured_point_labels = set(labels or [])
        if hasattr(self, "_btn_measured"):
            self._btn_measured.setVisible(bool(visible))
        self._refresh()

    def _epoch_index_for_label(self, label: str) -> Optional[int]:
        """Return the epoch_sections index for a Step 6 label like T1/T5."""
        label = str(label or "")
        labels = [str(v) for v in (getattr(self, "_times_labels", []) or [])]
        if label in labels:
            return labels.index(label)
        if label.upper().startswith("T"):
            try:
                idx = int(label[1:])
                if 0 <= idx < len(getattr(self, "_epoch_sections", []) or []):
                    return idx
            except Exception:
                pass
        return None

    def _crown_marker_point_for_epoch(self, epoch_idx: int, z_display_shift: float):
        """Return a crown marker located on the same displayed outline line."""
        if not getattr(self, "_epoch_sections", None):
            return None
        if epoch_idx is None or epoch_idx < 0 or epoch_idx >= len(self._epoch_sections):
            return None
        secs = self._epoch_sections[epoch_idx]
        if self._idx >= len(secs) or secs[self._idx] is None:
            return None
        pts = getattr(secs[self._idx], "pts_2d", None)
        if pts is None:
            return None
        pts = np.asarray(pts, dtype=np.float64)
        pts = pts[np.isfinite(pts).all(axis=1)]
        if len(pts) < 8:
            return None

        ref0 = None
        if self._epoch_sections and len(self._epoch_sections[0]) > self._idx:
            ref0 = self._epoch_sections[0][self._idx]
        if str(getattr(self, "_section_render_mode", "")).lower().startswith("field") or epoch_idx == 0:
            pv = pts
        else:
            pv, _ = self._amplify_points_for_display(pts, ref0, alpha=1.0)

        out = self._robust_non_circular_outline(pv)
        if out is None:
            return None
        ox, oz = out

        if epoch_idx > 0 and ref0 is not None and str(getattr(self, "_section_render_mode", "")).lower().startswith("field"):
            scale = self._visual_deformation_scale()
            if scale > 1.0:
                try:
                    ref_pts = np.asarray(ref0.pts_2d, dtype=np.float64)
                    cur_pts = np.asarray(pts, dtype=np.float64)
                    ref_mask = self._robust_display_mask(ref_pts[:, 0], ref_pts[:, 1])
                    cur_mask = self._robust_display_mask(cur_pts[:, 0], cur_pts[:, 1])
                    rz = ref_pts[ref_mask, 1] if np.count_nonzero(ref_mask) >= 16 else ref_pts[:, 1]
                    cz = cur_pts[cur_mask, 1] if np.count_nonzero(cur_mask) >= 16 else cur_pts[:, 1]
                    ref_crown = float(np.nanpercentile(rz, 98.0))
                    cur_floor = float(np.nanpercentile(cz, 8.0))
                    cur_crown = float(np.nanpercentile(cz, 98.0))
                    dz_crown = cur_crown - ref_crown
                    height = max(0.25, cur_crown - cur_floor)
                    crown_weight = np.clip((oz - cur_floor) / height, 0.0, 1.0)
                    oz = oz + (scale - 1.0) * dz_crown * crown_weight
                except Exception:
                    pass
        if self._profile != "Circle" or str(getattr(self, "_section_render_mode", "")).lower().startswith("field"):
            oz = oz + z_display_shift

        finite = np.isfinite(ox) & np.isfinite(oz)
        if not np.any(finite):
            return None
        ox = ox[finite]
        oz = oz[finite]
        crown_cut = float(np.nanpercentile(oz, 97.0))
        crown_band = oz >= crown_cut
        if np.count_nonzero(crown_band) < 1:
            idx = int(np.nanargmax(oz))
        else:
            target_x = float(np.nanmedian(ox[crown_band]))
            band_idxs = np.flatnonzero(crown_band)
            idx = int(band_idxs[int(np.nanargmin(np.abs(ox[band_idxs] - target_x)))])
        return float(ox[idx]), float(oz[idx])

    def _go_to_measured_point(self) -> None:
        self._jump_to_active_hotspot()

    def set_section_index(self, idx: int) -> None:
        if not self._sections:
            return
        idx = max(0, min(int(idx), len(self._sections) - 1))
        self._idx = idx
        if hasattr(self, "_slider_ch"):
            self._slider_ch.blockSignals(True)
            self._slider_ch.setValue(idx)
            self._slider_ch.blockSignals(False)
        self._refresh()

    def jump_to_chainage(self, chainage_m: float) -> None:
        if not self._sections:
            return
        try:
            ch = float(chainage_m)
        except Exception:
            return
        chs = np.asarray([getattr(s, "chainage", np.nan) for s in self._sections], dtype=np.float64)
        finite = np.isfinite(chs)
        if not np.any(finite):
            return
        finite_idxs = np.flatnonzero(finite)
        idx = int(finite_idxs[int(np.nanargmin(np.abs(chs[finite] - ch)))])
        self.set_section_index(idx)

    def _jump_to_active_hotspot(self) -> None:
        hotspots = list(getattr(self, "_trend_hotspots", []) or [])
        if not hotspots or not self._sections:
            return
        def _score(hp):
            try:
                return abs(float(hp.get("value_mm", hp.get("p95_abs_mm", 0.0))))
            except Exception:
                return 0.0
        hp = max(hotspots, key=_score)
        self.jump_to_chainage(hp.get("chainage_m", np.nan))

    def set_section_render_mode(self, mode: str) -> None:
        """Set 2D section rendering mode without changing measurement profile."""
        mode = str(mode or "Field Robust")
        self._section_render_mode = mode
        self._refresh()

    def _update_warn_track(self) -> None:
        """Rebuild the warning track dots from current sections + ref_sections.

        Uses ``classify_sections()`` ??the same classifier as the chainage
        ruler and 3D markers ??so all three views are always consistent.
        """
        if not self._sections:
            self._warn_track.set_marks([])
            self._section_statuses = []
            return
        n = len(self._sections)
        statuses = classify_sections(self._sections, self._ref_sections,
                                     epoch_sections=self._epoch_sections)
        # Cache for the 2D banner / title / info-dialog so they agree with the
        # ruler, 3D markers and dashboard (single source of truth).
        self._section_statuses = statuses
        marks = []
        for i, (status, issues) in enumerate(statuses):
            if status == "OK":
                continue
            frac = i / max(n - 1, 1)
            color = "#DC2626" if status == "CRITICAL" else "#D97706"
            try:
                detail = section_warning_text(issues, limit=2)
            except Exception:
                detail = status
            label = f"Ch {self._sections[i].chainage:.2f}m  [{status}]\n{detail}"
            marks.append((frac, color, label, i))
        self._warn_track.set_marks(marks)

    def _status_for_idx(self, idx: int):
        """(status, issues) for section *idx* from the shared classifier.

        Falls back to per-section section_warning_status only if the cached
        list is missing/stale (e.g. before _update_warn_track has run).
        """
        if 0 <= idx < len(self._section_statuses):
            return self._section_statuses[idx]
        sg = self._sections[idx] if 0 <= idx < len(self._sections) else None
        ref = (self._ref_sections[idx]
               if 0 <= idx < len(self._ref_sections) else None)
        if sg is None:
            return "OK", []
        return section_warning_status(sg, ref)

    def _toggle_animation(self, checked: bool) -> None:
        if checked:
            self._anim_alpha = 0.0; self._anim_dir = 1
            self._btn_anim.setText(self._stop_label); self._anim_timer.start()
        else:
            self._anim_timer.stop(); self._btn_anim.setText(self._anim_label); self._refresh()

    def _anim_step(self) -> None:
        self._anim_alpha += 0.05 * self._anim_dir
        if self._anim_alpha >= 1.0: self._anim_alpha = 1.0; self._anim_dir = -1
        elif self._anim_alpha <= 0.0: self._anim_alpha = 0.0; self._anim_dir = 1
        if not _MPL_OK or not self._sections: return
        sg_n = self._sections[self._idx]
        sg_0 = self._ref_sections[self._idx] if self._ref_sections and self._idx < len(self._ref_sections) else None
        self._draw_section(sg_n, ref_sg=sg_0, alpha=self._anim_alpha)

    def _reset_zoom(self) -> None:
        """Reset matplotlib view to fit the full section."""
        if not _MPL_OK: return
        self._ax.autoscale()
        self._ax.set_aspect("equal", adjustable="box")
        self._canvas.draw_idle()

    def _visual_deformation_scale(self) -> float:
        if hasattr(self, "_sp_deform_scale"):
            return max(1.0, float(self._sp_deform_scale.value()))
        return 1.0

    def _set_visual_deformation_scale(self, scale: float) -> None:
        if hasattr(self, "_sp_deform_scale"):
            self._sp_deform_scale.setValue(float(scale))
        self._refresh()

    def _amplify_points_for_display(self, pts2d: np.ndarray, ref_sg, alpha: float) -> tuple[np.ndarray, bool]:
        """Return visual-only amplified Tn points against T0 by polar radius.

        There is no point-to-point correspondence between section clouds, so the
        display approximation compares Tn radius to the median T0 radius at the
        same polar angle. This makes small mm-level deformation visible without
        changing any measured section parameters.
        """
        scale = self._visual_deformation_scale()
        if scale <= 1.0 or ref_sg is None or ref_sg.pts_2d is None or len(ref_sg.pts_2d) < 16:
            return pts2d, False
        ref = np.asarray(ref_sg.pts_2d, dtype=np.float64)
        ref = ref[np.isfinite(ref).all(axis=1)]
        pts = np.asarray(pts2d, dtype=np.float64)
        if len(ref) < 16 or len(pts) < 4:
            return pts2d, False

        n_bins = 720
        theta_ref = (np.arctan2(ref[:, 1], ref[:, 0]) + 2.0 * np.pi) % (2.0 * np.pi)
        r_ref = np.hypot(ref[:, 0], ref[:, 1])
        bins = np.floor(theta_ref / (2.0 * np.pi) * n_bins).astype(np.int64)
        med = np.full(n_bins, np.nan, dtype=np.float64)
        for b in np.unique(bins):
            med[b] = float(np.nanmedian(r_ref[bins == b]))
        good = np.flatnonzero(np.isfinite(med))
        if len(good) < 8:
            return pts2d, False
        x_good = np.r_[good - n_bins, good, good + n_bins]
        y_good = np.r_[med[good], med[good], med[good]]

        theta = (np.arctan2(pts[:, 1], pts[:, 0]) + 2.0 * np.pi) % (2.0 * np.pi)
        r = np.hypot(pts[:, 0], pts[:, 1])
        pos = theta / (2.0 * np.pi) * n_bins
        r0 = np.interp(pos, x_good, y_good)
        scale_eff = 1.0 + (scale - 1.0) * max(0.0, min(1.0, float(alpha)))
        r_vis = r0 + (r - r0) * scale_eff
        out = np.column_stack([r_vis * np.cos(theta), r_vis * np.sin(theta)])
        return out, True

    @staticmethod
    def _robust_display_mask(x: np.ndarray, z: np.ndarray) -> np.ndarray:
        """Mask extreme 2D section points for display only.

        Keeps the plotted cross-section readable by removing sparse spikes from
        scan noise, clutter, or registration leftovers. Measurement values still
        come from the original SectionGeometry data.
        """
        x = np.asarray(x, dtype=np.float64)
        z = np.asarray(z, dtype=np.float64)
        finite = np.isfinite(x) & np.isfinite(z)
        if finite.sum() < 16:
            return finite
        xf = x[finite]; zf = z[finite]
        x0, x1 = np.percentile(xf, [0.5, 99.5])
        z0, z1 = np.percentile(zf, [0.5, 99.5])
        cx = float(np.median(xf)); cz = float(np.median(zf))
        r = np.hypot(xf - cx, zf - cz)
        r_med = float(np.median(r))
        mad = float(np.median(np.abs(r - r_med)))
        r_hi = np.percentile(r, 99.2) if mad <= 1e-9 else min(np.percentile(r, 99.5), r_med + 5.0 * 1.4826 * mad)
        keep_f = (xf >= x0) & (xf <= x1) & (zf >= z0) & (zf <= z1) & (r <= r_hi)
        out = np.zeros(len(x), dtype=bool)
        out[np.flatnonzero(finite)] = keep_f
        return out

    @staticmethod
    def _smooth_outline_series(values: np.ndarray, window: int = 5) -> np.ndarray:
        """Small rolling-median smoother for display-only section outlines."""
        arr = np.asarray(values, dtype=np.float64).copy()
        if arr.size < 3 or window <= 1:
            return arr
        window = int(max(3, window if window % 2 == 1 else window + 1))
        half = window // 2
        out = arr.copy()
        for i in range(arr.size):
            lo = max(0, i - half)
            hi = min(arr.size, i + half + 1)
            vals = arr[lo:hi]
            vals = vals[np.isfinite(vals)]
            if vals.size:
                out[i] = float(np.median(vals))
        return out


    @staticmethod
    def _despike_outline_series(values: np.ndarray, window: int = 11, sigma: float = 2.5) -> np.ndarray:
        """Replace local outline spikes by the local median, display-only."""
        arr = np.asarray(values, dtype=np.float64).copy()
        if arr.size < 5:
            return arr
        window = int(max(5, window if window % 2 == 1 else window + 1))
        half = window // 2
        out = arr.copy()
        for i in range(arr.size):
            lo = max(0, i - half)
            hi = min(arr.size, i + half + 1)
            vals = arr[lo:hi]
            vals = vals[np.isfinite(vals)]
            if vals.size < 5 or not np.isfinite(arr[i]):
                continue
            med = float(np.median(vals))
            mad = float(np.median(np.abs(vals - med)))
            limit = sigma * 1.4826 * mad if mad > 1e-9 else 0.10
            if abs(float(arr[i]) - med) > max(0.06, limit):
                out[i] = med
        return out

    @staticmethod
    def _fill_outline_nans(values: np.ndarray) -> np.ndarray:
        """Interpolate sparse missing outline bins without inventing endpoints."""
        arr = np.asarray(values, dtype=np.float64).copy()
        good = np.flatnonzero(np.isfinite(arr))
        if good.size == 0:
            return arr
        if good.size == 1:
            arr[:] = arr[good[0]]
            return arr
        bad = ~np.isfinite(arr)
        arr[bad] = np.interp(np.flatnonzero(bad), good, arr[good])
        return arr

    @classmethod
    def _robust_non_circular_outline(cls, pts2d: np.ndarray,
                                     n_x_bins: int = 96,
                                     min_bin_points: int = 4):
        """Display-only robust outline for horseshoe/U/box-like sections.

        Unlike radial outlines, this does not let one extreme ray, pipe, rail,
        or registration leftover pull the plotted section into a spike. It builds
        a closed curve from robust floor, right-wall, crown, and left-wall bands.
        """
        p = np.asarray(pts2d, dtype=np.float64)
        p = p[np.isfinite(p).all(axis=1)]
        if len(p) < max(24, min_bin_points * 6):
            return None
        mask = cls._robust_display_mask(p[:, 0], p[:, 1])
        if np.count_nonzero(mask) >= max(24, min_bin_points * 6):
            p = p[mask]
        x = p[:, 0]
        z = p[:, 1]
        x_lo, x_hi = np.percentile(x, [1.0, 99.0])
        z_lo, z_hi = np.percentile(z, [1.0, 99.0])
        keep = (x >= x_lo) & (x <= x_hi) & (z >= z_lo) & (z <= z_hi)
        if np.count_nonzero(keep) >= max(24, min_bin_points * 6):
            x = x[keep]
            z = z[keep]
        if x.size < max(24, min_bin_points * 6):
            return None

        x_edges = np.linspace(float(np.min(x)), float(np.max(x)), n_x_bins + 1)
        x_mid = 0.5 * (x_edges[:-1] + x_edges[1:])
        floor_z = np.full(n_x_bins, np.nan, dtype=np.float64)
        crown_z = np.full(n_x_bins, np.nan, dtype=np.float64)
        for b in range(n_x_bins):
            m = (x >= x_edges[b]) & (x < x_edges[b + 1] if b < n_x_bins - 1 else x <= x_edges[b + 1])
            if np.count_nonzero(m) < min_bin_points:
                continue
            zb = z[m]
            lo, hi = np.percentile(zb, [2.0, 98.0]) if zb.size >= 10 else (np.min(zb), np.max(zb))
            zb = zb[(zb >= lo) & (zb <= hi)]
            if zb.size < min_bin_points:
                continue
            floor_z[b] = float(np.percentile(zb, 8.0))
            crown_z[b] = float(np.percentile(zb, 97.5))
        if np.isfinite(floor_z).sum() < 8 or np.isfinite(crown_z).sum() < 8:
            return None
        floor_z = cls._fill_outline_nans(floor_z)
        crown_z = cls._fill_outline_nans(crown_z)
        floor_z = cls._despike_outline_series(floor_z, window=13, sigma=2.2)
        crown_z = cls._despike_outline_series(crown_z, window=13, sigma=2.2)
        floor_z = cls._smooth_outline_series(floor_z, window=17)
        crown_z = cls._smooth_outline_series(crown_z, window=17)
        floor_z = cls._smooth_outline_series(floor_z, window=9)
        crown_z = cls._smooth_outline_series(crown_z, window=9)

        # Build a simple stable perimeter from the robust lower and upper
        # envelopes. Do not trace z-binned wall points here: sparse wall/clutter
        # bins can jump across the section and draw vertical spikes through the
        # tunnel interior. The side walls are represented by the two outer edge
        # connections only.
        valid = np.isfinite(floor_z) & np.isfinite(crown_z) & np.isfinite(x_mid)
        if np.count_nonzero(valid) < 8:
            return None
        x_edge = x_mid[valid]
        floor_edge = floor_z[valid]
        crown_edge = crown_z[valid]
        order = np.argsort(x_edge)
        x_edge = x_edge[order]
        floor_edge = floor_edge[order]
        crown_edge = crown_edge[order]

        # Reject bins where the lower/upper envelopes collapsed or crossed.
        height = crown_edge - floor_edge
        h_med = float(np.nanmedian(height)) if height.size else 0.0
        keep_h = height > max(0.20, 0.08 * h_med)
        if np.count_nonzero(keep_h) >= 8:
            x_edge = x_edge[keep_h]
            floor_edge = floor_edge[keep_h]
            crown_edge = crown_edge[keep_h]

        floor = np.column_stack([x_edge, floor_edge])
        right = np.array([[x_edge[-1], floor_edge[-1]], [x_edge[-1], crown_edge[-1]]], dtype=np.float64)
        crown = np.column_stack([x_edge[::-1], crown_edge[::-1]])
        left = np.array([[x_edge[0], crown_edge[0]], [x_edge[0], floor_edge[0]]], dtype=np.float64)
        outline = np.vstack([floor, right, crown, left])
        if len(outline) < 16:
            return None
        return outline[:, 0], outline[:, 1]

    @classmethod
    def _robust_outer_hull_outline(cls, pts2d: np.ndarray):
        """Display-only outer boundary for noisy tunnel sections.

        Multi-time overlays should show the tunnel envelope, not trace pipes,
        rails, sparse ray artifacts, or interior clutter. A robust convex hull
        matches the old clean visual style: smooth arch + side walls + floor
        chord, with no lines pulled through the tunnel interior.
        """
        p = np.asarray(pts2d, dtype=np.float64)
        p = p[np.isfinite(p).all(axis=1)]
        if len(p) < 8:
            return None
        mask = cls._robust_display_mask(p[:, 0], p[:, 1])
        if np.count_nonzero(mask) >= 8:
            p = p[mask]
        if len(p) < 8:
            return None
        x = p[:, 0]
        z = p[:, 1]
        x_lo, x_hi = np.percentile(x, [0.5, 99.5])
        z_lo, z_hi = np.percentile(z, [0.5, 99.5])
        keep = (x >= x_lo) & (x <= x_hi) & (z >= z_lo) & (z <= z_hi)
        if np.count_nonzero(keep) >= 8:
            p = p[keep]
        if len(p) < 8:
            return None
        try:
            from scipy.spatial import ConvexHull
            hull = ConvexHull(p)
            outline = p[hull.vertices]
        except Exception:
            return None
        if len(outline) < 4:
            return None
        center = np.median(outline, axis=0)
        angle = np.arctan2(outline[:, 1] - center[1], outline[:, 0] - center[0])
        order = np.argsort(angle)
        outline = outline[order]
        outline = np.vstack([outline, outline[0]])
        return outline[:, 0], outline[:, 1]

    @staticmethod
    def _radial_outline(pts2d: np.ndarray, n_bins: int = 180):
        """Median-radius boundary curve of a centred section cloud.

        Bins points by polar angle about the origin (the section design centre)
        and takes the median radius per bin, giving a smooth closed outline that
        is robust to stray points ??clearer than a raw scatter when several
        times are overlaid. Returns (x, z) of the closed curve, or None.
        """
        p = np.asarray(pts2d, dtype=np.float64)
        p = p[np.isfinite(p).all(axis=1)]
        if len(p) < 8:
            return None
        theta = np.arctan2(p[:, 1], p[:, 0])
        radius = np.hypot(p[:, 0], p[:, 1])
        edges = np.linspace(-np.pi, np.pi, n_bins + 1)
        idx = np.clip(np.digitize(theta, edges) - 1, 0, n_bins - 1)
        ang_list = []; rad_list = []
        for b in range(n_bins):
            m = idx == b
            if not np.any(m):
                continue
            ang_list.append(0.5 * (edges[b] + edges[b + 1]))
            rad_list.append(float(np.median(radius[m])))
        if len(ang_list) < 8:
            return None
        a = np.asarray(ang_list); r = np.asarray(rad_list)
        ox = r * np.cos(a); oz = r * np.sin(a)
        ox = np.r_[ox, ox[0]]; oz = np.r_[oz, oz[0]]   # close the loop
        return ox, oz

    @staticmethod
    def _radial_profile(pts2d: np.ndarray, edges: np.ndarray) -> np.ndarray:
        """Median radius per fixed angular bin (NaN where empty).

        Same binning as _radial_outline but with caller-supplied edges so two
        clouds (T0 and Tn) align bin-by-bin and their radii can be subtracted to
        get the local radial deviation (used for the per-times Info summary).
        """
        p = np.asarray(pts2d, dtype=np.float64)
        p = p[np.isfinite(p).all(axis=1)]
        n_bins = len(edges) - 1
        prof = np.full(n_bins, np.nan, dtype=np.float64)
        if len(p) < 8:
            return prof
        theta = np.arctan2(p[:, 1], p[:, 0])
        radius = np.hypot(p[:, 0], p[:, 1])
        idx = np.clip(np.digitize(theta, edges) - 1, 0, n_bins - 1)
        for b in range(n_bins):
            m = idx == b
            if np.any(m):
                prof[b] = float(np.median(radius[m]))
        return prof

    def _draw_times_outlines(self, ax, z_display_shift: float) -> None:
        """Draw one coloured median-radius outline per loaded times at _idx.

        T0 is drawn as-is; later times are amplified against T0 (same visual
        scale as the single overlay) so mm-level deformation is visible. Outline
        radii are computed about the origin, then shifted for non-circular
        profiles to match the on-screen scatter.
        """
        self._times_legend_handles = []
        if not self._epoch_sections:
            return
        ref0 = None
        ref_list = self._epoch_sections[0]
        if self._idx < len(ref_list):
            ref0 = ref_list[self._idx]
        drew_any = False
        last_i = len(self._epoch_sections) - 1
        for i, secs in enumerate(self._epoch_sections):
            if self._idx >= len(secs):
                continue
            sgi = secs[self._idx]
            if sgi is None or sgi.pts_2d is None or len(sgi.pts_2d) < 8:
                continue
            pts = np.asarray(sgi.pts_2d, dtype=np.float64)
            if str(getattr(self, "_section_render_mode", "")).lower().startswith("field"):
                # Do not amplify raw section points in field mode: x10 visual
                # scale also magnifies TLS noise and creates jagged outlines.
                # Deformation magnitude is shown by the crown trend/table.
                pv = pts
            elif i == 0:
                pv = pts
            else:
                pv, _ = self._amplify_points_for_display(pts, ref0, alpha=1.0)
            # Field robust outline: never use convex hull first here. Hulls can
            # be pulled by rails/pipes/cables or sparse ray hits, while the
            # binned crown/floor envelope keeps all epochs comparable.
            out = self._robust_non_circular_outline(pv)
            color = _EPOCH_COLORS[i % len(_EPOCH_COLORS)]
            label = self._times_labels[i] if i < len(self._times_labels) else f"T{i}"
            if out is None:
                continue
            ox, oz = out
            if i > 0 and ref0 is not None and str(getattr(self, "_section_render_mode", "")).lower().startswith("field"):
                scale = self._visual_deformation_scale()
                if scale > 1.0:
                    try:
                        ref_pts = np.asarray(ref0.pts_2d, dtype=np.float64)
                        cur_pts = np.asarray(pts, dtype=np.float64)
                        ref_mask = self._robust_display_mask(ref_pts[:, 0], ref_pts[:, 1])
                        cur_mask = self._robust_display_mask(cur_pts[:, 0], cur_pts[:, 1])
                        rz = ref_pts[ref_mask, 1] if np.count_nonzero(ref_mask) >= 16 else ref_pts[:, 1]
                        cz = cur_pts[cur_mask, 1] if np.count_nonzero(cur_mask) >= 16 else cur_pts[:, 1]
                        ref_crown = float(np.nanpercentile(rz, 98.0))
                        cur_floor = float(np.nanpercentile(cz, 8.0))
                        cur_crown = float(np.nanpercentile(cz, 98.0))
                        dz_crown = cur_crown - ref_crown
                        height = max(0.25, cur_crown - cur_floor)
                        crown_weight = np.clip((oz - cur_floor) / height, 0.0, 1.0)
                        oz = oz + (scale - 1.0) * dz_crown * crown_weight
                    except Exception:
                        pass
            if self._profile != "Circle" or str(getattr(self, "_section_render_mode", "")).lower().startswith("field"):
                oz = oz + z_display_shift
            # Clean solid colour per times ??the 2D view only needs to tell the
            # times apart; numbers (dimensions, deviation mm) live in the Info
            # dialog. The latest times is drawn slightly bolder.
            lw = 2.2 if i == last_i else 1.5
            al = 0.95 if i == last_i else 0.8
            ax.plot(ox, oz, color=color, lw=lw, alpha=al, zorder=6)
            self._times_legend_handles.append(mpatches.Patch(color=color, label=label))
            drew_any = True
        if drew_any:
            # The legend itself is emitted by the shared legend block in
            # _draw_section (so a later ax.legend() can't clobber it).
            if self._visual_deformation_scale() > 1.0:
                ax.text(0.02, 0.98,
                        f"Crown visual x{self._visual_deformation_scale():.0f} (measurements true)",
                        transform=ax.transAxes, ha="left", va="top", fontsize=6.5,
                        color="#7C3AED", fontweight="bold",
                        bbox=dict(facecolor="#F5F3FF", edgecolor="#C4B5FD",
                                  boxstyle="round,pad=0.2", alpha=0.95), zorder=11)

    def _show_info_dialog(self) -> None:
        """Show section parameters grouped by engineering purpose."""
        sg = getattr(self, "_current_sg", None)
        if sg is None:
            if not self._sections:
                return
            sg = self._sections[self._idx]
        # T0 reference for the current section (None when no times loaded).
        # Restored: the dialog uses ref_sg throughout (delta_mm, title, mode).
        ref_sg = getattr(self, "_current_ref_sg", None)
        # Consistent with ruler/3D/dashboard via the shared classifier.
        warn_status, warn_issues = self._status_for_idx(self._idx)
        tr = self._translate

        def finite(value: float) -> bool:
            return np.isfinite(value)

        def fmt_m(value: float) -> str:
            return f"{value:.4f} m" if finite(value) else "N/A"

        def fmt_mm(value: float, signed: bool = False) -> str:
            if not finite(value):
                return "N/A"
            return f"{value:+.2f} mm" if signed else f"{value:.2f} mm"

        def fmt_pct(value: float, signed: bool = False) -> str:
            if not finite(value):
                return "N/A"
            return f"{value:+.4f} %" if signed else f"{value:.4f} %"

        def delta_mm(attr: str) -> float:
            if ref_sg is None:
                return float("nan")
            a = getattr(sg, attr, float("nan"))
            b = getattr(ref_sg, attr, float("nan"))
            return (a - b) * 1e3 if finite(a) and finite(b) else float("nan")

        def value_color(is_warn: bool) -> str:
            return "#DC2626" if is_warn else "#0F172A"

        dlg = QtWidgets.QDialog(self.parent() if self.parent() else self)
        title_prefix = "Section Info  |  T0 vs Tn" if ref_sg is not None else "Section Info"
        dlg.setWindowTitle(title_prefix + "  |  Ch. " + f"{sg.chainage:.3f} m")
        dlg.setMinimumWidth(520)
        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        hdr = QtWidgets.QFrame()
        hdr.setStyleSheet("QFrame{background:#0F4C81;padding:10px;}")
        hl = QtWidgets.QVBoxLayout(hdr)
        hl.setContentsMargins(16, 10, 16, 10)
        t1 = QtWidgets.QLabel("Chainage: " + f"{sg.chainage:.3f} m")
        t1.setStyleSheet("color:white;font-size:14pt;font-weight:bold;background:transparent;")
        mode = "T0 vs Tn comparison" if ref_sg is not None else "single-scan geometry"
        view_label = self._section_render_mode if self._section_render_mode else self._profile
        t2 = QtWidgets.QLabel(f"View: {view_label}   |   Profile metadata: {self._profile}   |   Mode: {mode}")
        t2.setStyleSheet("color:#CBD5E1;font-size:10pt;background:transparent;")
        hl.addWidget(t1)
        hl.addWidget(t2)
        lay.addWidget(hdr)

        body = QtWidgets.QWidget()
        body.setStyleSheet("QWidget{background:#F8FAFC;}")
        body_lay = QtWidgets.QVBoxLayout(body)
        body_lay.setContentsMargins(14, 10, 14, 10)
        body_lay.setSpacing(8)

        def add_group(title: str, rows: list[tuple[str, str, str, bool]]) -> None:
            box = QtWidgets.QGroupBox(title)
            box.setStyleSheet(
                "QGroupBox{font-weight:700;color:#1E3A5F;border:1px solid #CBD5E1;"
                "border-radius:6px;margin-top:8px;padding-top:8px;background:#FFFFFF;}"
                "QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;}")
            grid = QtWidgets.QGridLayout(box)
            grid.setContentsMargins(12, 10, 12, 10)
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(6)
            for i, (label, value, tip, is_warn) in enumerate(rows):
                l = QtWidgets.QLabel(label)
                l.setStyleSheet("color:#64748B;font-size:9pt;font-weight:600;background:transparent;")
                l.setToolTip(tip)
                v = QtWidgets.QLabel(value)
                v.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                v.setStyleSheet(
                    f"color:{value_color(is_warn)};font-size:10pt;font-weight:800;"
                    "font-family:monospace;background:transparent;")
                v.setToolTip(tip)
                grid.addWidget(l, i, 0)
                grid.addWidget(v, i, 1)
            body_lay.addWidget(box)

        if warn_issues:
            issue_rows = []
            for level, label, value, unit in warn_issues:
                value_txt = fmt_pct(value, signed=True) if unit == "%" else fmt_mm(value, signed=True)
                issue_rows.append((f"{level}  {label}", value_txt, "This item triggered the section warning.", True))
            add_group("Warning drivers", issue_rows)

        geometry_rows = [
            ("H1  Clear height", fmt_m(sg.H1), "Vertical clearance from floor to crown.", False),
            ("W1  Clear width", fmt_m(sg.W1), "Horizontal clearance between left and right walls.", False),
            ("R   Fitted radius", fmt_m(sg.radius_fit), "Best-fit section radius.", False),
            ("Ovality", fmt_pct(sg.ovality), "Shape distortion. Caution >= 0.5%, critical >= 1.0%.", finite(sg.ovality) and abs(sg.ovality) >= 0.5),
            ("Eccentricity", fmt_mm(sg.eccentricity), "Measured center offset. Caution >= 10 mm, critical >= 25 mm.", finite(sg.eccentricity) and abs(sg.eccentricity) >= 10.0),
        ]
        add_group("Current section geometry", geometry_rows)

        shape_rows = [
            ("H2  Crown height", fmt_m(sg.H2), "Upper arch height from springline to crown.", False),
            ("H3  Invert height", fmt_m(sg.H3), "Lower section height from floor to springline.", False),
            ("W2  Base width", fmt_m(sg.W2), "Width near floor/base level.", False),
            ("Angle L", f"{sg.wall_angle_L:.2f} deg" if finite(sg.wall_angle_L) else "N/A", "Left wall-floor angle.", False),
            ("Angle R", f"{sg.wall_angle_R:.2f} deg" if finite(sg.wall_angle_R) else "N/A", "Right wall-floor angle.", False),
        ]
        add_group("Shape details", shape_rows)

        if ref_sg is not None:
            dw = delta_mm("W1")
            dh = delta_mm("H1")
            dr = delta_mm("radius_fit")
            d_oval = sg.ovality - ref_sg.ovality if finite(sg.ovality) and finite(ref_sg.ovality) else float("nan")
            d_ecc = sg.eccentricity - ref_sg.eccentricity if finite(sg.eccentricity) and finite(ref_sg.eccentricity) else float("nan")
            comparison_rows = [
                ("T0 W1", fmt_m(ref_sg.W1), "Baseline clear width.", False),
                ("Tn-T0 W1", fmt_mm(dw, signed=True), "Negative means convergence / reduced width.", finite(dw) and abs(dw) >= SECTION_DELTA_CAUTION_MM),
                ("T0 H1", fmt_m(ref_sg.H1), "Baseline clear height.", False),
                ("Tn-T0 H1", fmt_mm(dh, signed=True), "Negative means clearance loss / settlement.", finite(dh) and abs(dh) >= SECTION_DELTA_CAUTION_MM),
                ("T0 R", fmt_m(ref_sg.radius_fit), "Baseline fitted radius.", False),
                ("Tn-T0 R", fmt_mm(dr, signed=True), "Negative means radius shrinkage.", finite(dr) and abs(dr) >= SECTION_DELTA_CAUTION_MM),
                ("Tn-T0 ovality", fmt_pct(d_oval, signed=True), "Change in section ovality.", finite(d_oval) and abs(d_oval) >= 0.5),
                ("Tn-T0 eccentricity", fmt_mm(d_ecc, signed=True), "Change in measured center offset.", finite(d_ecc) and abs(d_ecc) >= 10.0),
            ]
            add_group("T0/Tn comparison", comparison_rows)

        # Per-times deformation summary (the info moved off the 2D plot, which
        # now only shows the coloured T0~Tn outlines). One row per times: clear-
        # height change and peak radial deviation vs T0 at this section.
        times_secs = getattr(self, "_epoch_sections", None)
        if times_secs and len(times_secs) > 1:
            edges = np.linspace(-np.pi, np.pi, 181)
            ref_list = times_secs[0]
            r0sg = ref_list[self._idx] if self._idx < len(ref_list) else None
            r0prof = (self._radial_profile(r0sg.pts_2d, edges)
                      if (r0sg is not None and r0sg.pts_2d is not None) else None)
            times_rows = []
            for k, secs in enumerate(times_secs):
                if self._idx >= len(secs):
                    continue
                sgk = secs[self._idx]
                lbl = self._times_labels[k] if k < len(self._times_labels) else f"T{k}"
                if k == 0:
                    times_rows.append((lbl, "baseline (T0)", "Reference times.", False))
                    continue
                dh = ((sgk.H1 - r0sg.H1) * 1e3
                      if (r0sg is not None and finite(sgk.H1) and finite(r0sg.H1)) else float("nan"))
                peak = float("nan")
                if r0prof is not None and sgk.pts_2d is not None:
                    dev = self._radial_profile(sgk.pts_2d, edges) - r0prof
                    if np.isfinite(dev).any():
                        peak = float(dev[np.nanargmax(np.abs(dev))]) * 1e3
                if finite(dh) and finite(peak):
                    val = f"?H1 {dh:+.0f} mm  |  peak {peak:+.0f} mm"
                else:
                    val = fmt_mm(dh, signed=True)
                warn = (finite(peak) and abs(peak) >= 10.0) or (finite(dh) and abs(dh) >= 10.0)
                times_rows.append((lbl, val,
                    "Deformation of this times vs T0 at this section: clear-height "
                    "change and peak radial deviation.", warn))
            if times_rows:
                add_group("Deformation by times (vs T0)", times_rows)

        clearance_rows = [
            ("Clearance min", fmt_m(sg.min_clearance_dist), "Minimum distance to vehicle clearance envelope. Negative means violation.", sg.clearance_violation),
            ("Status", warn_status if warn_status != "OK" else "OK - Within Limits", section_warning_text(warn_issues), warn_status != "OK"),
        ]
        add_group("Safety", clearance_rows)

        lay.addWidget(body)
        btn = QtWidgets.QPushButton(tr("Close"))
        btn.setStyleSheet("QPushButton{background:#0F4C81;color:white;border-radius:0;padding:10px;font-weight:700;font-size:10pt;border:none;}QPushButton:hover{background:#1D4ED8;}")
        btn.clicked.connect(dlg.accept)
        lay.addWidget(btn)
        dlg.exec()

    def _open_fullscreen(self) -> None:
        """Open current section in a resizable full-screen dialog."""
        if not self._sections or not _MPL_OK:
            return
        sg = self._sections[self._idx]
        if sg.pts_2d is None or len(sg.pts_2d) < 4:
            return
        dlg = _SectionFullscreenDialog(sg, self._profile,
                                        self._vl_box_w, self._vl_box_h,
                                        self._vl_cir_r, translate=self._translate,
                                        parent=self)
        dlg.exec()

    def _on_slider_changed(self, value: int) -> None:
        if not self._sections: return
        if value != self._idx:
            self._idx = value
            self._refresh()
        if hasattr(self, "_lbl_slider_val") and self._sections:
            sg = self._sections[self._idx]
            self._lbl_slider_val.setText(f"{sg.chainage:.2f}m")

    def _prev(self) -> None:
        if not self._sections: return
        self._idx = (self._idx - 1) % len(self._sections); self._refresh()

    def _next(self) -> None:
        if not self._sections: return
        self._idx = (self._idx + 1) % len(self._sections); self._refresh()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        key = event.key()
        if key == QtCore.Qt.Key_Left:   self._prev()
        elif key == QtCore.Qt.Key_Right: self._next()
        elif key == QtCore.Qt.Key_Home:
            if self._sections: self._idx = 0; self._refresh()
        elif key == QtCore.Qt.Key_End:
            if self._sections: self._idx = len(self._sections)-1; self._refresh()
        elif key == QtCore.Qt.Key_PageUp:
            if self._sections:
                self._idx = max(0, self._idx - 5); self._refresh()
        elif key == QtCore.Qt.Key_PageDown:
            if self._sections:
                self._idx = min(len(self._sections)-1, self._idx + 5); self._refresh()
        elif key == QtCore.Qt.Key_R:
            self._reset_zoom()
        elif key == QtCore.Qt.Key_A:
            self._toggle_animation(not self._btn_anim.isChecked())
            self._btn_anim.setChecked(not self._btn_anim.isChecked())
        super().keyPressEvent(event)

    def set_sections(self, sections: List[SectionGeometry], profile: str, vl_box_w: float, vl_box_h: float, vl_cir_r: float, render_mode: str = None) -> None:
        self._sections = sections; self._profile = profile
        if render_mode is not None:
            self._section_render_mode = str(render_mode)
        self._vl_box_w = vl_box_w; self._vl_box_h = vl_box_h; self._vl_cir_r = vl_cir_r
        # Land on the FIRST section that actually has 2D points, so the user
        # never opens onto an empty (occluded/sparse) slice. Falls back to 0.
        self._idx = self._first_drawable_index(sections)
        if hasattr(self, "_slider_ch") and sections:
            self._slider_ch.setRange(0, len(sections) - 1)
            self._slider_ch.blockSignals(True)
            self._slider_ch.setValue(self._idx)
            self._slider_ch.blockSignals(False)
        self._ref_sections = []          # clear stale ref until set_ref_sections called
        self._epoch_sections = []        # clear stale multi-times overlay too
        self._times_labels = []
        self._update_warn_track()
        self._update_deform_controls_enabled()
        self._jump_to_active_hotspot()
        self._refresh()

    def _update_deform_controls_enabled(self) -> None:
        """Enable the T0/Tn-only controls (visual scale, animation, overlay)
        only when a T0 reference is loaded.

        "Ph筌ｌ겖g ?猿끸닆雅?nh筌?뀶" amplifies the Tn-vs-T0 deviation; with a single scan
        there is no T0 to compare against, so the control would silently do
        nothing. Disabling it (with an explanatory tooltip) makes that clear
        instead of looking broken.
        """
        has_ref = bool(self._ref_sections) or bool(self._epoch_sections)
        tip_on  = self._translate("Visual-only deformation magnification for "
                                  "T0/Tn overlay and animation. Measurements stay real.")
        tip_off = self._translate("C閭잙끃奎 t閭잙끃弛?T0 (2 l閭잙끃奎 ?湲? ?猿낃펷?ph筌ｌ겖g ?猿끸닆雅?bi閭잙끉諭?d閭잙끃吏괾 "
                                  "Tn so v雅?눘??T0.")
        for w in (getattr(self, "_sp_deform_scale", None),
                  getattr(self, "_btn_scale_1x", None),
                  getattr(self, "_btn_scale_10x", None),
                  getattr(self, "_btn_anim", None),
                  getattr(self, "_chk_overlay", None),
                  getattr(self, "_lbl_deform_scale", None)):
            if w is None:
                continue
            w.setEnabled(has_ref)
            w.setToolTip(tip_on if has_ref else tip_off)
        # Stop any running animation if the reference went away.
        if not has_ref and hasattr(self, "_btn_anim") and self._btn_anim.isChecked():
            self._btn_anim.setChecked(False)

    @staticmethod
    def _first_drawable_index(sections) -> int:
        """Index of the first section with ?? valid 2D points (else 0)."""
        for i, sg in enumerate(sections or []):
            if sg.pts_2d is not None and len(sg.pts_2d) >= 4:
                return i
        return 0

    def _draw_empty(self, reason: str = None) -> None:
        if not _MPL_OK: return
        ax = self._ax; ax.clear(); ax.set_facecolor(_BG)
        if reason:
            msg = reason
            col = "#D97706"   # amber: data exists but this slice is sparse
        elif self._sections:
            # Sections are loaded but the current one has no usable points.
            n_draw = sum(1 for s in self._sections
                         if s.pts_2d is not None and len(s.pts_2d) >= 4)
            msg = (f"Current section has too few valid 2D points.\n\n"
                   f"{n_draw}/{len(self._sections)} sections are drawable. "
                   f"Use the chainage ruler or Prev/Next to inspect another section.")
            col = "#D97706"
        else:
            msg = ("Run Step 6.3: Plot 2D Technical Section\n"
                   "to display tunnel cross-sections and engineering dimensions.")
            col = _FG
        ax.text(0.5, 0.5, msg, ha="center", va="center",
                color=col, fontsize=11, transform=ax.transAxes)
        for s in ax.spines.values(): s.set_color(_GRID)
        ax.tick_params(colors=_FG); self._canvas.draw_idle()

    def _refresh(self) -> None:
        if not _MPL_OK or not self._sections: self._draw_empty(); return
        sg = self._sections[self._idx]
        self._lbl_ch.setText(f"Ch: {sg.chainage:.2f}m  [{self._idx + 1}/{len(self._sections)}]")
        if hasattr(self, "_slider_ch"):
            self._slider_ch.blockSignals(True)
            self._slider_ch.setValue(self._idx)
            self._slider_ch.blockSignals(False)
        if hasattr(self, "_lbl_slider_val"):
            self._lbl_slider_val.setText(f"{sg.chainage:.2f}m")
        self.section_changed.emit(self._idx)
        if sg.pts_2d is None or len(sg.pts_2d) < 4: self._draw_empty(); return
        ref_sg_info = None
        if self._ref_sections and self._idx < len(self._ref_sections):
            ref_sg_info = self._ref_sections[self._idx]
        # Update warning banner for current section
        if hasattr(self, "_warn_banner"):
            _ws, _wi = self._status_for_idx(self._idx)
            if _ws == "CRITICAL":
                self._warn_banner.setText(
                    f"CRITICAL | Ch {sg.chainage:.2f} m | {section_warning_text(_wi, limit=3)}")
                self._warn_banner.setStyleSheet(
                    "background:#DC2626;color:white;font-weight:800;"
                    "font-size:10.5pt;padding:6px 12px;")
                self._warn_banner.setVisible(True)
            elif _ws == "CAUTION":
                self._warn_banner.setText(
                    f"CAUTION | Ch {sg.chainage:.2f} m | {section_warning_text(_wi, limit=3)}")
                self._warn_banner.setStyleSheet(
                    "background:#D97706;color:white;font-weight:800;"
                    "font-size:10.5pt;padding:6px 12px;")
                self._warn_banner.setVisible(True)
            else:
                self._warn_banner.setVisible(False)
        self._current_ref_sg = ref_sg_info
        ref_sg = None
        if hasattr(self, "_chk_overlay") and self._chk_overlay.isChecked() and not self._epoch_sections:
            ref_sg = ref_sg_info
        self._draw_section(sg, ref_sg=ref_sg)

    def _draw_section(self, sg: SectionGeometry, ref_sg=None, alpha: float = 1.0) -> None:
        """Engineering Drawing style v2 - all 5 improvements."""
        from scipy.spatial import ConvexHull
        ax = self._ax
        ax.clear()
        warn_ref_sg = ref_sg if ref_sg is not None else getattr(self, "_current_ref_sg", None)
        # Use the shared classifier result so the 2D banner/border agrees with
        # the ruler / 3D markers / dashboard (consistent CRITICAL/CAUTION/OK).
        warn_status, warn_issues = self._status_for_idx(self._idx)

        # ???? Background & grid ????????????????????????????????????????????????????????????????????????????????????????????
        ax.set_facecolor("#FFFFFF")
        self._fig.patch.set_facecolor("#FFFFFF")
        # Show only the point cloud and measurement dimensions; hide the
        # decorative reference lines (grid, hull, fit circle, radial spokes,
        # clearance envelope, centre cross, ovality ellipse).
        SHOW_OVERLAY_LINES = False
        if SHOW_OVERLAY_LINES:
            ax.grid(True, color="#DDDDDD", lw=0.4, linestyle="--", alpha=0.7, zorder=0)
        else:
            ax.grid(False)
            ax.grid(False, which="both", axis="both")
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color("#888888"); spine.set_linewidth(0.8)
        ax.tick_params(colors="#333333", labelsize=7.5, direction="in", length=3)

        pts2d = sg.pts_2d
        if pts2d is None or len(pts2d) < 4:
            self._draw_empty(); return
        labels = sg.labels if sg.labels is not None and len(sg.labels) == len(pts2d) else np.zeros(len(pts2d), dtype=np.int32)
        finite = np.isfinite(pts2d[:, 0]) & np.isfinite(pts2d[:, 1])
        pts2d  = pts2d[finite]; labels = labels[finite]
        if len(pts2d) < 4:
            self._draw_empty(); return
        pts2d_plot, amplified = self._amplify_points_for_display(pts2d, warn_ref_sg, alpha)
        x = pts2d_plot[:, 0]; z = pts2d_plot[:, 1]
        z_display_shift = 0.0
        field_robust_view = str(getattr(self, "_section_render_mode", "")).lower().startswith("field")
        if self._profile != "Circle" or field_robust_view:
            z_display_shift = -float(np.percentile(z, 1))
            z = z + z_display_shift

        # Cap plotted points: a section can hold >10k points (mean ~6k on
        # real scans); re-scattering all of them every refresh/animation
        # frame stalls the Agg renderer. Geometry was already computed from
        # the full cloud, so this only thins the on-screen display.
        # Display-only robust filter: avoid drawing sparse scan spikes/outliers
        # as part of the 2D shape. Measurements still use full SectionGeometry.
        _display_mask = self._robust_display_mask(x, z)
        if np.count_nonzero(_display_mask) >= 16:
            x = x[_display_mask]; z = z[_display_mask]; labels = labels[_display_mask]

        _MAX_DRAW = 2500
        if len(x) > _MAX_DRAW:
            _sub = np.linspace(0, len(x) - 1, _MAX_DRAW).astype(np.int64)
            x = x[_sub]; z = z[_sub]; labels = labels[_sub]

        # ???? 3. Deviation colormap from best-fit circle ??????????????????????????????????????????
        if self._profile == "Circle":
            r_ref = sg.radius_fit if np.isfinite(sg.radius_fit) else float(np.median(np.hypot(x, z)))
            radii = np.hypot(x, z)
            dev_mm = (radii - r_ref) * 1e3  # mm
            dev_abs = np.abs(dev_mm)
            # green < 1mm, yellow 1-3mm, red > 3mm
            pt_colors = np.where(dev_abs < 1.0, "#16A34A",
                        np.where(dev_abs < 3.0, "#D97706", "#DC2626"))
        else:
            radii = np.hypot(x, z)
            pt_colors = np.full(len(x), "#64748B", dtype=object)

        # ???? 1. Wall/Crown/Floor colour override ????????????????????????????????????????????????????????
        WALL_C   = "#1D4ED8"
        CROWN_C  = "#C2410C"
        FLOOR_C  = "#047857"
        struct_colors = np.where(labels == 1, CROWN_C,
                        np.where(labels == 2, FLOOR_C, WALL_C))
        # blend: use struct color for classified, deviation color for unclassified
        has_labels = np.any(labels != 0)
        final_colors = struct_colors if has_labels else pt_colors

        # Multi-times overlay: draw clean robust outlines when several times are
        # loaded. Controls are hidden in core mode, so Step 6.3 still shows the
        # T0~Tn comparison without exposing extra UI clutter.
        multi_epoch = bool(self._epoch_sections) and (
            (not getattr(self, "_show_deform_controls", True))
            or (hasattr(self, "_chk_overlay") and self._chk_overlay.isChecked()))

        pt_alpha = max(0.3, min(0.75, 0.35 + 0.40 * alpha))
        if not multi_epoch:
            ax.scatter(x, z, c=final_colors, s=2.2, alpha=pt_alpha,
                       linewidths=0, rasterized=True, zorder=2)
        if amplified and not multi_epoch:
            ax.text(0.02, 0.98, f"Visual x{self._visual_deformation_scale():.0f} (measurements true)",
                    transform=ax.transAxes, ha="left", va="top", fontsize=6.5,
                    color="#7C3AED", fontweight="bold",
                    bbox=dict(facecolor="#F5F3FF", edgecolor="#C4B5FD",
                              boxstyle="round,pad=0.2", alpha=0.95), zorder=11)
        # When a T0 reference is loaded the user cares about deformation, not
        # absolute geometry.  Hide the dimension lines / eccentricity / ovality
        # overlays to keep the plot readable; those numbers are still available
        # in the Info dialog.
        _comparing = (ref_sg is not None and ref_sg.pts_2d is not None
                      and len(ref_sg.pts_2d) >= 4)

        # ???? ???Crown settlement arrow ????????????????????????????????????????????????????????????????????????????
        if not multi_epoch and hasattr(sg, "H1") and np.isfinite(sg.H1):
            crown_z = float(np.percentile(z, 97))
            spring_z = float(np.percentile(z, 50))
            if _comparing:
                crown_z0 = float(np.percentile(ref_sg.pts_2d[:, 1], 97))
                dv_mm = (crown_z - crown_z0) * 1e3
                ax.annotate("", xy=(0, crown_z), xytext=(0, crown_z + 0.3),
                    arrowprops=dict(arrowstyle="->", color="#DC2626", lw=2.0),
                    zorder=9)
                ax.text(0.05, crown_z + 0.35, f"dv={dv_mm:.0f}mm",
                    color="#DC2626", fontsize=8, fontweight="bold",
                    bbox=dict(facecolor="white", edgecolor="#DC2626",
                              boxstyle="round,pad=0.2", alpha=0.9), zorder=10)
            else:
                crown_h_mm = (crown_z - spring_z) * 1e3
                ax.text(0.05, crown_z + 0.35, f"crown h={crown_h_mm:.0f}mm",
                    color="#475569", fontsize=8, fontweight="bold",
                    bbox=dict(facecolor="white", edgecolor="#94A3B8",
                              boxstyle="round,pad=0.2", alpha=0.9), zorder=10)

        # ???? ???Convergence arrows ??????????????????????????????????????????????????????????????????????????????????????
        # Convergence (delta-h) is a deformation that only has meaning across
        # two times (T0 vs Tn); on a single scan it was just the absolute width,
        # which misleads. Hidden here; set SHOW_CONVERGENCE = True to restore.
        SHOW_CONVERGENCE = False
        if SHOW_CONVERGENCE and hasattr(sg, "W1") and np.isfinite(sg.W1):
            mid_z = float(np.percentile(z, 50))
            left_x  = float(np.percentile(x, 2))
            right_x = float(np.percentile(x, 98))
            dh_mm = (right_x - left_x) * 1e3
            # Left arrow pointing right
            ax.annotate("", xy=(left_x + 0.25, mid_z),
                xytext=(left_x, mid_z),
                arrowprops=dict(arrowstyle="->", color="#1D4ED8", lw=2.0), zorder=9)
            # Right arrow pointing left
            ax.annotate("", xy=(right_x - 0.25, mid_z),
                xytext=(right_x, mid_z),
                arrowprops=dict(arrowstyle="->", color="#1D4ED8", lw=2.0), zorder=9)
            ax.text(0.0, mid_z + 0.15, f"???{dh_mm:.0f}mm",
                color="#1D4ED8", fontsize=8, fontweight="bold", ha="center",
                bbox=dict(facecolor="white", edgecolor="#1D4ED8",
                          boxstyle="round,pad=0.2", alpha=0.9), zorder=10)

        if self._profile == "Circle" and not _comparing and not multi_epoch:
            # ???? e Eccentricity: measured center dot (single-scan only) ??????????
            try:
                _A = np.column_stack([x, z, np.ones(len(x))])
                _b = x * x + z * z
                _sol, _, _, _ = np.linalg.lstsq(_A, _b, rcond=None)
                cx_meas = float(_sol[0] / 2.0); cz_meas = float(_sol[1] / 2.0)
                if not (np.isfinite(cx_meas) and np.isfinite(cz_meas)):
                    cx_meas = float(np.mean(x)); cz_meas = float(np.mean(z))
            except Exception:
                cx_meas = float(np.mean(x)); cz_meas = float(np.mean(z))
            ax.plot(cx_meas, cz_meas, "D", color="#7C3AED", ms=7, zorder=10,
                    label=f"C_meas")
            ax.plot(0, 0, "+", color="#64748B", ms=10, mew=2, zorder=10,
                    label="C_design")
            ecc_mm = np.sqrt(cx_meas**2 + cz_meas**2) * 1e3
            if ecc_mm > 1.0:
                ax.plot([0, cx_meas], [0, cz_meas], "--",
                    color="#7C3AED", lw=1.2, alpha=0.7, zorder=8)
                ax.text(cx_meas/2, cz_meas/2 + 0.1, f"e={ecc_mm:.0f}mm",
                    color="#7C3AED", fontsize=7.5, ha="center",
                    bbox=dict(facecolor="white", edgecolor="#7C3AED",
                              boxstyle="round,pad=0.15", alpha=0.85), zorder=10)

            # ???? ??Ovality: show fitted ellipse (single-scan only) ????????????????????
            a_semi = float(np.max(np.abs(x)))
            b_semi = float(np.max(np.abs(z)))
            if a_semi > 0.1 and b_semi > 0.1:
                theta_e = np.linspace(0, 2*np.pi, 100)
                ex = a_semi * np.cos(theta_e)
                ez = b_semi * np.sin(theta_e)
                ax.plot(ex, ez, "--", color="#D97706", lw=1.2, alpha=0.6,
                        zorder=3, label=f"Ovality {sg.ovality:.1f}%")

        # Multi-times coloured outlines (T0~Tn). Deviation is mm-scale on a
        # metre-scale radius, so each times is amplified against T0 by the same
        # visual-scale factor as the single overlay; measurements stay real.
        if multi_epoch:
            self._draw_times_outlines(ax, z_display_shift)

        # T0 reference overlay

        if ref_sg is not None and ref_sg.pts_2d is not None and len(ref_sg.pts_2d) >= 4:
            rx = ref_sg.pts_2d[:, 0]; rz = ref_sg.pts_2d[:, 1]
            if z_display_shift != 0.0:
                rz = rz + z_display_shift
            ref_mask = self._robust_display_mask(rx, rz)
            if np.count_nonzero(ref_mask) >= 16:
                rx = rx[ref_mask]; rz = rz[ref_mask]
            ref_alpha = max(0.15, 0.55 * (1.0 - alpha))
            ax.scatter(rx, rz, c="#94A3B8", s=1.5, alpha=ref_alpha,
                       linewidths=0, rasterized=True, zorder=1, label="T0 reference")
            if self._profile == "Circle" and np.isfinite(ref_sg.radius_fit):
                ax.add_patch(plt.Circle((0.0, 0.0), ref_sg.radius_fit,
                    fill=False, edgecolor="#94A3B8", lw=1.2, ls=":", alpha=0.7,
                    zorder=2, label=f"T0 R={ref_sg.radius_fit:.3f}m"))
            if np.isfinite(sg.radius_fit) and np.isfinite(ref_sg.radius_fit):
                dr = (sg.radius_fit - ref_sg.radius_fit) * 1e3
                for ang_deg in [0, 90, 180, 270]:
                    rad = math.radians(ang_deg)
                    ax.annotate("", xy=(sg.radius_fit*math.cos(rad), sg.radius_fit*math.sin(rad)),
                        xytext=(ref_sg.radius_fit*math.cos(rad), ref_sg.radius_fit*math.sin(rad)),
                        arrowprops=dict(arrowstyle="->",
                            color="#DC2626" if dr < 0 else "#16A34A", lw=1.5), zorder=8)
                col = "#DC2626" if dr < 0 else "#16A34A"
                lbl = "convergence" if dr < 0 else "expansion"
                ax.text(0.01, 0.01, f"?R = {dr:+.1f} mm ({lbl})",
                    transform=ax.transAxes, fontsize=8, color=col, fontweight="bold",
                    bbox=dict(facecolor="white", edgecolor="#CBD5E1",
                    boxstyle="round,pad=0.3", alpha=0.9), zorder=10)

        # ???? 2. Convex hull outline ??????????????????????????????????????????????????????????????????????????????????
        if SHOW_OVERLAY_LINES and len(pts2d) >= 4:
            try:
                hull = ConvexHull(pts2d)
                hull_pts = pts2d[hull.vertices]
                hull_pts = np.vstack([hull_pts, hull_pts[0]])
                ax.plot(hull_pts[:, 0], hull_pts[:, 1],
                        color="#475569", lw=1.0, ls="-", alpha=0.5,
                        zorder=3, label="Section outline")
            except Exception:
                pass

        # ???? Best-fit circle ????????????????????????????????????????????????????????????????????????????????????????????????
        if SHOW_OVERLAY_LINES and self._profile == "Circle" and np.isfinite(sg.radius_fit):
            fit_c = plt.Circle((0.0, 0.0), sg.radius_fit,
                               fill=False, edgecolor="#2563EB", lw=1.6,
                               ls="--", alpha=0.9, zorder=4,
                               label=f"Best-fit R={sg.radius_fit:.3f}m")
            ax.add_patch(fit_c)

        # ???? 4. Radial lines every 30筌?????????????????????????????????????????????????????????????????????????????
        r_max = float(np.percentile(radii, 97)) * 1.05
        for deg in (range(0, 360, 30) if SHOW_OVERLAY_LINES else ()):
            rad = math.radians(deg)
            ax.plot([0, r_max * math.cos(rad)], [0, r_max * math.sin(rad)],
                    color="#CCCCCC", lw=0.5, ls=":", zorder=1, alpha=0.7)
            # label at 45/135/225/315
            if deg % 90 == 45:
                ax.text(r_max * 1.05 * math.cos(rad),
                        r_max * 1.05 * math.sin(rad),
                        f"{deg}째", color="#AAAAAA", fontsize=6.5,
                        ha="center", va="center")

        # Step 6 measured crown markers. Each label (T1..Tn) is mapped to
        # the matching epoch_sections entry, so toggling labels cannot shift
        # markers onto the wrong epoch line.
        hotspots = (getattr(self, "_trend_hotspots", []) or []) if getattr(self, "_show_measured_points", True) else []
        if hotspots:
            if len(self._sections) > 1:
                chs = np.array([getattr(s, "chainage", np.nan) for s in self._sections], dtype=np.float64)
                spacing = float(np.nanmedian(np.abs(np.diff(chs)))) if np.isfinite(chs).sum() > 1 else 1.0
            else:
                spacing = 1.0
            tol = max(0.75, spacing * 0.65)
            base_r = float(sg.radius_fit) if np.isfinite(sg.radius_fit) else float(np.nanpercentile(radii, 90))
            allowed_labels = set(getattr(self, "_measured_point_labels", set()) or [])
            visible_hotspots = []
            for hp in hotspots:
                try:
                    label = str(hp.get("label", ""))
                    if allowed_labels and label not in allowed_labels:
                        continue
                    ch = float(hp.get("chainage_m", np.nan))
                    if not np.isfinite(ch) or abs(ch - float(sg.chainage)) > tol:
                        continue
                    visible_hotspots.append(hp)
                except Exception:
                    continue

            count_visible = max(1, len(visible_hotspots))
            skipped_markers = []
            for draw_idx, hp in enumerate(visible_hotspots):
                try:
                    label = str(hp.get("label", "p95"))
                    ch = float(hp.get("chainage_m", np.nan))
                    val = float(hp.get("value_mm", np.nan))
                    is_crown = hp.get("metric") == "crown_settlement_mm" or str(hp.get("position", "")).lower().startswith("crown")
                    epoch_idx = self._epoch_index_for_label(label) if is_crown else None
                    if is_crown:
                        marker_pt = self._crown_marker_point_for_epoch(epoch_idx, z_display_shift)
                        if marker_pt is None:
                            skipped_markers.append(label)
                            continue
                        hx, hz = marker_pt
                    else:
                        ang = math.radians(float(hp.get("angle_deg", 0.0)))
                        hx = base_r * math.cos(ang)
                        hz = base_r * math.sin(ang)
                        if self._profile != "Circle":
                            hz += z_display_shift

                    spread = 0.26 if count_visible > 1 else 0.0
                    marker_offset = (draw_idx - (count_visible - 1) / 2.0) * spread
                    hx_marker = hx + marker_offset
                    hz_marker = hz
                    color_idx = epoch_idx if epoch_idx is not None else draw_idx + 1
                    color = _EPOCH_COLORS[color_idx % len(_EPOCH_COLORS)]

                    if is_crown:
                        ax.plot([hx, hx_marker], [hz, hz_marker], color=color, lw=0.9,
                                alpha=0.85, zorder=11)
                        ax.scatter([hx_marker], [hz_marker], marker="o", s=125, c=color,
                                   edgecolors="white", linewidths=1.4, zorder=12,
                                   label="Crown measurement points" if draw_idx == 0 else None)
                        ax.annotate("", xy=(hx_marker, hz_marker), xytext=(hx_marker, hz_marker + 0.35),
                                    arrowprops=dict(arrowstyle="->", color=color, lw=1.8),
                                    zorder=12)
                        marker_text = f"{label}: {val:+.1f} mm\non outline"
                        text_color = "#991B1B"
                        face_color = "#FEE2E2"
                        edge_color = color
                    else:
                        ax.scatter([hx_marker], [hz_marker], marker="*", s=130, c="#22C55E",
                                   edgecolors="#064E3B", linewidths=0.8, zorder=12,
                                   label="Trend hotspot")
                        marker_text = f"{label}: {val:.1f} mm"
                        text_color = "#065F46"
                        face_color = "#DCFCE7"
                        edge_color = "#22C55E"

                    text_dx = 8 if draw_idx % 2 == 0 else -58
                    text_dy = 10 + 10 * (draw_idx % 3)
                    ax.annotate(marker_text,
                                xy=(hx_marker, hz_marker), xytext=(text_dx, text_dy), textcoords="offset points",
                                fontsize=7.5, color=text_color, fontweight="bold",
                                bbox=dict(facecolor=face_color, edgecolor=edge_color,
                                          boxstyle="round,pad=0.2", alpha=0.92),
                                zorder=13)
                except Exception:
                    try:
                        skipped_markers.append(str(hp.get("label", "?")))
                    except Exception:
                        skipped_markers.append("?")
                    continue
            if skipped_markers:
                ax.text(0.02, 0.90,
                        "Measured marker skipped: " + ", ".join(skipped_markers[:4]),
                        transform=ax.transAxes, ha="left", va="top", fontsize=6.5,
                        color="#92400E", fontweight="bold",
                        bbox=dict(facecolor="#FEF3C7", edgecolor="#F59E0B",
                                  boxstyle="round,pad=0.2", alpha=0.92), zorder=14)

        # ???? Vehicle clearance envelope ??????????????????????????????????????????????????????????????????????????
        vl_ok    = not sg.clearance_violation
        vl_color = "#888888" if vl_ok else "#DC2626"
        vl_lw    = 1.6 if vl_ok else 2.4
        vl_ls    = "-." if vl_ok else "-"
        vl_label = "Clearance limit" if vl_ok else "CLEARANCE VIOLATION"
        if SHOW_OVERLAY_LINES and self._profile == "Circle":
            ax.add_patch(plt.Circle((0.0, 0.0), self._vl_cir_r,
                fill=False, edgecolor=vl_color, lw=vl_lw, ls=vl_ls,
                alpha=0.95, zorder=5, label=vl_label))
        elif SHOW_OVERLAY_LINES:
            ax.add_patch(mpatches.Rectangle(
                (-self._vl_box_w, 0.0), 2*self._vl_box_w, self._vl_box_h,
                fill=False, edgecolor=vl_color, lw=vl_lw, ls=vl_ls,
                alpha=0.95, zorder=5, label=vl_label))
            if self._profile == "Box 2-cell":
                ax.plot([0.0, 0.0], [0.0, self._vl_box_h],
                        color=vl_color, lw=1.0, ls=":", zorder=5)

        # ???? Centre cross ??????????????????????????????????????????????????????????????????????????????????????????????????????
        cs = max(0.12, r_max * 0.04)
        if SHOW_OVERLAY_LINES:
            ax.plot([-cs, cs], [0, 0], color="#333333", lw=1.0, zorder=6)
            ax.plot([0, 0], [-cs, cs], color="#333333", lw=1.0, zorder=6)

        # ???? Dimension helpers ????????????????????????????????????????????????????????????????????????????????????????????
        xmn = float(np.percentile(x, 1)); xmx = float(np.percentile(x, 99))
        zmn = float(np.percentile(z, 1)); zmx = float(np.percentile(z, 99))
        zmid = (zmn + zmx) / 2.0
        x_span = max(xmx - xmn, 1.0); z_span = max(zmx - zmn, 1.0)
        dim_gap = max(0.30, 0.07 * max(x_span, z_span))
        lbox = dict(facecolor="#FFFFFF", edgecolor="#AAAAAA",
                    boxstyle="round,pad=0.18", alpha=0.95)
        arr  = dict(arrowstyle="<->", color="#333333", lw=1.0)

        def _hdim(x0, x1, y, text):
            ax.annotate("", xy=(x1, y), xytext=(x0, y), arrowprops=arr, zorder=7)
            ax.plot([x0,x0],[y-dim_gap*0.07,y+dim_gap*0.07], color="#333333", lw=0.8, zorder=7)
            ax.plot([x1,x1],[y-dim_gap*0.07,y+dim_gap*0.07], color="#333333", lw=0.8, zorder=7)
            ax.text((x0+x1)/2.0, y+dim_gap*0.14, text, color="#111111",
                    fontsize=7.5, ha="center", va="bottom", bbox=lbox, zorder=8,
                    fontfamily="monospace")

        def _vdim(y0, y1, x_pos, text):
            ax.annotate("", xy=(x_pos, y1), xytext=(x_pos, y0), arrowprops=arr, zorder=7)
            ax.plot([x_pos-dim_gap*0.07,x_pos+dim_gap*0.07],[y0,y0], color="#333333", lw=0.8, zorder=7)
            ax.plot([x_pos-dim_gap*0.07,x_pos+dim_gap*0.07],[y1,y1], color="#333333", lw=0.8, zorder=7)
            ax.text(x_pos+dim_gap*0.16, (y0+y1)/2.0, text, color="#111111",
                    fontsize=7.5, ha="left", va="center", bbox=lbox, zorder=8,
                    fontfamily="monospace")

        dim_y_top    = zmx + dim_gap * 0.55
        dim_y_bottom = zmn - dim_gap * 0.55
        dim_x_right  = xmx + dim_gap * 0.55
        dim_x_left   = xmn - dim_gap * 0.55

        # Keep the basic dimension schematic (W/H "s???猿낃펷?) on the section ??it's
        # requested even with the multi-times overlay. Only the single T0-vs-Tn
        # comparison hides them (there the focus is deformation, not absolutes).
        if not _comparing:
            if np.isfinite(sg.W1): _hdim(xmn, xmx, dim_y_top,    f"W1={sg.W1:.3f}m")
            if np.isfinite(sg.W2): _hdim(xmn, xmx, dim_y_bottom, f"W2={sg.W2:.3f}m")
            if np.isfinite(sg.H1): _vdim(zmn, zmx, dim_x_right,  f"H1={sg.H1:.3f}m")
            if np.isfinite(sg.H2): _vdim(zmid, zmx, dim_x_left,  f"H2={sg.H2:.3f}m")
            if np.isfinite(sg.H3): _vdim(zmn, zmid, dim_x_left-dim_gap*0.55, f"H3={sg.H3:.3f}m")

        # ???? Wall angle arcs ????????????????????????????????????????????????????????????????????????????????????????????????
        def _angle_arc(angle, cx, cz, side):
            if not np.isfinite(angle): return
            r_arc = min(x_span, z_span) * 0.12
            sa = 90.0; ext = angle if side == "left" else -angle
            ax.add_patch(mpatches.Arc((cx, cz), 2*r_arc, 2*r_arc, angle=0,
                theta1=min(sa,sa+ext), theta2=max(sa,sa+ext),
                color="#D97706", lw=1.4, zorder=7))
            m_rad = math.radians(sa + ext/2.0)
            ax.text(cx+r_arc*1.5*math.cos(m_rad), cz+r_arc*1.5*math.sin(m_rad),
                    f"{angle:.1f}째", color="#D97706", fontsize=7.5, fontweight="bold",
                    ha="center", va="center", bbox=lbox, zorder=8)

        # Wall-to-floor angle arcs/labels are hidden on the section view.
        # Set SHOW_WALL_ANGLE = True to restore them; they are anchored at
        # the wall-floor corner (bottom of each side wall).
        SHOW_WALL_ANGLE = False
        if SHOW_WALL_ANGLE:
            z_corner = zmn + z_span * 0.08
            _angle_arc(sg.wall_angle_L, xmn + x_span * 0.04, z_corner, "left")
            _angle_arc(sg.wall_angle_R, xmx - x_span * 0.04, z_corner, "right")

        # ???? Clearance violation banner ??????????????????????????????????????????????????????????????????????????
        if sg.clearance_violation:
            ax.text(0.5, 0.97, "CLEARANCE VIOLATION DETECTED",
                    transform=ax.transAxes, ha="center", va="top",
                    color="#DC2626", fontsize=10, fontweight="bold",
                    bbox=dict(facecolor="#FFF1F1", edgecolor="#DC2626",
                              boxstyle="round,pad=0.4", alpha=0.95), zorder=10)

        if warn_status != "OK":
            banner_color = "#DC2626" if warn_status == "CRITICAL" else "#D97706"
            banner_bg = "#FFF1F1" if warn_status == "CRITICAL" else "#FFFBEB"
            ax.text(0.01, 1.015, f"{warn_status}: {section_warning_text(warn_issues, limit=2)}",
                    transform=ax.transAxes, ha="left", va="bottom", clip_on=False,
                    color=banner_color, fontsize=8.2, fontweight="bold",
                    bbox=dict(facecolor=banner_bg, edgecolor=banner_color,
                              boxstyle="round,pad=0.25", alpha=0.95), zorder=10)
            # Colour the plot border to match warning level
            spine_lw = 3.0 if warn_status == "CRITICAL" else 2.0
            for sp in ax.spines.values():
                sp.set_color(banner_color); sp.set_linewidth(spine_lw)
            self._fig.patch.set_facecolor(banner_bg)
        else:
            for sp in ax.spines.values():
                sp.set_color("#888888"); sp.set_linewidth(0.8)
            self._fig.patch.set_facecolor("#FFFFFF")

        # ???? Limits & aspect ????????????????????????????????????????????????????????????????????????????????????????????????
        if self._profile == "Circle":
            vl_x0, vl_x1 = -self._vl_cir_r, self._vl_cir_r
            vl_z0, vl_z1 = -self._vl_cir_r, self._vl_cir_r
        else:
            vl_x0, vl_x1 = -self._vl_box_w, self._vl_box_w
            vl_z0, vl_z1 = 0.0, self._vl_box_h
            if z_display_shift != 0.0:
                vl_z0 += z_display_shift
                vl_z1 += z_display_shift
        pad = max(0.5, 0.08 * max(x_span, z_span))
        x_lo = float(np.percentile(x, 0.5)); x_hi = float(np.percentile(x, 99.5))
        z_lo = float(np.percentile(z, 0.5)); z_hi = float(np.percentile(z, 99.5))
        if _comparing:
            plot_x0 = min(x_lo, vl_x0) - pad
            plot_x1 = max(x_hi, vl_x1) + pad
            plot_z0 = min(z_lo, vl_z0) - pad
            plot_z1 = max(z_hi, vl_z1) + pad
        else:
            plot_x0 = min(x_lo, vl_x0, dim_x_left  - dim_gap) - pad
            plot_x1 = max(x_hi, vl_x1, dim_x_right + dim_gap) + pad
            plot_z0 = min(z_lo, vl_z0, dim_y_bottom - dim_gap) - pad
            plot_z1 = max(z_hi, vl_z1, dim_y_top   + dim_gap) + pad
        cap = 18.0
        plot_x0 = max(plot_x0,-cap); plot_x1 = min(plot_x1, cap)
        plot_z0 = max(plot_z0,-cap); plot_z1 = min(plot_z1, cap)
        if plot_x1-plot_x0 < 1.0:
            mid=(plot_x0+plot_x1)/2.0; plot_x0,plot_x1=mid-0.5,mid+0.5
        if plot_z1-plot_z0 < 1.0:
            mid=(plot_z0+plot_z1)/2.0; plot_z0,plot_z1=mid-0.5,mid+0.5
        ax.set_xlim(plot_x0, plot_x1); ax.set_ylim(plot_z0, plot_z1)
        ax.set_aspect("equal", adjustable="box")

        # ???? Axes labels & title ????????????????????????????????????????????????????????????????????????????????????????
        ax.set_xlabel("X_2D  (N vector, m)", color="#333333", fontsize=8, labelpad=3)
        ax.set_ylabel("Z_2D  (B vector, m)", color="#333333", fontsize=8, labelpad=3)
        _mode_tag = "T0 vs Tn" if _comparing else self._profile
        ax.set_title(
            f"TUNNEL CROSS-SECTION  |  Ch. {sg.chainage:.2f} m  |  {_mode_tag}",
            color="#0F172A", fontsize=9.5, fontweight="bold",
            fontfamily="monospace", pad=5)

        # ???? Legend ??????????????????????????????????????????????????????????????????????????????????????????????????????????????????
        legend_handles = []
        legend_loc = "lower right"; legend_ncol = 1
        if multi_epoch and getattr(self, "_times_legend_handles", None):
            legend_handles = self._times_legend_handles
            legend_loc = "upper right"; legend_ncol = 2
        elif _comparing:
            legend_handles = [
                mpatches.Patch(color="#94A3B8", label="T0 (reference)"),
                mpatches.Patch(color="#3B82F6", label="Tn (monitoring)"),
            ]
        elif has_labels:
            legend_handles = [
                mpatches.Patch(color=WALL_C,  label="Wall"),
                mpatches.Patch(color=CROWN_C, label="Crown"),
                mpatches.Patch(color=FLOOR_C, label="Floor"),
            ]
        else:
            legend_handles = [
                mpatches.Patch(color="#16A34A", label="Dev <1mm"),
                mpatches.Patch(color="#D97706", label="Dev 1-3mm"),
                mpatches.Patch(color="#DC2626", label="Dev >3mm"),
            ]
        ax.legend(handles=legend_handles, fontsize=7.5, facecolor="#FFFFFF",
                  edgecolor="#CCCCCC", labelcolor="#111111",
                  loc=legend_loc, ncol=legend_ncol, framealpha=0.95, borderpad=0.6)

        # Title block moved to Info dialog button
        self._current_sg = sg
        if hasattr(self, "_info_label"):
            ref_info = getattr(self, "_current_ref_sg", None)
            parts = []
            if warn_status != "OK":
                parts.append(f"{warn_status}: {section_warning_text(warn_issues)}")
            parts.append(f"Ch:{sg.chainage:.2f}m")
            if ref_info is not None:
                parts.append("Tn vs T0")
            else:
                parts.append("single scan")
            if ref_info is not None and self._visual_deformation_scale() > 1.0:
                parts.append(f"Visual x{self._visual_deformation_scale():.0f}")
            if np.isfinite(sg.W1):
                parts.append(f"W1={sg.W1:.3f}m")
            if np.isfinite(sg.H1):
                parts.append(f"H1={sg.H1:.3f}m")
            if self._profile == "Circle" and np.isfinite(sg.radius_fit):
                parts.append(f"R={sg.radius_fit:.3f}m")
            if np.isfinite(sg.ovality):
                parts.append(f"Oval={sg.ovality:.2f}%")
            if np.isfinite(sg.eccentricity):
                parts.append(f"e={sg.eccentricity:.1f}mm")
            if np.isfinite(sg.min_clearance_dist):
                parts.append(f"Clr={sg.min_clearance_dist:.3f}m")
            if ref_info is not None:
                delta_parts = []
                if np.isfinite(sg.W1) and np.isfinite(ref_info.W1):
                    delta_parts.append(f"dW={(sg.W1 - ref_info.W1) * 1e3:+.1f}mm")
                if np.isfinite(sg.H1) and np.isfinite(ref_info.H1):
                    delta_parts.append(f"dH={(sg.H1 - ref_info.H1) * 1e3:+.1f}mm")
                if np.isfinite(sg.radius_fit) and np.isfinite(ref_info.radius_fit):
                    delta_parts.append(f"dR={(sg.radius_fit - ref_info.radius_fit) * 1e3:+.1f}mm")
                if np.isfinite(sg.ovality) and np.isfinite(ref_info.ovality):
                    delta_parts.append(f"dOval={sg.ovality - ref_info.ovality:+.2f}%")
                if np.isfinite(sg.eccentricity) and np.isfinite(ref_info.eccentricity):
                    delta_parts.append(f"dEcc={sg.eccentricity - ref_info.eccentricity:+.1f}mm")
                if delta_parts:
                    parts.append("Delta " + " ".join(delta_parts))
            color = "#DC2626" if warn_status == "CRITICAL" else ("#D97706" if warn_status == "CAUTION" else "#0F172A")
            self._info_label.setStyleSheet(
                f"color:{color}; font-family:monospace; font-size:9pt; "
                "padding:4px 8px; background:#F8FAFC; "
                "border-top-width:1px; border-top-style:solid; border-top-color:#CBD5E1;")
            self._info_label.setText("   |   ".join(parts))

        self._fig.tight_layout(pad=0.55)
        self._canvas.draw_idle()



# ------------------------------------------------------------------------------
# Full-screen section dialog
# ------------------------------------------------------------------------------

class _SectionFullscreenDialog(QtWidgets.QDialog):
    """Resizable full-screen dialog for 2D cross-section."""

    def __init__(self, sg, profile, vl_w, vl_h, vl_r, translate=None, parent=None):
        super().__init__(parent)
        self._translate = translate or (lambda text: text)
        self.setWindowTitle(f"Cross-Section  |  Ch. {sg.chainage:.3f} m  |  {profile}")
        self.setWindowFlags(self.windowFlags() |
                            QtCore.Qt.WindowMaximizeButtonHint |
                            QtCore.Qt.WindowMinimizeButtonHint)
        self.resize(1000, 800)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8); lay.setSpacing(6)

        # Toolbar
        tb = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel(
            f"Chainage: {sg.chainage:.3f} m  |  View: Field Robust  |  Profile metadata: {profile}")
        lbl.setStyleSheet("font-weight:bold; font-size:11pt; color:#0F172A;")
        btn_save = QtWidgets.QPushButton(self._translate("Save PNG"))
        btn_save.setStyleSheet(
            "QPushButton{background:#047857;color:white;border-radius:5px;"
            "padding:5px 14px;font-weight:600;}"
            "QPushButton:hover{background:#065F46;}")
        btn_close = QtWidgets.QPushButton(self._translate("Close"))
        btn_close.setStyleSheet(
            "QPushButton{background:#64748B;color:white;border-radius:5px;"
            "padding:5px 14px;font-weight:600;}"
            "QPushButton:hover{background:#475569;}")
        tb.addWidget(lbl, 1)
        tb.addWidget(btn_save)
        tb.addWidget(btn_close)
        lay.addLayout(tb)

        # Large matplotlib canvas
        if _MPL_OK:
            self._fig = Figure(figsize=(12, 10), facecolor="white", dpi=100)
            self._ax  = self._fig.add_subplot(111)
            self._canvas = FigureCanvas(self._fig)
            lay.addWidget(self._canvas, 1)

            # Reuse MatplotlibSectionWidget draw logic
            tmp = MatplotlibSectionWidget.__new__(MatplotlibSectionWidget)
            tmp._fig = self._fig
            tmp._ax  = self._ax
            tmp._profile  = profile
            tmp._vl_box_w = vl_w
            tmp._vl_box_h = vl_h
            tmp._vl_cir_r = vl_r
            tmp._draw_section(sg)

            btn_save.clicked.connect(lambda: self._save_png(sg))
        else:
            lay.addWidget(QtWidgets.QLabel(self._translate("Matplotlib not available.")))

        btn_close.clicked.connect(self.accept)

    def _save_png(self, sg) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, self._translate("Save Section PNG"),
            f"section_ch{sg.chainage:.2f}m.png",
            "PNG Images (*.png)")
        if path:
            self._fig.savefig(path, dpi=200, bbox_inches="tight",
                              facecolor="white")
            QtWidgets.QMessageBox.information(self, self._translate("Saved"), self._translate("Saved to:") + f"\n{path}")


# ------------------------------------------------------------------------------
# PolarDeformationPlotWidget
# ------------------------------------------------------------------------------

class PolarDeformationPlotWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._translate = lambda text: text
        self._angles: Optional[np.ndarray] = None; self._dmap: Optional[np.ndarray] = None
        lay = QtWidgets.QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        if _MPL_OK:
            self._fig, self._ax = plt.subplots(subplot_kw={"projection":"polar"}, figsize=(4, 4))
            self._fig.patch.set_facecolor(_BG); self._canvas = FigureCanvas(self._fig); lay.addWidget(self._canvas)
        else:
            self._missing_label = QtWidgets.QLabel("Matplotlib missing.")
            lay.addWidget(self._missing_label)

    def retranslate(self, translate: Callable[[str], str]) -> None:
        self._translate = translate
        if not _MPL_OK and hasattr(self, "_missing_label"):
            self._missing_label.setText(translate("Matplotlib missing."))
        self._redraw()

    def update_data(self, angles: np.ndarray, dmap: np.ndarray) -> None:
        if not _MPL_OK: return
        self._angles = angles; self._dmap = dmap; self._redraw()

    def _redraw(self) -> None:
        if not _MPL_OK or self._angles is None: return
        ax = self._ax; ax.clear()
        mean_dr = np.nanmean(self._dmap, axis=0); ang = self._angles
        for i in range(len(ang)-1):
            if np.isnan(mean_dr[i]): continue
            av = abs(float(mean_dr[i]))
            col = _GRN if av < 1.0 else (_YEL if av < 3.0 else _RED)
            ax.bar(ang[i], av, width=(ang[1] - ang[0]), color=col, alpha=0.85, edgecolor="none")
        ax.set_title(self._translate("Polar radial deformation dr [mm]"), color=_FG, fontsize=9, pad=8)
        ax.set_facecolor(_BG); ax.tick_params(colors=_FG, labelsize=7); ax.grid(True, color=_GRID, lw=0.6, alpha=0.75)
        ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
        self._fig.tight_layout(); self._canvas.draw_idle()


# ------------------------------------------------------------------------------
# LinePlotWidget
# ------------------------------------------------------------------------------

class LinePlotWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._translate = lambda text: text
        self.values: Optional[np.ndarray] = None; self.title = "Time-series"; self.setMinimumHeight(220)
        self.labels: list[str] = []

    def retranslate(self, translate: Callable[[str], str]) -> None:
        self._translate = translate
        self.update()

    def set_values(self, values: Optional[np.ndarray], title: str = "", labels: Optional[list[str]] = None) -> None:
        self.values = None if values is None else np.asarray(values, dtype=np.float64).ravel()
        value_count = 0 if self.values is None else len(self.values)
        self.labels = list(labels or []) if labels and len(labels) == value_count else []
        self.title = title or "Time-series"; self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        p = QtGui.QPainter(self); p.setRenderHint(QtGui.QPainter.Antialiasing)
        rc = self.rect().adjusted(14, 14, -14, -14)
        p.fillRect(self.rect(), QtGui.QColor("#FFFFFF"))
        p.setPen(QtGui.QPen(QtGui.QColor("#CBD5E1"), 1)); p.drawRoundedRect(rc, 6, 6)
        p.setPen(QtGui.QColor("#111827")); p.setFont(QtGui.QFont("Segoe UI", 10, QtGui.QFont.Bold))
        p.drawText(rc.adjusted(10, 6, -10, -6), QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft, self._translate(self.title))
        if self.values is None or len(self.values) < 2:
            p.setFont(QtGui.QFont("Segoe UI", 9)); p.setPen(QtGui.QColor("#64748B"))
            p.drawText(rc, QtCore.Qt.AlignCenter, self._translate("Run Step 6.2 to generate chart.")); return
        pr = rc.adjusted(42, 42, -18, -34)
        p.setPen(QtGui.QPen(QtGui.QColor("#E2E8F0"), 1))
        for i in range(5):
            y = pr.top() + i * pr.height() / 4.0; p.drawLine(pr.left(), int(y), pr.right(), int(y))
        vals = self.values[np.isfinite(self.values)]
        if len(vals) < 2: return
        vmin, vmax = float(np.min(vals)), float(np.max(vals))
        if math.isclose(vmin, vmax): vmax = vmin + 1.0
        pts = []
        for i, v in enumerate(self.values):
            x = pr.left() + i / max(1, len(self.values) - 1) * pr.width()
            y = pr.bottom() - (float(v) - vmin) / (vmax - vmin) * pr.height()
            pts.append(QtCore.QPointF(x, y))
        p.setPen(QtGui.QPen(QtGui.QColor("#2563EB"), 2))
        for a, b in zip(pts[:-1], pts[1:]): p.drawLine(a, b)
        p.setPen(QtGui.QColor("#475569")); p.setFont(QtGui.QFont("Segoe UI", 8))
        p.drawText(pr.left(), rc.bottom() - 8, f"min {vmin:.2f}mm")
        p.drawText(pr.right() - 110, rc.bottom() - 8, f"max {vmax:.2f}mm")
        tick_labels = self.labels or [str(i) for i in range(len(self.values))]
        for idx, label in enumerate(tick_labels):
            x = pr.left() + idx / max(1, len(tick_labels) - 1) * pr.width()
            text = str(label)
            p.drawText(QtCore.QRectF(x - 24, pr.bottom() + 4, 48, 16), QtCore.Qt.AlignCenter, text)


# ------------------------------------------------------------------------------
# Multi-Times Time-Series Trend Widget
# ------------------------------------------------------------------------------

class MultiEpochTimeSeriesWidget(QtWidgets.QWidget):
    measured_points_visibility_changed = QtCore.Signal(bool)
    """Matplotlib-based multi-times deformation trend chart.

    Shows per-times displacement (p95 and median) across monitoring campaigns,
    threshold bands (caution / critical), and polynomial forecast extrapolation.
    Includes an times summary table below the chart.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._translate = lambda text: text
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)

        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except ImportError:
            lay.addWidget(QtWidgets.QLabel("Matplotlib required for multi-times chart."))
            self._canvas = None
            return

        self._fig = Figure(figsize=(8, 4), dpi=100, facecolor="white")
        self._canvas = FigureCanvasQTAgg(self._fig)
        lay.addWidget(self._canvas, stretch=3)

        self._info_table = QtWidgets.QTableWidget()
        self._info_table.setMaximumHeight(160)
        self._info_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._info_table.setAlternatingRowColors(True)
        self._info_table.setStyleSheet(
            "QTableWidget { font-size: 9pt; gridline-color: #E2E8F0; }"
            "QHeaderView::section { background: #F1F5F9; font-weight: bold; padding: 4px; }")
        lay.addWidget(self._info_table, stretch=1)

        self._chk_show_measured_points = QtWidgets.QCheckBox("Show measured points on 2D (markers only; lines always visible)")
        self._chk_show_measured_points.setChecked(True)
        self._chk_show_measured_points.setToolTip(
            "Show/hide the Step 6 measured crown points for all time epochs on the 2D section.")
        self._chk_show_measured_points.setStyleSheet(
            "QCheckBox { font-size: 9pt; font-weight: 600; color: #0F172A; padding: 2px; }")
        self._chk_show_measured_points.toggled.connect(self.measured_points_visibility_changed.emit)
        lay.addWidget(self._chk_show_measured_points)

        self._measured_epoch_box = QtWidgets.QWidget()
        epoch_lay = QtWidgets.QHBoxLayout(self._measured_epoch_box)
        epoch_lay.setContentsMargins(2, 0, 2, 2)
        epoch_lay.setSpacing(8)
        self._measured_epoch_checks = []
        lay.addWidget(self._measured_epoch_box)

        self._link_label = QtWidgets.QLabel("")
        self._link_label.setWordWrap(True)
        self._link_label.setStyleSheet(
            "background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 4px;"
            "padding: 6px; font-size: 9pt; color: #1E3A8A;")
        self._link_label.setVisible(False)
        lay.addWidget(self._link_label)

        self._forecast_label = QtWidgets.QLabel("")
        self._forecast_label.setWordWrap(True)
        self._forecast_label.setStyleSheet(
            "background: #FFF7ED; border: 1px solid #FED7AA; border-radius: 4px;"
            "padding: 6px; font-size: 9pt; color: #9A3412;")
        self._forecast_label.setVisible(False)
        lay.addWidget(self._forecast_label)

        self._series_data: Optional[Dict] = None
        self._forecast_data: Optional[Dict] = None
        self._link_hotspot: Optional[Dict] = None

    def measured_points_visible(self) -> bool:
        return bool(getattr(self, "_chk_show_measured_points", None) is None
                    or self._chk_show_measured_points.isChecked())

    def visible_measured_labels(self) -> set:
        checks = getattr(self, "_measured_epoch_checks", []) or []
        return {chk.text() for chk in checks if chk.isChecked()}

    def measured_points_filter(self) -> dict:
        return {"enabled": self.measured_points_visible(),
                "labels": self.visible_measured_labels()}

    def _set_measured_epoch_labels(self, labels) -> None:
        if not hasattr(self, "_measured_epoch_box"):
            return
        previous = {chk.text(): chk.isChecked()
                    for chk in (getattr(self, "_measured_epoch_checks", []) or [])}
        layout = self._measured_epoch_box.layout()
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._measured_epoch_checks = []
        for lbl in labels:
            chk = QtWidgets.QCheckBox(str(lbl))
            chk.setChecked(previous.get(str(lbl), True))
            chk.setStyleSheet("QCheckBox { font-size: 8.5pt; color: #334155; }")
            chk.toggled.connect(lambda _checked: self.measured_points_visibility_changed.emit(self.measured_points_visible()))
            layout.addWidget(chk)
            self._measured_epoch_checks.append(chk)
        layout.addStretch(1)
        self._measured_epoch_box.setVisible(bool(labels))

    def retranslate(self, translate) -> None:
        self._translate = translate
        self._redraw()

    def set_series(self, series: Dict, forecast: Optional[Dict] = None) -> None:
        self._series_data = series
        self._forecast_data = forecast
        self._set_measured_epoch_labels(series.get("labels", []) if isinstance(series, dict) else [])
        self._redraw()

    def set_link_hotspot(self, hotspot: Optional[Dict]) -> None:
        self._link_hotspot = hotspot
        self._update_link_label()

    def _redraw(self) -> None:
        if self._canvas is None:
            return
        self._fig.clear()
        s = self._series_data
        if s is None:
            ax = self._fig.add_subplot(111)
            ax.text(0.5, 0.5, self._translate("Load multi-times data and run trend analysis."),
                    ha="center", va="center", fontsize=11, color="#64748B",
                    transform=ax.transAxes)
            ax.set_axis_off()
            self._canvas.draw()
            return

        labels = s.get("labels", [])
        median = np.asarray(s.get("median_mm", []), dtype=np.float64)
        p95 = np.asarray(s.get("p95_abs_mm", []), dtype=np.float64)
        crown = np.asarray(s.get("crown_settlement_mm", []), dtype=np.float64)
        crown_plot = np.abs(crown) if crown.size == len(labels) + 1 else np.asarray([], dtype=np.float64)
        n = len(labels)
        x = np.arange(n)
        x_labels = ["T0"] + list(labels)
        median_full = np.concatenate([[0.0], median])
        p95_full = np.concatenate([[0.0], p95])
        main_full = crown_plot if crown_plot.size == n + 1 else p95_full
        x_full = np.arange(n + 1)

        ax = self._fig.add_subplot(111)

        caution_mm = SECTION_DELTA_CAUTION_MM
        critical_mm = SECTION_DELTA_CRITICAL_MM
        if self._forecast_data:
            caution_mm = self._forecast_data.get("caution_mm", SECTION_DELTA_CAUTION_MM)
            critical_mm = self._forecast_data.get("critical_mm", SECTION_DELTA_CRITICAL_MM)

        base = float(np.nanmax(main_full)) if main_full.size else 0.0
        ymax = max(base * 1.25, critical_mm * 1.2)

        ax.axhspan(0, caution_mm, color="#DCFCE7", alpha=0.25)
        ax.axhspan(caution_mm, critical_mm, color="#FEF9C3", alpha=0.25)
        ax.axhspan(critical_mm, ymax, color="#FEE2E2", alpha=0.25)
        ax.axhline(caution_mm, color="#F59E0B", ls="--", lw=1, alpha=0.75,
                   label=f"Caution {caution_mm:g} mm")
        ax.axhline(critical_mm, color="#EF4444", ls="--", lw=1, alpha=0.75,
                   label=f"Critical {critical_mm:g} mm")

        ax.plot(x_full, main_full, "o-", color="#2563EB", lw=2.2, markersize=6,
                label=self._translate("Crown settlement trend (mm)") if crown_plot.size == n + 1 else self._translate("Main settlement trend (mm)"))

        ax.set_xticks(x_full)
        ax.set_xticklabels(x_labels, fontsize=9)
        ax.set_xlabel(self._translate("Time point"), fontsize=10)
        ax.set_ylabel(self._translate("Settlement / movement (mm)"), fontsize=10)
        ax.set_title(self._translate("Multi-Times Deformation Trend"), fontsize=11, fontweight="bold")
        ax.legend(loc="upper left", fontsize=8, framealpha=0.8)
        ax.grid(True, alpha=0.3)
        x_right = max(len(x_labels) - 0.5, 2.0)
        ax.set_xlim(-0.3, x_right)
        ax.set_ylim(0, ymax)

        self._fig.tight_layout()
        self._canvas.draw()

        self._update_table(labels, median, p95, crown)
        self._update_forecast_label()
        self._update_link_label()

    def _update_table(self, labels, median, p95, crown=None):
        s = self._series_data or {}
        crown_arr = np.asarray(crown if crown is not None else [], dtype=np.float64)
        if crown_arr.size == len(labels) + 1:
            crown_arr = crown_arr[1:]
        zone_points = np.asarray(s.get("crown_zone_points", []), dtype=np.float64)
        if zone_points.size == len(labels) + 1:
            zone_points = zone_points[1:]
        chainage = s.get("crown_chainage_m", 52.0)
        try:
            location_txt = f"Ch {float(chainage):.1f}m"
        except Exception:
            location_txt = "Ch --"
        measured_point_txt = self._translate("Tunnel crown")
        cols = [self._translate("Time"), self._translate("Location"),
                self._translate("Measured point"), self._translate("Crown settlement (mm)"),
                self._translate("New crown move (mm)"), self._translate("Result")]
        self._info_table.setColumnCount(len(cols))
        self._info_table.setHorizontalHeaderLabels(cols)
        self._info_table.setRowCount(len(labels))

        caution = 10.0
        critical = 25.0
        if self._forecast_data:
            caution = self._forecast_data.get("caution_mm", SECTION_DELTA_CAUTION_MM)
            critical = self._forecast_data.get("critical_mm", SECTION_DELTA_CRITICAL_MM)

        def _cell(txt):
            return QtWidgets.QTableWidgetItem(txt)

        prev_crown = 0.0
        for i, lbl in enumerate(labels):
            self._info_table.setItem(i, 0, _cell(str(lbl)))
            self._info_table.setItem(i, 1, _cell(location_txt))
            self._info_table.setItem(i, 2, _cell(measured_point_txt))
            has_crown = i < crown_arr.size and np.isfinite(crown_arr[i])
            crown_val = float(crown_arr[i]) if has_crown else float("nan")
            crown_txt = f"{crown_val:+.2f}" if has_crown else "-"
            self._info_table.setItem(i, 3, _cell(crown_txt))
            new_move = crown_val - prev_crown if has_crown else float("nan")
            self._info_table.setItem(i, 4, _cell(f"{new_move:+.2f}" if np.isfinite(new_move) else "-"))
            val = abs(crown_val) if has_crown else 0.0
            if val >= critical:
                st = self._translate("Danger")
            elif val >= caution:
                st = self._translate("Warning")
            else:
                st = self._translate("OK")
            item = _cell(st)
            if val >= critical:
                item.setForeground(QtGui.QColor("#DC2626"))
            elif val >= caution:
                item.setForeground(QtGui.QColor("#D97706"))
            else:
                item.setForeground(QtGui.QColor("#059669"))
            self._info_table.setItem(i, 5, item)
            if has_crown:
                prev_crown = crown_val
        self._info_table.resizeColumnsToContents()
        if crown_arr.size:
            self._link_label.setText(
                self._translate("Table values are measured at the tunnel crown")
                + f", {location_txt}. "
                + self._translate("Check the same point in the 2D section."))
            self._link_label.setVisible(True)
        else:
            self._link_label.setText(
                self._translate("Could not identify tunnel crown measurements; rerun Step 6.1 or check T0/Tn data."))
            self._link_label.setVisible(True)

    def _update_forecast_label(self):
        fc = self._forecast_data
        if fc is None:
            self._forecast_label.setVisible(False)
            return
        lines = []
        caution_cross = fc.get("caution_crossing_epoch")
        critical_cross = fc.get("critical_crossing_epoch")
        r2 = fc.get("r_squared")
        if caution_cross is not None:
            lines.append(f"Caution ({fc.get("caution_mm", SECTION_DELTA_CAUTION_MM):.0f}mm): times {caution_cross:.1f}")
        if critical_cross is not None:
            lines.append(f"Critical ({fc.get("critical_mm", SECTION_DELTA_CRITICAL_MM):.0f}mm): times {critical_cross:.1f}")
        if r2 is not None:
            lines.append(f"R筌?= {r2:.4f}")
        if lines:
            self._forecast_label.setText(
                self._translate("Forecast threshold crossing") + ":  " + "  |  ".join(lines))
            self._forecast_label.setVisible(True)
        else:
            self._forecast_label.setVisible(False)

    def _update_link_label(self):
        h = self._link_hotspot
        if not h:
            s = self._series_data or {}
            if len(s.get("crown_settlement_mm", [])):
                try:
                    location_txt = f"Ch {float(s.get('crown_chainage_m', 52.0)):.1f}m"
                except Exception:
                    location_txt = "Ch --"
                self._link_label.setText(
                    self._translate("Table values are measured at the tunnel crown")
                    + f", {location_txt}. "
                    + self._translate("Check the same point in the 2D section."))
                self._link_label.setVisible(True)
                return
            self._link_label.setVisible(False)
            return
        self._link_label.setText(
            self._translate("Step 6 linked hotspot") + ": "
            f"{h.get('label', 'Tn')} @ Ch {h.get('chainage_m', 0.0):.2f} m, "
            f"{h.get('position', '')}, {('crown' if h.get('metric') == 'crown_settlement_mm' else 'p95')} {h.get('value_mm', h.get('p95_abs_mm', 0.0)):.1f} mm. "
            + self._translate("Follow this same location on the chainage ruler, M3C2 map, and the red dot in the 2D section."))
        self._link_label.setVisible(True)


class M3C2MapWidget(QtWidgets.QWidget):
    """2D developed (unwrapped) view of an M3C2 deformation map.

    X = chainage along the tunnel axis (m), Y = angle around the circumference
    (deg), colour = signed M3C2 displacement (mm). This gives M3C2 a flat result
    chart like the 2D section view, instead of only colouring the 3D cloud.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._translate = lambda text: text
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4); lay.setSpacing(4)
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except ImportError:
            lay.addWidget(QtWidgets.QLabel("Matplotlib required for the M3C2 map."))
            self._canvas = None
            return
        self._fig = Figure(figsize=(8, 3.6), dpi=100, facecolor="white")
        self._canvas = FigureCanvasQTAgg(self._fig)
        lay.addWidget(self._canvas, stretch=3)
        # Damage-zone table (chainage, position, magnitude, severity).
        self._table = QtWidgets.QTableWidget()
        self._table.setMaximumHeight(180)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            "QTableWidget { font-size: 9pt; gridline-color: #E2E8F0; }"
            "QHeaderView::section { background: #F1F5F9; font-weight: bold; padding: 4px; }")
        lay.addWidget(self._table, stretch=1)
        self._link_label = QtWidgets.QLabel("")
        self._link_label.setWordWrap(True)
        self._link_label.setStyleSheet(
            "background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 4px;"
            "padding: 6px; font-size: 9pt; color: #1E3A8A;")
        self._link_label.setVisible(False)
        lay.addWidget(self._link_label)
        self._draw_empty()

    def retranslate(self, translate) -> None:
        self._translate = translate

    def _draw_empty(self, msg=None):
        if self._canvas is None:
            return
        self._fig.clear()
        ax = self._fig.add_subplot(111)
        ax.text(0.5, 0.5, msg or self._translate("Run Step 6.2: M3C2 deformation map."),
                ha="center", va="center", fontsize=11, color="#64748B", transform=ax.transAxes)
        ax.set_axis_off(); self._canvas.draw()
        if hasattr(self, "_table"):
            self._table.setRowCount(0)

    def set_map(self, chainage, angle_deg, dist_mm, zones=None, method="M3C2",
                axis_labels=None, bands=True, link_hotspots=None, link_hotspot=None) -> None:
        """Binned developed damage map + damage-zone table.

        ``zones`` is a list of dicts (chainage, position, peak_mm, severity) from
        the damage finder. ``bands`` draws crown/wall/invert guide lines on the
        angle axis. ``axis_labels`` overrides titles for the plan-view fallback.
        """
        if self._canvas is None:
            return
        x = np.asarray(chainage, dtype=np.float64)
        y = np.asarray(angle_deg, dtype=np.float64)
        d = np.asarray(dist_mm, dtype=np.float64)
        ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(d)
        x, y, d = x[ok], y[ok], d[ok]
        if d.size < 4:
            self._draw_empty(self._translate("Not enough M3C2 points to display."))
            return
        self._fig.clear()
        ax = self._fig.add_subplot(111)

        # Bin into a smooth grid so damaged zones read as solid patches, not a
        # speckled scatter. Each cell = mean signed displacement; empty = blank.
        nx = max(20, min(120, int((x.max() - x.min()) / 0.3) or 60))
        ylo, yhi = (float(y.min()), float(y.max())) if axis_labels else (-180.0, 180.0)
        xe = np.linspace(float(x.min()), float(x.max()) + 1e-6, nx + 1)
        ye = np.linspace(ylo, yhi + 1e-6, 73)
        ssum, _, _ = np.histogram2d(x, y, bins=[xe, ye], weights=d)
        cnt, _, _ = np.histogram2d(x, y, bins=[xe, ye])
        with np.errstate(invalid="ignore", divide="ignore"):
            grid = np.where(cnt > 0, ssum / cnt, np.nan)
        lim = max(float(np.nanmax(np.abs(d))), 1e-6)
        import matplotlib.cm as _cm
        cmap = _cm.get_cmap("turbo").copy(); cmap.set_bad("#F1F5F9")
        im = ax.imshow(grid.T, origin="lower", aspect="auto",
                       extent=[xe[0], xe[-1], ye[0], ye[-1]],
                       cmap=cmap, vmin=-lim, vmax=lim, interpolation="nearest")
        cb = self._fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
        cb.set_label(self._translate("Displacement (mm)"), fontsize=9)

        xl, yl = (axis_labels or (self._translate("Chainage (m)"),
                                  self._translate("Circumferential position")))
        ax.set_xlabel(xl, fontsize=10); ax.set_ylabel(yl, fontsize=10)
        if bands and not axis_labels:
            ax.set_yticks([-180, -90, 0, 90, 180])
            ax.set_yticklabels(["Wall L", "Invert", "Wall R", "Crown", "Wall L"], fontsize=8)
            for yy in (-90, 0, 90):
                ax.axhline(yy, color="#94A3B8", lw=0.5, ls=":", alpha=0.7)
        ax.set_title(self._translate("M3C2 Damage Map (developed)") + f"  [{method}]",
                     fontsize=11, fontweight="bold")
        ax.text(0.01, 0.99, self._translate("Supplementary map, not crown settlement result"),
                transform=ax.transAxes, ha="left", va="top", fontsize=7.5,
                color="#7C2D12", fontweight="bold",
                bbox=dict(facecolor="#FFEDD5", edgecolor="#FDBA74",
                          boxstyle="round,pad=0.2", alpha=0.92), zorder=7)

        # Mark the worst zones on the map so the eye lands on them.
        for z in (zones or [])[:6]:
            ax.plot(z["chainage"], z.get("angle", 0.0), marker="o", ms=9,
                    mfc="none", mec="#111827", mew=1.4, zorder=5)
        developed_axes = not axis_labels or str(axis_labels[0]).startswith("Chainage")
        hotspots = list(link_hotspots or ([] if link_hotspot is None else [link_hotspot]))
        if hotspots and developed_axes:
            for hp in hotspots:
                hx = float(hp.get("chainage_m", np.nan))
                hy = float(hp.get("angle_deg", np.nan))
                if np.isfinite(hx) and np.isfinite(hy):
                    ax.plot(hx, hy, marker="*", ms=14, mfc="#22C55E", mec="#14532D",
                            mew=1.0, zorder=6)
                    ax.annotate(str(hp.get("label", "Tn")), (hx, hy),
                                xytext=(6, 6), textcoords="offset points", fontsize=8,
                                color="#14532D", weight="bold")
        self._fig.tight_layout(); self._canvas.draw()
        self._fill_table(zones or [])

        if hotspots:
            preview = ", ".join(
                f"{h.get('label', 'Tn')}@Ch{h.get('chainage_m', 0.0):.1f}m"
                for h in hotspots[:6])
            self._link_label.setText(
                self._translate("Supplementary M3C2 map; green stars = Step 6 measured crown positions")
                + ": " + preview)
            self._link_label.setVisible(True)
        else:
            self._link_label.setVisible(False)

    def _fill_table(self, zones):
        cols = [self._translate("Chainage (m)"), self._translate("Position"),
                self._translate("Peak (mm)"), self._translate("Severity")]
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setRowCount(len(zones))
        for i, z in enumerate(zones):
            sev = z.get("severity", "")
            color = "#DC2626" if sev == "CRITICAL" else ("#D97706" if sev == "CAUTION" else "#059669")
            cells = [f"{z['chainage']:.2f}", str(z.get("position", "")),
                     f"{z['peak_mm']:+.1f}", sev]
            for c, txt in enumerate(cells):
                it = QtWidgets.QTableWidgetItem(txt)
                if c == 3:
                    it.setForeground(QtGui.QColor(color))
                self._table.setItem(i, c, it)
        self._table.resizeColumnsToContents()


# ------------------------------------------------------------------------------
# Analysis Summary Dashboard
# ------------------------------------------------------------------------------

class SummaryDashboardWidget(QtWidgets.QWidget):
    """One-glance deformation summary dashboard.

    Shows all key metrics (crown, convergence, eccentricity, ovality) as
    colour-coded cards, an overall status banner, general scan info, and the
    top-N worst section alerts.  Updated via update_params() / update_sections().
    """

    # Colours (hex strings understood by QColor).
    _C_OK       = "#047857"   # dark green text
    _C_OK_BG    = "#ECFDF5"
    _C_OK_BD    = "#6EE7B7"
    _C_CAUT     = "#B45309"   # dark amber text
    _C_CAUT_BG  = "#FFFBEB"
    _C_CAUT_BD  = "#FCD34D"
    _C_CRIT     = "#DC2626"   # red text
    _C_CRIT_BG  = "#FEF2F2"
    _C_CRIT_BD  = "#FCA5A5"
    _C_NONE_BG  = "#F8FAFC"
    _C_NONE_BD  = "#CBD5E1"

    # Each dashboard metric: (display title key, param_key_mean, param_key_max, unit)
    _METRICS = [
        ("Crown Settlement",       "crown_settlement_mm",    "crown_settlement_max_mm",    "mm"),
        ("Horizontal Convergence", "lateral_convergence_mm", "lateral_convergence_max_mm", "mm"),
        ("Eccentricity",           "eccentricity_mean_mm",   "eccentricity_max_mm",        "mm"),
        ("Ovality",                "ovality_mean_pct",       "ovality_max_pct",            "%"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._translate = lambda text: text
        self._params: dict = {}
        self._sections = []
        self._ref_sections = []
        self._profile = "Circle"
        # Keys whose values come from single-scan geometry (not true T0 deformation).
        # These cards show a "C閭잙끃奎 T0" warning instead of a misleading number.
        self._single_scan_keys: set = set()
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(8)

        # Overall status banner
        self._banner = QtWidgets.QLabel(self._translate("No data yet - run Steps 5.1 to 5.6 to populate the dashboard."))
        self._banner.setWordWrap(True)
        self._banner.setAlignment(QtCore.Qt.AlignCenter)
        self._banner.setMinimumHeight(36)
        self._banner.setStyleSheet(
            "QLabel{background:#F1F5F9;color:#475569;border:1px solid #CBD5E1;"
            "border-radius:6px;padding:6px 12px;font-weight:600;font-size:10.5pt;}")
        outer.addWidget(self._banner)

        # Metric card grid (2 x 2)
        card_grid = QtWidgets.QGridLayout()
        card_grid.setSpacing(8)
        self._cards = {}
        for idx, (title, k_mean, k_max, unit) in enumerate(self._METRICS):
            card = self._make_card(title, unit)
            self._cards[k_mean] = card
            card_grid.addWidget(card["frame"], idx // 2, idx % 2)
        outer.addLayout(card_grid)

        # General info row
        info_frame = QtWidgets.QFrame()
        info_frame.setStyleSheet(
            "QFrame{background:#EFF6FF;border:1px solid #BFDBFE;border-radius:6px;padding:4px;}")
        info_lay = QtWidgets.QHBoxLayout(info_frame)
        info_lay.setContentsMargins(10, 6, 10, 6)
        info_lay.setSpacing(20)
        self._lbl_profile  = self._info_label("Profile: --")
        self._lbl_sections = self._info_label("Sections: --")
        self._lbl_length   = self._info_label("Length: --")
        self._lbl_rmse     = self._info_label("Reg. RMSE: --")
        for lbl in (self._lbl_profile, self._lbl_sections,
                    self._lbl_length, self._lbl_rmse):
            info_lay.addWidget(lbl)
        info_lay.addStretch()
        outer.addWidget(info_frame)

        # Section alerts table (worst 8)
        self._alerts_box = QtWidgets.QGroupBox("Section Alerts (worst 8)")
        self._alerts_box.setStyleSheet(
            "QGroupBox{font-weight:600;color:#1E3A5F;border:1px solid #CBD5E1;"
            "border-radius:6px;margin-top:8px;padding-top:4px;}"
            "QGroupBox::title{subcontrol-origin:margin;left:10px;}")
        alerts_lay = QtWidgets.QVBoxLayout(self._alerts_box)
        alerts_lay.setContentsMargins(4, 4, 4, 4)
        self._alerts_table = QtWidgets.QTableWidget(0, 4)
        self._alerts_table.setHorizontalHeaderLabels(
            ["Chainage", "Status", "Issues", "Details"])
        self._alerts_table.horizontalHeader().setStretchLastSection(True)
        self._alerts_table.verticalHeader().setVisible(False)
        self._alerts_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._alerts_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._alerts_table.setMinimumHeight(120)
        self._alerts_table.setMaximumHeight(200)
        self._alerts_table.setStyleSheet(
            "QTableWidget{border:none;font-size:9pt;}"
            "QTableWidget::item{padding:3px 6px;}"
            "QHeaderView::section{background:#E2E8F0;color:#334155;padding:4px;"
            "font-weight:600;font-size:8.5pt;border:none;border-bottom:1px solid #CBD5E1;}")
        alerts_lay.addWidget(self._alerts_table)
        outer.addWidget(self._alerts_box)

        # Refresh button
        self._refresh_btn = QtWidgets.QPushButton("Refresh Dashboard")
        self._refresh_btn.setStyleSheet(
            "QPushButton{background:#1D4ED8;color:white;border:none;border-radius:6px;"
            "padding:6px 16px;font-weight:700;}"
            "QPushButton:hover{background:#2563EB;}")
        self._refresh_btn.clicked.connect(self._refresh)
        outer.addWidget(self._refresh_btn, 0, QtCore.Qt.AlignRight)

    def retranslate(self, translate: Callable[[str], str]) -> None:
        """Update static dashboard labels when the app language changes."""
        self._translate = translate
        self._alerts_box.setTitle(translate("Section Alerts (worst 8)"))
        self._alerts_table.setHorizontalHeaderLabels([
            translate("Chainage"), translate("Status"),
            translate("Issues"), translate("Details")])
        self._refresh_btn.setText(translate("Refresh Dashboard"))
        for title, k_mean, _k_max, _unit in self._METRICS:
            card = self._cards.get(k_mean)
            if card is not None:
                card["title_lbl"].setText(translate(title))
        self._refresh()

    # ------------------------------------------------------------------
    @staticmethod
    def _info_label(text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet(
            "color:#1E3A5F;font-size:9pt;font-weight:600;background:transparent;")
        return lbl

    @staticmethod
    def _make_card(title: str, unit: str) -> dict:
        """Return a dict with references to the card's sub-widgets."""
        frame = QtWidgets.QFrame()
        frame.setMinimumHeight(90)
        frame.setStyleSheet(
            "QFrame{background:#F8FAFC;border:1px solid #CBD5E1;"
            "border-radius:8px;padding:4px;}")
        lay = QtWidgets.QVBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)

        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setStyleSheet("color:#475569;font-size:9pt;font-weight:600;background:transparent;")

        lbl_mean = QtWidgets.QLabel("--")
        lbl_mean.setStyleSheet("color:#111827;font-size:16pt;font-weight:800;background:transparent;")
        lbl_mean.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        lbl_max = QtWidgets.QLabel(f"max: -- {unit}")
        lbl_max.setStyleSheet("color:#64748B;font-size:8.5pt;background:transparent;")

        lbl_badge = QtWidgets.QLabel("--")
        lbl_badge.setAlignment(QtCore.Qt.AlignCenter)
        lbl_badge.setFixedHeight(20)
        lbl_badge.setStyleSheet(
            "background:#E2E8F0;color:#64748B;border-radius:4px;"
            "font-size:8pt;font-weight:700;padding:1px 6px;")

        lay.addWidget(lbl_title)
        lay.addWidget(lbl_mean)
        lay.addWidget(lbl_max)
        lay.addWidget(lbl_badge)

        return {
            "frame": frame, "unit": unit,
            "mean": lbl_mean, "max": lbl_max,
            "badge": lbl_badge, "title_lbl": lbl_title,
        }

    # ------------------------------------------------------------------
    def update_params(self, params: dict) -> None:
        """Update metric cards from a parameter dict (from _show_params)."""
        self._params.update(params)
        self._refresh()

    def update_step6_summary(self, series: dict = None, forecast: dict = None) -> None:
        """Push Step 6 trend peaks into the crown cards + banner."""
        series = series or {}
        params = {}
        crown = np.asarray(series.get("crown_settlement_mm", []), dtype=np.float64)
        if crown.size:
            finite = crown[np.isfinite(crown)]
            if finite.size:
                # Use absolute peak magnitude for cards; sign preserved in max abs pick.
                peak_idx = int(np.nanargmax(np.abs(crown)))
                peak = float(crown[peak_idx])
                params["crown_settlement_mm"] = abs(peak)
                params["crown_settlement_max_mm"] = abs(peak)
        p95 = np.asarray(series.get("p95_abs_mm", []), dtype=np.float64)
        if p95.size and np.any(np.isfinite(p95)):
            # Keep as supplemental context via RMSE/info style fields is not ideal;
            # only fill crown if missing.
            if "crown_settlement_mm" not in params:
                params["crown_settlement_mm"] = float(np.nanmax(np.abs(p95)))
                params["crown_settlement_max_mm"] = params["crown_settlement_mm"]
        if params:
            # Clear single-scan flags for crown once true T0/Tn trend exists.
            self._single_scan_keys.discard("crown_settlement_mm")
            self._single_scan_keys.discard("crown_settlement_max_mm")
            self._params.update(params)
        # stash short note for banner consumers via params
        if series.get("crown_chainage_m") is not None:
            try:
                self._params["step6_crown_chainage_m"] = float(series.get("crown_chainage_m"))
            except Exception:
                pass
        if forecast and forecast.get("ok"):
            self._params["step6_forecast_ready"] = 1.0
        self._refresh()

    def update_sections(self, sections, ref_sections=None, profile: str = "Circle",
                        epoch_sections=None) -> None:
        """Update section alerts table.

        ``epoch_sections`` (per-times section lists, T0 first) makes the alert
        statuses reflect the worst times vs T0, consistent with the 2D track.
        """
        self._sections = sections or []
        self._ref_sections = ref_sections or []
        self._epoch_sections = epoch_sections or []
        self._profile = profile
        self._refresh()

    def clear(self) -> None:
        """Reset to empty state."""
        self._params = {}
        self._sections = []
        self._ref_sections = []
        self._epoch_sections = []
        self._single_scan_keys = set()
        self._refresh()

    def set_reference_flags(self, single_scan_keys) -> None:
        """Mark metric keys whose values come from single-scan geometry (no T0).

        Cards for these keys show "??C閭잙끃奎 T0" instead of a misleading number.
        Call this whenever new parameters are loaded.

        Example::
            dashboard.set_reference_flags({"crown_settlement_mm",
                                            "crown_settlement_max_mm"})
        """
        self._single_scan_keys = set(single_scan_keys)
        self._refresh()

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        """Rebuild all cards and alerts from current data."""
        self._refresh_cards()
        self._refresh_banner()
        self._refresh_info()
        self._refresh_alerts()

    def _refresh_cards(self) -> None:
        from ..common import classify_parameter
        for idx, (title, k_mean, k_max, unit) in enumerate(self._METRICS):
            card = self._cards.get(k_mean)
            if card is None:
                continue

            # Single-scan: metric is geometry, NOT real deformation.
            if k_mean in self._single_scan_keys:
                card["mean"].setText(self._translate("Requires T0"))
                card["max"].setText(self._translate("Load 2 scans to compare"))
                card["badge"].setText("?")
                card["badge"].setStyleSheet(
                    "background:#94A3B8;color:white;border-radius:4px;"
                    "font-size:8pt;font-weight:700;padding:1px 6px;")
                card["frame"].setStyleSheet(
                    "QFrame{background:#F8FAFC;border:1px dashed #94A3B8;"
                    "border-radius:8px;padding:4px;}")
                card["mean"].setStyleSheet(
                    "color:#94A3B8;font-size:13pt;font-weight:700;background:transparent;")
                card["frame"].setToolTip(self._translate(
                    "This metric requires a T0 reference scan for reliable deformation calculation. "
                    "Load T0 and rerun the pipeline. Current values may be absolute geometry, not deformation."))
                continue  # skip threshold classification for this card

            v_mean = self._params.get(k_mean)
            v_max  = self._params.get(k_max)
            status = classify_parameter(k_mean, v_mean) if v_mean is not None else ""

            # Format mean
            if v_mean is not None and np.isfinite(float(v_mean)):
                if unit == "%":
                    mean_txt = f"{float(v_mean):.3f} {unit}"
                else:
                    mean_txt = f"{float(v_mean):+.1f} {unit}"
            else:
                mean_txt = "--"

            # Format max
            if v_max is not None and np.isfinite(float(v_max)):
                if unit == "%":
                    max_txt = f"{self._translate('max:')} {float(v_max):.3f} {unit}"
                else:
                    max_txt = f"{self._translate('max:')} {float(v_max):+.1f} {unit}"
            else:
                max_txt = f"{self._translate('max:')} -- {unit}"

            card["mean"].setText(mean_txt)
            card["max"].setText(max_txt)
            card["frame"].setToolTip("")   # clear any previous tooltip

            # Status badge colours
            if status == "CRITICAL":
                bg, bd, fg = self._C_CRIT_BG, self._C_CRIT_BD, self._C_CRIT
                badge_style = (f"background:{self._C_CRIT};color:white;border-radius:4px;"
                               "font-size:8pt;font-weight:700;padding:1px 6px;")
                frame_style = (f"QFrame{{background:{self._C_CRIT_BG};border:2px solid {self._C_CRIT_BD};"
                               "border-radius:8px;padding:4px;}}")
                mean_color = self._C_CRIT
            elif status == "CAUTION":
                bg, bd, fg = self._C_CAUT_BG, self._C_CAUT_BD, self._C_CAUT
                badge_style = (f"background:{self._C_CAUT};color:white;border-radius:4px;"
                               "font-size:8pt;font-weight:700;padding:1px 6px;")
                frame_style = (f"QFrame{{background:{self._C_CAUT_BG};border:2px solid {self._C_CAUT_BD};"
                               "border-radius:8px;padding:4px;}}")
                mean_color = self._C_CAUT
            elif status == "OK":
                bg, bd, fg = self._C_OK_BG, self._C_OK_BD, self._C_OK
                badge_style = (f"background:{self._C_OK};color:white;border-radius:4px;"
                               "font-size:8pt;font-weight:700;padding:1px 6px;")
                frame_style = (f"QFrame{{background:{self._C_OK_BG};border:2px solid {self._C_OK_BD};"
                               "border-radius:8px;padding:4px;}}")
                mean_color = self._C_OK
            else:
                badge_style = ("background:#E2E8F0;color:#64748B;border-radius:4px;"
                               "font-size:8pt;font-weight:700;padding:1px 6px;")
                frame_style = (f"QFrame{{background:{self._C_NONE_BG};border:1px solid {self._C_NONE_BD};"
                               "border-radius:8px;padding:4px;}}")
                mean_color = "#111827"

            card["frame"].setStyleSheet(frame_style)
            card["mean"].setStyleSheet(
                f"color:{mean_color};font-size:16pt;font-weight:800;background:transparent;")
            card["badge"].setStyleSheet(badge_style)
            card["badge"].setText(self._translate(status) if status else "--")

    def _refresh_banner(self) -> None:
        from ..common import classify_parameter
        n_crit = sum(
            1 for (_, k, _, _) in self._METRICS
            if classify_parameter(k, self._params.get(k)) == "CRITICAL"
        )
        n_caut = sum(
            1 for (_, k, _, _) in self._METRICS
            if classify_parameter(k, self._params.get(k)) == "CAUTION"
        )
        n_ok = sum(
            1 for (_, k, _, _) in self._METRICS
            if classify_parameter(k, self._params.get(k)) == "OK"
        )
        total = n_crit + n_caut + n_ok

        # Section-level alerts (clearance + per-section dW/dH/ovality/ecc) come
        # from the SAME classify_sections() the alerts table uses, so the banner
        # can never read "all safe" while the table shows CRITICAL sections.
        sec_crit = sec_caut = 0
        if self._sections:
            try:
                for status, _issues in classify_sections(self._sections, self._ref_sections, epoch_sections=getattr(self, "_epoch_sections", None)):
                    if status == "CRITICAL":
                        sec_crit += 1
                    elif status == "CAUTION":
                        sec_caut += 1
            except Exception:
                pass

        crit = n_crit + sec_crit
        caut = n_caut + sec_caut
        sec_note = (f",  {sec_crit} {self._translate('section alert(s)')}"
                    if sec_crit else
                    (f",  {sec_caut} {self._translate('section alert(s)')}" if sec_caut else ""))

        if total == 0 and not self._sections:
            self._banner.setText(
                self._translate("No data yet - run Steps 5.1 to 5.6 to populate the dashboard."))
            self._banner.setStyleSheet(
                "QLabel{background:#F1F5F9;color:#475569;border:1px solid #CBD5E1;"
                "border-radius:6px;padding:6px 12px;font-weight:600;font-size:10.5pt;}")
        elif crit > 0:
            self._banner.setText(
                f"{self._translate('CRITICAL')}  --  {n_crit} {self._translate('critical metric(s)')},"
                f"  {n_caut} {self._translate('caution')},  {n_ok} {self._translate('OK')}{sec_note}")
            self._banner.setStyleSheet(
                f"QLabel{{background:{self._C_CRIT_BG};color:{self._C_CRIT};"
                "border:2px solid #FCA5A5;border-radius:6px;padding:6px 12px;"
                "font-weight:800;font-size:11pt;}}")
        elif caut > 0:
            self._banner.setText(
                f"{self._translate('CAUTION')}  --  {n_caut} {self._translate('caution metric(s)')},"
                f"  {n_ok} {self._translate('OK')}{sec_note}")
            self._banner.setStyleSheet(
                f"QLabel{{background:{self._C_CAUT_BG};color:{self._C_CAUT};"
                "border:2px solid #FCD34D;border-radius:6px;padding:6px 12px;"
                "font-weight:800;font-size:11pt;}}")
        else:
            self._banner.setText(
                f"{self._translate('OK')}  --  {self._translate('All metrics within safe limits.').format(n=n_ok)}")
            self._banner.setStyleSheet(
                f"QLabel{{background:{self._C_OK_BG};color:{self._C_OK};"
                "border:2px solid #6EE7B7;border-radius:6px;padding:6px 12px;"
                "font-weight:800;font-size:11pt;}}")

    def _refresh_info(self) -> None:
        n_sec = len(self._sections)
        valid = [s for s in self._sections if s.pts_2d is not None]

        if valid:
            chainages = [s.chainage for s in valid if np.isfinite(s.chainage)]
            if len(chainages) >= 2:
                length_m = max(chainages) - min(chainages)
                self._lbl_length.setText(f"{self._translate('Length:')} {length_m:.1f} m")
            else:
                self._lbl_length.setText(f"{self._translate('Length:')} --")
            self._lbl_sections.setText(f"{self._translate('Sections:')} {len(valid)}")
        else:
            self._lbl_length.setText(f"{self._translate('Length:')} --")
            self._lbl_sections.setText(f"{self._translate('Sections:')} {n_sec if n_sec else '--'}")

        self._lbl_profile.setText(f"{self._translate('Profile:')} {self._profile or '--'}")

        # RMSE from params if available
        rmse = self._params.get("rmse_mm")
        if rmse is not None and np.isfinite(float(rmse)):
            self._lbl_rmse.setText(f"{self._translate('Reg. RMSE:')} {float(rmse):.2f} mm")
        else:
            self._lbl_rmse.setText(f"{self._translate('Reg. RMSE:')} --")

    def _refresh_alerts(self) -> None:
        tbl = self._alerts_table
        tbl.setRowCount(0)
        if not self._sections:
            return

        # Gather all sections with their status and sort by severity then ch.
        # Uses classify_sections() ??same classifier as ruler/2D-track/3D markers.
        alerts = []
        statuses = classify_sections(self._sections, self._ref_sections, epoch_sections=getattr(self, "_epoch_sections", None))
        for sg, (status, issues) in zip(self._sections, statuses):
            if status != "OK":
                alerts.append((status, sg.chainage, issues))

        # Sort: CRITICAL first, then by chainage descending within level
        alerts.sort(key=lambda x: (0 if x[0] == "CRITICAL" else 1, -x[1]))
        alerts = alerts[:8]   # cap at 8

        status_colors = {
            "CRITICAL": (self._C_CRIT_BG, self._C_CRIT),
            "CAUTION":  (self._C_CAUT_BG, self._C_CAUT),
        }

        for status, chainage, issues in alerts:
            r = tbl.rowCount()
            tbl.insertRow(r)

            ch_item = QtWidgets.QTableWidgetItem(f"Ch {chainage:.2f} m")
            ch_item.setTextAlignment(QtCore.Qt.AlignCenter)
            tbl.setItem(r, 0, ch_item)

            bg, fg = status_colors.get(status, ("#F8FAFC", "#111827"))
            st_item = QtWidgets.QTableWidgetItem(self._translate(status))
            st_item.setTextAlignment(QtCore.Qt.AlignCenter)
            st_item.setBackground(QtGui.QColor(bg))
            st_item.setForeground(QtGui.QColor(fg))
            f = st_item.font(); f.setBold(True); st_item.setFont(f)
            tbl.setItem(r, 1, st_item)

            n_issues = len(issues)
            tbl.setItem(r, 2, QtWidgets.QTableWidgetItem(f"{n_issues} {self._translate('issue(s)')}"))

            detail_parts = []
            for level, label, val, unit in issues:
                detail_parts.append(f"{label}: {val:+.1f} {unit}" if isinstance(val, float) else f"{label}: {val}")
            tbl.setItem(r, 3, QtWidgets.QTableWidgetItem("  |  ".join(detail_parts)))

        tbl.resizeColumnsToContents()
        if not alerts:
            tbl.insertRow(0)
            msg = QtWidgets.QTableWidgetItem(self._translate("No deformation alerts detected."))
            msg.setForeground(QtGui.QColor(self._C_OK))
            tbl.setItem(0, 0, msg)
            tbl.setSpan(0, 0, 1, 4)


# ------------------------------------------------------------------------------
# Main Window & PySide6 UI




