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
                   engineer: str = "CBNU Smart Structure Lab") -> str:
        try:
            import ifcopenshell
            import ifcopenshell.api
        except ImportError:
            raise RuntimeError("ifcopenshell required: pip install ifcopenshell")

        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        ifc = ifcopenshell.file(schema="IFC4")

        # Project
        project = ifcopenshell.api.run("root.create_entity", ifc,
                                        ifc_class="IfcProject", name=project_name)
        ifcopenshell.api.run("unit.assign_unit", ifc)
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

        # Centerline as IfcAnnotation
        cl = context.centerline
        if cl is not None and len(cl) >= 2:
            cl_entity = ifcopenshell.api.run("root.create_entity", ifc,
                                              ifc_class="IfcAnnotation",
                                              name="Tunnel Centerline")
            pts_3d = [ifc.createIfcCartesianPoint(
                (float(p[0]), float(p[1]), float(p[2]))) for p in cl]
            polyline = ifc.createIfcPolyline(pts_3d)
            shape = ifc.createIfcShapeRepresentation(
                body_ctx, "Axis", "Curve3D", [polyline])
            prod_def = ifc.createIfcProductDefinitionShape(None, None, [shape])
            cl_entity.Representation = prod_def
            ifcopenshell.api.run("spatial.assign_container", ifc,
                                  products=[cl_entity], relating_structure=storey)

        # Sections as IfcBuildingElementProxy with placement + ring geometry
        frames = context.frenet_frames or []
        profile = getattr(context, "tunnel_profile", "Circle")
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
            placement, shape = self._section_placement_shape(ifc, body_ctx, sec, fr, profile)
            if placement is not None:
                elem.ObjectPlacement = placement
            if shape is not None:
                elem.Representation = ifc.createIfcProductDefinitionShape(None, None, [shape])
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

        ifc.write(str(path))
        return str(path)

    @staticmethod
    def _section_placement_shape(ifc, body_ctx, sec, fr, profile):
        """Build (IfcLocalPlacement, IfcShapeRepresentation) for a section."""
        import numpy as _np
        C = _np.asarray(sec.center_3d, dtype=float)
        if fr is not None and all(k in fr for k in ("T", "N", "B")):
            T = _np.asarray(fr["T"], dtype=float)
            N = _np.asarray(fr["N"], dtype=float)
        else:
            T = _np.array([0.0, 1.0, 0.0]); N = _np.array([1.0, 0.0, 0.0])
        def _unit3(v):
            n = float(_np.linalg.norm(v));
            return v / n if n > 1e-9 else v
        T = _unit3(T); N = _unit3(N)
        loc = ifc.createIfcCartesianPoint((float(C[0]), float(C[1]), float(C[2])))
        axis = ifc.createIfcDirection((float(T[0]), float(T[1]), float(T[2])))
        refd = ifc.createIfcDirection((float(N[0]), float(N[1]), float(N[2])))
        a2p = ifc.createIfcAxis2Placement3D(loc, axis, refd)
        placement = ifc.createIfcLocalPlacement(None, a2p)
        # Ring in the LOCAL section plane (local XY = N-B), closed polyline.
        import math as _math
        pts = None
        if str(profile).lower().startswith("circle") and _np.isfinite(sec.radius_fit) and sec.radius_fit > 0:
            R = float(sec.radius_fit)
            ang = _np.linspace(0.0, 2.0 * _math.pi, 49)
            pts = [(R * _math.cos(t), R * _math.sin(t), 0.0) for t in ang]
        elif _np.isfinite(sec.W1) and _np.isfinite(sec.H1) and sec.W1 > 0 and sec.H1 > 0:
            w = float(sec.W1) / 2.0; h = float(sec.H1) / 2.0
            pts = [(-w, -h, 0.0), (w, -h, 0.0), (w, h, 0.0), (-w, h, 0.0), (-w, -h, 0.0)]
        if pts is None:
            return placement, None
        poly = ifc.createIfcPolyline([ifc.createIfcCartesianPoint(pt) for pt in pts])
        shape = ifc.createIfcShapeRepresentation(body_ctx, "Body", "Curve3D", [poly])
        return placement, shape
