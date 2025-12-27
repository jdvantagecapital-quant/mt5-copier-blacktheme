@echo off
REM =====================================================
REM JD MT5 Trade Copier - Uninstaller Script
REM Removes the application from Program Files
REM Must be run as Administrator
REM =====================================================

echo.
echo =====================================================
echo   JD MT5 Trade Copier - Uninstaller
echo =====================================================
echo.

REM Check for admin rights
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: This uninstaller requires Administrator privileges.
    echo Please right-click and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

set INSTALL_DIR=%ProgramFiles%\JD_MT5_TradeCopier
set APP_DATA_DIR=%LOCALAPPDATA%\JD_MT5_TradeCopier

echo This will remove JD MT5 Trade Copier from your computer.
echo.
echo Installation directory: %INSTALL_DIR%
echo Data directory: %APP_DATA_DIR%
echo.

set /p CONFIRM=Do you want to uninstall? (Y/N): 
if /i not "%CONFIRM%"=="Y" (
    echo Uninstallation cancelled.
    pause
    exit /b 0
)

echo.
echo [1/3] Removing application files...
if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%"
    echo Application files removed.
) else (
    echo Application directory not found.
)

echo [2/3] Removing desktop shortcut...
del "%USERPROFILE%\Desktop\JD MT5 Trade Copier.lnk" 2>nul

set /p REMOVE_DATA=Do you want to remove application data? (Y/N): 
if /i "%REMOVE_DATA%"=="Y" (
    echo [3/3] Removing application data...
    if exist "%APP_DATA_DIR%" (
        rmdir /s /q "%APP_DATA_DIR%"
        echo Data directory removed.
    )
) else (
    echo [3/3] Keeping application data.
)

echo.
echo =====================================================
echo   UNINSTALLATION COMPLETE!
echo =====================================================
echo.
pause
