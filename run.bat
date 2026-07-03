@echo off
:: NutriVision - Startup Script for Windows
:: Automatically activates virtual environment and runs Streamlit

echo.
echo  ========================================
echo    NutriVision Startup - Nutrition Assistant
echo  ========================================
echo.

:: Set UTF-8 encoding for Python
set PYTHONUTF8=1
chcp 65001 > nul

:: 1. Auto-detect and activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Found virtual environment at .venv. Activating...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [INFO] Found virtual environment at venv. Activating...
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] No virtual environment found - .venv or venv
    echo           The system will run using the global Python environment.
    echo.
)

:: 2. Check for .env file
if not exist ".env" (
    echo [WARNING] .env file not found.
    echo           Please copy .env.example to .env and fill in your API keys.
    echo           The application will run in Demo mode - without LLM advice.
    echo.
)

:: 3. Check if Streamlit is available
echo [INFO] Checking Streamlit library...

:: Check for global streamlit command
where streamlit >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Found streamlit command. Starting application...
    echo [INFO] The browser will open automatically at http://localhost:8501
    echo [INFO] Press Ctrl+C to stop the application.
    echo.
    streamlit run app.py --server.port 8501
    goto end
)

:: Check if streamlit can be imported via Python
python -c "import streamlit" >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Found streamlit library via Python. Starting application...
    echo [INFO] The browser will open automatically at http://localhost:8501
    echo [INFO] Press Ctrl+C to stop the application.
    echo.
    python -m streamlit run app.py --server.port 8501
    goto end
)

:: If both fail, print installation instructions
echo [ERROR] Streamlit library not found on your system.
echo.
echo Please open PowerShell or CMD in this directory and run the following command to install:
echo   pip install -r requirements.txt
echo.
echo After installation is complete, please run this run.bat file again.
echo.

:end
pause
