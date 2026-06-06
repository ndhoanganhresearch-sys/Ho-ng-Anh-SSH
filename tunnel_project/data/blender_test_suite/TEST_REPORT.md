# Bao Cao Test Bo Du Lieu Blender Cho Tool Ham

Ngay lap bao cao: 2026-06-06

Bo du lieu: `data/blender_test_suite`

Nguon sinh du lieu: `tools/create_blender_test_dataset.py`

Lenh benchmark: `benchmark_blender_dataset.py`

Ket qua tong quat: **PASS toan bo gate hien tai**

## 1. Muc Tieu

Bo du lieu Blender nay duoc tao de test dong thoi cac tinh nang chinh cua tool ham:

- Load du lieu T0/Tn.
- Trich centerline.
- Tao section va fit hinh hoc mat cat.
- So sanh bien dang T0/Tn.
- Canh bao deformation cuc bo tren 2D/3D.
- Clean noise voi nhieu/outlier/cable.
- Kiem tra clearance/headroom.
- Kiem tra tunnel cong, chainage va section frame.
- Kiem tra du lieu thua/bi che khuat mot phan.

Truc toa do cua dataset:

```text
Y = truc doc ham / chainage
X = ngang trai-phai
Z = phuong dung
Don vi toa do = met
Don vi bien dang ground truth = milimet
```

## 2. Lenh Da Chay

```powershell
..\.venv\Scripts\python.exe -m py_compile tools\create_blender_test_dataset.py smoke_test_blender_dataset.py benchmark_blender_dataset.py
..\.venv\Scripts\python.exe smoke_test_blender_dataset.py
..\.venv\Scripts\python.exe benchmark_blender_dataset.py
```

Ket qua:

```text
SMOKE TEST PASSED
dataset=blender_test_suite cases=6 files_loaded=24

RESULT: ALL PASS
```

Ghi chu: khi loader tao PyVista cloud co xuat hien mot so dong VTK `Unsupported cell type`. Test van pass, du lieu van load dung. Hien tai day la canh bao noisy output, chua phai loi tinh nang.

## 3. Cac Case Trong Dataset

| Case | Diem T0 | Diem Tn | Muc dich |
| --- | ---: | ---: | --- |
| `case_01_clean_reference` | 7,008 | 7,008 | Baseline sach: load, centerline, section, khong canh bao |
| `case_02_local_deformation` | 7,008 | 7,008 | Bien dang cuc bo T0/Tn quanh chainage 0 m |
| `case_03_noise_and_cables` | 7,008 | 8,068 | Clean noise: outlier, cum nhieu ben trong, cable gan crown |
| `case_04_clearance_intrusion` | 7,008 | 8,088 | Clearance/headroom voi vat the xam pham gauge 2.2 m |
| `case_05_curved_centerline` | 7,008 | 7,008 | Ham cong va co do doc nhe de test centerline/section frame |
| `case_06_occlusion_sparse` | 6,441 | 6,441 | Mat mot cung diem de test section fitting voi du lieu thua |

Moi case co cac file:

```text
T0.txt
Tn.txt
T0_labels.txt
Tn_labels.txt
ground_truth.json
```

File co label dung format:

```text
x y z r g b intensity label
```

Label trong dataset:

```text
1 = structure / tunnel lining
2 = noise / outlier
3 = cable
4 = clearance intruder
```

## 4. Ket Qua Tong Hop

| Nhom test | Case | Metric chinh | Ket qua | Danh gia |
| --- | --- | --- | ---: | --- |
| Load du lieu | Tat ca case | File load thanh cong | 24/24 | PASS |
| Clean baseline | `case_01` | C2C p95 | 8.23 mm | PASS |
| Section baseline | `case_01` | So section | 48 | PASS |
| Local deformation | `case_02` | Polar max abs | 83.46 mm | PASS |
| Local warning | `case_02` | Section canh bao | 10 | PASS |
| Clean noise | `case_03` | Noise recall | 0.826 | PASS |
| Clean noise | `case_03` | Lining retention | 0.9999 | PASS |
| Clearance | `case_04` | Precision / recall | 1.00 / 1.00 | PASS |
| Curved centerline | `case_05` | X-span centerline | 2.03 m | PASS |
| Sparse section | `case_06` | Median radius | 3.99 m | PASS |

Runtime benchmark: khoang `0.75 s` cho benchmark logic headless hien tai.

## 5. Chi Tiet Theo Tinh Nang

### 5.1 Load T0/Tn

Tat ca 6 case duoc load thanh cong, gom 24 file input chinh:

```text
6 case x 4 file = 24 file
```

Ket qua nay xac nhan tool doc duoc:

- File 6 cot: `x y z r g b`.
- File 8 cot: `x y z r g b intensity label`.
- Metadata label duoc nhan dung dung voi cac file `_labels.txt`.

Danh gia: **dat yeu cau lam fixture test chuan cho tool**.

### 5.2 Centerline Va Section

Case sach `case_01_clean_reference`:

```text
centerline_points = 48
frames = 48
sections = 48
profile = Circle
median_radius = 3.99997 m
```

Case cong `case_05_curved_centerline`:

```text
sections = 48
median_radius = 3.99925 m
centerline_span_x = 2.03 m
centerline_span_y = 48.01 m
centerline_span_z = 0.18 m
```

Case du lieu thua `case_06_occlusion_sparse`:

```text
sections = 48
median_radius = 3.98906 m
```

Nhan xet:

- Tool fit ban kinh gan dung ground truth 4.0 m.
- Centerline cong co X-span 2.03 m, dung ky vong vi dataset co ham cong.
- Case sparse van tao duoc 48 section va ban kinh gan dung.

Danh gia: **centerline va section dang on voi dataset Blender**.

### 5.3 Deformation T0/Tn

Case `case_02_local_deformation` co ground truth:

```text
crown settlement = -80 mm
sidewall convergence = -50 mm
invert heave = +15 mm
vung bien dang chinh quanh chainage 0 m
```

Ket qua benchmark:

```text
C2C RMSE = 20.35 mm
C2C mean = 12.02 mm
C2C p95 = 50.95 mm
C2C max = 86.54 mm
polar max abs = 83.46 mm
heatmap p95 = 50.95 mm
```

Nhan xet:

- `polar max abs = 83.46 mm` bam sat ground truth crown settlement 80 mm.
- `C2C max = 86.54 mm` hop ly vi co noise va nearest-neighbor effect.
- `C2C p95 = 50.95 mm` cho thay tin hieu bien dang lon hien ro tren heatmap.

Danh gia: **deformation T0/Tn dat yeu cau cho case local deformation**.

### 5.4 Canh Bao Local 2D/3D

Nguong benchmark dang dung trong runner:

```text
abs(polar_deformation) >= 40 mm
```

Ket qua:

```text
warning_sections = 10
warning_chainage_y_min = -4.73 m
warning_chainage_y_max = +4.61 m
```

Ground truth cua dataset:

```text
warning_chainage_m = [-6.0, +6.0]
```

Nhan xet:

- Tool khong highlight toan bo ham.
- Vung canh bao nam cuc bo quanh chainage 0 m.
- Khoang canh bao do duoc `[-4.73, +4.61] m`, nam trong vung ground truth `[-6, +6] m`.

Danh gia: **dat dung muc tieu: canh bao cuc bo, khong lan sai toan tuyen**.

### 5.5 Clean Noise

Case `case_03_noise_and_cables` co:

```text
structure label = 1
noise labels = 2, 3
raw_points = 8,068
```

Ket qua:

```text
n_raw = 8,068
n_clean = 7,191
n_removed = 877
n_radial = 877
label_noise_recall = 0.8264
label_lining_retention = 0.9999
```

Y nghia:

- Noise recall 0.826: tool loai duoc khoang 82.6% diem noise/cable da gan label.
- Lining retention 0.9999: gan nhu giu nguyen diem lining that.
- Ket qua nay tot cho muc tieu hien tai vi uu tien khong lam mat be mat ham.

Nhan xet quan trong:

- Benchmark hien tai bao cao `n_cable = 0`, `n_light = 0`, `n_person = 0`, nhung `n_radial = 877`.
- Nghia la tool dang loai cac diem nhieu chu yeu bang radial/statistical stage, khong phai semantic cable detector.
- Ket qua dau ra van dat gate, nhung neu bai bao muon claim “phat hien cable rieng”, can them benchmark semantic ro hon.

Danh gia: **clean noise dat cho muc tieu lam sach diem nhieu va giu lining; chua nen claim manh ve semantic cable classification**.

### 5.6 Clearance / Headroom

Case `case_04_clearance_intrusion` co intruder label 4, gauge radius 2.2 m.

Ket qua:

```text
n_intruding = 1080
max_intrusion_mm = 870.29 mm
severity = critical
sections = 49
sections_with_intrusion = 37
precision_vs_label = 1.00
recall_vs_label = 1.00
tp = 1080
fp = 0
fn = 0
```

Nhan xet:

- Tool bat dung toan bo intruder da gan label.
- Khong co false positive trong fixture nay.
- Do xam pham toi da 870 mm la hop ly vi intruder nam sau ben trong gauge.

Danh gia: **clearance/headroom dat rat tot tren fixture Blender**.

## 6. Ket Luan

Bo dataset Blender hien tai du dieu kien lam **bo test chuan dau tien** cho cac tinh nang chinh cua tool.

Ket qua manh nhat:

- Load/metadata: PASS.
- Centerline/section: PASS.
- Local deformation: PASS, max bien dang do duoc 83.46 mm voi ground truth 80 mm.
- Local warning: PASS, chi canh bao 10 section quanh vung bien dang.
- Clean noise: PASS, recall 0.826 va lining retention 0.9999.
- Clearance: PASS, precision/recall 1.00.

## 7. Han Che Va Viec Nen Lam Tiep

Nhung diem can luu y:

- Day la dataset synthetic tu Blender, chua thay the du lieu scan thuc te.
- Can test them voi `.las/.ply` neu muon benchmark format thuc dia.
- Can chup screenshot 2D/3D trong UI de xac nhan visual warning, vi benchmark hien tai la headless logic test.
- Clean-noise semantic cable detector chua duoc chung minh rieng; hien tai ket qua tot nhung do radial/statistical filtering la chinh.
- VTK warning output nen duoc lam gon neu muon log test sach hon.

Viec nen lam tiep:

1. Mo UI, load `case_02_local_deformation`, chup 2D va 3D warning.
2. Load `case_03_noise_and_cables`, so sanh truoc/sau clean noise bang hinh.
3. Load `case_04_clearance_intrusion`, xac nhan warning 3D clearance.
4. Tao `MATERIAL_PASSPORT` cho cac hinh va bang neu dua vao bai bao.
5. Chay lai benchmark nay moi khi sua deformation, clean noise, centerline hoac clearance.

