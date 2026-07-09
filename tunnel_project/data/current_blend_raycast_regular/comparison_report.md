# Current Blender Raycast vs Regular

- Source blend: C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project\data\blender_lidar_t0t5_realistic\blender_lidar_t0t5_realistic.blend
- Lining object: Tunnel_Lining_T5
- Regular mesh samples: 147584
- Raycast total hits: 161972
- Raycast lining hits: 155006
- Exact mesh-surface MAE: 0.000363 mm
- Exact mesh-surface P95: 0.000983 mm
- MAE to regular lining: 70.82 mm
- Median to regular lining: 69.04 mm
- P95 to regular lining: 122.26 mm

Exact mesh-surface metrics compare raycast lining hits against the same current Blender mesh surface.
Nearest regular metrics compare raycast lining hits against the exported regular point file, so they include regular sample spacing.
