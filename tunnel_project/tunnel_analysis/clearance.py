"""clearance.py - Train clearance-gauge intrusion analysis (collision detection).

Evaluates whether tunnel structure points intrude into the train's clearance
gauge (the safe movement envelope), and quantifies the intrusion distance.

Approach (pure NumPy/SciPy, headless; Open3D optional and not required):
  1. Build a clearance envelope swept along the tunnel axis. The envelope is a
     circular gauge of radius R (auto-derived from the measured bore, or given)
     centred on the local section centre, in the plane orthogonal to the local
     tangent (Frenet/Bishop frame already computed by GeometricLayer).
  2. Collision detection: for every structure point, take its radial distance r
     to the local axis. Points with r < R lie INSIDE the gauge => intrusion.
     The signed clearance is (r - R): negative means violation, and its
     magnitude is the intrusion depth.
  3. Quantify: per-point intrusion depth (mm), per-section worst intrusion and
     count, chainage of each section, and a severity level.

No external repo is vendored: GitHub has no dedicated train-clearance-gauge
point-cloud project (searched via API), and the tool already provides the
geometric primitives (Frenet frames, signed-distance clearance in
parameters._extract_section_geometry). This module generalises that idea to a
full-cloud, axis-swept collision test with quantitative output.

Severity thresholds (intrusion depth, mm) are configurable; defaults mirror the
caution/critical convention used elsewhere in the tool.
"""
from .common import *
from .models import PipelineContext

# Intrusion-depth severity thresholds in millimetres.
CLEARANCE_CAUTION_MM = 10.0
CLEARANCE_CRITICAL_MM = 50.0


class ClearanceLayer:
    """Train clearance-gauge intrusion (collision) analysis."""

    def evaluate(
        self,
        context: PipelineContext,
        gauge_radius: Optional[float] = None,
        gauge_margin: float = 0.20,
        section_len: float = 0.5,
    ) -> Dict[str, object]:
        """Detect structure points intruding the train clearance envelope.

        Parameters
        ----------
        gauge_radius : float, optional
            Radius (m) of the circular clearance gauge. If None, it is derived
            automatically from the measured bore: the 2nd-percentile radial
            distance minus ``gauge_margin`` (envelope sits just inside the
            innermost lining), matching the GUI's auto-gauge logic.
        gauge_margin : float
            Safety margin (m) subtracted from the inner bore radius when
            auto-deriving the gauge.
        section_len : float
            Axial bin length (m) for per-section aggregation / chainage.

        Returns a dict with per-point and per-section intrusion results.
        """
        pts = context.working_points
        if pts is None:
            raise RuntimeError("clearance.evaluate: no working_points.")
        pts = validate_xyz(pts)
        n = len(pts)

        # --- Tunnel axis + per-point radial distance to it ---
        centroid, axis, _e1, _e2 = principal_axes(pts)
        d = pts - centroid
        proj = d @ axis                                   # axial coordinate
        radial_vec = d - np.outer(proj, axis)
        r = np.linalg.norm(radial_vec, axis=1)            # distance to axis

        # --- Clearance gauge radius (auto or given) ---
        if gauge_radius is None:
            r_inner = float(np.percentile(r, 2))
            gauge_radius = max(0.3, r_inner - gauge_margin)
        gauge_radius = float(gauge_radius)

        # --- Collision detection: points inside the gauge intrude ---
        signed_clear = r - gauge_radius                   # <0 => intrusion (m)
        intruding = signed_clear < 0.0
        intrusion_depth_mm = np.where(intruding, -signed_clear, 0.0) * 1e3

        # --- Per-section aggregation along the axis (chainage) ---
        pmin, pmax = float(proj.min()), float(proj.max())
        ns = max(1, int(np.ceil((pmax - pmin) / section_len)))
        edges = np.linspace(pmin, pmax, ns + 1)
        slot = np.clip(np.searchsorted(edges, proj, side="right") - 1, 0, ns - 1)
        sections: List[Dict[str, float]] = []
        for s in range(ns):
            m = slot == s
            cnt = int(m.sum())
            if cnt == 0:
                continue
            depth_s = intrusion_depth_mm[m]
            n_intr = int(np.count_nonzero(depth_s > 0.0))
            worst = float(depth_s.max()) if cnt else 0.0
            chainage = float(((edges[s] + edges[s + 1]) * 0.5) - pmin)
            sections.append({
                "chainage_m": chainage,
                "n_points": cnt,
                "n_intruding": n_intr,
                "max_intrusion_mm": worst,
                "mean_intrusion_mm": float(depth_s[depth_s > 0].mean()) if n_intr else 0.0,
                "severity": self._severity(worst if n_intr else 0.0),
            })

        n_intruding = int(np.count_nonzero(intruding))
        worst_mm = float(intrusion_depth_mm.max()) if n else 0.0
        return {
            "gauge_radius_m": gauge_radius,
            "axis": axis,
            "centroid": centroid,
            "n_points": n,
            "n_intruding": n_intruding,
            "intrusion_fraction": (n_intruding / n) if n else 0.0,
            "max_intrusion_mm": worst_mm,
            "severity": self._severity(worst_mm),
            "signed_clearance_mm": signed_clear * 1e3,     # per-point (N,)
            "intrusion_depth_mm": intrusion_depth_mm,       # per-point (N,)
            "intruding_mask": intruding,                    # per-point (N,)
            "intruding_points": pts[intruding].copy(),
            "sections": sections,
        }

    @staticmethod
    def _severity(depth_mm: float) -> str:
        if not np.isfinite(depth_mm) or depth_mm <= 0.0:
            return "ok"
        if depth_mm >= CLEARANCE_CRITICAL_MM:
            return "critical"
        if depth_mm >= CLEARANCE_CAUTION_MM:
            return "caution"
        return "minor"
