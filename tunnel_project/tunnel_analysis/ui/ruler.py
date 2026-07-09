from ..common import *

# Section warning classification is core/Qt-free; ruler widgets use it to stay
# consistent with section view, 3D markers, dashboard and work orders.
from ..section_warnings import classify_sections, section_warning_text


class ChainageRulerWidget(QtWidgets.QWidget):
    """Full-width chainage ruler always visible below the viewport.

    • Draws the entire tunnel chainage range as a horizontal track.
    • CRITICAL positions → red filled triangles (▼) above the track.
    • CAUTION positions  → amber filled triangles (▼) above the track.
    • Section segments coloured by worst status in that zone.
    • Current section position → thin white vertical indicator line.
    • Click anywhere to jump to the nearest section.
    """

    jumped = QtCore.Signal(int)   # emits section index

    _H_TOTAL  = 62
    _H_TRI    = 18    # height of marker row above track
    _H_TRACK  = 14    # track band height
    _H_LABEL  = 16    # chainage label row height
    _ML       = 52    # left margin (for min-ch label)
    _MR       = 52    # right margin

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self._H_TOTAL)
        self.setMinimumWidth(200)
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip("Thanh lý trình — Click để nhảy đến mặt cắt  |  "
                        "▼ Đỏ = CRITICAL  ▼ Vàng = CAUTION")

        self._min_ch:   float       = 0.0
        self._max_ch:   float       = 0.0
        self._sections: list        = []    # SectionGeometry list
        self._seg_colors: list      = []    # per-section status color hex
        self._marks:    list        = []    # (frac, color, tooltip, idx) — warnings only
        self._hotspots: list        = []    # p95 trend markers shown as green stars
        self._hotspot_source: list  = []    # raw hotspot dicts, rebuilt after sections load
        self._fracs:    list        = []    # fraction for every section
        self._cur_frac: float       = -1.0  # current position indicator

    # ── Public API ─────────────────────────────────────────────────────────

    def set_sections(self, sections, ref_sections=None, epoch_sections=None) -> None:
        """Populate ruler from SectionGeometry list (Tn) and optional T0.

        Uses ``classify_sections()`` so the ruler is always consistent with
        the 2D warning track and 3D flag-pole markers. When ``epoch_sections``
        is given, the status is the worst across all epochs vs T0.
        """
        if not sections:
            self._sections = []; self._seg_colors = []; self._marks = []; self._hotspots = []; self._hotspot_source = []
            self._fracs = []; self._min_ch = self._max_ch = 0.0
            self._cur_frac = -1.0; self.update(); return

        chs = [s.chainage for s in sections]
        self._min_ch = min(chs); self._max_ch = max(chs)
        span = max(self._max_ch - self._min_ch, 1e-6)
        self._sections = sections
        self._fracs = [(c - self._min_ch) / span for c in chs]

        # Use the shared classifier so all views stay in sync.
        statuses = classify_sections(sections, ref_sections or [],
                                     epoch_sections=epoch_sections)

        seg_colors = []
        marks = []
        for i, (ws, wi) in enumerate(statuses):
            if ws == "CRITICAL":
                seg_colors.append("#DC2626")
                detail = section_warning_text(wi, limit=2) if wi else "CRITICAL"
                tip = f"CRITICAL  Ch {sections[i].chainage:.1f} m\n{detail}"
                marks.append((self._fracs[i], "#DC2626", tip, i))
            elif ws == "CAUTION":
                seg_colors.append("#D97706")
                detail = section_warning_text(wi, limit=2) if wi else "CAUTION"
                tip = f"CAUTION  Ch {sections[i].chainage:.1f} m\n{detail}"
                marks.append((self._fracs[i], "#D97706", tip, i))
            else:
                seg_colors.append("#1E3A5F")   # OK → dark blue (barely visible)

        self._seg_colors = seg_colors
        self._marks = marks
        self._rebuild_hotspots()
        self.update()

    def set_hotspots(self, hotspots) -> None:
        """Add p95 trend markers to the chainage ruler.

        ``hotspots`` is a list of dicts from the time-series trend, each with
        chainage_m, label, position and value_mm. Markers are separate from
        warning triangles and are drawn as green stars above the track.
        """
        self._hotspot_source = list(hotspots or [])
        self._rebuild_hotspots()
        self.update()

    def _rebuild_hotspots(self) -> None:
        marks = []
        if self._max_ch > self._min_ch and self._sections:
            span = self._max_ch - self._min_ch
            chs = [float(getattr(s, "chainage", 0.0)) for s in self._sections]
            for hp in self._hotspot_source:
                try:
                    ch = float(hp.get("chainage_m"))
                    frac = max(0.0, min(1.0, (ch - self._min_ch) / span))
                    idx = min(range(len(chs)), key=lambda i: abs(chs[i] - ch))
                    val = float(hp.get("p95_abs_mm", hp.get("value_mm", 0.0)))
                    label = str(hp.get("label", "Tn"))
                    tip = (f"Trend p95 hotspot  {label}\n"
                           f"Ch {ch:.1f} m | {hp.get('position', '')} | p95 {val:.1f} mm")
                    marks.append((frac, "#22C55E", tip, idx, label))
                except Exception:
                    continue
        self._hotspots = marks

    def set_current(self, chainage: float) -> None:
        """Move the current-position indicator to the given chainage."""
        if self._max_ch > self._min_ch:
            self._cur_frac = (chainage - self._min_ch) / (self._max_ch - self._min_ch)
        else:
            self._cur_frac = -1.0
        self.update()

    def clear(self) -> None:
        self.set_sections([])

    # ── Painting ───────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        W, H = self.width(), self.height()
        ML, MR = self._ML, self._MR
        TW = max(W - ML - MR, 1)  # track width

        track_y = self._H_TRI + 2
        track_h = self._H_TRACK
        label_y = track_y + track_h + 4

        # ── Background ──────────────────────────────────────────────────
        p.fillRect(0, 0, W, H, QtGui.QColor("#1E293B"))

        # ── Section segments ────────────────────────────────────────────
        if self._sections:
            n = len(self._fracs)
            for i, frac in enumerate(self._fracs):
                x = ML + int(frac * TW)
                # segment width = half gap to neighbours
                prev_x = ML + int(self._fracs[i - 1] * TW) if i > 0 else ML
                next_x = ML + int(self._fracs[i + 1] * TW) if i < n - 1 else ML + TW
                seg_left = (x + prev_x) // 2
                seg_right = (x + next_x) // 2
                sw = max(seg_right - seg_left, 2)
                qc = QtGui.QColor(self._seg_colors[i])
                qc.setAlpha(200)
                p.fillRect(seg_left, track_y, sw, track_h, qc)
        else:
            # Empty track
            p.fillRect(ML, track_y, TW, track_h, QtGui.QColor("#1E3A5F"))

        # Track border
        p.setPen(QtGui.QPen(QtGui.QColor("#334155"), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRect(ML, track_y, TW, track_h)

        # ── Warning triangles ────────────────────────────────────────────
        for frac, color, _tip, _idx in self._marks:
            cx = ML + int(frac * TW)
            cx = max(ML + 5, min(ML + TW - 5, cx))
            tri_top_y = 1
            tri_bot_y = track_y
            half = 6
            path = QtGui.QPainterPath()
            path.moveTo(cx - half, tri_top_y)
            path.lineTo(cx + half, tri_top_y)
            path.lineTo(cx,        tri_bot_y)
            path.closeSubpath()
            p.setBrush(QtGui.QColor(color))
            p.setPen(QtGui.QPen(QtGui.QColor(color).darker(140), 1))
            p.drawPath(path)

        # Trend p95 hotspots: green stars with T-labels, drawn above warnings.
        if self._hotspots:
            font_hot = QtGui.QFont("Segoe UI", 7, QtGui.QFont.Bold)
            p.setFont(font_hot)
            fm_hot = QtGui.QFontMetrics(font_hot)
            for item in self._hotspots:
                frac, _color, _tip, _idx, label = item
                cx = ML + int(frac * TW)
                cx = max(ML + 8, min(ML + TW - 8, cx))
                cy = track_y - 6
                p.setPen(QtGui.QPen(QtGui.QColor("#14532D"), 1))
                p.setBrush(QtGui.QColor("#22C55E"))
                path = QtGui.QPainterPath()
                path.moveTo(cx, cy - 8)
                path.lineTo(cx + 3, cy - 3)
                path.lineTo(cx + 8, cy - 3)
                path.lineTo(cx + 4, cy + 1)
                path.lineTo(cx + 6, cy + 7)
                path.lineTo(cx, cy + 4)
                path.lineTo(cx - 6, cy + 7)
                path.lineTo(cx - 4, cy + 1)
                path.lineTo(cx - 8, cy - 3)
                path.lineTo(cx - 3, cy - 3)
                path.closeSubpath()
                p.drawPath(path)
                text = f"{label} p95"
                tw = fm_hot.horizontalAdvance(text)
                p.setPen(QtGui.QColor("#DCFCE7"))
                p.drawText(cx - tw // 2, max(9, cy - 10), text)

        # ── Current position indicator ───────────────────────────────────
        if 0.0 <= self._cur_frac <= 1.0:
            cx = ML + int(self._cur_frac * TW)
            p.setPen(QtGui.QPen(QtGui.QColor("#FFFFFF"), 2))
            p.drawLine(cx, track_y - 1, cx, track_y + track_h + 1)
            # Small blue circle at top of track
            p.setBrush(QtGui.QColor("#38BDF8"))
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(cx - 4, track_y - 5, 8, 8)

        # ── Tick marks + labels ──────────────────────────────────────────
        if self._max_ch > self._min_ch:
            import math as _math
            span = self._max_ch - self._min_ch
            for iv in [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]:
                if span / iv <= 18:
                    interval = iv; break
            else:
                interval = 1000
            font_sm = QtGui.QFont("Segoe UI", 7)
            p.setFont(font_sm)
            p.setPen(QtGui.QColor("#64748B"))
            fm = QtGui.QFontMetrics(font_sm)
            start = _math.ceil(self._min_ch / interval) * interval
            ch = start
            while ch <= self._max_ch + 1e-6:
                frac = (ch - self._min_ch) / span
                x = ML + int(frac * TW)
                p.setPen(QtGui.QPen(QtGui.QColor("#475569"), 1))
                p.drawLine(x, track_y + track_h, x, track_y + track_h + 3)
                lbl = f"{ch:.0f}m"
                lw = fm.horizontalAdvance(lbl)
                p.setPen(QtGui.QColor("#94A3B8"))
                p.drawText(x - lw // 2, label_y + fm.ascent(), lbl)
                ch += interval

        # ── Min / max chainage labels ────────────────────────────────────
        font_b = QtGui.QFont("Segoe UI", 7, QtGui.QFont.Bold)
        p.setFont(font_b)
        p.setPen(QtGui.QColor("#CBD5E1"))
        fm2 = QtGui.QFontMetrics(font_b)
        lbl_min = f"Ch {self._min_ch:.1f}m"
        lbl_max = f"Ch {self._max_ch:.1f}m"
        mid_y = track_y + track_h // 2 + fm2.ascent() // 2
        p.drawText(2, mid_y, lbl_min)
        p.drawText(W - fm2.horizontalAdvance(lbl_max) - 2, mid_y, lbl_max)

        p.end()

    # ── Mouse ───────────────────────────────────────────────────────────

    def mouseMoveEvent(self, event):
        px = event.x()
        tip = self._tip_at(px)
        if tip:
            QtWidgets.QToolTip.showText(event.globalPos(), tip, self)
        elif self._max_ch > self._min_ch:
            frac = self._px_to_frac(px)
            if 0.0 <= frac <= 1.0:
                ch = self._min_ch + frac * (self._max_ch - self._min_ch)
                QtWidgets.QToolTip.showText(
                    event.globalPos(), f"Ch {ch:.1f} m", self)
        else:
            QtWidgets.QToolTip.hideText()

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        px = event.x()
        # Check warning marker hit first
        idx = self._mark_idx_at(px)
        if idx >= 0:
            self.jumped.emit(idx); return
        # Otherwise jump to nearest section
        if self._fracs:
            frac = self._px_to_frac(px)
            nearest = min(range(len(self._fracs)),
                          key=lambda i: abs(self._fracs[i] - frac))
            self.jumped.emit(nearest)

    # ── Helpers ─────────────────────────────────────────────────────────

    def _px_to_frac(self, px: int) -> float:
        TW = max(self.width() - self._ML - self._MR, 1)
        return (px - self._ML) / TW

    def _tip_at(self, px: int) -> str:
        TW = max(self.width() - self._ML - self._MR, 1)
        for frac, _c, tip, _i, *_rest in self._hotspots:
            if abs(self._ML + int(frac * TW) - px) <= 9:
                return tip
        for frac, _c, tip, _i in self._marks:
            if abs(self._ML + int(frac * TW) - px) <= 9:
                return tip
        return ""

    def _mark_idx_at(self, px: int) -> int:
        TW = max(self.width() - self._ML - self._MR, 1)
        for frac, _c, _t, idx, *_rest in self._hotspots:
            if abs(self._ML + int(frac * TW) - px) <= 9:
                return idx
        for frac, _c, _t, idx in self._marks:
            if abs(self._ML + int(frac * TW) - px) <= 9:
                return idx
        return -1

# ------------------------------------------------------------------------------
# Warning track — thin painted bar showing which sections are critical/caution
# ------------------------------------------------------------------------------

class _WarningTrack(QtWidgets.QWidget):
    """Thin bar below the slider showing coloured marks at warning-section positions.

    CRITICAL sections → red dot   CAUTION sections → amber dot
    Hover over a dot to see chainage + status in a tooltip.
    """

    jumped = QtCore.Signal(int)   # emits section index when user clicks a mark

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(14)
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._marks: list = []   # list of (frac 0-1, color_hex, label, sec_idx)

    def set_marks(self, marks: list) -> None:
        self._marks = marks
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background track
        p.fillRect(0, 0, w, h, QtGui.QColor("#E2E8F0"))

        r = h // 2
        for frac, color, _label, _idx in self._marks:
            cx = int(frac * w)
            cx = max(r, min(w - r, cx))
            qc = QtGui.QColor(color)
            p.setBrush(qc)
            p.setPen(QtGui.QPen(qc.darker(140), 1))
            p.drawEllipse(cx - r, 0, h, h)
        p.end()

    def mouseMoveEvent(self, event):
        tip = self._hit(event.x())
        if tip:
            QtWidgets.QToolTip.showText(event.globalPos(), tip, self)
        else:
            QtWidgets.QToolTip.hideText()

    def mousePressEvent(self, event):
        idx = self._hit_idx(event.x())
        if idx >= 0:
            self.jumped.emit(idx)

    def _hit(self, px: int) -> str:
        w = max(self.width(), 1)
        for frac, _color, label, _idx in self._marks:
            if abs(int(frac * w) - px) <= 8:
                return label
        return ""

    def _hit_idx(self, px: int) -> int:
        w = max(self.width(), 1)
        for frac, _color, _label, idx in self._marks:
            if abs(int(frac * w) - px) <= 8:
                return idx
        return -1


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
