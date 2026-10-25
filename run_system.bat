@echo off
echo ========================================================
echo   SALES DATA ANALYSIS SYSTEM - EXECUTIVE LAUNCHER
echo ========================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Python detected! Starting Flask Web Server with Pandas & SQLite/MySQL...
    echo Installing requirements if needed...
    pip install flask pandas numpy matplotlib >nul 2>nul
    start "" http://127.0.0.1:5000
    python app.py
) else (
    echo Opening Web Dashboard directly in your default browser...
    start "" index.html
)

pause
