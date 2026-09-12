# execution.md — T20260912-2242-01 apple-speech-analyzer-asr

> Stage 04 實作紀錄（Implementer 產物）。本檔所有數字均為實跑觀察值；未實跑者一律標「未驗證」。

## 0. 任務身分與前置核對

| 項目 | 值 | 證據 |
|---|---|---|
| TASK_ID | `T20260912-2242-01-apple-speech-analyzer-asr` | `plan.md` / `handoff.md` |
| PLAN_REVISION | 1 | `handoff.md:21` |
| PLAN_SHA256 | `20d8e4518d9c20252f645849204bedb5740fc4a88f003ae942715915eb9efd03` | `handoff.md:22`（實作前已重算比對一致） |
| REVIEW_REQUIRED | NO（Owner 2026-09-12 明示 waive） | `handoff.md:23` |
| INDEPENDENT_ACCEPTANCE_REQUIRED | NO（Owner waive；仍需 Mac/Win 雙機驗收證據） | `handoff.md:27` |
| E2E_REQUIRED | YES | `handoff.md:28` |
| HANDOFF | `handoff.md`（`STATUS: READY_FOR_IMPLEMENTATION`，含 `PROMPT_FOR_IMPLEMENTER`） | `handoff.md:7` |
| 基線 commit | `1bd54fb0c953dff75321a063216bb79686b33dd4` | `baseline/summary.md:5`、本回合 `git rev-parse HEAD` 同值 |
| 基線測試 | `550 passed, 3 skipped, 3 warnings` | `baseline/pytest-full.txt:27`、`baseline/summary.md:31` |

執行環境（實測）：macOS 26.6.2 (25G83)、arm64 / Apple M4 Pro、Xcode 26.6、Swift 6.3.3（`swift-driver 1.148.6`，target `arm64-apple-macosx26.0`）、ffmpeg 7.0 / ffprobe 7.1.1。Windows 實機不可得，Windows 面以模擬矩陣驗證（見 §6）。

## 1. 目標與關鍵路徑（GOAL_ANCHOR）

- **主要結果**：Mac（Apple Silicon / macOS 26+）上的**新上傳**預設改用 Apple SpeechAnalyzer 轉錄；Windows「完全不受影響、完全看不到 Apple」；`auto` 鏈為 `(apple, mlx_whisper)`；顯式 `apple` fail-closed 不 fallback；`APPLE_CANCELLED` 永不 fallback。
- **最小安全關鍵路徑**：契約骨架（§2 WAVE-01）→ Swift helper 移植與實機建置（WAVE-02）→ helper 呼叫層（WAVE-03a）→ 供應器與鏈整合（WAVE-03b）→ 觀測/前端/封裝（WAVE-04）→ 子程序 metadata 落地（WAVE-05a）。

## 2. 波次實作紀錄

### WAVE-01 路由＋契約骨架（CORE，先於一切 polish）

| 檔案 | 內容 |
|---|---|
| `backend/core/platform_config.py`（+20） | Apple 平台判定（Darwin + arm64，零子程序）與平台閘門 |
| `backend/core/asr_model_resolver.py`（+41） | `auto` 在各平台的鏈解析；非 Apple 平台永不含 `apple` |
| `backend/services/asr_apple/contract.py`（130 行） | 凍結契約：`SCHEMA_VERSION="1.0"`(:18)、`HELPER_ENGINE_NAME="apple"`(:21)、`APPLE_AUTO_FALLBACK=("apple","mlx_whisper")`(:37)、8 個穩定錯誤碼(:41-48)、離場碼→錯誤碼表(:66)、`normalize_engine_name()`(:78)、`ASRSegment`(:93)、`AppleSpeechError`(:105)、`is_cancelled_error()`(:127) |
| `backend/services/asr_apple/dispatcher.py`（52 行） | 引擎鏈派送與 fallback 決策（`should_fallback`） |
| `backend/core/config.py`（+22） | `ASR_BACKEND` 新值 `apple` 與 `APPLE_*` 設定（`config.py:357-372`） |
| `tests/test_apple_dispatcher.py`（240 行） | **17 passed**（本回合實跑） |

### WAVE-02 Swift helper 移植與實機建置

- `apple_speech_cli/`（SwiftPM 套件）自母專案 `yt_down_txt` **原始碼逐字移植，未改任何 Swift 檔**：`Package.swift`、`Sources/AppleSpeechKit/*.swift`（15 檔）、`Sources/apple-speech-cli/AppleSpeechCLI.swift`、`Tests/AppleSpeechKitTests/*.swift`（2 檔）。
- 實機建置：`swift build -c release` → `Build complete! (5.43s)`；產物 `apple_speech_cli/.build/release/apple-speech-cli`，**515,376 bytes**、`Mach-O 64-bit executable arm64`、`otool -L` 可見 `Speech.framework ... (weak)`；本回合重算 sha256 = `a0fd9c0265443def9fa14b5fccac00529001b2260418ab60965adb503bd2d3a4`。
- Swift 測試：`swift test` → **52 passed**。
- **binary 永不入版控**：`apple_speech_cli/.gitignore`（`.build/`、`.swiftpm/`、`Package.resolved`、`*.o`）＋根 `.gitignore:115-117`（`apple_speech_cli/.build/`、`apple_speech_cli/apple-speech-cli`）。
- 文件：`doc/apple-speech-cli-build.md`（209 行，建置／驗證手冊）。

### WAVE-03a helper 呼叫層

| 檔案 | 內容 |
|---|---|
| `backend/services/asr_apple/apple_cli.py`（1027 行） | 執行 helper、逾時、輸出驗證、進度解析、文字正規化。關鍵：`resolved_timeout_seconds()`(:134) `max(600, duration*3+300)`、`resolve_executable()`(:180) configured→repo release→PATH、`run_helper()`(:340)、`validate_transcription_payload()`(:666)、`build_transcribe_argv()`(:706)、`error_from_helper_result()`(:872)、`normalize_apple_text()`(:904)、`parse_progress_line()`(:1013) |
| `tests/test_apple_cli.py`（799 行） | **79 passed** |

### WAVE-03b 供應器＋鏈整合

| 檔案 | 內容 |
|---|---|
| `backend/services/asr_apple/apple.py`（693 行） | `apple_platform_supported()`(:108)、`preflight_conversion_reason()`(:127)（`.mp3`→`fragile_native_container`）、`sweep_stale_apple_temp_files()`(:137)（SI-08：精確 regex＋>24h、不跟隨連結）、`transcribe_with_apple()`(:479)、`apple_helper_status()`(:654) |
| `backend/services/transcription.py`（+187） | `_transcribe_with_apple_chain` 與 fallback 決策；`engine_chain` 於 `:701` 落地 |
| `tests/test_apple_provider.py`（752 行） | **34 passed** |
| `tests/test_apple_chain_integration.py`（450 行） | **12 passed** |

### WAVE-04a 健康觀測／裝置／任務文字／模型下載

| 檔案 | 內容 |
|---|---|
| `backend/api/routes.py`（+77） | `/health` 新增 `device_info.apple_helper{supported,available,path,probe,reason}`（`:63-121`）、`?quick=true` 不 spawn、不 probe（`routes.py:81-88`）；`effective_asr_backend` 全檔唯一出現於 `/api/config`（`:533`） |
| `backend/services/device_detector.py`（+36） | `apple-neural` 加速器語意 |
| `backend/services/task_processor.py`（+21） | 任務進度／狀態文字 |
| `scripts/download_models.py`（+22） | Mac 不再被要求下載 Whisper 模型 |
| `tests/test_health_apple_helper.py`（279 行） | **8 passed** |

### WAVE-04b 前端／安裝／環境檢查／文件

- `frontend/js/app.js`（+9）：Mac 顯示 Apple；Windows 產物無 Apple 字樣。
- `install_deps.py`（+105）`--check`、`scripts/verify_env.py`（+118）、`.env.example`（+12）、`config.macos.yaml`（+14）、`README.md`、`CHANGELOG.md`、`doc/apple-speech-analyzer-operations.md`（200 行）。
- 測試：`tests/test_install_deps.py`（+76）、`tests/test_verify_env.py`（+63）、`tests/test_frontend_upload_flow.py`（+88）→ 三檔 **19 passed**。
- 封裝守衛：`tests/test_apple_packaging_guard.py`（149 行）→ **4 passed**（repo 無 tracked binary、Windows 依賴無 Apple）。

### WAVE-05a 子程序 metadata 落地（觀測可追溯）

| 檔案 | 內容 |
|---|---|
| `backend/workers/asr_worker.py`（+16） | `_scalar_metadata()`(:23) 僅保留 JSON 純量；payload 增列 `metadata`(:80) |
| `backend/services/asr_subprocess.py`（+6） | `_payload_to_detailed` 還原 `metadata`(:108,:116)；父程序輸出單行 INFO `ASR 引擎觀測：{...}`(:188) |
| `tests/test_asr_subprocess.py`（+193） | 新增 7 測試（純量過濾／舊物件降級／還原與缺欄位／日誌恰一行） |

### WAVE-05b 真 helper 缺席的 E2E（缺席自然性）

- `tests/test_apple_helper_absent_e2e.py`（345 行）→ **4 passed**：真缺席自然構成證據（非 fake script）、顯式 `apple` fail-closed、`auto` → mlx fallback、離場碼 7 不 fallback。
- 變異敏感度自查：注入變異使 `should_fallback` 恆真／使顯式 apple 也回 2 段鏈 → 對應案例失敗，證明測試非空轉。

### WAVE-05c 文件稽核與補正

- 獨立稽核 `verification/docs-audit.md`（8 項指定稽核：PASS 5 / MISMATCH 4 / UNVERIFIABLE 1，另自尋 2 項）。
- 修正後複審（read-only）：M1–M5、G3、`4.9×`（稽核指定 3 處）皆 **CLOSED**；並以碼＋`rg --no-ignore` 全庫掃描複核（`/health` 欄位、`/api/config`、metadata 唯一落地處、`app_$(date +%F).log`）。
- 複審另指出 4 個非阻斷缺口（`/result` 不供逐字稿、metadata 落地處句內矛盾、建置手冊缺 `--preset` 行、porting-context 來源專案數字未標註），本回合已補正（見 §6.3）。

## 3. CHECK-01…14 驗收矩陣

| CHECK | REQ | GOAL_CRITICALITY | CLOSURE_GATE | 判定 | 證據 |
|---|---|---|---|---|---|
| CHECK-01 Mac auto 預設解析 | REQ-01 | CORE | YES | **PASS** | `tests/test_apple_dispatcher.py` 17 passed；Mac `auto` 鏈為 `(apple, mlx_whisper)`；基線快照已記錄「Mac auto 預設改變」 |
| CHECK-02 Windows 排除 | REQ-02 | CORE | YES | **PASS** | mock Windows/Linux ＋ `ValueError` 訊息斷言；`verification/windows-matrix-audit.md`（216 變體全拒、auto 全平台不含 apple） |
| CHECK-03 顯式 fail-closed | REQ-03 | CORE | YES | **PASS** | `test_apple_provider.py`／`test_apple_helper_absent_e2e.py`：顯式 apple 直接拋、`auto` 才 fallback |
| CHECK-04 取消不 fallback | REQ-03 | CORE | YES | **PASS** | 離場碼 7 → `APPLE_CANCELLED`，`auto` 亦直接拋（`test_apple_chain_integration.py`、`test_apple_helper_absent_e2e.py` 案例 4） |
| CHECK-05 契約純潔 | NFR-03 | CORE | YES | **PASS** | `import contract` 後 `sys.modules` 無 `torch/mlx_whisper/silero/faster_whisper`；Windows import apple provider 無副作用 |
| CHECK-06 超時公式 | REQ-05 | SUPPORTING（NON_GATING） | NO | **PASS** | `resolved_timeout_seconds(0/600/3600) = (600/2100/11100)`；ffprobe 失敗→600 |
| CHECK-07 長 MP3 單次呼叫（E2E） | REQ-06 | CORE | YES | **PASS** | §4 |
| CHECK-08 輸出驗證 | REQ-07 | CORE | YES | **PASS** | 污染 stdout／缺欄位／`end<start`／空白段 → `APPLE_OUTPUT_INVALID`＋計數正確；合法 payload 通過 |
| CHECK-09 CJK 空白 | REQ-08 | SUPPORTING（NON_GATING） | NO | **PASS** | `今天天氣很好 ，我們一起去公園散步`→`今天天氣很好，我們一起去公園散步` |
| CHECK-10 暫存衛生 | REQ-09 | SUPPORTING（NON_GATING） | NO | **PASS** | 成功無殘留；sweep 只刪精確正則＋>24h、不跟隨連結 |
| CHECK-11 健康可觀察 | REQ-10 | SUPPORTING（NON_GATING） | NO | **PASS** | Mac `/health` 含 `apple_helper.available=true`、`accelerator=apple-neural`；Windows `supported:false` 且不 probe |
| CHECK-12 包裝守衛 | REQ-11 | CORE | YES | **PASS** | `install_deps.py --check` Windows 0 Apple 字樣；`uv pip compile --python-platform windows/linux` 無 mlx/apple；無 tracked binary |
| CHECK-13 前端 | REQ-12 | SUPPORTING（NON_GATING） | NO | **PASS** | Mac 顯示 Apple；Windows payload/前端 chunk 掃 `apple|swift|xcode` 0 hits |
| CHECK-14 全量回歸 | MUST_NOT_BREAK | repo-health | BASELINE_DELTA | **PASS** | 基線 `550 passed/3 skipped` → 現行 **726 passed / 3 skipped / 0 failed**（+176，0 失敗；差額全為本任務新增測試） |

**waiver 使用情形**：本任務所有 `CLOSURE_GATE=YES` 的檢查皆實跑通過，**未動用任何 waiver**；NON_GATING 項（CHECK-06/09/10/11/13）亦全數通過。

## 4. 真機 E2E 證據（CHECK-07）

- harness：`e2e/run_apple_asr_e2e.py`（owned-child uvicorn、隔離 `DATA_DIR`）；報告：`e2e/attempt-03/report.json`（attempt-01/02 為 harness bug，append-only 保留）。
- **verdict `PASS`**（`report.json:71`）；11 項 core checks 全 `true`（`:4-16`）、`core_failed=[]`（`:17`）、`failures=[]`（`:18`）、8 項 supporting checks 全 `true`（`:60-69`）。

| 觀測 | 值 | 證據 |
|---|---|---|
| 音訊長度 | `1658.958` 秒（約 27.7 分鐘，`meeting-30min.mp3`） | `report.json:29` |
| 引擎 | `requested_engine=auto`、`resolved_engine=apple`、`engine_chain=apple,mlx_whisper` | `:33,37,38` |
| 耗時 | `elapsed_seconds=9.9`、`real_time_factor=0.006`、`conversion_seconds=0.599` | `:32,36,31` |
| helper 呼叫 | `helper_invocations=1`（單次） | `:34` |
| 轉檔原因 | `conversion_reason="fragile_native_container"` | `:30`（observed `:52` 同值） |
| 輸出 | `segment_count=572`、`segments_dropped=0`、`segments_time_degraded=0`、`transcript_chars=6811` | `:39,40,41,57` |
| 健康 | `accelerator="apple-neural"`、`apple_helper.available=true`（`supported=true`, `reason=null`） | `:50,22-27` |
| 無 fallback | `apple_fallback_log_lines=[]` | `:21` |
| 無殘留 | `apple_temp_residues=[]` | `:46` |
| 會議紀錄生成 | `summary_failed=true`、`task_status="completed"` | `:54,56`（本機 Ollama 0 模型，屬預期；ASR 段不受影響） |

**harness 透明度揭露**：此 harness 刻意「記錄」而非「以 clean worktree 為 gate」（docstring／provenance 已載明），因 Stage-04 期間工作樹必然為 dirty；此為 E2E 方法論偏離，已明文揭露而非隱藏。

## 5. 使用者要求的 Apple vs Whisper 實測比較（`tests/0903-科務會議.m4a`）

同一支 44.9 分鐘會議音檔（`duration_seconds=2695.061`、sha256 `b42f83d2…8ce6bb5e`，`comparison.json:63-65`），以產品服務層 `transcribe_detailed` 分別跑三種引擎：

| 引擎 | backend / model | 耗時 (s) | RTF | CJK 字數 | 標點/100 CJK | 8-gram 重複率 |
|---|---|---|---|---|---|---|
| Apple | `apple`（SpeechAnalyzer） | **15.43** | **0.0057** | 10001 | 1.38 | 0.00099 |
| Whisper turbo | `mlx_whisper` / `mlx-community/whisper-large-v3-turbo` | 145.58 | 0.054 | 9713 | **2.47** | 0.0034 |
| Whisper Breeze | `mlx_whisper` / `doggy8088/Breeze-ASR-26-MLX` | 441.98 | 0.164 | 10746 | **0.0** | **0.046** |

- 速度換算（音訊分鐘／耗時分鐘）：Apple `174.7×`、turbo `18.5×`、breeze `6.1×`（`comparison.md:9-13`）。
- 逐窗離群（20 窗）：`whisper_turbo 0/20`、`apple 9/20`、`whisper_breeze_mlx 11/20`（`quality-analysis.md:28-31`）。
- 迴圈證據：breeze 最長重複片段 `('我我我我我我我我我我我我', 101)`；turbo `('沒有沒有沒有沒有沒有沒有', 3)`；apple `[]`（`quality-analysis.md:1-4`）。
- Apple 已知弱點（**本回合實測**，`data/cache/apple-vs-whisper-0903/transcript-apple.txt`）：偏好變體／簡化字形——`麵` 43 次、`裏` 20 次、`錶` 5 次、`係統` 5 次、`註意` 3 次（其他兩引擎皆 0 次）。屬後處理／詞彙表可修，非結構性錯誤。
- **判定**：Apple 在速度（相對 turbo 快 9.4×、相對 breeze 快 28.6×）與穩定度（零迴圈、無爆走）上最佳；turbo 標點最完整但慢 9.4×；breeze 最差（開頭幻覺＋101 次迴圈＋零標點）。**無 ground truth 逐字稿**，故本判定為品質代理指標（標點率、8-gram 重複、人工抽看）之綜合結論，非字元錯誤率（CER/WER）實測。

## 6. 獨立稽核與缺陷處置

### 6.1 `verification/docs-audit.md`（文件對碼稽核）

8 項指定稽核：PASS 5、MISMATCH 4、UNVERIFIABLE 1；最嚴重為「觀測指示失效」（照文件 grep `data/logs/app.log` 將看不到 `helper_invocations`）。已全數修正，複審判定 CLOSED（§2 WAVE-05c）。

### 6.2 `verification/windows-matrix-audit.md`（Windows 零 Apple 對抗式驗證）

**PASS**：`docker/`、`pyproject.toml`、`requirements*.txt` 掃 `apple|swift|xcode` 零命中；`uv pip compile --python-platform windows/linux` 無 mlx/apple；215 個 tracked 檔皆非 binary；前端 54 個渲染 chunk 零命中；216 次（8 平台 × 9 變體 × 3 函式）顯式 apple 全數拒絕且訊息一致。

### 6.3 稽核後的 4 處文件補正（WAVE-05c 收斂）

1. `doc/apple-speech-analyzer-operations.md:150-152`（原誤把逐字稿算進 `/result`）：改為「API 沒有 JSON metadata 端點：`model_info`（`backend/models/schemas.py:67`）從未被賦值」＋「逐字稿＝`GET /api/tasks/<TASK_ID>/transcript`（`text/plain`）」＋「會議紀錄檔案下載＝`GET /api/tasks/<TASK_ID>/result`（僅 md/docx）」；權威碼 `routes.py:295`（transcript）／`routes.py:319`（result），改前已讀碼。
2. 同檔 `:147-148`（原句內矛盾）：改為「任務 metadata 落地處：當日 app 日誌的『ASR 引擎觀測』行（鍵名見 §2.3）；`structured_<日期>.jsonl` 亦會收到同一行訊息（同一筆 loguru INFO 記錄）」；權威碼 `logger.py:40-55`（app sink, DEBUG）與 `:72-80`（structured sink, INFO）。
3. `doc/apple-speech-cli-build.md:66`：補 `--preset <name>` 用法行（5 個合法值、預設 `time-indexed`）；權威碼 `CLIArgumentParser.swift:32,:116`、`backend/core/config.py:366-368`。
4. `doc/apple-speech-analyzer-porting-context.md:232`：原數字保留，句後加註「（此為來源專案 `yt_down_txt` 之實測數據，未於本 repo 複驗；本 repo 的實測數字見 e2e attempt-03）」。

## 7. 語意紅線 SI-01…SI-12

實作全程未變更任何紅線語意：`auto` 鏈與 fallback 邊界（SI-01/02）、取消不 fallback（SI-03）、契約 schema 與錯誤碼（SI-04/05）、逾時語意（SI-06）、Windows 零 Apple（SI-07）、暫存衛生（SI-08）、`ASR_BACKEND=mlx_whisper` 回滾路徑（SI-09）、`transcribe_isolated` tuple 介面（SI-10）、錯誤字串／類型穩定性（SI-11）、gating 行為（SI-12）皆未觸及 → **無需 `escalation.md`**。

## 8. 殘留風險與已知偏離（不阻斷）

1. **F1（Windows 字面偏離）**：`transcription.py:31/36` 頂層 import 使 `asr_apple.contract/.dispatcher` 隨健康路由一併載入（非「零載入」，但 provider 與 helper 全未觸及、純輕量模組）。要「零載入」需回 Stage 01。
2. **`?quick=true` 語意**只經 TestClient 驗證，未對 live server curl。
3. **`ASR_WORKER_TIMEOUT` 與 helper 逾時公式不一致**：音訊長度超過約 38 分鐘時，worker 層逾時可能先於 helper 的 `max(600, 3×duration+300)` 觸發。
4. **顯式 `apple` 前置載入不經 MLX**：顯式路徑不會預載 mlx 模型（設計如此，但與 `auto` 的記憶體行為不同）。
5. **fallback 結果 metadata 為空 dict**：`auto` 換手到 mlx 後不回填 `resolved_engine`（屬 REQ-10 觀測語意變更，需 Planner 決策；本回合僅記錄，未自行變更）。
6. **E2E 未涵蓋會議紀錄生成**：`summary_failed=true`（本機無 LLM 模型）；已以 `e2e/attempt-03` 限縮引用範圍，文件未宣稱整條 pipeline 端到端時間。
7. **pre-existing（非本任務造成，未修）**：(a) 預設 `WHISPER_MODEL=MediaTek-Research/Breeze-ASR-26` 在 `mlx_whisper 0.4.3` 下載入失敗（`ModelDimensions.__init__() got an unexpected keyword argument '_name_or_path'`），比較測試改用具 MLX 格式的 `doggy8088/Breeze-ASR-26-MLX`；(b) `tests/test_task_processor.py` 單獨收集需外部 `DATA_DIR`（預設 `/app` 唯讀）；(c) `README.md` 既有的 `data/logs/app.log` 無效路徑（已由 WAVE-05c 順帶修正）。
8. **Windows 無實機**：`sys.platform` 未改、以模擬替代；真機轉錄 E2E 未跑（以模擬矩陣＋實機 Mac E2E 補強）。

## 9. 狀態欄位（v4.2）

| 欄位 | 值 |
|---|---|
| PRIMARY_OUTCOME_STATUS | **ACHIEVED** — Mac 新上傳預設 Apple SpeechAnalyzer、真機 E2E PASS、Windows 零 Apple（對抗式驗證 PASS） |
| IMPLEMENTATION_STATUS | **COMPLETE** |
| CORE_ACCEPTANCE_STATUS | **PASS**（CHECK-01/02/03/04/05/07/08/12 全通過） |
| REQUIRED_VERIFICATION_STATUS | **COMPLETE**（E2E_REQUIRED=YES → `e2e/attempt-03` PASS；全量 726 passed / 0 failed） |
| INDEPENDENT_ACCEPTANCE_STATUS | **WAIVED**（Owner；另以 4 份獨立稽核/複審作為補充證據） |
| TASK_CLOSURE_STATUS | **COMPLETE**（Stage-04 產物齊備、驗證有實據、無隱藏阻斷） |
| NEXT_ACTION | Stage 05 若 Owner 要求可重跑獨立驗收；否則以 §8 殘留風險清單作為後續追蹤項 |

## 10. 證據索引

- 計畫／交接：`plan.md`、`handoff.md`、`baseline/{summary.md,pytest-full.txt,pytest-focused.txt}`
- E2E：`e2e/attempt-03/{report.json,report.md,task_final.json,health_snapshot.json,provenance.json}`、harness `e2e/run_apple_asr_e2e.py`
- 比較測試：`e2e/comparison-0903/{comparison.json,comparison.md,quality-analysis.md}`、腳本 `e2e/compare_apple_vs_whisper.py`
- 獨立稽核：`verification/docs-audit.md`、`verification/windows-matrix-audit.md`
- 文件：`doc/apple-speech-analyzer-operations.md`、`doc/apple-speech-cli-build.md`、`doc/apple-speech-analyzer-porting-context.md`、`README.md`、`CHANGELOG.md`

---

# 附錄 A — 語意變更回合（Owner 指示，2026-09-13，PLAN_REVISION 1 之 §附錄）

> 本附錄記錄 Owner 於 2026-09-13 明示的「Mac 僅提供 Apple SpeechAnalyzer」語意收斂。
> 依 harness §10，變更 fallback 邊界屬語意變更 → 已落 `escalation.md`（`OWNER_DIRECTED /
> RESOLVED`）。§0–§10 為前一回合之事實，**SI-02 的 auto 鏈已由本附錄取代**。

## A.1 新語意（取代 SI-02）

| requested | is_apple_platform | 前一回合（§7 SI-02） | **本回合新語意** |
|---|---|---|---|
| `auto` | True | `("apple","mlx_whisper")` | **`("apple",)`** 單一引擎、永不 fallback |
| `apple` | True | `("apple",)` fail-closed | `("apple",)` fail-closed（不變） |
| `transformers`/`faster_whisper`/`mlx_whisper` | True | 原樣尊重（單點） | **`ValueError` 硬性拒絕** |
| `auto` / 其他顯式值 | False | 單點解析／原樣 | **完全不變**（逐值驗證，見 A.4） |

`should_fallback()` 已刪除；`APPLE_AUTO_FALLBACK` 保留但長度為 1。

## A.2 程式變更（14 檔；主 agent 6 檔 + 4 個平行 subagent 分工）

| 檔案 | 變更 |
|---|---|
| `backend/services/asr_apple/dispatcher.py` | `APPLE_ONLY_BACKENDS_ERROR`；Mac 顯式 legacy → `ValueError`；`should_fallback` 刪除 |
| `backend/services/asr_apple/contract.py` | `APPLE_AUTO_FALLBACK = ("apple",)` |
| `backend/core/platform_config.py` | `APPLE_PLATFORM_ASR_BACKENDS={"auto","apple"}`；Mac 拒 legacy；accelerator `mlx-metal`→`apple-neural` |
| `backend/core/asr_model_resolver.py` | legacy 值走平台守衛；`resolve_asr_model` 在 Mac+`auto` 回 `""`（不再映射 MLX 模型 id） |
| `backend/services/transcription.py` | 移除 `should_fallback` import；`_transcribe_with_apple_chain` 改為一律 `_apple_failure`（永不 fallback）；module/函式 docstring 同步 |
| `backend/core/config.py` | `ASR_BACKEND` 描述更新 |
| `backend/api/routes.py` | `/api/config` 在 effective=apple 時 `whisper_model`/`effective_whisper_model`/`whisper_model_revision` 回 `null`（欄位名與 schema 不變） |
| `backend/main.py` | 啟動 log 在 Mac 顯示 `model=Apple SpeechAnalyzer（系統內建模型；fail-closed，無 fallback）`；舊 legacy 設定多一行可讀 ERROR 後仍 fail-loud |
| `scripts/download_models.py` | Mac/apple 直接回報「系統內建模型、免下載」並 return True；刪除 fallback 預載邏輯 |
| `scripts/verify_env.py` | apple 不再要求 `mlx_whisper`；Apple 路徑 supporting 清單為空；Mac 顯式 legacy 與 startup 同訊息 |
| `install_deps.py` / `.env.example` / `config.macos.yaml` | 移除「回退 MLX-Whisper」敘述與 `mlx_whisper` 回滾開關；`gpu.accelerator` → `apple-neural` |
| `README.md` / `CHANGELOG.md` / `doc/apple-speech-analyzer-operations.md` / `doc/apple-speech-analyzer-porting-context.md` / `doc/規格與設計/spec.md` | Mac 契約改寫；§4「回滾」改為「無回滾路徑」 |
| `pyproject.toml` / `requirements.txt` / `uv.lock` | **移除** `mlx-whisper==0.4.3 ; Darwin/arm64` 平台相依（`uv lock` 172 行刪除、0 行新增；連帶移除 `mlx`/`mlx-metal`/`llvmpipe`/`numba`/`scipy`/`tiktoken`），venv 同步卸載 |

前端 `frontend/**` **無需變更**：全站沒有引擎／模型下拉選單，唯一 ASR UI 是 accelerator 文案，
`apple-neural`→「Apple 神經引擎（本機）」已正確；`mlx-metal` 分支在 Mac 已不可達但保留給非 Mac legacy。

## A.3 測試變更（9 檔；14 處 Mac-fallback 斷言轉換）

| 檔案 | 變更 |
|---|---|
| `tests/test_apple_dispatcher.py` | 刪 `should_fallback` 8 斷言；Mac auto 鏈長 1；Mac ×3 legacy（含大小寫／連字號變體）`ValueError`；新增 `should_fallback` 不存在守衛、非 Mac 回歸守衛 |
| `tests/test_apple_chain_integration.py` | auto+Apple 錯誤改 fail-closed；`engine_chain` → `"apple"`；新增 legacy 引擎 spy 證明零呼叫 |
| `tests/test_apple_helper_absent_e2e.py` | REAL-ABSENT-02 改寫為 fail-closed（`APPLE_UNAVAILABLE`＋「未 fallback」） |
| `tests/test_download_models.py` | Mac auto 不預載（兩個 resolver `assert_not_called()`）；Mac 顯式 legacy 需 raise |
| `tests/test_verify_env.py` | apple 不再要求 `mlx_whisper` |
| `tests/test_api_routes.py` | `/api/config` Mac auto 三欄位為 `None` |
| `tests/test_transcription_service.py`、`test_device_detector.py`、`test_file_manager.py`、`test_task_processor.py` | 顯式 legacy 測試釘在非 Mac 平台（避免斷言取決於執行主機） |
| `tests/test_asr_subprocess.py` | metadata 字面 `["apple","mlx_whisper"]` → `["apple"]` |
| `tests/test_apple_packaging_guard.py` | 守衛契約反轉：本專案不得再有 `mlx-whisper`／`mlx` 相依 |

## A.4 驗證證據（全部為實跑觀察值）

- **全量測試**：`uv run pytest tests/ -q` → **`730 passed, 3 skipped, 0 failed`**（8s；
  前一回合 `88e136d` 基線為 726 passed / 3 skipped）。3 個 skip 皆為既有的 opt-in／缺 fixture。
- **真機 E2E**（同一支 `tests/0903-科務會議.m4a`，44.9 分鐘音檔，sha256 見報告）：
  `uv run python .agent/tasks/.../e2e/mac_apple_only_e2e.py` → **`verdict: PASS`**，17/17 checks 全過：
  | 情境 | 結果 |
  |---|---|
  | `ASR_BACKEND=auto`（Mac） | `backend=apple`、`engine_chain=apple`、`resolved_engine=apple`、**15.4s**、載入的 Whisper/MLX 模組 `[]` |
  | `ASR_BACKEND=apple`（Mac） | 同上、**15.4s**、逐字稿 sha256 與 auto **完全相同** |
  | helper 失敗 + `auto`（shim 立即非零離場） | `AppleSpeechError`、訊息含「未 fallback」、Whisper/MLX 模組 `[]`、legacy 引擎零呼叫 |
  報告：`e2e/mac-apple-only/report.json`。
- **路由紅線**：Mac `auto`→`("apple",)`；Mac ×3 legacy + 變體 → `ValueError`（訊息一致）；
  `APPLE_AUTO_FALLBACK == ("apple",)`；`APPLE_PLATFORM_ASR_BACKENDS == {"apple","auto"}`；
  `should_fallback` 不存在；非 Mac `auto`→`("mlx_whisper",)`、顯式 legacy 原樣通過。
- **`/api/config` 實測**（Mac）：`{"asr_backend":"auto","effective_asr_backend":"apple","whisper_model":null,"effective_whisper_model":null,"whisper_model_revision":null}`；
  `/api/health`：`accelerator=apple-neural`、`asr_backend=apple`。
- **`scripts/verify_env.py`**：Mac 實跑 exit 0，Supporting 模組不再列 MLX；`ASR_BACKEND=transformers` 時 exit 1 並印出與 startup 相同的拒絕訊息。
- **相依淨空**：`rg -n "mlx" pyproject.toml requirements.txt uv.lock` 零命中；`.venv` 內 `mlx*` 零命中；`uv sync` 已卸載 `mlx`/`mlx-metal`/`mlx-whisper`/`llvmpipe`/`numba`/`scipy`/`tiktoken`。

## A.5 殘留風險

1. **fail-loud 啟動**：舊 `.env` 若殘留 `ASR_BACKEND=mlx_whisper`，Mac 服務會在 startup
   以 `ValueError` 直接失敗（刻意，且 log 已先印一行可讀 ERROR）。修復方式：改 `auto` 或 `apple`。
2. **Windows/Linux 真機仍未複驗**：相依移除的 marker 為 Darwin/arm64，理論上不影響
   Windows/Linux；本回合以模擬矩陣重掃（`verification/windows-matrix-audit-rev2.md`）。
3. **`apple_speech_cli/.build/`** 仍在使用者本機（gitignored，未提交）；helper binary 不入版控。
4. **範圍界線（獨立稽核 C4）**：根目錄舊版 CLI（`main.py`／`src/whisper_transcriber.py`，
   git tracked）是與網頁服務無關的獨立舊工具，仍使用 faster-whisper，在 macOS 可執行。
   本回合未變更它（改造它等於新增第二套 Apple 整合＝新架構決策），已在 README 明示範圍界線。
5. **獨立稽核**：`verification/mac-apple-only-audit.md`（對抗式，判定 PARTIAL → 3 項已修：
   `apple_cli.py:449` docstring、porting-context 上游碼段限定詞、移除永久 skip 的
   `tests/test_mlx_direct.py`）與 `verification/windows-matrix-audit-rev2.md`。
