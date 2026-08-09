# PLAN.md - Kế hoạch hoàn thiện NutriVision

## 1. Mục tiêu

**Đề tài:** Hệ thống Trợ lý Tư vấn Dinh dưỡng Cá nhân hóa kết hợp Thị giác Máy tính và Mô hình Ngôn ngữ Lớn.

NutriVision cần hoàn thiện một luồng có thể kiểm chứng và triển khai được:

1. Nhận diện 12 món ăn Việt Nam bằng YOLOv8n.
2. Chuyển nhãn gốc của checkpoint sang ID chuẩn dùng trong ứng dụng.
3. Tra cứu dinh dưỡng và cho phép người dùng điều chỉnh khẩu phần bằng HITL từ `0.25x` đến `3.0x`.
4. Tính BMI, BMR, TDEE, mục tiêu calo và macro.
5. Sinh tư vấn tiếng Việt bằng Gemini/OpenAI hoặc nội dung mẫu khi không có API key.
6. Lưu và trực quan hóa lịch sử bữa ăn.
7. So sánh Baseline A và Baseline B trên cùng một benchmark trước khi chọn model triển khai.

Trạng thái hiện tại: A0/A/B đã được đánh giá trên benchmark sạch 404 ảnh; Baseline B đã được chọn bằng tie-break, hợp đồng 12 lớp và giao diện model thật đã được tích hợp. Kiểm thử release và deployment công khai vẫn cần hoàn tất.

## 2. Kiến trúc mục tiêu

```text
Ảnh đầu vào
-> YOLOv8n checkpoint
-> Bộ chuyển raw label sang canonical food ID
-> Cơ sở dữ liệu dinh dưỡng 12 món
-> HITL điều chỉnh khẩu phần (0.25x - 3.0x, bước 0.25)
-> Tổng calo và macro
-> Hồ sơ người dùng + BMI/BMR/TDEE + mục tiêu
-> Gemini/OpenAI hoặc sample advice có ghi nhãn rõ ràng
-> Lịch sử bữa ăn theo phiên/người dùng
```

Các thành phần chính:

| Thành phần | Nguồn sự thật |
|---|---|
| Streamlit entrypoint | `app.py` |
| Phân tích ảnh, HITL, tư vấn | `pages/1_Phan_tich_anh.py` |
| Lịch sử và biểu đồ | `pages/2_Lich_su.py` |
| Hồ sơ và API key trong phiên | `pages/3_Ho_so.py` |
| YOLO wrapper | `models/detector.py` |
| Cấu hình và hợp đồng lớp | `config.py` |
| Dữ liệu dinh dưỡng | `data/nutrition_db.json` |
| Tính toán dinh dưỡng | `utils/nutrition.py` |
| LLM | `utils/llm.py` |
| Benchmark A/B | `test_model/` |
| Dataset A/B local | `datasets/Baseline_A_yolov8/`, `datasets/Baseline_B_yolov8/` |

## 3. Hiện trạng dữ liệu và mô hình

### 3.1 Nguồn huấn luyện

- Cả Baseline A và Baseline B được huấn luyện trên Kaggle.
- Checkpoint cho thấy cả hai dùng `yolov8n.pt`, 100 epoch, batch 32, ảnh 640 và seed 0 ở chế độ deterministic.
- `training/train.py` trong repository là script local mang tính tham khảo, không phải cấu hình đã tạo ra hai checkpoint Kaggle.
- Cần lưu notebook hoặc lệnh train thực tế từ Kaggle để tái lập thí nghiệm.

### 3.2 Phân biệt hai loại augmentation

**Offline augmentation** tạo ảnh mới trước khi train và lưu trực tiếp trong dataset.

**Online augmentation** được YOLO áp dụng ngẫu nhiên khi đọc ảnh trong từng epoch; ảnh biến đổi không được lưu thành file nguồn mới.

Baseline A không có offline augmentation từ Roboflow, nhưng vẫn có online augmentation mặc định của YOLO. Metadata checkpoint A ghi nhận:

| Tham số | Giá trị |
|---|---:|
| `hsv_h` | 0.015 |
| `hsv_s` | 0.7 |
| `hsv_v` | 0.4 |
| `translate` | 0.1 |
| `scale` | 0.5 |
| `fliplr` | 0.5 |
| `mosaic` | 1.0 |
| `close_mosaic` | 10 |

Baseline B có hai tầng augmentation:

- Roboflow tạo 3 phiên bản từ mỗi ảnh nguồn bằng flip ngang 50%, rotation từ -15 đến +15 độ và brightness từ -15% đến +15%.
- YOLO tiếp tục áp dụng online augmentation mặc định trong quá trình train.

Tên gọi chính xác trong báo cáo:

- **Baseline A:** dữ liệu gốc, không offline augmentation, có online augmentation mặc định của YOLO.
- **Baseline B:** dữ liệu mở rộng, có offline augmentation 3x, có online augmentation mặc định của YOLO, bổ sung Phở/Xôi và hard negatives.

Không gọi A là model "hoàn toàn không augmentation". Trường `train_args["augment"] = False` trong checkpoint không vô hiệu hóa các biến đổi train được điều khiển bởi `hsv_*`, `translate`, `scale`, `fliplr`, `mosaic` và các tham số liên quan.

Một thí nghiệm thật sự không augmentation phải đặt toàn bộ hệ số biến đổi về 0, tối thiểu gồm `hsv_h`, `hsv_s`, `hsv_v`, `degrees`, `translate`, `scale`, `shear`, `perspective`, `flipud`, `fliplr`, `mosaic`, `mixup`, `cutmix`, `copy_paste` và `erasing`.

### 3.3 Dataset local đã kiểm tra

| Dataset | Train | Validation | Test | Tổng box | Empty-label negatives |
|---|---:|---:|---:|---:|---:|
| Baseline A | 2,711 | 751 | 398 | 4,491 | 0 / 0 / 0 |
| Baseline B | 8,852 | 819 | 432 | 11,578 | 225 / 21 / 11 |

Các quan sát cần giữ trong báo cáo:

- Với 10 lớp đầu, số ảnh và số box train của B đúng bằng 3 lần A, phù hợp với quy trình offline augmentation 3x.
- B có thêm dữ liệu Phở, Xôi và ảnh nền/hard negative ngoài phần nhân 3.
- Empty-label files của B là nhãn hợp lệ cho ảnh không chứa đối tượng mục tiêu, không phải file hỏng.
- README Roboflow ghi 8,205 ảnh cho A và 20,255 ảnh cho B, trong khi inventory local lần lượt là 3,860 và 10,103 ảnh. Chênh lệch này phải được đối chiếu với filter/export version trước khi đưa số liệu vào báo cáo.
- Dataset và checkpoint là artifact gitignored; Git hiện không phải bản sao lưu cho các tệp này.

### 3.4 Checkpoint đã kiểm tra

| Thuộc tính | Baseline A | Baseline B |
|---|---|---|
| File chính | `test_model/weights_test/best_baseline_A.pt` | `test_model/weights_test/best_baseline_B.pt` |
| SHA-256 | `2b0e758aeefb42a30784bcc343a1111ccf0a44748152a0a614cc84fadb7d49d4` | `18b8f1dd160a4b6df6ae0f4dc31d00ec729722daefafdc50422dc9e36d845998` |
| Base model | YOLOv8n | YOLOv8n |
| Ultralytics lúc train | 8.4.106 | 8.4.105 |
| Epoch tốt nhất theo mAP50-95 | 86 | 42 |
| Native precision | 0.83242 | 0.81433 |
| Native recall | 0.78698 | 0.80080 |
| Native mAP50 | 0.83409 | 0.85266 |
| Native mAP50-95 | 0.63715 | 0.63259 |

Hai bản `best_baseline_B.pt` trong `models/weights/` và `test_model/weights_test/` hiện giống hệt nhau theo SHA-256.

Các metric trên là **native validation metrics**, không phải kết quả A/B công bằng, vì validation distribution và Ultralytics patch version không hoàn toàn giống nhau. B tốt hơn về recall và mAP50; A nhỉnh hơn precision và mAP50-95. Chỉ benchmark chung mới được dùng để chọn model và viết kết luận so sánh.

## 4. Hợp đồng 12 lớp

Checkpoint A và B có cùng thứ tự 12 nhãn:

| Index | Raw checkpoint label | Canonical ID | Tên hiển thị |
|---:|---|---|---|
| 0 | `Banh-mi` | `banh_mi` | Bánh mì |
| 1 | `Banh-trang-nuong` | `banh_trang_nuong` | Bánh tráng nướng |
| 2 | `Banh-xeo` | `banh_xeo` | Bánh xèo |
| 3 | `Bun-bo-Hue` | `bun_bo_hue` | Bún bò Huế |
| 4 | `Bun-dau-mam-tom` | `bun_dau_mam_tom` | Bún đậu mắm tôm |
| 5 | `Bun-rieu` | `bun_rieu` | Bún riêu |
| 6 | `Bun-thit-nuong` | `bun_thit_nuong` | Bún thịt nướng |
| 7 | `Chao-long` | `chao_long` | Cháo lòng |
| 8 | `Com-tam` | `com_tam` | Cơm tấm |
| 9 | `Goi-cuon` | `goi_cuon` | Gỏi cuốn |
| 10 | `Pho` | `pho` | Phở |
| 11 | `Xoi` | `xoi` | Xôi |

Quy tắc tích hợp:

- Không sửa tên lớp bên trong checkpoint; giữ nguyên để bảo toàn provenance.
- Thêm một mapping tường minh và đầy đủ từ raw label sang canonical ID.
- Dùng canonical ID trong app, nutrition DB và cấu hình dataset tương lai.
- Khi khởi động, app phải kiểm tra đủ 12 raw labels và báo lỗi rõ ràng nếu mapping thiếu hoặc thừa.
- Không tiếp tục âm thầm bỏ prediction không khớp như hành vi hiện tại.

Năm bản ghi dinh dưỡng cần bổ sung với nguồn trích dẫn rõ ràng:

- `banh_trang_nuong`
- `banh_xeo`
- `bun_dau_mam_tom`
- `bun_rieu`
- `bun_thit_nuong`

Ba món cũ không có trong checkpoint và phải được loại khỏi danh mục nhận diện hoặc chuyển sang danh mục thủ công riêng:

- `bun_cha`
- `nem_ran`
- `banh_cuon`

Điều kiện hợp đồng dữ liệu:

```text
raw checkpoint labels == raw-label adapter keys
adapter values == config.FOOD_CLASSES
config.FOOD_CLASSES == display-map keys
config.FOOD_CLASSES == emoji-map keys
config.FOOD_CLASSES == nutrition_db["foods"] keys
config.FOOD_CLASSES == canonical names của dataset tương lai
```

## 5. Khoảng trống hiện tại

| Khoảng trống | Ảnh hưởng |
|---|---|
| Benchmark chỉ có 10 ảnh negative | Tie-break false-positive cần được xác nhận trên tập OOD lớn hơn |
| Một số lớp benchmark dưới 30 mẫu | Per-class metric có độ bất định cao |
| `test_model/run_test_ab.py` dùng đường dẫn phụ thuộc working directory | Không có thư mục chạy nào hiện tải đúng cả weights và ảnh |
| A/B script chỉ đếm số box | Không đo đúng lớp, IoU, false positive hoặc mAP |
| Năm ảnh challenge chưa có ground truth | Chỉ phù hợp minh họa định tính |
| `training/train.py` không tái lập checkpoint Kaggle | Không thể dùng script hiện tại làm bằng chứng phương pháp train |
| `test_imports.py` bắt mọi exception và vẫn thường exit 0 | Không phải release gate đáng tin cậy |
| Meal history dùng một JSON chung trên disk | Không phù hợp deployment đa người dùng |
| Model, dataset và báo cáo đang ignored/untracked | Có nguy cơ mất artifact nếu chỉ dựa vào Git |

## 6. Lộ trình theo phase

Thứ tự mặc định: `P0 -> P1 -> P2 -> P3 (nếu cần) -> P4 -> P5 -> P6 -> P7`.

### P0 - Khóa artifact và provenance

Mục tiêu: bảo đảm mọi số liệu về A/B có thể truy ngược về đúng dataset, checkpoint và môi trường Kaggle.

Công việc:

- Lưu checkpoint A/B cùng SHA-256 tại nơi backup độc lập với repository.
- Xuất notebook hoặc lệnh train thực tế từ Kaggle.
- Ghi Python, Ultralytics, PyTorch, CUDA/GPU, seed, epoch, batch, image size và optimizer.
- Lưu URL, version và license của hai dataset Roboflow.
- Tạo manifest số ảnh, box, negative theo split và class.
- Đối chiếu chênh lệch inventory local với số liệu trong README Roboflow.
- Kiểm tra exact duplicate, perceptual duplicate và leakage giữa train/validation/test.
- Ghi rõ `training/train.py` là local/reference scaffold nếu chưa thay bằng cấu hình tái lập Kaggle.

Điều kiện hoàn thành:

- Hai checkpoint có hash bất biến và có ít nhất hai bản sao.
- Có tài liệu hoặc notebook mô tả đúng cấu hình Kaggle đã dùng.
- Mọi số liệu dataset trong báo cáo khớp manifest hoặc được giải thích rõ.
- Không có augmented derivative hoặc duplicate không được ghi nhận trong test benchmark.

### P1 - Xây benchmark chung

Mục tiêu: tạo một validation/test protocol giống hệt nhau cho A và B.

Công việc:

- Dùng cùng một phiên bản Ultralytics để load cả hai checkpoint.
- Dùng validation chung để chọn confidence threshold; không tune trên test.
- Dùng test chung cho lần đánh giá cuối cùng.
- Lấy `datasets/Baseline_B_yolov8/test` làm ứng viên ban đầu vì chứa 12 lớp và negative images, sau đó audit leakage trước khi khóa.
- Bổ sung ảnh held-out nếu một lớp có dưới 30 object trong test.
- Mở rộng target-free/OOD set lên tối thiểu 100 ảnh để đo false positives đáng tin cậy.
- Gắn ground truth cho năm ảnh challenge hoặc ghi manifest rõ ảnh positive/negative.
- Đổi đúng phần mở rộng hoặc re-encode năm ảnh đang mang đuôi `.png` nhưng có nội dung JPEG.
- Cố định manifest và checksum benchmark sau khi hoàn tất.

Điều kiện hoàn thành:

- A và B nhận đúng cùng image bytes và annotations.
- Mỗi lớp có số mẫu test đủ để đọc per-class AP.
- Test set không chứa ảnh nguồn hoặc biến thể augmentation từ train.
- Benchmark có positive, multi-object, small-object, occlusion và target-free cases.

### P2 - Đánh giá A/B và chọn model

Mục tiêu: chọn model bằng số liệu chung thay vì native validation metrics.

Công việc:

- Sửa `test_model/run_test_ab.py` để neo đường dẫn theo `Path(__file__)` và nhận model/data/output qua CLI.
- Đánh giá cùng `imgsz=640`, NMS settings, runtime, hardware và warm-up.
- Xuất overall và per-class precision, recall, F1, AP50, AP50-95.
- Xuất confusion matrix, PR curve, F1 curve và bảng lỗi theo class.
- Đo false-positive image rate và FP/image trên negative set.
- Đo p50/p95 latency, throughput, RAM/VRAM và kích thước checkpoint.
- Quét confidence threshold trên validation, sau đó khóa threshold trước khi mở test result.
- Lưu kết quả dạng JSON/CSV cùng ảnh định tính của cả A và B.
- Nếu cần tuyên bố vượt trội, dùng paired bootstrap confidence interval trên benchmark chung.

Quy tắc chọn đề xuất:

1. Ưu tiên mAP50-95 trên validation/test chung.
2. Nếu chênh lệch mAP50-95 nhỏ hơn `0.01`, ưu tiên model có FP/image thấp hơn trên negative set.
3. Nếu vẫn tương đương, ưu tiên recall và p95 latency phù hợp trải nghiệm ứng dụng.
4. Chỉ model thắng benchmark chung mới được cài dưới tên triển khai `best.pt`.

Điều kiện hoàn thành:

- Có một bảng A/B chung, per-class metrics và machine-readable results.
- Model được chọn bằng quy tắc đã công bố trước.
- Năm ảnh challenge chỉ được dùng bổ sung định tính, không thay thế benchmark có nhãn.

### P3 - Controlled ablation, chỉ thực hiện khi cần

Mục tiêu: chỉ ra tác động riêng của augmentation hoặc dữ liệu bổ sung nếu báo cáo muốn đưa ra kết luận nhân quả.

Hai model hiện tại thay đổi đồng thời nhiều yếu tố: offline augmentation, số lượng Phở/Xôi, hard negatives và validation distribution. Vì vậy A/B hiện tại là **system comparison**, không phải controlled augmentation ablation.

Nếu chỉ cần chứng minh pipeline cải tiến hoạt động tốt hơn, có thể bỏ qua P3 và diễn đạt đúng giới hạn.

Nếu cần kết luận riêng về augmentation, các arm phải dùng cùng raw split, base weights, Ultralytics version, epoch, batch, optimizer và seed. Thiết kế tích lũy đề xuất:

| Arm | Dữ liệu | Offline augmentation | Online YOLO augmentation | Hard negatives |
|---|---|---|---|---|
| A0 | Dataset gốc | Không | Tắt toàn bộ | Không |
| A1 | Dataset gốc | Không | Mặc định | Không |
| A2 | Dataset gốc | 3x | Mặc định | Không |
| A3 | Dataset gốc + Phở/Xôi bổ sung | 3x | Mặc định | Không |
| A4 | Dataset gốc + Phở/Xôi bổ sung | 3x | Mặc định | Có |

A1 tương ứng gần nhất với Baseline A hiện tại; A4 tương ứng gần nhất với Baseline B hiện tại. Mỗi arm nên chạy ít nhất ba seed nếu dùng để kết luận thống kê.

Điều kiện hoàn thành:

- Mỗi cặp arm liền kề chỉ thay đổi một yếu tố.
- Báo cáo mean/std hoặc confidence interval thay vì một lần train duy nhất.
- Nếu không thực hiện P3, báo cáo không tuyên bố augmentation là nguyên nhân duy nhất tạo ra khác biệt.

### P4 - Tích hợp model 12 lớp vào app

Mục tiêu: thay Demo Mode bằng inference thật và đồng bộ toàn bộ data contract.

Công việc:

- Thêm raw-label adapter đúng bảng 12 lớp ở mục 4.
- Cập nhật `config.FOOD_CLASSES`, display names và emoji map.
- Bổ sung năm món còn thiếu trong `data/nutrition_db.json` với khẩu phần, calo, macro và nguồn tham khảo.
- Loại hoặc tách ba món cũ không có trong checkpoint.
- Cập nhật `training/dataset.yaml`, collection queries, README và UI sang ontology 12 lớp.
- Thêm startup validation so sánh checkpoint names, adapter, config và nutrition DB.
- Cài model được chọn tại `models/weights/best.pt` hoặc chuyển model path thành cấu hình tường minh có checksum.
- Hiển thị lỗi rõ nếu checkpoint sai lớp; không tự chuyển sang random demo khi production được cấu hình dùng model thật.
- Kiểm tra mỗi lớp tạo đúng display name, HITL slider và nutrition totals.

Điều kiện hoàn thành:

- Cả 12 raw labels ánh xạ bijective sang 12 canonical IDs.
- Cả 12 canonical IDs có bản ghi dinh dưỡng hợp lệ.
- App status xác nhận model thật được load.
- Một ảnh target hợp lệ không còn bị trả về danh sách rỗng do mismatch tên lớp.

### P5 - Kiểm thử tự động và kiểm thử hệ thống

Mục tiêu: có release gate trả exit code đúng và bao phủ luồng chính.

Công việc:

- Chuyển các phép tính BMI/BMR/TDEE/goal/macro thành unit tests có assertion.
- Thêm contract test cho 12 class, raw-label adapter và nutrition DB.
- Thêm deterministic model smoke test bằng fixture có ground truth.
- Kiểm tra no-detection, unknown label, duplicate dishes và nhiều box cùng lớp.
- Kiểm tra slider tại `0.25x`, `1.0x`, `3.0x` và tổng dinh dưỡng.
- Kiểm tra ảnh hỏng, sai định dạng, ảnh lớn và ảnh không có món ăn.
- Kiểm tra thiếu/sai API key, lỗi mạng LLM và sample-advice fallback.
- Kiểm tra lưu, đọc, gộp và xóa lịch sử.
- Sửa `test_imports.py` để dùng đúng chuỗi tiếng Việt và trả non-zero khi có lỗi, hoặc thay bằng test suite chuẩn.
- Thêm một lệnh kiểm thử duy nhất cho release.

Điều kiện hoàn thành:

- Test command trả non-zero khi có test thất bại.
- Pure-logic tests không cần model hoặc API key.
- Model smoke test dùng đúng checkpoint được chọn.
- Luồng upload -> detection -> HITL -> nutrition -> advice -> history được smoke-test end to end.

### P6 - Báo cáo và khả năng tái lập

Mục tiêu: mọi tuyên bố trong báo cáo truy được về artifact và kết quả thực nghiệm.

Công việc:

- Cập nhật báo cáo từ 10 lớp/Colab sang 12 lớp/Kaggle.
- Phân biệt native validation metrics và common benchmark metrics.
- Mô tả đúng offline và online augmentation.
- Trình bày dataset class distribution, hard negatives và quy trình chống leakage.
- Thêm bảng overall/per-class A/B, confusion matrix, PR/F1 curves và latency.
- Thêm ca đúng, sai class, missed detection, false positive và OOD.
- Ghi rõ giới hạn HITL: model không ước lượng chính xác khối lượng từ ảnh 2D.
- Ghi nguồn và giả định cho dinh dưỡng của cả 12 món.
- Ghi checksum checkpoint, dataset manifest, môi trường Kaggle và benchmark command.
- Đồng bộ `README.md`, `training/README.md`, `PLAN.md` và nội dung trong app.

Điều kiện hoàn thành:

- Không còn tuyên bố 10 lớp, Colab hoặc no-augmentation tuyệt đối không đúng thực tế.
- Không gọi A/B là causal augmentation ablation nếu P3 chưa hoàn tất.
- Mọi bảng số liệu có file kết quả hoặc manifest tương ứng.
- Báo cáo nêu rõ model nào được triển khai và vì sao.

### P7 - Deployment, release và cleanup

Mục tiêu: một clean clone có thể lấy đúng model, chạy an toàn và khôi phục được.

Công việc:

- Chọn cơ chế phân phối checkpoint: Git LFS, release asset hoặc model registry.
- Tải và xác minh SHA-256 trước khi dùng checkpoint từ xa.
- Pin dependency versions đã benchmark, đặc biệt Ultralytics, PyTorch, Streamlit và LLM SDK.
- Kiểm tra Gemini SDK/model hiện còn được hỗ trợ trước release.
- Cấu hình Streamlit production thay vì ép `localhost` và `headless=false`.
- Dùng secrets/environment variables; không commit API key.
- Thay `data/meal_history.json` dùng chung bằng storage theo user/session hoặc tắt persistence trên public demo.
- Đo CPU latency trên target deployment và đặt giới hạn upload.
- Thực hiện production smoke test cho mọi page.
- Backup checkpoint, dataset, notebook Kaggle và báo cáo trước khi cleanup file local.
- Xóa cache, network-test artifacts, spent migration scripts và output tạm sau khi được xác nhận.
- Ghi release version, model hash, benchmark result và rollback artifact.

Điều kiện hoàn thành:

- Clean clone lấy đúng model và khởi động không dùng randomized Demo Mode.
- Không có secret trong repository.
- Người dùng không đọc được lịch sử của người dùng khác.
- Có URL demo, model hash và phương án rollback.

## 7. Definition of Done

Dự án chỉ được xem là hoàn tất khi đáp ứng toàn bộ điều kiện sau:

1. A và B đã được đánh giá trên cùng validation/test benchmark đã khóa.
2. Quyết định chọn model được ghi bằng common metrics, không dựa riêng vào native validation.
3. Mười hai raw checkpoint labels ánh xạ đầy đủ sang 12 canonical IDs.
4. Mười hai canonical IDs có nutrition records và nguồn tham khảo hợp lệ.
5. App chạy inference thật bằng model được chọn, không phải randomized Demo Mode.
6. Luồng upload -> detection -> HITL -> nutrition -> advice -> history vượt qua release test.
7. Báo cáo mô tả đúng Kaggle, dataset, augmentation, benchmark và giới hạn thực nghiệm.
8. Checkpoint, Kaggle notebook, dataset manifest và benchmark results có backup độc lập.
9. Clean deployment tải đúng checkpoint theo checksum và không lộ secret hoặc lịch sử dùng chung.

## 8. Rủi ro và nguyên tắc quyết định

| Rủi ro | Cách xử lý |
|---|---|
| Data leakage do ảnh augmentation hoặc duplicate | Audit exact/perceptual hashes trước khi khóa benchmark |
| B có mAP50 cao hơn nhưng mAP50-95 thấp hơn trong native metrics | Chỉ quyết định bằng common benchmark và error analysis |
| Model labels không khớp app | Raw-label adapter + startup contract validation |
| Năm món mới thiếu dữ liệu dinh dưỡng | Chỉ thêm khi có nguồn và khẩu phần chuẩn rõ ràng |
| Overfitting hoặc train quá lâu | Theo dõi validation curve; B hiện đạt đỉnh khoảng epoch 42 |
| Test challenge quá nhỏ | Dùng challenge set cho định tính, dùng labeled benchmark cho định lượng |
| Artifact bị mất vì gitignored/untracked | Backup ngoài Git và lưu checksum/manifest |
| Public history làm lộ dữ liệu giữa người dùng | Storage theo user/session hoặc không persist trên public demo |
| Dependency/model API thay đổi | Pin phiên bản và chạy release smoke test trên môi trường sạch |

## 9. Thứ tự ưu tiên tiếp theo

1. Backup checkpoint, benchmark, notebook và báo cáo theo checksum.
2. Mở rộng negative/OOD benchmark và các lớp dưới 30 mẫu nếu còn thời gian.
3. Hoàn thiện automated tests, history privacy và LLM runtime theo P5.
4. Đồng bộ báo cáo cuối và chuẩn bị deployment theo P6-P7.

## 10. Kế hoạch thực thi hoàn thiện sản phẩm

### 10.1 Quyết định phạm vi

- Khóa model triển khai là `Baseline B` tại `models/weights/best_baseline_B.pt` với SHA-256 trong `config.py`.
- Giữ A0, A và B cùng toàn bộ kết quả trong `test_model/` làm bằng chứng cho báo cáo; không xóa hoặc train đè các artifact này.
- Không mở thêm lớp món ăn, tính năng lớn hoặc thí nghiệm train mới trong giai đoạn hoàn thiện.
- Chỉ quay lại data/model nếu một lỗi lặp lại làm hỏng demo, ví dụ một lớp không nhận diện được trên ảnh kiểm thử đại diện. Mọi thay đổi như vậy phải được benchmark lại và ghi vào báo cáo.

### 10.2 Thứ tự thực hiện

Các phase dưới đây được thực hiện tuần tự. Tổng khối lượng khoảng 10-12 ngày làm việc, phù hợp cho phần còn lại của một đồ án 9 tuần.

| Phase | Thời lượng | Mục tiêu | Kết quả đầu ra |
|---|---:|---|---|
| A. Khóa baseline | 1 ngày | Bảo toàn đúng artifact và trạng thái mã nguồn | Backup có checksum, phạm vi đã chốt |
| B. Chạy ổn định | 1-2 ngày | App khởi động trên môi trường sạch với model thật | Smoke check và toàn bộ page chạy được |
| C. Hoàn thiện luồng người dùng | 2-3 ngày | Người dùng đi hết luồng mà không gặp trạng thái mơ hồ hoặc lộ dữ liệu | Luồng sản phẩm hoàn chỉnh |
| D. Release gate | 3 ngày | Kiểm thử các logic và luồng quan trọng | Một lệnh test có exit code chính xác |
| E. Báo cáo và demo | 3 ngày | Có thể chứng minh, trình diễn và triển khai lại kết quả | Báo cáo, slide, kịch bản demo, release checklist |

### Phase A - Khóa baseline và artifact

- [x] Sao lưu checkpoint A0/A/B, benchmark, notebook Kaggle, dataset và báo cáo lên Google Drive; người dùng xác nhận hoàn tất ngày 2026-08-06.
- [x] Lưu SHA-256 checkpoint B và vị trí backup Google Drive trong `PROGRESS.md`; chưa tải lại bản cloud để xác minh hash độc lập.
- [x] Rà soát file untracked; chỉ đưa source, tài liệu và benchmark metadata nhỏ cần thiết vào Git.
- [x] Không đưa API key, dataset lớn, checkpoint lớn hoặc runtime history vào Git.

**Hoàn thành khi:** Có thể khôi phục đúng checkpoint B và kết quả benchmark ngay cả khi máy hiện tại bị mất.

### Phase B - Ổn định môi trường và runtime

- [x] Tạo `.venv311` với Python 3.11.9, cài `pip install -r requirements.txt` và kiểm tra dependency không xung đột.
- [x] Sửa mọi lỗi import; `numpy` đã được cài và `utils/nutrition.py` cùng `utils/visualization.py` hoạt động.
- [x] Chạy `python test_imports.py`; lệnh pass và trả exit code khác 0 khi có lỗi.
- [x] Khởi động Streamlit bằng Python 3.11, health endpoint trả `ok`, và kiểm tra render đủ các trang `app.py`, phân tích ảnh, lịch sử, hồ sơ và đánh giá model.
- [x] Xác nhận app tải `Baseline B` thật, checksum hợp lệ, `ENABLE_RANDOM_DEMO` không bật và inference ảnh test trả về detection hợp lệ.

**Hoàn thành khi:** Một môi trường sạch chạy được app mà không cần sửa tay dependency hay thay checkpoint.

### Phase C - Hoàn thiện luồng người dùng

Luồng cần được kiểm tra và hoàn thiện theo đúng thứ tự:

```text
Hồ sơ -> Upload/camera -> YOLO Baseline B -> Mapping 12 lớp
-> HITL chỉnh khẩu phần -> Tổng dinh dưỡng -> Tư vấn LLM/fallback
-> Lưu lịch sử -> Xem thống kê 7 ngày
```

- [x] Kiểm tra ảnh có một món, nhiều món, không có món, ảnh sai định dạng và ảnh quá lớn.
- [x] Kiểm tra thông báo khi checkpoint thiếu/sai, không nhận diện được món, API key không có hoặc LLM lỗi mạng.
- [x] Kiểm tra slider tại `0.25x`, `1.0x`, `3.0x`; tổng calo và macro thay đổi đúng theo khẩu phần.
- [x] History bản public chỉ lưu trong Streamlit session; không đọc/ghi `data/meal_history.json` dùng chung giữa người dùng.
- [ ] Kiểm tra giao diện desktop và điện thoại, nhất là upload, bảng dinh dưỡng, tư vấn dài và biểu đồ.

Thứ tự triển khai phần còn lại của Phase C:

1. **C1 - Input ảnh:** kiểm tra JPG/PNG/WEBP hợp lệ, file hỏng, ảnh lớn, EXIF rotation và ảnh không chứa món hỗ trợ.
2. **C2 - Inference:** dùng fixture một món, nhiều món và negative/OOD; ghi detection, confidence, thời gian và thông báo UI.
3. **C3 - HITL:** kiểm tra `0.25x`, `1.0x`, `3.0x`, nhiều box cùng lớp và tổng calo/macro.
4. **C4 - LLM:** kiểm tra không có key, provider/key không hợp lệ và lỗi mạng; app phải fallback hoặc báo lỗi rõ mà không mất meal state.
5. **C5 - Responsive:** kiểm tra desktop và điện thoại qua HTTPS, tập trung upload/camera, bảng, tư vấn dài và biểu đồ.

Mỗi test case phải được ghi vào `PROGRESS.md` với input, expected result, actual result và bằng chứng/lệnh kiểm tra.

**Hoàn thành khi:** Người dùng mới có thể đi hết luồng trên mà không cần biết cấu trúc dự án hoặc chỉnh file cấu hình.

### Phase D - Release gate và kiểm thử

- [ ] Thêm test có assertion cho BMI, BMR, TDEE, mục tiêu calo và tính macro.
- [ ] Thêm contract test cho 12 lớp: checkpoint labels, `MODEL_CLASS_MAP`, `FOOD_CLASSES`, display map và `nutrition_db.json`.
- [ ] Thêm model smoke test xác định với ảnh fixture có kết quả mong đợi; không dùng demo ngẫu nhiên.
- [ ] Kiểm thử no-detection, unknown label, nhiều box cùng lớp, món trùng và lịch sử rỗng.
- [ ] Kiểm thử lưu/đọc/xóa history theo chiến lược privacy đã chọn.
- [ ] Chọn một lệnh release duy nhất, ví dụ `python -m pytest`, và chỉ release khi lệnh này pass.

**Hoàn thành khi:** Luồng `upload -> detection -> HITL -> nutrition -> advice -> history` có kiểm thử và lỗi kiểm thử làm command thất bại rõ ràng.

### Phase E - Báo cáo, demo và đóng gói

- [ ] Đồng bộ báo cáo, `README.md`, `training/README.md` và dashboard theo 12 lớp, Kaggle và Baseline B.
- [ ] Trình bày A0/A/B là so sánh hệ thống; không kết luận augmentation là nguyên nhân duy nhất nếu không thực hiện P3.
- [ ] Chèn bảng benchmark chung, metric theo lớp, ví dụ đúng/sai, false positive và giới hạn của HITL vào báo cáo.
- [ ] Thay toàn bộ placeholder về repository, sinh viên, MSSV, giáo viên hướng dẫn và URL deploy.
- [ ] Viết kịch bản demo 5 phút: hồ sơ, một ảnh nhận diện tốt, chỉnh khẩu phần, tư vấn, lịch sử, dashboard A/B, giới hạn hệ thống.
- [ ] Chạy clean-clone/production smoke test, xác nhận secret không nằm trong Git và checkpoint tải/kiểm tra hash đúng.

**Hoàn thành khi:** Có URL hoặc cách chạy cục bộ lặp lại được, báo cáo truy được mọi số liệu, và demo có phương án dự phòng khi mạng/LLM lỗi.

### 10.3 Việc bắt đầu ngay

1. Hoàn tất Phase C bằng test ảnh biên, HITL, LLM fallback và giao diện điện thoại.
2. Ghi từng test case và kết quả vào `PROGRESS.md` để dùng trong báo cáo.
3. Sau khi Phase C ổn định, chuyển sang Phase D và thiết lập release gate tự động.

---

*Phiên bản: 2.4 | Cập nhật: 2026-08-06 | Trạng thái: Phase A-B hoàn tất; Phase C đang kiểm thử và hoàn thiện luồng người dùng.*
