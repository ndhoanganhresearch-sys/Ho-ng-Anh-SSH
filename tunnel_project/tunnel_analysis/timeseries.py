from .common import *
from .models import PointCloudBundle, PipelineContext
from .io_layer import BaseLayer
# ------------------------------------------------------------------------------
# TimeSeriesLayer
# ------------------------------------------------------------------------------

class TimeSeriesLayer:
    def load_epochs(self, p0: str, pn: str) -> Tuple[PointCloudBundle, PointCloudBundle]:
        bl = BaseLayer(); return bl.load_scan(p0), bl.load_scan(pn)

    def plot_deformation(self, context: PipelineContext) -> np.ndarray:
        """Crown-height trend (mm) sampled along the tunnel chainage.

        When Frenet frames exist, sample the crown (max projection on the
        vertical B axis) in each section so the trend follows the real tunnel
        axis and stays valid for curved/non-axis-aligned tunnels. Falls back to
        a PCA-axis binning of global Z only when no centerline is available
        (the old version binned by the raw X coordinate, which is meaningless
        unless the tunnel happens to run along X).
        """
        pts = context.working_points
        if pts is None: raise RuntimeError("Load epochs first.")
        pts = validate_xyz(pts)
        frames = context.frenet_frames
        if frames:
            from .parameters import ParameterExtractionLayer
            eps = ParameterExtractionLayer._section_epsilon(context)
            crowns = []
            for fr in frames:
                C, T, B = fr["center"], fr["T"], fr["B"]
                sl = pts[np.abs((pts - C) @ T) < eps]
                if len(sl) < 5:
                    crowns.append(np.nan); continue
                crowns.append(float(((sl - C) @ B).max()) * 1e3)
            arr = np.array(crowns, dtype=np.float64)
            if np.isfinite(arr).any():
                return arr
        # Fallback: project Z trend along the PCA dominant axis.
        c, axis, _e1, _e2 = principal_axes(pts)
        proj = (pts - c) @ axis
        sc = (pts[:, 2] - np.median(pts[:, 2])) * 1e3
        order = np.argsort(proj)
        return np.array([float(np.nanmean(c2)) for c2 in np.array_split(sc[order], 120) if len(c2) > 0])

    def m3c2_distances(
        self,
        epoch0: np.ndarray,
        epoch1: np.ndarray,
        corepoints: Optional[np.ndarray] = None,
        cyl_radius: float = 0.5,
        normal_radius: float = 0.5,
        max_corepoints: int = 50_000,
    ) -> Dict[str, np.ndarray]:
        """Compute M3C2 surface displacement between two epochs (T0 vs Tn).

        Uses py4dgeo's M3C2 algorithm (signed distance along local surface
        normals + level-of-detection). Falls back to a cloud-to-cloud
        nearest-neighbour distance when py4dgeo is unavailable.

        Returns a dict with:
        - ``corepoints``: (M, 3) points where distances are evaluated
        - ``distance_mm``: (M,) signed displacement in millimetres
        - ``lod_mm``: (M,) level of detection in millimetres (NaN in fallback)
        - ``significant``: (M,) bool mask where |distance| exceeds LoD
        - ``method``: "M3C2" or "C2C-fallback"
        """
        src = validate_xyz(epoch0)
        tgt = validate_xyz(epoch1)

        if corepoints is None:
            cp = src
        else:
            cp = validate_xyz(corepoints)
        if max_corepoints and cp.shape[0] > max_corepoints:
            step = int(np.ceil(cp.shape[0] / max_corepoints))
            cp = cp[::step]

        if py4dgeo is not None and src.shape[0] >= 10 and tgt.shape[0] >= 10:
            ep0 = py4dgeo.Epoch(np.ascontiguousarray(src, dtype=np.float64))
            ep1 = py4dgeo.Epoch(np.ascontiguousarray(tgt, dtype=np.float64))
            algo = py4dgeo.M3C2(
                epochs=(ep0, ep1),
                corepoints=np.ascontiguousarray(cp, dtype=np.float64),
                cyl_radius=float(cyl_radius),
                normal_radii=(float(normal_radius),),
            )
            dist, unc = algo.run()
            dist_mm = np.asarray(dist, dtype=np.float64) * 1e3
            lod_mm = np.asarray(unc["lodetection"], dtype=np.float64) * 1e3
            significant = np.abs(dist_mm) > lod_mm

            # Data-quality guard: a partial re-scan (e.g. Tn covers only the
            # entrance) leaves most corepoints with no Tn neighbour inside
            # cyl_radius, so M3C2 returns NaN there. The downstream nanmedian /
            # nanpercentile would still report plausible-looking numbers from
            # the few valid points, silently masking the degraded coverage.
            quality_warning = None
            n_total = dist_mm.size
            nan_frac = float(np.isnan(dist_mm).mean()) if n_total else 1.0
            ratio = max(src.shape[0], tgt.shape[0]) / max(1, min(src.shape[0], tgt.shape[0]))
            if nan_frac > 0.5:
                quality_warning = (f"M3C2: {nan_frac*100:.0f}% of corepoints have no Tn "
                                   f"neighbour within {cyl_radius} m - coverage likely partial.")
            elif ratio >= 10.0:
                quality_warning = (f"M3C2: epoch point counts differ {ratio:.0f}x "
                                   f"(T0={src.shape[0]:,}, Tn={tgt.shape[0]:,}) - "
                                   f"results may be unreliable.")
            if quality_warning:
                warnings.warn(quality_warning)
            return {
                "corepoints": cp,
                "distance_mm": dist_mm,
                "lod_mm": lod_mm,
                "significant": significant,
                "method": "M3C2",
                "quality_warning": quality_warning,
            }

        return self._c2c_fallback(cp, tgt)

    def _c2c_fallback(self, corepoints: np.ndarray, tgt: np.ndarray) -> Dict[str, np.ndarray]:
        """Signed cloud-to-cloud distance (Z component) when py4dgeo is absent."""
        if cKDTree is None:
            raise RuntimeError("Neither py4dgeo nor scipy.cKDTree is available.")
        _, idx = cKDTree(tgt).query(corepoints, k=1, workers=-1)
        dist_mm = (tgt[idx, 2] - corepoints[:, 2]) * 1e3
        nan = np.full(corepoints.shape[0], np.nan)
        return {
            "corepoints": corepoints,
            "distance_mm": dist_mm,
            "lod_mm": nan,
            "significant": np.zeros(corepoints.shape[0], dtype=bool),
            "method": "C2C-fallback",
        }

    def spatiotemporal_series(
        self,
        epochs: List[np.ndarray],
        labels: Optional[List[str]] = None,
        cyl_radius: float = 0.5,
        normal_radius: float = 0.5,
        max_corepoints: int = 50_000,
    ) -> Dict[str, object]:
        """Multi-epoch deformation trend relative to the first epoch (T0).

        Computes M3C2 displacement of every later epoch against the T0
        reference at a fixed set of corepoints, producing a settlement/
        convergence trend over time (e.g. monthly campaigns).

        Returns a dict with:
        - ``labels``: list of epoch labels (excludes T0)
        - ``corepoints``: (M, 3) reference corepoints from T0
        - ``distance_matrix_mm``: (T, M) signed displacement per epoch
        - ``median_mm``: (T,) median displacement per epoch
        - ``p95_abs_mm``: (T,) 95th-percentile absolute displacement per epoch
        - ``max_abs_mm``: (T,) peak absolute displacement per epoch (worst
          corepoint) — tracks LOCAL defects that a tunnel-wide percentile
          dilutes; used by :meth:`forecast_threshold_crossing`
        - ``method``: "M3C2" or "C2C-fallback"
        """
        if len(epochs) < 2:
            raise RuntimeError("Need at least two epochs (T0 and one monitoring epoch).")

        ref = validate_xyz(epochs[0])
        cp = ref
        if max_corepoints and cp.shape[0] > max_corepoints:
            step = int(np.ceil(cp.shape[0] / max_corepoints))
            cp = cp[::step]

        if labels is None:
            labels = [f"T{i}" for i in range(1, len(epochs))]

        rows: List[np.ndarray] = []
        method = "M3C2" if py4dgeo is not None else "C2C-fallback"
        for epoch in epochs[1:]:
            out = self.m3c2_distances(
                ref, epoch, corepoints=cp,
                cyl_radius=cyl_radius, normal_radius=normal_radius,
                max_corepoints=0,
            )
            rows.append(np.asarray(out["distance_mm"], dtype=np.float64))
            method = out["method"]

        matrix = np.vstack(rows)
        median_mm = np.array([float(np.nanmedian(r)) for r in matrix])
        p95_abs_mm = np.array([float(np.nanpercentile(np.abs(r), 95)) for r in matrix])
        max_abs_mm = np.array([float(np.nanmax(np.abs(r))) for r in matrix])
        return {
            "labels": list(labels),
            "corepoints": cp,
            "distance_matrix_mm": matrix,
            "median_mm": median_mm,
            "p95_abs_mm": p95_abs_mm,
            "max_abs_mm": max_abs_mm,
            "method": method,
        }

    def forecast_threshold_crossing(
        self,
        series: Dict[str, object],
        times: Optional[List[float]] = None,
        caution_mm: float = 10.0,
        critical_mm: float = 25.0,
        degree: int = 1,
        min_epochs: int = 3,
        metric: str = "p95_abs_mm",
    ) -> Dict[str, object]:
        """Extrapolate a multi-epoch deformation trend to predict when it will
        cross the CAUTION / CRITICAL safety thresholds (predictive maintenance,
        PDF Phase 4).

        Takes the output of :meth:`spatiotemporal_series` and fits a low-order
        polynomial (``degree`` 1 = constant rate, 2 = with acceleration) to the
        chosen per-epoch magnitude series over ``times``, then solves for the
        first FUTURE time the fitted curve reaches each threshold.

        ``times`` are the epoch times (e.g. months since T0) for T1..Tn and must
        match ``series['labels']``; defaults to 1, 2, 3, ... (unit spacing, T0
        implied at 0). Returns the fitted instantaneous ``rate_per_unit`` at the
        latest epoch, the fit ``r_squared``, the predicted crossing times
        (``None`` when the trend never reaches a threshold, e.g. flat/recovering)
        and a human-readable ``summary``. ``low_confidence`` flags an R^2 below
        0.5, where extrapolation should not be trusted.
        """
        values = np.asarray(series.get(metric, []), dtype=np.float64).ravel()
        n = int(values.size)
        result: Dict[str, object] = {
            "ok": False, "metric": metric, "degree": int(degree),
            "rate_per_unit": None, "r_squared": None,
            "t_caution": None, "t_critical": None,
            "dt_caution": None, "dt_critical": None,
            "caution_mm": float(caution_mm), "critical_mm": float(critical_mm),
            "low_confidence": False, "reason": "", "summary": "",
        }
        if n < min_epochs:
            result["reason"] = f"need >= {min_epochs} epochs, got {n}"
            result["summary"] = (
                f"Chua du du lieu de du bao (can >= {min_epochs} epoch, co {n}).")
            return result
        if times is None:
            t = np.arange(1, n + 1, dtype=np.float64)
        else:
            t = np.asarray(times, dtype=np.float64).ravel()
            if t.size != n:
                result["reason"] = f"times length {t.size} != series length {n}"
                return result
        finite = np.isfinite(values) & np.isfinite(t)
        if int(finite.sum()) < min_epochs:
            result["reason"] = "too many non-finite samples"
            return result
        t = t[finite]; values = values[finite]

        deg = int(max(1, min(degree, t.size - 1)))
        coeffs = np.polyfit(t, values, deg)
        fit = np.poly1d(coeffs)
        pred = fit(t)
        ss_res = float(np.sum((values - pred) ** 2))
        ss_tot = float(np.sum((values - values.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 1.0
        rate = float(np.polyder(fit)(t[-1]))     # instantaneous rate at latest epoch
        t_last = float(t[-1]); v_last = float(values[-1])

        def _first_future_crossing(thr: float) -> Optional[float]:
            if v_last >= thr:
                return t_last                      # already at/over the threshold
            c = coeffs.copy(); c[-1] -= thr        # solve fit(t) - thr = 0
            roots = np.roots(c) if c.size > 1 else np.array([])
            future = [float(r.real) for r in np.atleast_1d(roots)
                      if abs(getattr(r, "imag", 0.0)) < 1e-6 and r.real > t_last + 1e-9]
            return min(future) if future else None

        t_caution = _first_future_crossing(float(caution_mm))
        t_critical = _first_future_crossing(float(critical_mm))
        dt_caution = (t_caution - t_last) if t_caution is not None else None
        dt_critical = (t_critical - t_last) if t_critical is not None else None

        result.update({
            "ok": True,
            "rate_per_unit": rate,
            "r_squared": r2,
            "t_caution": t_caution, "t_critical": t_critical,
            "dt_caution": dt_caution, "dt_critical": dt_critical,
            "low_confidence": bool(r2 < 0.5),
        })

        def _phrase(label, thr, v_now, dt):
            if v_now >= thr:
                return f"Da vuot {label} ({thr:g}mm). "
            if dt is None:
                return f"Khong du bao dat {label} ({thr:g}mm) (xu huong on dinh/giam). "
            return f"Du bao dat {label} ({thr:g}mm) sau ~{dt:.1f} don vi thoi gian. "

        summary = f"Toc do {metric}: {rate:+.2f} mm/don-vi (R^2={r2:.2f}). "
        summary += _phrase("CAUTION", caution_mm, v_last, dt_caution)
        summary += _phrase("CRITICAL", critical_mm, v_last, dt_critical)
        if r2 < 0.5:
            summary += "(Do tin cay thap - xu huong khong tuyen tinh, can them epoch.) "
        result["summary"] = summary
        return result


