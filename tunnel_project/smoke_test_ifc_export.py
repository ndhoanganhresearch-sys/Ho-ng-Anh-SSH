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
    ctx.denoise_stats = {"n_cable": 12, "n_light": 4, "n_person": 1,
                         "n_wall_cable": 3, "n_radial": 50, "n_removed": 900}
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
        all_proxies = f.by_type("IfcBuildingElementProxy")
        # One proxy per section plus the single whole-bore proxy.
        proxies = [e for e in all_proxies if e.Name and e.Name.startswith("Section_")]
        bores = [e for e in all_proxies if e.Name == "Tunnel Bore"]
        assert len(proxies) == len(ctx.sections), (len(proxies), len(ctx.sections))
        assert len(bores) == 1, f"expected 1 Tunnel Bore proxy, got {len(bores)}"
        n_rep = sum(1 for e in proxies if e.Representation is not None)
        n_pl = sum(1 for e in proxies if e.ObjectPlacement is not None)
        assert n_rep == len(proxies), f"only {n_rep}/{len(proxies)} proxies have geometry"
        assert n_pl == len(proxies), f"only {n_pl}/{len(proxies)} proxies have placement"
        # property sets carried through
        psets = f.by_type("IfcPropertySet")
        assert any(p.Name == "TunnelSectionProperties" for p in psets), "section pset missing"
        # Solid geometry: each section is an extruded-area solid; the whole
        # bore is a single swept-disk solid (Circle profile).
        n_extruded = len(f.by_type("IfcExtrudedAreaSolid"))
        n_disk = len(f.by_type("IfcSweptDiskSolid"))
        assert n_extruded >= len(ctx.sections) - 2, f"too few solid slices: {n_extruded}"
        assert n_disk >= 1, "tunnel bore swept-disk solid missing"
        # Coloured components: every solid carries a surface style.
        n_style = len(f.by_type("IfcStyledItem"))
        n_surf = len(f.by_type("IfcSurfaceStyle"))
        assert n_style >= n_extruded, f"too few styled items: {n_style}"
        assert n_surf >= 1, "no surface styles"
        # Detected-component counts recorded on the project.
        comp = [x for x in f.by_type("IfcPropertySet") if x.Name == "TunnelComponents"]
        assert len(comp) == 1, "TunnelComponents pset missing"
        cprops = {pp.Name: pp.NominalValue.wrappedValue for pp in comp[0].HasProperties}
        assert cprops.get("CableSegments") == 12, cprops
        assert cprops.get("LightFixtures") == 4, cprops
        # Every proxy shape must actually build via the geometry kernel.
        import ifcopenshell.geom as geom
        settings = geom.settings()
        built = 0
        for e in f.by_type("IfcBuildingElementProxy"):
            if e.Representation is None:
                continue
            geom.create_shape(settings, e); built += 1
        result = (f"{len(proxies)} section proxies; extruded={n_extruded}, "
                  f"swept_disk={n_disk}, styled={n_style}, shapes_built={built}")
        del f
        return result


def test_ifc_components_by_label():
    """When the scan carries per-point labels, IFC records exact per-class
    point counts in a TunnelComponentsByLabel pset (ground truth, not the
    heuristic counts)."""
    if not _HAS_IFC:
        return "skipped (ifcopenshell missing)"
    import ifcopenshell
    ctx = _ctx()
    # attach synthetic per-point labels to the active scan
    n = len(ctx.scans[0].points)
    rng = np.random.default_rng(7)
    labels = rng.integers(0, 3, size=n)
    ctx.scans[0].metadata["labels"] = labels
    import collections
    truth = collections.Counter(labels.tolist())
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "labeled.ifc")
        TunnelIFCExporter().export_ifc(ctx, out, project_name="Labeled")
        f = ifcopenshell.open(out)
        ps = [x for x in f.by_type("IfcPropertySet") if x.Name == "TunnelComponentsByLabel"]
        assert len(ps) == 1, "TunnelComponentsByLabel pset missing"
        props = {pp.Name: pp.NominalValue.wrappedValue for pp in ps[0].HasProperties}
        for cid, cnt in truth.items():
            key = f"Class_{int(cid)}"
            assert props.get(key) == int(cnt), (key, props.get(key), cnt)
        del f
        return f"by-label classes={sorted(props)}"


def test_ifc4x3_alignment():
    """IFC4X3 schema exports the centerline as an IfcAlignment (infra
    standard); IFC4 keeps IfcAnnotation. Geometry still builds."""
    if not _HAS_IFC:
        return "skipped (ifcopenshell missing)"
    import ifcopenshell
    ctx = _ctx()
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "align.ifc")
        TunnelIFCExporter().export_ifc(ctx, out, project_name="Align", schema="IFC4X3_ADD2")
        f = ifcopenshell.open(out)
        assert f.schema.startswith("IFC4X3"), f.schema
        assert len(f.by_type("IfcAlignment")) == 1, "centerline not exported as IfcAlignment"
        assert len(f.by_type("IfcAnnotation")) == 0, "unexpected IfcAnnotation in 4X3"
        n_solid = len(f.by_type("IfcExtrudedAreaSolid"))
        assert n_solid >= len(ctx.sections) - 2, n_solid
        del f
        return f"IFC4X3 alignment OK, extruded={n_solid}"


def test_ifc_components_export():
    """include_components=True models detected cables/lights as coloured
    proxies clustered into discrete items."""
    if not _HAS_IFC:
        return "skipped (ifcopenshell missing)"
    import ifcopenshell
    ctx = _ctx()
    rng = np.random.default_rng(3)
    cable = np.column_stack([np.full(200, -2.4), np.linspace(2, 18, 200), np.full(200, 2.0)]) + rng.normal(0, 0.01, (200, 3))
    lights = np.vstack([rng.normal(0, 0.1, (30, 3)) + np.array([0, c, 4.8]) for c in (4, 10, 16)])
    ctx.component_points = {"cable": cable, "light": lights, "person": np.empty((0, 3))}
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "comp.ifc")
        TunnelIFCExporter().export_ifc(ctx, out, include_components=True)
        f = ifcopenshell.open(out)
        names = [e.Name or "" for e in f.by_type("IfcBuildingElementProxy")]
        cables = [n for n in names if n.startswith("Cable")]
        lights_p = [n for n in names if n.startswith("Light")]
        assert len(cables) >= 1, names
        assert len(lights_p) >= 1, names
        # Cable must be a swept-disk TUBE, not a box. The bore is also a
        # swept disk, so require at least 2 (bore + >=1 cable).
        assert len(f.by_type("IfcSweptDiskSolid")) >= 2, "cable not a tube"
        del f
        return f"components: {len(cables)} cable tube(s), {len(lights_p)} light box(es)"


if __name__ == "__main__":
    print("test_ifc_export_geometry_and_hierarchy ->",
          test_ifc_export_geometry_and_hierarchy())
    print("test_ifc_components_by_label ->", test_ifc_components_by_label())
    print("test_ifc4x3_alignment ->", test_ifc4x3_alignment())
    print("test_ifc_components_export ->", test_ifc_components_export())
    print("SMOKE TEST PASSED")
