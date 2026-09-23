@echo off
cd /d %~dp0
set PYTHONUTF8=1
if not exist .venv\Scripts\python.exe (
  echo 未找到 .venv，请先按 README.md 完成安装。
  pause
  exit /b
)
start "" http://127.0.0.1:8081
.venv\Scripts\python.exe backend\main.py
pause
