# Step 6 Deformation

#step6 #deformation #m3c2 #tunnel-analysis

## Mục tiêu

Đo và kiểm chứng biến dạng tunnel giữa baseline `T0` và các epoch `Tn`.

## Input chính

- [[Dataset T0-T5]]
- Point cloud baseline `T0`
- Point cloud target `T1` đến `T5`

## Output mong muốn

- Bản đồ biến dạng
- Sai số so với `ground_truth.csv`
- Hình/biểu đồ phục vụ báo cáo và paper

## Tiêu chí pass

- Chạy được pipeline Step 6 không lỗi runtime
- Kết quả deformation đúng đơn vị
- Crown settlement theo T0-T5 khớp xu hướng ground truth
- Có log/ảnh/kết quả lưu lại trong [[Experiment Log]]

## Lệnh kiểm tra

`.\agent_verify.ps1 step6`

> Nếu lệnh trên không đúng trong phiên làm việc, xem [[QUICK_REFERENCE]].

## Liên kết

- [[Dataset T0-T5]]
- [[Experiment Log]]
- [[Research Claims]]
