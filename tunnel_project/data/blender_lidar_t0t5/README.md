# Blender LiDAR T0-T5 Dataset

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
