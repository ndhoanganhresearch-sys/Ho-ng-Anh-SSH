# Raycasting Cheat Sheet

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
