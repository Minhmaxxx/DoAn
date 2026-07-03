# NutriVision — Hệ thống Trợ lý Tư vấn Dinh dưỡng Cá nhân hóa

> **Đồ án Tốt nghiệp — Ngành Khoa học Máy tính** 
> *Personalized Nutrition Advisory System combining Computer Vision (YOLOv8) and Large Language Models*

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?logo=streamlit)](https://streamlit.io)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple)](https://ultralytics.com)
[![Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-orange)](https://ai.google.dev)

---

## Tổng quan

**NutriVision** là một web application tích hợp Computer Vision và AI ngôn ngữ để giúp người dùng:

1. **Nhận diện tự động** các món ăn Việt Nam từ ảnh chụp
2. **Tinh chỉnh khẩu phần** bằng cơ chế Human-in-the-Loop (HITL) 
3. **Nhận tư vấn dinh dưỡng** cá nhân hóa từ AI (Gemini/GPT)
4. **Theo dõi lịch sử** ăn uống và xu hướng dinh dưỡng

---

## Kiến trúc Hệ thống

```
Ảnh đầu vào → YOLOv8n Detection → HITL Slider → Calorie Calculation
                                                           ↓
User Biometrics (BMI, TDEE) ────────────────→ Prompt Engineering → Gemini/GPT
                                                           ↓
                                              Lời khuyên dinh dưỡng (Tiếng Việt)
```

### Điểm nổi bật học thuật: Human-in-the-Loop (HITL)
AI không thể ước lượng chính xác thể tích món ăn từ ảnh 2D. Thay vì cố gắng giải quyết bài toán khó này, NutriVision sử dụng cơ chế HITL: sau khi nhận diện tên món, người dùng dùng **thanh trượt** để tinh chỉnh khẩu phần (0.25x đến 3.0x), giúp tính calo chính xác hơn với chi phí tương tác tối thiểu.

---

## Tech Stack

| Component | Technology |
|---|---|
| Web Framework | Streamlit 1.35+ |
| Object Detection | YOLOv8n (Ultralytics) |
| Transfer Learning | Google Colab + GPU T4 |
| Dataset Labeling | Roboflow |
| LLM (primary) | Google Google Gemini |
| LLM (backup) | OpenAI GPT-4o-mini |
| Visualization | Plotly Express |
| Deployment | Streamlit Community Cloud |

---

## Món ăn được hỗ trợ

| # | Món ăn | Calo chuẩn |
|---|---|---|
| 1 |  Phở bò | 425 kcal/tô |
| 2 |  Bún bò Huế | 480 kcal/tô |
| 3 |  Bún chả | 620 kcal/suất |
| 4 |  Cơm tấm sườn | 750 kcal/đĩa |
| 5 |  Bánh mì | 380 kcal/ổ |
| 6 |  Gỏi cuốn | 180 kcal/4 cuốn |
| 7 |  Nem rán | 320 kcal/5 cái |
| 8 |  Bánh cuốn | 320 kcal/đĩa |
| 9 |  Cháo lòng | 380 kcal/tô |
| 10 |  Xôi gà | 520 kcal/hộp |

---

## Cài đặt & Chạy

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/nutrivision.git
cd nutrivision

# Tạo virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Cài đặt dependencies
pip install -r requirements.txt
```

### 2. Cấu hình API Key

```bash
# Copy template và điền API key
copy .env.example .env
# Mở .env và nhập GEMINI_API_KEY của bạn
# Lấy miễn phí tại: https://aistudio.google.com
```

### 3. Chạy ứng dụng

```bash
streamlit run app.py
```

Truy cập: `http://localhost:8501`

---

## Huấn luyện Mô hình YOLOv8

> Xem hướng dẫn chi tiết tại [training/README.md](training/README.md)

```bash
# Thu thập dữ liệu
python training/data_collection.py --food all --count 350

# Sau khi gán nhãn trên Roboflow → Huấn luyện
python training/train.py
```

---

## Cấu trúc Dự án

```
nutrivision/
├── app.py                    # Entry point Streamlit
├── config.py                 # Global config
├── requirements.txt
├── PLAN.md                   # Kế hoạch 9 tuần
├── pages/
│   ├── 1_Phan_tich_anh.py   # Food detection + HITL
│   ├── 2_Lich_su.py         # Meal history
│   └── 3_Ho_so.py           # User profile
├── models/
│   ├── detector.py           # YOLOv8 wrapper
│   └── weights/              # Trained .pt files
├── utils/
│   ├── nutrition.py          # BMI, TDEE calculations
│   ├── llm.py                # Gemini/GPT integration
│   └── visualization.py      # Plotly charts
├── data/
│   └── nutrition_db.json     # 10 Vietnamese foods DB
├── training/
│   ├── train.py              # Training script
│   ├── data_collection.py    # Image scraper
│   └── dataset.yaml          # YOLOv8 dataset config
└── assets/
    └── style.css             # Custom dark theme CSS
```

---

## Demo Mode

Nếu chưa có file mô hình `models/weights/best.pt`, hệ thống tự động chuyển sang **Demo Mode** — sinh kết quả nhận diện mẫu để minh họa toàn bộ luồng UI mà không cần mô hình thực.

---

## Thông tin Đồ án

| Thông tin | Chi tiết |
|---|---|
| Sinh viên | [Tên của bạn] |
| MSSV | [Mã số sinh viên] |
| Giáo viên hướng dẫn | [Tên GVHD] |
| Trường | [Tên trường] |
| Năm học | 2025 – 2026 |

---

* 2026 NutriVision — Đồ án Tốt nghiệp*
