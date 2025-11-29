# 🖥️ Windows 11 移植方案（簡化版）

## 組織內部使用 - 零成本快速部署

> 📅 文件建立日期：2025-11-27  
> 📅 最後更新：2025-11-27（深度優化版）  
> 🎯 目標：以最低成本、最快速度，在 Windows 11 + RTX 4090 環境運行

---

## ⚠️ 重要提醒

### 批次腳本（.bat）繁體中文顯示

**必須遵守**：所有 `.bat` 檔案必須以 **UTF-8 with BOM** 編碼儲存，否則中文會顯示亂碼。

**在 VS Code 中設定**：
1. 開啟 .bat 檔案
2. 點擊右下角的編碼（如 `UTF-8`）
3. 選擇「以編碼方式儲存」→「UTF-8 with BOM」

**在 Notepad 中設定**：
1. 另存新檔
2. 編碼選擇「UTF-8 (含 BOM)」

---

## 🧠 第一性原理分析

### 需求本質是什麼？

```
使用者真正需要的：
┌─────────────────────────────────────────────────────┐
│  輸入：音訊/視訊檔案                                 │
│    ↓                                                │
│  處理：語音轉文字 → LLM 摘要                         │
│    ↓                                                │
│  輸出：結構化的會議記錄 Markdown                     │
└─────────────────────────────────────────────────────┘
```

### 去除不必要的複雜性

| 原方案要求 | 是否真正需要？ | 簡化後 |
|-----------|--------------|--------|
| 打包成單一 EXE | ❌ 不需要 | 批次腳本 + 可攜式 Python |
| 程式碼簽章證書 | ❌ 內部使用不需要 | IT 白名單 / 本地執行 |
| 避開所有防毒軟體 | ❌ 內部可控 | 加入例外清單 |
| 支援所有 Windows 環境 | ❌ 只有一台 PC | 針對該 PC 優化 |

### 核心洞察

**您已經有 Ollama 和本地 LLM！** 這意味著：
1. 不需要外部 API（Gemini/OpenAI）
2. 完全離線運行
3. 資料安全性最高
4. 零 API 成本

---

## ⚡ 最終方案：批次腳本 + 可攜式工具

### 架構設計

```
┌─────────────────────────────────────────────────────────────┐
│                    Windows 11 部署架構                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  使用者操作：                                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  雙擊「開始轉錄.bat」                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               批次腳本 (.bat)                         │   │
│  │  • 檢查 Ollama 是否運行                              │   │
│  │  • 呼叫 faster-whisper-xxl.exe 轉錄                  │   │
│  │  • 呼叫 Python 腳本處理 LLM 摘要                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│         ┌───────────────┼───────────────┐                    │
│         ▼               ▼               ▼                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │ faster-    │  │ Ollama     │  │ Python     │             │
│  │ whisper-   │  │ (已安裝)   │  │ 可攜式     │             │
│  │ xxl.exe    │  │            │  │            │             │
│  │ (獨立)     │  │ 本地 LLM   │  │ 主程式     │             │
│  └────────────┘  └────────────┘  └────────────┘             │
│        │               │               │                     │
│        └───────────────┴───────────────┘                     │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              RTX 4090 (24GB VRAM)                     │   │
│  │              CUDA 加速轉錄                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 套件內容

最終部署的資料夾結構：

```
會議轉錄工具/
├── 開始轉錄.bat              # 🖱️ 使用者雙擊這個
├── faster-whisper-xxl.exe    # 語音轉錄引擎（獨立執行檔）
├── python/                   # 可攜式 Python（約 50MB）
│   ├── python.exe
│   └── Lib/site-packages/
├── src/                      # 程式碼（從 macOS 複製）
│   ├── transcription_summarizer.py
│   ├── llm_providers.py      # 修改為呼叫 Ollama
│   ├── config_manager.py
│   ├── file_manager.py
│   ├── markdown_generator.py
│   └── ...
├── config.yaml               # 配置檔（指向 Ollama）
├── input/                    # 放入音訊檔案
├── output/                   # 輸出結果
├── temp/                     # 逐字稿快取
├── logs/                     # 日誌
└── models/                   # Whisper 模型（自動下載）
```

---

## 🛠️ 實施步驟

### 第一步：下載必要組件（約 10 分鐘）

#### 1.1 下載 faster-whisper-xxl 獨立執行檔

```powershell
# 前往 GitHub 下載頁面
# https://github.com/Purfview/whisper-standalone-win/releases

# 下載最新的 Faster-Whisper-XXL_rXXX_windows.zip
# 解壓縮到專案資料夾
```

**為什麼選這個？**
- ✅ 獨立執行，不需要 Python
- ✅ 自動支援 CUDA（偵測到 RTX 4090 就會使用）
- ✅ 已經被社群廣泛測試
- ✅ 中文轉錄效果優秀

#### 1.2 下載可攜式 Python

```powershell
# 方法 A：使用 Python 官方 Embedded 版本
# 前往 https://www.python.org/downloads/windows/
# 下載「Windows embeddable package (64-bit)」
# 例如：python-3.11.9-embed-amd64.zip

# 方法 B：使用 WinPython（推薦，已包含 pip）
# 前往 https://winpython.github.io/
# 下載精簡版（約 50MB）
```

#### 1.3 安裝必要的 Python 套件

**⚠️ 重要：Python Embedded 版本需要額外配置才能使用 pip**

```powershell
# === 步驟 A：配置 Python Embedded ===

# 1. 解壓縮 python-3.11.x-embed-amd64.zip 到 python 資料夾

# 2. 編輯 python311._pth 檔案（版本號依下載版本調整）
#    取消註解最後一行 import site，並新增路徑：
#    內容應該像這樣：
#    python311.zip
#    .
#    Lib
#    Lib\site-packages
#    import site

# 3. 下載 get-pip.py
#    https://bootstrap.pypa.io/get-pip.py
#    存到 python 資料夾

# 4. 安裝 pip
cd python
python.exe get-pip.py

# 5. 安裝依賴套件
python.exe -m pip install pyyaml httpx requests

# === 步驟 B：使用 WinPython（推薦，免配置） ===

# 如果覺得步驟 A 太麻煩，直接用 WinPython：
# 前往 https://winpython.github.io/
# 下載 WinPython64-3.11.x.0dot（精簡版，約 30MB）
# 解壓縮後已包含 pip，直接使用
```

---

### 第二步：修改程式碼（約 30 分鐘）

#### 2.1 建立 Ollama 整合模組

建立新檔案 `src/ollama_client.py`：

```python
"""
Ollama 本地 LLM 客戶端
直接呼叫已安裝的 Ollama API
"""
import httpx
import json
import logging
from typing import Optional, List, Dict, Any

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaClient:
    """本地 Ollama LLM 客戶端"""
    
    def __init__(
        self, 
        base_url: str = "http://localhost:11434", 
        model: str = "llama3",
        num_ctx: int = 32768,  # 上下文視窗大小（支援長逐字稿）
        timeout: int = 600     # 10 分鐘超時
    ):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.num_ctx = num_ctx
        self.timeout = timeout
    
    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        呼叫 Ollama 生成回應
        
        Args:
            prompt: 使用者提示詞
            system_prompt: 系統提示詞（可選）
            temperature: 生成溫度（0-1）
        
        Returns:
            生成的文字
        """
        url = f"{self.base_url}/api/generate"
        
        # 組合完整提示詞
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,  # 不使用串流，等待完整回應
            "options": {
                "num_ctx": self.num_ctx,
                "temperature": temperature,
                "num_predict": 4096  # 最大輸出 token 數
            }
        }
        
        logger.info(f"[Ollama] 開始生成，模型: {self.model}")
        logger.info(f"[Ollama] 輸入長度: {len(full_prompt)} 字元")
        
        try:
            with httpx.Client(timeout=httpx.Timeout(self.timeout)) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                
                output = result.get("response", "")
                logger.info(f"[Ollama] 生成完成，輸出長度: {len(output)} 字元")
                
                # 顯示效能資訊
                if "total_duration" in result:
                    duration_sec = result["total_duration"] / 1e9
                    logger.info(f"[Ollama] 耗時: {duration_sec:.1f} 秒")
                
                return output
                
        except httpx.TimeoutException:
            logger.error("[Ollama] 請求超時")
            raise TimeoutError(f"Ollama 請求超時（{self.timeout}秒）")
        except httpx.HTTPStatusError as e:
            logger.error(f"[Ollama] HTTP 錯誤: {e.response.status_code}")
            raise ConnectionError(f"Ollama HTTP 錯誤: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"[Ollama] 連線失敗: {e}")
            raise ConnectionError(f"Ollama 連線失敗: {e}")
    
    def chat(
        self, 
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> str:
        """
        使用聊天格式呼叫 Ollama（推薦用於多輪對話）
        
        Args:
            messages: [{"role": "system/user/assistant", "content": "..."}]
            temperature: 生成溫度
        
        Returns:
            助手的回應
        """
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": self.num_ctx,
                "temperature": temperature
            }
        }
        
        try:
            with httpx.Client(timeout=httpx.Timeout(self.timeout)) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"[Ollama] Chat 錯誤: {e}")
            raise ConnectionError(f"Ollama Chat 失敗: {e}")
    
    def is_running(self) -> bool:
        """檢查 Ollama 是否正在運行"""
        try:
            with httpx.Client(timeout=httpx.Timeout(5)) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> List[str]:
        """列出可用的模型"""
        try:
            with httpx.Client(timeout=httpx.Timeout(10)) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                result = response.json()
                return [m["name"] for m in result.get("models", [])]
        except Exception as e:
            logger.warning(f"[Ollama] 無法列出模型: {e}")
            return []
    
    def get_model_info(self) -> Optional[Dict[str, Any]]:
        """取得目前模型的資訊"""
        try:
            with httpx.Client(timeout=httpx.Timeout(10)) as client:
                response = client.post(
                    f"{self.base_url}/api/show",
                    json={"name": self.model}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"[Ollama] 無法取得模型資訊: {e}")
            return None
```

#### 2.2 建立 Windows 專用轉錄器

建立新檔案 `src/whisper_windows.py`：

```python
"""
Windows 專用 Whisper 轉錄器
使用 faster-whisper-xxl.exe 獨立執行檔
"""
import subprocess
import json
import logging
import time
from pathlib import Path
from typing import Optional
import os

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhisperWindowsTranscriber:
    """Windows 版本的 Whisper 轉錄器"""
    
    # 支援的音訊/視訊格式
    SUPPORTED_FORMATS = {
        '.mp3', '.mp4', '.wav', '.m4a', '.mkv', 
        '.webm', '.flac', '.ogg', '.wma', '.aac',
        '.avi', '.mov', '.wmv'
    }
    
    def __init__(
        self, 
        exe_path: str = "faster-whisper-xxl.exe", 
        model: str = "large-v3",
        language: str = "zh",
        device: str = "cuda"
    ):
        self.exe_path = Path(exe_path).resolve()
        self.model = model
        self.language = language
        self.device = device
        
        # 驗證執行檔存在
        if not self.exe_path.exists():
            # 嘗試在當前目錄查找
            alt_path = Path.cwd() / "faster-whisper-xxl.exe"
            if alt_path.exists():
                self.exe_path = alt_path
            else:
                raise FileNotFoundError(
                    f"找不到轉錄程式: {exe_path}\n"
                    f"請確認 faster-whisper-xxl.exe 存在於專案目錄中"
                )
        
        logger.info(f"[Whisper] 初始化完成")
        logger.info(f"[Whisper] 執行檔: {self.exe_path}")
        logger.info(f"[Whisper] 模型: {model}, 語言: {language}, 裝置: {device}")
    
    def transcribe(
        self, 
        audio_path: str, 
        output_dir: str = "temp",
        use_cache: bool = True
    ) -> str:
        """
        轉錄音訊檔案
        
        Args:
            audio_path: 音訊檔案路徑
            output_dir: 輸出目錄
            use_cache: 是否使用快取
        
        Returns:
            轉錄文字
        """
        audio_path = Path(audio_path).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 驗證輸入檔案
        if not audio_path.exists():
            raise FileNotFoundError(f"找不到音訊檔案: {audio_path}")
        
        if audio_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"不支援的檔案格式: {audio_path.suffix}\n"
                f"支援格式: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        # 檢查快取
        cache_file = output_dir / f"{audio_path.stem}.txt"
        if use_cache and cache_file.exists():
            cached_text = cache_file.read_text(encoding="utf-8").strip()
            if cached_text:  # 確保快取不是空的
                logger.info(f"[快取] 使用已存在的逐字稿: {cache_file.name}")
                logger.info(f"[快取] 字數: {len(cached_text)}")
                return cached_text
        
        # 取得檔案大小
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        logger.info(f"[轉錄] 檔案: {audio_path.name} ({file_size_mb:.1f} MB)")
        
        # 建立命令
        cmd = [
            str(self.exe_path),
            str(audio_path),
            "--language", self.language,
            "--model", self.model,
            "--output_format", "txt",
            "--output_dir", str(output_dir),
            "--device", self.device,
            "--task", "transcribe"
        ]
        
        logger.info(f"[轉錄] 開始處理...")
        logger.info(f"[轉錄] 模型: {self.model}, 裝置: {self.device}")
        
        start_time = time.time()
        
        try:
            # 執行轉錄
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",  # 處理編碼錯誤
                cwd=str(self.exe_path.parent)  # 在執行檔目錄執行
            )
            
            elapsed = time.time() - start_time
            
            # 檢查錯誤
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "未知錯誤"
                logger.error(f"[轉錄] 失敗: {error_msg}")
                raise RuntimeError(f"轉錄失敗 (返回碼 {result.returncode}): {error_msg}")
            
            # 讀取輸出檔案
            output_file = output_dir / f"{audio_path.stem}.txt"
            if not output_file.exists():
                # 嘗試其他可能的輸出位置
                alt_output = self.exe_path.parent / f"{audio_path.stem}.txt"
                if alt_output.exists():
                    output_file = alt_output
                else:
                    raise FileNotFoundError(
                        f"找不到輸出檔案: {output_file}\n"
                        f"請檢查 faster-whisper-xxl 的輸出設定"
                    )
            
            text = output_file.read_text(encoding="utf-8").strip()
            
            if not text:
                logger.warning("[轉錄] 輸出為空，可能是無聲音訊")
            
            logger.info(f"[轉錄] 完成！耗時: {elapsed:.1f} 秒")
            logger.info(f"[轉錄] 字數: {len(text)}")
            
            return text
            
        except subprocess.TimeoutExpired:
            logger.error("[轉錄] 處理超時")
            raise TimeoutError("轉錄超時，請檢查音訊檔案或嘗試較小的模型")
        except FileNotFoundError as e:
            raise e
        except Exception as e:
            logger.error(f"[轉錄] 發生錯誤: {e}")
            raise RuntimeError(f"轉錄過程發生錯誤: {e}")
    
    def check_cuda_available(self) -> bool:
        """檢查 CUDA 是否可用"""
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
```

#### 2.3 修改 config.yaml

```yaml
# =====================================================
# Windows 版本配置檔
# 使用本地 Ollama + faster-whisper-xxl
# =====================================================

# ===== LLM 設定 =====
llm:
  provider: "ollama"
  
  ollama:
    # Ollama 服務位址（預設本地）
    base_url: "http://localhost:11434"
    
    # 使用的模型（請確認已用 ollama pull 下載）
    # 推薦選項：
    #   - llama3.1:8b      (平衡速度與品質)
    #   - qwen2.5:7b       (中文優化)
    #   - mistral:7b       (快速)
    #   - llama3.1:70b     (最高品質，需要大量記憶體)
    model: "llama3.1:8b"
    
    # 上下文視窗大小（越大可處理越長的逐字稿）
    # 8192   = 約 6,000 中文字
    # 32768  = 約 24,000 中文字（推薦）
    # 131072 = 約 100,000 中文字（需要支援的模型）
    num_ctx: 32768
    
    # 超時設定（秒）- 長逐字稿需要更多時間
    timeout: 600
    
    # 生成參數
    temperature: 0.7
    max_output_tokens: 4096

# ===== Whisper 設定 =====
whisper:
  # faster-whisper-xxl.exe 的路徑（相對或絕對路徑）
  exe_path: "faster-whisper-xxl.exe"
  
  # 模型大小
  # tiny    = 最快，準確度較低
  # base    = 快速
  # small   = 平衡
  # medium  = 較準確
  # large-v3 = 最準確（推薦，RTX 4090 可輕鬆運行）
  model: "large-v3"
  
  # 語言代碼
  # zh = 中文（繁體/簡體自動識別）
  # en = 英文
  # ja = 日文
  # auto = 自動偵測
  language: "zh"
  
  # 運算裝置
  # cuda = NVIDIA GPU（推薦）
  # cpu  = CPU（較慢）
  device: "cuda"

# ===== 路徑設定 =====
paths:
  input: "input"     # 輸入音訊/視訊檔案
  output: "output"   # 輸出 Markdown 摘要
  temp: "temp"       # 暫存（逐字稿快取）
  logs: "logs"       # 日誌檔案

# ===== 系統提示詞 =====
# 會議記錄摘要專用提示詞
system_prompt: |
  你是一位專業的政府機關資深承辦人員，擅長整理會議紀錄。
  
  請根據以下逐字稿，整理出結構化的會議摘要。
  
  ## 輸出要求
  
  1. 使用台灣繁體中文
  2. 語氣正式專業
  3. 重點摘要，避免冗長
  4. 保留重要的人名、日期、數字
  
  ## 輸出格式
  
  ### 一、會議概要
  - 會議主題
  - 主要與會者（如有提及）
  
  ### 二、議題與決議（約 400 字）
  - 列出主要討論議題
  - 說明最終決議或共識
  
  ### 三、問題與解決方案（約 300 字）
  - 列出會議中提出的問題
  - 說明對應的解決方案或處理方式
  
  ### 四、追蹤事項（約 300 字）
  - 列出需要追蹤的事項
  - 標註負責人（如有提及）
  - 標註預計完成時間（如有提及）
  
  ### 五、其他備註
  - 其他重要但不屬於上述分類的內容

# ===== 進階設定 =====
advanced:
  # 是否使用逐字稿快取
  use_cache: true
  
  # 是否顯示詳細日誌
  verbose: true
  
  # 處理失敗時是否繼續處理下一個檔案
  continue_on_error: true
```

---

### 第三步：建立啟動腳本（約 5 分鐘）

建立 `開始轉錄.bat`：

**⚠️ 重要：此檔案必須以「UTF-8 with BOM」編碼儲存！**

```batch
@echo off
setlocal EnableDelayedExpansion

REM =====================================================
REM 會議轉錄工具 - Windows 版啟動腳本
REM 編碼：UTF-8 with BOM（必須）
REM =====================================================

REM 設定控制台為 UTF-8
chcp 65001 >nul 2>&1

REM 設定視窗標題
title 會議轉錄工具 - Windows 版

REM 清除畫面
cls

echo.
echo  ============================================
echo       會議轉錄工具 - Windows 版
echo       RTX 4090 CUDA 加速
echo  ============================================
echo.

REM 切換到腳本所在目錄
cd /d "%~dp0"

REM ===== 檢查 1：Ollama 服務 =====
echo [1/4] 檢查 Ollama 服務...
curl -s -o nul -w "%%{http_code}" http://localhost:11434/api/tags > "%TEMP%\ollama_check.txt" 2>nul
set /p OLLAMA_STATUS=<"%TEMP%\ollama_check.txt"
del "%TEMP%\ollama_check.txt" 2>nul

if not "%OLLAMA_STATUS%"=="200" (
    echo       [!] Ollama 未運行
    echo       [*] 嘗試啟動 Ollama...
    
    REM 嘗試啟動 Ollama
    start "" /min "ollama" serve 2>nul
    
    REM 等待 Ollama 啟動
    timeout /t 5 /nobreak >nul
    
    REM 再次檢查
    curl -s -o nul -w "%%{http_code}" http://localhost:11434/api/tags > "%TEMP%\ollama_check.txt" 2>nul
    set /p OLLAMA_STATUS=<"%TEMP%\ollama_check.txt"
    del "%TEMP%\ollama_check.txt" 2>nul
    
    if not "!OLLAMA_STATUS!"=="200" (
        echo.
        echo  [錯誤] 無法啟動 Ollama！
        echo  [提示] 請手動啟動 Ollama 應用程式後重試
        echo.
        pause
        exit /b 1
    )
)
echo       [OK] Ollama 服務正常

REM ===== 檢查 2：GPU 狀態 =====
echo [2/4] 檢查 GPU 狀態...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo       [!] 警告：無法偵測 NVIDIA GPU
    echo       [!] 將使用 CPU 模式（較慢）
    set DEVICE=cpu
) else (
    echo       [OK] NVIDIA GPU 可用
    set DEVICE=cuda
)

REM ===== 檢查 3：Python 環境 =====
echo [3/4] 檢查 Python 環境...
if not exist "python\python.exe" (
    echo       [錯誤] 找不到 python\python.exe
    echo       [提示] 請確認可攜式 Python 已正確安裝
    pause
    exit /b 1
)
echo       [OK] Python 環境正常

REM ===== 檢查 4：輸入檔案 =====
echo [4/4] 掃描輸入檔案...

REM 確保 input 資料夾存在
if not exist "input" (
    mkdir "input"
    echo       [提示] 已建立 input 資料夾
)

REM 計算檔案數量
set FILE_COUNT=0
for %%f in (input\*.mp3 input\*.mp4 input\*.wav input\*.m4a input\*.mkv input\*.webm input\*.flac) do (
    set /a FILE_COUNT+=1
)

if %FILE_COUNT%==0 (
    echo.
    echo  [提示] input 資料夾沒有音訊/視訊檔案
    echo  [提示] 請將檔案放入 input 資料夾後重新執行
    echo.
    echo  支援的格式：.mp3 .mp4 .wav .m4a .mkv .webm .flac
    echo.
    pause
    exit /b 1
)
echo       [OK] 找到 %FILE_COUNT% 個待處理檔案

REM ===== 確認執行 =====
echo.
echo  ============================================
echo  準備開始處理 %FILE_COUNT% 個檔案
echo  ============================================
echo.
echo  按任意鍵開始，或按 Ctrl+C 取消...
pause >nul

REM ===== 執行主程式 =====
echo.
echo  [開始] 執行轉錄與摘要...
echo  ============================================
echo.

python\python.exe main_windows.py

echo.
echo  ============================================
echo  [完成] 所有處理已結束！
echo  [輸出] 請查看 output 資料夾
echo  ============================================
echo.
pause

endlocal
```

---

### 第四步：建立 Windows 主程式（約 20 分鐘）

建立 `main_windows.py`：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows 版本主程式
整合 faster-whisper-xxl + Ollama

使用方式：
    python main_windows.py
    python main_windows.py --config custom_config.yaml
    python main_windows.py --verbose
"""
import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 確保工作目錄正確
SCRIPT_DIR = Path(__file__).parent.resolve()
os.chdir(SCRIPT_DIR)
sys.path.insert(0, str(SCRIPT_DIR / "src"))

import yaml

# 設定日誌
def setup_logging(verbose: bool = False, log_dir: Path = None):
    """設定日誌系統"""
    level = logging.DEBUG if verbose else logging.INFO
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"transcription_{datetime.now():%Y%m%d_%H%M%S}.log"
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=handlers
    )
    return logging.getLogger(__name__)

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """載入配置檔"""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"找不到配置檔: {config_path}")
    
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def print_banner():
    """顯示程式標題"""
    print()
    print("=" * 60)
    print("           會議轉錄工具 - Windows 版")
    print("      faster-whisper-xxl + Ollama 本地 LLM")
    print("=" * 60)
    print()

def format_duration(seconds: float) -> str:
    """格式化時間"""
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins} 分 {secs} 秒"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours} 小時 {mins} 分"

def main():
    """主程式"""
    # 解析命令列參數
    parser = argparse.ArgumentParser(description="會議轉錄工具 - Windows 版")
    parser.add_argument("--config", default="config.yaml", help="配置檔路徑")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細輸出")
    args = parser.parse_args()
    
    print_banner()
    
    # 載入配置
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"[錯誤] 載入配置失敗: {e}")
        return 1
    
    # 設定日誌
    log_dir = Path(config.get("paths", {}).get("logs", "logs"))
    verbose = args.verbose or config.get("advanced", {}).get("verbose", False)
    logger = setup_logging(verbose, log_dir)
    
    logger.info(f"配置檔: {args.config}")
    
    # 延遲載入模組（避免 import 錯誤時沒有提示）
    try:
        from src.ollama_client import OllamaClient
        from src.whisper_windows import WhisperWindowsTranscriber
    except ImportError as e:
        logger.error(f"載入模組失敗: {e}")
        logger.error("請確認 src 目錄中有 ollama_client.py 和 whisper_windows.py")
        return 1
    
    # 初始化 Ollama 客戶端
    ollama_config = config["llm"]["ollama"]
    try:
        ollama = OllamaClient(
            base_url=ollama_config.get("base_url", "http://localhost:11434"),
            model=ollama_config.get("model", "llama3"),
            num_ctx=ollama_config.get("num_ctx", 32768),
            timeout=ollama_config.get("timeout", 600)
        )
    except Exception as e:
        logger.error(f"初始化 Ollama 失敗: {e}")
        return 1
    
    # 檢查 Ollama 連線
    if not ollama.is_running():
        logger.error("無法連線到 Ollama！")
        logger.error("請確認 Ollama 已啟動並運行中")
        return 1
    
    models = ollama.list_models()
    logger.info(f"Ollama 可用模型: {', '.join(models) if models else '(無法取得)'}")
    logger.info(f"使用模型: {ollama_config['model']}")
    
    # 檢查模型是否存在
    if models and ollama_config['model'] not in models:
        # 嘗試匹配不完整的名稱
        matched = [m for m in models if ollama_config['model'] in m]
        if matched:
            logger.info(f"匹配到模型: {matched[0]}")
        else:
            logger.warning(f"警告：模型 {ollama_config['model']} 可能未下載")
            logger.warning(f"請執行: ollama pull {ollama_config['model']}")
    
    # 初始化 Whisper 轉錄器
    whisper_config = config["whisper"]
    try:
        transcriber = WhisperWindowsTranscriber(
            exe_path=whisper_config.get("exe_path", "faster-whisper-xxl.exe"),
            model=whisper_config.get("model", "large-v3"),
            language=whisper_config.get("language", "zh"),
            device=whisper_config.get("device", "cuda")
        )
    except FileNotFoundError as e:
        logger.error(f"初始化 Whisper 失敗: {e}")
        return 1
    
    # 準備目錄
    input_dir = Path(config["paths"]["input"]).resolve()
    output_dir = Path(config["paths"]["output"]).resolve()
    temp_dir = Path(config["paths"]["temp"]).resolve()
    
    for d in [input_dir, output_dir, temp_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # 掃描輸入檔案
    extensions = [".mp3", ".mp4", ".wav", ".m4a", ".mkv", ".webm", ".flac", ".ogg"]
    files = sorted([
        f for f in input_dir.iterdir() 
        if f.is_file() and f.suffix.lower() in extensions
    ])
    
    if not files:
        logger.warning(f"input 資料夾沒有可處理的檔案: {input_dir}")
        logger.info(f"支援格式: {', '.join(extensions)}")
        return 0
    
    logger.info(f"找到 {len(files)} 個待處理檔案")
    
    # 處理設定
    use_cache = config.get("advanced", {}).get("use_cache", True)
    continue_on_error = config.get("advanced", {}).get("continue_on_error", True)
    system_prompt = config.get("system_prompt", "")
    
    # 統計
    success_count = 0
    fail_count = 0
    total_start = datetime.now()
    
    # 處理每個檔案
    for i, file_path in enumerate(files, 1):
        print()
        logger.info("=" * 50)
        logger.info(f"[{i}/{len(files)}] 處理: {file_path.name}")
        logger.info("=" * 50)
        
        file_start = datetime.now()
        
        try:
            # === 步驟 1：語音轉文字 ===
            logger.info("[步驟 1/3] 語音轉錄...")
            transcript = transcriber.transcribe(
                str(file_path),
                str(temp_dir),
                use_cache=use_cache
            )
            
            if not transcript.strip():
                logger.warning("轉錄結果為空，跳過此檔案")
                fail_count += 1
                continue
            
            # === 步驟 2：LLM 摘要 ===
            logger.info("[步驟 2/3] LLM 摘要生成...")
            
            prompt = f"""以下是會議逐字稿，請整理成結構化的會議摘要：

=== 逐字稿開始 ===
{transcript}
=== 逐字稿結束 ===

請按照指定格式輸出摘要。"""
            
            summary = ollama.generate(prompt, system_prompt)
            
            if not summary.strip():
                logger.warning("LLM 摘要為空")
                summary = "（摘要生成失敗，請檢查 Ollama 設定）"
            
            # === 步驟 3：生成輸出檔案 ===
            logger.info("[步驟 3/3] 生成 Markdown...")
            
            output_file = output_dir / f"{file_path.stem}_摘要.md"
            
            content = f"""# {file_path.stem} - 會議摘要

> **生成時間**：{datetime.now():%Y-%m-%d %H:%M:%S}  
> **原始檔案**：{file_path.name}  
> **轉錄模型**：{whisper_config['model']}  
> **摘要模型**：{ollama_config['model']}

---

{summary}

---

## 📝 原始逐字稿

<details>
<summary>點擊展開完整逐字稿（{len(transcript)} 字）</summary>

```
{transcript}
```

</details>

---

*本文件由會議轉錄工具自動生成*
"""
            
            output_file.write_text(content, encoding="utf-8")
            
            file_elapsed = (datetime.now() - file_start).total_seconds()
            logger.info(f"[完成] 輸出: {output_file.name}")
            logger.info(f"[耗時] {format_duration(file_elapsed)}")
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"[錯誤] 處理失敗: {e}")
            fail_count += 1
            
            if not continue_on_error:
                logger.error("設定為錯誤時停止，終止處理")
                break
    
    # 顯示統計
    total_elapsed = (datetime.now() - total_start).total_seconds()
    
    print()
    logger.info("=" * 50)
    logger.info("處理完成！")
    logger.info("=" * 50)
    logger.info(f"成功: {success_count} 個檔案")
    logger.info(f"失敗: {fail_count} 個檔案")
    logger.info(f"總耗時: {format_duration(total_elapsed)}")
    logger.info(f"輸出目錄: {output_dir}")
    print()
    
    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## 🔒 安全性處理（內部使用）

### 方案：IT 白名單（零成本）

對於組織內部使用，**不需要購買程式碼簽章證書**。請 IT 執行以下操作：

#### Windows Defender 例外

```powershell
# ⚠️ 必須以「系統管理員身分」執行 PowerShell

# 方法 1：將整個工具資料夾加入例外（推薦）
Add-MpPreference -ExclusionPath "C:\Tools\會議轉錄工具"

# 方法 2：只排除特定執行檔
Add-MpPreference -ExclusionPath "C:\Tools\會議轉錄工具\faster-whisper-xxl.exe"
Add-MpPreference -ExclusionPath "C:\Tools\會議轉錄工具\python\python.exe"

# 驗證例外設定
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
```

#### SmartScreen 處理

內部網路共享的檔案通常不會觸發 SmartScreen。如果檔案是從網路下載的：

```powershell
# 移除所有檔案的「來自網路」標記（Zone.Identifier）
Get-ChildItem "C:\Tools\會議轉錄工具" -Recurse | Unblock-File

# 驗證（應該不會顯示任何 Zone.Identifier）
Get-ChildItem "C:\Tools\會議轉錄工具" -Recurse | Get-Item -Stream Zone.Identifier -ErrorAction SilentlyContinue
```

#### 企業 EDR 處理

請 IT 將以下程序加入白名單：

| 程式 | 路徑 | 說明 |
|------|------|------|
| faster-whisper-xxl.exe | 專案根目錄 | 語音轉錄引擎 |
| python.exe | python\ 目錄 | Python 直譯器 |
| curl.exe | 系統內建 | 用於檢查 Ollama 服務 |

**提供給 IT 的 SHA-256 雜湊值**：

```powershell
# 產生檔案雜湊值供 IT 驗證
Get-FileHash "C:\Tools\會議轉錄工具\faster-whisper-xxl.exe" -Algorithm SHA256
Get-FileHash "C:\Tools\會議轉錄工具\python\python.exe" -Algorithm SHA256
```

## 🐛 常見問題排除

### Q1：批次腳本顯示亂碼

**症狀**：執行 .bat 檔案時，中文顯示為問號或方塊

**解決方案**：
1. 用 VS Code 或 Notepad 開啟 .bat 檔案
2. 以「UTF-8 with BOM」編碼重新儲存
3. 確認 `chcp 65001` 在腳本開頭

### Q2：Ollama 連線失敗

**症狀**：顯示「無法連線到 Ollama」

**解決方案**：
```powershell
# 1. 確認 Ollama 正在運行
ollama list

# 2. 測試 API 連線
curl http://localhost:11434/api/tags

# 3. 如果沒有回應，啟動 Ollama
ollama serve

# 4. 確認防火牆沒有阻擋 port 11434
```

### Q3：CUDA 無法使用 / GPU 未偵測到

**症狀**：轉錄使用 CPU，非常慢

**解決方案**：
```powershell
# 1. 確認 NVIDIA 驅動程式
nvidia-smi

# 2. 如果指令不存在，安裝最新驅動
# https://www.nvidia.com/drivers

# 3. 確認 CUDA 可用
# 在 faster-whisper-xxl 同目錄應該有 cudnn*.dll 等檔案
```

### Q4：Python 套件安裝失敗

**症狀**：pip install 顯示錯誤

**解決方案**：
```powershell
# 如果使用 Python Embedded
# 1. 確認已編輯 python311._pth 檔案
# 2. 確認已取消註解 import site
# 3. 確認已新增 Lib\site-packages 路徑

# 建議改用 WinPython（已預設配置好）
```

### Q5：逐字稿為空或品質差

**症狀**：轉錄結果是空的或錯誤很多

**解決方案**：
1. 確認音訊檔案可以正常播放
2. 嘗試較大的模型（如 large-v3）
3. 檢查語言設定是否正確
4. 音訊品質太差時考慮預處理

### Q6：LLM 摘要品質不佳

**症狀**：摘要內容不準確或格式錯誤

**解決方案**：
1. 嘗試不同的模型（qwen2 對中文較好）
2. 調高 num_ctx 參數（如果逐字稿被截斷）
3. 調整 temperature（較低會更精確）
4. 修改系統提示詞

---

## 💰 成本分析

| 項目 | 成本 |
|------|------|
| faster-whisper-xxl | **$0**（開源） |
| 可攜式 Python | **$0**（官方免費） |
| Ollama | **$0**（已安裝） |
| 本地 LLM 模型 | **$0**（開源） |
| 程式碼簽章 | **$0**（內部使用不需要） |
| **總計** | **$0** |

---

## ⚡ 效能預估

### RTX 4090 + faster-whisper-xxl

| 音訊長度 | 轉錄時間 | 速度比 |
|----------|----------|--------|
| 10 分鐘 | ~30 秒 | **20x** |
| 30 分鐘 | ~1.5 分鐘 | **20x** |
| 1 小時 | ~3 分鐘 | **20x** |
| 2 小時 | ~6 分鐘 | **20x** |

### Ollama 本地 LLM

| 模型 | VRAM 需求 | 摘要生成時間（約 5000 字逐字稿） | 中文品質 |
|------|----------|--------------------------------|----------|
| llama3.1:8b | ~5GB | 約 30-60 秒 | ⭐⭐⭐ |
| qwen2.5:7b | ~5GB | 約 30-60 秒 | ⭐⭐⭐⭐⭐ |
| mistral:7b | ~5GB | 約 20-40 秒 | ⭐⭐⭐ |
| llama3.1:70b | ~40GB | 約 2-3 分鐘 | ⭐⭐⭐⭐ |

> 💡 **推薦**：RTX 4090 (24GB) 建議使用 `qwen2.5:7b` 或 `llama3.1:8b`，中文摘要品質最佳。

---

## 📋 實施時程

```
第 1 天（約 2 小時）：
├── 下載 faster-whisper-xxl 獨立執行檔
├── 下載可攜式 Python
├── 複製專案程式碼
└── 安裝 Python 依賴

第 2 天（約 2 小時）：
├── 建立 ollama_client.py
├── 建立 whisper_windows.py
├── 修改 config.yaml
└── 建立批次腳本

第 3 天（約 1 小時）：
├── 測試完整流程
├── 調整配置
└── IT 設定白名單
```

**總計：約 5 小時即可完成部署**

---

## ✅ 檢核清單

### 部署前準備

- [ ] 確認 Windows PC 有安裝 NVIDIA 驅動程式（執行 `nvidia-smi` 驗證）
- [ ] 確認 Ollama 已安裝（執行 `ollama list` 驗證）
- [ ] 確認有可用的 LLM 模型（如 `ollama pull qwen2.5:7b`）
- [ ] 下載 faster-whisper-xxl 獨立執行檔
- [ ] 下載可攜式 Python 3.11（推薦 WinPython）

### 檔案建立

- [ ] 建立 `src/ollama_client.py`
- [ ] 建立 `src/whisper_windows.py`
- [ ] 建立 `config.yaml`（Windows 版本）
- [ ] 建立 `main_windows.py`
- [ ] 建立 `開始轉錄.bat`（⚠️ UTF-8 with BOM 編碼）

### 資料夾結構

- [ ] 建立 `input/` 資料夾
- [ ] 建立 `output/` 資料夾
- [ ] 建立 `temp/` 資料夾
- [ ] 建立 `logs/` 資料夾

### 測試驗證

- [ ] 測試 faster-whisper-xxl 單獨執行
  ```cmd
  faster-whisper-xxl.exe --help
  ```
- [ ] 測試 Ollama API 連線
  ```cmd
  curl http://localhost:11434/api/tags
  ```
- [ ] 測試 Python 環境
  ```cmd
  python\python.exe -c "import yaml; print('OK')"
  ```
- [ ] 測試完整流程（放入測試音訊執行）
- [ ] 驗證輸出 Markdown 品質

### IT 設定（如需要）

- [ ] Windows Defender 例外設定
- [ ] 移除檔案網路標記（Unblock-File）
- [ ] EDR 白名單（如有）

---

## 🎯 總結

### 這個方案的優勢

1. **零成本**：所有組件都是免費的
2. **快速部署**：約 5 小時完成
3. **離線運行**：不需要網路連線
4. **資料安全**：所有處理都在本地
5. **效能卓越**：RTX 4090 提供極速轉錄
6. **簡單維護**：批次腳本易於理解和修改

### 核心原則

```
需求：會議音訊 → 結構化摘要

最簡方案：
  faster-whisper-xxl.exe（轉錄）
        ↓
  Ollama + 本地 LLM（摘要）
        ↓
  Markdown 輸出

執行方式：雙擊 .bat 檔案
```

**不需要**：
- ❌ 打包成 EXE
- ❌ 程式碼簽章
- ❌ 複雜的安裝程序
- ❌ 外部 API 費用

---

## 📚 參考資料

### 工具下載

| 工具 | 下載連結 | 說明 |
|------|----------|------|
| faster-whisper-xxl | [GitHub Releases](https://github.com/Purfview/whisper-standalone-win/releases) | 選擇最新的 `Faster-Whisper-XXL_rXXX_windows.zip` |
| Python Embedded | [Python 官方](https://www.python.org/downloads/windows/) | 選擇「Windows embeddable package (64-bit)」 |
| WinPython | [WinPython 官方](https://winpython.github.io/) | 推薦下載精簡版（dot 版本） |
| Ollama | [Ollama 官方](https://ollama.ai/) | Windows 版安裝程式 |

### 技術文件

- [Ollama API 文件](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [faster-whisper 使用說明](https://github.com/Purfview/whisper-standalone-win)
- [Python Embedded 配置指南](https://dev.to/fpim/setting-up-python-s-windows-embeddable-distribution-properly-1081)

### 推薦的 Ollama 模型

```powershell
# 中文優化（推薦）
ollama pull qwen2.5:7b

# 通用（平衡）
ollama pull llama3.1:8b

# 快速
ollama pull mistral:7b

# 高品質（需要大量 VRAM）
ollama pull llama3.1:70b
```

---

> 📝 **文件版本**：2.1（深度優化版）  
> 📅 **最後更新**：2025-11-27  
> ✍️ **設計原則**：第一性原理、最小可行方案、可靠性優先  
> 🔍 **優化項目**：UTF-8 編碼處理、Python Embedded 配置、Ollama num_ctx 設定、錯誤處理、日誌系統
