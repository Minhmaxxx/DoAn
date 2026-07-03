@echo off
:: NutriVision — Startup Script for Windows
:: Chạy script này để khởi động ứng dụng Streamlit

echo.
echo  ========================
echo    NutriVision Startup
echo  ========================
echo.

:: Set UTF-8 for Vietnamese characters
set PYTHONUTF8=1
chcp 65001 > nul

:: Check if .env exists
if not exist ".env" (
    echo [WARNING] .env file not found.
    echo           Copy .env.example to .env and add your API keys.
    echo           App will run in Demo mode without LLM advice.
    echo.
)

:: Launch Streamlit
echo Starting Streamlit app at http://localhost:8501 ...
echo Press Ctrl+C to stop.
echo.

streamlit run app.py --server.port 8501

pause
