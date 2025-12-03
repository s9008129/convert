# Windows PowerShell 執行政策問題解決方案指南

**適用範圍**：所有 Windows 平台上需要執行 PowerShell 腳本的 Docker 項目  
**最後更新**：2025-12-03  
**版本**：v1.0

---

## 📋 目錄

1. [問題分析](#問題分析)
2. [根本原因](#根本原因)
3. [解決方案對比](#解決方案對比)
4. [批次檔實現方案](#批次檔實現方案)
5. [實施步驟](#實施步驟)
6. [驗證檢查清單](#驗證檢查清單)
7. [故障排除](#故障排除)
8. [最佳實踐](#最佳實踐)

---

## 問題分析

### 典型錯誤現象

在 Windows 系統上執行 PowerShell 腳本時，常出現以下錯誤：

```
無法載入檔案 'D:\project\scripts\deploy.ps1'，因為這個系統上已停用指令碼執行。
如需詳細資訊，請參閱 about_Execution_Policies。
位於 線路:1 字元:1
+ .\scripts\deploy.ps1 build
+ ~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : SecurityError: (:) [], PSSecurityException
    + FullyQualifiedErrorId : UnauthorizedAccess
```

### 為什麼會發生這個問題

1. **Windows 安全機制**：PowerShell 執行政策是 Windows 內建的安全功能
2. **預設限制性設定**：企業環境或新系統通常設定為 `Restricted`
3. **無法透過臨時參數繞過**：在某些環境下，即使使用 `-ExecutionPolicy Bypass` 也無法生效
4. **管理員權限要求**：修改全局執行政策需要管理員權限，帶來安全風險

---

## 根本原因

### 執行政策的分層結構

Windows PowerShell 有 4 個執行政策層級，從高到低優先級：

```
MachinePolicy  ← 企業 GPO 設定（最高優先級）
UserPolicy     ← 使用者 GPO 設定
Process        ← 當前 PowerShell 進程設定（臨時參數）
CurrentUser    ← 目前使用者設定
LocalMachine   ← 整個系統設定（最低優先級）
```

### 為什麼 Bypass 參數無效

當系統設有 GPO 強制執行政策時，即使使用 `-ExecutionPolicy Bypass` 也會被 MachinePolicy 覆蓋：

```
┌─────────────────────────────────────────┐
│ 使用者執行：.\deploy.ps1 build          │
└─────────────────────────────────────────┘
                    ↓
        ┌──────────────────────┐
        │ 檢查執行政策優先級   │
        └──────────────────────┘
                    ↓
    ┌───────────────────────────────┐
    │ MachinePolicy = Restricted?   │ ← GPO 設定（無法覆蓋）
    └───────────────────────────────┘
                    ↓ 是
    ✗ 拒絕執行（即使使用 Bypass 參數）
```

### PowerShell 的根本限制

**PowerShell 執行政策設計目的**：
- 防止無意中執行惡意腳本
- 不提供高度安全防護（只是行為阻止）
- 可被管理員或 GPO 強制設定

**結論**：無法透過 PowerShell 層面完全規避此限制

---

## 解決方案對比

### 方案 A：修改執行政策（❌ 不推薦）

**優點**：
- 可直接執行 PowerShell 腳本

**缺點**：
- ❌ 需要管理員權限
- ❌ 修改系統全局設定，影響安全性
- ❌ 在企業環境可能違反政策
- ❌ 無法應對 GPO 強制的政策

```powershell
# 不推薦的方式
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# 這會降低系統安全性！
```

### 方案 B：使用 PowerShell Bypass 參數（⚠️ 不可靠）

**優點**：
- 無需修改系統設定

**缺點**：
- ⚠️ 無法應對 GPO 強制的政策
- ⚠️ 只在某些環境有效
- ⚠️ 用戶體驗不穩定

```powershell
# 不可靠的方式
powershell -ExecutionPolicy Bypass -File .\deploy.ps1 build
# 在 GPO Restricted 環境中仍會失敗
```

### 方案 C：使用批次檔包裝（✅ 推薦）

**優點**：
- ✅ 完全規避 PowerShell 限制
- ✅ 無需修改系統設定
- ✅ 無需管理員權限
- ✅ 在所有 Windows 版本上原生支援
- ✅ 可靠且穩定

**缺點**：
- 需要建立額外的 `.bat` 檔案

```batch
@echo off
REM 批次檔完全獨立於 PowerShell
REM 使用系統命令直接調用
cd /d "%~dp0\.."
docker compose build
```

---

## 批次檔實現方案

### 架構設計

批次檔透過調用系統命令完全規避 PowerShell 限制：

```
┌─────────────────────────────────┐
│ 使用者執行：.\deploy.bat build  │
└─────────────────────────────────┘
                ↓
    ┌──────────────────────────┐
    │ Windows CMD.EXE          │ ← 系統命令解釋器
    │（獨立於 PowerShell）     │
    └──────────────────────────┘
                ↓
        ┌──────────────────────┐
        │ 解析批次檔命令      │
        └──────────────────────┘
                ↓
        ┌──────────────────────┐
        │ 執行 Docker Compose  │
        └──────────────────────┘
                ↓
        ✅ 成功執行（無執行政策限制）
```

### 核心要素

| 要素 | 說明 | 示例 |
|------|------|------|
| **路徑處理** | 動態獲取絕對路徑 | `cd /d "%~dp0"` |
| **變數延遲展開** | 支援動態變數替換 | `setlocal enabledelayedexpansion` |
| **條件邏輯** | 實現流程控制 | `if /i "!COMMAND!"=="build" goto cmd_build` |
| **錯誤檢查** | 驗證命令成功 | `if errorlevel 1 (...)` |
| **標籤與跳轉** | 函數式邏輯實現 | `:cmd_build` / `goto cmd_build` |

### 批次檔完整模板

```batch
@echo off
REM ============================================
REM 專案部署工具 - 批次檔版本
REM ============================================
REM 特點：完全規避 PowerShell 執行政策限制

setlocal enabledelayedexpansion

REM === 路徑初始化 ===
cd /d "%~dp0"
set "SCRIPT_DIR=%CD%"
cd ..
set "PROJECT_ROOT=%CD%"
set "DOCKER_DIR=%PROJECT_ROOT%\docker"

REM === 參數處理 ===
set COMMAND=%1
if "!COMMAND!"=="" set COMMAND=help

REM === 前置檢查 ===
:test_docker
echo [INFO] Checking Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not found
    exit /b 1
)

REM === 命令分派 ===
if /i "!COMMAND!"=="build" goto cmd_build
if /i "!COMMAND!"=="up" goto cmd_up
if /i "!COMMAND!"=="down" goto cmd_down
if /i "!COMMAND!"=="help" goto cmd_help

:cmd_build
echo [INFO] Building...
cd /d "!DOCKER_DIR!"
docker compose build --progress=plain
if errorlevel 1 (
    echo [ERROR] Build failed
    exit /b 1
)
echo [OK] Build completed
exit /b 0

:cmd_up
echo [INFO] Starting services...
cd /d "!DOCKER_DIR!"
docker compose up -d
echo [OK] Services started
exit /b 0

:cmd_down
echo [INFO] Stopping services...
cd /d "!DOCKER_DIR!"
docker compose down
echo [OK] Services stopped
exit /b 0

:cmd_help
echo.
echo Usage: deploy.bat [command]
echo Commands: build, up, down, help
echo.
exit /b 0
```

---

## 實施步驟

### 步驟 1：分析現有 PowerShell 腳本

首先理解現有 `.ps1` 腳本的功能結構：

```powershell
# 例如原始 deploy.ps1
param([string]$Command = "help")

function Test-Docker { ... }
function Invoke-Build { ... }
function Invoke-Up { ... }

switch ($Command.ToLower()) {
    "build" { Invoke-Build }
    "up" { Invoke-Up }
    "help" { Write-Host "Usage..." }
}
```

**提取要點**：
- ✅ 參數：`$Command`（build、up、help 等）
- ✅ 功能：Docker 檢查、映像構建、服務啟動
- ✅ 流程控制：基於命令的條件邏輯

### 步驟 2：設計批次檔結構

建立對應的批次檔結構：

```batch
@echo off
REM 參數處理
set COMMAND=%1

REM 前置檢查
:test_docker
docker info >nul 2>&1
if errorlevel 1 exit /b 1

REM 命令分派
if /i "!COMMAND!"=="build" goto cmd_build
if /i "!COMMAND!"=="up" goto cmd_up
if /i "!COMMAND!"=="help" goto cmd_help

REM 實現各命令
:cmd_build
...
goto end

:cmd_up
...
goto end

:cmd_help
...

:end
```

### 步驟 3：轉換 PowerShell 命令

| PowerShell | 批次檔 | 說明 |
|-----------|--------|------|
| `Split-Path -Parent $path` | `cd /d "%~dp0"` | 獲取父目錄 |
| `Write-Host "text"` | `echo text` | 輸出文本 |
| `$LASTEXITCODE` | `%ERRORLEVEL%` | 檢查上一個命令狀態 |
| `if ($condition) { ... }` | `if condition (...)` | 條件判斷 |
| `foreach ($item in $list)` | `for %%i in (...) do` | 迴圈 |
| `Start-Sleep -Seconds 5` | `timeout /t 5 /nobreak` | 延遲執行 |

### 步驟 4：實施路徑處理

批次檔路徑處理的關鍵技巧：

```batch
@echo off
setlocal enabledelayedexpansion

REM 獲取腳本所在目錄
cd /d "%~dp0"
set "SCRIPT_DIR=%CD%"

REM 獲取上級目錄（項目根目錄）
cd ..
set "PROJECT_ROOT=%CD%"

REM 建構 Docker 目錄路徑
set "DOCKER_DIR=%PROJECT_ROOT%\docker"

REM 輸出調試信息
echo [DEBUG] Script dir: !SCRIPT_DIR!
echo [DEBUG] Project root: !PROJECT_ROOT!
echo [DEBUG] Docker dir: !DOCKER_DIR!

REM 驗證目錄存在
if not exist "!DOCKER_DIR!" (
    echo [ERROR] Docker directory not found: !DOCKER_DIR!
    exit /b 1
)

REM 轉移到 Docker 目錄並執行
cd /d "!DOCKER_DIR!"
docker compose build
```

**關鍵要點**：
- `%~dp0` - 當前批次檔的完整路徑
- `setlocal enabledelayedexpansion` - 啟用延遲變數擴展
- `!variable!` - 使用延遲擴展的變數
- `/d` 參數 - 允許 `cd` 命令改變磁碟機

### 步驟 5：實施錯誤處理

完善的錯誤處理確保腳本可靠性：

```batch
REM 檢查前置條件
:check_docker
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running
    exit /b 1
)

REM 執行核心命令
docker compose build --progress=plain

REM 檢查執行結果
if errorlevel 1 (
    echo [ERROR] Docker build failed
    exit /b 1
)

echo [OK] Docker build completed
exit /b 0
```

### 步驟 6：測試和驗證

完整的測試流程：

```bash
# 測試 1：基本執行
.\deploy.bat help

# 測試 2：Docker 檢查
.\deploy.bat status

# 測試 3：實際構建（小型項目）
.\deploy.bat build

# 測試 4：參數驗證
.\deploy.bat invalid_command
```

---

## 驗證檢查清單

### 預部署檢查

- [ ] PowerShell 腳本邏輯已完全理解
- [ ] 所有命令和參數已列舉
- [ ] 路徑處理方案已設計
- [ ] 錯誤情況已識別

### 批次檔實施檢查

- [ ] 批次檔語法正確（無編碼錯誤）
- [ ] 所有路徑使用絕對路徑
- [ ] 所有變數使用 `!variable!` 延遲擴展
- [ ] 所有命令都有錯誤檢查
- [ ] 有調試輸出便於故障排除

### 功能測試檢查

- [ ] 不同命令都能正確執行
- [ ] 路徑解析正確
- [ ] 錯誤信息清晰明確
- [ ] Docker 命令成功調用

### 文檔檢查

- [ ] 更新了 README.md 的部署說明
- [ ] 添加了 WINDOWS_DEPLOYMENT_SOLUTION.md 指南
- [ ] 更新了 CHANGELOG.md
- [ ] 編寫了批次檔使用指南

---

## 故障排除

### 常見問題 1：找不到 Docker 目錄

**症狀**：
```
[ERROR] Cannot change to Docker directory: ...
```

**原因**：
- 路徑計算錯誤
- Docker 目錄不存在

**解決方案**：
```batch
REM 添加調試輸出
echo [DEBUG] SCRIPT_DIR: !SCRIPT_DIR!
echo [DEBUG] PROJECT_ROOT: !PROJECT_ROOT!
echo [DEBUG] DOCKER_DIR: !DOCKER_DIR!

REM 驗證目錄存在
if not exist "!DOCKER_DIR!" (
    echo [ERROR] Directory not found: !DOCKER_DIR!
    dir "!PROJECT_ROOT!"
    exit /b 1
)
```

### 常見問題 2：批次檔中文亂碼

**症狀**：
```
[INFO] 啟動服務... → 顯示為亂碼
```

**原因**：
- 批次檔編碼問題（應使用 UTF-8 或 ANSI）

**解決方案**：
- 使用 VS Code 以 UTF-8 編碼保存
- 或使用純英文 ASCII 字符的批次檔

### 常見問題 3：變數未展開

**症狀**：
```
!COMMAND! is not recognized
```

**原因**：
- 未啟用 `setlocal enabledelayedexpansion`
- 使用了 `%variable%` 而非 `!variable!`

**解決方案**：
```batch
@echo off
setlocal enabledelayedexpansion
REM 之後使用 !variable! 而非 %variable%
```

### 常見問題 4：Docker 命令無法找到

**症狀**：
```
'docker' is not recognized as an internal or external command
```

**原因**：
- Docker 未安裝或未在 PATH 中

**解決方案**：
```batch
REM 使用絕對路徑或確保 Docker 在 PATH 中
where docker
REM 應該輸出：C:\Program Files\Docker\Docker\Resources\bin\docker.exe
```

---

## 最佳實踐

### 1. 批次檔設計原則

**保持簡潔**：
```batch
REM ✅ 推薦：清晰的命令分派
if /i "!COMMAND!"=="build" goto cmd_build

REM ❌ 避免：複雜的嵌套邏輯
if "!COMMAND!"=="build" (
    if !CHECK1! (
        if !CHECK2! ( ... )
    )
)
```

**使用標籤標記**：
```batch
REM ✅ 推薦：使用清晰的標籤
:test_prerequisites
:cmd_build
:cmd_up
:cmd_help
:error_handler

REM ❌ 避免：含糊的標籤名稱
:start1
:section2
:part3
```

**一致的錯誤處理**：
```batch
REM ✅ 推薦：統一的錯誤檢查
docker compose build
if errorlevel 1 (
    echo [ERROR] Build failed
    exit /b 1
)

REM ❌ 避免：不一致的處理
docker compose build
if errorlevel 1 goto error
echo [OK] Build completed
goto end
:error
echo Something went wrong
```

### 2. 路徑處理最佳實踐

**使用絕對路徑**：
```batch
REM ✅ 推薦：絕對路徑
cd /d "!DOCKER_DIR!"

REM ❌ 避免：相對路徑
cd docker
```

**驗證路徑存在**：
```batch
if not exist "!DOCKER_DIR!" (
    echo [ERROR] Directory not found: !DOCKER_DIR!
    exit /b 1
)
```

**使用 /d 參數跨磁碟機**：
```batch
REM ✅ 推薦：支援跨磁碟機
cd /d "!DOCKER_DIR!"

REM ❌ 避免：可能失敗
cd "!DOCKER_DIR!"
```

### 3. 調試技巧

**添加調試輸出**：
```batch
REM === 調試模式 ===
echo [DEBUG] Command: !COMMAND!
echo [DEBUG] Project root: !PROJECT_ROOT!
echo [DEBUG] Docker dir: !DOCKER_DIR!

REM === 詳細輸出 ===
echo.
echo Directories:
dir "!PROJECT_ROOT!"
```

**捕獲命令輸出**：
```batch
REM 輸出到文件便於分析
docker compose build > build.log 2>&1
if errorlevel 1 (
    echo [ERROR] Build failed. See build.log
    type build.log
    exit /b 1
)
```

### 4. 維護性考慮

**文檔註解**：
```batch
REM ============================================
REM 用途：Docker 部署管理工具
REM 作者：Team
REM 維護日期：2025-12-03
REM ============================================

REM === 路徑初始化 ===
REM 獲取當前目錄，支援相對和絕對執行
REM %~dp0 = 當前批次檔的完整路徑
```

**版本管理**：
```batch
REM === 版本信息 ===
setlocal
set "SCRIPT_VERSION=1.0"
set "LAST_UPDATED=2025-12-03"
set "COMPATIBLE_DOCKER=4.0+"
```

**配置選項**：
```batch
REM === 可配置參數 ===
set "DOCKER_COMPOSE_VERSION=--progress=plain"
set "TIMEOUT=120"
set "RETRY_COUNT=3"
```

---

## 應用於其他專案的檢查清單

當將此方案應用於其他 Docker 項目時：

### 前期準備

- [ ] 確認現有 PowerShell 腳本的所有功能
- [ ] 列舉所有需要支援的命令
- [ ] 識別所有 Docker Compose 命令的使用

### 批次檔開發

- [ ] 建立批次檔框架
- [ ] 實現路徑處理邏輯
- [ ] 轉換所有命令
- [ ] 添加錯誤檢查

### 測試和驗證

- [ ] 單個命令測試
- [ ] 路徑解析驗證
- [ ] 錯誤處理測試
- [ ] 跨環境測試（不同 Windows 版本）

### 文檔和部署

- [ ] 更新 README.md
- [ ] 編寫快速開始指南
- [ ] 記錄 CHANGELOG
- [ ] 提供故障排除指南

---

## 官方參考文檔

- [Microsoft PowerShell 執行政策文檔](https://learn.microsoft.com/zh-tw/powershell/module/microsoft.powershell.core/about/about_execution_policies)
- [Windows 批次檔命令參考](https://docs.microsoft.com/zh-tw/windows-server/administration/windows-commands/windows-commands-reference)
- [Docker Compose 官方文檔](https://docs.docker.com/compose/)

---

## 結論

**批次檔方案的優勢**：
- ✅ 完全規避 PowerShell 執行政策限制
- ✅ 無需修改系統設定
- ✅ 無需管理員權限
- ✅ 在所有 Windows 版本上可靠工作
- ✅ 易於維護和擴展

**適用場景**：
- ✅ 開發環境部署
- ✅ CI/CD 管道
- ✅ 自動化指令碼
- ✅ 企業環境部署（受 GPO 限制）

**建議**：
使用批次檔包裝是在 Windows 上執行 Docker 部署的最佳實踐，特別是在企業環境或受執行政策限制的系統上。

---

**版本歷史**

| 版本 | 日期 | 變更 |
|------|------|------|
| v1.0 | 2025-12-03 | 初始版本，完整的解決方案指南 |

