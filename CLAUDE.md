# CLAUDE.md - Huong dan cho Claude Code

Muc tieu cua file nay la giup Claude lam viec an toan, dung workflow, va verify duoc thay doi trong du an SSL Tunnel Analysis.

## Cach lam viec mac dinh

Moi task code nen theo vong lap:

1. Investigate: doc file lien quan, tim root cause, khong sua voi.
2. Plan: neu task lon, de xuat plan ngan va neu rui ro.
3. Implement: sua toi thieu, dung style hien co, khong refactor ngoai pham vi.
4. Verify: chay test gan nhat truoc, sau do chay gate rong hon neu can.
5. Summarize: bao file da sua, lenh da chay, ket qua, rui ro con lai.

## Karpathy-style coding discipline

Ap dung tinh than tu `multica-ai/andrej-karpathy-skills`: uu tien code don gian, thay doi toi thieu, va verify duoc.

- Think before coding: neu yeu cau mo ho, neu assumption ro rang; neu rui ro cao thi hoi lai truoc khi sua.
- Simplicity first: khong them abstraction/config/feature neu user khong yeu cau; neu cach lam dang qua phuc tap, rut gon.
- Surgical changes: chi sua dong/file can thiet; khong refactor, format, hay cleanup code khong lien quan.
- Goal-driven execution: voi task nhieu buoc, dat success criteria ngan va verify bang test/build/smoke gan nhat.
- Diff discipline: moi dong thay doi phai trace duoc ve yeu cau cua user; unrelated issue chi mention trong handoff.

## Quy tac bat buoc

- Khong refactor code khong lien quan khi fix bug hoac them feature.
- Khong revert thay doi cua user hoac artifact benchmark tru khi duoc yeu cau ro.
- Doc file truoc khi edit; neu file thay doi trong luc lam, doc lai truoc khi sua tiep.
- Treat benchmark numbers as evidence: khong claim thuat toan tot hon neu chua co so do.
- Giu workflow T0/Tn: T0 la reference, Tn la epoch can so sanh.
- Warning deformation phai gan voi section/chainage cuc bo, khong highlight tran lan.
- Headroom la optional tren Windows; native compression day du chay qua WSL `.venv-headroom`.
- PaddleOCR la optional; dung cho report/label/document, khong dua vao core point-cloud math.

## Duong dan va moi truong

- Workspace Windows: `C:\Users\ssl\Desktop\Code Python\data python cusor`
- Project chinh: `tunnel_project/`
- Python Windows: `..\.venv\Scripts\python.exe` khi dang o `tunnel_project/`
- Python WSL Headroom: `.venv-headroom/bin/python`
- App entrypoint: `tunnel_project/run_tunnel_analysis.py`
- Package chinh: `tunnel_project/tunnel_analysis/`

Khong tron path Windows voi WSL:

- PowerShell dung `C:\Users\ssl\...`
- Bash/WSL dung `/mnt/c/Users/ssl/...`

## Lenh verify chuan

Chay tu `tunnel_project/`.

### Gate nhanh mac dinh

```powershell
.\agent_verify.ps1 quick
```

Tuong duong voi compile package + smoke/guard co ban. Dung sau thay doi nho.

### Gate Step 6 / T0-Tn

```powershell
.\agent_verify.ps1 step6
```

Dung khi sua deformation, registration, centerline, section, warning 2D/3D, pipeline T0/Tn.

### Gate AI / Headroom

```powershell
.\agent_verify.ps1 ai
```

Dung khi sua `headroom_adapter.py`, `rag_ai.py`, `digital_twin.py`, OCR/RAG/AI integration.

### Gate file cu the

```powershell
.\agent_verify.ps1 compile tunnel_analysis\parameters.py tunnel_analysis\ui\widgets.py
```

Dung khi chi can compile nhanh cac file vua sua.

## Mapping task -> verify

- Small Python logic: `agent_verify.ps1 compile <changed_files>` roi smoke gan nhat neu co.
- UI PyQt/PyVista: compile + launch app neu feasible; kiem tra widget fit va step order.
- Registration/T0-Tn/deformation: `agent_verify.ps1 step6`.
- Clean noise/outlier/cable: smoke auto-denoise + benchmark theo `BENCHMARK_WORKFLOW.md`.
- Blender synthetic dataset: `smoke_test_blender_dataset.py` va `benchmark_blender_dataset.py`.
- AI/Headroom/RAG/OCR: `agent_verify.ps1 ai`.
- Paper/research claim: theo `RESEARCH_WORKFLOW.md`, `MATERIAL_PASSPORT.md`, `PAPER_REVIEW_CHECKLIST.md`.

## MCP va tool integration

Workspace `.mcp.json` co:

- `headroom`: local Headroom MCP server voi `HEADROOM_MCP_READ=on`. Dung cho compression/RAG read, digital-twin/AI context.
- `blender`: Blender MCP bridge, dung khi can scene inspection, 3D visualization, render, Blender-side scripting.
- `openalex`: academic literature MCP, dung de tim paper, survey/review, citation metadata, va research gap theo topic.
- `notebooklm`: NotebookLM MCP, dung de tong hop/ review tai lieu, sinh draft, doc-cross-query. Chi cho draft/review, khong dung lam core point-cloud math.

Khi user yeu cau kiem research gap:

1. Dung `openalex` de tim survey/review paper moi nhat theo topic, uu tien 2021-2026.
2. Lay paper co citation cao va paper moi gan day de so sanh trend.
3. Tom tat bang: paper, year, method/topic, limitation/open problem, possible gap.
4. Khong claim gap la "chua ai lam" neu chua verify bang citation/search tiep.

Neu MCP khong hien trong session, restart agent/Claude Code de load lai `.mcp.json`.

## Repo & MCP Router (doc dau moi task de chon dung)

Quy tac vang: chi PHAT TRIEN trong `tunnel_project/`. Cac repo `_ref_*` la READ-ONLY, chi
lay y tuong/thuat toan/benchmark, khong import nguyen khoi; neu trich dung phai ghi lai
o `REPO_INTEGRATION_STATUS.md`. Source of truth chi tiet: `REPO_INVENTORY.md` +
`REPO_INTEGRATION_STATUS.md` (doc khi can sau).

Bang dinh tuyen: loai task -> noi lam viec (trong tunnel_project) -> repo tham khao -> MCP -> verify.

| Loai task | Module lam viec | Repo tham khao (_ref, read-only) | MCP | Verify |
| --- | --- | --- | --- | --- |
| Deformation / T0-Tn / M3C2 / centerline / section | `tunnel_analysis/parameters.py`, m3c2, centerline | `_ref_FY387_calc` (deformation, dataset) | - | `agent_verify.ps1 step6` |
| Registration / alignment / outlier | `tunnel_analysis/registration.py` | `_ref_GROR` (robust GROR+FPFH) | - | `agent_verify.ps1 step6` |
| Lining segmentation / component | `tunnel_analysis/segmentation.py` | `_ref_SAM4Tun` (SAM + projection) | - | smoke segmentation |
| BIM / IFC export | `tunnel_analysis/ifc_exporter.py` | `_ref_Cloud2BIM` (scan-to-BIM) | - | IFC smoke + visual |
| Clean noise / cable / line | clean/denoise module | `_ref_PowerLine` | - | benchmark denoise |
| AI / RAG / OCR / digital twin | `rag_ai.py`, `headroom_adapter.py`, `digital_twin.py` | - | `headroom` | `agent_verify.ps1 ai` |
| Document/PDF/DOCX/PPTX/XLSX -> RAG | `rag_ai.py`, `tools/ingest_mineru_markdown.py`, outputs | `_ref_trending/MinerU` | `headroom` optional | MinerU output + RAG retrieval smoke |
| Agent codebase memory / structural search | MCP config/docs only until tested | `_ref_trending/codebase-memory-mcp` | optional MCP | isolated MCP/query smoke |
| Streaming 3D reconstruction ideas | prototype/tools first | `_ref_trending/lingbot-map` | `blender` optional | synthetic/visual smoke |
| GPU acceleration for NumPy-heavy kernels | prototype first, then target module | `_ref_trending/cupy` | - | CPU-vs-GPU numeric/timing benchmark |
| Research gap / paper / citation | docs, drafts, ARS skills | `_ref_FY387_calc` (benchmark) | `openalex` | RESEARCH_WORKFLOW |
| Doc synthesis / review / draft | docs/ | - | `notebooklm` | doc review |
| 3D scene / render / scene inspect | tools/ | - | `blender` | visual |
| UI PyQt / PyVista | `tunnel_analysis/ui/` | - | - | compile + launch app |

Cach chon repo: neu task khop ro mot dong trong bang -> TU DONG lam theo, khong hoi.
Chi hoi lai khi task mo ho hoac dung cham nhieu module/repo cung luc, hoac khi can trich
code tu `_ref_*` vao production (vi vi pham quy tac read-only).

Voi cac repo trending moi trong `_ref_trending/`, dung `tunnel_project/docs/TRENDING_REPO_DECISION_GUIDE.md`
va co the chay `tunnel_project/tools/choose_trending_repo.py "<mo ta task>"` de tu tinh diem chon repo.
Mac dinh: MinerU duoc phep dung nhu tooling tai lieu/RAG da test; codebase-memory-mcp/lingbot-map/CuPy
chi dung isolated/reference cho den khi co smoke test rieng va khong sua production code neu chua benchmark.

## Review focus

- Python runtime errors, imports, PyQt signal/slot.
- Threading va worker lifecycle trong UI.
- Unit conversion, section indexing, 2D/3D mapping.
- Registration khong duoc triet tieu bien dang cuc bo.
- Benchmark regression: clean noise, centerline, registration, T0/Tn comparison.
- Memory behavior voi point cloud lon tren may 32GB RAM.
- Research/paper claim phai co provenance va benchmark.

## Trang thai du an can nho

- UI giu 7 step va khong doi ten nut; Advanced/debug buttons an mac dinh, bat bang checkbox `Show Advanced` roi restart tool.
- App that su chay qua `run_tunnel_analysis.py` -> `tunnel_analysis/`.
- Legacy prototypes nhu `TunnelApp.py`, `main_app.py`, `New folder/` chi la tham khao lich su.
- `data/blender_step6_t1_tn/`, `data/blender_test_suite/`, `data/full_test/` la benchmark fixtures quan trong.
- Logs, screenshots, export tam va point-cloud lon khong commit tru khi duoc promote thanh fixture co ten.

## Format handoff cuoi task

Luon tom tat ngan gon:

- Changed: file/module da sua.
- Verified: lenh da chay va ket qua.
- Risks: rui ro con lai hoac test chua chay.
- Next: de xuat buoc tiep theo neu co.

## Cap nhat hien trang moi - Time-series T0~T5 va Step 6

### Dataset T0~T5 moi tao

Da co bo dataset sach de test time-series deformation:

- Thu muc: `tunnel_project/data/time_series_deformation/`
- Script tao lai: `tunnel_project/tools/create_time_series_deformation_dataset.py`
- Test kiem chung: `tunnel_project/test_time_series_deformation_dataset.py`

Cac file chinh:

- `T0.las` den `T5.las`: 6 epoch point cloud.
- `T0.txt` den `T5.txt`: ban debug text 8 cot `x y z nx ny nz intensity label`.
- `ground_truth.csv`: bien dang tuyet doi theo tung epoch.
- `baseline_pairs.csv`: bien dang tich luy `T0 -> Tn`.
- `incremental_pairs.csv`: bien dang tang them `Tn -> Tn+1`.
- `manifest.json`: metadata may doc duoc.
- `README.md`: huong dan dung dataset.

Thong so ground truth:

- Tunnel dai `80 m`, ban kinh `3.0 m`, moi epoch `15456` diem.
- `T0` la baseline sach.
- Crown settlement tai chainage `20 m`: `0 -> -45 mm` tu `T0` den `T5`.
- Sidewall convergence tai chainage `45 m`: `0 -> -35 mm` tu `T0` den `T5`.
- Local damage tai chainage `65 m`: bat dau o `T3`, den `-40 mm` o `T5`.
- Dataset nay da registered san: `registration.transform = identity`, `rmse_mm = 0` trong `manifest.json`.

Lenh tao lai va test:

```powershell
cd "C:\Users\ssl\Desktop\Code Python\data python cusor\tunnel_project"
..\.venv\Scripts\python.exe tools\create_time_series_deformation_dataset.py
..\.venv\Scripts\python.exe test_time_series_deformation_dataset.py
```

Ket qua mong doi:

- `TIME-SERIES DEFORMATION DATASET TEST PASSED`

### Nguyen nhan va fix tab Time-Series Plot

Truoc do tab `Time-Series Plot` nhin nhu khong hoat dong vi:

- `spatiotemporal_series()` tra ve gia tri cho cac epoch sau `T0`.
- Neu chi load cap `T0/Tn`, ket qua chi co 1 diem.
- `LinePlotWidget` can it nhat 2 diem de ve line.
- Vi vay chart trong tab trong/khong thay duong.

Fix da lam trong `tunnel_project/tunnel_analysis/ui/main_window.py`:

- Neu co nhieu scan `T0~T5`, Step `6.1 Plot deformation trend` dung tat ca epoch trong `context.scans`.
- Neu chi co cap `T0/Tn`, chart tu them baseline `T0 = 0 mm` va ve `Tn = p95_abs_mm`.
- Bieu do hien tai ve `p95 absolute displacement` thay vi median, vi median toan cloud thuong gan 0 khi bien dang cuc bo.

Cac dong lien quan:

- `tunnel_analysis/ui/main_window.py`: slot `_slot_6_2_plot`
- `tunnel_analysis/ui/main_window.py`: dispatch `elif key == "6.2_plot"`

Lenh verify da chay:

```powershell
..\.venv\Scripts\python.exe test_step6_timeseries.py
..\.venv\Scripts\python.exe test_time_series_deformation_dataset.py
```

Ca hai deu PASS.

### Cach dung dataset moi trong tool

Dung nhanh theo cap baseline:

1. Load `data/time_series_deformation/T0.las`.
2. Load `data/time_series_deformation/T5.las` lam Tn.
3. Dataset da aligned san, co the bo qua registration hoac chay `3.0` de kiem tra RMSE.
4. Chay `6.1 Plot deformation trend T0->Tn`.
5. Chart se co baseline `T0=0` va diem Tn theo `p95_abs_mm`.

Dung theo chuoi day du:

1. Load/add du cac scan `T0.las` den `T5.las` vao `context.scans`.
2. Chay `6.1 Plot deformation trend T0->Tn`.
3. Slot se dung tat ca scan trong `context.scans` va ve trend nhieu epoch.

Luu y hien tai:

- UI hien tai chua co workflow rieng that dep de chon mot luc 6 epoch `T0~T5`; co the can nang cap UI sau.
- Dataset sach chu yeu de validate deformation/time-series, khong phai de stress-test registration.
- Sau nay can tao bo realistic/Blender LiDAR co offset/rotation/noise/targets de test `3.0 Auto-align`.

### Neu tiep tuc phat trien Step 6

Uu tien tiep theo:

1. Tao UI load multi-epoch `T0~T5` mot lan.
2. Hien label truc X theo epoch name thay vi chi index.
3. Xuat Excel/PDF rieng cho time-series: baseline, incremental, warning count per epoch.
4. Them chart `baseline deformation` va `incremental deformation` tach rieng.
5. Them so sanh output tool voi `ground_truth.csv` de tinh sai so mm.

## Quan ly nut UI Public/Advanced

Da co file registry: `tunnel_project/docs/UI_BUTTON_REGISTRY.md`.

Quy tac hien tai:

- Khong xoa nut Advanced khi chua duoc yeu cau ro.
- Khong doi ten/doi so nut hien co neu user khong yeu cau.
- `CORE_FEATURES_ONLY = True` giu UI gon theo 7 step.
- `SHOW_ADVANCED_BUTTONS = False` an cac nut Advanced/debug.
- Muon debug day du, doi `SHOW_ADVANCED_BUTTONS = True` trong `tunnel_analysis/ui/main_window.py` roi restart app.
- Nut Advanced bi an, khong bi xoa; slot/function van phai giu de benchmark va troubleshooting.
