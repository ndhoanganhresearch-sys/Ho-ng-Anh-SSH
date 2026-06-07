import os
import sys
import warnings
import logging

# ── Isolate from Microsoft Store Python user-site ───────────────────────────
# The MS Store Python injects its per-user site-packages
# (…\LocalCache\local-packages\Python312\site-packages) onto sys.path even
# inside a venv in some launch contexts (e.g. an IDE "Run" button). That folder
# can hold a DIFFERENT numpy (e.g. 2.4.3) than the venv's (2.4.6); loading that
# numpy against the venv's scipy is an ABI mismatch and triggers a
# RecursionError while importing scipy.stats (via py4dgeo). Prune those entries
# BEFORE anything imports numpy (vtk below pulls it in). The venv's own
# "…\.venv\Lib\site-packages" does NOT contain "local-packages", so it stays.
_before = len(sys.path)
sys.path[:] = [p for p in sys.path if "local-packages" not in p.replace("/", "\\").lower()]
if len(sys.path) != _before:
    os.environ["PYTHONNOUSERSITE"] = "1"   # belt-and-suspenders for child procs
    sys.modules.pop("numpy", None)         # ensure a clean (re)import from venv

# Suppress VTK/PyVista warning spam
os.environ["VTK_SILENCE_GET_VOID_POINTER_WARNINGS"] = "1"
os.environ["PYVISTA_OFF_SCREEN"] = "false"

# Use HuggingFace offline mode to suppress token warning
# Models are cached locally after first download
import os
os.environ.setdefault("TRANSFORMERS_OFFLINE", "0")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "0")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Prevent recursive WARNING:root: loop in PyVista VTK error handler
logging.getLogger("root").setLevel(logging.CRITICAL)
logging.getLogger("pyvista").setLevel(logging.ERROR)
logging.getLogger("vtk").setLevel(logging.ERROR)

# Disable all root logger handlers to stop the loop
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(logging.NullHandler())

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*VTK.*")
warnings.filterwarnings("ignore", message=".*pyvista.*")

try:
    import vtk
    vtk.vtkObject.GlobalWarningDisplayOff()
except Exception:
    pass
try:
    import vtkmodules.vtkRenderingCore as _vtk_rc
    _vtk_rc.vtkObject.GlobalWarningDisplayOff()
except Exception:
    pass

from tunnel_analysis.main import main

if __name__ == "__main__":
    raise SystemExit(main())
