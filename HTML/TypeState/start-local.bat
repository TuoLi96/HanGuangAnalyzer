@echo off
chcp 65001 >nul
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo 未检测到 Node.js。
  echo 请在 PowerShell 中运行：winget install OpenJS.NodeJS.LTS
  echo 安装完成后重新打开终端，再双击此文件。
  pause
  exit /b 1
)
node server.js
pause
