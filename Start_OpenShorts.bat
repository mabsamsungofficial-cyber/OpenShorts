@echo off
setlocal enabledelayedexpansion
title OpenShorts Launcher
chcp 65001 >nul

echo ========================================================
echo               OPENSHORTS DESKTOP APP
echo ========================================================
echo.

cd /d "%~dp0"

REM Refresh PATH from Windows Registry so newly installed FFmpeg/Python/Node are found
for /f "tokens=2*" %%a in ('reg query "HKLM\System\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%b"
set "PATH=%SYS_PATH%;%USER_PATH%;%PATH%"

REM 1. Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.11 or 3.12 from https://www.python.org/downloads/
    echo NOTE: Make sure to check "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM 2. Run Windows setup & diagnostics (shims, dependencies, desktop shortcut)
python -u windows_setup.py
if errorlevel 1 (
    echo [ERROR] Setup encountered an issue.
    pause
    exit /b 1
)

REM 3. Configure dev server proxy
set VITE_PROXY_TARGET=http://127.0.0.1:8000

echo.
echo [1/3] Starting OpenShorts AI Engine & Backend...
start "OpenShorts-Backend" /min python -m uvicorn app:app --host 127.0.0.1 --port 8000

echo [2/3] Starting OpenShorts Interface...
start "OpenShorts-Frontend" /min cmd /c "cd /d %~dp0dashboard && npm.cmd run dev"

echo [3/3] Waiting for servers to initialize...
timeout /t 4 /nobreak >nul

echo.
echo ========================================================
echo           OpenShorts is running!
echo ========================================================
echo  App Window is opening.
echo  Keep this launcher window open while using OpenShorts.
echo  Closing this window will automatically STOP OpenShorts.
echo ========================================================
echo.

REM Launch in Native Desktop App Mode (Microsoft Edge or Google Chrome)
where msedge >nul 2>&1
if not errorlevel 1 (
    start msedge --app=http://localhost:5173/#app
) else (
    where chrome >nul 2>&1
    if not errorlevel 1 (
        start chrome --app=http://localhost:5173/#app
    ) else (
        start http://localhost:5173/#app
    )
)

echo Press any key or close this window to STOP OpenShorts...
pause >nul

echo Stopping OpenShorts servers...
taskkill /fi "WINDOWTITLE eq OpenShorts-Backend*" /f /t >nul 2>&1
taskkill /fi "WINDOWTITLE eq OpenShorts-Frontend*" /f /t >nul 2>&1
echo Done.
