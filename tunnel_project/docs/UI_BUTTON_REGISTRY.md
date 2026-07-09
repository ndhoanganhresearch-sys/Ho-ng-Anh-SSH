# UI Button Registry

Muc tieu cua file nay la quan ly nut UI theo trang thai, de tool don gian hon ma khong xoa tinh nang.

## Trang thai

| Status | Y nghia |
|---|---|
| Public | Hien trong UI mac dinh, phuc vu workflow chinh. |
| Advanced | An mac dinh, dung cho debug/benchmark/manual verification. |
| Internal | Khong can nut rieng, nhung function/module van duoc pipeline goi. |
| Deprecated | Chua xoa, nhung khong nen dung cho workflow moi neu da co thay the. |

## Nguyen tac

- Khong xoa nut Advanced neu chua co ly do ro rang.
- Khong doi ten nut hien co neu khong duoc yeu cau.
- Nut Public la workflow don gian cho nguoi dung.
- Nut Advanced giu lai de debug khi nut tong hop chay sai.
- Khi sua pipeline, uu tien goi lai function cu thay vi viet lai logic.

## Cach dieu khien UI

Trong `tunnel_analysis/ui/main_window.py`:

- `CORE_FEATURES_ONLY = True`: bat che do UI gon.
- `SHOW_ADVANCED_BUTTONS = False`: an cac nut Advanced.
- Doi `SHOW_ADVANCED_BUTTONS = True` de hien lai tat ca nut ky thuat.

## Registry hien tai

| Step | Button | Slot | Status | Ly do giu |
|---|---|---|---|---|
| 1 | 1.1 Import LAS / PLY data | `_slot_1_1_import` | Public | Nap du lieu chinh. |
| 1 | 1.2 Initialize 3D viewport | `_slot_1_2_viewport` | Advanced | Viewport thuong tu khoi tao; giu de debug. |
| 1 | 1.3 Add scan station (+) | `_slot_1_3_add_scan` | Public | Them tram quet/epoch. |
| 1 | 1.4 Register & merge all stations | `_slot_1_4_merge` | Advanced | Ghep tram rieng, co the dung debug. |
| 1 | 1.8 Load T0 and Tn epochs | `_slot_1_8_epochs` | Advanced | Workflow T0/Tn co the thay bang load scan hien co; giu cho debug. |
| 1 | 1.5 Rough alignment (manual) | `_slot_1_5_rough` | Advanced | Manual/debug alignment. |
| 1 | 1.6 Chain register & merge | `_slot_1_6_chain` | Advanced | Debug chain registration. |
| 1 | 1.7 Registration error heatmap | `_slot_1_7_reg_error` | Advanced | Diagnostics. |
| 2 | 2.0 Range crop (drop far points) | `_slot_2_0_range_crop` | Advanced | Manual preprocessing. |
| 2 | 2.1 Voxel downsampling | `_slot_2_1_voxel` | Public | Giam diem nhanh, huu ich truoc khi chay pipeline. |
| 2 | 2.5 Clean noise (auto: cables, lights, people, wall cables) | `_slot_2_5_auto_denoise` | Public | Nut clean chinh. |
| 2 | 2.2 Statistical outlier removal | `_slot_2_2_sor` | Advanced | Debug/filter rieng. |
| 2 | 2.3 Extract tunnel lining shell | `_slot_2_3_lining` | Advanced | Lining extraction rieng, giu debug. |
| 2 | 2.3b Extract lining by label (FY387/STSD) | `_slot_2_3b_lining_label` | Advanced | Dataset co label. |
| 2 | 2.4 Semantic noise removal (PDF 3.2) | `_slot_2_4_semantic` | Advanced | Experimental/reference. |
| 2 | 2.6 Extract lining (density-variation) | `_slot_2_6_density_lining` | Advanced | Alternative lining method. |
| 3 | 3.0 Auto-align T0/Tn epochs (target or ICP) | `_slot_3_0_register_epochs` | Public | Registration chinh. |
| 3 | 3.1 Anchor translation | `_slot_3_1_anchor` | Advanced | Coarse/debug only. |
| 3 | 3.2 Fine surface ICP | `_slot_3_2_icp` | Advanced | Refine/debug only. |
| 3 | 3.3 Calculate RMSE | `_slot_3_3_rmse` | Advanced | Diagnostics, co the public neu can. |
| 4 | 4.1 Extract PCA centerline | `_slot_4_1_centerline` | Advanced | Method rieng. |
| 4 | 4.2 Iterative centerline refinement | `_slot_4_2_iterative` | Advanced | Method rieng. |
| 4 | 4.3 Smooth B-Spline centerline | `_slot_4_3_bspline` | Advanced | Method rieng. |
| 4 | 4.3b B-Spline C2 centerline (PDF 3.4) | `_slot_4_3b_bspline` | Public | Centerline workflow chinh hien tai. |
| 4 | 4.4 Generate gravity-aligned N-B sections | `_slot_4_4_frenet` | Advanced | Advanced frame generation. |
| 4 | 4.5 Detect ring seams | `_slot_4_5_seams` | Advanced | Segmentation/debug. |
| 4 | 4.5b Intensity ring seam detection (PDF 3.3) | `_slot_4_5b_intensity_seams` | Advanced | Experimental/reference. |
| 5 | 5.1 Crown settlement dv | `_slot_5_1_settlement` | Public | Metric chinh. |
| 5 | 5.2 Horizontal convergence dh | `_slot_5_2_convergence` | Public | Metric chinh. |
| 5 | 5.3 3D deformation heatmap | `_slot_5_3_heatmap` | Advanced | Visualization/debug. |
| 5 | 5.3b Hausdorff heatmap T0/Tn (PDF 3.5) | `_slot_5_3b_hausdorff` | Advanced | Experimental/reference. |
| 5 | 5.4 Polar radial deformation dr | `_slot_5_4_polar` | Advanced | Visualization/debug. |
| 5 | 5.5 Ovality epsilon | `_slot_5_5_ovality` | Public | Metric chinh. |
| 5 | 5.6 Section eccentricity e | `_slot_5_6_eccentricity` | Public | Metric chinh. |
| 5 | 5.8 Deformation / clearance 3D warning map | `_slot_5_8_clearance_3d` | Advanced | Visualization/debug. |
| 6 | 6.1 Deformation trend + forecast T0→Tn | `_slot_6_2_plot` | Public | Trend + forecast gop chung (gom 6.5 cu). |
| 6 | 6.2 M3C2 deformation map T0→Tn | `_slot_6_3_m3c2` | Public | 4D/M3C2 map. |
| 6 | 6.3 Plot 2D Technical Section T0/Tn | `_slot_5_7_sections` | Public | Mat cat 2D chinh. |
| 7 | 6.6 Export time-series report (Excel/PDF) | `_slot_6_6_export_timeseries` | Public | Export time-series (chuyen sang Step 7). |
| - | (6.5 Forecast threshold crossing) | `_slot_6_5_forecast` | Retired | Da gop vao 6.1; slot+handler giu lai, khong co nut. |
| 7 | 7.1 Export IFC tunnel structure | `_slot_7_1_ifc` | Public | BIM export chinh. |
| 7 | 7.1b Export IFC4X3 (IfcAlignment) | `_slot_7_1b_ifc_alignment` | Advanced | IFC advanced/infrastructure. |
| 7 | 7.1c Export IFC + components (cables/lights) | `_slot_7_1c_ifc_components` | Advanced | Component BIM advanced. |
| 7 | 8.1 Export section CSV | `_slot_8_1_csv` | Public | Raw/result export. |
| 7 | 8.2 Export Excel report | `_slot_8_2_excel` | Public | Report bang. |
| 7 | 8.3 Export PDF report | `_slot_8_3_pdf` | Public | Report doc. |
| 7 | 8.5 Generate AI work order (PDF) | `_slot_8_5_work_order` | Public | Work order. |
| 7 | 7.2 Query structural AI assistant | `_slot_7_2_query_ai` | Public | AI assistant. |
| 8 | 8.4 Open web dashboard | `_slot_8_4_web` | Advanced | Optional web view. |

## Ghi chu

- Step 8 hien dang an trong UI gon de giu tong the 7 step nhu mong muon.
- Cac nut Advanced khong bi xoa; chi khong render trong UI gon.
- Muon hien Advanced/debug buttons: tick `Show Advanced` trong sidebar, dong tool va mo lai.
- Gia tri mac dinh nam o `SHOW_ADVANCED_BUTTONS`; lua chon cua user duoc luu trong `QSettings` key `ui/show_advanced_buttons`.

## Step 6 internal key map (2026-07-09)
- Visible `6.1` trend -> worker key `6.1_plot` (legacy alias `6.2_plot`)
- Visible `6.2` M3C2 -> worker key `6.2_m3c2` (legacy alias `6.3_m3c2`)
- Visible `6.3` sections -> `6.3_sections_auto` / section path
- Visible `6.6` export -> `6.6_export_ts` (pair T0/Tn and multi-epoch)
- Retired visible `6.5` forecast remains internal-only / merged into 6.1
- Visible `1.9b` demo T0~T5 -> `_slot_1_9_demo_timeseries` (loads `data/time_series_deformation`, reuses `1.9_epoch_folder` worker)
- Visible core acquire loaders: `1.1`, `1.3`, `1.9b`.
- `1.9 Load epoch folder T0→Tn` remains available only when Advanced buttons are shown (slot `_slot_1_9_epoch_folder` kept).
