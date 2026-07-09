# Raycasting Parameters Table

| Nhóm | Thông số | Giá trị | Đơn vị | Ý nghĩa |
| --- | --- | ---: | --- | --- |
| Scene | `BLEND` | `tunnel_lidar_scene.blend` | file | Blender scene dùng để raycast |
| Scene | `LINING` | `Tunnel_Lining` | object | Mesh tunnel lining được bắn tia |
| Epoch | `EPOCH` | `T0`-`T5` | epoch | Mốc thời gian/deformation cần tạo point cloud |
| Hình học | `R` | `500.0` | m | Bán kính cong tuyến hầm theo phương ngang |
| Hình học | `radius_m` | `4.25` | m | Bán kính mặt cắt tunnel trong metadata |
| Hình học | `chainage` | arc length | m | Chainage tính theo chiều dài cung |
| Scanner | `STATION_S` | `10, 40, 70` | m | Vị trí 3 trạm TLS theo chainage |
| Scanner | `STATION_Z` | `-1.3` | m | Cao độ tripod/scanner |
| Ray grid | `DA` | `1.0` | độ | Bước quét azimuth |
| Ray grid | `DE` | `1.0` | độ | Bước quét elevation |
| Ray grid | `EL0` | `-25.0` | độ | Góc elevation bắt đầu |
| Ray grid | `EL1` | `90.0` | độ | Góc elevation kết thúc |
| Ray grid | `MAXR` | `60.0` | m | Tầm bắn raycast tối đa |
| Noise | `SEED` | `0` | - | Seed cố định để T0/Tn có cùng chuỗi noise |
| Noise | `sigma` | `0.002 + 0.00006 * dist` | m | Mô hình nhiễu tăng theo khoảng cách |
| Output | Format | `x y z intensity label` | txt | Cấu trúc mỗi điểm raycast |
| Output | `label` | `1` | class | Nhãn tunnel lining |

## Deformation Specs

| Loại biến dạng | Chainage | Sigma | Góc theta | T1 | T2 | T3 | T4 | T5 | Đơn vị |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Crown settlement | `20.0` | `3.0` | `90°` | `-5` | `-12` | `-20` | `-30` | `-45` | mm |
| Sidewall convergence | `45.0` | `3.0` | `0°` | `0` | `-5` | `-12` | `-22` | `-35` | mm |
| Local damage | `65.0` | `1.2` | `55°` | `0` | `0` | `-15` | `-25` | `-40` | mm |

## Code Location

- Main script: `tunnel_project/tools/raycast_tunnel_epochs.py`
- Raycast function: `tunnel_project/tools/raycast_tunnel_epochs.py:136`
- BVH ray call: `tunnel_project/tools/raycast_tunnel_epochs.py:149`
- Output writer: `tunnel_project/tools/raycast_tunnel_epochs.py:155`
