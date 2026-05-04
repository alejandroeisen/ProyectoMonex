@echo off
cd /d "%~dp0"
if exist "venv\Scripts\pythonw.exe" (
    venv\Scripts\pythonw.exe excel_push.py --loop
) else (
    pythonw excel_push.py --loop
)
