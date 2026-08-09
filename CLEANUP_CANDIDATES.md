# Cleanup Status

Không xóa artifact train, benchmark, checkpoint hoặc báo cáo khi chưa có backup độc lập. Người dùng xác nhận backup Google Drive đã hoàn tất ngày 2026-08-06.

## Đã xóa an toàn

- `.venv/` Python 3.10.6: đã được `.venv311/` thay thế, thu hồi khoảng 1.49 GiB.
- `__pycache__/` và mọi cache module: bytecode Python sinh tự động.
- `test_model/benchmark_common_v1/labels.cache`: cache Ultralytics, có thể tự tạo lại.
- `test_bing/`: ảnh tải thử từ crawler smoke test.
- `7.2.0`: output cài đặt pip bị ghi nhầm thành file.
- `remove_emojis.py`, `rename_classes.py`, `rename_xoi.py`: migration/no-op một lần.
- `test_crawler.py`: network probe, không phải automated test.

## Giữ có chủ đích

- `training/fetch_pho_xoi.py`: giữ đến Phase E vì ghi lại provenance thu thập bổ sung Phở/Xôi.
- `test_model/Ket_Qua_So_Sanh/`: giữ output định tính A0/A/B cho báo cáo.

## Bản sao checkpoint trùng

- `KetQuaTrain/best_baseline_A0.pt`
- `KetQuaTrain/best_baseline_A.pt`
- `KetQuaTrain/best_baseline_B.pt`

Ba file trên trùng checksum với checkpoint trong thư mục train và `test_model/weights_test/`. Hiện giữ lại vì tổng dung lượng nhỏ và hữu ích khi đối chiếu provenance.

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
