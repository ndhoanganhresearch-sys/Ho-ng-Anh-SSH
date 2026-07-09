# Experiment Log

#experiment #log #verification

Ghi lại mỗi lần chạy test, benchmark hoặc thử nghiệm.

## Template nhanh

```md
## EXP YYYY-MM-DD - Tên thử nghiệm

### Mục tiêu

### Dataset
- [[Dataset T0-T5]]

### Lệnh chạy
`command here`

### Kết quả
- Pass/Fail:
- Sai số:
- Output:

### Nhận xét

### Việc tiếp theo
```

## EXP 2026-06-30 - Khởi tạo Obsidian vault

### Mục tiêu

Kết nối dự án với Obsidian để quản lý bản đồ tri thức và tài liệu nghiên cứu.

### Kết quả

- Vault mở được trong Obsidian
- Có trang chủ [[../OBSIDIAN_PROJECT_HOME|OBSIDIAN_PROJECT_HOME]]

### Việc tiếp theo

- Bật plugin [[Obsidian MCP Setup]] nếu cần MCP
- Ghi thí nghiệm Step 6 vào log này

## Planned Experiments

- [[EXP Step6 T0-T5]] - validate cumulative deformation from T0 to T5
- [[Step 6 Benchmark Table]] - aggregate measured error by epoch
- [[Ground Truth Definition]] - source of expected deformation values

## EXP 2026-06-30 - Step 6 T0-T5 benchmark

### Mục tiêu

Validate cumulative deformation from `T0` to `T5` and fill the benchmark evidence chain.

### Lệnh chạy

```powershell
cd tunnel_project
.\agent_verify.ps1 step6
..\.venv\Scripts\python.exe benchmark_timeseries_t0t5.py
```

### Kết quả

- `agent_verify.ps1 step6`: PASS
- `benchmark_timeseries_t0t5.py`: `17 passed / 0 failed`
- `T0 -> T5` crown max: expected `45.00 mm`, measured `44.05 mm`, error `0.95 mm`
- Evidence note: [[EXP Step6 T0-T5]]
- Summary table: [[Step 6 Benchmark Table]]

### Việc tiếp theo

- Use these results to draft method/validation text.
- Add citations before treating publication-level claims as final.

## Liên kết

- [[Dataset T0-T5]]
- [[Step 6 Deformation]]
- [[Research Claims]]
- [[Future Direction Map]]

