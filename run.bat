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
    echo           Hệ thống sẽ chạy bằng môi trường Python hệ thống (Global).
    echo.
)

:: 2. Kiểm tra file cấu hình .env
if not exist ".env" (
    echo [WARNING] Không tìm thấy file .env.
    echo           Hãy copy file .env.example thành .env và điền API keys.
    echo           Ứng dụng sẽ tự động chạy ở chế độ Demo (không có tư vấn LLM).
    echo.
)

:: 3. Kiểm tra xem Streamlit có sẵn sàng không
echo [INFO] Đang kiểm tra thư viện Streamlit...

:: Thử kiểm tra lệnh streamlit toàn cục
where streamlit >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Tìm thấy lệnh streamlit. Đang khởi động ứng dụng...
    echo [INFO] Trình duyệt sẽ tự động mở tại http://localhost:8501
    echo [INFO] Nhấn Ctrl+C để dừng ứng dụng.
    echo.
    streamlit run app.py --server.port 8501
    goto end
)

:: Kiểm tra xem có thể import streamlit qua python không
python -c "import streamlit" >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Tìm thấy thư viện streamlit qua Python. Đang khởi động ứng dụng...
    echo [INFO] Trình duyệt sẽ tự động mở tại http://localhost:8501
    echo [INFO] Nhấn Ctrl+C để dừng ứng dụng.
    echo.
    python -m streamlit run app.py --server.port 8501
    goto end
)

:: Nếu cả hai cách đều lỗi, hướng dẫn cài đặt
echo [ERROR] Không tìm thấy thư viện Streamlit trên máy của bạn.
echo.
echo Vui lòng mở PowerShell hoặc CMD tại thư mục này và chạy lệnh sau để cài đặt:
echo   pip install -r requirements.txt
echo.
echo Sau khi cài đặt xong, hãy chạy lại file run.bat này.
echo.

:end
pause
