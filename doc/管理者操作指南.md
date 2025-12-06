# 🎯 MeetingScribe 管理者操作指南

> **版本**: v3.4.4  
> **建立日期**: 2025-12-06  
> **適用對象**: 系統管理者、專案負責人、維運人員  
> **目的**: 用友善、非技術人員可理解的方式，說明整個專案的管理、維護、Debug

---

## 📑 目錄

1. [專案簡介](#專案簡介)
2. [系統架構說明](#系統架構說明)
3. [跨平台部署方式](#跨平台部署方式)
4. [設定檔對映表](#設定檔對映表)
5. [Docker Rebuild 時機判斷](#docker-rebuild-時機判斷)
6. [GPU 加速條件與相依](#gpu-加速條件與相依)
7. [常見問題 Q&A](#常見問題-qa)
8. [維護與Debug指南](#維護與debug指南)

---

## 專案簡介

### 🎯 這個專案是什麼？

MeetingScribe 是一個**會議錄音自動轉文字並生成會議記錄的工具**。

**簡單來說**：
1. 你上傳一個會議錄音檔（MP3、WAV、MP4 等）
2. 系統自動將語音轉成逐字稿（使用 Whisper AI）
3. 系統再將逐字稿整理成結構化的會議記錄（使用 LLM AI）
4. 你下載整理好的會議記錄（Markdown 格式）

### 🔒 兩種處理模式

| 模式 | 說明 | 優點 | 缺點 | 適用場景 |
|------|------|------|------|----------|
| **本地模式** | 資料在你電腦上處理，不上傳雲端 | 安全、隱私、不需網路 | 品質較一般 | 政府、醫療、商業機密 |
| **雲端模式** | 使用 Google Gemini API 處理 | 品質優秀 | 需網路、資料上傳 | 一般會議、非機敏資料 |

### 📦 為什麼用 Docker？

**傳統方式的問題**：
- 要裝 Python、CUDA、各種套件
- 每台電腦環境不同，常常裝不起來
- Windows、Mac 設定方式差異大

**Docker 的好處**：
- 像「打包便當」一樣，所有東西都包在一起
- 直接拿到新電腦，解壓就能用
- 不會影響電腦原本的設定

---

## 系統架構說明

### 🏗️ 系統組成（非技術說明）

想像這是一個「會議記錄製作工廠」：

```
┌─────────────────────────────────────────────────────────┐
│                   MeetingScribe 系統                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1️⃣ 【前台】網頁介面                                      │
│     - 讓你上傳檔案、選擇模式、下載結果                     │
│     - 位置：frontend/ 資料夾                             │
│                                                          │
│  2️⃣ 【後台】處理引擎                                      │
│     - 負責實際轉錄和摘要                                  │
│     - 位置：backend/ 資料夾                              │
│                                                          │
│  3️⃣ 【AI 引擎】兩個 AI 模型                               │
│     - Whisper：語音轉文字                                │
│     - LLM（Gemma3 或 Gemini）：文字摘要                  │
│                                                          │
│  4️⃣ 【資料庫】檔案儲存                                    │
│     - 上傳的檔案放在 data/uploads/                       │
│     - 處理結果放在 data/outputs/                         │
│     - 快取資料放在 data/cache/                           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 🖥️ 跨平台架構差異

#### Windows 11 + RTX 4090（GPU 加速版）

```
主機（你的電腦）
├── Ollama（本地 AI 引擎）─── 運行 Gemma3 模型
├── NVIDIA 驅動程式 ─────── 提供 GPU 支援
│
└── Docker 容器（隔離環境）
    ├── Whisper（語音轉文字）─ 使用 GPU 加速
    ├── 後端服務（FastAPI）
    └── 前端網頁（靜態檔案）

連接方式：容器透過 host.docker.internal 連接主機的 Ollama
```

**重點**：
- Ollama 不在 Docker 裡，在你的電腦上
- Whisper 在 Docker 裡，但可以用你電腦的 GPU
- 前後端都在 Docker 裡

#### macOS（CPU 模式）

```
主機（你的 Mac）
├── Ollama（本地 AI 引擎）─── 運行 Gemma3 模型，使用 MPS 加速
│
└── Docker 容器（隔離環境）
    ├── Whisper（語音轉文字）─ 使用 CPU（Mac 不支援 GPU 直通）
    ├── 後端服務（FastAPI）
    └── 前端網頁（靜態檔案）

連接方式：容器透過 host.docker.internal 連接主機的 Ollama
```

**重點**：
- Mac 的 Docker 不能用 GPU，Whisper 會比較慢
- Ollama 在 Mac 上可以用 Apple Silicon 的 MPS 加速
- 架構跟 Windows 類似，只是 Whisper 用 CPU

---

## 跨平台部署方式

### 📋 部署前準備（所有平台共通）

**必裝項目**：
1. ✅ Docker Desktop（[下載位置](https://www.docker.com/products/docker-desktop/)）
2. ✅ Ollama（[下載位置](https://ollama.ai/)）
3. ✅ Gemma3 模型（安裝 Ollama 後執行：`ollama pull gemma3:27b-it-qat`）

**選裝項目**：
- Gemini API Key（只有用雲端模式才需要）
- NVIDIA 驅動（只有 Windows GPU 版需要）

---

### 🪟 Windows 11 快速部署（推薦使用批次檔）

#### 方法一：使用 .bat 批次檔（✅ 推薦，v3.3.3+）

**為什麼推薦**：
- 不受 PowerShell 執行策略限制
- 不需要管理員權限
- 企業環境也能用

**步驟**：

```batch
# 1. 開啟「命令提示字元」（不是 PowerShell）
#    按 Win+R → 輸入 cmd → Enter

# 2. 切換到專案目錄
cd D:\dev\convert

# 3. 建構 Docker 映像（首次約 10-30 分鐘）
scripts\deploy.bat build

# 4. 啟動服務
scripts\deploy.bat up

# 5. 開啟瀏覽器，訪問
#    http://localhost:9527
```

**其他指令**：
```batch
scripts\deploy.bat status      # 查看服務狀態
scripts\deploy.bat logs        # 查看日誌
scripts\deploy.bat restart     # 重啟服務
scripts\deploy.bat down        # 停止服務
```

#### 方法二：使用 PowerShell（舊版本）

**注意**：如果遇到「無法載入，因為系統已停用指令碼執行」錯誤，請改用方法一。

```powershell
# 1. 以系統管理員身分開啟 PowerShell

# 2. 切換到專案目錄
cd D:\dev\convert

# 3. 建構並啟動
.\scripts\deploy.ps1 build
.\scripts\deploy.ps1 up
```

#### Windows GPU 版專用部署

如果你有 NVIDIA 顯示卡（如 RTX 4090），使用 GPU 加速版：

```batch
# 使用 GPU 專用配置檔
cd D:\dev\convert\docker
docker compose -f docker-compose-windows-gpu.yml build --no-cache
docker compose -f docker-compose-windows-gpu.yml up -d

# 驗證 GPU 是否啟用
docker logs meetingscribe-app | findstr "CUDA"
```

---

### 🍎 macOS 快速部署

```bash
# 1. 開啟終端機（Terminal）

# 2. 切換到專案目錄
cd ~/dev/convert

# 3. 使用 Mac 專用腳本
chmod +x scripts/start-mac.sh
./scripts/start-mac.sh

# 4. 開啟瀏覽器，訪問
#    http://localhost:9527
```

**或使用 Docker Compose**：

```bash
cd ~/dev/convert/docker
docker compose -f docker-compose-mac.yml build
docker compose -f docker-compose-mac.yml up -d
```

**其他指令**：
```bash
./scripts/restart-mac.sh      # 重啟服務
docker compose -f docker/docker-compose-mac.yml logs -f   # 查看日誌
docker compose -f docker/docker-compose-mac.yml down      # 停止服務
```

---

## 設定檔對映表

### 📁 設定檔總覽（按用途分類）

這是最容易混淆的部分。以下用**情境分類**來說明：

#### 🎯 情境一：我想調整系統參數（檔案大小、排隊數量等）

**使用檔案**：`.env`（環境變數檔）

| 參數名稱 | 說明 | 預設值 | 範例 |
|---------|------|-------|------|
| `MAX_FILE_SIZE_MB` | 單檔上傳大小限制（MB） | 200 | `MAX_FILE_SIZE_MB=500` |
| `MAX_CONCURRENT_TASKS` | 同時處理幾個任務 | 1 | `MAX_CONCURRENT_TASKS=2` |
| `QUEUE_MAX_SIZE` | 最多可以排隊幾個 | 50 | `QUEUE_MAX_SIZE=100` |
| `GEMINI_API_KEY` | Gemini API 金鑰（雲端模式） | 無 | `GEMINI_API_KEY=AIza...` |
| `WHISPER_MODEL` | Whisper 模型大小 | medium | `WHISPER_MODEL=large-v3` |
| `LOCAL_LLM_MODEL` | 本地 LLM 模型 | gemma3:27b-it-qat | `LOCAL_LLM_MODEL=qwen2.5:7b` |

**修改方式**：
1. 用記事本打開 `.env` 檔案
2. 修改對應的值
3. 存檔後重啟服務（`scripts\deploy.bat restart`）

---

#### 🎯 情境二：我想改變會議記錄的格式或內容

**使用檔案**：`config.yaml`（系統提示詞設定）

**位置**：專案根目錄的 `config.yaml`

**關鍵區塊**：
```yaml
system_prompt: |
  【系統角色與任務】
  你是一位專業的政府機關資深承辦人員...
  
  【標準輸出格式 - 必須完全按照此格式】
  # 會議記錄摘要
  ## 1. 會議概況
  ...
```

**修改方式**：
1. 用記事本打開 `config.yaml`
2. 找到 `system_prompt:` 區塊
3. 修改你想要的格式或內容
4. 存檔後重啟服務

**⚠️ 注意**：
- 不要刪除 `【強制約束】` 和 `【語言要求】` 區塊
- 保持縮排正確（YAML 格式要求）

---

#### 🎯 情境三：我要部署到不同電腦（Windows/Mac/GPU）

**使用檔案**：Docker Compose 配置檔

| 檔案名稱 | 適用情境 | 何時使用 |
|---------|---------|---------|
| `docker-compose.yml` | Windows/Linux 通用版（CPU） | 沒有 NVIDIA GPU 的電腦 |
| `docker-compose-windows-gpu.yml` | Windows GPU 加速版 | Windows + RTX 4090 等 NVIDIA 顯卡 |
| `docker-compose-mac.yml` | macOS 專用版 | Mac 電腦（Intel 或 Apple Silicon） |

**選擇方式**：

```
你的電腦是什麼？
├─ Windows 11 + RTX 4090 
│  → 使用 docker-compose-windows-gpu.yml
│  → 指令：docker compose -f docker/docker-compose-windows-gpu.yml up -d
│
├─ Windows 11（無 NVIDIA 顯卡）
│  → 使用 docker-compose.yml
│  → 指令：scripts\deploy.bat up
│
└─ macOS（任何版本）
   → 使用 docker-compose-mac.yml
   → 指令：docker compose -f docker/docker-compose-mac.yml up -d
```

---

#### 🎯 情境四：我想改變 Dockerfile（專家級）

**使用檔案**：Dockerfile

| 檔案名稱 | 適用情境 |
|---------|---------|
| `Dockerfile` | Windows/Linux 通用版（不含 GPU 支援） |
| `Dockerfile.gpu` | Windows GPU 版（包含 CUDA + cuDNN） |
| `Dockerfile.mac` | macOS 版 |

**⚠️ 警告**：修改 Dockerfile 需要技術背景，建議不要輕易修改。

---

### 📊 設定檔決策樹（快速查找）

```
我想要做什麼？

├─ 調整上傳檔案大小、排隊數量
│  → 修改 .env
│  → 重啟服務即可（不需 rebuild）
│
├─ 改變會議記錄格式或 AI 行為
│  → 修改 config.yaml
│  → 重啟服務即可（不需 rebuild）
│
├─ 部署到不同電腦或平台
│  → 選擇對應的 docker-compose-xxx.yml
│  → 需要 rebuild
│
├─ 修改 Python 程式碼
│  → 修改 backend/ 或 frontend/
│  → 重啟服務即可（開發模式有 volume mount）
│
└─ 安裝新的 Python 套件或系統套件
   → 修改 requirements.txt 或 Dockerfile
   → 需要 rebuild
```

---

## Docker Rebuild 時機判斷

### 🤔 什麼時候需要 Rebuild？

這是最常見的困惑。用**紅綠燈**來判斷：

#### 🟢 綠燈：不需要 Rebuild（只需重啟）

| 修改內容 | 原因 | 重啟指令 |
|---------|------|---------|
| `.env` 環境變數 | Docker 啟動時讀取 | `scripts\deploy.bat restart` |
| `config.yaml` 設定檔 | 程式執行時讀取 | `scripts\deploy.bat restart` |
| `backend/*.py` Python 程式 | Volume mount 即時同步 | `scripts\deploy.bat restart` |
| `frontend/*.html/css/js` 前端檔案 | Volume mount 即時同步 | 重整瀏覽器即可 |

**判斷口訣**：「如果只是改參數或程式碼，重啟就好」

---

#### 🟡 黃燈：建議 Rebuild（但不一定必要）

| 修改內容 | 原因 | Rebuild 指令 |
|---------|------|------------|
| `requirements.txt` 新增套件 | 需要安裝新的 Python 套件 | `scripts\deploy.bat build` |
| Docker Compose 環境變數 | 確保設定正確套用 | `scripts\deploy.bat build` |

**判斷口訣**：「如果加了新功能或新套件，最好 rebuild」

---

#### 🔴 紅燈：一定要 Rebuild

| 修改內容 | 原因 | Rebuild 指令 |
|---------|------|------------|
| `Dockerfile` 或 `Dockerfile.gpu` | 改變 Docker 映像構建方式 | `docker compose ... build --no-cache` |
| 切換 GPU/CPU 版本 | 需要不同的基底映像 | `docker compose ... build --no-cache` |
| 系統套件變更（apt install） | 需要在映像中安裝 | `docker compose ... build --no-cache` |

**判斷口訣**：「如果改了 Dockerfile，一定要 rebuild」

---

### ⏱️ Rebuild 時間估算

| 情境 | 首次 Build | 有快取 Rebuild | 使用 --no-cache |
|------|-----------|---------------|----------------|
| CPU 版 | 10-15 分鐘 | 2-3 分鐘 | 10-15 分鐘 |
| GPU 版（Windows） | 20-30 分鐘 | 3-5 分鐘 | 20-30 分鐘 |
| Mac 版 | 15-20 分鐘 | 2-4 分鐘 | 15-20 分鐘 |

**時間差異原因**：
- GPU 版需要下載 CUDA、cuDNN（約 5GB）
- Whisper 模型下載（約 1.5GB，但有 Volume 快取）
- Python 套件安裝（約 2GB）

---

### 🎯 快速判斷表（一分鐘版）

```
修改了什麼？
├─ .env、config.yaml → 重啟 ✅
├─ Python 程式碼 → 重啟 ✅
├─ 前端 HTML/CSS/JS → 重整瀏覽器 ✅
├─ requirements.txt → Rebuild 🔄
└─ Dockerfile → Rebuild --no-cache 🔄
```

---

## GPU 加速條件與相依

### 🎮 GPU 加速是什麼？

**簡單說明**：
- GPU（顯示卡）比 CPU（處理器）快很多，特別是 AI 運算
- 有 GPU：處理 60 分鐘錄音約 6 分鐘
- 沒 GPU：處理 60 分鐘錄音約 30 分鐘

---

### ✅ GPU 加速的條件（缺一不可）

#### 1️⃣ 硬體條件

| 項目 | 要求 | 檢查方式 |
|------|------|---------|
| 顯示卡 | NVIDIA GTX 1060 以上 | 裝置管理員 → 顯示卡 |
| VRAM | 6GB 以上（建議 12GB+） | 執行 `nvidia-smi` |
| 作業系統 | Windows 10/11 或 Linux | - |

**❌ 不支援**：
- AMD 顯示卡（RX 系列）
- Intel 內顯
- macOS（Docker 不支援 GPU 直通）

---

#### 2️⃣ 軟體條件

**必裝清單**：

| 軟體 | 版本要求 | 下載位置 | 檢查指令 |
|------|---------|---------|---------|
| NVIDIA 驅動程式 | 520 以上 | [NVIDIA 官網](https://www.nvidia.com/Download/index.aspx) | `nvidia-smi` |
| NVIDIA Container Toolkit | 最新版 | [安裝指南](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) | `docker run --gpus all nvidia/cuda:12.0-base nvidia-smi` |
| Docker Desktop GPU 支援 | 已啟用 | Settings → Resources → GPU | - |

**安裝順序**：
1. 安裝 NVIDIA 驅動程式
2. 安裝 Docker Desktop
3. 安裝 NVIDIA Container Toolkit
4. 在 Docker Desktop 啟用 GPU 支援

---

#### 3️⃣ Docker 配置條件

**使用正確的配置檔**：

```bash
# ✅ 正確：GPU 版配置檔
docker compose -f docker/docker-compose-windows-gpu.yml up -d

# ❌ 錯誤：通用版不支援 GPU
docker compose -f docker/docker-compose.yml up -d
```

**確認配置檔中有 GPU 設定**：

```yaml
# docker-compose-windows-gpu.yml 必須包含
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

---

### 🔍 如何驗證 GPU 是否啟用？

#### 步驟一：檢查容器內是否偵測到 GPU

```bash
# Windows
docker exec meetingscribe-app python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# 預期輸出：
# CUDA available: True
```

#### 步驟二：檢查日誌

```bash
docker logs meetingscribe-app | findstr "CUDA"

# 預期輸出：
# ✅ 偵測到 NVIDIA GPU: NVIDIA GeForce RTX 4090，使用 CUDA 加速
# 裝置偵測完成: cuda, 精度: float16
# 載入 Whisper 模型: medium, 裝置: cuda, 精度: float16
```

#### 步驟三：上傳測試檔案

上傳一個音訊檔案，查看處理時間：
- GPU 模式：約 10 分鐘音訊 1 分鐘處理
- CPU 模式：約 10 分鐘音訊 5 分鐘處理

---

### 🚨 GPU 加速常見問題（第一性原理分析）

#### 問題一：`libcudnn_ops_infer.so.8: cannot open shared object file`

**根本原因**：
- CTranslate2（Whisper 底層）需要 **cuDNN 8**（不是 cuDNN 9）
- 官方文件明確說明：語音識別模型需要 cuDNN 8

**解決方案**：
```dockerfile
# 必須在 Dockerfile.gpu 中安裝 cuDNN 8
RUN apt-get install -y libcudnn8=8.9.7.29-1+cuda12.2
```

**驗證**：
```bash
docker exec meetingscribe-app ls -la /usr/lib/x86_64-linux-gnu/libcudnn_ops_infer.so.8
```

**參考文件**：[INSTRUCTIONS.md - cuDNN 依賴規則](.github/INSTRUCTIONS.md)

---

#### 問題二：顯示「CUDA available: True」但實際用 CPU

**根本原因**：
- 程式啟動時快取裝置偵測結果
- Ollama 佔用 VRAM 後，Whisper 誤判 GPU 不可用
- 快取機制阻止重新偵測

**解決方案**（v3.4.0 已修復）：
```python
# backend/services/transcription.py
# 每次轉錄前重置快取
device_detector.current_device = None
```

**驗證**：
```bash
docker logs meetingscribe-app | findstr "重新偵測"
```

---

#### 問題三：Docker 重建後模型要重新下載

**根本原因**：
- Whisper 模型在 Docker image layer 中
- `--no-cache` 清除所有 layer
- 模型約 1.5GB，每次都下載很慢

**解決方案**（v3.4.4 已修復）：
```yaml
# docker-compose-windows-gpu.yml
volumes:
  - meetingscribe-whisper-models:/app/models  # 持久化模型快取
```

**驗證**：
```bash
docker volume ls | findstr whisper-models
```

---

## 常見問題 Q&A

### 🔧 部署與啟動

#### Q1: 服務啟動失敗，顯示「port 9527 already in use」

**原因**：9527 埠被其他程式佔用。

**解決方式**：
```bash
# Windows：查看誰在用 9527 埠
netstat -ano | findstr :9527

# 找到 PID（最後一欄數字），然後關閉該程式
taskkill /PID <PID> /F

# 或修改 .env 改用其他埠
# PORT=9528
```

---

#### Q2: 執行 `deploy.bat` 出現「docker-compose: command not found」

**原因**：Docker Desktop 未啟動或未安裝。

**解決方式**：
1. 確認 Docker Desktop 已安裝
2. 啟動 Docker Desktop（系統列會出現鯨魚圖示）
3. 等待鯨魚圖示變綠（約 30 秒）
4. 重新執行指令

---

#### Q3: macOS 顯示「permission denied」

**原因**：腳本沒有執行權限。

**解決方式**：
```bash
chmod +x scripts/start-mac.sh
chmod +x scripts/restart-mac.sh
./scripts/start-mac.sh
```

---

### 🎯 功能與操作

#### Q4: 上傳檔案後一直卡在「處理中」

**可能原因與排查**：

1. **檢查服務狀態**：
   ```bash
   docker logs meetingscribe-app --tail 50
   ```

2. **常見狀況**：
   - GPU 記憶體不足 → 自動降級 CPU，會比較慢，耐心等待
   - Ollama 未啟動 → 日誌會顯示「connection refused」
   - 檔案太大 → 檢查 `.env` 的 `MAX_FILE_SIZE_MB`

---

#### Q5: 會議記錄輸出是英文，不是中文

**原因**（v3.4.4 已修復）：
- Gemma3 模型傾向使用輸入語言
- 逐字稿含英文時會切換英文模式

**解決方式**：
1. 確認使用 v3.4.4 或更新版本
2. 檢查 `backend/core/config.py` 是否有 `<language_enforcement>` 區塊
3. 檢查 `backend/services/summarization.py` user_message 是否有中文前綴

**驗證**：
```bash
docker logs meetingscribe-app | findstr "繁體中文"
```

---

#### Q6: 本地模式和雲端模式品質差很多

**說明**：
- 本地模式（Gemma3）：約雲端模式 70% 品質（v3.3.0 優化後）
- 雲端模式（Gemini）：最高品質

**建議**：
- 機敏資料：使用本地模式，接受品質折衷
- 一般會議：使用雲端模式，獲得最佳品質
- 或嘗試升級本地模型（如 `llama3.1:70b`，需 40GB+ VRAM）

---

### 🔐 安全與隱私

#### Q7: 本地模式真的不會上傳資料嗎？

**答案**：是的，100% 本地處理。

**驗證方式**：
```bash
# 斷開網路，本地模式仍可運作
# 查看網路連線
docker logs meetingscribe-app | findstr "http"
# 只會看到本地連線 (host.docker.internal:11434)
```

---

#### Q8: Gemini API Key 會不會外洩？

**安全措施**：
- API Key 存在 `.env` 檔案（不進版本控制）
- 使用 Pydantic `SecretStr` 保護（日誌不會顯示）
- 建議定期更換 API Key

---

### 🐛 Debug 與維護

#### Q9: 如何查看詳細錯誤訊息？

**方式一：Docker 日誌**
```bash
# 查看最新 100 行
docker logs meetingscribe-app --tail 100

# 即時追蹤日誌
docker logs meetingscribe-app -f
```

**方式二：檔案日誌**
```bash
# 日誌存在 logs/ 資料夾
ls logs/
# 用記事本打開最新的 .log 檔案
```

---

#### Q10: 系統變慢或記憶體不足

**檢查資源使用**：
```bash
# 查看容器資源
docker stats meetingscribe-app

# 查看 GPU 使用
nvidia-smi
```

**清理建議**：
```bash
# 清理過期檔案（自動清理機制 v2.3.7+）
curl -X POST http://localhost:9527/api/storage/cleanup

# 查看儲存空間
curl http://localhost:9527/api/storage/stats
```

---

#### Q11: Whisper 模型重新下載很慢，有快取嗎？

**答案**（v3.4.4 已優化）：
- 模型快取在 Docker Volume `meetingscribe-whisper-models`
- 首次下載後，rebuild 不會重新下載
- 除非你刪除 Volume：`docker volume rm meetingscribe-whisper-models`

**驗證**：
```bash
docker volume inspect meetingscribe-whisper-models
```

---

### 🔄 更新與維護

#### Q12: 如何更新到最新版本？

**步驟**：
```bash
# 1. 停止服務
scripts\deploy.bat down

# 2. 備份資料（重要！）
# 複製 data/ 資料夾到安全位置

# 3. 拉取最新程式碼
git pull origin main

# 4. 重新建構
scripts\deploy.bat build

# 5. 啟動服務
scripts\deploy.bat up
```

---

#### Q13: 如何備份資料？

**需要備份的內容**：
```
convert/
├── .env                    # ✅ API Key 和設定
├── config.yaml            # ✅ 系統提示詞
└── data/
    ├── uploads/           # ✅ 上傳的檔案
    └── outputs/           # ✅ 處理結果
```

**備份指令**：
```bash
# Windows
xcopy /E /I data data_backup_%date:~0,10%

# Mac/Linux
cp -r data data_backup_$(date +%Y%m%d)
```

---

#### Q14: 多久需要清理一次檔案？

**自動清理機制**（v2.3.7+）：
- 上傳檔案：1 天後自動刪除
- 處理結果：7 天後自動刪除
- 快取檔案：30 天後自動刪除
- 執行時間：每日凌晨 3:00

**手動清理**：
```bash
curl -X POST http://localhost:9527/api/storage/cleanup
```

---

## 維護與Debug指南

### 🛠️ 日常維護檢查清單

**每週檢查**（5 分鐘）：
- [ ] 服務健康檢查：`scripts\health-check.bat`
- [ ] 查看錯誤日誌：`docker logs meetingscribe-app --tail 50 | findstr ERROR`
- [ ] 確認 Ollama 運行：`ollama list`

**每月檢查**（15 分鐘）：
- [ ] 更新 Ollama 模型：`ollama pull gemma3:27b-it-qat`
- [ ] 檢查 Docker 映像更新：`docker images | findstr meetingscribe`
- [ ] 備份重要資料：`data/outputs/`

**每季檢查**（30 分鐘）：
- [ ] 更新系統到最新版本：`git pull && scripts\deploy.bat build`
- [ ] 檢查磁碟空間：`docker system df`
- [ ] 測試雲端模式（如有使用）：上傳測試檔案

---

### 🔍 Debug 流程（系統性排查）

#### 階段一：確認服務狀態

```bash
# 1. 檢查容器是否運行
docker ps | findstr meetingscribe
# 應該看到 STATUS 為 "Up"

# 2. 檢查網路連線
curl http://localhost:9527/api/health
# 應該回傳 {"status": "healthy"}

# 3. 檢查 Ollama 連線（本地模式）
curl http://localhost:11434/api/tags
# 應該看到模型列表
```

---

#### 階段二：分析錯誤日誌

```bash
# 查看最新錯誤
docker logs meetingscribe-app --tail 100 | findstr "ERROR\|WARN\|Exception"

# 常見錯誤代碼
# - "CUDA out of memory" → GPU 記憶體不足，降低 MAX_CONCURRENT_TASKS
# - "Connection refused" → Ollama 未啟動
# - "API key invalid" → Gemini API Key 錯誤
```

---

#### 階段三：驗證配置

```bash
# 檢查環境變數
docker exec meetingscribe-app env | findstr OLLAMA
docker exec meetingscribe-app env | findstr GEMINI

# 檢查模型是否載入
docker exec meetingscribe-app ls -la /app/models
```

---

#### 階段四：重建服務（最後手段）

```bash
# 完全清理並重建
scripts\deploy.bat down
docker system prune -f
scripts\deploy.bat build
scripts\deploy.bat up
```

---

### 📊 效能優化建議

#### 優化一：GPU 加速（最優先）

**效果**：速度提升 5-10 倍

**檢查清單**：
- [ ] 使用 `docker-compose-windows-gpu.yml`
- [ ] 安裝 NVIDIA 驅動 520+
- [ ] 安裝 NVIDIA Container Toolkit
- [ ] 驗證 `docker logs` 顯示 "CUDA"

---

#### 優化二：調整並發數

**適用情境**：多人同時使用

**設定**（`.env`）：
```bash
# 單 GPU 建議
MAX_CONCURRENT_TASKS=1  # RTX 3060 (12GB)
MAX_CONCURRENT_TASKS=2  # RTX 4090 (24GB)
MAX_CONCURRENT_TASKS=4  # A100 (40GB)
```

---

#### 優化三：模型選擇

**Whisper 模型**：
```bash
# 快速但準確度較低
WHISPER_MODEL=base

# 平衡（預設，推薦）
WHISPER_MODEL=medium

# 最高準確度但較慢
WHISPER_MODEL=large-v3
```

**本地 LLM 模型**：
```bash
# 快速但品質一般
LOCAL_LLM_MODEL=gemma3:12b

# 平衡（預設，推薦）
LOCAL_LLM_MODEL=gemma3:27b-it-qat

# 最高品質但需大 VRAM
LOCAL_LLM_MODEL=llama3.1:70b
```

---

### 🚨 緊急狀況處理

#### 狀況一：系統完全無回應

**步驟**：
```bash
# 1. 強制停止
docker stop meetingscribe-app

# 2. 清理殘留
docker rm meetingscribe-app

# 3. 重新啟動
scripts\deploy.bat up
```

---

#### 狀況二：處理結果不見了

**檢查位置**：
```bash
# 檢查 outputs 資料夾
dir data\outputs

# 檢查 Docker Volume
docker exec meetingscribe-app ls /app/data/outputs
```

**恢復方式**：
- 檢查自動清理設定（預設 7 天）
- 從備份恢復（如有）

---

#### 狀況三：API Key 洩漏

**立即行動**：
1. 前往 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 刪除舊的 API Key
3. 建立新的 API Key
4. 更新 `.env` 檔案
5. 重啟服務：`scripts\deploy.bat restart`

---

## 📞 支援與資源

### 📚 延伸閱讀

- [CHANGELOG.md](../CHANGELOG.md) - 完整版本歷史
- [INSTRUCTIONS.md](../.github/INSTRUCTIONS.md) - 開發最高指導原則
- [Windows批次檔部署指南](./Windows批次檔部署指南.md) - Windows 專用
- [MAC_Docker部署指南](./MAC_Docker部署指南.md) - macOS 專用
- [Docker映像檔Rebuild時機指南](./Docker映像檔Rebuild時機指南.md) - Rebuild 詳細說明

### 🆘 取得協助

**查看日誌**：
```bash
docker logs meetingscribe-app --tail 100 > debug.log
```

**提供以下資訊**：
- 作業系統和版本
- Docker Desktop 版本
- 錯誤訊息截圖
- `debug.log` 檔案

---

## 🎓 術語表（非技術人員版）

| 術語 | 簡單解釋 | 舉例 |
|------|---------|------|
| Docker | 像「打包便當」一樣把程式包起來 | 便當盒裡有飯、菜、湯，全部一起帶走 |
| Container（容器） | Docker 的「便當盒」 | 一個獨立的小環境，不影響外面 |
| Image（映像） | 便當的「食譜」 | 照著食譜做出一個一樣的便當 |
| Volume | Docker 的「外接硬碟」 | 存重要資料，容器刪了資料還在 |
| GPU | 顯示卡，專門做 AI 運算 | 就像請專業廚師煮，比自己煮快很多 |
| CUDA | NVIDIA GPU 的「工具箱」 | 讓程式可以使用 GPU |
| LLM | 大型語言模型，會寫文章的 AI | 像 ChatGPT 那樣的 AI |
| Whisper | 語音轉文字的 AI | 把錄音變成文字 |
| Ollama | 在你電腦上跑 AI 的工具 | 不用網路的 AI 引擎 |
| API Key | 像「會員卡號」 | 用來存取雲端服務的密碼 |

---

## ✅ 總結：管理者快速上手指南

### 三個核心概念

1. **Docker = 便當盒**：所有東西打包好，拿到哪都能用
2. **兩種模式**：本地（安全但慢）vs 雲端（快但上傳）
3. **改設定不用 Rebuild，改 Dockerfile 才要**

### 五個常用指令

```bash
scripts\deploy.bat up        # 啟動服務
scripts\deploy.bat down      # 停止服務
scripts\deploy.bat restart   # 重啟服務
scripts\deploy.bat logs      # 查看日誌
scripts\deploy.bat build     # 重新建構（慎用）
```

### 一個決策樹

```
遇到問題？
├─ 服務無法啟動 → 檢查 Docker Desktop 是否執行
├─ 處理很慢 → 檢查是否使用 GPU 版本
├─ 輸出英文 → 確認版本是 v3.4.4+
├─ API Key 錯誤 → 用 setup-api-key.ps1 重設
└─ 其他問題 → 查看 docker logs 尋找錯誤訊息
```

---

**🎉 恭喜你完成管理者操作指南！**

現在你應該能夠：
✅ 理解整個系統的架構  
✅ 在不同平台部署服務  
✅ 判斷何時需要 Rebuild  
✅ 設定 GPU 加速  
✅ 解決常見問題  
✅ 進行日常維護

**還有問題？** 參考 [常見問題 Q&A](#常見問題-qa) 或查看 [CHANGELOG.md](../CHANGELOG.md) 瞭解最新變更。
