# PLAN.md — Kế hoạch Thực hiện Đồ án Tốt nghiệp

## Tên đề tài
**"Hệ thống Trợ lý Tư vấn Dinh dưỡng Cá nhân hóa kết hợp Thị giác Máy tính và Mô hình Ngôn ngữ Lớn"**

> *Personalized Nutrition Advisory System using Computer Vision (YOLOv8) and Large Language Models*

---

## Thông tin Dự án

| Thuộc tính | Chi tiết |
|---|---|
| Người thực hiện | Solo (1 người) |
| Tổng thời gian | **9 tuần** |
| Framework chính | Streamlit (Python) |
| Mô hình CV | YOLOv8n (Ultralytics) |
| LLM API | Google Gemini / OpenAI GPT |
| Môi trường train | Google Colab (GPU T4) |
| Deploy target | Streamlit Community Cloud |

---

## Kiến trúc Hệ thống (System Architecture)

`
Ảnh đầu vào
     │
     ▼
YOLOv8n Inference (detect tên và vị trí món ăn)
     │
     ▼
Ánh xạ nutrition_db.json (lấy calo chuẩn theo khẩu phần 1x)
     │
     ▼
HITL Slider (người dùng điều chỉnh ratio 0.5x → 2.0x)
     │
     ▼
Tính toán Tổng Calo + Macronutrients (Carb / Protein / Fat)
     │
     ▼
Tổng hợp: Sinh trắc học (BMI, TDEE, Mục tiêu) + Thực đơn thực tế
     │
     ▼
Prompt Engineering → LLM API (Gemini / GPT)
     │
     ▼
Lời khuyên dinh dưỡng cá nhân hóa (Tiếng Việt, Markdown)
`

---

## Cấu trúc Thư mục Dự án

`
DoAn/
├── app.py                    # Streamlit main app (Entry point)
├── config.py                 # Global configurations
├── requirements.txt          # Python dependencies
├── .env.example              # API key template
├── .gitignore
├── README.md
├── PLAN.md                   # This file
│
├── pages/                    # Streamlit multi-page app
│   ├── 1_Phan_tich_anh.py   # Food detection + HITL
│   ├── 2_Lich_su.py         # Meal history and charts
│   └── 3_Ho_so.py           # User profile and biometrics
│
├── models/                   # AI model layer
│   ├── __init__.py
│   ├── detector.py          # YOLOv8 wrapper class
│   └── weights/             # Trained .pt model files (gitignored)
│
├── utils/                    # Utility modules
│   ├── __init__.py
│   ├── nutrition.py         # BMI, TDEE, BMR calculations
│   ├── llm.py               # LLM API integration
│   └── visualization.py     # Plotly charts for macros
│
├── data/                    # Data files
│   ├── nutrition_db.json    # Food nutrition database
│   └── sample_images/       # Test images for demo
│
├── training/                # YOLOv8 training scripts
│   ├── train.py             # Training script
│   ├── dataset.yaml         # Dataset config for Ultralytics
│   └── README.md            # Training instructions
│
└── assets/                  # Static assets
    └── style.css            # Custom Streamlit CSS
`

---

## Lịch trình 9 Tuần

| Tuần | Nội dung | Deliverable |
|---|---|---|
| 1-2 | Thu thập, gán nhãn dữ liệu 10 món ăn Việt Nam | Dataset Roboflow + nutrition_db.json |
| 3-4 | Huấn luyện YOLOv8n, đánh giá mAP50 >= 80% | Mô hình .pt đã train |
| 5   | Xây dựng Streamlit core + HITL slider | App chạy được detect + slider |
| 6   | Tích hợp LLM API + Prompt Engineering | Lời khuyên cá nhân hóa |
| 7   | Lịch sử bữa ăn, biểu đồ Plotly, tối ưu UI | Full feature app |
| 8   | Kiểm thử, xử lý edge cases, deploy | URL public |
| 9   | Viết báo cáo, làm slide, chuẩn bị bảo vệ | Báo cáo + Slide |

---

## Tech Stack

| Layer | Công nghệ | Lý do |
|---|---|---|
| Web Framework | Streamlit 1.35+ | FE+BE trong Python, deploy nhanh |
| Object Detection | Ultralytics YOLOv8n | Nhẹ, chạy trên CPU, API thân thiện |
| LLM | Google Google Gemini | Free tier, tiếng Việt tốt |
| LLM backup | OpenAI GPT-4o-mini | Backup |
| Data Labeling | Roboflow | Auto-label, augmentation |
| Training | Google Colab (T4 GPU) | Miễn phí |
| Visualization | Plotly Express | Biểu đồ interactive |
| Deploy | Streamlit Community Cloud | Miễn phí, từ GitHub |

---

*Phiên bản: 1.0 | Ngày tạo: 2026-07-03*
