# -*- coding: utf-8 -*-
import os
from pathlib import Path
import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tunnel_analysis.io_layer import BaseLayer
from tunnel_analysis.timeseries import TimeSeriesLayer

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "data" / "time_series_deformation"
assert DEMO.is_dir(), DEMO

files, skipped = BaseLayer.discover_epoch_files(str(DEMO))
assert len(files) >= 2, files
assert Path(files[0]).name.lower().startswith("t0"), files[0]
assert any(Path(f).stem.lower() == "t5" for f in files), files

# Load two epochs and build a Step 6-like series, then feed dashboard summary API.
loader = BaseLayer()
t0 = loader.load_scan(str(DEMO / "T0.las"), max_points=40_000).points
t5 = loader.load_scan(str(DEMO / "T5.las"), max_points=40_000).points
ts = TimeSeriesLayer()
pick = ts.suggest_crown_chainage([t0, t5], curve_radius_m=None)
series = ts.spatiotemporal_series([t0, t5], labels=["T5"], cyl_radius=0.5, normal_radius=0.6)
crown = ts.crown_settlement_series([t0, t5], labels=["T0", "T5"], chainage_m=float(pick["chainage_m"]), curve_radius_m=None)
series["crown_settlement_mm"] = crown["crown_settlement_mm"]
series["crown_chainage_m"] = crown["chainage_m"]
series["crown_chainage_source"] = pick["source"]

# Import dashboard without requiring a full QApplication display.
from tunnel_analysis.ui.widgets import SummaryDashboardWidget
from tunnel_analysis.common import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
dash = SummaryDashboardWidget()
assert hasattr(dash, "update_step6_summary")
dash.update_step6_summary(series, forecast={"ok": True})
assert "crown_settlement_mm" in dash._params
assert dash._params["crown_settlement_mm"] > 10.0
assert abs(float(dash._params.get("step6_crown_chainage_m", 0.0)) - float(pick["chainage_m"])) < 1e-6
print("STEP6 DEMO+DASHBOARD TEST PASSED",
      "ch", pick["chainage_m"],
      "crown", dash._params["crown_settlement_mm"])
