# Validation Report: T0 vs T5

Measured directly from raycast point clouds (no GUI).

| Metric | Chainage | GT (mm) | Measured (mm) | Error (mm) | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| crown_settlement | 20 | -45.0 | -46.9 | 1.9 | PASS |
| sidewall_convergence | 45 | -35.0 | -32.7 | 2.3 | PASS |
| local_damage | 65 | -40.0 | -34.5 | 5.5 | PASS |

**MAE:** 3.2 mm  | tolerance 8 mm/peak

## Verdict

PASS - raycast deformation recovered within tolerance.

Window: +/-0.75 m arc-length, +/-10 deg angular around each peak.
