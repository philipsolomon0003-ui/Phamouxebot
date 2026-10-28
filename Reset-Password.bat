@echo off
title Famous Media Technologies — Reset Master Password
color 0B

echo ======================================================================
echo       FAMOUS MEDIA TECHNOLOGIES | RESET MASTER PASSWORD
echo ======================================================================
echo.
echo  This tool will reset your login password without touching any of your:
echo    - Customer leads & contact history
echo    - Discovered servers & monitored channels
echo    - Saved messages, notes, and business settings
echo.
echo  Resetting password...
echo.

cd /d "%~dp0"

if exist "C:\Users\USER\AppData\Local\Programs\Python\Python314\python.exe" (
    "C:\Users\USER\AppData\Local\Programs\Python\Python314\python.exe" app\reset_password.py
) else if exist "py.exe" (
    py app\reset_password.py
) else (
    python app\reset_password.py
)

echo.
pause
