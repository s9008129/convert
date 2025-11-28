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
# 推薦：高品質模型（RTX 4090 建議使用，需 ~10GB VRAM）
ollama pull gemma3:12b

# 或使用中文優化模型（需 ~5GB VRAM，適合大多數 GPU）
ollama pull qwen2.5:7b

# 或使用通用模型（需 ~5GB VRAM）
ollama pull llama3.1:8b
```

### 2. 建立 Python 環境並安裝依賴

建立虛擬環境並安裝 `requirements.txt`（**推薦方式**）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

或執行自動安裝腳本：

```powershell
python install_deps.py
```

> 💡 **提示**：`開始轉錄.bat` 啟動腳本會自動檢測並建立虛擬環境，首次執行時會自動安裝必要的套件（包括 `faster-whisper`、`pyyaml`、`httpx` 等）。若安裝失敗，請參考「常見問題」中的「顯示找不到 Whisper 語音辨識引擎」章節。
>
> 若您偏好可攜式 Python，請將其放在 `python/` 目錄後執行 `python\python.exe -m pip install -r requirements.txt`。

### 3. （選用）GPU 加速

如果您有 NVIDIA GPU，批次腳本會自動偵測並安裝 CUDA 加速套件：

```powershell
# 批次腳本會自動執行以下安裝
pip install nvidia-cudnn-cu12 nvidia-cublas-cu12
```

### 4. （選用）下載 faster-whisper-xxl.exe

若仍需舊版獨立執行檔，可從 [GitHub Releases](https://github.com/Purfview/whisper-standalone-win/releases) 下載並放在專案根目錄，並將 `config.yaml` 中的 `backend` 設為 `exe`。但預設流程已改為 Python 版 faster-whisper。

### 5. 開始使用

1. 將音訊/視訊檔案放入 `input/` 資料夾
2. 雙擊 `開始轉錄.bat`（Windows）或執行 `python main.py`
3. 批次腳本會自動執行 6 項系統檢查：
   - ✅ Python 環境（自動建立虛擬環境）
   - ✅ Python 套件（自動安裝缺少的依賴）
   - ✅ CUDA 加速支援（自動偵測 GPU）
   - ✅ Ollama 服務（自動啟動）
   - ✅ LLM 模型（提示下載）
   - ✅ 輸入檔案（自動掃描）
4. 查看 `output/` 資料夾中的會議摘要

---

## 目錄結構

```
會議轉錄工具/
├── 開始轉錄.bat          # Windows 啟動腳本（含 6 項自動檢查）
├── main.py               # 主程式
├── config.yaml           # 配置檔
├── .venv/                # 推薦：專案虛擬環境（自動建立）
├── requirements.txt      # Python 依賴清單
├── install_deps.py       # 依賴安裝腳本
├── faster-whisper-xxl.exe # （選用）舊版獨立轉錄引擎
├── python/               # （選用）可攜式 Python
├── src/                  # 核心模組
│   ├── ollama_client.py  # Ollama LLM 客戶端
│   ├── whisper_transcriber.py # Whisper 轉錄器（支援 Python/exe 後端）
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
    # RTX 4090 (24GB VRAM) 推薦使用 gemma3:12b
    # 8GB VRAM 以下建議使用 qwen2.5:7b
    model: "gemma3:12b"    # 使用的模型
    num_ctx: 32768         # 上下文視窗大小

# Whisper 設定
whisper:
  backend: "python"        # 後端選項：python / exe / auto
  model: "large-v3"        # 轉錄模型
  language: "zh"           # 語言
  device: "auto"           # 運算裝置（auto/cuda/cpu）
```

### 推薦的 Ollama 模型

| 模型 | VRAM 需求 | 中文品質 | 特點 |
|------|-----------|----------|------|
| gemma3:12b | ~10GB | ⭐⭐⭐⭐⭐ | 高品質，RTX 4090 推薦 |
| qwen2.5:7b | ~5GB | ⭐⭐⭐⭐⭐ | 中文優化，推薦首選 |
| llama3.1:8b | ~5GB | ⭐⭐⭐ | 通用平衡 |
| mistral:7b | ~5GB | ⭐⭐⭐ | 速度快 |
| llama3.1:70b | ~40GB | ⭐⭐⭐⭐ | 最高品質 |

### Whisper 後端選項

| 後端 | 說明 | 建議使用情境 |
|------|------|-------------|
| `python` | 使用 Python 版 faster-whisper（預設） | 推薦，無需額外下載 |
| `exe` | 使用 faster-whisper-xxl.exe | 需要獨立執行檔時 |
| `auto` | 自動選擇可用的後端 | 自動偵測環境 |

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

### Q: 顯示「找不到 Whisper 語音辨識引擎」？

1. 確認 Python 虛擬環境已正確建立
2. 手動執行安裝：
   ```powershell
   .\.venv\Scripts\pip.exe install faster-whisper
   ```
3. 或重新安裝所有依賴：
   ```powershell
   .\.venv\Scripts\pip.exe install -r requirements.txt
   ```

### Q: Ollama 連線失敗？

1. 確認 Ollama 已啟動（系統匣有圖示）
2. 執行 `ollama list` 確認正常
3. 測試連線：`curl http://localhost:11434/api/tags`

### Q: GPU 未被使用？

1. 確認已安裝 NVIDIA 驅動程式
2. 執行 `nvidia-smi` 確認 GPU 可被偵測
3. 檢查 config.yaml 中 `device` 設為 `cuda` 或 `auto`
4. 批次腳本會自動安裝 CUDA 套件，若失敗請手動執行：
   ```powershell
   pip install nvidia-cudnn-cu12 nvidia-cublas-cu12
   ```

### Q: 摘要品質不佳？

1. 嘗試更換模型（推薦 `gemma3:12b` 或 `qwen2.5:7b` 處理中文）
2. 調低 temperature（如 0.5）讓輸出更精確
3. 自訂 system_prompt 符合您的需求
4. 注意：過小的模型（如 gemma3:270m）無法正確處理長文本摘要

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
│                 批次腳本 6 項自動檢查                    │
├─────────────────────────────────────────────────────────┤
│  [1/6] Python 環境 → 自動建立 .venv 虛擬環境            │
│  [2/6] Python 套件 → 自動安裝 faster-whisper 等依賴     │
│  [3/6] CUDA 加速   → 偵測 GPU，自動安裝 CUDA 套件       │
│  [4/6] Ollama 服務 → 檢查/啟動 Ollama                   │
│  [5/6] LLM 模型    → 檢查模型是否已下載                 │
│  [6/6] 輸入檔案    → 掃描 input/ 資料夾                 │
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
│  │ large-v3    │    │ gemma3:12b  │    │  .md     │  │
│  │ (Python)    │    │              │    │          │  │
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
