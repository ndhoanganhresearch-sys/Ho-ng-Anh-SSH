# Tài Liệu Tham Khảo - SSL Smart Tunnel Monitoring System (4D-LiDAR)

Ghi chú nguồn mở liên quan, ánh xạ vào từng module trong `tunnel_project/tunnel_analysis/`.
Cột "Mức dùng": **Áp dụng** = nên tích hợp/đối chiếu trực tiếp; **Tham khảo** = đọc để học cách làm.

Cập nhật: 2026-05-30. Nguồn: GitHub Search API (truy vấn theo chủ đề tunnel point cloud, registration, M3C2, BIM/IFC).

---

## 0. Trạng thái tích hợp (2026-05-30)

Hai thư viện đã được tích hợp vào tool, kèm fallback nếu thiếu package:

| Thư viện | Phiên bản | Tích hợp tại | Hàm/Method | Fallback |
|----------|-----------|--------------|------------|----------|
| `py4dgeo` | 0.7.0 | `tunnel_analysis/timeseries.py` | `TimeSeriesLayer.m3c2_distances(...)` | C2C nearest-neighbour (scipy `cKDTree`) |
| `small_gicp` | 1.0.0 | `tunnel_analysis/registration.py` | `RegistrationLayer._icp_gicp(...)` (ưu tiên trong `_icp`) | Open3D point-to-plane ICP, rồi RMSE thô |

- Import optional khai báo trong `tunnel_analysis/common.py` (`small_gicp`, `py4dgeo`) và export qua `__all__`.
- Smoke test: `tunnel_project/smoke_test_advanced_integrations.py` (M3C2 10mm, C2C fallback 10mm, GICP RMSE ~0mm — đã pass).
- Cài đặt: `pip install small_gicp==1.0.0 py4dgeo==0.7.0`.
- Ghi chú M3C2: đo displacement dọc pháp tuyến bề mặt, nên dịch chuyển thuần Z trên tường cong cho giá trị nhỏ hơn dịch chuyển hình học; dùng corepoints/normal phù hợp hình học hầm khi diễn giải kết quả.

### Benchmark GICP vs Open3D ICP (LAS thật, 400k điểm)

Dữ liệu: `tunnel_project/data/T0/box_tunnel_dw.las`, áp transform 1.2° yaw + ~7cm tịnh tiến.
Script: `tunnel_project/benchmark_registration.py`.

| Backend | RMSE sau căn chỉnh | Thời gian (best of 3) |
|---------|--------------------|------------------------|
| `small_gicp` GICP | 0.196 mm | ~339 ms |
| Open3D point-to-plane | 34.463 mm | ~4524 ms |

Kết luận: GICP nhanh hơn ~13x và chính xác hơn nhiều ở residual nhỏ → ưu tiên `small_gicp` trong `_icp`, giữ Open3D làm fallback.

### Tính năng đa epoch

- `TimeSeriesLayer.spatiotemporal_series(...)` trong `tunnel_analysis/timeseries.py`: tính M3C2 mỗi epoch so với T0 tại corepoints cố định → chuỗi lún/hội tụ theo thời gian (monthly trend). Test xác nhận chuỗi -3/-6/-9mm.
- UI: nút "6.3 M3C2 deformation map T0→Tn" trong tab Time-series (`tunnel_analysis/ui/main_window.py`), render heatmap `RdBu_r` + log significant/LoD.

---

## 1. Biến dạng đường hầm (sát bài toán nhất)

| Repo | Link | Module liên quan | Mức dùng |
|------|------|------------------|----------|
| FY387/Deformation-calculation-of-metro-tunnels-based-on-point-clouds | https://github.com/FY387/Deformation-calculation-of-metro-tunnels-based-on-point-clouds | `timeseries.py`, `geometry.py`, `parameters.py` | Áp dụng |
| FY387/Deformation-interpretation-of-metro-tunnels-with-point-clouds | https://github.com/FY387/Deformation-interpretation-of-metro-tunnels-with-point-clouds | `timeseries.py` | Áp dụng |
| cqc2/pc-tunnel | https://github.com/cqc2/pc-tunnel | `preprocessing.py`, `geometry.py` | Tham khảo (MATLAB) |
| Ritika-a/Detection-of-Objects-in-a-Tunnel-Using-Deep-Learning | https://github.com/Ritika-a/Detection-of-Objects-in-a-Tunnel-Using-Deep-Learning | `segmentation.py`, `digital_twin.py` | Tham khảo |

Ghi chú: bài toán crown settlement / wall convergence của ta giống FY387. Đối chiếu cách họ trích centerline và cắt mặt cắt ngang để kiểm chứng `geometry.py`.

---

## 2. Phân tích biến đổi 4D / M3C2

| Repo | Link | Module liên quan | Mức dùng |
|------|------|------------------|----------|
| 3dgeo-heidelberg/py4dgeo | https://github.com/3dgeo-heidelberg/py4dgeo | `timeseries.py` | Áp dụng |
| Kostka22/Geology_M3C2-from-point-cloud | https://github.com/Kostka22/Geology_M3C2-from-point-cloud | `timeseries.py`, `exporter.py` | Tham khảo |

Ghi chú: `py4dgeo` là thư viện M3C2 chuẩn học thuật (signed distance, significance test, LoD). Dùng để validate kết quả 4D deformation của ta hoặc thay phần tự code. Hỗ trợ trích dẫn trong báo cáo nghiên cứu.

---

## 3. Registration (ICP / Targets)

| Repo | Link | Module liên quan | Mức dùng |
|------|------|------------------|----------|
| neka-nat/probreg | https://github.com/neka-nat/probreg | `registration.py` | Tham khảo |
| koide3/small_gicp | https://github.com/koide3/small_gicp | `registration.py` | Áp dụng (tăng tốc) |
| CodeName-Detective/Point-Cloud-Registration-and-Evaluation | https://github.com/CodeName-Detective/Point-Cloud-Registration-and-Evaluation | `registration.py` | Tham khảo |
| lazyJLBL/PointCloud-GeoLab | https://github.com/lazyJLBL/PointCloud-GeoLab | `registration.py`, `target_detector.py` | Tham khảo |

Ghi chú: engine hiện tại dùng SVD + target matching rồi point-to-plane ICP. `small_gicp` cho ICP/GICP song song hiệu năng cao (phù hợp workstation 32GB, point cloud lớn). `probreg` hữu ích nếu cần đăng ký khi thiếu target chung.

---

## 4. Thư viện nền tảng (đang dùng trong tool)

| Repo | Link | Module liên quan | Mức dùng |
|------|------|------------------|----------|
| isl-org/Open3D | https://github.com/isl-org/Open3D | toàn pipeline | Áp dụng |
| isl-org/Open3D-ML | https://github.com/isl-org/Open3D-ML | `segmentation.py` | Tham khảo |
| laspy/laspy | https://github.com/laspy/laspy | `io_layer.py` | Áp dụng |
| IfcOpenShell/IfcOpenShell | https://github.com/IfcOpenShell/IfcOpenShell | `ifc_exporter.py` | Áp dụng |
| jakob-beetz/ifcopenshell-notebooks | https://github.com/jakob-beetz/ifcopenshell-notebooks | `ifc_exporter.py` | Tham khảo (học IFC) |

---

## 5. Khoảng trống chưa có repo sát

- Tunnel + xuất IFC/BIM: chưa tìm thấy repo công khai sát. Phần `ifc_exporter.py` của ta khá độc đáo — dựa trực tiếp tài liệu IfcOpenShell.
- Point cloud + trợ lý RAG/LLM: chưa có repo sát cho `rag_ai.py`. Tự phát triển theo hướng riêng.

---

## 6. Tìm kiếm theo tính năng (đợt 2 — 2026-05-30)

### 6.1 Segmentation / RANSAC (`segmentation.py`)
- `leomariga/pyRANSAC-3D` (653★) — https://github.com/leomariga/pyRANSAC-3D — fit primitive 3D (plane, cylinder, sphere) bằng RANSAC. **Áp dụng**: đối chiếu thuật toán fit cylinder cho mặt cắt hầm tròn.
- `isl-org/Open3D-PointNet2-Semantic3D` — semantic segmentation point cloud. **Tham khảo** cho phân loại lining/nhiễu.
- `Jiang-Muyun/PointNet12` (37★), `camillelhenry/Pointnetv2-PFE-2021` — PointNet/PointNet++ PyTorch. **Tham khảo** nếu nâng segmentation lên deep learning.

### 6.2 BIM / IFC export (`ifc_exporter.py`)
- `VaclavNezerka/Cloud2BIM` (106★) — https://github.com/VaclavNezerka/Cloud2BIM — point-cloud → BIM tự động. **Áp dụng**: tham khảo pipeline tạo hình học IFC từ point cloud.
- `rsasaki0109/pointcloud2ifc` — point cloud → IFC qua semantic segmentation. **Tham khảo** mapping segment → entity IFC.

### 6.3 Crack detection / Digital twin (`digital_twin.py`)
- `konskyrt/Concrete-Crack-Detection-Segmentation` (104★) — https://github.com/konskyrt/Concrete-Crack-Detection-Segmentation — PyTorch CNN phát hiện nứt bê tông. **Áp dụng** cho nhận diện nứt lining.
- `rakehsaleem/DeepLearning-ConcreteDataset` (32★) — dataset Mask R-CNN nứt bê tông pixel-wise. **Tham khảo** dữ liệu huấn luyện.
- `michaelkapteyn/UAV-Digital-Twin` (68★) — digital twin SHM bằng probabilistic graphical model. **Tham khảo** kiến trúc digital twin.

### 6.4 RAG / AI assistant (`rag_ai.py`)
- `mytechnotalent/rea` (39★) — https://github.com/mytechnotalent/rea — trợ lý RAG + LLaMA-3.1. **Tham khảo** kiến trúc RAG (chunking, vector search, prompt).
- `hamdisco22/azure-rag-sim-assistant` — RAG cho tài liệu kỹ thuật. **Tham khảo** luồng truy hồi tài liệu.

Ghi chú: vẫn chưa có repo sát "tunnel + IFC" hay "point cloud + RAG"; các repo trên là gần nhất theo từng thành phần, dùng để học pattern chứ không thay thế trực tiếp.
---

## Ghi chú kỹ thuật khi tra cứu

- GitHub Search API gọi ẩn danh giới hạn ~10 request/phút, dễ dính lỗi 403. Cách khắc phục:
  - Giãn request bằng `Start-Sleep` giữa các truy vấn.
  - Dùng Personal Access Token (`github.com/settings/tokens`) kèm header `Authorization: Bearer <token>` để lên ~30 request/phút.
  - Cài `gh` CLI (`winget install GitHub.cli` rồi `gh auth login`) để tự dùng token.
