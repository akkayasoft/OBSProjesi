@echo off
chcp 65001 >nul 2>&1
title OBS Projesi - Kurulum

echo ============================================
echo   OBS Projesi - Otomatik Kurulum (Windows)
echo ============================================
echo.

:: Python kontrolu
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadi!
    echo Python 3.10+ yukleyin: https://www.python.org/downloads/
    echo Kurulum sirasinda "Add Python to PATH" secenegini isaretleyin.
    pause
    exit /b 1
)

echo [1/5] Python bulundu:
python --version
echo.

:: Sanal ortam olustur
echo [2/5] Sanal ortam olusturuluyor...
if not exist "venv" (
    python -m venv venv
    echo      Sanal ortam olusturuldu.
) else (
    echo      Sanal ortam zaten mevcut, atlaniyor.
)
echo.

:: Sanal ortami aktif et
echo [3/5] Sanal ortam aktif ediliyor...
call venv\Scripts\activate.bat
echo      Aktif edildi.
echo.

:: Bagimliliklari yukle
echo [4/5] Bagimliliklar yukleniyor...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [HATA] Bagimlilik yuklemesi basarisiz!
    pause
    exit /b 1
)
echo      Bagimliliklar yuklendi.
echo.

:: Instance klasoru olustur
if not exist "instance" mkdir instance

:: Veritabani ve baslangic verileri
echo [5/5] Veritabani olusturuluyor...
set FLASK_APP=run.py

:: Veritabani tablolarini olustur
python -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all(); print('      Tablolar olusturuldu.')"
if %errorlevel% neq 0 (
    echo [HATA] Veritabani olusturulamadi!
    pause
    exit /b 1
)

:: Admin kullanicisi ve sistem ayarlari
flask seed
echo      Admin kullanicisi ve sistem ayarlari eklendi.

echo.
echo ============================================
echo   KURULUM TAMAMLANDI!
echo ============================================
echo.
echo   Uygulamayi baslatmak icin: basla.bat
echo   Veya elle: venv\Scripts\activate ^& python run.py
echo.
echo   Varsayilan giris bilgileri:
echo     Kullanici: admin
echo     Sifre:     admin123
echo.
echo   Tarayicida: http://localhost:5000
echo ============================================
echo.
pause
