# Step 6 Workflow Explanation - Blender -> Ground Truth -> Regular/Raycast -> Tool Error

## One-minute explanation
Dau tien, em dung mot mo hinh ham duong sat cong trong Blender. Vi mo hinh nay do minh kiem soat, em dat truoc do lun that tai dinh ham cho 6 moc thoi gian T0-T5. Day la ground truth.

Tu cung mot mo hinh do, em tao hai bo du lieu kiem thu. Bo thu nhat la regular clean, tuc la xuat truc tiep be mat lining sach de kiem tra thuat toan trong dieu kien ly tuong. Bo thu hai la raycast field-like, tuc la mo phong may quet laser TLS ban tia tu nhieu tram doc theo ham cong, nen du lieu co noise, occlusion va dropout giong thuc dia hon.

Sau do em chay tool Step 6 tren ca hai bo du lieu. Tool luon do cung mot thong so la crown settlement, tuc lun dinh ham, tai cung vi tri Ch 52.0m. Cuoi cung em so ket qua tool voi ground truth de tinh sai lech theo mm va phan tram.

Ket qua: regular clean co MAPE 1.15%, raycast field-like co MAPE 2.315%. Raycast sai so cao hon vi giong thuc dia hon, nhung ca hai van bam dung xu huong lun tu T0 den T5.

## Formula
- Error mm = Tool result - Ground truth
- Error % = |Error mm| / |Ground truth mm| x 100
- T0 khong dung de tinh MAPE vi ground truth bang 0 mm.

## Main result table
| Time | Ground truth mm | Regular tool mm | Raycast tool mm | Regular error % | Raycast error % |
|---|---:|---:|---:|---:|---:|
| T0 | 0.0 | 0.0 | 0.0 | - | - |
| T1 | -10.0 | -9.9 | -10.243 | 1.00% | 2.43% |
| T2 | -22.0 | -21.7 | -21.632 | 1.36% | 1.67% |
| T3 | -38.0 | -37.6 | -37.070 | 1.05% | 2.45% |
| T4 | -58.0 | -57.3 | -56.607 | 1.21% | 2.40% |
| T5 | -80.0 | -79.1 | -77.900 | 1.13% | 2.63% |

## Key message for professor
Tool Step 6 is validated against a known Blender ground truth. The clean branch checks algorithm accuracy, and the raycast branch checks field-like robustness. The main measurement is crown settlement at Ch 52.0m, with average error 1.15% for clean data and 2.315% for raycast TLS data.
