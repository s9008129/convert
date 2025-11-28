# 會議轉錄工具 - 安裝指南

## Windows 11 + RTX 4090 專用安裝步驟

---

## 步驟 1：安裝 NVIDIA 驅動程式

確認已安裝最新的 NVIDIA 驅動程式。

```powershell
# 驗證 GPU 是否正常運作
nvidia-smi
```

如果指令無法執行，請前往 [NVIDIA 驅動下載](https://www.nvidia.com/drivers) 安裝。

---

## 步驟 2：安裝 Ollama

### 下載安裝

1. 前往 [ollama.ai](https://ollama.ai)
2. 下載 Windows 版本安裝程式
3. 執行安裝程式完成安裝

### 下載模型

開啟 PowerShell 或命令提示字元：

```powershell
# 推薦：中文優化模型（約 4GB）
ollama pull qwen2.5:7b

# 驗證安裝
ollama list
```

### 驗證 Ollama

```powershell
# 測試 API 連線
curl http://localhost:11434/api/tags

# 應該看到已下載的模型列表
```

---

## 步驟 3：建立 Python 環境並安裝依賴

### 建立虛擬環境（推薦）

```powershell
cd 會議轉錄工具
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 使用可攜式 Python

1. 下載 [WinPython](https://winpython.github.io/) 或官方 embeddable 版本
2. 解壓縮到 `會議轉錄工具\python\` 目錄
3. 執行：

```powershell
cd 會議轉錄工具
.\python\python.exe -m pip install -r requirements.txt
```

### 指令式安裝

亦可直接執行：

```powershell
python install_deps.py
```

> `requirements.txt` 已包含 `pyyaml`, `httpx`, `faster-whisper` 等必要套件，與批次腳本一致。

### （選用）Legacy faster-whisper-xxl.exe

若仍需傳統的 Windows 獨立執行檔，可依照原流程下載 `faster-whisper-xxl.exe` 至根目錄，但預設流程已改為 Python 版本。

---

## 步驟 4：設定 Windows 安全性

### Windows Defender 例外

**以系統管理員身分執行 PowerShell**：

```powershell
# 將工具資料夾加入例外
Add-MpPreference -ExclusionPath "C:\Tools\會議轉錄工具"

# 或只排除特定執行檔（依實際環境選擇）
Add-MpPreference -ExclusionPath "C:\Tools\會議轉錄工具\.venv\Scripts\python.exe"
Add-MpPreference -ExclusionPath "C:\Tools\會議轉錄工具\python\python.exe"
# （選用）若仍使用 legacy exe 可再加上：
# Add-MpPreference -ExclusionPath "C:\Tools\會議轉錄工具\faster-whisper-xxl.exe"

# 驗證設定
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
```

### 移除網路標記（如檔案從網路下載）

```powershell
# 移除所有檔案的「來自網路」標記
Get-ChildItem "C:\Tools\會議轉錄工具" -Recurse | Unblock-File
```

---

## 步驟 5：驗證安裝

### 檢查清單

```powershell
# 1. Ollama 服務
curl http://localhost:11434/api/tags

# 2. GPU
nvidia-smi

# 3. Python 依賴
.\.venv\Scripts\python.exe -c "import yaml, httpx, faster_whisper; print('Python OK')"

# 4. Whisper Backend
.\.venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', device='cpu'); print('Whisper backend OK')"

# （選用）Legacy exe
# .\faster-whisper-xxl.exe --help
```

### 測試完整流程

1. 將一個短音訊檔案（如 1 分鐘 MP3）放入 `input\` 資料夾
2. 雙擊 `開始轉錄.bat`
3. 確認 `output\` 資料夾產生 Markdown 摘要

---

## 目錄結構確認

安裝完成後，目錄結構應如下：

```
會議轉錄工具/
├── 開始轉錄.bat              ✅ 啟動腳本
├── main.py                    ✅ 主程式
├── config.yaml                ✅ 配置檔
├── README.md                  ✅ 說明文件
├── INSTALL.md                 ✅ 本安裝指南
├── .venv/                     ✅ 推薦：虛擬環境（或 python/ 可攜版本）
├── requirements.txt           ✅ 依賴清單
├── faster-whisper-xxl.exe     ⚙️ （選用）legacy 轉錄引擎
├── python/                    ⚙️ （選用）可攜式 Python
│   ├── python.exe
│   └── Lib/site-packages/
│       ├── yaml/
│       └── httpx/
├── src/                       ✅ 核心模組
│   ├── __init__.py
│   ├── ollama_client.py
│   ├── whisper_transcriber.py
│   └── summarizer.py
├── input/                     📁 放入音訊
├── output/                    📁 輸出摘要
├── temp/                      📁 快取
└── logs/                      📁 日誌
```

圖示說明：
- ✅ 已包含在專案中
- 📥 需要下載/設定
- 📁 資料夾（自動建立）

---

## 常見安裝問題

### 問題：Ollama 無法啟動

**解決方案**：

1. 確認 Ollama 已正確安裝
2. 檢查系統匣是否有 Ollama 圖示
3. 手動啟動：`ollama serve`

### 問題：faster-whisper-xxl 無法執行

**解決方案**：

1. 確認已安裝 Visual C++ Redistributable
   - 下載：[Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. 確認 Windows Defender 沒有阻擋
3. 以系統管理員身分執行

### 問題：Python 套件安裝失敗

**解決方案**：

1. 確認使用正確的 Python 路徑
2. 如使用 Embedded Python，確認已編輯 `.pth` 檔案
3. 嘗試：`python -m pip install --upgrade pip`

### 問題：GPU 未被使用

**解決方案**：

1. 確認 NVIDIA 驅動程式已安裝
2. 確認 CUDA 版本相容性
3. 在 config.yaml 中設定 `device: cuda`

---

## 需要協助？

如果遇到問題，請檢查：

1. `logs\` 目錄中的日誌檔案
2. 命令提示字元中的錯誤訊息
3. 確認所有步驟都已完成

---

*安裝指南版本：1.0.0*  
*最後更新：2025-11-27*

*最後更新：2025-11-27*
