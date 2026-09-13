# 政府智慧會議紀錄生成系統

[![Version](https://img.shields.io/badge/version-4.7.2-green)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-macOS%20|%20Windows%20|%20Linux-informational)](doc/操作手冊/)
[![Stability](https://img.shields.io/badge/stability-stable-brightgreen)](CHANGELOG.md)

> 將會議錄音自動轉換為結構化會議紀錄的智能系統，依**會議類型**套用專屬公文格式，支援 Markdown 與 Word (DOCX) 雙格式下載

> 📌 **本檔案用途**：介紹本專案的**用途、架構、設計理念與簡易操作**。
> 詳細的逐版變更紀錄請見 [CHANGELOG.md](CHANGELOG.md)；完整系統架構請見
> [系統架構與程式設計書](doc/規格與設計/系統架構與程式設計書.md)；
> 非技術使用者操作說明請見 [使用者手冊](doc/操作手冊/使用者手冊.md)；
> 正式環境的更新部署步驟請見 [部署更新手冊](doc/操作手冊/部署更新手冊_v4.1.md)。

## 🆕 最新版本：v4.7.2（2026-08-20）

**v4.7.2：修復地端公文段落編號階層不符標準**——地端弱模型（gemma4:31b）過去跳過中文數字層、
直接用阿拉伯數字條列各欄位；根因是共用提示詞未明講「一、→（一）→1、→（1）」階層與不可跳層規則，
補上規則後地端與雲端產出一致。詳見 [CHANGELOG](CHANGELOG.md#v472---2026-08-20)。

**同場：地端「空白會議紀錄」根因徹底根治——已於正式機真實模型（gemma4:31b／RTX 4090）驗證通過。**

2026-08 陸續發生的地端排程任務「空白會議紀錄」問題，經三輪根因分析全數解決：

- **v4.6.2**：診斷可見性——修復例外訊息為空導致「失敗原因」行消失的問題，
  補上模型預熱與 VRAM offload 偵測、瞬時錯誤重試。
- **v4.7.0**：VRAM offload 根治——Ollama 呼叫全面串流化（避免長生成撞逾時被誤殺）、
  ASR 改獨立子程序執行（確保 VRAM 完整歸還）、模型預熱自我修復＋失敗時任務級降級。
- **v4.7.1**：修復 v4.7.0 自身引入的迴歸——`done_reason=length`（輸出撞到
  `num_predict` 上限，內容完整只是被截斷，屬確定性結果）曾被誤判為可重試錯誤，
  導致整份紀錄失敗；現正確地「接受內容＋記警告」，並依 context 餘裕自動擴大
  `num_predict` 從源頭降低撞牆機率。已在正式機以真實長會議錄音完整驗證：
  截斷正確被接受、任務正常完成、產出結構完整的會議紀錄。

> 完整變更內容 → 詳見 [CHANGELOG.md](CHANGELOG.md#v472---2026-08-20)。
> 根因全貌與研究過程：[v4.7.0](CHANGELOG.md#v470---2026-08-19)、
> [v4.6.2](CHANGELOG.md#v462---2026-08-19)。
> 🍎 **Unreleased（尚未指派版本號）**：macOS ASR 收斂為唯一 Apple SpeechAnalyzer
> （移除 Whisper 選項與 fallback、相依淨空），詳見 [CHANGELOG](CHANGELOG.md) 最上方條目。

---

## ✨ 核心特性

### 🗂️ 會議類型模板系統（v4.4.0 起）
- 上傳前先選擇**會議類型**，系統自動套用專屬提示詞、驗證規則與 Word 排版：
  - **一般會議**（預設）：通用公文格式（報告事項／討論事項／主席裁示事項）
  - **科務會議**：科室官方範本，含決議事項辦理情形彙整表與獨立列管資料附件
  - **採購評選會**：工程會官方範本（壹、貳、參…），委員匿名、廠商具名、
    詢答逐項對應、機敏數字（個別評分／底價）強制不寫入紀錄
  - **ISMS 月工作會議**（v4.6.0）：機關「會議記錄表」表單式官方版面，
    LLM 產出標籤式欄位、程式確定性渲染成固定表格 DOCX
- 新增會議類型只需一個 prompt 模組＋一筆註冊，前端選單、驗證、Word 輸出全自動生效
- 機敏類型強制**僅限本地模式**：前端自動鎖定＋後端 400 雙重防護

### 🎯 雙模式部署
- **本地模式**：完整離線，資料不外傳，使用 Ollama（預設）／LM Studio＋本機 ASR（macOS 26+：Apple SpeechAnalyzer；Windows/Linux：faster-whisper／transformers）
- **雲端模式**：使用 Gemini API（分段併發萃取＋雙輸入生成，長會議紀錄豐富度與本地相當）

### 🚀 性能優化
- **GPU 加速**：macOS ASR 走 Apple 神經引擎（SpeechAnalyzer，不佔用 MLX/MPS）；Windows/Linux 支援 NVIDIA CUDA
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
   Apple SpeechAnalyzer（macOS 26+ 預設）／  LLM（依會議類型模板套用提示詞）
   faster-whisper / transformers            本地 Ollama/LM Studio 或雲端 Gemini
   Breeze-ASR-25/26（Windows/Linux 維持既有路徑）
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
- **語音辨識**：macOS 26+ / Apple Silicon 唯一引擎為 Apple SpeechAnalyzer（本機、免 HF 模型、fail-closed，永不 fallback）；Windows/Linux 為 `MediaTek-Research/Breeze-ASR-26`（transformers 路徑）／`faster-whisper` Breeze-ASR-25（可依環境切換）。
- **語言模型**：本地 Ollama（預設 `gemma4:31b`）／LM Studio，或雲端 Gemini（`gemini-3.5-flash-lite`）。
- **輸出**：Markdown 與 Word（DOCX，相容 Office 2024 / M365），依會議類型另有列管資料等附件。
- **部署**：Docker（GPU／標準兩種 compose，程式碼 volume 掛載、零 rebuild）或原生服務（`uv run` / `start_service.sh`）。

詳細更新紀錄請參閱：[CHANGELOG.md](CHANGELOG.md)

## 🚀 快速開始

### 系統需求

#### macOS
- **OS**: **macOS 26.0+（Apple Silicon）**——ASR 唯一引擎是系統內建的 Apple SpeechAnalyzer；macOS < 26 或 Intel Mac 上服務可啟動，但轉錄必然失敗（fail-closed，Mac 已無 Whisper 備援引擎）
- **RAM**: 16GB+ (本地模式需要)
- **Storage**: 20GB（本地 LLM 模型 + 資料；ASR 走系統內建模型，不需下載 Whisper 模型）
- **GPU**: Apple 神經引擎（ASR，macOS 26+ 需另建 helper）／Metal（本地 LLM 由 LM Studio、Ollama 使用）

> 🍎 **macOS 26+ / Apple Silicon 的 ASR：Apple SpeechAnalyzer（唯一引擎）**
> Mac 上 `ASR_BACKEND=auto`（預設值）與 `ASR_BACKEND=apple` 都只使用 macOS 內建
> SpeechAnalyzer 做本機轉錄（單一引擎、**永不 fallback**），不需下載 Hugging Face 模型；
> 本機實測（macOS 26 / Apple Silicon / 真實 helper）1658.958 秒
> （約 27.7 分鐘）MP3 的 ASR 轉錄 9.9 秒（`elapsed_seconds=9.9`、`real_time_factor=0.006`、
> `helper_invocations=1`，見 `.agent/tasks/T20260912-2242-01-apple-speech-analyzer-asr/e2e/attempt-03/`）；
> 未於本 repo 量測與 MLX-Whisper 的倍率。
> 任何 Apple 失敗（helper 缺失／不可執行、取消、逾時、輸出無效）都直接使任務失敗
> （fail-closed）；Mac 沒有 Whisper 依賴、本機 Whisper 模型或備援引擎，
> 顯式 legacy 值（`transformers`／`faster_whisper`／`mlx_whisper`）一律拒絕。
> 需求：**macOS 26+、Apple Silicon、`ffmpeg`（含 `ffprobe`）**，以及本機建置的
> Swift helper（`cd apple_speech_cli && swift build -c release`，需 Xcode 工具鏈；
> 安裝腳本**不會**自動編譯或下載模型）；`uv sync` 在 Mac 也不會安裝任何 Whisper／MLX
> 套件（`mlx-whisper` 的 macOS 平台相依已於 T20260912-2242-01 移除，`uv.lock` 同步收斂）。
> 回退舊 Whisper 行為須回退版本（Mac 已無 `ASR_BACKEND` 環境變數回滾開關）。
> **範圍界線**：本契約只涵蓋後端網頁服務（`backend/`）；根目錄的舊版 CLI
> （`main.py`／`src/whisper_transcriber.py`）是獨立的舊工具，仍使用 faster-whisper，
> 不在「Mac 僅 Apple SpeechAnalyzer」的適用範圍內。
> 完整操作、診斷與錯誤碼請見 [Apple SpeechAnalyzer 操作手冊](doc/apple-speech-analyzer-operations.md)。
> Windows / Linux / Docker 完全不受影響，也不會出現任何 Apple 設定。

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

> 🍎 **macOS 26+ / Apple Silicon 建議先建置 ASR helper**（一次性）：
> ```bash
> cd apple_speech_cli && swift build -c release
> cd .. && uv run python install_deps.py --check   # 檢視平台提示（僅 Mac 會出現 helper 提示）
> ```
> helper 未建置或 macOS < 26 時，Apple 轉錄直接失敗（fail-closed，Mac 不 fallback）；
> 引擎行為、診斷與錯誤碼請見 [操作手冊](doc/apple-speech-analyzer-operations.md)。

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
  "version": "4.7.1",
  "build_revision": "2e446ed9a6c54823c5d3a77da1b59d726adfe677",
  "gpu_available": true,
  "gpu_name": "NVIDIA GeForce RTX 4090",
  "ollama_available": true,
  "lmstudio_available": false,
  "gemini_available": true,
  "queue_status": { "queue_length": 0, "processing": 0 }
}
```

`build_revision` 為 nullable 的 runtime provenance 欄位（additive 向後相容）：
來源為環境變數 `MEETINGSCRIBE_BUILD_REVISION`（local/E2E launcher 注入
`git rev-parse HEAD`）；未設定時為 `null`，**不影響一般啟動與健康檢查**。
它用於區分 stale/current 服務——同一端口上兩個不同 commit 的 process
可藉此辨識；revision mismatch 只由 E2E harness（見下方 owned-process
E2E runner）視為驗收失敗，一般啟動不因 unknown revision 失敗。

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

### Owned-process E2E runner（驗證 / 驗收用）

`scripts/e2e/run_owned_e2e.py` 以「擁有 backend child process」的方式執行
隔離 E2E：自動選 free port、建立隔離 `DATA_DIR`、注入
`MEETINGSCRIBE_BUILD_REVISION=$(git rev-parse HEAD)`，並以
`/api/health` 的 `build_revision` 作為 freshness gate（只終止自己啟動的
process；artifacts 保存到 append-only attempt 目錄，已存在即拒絕覆寫）。

```bash
# 最小煙霧驗證：啟動 → health gate → LM Studio model snapshot → 乾淨終止（不上傳）
uv run python scripts/e2e/run_owned_e2e.py --smoke

# 完整 true E2E（昂貴；僅在獨立驗收階段執行）
uv run python scripts/e2e/run_owned_e2e.py --audio /path/to/meeting.m4a \
    --artifacts-dir .agent/tasks/<task>/evidence/stage05/attempt-01

# 只印執行計畫（選定 port、隔離目錄、expected revision），不啟動
uv run python scripts/e2e/run_owned_e2e.py --smoke --dry-run
```

artifacts 內容：`backend.log`（child 完整 log，含實際監聽端口與 build
revision）、`health_snapshot.json`、`model_snapshot.json`（LM Studio
loaded model/instance/context 唯讀快照）、`run_summary.json`（verdict
PASS/FAIL 與各項檢查）；完整 E2E 另含 `transcript.txt`、
`meeting_record.docx`、`upload_response.json`、`task_final.json`。

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
| `MEETINGSCRIBE_BUILD_REVISION` | - | 執行期 build revision（`/api/health` 的 `build_revision` 來源）；local/E2E launcher 注入 `git rev-parse HEAD`，未設定時 health 回傳 `null`，不影響一般啟動 |
| `MEETINGSCRIBE_PORT`（或 `SERVICE_PORT`） | `9527` | API 服務監聽端口；啟動 log 與 uvicorn `--port` 應使用同一來源（`scripts/macos/*.sh` 以此變數傳入） |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | 雲端 LLM 模型 |
| `ASR_BACKEND` | `auto` | ASR 後端（`auto`/`transformers`/`faster_whisper`/`mlx_whisper`/`apple`）。macOS 26+ Apple Silicon 只提供 Apple SpeechAnalyzer：`auto`＝`apple`、`apple`＝`apple`（皆單一引擎、永不 fallback），顯式 legacy 值（`transformers`/`faster_whisper`/`mlx_whisper`）一律拒絕；Windows/Linux 的 `auto` 維持既有解析，且永遠不會解析到 `apple` |
| `WHISPER_MODEL` | `MediaTek-Research/Breeze-ASR-26` | Whisper / ASR 模型名稱 |
| `APPLE_SPEECH_CLI_PATH` | - | （僅 macOS 生效）apple-speech-cli 執行檔路徑；空值＝依序搜尋 repo release 產物→PATH（不自動建置） |
| `APPLE_LOCALE`／`APPLE_PRESET`／`APPLE_ENABLE_PREFLIGHT` | `zh-Hant-TW`／`time-indexed`／`true` | （僅 macOS 生效）Apple SpeechAnalyzer locale、preset（可選 `time-indexed`／`plain`／`plain-alternatives`／`progressive`／`time-indexed-progressive`）、MP3 預轉 16k mono WAV 開關 |
| `ENABLE_TRANSCRIPT_CORRECTION` | `true` | 是否啟用語意校正（詞彙表＋LLM＋同音閘門） |

## 📊 性能指標（參考值，依模型與硬體而異）

### 轉錄速度
- **Apple SpeechAnalyzer（macOS 26+，唯一引擎）**: 本機實測（macOS 26 Apple Silicon、真實 helper）1658.958 秒（約 27.7 分鐘）MP3 的 ASR 轉錄 9.9 秒（`elapsed_seconds=9.9`）、`real_time_factor=0.006`、`helper_invocations=1`（`.agent/tasks/T20260912-2242-01-apple-speech-analyzer-asr/e2e/attempt-03/`；依硬體與 Asset 狀態而異；未於本 repo 量測與 MLX-Whisper 的倍率）
- **Apple MPS（歷史值）**: 1 分鐘音頻 ≈ 6-10 秒——此為舊 MLX-Whisper 路徑的實測值；macOS 已無 MLX/Whisper 引擎（唯一引擎為 Apple SpeechAnalyzer），僅供舊版 CLI 與歷史比較參考
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

#### Q: Mac 上沒有走 Apple 本機引擎（轉錄比預期慢）
- 檢查 `/api/health`：`device_info.accelerator` 應為 `apple-neural`、`device_info.asr_backend` 應為 `apple`（`/health?quick=true` 不 spawn helper、不做 probe，`available: false` 代表未驗證；`effective_asr_backend` 在 `/api/config`）
- 執行 `uv run python install_deps.py --check` 或 `uv run python scripts/verify_env.py`，看 helper 與 Swift 工具鏈提示
- 建置 helper（一次性）：`cd apple_speech_cli && swift build -c release`
- 常見原因與處理：macOS < 26（升級系統）、Intel Mac（不支援 Apple 引擎，darwin+arm64 限定）、helper 找不到（建置或設 `APPLE_SPEECH_CLI_PATH`）、Asset 未安裝（首次 `transcribe` 需網路下載）——任何 Apple 失敗皆 fail-closed、Mac 不 fallback，詳見 [操作手冊](doc/apple-speech-analyzer-operations.md)
- 回退舊行為：Mac 已無 `ASR_BACKEND=mlx_whisper` 回滾開關（顯式 legacy 值一律拒絕），須回退版本；Windows/Linux 無需任何設定

#### Q: 記憶體不足
- 改用較小的本地 LLM 模型
- 關閉其他應用程式
- 檢查 Ollama / LM Studio 模型是否過大

### 日誌檔案
```bash
# 應用日誌（每日輪轉，檔名帶日期）
cat "data/logs/app_$(date +%F).log"

# Docker 容器日誌
docker logs -f meetingscribe-app
```

## 📚 文件

- [系統架構與程式設計書](doc/規格與設計/系統架構與程式設計書.md) — 完整系統設計、模板系統、語意校正機制
- [使用者手冊](doc/操作手冊/使用者手冊.md) — 非技術使用者操作說明
- [部署更新手冊](doc/操作手冊/部署更新手冊_v4.1.md) — 正式環境部署與更新步驟
- [uv 管理說明](doc/操作手冊/uv管理說明.md) — 環境管理與依賴同步
- [Apple SpeechAnalyzer 操作手冊](doc/apple-speech-analyzer-operations.md) — Mac 本機 ASR 引擎確認、helper 建置與錯誤碼對照（Mac 無回滾路徑）
- [Apple Speech CLI 建置與驗證手冊](doc/apple-speech-cli-build.md) — Swift helper 的建置實測與契約細節
- [CHANGELOG](CHANGELOG.md) — 完整逐版變更紀錄

## 🏗️ 技術棧

### 後端
- **框架**: FastAPI + Uvicorn
- **轉錄**: macOS 26+ 唯一引擎 Apple SpeechAnalyzer（本機、fail-closed、永不 fallback）；Windows/Linux 維持 faster-whisper / transformers / MLX-Whisper（Breeze-ASR-25/26）
- **LLM**: Ollama / LM Studio（本地） + Gemini API（雲端）
- **資料**: 檔案系統（任務、逐字稿、輸出、詞彙表）

### 前端
- **框架**: HTML5 + CSS3 + Vanilla JavaScript
- **功能**: 拖放上傳、會議類型選單（依 `/api/config` 動態渲染）、實時進度、結果下載

### 環境支援
- **Python**: 3.11+（`uv` 管理）
- **OS**: macOS 12+、Windows 10/11、Ubuntu 20.04+
- **GPU/加速器**: Apple Neural Engine（macOS 26+ 預設 ASR）、NVIDIA CUDA、CPU；Apple MPS 僅存在於舊版 CLI／歷史路徑（後端 Mac 已無 MLX/MPS 引擎）
- **Office 相容性**: Office 2024, M365 (DOCX 輸出)

## 📝 版本歷史

### [v4.7.2] - 2026-08-20
- ✅ 修復**地端公文段落編號階層**不符標準（應為「一、」→「（一）」→「1、」→「（1）」）；
  根因是共用提示詞未明講階層與不可跳層規則，補上後地端與雲端產出一致（雲端原本即正常）

### [v4.7.1] - 2026-08-20
- ✅ 修復 v4.7.0 迴歸：`done_reason=length`（輸出撞 `num_predict` 上限，內容
  完整只是被截斷，確定性結果）不再誤判為可重試錯誤導致整份紀錄失敗
- ✅ num_predict 依 context 餘裕自動擴大，從源頭降低撞牆機率（整併呼叫例外，保收斂）
- ✅ 已在正式機（gemma4:31b／RTX 4090）以真實長會議錄音完整驗證通過

### [v4.7.0] - 2026-08-19
- ✅ 地端 VRAM offload 根治：Ollama 呼叫全面串流化、ASR 改獨立子程序執行
  （確保 VRAM 完整歸還）、模型預熱自我修復＋失敗時任務級降級 context
- ✅ 新增主機診斷／優化啟動腳本（`scripts/diagnose_ollama_host.ps1`、
  `scripts/start_ollama_optimized.ps1`）

### [v4.6.2] - 2026-08-19
- ✅ 地端排程任務「空白會議紀錄」診斷可見性根治：修復例外訊息為空導致
  失敗原因遺失、補模型預熱與 offload 偵測、瞬時錯誤重試

### [v4.6.0] - 2026-07-28
- ✅ 新增「ISMS 月工作會議」模板：表單式 DOCX 官方版面，程式確定性抽欄位渲染

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

Last updated: 2026-09-13
