@echo off
:: Service Dashboard Launcher (Batch)
:: Double-click this file to start the dashboard

title Service Dashboard Launcher

echo ======================================================================
echo   SERVICE DASHBOARD LAUNCHER
echo ======================================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python first.
    pause
    exit /b 1
)

echo [OK] Python found
echo.

:: Change to scripts directory
cd /d "%~dp0"

:: Check dependencies
echo Checking dependencies...

python -c "import redis" >nul 2>&1
if errorlevel 1 (
    echo [INSTALL] Installing redis...
    pip install redis
)

python -c "import psycopg2" >nul 2>&1
if errorlevel 1 (
    echo [INSTALL] Installing psycopg2-binary...
    pip install psycopg2-binary
)

echo.
echo ======================================================================
echo   STARTING DASHBOARD
echo ======================================================================
echo.
echo Dashboard will open at: http://localhost:8000
echo.
echo Press Ctrl+C to stop the dashboard
echo.
echo ======================================================================
echo.

:: Start dashboard
python service_dashboard.py

echo.
echo Dashboard stopped.
pause
