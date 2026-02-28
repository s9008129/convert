# ============================================
# MeetingScribe - Windows 部署腳本
# ============================================
# 執行政策說明：
# - 此腳本需要透過 deploy.bat 執行，或使用以下命令：
#   powershell -ExecutionPolicy Bypass -File .\deploy.ps1 build
# - 不建議更改系統全域執行政策（安全風險）
# ============================================

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

# 取得腳本所在目錄
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$DockerDir = Join-Path $ProjectRoot "docker"

function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Cyan }
function Write-Success { Write-Host "[OK] $args" -ForegroundColor Green }
function Write-Err { Write-Host "[ERROR] $args" -ForegroundColor Red }

# 檢查 Docker
function Test-Docker {
    Write-Host "正在檢查 Docker..." -ForegroundColor Yellow
    
    try {
        $output = docker info 2>&1
        Write-Host "Docker info 執行成功" -ForegroundColor Gray
        return $true
    } catch {
        Write-Err "未安裝 Docker 或 Docker 未啟動"
        exit 1
    }
}

# 建構映像
function Invoke-Build {
    Write-Info "開始建構 Docker 映像..."
    Write-Info "這可能需要 10-30 分鐘（首次建構需下載模型）"
    Write-Host ""
    
    Set-Location $DockerDir
    Write-Host "執行位置: $(Get-Location)" -ForegroundColor Gray
    
    docker compose build --progress=plain
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "映像建構完成"
    } else {
        Write-Err "映像建構失敗，錯誤代碼: $LASTEXITCODE"
        exit 1
    }
}

# 啟動服務
function Invoke-Up {
    Set-Location $DockerDir
    Write-Info "啟動服務..."
    docker compose up -d
    
    Write-Info "等待服務啟動..."
    $timeout = 120
    $elapsed = 0
    
    while ($elapsed -lt $timeout) {
        Start-Sleep -Seconds 5
        $elapsed += 5
        
        $health = docker inspect --format='{{.State.Health.Status}}' meetingscribe-app 2>$null
        if ($health -eq "healthy") {
            Write-Host ""
            Write-Success "服務已啟動！"
            Write-Host ""
            Write-Host "=====================================" -ForegroundColor Green
            Write-Host "  MeetingScribe 已就緒！" -ForegroundColor Green
            Write-Host "=====================================" -ForegroundColor Green
            Write-Host "  網址: http://localhost:9527" -ForegroundColor Cyan
            Write-Host "=====================================" -ForegroundColor Green
            return
        }
        
        Write-Host "   等待中... ($elapsed 秒)" -ForegroundColor Gray
    }
    
    Write-Err "服務啟動超時，請檢查日誌"
}

# 停止服務
function Invoke-Down {
    Set-Location $DockerDir
    Write-Info "停止服務..."
    docker compose down
    Write-Success "服務已停止"
}

# 查看狀態
function Invoke-Status {
    Set-Location $DockerDir
    Write-Info "服務狀態:"
    docker compose ps
}

# 查看日誌
function Invoke-Logs {
    Set-Location $DockerDir
    docker compose logs -f --tail 100
}

# 主程式
Write-Host "MeetingScribe 部署工具啟動" -ForegroundColor Green
Write-Host "命令: $Command" -ForegroundColor Gray

Test-Docker

switch ($Command.ToLower()) {
    "build" { Invoke-Build }
    "up" { Invoke-Up }
    "down" { Invoke-Down }
    "restart" { Invoke-Down; Start-Sleep -Seconds 2; Invoke-Up }
    "status" { Invoke-Status }
    "logs" { Invoke-Logs }
    default {
        Write-Host ""
        Write-Host "MeetingScribe Docker 部署工具" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "使用方式: .\deploy.bat [command]"
        Write-Host ""
        Write-Host "可用命令:"
        Write-Host "  build   - 建構 Docker 映像（首次使用）"
        Write-Host "  up      - 啟動服務"
        Write-Host "  down    - 停止服務"
        Write-Host "  restart - 重啟服務"
        Write-Host "  status  - 查看狀態"
        Write-Host "  logs    - 查看日誌"
        Write-Host ""
        Write-Host "快速開始:"
        Write-Host "  1. .\deploy.bat build    # 首次建構映像"
        Write-Host "  2. .\deploy.bat up       # 啟動服務"
        Write-Host "  3. 開啟 http://localhost:9527"
        Write-Host ""
    }
}
