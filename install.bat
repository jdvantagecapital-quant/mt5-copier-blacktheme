@echo off
REM =====================================================
REM JD MT5 Trade Copier - Installer Script
REM Installs the application to Program Files
REM Must be run as Administrator
REM =====================================================

echo.
echo =====================================================
echo   JD MT5 Trade Copier - Installer
echo =====================================================
echo.

REM Check for admin rights
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: This installer requires Administrator privileges.
    echo Please right-click and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Administrator rights confirmed.
echo.

REM Set installation directory
set INSTALL_DIR=%ProgramFiles%\JD_MT5_TradeCopier
set APP_DATA_DIR=%LOCALAPPDATA%\JD_MT5_TradeCopier

echo Installation directory: %INSTALL_DIR%
echo Data directory: %APP_DATA_DIR%
echo.

REM Confirm installation
set /p CONFIRM=Do you want to install JD MT5 Trade Copier? (Y/N): 
if /i not "%CONFIRM%"=="Y" (
    echo Installation cancelled.
    pause
    exit /b 0
)

echo.
echo [1/5] Creating installation directory...
if exist "%INSTALL_DIR%" (
    echo Removing previous installation...
    rmdir /s /q "%INSTALL_DIR%"
)
mkdir "%INSTALL_DIR%"
if errorlevel 1 (
    echo ERROR: Failed to create installation directory
    pause
    exit /b 1
)

echo [2/5] Copying application files...
REM Copy the EXE
copy "JD_MT5_TradeCopier.exe" "%INSTALL_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy application files
    pause
    exit /b 1
)

REM Create data folder in install dir
mkdir "%INSTALL_DIR%\data"

echo [3/5] Creating data directory...
if not exist "%APP_DATA_DIR%" mkdir "%APP_DATA_DIR%"
if not exist "%APP_DATA_DIR%\data" mkdir "%APP_DATA_DIR%\data"
if not exist "%APP_DATA_DIR%\logs" mkdir "%APP_DATA_DIR%\logs"

echo [4/5] Creating desktop shortcut...
REM Create a VBS script to create shortcut
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\JD MT5 Trade Copier.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%INSTALL_DIR%\JD_MT5_TradeCopier.exe" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%INSTALL_DIR%" >> CreateShortcut.vbs
echo oLink.Description = "JD MT5 Trade Copier" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs
cscript //nologo CreateShortcut.vbs
del CreateShortcut.vbs

echo [5/5] Setting up license...
REM Check if license file exists in current directory
if exist "license*.bat" (
    echo Found license file, copying to installation...
    copy "license*.bat" "%INSTALL_DIR%\" >nul
) else (
    echo.
    echo WARNING: No license file found!
    echo Please copy your license.bat file to:
    echo   %INSTALL_DIR%
    echo.
)

echo.
echo =====================================================
echo   INSTALLATION COMPLETE!
echo =====================================================
echo.
echo Application installed to:
echo   %INSTALL_DIR%
echo.
echo Data will be stored in:
echo   %APP_DATA_DIR%
echo.
echo A desktop shortcut has been created.
echo.
echo IMPORTANT: Copy your license.bat file to the
echo installation folder before running the application.
echo.
echo =====================================================
pause
