# Crown Settlement Tool Check

This uses the tool core crown-local metric for settlement at the tunnel crown, not whole-cloud p95.

- Regular MAE: 0.48 mm (1.15%)
- Raycast MAE: 1.01 mm (2.31%)

| Epoch | GT mm | Regular crown | Raycast crown | Regular err % | Raycast err % |
| --- | ---: | ---: | ---: | ---: | ---: |
| T0 | +0.0 | +0.0 | +0.0 | +0.0% | +0.0% |
| T1 | -10.0 | -9.9 | -10.2 | +1.0% | -2.4% |
| T2 | -22.0 | -21.7 | -21.6 | +1.4% | +1.7% |
| T3 | -38.0 | -37.6 | -37.1 | +1.1% | +2.4% |
| T4 | -58.0 | -57.3 | -56.6 | +1.2% | +2.4% |
| T5 | -80.0 | -79.1 | -77.9 | +1.1% | +2.6% |
