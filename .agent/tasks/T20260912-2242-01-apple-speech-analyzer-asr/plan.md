# Apple SpeechAnalyzer ASR（僅 Mac、預設）

## META

- Plan status: READY_FOR_REVIEW
- Task mode: NEW_PLAN
- Task class: CRITICAL（改預設 ASR、跨語言邊界、平台閘門；小 diff 也改變 validity/fallback 語意）
- TASK_ID: T20260912-2242-01-apple-speech-analyzer-asr
- PLAN_REVISION: 1
- REVIEW_REQUIRED: NO（技術上應 YES——改預設引擎與 fallback/gating 語意；Owner 於 2026-09-12 明示 waive 獨立審查，直進實作）
- INDEPENDENT_ACCEPTANCE_REQUIRED: NO（Owner 明示 waive；仍需 Mac/Win 雙機驗收證據）
- E2E_REQUIRED: YES（至少一次 Mac 真實音檔端到端＋一次 Windows 負向驗證）
- ACCEPTANCE_MODE: E2E
- Branch: main
- Anchor HEAD: 6da1e56
- Working tree: dirty（`?? doc/apple-speech-analyzer-porting-context.md` 未追蹤、`?? .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/e2e/attempt-02/` 未追蹤；後者與本任務無關，不得納入本任務提交）
- Canonical request/spec:
  - `doc/apple-speech-analyzer-porting-context.md`（297 行，來源 `yt_down_txt@ce7abe6+2de061d`）
  - 使用者指令：新增 Apple SpeechAnalyzer ASR、設為 Mac 預設、絕不進 Windows、第一性原理＋best practices 詳細規劃

## OWNER_CHECK

1. 我們真正要達成什麼？Mac 上傳會議音檔，預設走 Apple 本機 SpeechAnalyzer 轉逐字稿，又快（來源實測約 4.9 倍於 MLX large-v3-turbo）又免佔 HF 模型；Windows 行為完全不變。
2. 什麼是真正必要的？Mac 預設 `apple`、Windows 看不到也碰不到 `apple`、指定 `apple` 失敗就直報不偷換、`auto` 失敗才 fallback、長 MP3 不卡死、取消不殘留。
3. 什麼是支援/盡力/延後？說話人區分、熱詞/辭典校正、CJK 以外的語言調優、Linux 支援，全部延後或不做。
4. 什麼會卡死全系統，為什麼？Swift helper 找不到/編譯失敗、macOS<26 或非 Apple Silicon、Asset 未安裝、stdout 被污染、轉檔格式錯誤——任一發生若無明確錯誤碼與 fallback，前端會卡在轉錄中。
5. 我們刻意不做什麼？Windows 上任何 Apple 程式碼/依賴/建置/UI 選項；diarization；`contextualStrings` 熱詞；通用錯字表；自動編譯 helper；提交 binary。

## GOAL_CONTRACT

- PRIMARY_OUTCOME: Mac（macOS 26+、Apple Silicon）的新上傳預設使用 Apple SpeechAnalyzer 本機轉錄；Windows（含 Docker/WSL）完全不受影響、不可見、不可選。
- SUCCESS_EVIDENCE:
  - Mac `ASR_BACKEND=auto` 的新任務 `effective_asr_backend=apple`，`/health` 與日誌可觀察 `resolved_engine=apple`。
  - Windows `ASR_BACKEND=apple` 明確拒絕並提示僅 Mac；`auto` 在 Windows 永不解析到 `apple`。
  - 27 分鐘以上 MP3 在 Mac 端到端成功且 `helper_invocations=1`。
- MUST_NOT_BREAK:
  - Windows 現有三後端（`transformers`/`faster_whisper`/`mlx_whisper`）行為、快取、進度條不變。
  - 明確指定引擎 fail-closed；取消（`APPLE_CANCELLED`）永不 fallback。
  - 逐字稿不半寫、中斷不殘留暫存、stdout 單一 JSON 契約。
  - 不提交 helper binary；不把重型 ML 依賴拉進 Apple 路徑。
- NON_GOALS: diarization、熱詞/辭典/錯字表調優、Linux、Windows 版 Apple、雲端 fallback。
- CRITICAL_PATH: 平台閘門＋路由契約 → Swift helper 移植 → Python provider（執行/驗證/轉檔/超時）→ 接入 `TranscriptionService` 與隔離子程序 → 快取/健康檢查/前端預設 → 正負向驗證。

## SOURCE_OF_TRUTH

- 已驗證（讀檔）：
  - `doc/apple-speech-analyzer-porting-context.md:1-297`——兩層架構、雙命令、錯誤碼、超時公式、轉檔參數、CJK 正規化、原子寫檔、已驗證地雷。
  - `backend/services/transcription.py`（652 行）——三後端分派、`transcribe_detailed` 唯一入口、`DetailedTranscriptionResult(backend)` 已支援新引擎字串。
  - `backend/core/asr_model_resolver.py`——`infer_asr_backend`（Mac auto→`mlx_whisper`）、`build_asr_cache_signature` 已含 backend。
  - `backend/core/platform_config.py`——`SUPPORTED_ASR_BACKENDS={"auto","transformers","faster_whisper","mlx_whisper"}`、`is_darwin_arm64`、`get_platform_defaults`、`resolve_platform_asr_backend`。
  - `backend/core/config.py`（428 行）——`Settings.ASR_BACKEND="auto"`，後端只讀 env/`.env`，`config.yaml` 對後端無效。
  - `backend/services/asr_subprocess.py`（222 行）＋`backend/workers/asr_worker.py`（76 行）——v4.7.0 隔離子程序，stdout 純 JSON lines 進度。
  - `backend/services/file_manager.py:137-177`——`get_asr_cache_signature` 已按 backend/model/revision/語言分 key。
  - `backend/api/routes.py:441-460`——health 回 `asr_backend/effective_asr_backend/whisper_model`。
  - `pyproject.toml`——`mlx-whisper` 已用 `platform_system=="Darwin" and platform_machine=="arm64"` 標記；`requires-python>=3.11`。
  - `frontend/js/app.js`——加速器顯示（`mlx-metal`/CUDA/CPU），是 Apple 顯示接縫。
- 未驗證（列為未知，不擋核心方向）：`yt_down_txt` 原始 Swift/Python 原始檔內容（本 repo 無，需移植時以該 repo `ce7abe6+2de061d` 為準）；Mac 實機 `availableCompatibleAudioFormats` 與 Asset 狀態；`ffmpeg/ffprobe` 在目標 Mac 是否就緒。

## VERIFIED_CURRENT_STATE

- ASR 唯一業務入口：`TranscriptionService.transcribe_detailed` → `_load_model` → `_detect_runtime` → 三分支（`transformers`/`mlx_whisper`/`faster_whisper`）。
- 平台預設：Darwin-arm64 `auto`→`mlx_whisper`（`asr_model_resolver.infer_asr_backend`＋`platform_config.resolve_platform_asr_backend` 雙點，後者非 Mac 的 auto 原樣返回）。
- 快取：`file_manager.get_asr_cache_signature` 已把 backend 納入，換引擎自動換 key，無需遷移舊快取。
- 隔離執行：`task_processor._obtain_transcript` → `transcribe_isolated_detailed`（子程序）→ `asr_worker` in-process 調 `transcription_service`；stdout 進度契約已存在，與 Apple helper 的 stdout-JSON 契約正交（兩層 subprocess，不共用 pipe）。
- 前端無引擎選擇器（僅顯示 accelerator），改預設對 UI 衝擊小，只需顯示字串與健康資訊。

## CURRENT_FLOW

```text
上傳(mp3/wav/m4a/...) → task_processor._obtain_transcript
 → cache hit? 回傳 : transcribe_isolated_detailed(子程序)
 → asr_worker → TranscriptionService.transcribe_detailed
 → infer_asr_backend(auto→Mac:mlx_whisper / Win:transformers|faster)
 → 載模＋轉錄 → clean_transcript → (可選 LLM 校正) → 存檔/回傳
```

## REQUIREMENTS_AND_CRITICALITY

- REQ-01 Mac `auto` 預設走 `apple`（含 `ASR_BACKEND` 未設、`auto`、大小寫/`-`_`容錯）——CORE，缺則主目標失敗。
- REQ-02 Windows（含 Docker/WSL/Linux）`auto` 永不解析到 `apple`；顯式 `apple` 在非 Mac 明確拒絕（fail-fast，提示僅 Mac）——CORE，缺則違反硬約束。
- REQ-03 顯式 `apple` 在 Mac 失敗不 fallback（fail-closed）；`auto` 的 `apple` 失敗才按鏈 fallback（預設 `apple→mlx_whisper`）；`APPLE_CANCELLED` 永不 fallback——CORE。
- REQ-04 Swift helper 雙命令 `probe`/`transcribe`＋schema 1.0 單 JSON（stdout）/診斷（stderr）＋文件化離場碼——CORE。
- REQ-05 超時公式 `max(600, duration*3+300)`，`ffprobe` 失敗用 600 下限——CORE（1–2 小時會議不誤殺）。
- REQ-06 音檔前處理：MP3 一律預轉、其餘非原生轉；輸出 `pcm_s16le/16k/mono WAV`；`helper_invocations` 最小化——CORE（效能關鍵 28.6s→0.88s）。
- REQ-07 嚴格 payload 驗證（`schema_version/engine/text/segments/metadata`；`end<start` 降級；空白段丟棄計數）＋ `APPLE_OUTPUT_INVALID` 可參與 auto fallback——CORE。
- REQ-08 Apple 邊界 CJK 空白正規化（獨立函式，不動共用 normalizer）——SUPPORTING，缺則標點空白難看但不擋轉錄。
- REQ-09 原子寫逐字稿＋暫存命名/清理（`.<stem>.<12hex>.apple.wav`，正常 `finally` 刪、被殺靠 24h sweep）——SUPPORTING（正確性/磁碟衛生）。
- REQ-10 可觀測性：`metadata(requested/resolved/chain/locale/duration/elapsed/RTF/helper_invocations/conversion_reason/seconds/segment_count/dropped/time_degraded)`＋`/health` 暴露＋日誌——SUPPORTING。
- REQ-11 打包/安裝平台守衛：Windows 依賴/安裝腳本/文件絕不引入 Swift/Xcode/Apple 模型；helper 不提交 binary——CORE（與 REQ-02 同級硬約束）。
- REQ-12 前端：Mac 顯示 Apple 引擎/加速器，Windows 不出現 Apple 字樣——SUPPORTING。
- NFR-01 Mac 長檔 RTF 顯著 <1（參照值 27.7min→約 11s 級，不做硬門檻，只做回歸對比）——SUPPORTING。
- NFR-02 取消/逾時 5 秒寬限 `terminate→kill`，無殭屍行程、無殘留暫存——SUPPORTING。
- NFR-03 `import contract` 不拉 `mlx_whisper/torch/silero`；Apple 模組在 Windows import 安全（非 Mac 直接拒絕，頂層無重型依賴）——CORE。
- OOS-01 說話人區分（diarization）——另起模組。
- OOS-02 熱詞（`contextualStrings`）、繁中辭典校正、通用錯字表——實證無效/有害，不做。
- OOS-03 Linux 上的 Apple、Windows 上的 Apple、雲端 ASR fallback——不做。
- OOS-04 已有三後端解碼參數調優、LLM 摘要模板改動——不碰。

## DECISION_CONTRIBUTION_MATRIX

| Element | Goal/decision contribution | Criticality | Influence/weight | Global veto? | Missing/failure behavior | Rationale |
|---|---|---|---|---|---|---|
| `platform=gated(auto→apple)`（僅 darwin-arm64） | 決定預設引擎與 Windows 排除 | CORE | 決定性 | YES——誤判平台會讓 Windows 走向 Apple 或 Mac 走錯引擎，主 outcome 無定義 | 非 Mac 永不選 apple；Mac 上 `auto`=apple；未知平台視為非 Mac | 第一性：Apple framework 只存在於 Mac；平台是能力閘不是偏好 |
| `explicit apple fail-closed` | 誠實錯誤語意 | CORE | 決定性 | YES——偷 fallback 會掩蓋 Asset/版本問題，使用者無法定位 | 顯式 apple 任何 Apple 錯誤（含 OUTPUT_INVALID）直接拋，不試下一個 | 來源文件凍結規則；取消亦不 fallback |
| `auto fallback chain` | 可用性（Asset 未裝/舊系統時仍可轉） | CORE | 高 | NO——可降級為僅報錯，但體驗降級 | 預設 `("apple","mlx_whisper")`；台語/相容需求才保留 whisper 變體 | 先 probe 再 transcribe，減少無謂安裝等待 |
| `probe→transcribe` 順序 | 避免 transcribe 才觸發大模型下載的長等待 | SUPPORTING | 中 | NO | probe 不可用直接走 fallback，不觸發安裝 | 來源文件 §4 實測結論 |
| `timeout=max(600,duration*3+300)` | 長會議不誤殺、不無限卡 | CORE | 高 | NO（可用固定值但誤殺風險） | duration 未知用 600 下限，絕不因此失敗 | 1–2 小時會議的第一性公式 |
| `WAV 16k mono＋MP3 預轉` | 消除重取樣瓶頸 | CORE | 高（28.6s→0.88s） | NO | 轉檔失敗即該引擎失敗（auto 可 fallback） | `availableCompatibleAudioFormats` 只有 16k/8k mono |
| `stdout 單 JSON＋stderr 診斷` | 可解析性 | CORE | 高 | YES（stdout 污染即 OUTPUT_INVALID，主決策無效） | 污染→`APPLE_OUTPUT_INVALID` | Runner＋OutputGuard 保證 |
| `CJK normalize` 獨立函式 | 中文標點品質 | SUPPORTING | 低 | NO | 不做只影響美觀 | 不動共用 normalizer，避免回歸 |
| `metadata` 觀測欄位 | 除錯/驗收證據 | SUPPORTING | 中 | NO | 缺則驗收不可觀察 | 欄位只放純量，不放逐字稿與原始 payload |

## CONSTRAINTS_NON_GOALS_AND_OUT_OF_SCOPE

- 硬約束：macOS 26+、Apple Silicon、`Python>=3.12,<3.13`（來源文件；本 repo `pyproject` 目前 `>=3.11`，不全域收緊——見 DEC-09）、需 `ffmpeg/ffprobe`。
- 硬約束：Windows 零 Apple——程式碼（import/路由/錯誤訊息除外）、依賴、建置步驟、UI 字串、文件預設值皆不得讓 Windows 需要 Apple。
- OOS 見 REQ 區 `OOS-*`；特別重申：diarization、熱詞、辭典、錯字表、自動編譯 helper、提交 binary。

## SEMANTIC_CONTRACT

- 現狀：`SUPPORTED_ASR_BACKENDS={auto,transformers,faster_whisper,mlx_whisper}`；Mac auto→`mlx_whisper`；快取 key 含 backend；`DetailedTranscriptionResult.backend` 自由字串。
- 目標：
  - `SUPPORTED_ASR_BACKENDS` 新增 `apple`（驗證錯誤訊息同步更新）；`resolve_platform_asr_backend("apple")` 在非 Mac 拋 `ValueError（僅 macOS）`。
  - `infer_asr_backend`：`auto`＋darwin-arm64→`apple`；顯式值（含大小寫/`-`_`容錯）原樣尊重；非 Mac 的 `auto` 不變（不碰 Windows 行為）。
  - `resolve_engine_chain(requested)`：`apple→(apple,)` fail-closed；`auto`＋Mac→`(apple, mlx_whisper)`（是否追加 `transformers` 見 DEC-02：不追加）；`auto`＋非 Mac→現狀不變；`APPLE_CANCELLED` 永不繼續。
  - 錯誤碼（helper 離場碼→Python 例外）：`0` 成功、`2 APPLE_UNAVAILABLE`、`3 LOCALE_UNSUPPORTED`、`4 ASSET_ERROR`、`5 INPUT_ERROR`、`6 TRANSCRIPTION_ERROR`、`7 CANCELLED`、`1` 通用（含 `APPLE_TIMEOUT`/`APPLE_OUTPUT_INVALID` 子型別）。`explicit apple` 全向上拋；`auto` 下除 CANCELLED 外繼續鏈。
  - 副作用：只在輸入檔同目錄建 `.<stem>.<12hex>.apple.wav`，成功/`finally` 刪除；sweep 只認精確正則、只刪單層一般檔、不跟隨連結、不遞迴、>24h。
  - 相容：舊快取因 backend 不同自動失效；API 不刪欄位只加（`effective_asr_backend` 值域多 `apple`）；前端無引擎選擇器故無破壞性變更。
- 不變：`transcribe_detailed(audio_path, progress_callback)` 簽名；`_obtain_transcript` 快取優先；VAD/beam 等 Whisper 參數不套用到 Apple（Apple 固定 `use_vad=False` 語意的新請求，不改 frozen 入參）。

## DECISIONS

- DEC-01 預設引擎：Mac `auto`→`apple`，非 Mac 不變。證據：來源文件實測快約 4.9 倍＋使用者明確要求預設。替代：Mac auto 仍 mlx——否決，違背使用者指令。
- DEC-02 auto 鏈形狀：`(apple, mlx_whisper)` 為預設；`transformers/faster_whisper` 不入預設鏈（需顯式指定）。理由：最小 fallback、與現 Mac 預設（mlx）銜接。替代：三跳鏈——否決，無台語需求時多餘（來源文件 §3.2 已允許簡化）。
- DEC-03 獨立 Swift helper（SwiftPM executable，無簽名、無 Info.plist，Python subprocess 呼叫），不做 in-process 綁定。理由：Speech 框架僅 Swift API＋隔離重型依賴。替代：pyobjc 橋接——否決，脆弱且污染 Apple 路徑。
- DEC-04 helper 位置與產物：`apple_speech_cli/` 整包移植，release 產物路徑 `apple_speech_cli/.build/release/apple-speech-cli`；搜尋順序 `顯式設定→repo release 產物→PATH`；找不到只給建置指令、不自動編譯；binary 永不提交（`.gitignore`）。理由：直接複用來源文件 §5 最小清單。
- DEC-05 部署目標 `platforms:[.macOS(.v14)]`＋弱連結 Speech，舊系統啟動後回 `APPLE_UNAVAILABLE` 而非載入崩潰。理由：優雅降級＋auto 可 fallback。
- DEC-06 轉檔：`CONVERSION_ARGS=(-vn -c:a pcm_s16le -ar 16000 -ac 1)`、`SUFFIX=.wav`、`PREFLIGHT={.mp3}`、原生集合含 `m4a/mp4/wav/aif/aiff/caf/mp3`。理由：實測轉檔 28.6s→0.88s 且逐字一致。
- DEC-07 超時/執行：`resolved_timeout=max(600,duration*3+300)`；`SubprocessRunner` stdout/stderr 獨立排空、`terminate→5s→kill`、stdout 上限 8M 字符；`ffprobe` 失敗用下限。理由：長會議＋大 JSON 的第一性工程。
- DEC-08 文本：新增 `normalize_apple_text`（CJK 專用，複用來源正則），不改 `text_postprocess.clean_transcript` 共用路徑；Apple 文本仍走既有 `clean_transcript`（簡繁/黑名單/去重）下游。理由：避免回歸＋保留既有衛生層。
- DEC-09 Python 版本：不全域收緊 `pyproject requires-python`；Apple 模組在 import/執行期檢查 `>=3.12` 並報清晰錯誤，文件註明。理由：避免為單一 Mac-only 功能卡死 Windows/Linux 的 3.11 用戶。
- DEC-10 Windows 守衛縱深：`platform_config`（值驗證）＋`asr_model_resolver`（auto 永不 apple）＋`apple provider` 頂部 `platform.system()!=Darwin→APPLE_UNAVAILABLE`＋`install_deps.py`/docs/前端三處同步。理由：單點守衛會被繞過（env/直接 import/舊快取）。
- DEC-11 可觀測欄位：`metadata` 十一鍵（§5 清單）＋`/health` 新增 `apple_helper.{available,path,probe}`（僅 Mac 計算，Windows 回 `supported:false` 不執行 probe）。理由：驗收必須可觀察。
- DEC-12 不做：diarization、contextualStrings、辭典、通用錯字表、自動編譯。理由：來源文件 §4 實證 no-op/無鑑別力/有害。

## COUPLING_AND_FAILURE_CONTAINMENT

- Apple 失敗只影響該次轉錄該引擎嘗試；`auto` 下向鏈傳遞的是「已分類錯誤＋可觀察日誌」，不是崩潰；`explicit apple` 向上拋穩定錯誤，前端顯示明確訊息。
- Swift 崩潰/輸出污染被 `validate_transcription_payload` 收斂為 `APPLE_OUTPUT_INVALID`，不污染快取（驗證通過才寫快取）。
- 取消（SIGTERM/SIGINT→helper 協作取消→`APPLE_CANCELLED`）優先於逾時，且永不 fallback，避免使用者取消後又被鏈喚醒。
- Windows 側：Apple 模組 import 不得在模組頂層 import 重型依賴；任何 Apple 路徑在非 Mac 於最早分支返回，保證零副作用、零子程序、零檔案寫入。

## COMPLEXITY_BUDGET

- 新增抽象：`contract.py`（凍結介面＋錯誤型別，付費：跨語言契約唯一來源）、`dispatcher.resolve_engine_chain`（付費：fail-closed 語意集中）、`apple_cli.py`（執行/驗證/正規化，付費：subprocess hardening）、`apple.py`（前處理/provider，付費：效能關鍵轉檔）。每項都有來源文件對應物，非新發明。
- 新增狀態：`helper_invocations/conversion_reason/conversion_seconds`（付費：驗收 MP3 預轉與單次呼叫）；`APPLE_*` 設定 4–6 個（路徑/locale/preset/預轉開關，見 WAVE-04）。
- 新增依賴：零 Python 依賴；系統依賴 Xcode Swift 工具鏈＋ffmpeg（Mac only，文件＋`verify_env` 提示，不寫死安裝）。
- 跨層協調：Swift↔Python 僅經 schema 1.0 JSON＋離場碼，不共享記憶體/型別——協調面最小。

## TARGET_CONTRACT

```text
使用者(上傳) → task_processor(快取→chain) → dispatcher(auto→apple→mlx / explicit→單點)
 → apple provider(probe→ffprobe duration→preflight convert→helper transcribe→validate→normalize)
 → DetailedTranscriptionResult(backend="apple", chunks含time-indexed時間軸)
 → clean_transcript → 存檔 → metadata/health 可觀察
Windows: chain 永不含 apple；apple 顯式→清晰拒絕；helper 不存在也不被尋找之外的副作用。
```

## CHANGE_MAP

- 新增：`apple_speech_cli/`（Package.swift＋Sources/AppleSpeechKit/*＋Sources/apple-speech-cli/*＋Tests）、`backend/services/asr_apple/contract.py`、`dispatcher.py`、`apple_cli.py`、`apple.py`（若要避免與既有 `transcription.py` 同層膨脹；最終路徑 WAVE-01 鎖定）、`tests/test_apple_*`。
- 修改：`backend/core/platform_config.py`（SUPPORTED＋defaults＋resolve 守衛）、`backend/core/asr_model_resolver.py`（infer＋chain）、`backend/core/config.py`（APPLE_* 設定）、`backend/services/transcription.py`（分派 apple 分支）、`backend/services/asr_subprocess.py`＋`backend/workers/asr_worker.py`（progress/逾時相容）、`backend/services/file_manager.py`（簽名已相容，僅確認＋測試）、`backend/api/routes.py`（health/config）、`frontend/js/app.js`（顯示）、`install_deps.py`＋`.env.example`＋`config.macos.yaml`＋`README/CHANGELOG`＋`.gitignore`。
- 不碰：三舊後端解碼實作、VAD 參數語意、LLM 摘要、diarization（不存在）、`text_postprocess` 共用正規化器本體。

## CRITICAL_PATH

1. 鎖定 chain＋守衛語意（WAVE-01，無 Swift 也可單測）。
2. Swift helper 可建置＋`probe/transcribe` 契約成立（WAVE-02，最大不確定性最早消除）。
3. Python provider 打通＋長 MP3 單次呼叫（WAVE-03，效能命脈）。
4. 全鏈接線＋健康/快取/前端（WAVE-04）。
5. 正負向＋平台矩陣驗收（WAVE-05）。

## IMPLEMENTATION_WAVES

- WAVE-01 平台路由與契約骨架（無 Swift 可測）
  - 範圍：`backend/core/platform_config.py`（`SUPPORTED_ASR_BACKENDS＋"apple"`、`get_platform_defaults` Mac→`apple`、`resolve_platform_asr_backend` 非 Mac 拒 apple）、`backend/core/asr_model_resolver.py`（`infer_asr_backend`＋新增 `resolve_engine_chain`）、`backend/services/asr_apple/contract.py`（`EngineName/AUTO_FALLBACK/DEFAULT`、錯誤碼、`ASRSegment`、import hygiene 斷言測試）。
  - REQ: REQ-01/02/03、NFR-03。前置：無。意圖：先把「誰能上誰不能上」變成可單測的純函式。
  - 驗證：`pytest tests/test_apple_dispatcher.py -q`（auto-Mac→apple、auto-Win≠apple、explicit apple 單點、大小寫/`-`_`容錯）。
  - 退出：三平台（mock `platform.system/machine`）矩陣全綠。回滾：純新增＋預設改動可一行 revert。
- WAVE-02 Swift helper 移植與建置契約
  - 範圍：`apple_speech_cli/` 全包（TranscriptionService/SpeechRuntime/Runner/OutputGuard/SchemaPayload/Errors/CLI/Package＋Tests）、`.gitignore`（`.build/`＋產物）、`doc/apple-speech-*.md` 建置說明。
  - REQ: REQ-04。前置：需 Mac＋Xcode＋macOS 26 SDK（缺則本波記 env-blocker，不擋 WAVE-01）。意圖：把最大不確定性（Swift API/SDK/簽名）最早驗證。
  - 驗證：`swift test` 全綠；`apple-speech-cli probe` 回 JSON；短中文 `transcribe` stdout 單 JSON。
  - 退出：`probe`＋短檔 `transcribe` 在 Mac 實機通過。回滾：整目錄刪除不影響舊後端。
- WAVE-03 Python Apple provider（效能命脈）
  - 範圍：`asr_apple/apple_cli.py`（`resolve_executable`三階搜尋、`SubprocessRunner`雙執行緒排空/terminate-5s-kill/8M 上限、`validate_transcription_payload`、`normalize_apple_text`、`parse_progress_line`、`resolved_timeout_seconds`）、`asr_apple/apple.py`（`preflight_conversion_reason`、`CONVERSION_ARGS`、`_temp_target/_convert`/重試一次、`transcribe`主流程：probe→duration→convert→helper→validate→normalize→metadata）、`transcription.py` 接入分支（apple 用 `use_vad=False` 語意，不改 whisper 參數）。
  - REQ: REQ-05/06/07/08/09。前置：WAVE-02 的 helper 二進位（單測可用 fake helper 先行）。
  - 驗證：fake-helper 單測（逾時/污染/取消/重試）；Mac 實機 27min MP3 `helper_invocations=1`＋`conversion_reason=fragile_native_container`。
  - 退出：短檔＋長 MP3＋拔 helper 三場景符合預期。回滾：關閉預設（env 切回 mlx）即回退。
- WAVE-04 全鏈接線（設定/快取/健康/前端/隔離子程序）
  - 範圍：`config.py`（`APPLE_SPEECH_CLI_PATH/APPLE_LOCALE/APPLE_PRESET/APPLE_ENABLE_PREFLIGHT` 等，預設 `preset=time-indexed`、`locale=zh-Hant-TW` 可覆寫）、`transcription.py get_device_info`（`accelerator` 顯示字串，建議 `apple-neural`）、`file_manager`（確認簽名＋補測試）、`task_processor`（進度文案「Apple 本機轉錄中…」）、`routes.py`（health/config 加 `apple_helper` 區）、`asr_subprocess/asr_worker`（Apple 大 JSON/長超時相容）、`frontend/js/app.js`（Mac 顯示 Apple，Windows 無字樣）、`install_deps.py/.env.example/config.macos.yaml` 平台守衛。
  - REQ: REQ-10/11/12。前置：WAVE-01＋03。意圖：把能力變成可營運可觀察的產品行為。
  - 驗證：`/health` Mac/Win 差異快照測試；前端產物 grep 斷言（Win bundle 無 "Apple Speech"）。
  - 退出：Mac 預設＋Win 無感雙驗。回滾：env 明確指定舊 backend 即回退。
- WAVE-05 平台矩陣與文件收尾
  - 範圍：`tests/test_apple_*` 全套（見 TEST_AND_ACCEPTANCE）、`scripts/verify_env` Apple 段（僅 Mac 檢查 Xcode/helper/ffmpeg，Windows 跳過）、`README/CHANGELOG/doc/操作手冊`、長檔效能對比記錄。
  - REQ: 全 REQ 回歸。前置：WAVE-02/03/04。意圖：把「Mac 快、Win 看不見」變成可重跑的證據。
  - 驗證：`pytest tests/ -q -k "apple or dispatcher or transcription"`＋E2E 兩機矩陣。
  - 退出：DoD 全勾。回滾：文件版＋預設開關。

## TEST_AND_ACCEPTANCE

- CHECK-01 Mac auto 預設解析 | `pytest tests/test_apple_dispatcher.py -q`（mock darwin-arm64）| REQ-01，GOAL_CRITICALITY=CORE，EVIDENCE_ROLE=closure-gating，CLOSURE_GATE=YES，BASELINE_REQUIRED=YES（現 Mac auto→mlx_whisper，本變更為有意改變，需更新基線快照），failure=task regression，WAIVER_ALLOWED=NO，WAIVER_AUTHORITY=NONE。
- CHECK-02 Windows 排除 | 同上（mock Windows/Linux＋ValueError 訊息斷言）| REQ-02，CORE，closure-gating，CLOSURE_GATE=YES，BASELINE_REQUIRED=YES（Win auto 行為不變），failure=task regression，WAIVER_ALLOWED=NO，WAIVER_AUTHORITY=NONE。
- CHECK-03 顯式 fail-closed | fake helper 回錯誤碼 4/6/1，`requested=apple` 直接拋不試下一個；`auto` 則 fallback（mock）| REQ-03，CORE，closure-gating，CLOSURE_GATE=YES，BASELINE_REQUIRED=NO，failure=task regression，WAIVER_ALLOWED=NO，WAIVER_AUTHORITY=NONE。
- CHECK-04 取消不 fallback | fake helper 回 7/`APPLE_CANCELLED`，`auto` 亦直接拋 | REQ-03，CORE，closure-gating，CLOSURE_GATE=YES，BASELINE_REQUIRED=NO，failure=task regression，WAIVER_ALLOWED=NO，WAIVER_AUTHORITY=NONE。
- CHECK-05 契約純潔 | `import contract` 後 `sys.modules` 無 `torch/mlx_whisper/silero/faster_whisper`；Windows import apple provider 無副作用 | NFR-03，CORE，closure-gating，CLOSURE_GATE=YES，BASELINE_REQUIRED=NO，failure=task regression，WAIVER_ALLOWED=NO，WAIVER_AUTHORITY=NONE。
- CHECK-06 超時公式 | `resolved_timeout(0/600/3600)=(600/2100/11100)`；ffprobe 失敗→600 | REQ-05，SUPPORTING，EVIDENCE_ROLE=regression-guard，CLOSURE_GATE=NO，BASELINE_REQUIRED=NO，failure=task regression（需與 pre-existing 區分），WAIVER_ALLOWED=YES，WAIVER_AUTHORITY=OWNER。
- CHECK-07 長 MP3 單次呼叫 | Mac 實機 ≥27min MP3：`conversion_reason=fragile_native_container`、`helper_invocations=1`、端到端成功 | REQ-06，CORE，E2E gating，CLOSURE_GATE=YES，BASELINE_REQUIRED=YES（記錄 RTF 對比 mlx），failure=task regression，WAIVER_ALLOWED=NO，WAIVER_AUTHORITY=NONE；無 Mac 實機時記 env-blocker（見 v4.2 路由），不判 IMPLEMENTATION_BLOCKED。
- CHECK-08 輸出驗證 | 污染 stdout/缺欄位/`end<start`/空白段→`APPLE_OUTPUT_INVALID`＋計數正確；合法 payload 通過 | REQ-07，CORE，closure-gating，CLOSURE_GATE=YES，BASELINE_REQUIRED=NO，failure=task regression，WAIVER_ALLOWED=NO，WAIVER_AUTHORITY=NONE。
- CHECK-09 CJK 空白 | `今天天氣很好 ，我們一起去公園散步`→`今天天氣很好，我們一起去公園散步` | REQ-08，SUPPORTING，EVIDENCE_ROLE=regression-guard，CLOSURE_GATE=NO，BASELINE_REQUIRED=NO（BASELINE_DELTA），failure=task regression，WAIVER_ALLOWED=YES，WAIVER_AUTHORITY=OWNER。
- CHECK-10 暫存衛生 | 成功無殘留；sweep 只刪精確正則＋>24h，不跟隨連結 | REQ-09，SUPPORTING，EVIDENCE_ROLE=regression-guard，CLOSURE_GATE=NO，BASELINE_REQUIRED=NO，failure=task regression，WAIVER_ALLOWED=YES，WAIVER_AUTHORITY=OWNER。
- CHECK-11 健康可觀察 | Mac health 含 `apple_helper{available,path}`；Windows 為 `supported:false` 且不執行 probe | REQ-10，SUPPORTING，EVIDENCE_ROLE=acceptance-observable，CLOSURE_GATE=NO，BASELINE_REQUIRED=NO，failure=task regression，WAIVER_ALLOWED=YES，WAIVER_AUTHORITY=OWNER。
- CHECK-12 包裝守衛 | Windows 依賴解析無 Apple；`install_deps.py --check` 在 Win 不提示 Xcode；repo 無 tracked binary | REQ-11，CORE，closure-gating，CLOSURE_GATE=YES，BASELINE_REQUIRED=NO，failure=task regression，WAIVER_ALLOWED=NO，WAIVER_AUTHORITY=NONE。
- CHECK-13 前端 | Mac 顯示 Apple；Win 產物無 Apple 字樣 | REQ-12，SUPPORTING，EVIDENCE_ROLE=acceptance-observable，CLOSURE_GATE=NO（NON_GATING），BASELINE_REQUIRED=NO，failure=task regression，WAIVER_ALLOWED=YES，WAIVER_AUTHORITY=OWNER。
- CHECK-14 全量回歸 | `pytest tests/ -q` 與基線差異僅允許「Mac auto 預設改變」相關的預期更新 | MUST_NOT_BREAK，EVIDENCE_ROLE=repo-health，CLOSURE_GATE=BASELINE_DELTA（選 BASELINE_DELTA，不選 HARD_CLEAN），BASELINE_REQUIRED=YES，failure 三分類（task regression / pre-existing failure / environment blocker），WAIVER_ALLOWED=YES（僅 pre-existing），WAIVER_AUTHORITY=REVIEWER（本任務 Owner 代行）。
- 廣域檢查路由：pass→closure；task regression→IMPLEMENTATION_BLOCKED 修復；pre-existing failure→記錄＋OWNER waiver 可放行；unavailable baseline→先建基線；environment blocker（無 Mac/SDK）→CHECK-07 記 blocker，不 collapse 為 IMPLEMENTATION_BLOCKED。

## MIGRATION_COMPATIBILITY_ROLLBACK

- 遷移：無需資料遷移；舊快取因簽名含 backend 自動隔離；env 未設者 Mac 自動升級、Windows 無感。
- 相容：API 只加欄位；`/health` 新增區段前端忽略未知鍵；`config.macos.yaml` 僅文件參考（後端讀 env）。
- 回滾：任一波皆可 `ASR_BACKEND=mlx_whisper`（Mac）或 `transformers`（Win）一行恢復；WAVE-02/03 整目錄刪除即回到三後端；回滾不刪使用者逐字稿與快取。

## DEFERRED_OR_BEST_EFFORT

- BEST_EFFORT：RTF 基準記錄、probe 資產預熱提示文案、`zh-Hant-TW` locale 自動協商（先固定＋`localeReport` 解析）。
- DEFERRED：diarization、熱詞、辭典、錯字表、Linux、串流式進度（先用既有子程序進度 callback 粒度）、helper 自動編譯/自動下載模型。

## RISKS

- R1 macOS SDK/版本碎片：CI 或開發機無 macOS 26 SDK 導致 WAVE-02 無法驗證。緩解：部署目標 v14＋弱連結＋`APPLE_UNAVAILABLE`；無 SDK 時標 env-blocker 不硬擋純函式驗收。
- R2 Asset 首次下載長等待被誤判卡死。緩解：`probe` 先行＋進度文案＋超時公式下限 600s＋日誌可觀察。
- R3 長 MP3 原生讀取偶發失敗。緩解：MP3 一律預轉，不賭原生重試（來源實測 27.7min 穩定失敗）。
- R4 stdout 污染（watchdog/崩潰與正常競態）。緩解：OutputGuard＋單 JSON＋嚴格驗證→OUTPUT_INVALID。
- R5 PRIORITY_INVERSION：過早打磨 CJK/文案/metadata 而 helper 契約未通。緩解：波序強制 WAVE-02 先於 polish；CHECK-07 未過不做顯示層打磨。

## BLOCKING_UNKNOWNS

- 無（方向不被任何單一未知推翻；缺 Mac 實機只降級為 env-blocker，不判 BLOCKED）。

## NON_BLOCKING_UNKNOWNS

- U1 `yt_down_txt` 原始 Swift 檔的逐行差異（本 repo 僅有移植上下文，需移植時以該 repo `ce7abe6+2de061d` 為準）。
- U2 目標 Mac 的 `ffprobe` 可用性（缺則用下限＋明確日誌）。
- U3 `zh-Hant-TW` 在 `localeReport` 的 resolvedIdentifier 形態（執行期以 report 為準，測時記錄）。

## DEAD_ENDS

- D1 pyobjc/in-process 綁定：脆弱＋污染依賴，已否決。
- D2 通用錯字表/辭典校正：實測有害/無鑑別力，已否決。
- D3 `contextualStrings` 熱詞：SpeechTranscriber 下 no-op，已否決。
- D4 MP3 原生重試賭博：27.7min 穩定失敗，已否決，改一律預轉。
- D5 全域收緊 `requires-python` 到 3.12：為單一 Mac-only 功能懲罰全平台，已否決，改執行期檢查。

## RISKIEST_ASSUMPTIONS

- A1 目標 Mac 皆為 Apple Silicon＋macOS 26+（若有 Intel/舊系統，auto 必須優雅 fallback 而非崩潰——由 DEC-05＋probe 覆蓋）。
- A2 `ffmpeg` 在 Mac 可用（若無，Apple 路徑明確失敗並 fallback，而非靜默壞檔）。
- A3 Swift 工具鏈在建置機可用（若無，WAVE-02 記 env-blocker，產品碼仍保持 Windows 安全）。
- A4 16k mono WAV 即原生最速路徑在會議專案同樣成立（由 CHECK-07 實測確認，否則調回 AAC 對照）。
- A5 現有 `clean_transcript` 不會破壞 Apple 已正規化文本（由 CHECK-09＋回歸快照保護）。

## DEFINITION_OF_DONE

- Mac 新上傳預設 `apple` 且可從 health/日誌/metadata 證明；Windows `auto` 無 apple、顯式 apple 被拒。
- 長 MP3（≥27min）Mac E2E 成功＋`helper_invocations=1`；拔 helper 時 auto fallback 可觀察、顯式 fail-closed。
- `swift test`＋`pytest` 相關套件綠；repo 無 tracked binary；Windows 產物無 Apple 字樣/依賴。
- 文件（建置、env、操作手冊、CHANGELOG）同步；回滾開關（`ASR_BACKEND` 明確值）驗證過。

## HANDOFF_HINTS

- 實作時以 `doc/apple-speech-analyzer-porting-context.md §5` 最小清單為搬運清單，§4 地雷為禁區。
- 先寫 `contract＋dispatcher` 單測，再碰 Swift；Swift 通之前不打磨 UI 文案。
- 任何改動若改變 requiredness/gating/fallback/錯誤穩定語意，實作中必須升級為 STOP_AND_ESCALATE（本任務 Owner 已 waive 事前審查，不代表語意可擅改）。
