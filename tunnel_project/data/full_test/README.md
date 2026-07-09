# Bộ dữ liệu kiểm thử đầy đủ T0/Tn

Thư mục này chứa bộ test tổng hợp để kiểm tra gần như toàn bộ luồng xử lý của tool: nhập LAS, ghép T0/Tn, lọc nhiễu, phát hiện biến dạng, cảnh báo và xuất báo cáo.

## File chính

| File | Vai trò |
|---|---|
| `T0_full.las` | Bản quét gốc T0, dùng làm mốc so sánh |
| `Tn_full.las` | Bản quét Tn có biến dạng, nhiễu và vật thể phụ |
| `T0_full.txt` | Bản TXT tương ứng của T0 để debug/Blender đọc nhanh |
| `Tn_full.txt` | Bản TXT tương ứng của Tn để debug/Blender đọc nhanh |
| `full_test_blender_scene.blend` | Scene Blender tạo qua Blender MCP để xem trực quan dữ liệu test |
| `manifest.json` | Mô tả máy đọc được về bộ dữ liệu và các lỗi cài sẵn |

## Những tính năng được test

| Nhóm tính năng | Dữ liệu test |
|---|---|
| Hầm cong | Hầm dài khoảng 1000 m, bán kính cong 2500 m, dốc 0.4% |
| Ghép trạm / đăng ký T0-Tn | 5 sphere targets tại chainage 120, 320, 520, 720, 920 m |
| Lún vòm | Vùng lỗi quanh chainage khoảng 200 m |
| Hội tụ hông hầm | Vùng lỗi quanh chainage khoảng 450 m |
| Lọc nhiễu tự động | Cáp và cụm outlier quanh chainage khoảng 700 m |
| Lỗi tổng hợp | Lún vòm + hội tụ quanh chainage khoảng 900 m |
| Xuất báo cáo | Có đủ LAS/TXT/manifest để chạy pipeline và xuất CSV/Excel/PDF |

## Cách dùng trong tool

1. Import `T0_full.las` ở bước nhập dữ liệu T0.
2. Import `Tn_full.las` ở bước thêm lần quét Tn.
3. Chạy ghép T0/Tn bằng target hoặc ICP.
4. Chạy lọc nhiễu tự động để loại cáp và outlier.
5. Chạy pipeline biến dạng/cảnh báo, kỳ vọng cảnh báo quanh 200 m, 450 m và 900 m.
6. Dùng bước xuất báo cáo để kiểm tra CSV/Excel/PDF.

## Cách tạo lại dữ liệu

```powershell
cd "C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project"
..\.venv\Scripts\python.exe tools\create_full_test_dataset.py
..\.venv\Scripts\python.exe tools\create_full_test_blender_scene.py
..\.venv\Scripts\python.exe test_full_dataset.py
```

## Ghi chú Blender MCP

- LAS/TXT được tạo bằng `tools/create_full_test_dataset.py` để đảm bảo có point cloud chuẩn và đọc được bằng tool.
- Scene `.blend` được tạo qua Blender MCP bằng `tools/create_full_test_blender_scene.py` từ chính dữ liệu T0/Tn này.
- Scene chỉ lấy mẫu một phần điểm để Blender nhẹ hơn, còn LAS vẫn giữ đầy đủ điểm kiểm thử.
