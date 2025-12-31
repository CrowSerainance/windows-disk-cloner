@echo off
REM Quick launcher for Windows Disk Cloner GUI
REM This script checks for admin privileges and launches the GUI

echo ============================================================
echo Windows Disk Cloner - GUI Launcher
echo ============================================================
echo.

REM Change to the directory where this batch file is located
cd /d "%~dp0"

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running as Administrator: OK
    echo.
) else (
    echo ERROR: Not running as Administrator!
    echo.
    echo Please right-click this file and select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

REM Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found!
    echo.
    echo Please install Python from: https://www.python.org/
    echo.
    pause
    exit /b 1
)

REM Check if dependencies are installed
python -c "import win32api, wmi" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing required dependencies...
    python -m pip install pywin32 wmi
    echo.
)

REM Launch the GUI
echo Launching Windows Disk Cloner GUI...
echo Current directory: %CD%
echo.
python disk_cloner_gui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to launch GUI
    echo Check if disk_cloner_gui.py exists in: %CD%
    echo.
    pause
)
