@echo off
:: NutriVision — Startup Script for Windows
:: Tự động kích hoạt môi trường ảo và chạy ứng dụng Streamlit

echo.
echo  ========================================
echo    NutriVision Startup - Trợ lý Dinh Dưỡng
echo  ========================================
echo.

:: Thiết lập bảng mã UTF-8 để hiển thị tiếng Việt không bị lỗi font
set PYTHONUTF8=1
chcp 65001 > nul

:: 1. Tự động kiểm tra và kích hoạt môi trường ảo (Virtual Environment)
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Phát hiện môi trường ảo tại .venv. Đang kích hoạt...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [INFO] Phát hiện môi trường ảo tại venv. Đang kích hoạt...
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] Không tìm thấy thư mục môi trường ảo (.venv hoặc venv).
    echo           Hệ thống sẽ thử chạy Streamlit bằng môi trường Python hệ thống (Global).
    echo.
)

:: 2. Kiểm tra file cấu hình .env
if not exist ".env" (
    echo [WARNING] Không tìm thấy file .env.
    echo           Hãy copy file .env.example thành .env và điền API keys.
    echo           Ứng dụng sẽ tự động chạy ở chế độ Demo (không có tư vấn LLM).
    echo.
)

:: 3. Chạy Streamlit
echo [INFO] Đang khởi động Streamlit tại http://localhost:8501 ...
echo [INFO] Nhấn Ctrl+C trong cửa sổ này để tắt ứng dụng.
echo.

:: Thử chạy trực tiếp lệnh streamlit
where streamlit >nul 2>nul
if %errorlevel% equ 0 (
    streamlit run app.py --server.port 8501
    goto end
)

:: Nếu không tìm thấy lệnh streamlit trực tiếp, thử chạy thông qua python -m streamlit
python -m streamlit run app.py --server.port 8501 >nul 2>nul
if %errorlevel% equ 0 (
    python -m streamlit run app.py --server.port 8501
    goto end
)

:: Nếu cả hai cách đều lỗi, hướng dẫn cài đặt
echo [ERROR] Không tìm thấy thư viện Streamlit trên máy của bạn.
echo.
echo Để khắc phục, vui lòng chọn một trong hai cách sau:
echo.
echo CÁCH 1 (Khuyên dùng - Dùng môi trường ảo):
echo   1. Mở PowerShell/CMD tại thư mục dự án và chạy:
echo      python -m venv .venv
echo   2. Kích hoạt môi trường ảo:
echo      .venv\Scripts\activate
echo   3. Cài đặt các thư viện cần thiết:
echo      pip install -r requirements.txt
echo   4. Chạy lại file run.bat này.
echo.
echo CÁCH 2 (Cài trực tiếp lên máy):
echo   1. Mở PowerShell/CMD tại thư mục dự án và chạy:
echo      pip install -r requirements.txt
echo   2. Chạy lại file run.bat này.
echo.

:end
pause
