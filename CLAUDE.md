# CLAUDE.md — Hướng dẫn cho Claude Code

Tổng hợp từ phân tích lỗi session + AGENTS.md (ECC-influenced).

---

## 🎯 Quy tắc làm việc (từ AGENTS.md)

- **Không refactor** code không liên quan trong khi fix feature
- **Không revert** thay đổi của user hoặc benchmark artifacts trừ khi được yêu cầu
- **Benchmark là bằng chứng** — không claim thuật toán tốt hơn nếu chưa đo thực tế
- **Headroom optional trên Windows** — native compression chạy qua WSL `.venv-headroom`
- Giữ nguyên workflow T0/Tn: T0 = reference, Tn = so sánh, warnings gắn với section/deformation

---

## ✅ Verification (chạy trước khi báo fix xong)

```powershell
# Từ thư mục tunnel_project/
..\.venv\Scripts\python.exe -m py_compile tunnel_analysis\headroom_adapter.py tunnel_analysis\rag_ai.py tunnel_analysis\digital_twin.py
..\.venv\Scripts\python.exe smoke_test_headroom_adapter.py
..\.venv\Scripts\python.exe smoke_test_advanced_integrations.py
```

```powershell
# WSL Headroom verification
wsl --cd "C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project" .venv-headroom/bin/python smoke_test_headroom_adapter.py
```

---

## ⚠️ Các lỗi hay gặp & cách tránh

### 1. Nhầm đường dẫn Windows vs WSL
- **Windows**: dùng `C:\Users\ssl\...` với PowerShell
- **WSL/Linux**: dùng `/mnt/c/Users/ssl/...` với Bash
- **Không trộn lẫn** — PowerShell không hiểu `/mnt/c/`, Bash không hiểu `C:\`

### 2. Venv đúng theo môi trường
| Môi trường | Python | Headroom |
|-----------|--------|---------|
| Windows | `.venv\Scripts\python.exe` | `.venv\Scripts\headroom.exe` |
| WSL/Linux | `.venv-headroom/bin/python` | `.venv-headroom/bin/headroom` |

### 3. Luôn Read trước khi Edit
```
❌ Sai: Edit file ngay không đọc trước
✅ Đúng: Read file → sau đó mới Edit
```
Nếu file bị sửa đổi sau khi Read → phải Read lại trước khi Edit.

### 4. MCP Server config đúng chỗ
```
❌ Sai: thêm mcpServers vào settings.json hoặc settings.local.json
✅ Đúng: thêm vào .mcp.json ở thư mục gốc dự án
```

### 5. Escape dấu nháy trong PowerShell
- Lệnh phức tạp có `"` bên trong → dễ bị `unexpected EOF`
- Dùng single quote `'` hoặc escape `\"` đúng cách

---

## 🔍 Review Focus (từ AGENTS.md)

- Python runtime errors, imports, PyQt signal/slot issues
- Threading và worker lifecycle trong UI
- Deformation thresholds, unit conversion, section indexing, 2D/3D mapping
- Benchmark regressions: clean noise, registration, centerline, T0/Tn comparison
- Large point-cloud memory behavior trên máy 32GB RAM

---

## 🛠️ Cấu hình dự án

### MCP Server (Headroom)
File: `.mcp.json`
```json
{
  "mcpServers": {
    "headroom": {
      "command": "C:\\Users\\ssl\\Desktop\\Code Python\\data python cusor\\.venv\\Scripts\\headroom.exe",
      "args": ["mcp", "serve"],
      "env": {
        "HEADROOM_MCP_READ": "on"
      }
    }
  }
}
```

### Chạy Headroom Learn (Windows)
```powershell
$env:PYTHONUTF8="1"
.\.venv\Scripts\headroom.exe learn --agent claude --all --model ollama/qwen2.5:3b
# Không dùng --apply vì headroom decode sai Windows path có spaces
# Tự copy recommendations vào CLAUDE.md thủ công
```

### Ollama
- Model: `qwen2.5:3b` (1.9GB) — chạy **100% GPU** trên RTX 4060 Ti
- Không dùng model >6GB VRAM (Chrome/Zalo chiếm ~2GB trước)
- Kiểm tra: `ollama ps` → phải thấy `100% GPU`
- Ollama version phải ≥ v0.30 để nhận GPU đúng

---

## 📁 Cấu trúc dự án

```
data python cusor/
├── .mcp.json                    # MCP server config (headroom)
├── .venv/                       # Python venv Windows
├── CLAUDE.md                    # File này
└── tunnel_project/
    ├── AGENTS.md                # Agent guide (ECC-influenced) ← đã merge vào đây
    ├── BENCHMARK_WORKFLOW.md    # Quy trình benchmark
    ├── PROJECT_DECISIONS.md     # Quyết định thiết kế
    ├── VERIFICATION_CHECKLIST.md
    ├── .venv-headroom/          # Python venv WSL/Linux
    └── tunnel_analysis/
        ├── headroom_adapter.py  # Tích hợp headroom + Ollama
        ├── rag_ai.py            # RAG assistant (bug line 184)
        └── digital_twin.py
```

---

## 🤖 Headroom Learned Patterns
*qwen2.5:3b phân tích 118 tool calls — 9.3% failure rate*

- Quản lý Ollama: `ollama stop <model>`, `ollama rm <model>`, `ollama list`
- Kiểm tra path tồn tại trước khi đọc/ghi file
- Dùng `$env:PYTHONUTF8="1"` khi chạy headroom trên Windows
- Windows path: dùng `C:\Users\ssl\...`, không dùng `\\\Users\ssl\...`

---

## 📌 Tóm tắt phiên gần nhất (đọc trước khi tiếp tục)

**Tính năng đã thêm/sửa trong phiên này:**
- **ChainageRulerWidget** (`widgets.py`): thanh lý trình full-width dưới viewport, tam giác cảnh báo đỏ/vàng, click nhảy mặt cắt.
- **`classify_sections()` (nguồn chân lý chung)**: ruler + 2D track + 3D markers + dashboard + 2D banner dùng CHUNG hàm này → cảnh báo nhất quán. dW/dH/dR dùng ngưỡng tuyệt đối, dEcc/dOval giữ local-gate.
- **`register_epochs()` (`registration.py`)**: căn chỉnh T0/Tn đo từ vị trí khác — tự dùng mốc cầu (SVD, không triệt tiêu biến dạng) nếu ≥3 mốc, không thì trimmed-ICP. Có divergence-guard. Nút "3.0/3.1 Auto-align T0/Tn".
- **Sidebar gọn lại**: ẩn nút trùng qua `CORE_STEP_CODES`, đánh số hiển thị liền mạch qua `CORE_DISPLAY_RENUMBER` (giữ ID lọc ổn định), gộp Export (8.x) vào mục 7. i18n VN/KO cập nhật.
- **Bộ test all-in-one**: `data/full_test/` (T0_full + Tn_full, .las + .txt) — hầm CONG ~1km, 4 vị trí lỗi (lún 200m, hội tụ 450m, nhiễu 700m, kết hợp 900m) + 5 mốc. **BỊ gitignore** → chạy `tools/create_full_test_dataset.py` để tái tạo.
- **Fix eccentricity hầm cong + centerline guard** (chi tiết trong bug list dưới).

**Trạng thái hiện tại**: 14/14 test suite PASS. Nhánh `feature/m3c2-gicp-integration`.

**Lệnh test nhanh** (từ `tunnel_project/`, `$env:PYTHONUTF8="1"`):
`..\.venv\Scripts\python.exe test_full_dataset.py` (end-to-end) · `test_step6_evaluation.py` · `test_deformation_groundtruth.py` (benchmark).

**Tồn đọng đã biết (có workaround, không blocker)**:
- Ecc max ~245mm trên hầm CONG 1-scan (centerline lệch ~180mm khỏi tâm ống) → **luôn load T0+Tn** để ecc chính xác (bias triệt tiêu).
- Cảnh báo có thể nổi ở 2 đầu hầm cong/dài (artifact portal).
- `sg.eccentricity` (Info dialog/2D) còn cách cũ; chỉ card dashboard (calc_eccentricity) được detrend.

---

## 🐛 Lịch sử bug đã fix

- **rag_ai.py dead-code (line 184)** — ✅ đã fix: hàm `query()` giờ chỉ còn 1 `return` duy nhất, gộp `rag_note` + `optimized.note`.
- **parameters.py crown settlement** — ✅ đã fix: đổi `(crown_n - crown_0)` → `(crown_0 - crown_n)` (dương = lún xuống, khớp ngưỡng dương).
- **rag_ai.py / digital_twin.py model** — ✅ đã fix: đọc `TUNNEL_OLLAMA_MODEL` (mặc định `qwen2.5:3b`) ở instance, không hardcode `llama3`.
- **ChromaDB URL parsing** — ✅ đã fix: dùng `urllib.parse` để chịu được https/trailing-slash/thiếu port.
- **preprocessing.py NameError** — ✅ đã fix: khởi tạo `is_cable/is_light/is_person` trước block `cKDTree`.
- **geometry.py zero tangent** — ✅ đã fix: fallback tìm tangent hợp lệ gần nhất, tránh vector N/B = 0.
- **ifc_exporter.py atomic write** — ✅ đã fix: ghi temp + `os.replace` để tránh file IFC corrupt.
- **timeseries.py M3C2** — ✅ đã fix: cảnh báo khi tỷ lệ điểm T0/Tn lệch lớn hoặc NaN > 50%.
- **parameters.py compute_all_sections epsilon** — ✅ đã fix: slab cứng 5cm/section-spacing 80cm bỏ sót 45/80 mặt cắt → dùng `_section_epsilon` adaptive (0→80/80 mặt cắt có dữ liệu).
- **parameters.py crown/width outlier** — ✅ đã fix: crown `b_proj.max()` và width `max-min` bị 1 điểm lạc làm hỏng (crown_max 1265mm→92mm, khớp GT). Dùng percentile p99/p1. Verify: test_deformation_groundtruth 6/6 vẫn pass.
- **widgets.py classify_sections local-gate** — ✅ đã fix: gate `median+3·MAD` chặn cả biến dạng lớn trải rộng (dW=-63mm, dR=-27mm không được flag). Tách: dW/dH/dR dùng ngưỡng tuyệt đối (`local_gate=False`), dEcc/dOval giữ gate (chống offset hệ thống). v01→CAUTION, v02→CRITICAL recall 100%.
- **parameters.py _has_t0_reference** — ✅ đã fix: crown/convergence cũ bắt `active_index>0` → báo "Cần T0" dù đã tải T0 (khi monitoring nằm trong normalized_points, active_index=0). Helper chung khớp logic section.
- **run_tunnel_analysis.py user-site leak** — ✅ đã fix: MS Store Python inject user-site (numpy 2.4.3) vào venv (numpy 2.4.6) → RecursionError lúc import scipy.stats. Prune `local-packages` khỏi sys.path đầu file.
- **registration.py register_epochs (mới)** — ✅ thêm: căn chỉnh T0/Tn đo từ vị trí khác → tự dùng điểm mốc cố định (SVD cứng, không triệt tiêu biến dạng) nếu phát hiện ≥3 mốc; không thì trimmed ICP (`_trimmed_icp` loại vùng residual cao → giữ biến dạng cục bộ, full ICP làm mất ~75%). Wire vào AUTO PIPELINE (bước 2b) khi có ≥2 epochs. Test: test_register_epochs 8/8 (mốc + ICP + biến dạng giữ nguyên).
- **UI nút "3.0 Auto-align T0/Tn epochs"** — ✅ thêm: phơi bày register_epochs thành nút riêng ở section 3 (Registration), dùng key dispatch `epoch_register`. Thêm "3.0" vào CORE_STEP_CODES. Lưu ý: xoay quanh trục hầm (roll) với hầm tròn là bất khả quan sát → cần mốc; xoay quanh trục đứng (yaw) + tịnh tiến thì ICP khôi phục được. Test end-to-end: test_pipeline_end_to_end 16/16 (Tn lệch hệ tọa độ vẫn khớp, gap 2.1m→0.07m).
- **registration.py register_epochs divergence guard** — ✅ thêm: ICP trượt 233m trên hầm dài gần đối xứng → chọn kết quả tốt nhất theo RMSE trong {nguyên bản, coarse, trimmed-ICP}, không bao giờ tệ hơn đầu vào.
- **preprocessing.py voxel recenter đa trạm** — ✅ fix: voxel chỉ recenter khi 1 scan; ≥2 scan giữ khung tọa độ (T0/Tn không bị tách ~20m). Render lại cả 2 trạm sau 2.1/2.5 (giữ điểm nhiễu đỏ).
- **parameters.py calc_eccentricity hầm cong** — ✅ fix (đầu tư): eccentricity 1-scan trên hầm cong báo giả ~452mm (B-spline centerline lệch tâm ống). Nhánh fallback (no-T0): tâm fit vòng tròn (Kasa, robust với sampling lệch) + detrend bằng moving-median reflect-pad + median filter + bỏ portal → **mean 452→10mm**. Nhánh T0 (test GT) giữ nguyên. CÒN LẠI: max ~245mm do centerline lệch ~180mm khỏi tâm ống cong (giới hạn tracking — cần viết lại centerline từ gốc, rủi ro cao). Verify: test_deformation_groundtruth 6/6 vẫn pass.
- **geometry.py _refine_centerline_tangent guard** — ✅ fix: bước refine tiếp tuyến (chạy khi hầm cong) thực ra làm centerline TỆ HƠN trên vài data cong (offset 24mm→204mm, do frame bootstrap PCA thẳng). Thêm `_axis_offset_metric` + guard trong extract_centerline_bspline: chỉ giữ refine nếu GIẢM offset tâm, không thì giữ bootstrap. Chỉ chạy khi cong → hầm thẳng (GT/step6) không đụng. Verify regression: GT 6/6, sections radius 2.750m, clearance precision/recall 1.00, step6 10/10, consistency 12/12, end-to-end 16/16 — pass hết.
