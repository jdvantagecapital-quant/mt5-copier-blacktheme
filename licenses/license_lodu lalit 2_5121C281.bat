@echo off
REM =====================================================
REM JD MT5 Trade Copier - License File
REM Licensed to: lodu lalit 2
REM Valid until: 2025-12-26
REM DO NOT MODIFY THIS FILE - License will become invalid
REM =====================================================
REM [LICENSE_DATA_START]
set "JD_LICENSE_ID=5121C281EF54FE92"
set "JD_LICENSE_DATA=Z0FBQUFBQnBUbXJRRGVBTGtUTURvN3IyOHE1SExqVHZfWlpsSTFVQURRZHlMUXZEUy1EZGI5YnVsS19TVkFVSVBrUEFyQmFNLXJPRXpVTkRQcUFjWXJGZVVwMjV0ZF9JcVpUQ0JYYU5SbnFMNjVtazVSQmM3R0dyd3cwSkRBVFhJMnJVcFpuWmYxS2FxZVV2SHUzczZ4RTY2V291NUI1Um43Z3poQlRucEExb2NVZnFKakJaR1hjMFh4YUhoSVhaV1dINUhPR3VFY3cxRm44N3NkajNwb1ozVEJXZ2pxVFRQSHBSdURtLWV0elp3Z09uNVlBRzBGekI5SkhaZVk1VUdqRTljSkxpOGxrdFU5cjZ6VEI0R1FCOXJrM1Y0WUlvTG02YW5jeE41bUNEc01LMnE0NkxJZm9FUFBwVnlSU2xIcTVOa0lrclF0RUkyM203dHd3dnJTTUpzWkQwb01idHd2Sm9sVTEtbFpQSV9BY2oteVUxVGVKYUN4RjJETzktaFZrTEZzMXBZcEJRcmFZVVpYYzhOeXF1dURyNW1PdWI4TjgwZVIxazhibFp5YVQwSzZxTTJxVEtkWmoxbmN0Q0FrTzFjaWRhMDF4UEk2c0ZEVmdxbGxVd3U3WlVTdlhnRlBFR0ZhSW1yTzF3UERxbGRnVXlxckc1Z1BUeWQ0RmJ0ZFN3TTFfMDZRQk45cDhNcmlFcnhHQWpqdUoyR1piWk00VU9STlNHTVNKdXNGa0ZxaU5SOFpoU1VXZXlfQ2tiMkJ2WHJObXpqSlJHd09aVkVOamtLRHg3a1pjQ3g3cm1SUT09"
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
