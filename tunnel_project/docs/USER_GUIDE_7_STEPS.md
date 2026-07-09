# 7-Step User Guide

Muc tieu: huong dan bam tool theo workflow gon, de hieu, khong mat tinh nang. Cac nut Advanced van con trong code va co the hien bang `Show Advanced` khi can debug.

## Workflow mac dinh

| Step | Nguoi dung can lam | Nut chinh | Ket qua mong doi |
| --- | --- | --- | --- |
| 1 | Nap du lieu T0/Tn hoac them nhieu tram quet | `1.1 Import LAS / PLY data`, `1.3 Add scan station (+)` | Tool co reference T0 va epoch/scan can so sanh |
| 2 | Giam diem va loai nhieu tu dong | `2.1 Voxel downsampling`, `2.5 Clean noise` | Point cloud gon hon, bot cable/light/people/noise |
| 3 | Can chinh Tn ve T0 | `3.0 Auto-align T0/Tn epochs` | Tn duoc align, co RMSE/ket qua dang ky |
| 4 | Tao centerline va mat cat | `4.3b B-Spline C2 centerline` | Co centerline, frame/mat cat doc ham |
| 5 | Tinh thong so bien dang | `5.1`, `5.2`, `5.5`, `5.6` | Co settlement, convergence, ovality, eccentricity |
| 6 | Xem bien dang theo thoi gian/khong gian | `6.1`, `6.2`, `6.3`, `6.5` | Co chart, M3C2 map, 2D section, forecast |
| 7 | Xuat ket qua va hoi AI | `7.1`, `8.1`, `8.2`, `8.3`, `8.5`, `7.2` | Co IFC/CSV/Excel/PDF/work order/AI answer |

## Khi nao dung Show Advanced

Dung `Show Advanced` khi can:

- Debug registration rieng tung buoc: anchor, ICP, RMSE.
- So sanh method centerline/segmentation khac nhau.
- Kiem tra heatmap/phuong phap experimental.
- Xuat IFC advanced hoac web dashboard.

Sau khi tick `Show Advanced`, dong tool va mo lai de sidebar ap dung.

## Quy tac demo nhanh

1. Dung dataset nho truoc de tranh cham UI.
2. Chay Step 1 -> Step 6 truoc khi xuat report.
3. Neu warning xuat hien, kiem tra ca `2D Cross-Section` va 3D viewport.
4. Khi export xong, tool se hoi co mo file vua tao khong.
5. Neu ket qua bat thuong, khong sua threshold voi; chay benchmark/test truoc.

## Kiem tra sau khi sua tool

```powershell
cd "C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project"
.\agent_verify.ps1 quick
```

Neu sua Step 3, Step 5 hoac Step 6:

```powershell
.\agent_verify.ps1 step6
```
