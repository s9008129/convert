# 🚀 Windows 版本 v3.5.4 穩定版升級指南

> **文件版本**：v1.0  
> **建立日期**：2025-12-07  
> **適用版本**：v3.5.4 (Stable)  
> **適用平台**：Windows 10/11 + NVIDIA GPU (RTX 4090 驗證)

---

## 📋 升級前檢查清單

在升級之前，請確認以下項目已完成：

### 一、基礎環境檢查

| 項目 | 檢查方式 | 預期結果 | 狀態 |
|------|---------|---------|------|
| Docker Desktop | 開啟 Docker Desktop | 顯示「Engine running」 | ☐ |
| NVIDIA 驅動 | `nvidia-smi` | 顯示 GPU 資訊 | ☐ |
| Ollama 服務 | `ollama list` | 顯示已安裝模型 | ☐ |
| 網路連線 | `ping github.com` | 正常回應 | ☐ |
| 磁碟空間 | 至少 10GB 可用 | 足夠空間 | ☐ |

### 二、目前版本確認

在命令提示字元中執行：
```batch
docker inspect --format="{{.Config.Labels}}" meetingscribe-app
```

記錄您目前的版本號：____________

---

## 📥 升級步驟（非技術人員友善版）

### 步驟 1：備份重要資料（約 5 分鐘）

1. 開啟檔案總管
2. 進入 `convert\data` 資料夾
3. 複製 `outputs` 資料夾到安全位置（例如：桌面）
4. 確認 `.env` 檔案已備份

> 💡 **貼士**：輸出的會議記錄都在 `outputs` 資料夾中

### 步驟 2：停止目前服務（約 1 分鐘）

**方法 A：使用批次檔（推薦）**
1. 雙擊 `scripts\stop.bat`
2. 等待看到「✅ 服務已停止」

**方法 B：使用命令列**
```batch
cd convert\scripts
deploy.bat down
```

### 步驟 3：更新程式碼（約 2 分鐘）

1. 開啟命令提示字元（按 `Win + R`，輸入 `cmd`）
2. 進入專案目錄：
   ```batch
   cd C:\path\to\convert
   ```
3. 拉取最新穩定版本：
   ```batch
   git fetch origin
   git checkout main
   git reset --hard 7100d81
   ```

> ⚠️ **注意**：`7100d81` 是目前的穩定版本 commit

### 步驟 4：重建 Docker 映像（約 10-30 分鐘）

> 💡 這是最耗時的步驟，請確保網路穩定

```batch
cd scripts
deploy.bat build
```

等待看到「[OK] Docker image build completed」

### 步驟 5：啟動服務（約 2 分鐘）

**方法 A：使用批次檔（推薦）**
1. 雙擊 `scripts\start.bat`
2. 等待看到「✅ MeetingScribe 已成功啟動！」

**方法 B：使用命令列**
```batch
deploy.bat up
```

### 步驟 6：驗證升級成功

1. 開啟瀏覽器，進入 http://localhost:9527
2. 確認頁面正常顯示
3. 執行健康檢查：
   - 雙擊 `scripts\health-check.bat`
   - 確認所有項目顯示 ✅

---

## ✅ 升級後驗證檢查清單

| 項目 | 檢查方式 | 預期結果 | 狀態 |
|------|---------|---------|------|
| 網頁介面 | http://localhost:9527 | 顯示主頁面 | ☐ |
| 系統狀態 | 頁面右上角 | 顯示「運行中」 | ☐ |
| GPU 狀態 | 頁面狀態列 | 顯示 GPU 型號 | ☐ |
| 本地模式 | 選擇「本地模式」| 可正常選取 | ☐ |
| 雲端模式 | 選擇「雲端模式」| 可正常選取（需 API Key）| ☐ |
| 檔案上傳 | 上傳測試音檔 | 成功開始處理 | ☐ |
| 完整處理 | 等待處理完成 | 產生會議記錄 | ☐ |

---

## 🔧 常見問題排解

### Q1：Docker 映像建置失敗

**症狀**：執行 `deploy.bat build` 時出現錯誤

**解決方案**：
1. 確認 Docker Desktop 正在執行
2. 確認網路連線正常
3. 嘗試清理 Docker 快取：
   ```batch
   docker system prune -f
   deploy.bat build
   ```

### Q2：服務無法啟動

**症狀**：執行 `start.bat` 後，網頁無法開啟

**解決方案**：
1. 檢查端口是否被佔用：
   ```batch
   netstat -an | findstr "9527"
   ```
2. 如有其他程式佔用，請先關閉該程式
3. 重新啟動服務

### Q3：GPU 未被偵測

**症狀**：頁面顯示「CPU」而非 GPU 型號

**解決方案**：
1. 確認 NVIDIA 驅動已更新至最新版
2. 確認 Docker Desktop 已啟用 GPU 支援：
   - 開啟 Docker Desktop > Settings > Resources > GPU
   - 勾選「Enable GPU support」
3. 重新建置映像：
   ```batch
   deploy.bat down
   deploy.bat build
   deploy.bat up
   ```

### Q4：Ollama 連線失敗

**症狀**：選擇本地模式後，摘要生成失敗

**解決方案**：
1. 確認 Ollama 正在執行：
   ```batch
   ollama list
   ```
2. 確認已安裝正確的模型：
   ```batch
   ollama pull gemma3:27b-it-qat
   ```
3. 重新啟動服務

---

## 📁 檔案完整性檢查

以下是 v3.5.4 版本必要的檔案清單：

### 核心程式檔案

| 檔案 | 用途 | 必要性 |
|------|------|--------|
| `backend/main.py` | 主程式進入點 | ✅ 必要 |
| `backend/core/config.py` | 系統配置 | ✅ 必要 |
| `backend/services/transcription.py` | 語音轉錄 | ✅ 必要 |
| `backend/services/summarization.py` | 摘要生成 | ✅ 必要 |
| `backend/api/routes.py` | API 路由 | ✅ 必要 |
| `frontend/index.html` | 網頁介面 | ✅ 必要 |
| `frontend/js/app.js` | 前端邏輯 | ✅ 必要 |
| `frontend/css/style.css` | 樣式表 | ✅ 必要 |

### Docker 配置檔案

| 檔案 | 用途 | 必要性 |
|------|------|--------|
| `docker/Dockerfile.gpu` | GPU 映像定義 | ✅ 必要 |
| `docker/docker-compose-windows-gpu.yml` | Windows GPU 配置 | ✅ 必要 |
| `docker/docker-compose.yml` | 預設配置 | ✅ 必要 |

### 部署腳本

| 檔案 | 用途 | 必要性 |
|------|------|--------|
| `scripts/deploy.bat` | 部署工具 | ✅ 必要 |
| `scripts/start.bat` | 快速啟動 | ✅ 必要 |
| `scripts/stop.bat` | 快速停止 | ✅ 必要 |
| `scripts/health-check.bat` | 健康檢查 | ✅ 必要 |

### 配置檔案

| 檔案 | 用途 | 必要性 |
|------|------|--------|
| `config.yaml` | Windows 配置 | ✅ 必要 |
| `.env.example` | 環境變數範例 | ✅ 必要 |
| `.env` | 實際環境變數 | ⚠️ 需自行建立 |
| `requirements.txt` | Python 依賴 | ✅ 必要 |

---

## 📞 需要協助？

如果您在升級過程中遇到問題：

1. 查看日誌：
   ```batch
   deploy.bat logs
   ```

2. 查閱完整文件：
   - `doc/guides/windows_deployment_guide.md`
   - `doc/guides/docker_rebuild_guide.md`

3. 回報問題時，請提供：
   - Windows 版本
   - Docker Desktop 版本
   - 錯誤訊息截圖
   - `deploy.bat logs` 輸出

---

## 📌 版本資訊

| 項目 | 值 |
|------|-----|
| 穩定版本 | v3.5.4 |
| Commit | 7100d81 |
| 發布日期 | 2025-12-07 |
| 支援平台 | Windows 10/11 x64 |
| GPU 支援 | NVIDIA CUDA 12.x |
| 驗證環境 | RTX 4090, Windows 11 |

---

> **🎉 恭喜！** 您已完成 Windows 版本的穩定版升級。  
> 如有任何問題，請參閱上方的常見問題排解或查閱完整文件。
