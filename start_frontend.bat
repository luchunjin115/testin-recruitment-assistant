@echo off
setlocal
cd /d "%~dp0frontend"

echo Installing frontend dependencies...
call npm.cmd install
if errorlevel 1 (
  echo Frontend dependency installation failed.
  pause
  exit /b 1
)

echo Starting Vite frontend at http://localhost:5173 ...
call npm.cmd run dev
pause
