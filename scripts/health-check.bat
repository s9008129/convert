@echo off
REM ============================================
REM MeetingScribe - Windows 健康檢查腳本
REM ============================================

setlocal enabledelayedexpansion
cd /d "%~dp0.."

cls
echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║         🩺 MeetingScribe 系統健康檢查                        ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM 檢查 Docker
echo 1. Docker 狀態
docker info >nul 2>&1
if errorlevel 1 (
    echo    ❌ Docker 未啟動
) else (
    echo    ✅ Docker 運行中
)

REM 檢查 MeetingScribe 容器
echo.
echo 2. MeetingScribe 服務
docker ps --filter "name=meetingscribe-app" --format "{{.Names}}" >nul 2>&1
if errorlevel 1 (
    echo    ❌ 服務未啟動
) else (
    for /f %%i in ('docker inspect --format="{{.State.Health.Status}}" meetingscribe-app 2^>nul') do set health=%%i
    if "!health!"=="healthy" (
        echo    ✅ 服務運行中 (健康)
    ) else (
        echo    ⚠️ 服務運行中 (狀態: !health!)
    )
)

REM 檢查 GPU
echo.
echo 3. GPU 狀態
nvidia-smi --query-gpu=name,memory.free,memory.total --format=csv,noheader,nounits >nul 2>&1
if errorlevel 1 (
    echo    ⚠️ 無 NVIDIA GPU 或驅動未安裝
) else (
    for /f "tokens=1,2,3 delims=," %%a in ('nvidia-smi --query-gpu=name,memory.free,memory.total --format=csv,noheader,nounits') do (
        echo    ✅ GPU: %%a
        echo       記憶體: %%b MB 可用 / %%c MB 總計
    )
)

REM 檢查 Ollama
echo.
echo 4. Ollama 服務 (本地模式)
powershell -Command "Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 5" >nul 2>&1
if errorlevel 1 (
    echo    ❌ Ollama 未啟動或無法連接
) else (
    echo    ✅ Ollama 運行中
)

REM 檢查網頁服務
echo.
echo 5. 網頁服務
powershell -Command "Invoke-RestMethod -Uri 'http://localhost:9527/api/health' -TimeoutSec 5" >nul 2>&1
if errorlevel 1 (
    echo    ❌ 網頁服務無法連接
) else (
    echo    ✅ 網頁服務正常
    echo       網址: http://localhost:9527
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo.
pause
