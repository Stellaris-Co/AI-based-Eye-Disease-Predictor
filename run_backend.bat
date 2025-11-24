@echo off
title Eye Disease AI - BACKEND SERVER
color 0A
cls

echo ========================================================
echo        STARTING BACKEND (FastAPI + PyTorch)
echo ========================================================
echo.

echo [*] Activating Virtual Environment...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo [OK] Environment Active.
) else (
    echo [ERROR] venv not found! Please run setup first.
    pause
    exit
)
echo.

echo [*] Launching API Server...
python backend/main.py

pause