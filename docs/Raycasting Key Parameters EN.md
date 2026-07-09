# Key Raycasting Parameters

| Category | Parameter | Value | Note |
| --- | --- | ---: | --- |
| Scene | Blender file | `tunnel_lidar_scene.blend` | Input tunnel scene |
| Mesh | Target object | `Tunnel_Lining` | Raycast surface |
| Epochs | Time steps | `T0-T5` | T0 baseline, T1-T5 deformed |
| Alignment | Curve radius | `500 m` | Horizontal tunnel curve |
| Scanner | TLS stations | `10, 40, 70 m` | Chainage positions |
| Scanner | Scanner height | `-1.3 m` | Tripod height |
| Ray grid | Azimuth step | `1.0°` | Horizontal angular resolution |
| Ray grid | Elevation step | `1.0°` | Vertical angular resolution |
| Ray grid | Elevation range | `-25° to 90°` | Vertical scan range |
| Range | Max range | `60 m` | Raycast cutoff distance |
| Noise | Range noise | `0.002 + 0.00006 × distance` | Distance-dependent noise, in meters |
| Output | Point format | `x y z intensity label` | Text point cloud output |

## Deformation Inputs

| Deformation | Chainage | T5 magnitude |
| --- | ---: | ---: |
| Crown settlement | `20 m` | `-45 mm` |
| Sidewall convergence | `45 m` | `-35 mm` |
| Local damage | `65 m` | `-40 mm` |
