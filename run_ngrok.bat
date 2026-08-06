@echo off
:: NutriVision - Start Streamlit and expose an ngrok HTTPS URL

set PYTHONUTF8=1
chcp 65001 > nul

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python -c "import streamlit, pyngrok" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Thieu dependency. Chay: pip install -r requirements.txt
    pause
    exit /b 1
)

python run_ngrok.py
if errorlevel 1 (
    echo.
    echo [ERROR] Khong the tao ngrok tunnel. Kiem tra NGROK_AUTHTOKEN trong .env.
)
pause
