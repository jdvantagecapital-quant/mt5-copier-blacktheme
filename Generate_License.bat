@echo off
title JD MT5 Trade Copier - License Generator
echo.
echo ====================================================
echo   JD MT5 Trade Copier - License Generator
echo ====================================================
echo.
echo Starting web-based license generator...
echo.

cd /d "%~dp0"

python license_generator_web.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start license generator.
    echo Make sure Python and Flask are installed:
    echo   pip install flask cryptography
    echo.
    pause
)
