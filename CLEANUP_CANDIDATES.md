# Cleanup Candidates

Tài liệu này chỉ đánh dấu các mục cần xem xét. Không xóa artifact train, benchmark, checkpoint hoặc báo cáo trước khi có bản sao lưu đã kiểm tra checksum.

## Có thể xóa an toàn

- `__pycache__/` và mọi thư mục `*/__pycache__/`: bytecode Python sinh tự động.
- `test_model/benchmark_common_v1/labels.cache`: cache Ultralytics, tự tạo lại khi benchmark.
- `test_bing/`: năm ảnh tải thử từ crawler smoke test.
- `test_model/Ket_Qua_So_Sanh/Model_A/` và `test_model/Ket_Qua_So_Sanh/Model_B/`: output cũ của lần so sánh hai model; output ba model hiện dùng các thư mục `Baseline_A0/`, `Baseline_A/`, `Baseline_B/`.

## Script một lần, nên xóa sau khi xác nhận

- `remove_emojis.py`: migration rewrite toàn repository, không phải công cụ runtime.
- `rename_classes.py`: replacement hiện là no-op.
- `rename_xoi.py`: replacement và folder rename hiện là no-op.
- `test_crawler.py`: network probe, không phải automated test.
- `fetch_bing.py`: crawler riêng cho Phở/Xôi, trùng phần lớn chức năng `training/data_collection.py`; giữ đến khi provenance dữ liệu đã được ghi vào báo cáo.

## Bản sao trùng, chỉ xóa sau khi backup

- `KetQuaTrain/best_baseline_A0.pt`
- `KetQuaTrain/best_baseline_A.pt`
- `KetQuaTrain/best_baseline_B.pt`

Ba file trên trùng checksum với best checkpoint nằm trong thư mục train tương ứng và `test_model/weights_test/`. Giữ ít nhất hai bản sao độc lập trước khi dọn.

## Cần xác nhận thủ công

- `BaoCao_DoAn_old.docx`: báo cáo cũ; chỉ xóa sau khi báo cáo hiện tại đã được backup.
- Các file `last.pt` trong `KetQuaTrain/`: cần nếu muốn resume training.
- Các thư mục `Test_Samples*`, ảnh EDA và `Custom_Epoch_Overview*` trong `KetQuaTrain/`: có thể dùng trong báo cáo.
- `models/weights/best_baseline_B.pt`: checkpoint production, phải giữ.

## Phải giữ

- `test_model/benchmark_common_v1/` trừ `labels.cache`.
- `test_model/benchmark_results_common_v1/`.
- `test_model/build_common_benchmark.py`.
- `test_model/evaluate_common_benchmark.py`.
- `test_model/run_test_ab.py`.
- `test_model/weights_test/` và `test_model/anh_test/`.
- Ba thư mục provenance `KetQuaTrain/Ket_Qua_Do_An_Baseline_*`.
- `datasets/`, `notebooks/`, `BaoCao_DoAn.docx` và `AGENTS.md`.
