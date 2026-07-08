# ============================================
# 政府智慧會議紀錄生成系統 - 服務重啟工具
# 專為非技術人員設計，安全、不影響其他服務
# ============================================

# 設定視窗標題
$Host.UI.RawUI.WindowTitle = "政府智慧會議紀錄生成系統 服務重啟工具"

# 取得腳本所在目錄
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# 顯示歡迎訊息
Clear-Host
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "║         🔄 政府智慧會議紀錄生成系統 服務重啟工具                         ║" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "║    此工具將安全地重啟 政府智慧會議紀錄生成系統 服務                      ║" -ForegroundColor Cyan
Write-Host "║    不會影響 Docker 中的其他服務                               ║" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 切換到專案目錄
Set-Location (Join-Path $ProjectRoot "docker")

# 確認重啟
Write-Host "您即將重啟 政府智慧會議紀錄生成系統 服務" -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  注意事項：" -ForegroundColor Yellow
Write-Host "   • 正在處理中的任務會被中斷" -ForegroundColor Gray
Write-Host "   • 已完成的結果不受影響" -ForegroundColor Gray
Write-Host "   • 其他 Docker 服務不受影響" -ForegroundColor Gray
Write-Host ""
$confirm = Read-Host "確定要重啟嗎？(Y/N)"

if ($confirm -ne "Y" -and $confirm -ne "y") {
    Write-Host ""
    Write-Host "已取消操作" -ForegroundColor Gray
    exit 0
}

Write-Host ""
Write-Host "🔄 正在重啟服務..." -ForegroundColor Cyan

# 只重啟 meetingscribe-app 容器，不影響其他服務
try {
    # 檢查容器是否存在
    $containerExists = docker ps -a --filter "name=meetingscribe-app" --format "{{.Names}}" 2>$null
    
    if ($containerExists) {
        # 停止 meetingscribe-app
        Write-Host "   📦 停止 政府智慧會議紀錄生成系統 服務..." -ForegroundColor Gray
        docker stop meetingscribe-app 2>$null | Out-Null
        
        # 移除容器（保留映像和資料）
        Write-Host "   📦 移除舊容器..." -ForegroundColor Gray
        docker rm meetingscribe-app 2>$null | Out-Null
    }
    
    # 使用 docker compose 重新啟動（只啟動我們的服務）
    Write-Host "   📦 啟動新服務..." -ForegroundColor Gray
    docker compose up -d 2>&1 | Out-Null
    
    # 等待服務啟動
    Write-Host "   ⏳ 等待服務就緒..." -ForegroundColor Gray
    $timeout = 120
    $elapsed = 0
    $ready = $false
    
    while ($elapsed -lt $timeout) {
        Start-Sleep -Seconds 3
        $elapsed += 3
        
        # 檢查健康狀態
        $health = docker inspect --format='{{.State.Health.Status}}' meetingscribe-app 2>$null
        if ($health -eq "healthy") {
            $ready = $true
            break
        }
        
        # 檢查容器是否在運行
        $status = docker inspect --format='{{.State.Status}}' meetingscribe-app 2>$null
        if ($status -eq "running") {
            Write-Host "   ⏳ 已等待 $elapsed 秒，服務啟動中..." -ForegroundColor Gray
        }
    }
    
    if ($ready) {
        Write-Host ""
        Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
        Write-Host "║                                                               ║" -ForegroundColor Green
        Write-Host "║         ✅ 服務重啟成功！                                     ║" -ForegroundColor Green
        Write-Host "║                                                               ║" -ForegroundColor Green
        Write-Host "║    網址：http://localhost:9527                                ║" -ForegroundColor Green
        Write-Host "║                                                               ║" -ForegroundColor Green
        Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "⚠️  服務啟動中，請稍後再試" -ForegroundColor Yellow
        Write-Host "   您可以執行 'docker logs meetingscribe-app' 查看詳細日誌" -ForegroundColor Gray
    }
    
} catch {
    Write-Host ""
    Write-Host "❌ 重啟失敗：$_" -ForegroundColor Red
    Write-Host ""
    Write-Host "如果問題持續，請嘗試：" -ForegroundColor Yellow
    Write-Host "   1. 確認 Docker Desktop 已啟動" -ForegroundColor Gray
    Write-Host "   2. 執行 'docker compose logs' 查看錯誤訊息" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Write-Host "按任意鍵結束..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
