@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python environment...
  py -3 -m venv .venv
  if errorlevel 1 goto failed
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo.
  echo Created .env. Open it and add your Angel One SmartAPI credentials.
  echo Then run this file again.
  notepad .env
  pause
  exit /b 0
)
start "MCX Natural Gas Dashboard" http://127.0.0.1:8765
python server.py
pause
exit /b 0
:failed
echo Setup failed. Check that Python 3.10+ is installed and retry.
pause
exit /b 1
