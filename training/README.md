# 📌 Hướng dẫn Huấn luyện Mô hình YOLOv8

## Tổng quan

Script này huấn luyện mô hình **YOLOv8n** (nano) bằng transfer learning trên bộ dữ liệu
10 món ăn Việt Nam do bạn tự thu thập và gán nhãn qua Roboflow.

---

## Yêu cầu hệ thống

| Thành phần | Tối thiểu | Khuyến nghị |
|---|---|---|
| GPU | Không bắt buộc (chậm) | NVIDIA ≥ 4GB VRAM |
| RAM | 8 GB | 16 GB |
| Python | 3.9+ | 3.11 |
| Môi trường | Máy cục bộ | **Google Colab (T4 GPU)** |

---

## Bước 1: Cài đặt thư viện

```bash
pip install ultralytics roboflow icrawler python-dotenv
```

---

## Bước 2: Thu thập ảnh (nếu chưa có dataset)

```bash
# Thu thập ảnh cho tất cả 10 món (~350 ảnh/món)
python training/data_collection.py --food all --count 350

# Hoặc thu thập từng món
python training/data_collection.py --food pho_bo --count 400
```

Sau đó upload thư mục `datasets/raw/` lên **Roboflow** để gán nhãn Bounding Box.

---

## Bước 3: Gán nhãn trên Roboflow

1. Tạo project mới tại [app.roboflow.com](https://app.roboflow.com)
2. Chọn task: **Object Detection**
3. Upload ảnh từ `datasets/raw/`
4. Gán nhãn với Bounding Box cho từng món ăn
5. Bật **Auto-Labeling** (YOLOv8 pretrained) để tăng tốc
6. Cấu hình Augmentation:
   - Rotation: ±15°
   - Brightness: ±25%
   - Mosaic: Bật
   - Flip: Horizontal
7. Generate version → Export → **YOLOv8 format**
8. Lấy code download snippet và lưu `ROBOFLOW_API_KEY` vào `.env`

---

## Bước 4: Chạy Training

```bash
# Full pipeline: download dataset + train + evaluate
python training/train.py

# Skip download (đã có dataset)
python training/train.py --skip-download --yaml datasets/nutrivision/data.yaml

# Chỉ evaluate model đã train
python training/train.py --eval-only --yaml datasets/nutrivision/data.yaml
```

---

## Bước 5: Deploy mô hình

Sau khi train xong, file `models/weights/best.pt` sẽ được tự động copy vào.
Khởi động lại Streamlit app để dùng mô hình thực:

```bash
streamlit run app.py
```

---

## Chỉ tiêu kỳ vọng

| Metric | Mục tiêu |
|---|---|
| mAP50 | ≥ 0.80 |
| Precision | ≥ 0.78 |
| Recall | ≥ 0.75 |
| Inference (CPU) | < 200ms/ảnh |

---

## Mẹo Training trên Google Colab

```python
# Cell 1: Mount Drive và clone repo
from google.colab import drive
drive.mount('/content/drive')
!git clone https://github.com/yourusername/nutrivision /content/nutrivision

# Cell 2: Cài dependencies
!pip install ultralytics roboflow python-dotenv

# Cell 3: Chạy training (T4 GPU)
import os
os.chdir('/content/nutrivision')
!python training/train.py
```

---

## Troubleshooting

**GPU OOM (Out of Memory):**
- Giảm `BATCH_SIZE` từ 16 xuống 8 hoặc 4

**mAP thấp (<70%):**
- Tăng số ảnh mỗi class lên ≥400
- Kiểm tra lại chất lượng bounding box labels
- Tăng `EPOCHS` lên 200

**Inference quá chậm trên CPU:**
- Export sang ONNX: `model.export(format='onnx')`
- Sử dụng bản `yolov8n` thay vì `yolov8s`
