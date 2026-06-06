# Blender Sample-Like Dataset

Synthetic OS1/OS6-style tunnel point clouds generated in Blender.

Files:

- `OS1_blender_tunnel_entire_10cm.txt`: reference/T0 scan, no header, columns `x y z r g b`.
- `OS6_blender_tunnel_entire_10cm.txt`: monitoring/Tn scan, one header line like the real OS6 sample, columns `x y z r g b`.
- `manifest.json`: point counts and expected deformation/clutter behavior.
- `blender_sample_like.blend`: visual scene with reference/deformed clouds and chainage markers.

The dataset uses global coordinates near the real sample scale (`x~748`, `y~-367`, `z~3`) and includes a curved/graded tunnel lining, partial occlusion, cable-like clutter, random outliers, and a local deformation around chainage 38 m.
