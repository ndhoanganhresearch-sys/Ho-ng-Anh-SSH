# Easy Work Checklist

Muc tieu: lam nhung viec nho, ro rang, it rui ro truoc; neu muc nao da xong thi danh dau va khong lam lai.

## Nguyen tac

- Giu nguyen 7 step hien tai.
- Khong doi ten nut va khong doi so step hien tren UI.
- Khong xoa nut Advanced; chi an/hien bang `Show Advanced`.
- Khong sua thuat toan core neu khong co benchmark/test kem theo.
- Sau moi thay doi UI nho, chay compile file lien quan truoc.

## Cong viec de da xong

| Nhom | Viec | Trang thai | Bang chung / vi tri |
| --- | --- | --- | --- |
| UI | An overlay chu do/xanh trong viewport, giu geometry canh bao | Done | `tunnel_analysis/ui/main_window.py` |
| UI | Giu 7 step va khong renumber nut | Done | `tunnel_analysis/ui/main_window.py`, `docs/UI_BUTTON_REGISTRY.md` |
| UI | Them `Show Advanced` de quan ly nut an | Done | `tunnel_analysis/ui/main_window.py` |
| Step 1 | `Add scan station (+)` chon nhieu tram mot luc | Done | `_slot_1_3_add_scan` |
| Step 7 | Hoi co mo file vua export khong | Done | `_offer_open_exported_file` |
| Docs | Lap bang Public/Advanced button registry | Done | `docs/UI_BUTTON_REGISTRY.md` |
| Docs | Ghi quy tac lam viec cho Claude/Codex | Done | `../CLAUDE.md` |
| Data | Tao dataset T0-T5 time-series deformation | Done | `data/time_series_deformation/` |
| Step 6 | Fix time-series plot co baseline T0 | Done | `tunnel_analysis/ui/main_window.py` |

## Cong viec de nen lam tiep

| Uu tien | Viec | Ly do | Kiem tra nhanh |
| --- | --- | --- | --- |
| P1 | Tao user guide 7 step ngan gon | De nguoi dung bam dung thu tu | Doc `README.md` / app UI |
| P1 | Rà UI text con sot tieng Viet/Anh/Han | Giam loi ngon ngu trong demo | Search `_tr(...)` va dictionary |
| P1 | Chay `agent_verify.ps1 quick` | Biet tool co loi co ban khong | `.\agent_verify.ps1 quick` |
| P1 | Chay `agent_verify.ps1 step6` neu vua sua Step 3/6 | Bao ve workflow T0/Tn | `.\agent_verify.ps1 step6` |
| P2 | Cap nhat benchmark baseline da co ket qua | De co moc so sanh ve sau | `BENCHMARK_BASELINES.md` |
| P2 | Tao bang du lieu test/fixture dang co | De biet dataset nao test tinh nang nao | `data/*/README.md` |
| P2 | Rà file export CSV/Excel/PDF/IFC dat ten ro rang | De nguoi dung khong nham file | Test export nho |
| P2 | Viet checklist demo truoc khi quay video/bao cao | De demo khong bi sai buoc | Manual checklist |

## Viec de nhung can can than

| Viec | Rui ro | Cach lam an toan |
| --- | --- | --- |
| Sua text UI | Co the thieu translation key | Chi sua text hien thi, compile `i18n_v4.py` va `main_window.py` |
| An/hien nut | Co the mat duong vao tinh nang | Sua `CORE_STEP_CODES` / registry, khong xoa slot |
| Sua export | Co the anh huong PDF/Excel/IFC | Test tung nut export voi dataset nho |
| Sua Step 6 chart | Co the lech logic T0/Tn | Chay `agent_verify.ps1 step6` |

## Viec khong de, de sau

- Doi thuat toan ICP/registration.
- Thay doi threshold deformation theo tieu chuan neu chua mapping clause.
- Toi uu memory point cloud lon.
- RAG/AI tu dong ket luan engineering neu chua co evidence.
- Benchmark so sanh voi MATLAB/manual workflow.
