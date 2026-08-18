# Triển khai NutriVision

Tài liệu này mô tả cách deploy bản demo trên Streamlit Community Cloud và cách
cập nhật ứng dụng sau mỗi lần sửa source code.

## 1. Thành phần đã được chuẩn bị trong repository

- `requirements.txt` chỉ chứa dependency runtime của ứng dụng.
- `requirements-dev.txt` chứa test, ngrok, training và data collection.
- `.streamlit/config.toml` không còn khóa server vào `localhost`.
- `models/weights/best_baseline_B.pt` được phép đưa lên Git. App vẫn kiểm tra
  SHA-256 trước khi inference.
- Hai ảnh fixture của release gate được phép đưa lên Git; các ảnh benchmark còn
  lại vẫn bị loại bỏ.
- `.env`, Streamlit secrets, database local, private key, dataset, report và
  checkpoint thử nghiệm vẫn bị `.gitignore` loại bỏ.

## 2. Kiểm tra trước khi push

Môi trường chỉ chạy app:

```bash
pip install -r requirements.txt
```

Môi trường phát triển và release test:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Kiểm tra danh sách thay đổi trước khi commit:

```bash
git status
git diff
```

Tuyệt đối không thêm `.env`, `secrets.toml`, service-role key, dataset hoặc thư
mục virtual environment vào commit.

## 3. Deploy lần đầu

1. Push source code, checkpoint production và hai fixture lên nhánh `main`.
2. Đăng nhập `https://share.streamlit.io` bằng GitHub.
3. Chọn repository `Minhmaxxx/DoAn`, nhánh `main`, entrypoint `app.py`.
4. Trong Advanced settings, chọn Python 3.11.
5. Thêm secret ở cấp gốc bằng TOML, vì `config.py` đọc các giá trị này qua biến
   môi trường:

```toml
LLM_PROVIDER = "openai"
OPENAI_API_KEY = "thay-bằng-key-thật"
OPENAI_MODEL = "gpt-4o-mini"
ENABLE_RANDOM_DEMO = "false"
```

Không đưa `NGROK_AUTHTOKEN` lên Streamlit Cloud. Ngrok chỉ dùng để mở tunnel
tạm thời từ máy local.

## 4. Tự động cập nhật

Streamlit Community Cloud theo dõi commit trên GitHub. Sau khi sửa code:

```bash
python -m pytest -q
git add <các-file-đã-kiểm-tra>
git commit -m "feat: mô tả thay đổi"
git push origin main
```

Bản deploy sẽ tự rebuild. File mới chỉ tồn tại trên máy local, kể cả checkpoint,
sẽ không xuất hiện trên cloud nếu chưa được commit và push.

## 5. Việc phải làm thủ công

- Đăng nhập GitHub và Streamlit Community Cloud.
- Kiểm tra repository có được phép cho Streamlit truy cập hay không.
- Chọn Python 3.11 trong Advanced settings.
- Nhập LLM secret trong giao diện Streamlit Cloud.
- Sau khi tích hợp tài khoản, tạo Supabase project và nhập các giá trị theo
  `STORAGE_PLAN.md`.
- Kiểm tra app trên URL public và trên một điện thoại thật.
