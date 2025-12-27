@echo off
REM =====================================================
REM JD MT5 Trade Copier - License File
REM Licensed to: Demo Client
REM Valid until: 2026-01-25
REM DO NOT MODIFY THIS FILE - License will become invalid
REM =====================================================
REM [LICENSE_DATA_START]
set "JD_LICENSE_ID=8FBC9AAB481CD9D8"
set "JD_LICENSE_DATA=Z0FBQUFBQnBUaDFXTHBtTVlLZkVWbUpoSDF1SUZ1UEhNS0ZiaVFGT0ZwczFwOERaOURfcWVjQUhidnIwM1Q1T0cwdFlyZ3dWem12MU1SWEZVelg3NWlIbmFUbFFzUnk3dk5SSDFUVzdoblVYUGJjZkJWOTlORllyX1RMNFMzb0xLcUNielk5R1RKOVZ0N1c0Y1ZuTm5TUGVQbmFDcUxHNjNoTzRvcDhXcDZ4ZlFSZUJlZ1pocTJLQ1c5aDdEY1Z0d2JuRTM5U25qTFUzRFp4MkNGVGJvbTNSR2owYkZLVVpQaHZHNG1XS1dndGdfd3F1Unk0TTVJVldUVy1kSU1PejlJOHdIQzZZVG9OYlEwTV9haWQ0VEJVYUMyTkluWjBNT2ZjaHFxZlk4N2JkdkIxSUE0dG01Ql9fbExjdGxFVlN2SjkyeEo1X1BGVU9LS0xrdWVLTWVEQUl0MUVDSWV5TksxNS12cEwteXpCbnpQbHdvaDFpdC1Ub29rUm9JZUYzbFFMUUoxbjhDRUhKMnhtM3M0YldNaFJwYVdhc2w3YUY2c3F5NkdMQ0o0WldBU3VyS0p3b0VEUnFKQWp1ZWJzLXV1LXAtdk94Zk1FY1JIbjBjZmtaQy1aSUlndU03T011d2FtNXVTdEFhVEMwQVB1aFFVMXdNRWdaWkdQcWIxbWRvdW8wa3VnaFlaQmVWSE1xRjV2V3hmdk83cTJGX2kwcFpJSG9YZXlWNU53cF9vMVdPTmZtU2NVPQ=="
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
