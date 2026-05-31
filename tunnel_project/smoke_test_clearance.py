# -*- coding: utf-8 -*-
"""Smoke tests for clearance.ClearanceLayer (train-gauge intrusion).

Run from the tunnel_project directory:
    python smoke_test_clearance.py

Builds a synthetic tunnel shell plus KNOWN intruding objects (points pushed
inward, inside the clearance gauge) and verifies the collision detector flags
exactly those, reporting precision/recall and quantified intrusion depth.
"""
import numpy as np

from tunnel_analysis.clearance import ClearanceLayer
from tunnel_analysis.models import PipelineContext, PointCloudBundle


def _shell(n_axial=160, n_theta=160, radius=2.75, length=24.0, seed=0):
    rng = np.random.default_rng(seed)
    y = np.linspace(0.0, length, n_axial)
    th = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    yy, tt = np.meshgrid(y, th)
    rr = radius + rng.normal(0.0, 0.01, yy.shape)
    return np.column_stack([(rr * np.cos(tt)).ravel(), yy.ravel(), (rr * np.sin(tt)).ravel()])


def _intruder(radius_in=1.6, angle_deg=90.0, n=600, length=22.0, seed=1):
    """Object well inside the bore (radius 1.6 < gauge), running along axis."""
    rng = np.random.default_rng(seed)
    ang = np.deg2rad(angle_deg)
    y = np.linspace(1.0, length, n)
    rc = radius_in + rng.normal(0, 0.01, n)
    x = rc * np.cos(ang) + rng.normal(0, 0.02, n)
    z = rc * np.sin(ang) + rng.normal(0, 0.02, n)
    return np.column_stack([x, y, z])


def _ctx(pts):
    ctx = PipelineContext()
    ctx.scans.append(PointCloudBundle(points=pts))
    ctx.active_index = 0
    return ctx


def test_detects_known_intruder():
    shell = _shell()
    intr = _intruder()
    pts = np.vstack([shell, intr]).astype(np.float64)
    truth = np.concatenate([np.zeros(len(shell), bool), np.ones(len(intr), bool)])
    ctx = _ctx(pts)

    # Fixed gauge of 2.2 m: shell (~2.75) is outside, intruder (1.6) is inside.
    res = ClearanceLayer().evaluate(ctx, gauge_radius=2.2)

    pred = res["intruding_mask"]
    tp = int(np.sum(pred & truth)); fp = int(np.sum(pred & ~truth)); fn = int(np.sum(~pred & truth))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    assert recall >= 0.95, f"intruder recall too low: {recall:.2f}"
    assert precision >= 0.95, f"precision too low (shell flagged): {precision:.2f}"
    # Intruder at r=1.6, gauge 2.2 => depth ~0.6 m = 600 mm.
    assert res["max_intrusion_mm"] > 400.0, f"intrusion depth off: {res['max_intrusion_mm']:.0f}"
    assert res["severity"] == "critical"
    return precision, recall, res["max_intrusion_mm"]


def test_clean_tunnel_no_violation():
    ctx = _ctx(_shell(seed=5).astype(np.float64))
    # Auto gauge sits just inside the lining; a clean bore should not intrude.
    res = ClearanceLayer().evaluate(ctx)
    assert res["n_intruding"] == 0, f"clean tunnel flagged {res['n_intruding']} points"
    assert res["severity"] == "ok"
    return res["gauge_radius_m"]


def test_sections_and_chainage():
    shell = _shell(seed=7); intr = _intruder(seed=8)
    ctx = _ctx(np.vstack([shell, intr]).astype(np.float64))
    res = ClearanceLayer().evaluate(ctx, gauge_radius=2.2, section_len=1.0)
    secs = res["sections"]
    assert len(secs) > 0
    assert all("chainage_m" in s and "max_intrusion_mm" in s for s in secs)
    n_bad = sum(1 for s in secs if s["n_intruding"] > 0)
    assert n_bad > 0, "no section reported intrusion"
    return len(secs), n_bad


if __name__ == "__main__":
    p, r, depth = test_detects_known_intruder()
    gauge = test_clean_tunnel_no_violation()
    nsec, nbad = test_sections_and_chainage()
    print("SMOKE TEST PASSED")
    print(f"intruder detection: precision={p:.2f} recall={r:.2f} max_depth={depth:.0f} mm")
    print(f"clean tunnel auto-gauge R={gauge:.2f} m, no violation")
    print(f"sections={nsec}, sections_with_intrusion={nbad}")
