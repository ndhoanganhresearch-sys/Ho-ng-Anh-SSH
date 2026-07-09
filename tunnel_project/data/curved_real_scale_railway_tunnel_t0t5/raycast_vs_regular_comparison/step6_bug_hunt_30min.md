# Step 6 Bug Hunt Report - 30 Minutes

## Summary
- Static compile: PASS.
- Crown benchmark: PASS, within acceptance.
- Whole-cloud/M3C2 benchmark: PASS as secondary metric, but not comparable to crown GT.
- Main issue found: Excel/PDF time-series exports still use old p95/rate/acceleration layout and can conflict with the simplified UI table.

## Verified Results
- Crown metric: `crown_settlement_mm`.
- Crown chainage: `52.0 m`.
- Regular MAE/MAPE: `0.48 mm` / `1.15%`.
- Raycast MAE/MAPE: `1.007 mm` / `2.315%`.
- Expected raycast status by crown:
  - T1: Warning
  - T2: Warning
  - T3: Danger
  - T4: Danger
  - T5: Danger

## Bugs / Issues

### HIGH - Excel time-series export header/data mismatch
- File: `tunnel_analysis/exporter.py`.
- Repro:
  1. Run Step 6 time-series.
  2. Export Excel time-series report.
  3. Inspect `Time-Series` sheet.
- Expected:
  - Columns match simplified UI: time, crown settlement, new crown move, whole-cloud p95, result/points.
  - If Excel keeps extra metrics, header and row values must still align.
- Actual:
  - Header includes `Crown settlement (mm)`.
  - Row values do not insert crown at the matching position, so later values shift under wrong headers.
- Risk:
  - User may read p95/max/median values as crown settlement.

### MEDIUM - PDF time-series report still shows old p95/rate/accel story
- File: `tunnel_analysis/pdf_reporter.py`.
- Repro:
  1. Export time-series PDF after Step 6.
  2. Inspect chart and table.
- Expected:
  - PDF should match simplified Step 6 UI and emphasize crown settlement.
- Actual:
  - PDF chart/table still show cumulative p95, max, incremental p95, rate, acceleration.
- Risk:
  - PDF contradicts the simplified UI and may confuse crown settlement interpretation.

### MEDIUM - Log text still mentions incremental p95/rate/acceleration
- File: `tunnel_analysis/ui/main_window.py`, `_report_timeseries_extras`.
- Repro:
  1. Run Step 6 time-series.
  2. Read log panel.
- Expected:
  - Log should emphasize crown settlement and new crown move.
- Actual:
  - Log still prints incremental p95/rate/accel.
- Risk:
  - Logs imply p95/rate are primary, while UI now uses crown as primary.

### LOW - UI copy still uses English technical term `Whole-cloud p95`
- File: `tunnel_analysis/ui/widgets.py`.
- Repro:
  1. Open Step 6 trend and table.
- Expected:
  - User-friendly label, e.g. `Overall movement p95` or Vietnamese label.
- Actual:
  - Label is technically correct but may be hard for users.
- Risk:
  - User may ask again what whole-cloud means.

## No Blockers Found
- `py_compile` passed for Step 6 files.
- Crown benchmark passed.
- M3C2/p95 benchmark ran successfully.
- Standalone 6.3 logic has auto-prepare path present (`6.3_sections_auto`), but full GUI click behavior still needs manual visual confirmation.

## Recommended Fix Order
1. Fix Excel export header/value mismatch first.
2. Simplify PDF time-series report to match UI.
3. Change log text to crown-first.
4. Optionally rename `Whole-cloud p95` to a friendlier label.
