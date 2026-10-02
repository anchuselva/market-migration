@echo off
chcp 65001 >nul
title Nexus Exchange - Challenge 1.2 Mission Control Launcher
color 0B

:MENU
cls
echo ===============================================================================
echo   ⚡ NEXUS EXCHANGE — CHALLENGE 1.2 HYBRID CLOUD MIGRATION
echo   Zero-Downtime, Zero-Data-Loss Migration for 24/7 Financial Exchange
echo ===============================================================================
echo.
echo   [1] Run Live XAMPP MySQL Competition Demo (demo_xampp.py)
echo   [2] Start Mission Control Server (server.py - http://localhost:8080)
echo   [3] Open XAMPP phpMyAdmin in Browser (http://localhost/phpmyadmin/)
echo   [4] Open Live GitHub Pages Dashboard (Global Edge CDN)
echo   [5] Run Complete Test Suite (pytest -v)
echo   [6] Run Flake8 Code Quality / Lint Verification
echo   [7] Run Financial Data Hygiene Pipeline (cleanse_data.py)
echo   [8] Run Dedicated Disaster Recovery & Failback Drill (demo_rollback.py)
echo   [9] Exit
echo.
echo ===============================================================================
set /p opt="Select an option [1-9]: "

if "%opt%"=="1" goto RUN_XAMPP
if "%opt%"=="2" goto RUN_SERVER
if "%opt%"=="3" goto OPEN_PMA
if "%opt%"=="4" goto OPEN_PAGES
if "%opt%"=="5" goto RUN_TESTS
if "%opt%"=="6" goto RUN_LINT
if "%opt%"=="7" goto RUN_CLEANSE
if "%opt%"=="8" goto RUN_ROLLBACK
if "%opt%"=="9" goto END

echo Invalid selection. Please try again.
timeout /t 2 >nul
goto MENU

:RUN_XAMPP
cls
echo Starting Live XAMPP MySQL Competition Demo...
echo Ensure XAMPP MySQL is started in your XAMPP Control Panel.
echo.
.\.venv\Scripts\python.exe demo_xampp.py
echo.
pause
goto MENU

:RUN_SERVER
cls
echo Starting Mission Control Server on http://localhost:8080...
start "" "http://localhost:8080"
.\.venv\Scripts\python.exe server.py
echo.
pause
goto MENU

:OPEN_PMA
start "" "http://localhost/phpmyadmin/"
goto MENU

:OPEN_PAGES
start "" "https://anchuselva.github.io/market-migration/"
goto MENU

:RUN_TESTS
cls
echo Running Pytest Suite (Domain, Adapters, Parity, Idempotence)...
echo.
.\.venv\Scripts\pytest -v
echo.
pause
goto MENU

:RUN_LINT
cls
echo Running Flake8 Quality Check...
echo.
.\.venv\Scripts\flake8 src tests --count --max-line-length=100 --statistics
if %errorlevel% equ 0 (
    echo [+] PERFECT: 0 lint errors found. Strict PEP8 compliant.
)
echo.
pause
goto MENU

:RUN_CLEANSE
cls
echo Running Financial Data Cleansing & Normalization Pipeline...
echo.
.\.venv\Scripts\python.exe data\cleanse_data.py
echo.
pause
goto MENU

:RUN_ROLLBACK
cls
echo Running Zero-Loss Rollback & Disaster Recovery Drill...
echo.
.\.venv\Scripts\python.exe demo_rollback.py
echo.
pause
goto MENU

:END
exit /b 0
