# Full Test Dataset — curved ~1 km tunnel, 4 defect spots

Pure-NumPy synthetic. Load `T0_full.las` + `Tn_full.las` (or .txt) to self-test.

- Curved 1000 m tunnel (arc radius 2500 m, grade 0.4%)
- 5 sphere targets at ch [120.0, 320.0, 520.0, 720.0, 920.0] m (registration)

## 4 defect spots (well separated)
| Chainage | Defect |
|---|---|
| ~200 m | crown settlement −60 mm |
| ~450 m | sidewall convergence −50 mm/side |
| ~700 m | noise: cable (140 pts) + outlier blob (30 pts) |
| ~900 m | combined crown −45 + convergence −45 mm |

## Workflow
1. **1.1 Import** → `T0_full.las`
2. **1.2 Add scan station** → `Tn_full.las`
3. **3.1 Auto-align T0/Tn** (targets)
4. **2.2 Clean noise** → removes the ch-700 cable + blob
5. **AUTO PIPELINE** → centerline (curved), sections, deformation, warnings
   Expect warnings at ch ~200, ~450, ~900 m.
6. **7.x** → export CSV / Excel / PDF.
