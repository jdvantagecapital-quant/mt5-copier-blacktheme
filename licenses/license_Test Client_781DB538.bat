@echo off
REM =====================================================
REM JD MT5 Trade Copier - License File
REM Licensed to: Test Client
REM Valid until: 2026-01-25
REM DO NOT MODIFY THIS FILE - License will become invalid
REM =====================================================
REM [LICENSE_DATA_START]
set "JD_LICENSE_ID=781DB538A73FF4B7"
set "JD_LICENSE_DATA=Z0FBQUFBQnBUaG1wOHNvSUI4eDVtaDRKVGJjSF9kMFNMQVlMX1o0SHFPbUNYSGJ1ZDk4TklXZzZNYm5RNk9iM0NJbVJKTGk0UTVWaVgyNFFVZHNjTUVYZHBoNFFzUmQ5SFJNdEZNNVVCd0dna0h6YjI0U2Y2aWYzUVc1Q1NPT05RVDRHWWUwSVpiZUdnemhpWEQ2b3RYcWVhekxNZlRLcGFNRmlHRmV1Yk1rRWw1UUg3V2Nic2NDVHZuamxkMEVMWUg2d1BkUUdRdkRwU2Y3RnRTVEV1UVpMLW8xZjRoMjE4aGxPbjBZSTBCeWp0YjVXY0pCXzdWdTg1U3A1ODZWcXZkMEdVTzNoUHhrMlZoLXlSZ3VuSTlid2dtWGh3MkRWRTN6QTdqVUIzZzFuRms5Y3pBbjZMNFQ1emE0ZlItaVFHVVhoOHdmUm54dExjbzdiVDJXc2hLU3FXRlZYamVfYnFVUVVaQ2RPQ2Q1T1pVRVdNbHdndzF4T0R5aWUxdUNPdnl6dTllODBDTExuZWgwdE5SUmplTjNTWmpHSzI5Uy0wOW81T19zNTVKWjMyUHdfOXVjNFZxcHZQLWdnSi1JYUhfaEpzZU9lWXZXMUVrdDVJdFByX0pUSERFYVRqSUg3OXZMMnlXUmxfUWpYZE9Kc0FTR1ltd1BpM1kzVVpMa0ZsUFBzUl9rRHFyWGpqMGszLVNwVkItV3U0a0cwQWJaSHIwRnBmZ3B5WUtKQnVWLXFzci1uRHcwPQ=="
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
