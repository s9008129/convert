# MeetingScribe Windows部署指南 - 執行政策解決方案

## 問題分析

在Windows系統上執行PowerShell腳本時，您可能會遇到以下錯誤：

```
因為這個系統上已停用指令碼執行，所以無法載入 deploy.ps1 檔案
```

### 根本原因（第一性原理分析）

1. **PowerShell執行政策**是Windows的安全機制，預防惡意腳本執行
2. **Restricted政策**完全禁止本地指令碼執行
3. **-ExecutionPolicy Bypass參數**雖然可以用於臨時繞過，但在某些情況下仍可能被系統全局政策覆蓋
4. **官方推薦方案**：使用批次檔（`.bat`）或將PowerShell命令包裝在批次檔中

## 解決方案

我們已將PowerShell腳本轉換為純批次檔（`.bat`），完全規避執行政策限制。

### 使用方式

打開命令提示符或PowerShell，導航到項目根目錄，然後執行：

```bash
.\scripts\deploy.bat [command]
```

### 可用命令

| 命令 | 說明 |
|------|------|
| `build` | 建構Docker映像（首次部署時使用） |
| `up` | 啟動服務 |
| `down` | 停止服務 |
| `restart` | 重啟服務 |
| `status` | 查看服務狀態 |
| `logs` | 查看服務日誌 |
| `help` | 顯示幫助信息 |

### 快速開始

```bash
# 1. 首次部署 - 建構Docker映像（10-30分鐘）
.\scripts\deploy.bat build

# 2. 啟動服務
.\scripts\deploy.bat up

# 3. 開啟瀏覽器訪問
http://localhost:9527
```

## 技術細節

### 執行政策檢查

您可以檢查當前的執行政策設定：

```powershell
Get-ExecutionPolicy        # 查看有效政策
Get-ExecutionPolicy -List  # 查看所有scope的政策
```

### 為什麼選擇批次檔而不是修改執行政策

1. **安全性**：不修改系統全局設定，維持安全性
2. **便利性**：無需管理員權限修改政策
3. **兼容性**：批次檔在所有Windows版本上原生支援
4. **可靠性**：不依賴於系統配置或GPO設定

## 相關文檔

- [Microsoft PowerShell執行政策官方文檔](https://learn.microsoft.com/zh-tw/powershell/module/microsoft.powershell.core/about/about_execution_policies)
- [Windows批次檔文檔](https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands-reference)

## 故障排除

### 問題：deploy.bat無法執行

**解決方案**：確保以下條件：
- Docker Desktop已安裝並正在運行
- 項目根目錄中存在`docker/docker-compose.yml`檔案
- 批次檔有執行權限（通常Windows會自動授予）

### 問題：Docker build超時

**解決方案**：
- 這是正常的，首次build可能需要30分鐘以上
- 確保網路連接穩定
- 使用`.\scripts\deploy.bat logs`查看進度

### 問題：Port 9527已被占用

**解決方案**：
1. 修改`docker-compose.yml`中的port映射
2. 或停止占用該port的服務

## 文件結構

```
scripts/
├── deploy.bat       # 主部署腳本（推薦使用）
├── deploy.ps1       # 已廢棄（被deploy.bat替代）
├── start.bat        # 快速啟動腳本
├── stop.bat         # 快速停止腳本
├── health-check.ps1 # 健康檢查腳本
└── setup-api-key.ps1# API金鑰設定腳本
```

## 更新日誌

### v2.3 (2025-12-03)

- 用純批次檔替代PowerShell腳本以解決執行政策問題
- 添加詳細的Windows部署指南
- 優化路徑處理邏輯
- 改進錯誤處理和日誌輸出
