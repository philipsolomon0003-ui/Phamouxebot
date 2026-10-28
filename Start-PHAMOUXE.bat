@echo off
title Famous Media Technologies — Discord AI Business Assistant
color 09

echo ======================================================================
echo       FAMOUS MEDIA TECHNOLOGIES | DISCORD AI BUSINESS ASSISTANT
echo ======================================================================
echo.
echo  Starting your private assistant dashboard...
echo  Your web browser will open automatically in a few seconds.
echo.
echo  Access Address: http://127.0.0.1:8080
echo  Direct Telegram Contact: @Phamouxetv
echo.
echo  [Keep this window open while using your assistant]
echo  [Close this window when you want to stop the application]
echo ======================================================================
echo.

cd /d "%~dp0"

if exist "C:\Users\USER\AppData\Local\Programs\Python\Python314\python.exe" (
    "C:\Users\USER\AppData\Local\Programs\Python\Python314\python.exe" run.py
) else if exist "py.exe" (
    py run.py
) else (
    python run.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Notice] The dashboard stopped or encountered an issue.
    pause
)
