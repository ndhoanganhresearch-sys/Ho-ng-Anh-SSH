r"""
Cross-check the REAL tool Step 6 (M3C2) against ground truth.

Unlike phase_c_validate.py (which re-measures in the deformation frame), this
calls the production code path the GUI uses -- TimeSeriesLayer.m3c2_distances
(py4dgeo M3C2) -- on the raycast clouds, bins the corepoint displacements into
the three deformation zones, and compares to ground_truth.csv. This is the
genuine, independent tool validation.

Run from tunnel_project/:
  ..\.venv\Scripts\python.exe tools\crosscheck_tool_step6.py --epoch T5
"""
import os
import sys
import csv
import numpy as np

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)
from tunnel_analysis.timeseries import TimeSeriesLayer

R = 500.0
DATA = os.path.join(_BASE, "data", "blender_lidar_t0t5")
S_WIN, ANG_WIN = 1.0, 12.0
EPOCH = sys.argv[sys.argv.index("--epoch") + 1] if "--epoch" in sys.argv else "T5"


def load_lining(path):
    a = np.loadtxt(path)
    return (a[a[:, 4] == 1] if a.shape[1] > 4 else a)[:, :3]


def frame(pts):
    s = R * np.arcsin(np.clip(pts[:, 1] / R, -1, 1))
    cx = R * (1 - np.cos(s / R))
    theta = np.degrees(np.arctan2(pts[:, 2], pts[:, 0] - cx))
    return s, theta


def read_gt(epoch):
    gt = {}
    with open(os.path.join(DATA, "ground_truth.csv")) as f:
        for row in csv.DictReader(f):
            if row["epoch"] == epoch:
                gt[row["deformation_type"]] = (float(row["value_mm"]),
                                               float(row["chainage_m"]),
                                               float(row["theta_deg"]))
    return gt


def main():
    t0 = load_lining(os.path.join(DATA, "T0_raycast.txt"))
    tn = load_lining(os.path.join(DATA, "%s_raycast.txt" % EPOCH))
    print("Tool Step 6 cross-check  epoch:", EPOCH)
    print("loading clouds  T0=%d  %s=%d" % (len(t0), EPOCH, len(tn)))

    ts = TimeSeriesLayer()
    res = ts.m3c2_distances(t0, tn)
    cp = res["corepoints"]
    d = res["distance_mm"]
    print("method:", res["method"], " corepoints:", len(cp))

    s, theta = frame(cp)
    gt = read_gt(EPOCH)
    rows = []
    for kind, (gv, ch, th0) in gt.items():
        dth = np.abs(((theta - th0 + 180) % 360) - 180)
        m = (np.abs(s - ch) < S_WIN) & (dth < ANG_WIN) & np.isfinite(d)
        if m.sum() == 0:
            peak = 0.0
        else:
            dz = d[m]
            # peak signed displacement = the extreme matching GT sign (or 0)
            peak = dz.min() if gv < 0 else (dz.max() if gv > 0 else float(np.nanmean(dz)))
        err = abs(abs(peak) - abs(gv))
        rows.append((kind, ch, gv, round(float(peak), 1), round(float(err), 1), m.sum()))
        print("  %-22s GT=%+6.1f  tool M3C2 peak=%+7.1f  |err|=%4.1f  (n=%d)"
              % (kind, gv, peak, err, m.sum()))

    out = os.path.join(DATA, "tool_crosscheck_%s.csv" % EPOCH)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "chainage_m", "ground_truth_mm", "tool_m3c2_peak_mm", "abs_err_mm", "n_corepoints"])
        w.writerows(rows)
    print("wrote", out)


if __name__ == "__main__":
    main()
