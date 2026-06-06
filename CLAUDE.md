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

## 🐛 Lịch sử bug đã fix

- **rag_ai.py dead-code (line 184)** — ✅ đã fix: hàm `query()` giờ chỉ còn 1 `return` duy nhất, gộp `rag_note` + `optimized.note`.
- **parameters.py crown settlement** — ✅ đã fix: đổi `(crown_n - crown_0)` → `(crown_0 - crown_n)` (dương = lún xuống, khớp ngưỡng dương).
- **rag_ai.py / digital_twin.py model** — ✅ đã fix: đọc `TUNNEL_OLLAMA_MODEL` (mặc định `qwen2.5:3b`) ở instance, không hardcode `llama3`.
- **ChromaDB URL parsing** — ✅ đã fix: dùng `urllib.parse` để chịu được https/trailing-slash/thiếu port.
- **preprocessing.py NameError** — ✅ đã fix: khởi tạo `is_cable/is_light/is_person` trước block `cKDTree`.
- **geometry.py zero tangent** — ✅ đã fix: fallback tìm tangent hợp lệ gần nhất, tránh vector N/B = 0.
- **ifc_exporter.py atomic write** — ✅ đã fix: ghi temp + `os.replace` để tránh file IFC corrupt.
- **timeseries.py M3C2** — ✅ đã fix: cảnh báo khi tỷ lệ điểm T0/Tn lệch lớn hoặc NaN > 50%.
