# Crown Settlement Test Table

- Main metric: `crown_settlement_mm`
- Measured point: `Crown / Đỉnh hầm`
- Location: `Ch 52.0m`
- Regular MAPE: `1.15%`
- Raycast MAPE: `2.315%`

| Time | Ground truth (mm) | Regular tool (mm) | Raycast tool (mm) | Regular error (mm) | Raycast error (mm) | Regular error (%) | Raycast error (%) | Regular points | Raycast points |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| T0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 10710 | 8455 |
| T1 | -10.0 | -9.9 | -10.243 | 0.1 | -0.243 | 1.0 | -2.43 | 10710 | 8379 |
| T2 | -22.0 | -21.7 | -21.632 | 0.3 | 0.368 | 1.364 | 1.673 | 10710 | 8366 |
| T3 | -38.0 | -37.6 | -37.07 | 0.4 | 0.93 | 1.053 | 2.447 | 10710 | 8371 |
| T4 | -58.0 | -57.3 | -56.607 | 0.7 | 1.393 | 1.207 | 2.402 | 10710 | 8393 |
| T5 | -80.0 | -79.1 | -77.9 | 0.9 | 2.1 | 1.125 | 2.625 | 10710 | 8373 |

## Pass Criteria

- Regular MAPE should stay around `1–2%`.
- Raycast MAPE should stay around `2–4%`.
- Trend must increase in settlement magnitude from `T0` to `T5`.
- `Result`/warning logic in Step 6 should use `abs(crown_settlement_mm)`, not M3C2/p95.
