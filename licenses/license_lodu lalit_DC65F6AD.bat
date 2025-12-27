@echo off
REM =====================================================
REM JD MT5 Trade Copier - License File
REM Licensed to: lodu lalit
REM Valid until: 2025-01-26
REM DO NOT MODIFY THIS FILE - License will become invalid
REM =====================================================
REM [LICENSE_DATA_START]
set "JD_LICENSE_ID=DC65F6ADBBA6353E"
set "JD_LICENSE_DATA=Z0FBQUFBQnBUbXE3a01fNmJRaWV1VS1SUURFcU9Eb2szcHhDY19BdGxGYXlrWEtwVFFPemU4ZmFKekkxYldLeVRINlFLOHk1Mzg5cmxMV2Izc0tEMjRnSldWOU5LanNiLWpGR3J2SXBTTlhMbm9RR2ExaEtSMWtpZ2ZkRTdCeVI4em5BV0cyWF81MU5SaEIybElfT2VzVFRpQ00wZXN0aDd1ZVlVNnlncFRJSHJZRDFDUC10NWdhNVlJcGk4Qkw3VnhyZmR3eVk2MGZmTjFmczg1cU5uTnJQR3d0NENmVlJ6NGVYTU5uWC1yWF9fd09yQzNYSmRuX21LZTQ0dWlpcVJ3bHItV1RsNVpybE5GaUUxdk9JYUR4ZWNjenlUMm1FR2lfY1lHTW5NM093ampTR0Fqa2FBWkMzeGxJbVZGN2V1OHpmVGdfWFpBU2JNNlY1RmFkc3VmTVlaak1mNTE4UXVscG9GdXdrak84a2RQUW1lQ29yNHFXLXptdXVWeTJzZC1QbDFVYzM0QnZiY3ZKNGhSSG1pcXFqU2o5OXpFQ0tuSko0S3Z1VEVVVmJJYUpFTXEycXVxRHBudW50Y2w3TXNzU1N0OWItN0VPSTkwWTNEcVYzQVBHZHJYMXUxQ3AyN3hPb1Y1MFV3RUVzT0o2T1ZBa2NaUl9WLWR6eFVyTzlOdzJ3MzhnQXVGdlpDZlI5T1Z2VkZ0anpyMEFIX0ZsaVlXc0VwZllTMEI3TTllTDVjbklNYlRxS3RxcVhMVTBfT2ZOU3JEX1pGN0Ny"
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
