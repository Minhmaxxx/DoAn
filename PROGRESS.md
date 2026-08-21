# NutriVision Progress Record

**Cập nhật:** 2026-08-20<br>
**Trạng thái hiện tại:** Phase A, B và D hoàn tất; C1-C4 pass, OpenAI live smoke đã pass; UI desktop/mobile và PWA đã pass trên Edge DevTools, C5 còn kiểm tra camera/touch trên điện thoại thật. **Lưu trữ đa thiết bị (`STORAGE_PLAN.md`) đã hoàn tất về chức năng và xác minh trên production ngày 2026-08-20:** đồng bộ Supabase dạng opt-in ("Bật đồng bộ"), chế độ khách vẫn là mặc định, liên kết Google giữ nguyên `user_id`, bài 2 (F5 giữ đăng nhập) và bài 4 (đăng nhập ở thiết bị thứ hai, sửa dữ liệu ở máy này thấy ngay ở máy kia) đều PASS trên hai trình duyệt thật. Tổng cộng 12 lỗi tích hợp đã vá, sáu lỗi cuối chỉ lộ ra trên đúng môi trường triển khai. Còn nợ: bài 3/5/13 (biến thể PWA và redeploy), hai GitHub secrets cho cron chống pause, và Giai đoạn D (hardening XSS, export JSON).

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

### 2026-08-19 - Chặn lớn: Streamlit Community Cloud không chuyển cookie tới app

**Triệu chứng:** trên bản deploy, F5 làm mất sạch hồ sơ vừa lưu; đăng nhập Google trả về lỗi `AuthApiError: invalid request: both auth code and code verifier should be non-empty`.

**Đo đạc:** thêm hàm `cookie_diagnostics()` và khung "Chẩn đoán đồng bộ" ở trang Hồ sơ. Kết quả trên production, cả trước lẫn sau F5:

```
Số cookie máy chủ nhận được: 0
Thấy cookie phiên (nv_refresh_token): false
Cookie PKCE: không có
```

Trong khi đó DevTools của trình duyệt **có** cookie `nv_refresh_token`. Tức là JavaScript ghi cookie thành công, nhưng `st.context.cookies` phía Python luôn rỗng.

**Kết luận:** đây là giới hạn đã biết của Streamlit Community Cloud — `st.context.cookies` hoạt động ở local nhưng trả về dict rỗng khi deploy lên Cloud (nhiều báo cáo trên diễn đàn Streamlit). Không phải lỗi lập trình, mà là giả định nền tảng sai.

**Hệ quả:** toàn bộ cơ chế giữ phiên của bản 3 `STORAGE_PLAN.md` dựa trên cookie đọc qua `st.context.cookies` nên **không dùng được trên production**. Cả refresh token lẫn `code_verifier` PKCE đều đi qua đường này. Đăng nhập Google thất bại chỉ là triệu chứng của cùng một nguyên nhân.

**Sai lầm quy trình cần ghi nhận cho báo cáo:** mục 2 của `STORAGE_PLAN.md` xác định "giữ phiên" là *vấn đề cốt lõi* của cả kế hoạch, và ma trận kiểm thử mục 12 đặt bài 2 (F5 giữ đăng nhập) ngay gần đầu. Nhưng Giai đoạn C được xây trọn vẹn trên giả định cookie hoạt động, còn bài 2 thì để lại làm sau cùng. Giả định rủi ro nhất phải được kiểm chứng trên **đúng môi trường triển khai** trước khi xây tiếp, không phải chỉ ở local — local chạy tốt chính là thứ đã che giấu vấn đề này.

Những phần **không** bị ảnh hưởng và giữ nguyên được: `storage_schema.sql`, RLS, `utils/repository.py`, luồng đồng bộ, `enable_sync()`, và chế độ khách (vẫn chạy bình thường trên production). Chỉ tầng vận chuyển token cần thay.

**Cách sửa đã chọn** (người dùng chốt phương án "đổi sang cookie component"): thêm `utils/cookies.py` bọc `extra-streamlit-components.CookieManager`. Component này đọc `document.cookie` trong trình duyệt rồi trả về qua **kênh component**, không đi qua HTTP header nên nền tảng không bóc được. `utils/auth.py` bỏ toàn bộ `st.html` ghi cookie và `st.context.cookies`, chuyển sang gọi module này; `app.py` render component đúng một lần mỗi vòng chạy, trước khi bất cứ chỗ nào đọc cookie.

Hai chi tiết bắt buộc đúng, đều đã cài và có test chốt:

1. Component chỉ trả cookie **sau một vòng rerun**. `cookies_ready()` phân biệt "chưa trả lời" với "không có cookie"; nếu coi hai cái là một thì app sẽ đăng xuất người dùng ở **mỗi lần tải trang**. `bootstrap_session()` không làm gì cho tới khi biết chắc.
2. Cookie đặt `SameSite=Lax`, không dùng `Strict` mặc định của component — lượt quay về từ Google là điều hướng cross-site, đúng lúc `Strict` bị trình duyệt giữ lại.

Đồng thời bỏ luôn lỗi mã hoá cũ: cơ chế JS ghi qua `encodeURIComponent` mà đọc lại không giải mã; component truyền giá trị nguyên vẹn nên vấn đề đó biến mất.

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `.venv311\Scripts\python.exe -m pytest -q` | `141 passed, 1 skipped` |
| AppTest 5 trang ở chế độ khách | Không exception, không trang nào dựng Supabase client |

Chưa xác minh trên production — cần deploy rồi chạy lại bài 2 (F5) và bài 4 (đăng nhập ở thiết bị khác).

### 2026-08-19 - Lỗ hổng chức năng: thiếu đường đăng nhập trên thiết bị thứ hai

**Triệu chứng:** sau khi deploy, thử trên bản production bằng đúng tài khoản Google đã liên kết ở local thì thấy app trống trơn, tưởng mất hết dữ liệu.

**Nguyên nhân:** Giai đoạn C chỉ cài `start_google_link()` (dùng `link_identity()`), tức chỉ gắn Google vào tài khoản mà trình duyệt **đang** đăng nhập. Production là domain khác nên không có cookie → người dùng là khách. Bấm "Bật đồng bộ" ở đó tạo một tài khoản ẩn danh **mới, rỗng**, và liên kết Google sau đó chỉ có thể thất bại vì identity đó đã thuộc tài khoản của máy trước. Không có đường nào để *đăng nhập* vào tài khoản đã tồn tại — đúng chức năng mà cả tính năng sinh ra để phục vụ. Dữ liệu cũ không mất, vẫn nằm ở tài khoản ban đầu.

**Sửa:** thêm `start_google_signin()` dùng `sign_in_with_oauth()` — không cần phiên sẵn có và trả về đúng tài khoản mà identity Google đang thuộc về. Mục đồng bộ ở trạng thái khách giờ trình bày hai lựa chọn tách bạch: "Bật đồng bộ" (tài khoản mới) và "Đăng nhập bằng Google" (lấy lại tài khoản cũ). Trạng thái ẩn danh cảnh báo rằng liên kết lần hai sẽ lỗi và chỉ sang đăng xuất + đăng nhập.

URL OAuth chỉ được tạo sau khi bấm nút, không tạo lúc render, nên khách vẫn không dựng Supabase client và bài test chốt trong `tests/test_pages.py` vẫn đúng. Đã xác minh trên project thật: URL trỏ `/auth/v1/authorize`, có PKCE `s256`, nên cookie `code_verifier` sẵn có phủ luôn luồng này.

Bài học rút ra: bài 4 của ma trận mục 12 được đánh dấu pass quá sớm. Nó đòi "ẩn danh trên máy A, liên kết Google, **đăng nhập trên máy B**", nhưng phần kiểm thử chỉ chạy hết vế đầu trên cùng một trình duyệt. Vế "máy B" mới là vế phát hiện ra lỗ hổng. Bài 4 giờ tính là **chưa pass** cho tới khi thử thật trên thiết bị/trình duyệt thứ hai.

### 2026-08-20 - Cookie component chạy đúng, nhưng ghi cookie bị `st.rerun()` nuốt mất

**Mục tiêu:** đọc kết quả đo trên production sau khi chuyển sang `utils/cookies.py` và xử lý phần còn hỏng.

**Người dùng đo được ba trạng thái liên tiếp trong bảng "Chẩn đoán đồng bộ":**

| Thời điểm | Component trả lời | Số cookie đọc được | Thấy `nv_refresh_token` | Qua `st.context` |
|---|---|---|---|---|
| Khách, chưa làm gì | true | 9 | false | 0 |
| Ngay sau "Bật đồng bộ" (trạng thái `anonymous`) | true | 9 | **false** | 0 |
| Sau khi liên kết Google (trạng thái `linked`) | true | 9 | true (dài 12) | 0 |

**Kết luận 1 — bản vá component đã thành công.** `Số cookie đọc được: 9` so với `Qua st.context: 0` là bằng chứng trực tiếp: trình duyệt có cookie, nền tảng bóc sạch khỏi HTTP header, và kênh component lấy được. Chặn lớn ngày 2026-08-19 coi như đã xử lý xong ở tầng đọc.

**Kết luận 2 — `Độ dài token: 12` là bình thường, không phải bị cắt.** Đã đo trực tiếp trên project thật (spike, `.venv311`): refresh token Supabase dài đúng 12 ký tự chữ-số, và `refresh_session()` với đúng chuỗi đó trả về cùng `user.id`. Ghi lại vì con số này trông giống dấu hiệu cookie bị truncate.

**Kết luận 3 — lỗi thật nằm ở tầng *ghi*.** Dòng thứ hai của bảng là bằng chứng: tài khoản ẩn danh đã tạo xong nhưng trình duyệt **không** có cookie phiên. Nguyên nhân: `manager.set()` chỉ *render một iframe*; cookie chỉ thực sự tồn tại khi JS trong iframe đó chạy, tức sau khi script kết thúc. Nút "Bật đồng bộ" gọi `st.rerun()` ngay sau đó, Streamlit dựng lại cây phần tử và iframe chưa kịp chạy. Cùng lỗi này áp cho "Đăng xuất" (`clear_session_cookie()` rồi `st.rerun()`).

**Đây chính là nguyên nhân của hai triệu chứng người dùng báo:**

- *F5 mất hồ sơ vừa lưu*: không có cookie thì lần tải trang sau là khách.
- *Có hai dòng "Lăng Nhật Minh" trong bảng `profiles`*: mỗi lần "Bật đồng bộ" lại tạo một tài khoản ẩn danh mới rồi lưu hồ sơ vào đó, vì lần trước không để lại cookie nào.

**Sửa** (`utils/cookies.py` viết lại):

1. **Hàng đợi ghi có retry.** Mỗi lần ghi/xóa được lưu vào session state và phát lại ở đầu mỗi vòng chạy sau — trong `init_cookie_manager()`, tức trước khi bất cứ chỗ nào kịp `st.rerun()` — cho tới khi trình duyệt báo lại đúng giá trị. Nhờ vậy chỗ gọi được phép `st.rerun()` thoải mái. Hết lượt retry mà vẫn chưa xác nhận thì ghi vào `unconfirmed_writes()` để bảng chẩn đoán nói ra, thay vì phiên tự bốc hơi lúc tải lại.
2. **Lớp overlay khi đọc.** Snapshot của component chỉ cập nhật khi frontend trả lời, nên cookie vừa ghi sẽ đọc ra "không có" và cookie vừa xóa vẫn đọc ra "còn". `read_cookie()` ưu tiên overlay của chính mình; xóa để lại *tombstone* nên `bootstrap_session()` không thể khôi phục lại phiên mà người dùng vừa đăng xuất.
3. **`cookies_ready()` dính (sticky).** Một lần trả lời rồi thì giữ nguyên, tránh việc câu trả lời rỗng sau đó bị hiểu là "chưa hỏi" và làm bootstrap treo.
4. **Hạn cookie dùng timezone-aware.** `CookieManager` gửi `isoformat()` sang trình duyệt, mà JS đọc chuỗi không timezone theo giờ **local** — server Cloud chạy UTC nên mọi hạn dùng đều lệch đúng bằng offset của người xem.
5. **`retry=False` cho `code_verifier` PKCE.** Verifier được ghi lại ở mỗi lần render, nên retry sẽ gửi verifier *cũ* cùng lúc với verifier mới, và iframe nào chạy sau sẽ quyết định cookie còn khớp `code_challenge` trong URL hay không. Ghi lại mỗi render đã là tự lành, không cần retry.
6. **Khóa component tăng dần theo lượt.** Hai instance trùng khóa trong một vòng chạy là lỗi Streamlit; dùng lại khóa cũ với tham số không đổi thì Streamlit trả kết quả cache và retry thành no-op câm.
7. **Xóa cookie chưa từng tồn tại không tốn gì.** GoTrue gọi `remove_item()` cho các khóa nó chưa bao giờ ghi (`sign_in_with_oauth()` dọn sạch storage trước), nên nếu xếp hàng retry thì mỗi vòng chạy đều render một iframe xóa rồi báo nhầm là "trình duyệt từ chối ghi".

**Sửa kèm trong `pages/3_Ho_so.py`:** URL đăng nhập Google giờ dựng lại ở **mỗi lần render** thay vì cache trong session state. Mỗi lần dựng sinh một verifier mới và đè cookie, nên URL cache sẽ mang `code_challenge` của verifier mà cookie không còn giữ — đúng kiểu hỏng "bấm xong không thấy gì xảy ra". Cách này giống hệt nút liên kết, vốn vẫn chạy được chính vì nó dựng lại mỗi render. Cờ chỉ bật sau khi bấm nút, nên khách vẫn không dựng Supabase client và test chốt trong `tests/test_pages.py` vẫn đúng.

**Bảng chẩn đoán** thêm hai dòng: `Đang chờ trình duyệt ghi` (thoáng qua, bình thường) và `Trình duyệt từ chối ghi` (phiên này sẽ mất khi tải lại).

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `.venv311\Scripts\python.exe -m pytest -q` | `155 passed, 1 skipped` (thêm `tests/test_cookies.py`, 14 test) |
| `.venv311\Scripts\python.exe test_imports.py` | `All smoke checks passed` |
| Spike đo refresh token trên project thật | dài 12, `refresh_session()` trả về cùng `user.id` |

**Quyết định:** `tests/test_cookies.py` mô phỏng đúng hai tính chất đã gây ra lỗi — `.cookies` là snapshot cũ (ghi mới không thấy trong đó) và `.set()` chỉ là *yêu cầu* ghi mà frontend có thể không thực hiện. Test "ghi bị rerun nuốt thì vòng sau phát lại" là test lẽ ra phải có ngay từ đầu.

**Bài học nối tiếp mục trước:** lần trước rút ra "phải kiểm chứng giả định rủi ro nhất trên đúng môi trường triển khai". Lần này rút thêm: bảng chẩn đoán phải đo **cả hai chiều** — có đọc được cookie *và* ghi có tới nơi không. Bản chẩn đoán đầu chỉ đo chiều đọc nên khi chiều đọc đã xanh, vẫn không nhìn ra chiều ghi đang hỏng.

**Chưa xác minh trên production:** vẫn cần deploy rồi chạy lại bài 2 (F5 giữ đăng nhập) và bài 4 vế hai (đăng nhập ở thiết bị khác).

### 2026-08-20 - Bài 2 PASS; lỗi OAuth do app không đọc `?error=` Supabase trả về

**Bài 2 (F5 giữ đăng nhập) - PASS trên production.** Đo sau khi F5: `Trạng thái: anonymous`, `Thấy cookie phiên: true`, độ dài token 12, và hồ sơ vừa chỉnh vẫn còn. Hàng đợi ghi cookie đã giải quyết đúng chỗ hỏng. Đây là bài mà bản 3 `STORAGE_PLAN.md` coi là *vấn đề cốt lõi* của cả kế hoạch — nay đã có bằng chứng chạy thật trên đúng môi trường triển khai.

**Nhưng cùng lần đo đó lộ hai vấn đề.**

**Vấn đề 1 - báo động giả `Trình duyệt từ chối ghi: nv_refresh_token`.** Cookie có thật (`Thấy cookie phiên: true`) mà vẫn bị báo là bị từ chối. Nguyên nhân: Supabase **xoay refresh token ở mỗi lần `refresh_session()`**, nên mỗi lần tải trang lại ghi một giá trị mới; còn snapshot của component thì chậm ít nhất một vòng chạy. So sánh theo *giá trị* nên không bao giờ khớp. Sửa: xác nhận theo **sự tồn tại của tên cookie**, không theo giá trị. Lỗi mà hàng đợi sinh ra để bắt — ghi bị `st.rerun()` huỷ — vẫn bị bắt, vì khi đó tên cookie không hề tồn tại.

**Vấn đề 2 - đăng nhập/liên kết Google "chẳng có gì xảy ra".** Triệu chứng: bấm sang Google, quay về, trạng thái vẫn `anonymous`, hàng trong `profiles` vẫn `email = NULL, is_anonymous = true`, cookie PKCE nằm lại không ai dùng. Người dùng thử cả hai tài khoản Gmail, đều vậy.

**Nguyên nhân:** Supabase quay về app với **một trong hai**: `?code=...` khi thành công, hoặc `?error=...&error_description=...` khi thất bại. `bootstrap_session()` chỉ đọc `?code=`. Không có `code` thì nó rơi xuống nhánh khôi phục cookie, khôi phục lại đúng tài khoản ẩn danh đang có, và render lại y hệt trang cũ — nhìn từ ngoài đúng là *không có gì xảy ra*. Thông báo lỗi thật của máy chủ bị vứt đi ngay tại URL.

Vì sao lần này lỗi: `link_identity()` bị từ chối khi identity Google đó **đã thuộc về tài khoản khác**. Cả hai Gmail đều đã bị hai tài khoản trùng lặp sinh ra trước đó (mục nhật ký cùng ngày ở trên) chiếm chỗ, nên mọi lần liên kết tiếp đều chỉ có thể thất bại.

**Sửa:**

- `_oauth_error_from_query()` đọc `error_description` / `error_code` / `error`, đặt vào `sync_error` kèm gợi ý dùng *Đăng nhập bằng Google* thay vì liên kết lần nữa, rồi dọn query param và cookie verifier bị bỏ lại. **Không** hạ người dùng xuống khách: liên kết hỏng thì tài khoản ẩn danh vẫn dùng tốt.
- `?code=` giờ bị xoá **cả khi exchange thất bại**. Trước đó code đã tiêu vẫn nằm lại URL và bị thử lại ở mọi rerun, thay lỗi thật bằng một lỗi thứ hai khó hiểu hơn.
- `_record_oauth_result()` giữ kết quả Google gần nhất trong session state. `sync_error` bị trang nào render trước pop mất, nên thông báo hiện ở trang chủ đã biến mất trước khi người dùng sang trang Hồ sơ tìm nó.
- `oauth_diagnostics()` + bảng chẩn đoán hiển thị: địa chỉ `redirect_to` đang dùng, có `?code=` hay không, lỗi trên URL, và kết quả Google gần nhất.
- Trạng thái `anonymous` nay có thêm mục *"Tôi đã có tài khoản Google từ trước"* mở ra nút đăng nhập. Trước đó lối thoát duy nhất là đăng xuất rồi mới thấy nút, mà chỉ có một dòng caption nói điều đó.

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `.venv311\Scripts\python.exe -m pytest -q` | `158 passed, 1 skipped` |
| `.venv311\Scripts\python.exe test_imports.py` | `All smoke checks passed` |
| Bài 2 (F5 giữ đăng nhập) trên production | **PASS** |

**Bài học:** hai lần trước rút ra "kiểm chứng trên đúng môi trường triển khai" và "chẩn đoán phải đo cả hai chiều". Lần này thêm một dạng khác: **im lặng vì không đọc kênh báo lỗi có sẵn**. Máy chủ đã nói rõ lý do ngay trên URL suốt từ đầu; app chỉ đơn giản là không nhìn. Khi một luồng "không có gì xảy ra", việc đầu tiên phải làm là kiểm tra xem có kênh phản hồi nào đang bị bỏ qua hay không, trước khi đi đoán nguyên nhân.

### 2026-08-20 - `code challenge does not match` - hai URL OAuth cùng tranh một cookie

**Triệu chứng:** `AuthApiError: code challenge does not match previously saved code verifier`. Khác hẳn các lần trước ở chỗ đây là lỗi **có nội dung** — nhờ bản vá đọc `?error=` và giữ `last_oauth_result` ngay trước đó. Exchange đã chạy, đã tìm thấy verifier, chỉ là verifier sai.

**Nguyên nhân:** mỗi lần dựng URL OAuth (`sign_in_with_oauth()` hoặc `link_identity()`) sinh một verifier mới và **đè lên cùng một cookie** `nv_pkce_supabase.auth.token-code-verifier`. Vậy URL hiển thị trên màn hình và cookie trong trình duyệt bắt buộc phải do **cùng một lần gọi** sinh ra rồi để yên. Có hai cách làm hỏng điều đó, và code đang dính cả hai:

1. **Dựng lại URL ở mỗi lần render.** Đây là thay đổi tôi vừa đưa vào cùng ngày, với lý do tưởng là đúng ("URL cache có thể lệch với cookie"). Thực tế nó tạo vòng lặp: ghi cookie mới → component `getAll` thấy cookie đổi → Streamlit rerun → render lại → sinh verifier mới → ghi cookie mới → ... Tới lúc người dùng bấm, cookie đã đi trước URL đang hiển thị vài nhịp. Trước khi có component thì vòng lặp này không tồn tại (cookie ghi bằng `st.html`, đọc bằng `st.context.cookies`, không có kênh phản hồi) — nên cách làm cũ chạy được và tôi tưởng nó đúng.
2. **Hai URL sống cùng lúc.** Cũng cùng ngày, tôi thêm nút *Đăng nhập bằng Google* vào trạng thái `anonymous`, ngay cạnh nút *Liên kết Google* vốn dựng URL ở mỗi render. Cả hai ghi cùng một cookie trong cùng một vòng chạy; iframe nào chạy sau quyết định nút nào còn dùng được.

**Sửa:** một hàm `_request_oauth(kind)` duy nhất dựng URL, **chỉ chạy khi bấm nút**, lưu đúng **một** URL đang chờ vào `st.session_state["pending_oauth"]`; `_render_pending_oauth()` hiển thị nó. Xin URL mới thì thay thế URL cũ chứ không thêm vào. Nút *Liên kết Google* cũng chuyển sang hai bước như vậy, không còn dựng URL lúc render. `_record_oauth_result()` xoá `pending_oauth` khi vòng OAuth kết thúc, vì lúc đó verifier đã tiêu.

Chốt bằng test `test_only_one_place_mints_a_pkce_verifier` trong `tests/test_pages.py`: `auth.start_google_link` và `auth.start_google_signin` mỗi cái được phép xuất hiện **đúng một lần** trong trang, và cả hai phải nằm trong `_request_oauth`. Đây là bất biến tôi đã phá hai lần trong một ngày nên cần có test giữ.

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `.venv311\Scripts\python.exe -m pytest -q` | `159 passed, 1 skipped` |
| `.venv311\Scripts\python.exe test_imports.py` | `All smoke checks passed` |

**Bài học:** bản sửa buổi sáng ("dựng lại URL mỗi render để URL và cookie luôn khớp") là một cách chữa dựa trên suy đoán chứ không dựa trên số đo, và nó tự tạo ra đúng lỗi mà nó định phòng. Điểm chung với hai mục trước: khi chưa có tín hiệu đo được thì đừng sửa, hãy làm cho lỗi hiện ra trước. Đúng thứ tự đó lần này đã hiệu quả — chính bản vá "hiện lỗi lên" mới lôi được thông báo thật của máy chủ ra.

### 2026-08-20 - Bài 4 PASS: đồng bộ đa thiết bị chạy đúng end-to-end

**Điều kiện chạy:** xóa sạch `auth.users` trước (các tài khoản rác từ những lần lỗi trước vẫn đang giữ hai identity Google, khiến `link_identity()` chỉ có thể bị từ chối). Deploy commit `42f392a`, reboot app.

**Kịch bản đã chạy trên hai trình duyệt thật:**

| Bước | Kết quả |
|---|---|
| Trình duyệt A: Bật đồng bộ → lưu hồ sơ → Liên kết Google | Trạng thái `linked`, dữ liệu lên database |
| Trình duyệt B (không chung cookie): Đăng nhập bằng Google | Mở đúng tài khoản cũ, thấy đủ hồ sơ của A |
| Trình duyệt A: đổi cân nặng → Lưu thay đổi | Ghi lên máy chủ |
| Trình duyệt B: tải lại trang | Thấy ngay cân nặng mới |

**Xác nhận:** bài 4 của ma trận mục 12 `STORAGE_PLAN.md` **PASS toàn phần**, gồm cả vế thiết bị thứ hai — vế từng bị đánh dấu pass quá sớm ngày 2026-08-19 và chính nó đã lộ ra lỗ hổng thiếu `sign_in_with_oauth()`. Bước cuối (đổi dữ liệu ở A, đọc lại ở B) nằm ngoài ma trận nhưng là bằng chứng mạnh hơn: nó chứng minh đây là đồng bộ hai chiều thật, không phải chỉ khôi phục một lần lúc đăng nhập.

**Cùng với bài 2 đã pass sáng cùng ngày, hai bài quyết định của cả kế hoạch lưu trữ đều đã có bằng chứng chạy thật trên đúng môi trường triển khai.** Tính năng lưu trữ đa thiết bị coi như hoàn tất về mặt chức năng.

**Tổng kết chuỗi lỗi của tính năng này** (chi tiết ở các mục nhật ký 2026-08-19 và 2026-08-20). Tất cả đều là lỗi *tích hợp với nền tảng*, không phải lỗi thuật toán hay lỗi thiết kế dữ liệu — schema, RLS và `utils/repository.py` không phải sửa dòng nào sau khi chốt:

| # | Lỗi | Phát hiện bằng |
|---|---|---|
| 1 | Anonymous sign-ins chưa bật trong dashboard | spike thật, HTTP 422 |
| 2 | `redirect_to` phải lồng trong `options` | đọc shape của SDK |
| 3 | `get_client()` dựng client mới mỗi lần gọi → mọi truy vấn chạy bằng anon key | spike thật |
| 4 | `code_verifier` PKCE không sống qua vòng redirect | spike thật |
| 5 | `maybe_single().execute()` trả `None` | spike thật |
| 6 | `ClientOptions` không có `storage`, phải dùng `SyncClientOptions` | spike thật |
| 7 | `record_signature()` trùng nhau do `datetime.now()` trên Windows chỉ ~16ms | test |
| 8 | Thiếu hẳn đường đăng nhập ở thiết bị thứ hai | thử trên bản deploy |
| 9 | `st.context.cookies` luôn rỗng trên Streamlit Cloud | đo trên production |
| 10 | Ghi cookie bị `st.rerun()` huỷ | đo trên production |
| 11 | App không đọc `?error=` Supabase trả về | đo trên production |
| 12 | Hai URL OAuth cùng đè một cookie verifier | đo trên production |

Sáu lỗi đầu bắt được nhờ **spike chạy thật trước khi viết code**; sáu lỗi sau chỉ lộ ra **trên đúng môi trường triển khai**. Đó là kết luận đáng đưa vào báo cáo: với tích hợp dịch vụ ngoài, unit test và chạy local không đủ để kết luận đúng — cả hai đều xanh trong suốt thời gian sáu lỗi cuối đang tồn tại.

**Commit của tính năng lưu trữ, theo thứ tự:**

| Commit | Nội dung |
|---|---|
| `25e24b3` | Chuẩn bị deploy cloud và `STORAGE_PLAN.md` |
| `4a45566` | Đồng bộ Supabase dạng opt-in cho hồ sơ và lịch sử |
| `b3d65f6` | Nói rõ thiếu mục cấu hình Supabase nào |
| `8799ddb` | Thêm đăng nhập Google cho thiết bị thứ hai |
| `3af1cf2` | Không để cookie PKCE bị auto-redirect chạy trước |
| `d47e7bc` | Giải mã cookie phiên, không nuốt lỗi khôi phục |
| `6acb0c4` | Đọc cookie qua component thay cho `st.context.cookies` |
| `7ec94c1` | Chặn `st.rerun()` huỷ mất lệnh ghi cookie |
| `335e66c` | Đọc lỗi Supabase trả về, không chỉ đọc `?code=` |
| `42f392a` | Dựng URL Google một lần, không dựng lại mỗi render |

### 2026-08-20 - Cron chống pause đã chạy thật; thêm `verify_rls.sql`

**Cron:** người dùng đã thêm hai GitHub repo secrets. Workflow *Supabase keepalive* chạy xanh cả lần bấm tay lẫn lần theo lịch. Lần đầu mất 5 phút 09 giây, lần sau chỉ 7 giây — chênh lệch này khớp với việc lần đầu phải đánh thức project đang ngủ, còn về sau chỉ là một request tới project đang chạy. Giai đoạn A coi như xong trọn vẹn.

Lưu ý còn hiệu lực: GitHub tự tắt scheduled workflow sau 60 ngày repo không có hoạt động, nên trước buổi bảo vệ vẫn phải đánh thức và kiểm tra project thủ công.

**`verify_rls.sql` (mới):** ba câu truy vấn kiểm chứng RLS đang thực sự bật trong database, chạy trong SQL Editor.

Lý do cần có, và đây mới là điểm đáng ghi: **không có gì trong ứng dụng phát hiện được việc RLS bị tắt.** Trình duyệt nói thẳng với PostgREST, không có server trung gian nào của mình, nên các policy trong `storage_schema.sql` là lớp bảo vệ duy nhất. Nếu hôm chạy schema mà nửa dưới của file (`enable row level security` và tám `create policy`) không được thực thi, ứng dụng chạy **y hệt**: đồng bộ đúng, dữ liệu đúng, không lỗi ở đâu cả. Khác biệt duy nhất là bảng đang mở toang cho bất kỳ ai cầm publishable key — mà key đó gửi tới mọi trình duyệt.

Đọc source của policy chỉ chứng minh nó *được viết đúng*, không chứng minh nó *đang sống* trong database này. Ba câu truy vấn:

1. `pg_class.relrowsecurity` cho `profiles` và `meals` — kỳ vọng `true` cả hai.
2. Đếm policy trong `pg_policies` — kỳ vọng 8 dòng, mỗi bảng đủ SELECT/INSERT/UPDATE/DELETE.
3. Đọc `qual` và `with_check` của từng policy — kỳ vọng đều nhắc tới `auth.uid()` và `user_id`. Câu này bắt trường hợp policy tồn tại nhưng viết `using (true)`, tức thoả câu 2 mà không bảo vệ gì.

**Quyết định về phạm vi:** bài 1 của ma trận mục 12 `STORAGE_PLAN.md` yêu cầu tấn công trực diện — cầm JWT của tài khoản A gọi PostgREST đọc/sửa/xóa dữ liệu tài khoản B, gồm cả phép ghi một dòng `user_id = B` để kiểm chứng mệnh đề `with check`. Bài đó **cố ý hoãn lại**, không phải bỏ quên. Lý do: trọng tâm đồ án là phần AI, còn rủi ro thật ở đây không phải "policy viết sai" (đọc source là kiểm được) mà "policy chưa được bật", và ba câu truy vấn trên đã trả lời đúng câu đó với chi phí gần bằng không. Nếu cần một bằng chứng mạnh hơn để trả lời hội đồng thì viết script tấn công sau; hiện chưa cần.

**Kết quả chạy (2026-08-21):** câu 2 và câu 3 **đạt**. Trả về đúng 8 dòng, mỗi bảng đủ SELECT/INSERT/UPDATE/DELETE, và `qual`/`with_check` của từng policy khớp nguyên văn với `storage_schema.sql`:

```
((( SELECT auth.uid() AS uid) IS NOT NULL) AND (( SELECT auth.uid() AS uid) = user_id))
```

Đúng như thiết kế: `qual` trống ở INSERT (Postgres không đọc `using` cho INSERT), `with_check` trống ở SELECT/DELETE, còn UPDATE có cả hai — nếu UPDATE thiếu `with_check` thì một tài khoản vẫn sửa được dòng của mình rồi *đổi* `user_id` sang người khác. Dạng `(select auth.uid())` bọc trong subquery là chủ ý: Postgres coi đó là hằng số của câu truy vấn nên chỉ gọi một lần thay vì gọi lại trên từng dòng.

Câu 1 (`relrowsecurity`) ban đầu không có kết quả — SQL Editor của Supabase chỉ hiển thị kết quả của câu lệnh **cuối cùng** khi chạy nhiều câu một lượt, nên output của câu 1 và câu 2 bị câu 3 che mất. Chạy riêng câu 1 thì **đạt**: `meals = true`, `profiles = true`.

Đây là câu quyết định, không phải câu phụ: policy tồn tại đầy đủ nhưng RLS chưa bật thì Postgres **bỏ qua toàn bộ policy**, bảng vẫn mở toang, mà câu 3 vẫn trả về y hệt kết quả đẹp ở trên. Nói cách khác kết quả câu 3 một mình tương thích với cả trường hợp an toàn lẫn trường hợp thủng; chỉ câu 1 phân biệt được hai trường hợp đó. **Bài 1a đóng: RLS đang bật thật, tám policy đang sống, mỗi policy so `auth.uid()` với `user_id`.**

Rút ra cho lần sau: khi kiểm chứng bằng SQL Editor phải chạy từng câu một, hoặc gộp thành một câu bằng `union all`, chứ chạy cả file thì chỉ thấy câu cuối.

## 8. Công việc tiếp theo khi tiếp tục

### Phase C5 - Kiểm tra thủ công còn lại

- Khi có `NGROK_AUTHTOKEN`, mở HTTPS tunnel và kiểm tra navigation, upload/camera, bảng, tư vấn dài, biểu đồ và thao tác cảm ứng trên điện thoại thật.
- Chụp bằng chứng desktop/mobile và ghi input, expected, actual vào tài liệu này.

### Live OpenAI LLM

- Kiểm tra một ảnh/meal đại diện qua UI với `LLM_PROVIDER=openai` và `OPENAI_MODEL=gpt-4o-mini`; ghi latency, format và lỗi nếu có.
- Google Gemini/Gemma chỉ là phương án thay thế, không thuộc demo chính trừ khi có thay đổi quyết định.

### Lưu trữ đa thiết bị (STORAGE_PLAN.md)

- Giai đoạn 0, A và C **đã xong**. **Bài 2 (F5 giữ đăng nhập) và bài 4 (đồng bộ đa thiết bị) đều PASS trên production ngày 2026-08-20** — xem nhật ký cùng ngày ở mục 7. Tính năng coi như hoàn tất về mặt chức năng.
- **Cron chống pause đã xong** (2026-08-20): secrets đã thêm, workflow *Supabase keepalive* chạy xanh cả lần bấm tay lẫn lần theo lịch.
- **Kiểm thử thủ công còn nợ** — bảng tình trạng đầy đủ 14 bài nằm ở cuối mục 12 `STORAGE_PLAN.md`. **Bài 1a đã đạt** (2026-08-21): cả ba câu `verify_rls.sql` đều đúng kỳ vọng. Chạy lại file này mỗi khi áp lại schema hoặc khôi phục project sau khi bị pause. Bài 1b (tấn công trực diện bằng JWT của tài khoản khác) hoãn có chủ ý, xem lý do trong nhật ký 2026-08-20. Còn lại là biến thể môi trường: bài 3 (mở lại từ icon PWA), bài 5 (redeploy không mất phiên), bài 10 (lưu khi mất mạng), bài 13 (PWA standalone trên iPhone — Safari nghiêm ngặt nhất với cookie nên đây là bài dễ hỏng riêng), bài 14 (pause/restore project).
- **Rủi ro còn lại đã biết:** GitHub tự tắt scheduled workflow sau 60 ngày repo không có hoạt động, nên trước buổi bảo vệ vẫn phải đánh thức và kiểm tra project Supabase thủ công, không tin hoàn toàn vào cron.
- Giai đoạn D: rà 23 chỗ `unsafe_allow_html=True` còn lại (đã xác nhận `pages/3_Ho_so.py`→`utils/ui.py` escape đúng), thêm test XSS chốt hành vi, export JSON dự phòng.
- `utils/history.append_meal_once()` giờ không còn trang nào gọi (đã thay bằng `SessionRepository.save_meal`), chỉ còn test dùng — cân nhắc bỏ khi dọn dẹp.

### Phase E - Báo cáo và demo

- Đồng bộ báo cáo, README và dashboard theo 12 lớp, Kaggle và Baseline B.
- Chuẩn bị demo 5 phút và kịch bản dự phòng khi LLM/mạng lỗi.
- Thực hiện clean-clone/production smoke test sau khi có cơ chế phân phối checkpoint.
