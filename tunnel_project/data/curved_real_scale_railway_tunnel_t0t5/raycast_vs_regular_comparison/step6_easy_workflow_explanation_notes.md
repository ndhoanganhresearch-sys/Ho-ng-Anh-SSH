# Easy presentation script

1. First, I create a curved railway tunnel model in Blender. This model is controlled, so I can use it as the source for all test data.
2. Then I apply known crown settlement values from T0 to T5. This is the ground truth, or the answer key.
3. Next, I create regular clean data by exporting the clean lining surface directly from Blender. This checks the algorithm under ideal conditions.
4. I also create raycast TLS data by simulating laser scanning from multiple stations. This data includes field-like effects such as noise, occlusion and missing points.
5. I run Step 6 on both datasets. Step 6 measures crown settlement at the same location: Crown / Ch 52.0m.
6. Finally, I compare three versions: ground truth, regular tool result and raycast tool result. The error is calculated in millimeters and percent.
7. The result is Regular MAPE = 1.15% and Raycast MAPE = 2.315%. Both pass the validation criteria, so the tool is validated under controlled conditions.
