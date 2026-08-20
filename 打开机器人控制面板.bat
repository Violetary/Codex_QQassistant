@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHON=C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "PYTHONW=C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
if not exist "%PYTHON%" (
  echo Python runtime not found:
  echo %PYTHON%
  pause
  exit /b 1
)
if exist "%PYTHONW%" (
  start "" "%PYTHONW%" "%~dp0control_panel.py"
) else (
  start "" "%PYTHON%" "%~dp0control_panel.py"
)
