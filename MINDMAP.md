# NutriVision Mind Map

```mermaid
mindmap
  root((NutriVision))
    Mục tiêu
      Nhận diện 12 món ăn Việt Nam
      Tính dinh dưỡng theo khẩu phần
      Tư vấn cá nhân hóa
      Theo dõi lịch sử trong phiên
    Điều hướng
      Trang chủ
        Hero và giới thiệu luồng
        Hướng dẫn bắt đầu
        Trạng thái model LLM nutrition DB
      Hồ sơ
        Thông tin cơ bản
          Tên tuổi giới tính
          Chiều cao cân nặng
        Mức vận động
        Mục tiêu sức khỏe
        Kết quả cá nhân
          BMI và phân loại
          BMR TDEE calo mục tiêu
          Macro mục tiêu
        API tạm trong session
          OpenAI gpt-4o-mini mặc định
          Google AI Studio Gemini hoặc Gemma
          Cảnh báo dữ liệu gửi tới LLM
      Phân tích ảnh
        Bước 1 chọn ảnh
          Upload JPG PNG WEBP
          Camera điện thoại
          Preview và thông tin ảnh
        Bước 2 nhận diện
          YOLOv8n Baseline B
          12 lớp món ăn
          Bounding box và confidence
          No detection guidance
        Bước 3 HITL khẩu phần
          Một slider cho mỗi box
          0.25x đến 3x
          Món trùng vẫn chỉnh riêng
          Giới hạn ảnh 2D không đo được khối lượng
        Tóm tắt dinh dưỡng
          Tổng calo và macro
          Gauge donut progress chart
          Bảng chi tiết món ăn
        Tư vấn AI
          Dùng hồ sơ và bữa ăn hiện tại
          Stream Markdown
          Fallback phân tích mẫu khi thiếu key
          Lỗi mạng không mất meal state
        Lưu lịch sử
          Chỉ browser session hiện tại
      Lịch sử
        Empty state và ví dụ biểu đồ
        Chỉ số hôm nay
        Calo 7 ngày
        Danh sách bữa ăn
        Macro tuần
        Xóa session history
      Đánh giá model
        Benchmark A0 A B
        Baseline B triển khai
        Metric overall và per class
        Giới hạn benchmark
    Dữ liệu và state
      Session state
        user profile
        detections annotated image
        portion sliders meal nutrition
        LLM runtime key advice
        meal history
      Persistent files
        nutrition DB 12 món
        checkpoint Baseline B checksum
        benchmark CSV frozen
      Không persistent
        API key nhập trên UI
        Meal history của người dùng
    Luồng chính
      Onboarding
        Trang chủ
        Hồ sơ
        Phân tích ảnh
      Meal analysis
        Ảnh
        Detection
        HITL
        Nutrition
        Advice
        History
    AI advice
        Chọn provider và model
        OpenAI gpt-4o-mini là demo chính
        Có key gọi API
        Không key sample advice
        Lỗi API message an toàn
      Mobile demo
        Ngrok HTTPS
        Mở link điện thoại
        Camera upload touch responsive
    Thiết kế UI cần ưu tiên
      Progressive disclosure
        Chỉ hiện bước tiếp theo khi đủ dữ liệu
        Giữ kết quả đã có khi LLM lỗi
      Mobile first
        Camera và upload thao tác một tay
        Slider đủ lớn dễ kéo
        Bảng có cuộn ngang
        Chart và nội dung dài không tràn
      Tin cậy và minh bạch
        Confidence detection
        Giới hạn ước lượng khẩu phần
        Nguồn sample advice hay AI thật
        Cảnh báo không thay thế bác sĩ
      Privacy
        History chỉ trong session
        API key tạm thời
        Nêu rõ dữ liệu gửi tới LLM
      Feedback state
        Loading model detection advice
        Success saved profile meal
        Error invalid image model API
        Empty no upload no history no detection
    Kỹ thuật và release
      OpenAI
        gpt-4o-mini mặc định qua env
      Google GenAI SDK
        Google là phương án thay thế
      Pytest release gate
        Logic contracts images history LLM mock
        AppTest 5 pages
        Baseline B smoke test
        Live LLM optional
      Release command
        python -m pytest -q
```

## UI Flow Tóm Tắt

```mermaid
flowchart LR
    A[Trang chủ] --> B[Hồ sơ]
    B --> C[Chọn ảnh hoặc camera]
    C --> D[YOLO Baseline B]
    D -->|Có detection| E[HITL khẩu phần]
    D -->|Không có detection| C
    E --> F[Tổng dinh dưỡng và biểu đồ]
    F --> G[Tư vấn AI hoặc mẫu]
    F --> H[Lưu lịch sử session]
    H --> I[Dashboard lịch sử]
```

## Ràng Buộc Thiết Kế

- Không yêu cầu API key để hoàn thành luồng demo; dùng sample advice có nhãn khi thiếu key.
- Không để AI tự quyết định khẩu phần; người dùng luôn chỉnh được từng detection.
- Không lưu history hoặc API key sang phiên trình duyệt khác.
- Tối ưu các trạng thái `empty`, `loading`, `error` và `success` trước khi thêm hiệu ứng trang trí.
