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

## 步驟 3：下載 faster-whisper-xxl

### 下載執行檔

1. 前往 [GitHub Releases](https://github.com/Purfview/whisper-standalone-win/releases)
2. 下載最新的 `Faster-Whisper-XXL_rXXX_windows.zip`
3. 解壓縮到專案根目錄

### 驗證安裝

```powershell
cd 會議轉錄工具
.\faster-whisper-xxl.exe --help
```

應該會顯示使用說明。

---

## 步驟 4：設定 Python 環境

### 方法 A：可攜式 Python（推薦）

**優點**：不影響系統環境，可隨專案移動

1. 前往 [WinPython](https://winpython.github.io/)
2. 下載 `WinPython64-3.11.x.0dot`（精簡版，約 30MB）
3. 解壓縮到 `會議轉錄工具\python\` 目錄

安裝依賴：

```powershell
cd 會議轉錄工具
.\python\python.exe -m pip install pyyaml httpx
```

### 方法 B：Python Embedded

1. 前往 [Python 官方下載](https://www.python.org/downloads/windows/)
2. 下載「Windows embeddable package (64-bit)」
3. 解壓縮到 `會議轉錄工具\python\` 目錄

**重要設定**：

1. 編輯 `python\python311._pth`（版本號依下載版本調整）
2. 取消註解最後一行 `import site`
3. 新增一行 `Lib\site-packages`

下載 pip：

```powershell
# 下載 get-pip.py
Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile python\get-pip.py

# 安裝 pip
.\python\python.exe python\get-pip.py

# 安裝依賴
.\python\python.exe -m pip install pyyaml httpx
```

### 方法 C：系統 Python

```powershell
# 確認 Python 版本
python --version

# 安裝依賴
pip install pyyaml httpx
```

---

## 步驟 5：設定 Windows 安全性

### Windows Defender 例外

**以系統管理員身分執行 PowerShell**：

```powershell
# 將工具資料夾加入例外
Add-MpPreference -ExclusionPath "C:\Tools\會議轉錄工具"

# 或只排除特定執行檔
Add-MpPreference -ExclusionPath "C:\Tools\會議轉錄工具\faster-whisper-xxl.exe"
Add-MpPreference -ExclusionPath "C:\Tools\會議轉錄工具\python\python.exe"

# 驗證設定
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
```

### 移除網路標記（如檔案從網路下載）

```powershell
# 移除所有檔案的「來自網路」標記
Get-ChildItem "C:\Tools\會議轉錄工具" -Recurse | Unblock-File
```

---

## 步驟 6：驗證安裝

### 檢查清單

```powershell
# 1. Ollama 服務
curl http://localhost:11434/api/tags

# 2. GPU
nvidia-smi

# 3. Python
.\python\python.exe -c "import yaml; print('Python OK')"

# 4. Whisper
.\faster-whisper-xxl.exe --help
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
├── faster-whisper-xxl.exe     📥 需下載
├── python/                    📥 需設定
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
