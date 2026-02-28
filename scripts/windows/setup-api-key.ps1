# ============================================
# MeetingScribe - Gemini API Key 設定工具
# 專為非技術人員設計，友善易用
# ============================================

# 設定視窗標題
$Host.UI.RawUI.WindowTitle = "MeetingScribe API Key 設定工具"

# 取得腳本所在目錄
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# 顯示歡迎訊息
Clear-Host
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "║         🔐 MeetingScribe API Key 設定工具                     ║" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "║    此工具將協助您設定 Gemini API Key                          ║" -ForegroundColor Cyan
Write-Host "║    設定後即可使用「雲端模式」產生高品質的會議摘要             ║" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 檢查是否已有 .env 檔案
$envPath = Join-Path $ProjectRoot ".env"
$envExamplePath = Join-Path $ProjectRoot ".env.example"

if (Test-Path $envPath) {
    Write-Host "📁 找到現有的設定檔" -ForegroundColor Yellow
    $overwrite = Read-Host "   是否要更新 API Key？(Y/N)"
    if ($overwrite -ne "Y" -and $overwrite -ne "y") {
        Write-Host "   已取消操作" -ForegroundColor Gray
        exit 0
    }
}

# 顯示取得 API Key 的說明
Write-Host ""
Write-Host "📋 如何取得 Gemini API Key：" -ForegroundColor White
Write-Host ""
Write-Host "   1. 開啟瀏覽器，前往：" -ForegroundColor Gray
Write-Host "      https://makersuite.google.com/app/apikey" -ForegroundColor Cyan
Write-Host ""
Write-Host "   2. 使用 Google 帳號登入" -ForegroundColor Gray
Write-Host ""
Write-Host "   3. 點擊「Create API Key」建立新的 API Key" -ForegroundColor Gray
Write-Host ""
Write-Host "   4. 複製產生的 API Key" -ForegroundColor Gray
Write-Host ""

# 等待使用者準備好
Write-Host "準備好後，請按 Enter 繼續..." -ForegroundColor Yellow
Read-Host

# 輸入 API Key
Write-Host ""
Write-Host "請貼上您的 Gemini API Key：" -ForegroundColor White
$apiKey = Read-Host

# 驗證 API Key 格式
if ($apiKey.Length -lt 20) {
    Write-Host ""
    Write-Host "❌ API Key 格式不正確，請確認後重試" -ForegroundColor Red
    Write-Host "   API Key 通常以 'AIza' 開頭，長度約 39 個字元" -ForegroundColor Gray
    Write-Host ""
    Write-Host "按任意鍵結束..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# 寫入 .env 檔案
try {
    # 如果有 .env.example，複製一份
    if ((Test-Path $envExamplePath) -and !(Test-Path $envPath)) {
        Copy-Item $envExamplePath $envPath
    }
    
    # 讀取現有內容或建立新檔案
    if (Test-Path $envPath) {
        $content = Get-Content $envPath -Raw
        # 替換或新增 API Key
        if ($content -match "GEMINI_API_KEY=") {
            $content = $content -replace "GEMINI_API_KEY=.*", "GEMINI_API_KEY=$apiKey"
        } else {
            $content += "`nGEMINI_API_KEY=$apiKey"
        }
        $content | Set-Content $envPath -Encoding UTF8
    } else {
        "GEMINI_API_KEY=$apiKey" | Set-Content $envPath -Encoding UTF8
    }
    
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                                                               ║" -ForegroundColor Green
    Write-Host "║         ✅ API Key 設定成功！                                 ║" -ForegroundColor Green
    Write-Host "║                                                               ║" -ForegroundColor Green
    Write-Host "║    現在您可以使用「雲端模式」了                               ║" -ForegroundColor Green
    Write-Host "║                                                               ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  請重新啟動服務以套用新設定" -ForegroundColor Yellow
    Write-Host "   執行：.\restart-service.ps1" -ForegroundColor Cyan
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "❌ 設定失敗：$_" -ForegroundColor Red
    exit 1
}

Write-Host "按任意鍵結束..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
