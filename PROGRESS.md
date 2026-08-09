# NutriVision Progress Record

**Cập nhật:** 2026-08-09<br>
**Trạng thái hiện tại:** Phase A và B hoàn tất; Phase C đang tiếp tục sau khi xử lý privacy, môi trường và cleanup.

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

## 8. Công việc tiếp theo khi tiếp tục

### Phase C - Hoàn thiện luồng người dùng

- Kiểm tra ảnh một món, nhiều món, không có món, ảnh lỗi và ảnh lớn.
- Kiểm tra HITL tại `0.25x`, `1.0x`, `3.0x`; xác nhận calo và macro thay đổi đúng.
- Kiểm tra fallback khi không có API key, key không hợp lệ hoặc LLM lỗi mạng.
- Kiểm tra giao diện upload, bảng dinh dưỡng, tư vấn dài và biểu đồ trên điện thoại.

### Phase D - Release gate

- Thêm automated tests cho BMI/BMR/TDEE, macro, nutrition DB, label contract, history và model smoke test.
- Thiết lập một lệnh release test trả non-zero khi thất bại.

### Phase E - Báo cáo và demo

- Đồng bộ báo cáo, README và dashboard theo 12 lớp, Kaggle và Baseline B.
- Chuẩn bị demo 5 phút và kịch bản dự phòng khi LLM/mạng lỗi.
- Thực hiện clean-clone/production smoke test sau khi có cơ chế phân phối checkpoint.
