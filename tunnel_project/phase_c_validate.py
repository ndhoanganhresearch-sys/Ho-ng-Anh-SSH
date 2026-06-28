r"""
Phase C: Automated Validation (real, no GUI required).

Measures deformation directly from the raycast point clouds and compares it
against the ground truth in ground_truth.csv. This is a self-contained check of
the raycast track: it does NOT need the PyQt tool — it reproduces the geometric
measurement (crown settlement, sidewall convergence, local damage) that Step 6
performs, in the same curved cross-section frame the clouds were generated in.

Run from tunnel_project/ with the project venv:
  ..\.venv\Scripts\python.exe phase_c_validate.py --epoch T5

Inputs (data/blender_lidar_t0t5/):
  - T0_raycast.txt          clean reference  (from tools/raycast_tunnel_epochs.py)
  - <EPOCH>_raycast.txt     deformed epoch
  - ground_truth.csv        answer key (epoch, chainage, type, value_mm, ...)

Outputs:
  - validation_results.csv
  - validation_report.md
"""

import os
import sys
import csv
import math
import numpy as np

R = 500.0
try:
    _BASE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _BASE = os.getcwd()
DATA = os.path.join(_BASE, "data", "blender_lidar_t0t5")
TOL_MM = 8.0          # acceptance tolerance (mm) on window-mean deformation
S_WIN = 0.75          # arc-length half-window (m) around each chainage
ANG_WIN_DEG = 10.0    # angular half-window (deg) around each theta
# NOTE: measured values are window-MEANS over the windows above, so they are a
# lower bound on the true peak GT (the bias grows for narrow features like the
# local-damage patch). This validates raycast fidelity, NOT the PyQt tool.

EPOCH = "T5"
if "--epoch" in sys.argv:
    EPOCH = sys.argv[sys.argv.index("--epoch") + 1]


def load_lining(path):
    a = np.loadtxt(path)
    a = a[a[:, 4] == 1] if a.shape[1] > 4 else a
    return a[:, :3]


def frame(pts):
    """Return arc-length s, centerline-x cx, lateral, up, theta(deg) per point."""
    y = pts[:, 1]
    s = R * np.arcsin(np.clip(y / R, -1, 1))
    cx = R * (1 - np.cos(s / R))
    lat = pts[:, 0] - cx
    up = pts[:, 2]
    theta = np.degrees(np.arctan2(up, lat))
    return s, cx, lat, up, theta


def zone_mask(s, theta, chainage, theta0):
    dth = np.abs(((theta - theta0 + 180) % 360) - 180)
    return (np.abs(s - chainage) < S_WIN) & (dth < ANG_WIN_DEG)


def read_ground_truth(epoch):
    gt = {}
    with open(os.path.join(DATA, "ground_truth.csv")) as f:
        for row in csv.DictReader(f):
            if row["epoch"] == epoch:
                gt[row["deformation_type"]] = {
                    "value_mm": float(row["value_mm"]),
                    "chainage": float(row["chainage_m"]),
                    "theta": float(row["theta_deg"]),
                }
    return gt


def measure(t0, tn, kind, chainage, theta0):
    """Window-mean deformation (mm) for one zone, measured T0->Tn.

    A lower bound on the true peak: it averages over the s/angle window, so
    narrow features read low. Compared against the GT peak value_mm.
    """
    s0, _, lat0, up0, th0 = frame(t0)
    sn, _, latn, upn, thn = frame(tn)
    m0 = zone_mask(s0, th0, chainage, theta0)
    mn = zone_mask(sn, thn, chainage, theta0)
    if m0.sum() == 0 or mn.sum() == 0:
        return 0.0
    if kind == "crown_settlement":
        # crown apex drop: change in mean crown Z
        return (up0[m0].mean() - upn[mn].mean()) * -1000.0  # negative = down
    if kind == "sidewall_convergence":
        # inward change in half-width (|lateral|), reported as negative (inward)
        return (np.abs(latn[mn]).mean() - np.abs(lat0[m0]).mean()) * 1000.0
    if kind == "local_damage":
        # radial change at the patch
        r0 = np.hypot(lat0[m0], up0[m0]).mean()
        rn = np.hypot(latn[mn], upn[mn]).mean()
        return (rn - r0) * 1000.0
    return 0.0


def main():
    print("=" * 70)
    print("PHASE C VALIDATION  epoch:", EPOCH)
    print("=" * 70)
    t0 = load_lining(os.path.join(DATA, "T0_raycast.txt"))
    tn = load_lining(os.path.join(DATA, "%s_raycast.txt" % EPOCH))
    print("lining points  T0=%d  %s=%d" % (len(t0), EPOCH, len(tn)))

    gt = read_ground_truth(EPOCH)
    rows = []
    for kind, g in gt.items():
        measured = measure(t0, tn, kind, g["chainage"], g["theta"])
        error = abs(measured - g["value_mm"])
        status = "PASS" if error <= TOL_MM else "FAIL"
        rows.append({
            "epoch": EPOCH, "metric": kind, "chainage_m": g["chainage"],
            "ground_truth_mm": g["value_mm"], "measured_mm": round(measured, 1),
            "error_mm": round(error, 1), "tolerance_mm": TOL_MM, "status": status,
        })
        print("  %-22s GT=%+6.1f  measured=%+6.1f  err=%4.1f  %s"
              % (kind, g["value_mm"], measured, error, status))

    out_csv = os.path.join(DATA, "validation_results.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    errs = [r["error_mm"] for r in rows]
    mae = sum(errs) / len(errs)
    allpass = all(r["status"] == "PASS" for r in rows)
    lines = ["# Validation Report: T0 vs %s" % EPOCH, "",
             "Measured directly from raycast point clouds (no GUI).", "",
             "| Metric | Chainage | GT (mm) | Measured (mm) | Error (mm) | Status |",
             "| --- | ---: | ---: | ---: | ---: | --- |"]
    for r in rows:
        lines.append("| %s | %.0f | %+.1f | %+.1f | %.1f | %s |" % (
            r["metric"], r["chainage_m"], r["ground_truth_mm"],
            r["measured_mm"], r["error_mm"], r["status"]))
    lines += ["", "**MAE:** %.1f mm  | tolerance %.0f mm (window-mean vs GT peak)" % (mae, TOL_MM), "",
              "## Verdict", "",
              ("PASS - raycast deformation recovered within tolerance."
               if allpass else "FAIL - some zones exceed tolerance."),
              "",
              "Measured = window-MEAN over +/-%.2f m arc-length, +/-%.0f deg angular "
              "around each peak (lower bound on the GT peak; narrow features read low)."
              % (S_WIN, ANG_WIN_DEG),
              "This checks raycast fidelity (injected ~ recovered), not the PyQt tool's Step 6."]
    with open(os.path.join(DATA, "validation_report.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

    print("MAE %.1f mm  ->  %s" % (mae, "PASS" if allpass else "FAIL"))
    print("wrote:", out_csv, "and validation_report.md")


if __name__ == "__main__":
    main()
