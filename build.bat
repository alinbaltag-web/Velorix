@echo off
setlocal EnableDelayedExpansion

echo.
echo  ================================================
echo   VELORIX -- Build System v1.0
echo   Service Moto Romania
echo  ================================================
echo.

set PYTHON=C:\Users\Alin Baltag\AppData\Local\Programs\Python\Python312\python.exe
set ROOT=%~dp0
set DIST=%ROOT%dist\Velorix
set BUILD=%ROOT%build

echo [1/7] Verific Python...
"%PYTHON%" --version >nul 2>&1
if errorlevel 1 (
    echo  EROARE: Python nu a fost gasit!
    pause
    exit /b 1
)
echo  OK - Python gasit.

echo.
echo [2/7] Verific PyInstaller...
"%PYTHON%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo  PyInstaller nu e instalat. Instalez...
    "%PYTHON%" -m pip install pyinstaller
)
echo  OK - PyInstaller gasit.

echo.
echo [3/7] Curatare build anterior...
if exist "%BUILD%" (
    rmdir /s /q "%BUILD%"
    echo  Sters: build\
)
if exist "%DIST%" (
    rmdir /s /q "%DIST%"
    echo  Sters: dist\Velorix\
)
echo  OK - Curatare completa.

echo.
echo [4/7] Pregatire date curate...
if exist "%ROOT%service_moto.db" (
    echo  Gasit service_moto.db - sterg pentru build curat.
    del /f "%ROOT%service_moto.db"
    echo  OK - Baza de date stearsa.
) else (
    echo  OK - Nicio baza de date gasita.
)
if exist "%ROOT%assets\fonts\*.pkl" (
    del /f "%ROOT%assets\fonts\*.pkl"
    echo  OK - Cache fonturi sters.
)

echo.
echo [5/7] Rulare PyInstaller...
echo  Poate dura 2-5 minute...
echo.
cd /d "%ROOT%"
"%PYTHON%" -m PyInstaller velorix.spec --noconfirm --clean

if errorlevel 1 (
    echo.
    echo  EROARE: Build PyInstaller a esuat!
    pause
    exit /b 1
)

echo.
echo [6/7] Verificare output...
if not exist "%DIST%\Velorix.exe" (
    echo  EROARE: Velorix.exe nu a fost generat!
    pause
    exit /b 1
)
echo  OK - Velorix.exe generat.

echo.
echo [7/7] Creare .env template...
(
echo # VELORIX -- Configurare
echo # DB_MODE=local  -^> SQLite local
echo # DB_MODE=cloud  -^> PostgreSQL Supabase
echo.
echo DB_MODE=local
echo.
echo # Supabase - doar pentru cloud sync
echo # DB_HOST=
echo # DB_PORT=5432
echo # DB_NAME=postgres
echo # DB_USER=
echo # DB_PASSWORD=
) > "%DIST%\.env"
echo  OK - .env template creat.

echo.
echo  ================================================
echo   BUILD REUSIT!
echo   Output: dist\Velorix\Velorix.exe
echo   Urmatorul pas: compileaza installer.iss
echo   cu Inno Setup pentru Setup_Velorix_v1.0.exe
echo  ================================================
echo.
pause