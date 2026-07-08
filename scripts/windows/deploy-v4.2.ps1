# ============================================================
# 政府智慧會議紀錄生成系統 v4.2 遠端一鍵部署腳本（Windows + RTX 4090 主機）
#
# 用途：在 GPU 主機（10.97.15.58）上把服務更新到 v4.2。
# 使用方式（在該主機的 PowerShell 貼上執行；只需一次）：
#   cd <專案路徑>\convert\scripts\windows
#   .\deploy-v4.2.ps1
#
# 之後任何程式更新都只要：
#   git pull ; docker compose -f docker\docker-compose-windows-gpu.yml restart
#   （零 rebuild、零下載）
# ============================================================

$ErrorActionPreference = "Stop"

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

# 專案根目錄（腳本位於 scripts\windows\ 之下兩層）
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot
Write-Host "專案目錄：$RepoRoot"

Step "步驟 1/5：抓取最新程式碼（v4.2）"
git pull

Step "步驟 2/5：確認 Ollama 與既有模型仍在（不會重新下載）"
try {
    $tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 10
    $models = ($tags.models | ForEach-Object { $_.name }) -join ", "
    Write-Host "  已安裝模型：$models"
    Write-Host "  建議在 Ollama 服務端設定環境變數以提升效能："
    Write-Host "    OLLAMA_FLASH_ATTENTION=1"
    Write-Host "    OLLAMA_KV_CACHE_TYPE=q8_0"
} catch {
    Write-Warning "  無法連到 Ollama（11434），請確認 Ollama 服務執行中。"
}

Step "步驟 3/5：重建映像（僅本次；只下載約 4GB，一次性）"
Write-Host "  注意：這是最後一次需要 build 的更新；v4.2 起改程式碼只需 restart。"
docker compose -f docker\docker-compose-windows-gpu.yml build

Step "步驟 4/5：啟動服務（保留模型 volume，不刪資料）"
docker compose -f docker\docker-compose-windows-gpu.yml up -d

Step "步驟 5/5：健康檢查"
Start-Sleep -Seconds 10
$ok = $false
foreach ($i in 1..30) {
    try {
        $h = Invoke-RestMethod -Uri "http://localhost:9527/api/health?quick=true" -TimeoutSec 5
        if ($h.status -eq "healthy") {
            Write-Host "  服務健康：version=$($h.version), GPU=$($h.gpu_name)" -ForegroundColor Green
            $ok = $true
            break
        }
    } catch { }
    Start-Sleep -Seconds 5
}

if ($ok) {
    Write-Host "`n✅ v4.2 部署完成。" -ForegroundColor Green
    Write-Host "   - 語意校正機制已啟用（可用環境變數 CORRECTION_SCOPE 調整範圍：all/auto/off）"
    Write-Host "   - 機關詞彙表：編輯 data\glossary\公務詞彙.txt（存檔後 restart 生效）"
    Write-Host "   - 版本應顯示 4.2.0（若仍顯示舊版，代表 build 未成功，請回報）"
} else {
    Write-Warning "`n服務未在時限內回報健康，請檢查：docker compose -f docker\docker-compose-windows-gpu.yml logs --tail=50"
}

# ⚠️ 絕對不要執行以下指令（會清空 6GB 語音模型 volume、重新下載）：
#     docker compose ... down -v
# ⚠️ 絕對不要加 --no-cache（會重抓數 GB apt/pip 套件）
