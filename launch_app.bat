@echo off
REM RoomieRoster Application Launcher for Windows
REM This batch file launches the Python launcher script

echo ======================================================
echo 🏠 RoomieRoster Application Launcher (Windows)
echo    Household Chore Management Made Easy
echo ======================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Run the Python launcher
python launch_app.py

pause