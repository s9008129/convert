@echo off
REM ============================================
REM MeetingScribe - Windows 停止腳本
REM ============================================

setlocal enabledelayedexpansion
cd /d "%~dp0.."

echo.
echo 正在停止 MeetingScribe 服務...
echo.

cd docker
docker compose down

echo.
echo ✅ 服務已停止
echo.
pause
