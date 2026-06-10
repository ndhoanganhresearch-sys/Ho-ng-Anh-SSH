"""Standalone dialogs for the main window.

Extracted from ui/main_window.py (224 KB) as part of the incremental module
split: each dialog is self-contained, so main_window keeps only the window
class itself. main_window re-imports these names, existing references work
unchanged.
"""
from ..common import *
from .i18n_v4 import tr as _tr


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
