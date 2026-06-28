r"""
Plot measured-vs-ground-truth deformation across the full T0->T5 raycast series.

Reuses the measurement logic from phase_c_validate.py (no GUI). Produces:
  - data/blender_lidar_t0t5/series_validation.csv  (epoch x metric, GT vs measured)
  - data/blender_lidar_t0t5/series_validation.png  (3 panels, GT dashed vs measured)

Run from tunnel_project/:
  ..\.venv\Scripts\python.exe tools\plot_raycast_series.py
"""

import os
import sys
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from phase_c_validate import DATA, load_lining, read_ground_truth, measure

EPOCHS = ["T0", "T1", "T2", "T3", "T4", "T5"]
METRICS = [
    ("crown_settlement", "Crown settlement @20m", "tab:blue"),
    ("sidewall_convergence", "Sidewall convergence @45m", "tab:green"),
    ("local_damage", "Local damage @65m", "tab:red"),
]


def main():
    t0 = load_lining(os.path.join(DATA, "T0_raycast.txt"))
    series = {m: {"gt": [], "meas": []} for m, _, _ in METRICS}

    for ep in EPOCHS:
        tn = load_lining(os.path.join(DATA, "%s_raycast.txt" % ep))
        gt = read_ground_truth(ep) if ep != "T0" else {}
        for kind, _, _ in METRICS:
            if ep == "T0":
                series[kind]["gt"].append(0.0)
                series[kind]["meas"].append(0.0)
            else:
                g = gt[kind]
                series[kind]["gt"].append(g["value_mm"])
                series[kind]["meas"].append(round(measure(t0, tn, kind, g["chainage"], g["theta"]), 1))

    # CSV
    out_csv = os.path.join(DATA, "series_validation.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "metric", "ground_truth_mm", "measured_mm", "error_mm"])
        for i, ep in enumerate(EPOCHS):
            for kind, _, _ in METRICS:
                gtv = series[kind]["gt"][i]
                mv = series[kind]["meas"][i]
                w.writerow([ep, kind, gtv, mv, round(abs(mv - gtv), 1)])

    # Plot
    x = np.arange(len(EPOCHS))
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharex=True)
    for ax, (kind, title, color) in zip(axes, METRICS):
        gt = series[kind]["gt"]
        meas = series[kind]["meas"]
        ax.plot(x, gt, "--", color="gray", label="Ground truth", linewidth=1.6)
        ax.plot(x, meas, "o-", color=color, label="Measured", linewidth=1.8, markersize=6)
        for xi, (g, m) in enumerate(zip(gt, meas)):
            if g != 0:
                ax.annotate("%.0f" % (m - g), (xi, m), textcoords="offset points",
                            xytext=(0, -12), fontsize=7, color=color, ha="center")
        ax.set_title(title, fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(EPOCHS)
        ax.set_xlabel("Epoch")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Deformation (mm)")
    fig.suptitle("Raycast validation: measured vs ground truth (T0->T5, curved tunnel)\n"
                 "labels under points = measured - GT (mm)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    out_png = os.path.join(DATA, "series_validation.png")
    fig.savefig(out_png, dpi=130)
    print("wrote", out_csv)
    print("wrote", out_png)


if __name__ == "__main__":
    main()
