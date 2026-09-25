@echo off
rem Windows launcher for the Telegram printer bot (replaces systemd on Linux).
rem Restarts the bot on crash; stops on exit code 78 (config error).
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
if not exist logs mkdir logs

:loop
echo [%date% %time%] starting bot >> logs\bot.log
".venv\Scripts\python.exe" -m bot.main >> logs\bot.log 2>&1
set RC=%errorlevel%
echo [%date% %time%] bot exited with code %RC% >> logs\bot.log
if "%RC%"=="78" (
  echo Config error, see logs\bot.log
  pause
  exit /b 78
)
timeout /t 5 /nobreak >nul
goto loop
