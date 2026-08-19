# =====================================================================
# Ollama 主機診斷腳本（v4.7.0）
# 用途：釐清「OLLAMA_FLASH_ATTENTION / OLLAMA_KV_CACHE_TYPE 設了沒生效」的原因
# 在 Ollama 所在的 Windows 主機上以 PowerShell 執行（不需系統管理員）
#
# 背景：setx 設定「沒生效」最常見四種原因——
#   1. Ollama tray app 沒有真正重啟（右下角小圖示 Quit 才算，關視窗沒用；
#      tray app 會以「舊環境」重新拉起 ollama serve）
#   2. Ollama 以 Windows 服務（SYSTEM 身分）執行 → 看不到「使用者」環境變數
#   3. GPO 管制封鎖寫入 HKCU\Environment → setx 根本沒寫進去
#   4. 版本過舊或模型架構不支援 → 靜默退回 f16（Ollama 已知行為）
# 本腳本逐一檢查並給出結論。
# =====================================================================

$ErrorActionPreference = "Continue"
Write-Host "===== [1/5] 環境變數實際值（registry） =====" -ForegroundColor Cyan
foreach ($scope in @("HKCU:\Environment", "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment")) {
    Write-Host "-- $scope"
    foreach ($name in @("OLLAMA_FLASH_ATTENTION", "OLLAMA_KV_CACHE_TYPE", "OLLAMA_HOST", "OLLAMA_KEEP_ALIVE")) {
        try {
            $value = (Get-ItemProperty -Path $scope -Name $name -ErrorAction Stop).$name
            Write-Host "   $name = $value" -ForegroundColor Green
        } catch {
            Write-Host "   $name = (未設定)" -ForegroundColor Yellow
        }
    }
}
Write-Host "→ 若這裡『未設定』，代表之前的 setx 沒寫進 registry（極可能被 GPO 管制），"
Write-Host "  請改用 start_ollama_optimized.ps1（行內程序級環境變數，不經 registry）。"

Write-Host "`n===== [2/5] Ollama 執行型態 =====" -ForegroundColor Cyan
$svc = Get-Service -Name "*ollama*" -ErrorAction SilentlyContinue
if ($svc) {
    Write-Host "以 Windows 服務執行：$($svc.Name)（狀態 $($svc.Status)）" -ForegroundColor Yellow
    Write-Host "→ 服務（SYSTEM 身分）看不到『使用者』環境變數，須設『系統』層級或改用啟動腳本。"
} else {
    Write-Host "未發現 Ollama 服務（應為桌面 app / 手動啟動）"
}
Get-Process | Where-Object { $_.ProcessName -like "*ollama*" } |
    Select-Object Id, ProcessName, StartTime | Format-Table -AutoSize
Write-Host "→ 若有『ollama app』程序，setx 後必須從系統匣圖示完全 Quit 再重開才會吃到新環境變數。"

Write-Host "`n===== [3/5] Ollama server.log 生效設定傾印 =====" -ForegroundColor Cyan
$serverLog = Join-Path $env:LOCALAPPDATA "Ollama\server.log"
if (Test-Path $serverLog) {
    Write-Host "log: $serverLog（找最近一次啟動的設定行）"
    Select-String -Path $serverLog -Pattern "OLLAMA_FLASH_ATTENTION|OLLAMA_KV_CACHE_TYPE" |
        Select-Object -Last 4 | ForEach-Object { Write-Host "   $($_.Line)" }
    Write-Host "→ 這是『有沒有生效』的最終證據：Ollama 啟動時會印出實際吃到的 OLLAMA_* 值。"
    Write-Host "→ 注意：由 start_ollama_optimized.ps1 啟動的 serve 不寫這個檔（server.log 是 tray app 的），"
    Write-Host "  時間戳若是舊的屬正常；腳本啟動的程序請以 [4] 的實際載入量為準。"
} else {
    Write-Host "找不到 $serverLog（Ollama 可能以其他方式安裝）" -ForegroundColor Yellow
}

Write-Host "`n===== [4/5] 觸發載入並檢查 VRAM 分佈 =====" -ForegroundColor Cyan
try {
    $model = "gemma4:31b"
    Write-Host "載入 $model（load-only，可能需要數十秒）..."
    Invoke-RestMethod -Method Post -Uri "http://localhost:11434/api/generate" `
        -Body (@{ model = $model; options = @{ num_ctx = 16384 } } | ConvertTo-Json) `
        -ContentType "application/json" -TimeoutSec 600 | Out-Null
    $ps = Invoke-RestMethod -Uri "http://localhost:11434/api/ps" -TimeoutSec 10
    foreach ($m in $ps.models) {
        $gb = [math]::Round($m.size / 1GB, 1)
        $vramGb = [math]::Round($m.size_vram / 1GB, 1)
        Write-Host "   $($m.name): 總大小 ${gb}GB / VRAM ${vramGb}GB"
        if ($m.size_vram -eq 0) {
            Write-Host "   ✗ 100% 在 CPU（size_vram=0）→ Ollama 程序疑已失去 GPU（驅動更新/睡眠後的長駐程序），請重啟 Ollama" -ForegroundColor Red
        } elseif ($m.size_vram -lt $m.size) {
            Write-Host "   ✗ 部分卸載至 CPU（推理會崩跌）" -ForegroundColor Red
        } elseif ($m.size -gt 23.2GB) {
            Write-Host "   △ 完全在 VRAM，但總量 >23.2GB → KV 量化疑似未生效（f16 特徵）" -ForegroundColor Yellow
        } else {
            Write-Host "   ✓ 完全在 VRAM 且大小符合 q8 特徵（實測 ~22.6GB@16K）→ 量化已生效" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "無法連線 Ollama（$($_.Exception.Message)）" -ForegroundColor Red
}

Write-Host "`n===== [5/5] nvidia-smi 可用 VRAM =====" -ForegroundColor Cyan
try { nvidia-smi --query-gpu=name,memory.free,memory.total --format=csv } catch { Write-Host "nvidia-smi 不可用" }

Write-Host "`n結論判讀：" -ForegroundColor Cyan
Write-Host " A. registry 沒值 + server.log 沒印生效 → GPO 擋 setx → 用 start_ollama_optimized.ps1"
Write-Host " B. registry 有值 + server.log 沒印生效 → Ollama 沒真正重啟（tray Quit）或服務身分問題"
Write-Host " C. server.log 有印 + [4] 仍 ~23GB → 該 Ollama 版本對此模型 KV 量化靜默失效 → 升級 Ollama"
