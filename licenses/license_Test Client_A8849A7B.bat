@echo off
REM =====================================================
REM JD MT5 Trade Copier - License File
REM Licensed to: Test Client
REM Valid until: 2026-01-25
REM DO NOT MODIFY THIS FILE - License will become invalid
REM =====================================================
REM [LICENSE_DATA_START]
set "JD_LICENSE_ID=A8849A7B90528A4E"
set "JD_LICENSE_DATA=Z0FBQUFBQnBUaUhfQmxWTGh1M0wzX2RXQmtXeG5KQmhYOENITmdBV2l4ZGpQd1R1Q1pqNkdDOFMxUEoyX2xnTzhoZHRBVmpUeFNkUkZ2YnZKTGE0a3lSMzZZX1RQZVYtczF5TXV2bl9IN2MxekR1LUIxMDl4Q0dWTndodTBqdFRpUW5taTNfU0tYeWUyWFpyUVQtV1hmWUFkblJ1WmZNaXFrNTZNN3MzSkRtYnkwVU5sbzRJeXVSQXcxRnFGZkNRUmwyLWE4eHlERzR0SnpXRG5WR0JQZGxhMm1TeU9kd1IzRHdKSHJVMkczTWNzU25BcTROZ00xODBJY3lXUGt6RzZVbWlveEY2SnNrWEcwaGlyVnVNeUNESzRxYWNQUzdQTS1STzF3bnRaY2lKMXYzaklnMzhKSXJENm9lMTNIY1puNGVOejVTUnVra0pqVG82RmI1cFUzTU1ma2VoVXlzUHJfZmt2RXdKUlVwTHJNSEo2T01KeUFib1owXzhpQzB3NFpWdWhOZFM1M3lpWHMwVWt6S2JRdm1zQWY2UFpHQUREVVRDSFFjSG1aZl9tVmZtYVdjTTdpZU5pdFQyZVBrUjRqdF8yUzB2LVFXVzJGbGxXWFQ1Y1dRRVdud2R5OVRnbExTdFg2d2xXN0hmNVM2Z1NYd1BBZ3RkUzF5NW8zQW4wM1YxS1N6YXQ5ay15ZUdaLUNyMGkzcGRxSndsdnUyckY4Vzc1WURuZDBHYW9xR003NXFCOFFrPQ=="
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
