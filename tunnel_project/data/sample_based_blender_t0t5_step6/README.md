# Sample-Based Blender T0-T5 Step 6 Dataset

This is based on the real sample point cloud, not a procedural tunnel.

## Source

- Source point cloud: `C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project\data\sample_pcd\u-type_tunnel_0k630 cut_1.las`
- Points per LAS epoch: `498,557`
- Blender preview points per epoch: up to `80,000`

## Method

1. Use the sample point cloud as T0.
2. Create T1-T5 by applying controlled Step 6 deformation to the same sample points.
3. Export LAS/TXT for the tool.
4. Use Blender MCP to create six point-cloud tunnel objects from preview samples for visual inspection.
5. No raycasting is used.

## Ground truth

- Crown settlement: 0 to -36 mm
- Sidewall convergence: 0 to -24 mm
- Local damage: starts at T3 and reaches -30 mm

## Test

Load `T0.las` as reference, add `T1.las` to `T5.las`, then run Step 6.
