# 跨平台（macOS／Windows）獨立查核報告 — T20260922-2037-02 P2 可查核性波

- 查核角色：獨立查核員（read-only 對產品碼）。
- 查核日期：2026-09-22（Asia/Taipei）。
- 受查快照：`HEAD = 3fec08f`（branch `fix/qwen-local-model-quality-parity`）；工作樹含本波未提交變更。
  - `backend/core/platform_config.py` sha256 `145ef922…`（未修改）、`backend/services/summarization.py` sha256 `76d2fc7d…`（未修改）、
    `backend/core/text_postprocess.py` sha256 `2ce4d90e…`（本波修改中）、`docker/docker-compose.yml` sha256 `ee3bd5a9…`、
    `docker/docker-compose-windows-gpu.yml` sha256 `67a9fe4e…`、`tests/test_t20260922_record_quality.py` sha256 `f5af38c9…`。
- 方法與界線：只讀產品碼／設定／文件／既有 E2E 證據；**未修改任何產品碼**；**未呼叫任何模型**；**未執行 E2E**。
  唯一執行過的動態驗證＝使用者指定的 pytest 指令（已排除 `tests/test_end_to_end.py`）。本目錄僅新增本檔。
- 需求錨點：使用者新增硬需求「確保系統可同時支援 macOS 與 Windows」（記於 `plan.md:215-242` §7 N-2；該節自認 Windows 實機未驗 `[UNVERIFIED]`）。

## ① 一句總結

**程式碼層面為真：本波修復（出處標註吸附）位於兩平台共用的引擎無關管線，沒有 OS 分支會讓 macOS（LM Studio）或 Windows（Ollama）其中一邊繞過它；但 Windows 端從未在本專案的任何實機／E2E 中跑過，且「非 Darwin → Ollama」的引擎選擇邏輯沒有任何單元測試釘住——因此目前的正確說法是「設計上支援、程式碼層證據齊備、Windows 未實證」，而非「已驗證支援」。**

- 設計上支援（程式碼＋文件可證）：平台判定與引擎選擇（Mac＝LM Studio、Win11／Ollama＝Ollama-first）、本波修復的共用可達性、兩份 compose 與 macOS 啟動鏈的存在。
- 未實證（無實機證據）：Windows 11＋RTX 4090＋Ollama 上吸附的實際效果、Windows compose 更換模型／主機的實務流程（需手改 compose，文件只寫在研究文件、未進操作手冊）、以及「non-Darwin → Ollama」選擇邏輯的測試覆蓋。

## ② 逐項查核

### 總表

| # | 項目 | 判定 | 關鍵證據（file:line） |
|---|---|---|---|
| 1 | 平台判定與 provider 三分支語意 | `[VERIFIED]`（程式碼層） | `backend/core/platform_config.py:23-28`、`:31-43`、`:46-55`、`backend/services/summarization.py:1937-1972` |
| 2 | 引擎實作差異（端點／參數／逾時／keep_alive） | `[VERIFIED]`；「OS 分支讓一邊走不到修復」＝`[FALSIFIED]`（查無此分支） | `summarization.py:298-305`、`:2325-2469`、`:2528-2548`、`:3010-3050`、`:3854-3970` |
| 3 | 本波修復的跨平台可達性 | `[VERIFIED]`（兩平台共用同一條路徑） | `summarization.py:2027`、`:2138`、`:2180`、`:2214-2287`；`backend/core/text_postprocess.py:811-899` |
| 4 | Windows 部署面（compose 差異、換模型／換主機） | 寫死事實與差異 `[VERIFIED]`；「有文件說明」＝`[VERIFIED 部分]`（研究文件有、操作手冊未記） | `docker-compose-windows-gpu.yml:86-87`、`docker-compose.yml:60-67`；研究文件 §10.4 `:815-817`；部署更新手冊 `:433-447` |
| 5 | macOS 本機部署面 | `[VERIFIED]` | `README.md:74-87`、`:97-99`；`start_service.sh:1-13`；`scripts/macos/start-mac-native.sh:25-27`、`:35-48`；`.env.example:42-49` |
| 6 | 測試面：平台 skip、本機測試結果、非 Darwin→Ollama 覆蓋 | 結果 `[VERIFIED]`；平台 skip `[VERIFIED]`；「非 Darwin→Ollama 選擇邏輯有測試」＝`[FALSIFIED]`＝**覆蓋缺口** | `886 passed / 2 skipped`；`tests/test_apple_cli.py:40-42`；`tests/test_lmstudio_provider.py:130-142` 等 |
| 7 | 已知不對稱／風險清單 | 見 §③（含未實證與可能誤導點） | 如表 |

### 1. 平台判定（`backend/core/platform_config.py`）

- 判定函式：`is_darwin_arm64()`＝`platform.system()=="darwin"` 且 `platform.machine()` 為 `arm64/aarch64`（`:23-28`）；`get_platform()` 回 `macos/windows/linux`（`:111-125`）。
- 平台預設：Darwin＋arm64 → `asr_backend=apple`、`local_llm_provider=lmstudio`；其餘（Windows／Linux／Intel Mac）→ `auto/auto/None`（`:31-43`）。
- `LOCAL_LLM_PROVIDER` 三分支語意（`resolve_local_llm_provider`，`:46-55`；`_select_local_engine`，`summarization.py:1937-1972`）：
  - `auto`：Darwin＋arm64 固定解析為 `lmstudio`（且 `check_ollama_health` 在 provider==lmstudio 時直接短路、不探測 Ollama，`summarization.py:3452-3454`）；**非 Darwin 的 auto 原樣回 `"auto"`**，在 `_select_local_engine` 先探 Ollama（健康且模型存在→`ollama`，`:1960-1962`）；Ollama 不可達→改用 LM Studio（`:1966-1972`）；Ollama 可達但設定的模型不存在→帶模型錯誤訊息 `RuntimeError`、不靜默 fallback（`:1963-1964`）。
  - `lmstudio`：一律 LM Studio 選模（需恰好一個已載入 LLM，或有唯一匹配的 override；`:1890-1935`），永不探測 Ollama（`:3452-3454`）。
  - `ollama`：必須 Ollama 健康（含模型存在或可自動解析變體），否則 `RuntimeError`（`:1950-1956`）。
  - 顯式值在兩平台都保留原意（`:53-55`）：Mac 可強制 `ollama`、Windows 可強制 `lmstudio`。
- LM Studio 預設端點：Darwin 原生＝`http://127.0.0.1:1234`；其餘（含 Docker）＝`http://host.docker.internal:1234`（`:88-92`）；Ollama 預設端點＝`http://host.docker.internal:11434`（`backend/core/config.py:49-52`）。
- 小結：**macOS（Apple Silicon）走 LM Studio、Windows 的 auto 走 Ollama-first**——與專案設計一致。`[VERIFIED]`
  - 附帶事實：在 Mac 原生環境顯式用 `ollama` 時，預設 URL 是 `host.docker.internal`（需自行改 `OLLAMA_BASE_URL`）；Windows 原生（非 Docker）用 LM Studio 同理——但這兩者都不是文件建議路徑。

### 2. 引擎實作差異（`_select_local_engine`／`_generate_with_local_engine`）

`_generate_with_local_engine`（`summarization.py:1974-2017`）只做分派：`ollama` → `_summarize_with_ollama`（`:1993-2002`）、`lmstudio` → `_summarize_with_lmstudio`（`:2004-2015`）。

| 面向 | Ollama 路徑 | LM Studio 路徑 |
|---|---|---|
| 客戶端／端點 | `httpx`，base_url=`settings.OLLAMA_BASE_URL`，`POST /api/chat`（`:298-305`、`:2350`）；原生 API | `AsyncOpenAI`，root 正規化後加 `/v1`（OpenAI 相容 chat.completions）（`:354-366`；`platform_config.py:95-108`） |
| 串流 | `stream:True`＋逐行解析（`:2350-2385`） | 非串流單次 create（`:3041-3050`） |
| 取樣參數 | `temperature/top_p=0.95/top_k=64/repeat_penalty=1.08/num_ctx/num_predict/stop`（`:2539-2548`）；`think=False` 且 400 時降級重送（`:2425`、`:2430-2435`） | `temperature/max_tokens`；`extra_body`（reasoning 關閉與相容降級，`:3039`、`:3056-3070`） |
| keep_alive | 有：`LOCAL_LLM_KEEP_ALIVE`（預設 `30m`；`:2538`、`config.py:274-277`）；warmup 以 `/api/generate` 預載（`:3797-3805`）；任務前 `keep_alive:0` 卸載供 ASR 用 VRAM（`:3954-3957`） | **無此概念**：模型由 LM Studio 端管理，本 app 只選「已載入」instance、不 JIT load（`:2677-2682`） |
| 逾時 | 串流：connect 10s／read＝`LOCAL_LLM_STREAM_IDLE_TIMEOUT`（120s）／總時長＝`LOCAL_LLM_REQUEST_TIMEOUT`（1800s）（`:2340-2349`） | OpenAI client `timeout=LOCAL_LLM_REQUEST_TIMEOUT`、`max_retries=0`（`:358-366`） |
| 重試 | 瞬時錯誤重試 `LOCAL_LLM_TRANSIENT_RETRIES`（預設 2，`:2411-2469`） | 同參數、網路層重試（`:3023-3086`） |
| warmup／卸載 | 僅 Ollama（`:3871-3872`、`:3949-3950`） | 無（no-op） |

- **有無 OS 專屬分支讓其中一邊走不到本波修復（吸附）？→ `[FALSIFIED]`（查無此種分支）**。OS 只影響「選哪個引擎」；選完引擎後兩條路都彙入同一條 `_summarize_with_local_pipeline`（`:2027`）與同一條地端後處理（`:2138`、`:2180`）。引擎層不對稱參數（`allow_reasoning_retry` 僅 LM Studio、`expand_output_budget` 僅 Ollama）都只作用於「生成」，不繞過後處理（`:1989-1991`、`:2686-2687`）。

### 3. 本波修復的跨平台可達性

- `_finalize_record_text(mode="local")`（`:2214-2287`）固定鏈序：`finalize_record` → 術語修正 → **標註吸附 `snap_source_tags_to_transcript`**（`:2269`）→ 表格標註清除 → 佔位符修復 → 跨節去重；`mode!="local"` 時提前返回、雲端 byte 級不變（`:2255-2256`）。
- 呼叫端僅 `_summarize_with_local_pipeline`（`:2138` 最終生成、`:2180` 每一輪補強），而該 pipeline 對 `ollama`／`lmstudio` 完全相同；產品唯一地端入口是 `summarize()`（`:442-445`）→ 由 `task_processor.py:333-339` 呼叫。
- `snap_source_tags_to_transcript`（`text_postprocess.py:811-899`）只依賴逐字稿段落列（`TRANSCRIPT_SEGMENT_PATTERN`，`:752-754`；`iter_transcript_segments`，`:786-803`）。`text_postprocess.py` **完全沒有** `platform`／`sys`／`os.name` 相關 import 或分支。
- `summarization.py` 亦無 `platform`／`sys.platform`／`os.name` 判斷（唯一相關 import 是 `platform_config.resolve_local_llm_provider`，`:36`，只用於選引擎 `:1940`）。
- 逐字稿段落列格式由共用層產生：`speaker_transcript.build_speaker_labeled_transcript`（`backend/services/speaker_transcript.py:316-329`，輸出 `[HH:MM:SS-HH:MM:SS] 發言者N：…`），由 `task_processor._label_speakers`（`backend/services/task_processor.py:165-233`）在**任何 ASR 後端**之後呼叫；diarization 失敗時 fail-soft 退回純文字（吸附全 no-op，`:172-176`、`:190-197`、`:203-204`）。
- 判定：`[VERIFIED]`——兩平台共用同一條路徑、無 OS 判斷繞過；吸附在「無段落列」時安全失效（不會產生假標註，但也不作用）。

### 4. Windows 部署面

`docker/docker-compose-windows-gpu.yml` vs `docker/docker-compose.yml` 差異（皆已逐行核對）：

| 面向 | windows-gpu | 標準版 |
|---|---|---|
| 專案／映像 | `name: meetingscribe-win-gpu`、`docker/Dockerfile.gpu`、`meetingscribe:windows-gpu-cuda12`（`:33`、`:40-43`） | `name: meetingscribe`、`docker/Dockerfile`、`meetingscribe:latest`（`:15`、`:22-25`） |
| GPU | `deploy.resources…devices: nvidia` 啟用（`:56-70`） | 同區塊**整段註解**（`:39-50`） |
| 寫死環境變數 | `OLLAMA_BASE_URL=http://host.docker.internal:11434`、`LOCAL_LLM_MODEL=gemma4:31b`（`:86-87`）；`ASR_BACKEND=faster_whisper`＋`WHISPER_MODEL=SoybeanMilk/faster-whisper-Breeze-ASR-25`（`:98-99`）；`LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS=16384`（`:118`） | `OLLAMA_BASE_URL`／`LOCAL_LLM_MODEL=gemma4:31b`（`:60-61`）；`LMSTUDIO_BASE_URL=…:1234/v1`／`LMSTUDIO_MODEL=gpt-oss-20b`（`:66-67`）；`ASR_BACKEND=transformers`＋`Breeze-ASR-26`＋revision（`:86-88`）；**未設** context 覆蓋（走程式預設 8192） |
| 校正預設 | `CORRECTION_SCOPE:-auto`（`:109`） | `CORRECTION_SCOPE:-all`（`:96`） |
| volume | 多掛 `../VERSION:/app/VERSION:ro`（`:173`）；backend/frontend 可寫（`:171-172`） | 無 VERSION；backend/frontend（`:136-138`） |
| env_file | 只讀 `../.env`（`:49-50`） | `../.env`＋`../.env.local`（`:31-33`） |
| healthcheck | `start_period: 600s`（`:198`） | `120s`（`:160`） |
| context 相同點 | 兩者 build context 皆 `..`、`extra_hosts: host.docker.internal:host-gateway`（`:41`/`:23`、`:176-177`/`:141-142`）、同網路 172.30.0.0/16 |

- **更換模型／主機需否手改？→ 需要，且 `.env` 改不動。** `environment` 優先權高於 `env_file`，`:86-87` 兩鍵寫死；要換模型（例如 `gemma4:26b`）或指向區網 Ollama 主機，必須改 `docker-compose-windows-gpu.yml`（或先把這兩鍵移出 `environment`）。標準版 `:73-75` 的註解即記錄了同型教訓（GEMINI_MODEL 寫死無效）。
- 文件說明：**研究文件有**（`doc/規格與設計/地端會議紀錄品質對齊雲端-研究與優化規劃.md:815-817` 明列此寫死與「改 compose」；`:818-822` 另列 diarization、context 不對稱等硬前提）。**操作手冊沒有**：`doc/操作手冊/部署更新手冊_v4.1.md:433-447` 只談 `env_file 凍結陷阱` 與 GEMINI_MODEL，未提這兩鍵；`README.md:63-72`、`doc/操作手冊/使用者手冊.md:120-129` 亦未提。→ 「有文件」屬 `[VERIFIED 部分]`；對非技術使用者的操作文件＝缺口。
- 另：預設版 compose 寫死 `LMSTUDIO_MODEL=gpt-oss-20b`（`:67`）是 Windows 非主要路徑（auto→Ollama-first）才會踩到的選模 override；若該模型未載入，會直接報 `LMSTUDIO_MODEL_NOT_LOADED`（`summarization.py:1921-1925`）。

### 5. macOS 本機（非 Docker）部署面

- 啟動：`uv sync --frozen` → `./start_service.sh`（`README.md:74-81`；`:76` 明示需 `uv` 與 `ffmpeg`）；`start_service.sh:8-11` 非 Darwin 直接拒絕，實際邏輯在 `scripts/macos/start-mac-native.sh`。
- 啟動器要求：`uv`、`.venv/bin/python`、`ffmpeg` 缺一即拒啟（`start-mac-native.sh:35-48`）；`DATA_DIR` 預設 `$PROJECT_ROOT/data` 並做可寫探針（`:27`、`:59-72`）；`MEETINGSCRIBE_HOST/PORT` 預設 `0.0.0.0:9527`（`:25-26`）。
- 必要環境變數：本機 LLM 走 LM Studio 時**無必填環境變數**（Darwin 原生預設 `http://127.0.0.1:1234`，`platform_config.py:88-92`）；雲端模式需 `GEMINI_API_KEY`（`.env.example:14`）；ASR 需一次性建置 `apple_speech_cli`（`README.md:83-87`），其餘 Apple 參數皆有預設（`.env.example:66-75`）。
- `.env.example:42-43` 說明 provider 語意、`:48` 給 LM Studio base URL 範例；`README.md:97-99` 分列 Windows（Ollama、`ollama pull gemma4:31b`）與 macOS（LM Studio）的本地模式配置。判定 `[VERIFIED]`。

### 6. 測試面

- 執行結果（本機 macOS，指令照抄使用者指定）：
  `DATA_DIR="$PWD/data" uv run --no-sync pytest tests/ -q --ignore=tests/test_end_to_end.py -p no:randomly`
  → **`886 passed, 2 skipped in 11.01s`**（重跑加 `-rs` 同為 886／2，`10.11s`）。`[VERIFIED]`
  - 2 個 skip 原因＝測試音檔缺檔（`tests/test_whisper_fix.py:38` 的 `tests/test_audio/test1_5sec.wav`、`test2_3sec.wav`），**與平台無關**。
- 平台相關 skip／xfail：
  - 唯一平台條件 skip＝`tests/test_apple_cli.py:40-42` 的 `POSIX_ONLY`（`os.name != "posix"` → 非 POSIX 環境跳過），掛在 12 個測試（`:178,197,220,243,477,490,506,517,658,679,697,708`）→ **在 Windows 會少跑這 12 項 Apple helper 測試**。
  - `tests/test_macos_scripts.py:1-35` 直接以 `bash -n` 驗 macOS 腳本、**無 skip 保護**；在沒有 bash 的 Windows 環境可能無法執行（套件不是「Windows 可整包跑」的設計）。
  - Windows 情境的模擬測試已存在但都在 ASR／環境層：`tests/test_whisper_transcriber.py:269-289`、`tests/test_verify_env.py:68-144`、`tests/test_install_deps.py:10-27`、`tests/test_health_apple_helper.py:267`、`tests/test_apple_dispatcher.py:63-67`（三平台矩陣，但對象是 ASR backend 不是 LLM provider）。
- **「非 Darwin → Ollama」選擇邏輯的覆蓋：沒有 → `[FALSIFIED]`（覆蓋缺口）**。證據：
  - 直接呼叫 `_select_local_engine` 的測試只有 1 個：`tests/test_lmstudio_provider.py:130-142`（`test_mac_auto_does_not_probe_ollama`），且它 **mock `resolve_local_llm_provider` 回傳 `"lmstudio"`**——測的是 Mac 分支。
  - 其餘全部把 `_select_local_engine` 整個 monkeypatch 掉（`tests/test_summarization_service.py:353` 用 `"ollama"`、`tests/test_t20260922_record_quality.py:313,370,586` 與 `tests/test_t20260922_regression.py:346` 用 `"lmstudio"`）——等於**假設**引擎名稱、沒有驗證平台如何選出它。
  - 沒有任何測試 monkeypatch `platform.system/machine`（或 `is_darwin_arm64`）成 Windows／非 Darwin 後，斷言 `resolve_local_llm_provider("auto")=="auto"` 或 `_select_local_engine()` 回 `"ollama"`。
  - 本波 P2 的吸附契約測試（`tests/test_t20260922_record_quality.py:630-732` 等）是純函式／假引擎測試，**不含平台條件**、理論上任何 OS 都能跑；但「在 Windows 上實際跑過」`[UNVERIFIED]`。

### 本波既有 E2E 證據的跨平台歸屬（背景事實）

- `.agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/` 僅有 `attempt-A1-27b`、`attempt-B1-moe-fix`、`attempt-B2-27b-fix` 三次，全部是 **macOS ＋ LM Studio ＋ Qwen**（B2 `run_notes.md` 開頭即載明 LM Studio 已載入 27B、`context_length=128000`，verdict PASS）。
- 沒有任何 Windows／Ollama 的 attempt。計畫亦自認「本機無 Windows 實機、Windows 實機行為未驗 `[UNVERIFIED]`」（`plan.md:230-242`）。
- 治理狀態（供銜接）：`plan.md` 現為 `PLAN_REVISION 6`（已納入 N-2 雙平台驗收條目，`:215-242`）；最新獨立審查 `review/attempt-04/review.md:114` 對 rev 5 判 `PLAN_REVISION_REQUIRED`（F-C／F-D），rev 6 聲稱已收斂，**attempt-05 尚未出現**。

## ③ 風險與建議

### 風險清單（兩平台行為不一致或 Windows 未驗證）

| # | 風險 | 影響（會不會讓人誤以為已支援） | 等級 |
|---|---|---|---|
| R1 | Windows 實機 E2E 從未執行（Ollama＋Gemma 路徑的吸附效果、diarization 就緒度、段落列格式皆未在實機驗證） | **會**。README 標榜跨平台，但「支援」目前只有程式碼層證據 | 高（認知風險） |
| R2 | `docker-compose-windows-gpu.yml:86-87` 寫死 `OLLAMA_BASE_URL`／`LOCAL_LLM_MODEL`，`.env` 無效；操作手冊未記載 | **會**。使用者照 `.env.local.example:48-49`（未註解）或 `.env.example:44-45`（範例）改 `.env` 以為換了模型／主機，實際仍跑 `gemma4:31b`／本機 Ollama（或直接報錯） | 高 |
| R3 | context 預算不對稱：Windows GPU compose 16384、標準 compose 走預設 8192、LM Studio 走 instance context（E2E 128000） | 部分會。同一份修復在 Windows 可能因切塊／整併行為不同而指標較差，使用者可能誤判「修復沒用」 | 中 |
| R4 | ASR 後端不同（GPU compose＝faster_whisper＋Breeze-ASR-25；標準＝transformers＋Breeze-ASR-26）；diarization 模型未就緒時段落列不存在、吸附全 no-op 且**系統不會主動告警** | **會**。看起來「有出處標註」但其實標註是模型原稿（可回溯率低），只有離線量測才看得出（研究文件 `:810-814` 已記載此特性） | 中 |
| R5 | 「非 Darwin→Ollama」與「顯式值保留」無單元測試；`_select_local_engine` 的 Ollama 分支也無直接測試 | 會（回歸風險）。日後改動可能悄悄讓 Windows 走錯引擎或提早 fallback，CI 不會擋 | 中 |
| R6 | 測試套件非 Windows-可整包執行（12 個 POSIX-only Apple 測試＋`test_macos_scripts.py` 依賴 bash） | 部分。在 Windows 上宣稱「全套測試通過」不成立，需另立 Windows 範圍標準 | 中 |
| R7 | 預設版 compose 寫死 `LMSTUDIO_MODEL=gpt-oss-20b`（Windows 若走 LM Studio fallback 會踩到） | 低-中。多載入模型情境會直接報錯而非任意選 | 低 |
| R8 | Gemma 4 31B（Windows 主目標模型）尚未完成 E2E（plan N-1 進行中） | 部分。「模型無關」目前由程式碼結構＋單元契約支撐，尚未有跨模型家族實測 | 中 |

### 建議（具體可執行）

1. **補一個「Windows 路徑」單元測試（強烈建議，成本低）**——新增 `tests/test_platform_provider_routing.py`，以 monkeypatch `backend.core.platform_config.platform.system/machine`（或直接 patch `is_darwin_arm64` → False；現行做法見 `tests/test_apple_dispatcher.py:63-67`）模擬非 Darwin，斷言：
   - `resolve_local_llm_provider("auto") == "auto"`（不得提早變 `"lmstudio"`）；且 `"lmstudio"`／`"ollama"` 顯式值在任何平台都原樣保留（純函式可直測，不需模擬 OS）。
   - `_select_local_engine()` 在 `check_ollama_health()` 回 True → 回 `"ollama"`，且 `_resolve_lmstudio_selection` **未被呼叫**。
   - Ollama 服務可達但模型缺失（`_ollama_model_error` 已設）→ 拋 `RuntimeError`（含模型訊息），**不得**靜默 fallback 到 LM Studio。
   - Ollama 不可達（health False 且無 model error）→ fallback 回 `"lmstudio"`（LM Studio 選模被呼叫一次）。
   - 對照組（既有行為）：darwin＋arm64 的 `auto` → `"lmstudio"` 且 `check_ollama_health` 未被呼叫。
   這四條斷言把「Windows 端引擎選擇」從假設變成契約，未來 CI 即可在 macOS 上守門（不需 Windows 實機）。
2. **把 P2 吸附契約測試參數化跑雙引擎**：在 `tests/test_t20260922_record_quality.py` 既有的 `_summarize_with_local_pipeline` 契約測試（如 `:288`、`:336`、`:557`）加 `@pytest.mark.parametrize("engine", ["lmstudio", "ollama"])`，對 `_select_local_engine` 的 mock 傳入該值，斷言兩條引擎名稱下最終輸出都經過吸附（時間戳＝段落起點）。用一行參數證明「引擎無關」，比註解更有力。
3. **補 Windows 部署文件的「換模型／換主機」一節**：在 `doc/操作手冊/部署更新手冊_v4.1.md` 附錄補明「`docker-compose-windows-gpu.yml:86-87` 兩鍵為 compose 寫死、`.env` 無效；換模型／換區網主機請改這兩行後 `up -d`」。更好的做法是把這兩鍵改為 `${OLLAMA_BASE_URL:-http://host.docker.internal:11434}`／`${LOCAL_LLM_MODEL:-gemma4:31b}` 形式（比照 `:73-75` 的 GEMINI_MODEL 教訓），讓 `.env` 恢復效力，並順手消除 R2。
4. **Windows 驗收定義（在無實機前）**：把「Windows 支援」對外表述為「程式碼層共用、未實機驗證」，並列兩條可關閉條件：①上述單元測試落地；②RTX 4090 機器可用時跑同音檔 `section_meeting`＋`local`＋`measure_record_quality.py`，以 `on_start_tag_ratio ≥ 0.95`、`traceable_tag_ratio ≥ 0.95`、`table_source_tag_count = 0` 為閘門（比照 B2）。
5. **（選配）段落列缺失時的可觀測性**：吸附 no-op 目前只反映在離線量測。可考慮在 `_finalize_record_text` 的統計日誌中，當 `mode="local"`、模板支援標註、但 `stats["segments"]==0` 時加一條 WARNING（不影響輸出、只提高可發現性）——避免 R4 的「靜默無效」。

## ④ 給非技術使用者的白話結論

1. 這個系統「設計上」確實同時支援 Mac 和 Windows：Mac 用 LM Studio、辦公室的 Windows 11 加 RTX 4090 用 Ollama，選擇邏輯在程式裡是分開而完整的。
2. 這次修好的「會議紀錄時間出處變準」機制，是放在兩邊共用的同一條處理流程裡，程式碼上不會只有 Mac 生效、Windows 不生效。
3. 但截至目前，所有實際的品質驗證（含最新一次完整測試）都只在 Mac 上跑過；Windows 那台機器還沒有人真正用它跑完一份會議紀錄，所以還不能說「已經實測支援 Windows」。
4. 另外要提醒：Windows 的部署設定檔把「用哪個 Ollama 模型」和「Ollama 主機位置」寫死了，改 `.env` 檔案不會生效——要換模型或換主機，必須請工程師改 `docker/docker-compose-windows-gpu.yml`，而這件事目前只寫在研究文件、還沒寫進給使用者的操作手冊。
5. 建議在正式宣稱「完整支援兩平台」前，先補一個用程式模擬 Windows 的測試（成本低），並在 Windows 機器實際跑一次同一份會議音檔做交叉比對。
