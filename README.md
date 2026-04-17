# MeetingScribe v3.5.0

<div align="center">

![MeetingScribe Logo](https://img.shields.io/badge/MeetingScribe-v3.5.0-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-green?style=flat-square&logo=python)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=flat-square&logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**將會議錄音轉換為結構化會議記錄的跨平台 Docker 服務**

[快速開始](#-快速開始) • [功能特色](#-功能特色) • [部署指南](#-部署指南) • [API 文件](#-api-文件) • [快速部署指南](doc/快速部署指南.md) • [MAC 部署指南](doc/MAC_Docker部署指南.md) • [批次檔部署指南](doc/Windows批次檔部署指南.md) • [Docker Rebuild 指南](doc/Docker映像檔Rebuild時機指南.md)

</div>

---

## 🎯 簡介

MeetingScribe 是一個企業級會議轉錄工具，採用 Docker 容器化部署，實現「一包帶走，直接部署」的目標。支援跨 Windows、macOS、Linux 平台無縫部署，**完全隔離執行環境，絕對不影響主機其他 Docker 服務**。

### 🆕 近期更新：ASR 引擎升級至 Breeze-ASR-26 + Gemma4 本地模式

- 🎤 **ASR 引擎升級至 `MediaTek-Research/Breeze-ASR-26`**：官方 Transformers 管線，台語辨識相似度達 92.8%，保留 `faster-whisper` / ASR-25 回滾能力。詳見 [Breeze-ASR-26 驗收報告](驗收報告.md)
- ✅ **多語言混合驗證**：自動化腳本產生中文 / 英文 / 台語混合音檔，支援 `full-asr` 與 `taigi-priority` 驗收模式，並輸出台語標記逐字稿 / 會議記錄（`scripts/run_asr26_validation.py`）
- ✅ **模型版本鎖定與快取隔離**：`model_revision` 固定 + 後端感知的 transcript cache 簽章，避免升級誤用舊快取
- ✅ **本地模式預設改為 `gemma4:31b`**：Windows / RTX 4090 已完成實機驗證；若只安裝 `gemma4:31b-it-q4_K_M` 等相容標籤，後端會自動解析
- ✅ **台灣繁體中文摘要再優化**：沿用 extraction → merge → refine 管線，強化繁中約束、移除 thought tags，並降低簡繁體誤判
- ✅ **DOCX 下載問題根因修復**：前端改用 `fetch` + `blob`，後端補上 `python-docx` ImportError 處理，不再出現只拿到 JSON 錯誤內容
- ✅ **結果頁改為純下載流程**：移除內嵌 Markdown 預覽與複製按鈕，完成後僅保留下載 Markdown / DOCX
- ✅ **macOS 路徑保留支援**：可透過 `.env.local` 的 `LOCAL_LLM_MODEL_MAC` 覆寫較小的 Gemma4 標籤

### 🆕 v3.4.1 簡化設計：完全移除自訂格式功能

- ✅ **移除自訂會議記錄格式**：不再支援上傳格式範本或手動格式要求
- ✅ **統一預設格式**：所有會議記錄採用系統預設 COSTAR-A 框架
- ✅ **降低複雜度**：系統更穩定，無格式相關問題
- ✅ **提升品質**：專注優化預設格式的輸出品質
- ⚠️ **需要 Docker 重建**：前後端代碼均有變更，請執行 `docker-compose up -d --build`

### 🔄 v3.4.0 重大修復：GPU 加速 + VRAM 管理

- ✅ **修復 Whisper GPU 加速失效**：每次轉錄強制重新偵測裝置，解決快取導致的 GPU 不可用問題
- ✅ **實現 VRAM 資源釋放機制**：Whisper 轉錄後自動釋放、Ollama 使用完畢立即釋放
- ✅ **優化本地模式品質**：num_ctx 16384 + temperature 0.05 + repeat_penalty 1.2

### 🆕 v3.3.3 解決 Windows PowerShell 執行政策問題

- ✅ **完全規避 PowerShell 執行政策限制**：用純批次檔替代 PowerShell 腳本
- ✅ **無需修改系統設定**：無需管理員權限，無需更改執行政策
- ✅ **企業環境相容**：即使在受 GPO 限制的企業環境也能正常運作
- ✅ **完整部署指南**：新增 [Windows 批次檔部署指南](doc/Windows批次檔部署指南.md)

### 🆕 v3.3.1 修復：地端模式結果預覽一致性

- ✅ **修復地端模式結果預覽缺失**：地端和雲端模式現在提供一致的結果預覽顯示
- ✅ **WebSocket 連接時序問題解決**：無論任務何時完成，都能確保預覽內容傳遞
- ✅ **用戶體驗一致性**：兩種模式都能在完成時顯示詳細結果預覽

### 🆕 v3.3.0 新增：地端模型品質大幅優化

- ✅ **地端品質提升至雲端 70%+**：透過多層次改善策略，縮小地端與雲端品質差距
- ✅ **Whisper 轉錄層優化**：修正 `initial_prompt` 污染問題，避免指令混入逐字稿
- ✅ **Prompt Engineering 重構**：移除 XML 標籤，改用 Markdown 格式，提升地端模型遵循度
- ✅ **Ollama API 參數優化**：擴大上下文視窗、增加重複懲罰、設定停止標記
- ✅ **DOCX 下載功能**：處理完成後可下載 Markdown 或 DOCX 版本會議記錄
- ✅ **輸出後處理機制**：清理 LLM 無用前綴，確保結構完整性
- ✅ **完整品質比對報告**：詳見 [地端雲端會議記錄品質比對報告](doc/地端雲端會議記錄品質比對報告.md)

### 🆕 v3.2.0 新增：Gemini API 分層智能連線測試方案

- ✅ **分層智能檢查**：三層檢查機制（本地檢查 + 每日健康檢查 + 用戶發起驗證）
- ✅ **最小成本設計**：每日僅 1 次 API 調用，100+ 用戶無須超出 1000 次/天配額
- ✅ **自動快取機制**：24 小時快取健康檢查結果，多用戶共享快取
- ✅ **新增 API 端點**：`GET /api/gemini/health` 供定時任務調用
- ✅ **完整文檔**：詳見 [Gemini API 連線測試方案](doc/系統開發及實作規劃.md)

### 🇹🇼 v3.1.0 重大改進：英文混入根本修復

- ✅ **英文混入問題根本修復**：採用分層防禦機制，確保 100% 繁體中文輸出
- ✅ **提示詞全中文化**：移除英文 tag，添加明確禁止和自檢清單
- ✅ **低溫約束**：Gemma3:27b 溫度調至 0.1，強制中文輸出
- ✅ **自動清理機制**：三層清理（段落移除 + 詞彙替換 + 英文檢測）
- ✅ **完整驗證報告**：詳見 [英文修復驗證報告](ENGLISH_FIX_VERIFICATION.md)

### 🇹🇼 v2.3.8 新功能：提升檔案上傳限制至 200MB

- ✅ **檔案上傳限制提升**: 從 100MB 提升至 200MB，支援更大型會議錄音
- ✅ **環境變數可配置**: 通過 `.env` 檔案或環境變數靈活調整限制
- ✅ **動態前端驗證**: 前端自動讀取 API 配置，無須手動維護

### 🔒 隔離保證（首要任務）

- ✅ **獨立網路**: 使用專屬 Docker 網路 `meetingscribe-network` (172.30.0.0/16)
- ✅ **獨立命名**: 所有容器、Volume、網路都使用 `meetingscribe-` 前綴
- ✅ **完全隔離**: 不與其他 Docker 專案共用任何資源

### 核心特點

- 🇹🇼 **台灣繁體中文**：轉錄輸出為台灣正體中文，非簡體
- 🔒 **多種本地 LLM**：支援 Ollama（預設 `gemma4:31b`，可自動解析已安裝的 Gemma4 相容標籤）、LM Studio (`gpt-oss-20b`)，完全離線，資料不外傳
- ☁️ **雲端模式**：使用 Gemini API，高品質摘要輸出，適合一般會議
- 🛡️ **完全隔離**：獨立網路和命名空間，絕對不影響其他 Docker 服務
- 🖥️ **智能偵測**：自動偵測 CUDA GPU、Apple MPS、CPU，資源不足時自動降級
- 📊 **排隊系統**：支援多用戶同時使用，FIFO 公平排隊，前端即時顯示進度
- 🧹 **自動清理**：上傳檔保留 1 天、輸出保留 7 天、快取保留 30 天
- 🎨 **Apple 風格 UI**：簡約現代的使用者介面
- 📄 **結果下載**：處理完成後提供 Markdown 與 DOCX 下載，結果頁不內嵌預覽
- 🔐 **企業級安全**：API Key 安全存儲，路徑遍歷防護，XSS 防衛

---

## 🚀 快速開始

### 系統需求

| 項目 | 最低需求 | 建議配置 |
|------|----------|----------|
| 作業系統 | Windows 10/11, macOS 10.15+, Linux | Windows 11 / Ubuntu 20.04+ |
| Docker | Docker Desktop 4.0+ | 最新版本 |
| GPU | 無（CPU 模式）| NVIDIA RTX 4090 |
| 記憶體 | 8GB | 32GB |
| 磁碟空間 | 20GB | 50GB |

### 前置準備

1. 安裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. 安裝 [Ollama](https://ollama.ai/) 並下載模型：
   ```bash
   ollama pull gemma4:31b
   ```
   > 💡 若您只安裝 `gemma4:31b-it-q4_K_M` 等 Gemma4 相容標籤，本專案會自動優先解析已安裝的 Gemma4 模型。
3. （可選）取得 [Gemini API Key](https://ai.google.dev/) 用於雲端模式

### 三步驟部署

#### Windows 系統（推薦 ✅ v3.3.3+）

```batch
# 1. 建構映像（首次約 10-30 分鐘）
cd scripts
deploy.bat build

# 2. 啟動服務
deploy.bat up

# 3. 開啟瀏覽器
# 訪問 http://localhost:9527
```

> 💡 **GPU 自動偵測**：
> 
> `deploy.bat` 會自動偵測您的系統是否有 NVIDIA GPU：
> - **有 GPU**：自動使用 `docker-compose-windows-gpu.yml`，預設切到官方 `MediaTek-Research/Breeze-ASR-26`
> - **無 GPU**：使用標準 `docker-compose.yml`，維持 `faster-whisper` / Breeze-ASR-25 保守路徑
> 
> 無需手動選擇，一個指令即可完成！

> 🚀 **部署前建議先預載官方模型**
>
> ```batch
> python scripts\download_models.py
> ```
>
> 此腳本會使用固定 revision 與 safetensors allowlist 下載官方 ASR-26，避免執行期臨時抓取未鎖版模型。

> ⚠️ **Windows PowerShell 執行策略問題**？
> 
> 如果遇到 "Cannot be loaded because running scripts is disabled on this system" 錯誤，請使用 `deploy.bat` 批次檔替代 `deploy.ps1`。
> 
> **原因**：系統 PowerShell 執行策略設定為 `Restricted`，無法執行本地腳本。`deploy.bat` 不受 PowerShell 策略限制，可直接執行。
> 
> 詳見：[Windows 批次檔部署指南](./doc/Windows批次檔部署指南.md)

#### macOS（推薦使用專用腳本）

```bash
./scripts/start-mac.sh
```

> 💡 若您的 Mac 記憶體較小，可先在 `.env.local` 設定 `LOCAL_LLM_MODEL_MAC=gemma4:<較小標籤>`，再執行 `ollama pull` 下載對應標籤。

---

## ✨ 功能特色

### 🔄 雙模式處理

| 模式 | 說明 | 適用場景 | 優點 | 缺點 |
|------|------|----------|------|------|
| 🔒 本地模式 | Ollama + Gemma4:31B 家族 | 政府、醫療、商業機密 | 完全離線、台灣繁中品質佳 | 記憶體需求較高 |
| ☁️ 雲端模式 | Gemini API | 一般會議、非機敏 | 品質優良 | 需網路、隱私 |

### 📄 結果下載

處理完成後，結果頁提供：
- Markdown 檔案下載
- DOCX 檔案下載
- 重新開始

> 目前結果頁不再內嵌 Markdown 預覽，也不提供複製按鈕；所有下載錯誤都會以明確訊息回報。

### 📊 智能排隊系統

- **FIFO 公平排隊**：先進先出，保證公平性
- **即時顯示**：前端實時顯示排隊位置和預估時間
- **併發控制**：可配置同時處理任務數（預設 1）

### 🎛️ 自動裝置偵測

```
優先順序：CUDA GPU → Apple MPS → CPU
自動降級：若 GPU 記憶體 < 4GB → 切換到 CPU 模式
逾時保護：若 GPU 超時 30 秒 → 降級到 CPU 模式
```

---

## 📦 部署指南

### Docker Compose 部署

```yaml
services:
  meetingscribe:
    build: ./docker
    container_name: meetingscribe-app
    ports:
      - "9527:9527"
    volumes:
      - ./data:/app/data
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - MAX_FILE_SIZE_MB=100
      - ENABLE_BATCH_UPLOAD=false
    restart: unless-stopped
    networks:
      - app-network
```

### 環境變數配置

複製 `.env.example` 為 `.env`，設定以下參數：

| 變數 | 說明 | 預設值 | 範圍 |
|------|------|--------|------|
| `MAX_FILE_SIZE_MB` | 單檔大小上限 | 100 | 1-1024 |
| `ENABLE_BATCH_UPLOAD` | 批次上傳 | false | true/false |
| `MAX_CONCURRENT_TASKS` | 同時處理數 | 1 | 1-10 |
| `QUEUE_MAX_SIZE` | 排隊上限 | 50 | 1-1000 |
| `GEMINI_API_KEY` | Gemini API 金鑰 | - | 必要（雲端模式） |
| `ASR_BACKEND` | ASR 後端 | auto | auto / transformers / faster_whisper |
| `WHISPER_MODEL` | Whisper / ASR 模型 | MediaTek-Research/Breeze-ASR-26 | Hugging Face repo 或 faster-whisper 模型 |
| `WHISPER_MODEL_REVISION` | 官方模型版本鎖定 | 949c87bca9dbe90e160cf739460cc765e80805f3 | 建議固定 commit SHA |
| `WHISPER_LANGUAGE` | 語言提示 | auto | auto / zh / en / ... |
| `LOCAL_LLM_MODEL` | 本地 LLM 模型 | gemma4:31b | ollama 支援的任何模型 |
| `LOCAL_LLM_MODEL_MAC` | macOS 覆寫模型 | （留空） | 小記憶體 Mac 可指定較小 Gemma4 標籤 |

### 服務管理腳本

#### Windows （批次檔 - 推薦 ✅ v3.3.3+）

```batch
# 設定 API Key（雲端模式）
scripts\setup-api-key.ps1

# 重啟服務（不影響其他 Docker 服務）
scripts\restart-service.ps1

# 健康檢查
scripts\health-check.bat

# 部署工具（自動偵測 GPU）
scripts\deploy.bat [build|up|down|restart|status|logs]

# GPU 偵測說明：
# - deploy.bat 會自動檢測 NVIDIA GPU
# - 有 GPU：自動使用 GPU 加速版本
# - 無 GPU：自動使用 CPU 版本
# - 無需手動指定配置文件
```

#### Windows （PowerShell - 舊版本）

```powershell
# 設定 API Key（雲端模式）
.\scripts\setup-api-key.ps1

# 重啟服務（不影響其他 Docker 服務）
.\scripts\restart-service.ps1

# 健康檢查
.\scripts\health-check.ps1

# 部署工具
.\scripts\deploy.ps1 [build|up|down|restart|status|logs]
```

> ℹ️ v3.3.3 版本新增 `deploy.bat` 批次檔，解決 Windows PowerShell 執行策略問題。優先使用批次檔。

#### macOS / Linux

```bash
# 重啟服務
./scripts/restart-mac.sh

# 健康檢查
bash ./scripts/health-check.sh

# 部署工具
bash ./scripts/deploy.sh [build|up|down|restart|status|logs]
```

### ASR-26 驗收腳本

```batch
python scripts\run_asr26_validation.py --target-duration-seconds 600
```

此腳本會產生約 10 分鐘的繁中 / 英文 / 台語混合驗證音檔，並輸出：

1. `data\validation\*_manifest.json`
2. `data\validation\*_validation_transcript.md`
3. `data\validation\*_validation_notes.md`

驗證產物內會明確標註台語 / 閩南語段落；正式產品輸出仍不含這些測試標記。

---

## 📚 API 文件

### REST API 端點

| 端點 | 方法 | 說明 | 身份驗證 |
|------|------|------|--------|
| `/api/health` | GET | 健康檢查 | 無 |
| `/api/config` | GET | 取得系統配置 | 無 |
| `/api/upload` | POST | 上傳音訊/視訊檔案 | 無 |
| `/api/tasks/{task_id}` | GET | 查詢任務狀態 | 無 |
| `/api/tasks/{task_id}/result` | GET | 下載結果（預設 Markdown，支援 `?format=docx`） | 無 |
| `/api/queue/status` | GET | 排隊狀態 | 無 |
| `/api/storage/stats` | GET | 儲存空間使用統計 | 無 |
| `/api/storage/cleanup` | POST | 手動觸發檔案清理 | 無 |

### WebSocket 即時推送

```
ws://localhost:9527/ws/tasks/{task_id}
```

接收實時進度更新：
```json
{
  "status": "processing",
  "progress": 45,
  "stage": "summarizing",
  "message": "正在產製摘要..."
}
```

### 上傳檔案範例

```bash
curl -X POST http://localhost:9527/api/upload \
  -F "file=@meeting.mp3" \
  -F "processing_mode=local" \
  -F "user_prompt=請列出所有決議事項和負責人"
```

### 回應範例

```json
{
  "task_id": "task-20251129-abc123",
  "status": "queued",
  "queue_position": 2,
  "estimated_wait_seconds": 180,
  "file_size_mb": 45.5
}
```

---

## 🏗️ 專案結構

```
convert/
├── backend/                         # 後端服務（FastAPI）
│   ├── api/                         # API 路由
│   │   ├── routes.py               # REST API 端點
│   │   └── websocket.py            # WebSocket 進度推送
│   ├── core/                        # 核心模組
│   │   ├── config.py               # 參數化配置
│   │   └── logger.py               # 日誌系統
│   ├── models/                      # 資料模型
│   │   └── schemas.py              # Pydantic 資料模型
│   ├── services/                    # 業務邏輯
│   │   ├── device_detector.py      # 裝置偵測和降級
│   │   ├── queue_manager.py        # 排隊系統
│   │   ├── transcription.py        # Whisper 轉錄
│   │   ├── summarization.py        # LLM 摘要（本地/雲端）
│   │   ├── file_manager.py         # 檔案管理和安全驗證
│   │   └── task_processor.py       # 任務處理流程
│   └── main.py                      # FastAPI 主應用
│
├── frontend/                        # 前端介面
│   ├── css/
│   │   └── style.css               # Apple 風格 CSS
│   ├── js/
│   │   └── app.js                  # 前端邏輯（Vue-like）
│   └── index.html                  # 主頁面
│
├── docker/                          # Docker 配置
│   ├── Dockerfile                  # 映像定義
│   └── docker-compose.yml          # 容器編排
│
├── scripts/                         # 管理腳本
│   ├── deploy.ps1                  # 部署工具
│   ├── setup-api-key.ps1           # API Key 設定
│   ├── restart-service.ps1         # 安全重啟
│   └── health-check.ps1            # 健康檢查
│
├── data/                            # 資料目錄
│   ├── uploads/                    # 上傳檔案
│   ├── outputs/                    # 處理結果
│   └── cache/                      # 快取檔案
│
├── doc/                             # 文件
│   ├── 規劃和實作計劃.md            # 完整規劃
│   ├── 系統開發及實作規劃.md        # 詳細開發規劃
│   ├── 快速部署指南.md              # Windows 快速部署（非技術人員友善）
│   ├── 快速入門指南.md              # 快速入門
│   ├── DESIGN.md                   # 架構設計
│   └── Docker部署經驗指南.md       # Docker 經驗
│
└── requirements.txt                 # Python 依賴
```

---

## 🔧 故障排除

### 常見問題

**Q: 服務無法啟動？**

```powershell
# 查看詳細日誌
docker compose logs -f

# 執行健康檢查
.\scripts\health-check.ps1

# 確認 Docker Desktop 運行
docker ps
```

**Q: GPU 沒有被使用？**

- 確認 NVIDIA 驅動版本 >= 520
- 確認 Docker Desktop 設定中啟用 GPU 支援（Settings → Resources → GPU）
- 查看日誌確認 CUDA 初始化
- 系統會自動降級到 CPU 模式，檔案轉錄仍可正常運行

**Q: 雲端模式不可用？**

```powershell
# 設定 API Key
.\scripts\setup-api-key.ps1

# 驗證配置
curl http://localhost:9527/api/config | findstr gemini_available
```

**Q: 處理速度很慢？**

- 建議使用 GPU 模式（確認 NVIDIA 驅動已安裝）
- 嘗試減少 `MAX_CONCURRENT_TASKS` 以節省記憶體
- 若需快速回滾，可設定 `ASR_BACKEND=faster_whisper` 與 `WHISPER_MODEL=SoybeanMilk/faster-whisper-Breeze-ASR-25`
- 檢查磁碟 I/O 是否為瓶頸

**Q: 檔案上傳失敗「檔案名稱包含無效字符」？**

檔案名稱不能包含 `..`、`/` 或 `\` 字符。重新命名檔案後重試。

---

## 🔐 安全性考量

### 已實施的安全措施

- ✅ API Key 使用 Pydantic `SecretStr` 保護，避免日誌暴露
- ✅ 檔案上傳路徑遍歷防護，防止目錄脫逃攻擊
- ✅ XSS 防衛，前端使用 `textContent` 而非 `innerHTML`
- ✅ 檔案大小驗證，預設 100MB 上限（可配置）
- ✅ 副檔名白名單驗證
- ✅ SHA256 檔案 hash 確保完整性

### 建議的部署安全做法

1. **生產環境**：設定 `DEBUG=false`
2. **API Key**：使用環境變數而非硬碼
3. **網路**：在防火牆後運行，限制 API 訪問
4. **監控**：啟用容器日誌監控和告警
5. **備份**：定期備份 `/data` 目錄

---

## 📊 效能指標

### 典型效能表現（Windows 11 RTX 4090）

| 音訊長度 | GPU 模式 | CPU 模式 | 品質 |
|---------|---------|---------|------|
| 30 分鐘 | ~3 分鐘 | ~15 分鐘 | 高 |
| 60 分鐘 | ~6 分鐘 | ~30 分鐘 | 高 |
| 120 分鐘 | ~12 分鐘 | ~60 分鐘 | 高 |

*實際時間因檔案品質、背景雜音、模型配置而異*

---

## 📄 授權條款

本專案採用 MIT 授權條款。詳見 [LICENSE](LICENSE) 檔案。

---

## 🙏 致謝

感謝以下開源專案的支援：

- [OpenAI Whisper](https://github.com/openai/whisper) - 語音轉文字引擎
- [Ollama](https://ollama.ai/) - 本地 LLM 推理框架
- [FastAPI](https://fastapi.tiangolo.com/) - 現代化 Python Web 框架
- [Google Gemini](https://ai.google.dev/) - 雲端 AI 模型
- [Docker](https://www.docker.com/) - 容器化部署平台

---

## 📞 聯絡和反饋

有任何問題或建議，請提出 Issue 或 Pull Request。

---

<div align="center">

**Made with ❤️ for better meetings**

⭐ 如果本專案對您有幫助，請給予 Star 支持

[⬆ 回到頂部](#meetingscribe-v237)

</div>
