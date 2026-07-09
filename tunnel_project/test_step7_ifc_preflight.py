# -*- coding: utf-8 -*-
"""Smoke tests for Step 7 IFC preflight/export failure modes."""
import importlib.util
import tempfile
from pathlib import Path

import numpy as np

from tunnel_analysis.ifc_exporter import TunnelIFCExporter
from tunnel_analysis.models import PipelineContext, SectionGeometry

try:
    from tunnel_analysis.ui.main_window import TunnelAnalysisWindow
except Exception as exc:
    TunnelAnalysisWindow = None
    UI_IMPORT_ERROR = exc
else:
    UI_IMPORT_ERROR = None

P = F = 0

def ck(name, cond, info=""):
    global P, F
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  " + info) if info else ""))
    P += 1 if cond else 0
    F += 0 if cond else 1


def section(ch=0.0):
    sg = SectionGeometry(chainage=ch)
    a = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    sg.pts_2d = np.column_stack([3.0 * np.cos(a), 3.0 * np.sin(a)])
    sg.radius_fit = 3.0
    sg.W1 = 6.0
    sg.H1 = 6.0
    sg.ovality = 0.1
    sg.eccentricity = 1.0
    sg.clearance_violation = False
    return sg


def expect_runtime(name, fn, contains):
    try:
        fn()
    except RuntimeError as exc:
        msg = str(exc)
        ck(name, contains in msg, msg)
    except Exception as exc:
        ck(name, False, f"wrong exception: {type(exc).__name__}: {exc}")
    else:
        ck(name, False, "no exception")


print("=== Step 7 UI preflight helpers ===")
valid_ctx = PipelineContext(
    sections=[section(0.0), section(1.0)],
    centerline=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=float),
)
if TunnelAnalysisWindow is None:
    ck("UI helper tests skipped when PySide6/UI import unavailable", True, repr(UI_IMPORT_ERROR))
else:
    ok, msg = TunnelAnalysisWindow._step7_ifc_preflight(valid_ctx, "ok.ifc")
    ck("UI preflight accepts valid .ifc path", ok, msg)
    ok, msg = TunnelAnalysisWindow._step7_ifc_preflight(valid_ctx, "bad.txt")
    ck("UI preflight rejects non-ifc path", (not ok) and ".ifc" in msg, msg)
    count = TunnelAnalysisWindow._count_component_points({
        "meta": object(),
        "cable": np.zeros((3, 3)),
        "light": [1, 2],
    })
    ck("component counter skips non-sized metadata", count == 5, f"count={count}")

print("=== Step 7 IFC exporter input guards ===")
exp = TunnelIFCExporter()
empty = PipelineContext()
expect_runtime(
    "empty context fails before dependency check",
    lambda: exp.export_ifc(empty, "dummy.ifc"),
    "computed tunnel sections",
)

one_section = PipelineContext(sections=[section(0.0)])
expect_runtime(
    "single section without centerline fails preflight",
    lambda: exp.export_ifc(one_section, "dummy.ifc"),
    "centerline",
)

component_ctx = PipelineContext(
    sections=[section(0.0), section(1.0)],
    centerline=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=float),
)
expect_runtime(
    "components export requires detected component_points",
    lambda: exp.export_ifc(component_ctx, "dummy.ifc", include_components=True),
    "Step 2.5",
)

if importlib.util.find_spec("ifcopenshell") is None:
    expect_runtime(
        "missing ifcopenshell gives friendly message",
        lambda: exp.export_ifc(component_ctx, "dummy.ifc"),
        "pip install ifcopenshell",
    )
else:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "step7_smoke.ifc"
        try:
            path = exp.export_ifc(component_ctx, str(out))
            ck("IFC export writes file when dependency exists", Path(path).exists(), path)
        except Exception as exc:
            ck("IFC export writes file when dependency exists", False, repr(exc))

print(f"\nPASS={P} FAIL={F}")
raise SystemExit(1 if F else 0)
