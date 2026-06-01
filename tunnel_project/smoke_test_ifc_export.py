# -*- coding: utf-8 -*-
"""Smoke test for IFC4 export (tunnel_analysis.ifc_exporter).

Run from the tunnel_project directory:
    python smoke_test_ifc_export.py

Builds a synthetic tunnel context, exports an IFC4 file, reads it back with
ifcopenshell, and verifies the spatial hierarchy, the centerline annotation,
and that every section proxy now carries BOTH an ObjectPlacement and a
Representation (the gap this work closed). Skips cleanly if ifcopenshell is
unavailable.
"""
import importlib.util
import os
import tempfile

import numpy as np

from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.ifc_exporter import TunnelIFCExporter
from tunnel_analysis.models import PipelineContext, PointCloudBundle

_HAS_IFC = importlib.util.find_spec("ifcopenshell") is not None


def _ctx(profile_box=False, R=2.75, length=20.0, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for y in np.linspace(0.0, length, 200):
        m = rng.integers(80, 130)
        a = rng.uniform(0.0, 2 * np.pi, m)
        x = R * np.cos(a) + rng.normal(0, 0.006, m)
        z = R * np.sin(a) + R + rng.normal(0, 0.006, m)
        rows.append(np.column_stack([x, np.full(m, y), z]))
    pts = np.vstack(rows)
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=pts))
    ctx.active_index = 0
    geo, par = GeometricLayer(), ParameterExtractionLayer()
    cl, fr = geo.extract_centerline_bspline(ctx, section_count=40)
    ctx.centerline, ctx.frenet_frames = cl, fr
    ctx.tunnel_profile = par.detect_profile(ctx)
    ctx.sections = par.compute_all_sections(ctx, vl_box_w=5.0, vl_box_h=5.0, vl_cir_r=2.7)
    ctx.parameters.update(par.calc_ovality(ctx))
    ctx.parameters.update(par.calc_eccentricity(ctx))
    return ctx


def test_ifc_export_geometry_and_hierarchy():
    if not _HAS_IFC:
        return "skipped (ifcopenshell missing)"
    import ifcopenshell
    ctx = _ctx()
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "tunnel.ifc")
        path = TunnelIFCExporter().export_ifc(ctx, out, project_name="SmokeTunnel")
        assert os.path.isfile(path)
        f = ifcopenshell.open(path)
        assert f.schema == "IFC4", f.schema
        for t in ("IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey"):
            assert len(f.by_type(t)) == 1, (t, len(f.by_type(t)))
        assert len(f.by_type("IfcAnnotation")) == 1, "centerline annotation missing"
        proxies = f.by_type("IfcBuildingElementProxy")
        assert len(proxies) == len(ctx.sections), (len(proxies), len(ctx.sections))
        n_rep = sum(1 for e in proxies if e.Representation is not None)
        n_pl = sum(1 for e in proxies if e.ObjectPlacement is not None)
        assert n_rep == len(proxies), f"only {n_rep}/{len(proxies)} proxies have geometry"
        assert n_pl == len(proxies), f"only {n_pl}/{len(proxies)} proxies have placement"
        # property sets carried through
        psets = f.by_type("IfcPropertySet")
        assert any(p.Name == "TunnelSectionProperties" for p in psets), "section pset missing"
        result = (f"{len(proxies)} proxies, all placed+geom; "
                  f"polylines={len(f.by_type('IfcPolyline'))}")
        del f
        return result


if __name__ == "__main__":
    print("test_ifc_export_geometry_and_hierarchy ->",
          test_ifc_export_geometry_and_hierarchy())
    print("SMOKE TEST PASSED")
