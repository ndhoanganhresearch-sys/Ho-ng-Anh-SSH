"""
ifc_exporter.py - Real IFC4 export using ifcopenshell 0.8+.
Per PDF section 3.6.
"""
from .common import *
from .models import PipelineContext, SectionGeometry
from pathlib import Path
from datetime import datetime


class TunnelIFCExporter:
    """Export tunnel analysis results to IFC4 format."""

    def export_ifc(self, context: PipelineContext, out_path: str,
                   project_name: str = "Tunnel Analysis",
                   engineer: str = "CBNU Smart Structure Lab",
                   schema: str = "IFC4",
                   wall_thickness: float = 0.3,
                   include_components: bool = False) -> str:
        try:
            import ifcopenshell
            import ifcopenshell.api
        except ImportError:
            raise RuntimeError("ifcopenshell required: pip install ifcopenshell")

        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # IFC4 keeps maximum viewer compatibility; IFC4X3* adds IfcAlignment
        # for the centerline (infrastructure-standard linear referencing).
        schema = str(schema or "IFC4").upper()
        is_4x3 = schema.startswith("IFC4X3")
        ifc = ifcopenshell.file(schema=schema)

        # Project
        project = ifcopenshell.api.run("root.create_entity", ifc,
                                        ifc_class="IfcProject", name=project_name)
        # Coordinates are written in METRES, so assign an explicit metre length
        # unit. ifcopenshell's default assign_unit() uses MILLIMETRE, which made
        # viewers shrink the model 1000x (radius 6.7 m read as 6.7 mm).
        _m_unit = ifcopenshell.api.run("unit.add_si_unit", ifc, unit_type="LENGTHUNIT")
        ifcopenshell.api.run("unit.assign_unit", ifc, units=[_m_unit])
        ctx3d = ifcopenshell.api.run("context.add_context", ifc, context_type="Model")
        body_ctx = ifcopenshell.api.run("context.add_context", ifc,
                                         context_type="Model",
                                         context_identifier="Body",
                                         target_view="MODEL_VIEW",
                                         parent=ctx3d)

        # Hierarchy: Project > Site > Building > Storey
        site = ifcopenshell.api.run("root.create_entity", ifc,
                                     ifc_class="IfcSite", name="Osong Test Site")
        building = ifcopenshell.api.run("root.create_entity", ifc,
                                         ifc_class="IfcBuilding", name="Tunnel Structure")
        storey = ifcopenshell.api.run("root.create_entity", ifc,
                                       ifc_class="IfcBuildingStorey", name="Tunnel Level")

        # API 0.8+: products is a list
        ifcopenshell.api.run("aggregate.assign_object", ifc,
                              products=[site], relating_object=project)
        ifcopenshell.api.run("aggregate.assign_object", ifc,
                              products=[building], relating_object=site)
        ifcopenshell.api.run("aggregate.assign_object", ifc,
                              products=[storey], relating_object=building)

        # Set True once the continuous deformation-following lining shell is
        # built, so the per-section solid slices below are skipped (no overlap).
        mesh_built = False

        # Centerline: IfcAlignment (IFC4X3 infrastructure standard) or
        # IfcAnnotation (IFC4 fallback). Both carry the same Curve3D polyline.
        cl = context.centerline
        if cl is not None and len(cl) >= 2:
            pts_3d = [ifc.createIfcCartesianPoint(
                (float(p[0]), float(p[1]), float(p[2]))) for p in cl]
            polyline = ifc.createIfcPolyline(pts_3d)
            shape = ifc.createIfcShapeRepresentation(
                body_ctx, "Axis", "Curve3D", [polyline])
            prod_def = ifc.createIfcProductDefinitionShape(None, None, [shape])
            cl_class = "IfcAlignment" if is_4x3 else "IfcAnnotation"
            cl_entity = ifcopenshell.api.run("root.create_entity", ifc,
                                              ifc_class=cl_class,
                                              name="Tunnel Centerline")
            cl_entity.Representation = prod_def
            ifcopenshell.api.run("spatial.assign_container", ifc,
                                  products=[cl_entity], relating_structure=storey)

            # Continuous tunnel lining body. Preferred: a tessellated shell that
            # FOLLOWS the measured deformation (loft of the real per-section
            # rings, status-coloured). Fallback: a uniform median-radius
            # swept-disk tube when the loft cannot be built (no frames / too few
            # rings). When the deformation shell is built, the per-section solid
            # slices below are skipped to avoid overlapping (Z-fighting) bodies.
            try:
                lining_shape = self._deformed_lining_facetset(
                    ifc, body_ctx, context, float(wall_thickness))
            except Exception as e:
                lining_shape = None
                warnings.warn(f"Deformed lining mesh skipped: {e}")
            if lining_shape is not None:
                lining = ifcopenshell.api.run("root.create_entity", ifc,
                                              ifc_class="IfcBuildingElementProxy",
                                              name="Tunnel Lining (measured)")
                lining.Representation = ifc.createIfcProductDefinitionShape(None, None, [lining_shape])
                ifcopenshell.api.run("spatial.assign_container", ifc,
                                      products=[lining], relating_structure=storey)
                mesh_built = True
            else:
                try:
                    radii = [float(sc.radius_fit) for sc in context.sections
                             if np.isfinite(sc.radius_fit) and sc.radius_fit > 0]
                    is_circle = str(getattr(context, "tunnel_profile", "Circle")).lower().startswith("circle")
                    if is_circle and len(radii) >= 1 and len(cl) >= 3:
                        bore_R = float(np.median(radii))
                        directrix = ifc.createIfcPolyline(pts_3d)
                        inner_R = max(0.0, bore_R - float(wall_thickness))
                        inner_arg = inner_R if inner_R > 1e-6 else None
                        disk = ifc.createIfcSweptDiskSolid(directrix, bore_R, inner_arg, None, None)
                        bore = ifcopenshell.api.run("root.create_entity", ifc,
                                                    ifc_class="IfcBuildingElementProxy",
                                                    name="Tunnel Bore")
                        bshape = ifc.createIfcShapeRepresentation(body_ctx, "Body", "AdvancedSweptSolid", [disk])
                        bore.Representation = ifc.createIfcProductDefinitionShape(None, None, [bshape])
                        self._apply_color(ifc, disk, (0.62, 0.66, 0.71), name="BoreSurface")
                        ifcopenshell.api.run("spatial.assign_container", ifc,
                                              products=[bore], relating_structure=storey)
                except Exception as e:
                    warnings.warn(f"Tunnel bore swept solid skipped: {e}")

        # Sections as IfcBuildingElementProxy with placement + solid geometry
        frames = context.frenet_frames or []
        profile = getattr(context, "tunnel_profile", "Circle")
        # Slice thickness = median chainage spacing so adjacent solid slices
        # roughly tile the bore without overlapping; fall back to 0.3 m.
        chainages = [float(sc.chainage) for sc in context.sections
                     if sc.center_3d is not None and np.isfinite(sc.chainage)]
        slice_thk = 0.3
        if len(chainages) >= 2:
            diffs = np.diff(np.sort(np.asarray(chainages, dtype=float)))
            diffs = diffs[diffs > 1e-6]
            if len(diffs):
                slice_thk = float(np.clip(np.median(diffs) * 0.9, 0.05, 2.0))
        for i, sec in enumerate(context.sections):
            if sec.center_3d is None:
                continue
            name = f"Section_{i+1:03d}_Ch{sec.chainage:.2f}m"
            elem = ifcopenshell.api.run("root.create_entity", ifc,
                                         ifc_class="IfcBuildingElementProxy",
                                         name=name)
            # Place the section in space using its Frenet frame (T=local Z
            # along the tunnel axis, N=local X) and draw the measured ring in
            # the local section plane so the proxy is visible/located in a BIM
            # viewer instead of collapsing to the origin without geometry.
            fr = frames[i] if i < len(frames) else None
            # When the continuous deformation shell carries the geometry, keep
            # the per-section proxies as DATA-only carriers (property sets) and
            # skip their solid slice so the two bodies do not overlap.
            if mesh_built:
                placement, shape = None, None
            else:
                placement, shape = self._section_placement_shape(ifc, body_ctx, sec, fr, profile, thickness=slice_thk, wall_thickness=wall_thickness)
            if placement is not None:
                elem.ObjectPlacement = placement
            if shape is not None:
                elem.Representation = ifc.createIfcProductDefinitionShape(None, None, [shape])
                # Colour the slice by assessment: red = clearance violation,
                # amber = high ovality (>= 1%), green = OK.
                if sec.clearance_violation:
                    rgb = (0.86, 0.15, 0.15)
                elif np.isfinite(sec.ovality) and sec.ovality >= 1.0:
                    rgb = (0.85, 0.47, 0.04)
                else:
                    rgb = (0.02, 0.59, 0.41)
                if shape.Items:
                    self._apply_color(ifc, shape.Items[0], rgb, name="SectionStatus")
            # Property set
            pset = ifcopenshell.api.run("pset.add_pset", ifc,
                                         product=elem,
                                         name="TunnelSectionProperties")
            props = {}
            if np.isfinite(sec.chainage):     props["Chainage_m"]       = float(sec.chainage)
            if np.isfinite(sec.H1):           props["ClearHeight_H1_m"] = float(sec.H1)
            if np.isfinite(sec.W1):           props["ClearWidth_W1_m"]  = float(sec.W1)
            if np.isfinite(sec.ovality):      props["Ovality_pct"]      = float(sec.ovality)
            if np.isfinite(sec.eccentricity): props["Eccentricity_mm"]  = float(sec.eccentricity)
            if np.isfinite(sec.radius_fit):   props["RadiusFit_m"]      = float(sec.radius_fit)
            props["ClearanceViolation"] = bool(sec.clearance_violation)
            if np.isfinite(sec.min_clearance_dist):
                props["MinClearance_m"] = float(sec.min_clearance_dist)
            ifcopenshell.api.run("pset.edit_pset", ifc, pset=pset, properties=props)
            ifcopenshell.api.run("spatial.assign_container", ifc,
                                  products=[elem], relating_structure=storey)

        # Global parameters on project
        params = context.parameters
        if params:
            pset_g = ifcopenshell.api.run("pset.add_pset", ifc,
                                           product=project,
                                           name="TunnelGlobalParameters")
            clean = {k: float(v) for k, v in params.items()
                     if isinstance(v, (int, float)) and np.isfinite(float(v))}
            if clean:
                ifcopenshell.api.run("pset.edit_pset", ifc, pset=pset_g, properties=clean)

        # Detected non-structural components from auto_denoise (cable/light/
        # person/wall-cable counts). Recorded on the project so the IFC keeps
        # a record of what was identified and removed during cleaning.
        ds = getattr(context, "denoise_stats", None) or {}
        comp = {
            "CableSegments":    ds.get("n_cable"),
            "WallCableSegments": ds.get("n_wall_cable"),
            "LightFixtures":    ds.get("n_light"),
            "PersonsVehicles":  ds.get("n_person"),
            "RadialOutliers":   ds.get("n_radial"),
            "PointsRemoved":    ds.get("n_removed"),
        }
        comp = {k: int(v) for k, v in comp.items() if isinstance(v, (int, float))}
        if comp:
            pset_c = ifcopenshell.api.run("pset.add_pset", ifc,
                                           product=project,
                                           name="TunnelComponents")
            ifcopenshell.api.run("pset.edit_pset", ifc, pset=pset_c, properties=comp)

        # When the scan carries per-point semantic labels (FY387 / STSD), also
        # record the GROUND-TRUTH point count per class id. This is exact
        # (unlike the heuristic auto_denoise counts above) but class-id meaning
        # depends on the dataset legend, so it is stored as Class_<id> and kept
        # in a separate pset to avoid implying a fixed naming.
        try:
            labels = context.working_labels() if hasattr(context, "working_labels") else None
        except Exception:
            labels = None
        if labels is not None and len(labels):
            lab = np.asarray(labels).astype(np.int64).ravel()
            uniq, cnt = np.unique(lab, return_counts=True)
            by_label = {f"Class_{int(u)}": int(c) for u, c in zip(uniq, cnt)}
            if by_label:
                pset_l = ifcopenshell.api.run("pset.add_pset", ifc,
                                               product=project,
                                               name="TunnelComponentsByLabel")
                ifcopenshell.api.run("pset.edit_pset", ifc, pset=pset_l, properties=by_label)

        # Optionally model the detected non-structural objects (cables, lights,
        # people) as separate coloured proxies, clustered into discrete items.
        if include_components:
            self._export_components(ifc, body_ctx, storey, context)

        # Atomic write: serialise to a temp file in the same directory, then
        # replace the target. A crash or disk-full mid-write never leaves a
        # truncated/corrupt .ifc at the final path.
        import os as _os
        tmp = path.with_name(path.name + ".tmp")
        try:
            ifc.write(str(tmp))
            _os.replace(str(tmp), str(path))
        except Exception:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
            raise
        return str(path)

    def _export_components(self, ifc, body_ctx, storey, context):
        """Model detected non-structural objects as shape-appropriate IFC
        proxies: cables as thin swept-disk TUBES following the cluster's own
        axis (they are long and thin, not boxes), lights/people as small boxes.
        Clusters whose bounding box is implausibly large for the class are
        dropped (usually shell points misclassified). Safe no-op with no data.
        """
        import numpy as _np
        import ifcopenshell, ifcopenshell.api
        comp = getattr(context, 'component_points', None) or {}
        colours = {'cable': (0.90, 0.10, 0.10),
                   'light': (0.98, 0.85, 0.10),
                   'person': (0.10, 0.45, 0.95)}
        # Max bounding-box diagonal (m) a single object of each class may span;
        # bigger clusters are misclassified lining and are skipped.
        max_diag = {'cable': 60.0, 'light': 1.5, 'person': 2.5}
        try:
            from sklearn.cluster import DBSCAN as _DBSCAN
            have_db = True
        except Exception:
            have_db = False
        n_made = 0
        for cls, pts in comp.items():
            arr = _np.asarray(pts, dtype=float) if pts is not None else _np.empty((0, 3))
            if arr.ndim != 2 or len(arr) < 5:
                continue
            if have_db:
                eps = 0.4 if cls == 'cable' else 0.25
                labels = _DBSCAN(eps=eps, min_samples=5).fit(arr).labels_
                groups = [arr[labels == c] for c in sorted(set(labels.tolist())) if c != -1]
            else:
                groups = [arr]
            rgb = colours.get(cls, (0.6, 0.6, 0.6))
            diag_cap = max_diag.get(cls, 3.0)
            for gi, g in enumerate(groups):
                if len(g) < 5:
                    continue
                ext = g.max(axis=0) - g.min(axis=0)
                if float(_np.linalg.norm(ext)) > diag_cap:
                    continue  # implausibly large for this class -> skip
                if cls == 'cable':
                    shape = self._cable_tube_shape(ifc, body_ctx, g)
                    placement = None
                else:
                    placement, shape = self._box_shape(ifc, body_ctx, g)
                if shape is None:
                    continue
                elem = ifcopenshell.api.run('root.create_entity', ifc,
                                            ifc_class='IfcBuildingElementProxy',
                                            name=f'{cls.capitalize()}_{gi + 1:03d}')
                if placement is not None:
                    elem.ObjectPlacement = placement
                elem.Representation = ifc.createIfcProductDefinitionShape(None, None, [shape])
                if shape.Items:
                    self._apply_color(ifc, shape.Items[0], rgb, name=f'{cls}Colour')
                try:
                    pset = ifcopenshell.api.run('pset.add_pset', ifc, product=elem, name='ComponentClass')
                    ifcopenshell.api.run('pset.edit_pset', ifc, pset=pset,
                                         properties={'Class': cls, 'PointCount': int(len(g))})
                except Exception:
                    pass
                ifcopenshell.api.run('spatial.assign_container', ifc,
                                     products=[elem], relating_structure=storey)
                n_made += 1
        return n_made

    @staticmethod
    def _cable_tube_shape(ifc, body_ctx, g):
        """Swept-disk tube along the cluster axis (PCA dominant direction),
        ordered by projection so the directrix is monotonic. Radius from the
        transverse spread. Returns a ShapeRepresentation or None.
        """
        import numpy as _np
        if len(g) < 5:
            return None
        c = g.mean(axis=0)
        ev, vec = _np.linalg.eigh(_np.cov((g - c).T))
        axis = vec[:, int(_np.argmax(ev))]
        t = (g - c) @ axis
        order = _np.argsort(t)
        gs = g[order]; ts = t[order]
        # transverse radius = median distance from the axis, floored
        d = gs - c
        perp = d - _np.outer(d @ axis, axis)
        r = float(_np.median(_np.linalg.norm(perp, axis=1)))
        r = float(min(max(r, 0.02), 0.30))
        # thin out directrix to a handful of waypoints to keep it monotonic/clean
        n_way = int(min(12, max(2, len(gs) // 20)))
        idx = _np.linspace(0, len(gs) - 1, n_way).astype(int)
        way = gs[idx]
        # ensure distinct consecutive points
        pts3d = [way[0]]
        for q in way[1:]:
            if _np.linalg.norm(q - pts3d[-1]) > 1e-3:
                pts3d.append(q)
        if len(pts3d) < 2:
            return None
        directrix = ifc.createIfcPolyline([
            ifc.createIfcCartesianPoint((float(q[0]), float(q[1]), float(q[2]))) for q in pts3d])
        try:
            disk = ifc.createIfcSweptDiskSolid(directrix, r, None, None, None)
        except Exception:
            return None
        return ifc.createIfcShapeRepresentation(body_ctx, 'Body', 'AdvancedSweptSolid', [disk])

    @staticmethod
    def _box_shape(ifc, body_ctx, g):
        """Axis-aligned box solid at the cluster centroid (lights/people)."""
        import numpy as _np
        ctr = g.mean(axis=0)
        ext = g.max(axis=0) - g.min(axis=0)
        dx = float(max(ext[0], 0.05)); dy = float(max(ext[1], 0.05)); dz = float(max(ext[2], 0.05))
        loc = ifc.createIfcCartesianPoint((float(ctr[0]), float(ctr[1]), float(ctr[2]) - dz / 2.0))
        a2p = ifc.createIfcAxis2Placement3D(loc, None, None)
        placement = ifc.createIfcLocalPlacement(None, a2p)
        origin2d = ifc.createIfcCartesianPoint((0.0, 0.0))
        pos2d = ifc.createIfcAxis2Placement2D(origin2d, None)
        prof = ifc.createIfcRectangleProfileDef('AREA', None, pos2d, dx, dy)
        solid = ifc.createIfcExtrudedAreaSolid(prof, None, ifc.createIfcDirection((0.0, 0.0, 1.0)), dz)
        shape = ifc.createIfcShapeRepresentation(body_ctx, 'Body', 'SweptSolid', [solid])
        return placement, shape
    @staticmethod
    def _apply_color(ifc, item, rgb, name="Color"):
        """Attach an RGB surface style to a geometry item (IFC4).

        rgb is a 3-tuple in 0..1. Builds IfcSurfaceStyleRendering ->
        IfcSurfaceStyle -> IfcStyledItem so BIM viewers shade the element by
        its assessment colour (gray bore, green/amber/red sections).
        """
        try:
            r, g, b = (float(rgb[0]), float(rgb[1]), float(rgb[2]))
            col = ifc.createIfcColourRgb(name, r, g, b)
            rendering = ifc.createIfcSurfaceStyleRendering(
                col, 0.0, None, None, None, None, None, None, "FLAT")
            style = ifc.createIfcSurfaceStyle(name, "BOTH", [rendering])
            ifc.createIfcStyledItem(item, [style], None)
        except Exception as e:
            warnings.warn(f"Surface style skipped: {e}")
    @staticmethod
    def _boundary_polygon(pts_2d, wall_thickness, n_bins=72):
        """Trace the measured cross-section boundary as (outer, inner) polygons.

        Bins the section points by angle about their centroid and takes the
        farthest point per bin as the outer wall, giving a polygon that follows
        the true shape (circle / horseshoe / box) with no shape assumption. The
        inner (void) ring is the outer pulled inward by wall_thickness toward
        the centroid. Returns (outer_xy, inner_xy_or_None) in the local N-B
        plane, or None when there are too few points / bins to form a polygon.
        """
        import numpy as _np
        if pts_2d is None:
            return None
        P = _np.asarray(pts_2d, dtype=float)
        if P.ndim != 2 or P.shape[1] != 2 or len(P) < 24:
            return None
        ctr = P.mean(axis=0)
        d = P - ctr
        ang = _np.arctan2(d[:, 1], d[:, 0])
        rad = _np.hypot(d[:, 0], d[:, 1])
        bins = _np.clip(((ang + _np.pi) / (2 * _np.pi) * n_bins).astype(int), 0, n_bins - 1)
        outer = []
        for b in range(n_bins):
            m = bins == b
            if not m.any():
                continue
            # farthest point in this angular wedge = outer wall sample
            j = _np.where(m)[0][int(_np.argmax(rad[m]))]
            outer.append((float(P[j, 0]), float(P[j, 1])))
        if len(outer) < 8:
            return None
        outer_arr = _np.asarray(outer)
        # Inner ring: shrink each outer vertex toward the centroid by the wall
        # thickness (clamped so the void stays well inside the outer ring).
        ov = outer_arr - ctr
        r = _np.hypot(ov[:, 0], ov[:, 1])
        rmin = float(r.min())
        wt = float(min(wall_thickness, rmin * 0.6))
        inner = None
        if wt > 0.02:
            scale = _np.clip((r - wt) / _np.where(r > 1e-9, r, 1.0), 0.0, 1.0)
            inner_arr = ctr + ov * scale[:, None]
            inner = [(float(x), float(y)) for x, y in inner_arr]
        return [(float(x), float(y)) for x, y in outer_arr], inner
    @staticmethod
    def _deformed_lining_facetset(ifc, body_ctx, context, wall_thickness,
                                  K=48, radial_pct=92.0):
        """Continuous tunnel lining that FOLLOWS the measured deformation.

        Lofts the per-section measured rings into one tessellated hollow shell
        (IfcPolygonalFaceSet): each ring is sampled at K fixed angles from the
        real points (high-percentile radius = outer wall), reconstructed in 3D
        via the section's Frenet N/B axes, then consecutive rings are connected
        into outer + inner surfaces with annular end caps. Faces are bucketed by
        section status so problem bands render red/amber on the grey shell.

        Returns an IfcShapeRepresentation (RepresentationType "Tessellation")
        with up to three coloured face sets sharing one coordinate list, or
        None when fewer than two usable rings exist.
        """
        import numpy as _np
        sections = list(getattr(context, "sections", []) or [])
        frames = list(getattr(context, "frenet_frames", []) or [])
        if len(sections) < 2:
            return None
        wt0 = float(wall_thickness)

        def _u(v):
            n = float(_np.linalg.norm(v)); return v / n if n > 1e-9 else v

        outers, inners, ranks = [], [], []
        centers_ang = _np.linspace(0.0, 2.0 * _np.pi, K, endpoint=False) + (_np.pi / K)
        for i, sec in enumerate(sections):
            P = getattr(sec, "pts_2d", None)
            C = getattr(sec, "center_3d", None)
            fr = frames[i] if i < len(frames) else None
            if P is None or C is None or fr is None:
                continue
            if not all(k in fr for k in ("N", "B")):
                continue
            P = _np.asarray(P, dtype=float)
            if P.ndim != 2 or P.shape[1] != 2 or len(P) < 24:
                continue
            N = _u(_np.asarray(fr["N"], float)); B = _u(_np.asarray(fr["B"], float))
            C = _np.asarray(C, float)
            ctr = P.mean(axis=0)
            d = P - ctr
            ang = (_np.arctan2(d[:, 1], d[:, 0]) + 2 * _np.pi) % (2 * _np.pi)
            rad = _np.hypot(d[:, 0], d[:, 1])
            bins = _np.clip((ang / (2 * _np.pi) * K).astype(int), 0, K - 1)
            r = _np.full(K, _np.nan)
            for b in range(K):
                m = bins == b
                if m.any():
                    r[b] = float(_np.percentile(rad[m], radial_pct))
            good = ~_np.isnan(r)
            if good.sum() < 8:
                continue
            xs = _np.where(good)[0].astype(float)
            r = _np.interp(_np.arange(K, dtype=float), xs, r[good], period=K)
            rmin = float(_np.nanmin(r))
            wt = float(min(wt0, max(rmin * 0.6, 0.02)))
            r_in = _np.clip(r - wt, 0.02, None)
            cos = _np.cos(centers_ang); sin = _np.sin(centers_ang)
            ox = ctr[0] + r * cos;    oy = ctr[1] + r * sin
            ix = ctr[0] + r_in * cos; iy = ctr[1] + r_in * sin
            o3d = C[None, :] + ox[:, None] * N[None, :] + oy[:, None] * B[None, :]
            i3d = C[None, :] + ix[:, None] * N[None, :] + iy[:, None] * B[None, :]
            outers.append(o3d); inners.append(i3d)
            if getattr(sec, "clearance_violation", False):
                ranks.append(2)
            elif _np.isfinite(getattr(sec, "ovality", _np.nan)) and sec.ovality >= 1.0:
                ranks.append(1)
            else:
                ranks.append(0)
        S = len(outers)
        if S < 2:
            return None

        coords = []
        for s in range(S):
            coords.extend([(float(p[0]), float(p[1]), float(p[2])) for p in outers[s]])
            coords.extend([(float(p[0]), float(p[1]), float(p[2])) for p in inners[s]])

        def o(s, j): return s * 2 * K + (j % K) + 1          # 1-based
        def inr(s, j): return s * 2 * K + K + (j % K) + 1

        faces = {0: [], 1: [], 2: []}
        for s in range(S - 1):
            band = max(ranks[s], ranks[s + 1])
            for j in range(K):
                jn = j + 1
                faces[band].append([o(s, j), o(s, jn), o(s + 1, jn), o(s + 1, j)])
                faces[band].append([inr(s, j), inr(s + 1, j), inr(s + 1, jn), inr(s, jn)])
        for j in range(K):                                    # annular end caps
            jn = j + 1
            faces[0].append([o(0, j), inr(0, j), inr(0, jn), o(0, jn)])
            faces[0].append([o(S - 1, j), o(S - 1, jn), inr(S - 1, jn), inr(S - 1, j)])

        pts_list = ifc.createIfcCartesianPointList3D(coords)
        rgb_by_rank = {0: (0.62, 0.66, 0.71), 1: (0.85, 0.47, 0.04), 2: (0.86, 0.15, 0.15)}
        items = []
        for rank, flist in faces.items():
            if not flist:
                continue
            poly_faces = [ifc.createIfcIndexedPolygonalFace([int(x) for x in f]) for f in flist]
            fs = ifc.createIfcPolygonalFaceSet(pts_list, None, poly_faces, None)
            TunnelIFCExporter._apply_color(ifc, fs, rgb_by_rank[rank], name="LiningStatus")
            items.append(fs)
        if not items:
            return None
        return ifc.createIfcShapeRepresentation(body_ctx, "Body", "Tessellation", items)

    @staticmethod
    def _section_placement_shape(ifc, body_ctx, sec, fr, profile, thickness=0.3, wall_thickness=0.3):
        """Build (IfcLocalPlacement, IfcShapeRepresentation) for a section.

        Produces a SOLID slice (IfcExtrudedAreaSolid) of the measured profile,
        extruded by ``thickness`` along the local axis so the section is a
        visible 3D body in a BIM viewer, not just an outline. Falls back to a
        Curve3D ring polyline when no profile dimensions are available.
        """
        import numpy as _np
        import math as _math
        C = _np.asarray(sec.center_3d, dtype=float)
        if fr is not None and all(k in fr for k in ("T", "N", "B")):
            T = _np.asarray(fr["T"], dtype=float)
            N = _np.asarray(fr["N"], dtype=float)
        else:
            T = _np.array([0.0, 1.0, 0.0]); N = _np.array([1.0, 0.0, 0.0])
        def _unit3(v):
            n = float(_np.linalg.norm(v))
            return v / n if n > 1e-9 else v
        T = _unit3(T); N = _unit3(N)
        # Centre the slice on the section so the extrusion straddles it.
        half = float(thickness) / 2.0
        base = C - half * T
        loc = ifc.createIfcCartesianPoint((float(base[0]), float(base[1]), float(base[2])))
        axis = ifc.createIfcDirection((float(T[0]), float(T[1]), float(T[2])))
        refd = ifc.createIfcDirection((float(N[0]), float(N[1]), float(N[2])))
        a2p = ifc.createIfcAxis2Placement3D(loc, axis, refd)
        placement = ifc.createIfcLocalPlacement(None, a2p)

        # 2D profile in the local section plane (local XY = N,B), extruded +Z (=T).
        origin2d = ifc.createIfcCartesianPoint((0.0, 0.0))
        pos2d = ifc.createIfcAxis2Placement2D(origin2d, None)
        prof = None
        is_circle = str(profile).lower().startswith("circle")
        # Preferred: hollow polygon traced from the MEASURED boundary. Works for
        # any cross-section (circular, horseshoe, box) without guessing a shape,
        # and reflects real ovality/flat floor instead of an idealised circle.
        rings = TunnelIFCExporter._boundary_polygon(getattr(sec, "pts_2d", None),
                                                    float(wall_thickness))
        if rings is not None:
            outer, inner = rings
            op = ifc.createIfcPolyline(
                [ifc.createIfcCartesianPoint(pt) for pt in outer] +
                [ifc.createIfcCartesianPoint(outer[0])])
            voids = []
            if inner is not None and len(inner) >= 3:
                ip = ifc.createIfcPolyline(
                    [ifc.createIfcCartesianPoint(pt) for pt in inner] +
                    [ifc.createIfcCartesianPoint(inner[0])])
                voids = [ip]
            try:
                if voids:
                    prof = ifc.createIfcArbitraryProfileDefWithVoids("AREA", None, op, voids)
                else:
                    prof = ifc.createIfcArbitraryClosedProfileDef("AREA", None, op)
            except Exception:
                prof = None
        if prof is None and is_circle and _np.isfinite(sec.radius_fit) and sec.radius_fit > 0:
            # Fallback: idealised hollow circle when the boundary trace fails.
            R = float(sec.radius_fit)
            wt = float(min(wall_thickness, R * 0.9))
            prof = ifc.createIfcCircleHollowProfileDef("AREA", None, pos2d, R, wt)
        elif prof is None and _np.isfinite(sec.W1) and _np.isfinite(sec.H1) and sec.W1 > 0 and sec.H1 > 0:
            prof = ifc.createIfcRectangleProfileDef("AREA", None, pos2d, float(sec.W1), float(sec.H1))
        if prof is not None:
            extrude_dir = ifc.createIfcDirection((0.0, 0.0, 1.0))
            solid = ifc.createIfcExtrudedAreaSolid(prof, None, extrude_dir, float(thickness))
            shape = ifc.createIfcShapeRepresentation(body_ctx, "Body", "SweptSolid", [solid])
            return placement, shape

        # Fallback: outline ring as a Curve3D polyline (no profile dims).
        center_loc = ifc.createIfcCartesianPoint((float(C[0]), float(C[1]), float(C[2])))
        a2p_c = ifc.createIfcAxis2Placement3D(center_loc, axis, refd)
        placement = ifc.createIfcLocalPlacement(None, a2p_c)
        if is_circle and _np.isfinite(sec.radius_fit) and sec.radius_fit > 0:
            R = float(sec.radius_fit)
            ang = _np.linspace(0.0, 2.0 * _math.pi, 49)
            pts = [(R * _math.cos(t), R * _math.sin(t), 0.0) for t in ang]
        else:
            return placement, None
        poly = ifc.createIfcPolyline([ifc.createIfcCartesianPoint(pt) for pt in pts])
        shape = ifc.createIfcShapeRepresentation(body_ctx, "Body", "Curve3D", [poly])
        return placement, shape
