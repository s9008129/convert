# MeetingScribe v3.3.6

<div align="center">

![MeetingScribe Logo](https://img.shields.io/badge/MeetingScribe-v3.3.6-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-green?style=flat-square&logo=python)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=flat-square&logo=docker)
![NVIDIA GPU](https://img.shields.io/badge/GPU-NVIDIA_RTX_4090-green?style=flat-square&logo=nvidia)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**智能會議轉錄與摘要系統 - 完整 Docker 容器化方案**

[快速開始](#-快速開始) | [系統需求](#-系統需求) | [部署指南](#-部署指南) | [API 文檔](#-api-文檔) | [GPU 加速](#-gpu-加速)

</div>

---

## 📋 專案簡介

MeetingScribe 是一個智能會議轉錄系統，提供 Docker 容器化的完整方案。支援 Windows、macOS、Linux 多平台部署。**無需配置任何開發環境，只需要 Docker 即可！**

### 🚀 v3.3.6 重大修復：GPU 加速完全啟用

- ✅ **徹底修復 cuDNN 版本不相容問題**：升級 ctranslate2 到 4.6.1，支援 cuDNN 9
- ✅ **GPU 轉錄性能驗證**：30 秒音訊只需 0.32 秒，**93.7x 實時倍率**
- ✅ **GPU 記憶體正確使用**：運行時使用 ~3GB GPU 記憶體
- ✅ **完整版本相容表**：

| ctranslate2 版本 | cuDNN 版本 | 狀態 |
|-----------------|-----------|------|
| < 4.5.0 | cuDNN 8 | ❌ 不相容 |
| >= 4.5.0 | cuDNN 9 | ✅ 完全支援 |

### 📊 v3.3.5 修復：Docker GPU 映像

- ✅ **創建專用 GPU Dockerfile** (`docker/Dockerfile.gpu`)
- ✅ **使用 NVIDIA CUDA 官方基礎映像**：`nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04`
- ✅ **自動 GPU 偵測**：deploy.bat 自動選擇 GPU compose 檔案

### 🔧 v3.3.3 修復：Windows PowerShell 執行策略

- ✅ **解決 PowerShell 執行策略問題**：使用 deploy.bat 繞過限制
- ✅ **全新批次檔部署**：無需修改系統執行策略

---

## 🎯 核心功能

- 🎙️ **語音轉錄**：使用 Whisper medium 模型，支援中文
- 🤖 **智能摘要**：支援本地 LLM (Ollama) 或雲端 (Gemini API)
- 📊 **即時進度**：WebSocket 即時回報處理進度
- 📁 **批次上傳**：支援多檔案排隊處理
- 🔒 **安全性**：API Key 加密、檔案驗證、XSS 防護

---

## 💻 系統需求

### 最低需求

| 項目 | 需求 |
|------|------|
| 作業系統 | Windows 10/11, macOS 10.15+, Linux |
| Docker | Docker Desktop 4.0+ |
| RAM | 8GB |
| 儲存空間 | 20GB |

### GPU 加速需求（推薦）

| 項目 | 需求 |
|------|------|
| GPU | NVIDIA RTX 4090 或其他 CUDA GPU |
| NVIDIA Driver | >= 520 |
| VRAM | 4GB+ |

---

## 🚀 快速開始

### Windows 部署

```batch
# 1. 建置映像（首次約 10-30 分鐘）
cd scripts
deploy.bat build

# 2. 啟動服務
deploy.bat up

# 3. 開啟瀏覽器
# 訪問 http://localhost:9527
```

### macOS / Linux 部署

```bash
# 1. 建置映像
cd scripts
./deploy.ps1 build

# 2. 啟動服務
./deploy.ps1 up

# 3. 訪問 http://localhost:9527
```

---

## 🎮 GPU 加速

### 驗證 GPU 加速

```bash
# 檢查容器 GPU 狀態
docker exec meetingscribe-app nvidia-smi

# 測試 GPU 轉錄
docker exec meetingscribe-app python -c "
from faster_whisper import WhisperModel
import time

model = WhisperModel('medium', device='cuda', compute_type='float16')
print(f'Device: {model.model.device}')
print('GPU 加速已啟用！')
"
```

### 預期結果

```
============================================================
        GPU 轉錄完整驗證測試
============================================================

[1] ctranslate2 版本與 CUDA 狀態
    ctranslate2 版本: 4.6.1
    CUDA 支援: True
    CUDA 設備數量: 1

[2] Whisper 模型載入測試
    載入時間: 1.21s
    設備: cuda

[3] GPU 轉錄測試 (30 秒音訊)
    轉錄耗時: 0.32s
    即時倍率: 93.7x

✅ GPU 加速驗證成功!
============================================================
```

---

## 📡 API 文檔

### REST API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/health` | GET | 健康檢查 |
| `/api/config` | GET | 取得配置 |
| `/api/upload` | POST | 上傳音訊檔案 |
| `/api/tasks/{task_id}` | GET | 查詢任務狀態 |
| `/api/tasks/{task_id}/result` | GET | 取得結果 |
| `/api/queue/status` | GET | 佇列狀態 |

### WebSocket 即時通知

```
ws://localhost:9527/ws/tasks/{task_id}
```

---

## ⚙️ 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `MAX_FILE_SIZE_MB` | 最大檔案大小 | 100 |
| `ENABLE_BATCH_UPLOAD` | 啟用批次上傳 | false |
| `MAX_CONCURRENT_TASKS` | 最大並行任務 | 1 |
| `WHISPER_MODEL` | Whisper 模型 | medium |
| `GEMINI_API_KEY` | Gemini API 金鑰 | - |

---

## 📁 專案結構

```
convert/
├── backend/                # 後端服務 (FastAPI)
│   ├── api/               # API 路由
│   ├── core/              # 核心設定
│   ├── models/            # 資料模型
│   └── services/          # 業務邏輯
├── frontend/              # 前端介面
├── docker/                # Docker 配置
│   ├── Dockerfile         # CPU 版本
│   ├── Dockerfile.gpu     # GPU 版本 (CUDA)
│   └── docker-compose*.yml
├── scripts/               # 部署腳本
├── doc/                   # 文檔
└── tests/                 # 測試
```

---

## 🔧 故障排除

### GPU 未啟用

1. 確認 NVIDIA Driver 已安裝：`nvidia-smi`
2. 確認 Docker GPU 支援：Settings → Resources → GPU
3. 使用 GPU compose 檔案：`docker-compose-windows-gpu.yml`

### PowerShell 執行策略錯誤

使用 `deploy.bat` 而非 `deploy.ps1`，自動繞過執行策略限制。

### 容器啟動失敗

```powershell
# 檢查日誌
docker compose logs -f

# 重建映像
deploy.bat build
```

---

## 📄 授權

本專案採用 MIT 授權條款。

---

## 🙏 致謝

- [OpenAI Whisper](https://github.com/openai/whisper)
- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
- [CTranslate2](https://github.com/OpenNMT/CTranslate2)
- [Ollama](https://ollama.ai/)
- [FastAPI](https://fastapi.tiangolo.com/)

---

<div align="center">

**Made with ❤️ for better meetings**

如果這個專案對你有幫助，請給個 Star ⭐

</div>

