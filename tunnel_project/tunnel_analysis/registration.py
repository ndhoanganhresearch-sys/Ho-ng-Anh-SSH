from .common import *
from .models import PipelineContext
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

class RegistrationLayer:
    def anchor_translation(self, context: PipelineContext) -> np.ndarray:
        scan = context.active_scan; pts = context.working_points
        if scan is None or pts is None: raise RuntimeError("Load scan first.")
        src = validate_xyz(pts)
        if len(context.scans) < 2: return src
        tgt = validate_xyz(context.scans[0].points)
        return src + (self._anchor(tgt, context.scans[0].intensity) -
                      self._anchor(src, scan.intensity))

    def run_surface_icp(self, context: PipelineContext) -> Tuple[np.ndarray, float]:
        pts = context.working_points
        if pts is None: raise RuntimeError("Run anchor first.")
        src = validate_xyz(pts)
        if len(context.scans) < 2: return src, 0.0
        return self._icp(src, validate_xyz(context.scans[0].points))

    def calculate_rmse(self, context: PipelineContext) -> float:
        pts = context.working_points
        if pts is None or len(context.scans) < 2: return float("nan")
        return self._rmse(validate_xyz(pts), validate_xyz(context.scans[0].points))

    def register_epochs(
        self, context: PipelineContext, ref_index: int = 0,
        min_targets: int = 3, max_match_dist: float = 2.0,
        detect_max_points: int = 200_000,
    ) -> Dict:
        """Register the monitoring epoch (Tn) onto the reference epoch (T0).

        Solves the field problem: T0 and Tn are scanned from DIFFERENT setups,
        so their coordinate frames differ. This finds the rigid transform that
        brings Tn into T0's frame so deformation can be measured per section.

        Auto-selects the method (the caller need not know in advance):

          • **Target-based** — if >= ``min_targets`` fixed markers (reflectors /
            checkerboards / intensity peaks) are detected and matched in BOTH
            epochs, the transform is computed by rigid SVD from the markers
            alone. Markers do not deform, so this NEVER absorbs the tunnel's
            deformation into the alignment. Preferred for deformation work.

          • **ICP fallback** — when no markers are present, a coarse anchor /
            GROR alignment followed by surface ICP. Note: full-cloud ICP can
            slightly absorb a large localized deformation into the transform;
            it is fine when the deformation is a small fraction of the cloud.

        T0 = ``scans[ref_index]`` (kept fixed). Tn = the active scan (or the
        other scan when active == reference). Returns a dict::

            {"points": Nx3 aligned Tn, "rmse_mm": float,
             "method": "target"|"icp", "n_targets": int}

        The aligned points are also stored in ``context.registered_points`` so
        downstream steps (centerline / sections / deformation) use the aligned
        monitoring cloud automatically.
        """
        if len(context.scans) < 2:
            raise RuntimeError("register_epochs: need >= 2 epochs (T0 + Tn).")
        ref_index = max(0, min(ref_index, len(context.scans) - 1))
        tgt_scan = context.scans[ref_index]                       # T0 reference
        # Source = active monitoring scan; if active IS the reference, take the other.
        src_scan = context.active_scan
        if src_scan is None or src_scan is tgt_scan:
            other = 1 if ref_index == 0 else 0
            src_scan = context.scans[other]
        src = validate_xyz(src_scan.points)
        tgt = validate_xyz(tgt_scan.points)

        # ── 1) Try target-based rigid registration (no deformation absorption)
        T = None
        n_matched = 0
        try:
            from .target_detector import TargetDetector
            from .models import PointCloudBundle as _PCB
            det = TargetDetector()

            def _decim(pts, inten):
                if len(pts) > detect_max_points:
                    step = len(pts) // detect_max_points + 1
                    return pts[::step], (inten[::step] if inten is not None else None)
                return pts, inten

            s_pts, s_int = _decim(src, src_scan.intensity)
            t_pts, t_int = _decim(tgt, tgt_scan.intensity)
            src_targets = det.detect_all(_PCB(points=s_pts, intensity=s_int), scan_idx=1)
            tgt_targets = det.detect_all(_PCB(points=t_pts, intensity=t_int), scan_idx=0)
            matches = det.match_targets(src_targets, tgt_targets,
                                        max_dist=max_match_dist, centroid_align=True)
            if len(matches) >= min_targets:
                sc = np.array([m[0].center for m in matches], dtype=np.float64)  # Tn
                tc = np.array([m[1].center for m in matches], dtype=np.float64)  # T0
                # _horn_svd(src, tgt) -> T maps src(Tn) -> tgt(T0).
                T, _rmse_t = det._horn_svd(sc, tc)
                n_matched = len(matches)
        except Exception as exc:
            warnings.warn(f"register_epochs: target path skipped ({exc})")
            T = None

        if T is not None:
            ones = np.ones((len(src), 1))
            aligned = (T @ np.hstack([src, ones]).T).T[:, :3]
            rmse = self._rmse(aligned, tgt)
            method = "target"
        else:
            # ── 2) ICP fallback (coarse anchor/GROR + TRIMMED ICP) ───────────
            # Trimmed ICP rejects the deformed region from the fit so the
            # transform is driven by the stable lining and the deformation is
            # preserved (full-cloud ICP would absorb it).
            #
            # DIVERGENCE GUARD: on a long, near-symmetric tunnel ICP can slide
            # along the axis and end up worse than the input. So we evaluate
            # {as-is, coarse, trimmed-ICP} and keep whichever has the SMALLEST
            # residual to T0 — the result is never worse than doing nothing.
            candidates = [(src, self._rmse(src, tgt))]
            try:
                coarse = self._coarse_align(
                    src, tgt, src_intensity=src_scan.intensity,
                    tgt_intensity=tgt_scan.intensity)
                candidates.append((coarse, self._rmse(coarse, tgt)))
                icp, icp_rmse = self._trimmed_icp(coarse, tgt)
                candidates.append((icp, icp_rmse))
            except Exception as exc:
                warnings.warn(f"register_epochs: ICP fallback failed ({exc})")
            aligned, rmse = min(candidates, key=lambda c: c[1]
                                if np.isfinite(c[1]) else float("inf"))
            method = "icp"

        aligned = validate_xyz(aligned)
        context.registered_points = aligned
        return {"points": aligned, "rmse_mm": float(rmse),
                "method": method, "n_targets": int(n_matched)}


    def merge_scans(self, context: PipelineContext) -> Tuple[np.ndarray, List[float]]:
        """Merge all loaded scan stations into one point cloud.

        Steps per PDF 3.3:
        1. Use scan[0] as reference (anchor station)
        2. For each subsequent scan: anchor translation -> ICP -> merge
        3. Return merged cloud + per-scan RMSE list
        """
        if len(context.scans) < 2:
            pts = context.working_points
            if pts is None: raise RuntimeError("No scans loaded.")
            return validate_xyz(pts), [0.0]

        # Reference = scan[0]
        tgt = validate_xyz(context.scans[0].points)
        merged = [tgt]
        rmse_list = [0.0]

        for i in range(1, len(context.scans)):
            src_pts = validate_xyz(context.scans[i].points)
            # Step 1: coarse align (GROR rotation+translation, anchor fallback)
            src_shifted = self._coarse_align(src_pts, tgt,
                src_intensity=context.scans[i].intensity,
                tgt_intensity=context.scans[0].intensity)
            # Step 2: ICP fine registration
            src_reg, rmse = self._icp(src_shifted, tgt)
            merged.append(src_reg)
            rmse_list.append(rmse)

        merged_cloud = np.vstack(merged)
        return validate_xyz(merged_cloud), rmse_list

    def register_and_merge(self, context: PipelineContext) -> Tuple[np.ndarray, List[float]]:
        """Register all scans to reference and merge — main entry point."""
        return self.merge_scans(context)

    def apply_manual_transform(self, pts: np.ndarray, offset: Tuple[float, float, float], 
                                               rotation: Tuple[float, float, float]) -> np.ndarray:
        """Apply manual translation and rotation (degrees) to point cloud."""
        if pts is None: return None
        pts = validate_xyz(pts)
        
        # Translation
        pts = pts + np.asarray(offset)
        
        # Rotation
        rx, ry, rz = np.radians(rotation)
        # Rotation matrices
        Rx = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
        Ry = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
        Rz = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
        R = Rz @ Ry @ Rx
        
        return pts @ R.T


    def register_and_merge_chain(self, context: PipelineContext) -> Tuple[np.ndarray, List[float]]:
        """Chain registration: S1 -> S2 -> S3... per professional software."""
        if len(context.scans) < 2:
            pts = context.working_points
            if pts is None: raise RuntimeError("No scans loaded.")
            return validate_xyz(pts), [0.0]

        # Reference is Scan 0
        merged = [validate_xyz(context.scans[0].points)]
        rmse_list = [0.0]
        
        current_ref = merged[0]

        for i in range(1, len(context.scans)):
            src_pts = validate_xyz(context.scans[i].points)

            # 1. Coarse align to the current chain reference (GROR rot+trans,
            #    anchor fallback).
            # NOTE: tgt_intensity must match current_ref, which is the
            # registered version of scans[i-1] — NOT scans[0]. The rigid
            # transform preserves point order, so scans[i-1].intensity
            # indexes into current_ref correctly.
            src_shifted = self._coarse_align(src_pts, current_ref,
                src_intensity=context.scans[i].intensity,
                tgt_intensity=context.scans[i - 1].intensity)
            
            # 2. ICP fine registration
            src_reg, rmse = self._icp(src_shifted, current_ref)
            
            merged.append(src_reg)
            rmse_list.append(rmse)
            # Update reference for the next station (Chain)
            current_ref = src_reg

        merged_cloud = np.vstack(merged)
        return validate_xyz(merged_cloud), rmse_list


    def _coarse_align(self, src: np.ndarray, tgt: np.ndarray,
                      src_intensity=None, tgt_intensity=None) -> np.ndarray:
        """Coarse-align src onto tgt, returning the shifted source points.

        Tries GROR-style feature registration first (FPFH correspondences +
        pairwise-distance graph + Umeyama), which recovers ROTATION as well as
        translation. This fixes the failure mode of the old anchor-only init: a
        single matched point gives translation only, so any yaw between stations
        sent point-to-plane ICP into a local minimum. Falls back to the
        intensity/median anchor translation when features are unavailable
        (Open3D missing, too few correspondences, featureless clouds).
        """
        transform = None
        try:
            transform = self._gror_estimate_transform(src, tgt)
        except Exception as e:
            warnings.warn(f"GROR coarse alignment failed, using anchor shift: {e}")
            transform = None
        if transform is not None:
            ones = np.ones((src.shape[0], 1))
            return (transform @ np.hstack([src, ones]).T).T[:, :3]
        shift = self._anchor(tgt, tgt_intensity) - self._anchor(src, src_intensity)
        return src + shift
    def _anchor(self, pts: np.ndarray, intensity: Optional[np.ndarray]) -> np.ndarray:
        pts = validate_xyz(pts)
        if intensity is not None:
            vals = np.asarray(intensity, dtype=np.float64).ravel()
            if vals.shape[0] == pts.shape[0]:
                fm = np.isfinite(vals)
                if fm.any(): return pts[int(np.argmax(np.where(fm, vals, -np.inf)))].copy()
        est = np.median(pts, axis=0)
        for _ in range(300):
            d = np.linalg.norm(pts - est, axis=1); nz = d > 1e-10
            if not nz.any(): break
            w = 1.0 / d[nz]; new = (w[:, None] * pts[nz]).sum(axis=0) / w.sum()
            if np.linalg.norm(new - est) < 1e-7: est = new; break
            est = new
        return est

    @staticmethod
    def _rigid_svd(src: np.ndarray, tgt: np.ndarray) -> np.ndarray:
        """Best-fit rigid 4x4 mapping src -> tgt (Horn/Kabsch, no scale)."""
        sc = src.mean(0); tc = tgt.mean(0)
        H = (src - sc).T @ (tgt - tc)
        U, _S, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T
        if np.linalg.det(R) < 0:
            Vt[-1] *= -1; R = Vt.T @ U.T
        T = np.eye(4); T[:3, :3] = R; T[:3, 3] = tc - R @ sc
        return T

    def _trimmed_icp(self, src: np.ndarray, tgt: np.ndarray,
                     keep_frac: float = 0.80, iters: int = 25
                     ) -> Tuple[np.ndarray, float]:
        """Trimmed ICP (TrICP) — rigid alignment that does NOT absorb deformation.

        Standard ICP fits ALL correspondences, so a deformed region pulls the
        transform and the measured deformation shrinks (observed: a 60 mm crown
        settlement collapsed to ~16 mm after full-cloud ICP). TrICP instead
        rejects the worst ``1-keep_frac`` residuals each iteration — the
        deformed lining becomes an "outlier" and is excluded from the fit, so
        the transform is driven by the STABLE majority and the deformation is
        preserved for measurement.

        Returns (aligned_src, rmse_mm) where rmse is over the kept inliers.
        """
        try:
            from scipy.spatial import cKDTree
        except Exception:
            return self._icp(src, tgt)
        tree = cKDTree(tgt)
        cur = np.asarray(src, dtype=np.float64).copy()
        keep_frac = float(np.clip(keep_frac, 0.4, 0.98))
        prev_rmse = np.inf
        for _ in range(iters):
            d, idx = tree.query(cur, k=1, workers=-1)
            thr = np.quantile(d, keep_frac)
            m = d <= max(thr, 1e-9)
            if int(m.sum()) < 10:
                break
            T = self._rigid_svd(cur[m], tgt[idx[m]])
            ones = np.ones((len(cur), 1))
            cur = (T @ np.hstack([cur, ones]).T).T[:, :3]
            rmse_m = float(np.sqrt(np.mean(d[m] ** 2)))  # KD-tree distances are in metres
            if abs(prev_rmse - rmse_m) < 1e-5:            # converged within 0.01 mm
                break
            prev_rmse = rmse_m
        d, idx = tree.query(cur, k=1, workers=-1)
        thr = np.quantile(d, keep_frac); m = d <= max(thr, 1e-9)
        rmse_mm = float(np.sqrt(np.mean(d[m] ** 2))) * 1e3 if m.any() else float("nan")
        return cur, rmse_mm

    def _icp(self, src: np.ndarray, tgt: np.ndarray) -> Tuple[np.ndarray, float]:
        if small_gicp is not None and len(src) >= 20 and len(tgt) >= 20:
            try:
                return self._icp_gicp(src, tgt)
            except Exception as e:
                warnings.warn(f"GICP failed, falling back to Open3D ICP: {e}")
        if o3d is not None and len(src) >= 20 and len(tgt) >= 20:
            vs = float(np.clip(np.linalg.norm(np.ptp(tgt, axis=0)) / 600.0, 0.02, 0.12))
            def _pc(p):
                pc = o3d.geometry.PointCloud()
                pc.points = o3d.utility.Vector3dVector(p); return pc
            sd = _pc(src).voxel_down_sample(vs); td = _pc(tgt).voxel_down_sample(vs)
            nr = o3d.geometry.KDTreeSearchParamHybrid(radius=max(vs * 3, 0.05), max_nn=30)
            for pc in (sd, td):
                pc.estimate_normals(nr)
                pc.orient_normals_consistent_tangent_plane(k=15)
            est  = o3d.pipelines.registration.TransformationEstimationPointToPlane()
            crit = o3d.pipelines.registration.ICPConvergenceCriteria
            r1 = o3d.pipelines.registration.registration_icp(
                sd, td, max(vs * 6, 0.15), np.eye(4), est,
                crit(max_iteration=60, relative_fitness=1e-5, relative_rmse=1e-5))
            r2 = o3d.pipelines.registration.registration_icp(
                sd, td, max(vs * 1.5, 0.004), r1.transformation, est,
                crit(max_iteration=120, relative_fitness=1e-7, relative_rmse=1e-7))
            T = np.asarray(r2.transformation, dtype=np.float64)
            ones = np.ones((src.shape[0], 1))
            reg  = (T @ np.hstack([src, ones]).T).T[:, :3]
            return reg, float(r2.inlier_rmse) * 1000.0
        return src, self._rmse(src, tgt)

    def _icp_gicp(self, src: np.ndarray, tgt: np.ndarray) -> Tuple[np.ndarray, float]:
        """Fine registration via small_gicp (parallel GICP).

        Returns the transformed source cloud and post-alignment RMSE in mm.
        Voxel/downsampling resolutions adapt to the target's bounding extent
        so behaviour matches the Open3D path for tunnel-scale clouds.
        """
        extent = float(np.linalg.norm(np.ptp(tgt, axis=0)))
        vs = float(np.clip(extent / 600.0, 0.02, 0.12))
        src64 = np.ascontiguousarray(src, dtype=np.float64)
        tgt64 = np.ascontiguousarray(tgt, dtype=np.float64)
        result = small_gicp.align(
            tgt64, src64,
            registration_type="GICP",
            voxel_resolution=max(vs * 4, 0.1),
            downsampling_resolution=vs,
            max_correspondence_distance=max(vs * 6, 0.15),
            num_threads=max(1, (os.cpu_count() or 2)),
            max_iterations=60,
        )
        T = np.asarray(result.T_target_source, dtype=np.float64)
        ones = np.ones((src.shape[0], 1))
        reg = (T @ np.hstack([src64, ones]).T).T[:, :3]
        return reg, self._rmse(reg, tgt)

    def _rmse(self, src: np.ndarray, tgt: np.ndarray) -> float:
        if cKDTree is None: return float("nan")
        step = max(1, src.shape[0] // 100_000)
        d, _ = cKDTree(tgt).query(src[::step], k=1, workers=-1)
        return float(np.sqrt(np.mean(d ** 2))) * 1000.0

    # ------------------------------------------------------------------ GROR --
    # GROR-inspired robust registration. Re-implements the core idea of
    # WPC-WHU/GROR (TPAMI 2022) in Python/Open3D + NumPy: build FPFH feature
    # correspondences, then discard outliers using pairwise-distance
    # consistency (a rigid transform preserves inter-point distances, so true
    # correspondences form a mutually-consistent graph), solve the pose with
    # Umeyama/SVD, and refine with the existing ICP. See _ref_GROR/ for the
    # original C++ reference implementation.

    def register_gror_like(
        self,
        context: PipelineContext,
        voxel_factor: float = 1.0,
        max_correspondences: int = 1500,
        dist_tol_factor: float = 2.0,
        min_inliers: int = 3,
    ) -> Tuple[np.ndarray, float]:
        """Robustly register the active scan to scan[0] via GROR-style outlier
        removal, then ICP. Returns (registered_source_points, rmse_mm).

        Falls back to anchor-translation + ICP when Open3D is unavailable or
        too few reliable correspondences survive (e.g. tiny / featureless
        clouds), so it is always safe to call in place of run_surface_icp.
        """
        pts = context.working_points
        if pts is None:
            raise RuntimeError("Load scan first.")
        src = validate_xyz(pts)
        if len(context.scans) < 2:
            return src, 0.0
        tgt = validate_xyz(context.scans[0].points)

        transform = self._gror_estimate_transform(
            src, tgt,
            voxel_factor=voxel_factor,
            max_correspondences=max_correspondences,
            dist_tol_factor=dist_tol_factor,
            min_inliers=min_inliers,
        )
        if transform is None:
            # Coarse feature stage failed: fall back to the legacy anchor shift.
            shift = self._anchor(tgt, context.scans[0].intensity) - self._anchor(
                src, context.active_scan.intensity if context.active_scan else None)
            return self._icp(src + shift, tgt)

        ones = np.ones((src.shape[0], 1))
        src_coarse = (transform @ np.hstack([src, ones]).T).T[:, :3]
        # Refine the GROR coarse pose with the existing fine ICP/GICP stage.
        return self._icp(src_coarse, tgt)

    def _gror_estimate_transform(
        self,
        src: np.ndarray,
        tgt: np.ndarray,
        voxel_factor: float = 1.0,
        max_correspondences: int = 1500,
        dist_tol_factor: float = 2.0,
        min_inliers: int = 3,
    ) -> Optional[np.ndarray]:
        """Estimate a coarse 4x4 rigid transform from src to tgt using FPFH
        correspondences filtered by graph reliability. Returns None on failure.
        """
        if o3d is None or len(src) < 20 or len(tgt) < 20:
            return None
        resolution = float(np.clip(np.linalg.norm(np.ptp(tgt, axis=0)) / 600.0, 0.02, 0.12))
        resolution *= float(max(voxel_factor, 1e-3))

        kp_s, feat_s = self._fpfh_features(src, resolution)
        kp_t, feat_t = self._fpfh_features(tgt, resolution)
        if kp_s is None or kp_t is None or len(kp_s) < 3 or len(kp_t) < 3:
            return None

        corr = self._match_mutual(feat_s, feat_t)
        if len(corr) < min_inliers:
            return None
        if len(corr) > max_correspondences:
            # Keep a bounded random subset so the O(m^2) graph stays tractable.
            rng = np.random.default_rng(42)
            corr = corr[rng.choice(len(corr), max_correspondences, replace=False)]

        ps = kp_s[corr[:, 0]]
        pt = kp_t[corr[:, 1]]
        inlier_mask = self._graph_reliable_inliers(
            ps, pt, dist_tol=dist_tol_factor * resolution, min_inliers=min_inliers)
        if int(inlier_mask.sum()) < min_inliers:
            return None
        return self._umeyama(ps[inlier_mask], pt[inlier_mask])

    @staticmethod
    def _fpfh_features(pts: np.ndarray, resolution: float) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Downsample, estimate normals, and compute FPFH-33 descriptors.

        Mirrors GROR's preparation radii (normals 3x, FPFH 8x resolution).
        Returns (keypoint_xyz Nx3, feature NxD) or (None, None) on failure.
        """
        try:
            pc = o3d.geometry.PointCloud()
            pc.points = o3d.utility.Vector3dVector(np.ascontiguousarray(pts, dtype=np.float64))
            down = pc.voxel_down_sample(resolution)
            if len(down.points) < 3:
                return None, None
            down.estimate_normals(
                o3d.geometry.KDTreeSearchParamHybrid(radius=resolution * 3.0, max_nn=30))
            fpfh = o3d.pipelines.registration.compute_fpfh_feature(
                down, o3d.geometry.KDTreeSearchParamHybrid(radius=resolution * 8.0, max_nn=100))
            kp = np.asarray(down.points, dtype=np.float64)
            feat = np.asarray(fpfh.data, dtype=np.float64).T  # N x 33
            if feat.shape[0] != kp.shape[0] or kp.shape[0] < 3:
                return None, None
            return kp, feat
        except Exception:
            return None, None

    @staticmethod
    def _match_mutual(feat_s: np.ndarray, feat_t: np.ndarray) -> np.ndarray:
        """Mutual (reciprocal) nearest-neighbour matching in FPFH space.

        Returns an (M, 2) int array of (source_idx, target_idx) pairs.
        """
        if cKDTree is None:
            return np.empty((0, 2), dtype=np.int64)
        tree_t = cKDTree(feat_t)
        _, nn_st = tree_t.query(feat_s, k=1, workers=-1)
        tree_s = cKDTree(feat_s)
        _, nn_ts = tree_s.query(feat_t, k=1, workers=-1)
        s_idx = np.arange(len(feat_s))
        mutual = nn_ts[nn_st] == s_idx
        return np.column_stack([s_idx[mutual], nn_st[mutual]]).astype(np.int64)

    @staticmethod
    def _graph_reliable_inliers(ps: np.ndarray, pt: np.ndarray, dist_tol: float,
                                min_inliers: int = 3) -> np.ndarray:
        """Select inliers via pairwise-distance consistency (GROR node/edge
        reliability). Two correspondences are consistent if the distance
        between their source points matches that between their target points
        (a rigid transform preserves distances). The correspondence with the
        most consistent partners seeds a star-consistent inlier set.
        """
        m = len(ps)
        if m < 3:
            return np.ones(m, dtype=bool)
        ds = np.linalg.norm(ps[:, None, :] - ps[None, :, :], axis=2)
        dt = np.linalg.norm(pt[:, None, :] - pt[None, :, :], axis=2)
        consistent = np.abs(ds - dt) < dist_tol
        np.fill_diagonal(consistent, False)
        degree = consistent.sum(axis=1)
        seed = int(np.argmax(degree))

        # Candidate clique: the seed plus every correspondence consistent
        # with it (GROR node reliability).
        cand = consistent[seed].copy()
        cand[seed] = True
        cand_idx = np.where(cand)[0]
        if len(cand_idx) < 3:
            return cand

        # Refine to a mutually-consistent set: a coincidental outlier may
        # agree with the seed yet disagree with the rest, so keep only
        # members consistent with a majority of the candidate clique
        # (maximum-consistent-set / edge reliability).
        sub = consistent[np.ix_(cand_idx, cand_idx)]
        votes = sub.sum(axis=1)
        keep = votes >= max(min_inliers - 1, int(np.ceil(0.5 * (len(cand_idx) - 1))))
        inliers = np.zeros(m, dtype=bool)
        inliers[cand_idx[keep]] = True
        if int(inliers.sum()) < 3:
            inliers = cand  # fall back to the looser node-reliable set
        return inliers

    @staticmethod
    def _umeyama(src: np.ndarray, tgt: np.ndarray) -> np.ndarray:
        """Least-squares rigid transform (no scaling) via Umeyama/SVD.

        Returns a 4x4 matrix mapping src onto tgt.
        """
        mu_s = src.mean(axis=0)
        mu_t = tgt.mean(axis=0)
        S = src - mu_s
        T = tgt - mu_t
        H = (S.T @ T) / len(src)
        U, _, Vt = np.linalg.svd(H)
        d = np.sign(np.linalg.det(Vt.T @ U.T))
        D = np.diag([1.0, 1.0, d])
        R = Vt.T @ D @ U.T
        t = mu_t - R @ mu_s
        M = np.eye(4, dtype=np.float64)
        M[:3, :3] = R
        M[:3, 3] = t
        return M


