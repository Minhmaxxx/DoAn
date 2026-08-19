# NutriVision Progress Record

**Cập nhật:** 2026-08-19<br>
**Trạng thái hiện tại:** Phase A, B và D hoàn tất; C1-C4 pass, OpenAI live smoke đã pass; UI desktop/mobile và PWA đã pass trên Edge DevTools, C5 còn kiểm tra camera/touch trên điện thoại thật. Lưu trữ đa thiết bị (`STORAGE_PLAN.md`): Giai đoạn 0, A và C xong 2026-08-19 — đồng bộ Supabase đã nối vào app dưới dạng **opt-in** ("Bật đồng bộ"), chế độ khách vẫn là mặc định; 6 lỗi phát hiện nhờ chạy thật đã vá. Liên kết Google đã xác minh trên trình duyệt thật là giữ nguyên `user_id`; thử tiếp trên bản deploy thì lộ ra thiếu hẳn đường **đăng nhập** ở thiết bị thứ hai, đã bổ sung `sign_in_with_oauth()`. Còn nợ: kiểm thử thật vế thiết bị thứ hai (bài 4), bài 2/3/5/13, và Giai đoạn D (hardening XSS, export JSON).

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

### 2026-08-18 - Hardening bản deploy và dọn workspace an toàn

**Mục tiêu:** ổn định bản demo Streamlit Cloud trước khi tiếp tục chỉnh giao diện; giảm rủi ro RAM khi chụp ảnh, làm đúng ngày giờ Việt Nam, buộc xác nhận hồ sơ/detection, tránh gọi LLM hoặc lưu history không kiểm soát, và tự động hóa release gate.

Quyết định phạm vi:

- Chưa tích hợp Supabase Auth; hồ sơ và history tiếp tục ở session cho tới phase lưu trữ riêng.
- Chưa thêm quota/hard spending trong app vì bản demo hiện giới hạn người xem; chủ API key vẫn cần đặt giới hạn chi phí tại OpenAI nếu mở quyền truy cập rộng hơn.
- Giữ tuổi nhập từ 10 đến 100 theo yêu cầu hỗ trợ học sinh; không chặn người dưới 18 tuổi ở vòng này.
- Bỏ mục tiêu `Giảm cân nhanh`; session cũ có giá trị này được chuyển về `Giảm cân`.
- Giữ nguyên toàn bộ `KetQuaTrain/`, dataset, notebook, báo cáo và bằng chứng benchmark.

Thay đổi runtime:

- Tách giới hạn ảnh nguồn và ảnh làm việc. Ảnh nguồn trên 25 triệu pixel hoặc cạnh trên 6000 px bị từ chối trước khi decode đầy đủ; ảnh hợp lệ được resize xuống tối đa 4 triệu pixel và 2048 px mỗi cạnh trước khi hash/inference.
- Chụp nhiều ảnh tuần tự không cộng dồn ảnh trong history vì history chỉ lưu số liệu; session chỉ giữ ảnh phân tích hiện tại. Việc giảm ảnh làm việc giới hạn mỗi RGB buffer khoảng 12 MB thay vì tối đa khoảng 75 MB như cấu hình 25 MP cũ.
- Bắt `DecompressionBombWarning` như lỗi đầu vào để tránh ảnh nén bất thường gây áp lực bộ nhớ.
- Thêm múi giờ `Asia/Ho_Chi_Minh`; timestamp history có offset `+07:00`, trang Hôm nay và thống kê 7 ngày cùng dùng giờ Việt Nam.
- Thêm `profile_completed`; trang Phân tích yêu cầu người dùng đã bấm lưu hồ sơ, không dùng thầm dữ liệu mặc định để cá nhân hóa.
- Form hồ sơ chỉ ghi session khi submit, không còn thay đổi profile đã lưu trong các rerun chưa xác nhận.
- Mỗi detection có checkbox loại khỏi bữa ăn và selectbox sửa về một trong 12 lớp. Tổng dinh dưỡng/LLM chỉ dùng món đã xác nhận.
- OpenAI client dùng timeout 45 giây và tối đa một retry.
- Mỗi phiên phân tích giữ tập meal signature đã lưu; click lặp cùng một cấu hình không append history lần nữa.
- Thêm `.github/workflows/tests.yml`: Python 3.11, dependency cache và `python -m pytest -q` trên push/PR `main`.

Dọn workspace và Git:

- Xóa `CLEANUP_CANDIDATES.md` đã hết vai trò sau khi chốt cleanup.
- Xóa `models/weights/.gitkeep` và `data/sample_images/.gitkeep`; hai file rỗng không còn cần cho runtime/training.
- Không có file nào dưới `datasets/` hoặc `KetQuaTrain/` được Git track. `.gitignore` tiếp tục chặn toàn bộ `datasets/`, `*.zip` và `KetQuaTrain/`.
- Cache Python/pytest được dọn sau release test; `.venv311` được giữ vì vẫn là môi trường local đã xác minh.

Xác minh:

- `python -m pytest -q tests/test_images.py` trả `10 passed`.
- `python -m pytest -q tests/test_history.py tests/test_pages.py` trả `20 passed`.
- `python -m pytest -q tests/test_history.py tests/test_llm.py tests/test_pages.py` trả `31 passed`.
- Release gate cuối `python -m pytest -q` trả `76 passed, 1 skipped`; test skip duy nhất vẫn là live LLM.
- `git diff --check` pass; dataset và `KetQuaTrain/` không xuất hiện trong `git ls-files`.

### 2026-08-18 - Xây lại UI responsive và hỗ trợ cài lên màn hình chính

**Mục tiêu:** thay toàn bộ giao diện cũ bằng một hệ thống thiết kế riêng cho desktop/mobile, giữ nguyên logic dinh dưỡng đã harden và cho phép thêm NutriVision lên màn hình chính như một PWA.

Thay đổi sản phẩm:

- Pin `streamlit==1.61.1` để cố định DOM/API đã dùng trong giao diện và test.
- Viết lại `assets/style.css` theo visual language giấy ấm, xanh đậm, xanh chanh và cam; desktop dùng navigation rail cố định, mobile dùng header gọn cùng bottom navigation có safe-area.
- Tạo `utils/ui.py` cho page header, section header, stat grid và empty state dùng chung; xây lại Landing, Hôm nay, Phân tích, Lịch sử, Hồ sơ và dashboard benchmark trên cùng design system.
- `utils/navigation.py` dùng một registry `st.Page` cho cả desktop/mobile; active state chỉ do CSS thể hiện, không vô hiệu hóa link hiện tại.
- Thêm `utils/pwa.py`, manifest, service worker và icon 192/512/Apple Touch dưới `static/`; bật `server.enableStaticServing` và cung cấp nút cài cùng hướng dẫn fallback Android/iOS.
- Chuyển metadata tin cậy sang `st.html(..., unsafe_allow_javascript=True)` và install control sang `st.iframe`; không còn dùng `st.components.v1.html` đã hết vòng đời trong Streamlit 1.61.
- CSS được nạp bằng `st.html(Path)` để không tạo spacer zero-height trước mobile header. Selector navigation được khớp với DOM thực tế của Streamlit, khóa bốn wrapper ở một hàng và không tạo horizontal overflow.
- Tablet và laptop hẹp chuyển sang layout một cột ở `1200px`; desktop rail nén bốn link thành vùng bấm độc lập và ẩn note phụ khi chiều cao dưới `681px`, tránh che navigation.
- Bổ sung `:focus-visible`, `aria-current`, contrast chữ nhỏ đạt chuẩn, nhãn riêng cho từng detection và thông báo sau khi lưu hồ sơ; iframe cài đặt tiếp tục nằm trong thứ tự tab bàn phím.
- Service worker chỉ xóa cache có prefix của NutriVision, retry sau lỗi đăng ký và khai báo scope tĩnh tường minh; nút cài nhận biết standalone/appinstalled và hướng dẫn cả iPadOS desktop user agent.
- Đồng bộ palette Plotly với giao diện mới; giữ nội dung tiếng Việt và toàn bộ contract nhận diện/dinh dưỡng hiện có.

Bằng chứng browser:

- Edge DevTools kiểm tra các route `/`, `/hom-nay`, `/phan-tich`, `/lich-su`, `/ho-so` ở `1440x1000` và device emulation thật `390x844`.
- Cả năm route có `stException=0`, `documentElement.scrollWidth` bằng đúng viewport và mobile navigation luôn là `row nowrap` với bốn mục cùng hàng.
- Kiểm tra bổ sung `1366x768`, `1366x600`, `1201x700`, `1200x700` và `1024x600`: link rail không chồng/che nhau, note ẩn ở màn hình thấp, metric không bị cắt tại ranh giới desktop và tablet dùng form một cột.
- Dùng mouse event thật để lưu hồ sơ, sau đó chuyển trang bằng `st.page_link` trong cùng document; trang Phân tích mở đúng tab tải ảnh/camera và không còn cảnh báo thiếu hồ sơ.
- Manifest, service worker và hai icon đều trả HTTP `200`; worker ở trạng thái `activated`. Chrome DevTools trả `installabilityErrors=[]` và không có manifest error.
- Service worker hiện chỉ cache tài nguyên PWA tĩnh; không tuyên bố inference hoặc dữ liệu phiên hoạt động offline.

Xác minh tự động:

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `.venv311\\Scripts\\python.exe -m pytest -q` | `77 passed, 1 skipped` trong `9.31s`; skip duy nhất là live LLM |
| `.venv311\\Scripts\\python.exe test_imports.py` | Pass config, nutrition, fallback, chart và checksum Baseline B |
| `.venv311\\Scripts\\python.exe -m pip check` | `No broken requirements found` |
| `.venv311\\Scripts\\python.exe -m compileall -q app.py pages utils tests` | Pass |
| `git diff --check` | Pass; chỉ có cảnh báo line-ending LF/CRLF của Git trên Windows |

Giới hạn còn lại: cần mở bản HTTPS production trên điện thoại thật để xác nhận camera permission, bàn phím, touch target, safe-area iPhone/Android và thao tác cài từ Safari/Chrome thực tế.

### 2026-08-18 - Kế hoạch lưu trữ đa thiết bị: chốt kiến trúc và Giai đoạn B

**Mục tiêu:** giải quyết việc hồ sơ và lịch sử chỉ sống trong `st.session_state` (mất khi đổi thiết bị hoặc hết phiên), mà không buộc người dùng đăng ký/đăng nhập truyền thống.

Quyết định kiến trúc (`STORAGE_PLAN.md`, đã qua 3 bản):

- Bản 1 chọn Supabase Postgres + RLS nhưng bỏ sót việc giữ phiên trên Streamlit.
- Bản 2 thêm `st.login()` (Google OIDC) để giữ phiên qua cookie, nhưng việc gộp danh tính `st.login()` với user Supabase cần một bước di trú dữ liệu.
- Bản 3 (chốt): bỏ `st.login()`, để Supabase quản lý danh tính từ đầu. Tài khoản **ẩn danh được tạo lười** (`sign_in_anonymously()`, chỉ gọi ngay trước lần lưu đầu tiên) rồi **nâng cấp bằng Google** qua `link_identity()` khi cần đa thiết bị — cách này giữ nguyên `auth.users.id` nên không cần di trú và `storage_schema.sql` không đổi dòng nào. Đã xác minh trong `site-packages` rằng `st.context.cookies` chỉ đọc, nên refresh token phải ghi bằng JS vào cookie qua `st.html(..., unsafe_allow_javascript=True)`, cùng pattern `utils/pwa.py` đã dùng.
- Loại phương án "mỗi user một key bí mật" (ma sát khôi phục cao hơn, mất key là mất sạch) và email/mật khẩu (SMTP free tier dễ fail đúng lúc demo).
- Chi phí xác nhận là **$0**: OAuth client trên Google Cloud Console không cần bật billing; Supabase free tier không cần thẻ. Không dùng AWS credit cho phần này vì phải viết lại Cognito/RDS và bỏ RLS đã thiết kế xong, đổi lấy quá ít.

Giai đoạn B — module code, không cần Supabase project hay mạng:

- `utils/auth.py`: `ensure_account()`, `restore_session()`, `start_google_link()`, `complete_oauth_callback()`, `logout()`. Mọi hàm chạm Supabase nhận `client` qua tham số (cùng pattern `NutriLLM._get_google()`/`_get_openai()`), nên test được bằng fake client, không cần package `supabase` cài sẵn.
- `utils/repository.py`: `Repository` protocol (`@runtime_checkable`), `SessionRepository` (khách, giữ nguyên hành vi cũ trong `st.session_state`) và `SupabaseRepository` (đã lưu). `get_repository()` chọn theo `utils.auth.current_user_id()`.
- `utils/history.py`: thêm `meal_uuid(user_id, signature)` (uuid5 xác định, chống ghi trùng khi retry) và `record_from_row()` (map một dòng `meals` về đúng shape record trong session, đi qua `as_vietnam_time()` để tránh lệch múi giờ).
- 26 test mới (`tests/test_auth.py`, `tests/test_repository.py`) + 5 test bổ sung (`tests/test_history.py`), toàn bộ offline — `restore_session()` được test bằng cách tiêm một `st` giả (`monkeypatch.setattr(auth, "st", fake)`) vì `st.context.cookies` không có cách nào ghi giá trị test từ bên ngoài.

Xác minh:

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `.venv311\Scripts\python.exe -m pytest -q` | `107 passed, 1 skipped`; skip duy nhất là live LLM |
| `.venv311\Scripts\python.exe -m pytest -q tests/test_auth.py tests/test_repository.py tests/test_history.py` | `40 passed` |
| `.venv311\Scripts\python.exe test_imports.py` | Pass config, nutrition, fallback, chart và checksum Baseline B |

Quyết định phạm vi: **chưa** nối vào `app.py`/`pages/*.py` (đó là Giai đoạn C). Tên tham số của `client.link_identity()` và `client.exchange_code_for_session()` trong `utils/auth.py` viết theo hiểu biết về API `supabase-py`/GoTrue nhưng **chưa xác minh với package thật** — package `supabase` chưa có trong `requirements.txt`/`requirements-dev.txt` (cố ý, thuộc Giai đoạn A). Giả định quan trọng nhất chưa kiểm chứng: `link_identity()` giữ nguyên `auth.users.id` sau khi gắn Google — đây là việc của Giai đoạn 0 (mục 11 trong `STORAGE_PLAN.md`).

### 2026-08-19 - Lưu trữ đa thiết bị: Giai đoạn A (người dùng) và Giai đoạn 0 (spike thật)

**Mục tiêu:** hoàn tất hạ tầng Supabase/Google thật (Giai đoạn A), rồi chạy Giai đoạn 0 để xác minh mọi giả định API trong `utils/auth.py`/`utils/repository.py` trước khi nối vào trang (Giai đoạn C).

Giai đoạn A — người dùng thực hiện, đã xác nhận xong: tạo Supabase project (`ntyyhenrjgvvjzhyxrey`), chạy `storage_schema.sql`, bật Anonymous sign-in, tạo Google OAuth Client (Authorized JavaScript origins: `localhost:8501` + domain production; Authorized redirect URI: callback URL do Supabase cấp, không phải domain app), dán Client ID/Secret vào Supabase → Authentication → Providers → Google, đặt Site URL production. `.streamlit/secrets.toml.example` được thêm làm mẫu; `.streamlit/secrets.toml` thật đã tạo trên máy dev (xác nhận nằm ngoài git qua `git check-ignore`).

Giai đoạn 0 — cài `supabase==2.31.0` vào `.venv311`, chạy spike thật (không mock) chống lại project trên. Giả định quan trọng nhất được xác nhận đúng: `link_identity()` giữ nguyên `auth.users.id`. Nhưng phát hiện **4 chỗ sai** trong code đã viết ở Giai đoạn B, chỉ lộ ra khi chạy thật (unit test dùng fake client nên không bắt được):

1. `start_google_link()` gọi `link_identity({"provider": "google", "redirect_to": ...})` — sai vị trí, `redirect_to` phải lồng trong `options`; đặt sai không báo lỗi, chỉ âm thầm bị bỏ qua.
2. `get_client()` dựng `Client` mới mỗi lần gọi — làm mọi truy vấn `SupabaseRepository` sau khi đăng nhập vẫn chạy bằng anon key (Postgrest chỉ nhận JWT qua listener sự kiện sign-in/refresh gắn trên chính object `Client`), nghĩa là RLS sẽ chặn hết một khi nối vào trang thật. Đã sửa: cache `Client` trong `st.session_state["_supabase_client"]`.
3. PKCE `code_verifier` do `link_identity()` tự sinh chỉ lưu trong bộ nhớ của `Client` — không sống sót qua việc redirect sang Google rồi quay lại (một lượt tải trang mới, `st.session_state` không giữ được). Đã thêm `_CodeVerifierCookieStorage` (cookie riêng, TTL 10 phút) gắn qua `SyncClientOptions(persist_session=False, storage=...)`.
4. `SupabaseRepository.load_profile()` giả định `maybe_single().execute()` luôn trả response object có `.data` — thực tế trả `None` thẳng khi không có dòng nào. Đã sửa thành `result.data if result else None`.

Xác minh bằng ghi/đọc/xóa thật trên project (không chỉ đọc mã nguồn SDK): tạo tài khoản ẩn danh → `save_profile`/`load_profile` round-trip đúng → `save_meal`/`load_meals` round-trip đúng (kể cả quy đổi giờ Việt Nam) → `delete_all_meals` → xóa profile → `logout()`. Dữ liệu test đã dọn sạch; chỉ còn một dòng `auth.users` ẩn danh mồ côi (giống một khách vãng lai thật, không hại gì).

| Lệnh/kiểm tra | Kết quả |
|---|---|
| Spike thật chống Supabase project (3 script tạm, đã xóa) | `sign_in_anonymously`, `refresh_session`, `link_identity`, `exchange_code_for_session`, `sign_out` đúng shape sau khi sửa 4 điểm trên; ghi/đọc/xóa qua RLS thành công |
| `.venv311\Scripts\python.exe -m pytest -q` | `111 passed, 1 skipped` |
| `.venv311\Scripts\python.exe -m pytest -q tests/test_auth.py tests/test_repository.py` | `30 passed` |
| `.venv311\Scripts\python.exe test_imports.py` | Pass |

Thay đổi thêm: `requirements.txt` thêm `supabase>=2.0.0,<3.0.0` (Giai đoạn A liệt kê việc này; thêm sớm để môi trường production khớp với những gì đã xác minh, dù Giai đoạn C — nối vào trang — chưa làm). `STORAGE_PLAN.md` mục 6/11 cập nhật theo tên hàm thật và 4 phát hiện trên.

Quyết định phạm vi: vẫn **chưa** nối vào `app.py`/`pages/*.py`. Còn thiếu trong Giai đoạn A: cron GitHub Actions chống Supabase free-tier pause sau 7 ngày.

### 2026-08-19 - Lưu trữ đa thiết bị: cron chống pause và Giai đoạn C (nối vào app)

**Mục tiêu:** hoàn tất phần còn thiếu của Giai đoạn A (cron chống pause) và thực hiện Giai đoạn C — nối `utils/auth.py` + `utils/repository.py` vào app thật.

Cron chống pause (`.github/workflows/supabase-keepalive.yml`): chạy thứ Hai và thứ Năm thay vì hàng tuần, vì ngưỡng pause của Supabase là 7 ngày nên cron 7 ngày không có biên an toàn — một lần chạy trễ là project ngủ. Gọi một REST request nhẹ bằng anon key; RLS khiến nó trả `[]`, đó là kết quả mong muốn (chứng minh project còn sống mà không đọc dữ liệu ai). Dùng GitHub secrets `SUPABASE_URL`/`SUPABASE_PUBLISHABLE_KEY` thay vì ghi thẳng vào file: repo có thể public, và Anonymous sign-in đang bật nên anon key lộ ra cho phép bot tạo user rác. Nếu thiếu secrets thì workflow cảnh báo và thoát 0, không spam email lỗi hàng tuần. Đã xác minh thật: `curl` đúng lệnh đó trả `HTTP 200` và `[]`.

Giai đoạn C — thay đổi thiết kế có chủ ý so với `STORAGE_PLAN.md` mục 6: **đồng bộ là opt-in bằng nút "Bật đồng bộ"**, không tự tạo tài khoản khi lưu hồ sơ lần đầu. Lý do: (1) không nên âm thầm đẩy hồ sơ sức khỏe lên máy chủ khi người dùng chỉ bấm "Lưu thay đổi"; (2) giữ chế độ khách làm mặc định thật, nên release gate offline theo cấu trúc — máy dev đã có `secrets.toml` thật, nếu tự bật thì mỗi lần chạy AppTest trang hồ sơ sẽ tạo một tài khoản ẩn danh sống. Tính "tạo lười" của kế hoạch không đổi: khách không bật thì `auth.users` không có dòng nào.

Các file đã nối:

- `app.py`: `bootstrap_session()` chạy trước mọi trang (khôi phục cookie hoặc hoàn tất `?code=` sau OAuth), rồi `hydrate_session()` nạp hồ sơ + tối đa 50 bữa gần nhất. Caption landing đổi theo ba trạng thái.
- `pages/3_Ho_so.py`: lưu hồ sơ qua `get_repository()`; mục "03 · Đồng bộ và thiết bị" mới với nút Bật đồng bộ / Liên kết Google / Đăng xuất; nhãn header đổi theo trạng thái (`LƯU TRONG PHIÊN` → `LƯU TRÊN MÁY CHỦ` → `ĐÃ ĐỒNG BỘ`). Mục LLM và Cài đặt dịch số thành 04/05.
- `pages/1_Phan_tich_anh.py`: `_save_to_history()` ghi lên máy chủ trước, chỉ mirror vào session khi server đã nhận; lỗi mạng hiện `st.error` thay vì "Đã lưu" giả.
- `pages/2_Lich_su.py`: "Xóa tất cả" qua repository; nhãn tiêu đề/thống kê đổi theo trạng thái.
- `utils/navigation.py`, `utils/state.py`: chỉ báo trạng thái đồng bộ trong app shell; khai báo key `auth_user`.
- `utils/repository.py`: thêm `save_record()`, `enable_sync()` (đẩy hồ sơ + lịch sử khách lên rồi đọc lại) và `hydrate_session()`.

**Hai lỗi thật phát hiện khi chạy thật, unit test dùng fake không bắt được:**

1. `record_signature()` ban đầu khóa theo `timestamp`. Đo thực tế trên Windows: `datetime.now()` phân giải ~16ms nên **năm bản ghi tạo liên tiếp có timestamp giống hệt nhau** — hai bữa ăn khác nhau bị đè thành một dòng khi di trú lên cloud (mất dữ liệu thật). Đã đổi sang hash SHA-256 nội dung bản ghi; thêm test hồi quy.
2. Dưới AppTest, `st.context.cookies.get()` trả **`MagicMock`** — luôn truthy. `bootstrap_session()` vì thế tưởng có refresh token, dựng Supabase client và (trên máy dev có secrets) sẽ gọi mạng refresh bằng mock object, phá cam kết release gate không chạm mạng. Đã sửa: chỉ chấp nhận cookie là `str` không rỗng; `sync_available()` cũng đổi sang đọc cấu hình thay vì dựng client.

Xác minh:

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `.venv311\Scripts\python.exe -m pytest -q` | `134 passed, 1 skipped` |
| `.venv311\Scripts\python.exe test_imports.py` | Pass |
| Spike thật: khách có hồ sơ + 2 bữa → `enable_sync()` → Supabase | Hồ sơ và cả 2 bữa lên đúng, chạy lại `enable_sync()` vẫn là 2 bữa (không nhân đôi), xóa sạch, `logout()` về `guest` |
| `curl` keepalive chống project của mình | `HTTP 200`, body `[]` |
| AppTest cả 6 trang ở chế độ khách | Không exception, **không trang nào dựng Supabase client** (đã chốt bằng test trong `tests/test_pages.py`) |

Quyết định phạm vi: Giai đoạn D (rà `unsafe_allow_html`, test XSS, export JSON) chưa làm.

### 2026-08-19 - Kiểm thử liên kết Google trên trình duyệt thật (bài 4, ma trận mục 12)

**Mục tiêu:** chạy thật luồng khách → ẩn danh → liên kết Google trên trình duyệt, xác minh giả định cốt lõi rằng `link_identity()` giữ nguyên `user_id`.

Chạy app local (`streamlit run app.py`, port 8501) với `site_url = "http://localhost:8501"` trong `.streamlit/secrets.toml`.

Phát hiện thêm **một prerequisite Supabase mà kế hoạch chưa bắt được**: `link_identity()` trả lỗi `Manual linking is disabled`. Phải bật **Allow manual linking** ở Authentication → Sign In / Providers (khu toggle phía trên danh sách provider, cạnh Anonymous sign-ins); mặc định Supabase tắt. Không bài test tự động nào lộ ra được vì luồng này cần một phiên đăng nhập thật. Đã ghi vào `STORAGE_PLAN.md` mục 8. Cũng cần thêm `http://localhost:8501` vào Redirect URLs của Supabase để test local (không phải thêm vào Google Console — Google luôn redirect về callback của Supabase, không về app).

**Kết quả: giả định cốt lõi được xác nhận.** Truy vấn `profiles` join `auth.users` sau khi liên kết:

| user_id | name | email | is_anonymous |
|---|---|---|---|
| `6deef3b1-…14d750` | Lăng Nhật Minh | (email Google) | false |

Một dòng duy nhất mang cả hồ sơ lẫn danh tính Google: tài khoản ẩn danh được nâng cấp tại chỗ, `user_id` không đổi, hồ sơ đã lưu lúc còn ẩn danh vẫn thuộc về tài khoản đó. Không cần bước di trú, phương án dự phòng RPC `security definer` ở mục 13 `STORAGE_PLAN.md` không phải dùng đến. Lưu ý khi đọc `auth.identities`: user ẩn danh **không có** dòng identity nào, nên sau khi gắn Google `providers` chỉ hiện `["google"]` — đó là bình thường, không phải dấu hiệu tài khoản mới.

Ghi nhận sai sót trong quá trình: các script spike có đoạn dọn dữ liệu ở cuối, nhưng hai lần chạy crash giữa chừng (lỗi encoding console và assert số bữa ăn) nên không chạy tới đoạn dọn, để lại hai dòng `profiles` rác ("Spike Test", "Khách Spike") cùng 8 tài khoản ẩn danh mồ côi — đã phát hiện khi kiểm tra bảng và xóa bằng `delete from auth.users where is_anonymous = true` (cascade sang `profiles`/`meals`). Bài học: script kiểm thử chạm dữ liệu thật cần dọn trong `try/finally`, không đặt ở cuối luồng thành công.

Còn nợ trong ma trận mục 12: bài 2 (F5 giữ đăng nhập), 3 (mở lại từ icon PWA), 5 (redeploy không mất phiên), 13 (PWA standalone trên iPhone).

### 2026-08-19 - Lỗ hổng chức năng: thiếu đường đăng nhập trên thiết bị thứ hai

**Triệu chứng:** sau khi deploy, thử trên bản production bằng đúng tài khoản Google đã liên kết ở local thì thấy app trống trơn, tưởng mất hết dữ liệu.

**Nguyên nhân:** Giai đoạn C chỉ cài `start_google_link()` (dùng `link_identity()`), tức chỉ gắn Google vào tài khoản mà trình duyệt **đang** đăng nhập. Production là domain khác nên không có cookie → người dùng là khách. Bấm "Bật đồng bộ" ở đó tạo một tài khoản ẩn danh **mới, rỗng**, và liên kết Google sau đó chỉ có thể thất bại vì identity đó đã thuộc tài khoản của máy trước. Không có đường nào để *đăng nhập* vào tài khoản đã tồn tại — đúng chức năng mà cả tính năng sinh ra để phục vụ. Dữ liệu cũ không mất, vẫn nằm ở tài khoản ban đầu.

**Sửa:** thêm `start_google_signin()` dùng `sign_in_with_oauth()` — không cần phiên sẵn có và trả về đúng tài khoản mà identity Google đang thuộc về. Mục đồng bộ ở trạng thái khách giờ trình bày hai lựa chọn tách bạch: "Bật đồng bộ" (tài khoản mới) và "Đăng nhập bằng Google" (lấy lại tài khoản cũ). Trạng thái ẩn danh cảnh báo rằng liên kết lần hai sẽ lỗi và chỉ sang đăng xuất + đăng nhập.

URL OAuth chỉ được tạo sau khi bấm nút, không tạo lúc render, nên khách vẫn không dựng Supabase client và bài test chốt trong `tests/test_pages.py` vẫn đúng. Đã xác minh trên project thật: URL trỏ `/auth/v1/authorize`, có PKCE `s256`, nên cookie `code_verifier` sẵn có phủ luôn luồng này.

Bài học rút ra: bài 4 của ma trận mục 12 được đánh dấu pass quá sớm. Nó đòi "ẩn danh trên máy A, liên kết Google, **đăng nhập trên máy B**", nhưng phần kiểm thử chỉ chạy hết vế đầu trên cùng một trình duyệt. Vế "máy B" mới là vế phát hiện ra lỗ hổng. Bài 4 giờ tính là **chưa pass** cho tới khi thử thật trên thiết bị/trình duyệt thứ hai.

## 8. Công việc tiếp theo khi tiếp tục

### Phase C5 - Kiểm tra thủ công còn lại

- Khi có `NGROK_AUTHTOKEN`, mở HTTPS tunnel và kiểm tra navigation, upload/camera, bảng, tư vấn dài, biểu đồ và thao tác cảm ứng trên điện thoại thật.
- Chụp bằng chứng desktop/mobile và ghi input, expected, actual vào tài liệu này.

### Live OpenAI LLM

- Kiểm tra một ảnh/meal đại diện qua UI với `LLM_PROVIDER=openai` và `OPENAI_MODEL=gpt-4o-mini`; ghi latency, format và lỗi nếu có.
- Google Gemini/Gemma chỉ là phương án thay thế, không thuộc demo chính trừ khi có thay đổi quyết định.

### Lưu trữ đa thiết bị (STORAGE_PLAN.md)

- Giai đoạn 0, A và C **đã xong** (2026-08-19) — xem hai mục nhật ký cùng ngày ở mục 7.
- **Việc người dùng phải làm để cron chạy được:** thêm hai GitHub repo secrets ở Settings → Secrets and variables → Actions: `SUPABASE_URL` và `SUPABASE_PUBLISHABLE_KEY`. Chưa thêm thì workflow chỉ cảnh báo rồi bỏ qua.
- **Kiểm thử thủ công còn nợ:** bài 4 mới xong **vế đầu** (liên kết Google giữ nguyên `user_id`, xác minh bằng SQL). Vế quyết định — đăng nhập lại trên **thiết bị thứ hai** và thấy đủ dữ liệu cũ — vẫn chưa chạy; chính vế này đã lộ ra lỗ hổng thiếu `sign_in_with_oauth()`. Còn bài 2 (F5 giữ đăng nhập), 3 (mở lại từ icon PWA), 5 (redeploy không mất phiên) và 13 (PWA standalone trên iPhone).
- Bài 2 là bài đáng lo nhất còn lại: nó kiểm chứng cookie refresh-token ghi bằng JS có thực sự sống sót qua reload hay không — tức toàn bộ lý do bản 3 của kế hoạch bỏ `st.login()`.
- Giai đoạn D: rà 23 chỗ `unsafe_allow_html=True` còn lại (đã xác nhận `pages/3_Ho_so.py`→`utils/ui.py` escape đúng), thêm test XSS chốt hành vi, export JSON dự phòng.
- `utils/history.append_meal_once()` giờ không còn trang nào gọi (đã thay bằng `SessionRepository.save_meal`), chỉ còn test dùng — cân nhắc bỏ khi dọn dẹp.

### Phase E - Báo cáo và demo

- Đồng bộ báo cáo, README và dashboard theo 12 lớp, Kaggle và Baseline B.
- Chuẩn bị demo 5 phút và kịch bản dự phòng khi LLM/mạng lỗi.
- Thực hiện clean-clone/production smoke test sau khi có cơ chế phân phối checkpoint.
