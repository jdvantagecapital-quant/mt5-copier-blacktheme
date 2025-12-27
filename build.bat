@echo off
REM =====================================================
REM JD MT5 Trade Copier - Build Script
REM Creates production-ready EXE for distribution
REM =====================================================

echo.
echo =====================================================
echo   JD MT5 Trade Copier - Build Script
echo =====================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not installed
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/4] Cleaning previous build...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

echo.
echo [3/4] Building EXE with PyInstaller...
pyinstaller JD_MT5_TradeCopier.spec --clean --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo [4/4] Creating distribution package...

REM Create distribution folder
set DIST_DIR=dist\JD_MT5_TradeCopier_Distribution
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

REM Copy EXE
copy "dist\JD_MT5_TradeCopier.exe" "%DIST_DIR%\" >nul

REM Create data folder
if not exist "%DIST_DIR%\data" mkdir "%DIST_DIR%\data"
echo {} > "%DIST_DIR%\data\placeholder.json"

REM Create README for clients
echo. > "%DIST_DIR%\README.txt"
echo ===================================================== >> "%DIST_DIR%\README.txt"
echo   JD MT5 Trade Copier >> "%DIST_DIR%\README.txt"
echo   Installation Guide >> "%DIST_DIR%\README.txt"
echo ===================================================== >> "%DIST_DIR%\README.txt"
echo. >> "%DIST_DIR%\README.txt"
echo 1. Place your license.bat file in this folder >> "%DIST_DIR%\README.txt"
echo 2. Double-click the license.bat file to start >> "%DIST_DIR%\README.txt"
echo    (or double-click JD_MT5_TradeCopier.exe) >> "%DIST_DIR%\README.txt"
echo 3. The application will open in your web browser >> "%DIST_DIR%\README.txt"
echo. >> "%DIST_DIR%\README.txt"
echo For support, contact your software provider. >> "%DIST_DIR%\README.txt"
echo ===================================================== >> "%DIST_DIR%\README.txt"

echo.
echo =====================================================
echo   BUILD COMPLETE!
echo =====================================================
echo.
echo Distribution package created at:
echo   %CD%\%DIST_DIR%
echo.
echo Contents:
dir "%DIST_DIR%" /b
echo.
echo Next steps:
echo 1. Use license_generator.py to create client licenses
echo 2. Send the distribution folder + license.bat to client
echo =====================================================
echo.
pause
