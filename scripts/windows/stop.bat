@echo off
REM ============================================
REM 政府智慧會議紀錄生成系統 - Windows 停止腳本
REM ============================================

setlocal enabledelayedexpansion
cd /d "%~dp0.."

echo.
echo 正在停止 政府智慧會議紀錄生成系統 服務...
echo.

cd docker
docker compose down

echo.
echo ✅ 服務已停止
echo.
pause
