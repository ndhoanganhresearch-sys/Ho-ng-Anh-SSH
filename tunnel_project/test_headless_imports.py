# -*- coding: utf-8 -*-
"""Regression checks for headless Step 6 imports.

The numeric T0/Tn pipeline must stay importable without eagerly loading the
PyVista/PyVistaQt render stack. Eager render imports produced noisy VTK stderr
and PyVista shutdown cleanup messages in headless tests, hiding real failures.
"""
import sys
from pathlib import Path


def fail(msg):
    print(f"  [FAIL] {msg}")
    raise SystemExit(1)


def ok(msg):
    print(f"  [PASS] {msg}")


import tunnel_analysis.common as common

if "pyvista" in sys.modules:
    fail("common import should not eagerly import pyvista")
ok("common import does not load pyvista")

if "pyvistaqt" in sys.modules:
    fail("common import should not eagerly import pyvistaqt")
ok("common import does not load pyvistaqt")

from tunnel_analysis.io_layer import BaseLayer

fixture = Path("_headless_import_fixture.txt")
fixture.write_text("0 0 0\n1 0 0\n0 1 0\n0 0 1\n", encoding="utf-8")
try:
    bundle = BaseLayer().load_scan(str(fixture))
finally:
    fixture.unlink(missing_ok=True)

if bundle.cloud is not None:
    fail("load_scan should not create a PyVista cloud in headless I/O")
ok("load_scan keeps cloud=None")

if "pyvista" in sys.modules:
    fail("load_scan should not import pyvista for numeric pipeline")
ok("load_scan does not load pyvista")

print("HEADLESS IMPORT REGRESSION PASSED")
