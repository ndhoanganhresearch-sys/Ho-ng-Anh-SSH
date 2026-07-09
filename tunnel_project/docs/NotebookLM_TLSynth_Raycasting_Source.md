# TLSynth-Principle Raycasting for Tunnel LiDAR Validation

## Project Goal
This project uses a custom Blender raycasting pipeline to generate synthetic tunnel LiDAR point clouds for validating tunnel deformation analysis. The goal is not to claim direct use of the TLSynth add-on, but to follow the TLSynth principle: virtual scanner rays are cast into a 3D mesh, first hit points are stored as point cloud data, and LiDAR-like noise/intensity are added.

## Recommended Academic Wording
Use: "following the TLSynth principle" or "inspired by TLSynth methodology".
Avoid: "we use TLSynth add-on" unless the add-on is directly integrated.

## Dataset Summary
- Dataset: blender_lidar_t0t5
- Purpose: Blender raycasting LiDAR simulation for realistic time-series deformation testing with occlusion, density gradient, and intensity.
- Method: scene.ray_cast() from 3 scanner positions per epoch, spherical grid 0.5deg resolution
- Units: meters; deformation values in ground_truth.csv are millimeters
- Epochs: T0, T1, T2, T3, T4, T5
- Points per epoch: 527418

## Scanner Configuration
- Scanner type: simulated_TLS
- Horizontal resolution: 0.5 degrees
- Vertical resolution: 0.5 degrees
- Vertical FOV: [-35, 90]
- Max range: 60.0 m
- Noise model: sigma_m = 0.002 + 0.00006 * distance_m
- Intensity model: base_reflectivity[label] * Lambert cosine * distance falloff
- Positions note: Scanners sit on the curved centerline at arc-length (chainage) 10/40/70 m, tripod height z=-1.3 m (~1.5 m above the track bed). X/Y follow the alignment, so they are NOT on a straight Y axis.

## Scanner Positions
- Station 1: chainage 10 m, z=-1.3 m
- Station 2: chainage 40 m, z=-1.3 m
- Station 3: chainage 70 m, z=-1.3 m

## Tunnel Geometry
- type: circular TBM rail tunnel
- geometry: circular ARCH above the floor (NOT a full ring); lining spans crown down to the springline at floor level z=-2.8 m. Below the floor there is no lining (invert/fill), matching a real tunnel scanned from ground up.
- length_m: 80.0
- radius_m: 4.25
- diameter_m: 8.5
- alignment: gentle horizontal curve, radius 500 m, turning toward +X; end lateral offset 6.39 m at arc-length 80 m
- surface_undulation_m: baked as-built waviness ~1.0-1.5 cm RMS (low-freq sin + 5 mm random), constant across epochs (NOT scan noise)

## Deformation Ground Truth
- crown_settlement at chainage 20.0 m: {'T0': 0, 'T1': -5, 'T2': -12, 'T3': -20, 'T4': -30, 'T5': -45}
- sidewall_convergence at chainage 45.0 m: {'T0': 0, 'T1': 0, 'T2': -5, 'T3': -12, 'T4': -22, 'T5': -35}
- local_damage at chainage 65.0 m: {'T0': 0, 'T1': 0, 'T2': 0, 'T3': -15, 'T4': -25, 'T5': -40}

## Why Raycasting Is Useful
Raycasting creates realistic effects that simple synthetic point generation does not capture: occlusion, uneven point density, range-dependent noise, and object-dependent intensity. This makes the dataset more suitable for validating denoise, registration, cross-section analysis, and deformation trend detection.

## Integration Plan
1. Keep the current custom Blender raycasting pipeline.
2. Document it as TLSynth-principle / TLSynth-inspired methodology.
3. Standardize generation scripts for T0 to T5, manifest, registration transforms, and ground truth.
4. Run Step 3 registration validation and Step 6 deformation validation.
5. Only integrate the real TLSynth add-on later if direct tool standardization or comparison is required.

## Key Questions for NotebookLM
- How should this project describe TLSynth-principle raycasting without overclaiming?
- Why is raycasting better than adding random noise to a clean tunnel mesh?
- How do scanner position, FOV, angular resolution, and range-dependent noise affect the point cloud?
- How can T0 to T5 ground truth validate Step 6 deformation analysis?
- What limitations should be disclosed in a paper or thesis?

---

# Existing README Notes

﻿# Blender LiDAR T0-T5 Dataset

Thu muc nay chua bo du lieu mo phong LiDAR trong Blender de test Step 6/time-series deformation cua tool.

## File trong thu muc

| File | Vai tro |
| --- | --- |
| `T0.txt` | Epoch tham chieu/reference, chua co bien dang. |
| `T1.txt` -> `T5.txt` | Cac epoch monitoring, bien dang tang dan theo thoi gian. |
| `ground_truth.csv` | Bang gia tri bien dang that da inject vao tung epoch. |
| `manifest.json` | Mo ta scanner, tunnel, deformation, noise, label va so diem. |
| `tunnel_lidar_scene.blend` | Scene Blender dung de tao/mo phong bo du lieu. |

## Raycasting la gi?

Raycasting co the hieu don gian la: tu vi tri may quet LiDAR, ban ra rat nhieu tia laser ao vao scene Blender. Tia nao cham vao be mat dau tien thi lay diem cham do lam mot diem point cloud.

Vi du mot tia:

```text
Scanner station
      o
       \
        \  tia laser ao
         \
          x  diem va cham voi mat ham
        Tunnel lining mesh
```

Trong Blender, moi tia duoc tinh bang ham dang nhu:

```python
hit, location, normal, face_index, obj, matrix = scene.ray_cast(...)
```

Neu `hit = True`, Blender tra ve:

- `location`: toa do diem ma tia cham vao be mat.
- `normal`: huong phap tuyen be mat tai diem cham.
- `obj`: object bi cham, vi du tunnel lining, cable, light, target sphere.
- `face_index`: mat tam giac/mesh face bi cham.

Noi ngan gon: raycasting bien mesh Blender thanh point cloud giong cach may LiDAR nhin thay moi truong.

## Khac gi voi tao point cloud bang cong thuc?

| Cach tao | Uu diem | Nhuoc diem |
| --- | --- | --- |
| Sinh diem truc tiep bang cong thuc | Nhanh, sach, de kiem soat ground truth | Qua ly tuong, it giong scan that |
| Raycasting trong Blender | Co occlusion, mat do diem khong deu, object che khuat, noise giong TLS hon | Cham hon, can scene Blender va tham so scanner |

Step 6 can du lieu giong scan that hon, nen raycasting huu ich hon vi no tao ra cac van de ma tool se gap ngoai thuc dia.

## Dataset nay raycast nhu the nao?

Theo `manifest.json`:

| Thanh phan | Gia tri |
| --- | --- |
| Scanner type | Simulated TLS / terrestrial laser scanner |
| So tram quet | 3 tram |
| Vi tri tram | chainage 10 m, 40 m, 70 m |
| Horizontal resolution | 0.5 do |
| Vertical resolution | 0.5 do |
| Vertical FOV | -30 do den 90 do |
| Max range | 50 m |
| Noise | `sigma = 0.002 + 0.00006 * distance_m` |
| Intensity | Lambert cosine + distance falloff |
| Points/epoch | 510,602 diem |
| Don vi | meter, deformation trong ground truth la millimeter |

Quy trinh tao mot epoch:

```text
1. Tao mesh ham trong Blender
2. Them cable, light fixture, target sphere
3. Neu la T1-T5 thi bien dang mesh theo ground truth
4. Dat scanner o 3 vi tri
5. Moi scanner ban tia theo luoi goc 0.5 do
6. Tia cham object nao truoc thi lay diem do
7. Them range noise va intensity
8. Ghi thanh Tn.txt
```

## Tai sao raycasting tao occlusion that?

Vi raycasting chi lay diem va cham dau tien tren moi tia.

Neu tia gap cable truoc mat ham:

```text
Scanner o -----> cable x -----> tunnel wall bi che
```

Diem duoc luu la cable, khong phai mat ham phia sau. Do do point cloud co vung bi che khuat that, giong LiDAR ngoai hien truong.

Day la ly do dataset nay tot de test:

- Step 2 denoise: cable/light co the can bi loai bo.
- Step 3 registration: target sphere co the dung lam moc.
- Step 6 deformation: tool phai phan biet bien dang that voi noise/occlusion.

## Bien dang trong T0-T5

Ground truth hien co:

| Dang bien dang | Chainage | T0 | T1 | T2 | T3 | T4 | T5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Crown settlement | 20 m | 0 mm | -5 mm | -12 mm | -20 mm | -30 mm | -45 mm |
| Sidewall convergence | 45 m | 0 mm | 0 mm | -5 mm | -12 mm | -22 mm | -35 mm |
| Local damage | 65 m | 0 mm | 0 mm | 0 mm | -15 mm | -25 mm | -40 mm |

Cac gia tri nay nam trong `ground_truth.csv` va `manifest.json`.

## Dung dataset nay cho Step 6 nhu the nao?

Cach test nhanh:

1. Mo tool bang `run_tunnel_analysis.py`.
2. Load `T0.txt` lam reference.
3. Them `T1.txt` -> `T5.txt` bang `1.3 Add scan station (+)` neu muon test time-series.
4. Chay Step 2 neu muon test denoise/voxel.
5. Step 3 co the bo qua neu giu synthetic registered, vi `manifest.json` ghi registration la identity.
6. Chay Step 4/5 de tao centerline, section va metric.
7. Chay Step 6:
   - `6.1 Plot deformation trend T0→Tn`
   - `6.2 M3C2 deformation map T0→Tn`
   - `6.3 Plot 2D Technical Section T0/Tn`
   - `6.5 Forecast threshold crossing`

Ky vong:

- Gan chainage 20 m: thay crown settlement tang dan.
- Gan chainage 45 m: thay sidewall convergence tang dan.
- Gan chainage 65 m: local damage bat dau ro tu T3.

## Luu y quan trong

- Dataset nay da registered san: cac scanner positions giong nhau giua T0-T5.
- Neu muon test Step 3 auto-align kho hon, can tao ban moi co scanner bias/rigid transform cho Tn.
- Moi file co hon 510k diem, nen co the dung voxel/downsample de UI nhe hon.
- Raycasting khong phai render anh; no la phep tinh giao diem giua tia va mesh 3D.
- Neu mesh/object trong Blender thay doi, point cloud raycast cung thay doi theo.

## Tom tat ngan gon

Raycasting = dat may quet ao trong Blender, ban tia laser ao vao scene, lay diem tia cham dau tien tren mesh/object, them noise/intensity, roi xuat thanh point cloud. Dataset nay dung cach do de tao T0-T5 giong moi truong LiDAR hon, giup Step 6 test deformation/time-series sat thuc te hon.


---

# Existing Raycasting Cheat Sheet

﻿# Raycasting Cheat Sheet

## Mot cau de hieu

Raycasting la viec dat may quet ao trong Blender, ban rat nhieu tia laser ao vao mesh/object, tia cham dau tien o dau thi luu diem do thanh point cloud.

## Cong thuc tu duy

```text
scanner_position + direction_vector * distance = hit_point
```

Blender tu tinh `distance` bang `scene.ray_cast()`.

## Vi sao giong LiDAR?

May LiDAR that cung lam tuong tu:

1. Phat tia laser.
2. Tia cham vat the.
3. May do khoang cach va huong tia.
4. Doi thanh toa do XYZ.
5. Lap lai hang tram nghin/triệu tia.

Trong Blender, ta thay laser that bang tia toan hoc va thay vat the that bang mesh 3D.

## Dataset nay dang mo phong cai gi?

- 3 tram quet tai chainage 10 m, 40 m, 70 m.
- Moi tram quet ban tia 360 do theo ngang.
- Goc dung tu -30 do den 90 do.
- Moi tia cach nhau 0.5 do.
- Tia cham vao tunnel/cable/light/target thi sinh 1 diem.
- Them noise theo khoang cach.
- Tinh intensity gia lap.

## Ket qua tao ra

- `T0.txt`: ham chua bien dang.
- `T1.txt` den `T5.txt`: bien dang tang dan.
- `ground_truth.csv`: dap an dung de doi chieu Step 6.
- `manifest.json`: cau hinh scanner va deformation.

## Dieu quan trong cho Step 6

Step 6 khong chi can du lieu dep. No can du lieu co:

- Occlusion: bi cable/object che.
- Mat do diem khong deu: gan scanner day diem, xa scanner thua diem.
- Noise: diem rung vai mm.
- Bien dang that co ground truth.

Raycasting tao duoc cac van de nay nen tot hon dataset cong thuc qua sach.
