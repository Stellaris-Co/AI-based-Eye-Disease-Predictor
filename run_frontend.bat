@echo off
title Eye Disease AI - FRONTEND UI
color 0B
cls

echo ========================================================
echo        STARTING FRONTEND (React + Tailwind)
echo ========================================================
echo.

if exist frontend (
    cd frontend
) else (
    echo [ERROR] 'frontend' folder not found!
    pause
    exit
)

echo [*] Launching React App...
echo    (Wait for the Local URL to appear, then Ctrl+Click it)
echo.
npm run dev

pause