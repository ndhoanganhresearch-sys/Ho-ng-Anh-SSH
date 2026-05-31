# -*- coding: utf-8 -*-
"""Smoke tests for parameter presentation helpers (format_parameter).

Run from the tunnel_project directory:
    python smoke_test_param_format.py

Checks unit formatting by suffix, threshold classification (OK/CAUTION/CRITICAL),
string passthrough (reference), NaN handling, integer counts, and unknown-key
fallback - the contract relied on by the Results log, auto summary, and the
Parameters table.
"""
import math

from tunnel_analysis.common import format_parameter, classify_parameter


def test_units():
    assert format_parameter("crown_settlement_max_mm", 12.345)[1] == "12.35 mm"
    assert format_parameter("ovality_mean_pct", 0.4)[1] == "0.400 %"
    assert format_parameter("width_Tn_mean_m", 5.5)[1] == "5.500 m"
    assert format_parameter("wall_angle_L_deg", 87.6)[1].endswith("\u00b0")
    assert format_parameter("n_sections", 80)[1] == "80"
    return "units OK"


def test_status_bands():
    assert classify_parameter("crown_settlement_mm", 3.0) == "OK"
    assert classify_parameter("crown_settlement_mm", 12.0) == "CAUTION"
    assert classify_parameter("crown_settlement_mm", 30.0) == "CRITICAL"
    # mean/max variants share the band
    assert classify_parameter("crown_settlement_max_mm", 30.0) == "CRITICAL"
    assert classify_parameter("ovality_max_pct", 1.5) == "CRITICAL"
    # magnitude (negative settlement judged by abs)
    assert classify_parameter("crown_settlement_mm", -30.0) == "CRITICAL"
    return "status OK"


def test_strings_and_nan():
    label, text, status = format_parameter("reference", "single_scan_global")
    assert "absolute geometry" in text, text
    assert status == ""
    label, text, status = format_parameter("crown_settlement_mm", float("nan"))
    assert text == "n/a", text
    return "string+nan OK"


def test_unknown_key():
    label, text, status = format_parameter("weird_metric", 7.0)
    assert label == "weird_metric"
    assert status == ""
    assert text == "7.0000"
    return "unknown-key OK"


def test_no_threshold_returns_blank():
    # a real key without a defined band
    assert classify_parameter("crown_B_mean_m", 2.9) == ""
    return "no-threshold OK"


if __name__ == "__main__":
    for fn in (test_units, test_status_bands, test_strings_and_nan,
               test_unknown_key, test_no_threshold_returns_blank):
        print(fn.__name__, "->", fn())
    print("SMOKE TEST PASSED")
