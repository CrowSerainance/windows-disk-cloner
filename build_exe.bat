@echo off
REM Build script for Windows Disk Cloner
REM This creates standalone .exe files from both Python and C# versions
REM Also creates an installer if Inno Setup is available

setlocal enabledelayedexpansion

echo ============================================================
echo Windows Disk Cloner - Build Script
echo ============================================================
echo.

REM Create dist directory if it doesn't exist
if not exist "dist" mkdir dist

REM Check for Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found in PATH!
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Check for .NET SDK
where dotnet >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: .NET SDK not found!
    echo C# version will not be compiled.
    echo Download from: https://dotnet.microsoft.com/download
    echo.
    set BUILD_CSHARP=0
) else (
    set BUILD_CSHARP=1
)

REM Check for Inno Setup Compiler
where iscc >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Inno Setup Compiler not found!
    echo Installer will not be created.
    echo Download from: https://jrsoftware.org/isdl.php
    echo.
    set BUILD_INSTALLER=0
) else (
    set BUILD_INSTALLER=1
)

echo Step 1: Installing Python dependencies...
echo ============================================================
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
REM Try to install Pillow for icon creation (optional)
python -m pip install Pillow 2>nul

echo.
echo Step 2: Creating disk icon (if possible)...
echo ============================================================
python create_disk_icon.py 2>nul
if exist "disk_icon.ico" (
    echo Icon created successfully
    set ICON_FILE=disk_icon.ico
) else (
    echo No custom icon - using default
    set ICON_FILE=NONE
)

echo.
echo Step 3: Cleaning previous builds...
echo ============================================================
if exist "build" rmdir /s /q build
if exist "dist\*.exe" del /q "dist\*.exe"
if exist "*.spec" del /q *.spec

echo.
echo Step 4: Building Python CLI version...
echo ============================================================
pyinstaller --onefile ^
    --name "DiskClonerCLI" ^
    --console ^
    --icon=%ICON_FILE% ^
    --hidden-import=win32timezone ^
    --hidden-import=win32api ^
    --hidden-import=win32file ^
    --hidden-import=win32con ^
    --hidden-import=wmi ^
    --hidden-import=pythoncom ^
    --add-data "disk_cloner.py;." ^
    --distpath dist ^
    --workpath build ^
    --specpath . ^
    disk_cloner.py

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build CLI version!
    pause
    exit /b 1
)

echo.
echo Step 5: Building Python GUI version...
echo ============================================================
pyinstaller --onefile ^
    --name "DiskClonerGUI" ^
    --windowed ^
    --icon=%ICON_FILE% ^
    --hidden-import=win32timezone ^
    --hidden-import=win32api ^
    --hidden-import=win32file ^
    --hidden-import=win32con ^
    --hidden-import=wmi ^
    --hidden-import=pythoncom ^
    --add-data "disk_cloner.py;." ^
    --distpath dist ^
    --workpath build ^
    --specpath . ^
    disk_cloner_gui.py

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build GUI version!
    pause
    exit /b 1
)

if %BUILD_CSHARP% EQU 1 (
    echo.
    echo Step 6: Building C# version...
    echo ============================================================
    dotnet restore
    if %ERRORLEVEL% NEQ 0 (
        echo WARNING: Failed to restore C# dependencies
        set BUILD_CSHARP=0
    ) else (
        dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true
        if %ERRORLEVEL% EQU 0 (
            echo.
            echo Copying C# executable...
            if exist "bin\Release\net6.0-windows\win-x64\publish\WindowsDiskCloner.exe" (
                copy "bin\Release\net6.0-windows\win-x64\publish\WindowsDiskCloner.exe" "dist\WindowsDiskCloner.exe"
            )
        ) else (
            echo WARNING: Failed to build C# version
            set BUILD_CSHARP=0
        )
    )
)

if %BUILD_INSTALLER% EQU 1 (
    echo.
    echo Step 7: Creating installer...
    echo ============================================================
    if exist "dist\DiskClonerGUI.exe" (
        if not exist "installer" mkdir installer
        iscc create_installer.iss
        if %ERRORLEVEL% EQU 0 (
            echo Installer created successfully!
        ) else (
            echo WARNING: Failed to create installer
        )
    ) else (
        echo WARNING: Cannot create installer - GUI executable not found
    )
)

echo.
echo ============================================================
echo Build Complete!
echo ============================================================
echo.
echo Executables are located in the 'dist' folder:
if exist "dist\DiskClonerCLI.exe" echo   [OK] DiskClonerCLI.exe (Python CLI version)
if exist "dist\DiskClonerGUI.exe" echo   [OK] DiskClonerGUI.exe (Python GUI version)
if %BUILD_CSHARP% EQU 1 (
    if exist "dist\WindowsDiskCloner.exe" echo   [OK] WindowsDiskCloner.exe (C# version)
)
echo.
if %BUILD_INSTALLER% EQU 1 (
    if exist "installer\WindowsDiskCloner-Setup.exe" (
        echo Installer is located in the 'installer' folder:
        echo   [OK] WindowsDiskCloner-Setup.exe
        echo.
    )
)
echo IMPORTANT: Run these executables as Administrator!
echo.
echo To create an installer, install Inno Setup from:
echo   https://jrsoftware.org/isdl.php
echo.
pause
