"""find_curved_stsd.py - Locate curved tunnel stretches in the STSD las folder.

Reads only LAS headers (fast, no point loading), computes each scan's centroid
(bbox centre), orders channels along the tunnel, and measures direction change
between consecutive segments to find the most curved run per shape.
"""
import os
import re
import glob
import numpy as np
import laspy

BASE = r"F:\data mẫu\STSD v 1.1\las"


def centroid(path):
    with laspy.open(path) as fh:
        h = fh.header
        return np.array([(h.x_min + h.x_max) / 2, (h.y_min + h.y_max) / 2,
                         (h.z_min + h.z_max) / 2])


def key(fname):
    # e.g. round-1-12_3 -> (round, 12, 3)
    m = re.match(r"(horse|rec|round)-1-(\d+)_(\d+)", fname)
    if not m:
        return None
    return (m.group(1), int(m.group(2)), int(m.group(3)))


def main():
    files = glob.glob(os.path.join(BASE, "*.las"))
    recs = []
    for p in files:
        k = key(os.path.basename(p))
        if k:
            recs.append((k, p))
    by_shape = {}
    for (shape, sec, ch), p in recs:
        by_shape.setdefault(shape, []).append((sec, ch, p))

    for shape, items in by_shape.items():
        items.sort(key=lambda t: (t[0], t[1]))   # order along tunnel
        cents, labels = [], []
        for sec, ch, p in items:
            try:
                cents.append(centroid(p)); labels.append(f"{shape}-1-{sec}_{ch}")
            except Exception:
                pass
        cents = np.array(cents)
        if len(cents) < 5:
            continue
        # direction of each segment, then turn-angle (deg) between segments
        seg = np.diff(cents[:, :2], axis=0)
        seglen = np.linalg.norm(seg, axis=1, keepdims=True)
        u = seg / np.where(seglen < 1e-9, 1, seglen)
        dots = np.clip((u[:-1] * u[1:]).sum(axis=1), -1, 1)
        turn = np.degrees(np.arccos(dots))   # turn angle at each interior node
        print(f"\n===== {shape}: {len(cents)} channels, "
              f"total path {seglen.sum():.0f} m =====")
        print(f"  max turn/seg = {turn.max():.1f} deg, cumulative turn = {turn.sum():.0f} deg")
        # find the window of consecutive channels with the largest cumulative turn
        W = 8
        if len(turn) >= W:
            best_i, best_turn = 0, -1
            for i in range(len(turn) - W + 1):
                t = turn[i:i + W].sum()
                if t > best_turn:
                    best_turn, best_i = t, i
            seg_files = labels[best_i:best_i + W + 2]
            print(f"  MOST CURVED run ({best_turn:.0f} deg over {W} segs): "
                  f"{seg_files[0]} .. {seg_files[-1]}")
            secs = sorted(set(int(re.match(r'.+-1-(\d+)_', s).group(1)) for s in seg_files))
            print(f"  -> sections involved: {secs}")


if __name__ == "__main__":
    main()
