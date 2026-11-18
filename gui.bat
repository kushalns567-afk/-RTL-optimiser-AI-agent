@echo off
setlocal
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
echo =======================================================
echo   Launching RTL Optimizer Web Dashboard...
echo   Open http://localhost:8501 in your browser
echo =======================================================
python -m streamlit run rtl_agent\ui\app.py
pause
