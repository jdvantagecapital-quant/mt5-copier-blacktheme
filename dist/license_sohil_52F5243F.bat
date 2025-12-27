@echo off
REM =====================================================
REM JD MT5 Trade Copier - License File
REM Licensed to: sohil
REM Valid until: 2026-01-25
REM DO NOT MODIFY THIS FILE - License will become invalid
REM =====================================================
REM [LICENSE_DATA_START]
set "JD_LICENSE_ID=52F5243F901778BE"
set "JD_LICENSE_DATA=Z0FBQUFBQnBUamdEb0RvVUJDYkwzYm9nMEg4cFZCa3p4NV9TTjFQellrYTRsSURiWHh0dmt3SmVwMXVmbDRPc2NOOXRtZkk3aWsxYVZDemlMYlhqNkJadm1oZ1BUeDlUX1B3V0VNSkwtZnFKSWljd2tfWFNfV01FaWVpZEc3UEFQcV9nOTlWZWRGaTNBSVp5TWUxMGdMbExPZHlWRGVWOXFFdVYtaUJXbjEweVpYMF9DOVl3M21GRjQtcVpZYmFvMC1sZlVpejdNdlNNZk9rTmJlOXV6eFFmZ1VNTzNSQlZWMjZRWkRPV0hQZ2xXcGN5WnZWVi1WZHZpWVJwOEptVExYZElGMkE1SEJwdkQzYmZtZGVFNVRaNW80WlFtZm5Ec3djektSQ1NnSUVoZ2hfTUZ2UFpCenRwbkttSUhBRzk1OXM4dmxQZUQwc0l2bkRHTEd3QjR5TUhnRlpFeGdLd0paYWFQVWFzWjJhaWJNcklwSVZ0OEVhNVVoMlFUN2dnVU5hZ2RLSkxJTHlzSHBjN2MxQWRiUzktTXk2UHFDakdJVm9vM2NLRUVqaUV4dFFCRjBrUElBOUxWUmQ3LXhYLUxHMkRTd0tpQm5zbDIxSGJVY05Hb3l6SGhSTlJkbW1wLXpsTVZ5alFMMUhHQnVwNnZNMkxHcTkwM1d1QzZCOW11VFNWX08yeEgzSTFqUGt0d2VLU1hFS3pRNDVMZWN5b0VUOF9QOHVGbVhoVFhveHNkSFNrRDlidElFNTRpUzdSWjJ5ZGhjUUR4SGRu"
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
