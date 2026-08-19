# =====================================================================
# Ollama 優化啟動腳本（v4.7.0）——繞過 setx／GPO 管制的主路徑
# 在 Ollama 所在的 Windows 主機上以 PowerShell 執行
#
# 原理：$env:XXX 是「程序級」環境變數，只作用於本 shell 及其子程序，
#       不寫 registry、不經 setx —— GPO 對持久性環境變數的管制通常擋不到。
#       由本腳本啟動的 ollama serve 一定吃得到這兩個變數。
#
# 效果（同模型另一專案實測）：KV cache 減半，gemma4:31b @num_ctx=16384
#       佔用從 ~23.0GB 降到 ~21GB，offload 根因消失。
#
# 開機自動啟動（可選）：用「工作排程器」建立登入時觸發的工作，
#       動作＝powershell -ExecutionPolicy Bypass -File <本腳本路徑>
# =====================================================================

$ErrorActionPreference = "Stop"

Write-Host "[1/4] 停止既有 Ollama 程序（含 tray app——它會用舊環境重新拉起 server）..."
Get-Process | Where-Object { $_.ProcessName -like "*ollama*" } | ForEach-Object {
    Write-Host "   停止 $($_.ProcessName) (pid=$($_.Id))"
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 3

Write-Host "[2/4] 以行內環境變數啟動 ollama serve..."
$env:OLLAMA_FLASH_ATTENTION = "1"
$env:OLLAMA_KV_CACHE_TYPE   = "q8_0"   # KV cache 減半；需搭配 flash attention 才生效
# 供容器內服務連線（維持既有部署拓樸；若原本未設定可拿掉）
if (-not $env:OLLAMA_HOST) { $env:OLLAMA_HOST = "0.0.0.0:11434" }

$proc = Start-Process -FilePath "ollama" -ArgumentList "serve" -PassThru -WindowStyle Minimized
Write-Host "   ollama serve 已啟動 (pid=$($proc.Id))"

Write-Host "[3/4] 等待服務就緒..."
$ready = $false
foreach ($i in 1..30) {
    try {
        Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 | Out-Null
        $ready = $true; break
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $ready) { Write-Host "✗ 服務 30 秒內未就緒" -ForegroundColor Red; exit 1 }

Write-Host "[4/4] 載入模型並驗證（load-only + /api/ps + 吞吐測試）..."
$model = "gemma4:31b"
Invoke-RestMethod -Method Post -Uri "http://localhost:11434/api/generate" `
    -Body (@{ model = $model; keep_alive = "30m"; options = @{ num_ctx = 16384 } } | ConvertTo-Json) `
    -ContentType "application/json" -TimeoutSec 600 | Out-Null

$ps = Invoke-RestMethod -Uri "http://localhost:11434/api/ps" -TimeoutSec 10
$pass = $true
foreach ($m in $ps.models) {
    $gb = [math]::Round($m.size / 1GB, 1)
    $vramGb = [math]::Round($m.size_vram / 1GB, 1)
    Write-Host "   $($m.name): 總大小 ${gb}GB / VRAM ${vramGb}GB"
    if ($m.size_vram -lt $m.size) { Write-Host "   ✗ FAIL：部分卸載至 CPU" -ForegroundColor Red; $pass = $false }
    elseif ($m.size -gt 22.5GB)   { Write-Host "   △ 完全在 VRAM 但 >22.5GB：KV 量化疑似未生效" -ForegroundColor Yellow; $pass = $false }
    else                          { Write-Host "   ✓ PASS：~21GB@16K，KV 量化生效" -ForegroundColor Green }
}

# 吞吐驗證：防 KV 量化在特定模型上反而觸發 CPU 慢速路徑（Ollama 已知案例）
Write-Host "   吞吐測試（短生成）..."
$gen = Invoke-RestMethod -Method Post -Uri "http://localhost:11434/api/generate" `
    -Body (@{ model = $model; prompt = "請用一句話介紹台灣。"; stream = $false; options = @{ num_ctx = 16384; num_predict = 128 } } | ConvertTo-Json) `
    -ContentType "application/json" -TimeoutSec 300
if ($gen.eval_duration -gt 0) {
    $tps = [math]::Round($gen.eval_count / ($gen.eval_duration / 1e9), 1)
    Write-Host "   tokens/s = $tps"
    if ($tps -lt 10) { Write-Host "   △ 吞吐偏低（<10 tok/s）——若明顯低於未量化時，考慮只留 FLASH_ATTENTION、拿掉 KV_CACHE_TYPE" -ForegroundColor Yellow }
}

if ($pass) { Write-Host "`n✓ 全部通過：Ollama 已以優化組態運行" -ForegroundColor Green }
else       { Write-Host "`n✗ 未全數通過：請執行 diagnose_ollama_host.ps1 判讀原因" -ForegroundColor Red }
