# NutriVision Progress Record

**Cập nhật:** 2026-08-13<br>
**Trạng thái hiện tại:** Phase A, B và D hoàn tất; C1-C4 pass, OpenAI live smoke đã pass; C5 còn kiểm tra trực quan trên điện thoại thật.

Tài liệu này lưu lại các quyết định, kết quả kiểm tra và bằng chứng có thể dùng khi viết báo cáo hoặc tiếp tục phát triển.

Quy ước từ thời điểm này: sau mỗi nhóm thay đổi có ý nghĩa, nhật ký phải ghi mục tiêu, file/commit liên quan, lệnh kiểm tra, kết quả và quyết định kỹ thuật. Không ghi các thao tác đọc file nhỏ lẻ để tránh làm nhiễu tư liệu báo cáo.

## 1. Phạm vi đã chốt

- Ứng dụng triển khai checkpoint `Baseline B` tại `models/weights/best_baseline_B.pt`.
- SHA-256 checkpoint B: `18b8f1dd160a4b6df6ae0f4dc31d00ec729722daefafdc50422dc9e36d845998`.
- 12 lớp checkpoint được ánh xạ sang canonical food ID trong `config.MODEL_CLASS_MAP`.
- A0, A và B được giữ để làm bằng chứng thực nghiệm; không train đè hoặc xóa artifact khi chưa có backup.
- A0/A/B là so sánh hệ thống. Không kết luận augmentation là nguyên nhân duy nhất của chênh lệch nếu chưa thực hiện controlled ablation.

## 2. Kết quả benchmark phục vụ báo cáo

Nguồn: `test_model/benchmark_results_common_v1/overall_metrics.csv`.

| Model | Precision | Recall | mAP50 | mAP50-95 | FP trên 10 ảnh negative | Inference CPU (ms/ảnh) |
|---|---:|---:|---:|---:|---:|---:|
| Baseline A0 | 0.7968 | 0.7129 | 0.7666 | 0.5507 | 1 | 78.06 |
| Baseline A | 0.8750 | 0.8450 | 0.8928 | 0.6647 | 1 | 77.81 |
| Baseline B | 0.8805 | 0.8300 | 0.9009 | 0.6547 | 0 | 80.95 |

Thiết lập benchmark chung:

- 404 ảnh, `imgsz=640`, IoU `0.7`, confidence tính mAP `0.001`, batch `16`, CPU.
- Cấu hình vận hành app: confidence `0.45`, IoU `0.45`.
- Manifest benchmark SHA-256: `93412285838b95a36bcd509bcf2a871af28c84ed982cac8b83bae242d1b51913`.
- Baseline B được chọn để triển khai vì có precision/mAP50 cao nhất và không có false positive trên 10 ảnh negative. Baseline A cao hơn ở recall và mAP50-95; cần nêu rõ giới hạn negative set nhỏ trong báo cáo.

## 3. Công việc đã hoàn thành

### Tích hợp model và benchmark

- Tích hợp mapping raw label checkpoint sang 12 canonical ID cùng nutrition DB tương ứng.
- Thêm xác thực SHA-256 và exact label contract trước khi inference.
- Thêm dashboard `pages/4_Danh_gia_mo_hinh.py` dùng CSV benchmark chung.
- Chỉ bật randomized demo khi `ENABLE_RANDOM_DEMO=true`.

### Sửa lỗi inference ảnh

- Đã phát hiện Ultralytics diễn giải NumPy image input theo BGR trong khi app đưa ảnh RGB.
- Đã chuyển RGB sang BGR trong `models/detector.py` trước khi gọi YOLO.
- Kiểm tra trên ảnh test B: app trả `banh_mi` confidence `0.9051` và `bun_bo_hue` confidence `0.4749`.

### Ổn định môi trường

- Cài Python `3.11.9` từ installer chính thức của Python Software Foundation.
- Tạo `.venv311`, cài `requirements.txt`, và xác nhận `pip check` không báo dependency lỗi.
- `python test_imports.py` pass toàn bộ: config 12 lớp, nutrition, LLM fallback, visualization và checksum checkpoint.
- Streamlit health endpoint trả `ok`; các trang chủ, phân tích, lịch sử, hồ sơ và dashboard đều render qua `streamlit.testing.v1.AppTest`.

### Privacy và UI

- Meal history chỉ lưu trong Streamlit session; không còn đọc/ghi/xóa `data/meal_history.json` dùng chung.
- Lịch sử được thông báo rõ là mất khi browser session kết thúc.
- Chuyển các lời gọi `use_container_width=True` sang `width="stretch"` để tương thích Streamlit hiện tại.

## 4. Commit liên quan

| Commit | Nội dung |
|---|---|
| `aa12219` | Tích hợp Baseline B, dashboard benchmark, state helper và artifact metadata nhỏ |
| `f0fff31` | Sửa kênh màu BGR cho YOLO inference |
| `6a3a41c` | Tách meal history theo Streamlit session, cập nhật Phase B và UI API |
| `9da861d` | Ghi nhận backup, cleanup workspace và chuẩn hóa launcher Python 3.11 |

## 5. Backup Phase A bắt buộc

Git chỉ lưu source code và metadata nhỏ. Các artifact lớn hoặc ignored/untracked phải có ít nhất một bản sao ở vị trí độc lập với `E:\DoAn`, ví dụ Google Drive, OneDrive hoặc ổ cứng ngoài.

**Trạng thái:** Người dùng xác nhận ngày 2026-08-06 rằng toàn bộ danh sách bên dưới đã được upload lên Google Drive. Hash checkpoint local đã được ghi lại; hash của bản cloud chưa được kiểm tra lại bằng cách tải xuống.

Sao lưu các mục sau vào một thư mục có ngày, ví dụ `NutriVision_Backup_2026-08-06`:

- `models/weights/best_baseline_B.pt`
- `test_model/weights_test/`
- `KetQuaTrain/`
- `datasets/`
- `test_model/benchmark_common_v1/images/` và `test_model/benchmark_common_v1/labels/`
- `test_model/benchmark_results_common_v1/`
- `notebooks/`
- `BaoCao_DoAn.docx`

Sau khi copy, xác minh ít nhất checkpoint B bằng lệnh:

```powershell
Get-FileHash -Algorithm SHA256 "<duong-dan-backup>\best_baseline_B.pt"
```

Hash phải trùng giá trị ở mục 1. Không xóa file local trước khi kiểm tra được cả bản backup và hash.

## 6. Virtual environment

| Thư mục | Python | Dung lượng | Khuyến nghị |
|---|---:|---:|---|
| `.venv` | 3.10.6 | 1.49 GiB | Đã xóa ngày 2026-08-06 |
| `.venv311` | 3.11.9 | 1.60 GiB | Giữ; đây là môi trường đã pass toàn bộ kiểm tra Phase B |

`.venv311/` đã được thêm vào `.gitignore`; `run.bat` và `run_ngrok.bat` ưu tiên môi trường này. `.venv` cũ đã được xóa sau khi xác nhận không có executable nào chạy từ thư mục đó.

## 7. Nhật ký thực hiện

### 2026-08-06 - Chuẩn hóa môi trường và cleanup

**Mục tiêu:** chỉ giữ môi trường Python 3.11 đã kiểm chứng và loại bỏ file sinh tự động hoặc script một lần không còn tác dụng.

Đã thực hiện:

- Xóa `.venv` Python 3.10.6, thu hồi khoảng 1.49 GiB.
- Xóa `__pycache__/` tại root và các module, cùng `test_model/benchmark_common_v1/labels.cache`.
- Xóa log cài đặt nhầm `7.2.0` và năm ảnh crawler thử trong `test_bing/`.
- Xóa `remove_emojis.py`, `rename_classes.py`, `rename_xoi.py` và `test_crawler.py`; đây là migration/no-op/network probe, không thuộc runtime hoặc automated test.
- Cập nhật launcher để ưu tiên `.venv311`.

Cố ý giữ:

- `training/fetch_pho_xoi.py` vì ghi lại truy vấn và target thu thập bổ sung cho Phở/Xôi, còn hữu ích cho provenance trong báo cáo.
- `test_model/Ket_Qua_So_Sanh/` vì chứa output định tính đủ A0/A/B và `qualitative_predictions.csv`.
- Các checkpoint trùng ở `KetQuaTrain/` vì tổng dung lượng chỉ khoảng 18 MiB và còn có giá trị đối chiếu provenance.
- `BaoCao_DoAn_old.docx`, các `last.pt`, ảnh EDA và train outputs cho đến khi hoàn tất báo cáo.

Dung lượng thu hồi ước tính: khoảng 1.50 GiB. Artifact model, dataset, notebook, benchmark và báo cáo không bị xóa.

**Xác minh sau cleanup:**

- `.venv311` kích hoạt Python `3.11.9`.
- `python test_imports.py`: tất cả smoke checks pass.
- `pip check`: `No broken requirements found`.
- Inference fixture vẫn trả `banh_mi=0.9051` và `bun_bo_hue=0.4749`.
- `run.bat` khởi động Streamlit, health endpoint trả `ok`; process thực tế dùng Python 3.11 và `E:\DoAn\.venv311\Scripts\streamlit.exe`.
- `git diff --check`: không có lỗi whitespace.

Các artifact train/benchmark/report đã backup được thêm vào `.gitignore` theo đường dẫn cụ thể để giữ worktree sạch mà không xóa dữ liệu local.

### 2026-08-09 - Phase C1-C4: input, inference, HITL và LLM

**Mục tiêu:** kiểm tra các nhánh chính của luồng sản phẩm trước khi chuyển sang release test tự động.

Thay đổi sản phẩm:

- Giới hạn file upload ở 20 MB qua `server.maxUploadSize`.
- Đưa giới hạn ảnh vào `config.py`: tối đa 25 triệu pixel trước khi resize, cạnh tối đa 5000 px.
- Resize ảnh lớn trước bước chuyển sang RGB để giảm peak memory.
- Giữ xử lý EXIF orientation trước inference.

Kết quả kiểm tra:

| Test case | Expected | Actual | Kết quả |
|---|---|---|---|
| JPEG, PNG, WEBP | Đọc được ảnh RGB | Cả ba định dạng trả ảnh RGB đúng kích thước | Pass |
| EXIF orientation 6 | Ảnh `20x30` thành `30x20` | Kích thước `30x20` | Pass |
| Dữ liệu không phải ảnh | Không crash, báo lỗi tiếng Việt | Trả `None` và thông báo `Không thể đọc ảnh...` | Pass |
| Ảnh `5100x5100` | Resize về giới hạn | Trả ảnh `5000x5000` | Pass |
| Checkpoint thiếu | Báo rõ đường dẫn thiếu | `Không tìm thấy checkpoint tại ...` | Pass |
| Checkpoint sai checksum | Từ chối artifact | `Checksum checkpoint không khớp...` | Pass |
| Fixture 1 box Bánh mì | Nhận diện Bánh mì | `banh_mi=0.6901` | Pass |
| Fixture 3 box Bún riêu | Luồng trả detection hợp lệ | Phát hiện `1/3` box, `bun_rieu=0.7475` | Pass có giới hạn recall |
| 10 ảnh negative | Không false positive ở confidence 0.45 | `0/10` ảnh có detection, trung bình `106.95 ms/ảnh` sau warm-up | Pass |
| HITL Bánh xèo | Calo tuyến tính theo khẩu phần | `0.25x=145`, `1x=580`, `3x=1740` kcal | Pass |
| Hai box Bánh xèo | Cộng riêng từng box | Tổng `1160 kcal`, `48 g protein` | Pass |
| Không có API key | Sample advice có nhãn rõ | Trả nội dung `Đây là phân tích mẫu` | Pass |
| Key sai/lỗi mạng mô phỏng | Không crash, báo lỗi rõ | Trả `Lỗi kết nối AI` | Pass |

Ghi chú hiệu năng:

- Cold start gồm load checkpoint và khởi tạo runtime mất khoảng `8.02 giây` trên CPU ở lần đo này.
- Inference warm cho fixture multi-object khoảng `192 ms`; negative set trung bình khoảng `107 ms/ảnh`.
- Con số benchmark chuẩn trong mục 2 vẫn là nguồn chính để báo cáo hiệu năng; phép đo Phase C dùng để đánh giá trải nghiệm runtime.

Giới hạn được ghi nhận:

- Model bỏ sót hai trong ba box Bún riêu ở fixture multi-object tại confidence `0.45`. Không sửa bằng cách hạ ngưỡng tùy tiện vì ngưỡng đã được khóa theo benchmark.
- Responsive CSS đã có breakpoint `768 px` và `480 px`, dataframe có horizontal overflow và card/grid tự co. Kiểm tra trực quan trên điện thoại thật qua HTTPS vẫn đang chờ thực hiện thủ công.

Regression check sau thay đổi: `test_imports.py`, `pip check` và render bằng `AppTest` cho trang chủ cùng bốn trang chức năng đều pass.

### 2026-08-09 - Google LLM, C5 local và Phase D release gate

**Mục tiêu:** cấu hình một adapter Google dùng được cho cả Gemini/Gemma, tăng độ an toàn responsive/session key và chuyển các kiểm tra thủ công quan trọng thành một release gate có assertion.

Thay đổi sản phẩm:

- Thay SDK `google-generativeai` đã deprecated bằng `google-genai`; `.venv311` dùng `google-genai 2.17.0` và đã gỡ SDK cũ.
- Đổi provider Google thành `LLM_PROVIDER=google`; model được chọn qua `GOOGLE_MODEL`, mặc định `gemini-3.5-flash`. Model Gemma hosted có thể dùng cùng adapter bằng cách thay đúng model ID từ AI Studio.
- Cập nhật `.env.example` nhưng không tạo hoặc commit `.env`; API key thật vẫn chỉ nằm trong environment hoặc Streamlit session.
- Thêm cảnh báo rằng dữ liệu sinh trắc học và bữa ăn được gửi tới provider khi người dùng yêu cầu tư vấn.
- Không còn trả exception thô của SDK ra UI, tránh lộ key hoặc chi tiết request trong lỗi.
- AppTest phát hiện nút xóa API key chỉ xóa runtime config nhưng widget password có thể được Streamlit khôi phục sau rerun. Đã sửa để đặt cả hai password field về chuỗi rỗng và thêm regression test.
- Tách xử lý ảnh sang `utils/images.py`; giới hạn đồng thời tổng pixel và cạnh dài, giữ EXIF transpose và resize trước RGB.
- Tách record/sort history sang `utils/history.py`; history vẫn chỉ được append, đọc và xóa trong session hiện tại.
- Bổ sung responsive safeguards cho tab, radio, uploader/camera, metric, Plotly, dataframe và Markdown dài.
- Đồng bộ emoji Bún bò Huế giữa `config.py` và nutrition DB sau khi contract test phát hiện chênh lệch.

Release suite:

- Thêm `pytest.ini` và test cho nutrition, hợp đồng 12 lớp, image input, session history, Google/OpenAI adapter mock, lỗi provider/key, năm Streamlit page và responsive CSS.
- Model smoke test dùng checkpoint Baseline B thật và fixture benchmark có SHA-256 `07fb336590bd3a8e7209e13f90ebfdda04fb0b1e2f2f53f905e8179e56467c7d`.
- Pipeline test xác nhận fixture trả `banh_mi` với confidence tối thiểu `0.60`, tổng chuẩn `380 kcal`, tạo prompt, sample advice và record history; một fixture negative trả danh sách rỗng.
- Test live LLM được đánh dấu `live` và chỉ chạy khi `RUN_LIVE_LLM_TEST=1`, nên release mặc định không tiêu quota hoặc phụ thuộc mạng.

Kết quả xác minh:

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `python -m pytest -q` | `66 passed, 1 skipped` trong `12.08s`; skip duy nhất là live LLM |
| `python test_imports.py` | Pass config, nutrition, fallback, chart và checksum Baseline B |
| `python -m pip check` | `No broken requirements found` |
| Khởi tạo `google.genai.Client` bằng key giả, không gọi mạng | Pass; client được tạo và đóng |
| Streamlit health endpoint local | `ok` |
| `AppTest` | Trang chủ và bốn page chức năng render không exception |
| Secret pattern scan | Không tìm thấy Google/OpenAI/ngrok token có dạng secret trong source/tài liệu |
| `git diff --check` | Không có lỗi whitespace |

Giới hạn còn lại:

- Chưa có `GEMINI_API_KEY`, nên chưa gọi live Gemini/Gemma và chưa khóa model cuối bằng thử nghiệm cùng prompt.
- Chưa có `NGROK_AUTHTOKEN` và điện thoại thật trong phiên kiểm tra, nên camera/touch/layout thực tế qua HTTPS vẫn pending.
- Edge headless chỉ chụp được loading state bất đồng bộ của Streamlit; ảnh đó không được dùng làm bằng chứng responsive.
- Checkpoint và benchmark image fixture đang gitignored. Release gate pass trên workspace hiện tại, nhưng clean clone cần cơ chế phân phối/xác minh artifact ở Phase E.

### 2026-08-13 - Khóa LLM OpenAI

**Quyết định:** Dùng OpenAI `gpt-4o-mini` làm LLM triển khai. Người dùng đã cấu hình `LLM_PROVIDER=openai`, `OPENAI_MODEL=gpt-4o-mini` và API key trong `.env`; chỉ xác minh provider, model và sự hiện diện của key, không đọc hoặc ghi secret.

Thay đổi liên quan:

- Default không-secret trong `config.py` và `.env.example` là `openai` / `gpt-4o-mini`.
- UI Hồ sơ ưu tiên OpenAI trong thứ tự provider và trường API key; Google Gemini/Gemma vẫn là phương án thay thế có thể bật qua environment.
- `README.md` và `PLAN.md` ghi đúng quyết định triển khai để tránh nhầm model mặc định trong demo/báo cáo.
- Live smoke test dùng fixture tổng hợp với `RUN_LIVE_LLM_TEST=1` pass: OpenAI `gpt-4o-mini` trả lời thành công trong `17.50s`. Test không gửi ảnh hoặc dữ liệu người dùng thật.

### 2026-08-13 - Trợ lý AI tùy chọn và giao diện light health

**Mục tiêu:** người dùng tự quyết định có dùng LLM trong phiên hiện tại hay không, đồng thời đưa giao diện Streamlit về ngôn ngữ thiết kế sáng, card gọn và ưu tiên mobile của `ui_example/`.

Thay đổi sản phẩm:

- Bổ sung `assistant_enabled` trong shared session state, mặc định bật để không thay đổi hành vi cũ.
- Trang Hồ sơ có công tắc **Bật trợ lý AI cho phiên này**, nêu rõ dữ liệu nào chỉ được gửi khi người dùng chủ động yêu cầu tư vấn.
- Trang Phân tích ảnh dùng cùng công tắc. Khi tắt, advice cũ bị xóa, nút gọi AI bị vô hiệu hóa và không khởi tạo `NutriLLM`; YOLO, HITL, tính macro và lưu history vẫn hoạt động.
- Trang chủ phản ánh trạng thái tắt của trợ lý thay vì hiển thị provider/API key là sẵn sàng.
- Áp dụng palette light health từ `ui_example/`: nền `#f8fafc`, card trắng, primary xanh lá, sidebar/header sáng và khối tư vấn AI tách biệt.
- `utils/llm.py` đã có `SYSTEM_PROMPT` dùng cho cả OpenAI (`role=system`) và Google (`system_instruction`); không thay đổi nội dung prompt trong đợt này.

Xác minh:

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `.venv311\\Scripts\\python.exe -m pytest -q tests/test_llm.py tests/test_pages.py` | `18 passed` trong `3.82s` |
| `.venv311\\Scripts\\python.exe -m compileall -q app.py pages utils` | Pass |
| `git diff --check` | Không có lỗi whitespace |

Giới hạn: chưa kiểm tra trực quan bằng browser/device thật cho palette mới; kiểm tra hiện tại xác nhận render qua `AppTest` và contract session state.

### 2026-08-13 - Ổn định launcher demo ngrok

**Mục tiêu:** tránh tunnel vào một Streamlit cũ và tránh giữ cổng local sau khi người dùng đóng demo.

Thay đổi sản phẩm:

- `run_ngrok.py` kiểm tra cổng `STREAMLIT_PORT` trước khi tạo Streamlit. Nếu cổng đang dùng, launcher dừng với hướng dẫn đóng instance cũ hoặc đổi cổng, thay vì thử kết nối nhầm vào server cũ.
- Trên Windows, launcher dừng toàn bộ process tree mà nó đã tạo bằng `taskkill /T`; điều này xử lý child process do Streamlit tạo.
- Cleanup dùng `try/finally` lồng nhau để Streamlit luôn được dừng và cổng luôn được giải phóng, kể cả khi ngrok disconnect/kill báo lỗi.
- `README.md` bổ sung hướng dẫn xử lý cổng đã dùng và lựa chọn `STREAMLIT_PORT=8502`.

Xác minh:

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `tests/test_run_ngrok.py` | Kiểm tra từ chối cổng bận và dừng child process để giải phóng cổng |
| `python -m pytest -q tests/test_run_ngrok.py tests/test_llm.py tests/test_pages.py` | Pass |

### 2026-08-13 - Mobile-first UI refinement

**Mục tiêu:** giảm mật độ thông tin và biểu tượng trang trí, ưu tiên thao tác một tay trên điện thoại.

Thay đổi sản phẩm:

- Đồng bộ `.streamlit/config.toml` sang light theme để không còn xung đột với CSS giao diện sáng.
- Sidebar mặc định thu gọn; trang chủ dùng luồng ba bước ngắn thay vì phần hướng dẫn dài.
- Rút gọn tiêu đề, nhãn nút, trạng thái và thông báo tại trang Hồ sơ, Phân tích ảnh, Lịch sử; emoji chỉ giữ ở ngữ cảnh món ăn khi thực sự hỗ trợ quét nhanh.
- Các action chính và input có chiều cao tối thiểu `44px`; thumb slider lớn hơn cho thao tác cảm ứng.
- Breakpoint mobile bổ sung khoảng trống đáy, quy tắc lưới 2 cột cho chỉ số và một cột cho màn hình hẹp; bảng/tab vẫn cuộn ngang khi cần.

Xác minh: `.venv311\\Scripts\\python.exe -m pytest -q tests/test_pages.py tests/test_llm.py tests/test_run_ngrok.py` trả `20 passed` trong `4.12s`; `compileall` và `git diff --check` pass.

### 2026-08-13 - Điều hướng mobile và giám sát tunnel

**Mục tiêu:** người dùng điện thoại không cần mở sidebar kiểu desktop và launcher không để Streamlit chạy nền khi ngrok tự đóng tunnel.

Thay đổi sản phẩm:

- Thêm thanh điều hướng đáy bằng chữ: Trang chủ, Phân tích, Lịch sử, Hồ sơ. Mục hiện tại được đánh dấu, không dùng icon.
- Ở breakpoint mobile (`<=768px`), ẩn hoàn toàn sidebar và nút mở sidebar; desktop vẫn dùng navigation mặc định của Streamlit.
- `run_ngrok.py` kiểm tra tunnel mỗi giây. Nếu ngrok không còn forwarder, launcher in thông báo và cleanup Streamlit để giải phóng cổng local.
- `AppTest` chạy từng file page riêng lẻ không có multipage registry; navigation helper bỏ qua riêng tình huống test này, còn app multipage thực tế vẫn render bottom navigation.

Xác minh: `.venv311\\Scripts\\python.exe -m pytest -q tests/test_pages.py tests/test_run_ngrok.py tests/test_llm.py` trả `20 passed` trong `4.00s`; `compileall` và `git diff --check` pass.

### 2026-08-13 - Xác minh mobile bằng browser thật

**Mục tiêu:** loại bỏ các giả định CSS dựa trên DOM Streamlit cũ và xác minh điều hướng bằng Chromium DevTools ở viewport điện thoại `390x844`.

Phát hiện và sửa:

- Route multipage thực tế của Streamlit 1.61 là `/Phan_tich_anh`, `/Lich_su`, `/Ho_so`; các route có tiền tố số gây `Page not found`. Bottom navigation đã chuyển sang route thực tế.
- Selector thực tế để ẩn nút sidebar là `stExpandSidebarButton`/`stSidebarCollapseButton`; mobile hiện ẩn cả header/sidebar thay vì chỉ thu gọn.
- Selector container cũ `.main .block-container` không còn khớp Streamlit 1.61. Đã chuyển sang `stMainBlockContainer`, giúp padding mobile thực sự có hiệu lực.
- Các horizontal block được bật `flex-wrap`; viewport `390px` xác nhận Hồ sơ dùng cột chính `358px` và các chỉ số con khoảng `157px`.
- Bottom navigation dùng HTML route trực tiếp thay vì `st.page_link`, tránh phụ thuộc multipage registry và DOM widget nội bộ.
- Cleanup ngrok bắt `PyngrokNgrokError` khi local ngrok API đã đóng trước; `Ctrl+C` không còn in traceback `ConnectionRefusedError`.

Bằng chứng browser: viewport `390x844` xác nhận sidebar `display:none`, bottom nav `position:fixed`, cạnh đáy tại `844px`, active state và route đúng trên Trang chủ, Phân tích và Hồ sơ.

### 2026-08-13 - Thay legacy multipage bằng router ẩn

**Mục tiêu:** loại bỏ triệt để sidebar tự sinh với tên file thô và tránh full-page reload khi chuyển mục.

Thay đổi kiến trúc:

- `app.py` là router duy nhất qua `st.navigation(position="hidden")`; Streamlit không còn dùng menu tự sinh từ thư mục `pages/`.
- Các `st.Page` có tên và route sạch: Trang chủ `/`, Phân tích `/phan-tich`, Lịch sử `/lich-su`, Hồ sơ `/ho-so`. Đánh giá mô hình vẫn truy cập được qua route ẩn `/danh-gia` nhưng không chiếm chỗ ở navigation người dùng.
- Thanh điều hướng dùng `st.page_link` với các `Page` đã đăng ký, không còn HTML `<a>` tải lại document.
- `set_page_config`, CSS và shared state chỉ được khởi tạo ở entrypoint; page con chỉ render nội dung, giảm code lặp và tránh cấu hình khác nhau giữa các trang.

Bằng chứng browser ở viewport `390x844`:

- Không còn `stSidebarNav` trong DOM.
- Navigation chỉ có `Trang chủ`, `Phân tích`, `Lịch sử`, `Hồ sơ`.
- Click Phân tích đổi route từ `/` sang `/phan-tich`, render đúng tiêu đề và giữ marker JavaScript trong `window` (`sameDocument=true`), xác nhận không full-page reload.

### 2026-08-13 - Tách Landing và không gian người dùng

**Mục tiêu:** không coi Landing công khai là trang chủ của người dùng và không ép navigation riêng cho mobile.

Thay đổi sản phẩm:

- Landing chỉ giới thiệu giá trị sản phẩm, có hai CTA rõ ràng: thiết lập hồ sơ hoặc mở không gian cá nhân.
- Thêm `Hôm nay` làm user home: hiển thị calo đã ăn/còn lại/số bữa trong phiên và đưa CTA theo trạng thái thực tế: hoàn tất hồ sơ, phân tích bữa đầu tiên, hoặc thêm bữa ăn tiếp theo.
- App shell dùng duy nhất một navigation Streamlit đã đăng ký cho desktop và mobile. Desktop hiển thị brand `NutriVision` cùng các mục; mobile ẩn brand để giữ bốn mục thao tác đủ rộng ở đáy. Không còn hai navigation khác nhau hay HTML route tự quản.
- Nêu rõ ranh giới dữ liệu hiện tại và hướng mở rộng khóa cá nhân để khôi phục hồ sơ/lịch sử đa thiết bị; không giả lập đăng nhập khi chưa có backend/persistence.

Xác minh browser: mobile hiển thị Landing + CTA và navigation `Hôm nay`, `Phân tích`, `Lịch sử`, `Hồ sơ`; desktop hiển thị thêm brand. Cả hai không có `stSidebarNav`.

## 8. Công việc tiếp theo khi tiếp tục

### Phase C5 - Kiểm tra thủ công còn lại

- Khi có `NGROK_AUTHTOKEN`, mở HTTPS tunnel và kiểm tra navigation, upload/camera, bảng, tư vấn dài, biểu đồ và thao tác cảm ứng trên điện thoại thật.
- Chụp bằng chứng desktop/mobile và ghi input, expected, actual vào tài liệu này.

### Live OpenAI LLM

- Kiểm tra một ảnh/meal đại diện qua UI với `LLM_PROVIDER=openai` và `OPENAI_MODEL=gpt-4o-mini`; ghi latency, format và lỗi nếu có.
- Google Gemini/Gemma chỉ là phương án thay thế, không thuộc demo chính trừ khi có thay đổi quyết định.

### Phase E - Báo cáo và demo

- Đồng bộ báo cáo, README và dashboard theo 12 lớp, Kaggle và Baseline B.
- Chuẩn bị demo 5 phút và kịch bản dự phòng khi LLM/mạng lỗi.
- Thực hiện clean-clone/production smoke test sau khi có cơ chế phân phối checkpoint.
