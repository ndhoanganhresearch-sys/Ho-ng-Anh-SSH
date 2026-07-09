# Research Claims

#paper #research #claims

Nơi gom các claim khoa học cần chứng minh bằng dữ liệu, benchmark và citation.

## Claim 1: Time-series deformation có ground truth kiểm chứng được

### Evidence cần có

- [[Dataset T0-T5]]
- `ground_truth.csv`
- Kết quả Step 6 trong [[Experiment Log]]

### Trạng thái

- [x] Supported for synthetic T0-T5 dataset by [[Step 6 Benchmark Table]] and [[EXP Step6 T0-T5]]

## Claim 2: Pipeline Step 6 đo biến dạng nhất quán theo epoch

### Evidence cần có

- Kết quả `T0 -> T1` đến `T0 -> T5`
- Sai số theo từng epoch
- Hình deformation map

### Trạng thái

- [x] Supported for crown deformation tracking across T0-T5 by [[Step 6 Benchmark Table]]

## Claim 3: Quy trình có thể dùng cho báo cáo/paper tunnel monitoring

### Evidence cần có

- Benchmark
- Hình minh họa
- So sánh với phương pháp liên quan
- Citation từ OpenAlex/literature review

### Trạng thái

- [ ] Partially supported; still needs citation review, limitations text, and final figures/tables


## Gap Reports

Use these reports to decide which claims are strong enough for publication and which remain future work.

- [[GAP_MASTER_REPORT_2026]] - master gap assessment
- [[GAP_VERIFICATION_REPORT_2026]] - verification-focused gap review
- [[GAP_FEASIBILITY_REPORT]] - feasibility and implementation risk
- [[GAP_FULL_PROJECT_SCAN_2026]] - full project scan
- [[REPO_INTEGRATION_STATUS]] - reference repo integration status

## Draft Text

- [[Validation Method Draft]]
- [[Figure Table Index]]
- [[Citation Notes]]
- [[References Draft]]
- [[Manuscript Outline - Tunnel Time-Series Deformation]]
- [[Limitations Draft]]
- [[Paper Abstract Draft]]
- [[Paper Section Draft - Validation]] - method and validation text derived from benchmark evidence

## Evidence Chain

```text
Dataset T0-T5
  -> Ground Truth Definition
  -> Step 6 Benchmark Table
  -> EXP Step6 T0-T5
  -> Validation Method Draft
  -> Research Claims
```

## Liên kết

- [[Dataset T0-T5]]
- [[Step 6 Deformation]]
- [[Experiment Log]]
- [[Ground Truth Definition]]
- [[Step 6 Benchmark Table]]
- [[Future Direction Map]]
- [[PUBLICATION_ROADMAP]]





