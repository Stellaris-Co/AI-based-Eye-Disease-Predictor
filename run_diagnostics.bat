@echo off
title Eye Disease AI - System Diagnostics
color 0B
cls

echo ========================================================
echo        EYE DISEASE AI - DIAGNOSTICS SUITE
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

echo ========================================================
echo  STEP 1: SYSTEM CHECK
echo ========================================================
python scripts/check_setup.py
echo.
timeout /t 2 >nul

echo ========================================================
echo  STEP 2: DATASET INTEGRITY SCAN
echo ========================================================
echo Scanning for corrupt images...
python scripts/verify_dataset.py
echo.
timeout /t 2 >nul

echo ========================================================
echo  STEP 3: DATA EXPLORATION
echo ========================================================
echo Generating distribution charts...
python scripts/explore_data.py
echo.

echo ========================================================
echo  DIAGNOSTICS COMPLETE
echo ========================================================
echo.
pause