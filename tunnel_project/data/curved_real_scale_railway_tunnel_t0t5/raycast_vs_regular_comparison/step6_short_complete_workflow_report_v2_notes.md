# Short presentation script v2

1. I created one controlled curved railway tunnel in Blender.
2. I applied known crown settlement values from T0 to T5, so this is the ground truth.
3. From the same model, I generated two datasets: regular clean and raycast field-like TLS.
4. Regular clean tests ideal algorithm accuracy; raycast TLS tests field-like robustness.
5. Step 6 measures only crown settlement at the same location: Crown / Ch 52.0m.
6. I compare tool output with ground truth using error in mm and percent.
7. Validation criteria are Regular MAPE < 2% and Raycast MAPE < 5%.
8. Results pass: Regular MAPE = 1.15%, Raycast MAPE = 2.315%.
9. The raycast error is higher because it includes noise and occlusion, but the settlement trend remains correct from T0 to T5.
