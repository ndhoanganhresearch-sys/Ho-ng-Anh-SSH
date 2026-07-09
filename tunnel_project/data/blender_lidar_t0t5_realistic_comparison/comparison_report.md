# Raycast vs Regular Comparison

- Regular MAE to GT: 1.10 mm
- Raycast MAE to GT: 1.66 mm
- Raycast MAE to regular: 0.57 mm
- Window: +/-3.0 m, +/-18 deg

| Epoch | Metric | GT | Regular | Raycast | Raycast-GT Err | Raycast-Regular Err |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| T1 | crown_settlement_mm | -5.0 | -4.8 | -4.7 | 0.3 | 0.1 |
| T1 | sidewall_convergence_mm | -2.0 | -1.9 | -2.0 | 0.0 | 0.1 |
| T1 | local_damage_mm | +0.0 | +0.1 | +0.1 | 0.1 | 0.0 |
| T2 | crown_settlement_mm | -12.0 | -11.4 | -11.0 | 1.0 | 0.4 |
| T2 | sidewall_convergence_mm | -8.0 | -7.7 | -6.9 | 1.1 | 0.8 |
| T2 | local_damage_mm | +0.0 | +0.1 | +0.1 | 0.1 | 0.0 |
| T3 | crown_settlement_mm | -21.0 | -20.0 | -19.4 | 1.6 | 0.6 |
| T3 | sidewall_convergence_mm | -16.0 | -15.4 | -15.2 | 0.8 | 0.3 |
| T3 | local_damage_mm | -14.0 | -15.1 | -15.4 | 1.4 | 0.3 |
| T4 | crown_settlement_mm | -32.0 | -30.4 | -29.3 | 2.7 | 1.1 |
| T4 | sidewall_convergence_mm | -27.0 | -26.0 | -25.0 | 2.0 | 1.0 |
| T4 | local_damage_mm | -27.0 | -29.3 | -29.9 | 2.9 | 0.6 |
| T5 | crown_settlement_mm | -48.0 | -45.7 | -44.1 | 3.9 | 1.5 |
| T5 | sidewall_convergence_mm | -40.0 | -38.5 | -37.6 | 2.4 | 0.9 |
| T5 | local_damage_mm | -43.0 | -46.7 | -47.7 | 4.7 | 0.9 |
