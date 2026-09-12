# Handoff — Apple SpeechAnalyzer ASR（僅 Mac、預設）

## PROMPT_FOR_IMPLEMENTER

> （本節為 Owner 要求的實作指示前言，優先於 Stage 03 固定節格式；其餘各節仍嚴格遵守 handoff 契約。）

你是一名接手實作的編碼 Agent。你的唯一任務是依據本目錄 `plan.md`（PLAN_REVISION 1，SHA-256 見下 `PLAN_SHA256`）為 `convert` 專案新增 **Apple SpeechAnalyzer 本機 ASR**，並設為 **Mac 預設**、**絕對不得進入 Windows**。請按以下方式工作：

1. 先完整讀完 `plan.md`（特別是 GOAL_CONTRACT、REQUIREMENTS_AND_CRITICALITY、SEMANTIC_CONTRACT、DECISIONS、IMPLEMENTATION_WAVES、TEST_AND_ACCEPTANCE），再讀 `doc/apple-speech-analyzer-porting-context.md`（移植來源上下文，§4 地雷為禁區、§5 為搬運清單），以及 `yt_down_txt` 原始檔（commit `ce7abe6`＋`2de061d`，以其 `apple_speech_cli/` 與 `media_toolbox/asr/` 為移植母本）。
2. 嚴格按 IMPLEMENTATION_WAVES 順序實作：WAVE-01（路由＋契約骨架，無 Swift 可測）→ WAVE-02（Swift helper 移植，需 Mac＋Xcode＋macOS 26 SDK；若環境缺失記 env-blocker 繼續，不硬擋）→ WAVE-03（Python provider，效能命脈）→ WAVE-04（全鏈接線）→ WAVE-05（矩陣驗收＋文件）。禁止跳波、禁止先打磨 UI 文案（R5 PRIORITY_INVERSION）。
3. 不可變更的語意紅線（見 SEMANTIC_INVARIANTS）：Mac `auto`→`apple`；非 Mac `auto` 永不含 `apple` 且顯式 `apple` 明確拒絕；顯式 `apple` fail-closed；`APPLE_CANCELLED` 永不 fallback；stdout 單 JSON 契約；`import contract` 零重型依賴；Windows 零 Apple 依賴/建置/UI。任何一條若需鬆動，立即 STOP_AND_ESCALATE，不可自行重新設計。
4. 常數必須照抄（見 CURRENT_STATE_DELTA 與 plan DEC-05/06/07/08）：超時公式、轉檔參數、暫存命名正則、離場碼表、CJK 正規化正則、metadata 十一鍵。不要發明新規格。
5. 每完成一波，執行其指定的驗證命令並記錄證據；全部完成後按 ACCEPTANCE_CONTRACT 逐項 CHECK-01～CHECK-14 回報 pass/fail/blocked（含 failure 分類與 waiver）。產出 durable `execution.md`（Stage 04 要求）記錄每波變更檔、驗證輸出與殘留風險。
6. 本任務 Owner 已 waive 獨立事前審查，但你對語意變更沒有豁免權；完工標準以 plan DEFINITION_OF_DONE 為準。

## TASK

- TASK_ID: T20260912-2242-01-apple-speech-analyzer-asr
- STATUS: READY_FOR_IMPLEMENTATION
- PLAN_PATH: .agent/tasks/T20260912-2242-01-apple-speech-analyzer-asr/plan.md
- PLAN_REVISION: 1
- PLAN_SHA256: 20d8e4518d9c20252f645849204bedb5740fc4a88f003ae942715915eb9efd03
- REVIEW_REQUIRED: NO（Owner 2026-09-12 明示 waive 獨立審查；技術上改 gating 語意本應審查，故語意紅線改動仍須 escalate）
- REVIEW_REPORT: NONE
- REVIEWED_PLAN_REVISION: N/A
- REVIEWED_PLAN_SHA256: N/A
- INDEPENDENT_ACCEPTANCE_REQUIRED: NO（Owner waive；仍需 Mac/Win 雙機驗收證據）
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: E2E
- Fresh Implementer required: YES
- Planner/Reviewer transcript required: NO

## GOAL_ANCHOR

Mac（macOS 26+、Apple Silicon）新上傳預設走 Apple SpeechAnalyzer 本機轉錄（快約 4.9 倍、免 HF 模型）；Windows（含 Docker/WSL）完全不受影響、不可見、不可選。成功證據：Mac `auto` 任務 `effective_asr_backend=apple` 且 health/日誌可觀察；Windows `auto` 永不解析到 `apple`、顯式 `apple` 明確拒絕；≥27min MP3 在 Mac 以 `helper_invocations=1` 端到端成功。絕不破壞：三舊後端行為/快取/進度條、fail-closed 與取消不 fallback 語意、無半寫檔/殘留暫存、不提交 binary、不污染 Apple 路徑。

## CRITICAL_PATH

先把「誰能上誰不能上」變成可單測純函式（WAVE-01：`resolve_engine_chain`＋平台守衛）→ Swift helper 建置並讓 `probe`/`transcribe` 契約成立（WAVE-02，最大不確定性最早消除）→ Python provider 打通＋長 MP3 單次呼叫（WAVE-03：probe→ffprobe→預轉→helper→validate→normalize）→ 全鏈接線（WAVE-04：設定/快取/health/前端/隔離子程序）→ 平台矩陣驗收（WAVE-05）。

## SEMANTIC_INVARIANTS

- SI-01 平台閘門：僅 `platform.system()==darwin 且 machine∈{arm64,aarch64}` 的 `auto` 可解析到 `apple`；未知平台視為非 Mac；非 Mac `auto` 鏈組成與現狀完全一致（REQ-01/02，DEC-01/10）。
- SI-02 顯式 fail-closed：`requested==apple` → chain 嚴格等於 `(apple,)`，任何 Apple 錯誤（含 `APPLE_OUTPUT_INVALID`）直接向上拋，不試下一個引擎（REQ-03）。
- SI-03 取消優先：`APPLE_CANCELLED`（helper 離場碼 7）在 `auto` 下亦不 fallback；取消優先於逾時（REQ-03）。
- SI-04 stdout 契約：helper stdout 有且僅有一份 schema 1.0 JSON，stderr 全是診斷；任何 stdout 污染 → `APPLE_OUTPUT_INVALID`（可參與 auto fallback，顯式 apple 下照常拋出）（REQ-04/07）。
- SI-05 錯誤碼表凍結：0 成功；2 `APPLE_UNAVAILABLE`；3 `LOCALE_UNSUPPORTED`；4 `ASSET_ERROR`；5 `INPUT_ERROR`；6 `TRANSCRIPTION_ERROR`；7 `CANCELLED`；1 通用（含 `APPLE_TIMEOUT`/`APPLE_OUTPUT_INVALID` 子型別）。絕不自動釋放其他 locale 的保留額度（REQ-04）。
- SI-06 超時公式凍結：`resolved_timeout = max(600.0, duration*3.0+300.0)`；`ffprobe` 失敗用 600 下限且絕不因此失敗（REQ-05）。
- SI-07 轉檔契約凍結：`CONVERSION_ARGS=(-vn -c:a pcm_s16le -ar 16000 -ac 1)`、`SUFFIX=.wav`；`NATIVE={.m4a,.mp4,.wav,.aif,.aiff,.caf,.mp3}`；`PREFLIGHT={.mp3}`（MP3 一律先轉）；非原生一律轉（REQ-06）。
- SI-08 暫存契約：命名 `.<stem>.<12hex>.apple.(wav|m4a)`，正常結束 `finally` 刪除；sweep 僅匹配 `^\..+\.[0-9a-f]{12}\.apple\.(?:wav|m4a)$`、僅單層一般檔、不跟隨連結、不遞迴、>24h 才刪（REQ-09）。
- SI-09 Apple 不吃 Whisper 參數：Apple 嘗試一律 `use_vad=False` 語意的新請求，不改傳入 frozen 物件；VAD/beam/hotwords 參數不套用於 Apple（SEMANTIC_CONTRACT）。
- SI-10 簽名契約：`transcribe_detailed(audio_path, progress_callback)` 簽名不變；`_obtain_transcript` 快取優先不變；快取簽名已含 backend，換引擎自動換 key，無遷移（SEMANTIC_CONTRACT）。
- SI-11 import 純潔：`import contract` 不得拉入 `mlx_whisper/torch/silero/faster_whisper`；Apple 模組頂層無重型依賴，非 Mac 最早分支返回、零副作用（NFR-03）。
- SI-12 Windows 零 Apple：Windows 依賴/安裝腳本/建置步驟/UI 字串/文件預設值不得引入 Apple；helper binary 永不提交（REQ-11）。

## BEST_EFFORT_DO_NOT_GATE

- BE-01 CJK 空白正規化（`normalize_apple_text`，REQ-08）：失敗只影響美觀，必須獨立函式、不得改 `text_postprocess.clean_transcript` 本體。
- BE-02 暫存 sweep 與 NFR-02（terminate→5s→kill）：盡力清理，失敗記 warn 不得使轉錄結果失效。
- BE-03 metadata 完整度與 health `apple_helper` 區（REQ-10/11）：欄位缺失不得阻擋轉錄成功路徑。
- BE-04 前端顯示（REQ-12）與 RTF 基準記錄（NFR-01）：NON_GATING／對比用，不設硬門檻。
- 以上任一失敗必須保持局部，不得升級為全域 veto，不得阻擋 CORE closure。

## DEFERRED_NOT_THIS_TASK

- OOS-01 diarization（說話人區分另起模組，勿塞進 ASR provider）。
- OOS-02 `contextualStrings` 熱詞（SpeechTranscriber 下 no-op）、繁中辭典校正（覆蓋極低）、通用錯字表（有害）。
- OOS-03 Linux/Windows 版 Apple、雲端 ASR fallback。
- OOS-04 三舊後端解碼調優、LLM 摘要模板改動。
- DEFERRED：helper 自動編譯/自動下載模型、串流式進度、`zh-Hant-TW` 之外的 locale 調優。

## REPO_ANCHOR

- Project root: /Users/hsiaojohnny/dev/convert
- Branch: main
- Anchor HEAD: 6da1e56（`docs(e2e): 保存 attempt-01 驗收報告與 redacted evidence`）
- Relevant dirty state: `?? doc/apple-speech-analyzer-porting-context.md`（本任務 canonical spec，建議與本任務同批提交）；`?? .agent/tasks/T20260912-2242-01-apple-speech-analyzer-asr/`（本任務 plan＋handoff，本次提交範圍）。
- Drift since plan/review: 無（plan 與 handoff 同一批落檔；另有無關的 `?? .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/e2e/attempt-02/`，不得納入本任務提交或實作範圍）。

## CURRENT_STATE_DELTA

- 相对 Anchor HEAD 的實作接縫（均已讀檔驗證，行號為落檔時實測）：
  - `backend/services/transcription.py`（652 行）：`TranscriptionService.transcribe_detailed` 唯一入口；`_detect_runtime`/`_load_model` 決定 backend；三分支 `transformers/mlx_whisper/faster_whisper`；`get_device_info` 回 `backend/accelerator/model/revision`。
  - `backend/core/asr_model_resolver.py`：`infer_asr_backend(model, pref)`（Mac auto→`mlx_whisper`，約第 60–80 行）；`resolve_asr_model`（Mac auto＋Breeze 官方→MLX 版）；`build_asr_cache_signature`（已含 backend/revision/language/prompt/beam/vad）。
  - `backend/core/platform_config.py`：`SUPPORTED_ASR_BACKENDS=frozenset({"auto","transformers","faster_whisper","mlx_whisper"})`；`is_darwin_arm64()`；`get_platform_defaults()`（Mac→`mlx_whisper/lmstudio/mlx-metal`）；`resolve_platform_asr_backend()`（Mac auto→`mlx_whisper`）。
  - `backend/core/config.py`（428 行）：`Settings.ASR_BACKEND="auto"`、`WHISPER_MODEL="MediaTek-Research/Breeze-ASR-26"`、`WHISPER_LANGUAGE="auto"`、VAD/beam/chunk 系列；後端只讀 env/`.env`，`config.yaml` 對後端無效。
  - `backend/services/asr_subprocess.py`（222 行）＋`backend/workers/asr_worker.py`（76 行）：v4.7.0 隔離子程序；stdout 純 JSON lines 進度；`ASR_WORKER_TIMEOUT_SECONDS` 病態輸入直接失敗不重試。
  - `backend/services/task_processor.py`：`_obtain_transcript`（快取→`transcribe_isolated_detailed`→`save_transcript_cache`）；`_apply_semantic_correction`（`clean_transcript`＋LLM 校正）。
  - `backend/services/file_manager.py:137-177`：`get_asr_cache_signature` 已按 backend 分 key。
  - `backend/api/routes.py:441-460`：health 回 `asr_backend/effective_asr_backend/whisper_model/effective_whisper_model/revision`。
  - `frontend/js/app.js`：accelerator 顯示（`mlx-metal`/CUDA/CPU）；無引擎選擇器。
  - `pyproject.toml`：`mlx-whisper==0.4.3 ; platform_system=="Darwin" and platform_machine=="arm64"`（Apple 新增依賴必須仿此加 platform marker——實際上 Apple 零 Python 依賴，此為參照 pattern）；`requires-python>=3.11`（DEC-09：不收緊）。
  - 移植母本：`yt_down_txt@ce7abe6+2de061d` 的 `apple_speech_cli/`（7 個 Swift 檔＋Package）與 `media_toolbox/asr/`（`contract/dispatcher/apple/apple_cli/pipeline/transcript_utils`）；本 repo 無，需向來源 repo 取。
- 關鍵常數（照抄，勿改）：
  - 離場碼：0/2/3/4/5/6/7/1（見 SI-05）；`SIGTERM/SIGINT`→協作取消→5s 寬限→強制結束→`APPLE_CANCELLED`。
  - `TIMEOUT_FLOOR_SECONDS=600.0`；`resolved_timeout=max(600.0, duration*3.0+300.0)`。
  - `CONVERSION_SUFFIX=".wav"`；`CONVERSION_ARGS=("-vn","-c:a","pcm_s16le","-ar","16000","-ac","1")`；`NATIVE_INPUT_SUFFIXES={.m4a,.mp4,.wav,.aif,.aiff,.caf,.mp3}`；`PREFLIGHT_CONVERSION_SUFFIXES={.mp3}`。
  - `STALE_TEMP_NAME_PATTERN=re.compile(r"^\..+\.[0-9a-f]{12}\.apple\.(?:wav|m4a)$")`。
  - stdout 擷取上限 `8_000_000` 字符；`terminate→5s grace→kill`，返回前回收子行程；stdout/stderr 獨立執行緒排空。
  - CJK 類 `"\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"`；三步：空白Run→單空格、CJK間空白刪除、CJK標點前後空白刪除、strip。例：`今天天氣很好 ，我們一起去公園散步`→`今天天氣很好，我們一起去公園散步`。
  - 路由凍結形：`requested==apple→(apple,)`；`auto→Mac (apple,mlx_whisper)`、非 Mac 現狀不變；`contract: EngineName=Literal["auto","apple","breeze","mlx"]` 僅為來源參考，本專案無台語需求，簡化為 `("apple","mlx_whisper")` 家族（DEC-02）。
  - metadata 十一鍵：`requested_engine/resolved_engine/engine_chain/locale/audio_duration_seconds/elapsed_seconds/real_time_factor/helper_invocations/conversion_reason/conversion_seconds/segment_count/segments_dropped/segments_time_degraded`（只放純量）。
  - Swift：`platforms:[.macOS(.v14)]` 弱連結 Speech；辨識順序 `localeReport→AssetInstallFlow.ensureReady→AVAudioFile→analyzer`；預設 preset `time-indexed`；只收 `isFinal==true`（volatile 只計數）；`attributedPieces` 優先 `TimeRangeAttribute` 切 run；`AnalysisContext.contextualStrings` 是 no-op（勿用）。
  - 新 Settings（WAVE-04）：`APPLE_SPEECH_CLI_PATH/APPLE_LOCALE（預設 zh-Hant-TW）/APPLE_PRESET（預設 time-indexed）/APPLE_ENABLE_PREFLIGHT`；health 顯示 `accelerator` 建議字串 `apple-neural`。

## MUST_READ_PLAN

- 首次動手前必讀：GOAL_CONTRACT、REQUIREMENTS_AND_CRITICALITY（REQ-01～12/NFR-01～03/OOS-01～04）、DECISION_CONTRIBUTION_MATRIX、SEMANTIC_CONTRACT、DECISIONS（DEC-01～12）、COUPLING_AND_FAILURE_CONTAINMENT、COMPLEXITY_BUDGET、IMPLEMENTATION_WAVES（WAVE-01～05）、TEST_AND_ACCEPTANCE（CHECK-01～14）、RISKS（R1～R5）、DEAD_ENDS（D1～D5）、DEFINITION_OF_DONE。

## SETTLED_DO_NOT_REOPEN

- DEC-01 Mac auto→apple（Owner 指令，不討論）。
- DEC-02 預設鏈 `(apple, mlx_whisper)`，不追加 transformers/faster（最小 fallback）。
- DEC-03 獨立 Swift helper＋subprocess，不做 pyobjc/in-process（D1）。
- DEC-06 MP3 一律預轉、不賭原生重試（D4）；WAV 16k mono（實測最速）。
- DEC-08 CJK 正規化獨立函式、不動共用 normalizer。
- DEC-09 不收緊 `requires-python`，Apple 做執行期 `>=3.12` 檢查（D5）。
- DEC-12 不做 diarization/熱詞/辭典/錯字表/自動編譯/提交 binary（D2/D3＋OOS）。
- R5 波序約束：WAVE-02 通之前不打磨 UI 文案。

## REVERIFY_ON_START

- `git -C /Users/hsiaojohnny/dev/convert status --short` 與 `rev-parse --short HEAD` 是否仍為 6da1e56、有無他人動過 `backend/services/transcription.py`、`asr_model_resolver.py`、`platform_config.py`、`config.py`。
- 實作機 `platform.system/machine`、`python --version`、`ffmpeg -version`、`ffprobe -version`、`swift --version`、macOS 版本（`sw_vers`）是否滿足 macOS 26+／Apple Silicon／Python 3.12／Xcode 工具鏈。
- 來源母本 `yt_down_txt@ce7abe6+2de061d` 是否可取到 `apple_speech_cli/` 與 `media_toolbox/asr/`。
- `uv run pytest tests/ -q -k "dispatcher or transcription or platform"` 基線是否綠（記錄基線，供 CHECK-14 BASELINE_DELTA 用）。

## TRIGGERED_POLICIES

- goal-alignment-design-economy.md（01a 要求常載；對應本 handoff 的刪除測試/耦合測試/複雜度預算）。
- workflow-routing.md §7（v4.2 verification/status：CHECK 欄位、failure 三分類、waiver、env-blocker 路由）。

## FIRST_ACTION

- 執行 WAVE-01：不碰 Swift，先在 `backend/core/platform_config.py`＋`backend/core/asr_model_resolver.py`＋新建 `backend/services/asr_apple/contract.py` 落 `SUPPORTED＋apple`／Mac auto→apple／非 Mac 守衛／`resolve_engine_chain`，並寫 `tests/test_apple_dispatcher.py` 覆蓋三平台 mock 矩陣，跑 `uv run pytest tests/test_apple_dispatcher.py -q` 全綠後再動 WAVE-02。

## IMPLEMENTATION_WAVES

- WAVE-01 平台路由與契約骨架｜CORE｜無 Swift 可測｜REQ-01/02/03＋NFR-03。
- WAVE-02 Swift helper 移植與建置契約｜CORE｜最大不確定性最早消除｜REQ-04（缺 Mac/SDK 記 env-blocker，不擋他波）。
- WAVE-03 Python Apple provider｜CORE｜效能命脈｜REQ-05/06/07/08/09。
- WAVE-04 全鏈接線（設定/快取/health/前端/隔離子程序）｜SUPPORTING（ decided 行為的產品化）｜REQ-10/11/12。
- WAVE-05 平台矩陣與文件收尾｜SUPPORTING｜全 REQ 回歸＋DoD。
- （細節、檔案、符號、驗證、退出、回滾一律以 plan.md IMPLEMENTATION_WAVES 為準，本 handoff 不複製。）

## ACCEPTANCE_CONTRACT

- CHECK-01 Mac auto 預設解析｜`uv run pytest tests/test_apple_dispatcher.py -q`（mock darwin-arm64，chain=(apple,mlx_whisper)）｜CORE｜closure-gating｜CLOSURE_GATE=YES｜BASELINE_RULE=基線變更（現 Mac auto→mlx_whisper，本變更有意改變，需更新快照）｜FAILURE_ROUTING=task regression→IMPLEMENTATION_BLOCKED｜WAIVER_ALLOWED=NO｜WAIVER_AUTHORITY=NONE。
- CHECK-02 Windows 排除｜同套件（mock Win/Linux：auto 不含 apple；`resolve_platform_asr_backend("apple")` 拋錯含「僅 macOS」）｜CORE｜closure-gating｜CLOSURE_GATE=YES｜BASELINE_RULE=Win 行為零變更｜FAILURE_ROUTING=task regression→BLOCKED｜WAIVER_ALLOWED=NO｜WAIVER_AUTHORITY=NONE。
- CHECK-03 顯式 fail-closed｜fake helper 回碼 4/6/1：requested=apple 直拋、auto fallback｜CORE｜closure-gating｜CLOSURE_GATE=YES｜BASELINE_RULE=N/A（新行為）｜FAILURE_ROUTING=task regression→BLOCKED｜WAIVER_ALLOWED=NO｜WAIVER_AUTHORITY=NONE。
- CHECK-04 取消不 fallback｜fake helper 回碼 7：auto 亦直拋 `APPLE_CANCELLED`｜CORE｜closure-gating｜CLOSURE_GATE=YES｜BASELINE_RULE=N/A｜FAILURE_ROUTING=task regression→BLOCKED｜WAIVER_ALLOWED=NO｜WAIVER_AUTHORITY=NONE。
- CHECK-05 契約純潔｜`import contract` 後無 torch/mlx_whisper/silero/faster_whisper；Win import 無副作用｜CORE｜closure-gating｜CLOSURE_GATE=YES｜BASELINE_RULE=N/A｜FAILURE_ROUTING=task regression→BLOCKED｜WAIVER_ALLOWED=NO｜WAIVER_AUTHORITY=NONE。
- CHECK-06 超時公式｜`resolved_timeout(0/600/3600)=(600/2100/11100)`；ffprobe 失敗→600｜SUPPORTING｜regression-guard｜CLOSURE_GATE=NO｜BASELINE_RULE=N/A｜FAILURE_ROUTING=task regression 修復、pre-existing 記錄｜WAIVER_ALLOWED=YES｜WAIVER_AUTHORITY=OWNER。
- CHECK-07 長 MP3 單次呼叫｜Mac 實機 ≥27min MP3：`fragile_native_container`＋`helper_invocations=1`＋E2E 成功｜CORE｜E2E gating｜CLOSURE_GATE=YES｜BASELINE_RULE=記錄 RTF 對比 mlx｜FAILURE_ROUTING=task regression→BLOCKED；無 Mac 實機記 environment blocker（不 collapse 為 IMPLEMENTATION_BLOCKED）｜WAIVER_ALLOWED=NO｜WAIVER_AUTHORITY=NONE。
- CHECK-08 輸出驗證｜污染/缺欄位/`end<start`/空白段→`APPLE_OUTPUT_INVALID`＋計數正確｜CORE｜closure-gating｜CLOSURE_GATE=YES｜BASELINE_RULE=N/A｜FAILURE_ROUTING=task regression→BLOCKED｜WAIVER_ALLOWED=NO｜WAIVER_AUTHORITY=NONE。
- CHECK-09 CJK 空白｜範例句轉換正確｜SUPPORTING｜regression-guard｜CLOSURE_GATE=NO｜BASELINE_RULE=BASELINE_DELTA｜FAILURE_ROUTING=task regression｜WAIVER_ALLOWED=YES｜WAIVER_AUTHORITY=OWNER。
- CHECK-10 暫存衛生｜成功無殘留；sweep 語意正確｜SUPPORTING｜regression-guard｜CLOSURE_GATE=NO｜BASELINE_RULE=N/A｜FAILURE_ROUTING=task regression｜WAIVER_ALLOWED=YES｜WAIVER_AUTHORITY=OWNER。
- CHECK-11 健康可觀察｜Mac health 含 `apple_helper{available,path}`；Win 為 `supported:false` 且不 probe｜SUPPORTING｜acceptance-observable｜CLOSURE_GATE=NO｜BASELINE_RULE=N/A｜FAILURE_ROUTING=task regression｜WAIVER_ALLOWED=YES｜WAIVER_AUTHORITY=OWNER。
- CHECK-12 包裝守衛｜Win 依賴解析無 Apple；Win 不提示 Xcode；repo 無 tracked binary｜CORE｜closure-gating｜CLOSURE_GATE=YES｜BASELINE_RULE=N/A｜FAILURE_ROUTING=task regression→BLOCKED｜WAIVER_ALLOWED=NO｜WAIVER_AUTHORITY=NONE。
- CHECK-13 前端｜Mac 顯示 Apple；Win 產物無 Apple 字樣｜SUPPORTING｜acceptance-observable｜CLOSURE_GATE=NO（NON_GATING）｜BASELINE_RULE=N/A｜FAILURE_ROUTING=task regression｜WAIVER_ALLOWED=YES｜WAIVER_AUTHORITY=OWNER。
- CHECK-14 全量回歸｜`uv run pytest tests/ -q` 與基線差異僅允許 Mac auto 預設改變相關更新｜REPO-HEALTH｜CLOSURE_GATE=BASELINE_DELTA｜BASELINE_REQUIRED=YES（先建基線）｜FAILURE_ROUTING=task regression→BLOCKED；pre-existing→記錄＋OWNER waiver 可放行；environment blocker→記錄不擋｜WAIVER_ALLOWED=YES（僅 pre-existing）｜WAIVER_AUTHORITY=OWNER（代行 REVIEWER）。
- Stage04 要求：實作方須產出 durable `execution.md`（每波變更檔＋驗證輸出＋殘留風險）；Stage05 要求：验收證據須註明新鮮度（fresh）與 carry-forward 來源，不得用過期證據冒充。

## STOP_AND_ESCALATE_IF

- 任一 SI-01～SI-12 無法成立（例如：Windows 無法排除 apple、必須偷 fallback 才能通、stdout 契約做不到、contract 被迫引入重型依賴）。
- `yt_down_txt` 母本關鍵檔缺失或與移植上下文矛盾（以母本 `ce7abe6+2de061d` 為準，矛盾處停下問 Owner，不可自創規格）。
- 目標 Mac 實為 Intel 或 macOS<26 且 Owner 仍要求預設 apple（與 A1 衝突）。
- 需改變任何 validity/requiredness/gating/veto/穩定錯誤/fallback/權重/優先序語意（即使 diff 很小）。
- WAVE-02 出現 plan 未載明的系統性障礙（SDK API 缺失、簽名/沙箱擋 helper 執行）且無法以 DEC-05（v14 部署目標＋弱連結）收斂。
- 發現本 handoff 與 plan.md PLAN_REVISION 1／SHA-256 不一致（stale handoff，不可執行）。

## HISTORICAL_TASK_DEPENDENCIES

- NONE（本任務不依賴其他 TASK_ID；`doc/apple-speech-analyzer-porting-context.md` 為外部來源上下文，非本 repo 歷史任務產物）。
