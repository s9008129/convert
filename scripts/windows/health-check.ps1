# ============================================
# MeetingScribe - 系統健康檢查工具
# ============================================

# 取得腳本所在目錄
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Clear-Host
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         🩺 MeetingScribe 系統健康檢查                         ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 檢查 Docker
Write-Host "1. Docker 狀態" -ForegroundColor White
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Docker 運行中" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Docker 未啟動" -ForegroundColor Red
        Write-Host "      請啟動 Docker Desktop" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ 無法連接 Docker" -ForegroundColor Red
}

# 檢查 MeetingScribe 容器
Write-Host ""
Write-Host "2. MeetingScribe 服務" -ForegroundColor White
$container = docker ps --filter "name=meetingscribe-app" --format "{{.Status}}" 2>$null
if ($container) {
    $health = docker inspect --format='{{.State.Health.Status}}' meetingscribe-app 2>$null
    if ($health -eq "healthy") {
        Write-Host "   ✅ 服務運行中 (健康)" -ForegroundColor Green
    } elseif ($health -eq "starting") {
        Write-Host "   ⏳ 服務啟動中..." -ForegroundColor Yellow
    } else {
        Write-Host "   ⚠️ 服務運行中 (狀態：$health)" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ❌ 服務未啟動" -ForegroundColor Red
    Write-Host "      執行：.\restart-service.ps1" -ForegroundColor Gray
}

# 檢查 Ollama（主機）
Write-Host ""
Write-Host "3. Ollama 服務（本地模式）" -ForegroundColor White
try {
    $ollamaResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 2>$null
    Write-Host "   ✅ Ollama 運行中" -ForegroundColor Green
    
    # 檢查 Gemma3:12B 模型
    $hasGemma = $ollamaResponse.models | Where-Object { $_.name -like "*gemma*" }
    if ($hasGemma) {
        Write-Host "   ✅ Gemma 模型已安裝" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️ Gemma 模型未安裝" -ForegroundColor Yellow
        Write-Host "      執行：ollama pull gemma3:12b" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ Ollama 未啟動或無法連接" -ForegroundColor Red
    Write-Host "      請確認 Ollama 是否已安裝並啟動" -ForegroundColor Gray
}

# 檢查 GPU
Write-Host ""
Write-Host "4. GPU 狀態" -ForegroundColor White
try {
    $nvidiaSmi = nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>$null
    if ($LASTEXITCODE -eq 0 -and $nvidiaSmi) {
        $gpuInfo = $nvidiaSmi -split ","
        Write-Host "   ✅ GPU: $($gpuInfo[0].Trim())" -ForegroundColor Green
        Write-Host "      記憶體：$($gpuInfo[2].Trim()) MB 可用 / $($gpuInfo[1].Trim()) MB 總計" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠️ 無 NVIDIA GPU 或驅動未安裝" -ForegroundColor Yellow
        Write-Host "      將使用 CPU 模式（處理速度較慢）" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ⚠️ 無 NVIDIA GPU 或驅動未安裝" -ForegroundColor Yellow
}

# 檢查 API Key
Write-Host ""
Write-Host "5. Gemini API Key（雲端模式）" -ForegroundColor White
$envPath = Join-Path $ProjectRoot ".env"
if (Test-Path $envPath) {
    $envContent = Get-Content $envPath -Raw
    if ($envContent -match "GEMINI_API_KEY=.{20,}") {
        Write-Host "   ✅ API Key 已設定" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️ API Key 未設定或格式不正確" -ForegroundColor Yellow
        Write-Host "      執行：.\setup-api-key.ps1" -ForegroundColor Gray
    }
} else {
    Write-Host "   ⚠️ .env 檔案不存在" -ForegroundColor Yellow
    Write-Host "      執行：.\setup-api-key.ps1 建立設定檔" -ForegroundColor Gray
}

# 檢查網頁服務
Write-Host ""
Write-Host "6. 網頁服務" -ForegroundColor White
try {
    $webResponse = Invoke-WebRequest -Uri "http://localhost:9527/api/health" -TimeoutSec 5 -UseBasicParsing 2>$null
    if ($webResponse.StatusCode -eq 200) {
        Write-Host "   ✅ 網頁服務正常" -ForegroundColor Green
        Write-Host "      網址：http://localhost:9527" -ForegroundColor Cyan
    }
} catch {
    Write-Host "   ❌ 網頁服務無法連接" -ForegroundColor Red
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "按任意鍵結束..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
