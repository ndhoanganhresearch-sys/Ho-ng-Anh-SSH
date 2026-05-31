from .common import *
from .models import PipelineContext
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
        c = pts.mean(axis=0)
        ev, vecs = np.linalg.eigh(np.cov((pts - c).T))
        ax = vecs[:, np.argmax(ev)]
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
            if len(ch) >= 30:
                # Geometric centre via circle fit (robust to uneven sampling),
                # not the mass centroid which zig-zags on real scans.
                centers.append(self._slice_center(ch, ax))
        if len(centers) < 4: raise RuntimeError(f"Only {len(centers)} centers (need >= 4).")
        cl = np.asarray(centers, dtype=np.float64)
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
            for fr in frs:
                C, T, N, B = fr["center"], fr["T"], fr["N"], fr["B"]
                mask = np.abs((pts - C) @ T) < 0.05; sl = pts[mask]
                if len(sl) < 10: continue
                d = sl - C; p2 = np.column_stack([d @ N, d @ B])
                try: c2d, _, _ = self._ransac_circle(p2)
                except Exception: continue
                c3d.append(C + float(c2d[0]) * N + float(c2d[1]) * B)
            if len(c3d) < 4: warnings.warn(f"Iter {iters}: only {len(c3d)} centers."); break
            ca = np.asarray(c3d, dtype=np.float64)
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
        window_size: int = 5,
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

        c = pts.mean(axis=0)
        ev, vecs = np.linalg.eigh(np.cov((pts - c).T))
        ax = vecs[:, np.argmax(ev)]
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
        centers = np.asarray(
            [self._slice_center(pts[slot == s], ax) for s in range(n_chunks)
             if int((slot == s).sum()) >= 5],
            dtype=np.float64,
        )
        if len(centers) < 4:
            raise RuntimeError(f"Only {len(centers)} raw centers (need >= 4).")

        ws = max(3, min(window_size, len(centers) // 4))
        curvatures = np.zeros(len(centers))
        for i in range(ws, len(centers) - ws):
            v1 = centers[i] - centers[i - ws]
            v2 = centers[i + ws] - centers[i]
            n1 = float(np.linalg.norm(v1))
            n2 = float(np.linalg.norm(v2))
            if n1 > 1e-9 and n2 > 1e-9:
                cos_a = float(np.clip(np.dot(v1 / n1, v2 / n2), -1.0, 1.0))
                curvatures[i] = 1.0 - cos_a

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
    def _perp(t: np.ndarray) -> np.ndarray:
        cands = [np.array([0., 0., 1.]), np.array([0., 1., 0.]), np.array([1., 0., 0.])]
        seed = cands[int(np.argmin([abs(float(c @ t)) for c in cands]))]
        return _unit(seed - (seed @ t) * t)

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

    def _ransac_circle(
        self, pts2d: np.ndarray, n_iter: int = 200, tol: float = 0.02
    ) -> Tuple[np.ndarray, float, np.ndarray]:
        K = len(pts2d)
        if K < 3: raise ValueError("Need >= 3 pts.")
        bc = pts2d.mean(axis=0)
        # FIX-1 & 2: axis=1 for norm, bn=-1
        br = float(np.median(np.linalg.norm(pts2d - bc, axis=1)))
        bm = np.ones(K, dtype=bool); bn = -1
        rng = np.random.default_rng(42)
        for _ in range(n_iter):
            idx = rng.choice(K, 3, replace=False)
            try: c, r = self._c3(pts2d[idx[0]], pts2d[idx[1]], pts2d[idx[2]])
            except Exception: continue
            # FIX-1: axis=1
            mask = np.abs(np.linalg.norm(pts2d - c, axis=1) - r) < tol
            ni   = int(mask.sum())
            if ni > bn:
                bn = ni; bm = mask
                inl = pts2d[mask]
                if len(inl) >= 3: bc, br = self._lsq_c(inl)
        return bc, br, bm

    @staticmethod
    def _c3(p1, p2, p3):
        ax, ay = p1; bx, by = p2; cx, cy = p3
        D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(D) < 1e-10: raise ValueError("Collinear.")
        ux = ((ax ** 2 + ay ** 2) * (by - cy) + (bx ** 2 + by ** 2) * (cy - ay) + (cx ** 2 + cy ** 2) * (ay - by)) / D
        uy = ((ax ** 2 + ay ** 2) * (cx - bx) + (bx ** 2 + by ** 2) * (ax - cx) + (cx ** 2 + cy ** 2) * (bx - ax)) / D
        c = np.array([ux, uy]); return c, float(np.linalg.norm(p1 - c))

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

