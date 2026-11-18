@echo off
setlocal
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
echo =======================================================
echo   Starting RTL Optimizer AI Agent Demonstration
echo =======================================================
python scripts\run_agent.py --demo
echo.
pause
