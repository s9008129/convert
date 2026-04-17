@echo off
REM ============================================
REM MeetingScribe - Windows Deployment Tool
REM ============================================
REM Pure batch script - no PowerShell execution policy restrictions

setlocal enabledelayedexpansion

REM Get the absolute path of script directory
cd /d "%~dp0"
set "SCRIPT_DIR=%CD%"
cd ..
set "PROJECT_ROOT=%CD%"
set "DOCKER_DIR=%PROJECT_ROOT%\docker"

echo [DEBUG] Script directory: !SCRIPT_DIR!
echo [DEBUG] Project root: !PROJECT_ROOT!
echo [DEBUG] Docker directory: !DOCKER_DIR!

REM Define command parameter (default: help)
set COMMAND=%1
if "!COMMAND!"=="" set COMMAND=help

REM ==============================================
REM TEST DOCKER INSTALLATION
REM ==============================================
:test_docker
echo.
echo [INFO] Checking Docker installation...
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running or not installed
    echo [ERROR] Please start Docker Desktop first
    exit /b 1
)
echo [OK] Docker is running
echo.

REM ==============================================
REM HANDLE COMMANDS
REM ==============================================

if /i "!COMMAND!"=="build" goto cmd_build
if /i "!COMMAND!"=="up" goto cmd_up
if /i "!COMMAND!"=="down" goto cmd_down
if /i "!COMMAND!"=="restart" goto cmd_restart
if /i "!COMMAND!"=="status" goto cmd_status
if /i "!COMMAND!"=="logs" goto cmd_logs
if /i "!COMMAND!"=="help" goto cmd_help
if "!COMMAND!"=="" goto cmd_help

echo [ERROR] Unknown command: !COMMAND!
goto cmd_help

REM ==============================================
REM BUILD COMMAND
REM ==============================================
:cmd_build
echo [INFO] Building Docker image...
echo [INFO] This may take 10-30 minutes (model download required on first build)
echo.
cd /d "!DOCKER_DIR!"
if errorlevel 1 (
    echo [ERROR] Cannot change to Docker directory: !DOCKER_DIR!
    exit /b 1
)

REM 檢查是否為 GPU 模式
if exist "docker-compose-windows-gpu.yml" (
    echo [INFO] Detected GPU compose file, checking GPU availability...
    nvidia-smi >nul 2>&1
    if not errorlevel 1 (
        echo [INFO] NVIDIA GPU detected, building GPU version...
        docker compose -f docker-compose-windows-gpu.yml --progress=plain build
    ) else (
        echo [WARN] No NVIDIA GPU detected, building standard version...
        docker compose --progress=plain build
    )
) else (
    docker compose --progress=plain build
)

if errorlevel 1 (
    echo [ERROR] Docker image build failed
    exit /b 1
)
echo [OK] Docker image build completed
exit /b 0

REM ==============================================
REM UP COMMAND
REM ==============================================
:cmd_up
echo [INFO] Starting services...
cd /d "!DOCKER_DIR!"
if errorlevel 1 (
    echo [ERROR] Cannot change to Docker directory
    exit /b 1
)

REM 檢查是否為 GPU 模式
if exist "docker-compose-windows-gpu.yml" (
    nvidia-smi >nul 2>&1
    if not errorlevel 1 (
        echo [INFO] Starting with GPU support...
        echo [INFO] Rebuilding GPU image to keep frontend/backend/dependencies in sync...
        docker compose -f docker-compose-windows-gpu.yml up -d --build
    ) else (
        echo [INFO] Starting without GPU...
        docker compose up -d
    )
) else (
    docker compose up -d
)

if errorlevel 1 (
    echo [ERROR] Failed to start services
    exit /b 1
)

echo [INFO] Waiting for services to start...
set TIMEOUT=120
set ELAPSED=0

:wait_loop
if !ELAPSED! geq !TIMEOUT! (
    echo [ERROR] Service startup timeout
    exit /b 1
)

timeout /t 5 /nobreak >nul

for /f "tokens=*" %%a in ('docker inspect --format="{{.State.Health.Status}}" meetingscribe-app 2^>nul') do set HEALTH=%%a

if "!HEALTH!"=="healthy" (
    echo.
    echo [OK] Service started successfully!
    echo.
    echo =====================================
    echo   MeetingScribe is ready!
    echo =====================================
    echo   URL: http://localhost:9527
    echo =====================================
    exit /b 0
)

set /a ELAPSED=!ELAPSED!+5
echo    Waiting... (!ELAPSED! seconds)
goto wait_loop

REM ==============================================
REM DOWN COMMAND
REM ==============================================
:cmd_down
echo [INFO] Stopping services...
cd /d "!DOCKER_DIR!"

REM 停止所有可能的 compose 配置
if exist "docker-compose-windows-gpu.yml" (
    docker compose -f docker-compose-windows-gpu.yml down 2>nul
)
docker compose down 2>nul

echo [OK] Services stopped
exit /b 0

REM ==============================================
REM RESTART COMMAND
REM ==============================================
:cmd_restart
call :cmd_down
timeout /t 2 /nobreak >nul
call :cmd_up
exit /b %ERRORLEVEL%

REM ==============================================
REM STATUS COMMAND
REM ==============================================
:cmd_status
echo [INFO] Service status:
cd /d "!DOCKER_DIR!"

REM 顯示所有可能的服務狀態
if exist "docker-compose-windows-gpu.yml" (
    echo [GPU Config]:
    docker compose -f docker-compose-windows-gpu.yml ps 2>nul
    echo.
)
echo [Standard Config]:
docker compose ps 2>nul

exit /b 0

REM ==============================================
REM LOGS COMMAND
REM ==============================================
:cmd_logs
cd /d "!DOCKER_DIR!"

REM 優先顯示 GPU 版本日誌
if exist "docker-compose-windows-gpu.yml" (
    nvidia-smi >nul 2>&1
    if not errorlevel 1 (
        docker compose -f docker-compose-windows-gpu.yml logs -f --tail 100
        exit /b %ERRORLEVEL%
    )
)

docker compose logs -f --tail 100
exit /b %ERRORLEVEL%

REM ==============================================
REM HELP COMMAND
REM ==============================================
:cmd_help
echo.
echo MeetingScribe Docker Deployment Tool
echo.
echo Usage: deploy.bat [command]
echo.
echo Available Commands:
echo   build   - Build Docker image (use on first deployment)
echo   up      - Start services
echo   down    - Stop services
echo   restart - Restart services
echo   status  - View service status
echo   logs    - View service logs
echo   help    - Show this help message
echo.
echo Quick Start:
echo   1. deploy.bat build    ^# First time only
echo   2. deploy.bat up       ^# Start services
echo   3. Open http://localhost:9527
echo.
exit /b 0
