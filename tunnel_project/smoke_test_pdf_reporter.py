# -*- coding: utf-8 -*-
"""Smoke test for PDF report export (tunnel_analysis.pdf_reporter).

Run from the tunnel_project directory:
    python smoke_test_pdf_reporter.py

Builds a synthetic tunnel context, exports a PDF report, and checks a non-empty
PDF file is produced with a valid header. Skips cleanly if reportlab is absent.
"""
import importlib.util
import os
import tempfile

import numpy as np

from tunnel_analysis.geometry import GeometricLayer
from tunnel_analysis.parameters import ParameterExtractionLayer
from tunnel_analysis.pdf_reporter import TunnelPDFReporter
from tunnel_analysis.models import PipelineContext, PointCloudBundle

_HAS_RL = importlib.util.find_spec("reportlab") is not None


def _ctx(R=2.75, length=20.0, seed=0):
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


def test_pdf_export_produces_file():
    if not _HAS_RL:
        return "skipped (reportlab missing)"
    ctx = _ctx()
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "report.pdf")
        path = TunnelPDFReporter().export_pdf(ctx, out, project_name="SmokePDF")
        assert os.path.isfile(path), "PDF not written"
        size = os.path.getsize(path)
        assert size > 1000, f"PDF suspiciously small: {size} bytes"
        with open(path, "rb") as fh:
            head = fh.read(5)
        assert head == b"%PDF-", f"bad PDF header: {head!r}"
        return f"PDF {size:,} bytes, valid header"


if __name__ == "__main__":
    print("test_pdf_export_produces_file ->", test_pdf_export_produces_file())
    print("SMOKE TEST PASSED")
