from .common import *
from .models import PointCloudBundle, PipelineContext
from .io_layer import BaseLayer
from .section_warnings import SECTION_DELTA_CAUTION_MM, SECTION_DELTA_CRITICAL_MM
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

        # ── Incremental (Tn-1 -> Tn) deformation ──────────────────────────
        # matrix rows are cumulative signed displacement vs T0 per corepoint.
        # Prepend a zero T0 row, then diff along epochs to get the per-step
        # incremental displacement (what changed THIS interval, not since T0).
        full = np.vstack([np.zeros((1, matrix.shape[1]), dtype=np.float64), matrix])
        inc_matrix = np.diff(full, axis=0)                  # (T, M) signed, by construction cumsum == matrix
        inc_median_mm = np.array([float(np.nanmedian(r)) for r in inc_matrix])
        inc_p95_abs_mm = np.array([float(np.nanpercentile(np.abs(r), 95)) for r in inc_matrix])
        inc_max_abs_mm = np.array([float(np.nanmax(np.abs(r))) for r in inc_matrix])

        # ── Rate (velocity) & acceleration of the monitored magnitude ──────
        # Track the cumulative p95 magnitude (T0 implied = 0). Velocity is the
        # per-epoch change (mm/epoch); acceleration its change (mm/epoch^2).
        # Accelerating epochs (acc > ~1 mm/epoch^2) are the early-warning signal.
        cum_mag = np.concatenate([[0.0], p95_abs_mm])       # len T+1
        velocity_mm_per_epoch = np.diff(cum_mag)            # len T
        acc_full = np.concatenate([[0.0], velocity_mm_per_epoch])
        acceleration_mm_per_epoch2 = np.diff(acc_full)      # len T
        accelerating = (acceleration_mm_per_epoch2 > 1.0).tolist()
        return {
            "labels": list(labels),
            "corepoints": cp,
            "distance_matrix_mm": matrix,
            "median_mm": median_mm,
            "p95_abs_mm": p95_abs_mm,
            "max_abs_mm": max_abs_mm,
            "incremental_matrix_mm": inc_matrix,
            "incremental_median_mm": inc_median_mm,
            "incremental_p95_abs_mm": inc_p95_abs_mm,
            "incremental_max_abs_mm": inc_max_abs_mm,
            "velocity_mm_per_epoch": velocity_mm_per_epoch,
            "acceleration_mm_per_epoch2": acceleration_mm_per_epoch2,
            "accelerating": accelerating,
            "method": method,
        }


    @staticmethod
    def _crown_zone_value(
        points: np.ndarray,
        chainage_m: float,
        chainage_window_m: float = 5.0,
        lateral_window_m: float = 12.0,
        crown_percentile: float = 98.0,
        curve_radius_m: Optional[float] = 420.0,
    ) -> Tuple[float, int]:
        """Robust local crown value for settlement checks.

        This is intentionally a local crown metric, not a whole-cloud metric:
        it measures the upper tunnel band around one chainage and is suitable
        for comparing against crown settlement ground truth.
        """
        pts = validate_xyz(points)
        if pts.shape[0] == 0:
            return float("nan"), 0
        x = pts[:, 0]
        y = pts[:, 1]
        z = pts[:, 2]
        if curve_radius_m and curve_radius_m > 0:
            radius = float(curve_radius_m)
            angle = np.arctan2(y, radius - x)
            chainage = radius * angle
            cx = radius * (1.0 - np.cos(angle))
            cy = radius * np.sin(angle)
            lateral = (x - cx) * np.cos(angle) + (y - cy) * (-np.sin(angle))
        else:
            # Stable axis-aligned chainage (longest horizontal span). Avoids
            # independent PCA frames per epoch that can shift the probe location.
            span_x = float(np.nanmax(x) - np.nanmin(x))
            span_y = float(np.nanmax(y) - np.nanmin(y))
            if span_y >= span_x:
                chainage = y - float(np.nanmin(y))
                lateral = x - float(np.nanmedian(x))
            else:
                chainage = x - float(np.nanmin(x))
                lateral = y - float(np.nanmedian(y))
        mask = ((np.abs(chainage - float(chainage_m)) <= float(chainage_window_m)) &
                (np.abs(lateral) <= float(lateral_window_m)))
        zone_pts = pts[mask]
        if zone_pts.shape[0] < 20:
            return float("nan"), int(zone_pts.shape[0])
        # Keep the upper lining of this slice so sidewall / invert noise does not
        # dominate the crown percentile.
        z_thr = float(np.nanpercentile(zone_pts[:, 2], 75.0))
        upper = zone_pts[zone_pts[:, 2] >= z_thr]
        if upper.shape[0] < 20:
            upper = zone_pts
        zone = upper[:, 2]
        return float(np.nanpercentile(zone, float(crown_percentile))), int(zone.size)


    def suggest_crown_chainage(
        self,
        epochs: List[np.ndarray],
        chainage_window_m: float = 5.0,
        lateral_window_m: float = 12.0,
        crown_percentile: float = 98.0,
        curve_radius_m: Optional[float] = None,
        step_m: float = 5.0,
        preferred_chainage_m: Optional[float] = None,
    ) -> Dict[str, object]:
        """Pick a crown probe chainage from data (or an optional preferred value).

        Preference order:
        1. ``preferred_chainage_m`` when finite
        2. chainage with largest |T0->Tn crown settlement| on a coarse scan
        3. mid-tunnel fallback
        """
        if len(epochs) < 2:
            raise RuntimeError("Need at least two epochs (T0 and one monitoring epoch).")

        if preferred_chainage_m is not None and np.isfinite(float(preferred_chainage_m)):
            ch = float(preferred_chainage_m)
            return {
                "chainage_m": ch,
                "source": "preferred",
                "settlement_mm": float("nan"),
                "curve_radius_m": None if curve_radius_m is None else float(curve_radius_m),
            }

        t0 = validate_xyz(epochs[0])
        tn = validate_xyz(epochs[-1])
        # Estimate usable chainage range from T0 with the same mapping as crown probe.
        if curve_radius_m and curve_radius_m > 0:
            radius = float(curve_radius_m)
            angle = np.arctan2(t0[:, 1], radius - t0[:, 0])
            chainage = radius * angle
        else:
            span_x = float(np.nanmax(t0[:, 0]) - np.nanmin(t0[:, 0]))
            span_y = float(np.nanmax(t0[:, 1]) - np.nanmin(t0[:, 1]))
            if span_y >= span_x:
                chainage = t0[:, 1] - float(np.nanmin(t0[:, 1]))
            else:
                chainage = t0[:, 0] - float(np.nanmin(t0[:, 0]))
        cmin = float(np.nanpercentile(chainage, 5))
        cmax = float(np.nanpercentile(chainage, 95))
        if not np.isfinite(cmin) or not np.isfinite(cmax) or cmax - cmin < 1.0:
            mid = 0.5 * (cmin + cmax) if np.isfinite(cmin) and np.isfinite(cmax) else 0.0
            return {
                "chainage_m": float(mid),
                "source": "midpoint-fallback",
                "settlement_mm": float("nan"),
                "curve_radius_m": None if curve_radius_m is None else float(curve_radius_m),
            }

        step = max(float(step_m), 1.0)
        candidates = np.arange(cmin + step, cmax - step + 1e-9, step, dtype=np.float64)
        if candidates.size == 0:
            candidates = np.asarray([0.5 * (cmin + cmax)], dtype=np.float64)

        best_ch = float(candidates[len(candidates) // 2])
        best_sett = float("nan")
        best_abs = -1.0
        for ch in candidates:
            z0, n0 = self._crown_zone_value(
                t0, chainage_m=float(ch), chainage_window_m=chainage_window_m,
                lateral_window_m=lateral_window_m, crown_percentile=crown_percentile,
                curve_radius_m=curve_radius_m,
            )
            zn, nn = self._crown_zone_value(
                tn, chainage_m=float(ch), chainage_window_m=chainage_window_m,
                lateral_window_m=lateral_window_m, crown_percentile=crown_percentile,
                curve_radius_m=curve_radius_m,
            )
            if n0 < 20 or nn < 20 or not np.isfinite(z0) or not np.isfinite(zn):
                continue
            sett = (zn - z0) * 1000.0
            if abs(sett) > best_abs:
                best_abs = abs(sett)
                best_sett = float(sett)
                best_ch = float(ch)

        source = "auto-peak" if best_abs >= 0.0 and np.isfinite(best_sett) else "midpoint-fallback"
        if source == "midpoint-fallback":
            best_ch = float(0.5 * (cmin + cmax))
        return {
            "chainage_m": best_ch,
            "source": source,
            "settlement_mm": best_sett,
            "curve_radius_m": None if curve_radius_m is None else float(curve_radius_m),
            "search_min_m": cmin,
            "search_max_m": cmax,
        }

    def crown_settlement_series(
        self,
        epochs: List[np.ndarray],
        labels: Optional[List[str]] = None,
        chainage_m: float = 52.0,
        chainage_window_m: float = 5.0,
        lateral_window_m: float = 12.0,
        crown_percentile: float = 98.0,
        curve_radius_m: Optional[float] = 420.0,
    ) -> Dict[str, object]:
        """Measure crown settlement at one chainage for T0..Tn.

        Returns signed settlement in millimetres relative to T0. Negative means
        the crown moved downward. Use this when ground truth is crown settlement;
        keep ``spatiotemporal_series`` for whole-cloud M3C2/p95 trend checks.
        """
        if len(epochs) < 2:
            raise RuntimeError("Need at least two epochs (T0 and one monitoring epoch).")
        if labels is None:
            labels = [f"T{i}" for i in range(len(epochs))]
        values = []
        counts = []
        for epoch in epochs:
            value, count = self._crown_zone_value(
                epoch,
                chainage_m=chainage_m,
                chainage_window_m=chainage_window_m,
                lateral_window_m=lateral_window_m,
                crown_percentile=crown_percentile,
                curve_radius_m=curve_radius_m,
            )
            values.append(value)
            counts.append(count)
        crown_z = np.asarray(values, dtype=np.float64)
        settlement = (crown_z - crown_z[0]) * 1000.0
        return {
            "labels": list(labels),
            "crown_z_m": crown_z,
            "crown_settlement_mm": settlement,
            "zone_points": np.asarray(counts, dtype=np.int64),
            "chainage_m": float(chainage_m),
            "chainage_window_m": float(chainage_window_m),
            "lateral_window_m": float(lateral_window_m),
            "crown_percentile": float(crown_percentile),
            "curve_radius_m": None if curve_radius_m is None else float(curve_radius_m),
            "metric": "crown_settlement_mm",
        }

    @staticmethod
    def compare_to_ground_truth(
        series: Dict[str, object], gt_csv_path: str, metric: str = "max_abs_mm",
    ) -> Dict[str, object]:
        """Validate measured per-epoch deformation against a ground-truth CSV.

        ``ground_truth.csv`` has columns ``epoch, chainage_m, deformation_type,
        value_mm, ...``. For each epoch we take the GT peak ``|value_mm|`` over
        all features and compare it to the tool's measured per-epoch magnitude
        (``metric``, default ``max_abs_mm`` from :meth:`spatiotemporal_series`),
        matched by epoch label. Returns per-epoch errors plus MAE and max
        absolute error (mm) — a quantitative accuracy figure for the report.
        """
        import csv
        gt_by_epoch: Dict[str, float] = {}
        for row in csv.DictReader(open(gt_csv_path, newline="")):
            ep = (row.get("epoch") or "").strip()
            try:
                v = abs(float(row["value_mm"]))
            except (KeyError, ValueError, TypeError):
                continue
            gt_by_epoch[ep] = max(gt_by_epoch.get(ep, 0.0), v)

        labels = list(series.get("labels", []))
        measured = np.asarray(series.get(metric, []), dtype=np.float64).ravel()
        per_epoch: List[Dict[str, float]] = []
        errs: List[float] = []
        for i, lbl in enumerate(labels):
            if lbl not in gt_by_epoch or i >= measured.size:
                continue
            gt = float(gt_by_epoch[lbl]); meas = float(measured[i])
            per_epoch.append({"epoch": lbl, "gt_peak_mm": gt,
                              "measured_mm": meas, "error_mm": meas - gt})
            errs.append(abs(meas - gt))
        mae = float(np.mean(errs)) if errs else float("nan")
        maxe = float(np.max(errs)) if errs else float("nan")
        summary = (f"Ground-truth validation ({metric}): {len(per_epoch)} epochs, "
                   f"MAE={mae:.1f} mm, max error={maxe:.1f} mm"
                   if errs else "Ground-truth validation: no matching epochs")
        return {"metric": metric, "per_epoch": per_epoch, "mae_mm": mae,
                "max_abs_error_mm": maxe, "n": len(per_epoch), "summary": summary}

    def forecast_threshold_crossing(
        self,
        series: Dict[str, object],
        times: Optional[List[float]] = None,
        caution_mm: float = SECTION_DELTA_CAUTION_MM,
        critical_mm: float = SECTION_DELTA_CRITICAL_MM,
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

        # Fitted-curve samples from the latest epoch out to the crossing horizon,
        # for the chart overlay. Aliases (*_crossing_epoch / forecast_*) match
        # what MultiEpochTimeSeriesWidget reads.
        horizon = next((c for c in (t_critical, t_caution) if c is not None),
                       t_last + max(3.0, float(n)))
        horizon = max(float(horizon), t_last + 1.0)
        fc_t = np.linspace(t_last, horizon, 20)
        fc_v = fit(fc_t)
        result.update({
            "ok": True,
            "rate_per_unit": rate,
            "r_squared": r2,
            "t_caution": t_caution, "t_critical": t_critical,
            "dt_caution": dt_caution, "dt_critical": dt_critical,
            "low_confidence": bool(r2 < 0.5),
            "caution_crossing_epoch": t_caution,
            "critical_crossing_epoch": t_critical,
            "forecast_epochs": fc_t.tolist(),
            "forecast_values": fc_v.tolist(),
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


