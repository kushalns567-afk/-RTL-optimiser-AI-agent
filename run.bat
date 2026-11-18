@echo off
setlocal
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
python scripts\run_agent.py %*
