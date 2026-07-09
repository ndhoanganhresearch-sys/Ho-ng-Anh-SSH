# Dataset T0-T5

#dataset #deformation #point-cloud

## Mục đích

Bộ dữ liệu time-series deformation dùng để kiểm tra biến dạng tunnel theo nhiều epoch.

## Vị trí

- Thư mục: `tunnel_project/data/time_series_deformation/`
- Manifest: `tunnel_project/data/time_series_deformation/manifest.json`
- Ground truth: `tunnel_project/data/time_series_deformation/ground_truth.csv`

## Epoch

- `T0.las`: baseline sạch
- `T1.las` đến `T5.las`: các epoch biến dạng

## File kiểm chứng

- `baseline_pairs.csv`: biến dạng tích lũy `T0 -> Tn`
- `incremental_pairs.csv`: biến dạng tăng thêm `Tn -> Tn+1`
- `README.md`: mô tả dataset

## Liên kết

- [[Step 6 Deformation]]
- [[Experiment Log]]
- [[Research Claims]]
