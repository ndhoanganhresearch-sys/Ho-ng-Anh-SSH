# Cơ chế hoạt động — SSL Smart Tunnel Monitoring System

> Tài liệu này giải thích cách dữ liệu LiDAR được xử lý từ khi nạp vào đến khi xuất báo cáo.

---

## Tổng quan

```
📂 File LiDAR (LAS/LAZ/PLY...)
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 0 │ Nạp dữ liệu                                  │
│  Stage 1 │ Làm sạch điểm (Preprocessing)                │
│  Stage 2 │ Căn chỉnh nhiều lần quét (Registration)      │
│  Stage 3 │ Phân tích hình học (Centerline + Frenet)      │
│  Stage 4 │ Phân đoạn vòng đốt (Segmentation)            │
│  Stage 5 │ Trích xuất thông số (Parameters)              │
│  Stage 6 │ Phân tích theo thời gian (T0 vs Tn)          │
│  Stage 7 │ Xuất báo cáo (CSV / Excel / PDF / IFC)       │
└─────────────────────────────────────────────────────────┘
        │
        ▼
📊 Báo cáo + 🏗️ Mô hình BIM (IFC) + 🤖 Đánh giá AI
```

---

## Stage 0 — Nạp dữ liệu

**Định dạng hỗ trợ:** LAS · LAZ · PLY · TXT · XYZ · CSV · ASC

Mỗi file được đọc thành một **đám mây điểm** (point cloud):

| Thuộc tính | Mô tả |
|-----------|-------|
| XYZ | Toạ độ 3D của từng điểm (tính bằng mét) |
| Intensity | Cường độ phản xạ laser (0–65535) |
| RGB | Màu sắc (nếu scanner có camera) |
| Labels | Nhãn ngữ nghĩa (nếu dùng dữ liệu STSD) |

> **Giới hạn:** Tối đa 5,000,000 điểm. Nếu file lớn hơn, hệ thống tự subsample.

---

## Stage 1 — Làm sạch điểm (Preprocessing)

Mục tiêu: **chỉ giữ lại điểm thuộc vỏ hầm**, loại bỏ nhiễu và vật thể không liên quan.

### 1a. Cắt theo khoảng cách (Range Crop)
Loại bỏ điểm quá xa scanner (điểm ngoài phạm vi đo tin cậy).

### 1b. Voxel Downsampling
Chia không gian thành các ô lưới nhỏ (ví dụ: 5cm × 5cm × 5cm), mỗi ô chỉ giữ 1 điểm đại diện → giảm khối lượng tính toán mà không mất thông tin hình dạng.

### 1c. Trích xuất vỏ hầm
Ba phương pháp, tự động chọn phù hợp:

```
Phương pháp A: Nhãn ngữ nghĩa (Label-based)
  → Dùng nhãn STSD để giữ lớp kết cấu (vỏ bê tông)
  → Chính xác nhất khi có dữ liệu đã được phân loại

Phương pháp B: Hình học (Geometric)
  → Phân tích thống kê bán kính từ trục → lọc ngoại biên
  → Dùng khi không có nhãn

Phương pháp C: Mật độ điểm (Density-variation)
  → Phân tích histogram mật độ theo chiều hướng tâm
  → Phát hiện ranh giới bề mặt nội thất hầm
```

### 1d. Tự động khử nhiễu (Auto-Denoise)
Ba bước chạy tuần tự:

```
Bước A — Hình thái học (Morphology):
  PCA cục bộ → nhận dạng cáp/đèn/người theo hình dạng điểm
  → Loại bỏ cụm điểm hình trụ nhỏ (cáp), phẳng nằm ngang (người)

Bước B — Thống kê bán kính (Radial Stats):
  Chia hầm thành vòng 1m, tính trung vị + MAD bán kính
  → Loại điểm lệch quá 2.5σ so với bề mặt vỏ

Bước C — Cáp gắn tường (Wall Cables):
  Lưới trụ → tìm điểm nhô ra + liên tục theo chiều dọc
  → Loại bỏ cáp chạy dọc tường
```

---

## Stage 2 — Căn chỉnh nhiều lần quét (Registration)

Khi có **nhiều file scan** (T0 + Tn, hoặc nhiều vị trí scanner), cần căn chỉnh về cùng hệ toạ độ.

### Bước 1 — Căn chỉnh thô (Coarse Alignment)
```
GROR (Graph-based Outlier Rejection):
  1. Trích xuất đặc trưng FPFH từ mỗi đám mây điểm
  2. Khớp đặc trưng giữa hai đám mây
  3. Xây đồ thị độ tin cậy → loại cặp khớp sai
  4. Tính ma trận biến đổi Rigid (SVD Umeyama)
```

### Bước 2 — Căn chỉnh tinh (Fine Registration)
```
GICP (Generalized ICP, song song hoá):
  Lặp cho đến khi RMSE hội tụ < 1mm
  → Đầu ra: ma trận biến đổi 4×4 + RMSE (mm)
```

> ✅ **Tiêu chuẩn chấp nhận:** RMSE < 2mm. Nếu cao hơn, cảnh báo người dùng.

---

## Stage 3 — Phân tích hình học

### 3a. Trích xuất đường tâm (Centerline)
```
1. Chia đám mây thành các lát mỏng dọc theo trục PCA chính
2. Mỗi lát: fit vòng tròn → lấy tâm
3. Khử đột biến (despiking) bằng median filter
4. Nội suy B-spline (liên tục bậc 2) → đường tâm mượt
```

### 3b. Khung Frenet (Frenet Frame)
Tại mỗi điểm trên đường tâm, xác định 3 vector vuông góc:

```
T (Tangent)  → chiều dọc hầm
N (Normal)   → ngang hầm (trái-phải)
B (Binormal) → đứng hầm (lên-xuống)
```

> **Tại sao quan trọng?** Chiếu điểm lên mặt phẳng N-B cho tiết diện **thực sự vuông góc** với trục hầm — tránh sai số ovality lên đến 15% khi dùng tiết diện nghiêng.

---

## Stage 4 — Phân đoạn vòng đốt (Segmentation)

```
1. Chia hầm thành vòng đốt dọc theo đường tâm
2. Phát hiện khe nối vòng (ring seam):
   → Gradient cường độ phản xạ: khe bê tông cho độ sụt 30–60%
   → Khoảng cách điển hình: 1.0–1.5m (bê tông lắp ghép)
```

---

## Stage 5 — Trích xuất thông số

Tại **mỗi tiết diện**, hệ thống tính:

### Hình dạng tiết diện
| Thông số | Cách tính | Đơn vị |
|---------|-----------|--------|
| Bán kính (R) | Fit vòng tròn / ellipse (Fitzgibbon DLS) | mm |
| Eccentricity (e) | Khoảng cách tâm đo vs tâm thiết kế | mm |
| Ovality (ε) | (a−b)/a × 100%, a/b là trục lớn/nhỏ của ellipse | % |

### Biến dạng (cần T0 + Tn)
| Thông số | Cách tính | Ngưỡng Cảnh báo | Ngưỡng Nguy hiểm |
|---------|-----------|----------------|-----------------|
| Crown Settlement (δv) | Độ lún đỉnh hầm Tn − T0 | 10 mm | 25 mm |
| Lateral Convergence (δh) | Thu hẹp ngang Tn − T0 | 15 mm | 30 mm |
| Ovality | | 0.5% | 1.0% |
| Eccentricity | | 10 mm | 25 mm |

### Bản đồ nhiệt (Heatmap)
```
Với mỗi điểm Tn → tìm điểm gần nhất trên T0
→ Khoảng cách Hausdorff = độ biến dạng cục bộ
→ Màu sắc: Xanh (<1mm) · Vàng (1–3mm) · Đỏ (>3mm)
```

### Kiểm tra khổ giới hạn (Clearance)
```
So sánh tiết diện hầm với khổ giới hạn đoàn tàu
→ Phát hiện vị trí xâm phạm khổ giới hạn
→ Tiêu chuẩn: Luật Đường sắt Hàn Quốc, Điều 26
```

---

## Stage 6 — Phân tích theo thời gian (T0 → Tn)

Khi có **nhiều epoch** (nhiều lần đo tại các thời điểm khác nhau):

```
M3C2 (Multiscale Model-to-Model Cloud Comparison):
  1. Tính pháp vector cục bộ tại mỗi điểm T0
  2. Đo khoảng cách có hướng dọc theo pháp vector đến Tn
  3. Tính Level of Detection (LoD) từ độ lệch chuẩn cục bộ
  → Chỉ báo cáo thay đổi có ý nghĩa thống kê (> LoD)
```

---

## Stage 7 — Xuất báo cáo

### CSV / Excel
```
Một hàng = một tiết diện
Cột: Chainage · H1/H2/H3 · W1/W2 · R · e · ε · δv · δh · Clearance
Excel: đa sheet, biểu đồ nhúng, mã màu Caution/Critical tự động
```

### PDF (Báo cáo chuyên nghiệp)
```
Trang 1: Bìa (dự án, kỹ sư, ngày quét, vị trí)
Trang 2: Bảng tóm tắt (mean/max các thông số vs ngưỡng)
Trang 3+: Vẽ tiết diện từng vòng (fit vòng tròn, heatmap, polar)
Cuối: Danh sách cảnh báo theo mức độ ưu tiên
```

### IFC4 / IFC4X3 (Mô hình BIM)
```
IfcAlignment          → Đường tâm hầm (IFC4X3)
IfcSweptDiskSolid     → Vỏ hầm dạng ống rỗng
IfcSectionedSolid     → Tiết diện từng vòng đốt
IfcWall               → Cáp / đèn phát hiện được
IfcDistributionElement→ Mốc khảo sát (cầu gương, bảng kiểm)
```

---

## AI Assistant (RAG + Ollama)

```
1. Kỹ sư đặt câu hỏi (ví dụ: "Tình trạng hầm có an toàn không?")
2. RAG tìm kiếm tiêu chuẩn liên quan từ knowledge base
   (KR C-08080, KDS 27 25 00, NATM, ITA guidelines)
3. Ghép dữ liệu đo + tiêu chuẩn → prompt cho Ollama
4. Ollama (qwen2.5:3b, chạy GPU local) → phân tích + khuyến nghị
5. Trả lời: đánh giá tình trạng · thông số vượt ngưỡng · hành động ưu tiên
```

> **Offline fallback:** Nếu Ollama không chạy, hệ thống tự đánh giá bằng rule-based (so sánh trực tiếp với ngưỡng).

---

## Sơ đồ dữ liệu tổng thể

```
LiDAR Scanner
    │
    │ .las / .laz / .ply
    ▼
┌──────────────┐    ┌──────────────┐
│  Scan T0     │    │  Scan Tn     │  ← Nhiều thời điểm
│  (Reference) │    │  (Monitoring)│
└──────┬───────┘    └──────┬───────┘
       │                   │
       └─────────┬─────────┘
                 │ Registration (GICP)
                 ▼
         ┌──────────────┐
         │ Preprocessing│ ← Lọc nhiễu, tách vỏ hầm
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │  Geometry    │ ← Đường tâm, Frenet frames
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │  Parameters  │ ← Settlement, Convergence, Heatmap
         └──────┬───────┘
                │
       ┌────────┴────────┐
       ▼                 ▼
  ┌─────────┐      ┌──────────┐
  │  Export │      │ AI Query │
  │CSV·Excel│      │ RAG+LLM  │
  │PDF · IFC│      └──────────┘
  └─────────┘
```

---

## Yêu cầu hệ thống

| Thành phần | Tối thiểu | Khuyến nghị |
|-----------|----------|-------------|
| RAM | 16 GB | 32 GB |
| GPU VRAM | — | 6 GB+ (RTX 3060+) |
| Ổ cứng | 20 GB | 100 GB (SSD) |
| Python | 3.11+ | 3.12 |
| OS | Windows 10 | Windows 11 / Ubuntu 22.04 |

---

*Tài liệu này mô tả phiên bản hiện tại của SSL Smart Tunnel Monitoring System.*
*Để biết thêm chi tiết kỹ thuật, xem `AGENTS.md` và source code trong `tunnel_analysis/`.*
