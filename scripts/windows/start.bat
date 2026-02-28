@echo off
REM ============================================
REM MeetingScribe - Windows 啟動腳本 (簡易版)
REM ============================================
REM 此腳本用於非技術使用者快速啟動服務
REM 使用方式：雙擊此檔案即可

setlocal enabledelayedexpansion
cd /d "%~dp0.."

cls
echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                                                               ║
echo ║         🚀 MeetingScribe 啟動工具                            ║
echo ║                                                               ║
echo ║    此工具將為您啟動會議轉錄應用                               ║
echo ║                                                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM 檢查 Docker
echo [1/3] 檢查 Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未啟動
    echo.
    echo 請執行以下步驟：
    echo   1. 點擊 Windows 工作列右下角的 Docker 圖示
    echo   2. 選擇「Docker Desktop」啟動
    echo   3. 等待 Docker 完全啟動（30 秒）
    echo   4. 重新執行此腳本
    echo.
    pause
    exit /b 1
)
echo ✅ Docker 正常

REM 啟動服務
echo [2/3] 啟動服務...
cd docker
docker compose up -d >nul 2>&1
if errorlevel 1 (
    echo ❌ 服務啟動失敗
    echo.
    echo 請檢查以下項目：
    echo   - Docker Desktop 是否正常運行
    echo   - 端口 9527 是否被佔用
    echo   - 磁碟空間是否充足
    echo.
    pause
    exit /b 1
)
echo ✅ 服務已啟動

REM 等待服務就緒
echo [3/3] 等待服務就緒（這需要 30-60 秒）...
set count=0
:wait_loop
set /a count+=1
if %count% gtr 60 (
    echo ⚠️ 服務啟動超時
    echo.
    echo 請執行以下命令查看詳情：
    echo   PowerShell: .\scripts\deploy.ps1 logs
    echo.
    pause
    exit /b 1
)

docker inspect --format="{{.State.Health.Status}}" meetingscribe-app >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

for /f %%i in ('docker inspect --format="{{.State.Health.Status}}" meetingscribe-app 2^>nul') do set health=%%i
if not "!health!"=="healthy" (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo ✅ 服務已就緒
echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                                                               ║
echo ║         ✅ MeetingScribe 已成功啟動！                        ║
echo ║                                                               ║
echo ║    🌐 網址: http://localhost:9527                            ║
echo ║                                                               ║
echo ║    請在瀏覽器中打開上述網址開始使用                           ║
echo ║                                                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo 貼士：
echo   - 按下 Windows + D 最小化此視窗
echo   - 按下 Windows 鍵查看「工作管理員」以監控資源使用
echo.
pause
