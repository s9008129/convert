# 🚀 MeetingScribe 快速開始（Windows 10 分鐘安裝）

## ⚡ 超快速安裝（已有環境）

如果您已有 Docker 和 NVIDIA 驅動，直接執行：

```powershell
cd C:\path\to\convert
.\scripts\deploy.ps1 build
.\scripts\deploy.ps1 up
```

然後打開 http://localhost:9527 ✅

---

## 📋 前置檢查（1 分鐘）

打開 PowerShell，執行以下命令逐一檢查：

### 1. 檢查 Docker

```powershell
docker --version
docker run hello-world
```

✅ 若顯示版本號和 "Hello from Docker" → 已安裝

❌ 若出現錯誤：下載 [Docker Desktop](https://www.docker.com/products/docker-desktop) 並安裝

### 2. 檢查 NVIDIA 驅動

```powershell
nvidia-smi
```

✅ 若顯示 GPU 信息 → 已安裝

❌ 若出現錯誤：下載 [NVIDIA 驅動](https://www.nvidia.com/Download/driverDetails.aspx/199537) 並安裝

### 3. 啟用 Docker GPU

1. 打開 Docker Desktop
2. Settings → Resources → GPU → ✅ Enable GPU
3. Apply & Restart

---

## 🎯 3 步啟動（5 分鐘）

### 步驟 1：下載專案

```powershell
# 選擇位置（例如 C:\Users\YourName\Documents）
cd C:\Users\YourName\Documents

# 方案 A：使用 Git（推薦）
git clone https://github.com/your-org/convert.git
cd convert

# 方案 B：直接下載 ZIP
# 1. 訪問 GitHub 頁面 → Code → Download ZIP
# 2. 解壓到 convert 資料夾
# 3. cd convert
```

### 步驟 2：配置環境（可選）

```powershell
# 複製環境變數範本
Copy-Item .env.example .env

# 編輯 .env（用記事本或 VS Code）
notepad .env
```

**推薦設定（RTX 4090）：**

```ini
MAX_FILE_SIZE_MB=500
MAX_CONCURRENT_TASKS=2
DEFAULT_MODE=local
```

### 步驟 3：啟動服務

```powershell
# 建構（首次，耗時 10-30 分鐘）
.\scripts\deploy.ps1 build

# 啟動
.\scripts\deploy.ps1 up
```

✅ **看到這個訊息表示成功：**

```
🎉 MeetingScribe 已就緒！
📍 網址: http://localhost:9527
```

打開瀏覽器訪問 http://localhost:9527 🎉

---

## 🔧 常用命令

| 用途 | 命令 |
|------|------|
| **停止服務** | `.\scripts\deploy.ps1 down` |
| **重啟服務** | `.\scripts\deploy.ps1 restart` |
| **查看狀態** | `.\scripts\health-check.ps1` |
| **查看日誌** | `.\scripts\deploy.ps1 logs` |

---

## ⚠️ 常見問題速救

| 問題 | 解決 |
|------|------|
| Docker 未啟動 | 開啟 Docker Desktop |
| GPU 未被使用 | 確認 Docker GPU 已啟用，見上文 |
| 服務無法連接 | `.\scripts\deploy.ps1 restart` |
| 檔案無法上傳 | 檢查檔案大小和格式（MP3/WAV/M4A） |

更多問題見 [完整指南](./Windows部署完整指南.md)

---

## 🎓 下一步

1. ✅ 上傳音訊檔案測試
2. 📖 閱讀 [完整部署指南](./Windows部署完整指南.md)
3. 📊 查看 [API 文件](./README.md)
4. 🚀 進階配置和最佳實踐

---

**需要幫助？** 檢查 [完整指南](./Windows部署完整指南.md) 或提交 Issue
