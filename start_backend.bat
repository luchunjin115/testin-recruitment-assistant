@echo off
setlocal
cd /d "%~dp0backend"

echo Installing backend dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Backend dependency installation failed.
  pause
  exit /b 1
)

echo Starting backend at http://localhost:8000 ...
python run.py
pause
