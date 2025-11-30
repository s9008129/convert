# MeetingScribe v2.2.1

<div align="center">

![MeetingScribe Logo](https://img.shields.io/badge/MeetingScribe-v2.2.1-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-green?style=flat-square&logo=python)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=flat-square&logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**將會議錄音轉換為結構化會議記錄的跨平台 Docker 服務**

[快速開始](#-快速開始) • [功能特色](#-功能特色) • [部署指南](#-部署指南) • [API 文件](#-api-文件) • [快速部署指南](doc/快速部署指南.md) • [MAC 部署指南](doc/MAC_Docker部署指南.md)

</div>

---

## 🎯 簡介

MeetingScribe 是一個企業級會議轉錄工具，採用 Docker 容器化部署，實現「一包帶走，直接部署」的目標。支援跨 Windows、macOS、Linux 平台無縫部署，**完全隔離執行環境，絕對不影響主機其他 Docker 服務**。

### 🔒 v2.2.1 新功能

- ✅ **WebSocket 即時進度推送**: 後端主動推送進度更新，前端即時顯示處理狀態
- ✅ **優化排隊狀態顯示**: 移除不準確的預估時間，改為顯示「即將處理」或「排隊中」
- ✅ **開發模式 Volume Mount**: 前端/後端程式碼變更無需重建 Docker 映像
- ✅ **前端穩定性提升**: 所有 DOM 操作添加 null 安全檢查

### 🔒 隔離保證（首要任務）

- ✅ **獨立網路**: 使用專屬 Docker 網路 `meetingscribe-network` (172.30.0.0/16)
- ✅ **獨立命名**: 所有容器、Volume、網路都使用 `meetingscribe-` 前綴
- ✅ **完全隔離**: 不與其他 Docker 專案共用任何資源

### 核心特點

- 🔒 **本地模式**：完全離線處理，使用 Ollama + Gemma3:12B，資料不外傳，適合機敏資料
- ☁️ **雲端模式**：使用 Gemini API，高品質摘要輸出，適合一般會議
- 🛡️ **完全隔離**：獨立網路和命名空間，絕對不影響其他 Docker 服務
- 🖥️ **智能偵測**：自動偵測 CUDA GPU、Apple MPS、CPU，資源不足時自動降級
- 📊 **排隊系統**：支援多用戶同時使用，FIFO 公平排隊，前端即時顯示進度
- 🎨 **Apple 風格 UI**：簡約現代的使用者介面
- 📝 **自訂 Prompt**：使用者可自訂會議記錄格式和內容
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
   ollama pull gemma3:12b
   ```
3. （可選）取得 [Gemini API Key](https://ai.google.dev/) 用於雲端模式

### 三步驟部署

```powershell
# 1. 建構映像（首次約 10-30 分鐘）
cd scripts
.\deploy.ps1 build

# 2. 啟動服務
.\deploy.ps1 up

# 3. 開啟瀏覽器
# 訪問 http://localhost:9527
```

---

## ✨ 功能特色

### 🔄 雙模式處理

| 模式 | 說明 | 適用場景 | 優點 | 缺點 |
|------|------|----------|------|------|
| 🔒 本地模式 | Ollama + Gemma3:12B | 政府、醫療、商業機密 | 資料安全、無延遲 | 品質一般 |
| ☁️ 雲端模式 | Gemini API | 一般會議、非機敏 | 品質優良 | 需網路、隱私 |

### 📝 自訂 Prompt

使用者可自訂會議記錄格式：
- 指定輸出項目（決議事項、待辦清單、參與者等）
- 調整摘要長度和風格
- 新增特殊要求或專業術語

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
| `WHISPER_MODEL` | Whisper 模型 | large-v3 | tiny/base/small/medium/large-v3 |
| `LOCAL_LLM_MODEL` | 本地 LLM 模型 | gemma3:12b | ollama 支援的任何模型 |

### 服務管理腳本（Windows PowerShell）

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

---

## 📚 API 文件

### REST API 端點

| 端點 | 方法 | 說明 | 身份驗證 |
|------|------|------|--------|
| `/api/health` | GET | 健康檢查 | 無 |
| `/api/config` | GET | 取得系統配置 | 無 |
| `/api/upload` | POST | 上傳音訊/視訊檔案 | 無 |
| `/api/tasks/{task_id}` | GET | 查詢任務狀態 | 無 |
| `/api/tasks/{task_id}/result` | GET | 下載結果（Markdown） | 無 |
| `/api/queue/status` | GET | 排隊狀態 | 無 |

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
- 考慮使用較小的 Whisper 模型（修改環境變數 `WHISPER_MODEL=base`）
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

[⬆ 回到頂部](#meetingscribe-v220)

</div>
