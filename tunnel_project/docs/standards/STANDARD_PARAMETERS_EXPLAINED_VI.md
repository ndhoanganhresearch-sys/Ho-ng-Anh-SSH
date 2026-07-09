# Standard Parameters Register - Ghi chú giải thích nhanh

Tài liệu này giải thích các thông số trong bảng **Standard Parameters Register** của dự án `tunnel_project`.
Mục đích là để khi quên, có thể đọc lại nhanh: thông số đó nghĩa là gì, tool dùng ở đâu, và cần lưu ý gì khi trình bày cho khách hàng/kỹ sư.

> Lưu ý quan trọng: nhiều thông số hiện là **project default / engineering threshold** của tool. Không nên nói là đã được tiêu chuẩn PDF Hàn xác nhận trực tiếp nếu chưa có nguồn trang/mục rõ ràng.

---

## 1. Ý nghĩa các trạng thái nguồn

Bảng register thường có các trạng thái sau:

| Trạng thái | Ý nghĩa |
| --- | --- |
| `verified` | Có nguồn tiêu chuẩn khớp trực tiếp theo trang/mục. |
| `unverified` | Tool đang dùng, nhưng chưa tìm thấy nguồn tiêu chuẩn xác nhận trực tiếp. |
| `project default` | Giá trị mặc định nội bộ của dự án/tool. |
| `needs review` | Có vẻ liên quan, nhưng ngữ cảnh hoặc mapping chưa chắc chắn. |

Khi làm slide/report, nếu một thông số chưa `verified`, nên gọi là:

- `project default`
- `engineering threshold`
- `internal monitoring threshold`

Không nên gọi là “tiêu chuẩn bắt buộc” nếu chưa có nguồn xác nhận.

---

## 2. Nhóm Clearance

### 2.1 Box width = 3.0 m

**Ý nghĩa**

- Đây là chiều rộng khổ thông thủy tham chiếu cho mặt cắt dạng box.
- Tool dùng để kiểm tra không gian an toàn theo phương ngang.

**Cách hiểu đơn giản**

Nếu tunnel là dạng hộp, tool coi vùng an toàn ngang có bề rộng tham chiếu là `3.0 m`.
Nếu point cloud cho thấy kết cấu/vật thể xâm phạm vào vùng này, section có thể bị cảnh báo clearance.

**Lưu ý nguồn**

- Trong repo hiện được ghi là giá trị đang dùng.
- Chưa thấy 2 PDF Korean hiện tại xác nhận trực tiếp giá trị `3.0 m` này.
- Nên xem là `project default` cho đến khi có tiêu chuẩn clearance đầy đủ.

---

### 2.2 Box height = 4.5 m

**Ý nghĩa**

- Đây là chiều cao khổ thông thủy tham chiếu cho mặt cắt dạng box.
- Dùng để kiểm tra khoảng không an toàn theo phương đứng.

**Cách hiểu đơn giản**

Nếu vùng thông thủy cần cao `4.5 m`, mọi điểm/vật thể đi vào vùng cấm có thể được xem là rủi ro.

**Lưu ý nguồn**

- Chưa được xác nhận trực tiếp từ 2 PDF Korean hiện có.
- Nên dùng cách gọi `project default / design envelope setting`.

---

### 2.3 Circle radius = 4.0 m

**Ý nghĩa**

- Bán kính tham chiếu cho mặt cắt tròn.
- Khi profile là `Circle`, tool dùng bán kính này để kiểm tra clearance hoặc so sánh hình học.

**Công thức liên quan**

Với điểm mặt cắt 2D `(x, z)`:

```text
d = sqrt(x^2 + z^2) - R_clearance
```

Nếu `d < 0`, điểm nằm trong vùng clearance cấm.

**Lưu ý nguồn**

- Đây là giá trị mặc định của app/tool, chưa phải tiêu chuẩn đã verify.

---

### 2.4 Minimum clearance = always maintained

**Ý nghĩa**

- Quy tắc an toàn: vùng clearance luôn phải được giữ.
- Nếu có điểm xâm phạm, tool đánh dấu `clearance_violation`.

**Cách hiểu đơn giản**

Dù các thông số biến dạng khác chưa vượt ngưỡng, chỉ cần clearance bị xâm phạm thì đó là vấn đề an toàn riêng.

---

## 3. Nhóm Settlement

### 3.1 Crown settlement caution = 10 mm

**Ý nghĩa**

- Vòm hầm lún khoảng `10 mm` thì bắt đầu cảnh báo mức `CAUTION`.

**Tool tính như thế nào**

Tool lấy cao độ vòm theo phương đứng local `B`:

```text
crown = percentile_99((p - C) · B)
```

Nếu có T0/Tn:

```text
settlement = crown_T0 - crown_Tn
```

Nếu giá trị dương, nghĩa là crown ở Tn thấp hơn T0, tức là vòm bị lún xuống.

**Lưu ý nguồn**

- Hiện là ngưỡng nội bộ/project threshold.
- Chưa thấy PDF Korean hiện tại xác nhận trực tiếp cho tunnel crown settlement.

---

### 3.2 Crown settlement critical = 25 mm

**Ý nghĩa**

- Vòm lún khoảng `25 mm` hoặc hơn thì xem là mức nghiêm trọng `CRITICAL`.

**Cách dùng trong tool**

- Dùng để tô đỏ section, dashboard, 2D/3D marker hoặc work order.

**Lưu ý nguồn**

- Chưa nên nói là verified theo Korean tunnel standard nếu chưa có tài liệu tunnel đầy đủ.

---

## 4. Nhóm Convergence

### 4.1 Lateral convergence caution = 15 mm

**Ý nghĩa**

- Hầm bị co hẹp ngang khoảng `15 mm` thì cảnh báo `CAUTION`.

**Tool tính như thế nào**

Chiều rộng mặt cắt theo phương ngang local `N`:

```text
W = percentile_99(x) - percentile_1(x)
```

với:

```text
x = (p - C) · N
```

So sánh T0/Tn:

```text
convergence = W_T0 - W_Tn
```

Nếu `W_Tn` nhỏ hơn `W_T0`, hầm đang co hẹp.

---

### 4.2 Lateral convergence critical = 30 mm

**Ý nghĩa**

- Co hẹp ngang khoảng `30 mm` hoặc hơn thì cảnh báo `CRITICAL`.

**Điểm cần lưu ý về PDF**

- Trong `KR C-08080` có xuất hiện giá trị `30 mm`, nhưng ngữ cảnh là **chuyển vị dọc tương đối cầu/ray**, không phải convergence hầm.
- Vì vậy chỉ có thể nói “trùng con số”, không thể nói là cùng tiêu chuẩn tunnel.

---

## 5. Nhóm Ovality

### 5.1 Ovality caution = 0.5 %

**Ý nghĩa**

- Mặt cắt bắt đầu méo đáng chú ý.
- Dùng nhiều cho hầm tròn/lining tròn.

**Công thức**

Tool fit ellipse mặt cắt, lấy:

- `a`: bán trục lớn
- `b`: bán trục nhỏ

```text
ovality = (a - b) / a * 100%
```

Nếu ovality tăng, mặt cắt không còn đều/tròn như thiết kế.

---

### 5.2 Ovality critical = 1.0 %

**Ý nghĩa**

- Mặt cắt méo rõ, cần kiểm tra kỹ.

**Lưu ý nguồn**

- Hiện chưa tìm thấy trong 2 PDF Korean hiện có.
- Nên xem là project default/engineering threshold.

---

## 6. Nhóm Eccentricity

### 6.1 Eccentricity caution = 10 mm

**Ý nghĩa**

- Tâm hình học đo được lệch khỏi tâm thiết kế khoảng `10 mm` thì cảnh báo `CAUTION`.

**Công thức**

Nếu tâm đo được là `(cx, cz)`:

```text
e = sqrt(cx^2 + cz^2)
```

Đổi sang mm để cảnh báo.

**Lưu ý PDF**

- `KR C-08080` có nhắc `10 mm`, nhưng là trong ngữ cảnh cầu/ray, không phải eccentricity hầm.
- Do đó không nên dùng làm nguồn xác nhận trực tiếp.

---

### 6.2 Eccentricity critical = 25 mm

**Ý nghĩa**

- Lệch tâm khoảng `25 mm` hoặc hơn thì xem là nghiêm trọng.

**Ý nghĩa kỹ thuật**

Có thể gợi ý:

- hầm bị biến dạng không đối xứng
- centerline/section geometry thay đổi
- có khả năng differential settlement hoặc sai lệch thi công/quan trắc

---

## 7. Nhóm QC - Quality Control

### 7.1 Registration RMSE target < 2 mm

**Ý nghĩa**

- Đây là mục tiêu sai số sau khi align/register Tn về T0.
- RMSE càng nhỏ thì so sánh biến dạng càng đáng tin.

**Công thức ý tưởng**

```text
RMSE = sqrt(mean(distance_i^2))
```

Trong đó `distance_i` là khoảng cách giữa điểm Tn đã align và bề mặt/điểm T0 gần nhất.

**Lưu ý**

- Đây là target QC nội bộ, không phải lúc nào dữ liệu thực địa cũng đạt.
- Nếu RMSE cao, các cảnh báo biến dạng cần được đọc cẩn thận.

---

### 7.2 Heatmap stable band < 1 mm

**Ý nghĩa**

- Vùng xanh trên heatmap.
- Sai khác bề mặt nhỏ hơn `1 mm`, coi như ổn định.

---

### 7.3 Heatmap caution band = 1–3 mm

**Ý nghĩa**

- Vùng vàng.
- Có sai khác nhẹ, nên theo dõi hoặc kiểm tra thêm.

---

### 7.4 Heatmap critical band > 3 mm

**Ý nghĩa**

- Vùng đỏ.
- Sai khác bề mặt lớn hơn `3 mm`, cần ưu tiên kiểm tra.

**Lưu ý**

- Heatmap là lớp trực quan hóa rất nhạy.
- Không nên kết luận chỉ từ màu đỏ nếu registration chưa tốt hoặc dữ liệu có nhiễu.

---

## 8. Nhóm Algorithm

### 8.1 Outlier removal band = mu +/- 2.5 sigma

**Ý nghĩa**

- Quy tắc lọc điểm nhiễu theo thống kê.
- `mu` là giá trị trung bình.
- `sigma` là độ lệch chuẩn.

Điểm nằm ngoài khoảng:

```text
mu ± 2.5 sigma
```

có thể bị xem là outlier.

**Cách hiểu đơn giản**

Nếu một điểm quá khác so với đám điểm xung quanh, nó có thể là nhiễu đo, cable, vật thể lạ hoặc artifact.

---

### 8.2 Voxel size quick preview = 0.10 m

**Ý nghĩa**

- Dùng voxel lớn để giảm điểm nhanh.
- Phù hợp xem nhanh hoặc preview.

**Ưu điểm**

- Chạy nhanh.

**Nhược điểm**

- Mất chi tiết nhỏ.
- Không nên dùng cho phân tích chính xác cao.

---

### 8.3 Voxel size precision = 0.02 m

**Ý nghĩa**

- Voxel nhỏ, giữ chi tiết tốt hơn.
- Phù hợp phân tích kỹ thuật chính xác.

**Ưu điểm**

- Giữ được biến dạng nhỏ.

**Nhược điểm**

- Chạy chậm hơn.
- Tốn RAM hơn.

---

### 8.4 Voxel size high-density = 0.05 m

**Ý nghĩa**

- Mức trung gian giữa nhanh và chính xác.
- Phù hợp dữ liệu dày nhưng vẫn muốn giữ hình học tương đối tốt.

---

## 9. Cách tool áp dụng các thông số

Tool áp dụng bảng này theo pipeline:

1. Load point cloud T0/Tn.
2. Register Tn về T0.
3. Tìm centerline.
4. Cắt section theo chainage.
5. Tính geometry từng section.
6. So sánh Tn với T0.
7. So với ngưỡng trong register.
8. Gán `OK / CAUTION / CRITICAL`.
9. Hiển thị trên 2D, 3D, dashboard, report.

---

## 10. Cách nói an toàn khi thuyết trình

Nên nói:

> Tool dùng các ngưỡng kỹ thuật nội bộ để phân loại mức biến dạng và clearance. Một số giá trị đang được kiểm chứng dần với tài liệu tiêu chuẩn; các giá trị chưa có nguồn trực tiếp được quản lý trong Standard Parameters Register.

Không nên nói:

> Tất cả ngưỡng này đều đã được tiêu chuẩn Hàn xác nhận.

Trừ khi có đủ nguồn PDF, trang, mục, và ngữ cảnh khớp trực tiếp.

---

## 11. Tóm tắt cực ngắn

| Nhóm | Dùng để làm gì |
| --- | --- |
| Clearance | Kiểm tra vùng thông thủy/an toàn. |
| Settlement | Đo lún vòm. |
| Convergence | Đo co hẹp ngang. |
| Ovality | Đo méo mặt cắt. |
| Eccentricity | Đo lệch tâm. |
| QC | Kiểm tra chất lượng registration/heatmap. |
| Algorithm | Điều khiển lọc nhiễu và downsample. |

---

## 12. File liên quan trong repo

- `docs/standards/STANDARD_PARAMETERS.md`: bảng register chính.
- `docs/standards/korean/KR_C-08080_221212_Rev3.ocr.txt`: OCR tiêu chuẩn KR C-08080.
- `docs/standards/korean/KDS_KCS_27_00_00_notice.ocr.txt`: OCR thông báo sửa đổi KDS/KCS.
- `tunnel_analysis/common.py`: nơi đặt một số ngưỡng và default geometry.
- `tunnel_analysis/ui/widgets.py`: nơi phân loại section `OK / CAUTION / CRITICAL`.
- `tunnel_analysis/rag_ai.py`: nơi có snippet tiêu chuẩn/khuyến nghị cho AI/report.
