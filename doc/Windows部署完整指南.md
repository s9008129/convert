# 🎯 MeetingScribe Windows 部署完整指南

**版本**: v2.3.6  
**更新日期**: 2025年12月  
**適用環境**: Windows 11/10 + RTX 4090 + Docker Desktop

---

## 📋 目錄

1. [先決條件檢查清單](#先決條件檢查清單)
2. [安裝步驟](#安裝步驟)
3. [配置系統](#配置系統)
4. [啟動服務](#啟動服務)
5. [常見問題排查](#常見問題排查)
6. [使用方法](#使用方法)
7. [性能優化](#性能優化)
8. [系統管理](#系統管理)

---

## 先決條件檢查清單

### 🖥️ 硬體要求

| 項目 | 最低要求 | 推薦配置 | 你的配置 |
|------|---------|--------|--------|
| **CPU** | Intel i5 / AMD Ryzen 5 | Intel i7+ / Ryzen 7+ | ✅ |
| **RAM** | 16GB | 32GB+ | ✅ |
| **GPU** | NVIDIA RTX 20 系列 | NVIDIA RTX 40 系列 | ✅ RTX 4090 |
| **硬碟** | 100GB 可用空間 | 200GB+ SSD | ✅ |
| **網路** | 100Mbps | 1Gbps | - |

### 📦 軟體要求

在開始之前，請確認您已安裝以下軟體。點擊相應的鏈接進行安裝。

#### ✅ 1. Windows 11/10（已安裝）
- 若您使用 Windows 10，請更新至最新版本

#### ✅ 2. Docker Desktop
**為什麼需要？** Docker 是一個容器化平台，允許應用在隔離的環境中運行。

**安裝步驟：**

1. 訪問 [Docker 官網](https://www.docker.com/products/docker-desktop)
2. 點擊「Download for Windows」
3. 下載後執行安裝程式（`Docker Desktop Installer.exe`）
4. 按照安裝嚮導完成安裝
5. **重啟電腦**
6. 啟動 Docker Desktop
7. 打開 PowerShell（以系統管理員身份），驗證安裝：

```powershell
docker --version
docker run hello-world
```

若看到 "Hello from Docker"，表示安裝成功 ✅

**⚠️ 重要配置（Windows GPU 支援）：**

安裝完成後，您必須啟用 GPU 支援：

1. 打開 Docker Desktop
2. 點擊右上角齒輪圖示 ⚙️（Settings）
3. 左側選擇「Resources」
4. 找到「GPU」選項，勾選「Enable GPU」
5. 點擊「Apply & Restart」

> **為什麼？** 啟用 GPU 支援後，Docker 容器內的應用就能使用您的 RTX 4090

#### ✅ 3. NVIDIA 驅動程式
**為什麼需要？** GPU 驅動程式讓 Windows 能與 NVIDIA 顯卡通信。

**檢查驅動版本：**

1. 打開 PowerShell（以系統管理員身份）
2. 執行命令：

```powershell
nvidia-smi
```

**預期輸出（示例）：**

```
+-------------------------+----------------------+----------------------+
| NVIDIA-SMI 552.06       Driver Version: 552.06 |
|---------|------|----------|---------|----------|
| GPU  Name          Persistence-M | Bus-Id  Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap |         Memory-Usage | GPU-Util  Compute M. |
|   0  NVIDIA RTX 4090        Off  |             0%    | 0MiB /   24576MiB |    0% |
+---------|------|----------|---------|----------|
```

- ✅ **如果顯示上述信息** → 驅動已正確安裝
- ❌ **如果出現「找不到 nvidia-smi」或「驅動未安裝」** → 執行下述步驟：

**安裝或更新驅動：**

1. 訪問 [NVIDIA 驅動下載](https://www.nvidia.com/Download/driverDetails.aspx/199537)
2. 選擇您的 GPU 型號（RTX 4090）
3. 下載最新驅動（建議版本 ≥ 552）
4. 執行安裝程式
5. 選擇「Custom」安裝並勾選「Perform a clean install」
6. 重啟電腦
7. 再次執行 `nvidia-smi` 驗證

#### ✅ 4. Git（可選，但推薦）
**用途：** 版本控制，方便日後更新

1. 訪問 [Git 官網](https://git-scm.com/download/win)
2. 下載並安裝
3. 驗證安裝（PowerShell）：

```powershell
git --version
```

#### ✅ 5. Ollama（本地 LLM，可選但推薦用於隱私）
**用途：** 在本機運行 AI 模型，無需雲端 API

**安裝步驟：**

1. 訪問 [Ollama 官網](https://ollama.ai)
2. 點擊「Download」→ 選擇 Windows 版本
3. 執行安裝程式
4. 驗證安裝（PowerShell）：

```powershell
ollama --version
```

5. **下載推薦模型**（一次性，首次啟動時自動進行）：

```powershell
ollama pull gemma3:27b-it-qat
```

> 💡 **什麼是 Gemma3:27b-it-qat？**
> - 這是一個針對繁體中文優化的 AI 模型
> - 下載大小約 16GB（需要約 20GB+ 硬碟空間）
> - 首次下載需要 15-30 分鐘（取決於網路速度）

6. **啟動 Ollama 服務**（保持在後台執行）：

```powershell
ollama serve
```

> ℹ️ 或者直接從「開始菜單」啟動「Ollama」應用

---

## 安裝步驟

### 步驟 1️⃣：下載專案

選擇以下任一方式下載專案：

**方案 A：使用 Git（推薦）**

打開 PowerShell，執行：

```powershell
cd C:\Users\YourUsername\Documents
git clone https://github.com/your-org/convert.git
cd convert
```

**方案 B：直接下載 ZIP**

1. 訪問 GitHub 專案頁面
2. 點擊綠色「Code」按鈕
3. 選擇「Download ZIP」
4. 解壓到您想存放的位置（例如 `C:\Users\YourUsername\Documents\convert`）

### 步驟 2️⃣：進入專案目錄

```powershell
cd C:\Users\YourUsername\Documents\convert
```

### 步驟 3️⃣：配置環境

#### 建立 `.env` 檔案（環境變數配置）

1. 在專案根目錄找到 `.env.example` 檔案
2. 複製此檔案並重命名為 `.env`
3. 用記事本打開 `.env` 檔案
4. 或執行 PowerShell 命令自動複製：

```powershell
Copy-Item .env.example .env
```

#### 配置檔案內容說明

編輯 `.env` 檔案，根據下表進行設定：

| 設定項 | 預設值 | 說明 | 是否需要修改 |
|--------|--------|------|-----------|
| `GEMINI_API_KEY` | （留空） | 雲端模式 API 密鑰，若只使用本地模式可留空 | ❌ 選填 |
| `MAX_FILE_SIZE_MB` | 200 | 單次上傳檔案大小上限（MB） | ✅ 按需調整 |
| `ENABLE_BATCH_UPLOAD` | false | 是否允許多檔批次上傳 | ❌ 通常保留 false |
| `MAX_CONCURRENT_TASKS` | 1 | 同時處理的任務數 | ✅ 按 GPU 記憶體調整 |
| `QUEUE_MAX_SIZE` | 50 | 排隊佇列最大長度 | ❌ 通常保留 50 |
| `OLLAMA_BASE_URL` | http://host.docker.internal:11434 | Ollama 連接地址 | ❌ Windows 預設正確 |
| `LOCAL_LLM_MODEL` | gemma3:27b-it-qat | 使用的 LLM 模型 | ❌ 推薦保留 |

**推薦配置（RTX 4090）：**

```ini
GEMINI_API_KEY=
MAX_FILE_SIZE_MB=200
ENABLE_BATCH_UPLOAD=false
MAX_CONCURRENT_TASKS=1
QUEUE_MAX_SIZE=50
OLLAMA_BASE_URL=http://host.docker.internal:11434
LOCAL_LM_MODEL=gemma3:27b-it-qat
LOG_LEVEL=INFO
DEFAULT_MODE=local
WHISPER_MODEL=medium
WHISPER_DEVICE=auto
```

---

## 配置系統

### 步驟 4️⃣：建構 Docker 映像

Docker 映像是應用的「藍圖」。首次需要建構映像（耗時 10-30 分鐘）。

**執行命令：**

```powershell
.\scripts\deploy.ps1 build
```

**預期輸出：**

您會看到一系列建構進度，最後出現：

```
[OK] 映像建構完成
```

> ⏳ **這會花費時間的原因：**
> - 下載 Python 基礎映像（約 500MB）
> - 安裝 Python 依賴（約 1-2GB）
> - 下載 Whisper 語音轉錄模型（約 1.5GB）

**若建構失敗？** 見 [常見問題排查](#常見問題排查)

### 步驟 5️⃣：啟動服務

建構完成後，啟動應用：

```powershell
.\scripts\deploy.ps1 up
```

**預期輸出：**

```
[INFO] 啟動服務...
[INFO] 等待服務啟動...
等待中... (5 秒)
等待中... (10 秒)
...
[OK] 服務已啟動！

═══════════════════════════════════════════
  🎉 MeetingScribe 已就緒！
═══════════════════════════════════════════
  📍 網址: http://localhost:9527
═══════════════════════════════════════════
```

✅ **恭喜！應用已成功啟動**

---

## 啟動服務

### 打開 Web 介面

1. 打開瀏覽器（Chrome、Edge 或 Firefox）
2. 訪問 `http://localhost:9527`
3. 您應該看到 MeetingScribe 主介面

### 檢查系統狀態

在 Web 介面頂部，您會看到系統狀態欄顯示：

- **系統狀態**：應顯示「正常」（綠色 ✅）
- **GPU**：應顯示「RTX 4090」或類似信息
- **排隊人數**：應顯示「0」

若任何欄位顯示❌，請參考 [常見問題排查](#常見問題排查)

---

## 常見問題排查

### 問題 1️⃣：Docker 顯示「未啟動」或「未連接」

**症狀：**
```
[ERROR] Docker 未啟動，請先啟動 Docker Desktop
```

**解決方案：**

1. 點擊 Windows 工作列右下角的 Docker 圖示 🐳
2. 若圖示未出現，手動啟動 Docker Desktop：
   - 按 `Win + R`
   - 輸入 `docker desktop`
   - 按 Enter

3. 等待 Docker Desktop 完全啟動（通常 30 秒）
4. 重新執行命令

### 問題 2️⃣：GPU 未被識別（顯示 CPU 模式）

**症狀：**
- 網頁介面顯示「GPU: --」或「GPU: CPU」
- 轉錄速度很慢

**診斷步驟：**

1. 打開 PowerShell，執行：

```powershell
nvidia-smi
```

2. 檢查輸出：

| 情況 | 解決方案 |
|------|--------|
| 顯示 GPU 信息（RTX 4090） | ✅ 驅動正常，檢查 Docker GPU 設定 |
| 顯示「找不到命令」| ❌ 驅動未安裝，見[先決條件檢查](#先決條件檢查清單) |
| 顯示「驅動版本 < 520」| ❌ 驅動過舊，升級驅動 |

**若驅動正常但 Docker 仍未使用 GPU：**

1. 打開 Docker Desktop
2. 進入 Settings → Resources
3. 確認 GPU 選項已勾選
4. 點擊「Apply & Restart」
5. 重新啟動應用

### 問題 3️⃣：Ollama 無法連接

**症狀：**
- 選擇「本地模式」後出現連接錯誤
- 網頁顯示「Ollama 未連接」

**診斷步驟：**

1. 確認 Ollama 已啟動：

```powershell
# 查看 Ollama 進程
Get-Process ollama -ErrorAction SilentlyContinue
```

2. 若未顯示進程，手動啟動 Ollama：

```powershell
ollama serve
```

3. 在新 PowerShell 視窗驗證連接：

```powershell
$response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags"
$response
```

4. 若出現模型列表，Ollama 正常運行

**若模型列表為空：**

下載模型：

```powershell
ollama pull gemma3:27b-it-qat
```

### 問題 4️⃣：檔案上傳失敗

**症狀：**
- 上傳檔案後出現錯誤訊息
- 不支援的格式提示

**常見原因及解決：**

| 錯誤信息 | 原因 | 解決方案 |
|--------|------|--------|
| 「檔案大小超過限制」| 檔案 > 200MB | 拆分成更小的檔案，或在 .env 中增加 `MAX_FILE_SIZE_MB` |
| 「檔案格式不支援」| 格式非音訊/視訊 | 使用支援的格式：MP3, WAV, M4A, MP4, MOV 等 |
| 「檔案名稱包含無效字符」| 檔名含特殊字符 | 重命名檔案，使用簡單的英數字 |
| 「服務暫時不可用」| Docker 容器異常 | 執行 `.\scripts\restart-service.ps1` 重啟服務 |

### 問題 5️⃣：轉錄速度很慢

**症狀：**
- 30 分鐘音訊需要 30+ 分鐘才能轉錄
- 預期應該 3-5 分鐘內完成

**診斷步驟：**

1. 檢查 GPU 是否被使用（見問題 2️⃣）

2. 檢查系統資源占用：

```powershell
# 開啟工作管理員
tasklist | findstr "python docker nvidia"
```

3. 檢查硬碟是否飽滿：

```powershell
Get-Volume | where {$_.DriveLetter -eq 'C'} | select DriveLetter,Size,SizeRemaining
```

**優化建議：**

| 措施 | 預期效果 |
|------|--------|
| 確保 GPU 被使用 | 速度提升 5-10 倍 |
| 關閉其他程式 | 釋放 RAM 和 CPU |
| 增加 SSD 空間 | 加快 I/O 操作 |
| 減少同時處理數 (`MAX_CONCURRENT_TASKS=1`) | 穩定性提升 |

### 問題 6️⃣：Web 介面無法打開

**症狀：**
- 無法訪問 `http://localhost:9527`
- 瀏覽器顯示「連接被拒絕」

**解決方案：**

1. 檢查容器是否正在運行：

```powershell
docker ps | findstr "meetingscribe"
```

2. 若無輸出，表示容器已停止。重啟：

```powershell
.\scripts\deploy.ps1 up
```

3. 檢查端口是否被佔用：

```powershell
netstat -ano | findstr "9527"
```

4. 若有其他進程佔用端口 9527，執行：

```powershell
# 終止佔用端口的進程（請注意 PID）
taskkill /PID <PID> /F
```

5. 重新啟動服務

### 問題 7️⃣：建構失敗（docker build error）

**症狀：**
```
[ERROR] 映像建構失敗
```

**常見原因和解決：**

| 原因 | 解決方案 |
|------|--------|
| 磁碟空間不足 | 清理 C: 盤，至少預留 50GB 可用空間 |
| 網路連接中斷 | 確認網路正常，重新執行建構 |
| Docker 資源限制 | 增加 Docker 記憶體上限（Settings → Resources） |
| 依賴下載失敗 | 嘗試手動重新建構：`docker system prune`，然後重新執行 |

**重新建構（清潔版）：**

```powershell
docker system prune -f
docker volume prune -f
.\scripts\deploy.ps1 build
```

---

## 使用方法

### 上傳音訊檔案

1. 在 Web 介面點擊「選擇檔案」或拖曳音訊檔案
2. 選擇處理模式：
   - **方案 A（本地模式）**：使用本機 Ollama（隱私，無網路費用）
   - **方案 B（雲端模式）**：使用 Google Gemini（高品質，需 API Key）

3. 輸入自訂提示（可選）：
   ```
   例如：請特別關注決議事項和待辦事項
   ```

4. 點擊「上傳」

### 查看進度

- Web 介面實時顯示進度條
- 您可以在「任務列表」查看所有任務狀態

### 下載結果

- 轉錄完成後，自動生成 Markdown 格式報告
- 點擊「下載」即可獲取結果檔案

---

## 性能優化

### 針對 RTX 4090 的最佳實踐

#### 配置建議

編輯 `.env` 檔案：

```ini
# 同時處理任務數（RTX 4090 有 24GB VRAM，可設 2-3）
MAX_CONCURRENT_TASKS=1

# 檔案大小限制（可提升至 500MB）
MAX_FILE_SIZE_MB=500

# Whisper 精度設定（float16 = 標準，int8 = 節省 VRAM）
# 通常保留 auto 讓系統自動選擇
WHISPER_DEVICE=auto
```

#### 預期性能

| 音訊時長 | GPU 模式 | CPU 模式 | 模型品質 |
|---------|---------|---------|--------|
| 30 分鐘 | ~3 分鐘 | ~15 分鐘 | 高 |
| 60 分鐘 | ~6 分鐘 | ~30 分鐘 | 高 |
| 120 分鐘 | ~12 分鐘 | ~60 分鐘 | 高 |

### 記憶體最佳化

若遇到「記憶體不足」錯誤：

1. 減少 `MAX_CONCURRENT_TASKS` 至 1
2. 使用較小的 Whisper 模型（編輯 config.yaml）：

```yaml
whisper:
  model: "base"  # 改為 base 而非 medium
```

3. 重啟容器

### GPU 監控

監控 GPU 使用情況：

```powershell
# 持續監控（每秒更新）
nvidia-smi -l 1

# 或查看詳細進程
nvidia-smi pmon
```

---

## 系統管理

### 常用管理命令

#### 查看服務狀態

```powershell
.\scripts\health-check.ps1
```

**輸出範例：**
```
1. Docker 狀態
   ✅ Docker 運行中

2. MeetingScribe 服務
   ✅ 服務運行中 (健康)

3. Ollama 服務（本地模式）
   ✅ Ollama 運行中

4. GPU 狀態
   ✅ GPU: NVIDIA RTX 4090
      記憶體：24GB 可用 / 24GB 總計

5. Gemini API Key（雲端模式）
   ⚠️ API Key 未設定

6. 網頁服務
   ✅ 網頁服務正常
      網址：http://localhost:9527
```

#### 停止服務

```powershell
.\scripts\deploy.ps1 down
```

#### 重啟服務

```powershell
.\scripts\deploy.ps1 restart
```

#### 查看服務日誌

```powershell
.\scripts\deploy.ps1 logs
```

**日誌說明：**
- `INFO`：正常信息
- `WARNING`：警告，但不影響運行
- `ERROR`：錯誤，需要立即處理

#### 設定 Gemini API Key（雲端模式）

若想使用高級的「雲端模式」（基於 Google Gemini）：

```powershell
.\scripts\setup-api-key.ps1
```

系統會引導您：
1. 訪問 Google Gemini API 密鑰頁面
2. 建立 API 密鑰
3. 貼上密鑰
4. 自動保存到 `.env` 檔案

### 資料備份

#### 備份用戶資料

所有上傳和結果檔案存放在 `data/` 資料夾：

```powershell
# 複製整個資料夾作為備份
Copy-Item -Recurse data/ data.backup
```

#### 清理舊檔案

系統會自動清理超過 7 天的檔案。手動清理：

```powershell
# 通過 API 觸發清理
Invoke-RestMethod -Uri "http://localhost:9527/api/storage/cleanup" -Method POST
```

### 更新應用

#### 拉取最新代碼

```powershell
git pull origin main
```

#### 重新建構映像

```powershell
.\scripts\deploy.ps1 build
```

#### 重啟服務以應用更新

```powershell
.\scripts\deploy.ps1 restart
```

---

## 📞 故障排除快速參考

| 問題 | 快速修復 |
|------|--------|
| 服務無法啟動 | `.\scripts\deploy.ps1 restart` |
| Web 無法訪問 | `docker ps` 檢查容器狀態 |
| GPU 未被使用 | 檢查 `nvidia-smi` 和 Docker 設定 |
| Ollama 連接失敗 | 啟動 Ollama：`ollama serve` |
| 檔案上傳失敗 | 檢查檔案大小和格式 |
| 轉錄速度慢 | 確保 GPU 被使用，見性能優化 |

---

## 📚 進階資源

### API 文件

完整的 REST API 文件見 `doc/` 資料夾中的相應檔案。

**常用 API 端點：**

```bash
# 上傳檔案
curl -X POST http://localhost:9527/api/upload \
  -F "file=@meeting.mp3" \
  -F "processing_mode=local"

# 查詢任務狀態
curl http://localhost:9527/api/tasks/{task_id}

# 下載結果
curl http://localhost:9527/api/tasks/{task_id}/result > result.md
```

### WebSocket 實時推送

監聽實時進度：

```javascript
const ws = new WebSocket("ws://localhost:9527/ws/tasks/{task_id}");
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`進度: ${data.progress}%`);
};
```

### 自訂系統提示詞

編輯 `config.yaml` 的 `system_prompt` 欄位以自訂 AI 摘要風格。

---

## ⚠️ 安全性提醒

### 保護您的資料

1. **API Key 安全**：
   - 不要在公開場合分享 API Key
   - `.env` 檔案已自動加入 `.gitignore`（不會上傳到 GitHub）

2. **本地 vs 雲端**：
   - **本地模式**（Ollama）：資料完全保留在您的電腦
   - **雲端模式**（Gemini）：音訊逐字稿會傳送到 Google 伺服器

3. **檔案清理**：
   - 系統自動清理 7 天前的檔案
   - 機敏資料建議手動刪除

---

## 🎓 學習資源

### 推薦閱讀

- [Docker 官方指南](https://docs.docker.com/)
- [NVIDIA CUDA 文件](https://docs.nvidia.com/cuda/)
- [Ollama 官方文件](https://ollama.ai)

### 社群支援

遇到問題？提交 Issue 或 Pull Request 到項目 GitHub 頁面。

---

## 📋 更新紀錄

| 版本 | 日期 | 變更 |
|------|------|------|
| v2.3.6 | 2025-12 | Windows RTX 4090 專用完整指南 |
| v2.3 | 2025-11 | 新增 GPU 支援和性能優化 |
| v2.1 | 2025-10 | 新增排隊系統 |

---

## ✅ 部署檢查清單

在啟動前，請確認以下項目已完成：

- [ ] Docker Desktop 已安裝並運行
- [ ] NVIDIA 驅動已安裝（版本 ≥ 520）
- [ ] Docker GPU 支援已啟用
- [ ] Ollama 已安裝（若使用本地模式）
- [ ] Gemma3 模型已下載（若使用本地模式）
- [ ] 專案代碼已下載到本地
- [ ] `.env` 檔案已配置
- [ ] Docker 映像已成功建構
- [ ] 服務已成功啟動
- [ ] Web 介面可以訪問（http://localhost:9527）
- [ ] 健康檢查通過（`.\scripts\health-check.ps1`）

✅ **所有項目完成後，您可以開始使用 MeetingScribe！**

---

<div align="center">

**Made with ❤️ for better meetings**

📧 有問題？提交 Issue 或聯絡維護者

⭐ 如果本指南對您有幫助，請給予支持

</div>

---

## 附錄：檔案結構說明

```
convert/
├── scripts/                      # Windows 管理腳本
│   ├── deploy.ps1              # 部署工具（build/up/down/restart）
│   ├── health-check.ps1        # 系統健康檢查
│   ├── setup-api-key.ps1       # Gemini API Key 設定
│   └── restart-service.ps1     # 安全重啟服務
│
├── docker/                       # Docker 配置
│   ├── Dockerfile              # 應用映像定義
│   └── docker-compose.yml      # Windows/Linux 通用版
│
├── backend/                      # 後端程式碼
│   ├── main.py                 # FastAPI 主應用
│   ├── api/                    # REST API 和 WebSocket
│   ├── services/               # 核心服務
│   └── core/                   # 配置和日誌
│
├── frontend/                     # Web 介面
│   ├── index.html              # 主頁面
│   ├── css/style.css           # 樣式
│   └── js/app.js               # 前端邏輯
│
├── data/                         # 資料目錄（自動建立）
│   ├── uploads/                # 上傳的音訊/視訊檔案
│   ├── outputs/                # 生成的摘要結果
│   └── cache/                  # 轉錄快取
│
├── config.yaml                   # 系統配置（Whisper、LLM 設定）
├── .env.example                 # 環境變數範本
└── requirements.txt             # Python 依賴
```

---

**祝您使用愉快！** 🎉
