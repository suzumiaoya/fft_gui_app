@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo Startup failed with code %EXIT_CODE%. See the message above.
    if not defined FFT_GUI_NO_PAUSE pause
)
exit /b %EXIT_CODE%
