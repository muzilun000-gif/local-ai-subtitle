@echo off
chcp 936 >nul 2>nul
cd /d "%~dp0"
set PYTHONUTF8=1

if not exist .venv\Scripts\python.exe (
  echo [错误] 未找到 .venv 虚拟环境。
  echo 请先按 README.md 完成安装:
  echo     python -m venv .venv
  echo     .venv\Scripts\pip install -r backend\requirements.txt
  echo     .venv\Scripts\python tools\download_model.py small
  pause
  exit /b 1
)

echo 正在启动本地服务...
start "一键字幕服务" .venv\Scripts\python.exe backend\main.py

echo 正在等待服务就绪（首次启动需要几秒）...
powershell -NoProfile -ExecutionPolicy Bypass -Command "for($i=0;$i -lt 120;$i++){$c=New-Object Net.Sockets.TcpClient;try{$c.Connect('127.0.0.1',8081);$c.Close();exit 0}catch{Start-Sleep -Milliseconds 500}};exit 1"

if errorlevel 1 (
  echo [警告] 等待服务超时。
  echo 请查看「一键字幕服务」窗口里的报错信息，或手动访问 http://127.0.0.1:8081
  pause
  exit /b 1
)

echo 服务已就绪，正在打开浏览器...
start "" http://127.0.0.1:8081
echo.
echo 使用完毕后, 关闭「一键字幕服务」窗口即可停止服务。
pause
