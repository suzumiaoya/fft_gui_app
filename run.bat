@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -m fft_gui_app
    set "EXIT_CODE=%errorlevel%"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python -m fft_gui_app
        set "EXIT_CODE=%errorlevel%"
    ) else (
        echo Python was not found in PATH.
        set "EXIT_CODE=9009"
    )
)

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Application exited with code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
