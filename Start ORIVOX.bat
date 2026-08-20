@echo off
setlocal
cd /d "%~dp0"
title ORIVOX Local Setup and Server
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\bootstrap-local.ps1"
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo ORIVOX stopped with error code %EXITCODE%.
  echo Review the messages above, then press any key to close this window.
  pause >nul
)
exit /b %EXITCODE%
