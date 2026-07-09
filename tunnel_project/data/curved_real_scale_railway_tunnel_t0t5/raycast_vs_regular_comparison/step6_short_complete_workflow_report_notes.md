# Short presentation script

1. I created a controlled curved railway tunnel in Blender.
2. I applied known crown settlement values from T0 to T5, so this is the ground truth.
3. From the same model, I generated two datasets: regular clean and raycast field-like TLS.
4. Regular clean tests the ideal algorithm condition. Raycast tests field-like scanning robustness.
5. Step 6 measures only crown settlement at Crown / Ch 52.0m.
6. I compare tool output with ground truth using error in mm and percent.
7. Result: Regular MAPE = 1.15%, Raycast MAPE = 2.315%. The raycast error is higher because it includes noise and occlusion, but the trend remains correct from T0 to T5.
