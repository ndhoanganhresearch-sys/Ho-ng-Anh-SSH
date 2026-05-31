from .common import *
from .models import PipelineContext

# Minimum points in an axial slice before a centre is computed. Matches the
# circle-fit floor in _slice_center (below this it returns the slice mean), so
# both centerline paths gate consistently (C5) instead of 30 vs 5.
MIN_SLICE_POINTS = 12
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

class GeometricLayer:
    def extract_centerline(
        self, context: PipelineContext, section_count: int = 80
    ) -> Tuple[np.ndarray, List[Dict]]:
        pts = context.working_points
        if pts is None: raise RuntimeError("No working_points.")
        pts = validate_xyz(pts)
        c, ax, _e1, _e2 = principal_axes(pts)
        proj = (pts - c) @ ax
        # Bin by equal axial position (not equal point count): count-based
        # splitting clusters all sections in the dense tunnel middle and leaves
        # the sparse ends uncovered, shortening the centerline.
        pmin, pmax = float(proj.min()), float(proj.max())
        edges = np.linspace(pmin, pmax, section_count + 1)
        slot = np.clip(np.searchsorted(edges, proj, side="right") - 1, 0, section_count - 1)
        centers = []
        for s in range(section_count):
            ch = pts[slot == s]
            if len(ch) >= MIN_SLICE_POINTS:
                # Geometric centre via circle fit (robust to uneven sampling),
                # not the mass centroid which zig-zags on real scans.
                centers.append(self._slice_center(ch, ax))
        if len(centers) < 4: raise RuntimeError(f"Only {len(centers)} centers (need >= 4).")
        cl = np.asarray(centers, dtype=np.float64)
        cl = self._despike_centers(cl, ax)   # C1: pull back sparse-ring spikes
        return cl, self._frenet(cl)

    def extract_centerline_iterative(
        self, context: PipelineContext, design_axis: np.ndarray,
        section_count: int = 80, mu: float = 0.03, max_iter: int = 20
    ) -> Tuple[np.ndarray, List[Dict], int]:
        from scipy.interpolate import splev, splprep
        pts = context.working_points
        if pts is None: raise RuntimeError("No working_points.")
        pts = validate_xyz(pts)
        cur = np.asarray(design_axis, dtype=np.float64)
        if cur.ndim != 2 or cur.shape[1] != 3 or len(cur) < 4:
            raise ValueError("design_axis must be (M >= 4, 3).")
        new_ax = cur.copy(); iters = 0
        for it in range(max_iter):
            iters = it + 1; frs = self._frenet(cur); c3d: List[np.ndarray] = []
            # C3: adaptive slice half-thickness from the current axis spacing
            # (was a hardcoded 0.05 m, which assumes metres and a fixed section
            # pitch). Mirrors ParameterLayer._section_epsilon.
            eps = self._axial_eps(cur)
            for fr in frs:
                C, T, N, B = fr["center"], fr["T"], fr["N"], fr["B"]
                mask = np.abs((pts - C) @ T) < eps; sl = pts[mask]
                if len(sl) < 12: continue
                # C2: reuse the LSQ + angular-coverage guard slice centre.
                # _ransac_circle (fixed tol) extrapolated centres metres away on
                # real data (verified: iterative wander 205 m, hook 35 m); the
                # LSQ fit with the partial-arc guard is far more stable.
                c3d.append(self._slice_center(sl, T))
            if len(c3d) < 4: warnings.warn(f"Iter {iters}: only {len(c3d)} centers."); break
            ca = np.asarray(c3d, dtype=np.float64)
            ca = self._despike_centers(ca, ca[-1] - ca[0])   # C1: pull back spikes
            # FIX-1: axis=
            ch = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(ca, axis=0), axis=1))])
            tot = ch[-1]
            if tot < 1e-6: break
            u = ch / tot; _, ui = np.unique(u, return_index=True)
            if len(ui) < 4: break
            try: tck, _ = splprep(ca[ui].T, u=u[ui], s=0, k=3, quiet=True)
            except Exception as e: warnings.warn(f"splprep: {e}"); break
            uf = np.linspace(0, 1, section_count)
            new_ax = np.column_stack(splev(uf, tck)).astype(np.float64)
            # FIX-1: axis=
            chp = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(cur, axis=0), axis=1))])
            tp  = chp[-1]; e_val = float("inf")
            if tp > 1e-6:
                _, uip = np.unique(chp / tp, return_index=True)
                if len(uip) >= 4:
                    try:
                        tp2, _ = splprep(cur[uip].T, u=(chp / tp)[uip], s=0, k=3, quiet=True)
                        pr2   = np.column_stack(splev(uf, tp2)).astype(np.float64)
                        e_val = float(np.mean(np.linalg.norm(new_ax - pr2, axis=1) ** 2))
                    except Exception: pass
            cur = new_ax
            if e_val < mu: break
        return new_ax, self._frenet(new_ax), iters

    def smooth_bspline(self, cl: np.ndarray, sf: float = 0.5) -> np.ndarray:
        """Cosmetic display smoothing of an existing centerline (C6).

        Returns a denser, smoothed polyline for the 3D overlay only. It does NOT
        recompute Frenet frames and downstream analysis (sections, settlement,
        eccentricity) keeps using context.centerline, not this result. Use
        extract_centerline_bspline if you need an analysis-grade smoothed axis
        with matching frames. Resampled at 4x the input control points.
        """
        try:
            from scipy.interpolate import splev, splprep
        except ImportError: return np.asarray(cl, dtype=np.float64)
        pts = np.asarray(cl, dtype=np.float64)
        if len(pts) < 4: raise RuntimeError("Need >= 4 pts.")
        # FIX-1: axis=
        delta = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        keep  = np.concatenate([[True], delta > 1e-10])
        ptsc  = pts[keep]
        if len(ptsc) < 4: return pts
        # FIX-1: axis=
        ch = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(ptsc, axis=0), axis=1))])
        tot = ch[-1]
        if tot < 1e-10: return pts
        try: tck, _ = splprep(ptsc.T, u=ch / tot, s=float(np.clip(sf, 0, 1)) * len(ptsc), k=3, quiet=True)
        except Exception: return pts
        return np.column_stack(splev(np.linspace(0, 1, len(ptsc) * 4), tck)).astype(np.float64)


    def extract_centerline_bspline(
        self, context: PipelineContext,
        section_count: int = 80,
        smooth_factor: float = 0.5,
    ) -> Tuple[np.ndarray, List[Dict]]:
        """B-spline C2 centerline per PDF section 3.4.

        smooth_factor controls the splprep smoothing s = smooth_factor * n_knots.
        It MUST be > 0: with s = 0 the spline interpolates every control point
        (including residual jitter from uneven sampling), which makes the axis
        wander more than the raw centreline (measured on real data: lateral
        wander 0.31 m at s=0 vs 0.002 m at s>=0.1). A small positive default
        smooths out that jitter while still following the tunnel axis.
        """
        from scipy.interpolate import splev, splprep

        pts = context.working_points
        if pts is None:
            raise RuntimeError("No working_points.")
        pts = validate_xyz(pts)

        c, ax, _e1, _e2 = principal_axes(pts)
        proj = (pts - c) @ ax
        # Bin by equal axial position (not equal point count): count-based
        # splitting clusters key points in the dense tunnel middle and leaves the
        # sparse ends uncovered, shortening the fitted B-spline centerline.
        n_chunks = max(section_count * 2, 40)
        pmin, pmax = float(proj.min()), float(proj.max())
        edges = np.linspace(pmin, pmax, n_chunks + 1)
        slot = np.clip(np.searchsorted(edges, proj, side="right") - 1, 0, n_chunks - 1)
        # Geometric centre per chunk via circle fit (robust to uneven
        # sampling), not the mass centroid which zig-zags on real scans.
        # Also record how far the circle-fit centre sits from the chunk mean:
        # for a full ring they coincide, but a one-sided partial arc (typical
        # of the sparse first/last chunks) makes the fit extrapolate outward,
        # which is the source of the B-spline 'hook' at the ends.
        centers_list = []
        fitdev_list = []
        for s in range(n_chunks):
            chunk = pts[slot == s]
            if len(chunk) < MIN_SLICE_POINTS:
                continue
            ctr = self._slice_center(chunk, ax)
            centers_list.append(ctr)
            fitdev_list.append(float(np.linalg.norm(ctr - chunk.mean(axis=0))))
        centers = np.asarray(centers_list, dtype=np.float64)
        fitdev = np.asarray(fitdev_list, dtype=np.float64)
        if len(centers) < 4:
            raise RuntimeError(f"Only {len(centers)} raw centers (need >= 4).")
        centers = self._despike_centers(centers, ax)   # C1: kill lateral spikes

        # Trim contiguous END chunks whose fit deviates from the mean far more
        # than the interior (partial-arc extrapolation). Full-ring sections
        # (incl. genuinely curved tunnels) have tiny fitdev, so this never
        # trims them and axial coverage is preserved.
        if len(centers) >= 10:
            q = len(centers) // 5
            interior_med = float(np.median(fitdev[q:len(centers) - q]))
            tol = max(0.30, interior_med + 0.50)
            lo = 0
            while lo < len(centers) // 4 and fitdev[lo] > tol:
                lo += 1
            hi = len(centers)
            while hi > len(centers) - len(centers) // 4 and fitdev[hi - 1] > tol:
                hi -= 1
            if hi - lo >= 4:
                centers = centers[lo:hi]

        key_pts = centers
        ch = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(key_pts, axis=0), axis=1))])
        tot = ch[-1]
        if tot < 1e-6:
            raise RuntimeError("Centerline has zero length.")
        u_norm = ch / tot
        _, ui = np.unique(u_norm, return_index=True)
        if len(ui) < 4:
            raise RuntimeError("Not enough unique knot positions for B-spline.")

        s_val = smooth_factor * len(ui)
        try:
            tck, _ = splprep(key_pts[ui].T, u=u_norm[ui], s=s_val, k=3, quiet=True)
        except Exception as e:
            warnings.warn(f"B-spline fit failed ({e}), falling back to linear.")
            return self.extract_centerline(context, section_count)

        u_fine = np.linspace(0.0, 1.0, section_count)
        cl = np.column_stack(splev(u_fine, tck)).astype(np.float64)
        return cl, self._frenet(cl)

    def generate_frenet_planes(self, fr: List[Dict]) -> List[Dict]:
        """Return gravity-aligned section frames.

        The frames are already gravity-anchored when built by _frenet (T along
        the axis, N = vertical projected orthogonal to T, B = N x T). If valid
        frames are passed in they are returned as-is; if the centres are present
        the frames are recomputed from them so the call is never a silent no-op.
        """
        if fr and all("center" in f and "T" in f and "N" in f and "B" in f for f in fr):
            centers = np.asarray([f["center"] for f in fr], dtype=np.float64)
            if len(centers) >= 2:
                return self._frenet(centers)
        return fr

    def _frenet(self, cl: np.ndarray) -> List[Dict]:
        """Gravity-anchored section frames (twist-free about the axis).

        A tunnel does not twist about its longitudinal axis, so every cross
        section should share the same "up" direction. Bishop parallel
        transport (used previously) accumulates roll from tangent noise and
        on real data wound the frame through ~359 deg along the drive,
        rotating the sections relative to each other ("twisted" sections).

        Here each frame is anchored directly to gravity: the in-section
        vertical N is the global Z projected orthogonal to the local tangent
        T, and B = N x T completes the right-handed basis. This removes the
        cumulative twist entirely. For near-vertical tangents (|Tz| ~ 1, a
        steeply plunging tunnel) Z is degenerate in-plane, so we fall back to
        global X as the reference up. The method name is kept for backward
        compatibility with existing callers.
        """
        pts = np.asarray(cl, dtype=np.float64)
        n = len(pts)
        if n < 2: raise RuntimeError("Frame: need >= 2 pts.")

        T = self._tangents(pts)
        Z_global = np.array([0.0, 0.0, 1.0])
        X_global = np.array([1.0, 0.0, 0.0])
        frames: List[Dict] = []
        for i in range(n):
            Ti = T[i]
            ref = X_global if abs(float(Ti[2])) > 0.9999 else Z_global
            # Vertical in-section direction (gravity 'up'), orthogonal to T.
            vert = ref - float(ref @ Ti) * Ti
            nrm = float(np.linalg.norm(vert))
            if nrm < 1e-9:
                vert = X_global - float(X_global @ Ti) * Ti
                nrm = float(np.linalg.norm(vert))
            vert = vert / (nrm + 1e-12)
            # Convention used by all consumers: section 2D x = d.N (lateral,
            # horizontal), section 2D z = d.B (vertical). So B is the vertical
            # (up) axis and N is the in-plane lateral axis. (Previously N was
            # set vertical and B lateral, which rotated every cross-section 90
            # deg and mislabelled crown/floor.)
            Bi = vert                                  # vertical, up
            Ni = _unit(np.cross(Bi, Ti))               # lateral, horizontal
            frames.append({"center": pts[i], "T": Ti, "N": Ni, "B": Bi})
        return frames
    @staticmethod
    def _tangents(pts: np.ndarray) -> np.ndarray:
        n = len(pts); T = np.empty_like(pts)
        T[1:-1] = pts[2:] - pts[:-2]; T[0] = pts[1] - pts[0]; T[-1] = pts[-1] - pts[-2]
        norms = np.linalg.norm(T, axis=1, keepdims=True)
        tiny = norms.ravel() < 1e-10
        for i in np.where(tiny)[0]: nb = i - 1 if i > 0 else i + 1; T[i] = T[nb]
        norms = np.linalg.norm(T, axis=1, keepdims=True); norms = np.where(norms < 1e-10, 1.0, norms)
        return T / norms

    @staticmethod
    def _axial_eps(axis_pts: np.ndarray, default: float = 0.05) -> float:
        """Adaptive slice half-thickness from centerline spacing (C3).

        Uses ~0.55x the median spacing between consecutive axis points so the
        slice is thick enough to catch a full ring but thin enough not to mix
        neighbouring sections. Falls back to a small default when the axis is
        degenerate. Mirrors ParameterLayer._section_epsilon.
        """
        a = np.asarray(axis_pts, dtype=np.float64)
        if a.ndim != 2 or len(a) < 2:
            return default
        d = np.linalg.norm(np.diff(a, axis=0), axis=1)
        d = d[np.isfinite(d) & (d > 1e-6)]
        if len(d) == 0:
            return default
        return float(np.clip(np.median(d) * 0.55, default, 0.5))

    @staticmethod
    def _despike_centers(centers: np.ndarray, axis: np.ndarray) -> np.ndarray:
        """Pull back slice centres that jump sideways off the local trend (C1).

        Sparse rings at segment boundaries / tunnel ends fit a circle whose
        centre extrapolates 1-3 m laterally even though the radial RMS stays
        small, so the per-slice angular guard cannot catch them. Here each
        centre is compared to the median of its neighbours in the plane
        orthogonal to the axis; if its lateral offset from that local median
        exceeds a robust threshold (median + 3*MAD, floored at 0.25 m) it is
        replaced by the neighbour median. This is curvature-preserving: a
        genuinely curved tunnel moves smoothly so no point is flagged.
        """
        cl = np.asarray(centers, dtype=np.float64)
        n = len(cl)
        if n < 5:
            return cl
        a = np.asarray(axis, dtype=np.float64)
        a = a / (np.linalg.norm(a) + 1e-12)
        out = cl.copy()
        win = max(2, n // 20)
        lat = np.empty(n)
        meds = np.empty((n, 3))
        for i in range(n):
            lo = max(0, i - win); hi = min(n, i + win + 1)
            nb = np.delete(cl[lo:hi], i - lo, axis=0)
            med = np.median(nb, axis=0)
            meds[i] = med
            off = cl[i] - med
            off = off - (off @ a) * a            # lateral component only
            lat[i] = float(np.linalg.norm(off))
        mad = float(np.median(np.abs(lat - np.median(lat)))) + 1e-9
        thr = max(0.25, float(np.median(lat)) + 3.0 * 1.4826 * mad)
        spike = lat > thr
        for i in np.where(spike)[0]:
            # keep the axial position, replace only the lateral coordinates
            proj = (cl[i] - meds[i]) @ a
            out[i] = meds[i] + proj * a
        return out

    def _slice_center(self, slice_pts: np.ndarray, axis: np.ndarray) -> np.ndarray:
        """Robust geometric centre of an axial slice.

        The plain centroid (mean) of a slice is pulled toward dense regions
        because tunnel scans are unevenly sampled (gaps on the floor, occluded
        zones, clutter). On real data this produced lateral jumps up to ~1.7 m
        between slices (a zig-zag centreline). Fitting a circle in the plane
        orthogonal to the tunnel axis recovers the geometric centre instead of
        the mass centroid, cutting the lateral jump ~3x. Falls back to the mean
        when there are too few points or the fit fails.
        """
        if len(slice_pts) < 12:
            return slice_pts.mean(axis=0)
        c = slice_pts.mean(axis=0)
        # In-plane basis orthogonal to the axis.
        a = np.asarray(axis, dtype=np.float64)
        a = a / (np.linalg.norm(a) + 1e-12)
        ref = np.array([0.0, 0.0, 1.0]) if abs(a[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        e1 = ref - (ref @ a) * a
        e1 = e1 / (np.linalg.norm(e1) + 1e-12)
        e2 = np.cross(a, e1)
        d = slice_pts - c
        p2 = np.column_stack([d @ e1, d @ e2])
        # Angular coverage guard: an end-of-tunnel slice often holds only a
        # one-sided arc (sparse, partial ring). Circle-fitting a partial arc
        # is ill-conditioned and extrapolates the centre OUTWARD, which is
        # exactly the B-spline 'hook' seen at the two ends. If the points do
        # not wrap around enough of the ring, fall back to the mean (which
        # stays inside the points and cannot curl outward).
        ang = np.arctan2(p2[:, 1], p2[:, 0])
        occ = np.zeros(36, dtype=bool)
        occ[np.clip(((ang + np.pi) / (2 * np.pi) * 36).astype(int), 0, 35)] = True
        # Angular-coverage guard (C1). A one-sided arc makes the circle fit
        # extrapolate the centre outward by 1-3 m even when the radial RMS is
        # small, which is the source of the end 'hook'. We also require the arc
        # to span a wide angle (not just many bins on one side): a partial arc
        # clustered in half the circle has a small angular span and is rejected.
        n_occ = int(occ.sum())
        span = float(ang.max() - ang.min())
        wrapped = (span > np.deg2rad(220)) or (n_occ >= 24)
        if n_occ < 20 or not wrapped:   # too little / one-sided coverage
            return c
        # Least-squares circle fit (Kasa). On real tunnel rings this is far
        # more stable than RANSAC with a fixed tolerance, which on large-radius
        # rings produced centres metres away (verified: LSQ jump max ~0.5 m vs
        # RANSAC ~12 m). Reject the fit only if the centre lands implausibly
        # far outside the in-plane point spread.
        try:
            c2d, _r = self._lsq_c(p2)
        except Exception:
            return c
        if not np.all(np.isfinite(c2d)):
            return c
        spread = float(np.linalg.norm(p2, axis=1).max()) + 1e-9
        if np.linalg.norm(c2d) > spread:
            return c
        return c + float(c2d[0]) * e1 + float(c2d[1]) * e2

    @staticmethod
    def _lsq_c(pts):
        x, y = pts[:, 0], pts[:, 1]
        A = np.column_stack([x, y, np.ones(len(pts))]); b = x ** 2 + y ** 2
        res, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
        cx, cy = res[0] / 2, res[1] / 2
        return np.array([cx, cy]), float(np.sqrt(res[2] + cx ** 2 + cy ** 2))


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

