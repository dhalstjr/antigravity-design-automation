@echo off
chcp 65001 >nul
title Antigravity PSD-to-Figma Server
echo.
echo ══════════════════════════════════════════════════════
echo   Antigravity Design Automation Server
echo   Starting...
echo ══════════════════════════════════════════════════════
echo.

cd /d "%~dp0"

echo [1/2] Checking Python...
python --version 2>nul
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

echo [2/2] Starting web server...
echo.
echo ══════════════════════════════════════════════════════
echo   Server ready!
echo   Now open Figma and run the Antigravity plugin.
echo   PSD file will be converted automatically.
echo.
echo   Press Ctrl+C to stop the server.
echo ══════════════════════════════════════════════════════
echo.

python web_app.py
pause
