from .common import *
from .models import PipelineContext
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

class PreprocessingLayer:
    def range_crop(
        self, context: PipelineContext, max_range_m: float = 20.0,
        mode: str = "sensor",
    ) -> Tuple[np.ndarray, Dict]:
        """Drop points farther than max_range_m, MATLAB-GUI style (PDF 3.2).

        Scanner range falls off with distance, so far points are sparse and
        noisy. The reference MATLAB tool crops with
        ``distances = sqrt(sum(xyz.^2,2)); idx = distances <= 20`` before any
        statistical denoise. This mirrors that as a cheap first pass.

        mode:
          - "sensor": Euclidean distance from the scan origin (0,0,0), matching
            the MATLAB crop (raw scans are in the scanner frame).
          - "centroid": distance from the cloud centroid (for already-centred
            clouds where the sensor origin is not meaningful).
          - "axis": radial distance from the PCA dominant axis (keeps a tube
            of radius max_range_m around the tunnel axis).
        Returns (kept_xyz, stats). Operates on working_points so it composes
        with voxel/SOR.
        """
        pts = context.working_points
        if pts is None:
            raise RuntimeError("range_crop: no working_points.")
        pts = validate_xyz(pts)
        n_raw = len(pts)
        if not (max_range_m and max_range_m > 0):
            return pts, {"n_raw": n_raw, "n_clean": n_raw, "n_removed": 0,
                         "mode": mode, "max_range_m": float(max_range_m)}
        if mode == "centroid":
            d = np.linalg.norm(pts - pts.mean(axis=0), axis=1)
        elif mode == "axis":
            c, axis, _e1, _e2 = principal_axes(pts)
            diff = pts - c
            d = np.linalg.norm(diff - (diff @ axis)[:, None] * axis, axis=1)
        else:  # sensor
            d = np.linalg.norm(pts, axis=1)
        keep = d <= float(max_range_m)
        kept = validate_xyz(pts[keep], "range_crop")
        # working_points is a computed property (registered > normalized > raw).
        # Update whichever backing field it currently draws from so downstream
        # steps always see the cropped cloud regardless of pipeline order.
        if context.registered_points is not None:
            context.registered_points = kept
        else:
            context.normalized_points = kept
        return kept, {
            "n_raw": n_raw,
            "n_clean": int(keep.sum()),
            "n_removed": int(n_raw - int(keep.sum())),
            "mode": mode,
            "max_range_m": float(max_range_m),
            "max_distance_seen": float(d.max()),
        }

    def voxel_downsample(
        self, context: PipelineContext, voxel_size: float = 0.05
    ) -> Tuple[np.ndarray, np.ndarray]:
        scan = context.active_scan
        if scan is None: raise RuntimeError("voxel_downsample: no active scan.")
        pts = validate_xyz(scan.points)
        if o3d is not None:
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(pts)
            dn = np.asarray(pcd.voxel_down_sample(float(voxel_size)).points, dtype=np.float64)
        else:
            dn = self._np_voxel(pts, voxel_size)
        dn = validate_xyz(dn, "voxel")
        c  = dn.mean(0)
        return dn - c, c


    def semantic_noise_removal(
        self,
        context: "PipelineContext",
        k_neighbors: int = 20,
        cable_linearity_thr: float = 0.30,
        light_sphericity_thr: float = 0.12,
        light_size_thr: float = 0.20,
        person_height_thr: float = 1.2,
        person_width_thr: float = 0.8,
    ) -> Tuple[np.ndarray, Dict]:
        """Semantic noise removal per PDF §3.2.
        Classify and remove non-structural objects:
          - Cables/pipes: high linearity (long, thin clusters)
          - Lights/fixtures: high sphericity (isolated small clusters)
          - People: human-shaped clusters (~1.7m height, <0.8m width)
        Uses local geometric features (PCA eigenvalues) per point neighborhood.
        Returns cleaned points + classification stats.
        """
        pts = context.working_points
        if pts is None: raise RuntimeError("No working_points.")
        pts = validate_xyz(pts)
        if cKDTree is None:
            warnings.warn("scipy required for semantic removal")
            return pts, {"n_raw": len(pts), "n_clean": len(pts)}

        n = len(pts)
        k = min(k_neighbors, n - 1)
        tree = cKDTree(pts)
        _, idx = tree.query(pts, k=k+1, workers=-1)
        neighbors = pts[idx[:, 1:]]  # (N, k, 3)

        # Compute local PCA features per point
        linearity   = np.zeros(n, dtype=np.float64)
        planarity   = np.zeros(n, dtype=np.float64)
        sphericity  = np.zeros(n, dtype=np.float64)
        local_size  = np.zeros(n, dtype=np.float64)

        for i in range(n):
            nb = neighbors[i]
            cov = np.cov(nb.T)
            try:
                ev = np.sort(np.linalg.eigvalsh(cov))[::-1]  # descending
                ev = np.clip(ev, 0, None)
                total = ev.sum() + 1e-9
                linearity[i]  = (ev[0] - ev[1]) / total
                planarity[i]  = (ev[1] - ev[2]) / total
                sphericity[i] = ev[2] / total
                local_size[i] = float(np.sqrt(ev[0]))
            except Exception:
                pass

        # Classify noise
        is_cable  = linearity >= cable_linearity_thr
        is_light  = (sphericity >= light_sphericity_thr) & (local_size <= light_size_thr)

        # People detection: cluster high-planarity points, check height/width
        is_person = np.zeros(n, dtype=bool)
        person_mask = planarity > 0.4
        if person_mask.sum() > 10:
            person_pts = pts[person_mask]
            from sklearn.cluster import DBSCAN
            db = DBSCAN(eps=0.15, min_samples=5).fit(person_pts)
            labels = db.labels_
            for c in set(labels) - {-1}:
                mask_c = labels == c
                cp = person_pts[mask_c]
                height = float(cp[:, 2].max() - cp[:, 2].min())
                width  = float(np.ptp(cp[:, :2], axis=0).max())
                if person_height_thr <= height <= 2.2 and width <= person_width_thr:
                    # Mark original points near this cluster as person
                    center = cp.mean(axis=0)
                    dists  = np.linalg.norm(pts - center, axis=1)
                    is_person[dists < 0.5] = True

        noise_mask = is_cable | is_light | is_person
        clean_pts  = validate_xyz(pts[~noise_mask])

        stats = {
            "n_raw":     n,
            "n_clean":   int((~noise_mask).sum()),
            "n_removed": int(noise_mask.sum()),
            "n_cable":   int(is_cable.sum()),
            "n_light":   int(is_light.sum()),
            "n_person":  int(is_person.sum()),
            "noise_pts": pts[noise_mask].copy(),
        }
        return clean_pts, stats


    @staticmethod
    def _np_voxel(pts: np.ndarray, vs: float) -> np.ndarray:
        pm = pts.min(0)
        cell = np.floor((pts - pm) / vs).astype(np.int64)
        dims = cell.max(0) + 1
        keys = cell[:, 0] + cell[:, 1] * int(dims[0]) + cell[:, 2] * int(dims[0]) * int(dims[1])
        order = np.argsort(keys, kind="stable")
        ks = keys[order]; ps = pts[order]
        _, first, counts = np.unique(ks, return_index=True, return_counts=True)
        cum = np.vstack([np.zeros((1, 3)), np.cumsum(ps, axis=0)])
        order_ends = first + counts
        return ((cum[order_ends] - cum[first]) / counts[:, None]).astype(np.float64)

    def statistical_outlier_removal_run(
        self, context: PipelineContext, k_sigma: float = 2.5, section_len: float = 0.5
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Improved SOR per PDF 3.2:
        1. Partition tunnel into sections along dominant axis
        2. Per section: compute radial distance from axis
        3. Use ROBUST median + MAD (not mean+std) to handle bimodal distribution
        4. Remove points outside [R_med - k*MAD, R_med + k*MAD]
        5. Also remove points with R < R_med * 0.4 (interior objects)
        """
        scan = context.active_scan
        if scan is None: raise RuntimeError("SOR: no active scan.")
        src = context.working_points
        if src is None: src = scan.points
        pts = validate_xyz(src); N = len(pts)
        # Colors only valid if they line up 1:1 with the working points
        colors = scan.colors_raw
        if colors is not None and np.asarray(colors).shape[0] != N:
            colors = None

        # Dominant axis
        centroid, long_ax, _e1, _e2 = principal_axes(pts)
        centred = pts - centroid
        proj = centred @ long_ax
        pmin, pmax = float(proj.min()), float(proj.max())
        ns = max(1, int(np.ceil((pmax - pmin) / section_len)))

        inlier = np.zeros(N, dtype=bool)
        for s in range(ns):
            lo = pmin + s * section_len
            hi = pmin + (s + 1) * section_len
            if s == ns - 1: hi = pmax + 1e-9
            mask = (proj >= lo) & (proj < hi)
            idx = np.where(mask)[0]
            if len(idx) < 6:
                inlier[idx] = True; continue

            sp = pts[idx]
            ao = centroid + float(proj[idx].mean()) * long_ax
            diff = sp - ao
            ax_c = (diff @ long_ax)[:, None] * long_ax
            ri = np.linalg.norm(diff - ax_c, axis=1)

            # Robust: use median + MAD
            R_med = float(np.median(ri))
            if R_med < 1e-4:
                inlier[idx] = True; continue
            mad = float(np.median(np.abs(ri - R_med))) + 1e-9
            # 1.4826 converts MAD to sigma-equivalent
            thr = k_sigma * 1.4826 * mad

            # Keep: within band AND not interior object (R > R_med * 0.4)
            band = (np.abs(ri - R_med) <= thr) & (ri >= R_med * 0.40)
            inlier[idx[band]] = True

        cleaned = validate_xyz(pts[inlier])
        cout: Optional[np.ndarray] = None
        if colors is not None:
            raw = np.asarray(colors, dtype=np.float64)
            if raw.shape[0] == N: cout = _normalize_rgb(raw[inlier])
        n_removed = N - int(inlier.sum())
        return cleaned, cout, {
            "n_raw": N, "n_clean": int(inlier.sum()),
            "n_removed": n_removed,
            "outlier_pts": pts[~inlier].copy()
        }

    def extract_tunnel_lining(self, context: PipelineContext) -> np.ndarray:
        """Extract tunnel lining surface per PDF 3.2.

        Multi-pass strategy:
        Pass 1 - Axis estimation: PCA dominant axis
        Pass 2 - Coarse radius band: keep [R_med*0.5, R_med*1.5] per section
        Pass 3 - Fine statistical filter: keep within mu +/- 2.5*sigma of radial deviation
        Pass 4 - Intensity-based filter: if intensity available, remove low-intensity
                 interior objects (cables/lights have different reflectance)
        """
        pts = context.working_points
        if pts is None: raise RuntimeError("No working_points.")
        pts = validate_xyz(pts)
        # T2: intensity is re-aligned to the current points even after
        # voxel/SOR/lining changed the count (nearest-neighbour to raw scan).
        intensity = context.working_intensity()
        if intensity is not None:
            intensity = np.asarray(intensity, dtype=np.float64).ravel()
            if len(intensity) != len(pts):
                intensity = None

        # Pass 1: dominant axis
        c, ax, _e1, _e2 = principal_axes(pts)
        proj = (pts - c) @ ax
        pmin, pmax = float(proj.min()), float(proj.max())
        section_len = max(0.3, (pmax - pmin) / 60.0)
        ns = max(1, int(np.ceil((pmax - pmin) / section_len)))

        keep = np.zeros(len(pts), dtype=bool)
        for s in range(ns):
            lo = pmin + s * section_len
            hi = pmin + (s + 1) * section_len
            if s == ns - 1: hi = pmax + 1e-9
            mask = (proj >= lo) & (proj < hi)
            idx = np.where(mask)[0]
            if len(idx) < 6:
                keep[idx] = True; continue

            sp = pts[idx]
            ao = c + float(proj[idx].mean()) * ax
            diff = sp - ao
            ax_c = (diff @ ax)[:, None] * ax
            ri = np.linalg.norm(diff - ax_c, axis=1)
            R_med = float(np.median(ri))
            R_std = float(np.std(ri)) + 1e-6

            # Pass 2: coarse band
            coarse = (ri >= R_med * 0.50) & (ri <= R_med * 1.50)
            if coarse.sum() < 6:
                keep[idx] = True; continue

            # Pass 3: fine statistical filter on coarse subset
            ri_c = ri[coarse]
            mu_c = float(np.mean(ri_c)); si_c = float(np.std(ri_c)) + 1e-6
            fine = coarse & (ri >= mu_c - 2.5 * si_c) & (ri <= mu_c + 2.5 * si_c)

            # Pass 4: intensity filter (remove very low intensity = interior objects)
            if intensity is not None:
                int_sec = intensity[idx]
                int_med = float(np.median(int_sec[fine])) if fine.sum() > 0 else float(np.median(int_sec))
                int_thr = int_med * 0.35
                int_ok  = int_sec >= int_thr
                final   = fine & int_ok
                if final.sum() >= 6:
                    keep[idx[final]] = True
                    continue
            keep[idx[fine]] = True

        result = validate_xyz(pts[keep])

        # Global pass: remove points far outside expected tunnel radius
        if len(result) >= 10:
            c2, ax2, _e1, _e2 = principal_axes(result)
            diff2 = result - c2
            ax_c2 = (diff2 @ ax2)[:, None] * ax2
            ri2 = np.linalg.norm(diff2 - ax_c2, axis=1)
            R_global = float(np.median(ri2))
            mad_global = float(np.median(np.abs(ri2 - R_global))) + 1e-9
            thr_global = 3.0 * 1.4826 * mad_global
            global_keep = (np.abs(ri2 - R_global) <= thr_global) & (ri2 >= R_global * 0.35)
            result = validate_xyz(result[global_keep])

        return result

    def extract_lining_by_label(
        self,
        context: PipelineContext,
        structure_labels: Optional[set] = None,
        band: Tuple[float, float] = (0.80, 1.20),
        min_inband_frac: float = 0.60,
    ) -> Tuple[np.ndarray, Dict]:
        """Isolate the lining using per-point semantic labels (FY387 / STSD).

        The ASCII reader stores a per-point label channel in
        ``scan.metadata['labels']`` for >=8-column files. This keeps only the
        structural classes and drops interior objects (cables, lights, signal
        devices, vehicles, people) without any geometric fitting.

        structure_labels: explicit set of label ids to keep. When None they are
        auto-detected: the dominant-axis radius is computed per point and any
        label whose points mostly (>= ``min_inband_frac``) fall inside the
        shell radius band (``band`` x median radius) is treated as lining.
        Returns (kept_xyz, stats). Falls back to the geometric
        extract_tunnel_lining when no labels are present.
        """
        scan = context.active_scan
        if scan is None:
            raise RuntimeError("extract_lining_by_label: no active scan.")
        wp = context.working_points
        if wp is None:
            raise RuntimeError("extract_lining_by_label: no working_points.")
        pts = validate_xyz(wp)
        # T2: labels are re-aligned to the current working_points (handles
        # voxel/SOR/lining), so this no longer has to run on the raw scan.
        labels = context.working_labels()
        if labels is None:
            # No semantic labels available -> geometric fallback.
            kept = self.extract_tunnel_lining(context)
            return kept, {"method": "geometric_fallback", "reason": "no labels",
                          "n_raw": int(len(pts)),
                          "n_clean": int(len(kept))}
        labels = np.asarray(labels).ravel()
        if len(labels) != len(pts):
            raise RuntimeError(
                f"label/point mismatch ({len(labels)} vs {len(pts)}) after alignment.")
        labels = labels.astype(np.int64)

        # Radius of each point about the PCA dominant axis (for auto-detect and
        # stats), computed once on the whole cloud.
        c, ax, _e1, _e2 = principal_axes(pts)
        diff = pts - c
        axc = (diff @ ax)[:, None] * ax
        radial = np.linalg.norm(diff - axc, axis=1)
        r_med = float(np.median(radial))
        lo, hi = band[0] * r_med, band[1] * r_med

        uniq = np.unique(labels)
        if structure_labels is None:
            detected = set()
            per_label = {}
            for lb in uniq.tolist():
                m = labels == lb
                inband = float(np.mean((radial[m] >= lo) & (radial[m] <= hi)))
                per_label[int(lb)] = round(inband, 3)
                if inband >= min_inband_frac:
                    detected.add(int(lb))
            structure_labels = detected
            detect_info = {"auto_detected": True, "inband_by_label": per_label,
                           "r_median": round(r_med, 4), "band": [round(lo, 3), round(hi, 3)]}
        else:
            structure_labels = {int(x) for x in structure_labels}
            detect_info = {"auto_detected": False}

        keep_mask = np.isin(labels, list(structure_labels)) if structure_labels \
            else np.ones(len(pts), dtype=bool)
        kept = validate_xyz(pts[keep_mask], "lining_by_label")

        stats = {
            "method": "label",
            "structure_labels": sorted(structure_labels),
            "n_raw": int(len(pts)),
            "n_clean": int(len(kept)),
            "n_removed": int(len(pts) - int(keep_mask.sum())),
            "labels_present": uniq.astype(int).tolist(),
        }
        stats.update(detect_info)
        return kept, stats

    def auto_denoise(
        self,
        context: PipelineContext,
        k_neighbors: int = 20,
        cable_linearity_thr: float = 0.30,
        light_sphericity_thr: float = 0.12,
        light_size_thr: float = 0.20,
        light_cluster_max: int = 500,
        person_height_thr: float = 1.2,
        person_width_thr: float = 0.8,
        k_sigma: float = 2.5,
        section_len: float = 0.5,
        interior_ratio: float = 0.40,
        wall_protrusion_thr: float = 0.05,
    ) -> Tuple[np.ndarray, Dict]:
        """Fully automatic intelligent denoising (no manual interaction).

        Combines morphological/semantic classification with distance-statistics
        filtering to identify and remove every non-structural object (cables,
        lights, signal devices, vehicles and people) from the tunnel lining,
        in a single pass:

        Stage A - Semantic morphology (local PCA shape per point):
          * Cables/pipes  -> high linearity      (long, thin)
          * Lights/signals-> high sphericity + small isolated cluster
          * People/vehicles-> planar clusters of human/vehicle size (DBSCAN)
        Stage B - Distance statistics along the tunnel axis (robust median+MAD):
          * Per axial slice, keep points whose radial distance lies within
            R_med +/- k_sigma*1.4826*MAD and outside the interior band
            (r < interior_ratio*R_med) where stray fixtures/vehicles sit.

        Returns the cleaned lining cloud plus per-class statistics. Pure
        NumPy/SciPy with optional scikit-learn; degrades gracefully when a
        dependency is missing so it is always safe to call headless.
        """
        pts = context.working_points
        if pts is None:
            raise RuntimeError("auto_denoise: no working_points.")
        pts = validate_xyz(pts)
        n_raw = len(pts)
        if n_raw < 10:
            return pts, {"n_raw": n_raw, "n_clean": n_raw, "n_removed": 0,
                         "n_cable": 0, "n_light": 0, "n_person": 0,
                         "n_radial": 0, "noise_pts": np.empty((0, 3))}

        # ---- Stage A: semantic / morphological classification --------------
        sem_noise = np.zeros(n_raw, dtype=bool)
        n_cable = n_light = n_person = 0
        # Per-class masks are consumed in the return dict below; initialise them
        # here so they exist even when Stage A is skipped (scipy/cKDTree absent).
        is_cable  = np.zeros(n_raw, dtype=bool)
        is_light  = np.zeros(n_raw, dtype=bool)
        is_person = np.zeros(n_raw, dtype=bool)
        if cKDTree is not None:
            k = min(k_neighbors, n_raw - 1)
            tree = cKDTree(pts)
            _, idx = tree.query(pts, k=k + 1, workers=-1)
            nbr_idx = idx[:, 1:]  # (N, k) neighbour ids, excluding self

            # Vectorised local PCA in memory-bounded chunks: build the (m,3,3)
            # neighbourhood covariance matrices per chunk and batch-solve their
            # eigenvalues. This is orders of magnitude faster than a per-point
            # Python loop while capping peak memory (a full (N,k,3) buffer would
            # be multi-GB at the 5M-point ceiling).
            linearity = np.zeros(n_raw)
            planarity = np.zeros(n_raw)
            sphericity = np.zeros(n_raw)
            local_size = np.zeros(n_raw)
            sig2_over_sig1 = np.ones(n_raw)
            chunk = max(1, min(n_raw, 200_000 // max(k, 1)))
            for start in range(0, n_raw, chunk):
                end = min(start + chunk, n_raw)
                nb = pts[nbr_idx[start:end]]                      # (m,k,3)
                nb = nb - nb.mean(axis=1, keepdims=True)
                cov = np.einsum('mki,mkj->mij', nb, nb) / max(k - 1, 1)
                ev = np.clip(np.linalg.eigvalsh(cov), 0.0, None)  # (m,3) ascending
                # Demantke (2011) features: sigma = sqrt(lambda) normalised by the
                # largest sigma (matches lyuhaitao/PowerLineDetection, see
                # _ref_PowerLine/lyutool/core.py::extractFeathersByPointCloud).
                sig = np.sqrt(ev)
                s3 = sig[:, 0]; s2 = sig[:, 1]; s1 = sig[:, 2]
                s1_safe = np.where(s1 > 1e-12, s1, 1e-12)
                linearity[start:end] = (s1 - s2) / s1_safe
                planarity[start:end] = (s2 - s3) / s1_safe
                sphericity[start:end] = s3 / s1_safe
                local_size[start:end] = s1
                sig2_over_sig1[start:end] = s2 / s1_safe

            # A true cable/pipe is thin along BOTH transverse axes, so its
            # second singular value is negligible. The Demantke linearity
            # already encodes (1 - s2/s1); the explicit s2/s1 gate keeps
            # merely elongated lining patches from being flagged as cables.
            is_cable = (linearity >= cable_linearity_thr) & (sig2_over_sig1 < 0.15)
            # Use the highest-F1 clean-noise benchmark behaviour (commit
            # 0909e7d): the raw shape gate is intentionally aggressive. It can
            # remove some lining points, but it catches far more non-structural
            # clutter than the later conservative cluster-isolation gate.
            is_light = (sphericity >= light_sphericity_thr) & (local_size <= light_size_thr)
            is_person = np.zeros(n_raw, dtype=bool)
            person_mask = planarity > 0.4
            if person_mask.sum() > 10:
                try:
                    from sklearn.cluster import DBSCAN
                    person_pts = pts[person_mask]
                    labels = DBSCAN(eps=0.15, min_samples=5).fit(person_pts).labels_
                    for c in set(labels) - {-1}:
                        cp = person_pts[labels == c]
                        height = float(cp[:, 2].max() - cp[:, 2].min())
                        width = float(np.ptp(cp[:, :2], axis=0).max())
                        if person_height_thr <= height <= 2.2 and width <= person_width_thr:
                            center = cp.mean(axis=0)
                            is_person[np.linalg.norm(pts - center, axis=1) < 0.5] = True
                except Exception:
                    pass

            # Sanity guard: each non-structural class can only be a small part
            # of a real tunnel. If a shape gate flags an implausibly large
            # fraction it is misfiring on clean/dense data (e.g. voxel-merged or
            # already-curated scans where local patches mimic the target shape)
            # and would strip the lining. Disable that class and warn instead of
            # silently destroying the structure.
            MAX_CLASS_FRAC = 0.30
            if is_cable.mean() > MAX_CLASS_FRAC:
                warnings.warn(f"Auto-denoise: cable gate flagged {100*is_cable.mean():.0f}% "
                              f"(> {int(MAX_CLASS_FRAC*100)}%) - likely lining, disabled.")
                is_cable = np.zeros(n_raw, dtype=bool)
            if is_light.mean() > MAX_CLASS_FRAC:
                warnings.warn(f"Auto-denoise: light gate flagged {100*is_light.mean():.0f}% "
                              f"(> {int(MAX_CLASS_FRAC*100)}%) - likely lining, disabled.")
                is_light = np.zeros(n_raw, dtype=bool)

            sem_noise = is_cable | is_light | is_person
            n_cable = int(is_cable.sum())
            n_light = int(is_light.sum())
            n_person = int(is_person.sum())

        # ---- Stage B: radial distance statistics (median + MAD) ------------
        radial_noise = np.zeros(n_raw, dtype=bool)
        survivors = ~sem_noise
        if survivors.sum() >= 6:
            sidx = np.where(survivors)[0]
            sp_all = pts[sidx]
            centroid, long_ax, _e1, _e2 = principal_axes(sp_all)
            centred = sp_all - centroid
            proj = centred @ long_ax
            pmin, pmax = float(proj.min()), float(proj.max())
            ns = max(1, int(np.ceil((pmax - pmin) / section_len)))
            radial_keep_local = np.zeros(len(sidx), dtype=bool)
            for s in range(ns):
                lo = pmin + s * section_len
                hi = pmin + (s + 1) * section_len
                if s == ns - 1:
                    hi = pmax + 1e-9
                m = (proj >= lo) & (proj < hi)
                loc = np.where(m)[0]
                if len(loc) < 6:
                    radial_keep_local[loc] = True
                    continue
                ao = centroid + float(proj[loc].mean()) * long_ax
                diff = sp_all[loc] - ao
                ri = np.linalg.norm(diff - (diff @ long_ax)[:, None] * long_ax, axis=1)
                R_med = float(np.median(ri))
                if R_med < 1e-4:
                    radial_keep_local[loc] = True
                    continue
                mad = float(np.median(np.abs(ri - R_med))) + 1e-9
                thr = k_sigma * 1.4826 * mad
                band = (np.abs(ri - R_med) <= thr) & (ri >= R_med * interior_ratio)
                radial_keep_local[loc[band]] = True
            radial_noise[sidx[~radial_keep_local]] = True

        # ---- Stage C: wall-mounted cable/conduit detection -----------------
        # Per-point shape and radial-MAD both fail for cables hugging the
        # wall (their neighbourhood looks planar and their radius matches the
        # lining). Detect them by inward protrusion from the local wall
        # envelope plus axial continuity. Only consider points still kept.
        wall_noise = np.zeros(n_raw, dtype=bool)
        if wall_protrusion_thr and wall_protrusion_thr > 0:
            candidate = ~(sem_noise | radial_noise)
            try:
                wall_noise = self._detect_wall_protrusion(
                    pts, candidate, protrusion_thr=float(wall_protrusion_thr))
            except Exception as e:
                warnings.warn(f"Wall-protrusion detection failed: {e}")
                wall_noise = np.zeros(n_raw, dtype=bool)
            # Same sanity guard as the shape gates: wall cables cannot be a huge
            # fraction of the cloud. If the protrusion detector flags too much it
            # is eating the curved lining itself (dense/merged data) - disable.
            if wall_noise.mean() > 0.30:
                warnings.warn(f"Auto-denoise: wall-cable gate flagged {100*wall_noise.mean():.0f}% "
                              f"(> 30%) - likely lining, disabled.")
                wall_noise = np.zeros(n_raw, dtype=bool)

        noise_mask = sem_noise | radial_noise | wall_noise
        clean_pts = validate_xyz(pts[~noise_mask])
        if context.registered_points is not None:
            context.registered_points = clean_pts
        else:
            context.normalized_points = clean_pts
        return clean_pts, {
            "n_raw": n_raw,
            "n_clean": int((~noise_mask).sum()),
            "n_removed": int(noise_mask.sum()),
            "n_cable": n_cable,
            "n_light": n_light,
            "n_person": n_person,
            "n_radial": int(radial_noise.sum()),
            "n_wall_cable": int(wall_noise.sum()),
            "noise_pts": pts[noise_mask].copy(),
            # Per-class point sets so downstream (IFC export) can model the
            # detected non-structural objects, not just count them. Wall cables
            # are grouped with cables.
            "component_points": {
                "cable": pts[is_cable | wall_noise].copy(),
                "light": pts[is_light].copy(),
                "person": pts[is_person].copy(),
            },
        }
    @staticmethod
    def _detect_wall_protrusion(
        pts: np.ndarray,
        candidate: np.ndarray,
        protrusion_thr: float = 0.05,
        n_axial: int = 60,
        n_theta: int = 180,
        wall_percentile: float = 90.0,
        min_axial_runs: int = 3,
    ) -> np.ndarray:
        """Detect wall-mounted cables/conduits by inward protrusion + axial run.

        Per-point shape features cannot separate a cable that hugs the wall: its
        k-neighbourhood is dominated by wall points, so its local geometry looks
        planar (verified on labelled real data: cable linearity median ~0.14,
        same as the wall). The discriminative signal is that a cable sits *inside*
        the local wall envelope and runs continuously along the tunnel axis.

        Builds a coarse wall-radius envelope (high percentile of r per
        axial x angular cell), flags points protruding inward beyond
        ``protrusion_thr``, then keeps only angular columns whose protruding
        points span several axial cells (a continuous run), which rejects
        isolated wall bumps. Returns a boolean mask over ``pts`` (True = cable).

        ``candidate`` restricts which points are eligible (e.g. points not
        already removed by other stages) to save work.
        """
        n = len(pts)
        mask = np.zeros(n, dtype=bool)
        idx_all = np.where(candidate)[0]
        if len(idx_all) < 50:
            return mask
        p = pts[idx_all]

        # Cylindrical coordinates about the PCA long axis.
        c, axis, e1, e2 = principal_axes(p)
        d = p - c
        h = d @ axis
        u = d @ e1
        w = d @ e2
        r = np.sqrt(u * u + w * w)
        theta = np.degrees(np.arctan2(w, u))

        h_edges = np.linspace(h.min(), h.max(), n_axial + 1)
        t_edges = np.linspace(-180.0, 180.0, n_theta + 1)
        hi = np.clip(np.digitize(h, h_edges) - 1, 0, n_axial - 1)
        ti = np.clip(np.digitize(theta, t_edges) - 1, 0, n_theta - 1)

        # Wall-radius envelope per (axial, angular) cell = high percentile of r.
        wall = np.full((n_axial, n_theta), np.nan)
        cell = hi * n_theta + ti
        order_c = np.argsort(cell, kind="stable")
        cs = cell[order_c]
        rs = r[order_c]
        uniq, first = np.unique(cs, return_index=True)
        bounds = np.append(first, len(cs))
        for gi in range(len(uniq)):
            seg = rs[bounds[gi]:bounds[gi + 1]]
            if len(seg) >= 5:
                wall.flat[uniq[gi]] = np.percentile(seg, wall_percentile)

        wall_r = wall[hi, ti]
        protrusion = wall_r - r
        prot = np.isfinite(protrusion) & (protrusion > protrusion_thr)

        # Axial continuity: keep an angular column only if its protruding points
        # span >= min_axial_runs distinct axial cells (cables run along h).
        keep_local = np.zeros(len(p), dtype=bool)
        prot_ti = ti[prot]
        prot_hi = hi[prot]
        prot_loc = np.where(prot)[0]
        if len(prot_loc):
            # Highest-F1 benchmark behaviour from commit 0909e7d: keep any
            # angular column with enough axial continuity. Later angular-width
            # caps preserved lining but drove wall-cable recall to zero.
            for tcol in np.unique(prot_ti):
                in_col = prot_ti == tcol
                if np.unique(prot_hi[in_col]).size >= min_axial_runs:
                    keep_local[prot_loc[in_col]] = True

        mask[idx_all[keep_local]] = True
        return mask

    def extract_lining_density_variation(
        self,
        context: PipelineContext,
        ring_count: int = 40,
        theta_step_deg: float = 0.5,
        r_step: float = 0.01,
        grad_threshold: float = 0.2,
        smooth_window: int = 5,
    ) -> Tuple[np.ndarray, Dict]:
        """Extract the tunnel lining via local density-difference denoising.

        Pure-NumPy re-implementation of Algorithm 2 ("Local point cloud
        density-difference-based denoising") from SAM4Tun (Ye et al., 2025,
        Tunnelling and Underground Space Technology; repo zxy239/SAM4Tun). The
        original notebook uses numba/torch; only the training-free density
        logic is reproduced here, kept dependency-light for headless use.

        Idea: convert the cloud to cylindrical coordinates (h along the axis,
        theta around it, r = radial distance). For each axial section and each
        angular bin, build a radial-distance histogram. The lining forms a
        dense radial peak; scanning inward from that peak, the first place where
        the point count drops sharply (negative gradient beyond grad_threshold)
        marks the inner boundary of the lining. Points inside that cut-off
        (cables, fixtures, vehicles in the bore) are discarded.

        Returns the lining cloud plus statistics. Updates
        context.normalized_points in place.
        """
        pts = context.working_points
        if pts is None:
            raise RuntimeError("extract_lining_density_variation: no working_points.")
        pts = validate_xyz(pts)
        n_raw = len(pts)
        if n_raw < 50:
            if context.registered_points is not None:
                context.registered_points = pts
            else:
                context.normalized_points = pts
            return pts, {"n_raw": n_raw, "n_clean": n_raw, "n_removed": 0,
                         "method": "skip-too-small"}

        # --- cylindrical coordinates around the PCA axis ---
        centroid, axis, e1, e2 = principal_axes(pts)
        centred = pts - centroid
        h = centred @ axis                      # along-axis position
        u = centred @ e1
        v = centred @ e2
        r = np.sqrt(u * u + v * v)              # radial distance to axis
        theta = np.degrees(np.arctan2(v, u))    # angle around axis [-180,180]

        keep = np.ones(n_raw, dtype=bool)
        hmin, hmax = float(h.min()), float(h.max())
        x_step = max((hmax - hmin) / max(ring_count, 1), 1e-6)
        x_edges = np.arange(hmin, hmax + x_step, x_step)
        t_edges = np.arange(-180.0, 180.0 + theta_step_deg, theta_step_deg)
        n_removed_density = 0

        for xi in range(len(x_edges) - 1):
            xm = (h >= x_edges[xi]) & (h < x_edges[xi + 1])
            if not xm.any():
                continue
            r_sub = r[xm]
            th_sub = theta[xm]
            idx_sub = np.where(xm)[0]

            r_lo, r_hi = float(r_sub.min()), float(r_sub.max())
            if r_hi - r_lo < r_step:
                continue
            r_bins = np.arange(r_lo, r_hi + r_step, r_step)
            t_idx = np.clip(np.digitize(th_sub, t_edges) - 1, 0, len(t_edges) - 2)

            def _inner_boundary(counts):
                """Radius (bin edge) of the lining inner edge: scan inward from
                the densest shell until the count drops off sharply."""
                if counts.sum() == 0:
                    return None
                peak = int(np.argmax(counts))
                grad = np.diff(counts) / (counts[:-1] + 1e-6)
                cut_bin = peak
                for j in range(peak, 0, -1):
                    if grad[j - 1] < -grad_threshold or (counts[j] == 0 and counts[j - 1] == 0):
                        cut_bin = j
                        break
                return float(r_bins[cut_bin])

            # Section-level baseline: the lining inner edge from ALL points in
            # this axial slice. Dense and robust, so sparse interior clutter
            # (a cable at one fixed angle, with few points per angular cell) is
            # still removed even where its own angular bin is too thin to fit.
            section_counts, _ = np.histogram(r_sub, bins=r_bins)
            base_cut = _inner_boundary(section_counts)
            if base_cut is None:
                continue
            cutoff = np.full(len(t_edges) - 1, base_cut)

            # Per-angle refinement only where a bin has enough points; never
            # below the section baseline (avoids re-admitting interior clutter).
            for ti in range(len(t_edges) - 1):
                sel = t_idx == ti
                if sel.sum() < 10:
                    continue
                counts, _ = np.histogram(r_sub[sel], bins=r_bins)
                cut = _inner_boundary(counts)
                if cut is not None:
                    cutoff[ti] = max(cut, base_cut)

            drop = r_sub < cutoff[t_idx]        # inside the lining boundary
            if drop.any():
                keep[idx_sub[drop]] = False
                n_removed_density += int(drop.sum())

        clean = validate_xyz(pts[keep])
        if context.registered_points is not None:
            context.registered_points = clean
        else:
            context.normalized_points = clean
        return clean, {
            "n_raw": n_raw,
            "n_clean": int(keep.sum()),
            "n_removed": int((~keep).sum()),
            "n_removed_density": n_removed_density,
            "method": "density-variation",
            "noise_pts": pts[~keep].copy(),
        }
