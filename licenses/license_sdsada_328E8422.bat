@echo off
REM =====================================================
REM JD MT5 Trade Copier - License File
REM Licensed to: sdsada
REM Valid until: 2026-01-25
REM DO NOT MODIFY THIS FILE - License will become invalid
REM =====================================================
REM [LICENSE_DATA_START]
set "JD_LICENSE_ID=328E84226BFF6065"
set "JD_LICENSE_DATA=Z0FBQUFBQnBUbkd0Z1hkYnU4TXlPdlNUYXhXN0paeURwcXJ0YVVCQ0RzUzVmOE9hanlFb3B6Q2tIR2MxdXNNQ2M3V0ZUczV1TWk0NEkyWlVtMjR0MXFKa25KSUx0M0UxUVRVSkxpdEFhRERmcU94NnhMOFhLSGt6SG83eVpSc1pDSzJsNjJaV3VfSlN5WkhmSzRDeUlvN2VfUEZ6NERWanZNVzE0OTY2S201LTBvNDhOcDFBOGN1MVNCeV9uaUlxVEpXRXlLQ2NUbmljM2Zkc0dhUVd1WnBDeFJtUl84elhFa1JPOGpqTmNjV05fbkdrai1NcU1FNzRqNTZ6QTFwU2Y4U0dUb3htV0VoQWVXRmd0dDNHRXhDMFU4Ui1SOS0zdzRocWtwWFhxV09ValdsSGhXUmZFcHVKbmpQZ2NZREZkTzQ2VTFpUHBubS02Y1pPNkRvMDkwZU9aYkFUQWdhdG5zVF81Y0RYX0g5bnZzaHB3Y2hxOE95VkZWSEduV3ByaGJfV2ZyNlFzVUFpVldRZGF2bTZyelFEbkhjNmNCYXA0dW9qZkhmdDhUR3dlLURlVWRZTGtjUnZWNTEtY2VwTW53Q2d1T1hCRE9SbnhJdXk4Rm52aHRQVnRBZlEyU3J5ZjRVT0dVUV9DRlF5Qkl1YlIzMzAtVk5rdTZZNndVdWUyaWFqZTdXWXNMd21iTE0zM042bjhleThFRzBKRHpvanhaaGhrY25STVRwVkJBQWVGTjg3Yjk0bzFRbVJ2dDF4WVNPOWttUUFRVEky"
set "JD_LICENSE_VER=2.0"
REM [LICENSE_DATA_END]
REM =====================================================
REM Starting MT5 Trade Copier...
if exist "JD_MT5_TradeCopier.exe" (
    start "" "JD_MT5_TradeCopier.exe" --license-file "%~f0"
) else (
    echo ERROR: JD_MT5_TradeCopier.exe not found in this folder!
    echo Please place this license file in the same folder as the EXE.
    pause
)
