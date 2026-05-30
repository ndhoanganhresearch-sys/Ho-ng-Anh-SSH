# -*- coding: utf-8 -*-
"""CLI: validate the tool's denoisers against labelled STSD tunnel LAS files.

Thin wrapper around tunnel_analysis.datasets.stsd. STSD is distributed on
request (Google Form, repo lichking2017/STSD); the labelled LAS files are NOT
bundled. Once you have a segment:

    python validate_auto_denoise_stsd.py path/to/segment.las [more.las ...]
    python validate_auto_denoise_stsd.py --methods auto_denoise,density_lining seg.las

Edit STRUCTURE_LABELS in tunnel_analysis/datasets/stsd.py (or pass --structure)
to match the dataset's structural-class ids before trusting the numbers.
"""
import sys
from pathlib import Path

from tunnel_analysis.datasets import stsd


def main(argv):
    args = argv[1:]
    methods = None
    structure = None
    files = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--methods" and i + 1 < len(args):
            methods = [m.strip() for m in args[i + 1].split(",") if m.strip()]
            i += 2
        elif a == "--structure" and i + 1 < len(args):
            structure = {int(x) for x in args[i + 1].split(",") if x.strip()}
            i += 2
        else:
            files.append(a)
            i += 1

    if not files:
        print(__doc__)
        print("Usage: python validate_auto_denoise_stsd.py <segment.las> [more.las ...]")
        return 1

    for path in files:
        if not Path(path).exists():
            print(f"[skip] not found: {path}")
            continue
        xyz, labels = stsd.load_stsd_las(path)
        res = stsd.evaluate_methods(xyz, labels, methods=methods, structure_labels=structure)
        print("=" * 72)
        print(f"File: {path}  ({len(xyz):,} points)")
        for name, s in res.items():
            if "error" in s:
                print(f"  {name:16s} ERROR: {s['error']}")
                continue
            print(f"  {name:16s} precision={s['noise_precision']:.3f}  "
                  f"recall={s['noise_recall']:.3f}  F1={s['noise_f1']:.3f}  "
                  f"lining_retention={s['lining_retention']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
