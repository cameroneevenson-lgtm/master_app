@echo off
setlocal
cd /d "%~dp0"
if exist "C:\Tools\.venv\Scripts\python.exe" (
  "C:\Tools\.venv\Scripts\python.exe" app.py
) else (
  python app.py
)

