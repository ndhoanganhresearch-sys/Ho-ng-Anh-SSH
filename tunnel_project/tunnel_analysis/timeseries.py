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
        pts = context.working_points
        if pts is None: raise RuntimeError("Load epochs first.")
        pts = validate_xyz(pts)
        sc  = (pts[:,2] - np.median(pts[:,2]))*1e3
        ord_= np.argsort(pts[:,0])
        return np.array([float(np.nanmean(c)) for c in np.array_split(sc[ord_],120) if len(c)>0])

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
            return {
                "corepoints": cp,
                "distance_mm": dist_mm,
                "lod_mm": lod_mm,
                "significant": significant,
                "method": "M3C2",
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
        return {
            "labels": list(labels),
            "corepoints": cp,
            "distance_matrix_mm": matrix,
            "median_mm": median_mm,
            "p95_abs_mm": p95_abs_mm,
            "method": method,
        }


