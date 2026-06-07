# -*- coding: utf-8 -*-
"""Verify the MS-Store user-site prune guard in run_tunnel_analysis.py.

Simulates the leak by injecting a fake '…\\LocalCache\\local-packages\\…' entry
onto sys.path, then applies the same prune logic and confirms:
  • the user-site entry is removed,
  • the venv's own site-packages is preserved,
  • numpy/scipy still import from the venv.
"""
import sys, os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = F = 0
def ck(n, c, i=""):
    global P, F
    print(("  [PASS] " if c else "  [FAIL] ") + n + ("  " + i if i else ""))
    P += (1 if c else 0); F += (0 if c else 1)

FAKE_USERSITE = (r"C:\Users\ssl\AppData\Local\Packages"
                 r"\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0"
                 r"\LocalCache\local-packages\Python312\site-packages")
VENV_SITE = r"C:\Users\ssl\Desktop\Code Python\data python cusor\.venv\Lib\site-packages"

# Inject the leak + a venv-style entry.
sys.path.insert(0, FAKE_USERSITE)
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

leak_before = [p for p in sys.path if "local-packages" in p.replace("/", "\\").lower()]
ck("leak injected", len(leak_before) >= 1, f"{len(leak_before)} entries")

# ── The exact prune logic from run_tunnel_analysis.py ───────────────────────
sys.path[:] = [p for p in sys.path
               if "local-packages" not in p.replace("/", "\\").lower()]

leak_after = [p for p in sys.path if "local-packages" in p.replace("/", "\\").lower()]
ck("user-site removed after prune", len(leak_after) == 0, f"{len(leak_after)} left")
ck("venv site-packages preserved", VENV_SITE in sys.path)

# numpy/scipy must still import from the venv (this process IS the venv python).
import numpy
ck("numpy imports from venv", ".venv" in numpy.__file__,
   f"{numpy.__version__} @ {numpy.__file__.split('site-packages')[0][-12:]}")
import scipy.stats  # the exact import that RecursionError'd
ck("scipy.stats imports OK", True)

print(f"\nPASS={P} FAIL={F}")
sys.exit(F)
