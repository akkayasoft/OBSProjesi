@echo off
chcp 65001 >nul 2>&1
title OBS Projesi - Calistir

:: Sanal ortam kontrolu
if not exist "venv\Scripts\activate.bat" (
    echo [HATA] Sanal ortam bulunamadi! Once setup.bat calistirin.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo ============================================
echo   OBS Projesi baslatiliyor...
echo   http://localhost:5000
echo   Durdurmak icin: Ctrl+C
echo ============================================
echo.

set FLASK_APP=run.py
python run.py
