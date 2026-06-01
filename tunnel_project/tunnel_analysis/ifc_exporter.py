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
                   wall_thickness: float = 0.3) -> str:
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

            # Whole-bore solid: a swept-disk tube of the median measured radius
            # following the centerline polyline, so the model carries a single
            # continuous 3D body for the tunnel (Circle profiles only; box bores
            # are represented by their per-section solid slices below).
            try:
                radii = [float(sc.radius_fit) for sc in context.sections
                         if np.isfinite(sc.radius_fit) and sc.radius_fit > 0]
                is_circle = str(getattr(context, "tunnel_profile", "Circle")).lower().startswith("circle")
                if is_circle and len(radii) >= 1 and len(cl) >= 3:
                    bore_R = float(np.median(radii))
                    directrix = ifc.createIfcPolyline(pts_3d)
                    # Hollow tube: inner radius = bore_R - wall_thickness so the
                    # tunnel is a shell, not a solid cylinder. Guard against a
                    # non-positive inner radius on thin/odd bores.
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

        ifc.write(str(path))
        return str(path)

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

        # 2D profile in the local section plane (local XY), extruded +Z (=T).
        origin2d = ifc.createIfcCartesianPoint((0.0, 0.0))
        pos2d = ifc.createIfcAxis2Placement2D(origin2d, None)
        prof = None
        is_circle = str(profile).lower().startswith("circle")
        if is_circle and _np.isfinite(sec.radius_fit) and sec.radius_fit > 0:
            # Hollow ring (CircleHollowProfileDef) so the extruded slice is a
            # tunnel-wall shell, not a solid disc. WallThickness clamped so it
            # never exceeds the radius.
            R = float(sec.radius_fit)
            wt = float(min(wall_thickness, R * 0.9))
            prof = ifc.createIfcCircleHollowProfileDef("AREA", None, pos2d, R, wt)
        elif _np.isfinite(sec.W1) and _np.isfinite(sec.H1) and sec.W1 > 0 and sec.H1 > 0:
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
