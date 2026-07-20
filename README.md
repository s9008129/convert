# 政府智慧會議紀錄生成系統

[![Version](https://img.shields.io/badge/version-4.5.0-green)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-macOS%20|%20Windows%20|%20Linux-informational)](doc/操作手冊/)
[![Stability](https://img.shields.io/badge/stability-stable-brightgreen)](CHANGELOG.md)

> 將會議錄音自動轉換為結構化會議紀錄的智能系統，依**會議類型**套用專屬公文格式，支援 Markdown 與 Word (DOCX) 雙格式下載

> 📌 **本檔案用途**：介紹本專案的**用途、架構、設計理念與簡易操作**。
> 詳細的逐版變更紀錄請見 [CHANGELOG.md](CHANGELOG.md)；完整系統架構請見
> [系統架構與程式設計書](doc/規格與設計/系統架構與程式設計書.md)；
> 非技術使用者操作說明請見 [使用者手冊](doc/操作手冊/使用者手冊.md)；
> 正式環境的更新部署步驟請見 [部署更新手冊](doc/操作手冊/部署更新手冊_v4.1.md)。

## 🆕 最新版本：v4.5.0（2026-07-20）

**「科務會議」專屬模板＋列管資料附件輸出，模板系統首次擴充驗證。**

v4.4.0 建立的**會議模板系統**（`backend/core/templates.py`）已能讓每種會議類型
（一般會議／採購評選會／科務會議）套用各自的系統提示詞、結構驗證、記錄骨架、
DOCX 公文層次與領域術語表。v4.5.0 依使用者提供的真實科室會議範本，
新增「科務會議」模板，並補上**附件輸出**基礎設施：紀錄本文中的「決議事項
辦理情形彙整表」可由本文 Markdown **程式確定性抽出**，另外產出一份獨立的
「列管資料」Word 檔，無需 LLM 二次生成即可保證兩份文件內容一致。

- 科務會議紀錄結構：時間／地點／主持人／出席人員 → 歷次列管案件 →
  決議事項辦理情形彙整表（承辦股／同仁一目瞭然）→ 條列式科長指示 → 散會
- 前端新增「下載列管資料 (Word)」按鈕，依任務實際使用的模板動態顯示
- 新增 22 個測試，全套 **371 passed／3 skipped**；一般會議與採購評選會零回歸

> 完整變更內容 → 詳見 [CHANGELOG.md](CHANGELOG.md#v450---2026-07-20)。
> 上一版重點：[v4.4.0](CHANGELOG.md#v440---2026-07-17) 建立可擴充會議模板系統，
> 新增「採購評選會」模板（機敏內容強制本地處理、委員匿名／廠商實名）。

---

## ✨ 核心特性

### 🗂️ 會議類型模板系統（v4.4.0 起）
- 上傳前先選擇**會議類型**，系統自動套用專屬提示詞、驗證規則與 Word 排版：
  - **一般會議**（預設）：通用公文格式（報告事項／討論事項／主席裁示事項）
  - **科務會議**：科室官方範本，含決議事項辦理情形彙整表與獨立列管資料附件
  - **採購評選會**：工程會官方範本（壹、貳、參…），委員匿名、廠商具名、
    詢答逐項對應、機敏數字（個別評分／底價）強制不寫入紀錄
- 新增會議類型只需一個 prompt 模組＋一筆註冊，前端選單、驗證、Word 輸出全自動生效
- 機敏類型強制**僅限本地模式**：前端自動鎖定＋後端 400 雙重防護

### 🎯 雙模式部署
- **本地模式**：完整離線，資料不外傳，使用 Ollama（預設）／LM Studio + faster-whisper/transformers
- **雲端模式**：使用 Gemini API（分段併發萃取＋雙輸入生成，長會議紀錄豐富度與本地相當）

### 🚀 性能優化
- **GPU 加速**：支援 Apple MPS、NVIDIA CUDA
- **智能降級**：GPU 不可用時自動切換至 CPU
- **並行處理**：任務排隊系統，支援批次上傳
- **零 rebuild 部署**：Docker 以 volume 掛載程式碼，改程式或提示詞只需 `restart`

### 📋 功能完整
- 支援多種音訊格式（MP3、MP4、WAV、M4A、MKV、WebM 等）
- 語意校正機制：詞彙表 hotwords ＋ LLM 校正 ＋ 同音驗證閘門
- 自動生成結構化會議紀錄（依會議類型呈現不同章節與欄位）
- **雙格式下載**：Markdown (.md) 與 Word (.docx)，特定會議類型另有附件下載
- 實時轉錄進度顯示（WebSocket）
- RESTful API + WebSocket 支援

### 🔒 隱私安全
- 本地模式：100% 離線，零資料上傳
- 機敏會議類型（如採購評選會）強制鎖定本地模式，前後端雙重防護
- 自動清理：過期檔案自動刪除

## 🧠 設計理念與系統架構

### 為什麼這樣設計？（專案意圖）

本系統的目標是讓**公務機關**能把會議錄音，自動轉成**符合台灣政府公文格式、有憑有據、不杜撰**的會議紀錄，並依會議性質（一般行政會議、科室內部會議、涉機敏之採購評選會）套用不同的格式與保密規則。因此設計上有三個核心堅持：

1. **忠於逐字稿**：紀錄只能根據錄音內容生成，查不到的欄位一律標註「（待確認）」，**絕不臆測或杜撰**單位、人名、決議。
2. **可離線、保護隱私**：機敏會議可走「本地模式」全程離線，資料不外傳；涉法定機敏內容的會議類型（如採購評選會）更強制鎖定本地。
3. **格式可擴充**：不同會議類型的公文格式、驗證規則、機敏處理原則集中在會議模板註冊表，新增類型不影響既有類型的行為。

### 處理流程（從音檔到會議紀錄）

```
音檔  ──①語音辨識(ASR)──▶  逐字稿  ──②萃取式三階段──▶  會議紀錄(.md / .docx [+ 附件])
            faster-whisper /             LLM（依會議類型模板套用提示詞）
          transformers                 本地 Ollama/LM Studio 或雲端 Gemini
          Breeze-ASR-25/26
```

**核心是「萃取優先（extraction-first）」的三階段流程**，刻意把「讀懂內容」與「寫成公文」分開，以降低杜撰風險；v4.4.0 起，所選**會議類型模板**會為每個階段附加專屬規則：

| 階段 | 做什麼 | 目的 |
|---|---|---|
| ① 萃取筆記 | 從逐字稿逐段抽出「事實、決議、待辦」（依模板增補角色標註、詢答配對等規則） | 只看得到的，不腦補 |
| ② 合併整理 | 去重、歸納、排序 | 形成結構化素材 |
| ③ 生成＋自我校驗 | 套用模板公文格式產出，再**自動驗證並補強重寫**（含模板專屬的機敏洩漏檢查） | 攔截英文洩漏、贅字、簡體、杜撰、機敏資訊外流 |

> 第 ③ 階段的「驗證＋補強」防護**本地與雲端路徑皆已套用**，是會議紀錄品質的最後一道關卡。
> 完整的模板系統設計（`MeetingTemplate` 欄位、附件輸出機制、新增會議類型步驟）
> 請見 [系統架構與程式設計書 §6.5](doc/規格與設計/系統架構與程式設計書.md)。

### 技術組成（簡述）

- **後端**：FastAPI（提供網頁與 RESTful API，預設埠 `9527`）。
- **語音辨識**：`MediaTek-Research/Breeze-ASR-26`（transformers 路徑）／`faster-whisper` Breeze-ASR-25（可依環境切換）。
- **語言模型**：本地 Ollama（預設 `gemma4:31b`）／LM Studio，或雲端 Gemini（`gemini-3.1-flash-lite`）。
- **輸出**：Markdown 與 Word（DOCX，相容 Office 2024 / M365），依會議類型另有列管資料等附件。
- **部署**：Docker（GPU／標準兩種 compose，程式碼 volume 掛載、零 rebuild）或原生服務（`uv run` / `start_service.sh`）。

詳細更新紀錄請參閱：[CHANGELOG.md](CHANGELOG.md)

## 🚀 快速開始

### 系統需求

#### macOS
- **OS**: macOS 12.0+ (Apple Silicon 優先)
- **RAM**: 16GB+ (本地模式需要)
- **Storage**: 20GB (模型 + 資料)
- **GPU**: Apple MPS (自動)

#### Windows（推薦：Docker + NVIDIA GPU）
- **OS**: Windows 10/11
- **RAM**: 16GB+
- **Storage**: 20GB+
- **GPU**: NVIDIA CUDA（建議 RTX 系列，24GB VRAM 可承載較大上下文設定）

#### Linux
- **OS**: Ubuntu 20.04+
- **RAM**: 16GB+
- **Storage**: 20GB
- **GPU**: CUDA 或 CPU

### 安裝步驟（原生服務，使用 uv）

環境管理一律建議使用 [uv](https://docs.astral.sh/uv/)，不再手動維護 `venv`。

#### 1. 克隆專案
```bash
git clone https://github.com/s9008129/convert.git
cd convert
```

#### 2. 安裝 uv 並建立環境
```bash
# 安裝 uv（擇一）
winget install astral-sh.uv          # Windows
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS / Linux

# 建立虛擬環境＋安裝依賴（依 uv.lock 精準還原）
uv sync
```

**Windows + NVIDIA GPU（官方 ASR-26 / Transformers 必做）**：
```bash
python install_deps.py
uv run python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())"
```
若最後一行不是 `True`，代表目前仍是 CPU-only torch，請執行：
```bash
uv run python -m pip install --upgrade --force-reinstall -r requirements.windows-cuda.txt --prefer-binary
```

> 🚀 建議先預載官方 ASR-26 模型：
> ```bash
> uv run python scripts/download_models.py
> ```

#### 3. 配置環境變數
```bash
cp .env.example .env
# 編輯 .env 填入需要的設定（雲端模式需 GEMINI_API_KEY）
```
⚠️ **重要**：後端網頁服務（`backend/`）**所有設定一律來自環境變數／`.env`**
（見 `backend/core/config.py`）；根目錄的 `config.yaml`／`config.macos.yaml`
僅供舊版 CLI（`main.py`）使用，修改它們對網頁服務**完全無效**。

#### 4. 本地模型（擇一）
- **Ollama**（Docker 部署預設）：安裝後執行 `ollama pull gemma4:31b`，服務位址 `http://localhost:11434`
- **LM Studio**（原生服務常見選擇）：官網 https://lmstudio.ai ，載入模型後啟動本地 API（預設 `http://localhost:1234/v1`）

#### 5. 啟動服務
```bash
# 使用 uv（推薦）
uv run uvicorn backend.main:app --host 0.0.0.0 --port 9527 --reload

# 或使用提供的腳本
./start_service.sh
```

#### 6. 開啟瀏覽器
```
http://localhost:9527
```

### 安裝步驟（Docker，Windows + NVIDIA GPU）

正式環境建議使用 Docker，程式碼以 volume 掛載，日常更新程式碼或提示詞
只需 `restart`、不需重新 build：

```bash
cd docker
docker compose -f docker-compose-windows-gpu.yml build   # 僅首次或依賴變更時
docker compose -f docker-compose-windows-gpu.yml up -d

# 日常更新（改程式碼/提示詞後）：
git pull && docker compose -f docker-compose-windows-gpu.yml restart
```

> 🚫 頻寬紅線：嚴禁 `build --no-cache`（會重抓依賴數百 MB～數 GB）；
> 嚴禁 `docker compose down -v`（會清空 ASR 模型 volume，需重新下載）。
> 完整部署與更新步驟請見 [部署更新手冊](doc/操作手冊/部署更新手冊_v4.1.md)。

## 📖 使用說明

### Web 介面

1. **選擇會議類型**
   - 一般會議（預設）／科務會議／採購評選會，清單由 `/api/config` 動態提供
   - 涉機敏內容的類型（如採購評選會）會自動鎖定本地模式

2. **選擇處理模式**
   - 本地模式：完全離線，無需網路
   - 雲端模式：需要 Gemini API 金鑰（機敏會議類型無法選取）

3. **上傳音檔**
   - 支援格式：MP3, MP4, WAV, M4A, MKV, WebM, FLAC, OGG, AVI, MOV
   - 檔案大小上限依 `.env` 的 `MAX_FILE_SIZE_MB` 設定（預設 200MB）
   - 批次上傳：依 `ENABLE_BATCH_UPLOAD` 設定

4. **自動處理**
   - 實時進度顯示（WebSocket）
   - 逐字稿轉錄 → 語意校正 → 會議紀錄生成
   - 結果下載（Markdown、Word，特定會議類型另有列管資料等附件）

### API 使用

#### 系統設定與會議類型清單
```bash
curl http://localhost:9527/api/config
```
回應包含 `meeting_templates`（各會議類型的 `id`／`display_name`／
`local_only`／`has_attachment` 等，前端選單資料來源）。

#### 健康檢查
```bash
curl http://localhost:9527/api/health
```

**回應**：
```json
{
  "status": "healthy",
  "version": "4.5.0",
  "gpu_available": true,
  "gpu_name": "NVIDIA GeForce RTX 4090",
  "ollama_available": true,
  "lmstudio_available": false,
  "gemini_available": true,
  "queue_status": { "queue_length": 0, "processing": 0 }
}
```

#### 上傳檔案
```bash
curl -F "file=@meeting.mp3" \
     -F "processing_mode=local" \
     -F "meeting_template=general" \
     http://localhost:9527/api/upload
```

#### 下載結果
```bash
# 會議紀錄本文（Word）
curl -O -J "http://localhost:9527/api/tasks/{task_id}/result?format=docx"

# 模板附件（如科務會議「列管資料」；僅該任務所用模板有定義附件時可用）
curl -O -J "http://localhost:9527/api/tasks/{task_id}/result?format=docx&doc=attachment"
```

#### WebSocket 連接（即時進度）
```javascript
const ws = new WebSocket(`ws://localhost:9527/ws/tasks/${taskId}`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.progress, data.status);
};
```

## ⚙️ 配置說明

> ⚠️ 以下環境變數僅適用於**後端網頁服務**（`backend/`）。根目錄的
> `config.yaml`／`config.macos.yaml` 僅供舊版 CLI（`main.py`）使用，
> 與網頁服務完全無關；完整變數清單請見 `.env.example`。

### 常用環境變數

| 變數名 | 預設值 | 說明 |
|-------|--------|------|
| `GEMINI_API_KEY` | - | Gemini API 金鑰（雲端模式必填） |
| `MAX_FILE_SIZE_MB` | `200` | 單檔最大大小（MB） |
| `ENABLE_BATCH_UPLOAD` | `false` | 是否允許批次上傳 |
| `MAX_CONCURRENT_TASKS` | `1` | 最大同時處理任務數 |
| `QUEUE_MAX_SIZE` | `50` | 排隊佇列最大長度 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 端點（Docker 內為 `host.docker.internal`） |
| `LOCAL_LLM_MODEL` | `gemma4:31b` | 本地 LLM 模型 |
| `LMSTUDIO_BASE_URL` | `http://localhost:1234/v1` | LM Studio 端點（OpenAI 相容 API） |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | 雲端 LLM 模型 |
| `WHISPER_MODEL` | `MediaTek-Research/Breeze-ASR-26` | Whisper / ASR 模型名稱 |
| `ENABLE_TRANSCRIPT_CORRECTION` | `true` | 是否啟用語意校正（詞彙表＋LLM＋同音閘門） |

## 📊 性能指標（參考值，依模型與硬體而異）

### 轉錄速度
- **Apple MPS**: 1 分鐘音頻 ≈ 6-10 秒
- **CUDA**: 1 分鐘音頻 ≈ 3-5 秒
- **CPU**: 1 分鐘音頻 ≈ 30-60 秒

### 記憶體用量
- **本地模式（LLM + ASR）**：閒置 2-3GB，處理中約 14-16GB（依模型大小而異）
- **雲端模式（Gemini API）**：約 1-2GB

## 🔧 故障排除

### 常見問題

#### Q: 服務無法啟動
```bash
# 檢查連接埠
lsof -i:9527          # macOS/Linux
netstat -ano | findstr :9527   # Windows

# 檢查依賴（uv 環境）
uv sync

# 檢查資料目錄
mkdir -p data/uploads data/outputs
```

#### Q: Ollama / LM Studio 連接失敗
```bash
# 確認 Ollama 正在運行
curl http://localhost:11434/api/tags

# 確認 LM Studio 正在運行
curl http://localhost:1234/v1/models
```

#### Q: 轉錄結果不佳
- 檢查音訊品質（建議 16kHz, mono）
- 機關常用專有名詞可加入詞彙表（`data/glossary/`），提升 ASR 與校正準確度
- 檢查所選會議類型是否符合實際會議性質（模板決定驗證規則與輸出格式）

#### Q: 有 NVIDIA GPU，但轉錄沒有使用 GPU
- 先執行 `uv run python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())"`
- 若結果是 `+cpu`、`None` 或 `False`，代表目前安裝的是 CPU-only torch
- 在 Windows + NVIDIA 環境請改執行：
```bash
uv run python -m pip install --upgrade --force-reinstall -r requirements.windows-cuda.txt --prefer-binary
```
- 重新啟動服務後再檢查 `/api/health` 或重新上傳音檔

#### Q: 記憶體不足
- 改用較小的本地 LLM 模型
- 關閉其他應用程式
- 檢查 Ollama / LM Studio 模型是否過大

### 日誌檔案
```bash
# 應用日誌
cat data/logs/app.log

# Docker 容器日誌
docker logs -f meetingscribe-app
```

## 📚 文件

- [系統架構與程式設計書](doc/規格與設計/系統架構與程式設計書.md) — 完整系統設計、模板系統、語意校正機制
- [使用者手冊](doc/操作手冊/使用者手冊.md) — 非技術使用者操作說明
- [部署更新手冊](doc/操作手冊/部署更新手冊_v4.1.md) — 正式環境部署與更新步驟
- [uv 管理說明](doc/操作手冊/uv管理說明.md) — 環境管理與依賴同步
- [CHANGELOG](CHANGELOG.md) — 完整逐版變更紀錄

## 🏗️ 技術棧

### 後端
- **框架**: FastAPI + Uvicorn
- **轉錄**: faster-whisper / transformers（Breeze-ASR-25/26）
- **LLM**: Ollama / LM Studio（本地） + Gemini API（雲端）
- **資料**: 檔案系統（任務、逐字稿、輸出、詞彙表）

### 前端
- **框架**: HTML5 + CSS3 + Vanilla JavaScript
- **功能**: 拖放上傳、會議類型選單（依 `/api/config` 動態渲染）、實時進度、結果下載

### 環境支援
- **Python**: 3.11+（`uv` 管理）
- **OS**: macOS 12+、Windows 10/11、Ubuntu 20.04+
- **GPU**: Apple MPS, NVIDIA CUDA, CPU
- **Office 相容性**: Office 2024, M365 (DOCX 輸出)

## 📝 版本歷史

### [v4.5.0] - 2026-07-20
- ✅ 新增「科務會議」專屬模板（依科室官方範本：彙整表、列管案件、條列指示）
- ✅ 附件輸出基礎設施：本文 Markdown 程式確定性抽出「列管資料」獨立 Word 檔
- ✅ 新增 22 個測試，全套 371 passed／3 skipped

### [v4.4.0] - 2026-07-17
- ✅ 建立可擴充**會議模板系統**（`backend/core/templates.py`）
- ✅ 新增「採購評選會」模板：工程會官方範本、委員匿名／廠商實名、詢答逐項對應
- ✅ 機敏會議類型強制本地處理（前端鎖定＋後端 400 雙防線）
- ✅ 原寫死的公文格式常數全面改由模板註冊表驅動，一般會議行為零回歸

### [v4.3.3] - 2026-07-08
- ✅ 雲端內容豐富度根治：分段併發萃取＋雙輸入生成，長會議紀錄品質與本地相當
- ✅ 品牌字樣移除、副標精簡放大

[查看完整歷史](CHANGELOG.md)

## 📧 聯絡方式

- Issues: https://github.com/s9008129/convert/issues

## 🙏 致謝

感謝以下開源專案：
- [FastAPI](https://github.com/tiangolo/fastapi)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) / [CTranslate2](https://github.com/OpenNMT/CTranslate2)
- [MediaTek Research Breeze-ASR](https://huggingface.co/MediaTek-Research)
- [Ollama](https://ollama.com) / [LM Studio](https://lmstudio.ai)
- [Google Gemini](https://ai.google.dev)

---

**政府智慧會議紀錄生成系統**

Last updated: 2026-07-20
