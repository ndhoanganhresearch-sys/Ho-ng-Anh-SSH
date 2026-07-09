"""Section warning classification — the single source of truth.

Pure NumPy logic (no Qt): classifies every cross-section as OK / CAUTION /
CRITICAL from its geometry vs an optional T0 reference. Used by the 2D warning
track, chainage ruler, 3D markers, dashboard alerts and the AI work order, so
all views stay consistent.

Lived in tunnel_analysis.ui.widgets historically; extracted here so core /
headless code (batch, rag_ai, reports) can depend on it without importing the
Qt UI. ui.widgets re-exports these names, so existing imports keep working.
"""
import numpy as np

from .models import SectionGeometry

SECTION_DELTA_CAUTION_MM = 10.0
SECTION_DELTA_CRITICAL_MM = 25.0


def _directed_delta_label(label: str, delta: float) -> str:
    """Return a section-delta label that explains the sign of the change."""
    if label == "dW":
        return "convergence dW" if delta < 0 else "expansion dW"
    if label == "dH":
        return "clearance loss dH" if delta < 0 else "height gain dH"
    if label == "dR":
        return "radius loss dR" if delta < 0 else "radius gain dR"
    if label == "dOval":
        return "ovality change dOval"
    if label == "dEcc":
        return "eccentricity change dEcc"
    return label


def section_warning_status(sg: SectionGeometry, ref_sg: SectionGeometry = None):
    """Classify risk. With T0 available, compare Tn against T0 baseline."""
    issues = []
    status = "OK"

    def add(level: str, label: str, value: float, unit: str) -> None:
        nonlocal status
        if level == "CRITICAL" or status == "OK":
            status = level
        elif level == "CAUTION" and status != "CRITICAL":
            status = level
        issues.append((level, label, value, unit))

    if sg.clearance_violation:
        val = sg.min_clearance_dist * 1e3 if np.isfinite(sg.min_clearance_dist) else float("nan")
        add("CRITICAL", "clearance", val, "mm")

    if ref_sg is not None:
        for label, attr in (("dW", "W1"), ("dH", "H1"), ("dR", "radius_fit")):
            a = getattr(sg, attr, float("nan"))
            b = getattr(ref_sg, attr, float("nan"))
            if np.isfinite(a) and np.isfinite(b):
                delta_mm = (a - b) * 1e3
                directed = _directed_delta_label(label, delta_mm)
                if abs(delta_mm) >= SECTION_DELTA_CRITICAL_MM:
                    add("CRITICAL", directed, delta_mm, "mm")
                elif abs(delta_mm) >= SECTION_DELTA_CAUTION_MM:
                    add("CAUTION", directed, delta_mm, "mm")
        if np.isfinite(sg.ovality) and np.isfinite(ref_sg.ovality):
            d_oval = sg.ovality - ref_sg.ovality
            if abs(d_oval) >= 1.0:
                add("CRITICAL", _directed_delta_label("dOval", d_oval), d_oval, "%")
            elif abs(d_oval) >= 0.5:
                add("CAUTION", _directed_delta_label("dOval", d_oval), d_oval, "%")
        if np.isfinite(sg.eccentricity) and np.isfinite(ref_sg.eccentricity):
            d_ecc = sg.eccentricity - ref_sg.eccentricity
            if abs(d_ecc) >= 25.0:
                add("CRITICAL", _directed_delta_label("dEcc", d_ecc), d_ecc, "mm")
            elif abs(d_ecc) >= 10.0:
                add("CAUTION", _directed_delta_label("dEcc", d_ecc), d_ecc, "mm")
    else:
        if np.isfinite(sg.ovality):
            if abs(sg.ovality) >= 1.0:
                add("CRITICAL", "ovality", sg.ovality, "%")
            elif abs(sg.ovality) >= 0.5:
                add("CAUTION", "ovality", sg.ovality, "%")
        if np.isfinite(sg.eccentricity):
            if abs(sg.eccentricity) >= 25.0:
                add("CRITICAL", "eccentricity", sg.eccentricity, "mm")
            elif abs(sg.eccentricity) >= 10.0:
                add("CAUTION", "eccentricity", sg.eccentricity, "mm")
    return status, issues


_SEVERITY = {"OK": 0, "CAUTION": 1, "CRITICAL": 2}


def classify_sections_worst_epoch(epoch_sections):
    """Worst-per-section status across several epochs (T0~Tn).

    ``epoch_sections`` is one per-chainage section list per epoch, T0 first.
    Each later epoch is classified against T0 with the normal
    ``classify_sections`` rules, then per section we keep the worst epoch's
    (status, issues). This is what the 2D warning track / ruler / dashboard use
    when a multi-epoch overlay is loaded, so a section that only becomes
    critical at, say, T5 is still flagged even if the active epoch looks calm.
    """
    epoch_sections = [e for e in (epoch_sections or []) if e]
    if len(epoch_sections) < 2:
        return classify_sections(epoch_sections[0] if epoch_sections else [], None)
    ref = epoch_sections[0]
    per_epoch = [classify_sections(epoch_sections[k], ref)
                 for k in range(1, len(epoch_sections))]
    n = max((len(st) for st in per_epoch), default=0)
    out = []
    for i in range(n):
        best_status, best_issues = "OK", []
        for st_list in per_epoch:
            if i >= len(st_list):
                continue
            st, iss = st_list[i]
            if (_SEVERITY[st] > _SEVERITY[best_status]
                    or (_SEVERITY[st] == _SEVERITY[best_status]
                        and len(iss) > len(best_issues))):
                best_status, best_issues = st, iss
        out.append((best_status, best_issues))
    return out


def classify_sections(sections, ref_sections=None, epoch_sections=None):
    """Classify every section as OK / CAUTION / CRITICAL.

    Uses **robust intra-dataset statistics** so it works even when no T0
    reference is available (single-scan case):

    • Always checks ``clearance_violation`` (CRITICAL).
    • With ref_sections: compares delta W1/H1/radius_fit/ovality/eccentricity
      vs T0 and applies ``local_flags`` to detect local anomalies.
    • Without ref_sections: applies ``local_flags`` directly on absolute
      ovality and eccentricity values so locally-anomalous sections are
      flagged even in a single-scan workflow.

    Returns a list of ``(status, issues)`` tuples, one per section.
    ``status`` is "OK", "CAUTION", or "CRITICAL".
    ``issues`` is a list of ``(level, label, value, unit)`` tuples.

    This is the single source-of-truth used by the 2D warning track,
    chainage ruler, 3D markers and dashboard alerts so all views stay
    consistent.

    When ``epoch_sections`` (a list of per-epoch section lists, T0 first) is
    supplied, the status is taken as the worst across all epochs vs T0 — see
    ``classify_sections_worst_epoch``.
    """
    if epoch_sections and len([e for e in epoch_sections if e]) >= 2:
        return classify_sections_worst_epoch(epoch_sections)
    if not sections:
        return []

    n = len(sections)
    statuses = [["OK", []] for _ in sections]
    ref_list = ref_sections or []

    def add(i, level, label, value, unit):
        cur = statuses[i][0]
        if level == "CRITICAL" or cur == "OK":
            statuses[i][0] = level
        elif level == "CAUTION" and cur != "CRITICAL":
            statuses[i][0] = level
        statuses[i][1].append((level, label, value, unit))

    def local_flags(values, caution_abs, critical_abs, floor, label, unit,
                    local_gate=True):
        """Flag sections exceeding caution/critical absolute thresholds.

        local_gate=True  (dEcc / dOval / single-scan metrics): also require the
          value to be a LOCAL anomaly (v >= median + 3·MAD). This suppresses a
          uniform systematic offset (e.g. a registration-induced eccentricity
          bias) from painting the whole tunnel — the user's earlier complaint.

        local_gate=False (dW / dH / dR — direct differential dimension changes
          vs T0): flag on the ABSOLUTE threshold alone. A registration error
          does not change a measured width/radius, so a large dW/dR is real
          deformation and must be flagged even when it spans a wide band (where
          the local gate would otherwise raise the baseline into the deformed
          range and suppress a genuine CRITICAL — observed: dW=-63mm, dR=-27mm
          went undetected on the complex test dataset).
        """
        arr = np.asarray(values, dtype=np.float64)
        mag = np.abs(arr)
        finite = np.isfinite(mag)
        if not finite.any():
            return
        if local_gate:
            vals = mag[finite]
            med  = float(np.nanmedian(vals))
            mad  = float(np.nanmedian(np.abs(vals - med)))
            robust_sigma = 1.4826 * mad
            local_thr = med + max(3.0 * robust_sigma, floor)
        for i, v in enumerate(mag):
            if not np.isfinite(v):
                continue
            is_local = (not local_gate) or n < 6 or v >= local_thr
            if v >= critical_abs and is_local:
                add(i, "CRITICAL", label, float(arr[i]), unit)
            elif v >= caution_abs and is_local:
                add(i, "CAUTION",  label, float(arr[i]), unit)

    # ── Clearance violation (always, except portal artifacts) ────────────
    # Incomplete rings at the two tunnel mouths leave stray inner points and a
    # mis-fit centerline, so the outermost sections systematically over-report
    # clearance intrusion (observed: every "worst" violation sat at the two
    # chainage ends). Skip a small margin at each end on tunnels long enough for
    # the portal to be a small fraction; short section runs (tests / stub data)
    # are never trimmed so mid-tunnel violations stay flagged.
    portal_n = int(round(n * 0.04)) if n >= 20 else 0
    for i, sec in enumerate(sections):
        if portal_n and (i < portal_n or i >= n - portal_n):
            continue
        if sec.clearance_violation:
            val = (sec.min_clearance_dist * 1e3
                   if np.isfinite(sec.min_clearance_dist) else float("nan"))
            add(i, "CRITICAL", "clearance", val, "mm")

    if ref_list:
        # ── T0 comparison ────────────────────────────────────────────────
        for lbl, attr in (("dW", "W1"), ("dH", "H1"), ("dR", "radius_fit")):
            deltas = []
            for i, sec in enumerate(sections):
                ref = ref_list[i] if i < len(ref_list) else None
                a = getattr(sec, attr, float("nan"))
                b = getattr(ref, attr, float("nan")) if ref is not None else float("nan")
                deltas.append(
                    (a - b) * 1e3 if np.isfinite(a) and np.isfinite(b) else float("nan"))
            # dW/dH/dR are direct dimension changes vs T0 → absolute threshold
            # (no local gate): a large width/radius change is real deformation.
            local_flags(deltas, 10.0, 25.0, 10.0, lbl, "mm", local_gate=False)

        d_oval, d_ecc = [], []
        for i, sec in enumerate(sections):
            ref = ref_list[i] if i < len(ref_list) else None
            d_oval.append(
                sec.ovality - ref.ovality
                if ref is not None and np.isfinite(sec.ovality) and np.isfinite(ref.ovality)
                else float("nan"))
            d_ecc.append(
                sec.eccentricity - ref.eccentricity
                if ref is not None and np.isfinite(sec.eccentricity) and np.isfinite(ref.eccentricity)
                else float("nan"))
        local_flags(d_oval, 0.5, 1.0, 0.35, "dOval", "%")
        local_flags(d_ecc, 10.0, 25.0, 15.0, "dEcc",  "mm")
    else:
        # ── Single-scan: absolute local anomaly detection ─────────────────
        local_flags([s.ovality     for s in sections], 0.5, 1.0,  0.35, "ovality",     "%")
        local_flags([s.eccentricity for s in sections], 10.0, 25.0, 15.0, "eccentricity", "mm")

    return [(st[0], st[1]) for st in statuses]


def section_warning_text(issues, limit: int = 3) -> str:
    if not issues:
        return "OK"
    parts = []
    for level, label, value, unit in issues[:limit]:
        if np.isfinite(value):
            if unit == "%":
                parts.append(f"{label}={value:.2f}%")
            else:
                parts.append(f"{label}={value:+.1f}{unit}")
        else:
            parts.append(label)
    if len(issues) > limit:
        parts.append(f"+{len(issues) - limit} more")
    return ", ".join(parts)
