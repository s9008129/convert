# 會議轉錄工具

**本地 AI 驅動的影音轉逐字稿轉會議紀錄工具**

> 🔒 完全離線運行，資料不離開本機  
> ⚡ RTX 4090 + CUDA 加速，2 小時音訊約 6 分鐘處理完成  
> 💰 零 API 成本，使用本地 LLM  

---

## 功能特點

- ✅ **語音轉逐字稿**：使用 faster-whisper (Whisper large-v3) 高品質轉錄
- ✅ **智能會議摘要**：使用本地 Ollama LLM 生成結構化會議紀錄
- ✅ **完全離線**：所有處理都在本機完成，資料安全有保障
- ✅ **多格式支援**：MP3, MP4, WAV, M4A, MKV, WebM, FLAC 等
- ✅ **中文優化**：針對中文語音和摘要特別優化
- ✅ **快取機制**：相同檔案不重複轉錄，節省時間
- ✅ **批次處理**：一次處理多個檔案

---

## 系統需求

### 硬體需求

| 組件 | 最低需求 | 建議配置 |
|------|----------|----------|
| CPU | 4 核心 | 8+ 核心 |
| RAM | 16 GB | 32 GB |
| GPU | - | NVIDIA RTX 3060+ (8GB VRAM) |
| 儲存空間 | 10 GB | 20+ GB |

### 軟體需求

- Windows 10/11 (64-bit) 或 macOS 10.15+ 或 Linux
- NVIDIA 驅動程式（如使用 GPU 加速）
- Ollama（本地 LLM 運行環境）
- Python 3.10+ 或可攜式 Python

---

## 快速開始

### 1. 安裝 Ollama

前往 [ollama.ai](https://ollama.ai) 下載並安裝 Ollama。

安裝後，下載推薦的中文優化模型：

```bash
# 推薦：中文優化模型
ollama pull qwen2.5:7b

# 或使用通用模型
ollama pull llama3.1:8b
```

### 2. 建立 Python 環境並安裝依賴

建立虛擬環境或使用可攜式 Python，並安裝 `requirements.txt`：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

或執行：

```powershell
python install_deps.py
```

> 若您偏好可攜式 Python，請將其放在 `python/` 目錄後執行 `python\python.exe -m pip install -r requirements.txt`。

### 3. （選用）下載 faster-whisper-xxl.exe

若仍需舊版獨立執行檔，可從 [GitHub Releases](https://github.com/Purfview/whisper-standalone-win/releases) 下載並放在專案根目錄，但預設流程已改為 Python 版 faster-whisper。

### 4. 開始使用

1. 將音訊/視訊檔案放入 `input/` 資料夾
2. 雙擊 `開始轉錄.bat`（Windows）或執行 `python main.py`
3. 查看 `output/` 資料夾中的會議摘要

---

## 目錄結構

```
會議轉錄工具/
├── 開始轉錄.bat          # Windows 啟動腳本
├── main.py               # 主程式
├── config.yaml           # 配置檔
├── .venv/                # 推薦：專案虛擬環境
├── requirements.txt      # Python 依賴清單
├── faster-whisper-xxl.exe # （選用）舊版獨立轉錄引擎
├── python/               # （選用）可攜式 Python
├── src/                  # 核心模組
│   ├── ollama_client.py  # Ollama LLM 客戶端
│   ├── whisper_transcriber.py # Whisper 轉錄器
│   └── summarizer.py     # 會議摘要生成器
├── input/                # 放入待處理的音訊/視訊
├── output/               # 輸出的會議摘要
├── temp/                 # 暫存（逐字稿快取）
└── logs/                 # 日誌檔案
```

---

## 配置說明

編輯 `config.yaml` 自訂設定：

```yaml
# LLM 設定
llm:
  ollama:
    model: "qwen2.5:7b"    # 使用的模型
    num_ctx: 32768         # 上下文視窗大小

# Whisper 設定
whisper:
  model: "large-v3"        # 轉錄模型
  language: "zh"           # 語言
  device: "auto"           # 運算裝置（auto/cuda/cpu）
```

### 推薦的 Ollama 模型

| 模型 | VRAM 需求 | 中文品質 | 特點 |
|------|-----------|----------|------|
| qwen2.5:7b | ~5GB | ⭐⭐⭐⭐⭐ | 中文優化，推薦首選 |
| llama3.1:8b | ~5GB | ⭐⭐⭐ | 通用平衡 |
| mistral:7b | ~5GB | ⭐⭐⭐ | 速度快 |
| llama3.1:70b | ~40GB | ⭐⭐⭐⭐ | 最高品質 |

---

## 效能參考

### RTX 4090 測試結果

| 音訊長度 | 轉錄時間 | 摘要時間 | 總時間 |
|----------|----------|----------|--------|
| 10 分鐘 | ~30 秒 | ~30 秒 | ~1 分鐘 |
| 30 分鐘 | ~1.5 分鐘 | ~1 分鐘 | ~2.5 分鐘 |
| 1 小時 | ~3 分鐘 | ~1.5 分鐘 | ~4.5 分鐘 |
| 2 小時 | ~6 分鐘 | ~2 分鐘 | ~8 分鐘 |

---

## 常見問題

### Q: 批次腳本顯示亂碼？

確認 `.bat` 檔案以「UTF-8 with BOM」編碼儲存。

### Q: Ollama 連線失敗？

1. 確認 Ollama 已啟動（系統匣有圖示）
2. 執行 `ollama list` 確認正常
3. 測試連線：`curl http://localhost:11434/api/tags`

### Q: GPU 未被使用？

1. 確認已安裝 NVIDIA 驅動程式
2. 執行 `nvidia-smi` 確認 GPU 可被偵測
3. 檢查 config.yaml 中 `device` 設為 `cuda` 或 `auto`

### Q: 摘要品質不佳？

1. 嘗試更換模型（推薦 qwen2.5:7b 處理中文）
2. 調低 temperature（如 0.5）讓輸出更精確
3. 自訂 system_prompt 符合您的需求

---

## 部署 / 移轉檢查表

若需要將專案移轉至另一台工作站，請參考 `docs/deployment_checklist.md`，逐項確認 GPU、Ollama、Python 依賴與批次腳本流程是否就緒。

---

## 隱私與安全

- 🔒 **完全離線**：所有處理都在本機完成
- 🔒 **不傳輸資料**：音訊和逐字稿不會上傳到任何伺服器
- 🔒 **本地 LLM**：使用 Ollama 運行的本地模型
- 🔒 **可審計**：完整開源，可檢視所有程式碼

---

## 授權

MIT License

---

## 技術架構

```
┌─────────────────────────────────────────────────────────┐
│                     使用者操作                          │
│              雙擊「開始轉錄.bat」                        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    批次腳本檢查                          │
│  • Ollama 服務 → GPU 狀態 → Python 環境 → 輸入檔案      │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   main.py 主程式                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│  │   Whisper    │    │   Ollama     │    │ Markdown │  │
│  │   轉錄器     │ → │   摘要器     │ → │  輸出器  │  │
│  │              │    │              │    │          │  │
│  │ large-v3    │    │ qwen2.5:7b  │    │  .md     │  │
│  └──────────────┘    └──────────────┘    └──────────┘  │
│         │                   │                           │
│         └───────────────────┘                           │
│                    │                                    │
│                    ▼                                    │
│         ┌──────────────────┐                           │
│         │   GPU 加速       │                           │
│         │   RTX 4090       │                           │
│         │   CUDA           │                           │
│         └──────────────────┘                           │
│                                                          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    輸出結果                              │
│           output/會議名稱_摘要.md                        │
└─────────────────────────────────────────────────────────┘
```
