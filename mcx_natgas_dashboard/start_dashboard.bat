@echo off
cd /d "%~dp0"
start "MCX Natural Gas Dashboard" http://localhost:8765
python -m http.server 8765
pause
