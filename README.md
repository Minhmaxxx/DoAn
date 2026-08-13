# NutriVision — Hệ thống Trợ lý Tư vấn Dinh dưỡng Cá nhân hóa

> **Đồ án Tốt nghiệp — Ngành Khoa học Máy tính** 
> *Personalized Nutrition Advisory System combining Computer Vision (YOLOv8) and Large Language Models*

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?logo=streamlit)](https://streamlit.io)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple)](https://ultralytics.com)
[![Google GenAI](https://img.shields.io/badge/LLM-Google%20GenAI-orange)](https://ai.google.dev)

---

## Tổng quan

**NutriVision** là một web application tích hợp Computer Vision và AI ngôn ngữ để giúp người dùng:

1. **Nhận diện tự động** các món ăn Việt Nam từ ảnh chụp
2. **Tinh chỉnh khẩu phần** bằng cơ chế Human-in-the-Loop (HITL) 
3. **Nhận tư vấn dinh dưỡng** cá nhân hóa từ AI (Gemini/Gemma/GPT)
4. **Theo dõi lịch sử** ăn uống và xu hướng dinh dưỡng

---

## Kiến trúc Hệ thống

```
Ảnh đầu vào → YOLOv8n Detection → HITL Slider → Calorie Calculation
                                                           ↓
User Biometrics (BMI, TDEE) ────────────────→ Prompt Engineering → Gemini/Gemma/GPT
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
| Transfer Learning | Kaggle GPU |
| Dataset Labeling | Roboflow |
| LLM (primary) | OpenAI GPT-4o-mini |
| LLM (alternative) | Google GenAI SDK, model Gemini hoặc Gemma trên AI Studio |
| Visualization | Plotly Express |
| Deployment | Streamlit Community Cloud |

---

## 12 lớp món ăn được hỗ trợ

| # | Món ăn | Calo tham khảo |
|---|---|---|
| 1 | Bánh mì | 380 kcal/ổ |
| 2 | Bánh tráng nướng | 380 kcal/bánh |
| 3 | Bánh xèo | 580 kcal/bánh lớn |
| 4 | Bún bò Huế | 480 kcal/tô |
| 5 | Bún đậu mắm tôm | 700 kcal/mẹt |
| 6 | Bún riêu | 480 kcal/tô |
| 7 | Bún thịt nướng | 550 kcal/tô |
| 8 | Cháo lòng | 380 kcal/tô |
| 9 | Cơm tấm | 750 kcal/đĩa |
| 10 | Gỏi cuốn | 180 kcal/4 cuốn |
| 11 | Phở | 425 kcal/tô |
| 12 | Xôi | 520 kcal/hộp |

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
# Mở .env, nhập OPENAI_API_KEY
# Hoặc để trống nếu chỉ muốn dùng nhận diện và tính dinh dưỡng
```

`LLM_PROVIDER` mặc định là `openai` với `OPENAI_MODEL=gpt-4o-mini`. Có thể chuyển
sang `google` và thay `GOOGLE_MODEL` bằng model Gemini/Gemma đúng như AI Studio
hiển thị mà không cần sửa source code. Không commit file `.env` hoặc API key.

Sau khi mở app, vào trang **Hồ sơ** để bật/tắt **Trợ lý dinh dưỡng AI** cho phiên
hiện tại. Khi tắt, ứng dụng không gửi hồ sơ hoặc dữ liệu bữa ăn đến OpenAI/Google;
nhận diện, tính dinh dưỡng và lịch sử vẫn hoạt động bình thường.

### 3. Chạy ứng dụng

```bash
python -m streamlit run app.py --server.port 8501
```

Truy cập: `http://localhost:8501`

Trên Windows, có thể chạy `run.bat`; launcher này ưu tiên môi trường `.venv311` và
bật UTF-8. Luồng khuyến nghị trong ứng dụng là: **Hồ sơ → Phân tích ảnh → bật trợ
lý nếu cần → Lịch sử**.

### Release test

```bash
python -m pytest -q
```

Lệnh trên chạy test logic, hợp đồng 12 lớp, ảnh đầu vào, history, LLM mock,
năm Streamlit page và smoke test Baseline B thật. Live API chỉ chạy khi đặt
`RUN_LIVE_LLM_TEST=1` và đã có API key cho provider đang chọn.

### Chạy trên điện thoại bằng ngrok

1. Tạo tài khoản miễn phí tại [ngrok.com](https://ngrok.com/).
2. Thêm `NGROK_AUTHTOKEN` vào `.env` theo mẫu `.env.example`, hoặc dán token vào prompt bảo mật khi launcher hỏi.
3. Chạy `run_ngrok.bat` trên Windows hoặc `python run_ngrok.py`.
4. Mở URL HTTPS được in sau dòng `LINK ĐIỆN THOẠI` trên điện thoại.

URL ngrok chỉ tồn tại khi cửa sổ launcher còn chạy. Đây là link công khai tạm thời; không chia sẻ link hoặc nhập API key nhạy cảm trên một phiên demo đã được chia sẻ.

Nếu launcher báo cổng `8501` đang được dùng, đừng mở thêm một instance. Quay lại cửa sổ app cũ và nhấn `Ctrl+C`; nếu không còn cửa sổ đó, PowerShell có thể tìm và dừng tiến trình bằng `Get-NetTCPConnection -LocalPort 8501 | Select-Object -ExpandProperty OwningProcess` rồi `Stop-Process -Id <PID>`. Hoặc đặt `STREAMLIT_PORT=8502` trong `.env` trước khi chạy `run_ngrok.py`.

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
│   ├── 3_Ho_so.py           # User profile
│   └── 4_Danh_gia_mo_hinh.py # Frozen A0/A/B benchmark
├── models/
│   ├── detector.py           # YOLOv8 wrapper
│   └── weights/              # Trained .pt files
├── utils/
│   ├── nutrition.py          # BMI, TDEE calculations
│   ├── llm.py                # Google GenAI/OpenAI integration
│   ├── images.py             # Decode, EXIF and image limits
│   ├── history.py            # Session history records
│   └── visualization.py      # Plotly charts
├── tests/                    # Pytest release suite
├── data/
│   └── nutrition_db.json     # 12 lớp món ăn, khẩu phần tham khảo
├── training/
│   ├── train.py              # Training script
│   ├── data_collection.py    # Image scraper
│   └── dataset.yaml          # YOLOv8 dataset config
└── assets/
    └── style.css             # Light health UI shared CSS
```

---

## Model triển khai

Ứng dụng dùng `models/weights/best_baseline_B.pt` và kiểm tra checksum cùng thứ tự 12 nhãn khi khởi động. Nếu checkpoint thiếu hoặc không hợp lệ, ứng dụng báo lỗi thay vì tự sinh detection ngẫu nhiên. `ENABLE_RANDOM_DEMO=true` chỉ dành cho phát triển giao diện.

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
