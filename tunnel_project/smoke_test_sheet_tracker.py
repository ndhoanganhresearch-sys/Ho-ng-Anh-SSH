"""Smoke tests for sheet_tracker.MonitoringTracker.

Run from the tunnel_project directory:
    python smoke_test_sheet_tracker.py

Covers: alert classification, CSV append/load round-trip, trend extraction,
and parameter-dict ingestion. Pure standard library; no GUI/network needed.
"""
import os
import tempfile

import sheet_tracker as st


def test_classify_uses_absolute_value():
    assert st.classify("crown_settlement_mm", 0.0) == "ok"
    assert st.classify("crown_settlement_mm", 12.0) == "caution"
    assert st.classify("crown_settlement_mm", -26.0) == "critical"
    assert st.classify("crown_settlement_mm", None) == "n/a"
    assert st.classify("unknown_metric", 99.0) == "n/a"
    return True


def test_record_load_roundtrip():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "campaigns.csv")
    tracker = st.MonitoringTracker(path)

    tracker.record_campaign(
        "T0",
        {"crown_settlement_mm": 0.0, "lateral_convergence_mm": 0.0,
         "ovality_mean_pct": 0.1, "eccentricity_mean_mm": 2.0},
        timestamp="2026-01-01T00:00:00Z",
    )
    tracker.record_campaign(
        "T1",
        {"crown_settlement_mm": 12.0, "lateral_convergence_mm": 5.0,
         "ovality_mean_pct": 0.3, "eccentricity_mean_mm": 4.0},
        timestamp="2026-02-01T00:00:00Z",
    )
    t2 = tracker.record_campaign(
        "T2",
        {"crown_settlement_mm": 28.0, "lateral_convergence_mm": 33.0,
         "ovality_mean_pct": 1.2, "eccentricity_mean_mm": 9.0},
        timestamp="2026-03-01T00:00:00Z",
    )

    records = tracker.load()
    assert [r.label for r in records] == ["T0", "T1", "T2"]
    assert records[0].overall_status == "ok"
    assert records[1].overall_status == "caution"
    assert t2.overall_status == "critical"
    assert tracker.latest().label == "T2"
    return [r.overall_status for r in records]


def test_trend_extraction():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "campaigns.csv")
    tracker = st.MonitoringTracker(path)
    for i, val in enumerate([0.0, 4.0, 9.0]):
        tracker.record_campaign(f"T{i}", {"crown_settlement_mm": val},
                                timestamp=f"2026-0{i + 1}-01T00:00:00Z")
    trend = tracker.trend("crown_settlement_mm")
    assert trend == [("T0", 0.0), ("T1", 4.0), ("T2", 9.0)], trend
    raised = False
    try:
        tracker.trend("nope")
    except KeyError:
        raised = True
    assert raised, "trend() must reject unknown metric keys"
    return trend


def test_metrics_from_parameters_filters():
    params = {
        "crown_settlement_mm": 5.0,
        "lateral_convergence_mm": 7.5,
        "ovality_mean_pct": float("nan"),
        "junk": "ignore-me",
        "eccentricity_mean_mm": None,
    }
    out = st.metrics_from_parameters(params)
    assert out == {"crown_settlement_mm": 5.0, "lateral_convergence_mm": 7.5}, out
    return out


if __name__ == "__main__":
    classify_ok = test_classify_uses_absolute_value()
    statuses = test_record_load_roundtrip()
    trend = test_trend_extraction()
    metrics = test_metrics_from_parameters_filters()
    print("SMOKE TEST PASSED")
    print(f"Classification checks: {classify_ok}")
    print(f"Campaign statuses: {statuses}")
    print(f"Crown settlement trend: {trend}")
    print(f"Filtered metrics: {metrics}")
