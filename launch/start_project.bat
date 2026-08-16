@echo off
setlocal
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_ROOT%\scripts\start_project.ps1" %*
if errorlevel 1 (
  echo.
  echo Project startup failed. Read the error above, then press any key to close.
  pause >nul
  exit /b 1
)

if /I "%~1"=="-CheckOnly" exit /b 0

echo.
echo Project startup finished. Press any key to close this launcher window.
pause >nul
endlocal
