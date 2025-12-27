@echo off
REM =====================================================
REM JD MT5 Trade Copier - License File
REM Licensed to: Test Client
REM Valid until: 2026-01-25
REM DO NOT MODIFY THIS FILE - License will become invalid
REM =====================================================
REM [LICENSE_DATA_START]
set "JD_LICENSE_ID=19E909DCBCCA9B5E"
set "JD_LICENSE_DATA=Z0FBQUFBQnBUaHVFeEYwbjZZOXdkMnJ5SjMxYnZQVTduYVNTTkgxVEJPZzF4aVpXYl9GRXJuRTFmUUpwWG82RERuRFRaMEZDY2VhRW11ZnY3REU3YTh6S1I3TElENExLZnFHYkprNEZCdXBFTVQzQmNnUWh0cUlxWG9IU3FpN25MOV9rR1dVUjE0TU43UWprN0NPNTBXZ2hIM0tPUV9HaEl0ck12am5FMVhZTy1nMnk2UTVjSjF1YXhhNWVoUXVUSURwdjRuYXFxeHN3RmNtMGhqdWpQWTVxdWNuM0psbHF3YXRtdVpXNVRHRVF4NkdjRUhyRlE0ZGt6MEhwZndqV2Jfckk4UDI0b3lOaWVIZW9vN2JVQXdkSVRKSUZObUtDVHZkejZwYnJ1LW9uVzlSQlV1YTRER3lNQlpFN1VQQllDMlZ1SkpqWmt6QkZBU01iRFBZVGwzdXdlQVgwaGl0U0FvMTVNcnZpM2FLNjRvNlhqd0loTmljN0hWMUVoanpmdmczbGlMcEFQQTVkMUs0cU1OQl9mdEVSWUM5WGh0c01FYWtvOHJVcGpIRGdiTVhucnRWSGNLTG94a0tYd1d6dmVEaS0zU0ZYSjRlUmpIaHdLTU9VXzhnd1pSYzJUWjBKalItS2NabDNpYU80X0lBV1hneW1EQVFhQ195T2l6eW9GZHhuSnZaREJjaUlmWVN3a3ZlTk9OS0V5ZmJnSHozdnBaQzVWbjFkRzNyTVdFdW1hU24wTDVnPQ=="
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
