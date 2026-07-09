# Curved Regular vs Raycast Comparison

This benchmark compares clean mesh-sampled lining points against field-like TLS raycast lining points.

- Regular MAE to ground truth: 0.40 mm
- Raycast MAE to ground truth: 0.84 mm
- Raycast MAE to regular: 0.47 mm
- Crown check chainage: 52.0 m on curved centerline R=420 m

| Epoch | GT mm | Regular mm | Raycast mm | Regular err | Raycast err | Raycast-Regular |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| T0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| T1 | -10.0 | -9.9 | -10.2 | +0.1 | -0.2 | -0.3 |
| T2 | -22.0 | -21.7 | -21.6 | +0.3 | +0.4 | +0.1 |
| T3 | -38.0 | -37.6 | -37.1 | +0.4 | +0.9 | +0.5 |
| T4 | -58.0 | -57.3 | -56.6 | +0.7 | +1.4 | +0.7 |
| T5 | -80.0 | -79.1 | -77.9 | +0.9 | +2.1 | +1.2 |
