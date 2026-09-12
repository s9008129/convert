# Apple SpeechAnalyzer 本機 ASR 操作手冊（僅 macOS）

> 適用：macOS 26+ / Apple Silicon 主機（`ASR_BACKEND=auto` 或 `apple`）。
> Windows / Linux / Docker 完全不受本功能影響：不會解析到 `apple`、不會顯示 Apple
> 狀態、安裝與環境檢查也不會出現 Xcode / Swift / helper 字樣。
> 建置細節與 Swift 契約另見 [Apple Speech CLI 建置與驗證手冊](apple-speech-cli-build.md)；
> 移植背景見 [移植開發上下文](apple-speech-analyzer-porting-context.md)。

## 1. 快速結論

| 情境 | 行為 |
|---|---|
| Mac + `ASR_BACKEND=auto`（預設） | Apple SpeechAnalyzer（唯一引擎、本機、免 HF 模型）；失敗直接失敗，**永不 fallback** |
| Mac + `ASR_BACKEND=apple`（明確指定） | Apple SpeechAnalyzer；任何失敗直接回報（fail-closed），不偷換引擎 |
| Mac + `ASR_BACKEND=transformers`／`faster_whisper`／`mlx_whisper` | 硬性拒絕（穩定 `ValueError`）：Mac 僅提供 Apple SpeechAnalyzer |
| Windows / Linux / Docker + `auto` | 維持既有 `transformers` / `faster_whisper` 解析，永不解析到 `apple` |
| 非 Mac + `ASR_BACKEND=apple` | 啟動/解析時直接拒絕並提示僅 macOS |
| 使用者取消（SIGTERM/SIGINT） | 回報 `APPLE_CANCELLED`，**任何情況都不 fallback** |

引擎解析鏈（凍結語意）：

- Mac `auto`：`apple`（單鏈、單一引擎，**永不 fallback**）
- Mac 明確 `apple`：`apple`（單點，fail-closed）
- Mac 顯式 `transformers`／`faster_whisper`／`mlx_whisper`：`ValueError`（Mac 已無 Whisper 選項）
- 非 Mac `auto`：與現狀完全一致（不含 `apple`）

## 2. 如何確認 Mac 走 Apple 引擎

### 2.1 `/api/health` 與 `/api/config`

```bash
# health：Apple 引擎可觀測欄位（device_info.asr_backend／accelerator／apple_helper）
curl -s http://localhost:9527/api/health | python3 -m json.tool
# config：effective_asr_backend（/health 沒有此欄）
curl -s http://localhost:9527/api/config | python3 -m json.tool | grep effective_asr_backend
```

檢查三個欄位：

- `device_info.asr_backend`＝`apple`：本次解析出的引擎（`/health` 無
  `effective_asr_backend`，該欄只在 `GET /api/config`，可交叉確認 `auto` 的解析結果）。
- `device_info.accelerator`＝`apple-neural`：前端狀態列顯示「Apple 神經引擎（本機）」的依據。
- `device_info.apple_helper` 區段：Mac 顯示 `supported`／`available`（helper 是否可用）、
  `path` 與 `probe`；非 Mac 顯示 `supported: false`，且**不會**去執行 helper probe。
  加 `?quick=true`（例如 `/api/health?quick=true`）時**不 spawn helper、不執行 probe**，
  只回報平台支援度；此時 `available: false` 代表「尚未驗證」，不代表 helper 不可用。

### 2.2 前端狀態列

Mac 上頁尾狀態列出現「Apple 神經引擎（本機）」＝目前引擎是 Apple（Mac 唯一引擎）；
Mac 不會再出現「Apple Silicon（MLX/Metal）」引擎狀態（已無 MLX-Whisper 引擎）。
（本產品沒有引擎選擇器；引擎由後端環境變數決定。）

### 2.3 任務 metadata 與日誌

每次 Apple 轉錄會產生中繼資料（metadata），鍵名為凍結契約：

| 鍵 | 意義 |
|---|---|
| `requested_engine` / `resolved_engine` / `engine_chain` | 要求引擎、實際使用引擎、本次解析出的引擎嘗試鏈；Mac 恆為 `resolved_engine="apple"`、`engine_chain="apple"`（單一引擎，無 fallback） |
| `locale` | 請求的 Apple locale（`APPLE_LOCALE`，預設 `zh-Hant-TW`；非協商後值） |
| `audio_duration_seconds` / `elapsed_seconds` / `real_time_factor` | 音長、耗時、RTF |
| `helper_invocations` | 本次呼叫 Apple helper 執行檔的次數（正常長檔應為 1） |
| `conversion_reason` / `conversion_seconds` | 是否預轉與原因／轉檔耗時 |
| `segment_count` / `segments_dropped` / `segments_time_degraded` | 段落計數與品質降級統計 |

```bash
# 應用日誌檔名帶日期（app_YYYY-MM-DD.log），搜尋當日檔案：
grep "ASR 引擎觀測" "data/logs/app_$(date +%F).log" | tail -20
# 每行即 metadata JSON，含 helper_invocations／conversion_reason／resolved_engine／engine_chain 等鍵
```

## 3. 如何建置 helper（一次性，不自動）

需求：macOS 26+、Apple Silicon、Xcode（Swift 6.0+ 工具鏈）、`ffmpeg`/`ffprobe`。
安裝腳本與服務**不會**自動編譯 helper，也不會下載模型。

```bash
cd apple_speech_cli
swift build -c release
# 產物：apple_speech_cli/.build/release/apple-speech-cli（不進版控）

# 選用：先確認 locale 與 asset 狀態（probe 不會安裝模型）
./.build/release/apple-speech-cli probe --locale zh-Hant-TW
```

檢查與提示（僅提示、不編譯）：

```bash
uv run python scripts/verify_env.py        # macOS 會多一段 Apple 檢查（缺工具有建置指令）
uv run python install_deps.py --check      # Windows 不會出現任何 Apple 字樣
```

- helper 位置搜尋順序：`APPLE_SPEECH_CLI_PATH` → repo `apple_speech_cli/.build/release/`
  → `PATH`。
- 若把 helper 放到自訂路徑，於 `.env` 設 `APPLE_SPEECH_CLI_PATH=/path/to/apple-speech-cli`。
- 相關設定（僅 macOS 生效）：`APPLE_LOCALE`（預設 `zh-Hant-TW`）、`APPLE_PRESET`
  （預設 `time-indexed`，才有逐詞時間軸；可選 `time-indexed`／`plain`／
  `plain-alternatives`／`progressive`／`time-indexed-progressive`，helper 端對應
  `--preset <值>`）、`APPLE_ENABLE_PREFLIGHT`（預設 `true`，MP3 等先預轉
  16k mono WAV，效能關鍵）。

## 4. 無回滾路徑：Mac 只提供 Apple SpeechAnalyzer

Mac 版沒有 Whisper 模型選項、也沒有 fallback：`ASR_BACKEND=auto` 與 `apple` 都只走
Apple SpeechAnalyzer，任何失敗（helper 缺失／不可執行、取消、逾時、輸出無效）都直接
使任務失敗（fail-closed）。

- 想回到舊 Whisper 行為：只能回退版本（Mac 沒有環境變數回滾開關）。
- 顯式 legacy 值（`transformers`／`faster_whisper`／`mlx_whisper`）會被硬性拒絕：
  `ASR_BACKEND=<x> 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）`。
- 移除 `apple_speech_cli/` 目錄只會讓 Apple 失敗（任務 failed），不會回退其他引擎。
- Windows / Linux 不需任何動作（原本就看不到 Apple）。

## 5. 錯誤碼對照（helper 離場碼，凍結契約）

| 離場碼 | 錯誤碼 | 意義 | 建議處理 |
|---|---|---|---|
| 0 | — | 成功 | — |
| 1 | `APPLE_TIMEOUT` / `APPLE_OUTPUT_INVALID` | 逾時（公式 `max(600, 音長*3+300)` 秒）、或 stdout 契約驗證失敗（污染、缺欄位、`end<start`、空白段） | 逾時：確認檔案可讀與機器負載；`OUTPUT_INVALID`：保留 stderr 診斷回報 |
| 2 | `APPLE_UNAVAILABLE` | 平台/API 不可用（macOS < 26、非 Apple Silicon、找不到 helper 等） | 升級 macOS、確認 Apple Silicon、建置 helper 或設 `APPLE_SPEECH_CLI_PATH` |
| 3 | `APPLE_LOCALE_UNSUPPORTED` | 該 locale 沒有對應支援（不會自動釋放其他 locale 保留額度） | 用 `probe --locale <id>` 確認支援清單，或改 `APPLE_LOCALE` |
| 4 | `APPLE_ASSET_ERROR` | 模型（asset）安裝/狀態錯誤 | 確認網路與系統語言資源後重試；先 `probe` 看 `asset_status` |
| 5 | `APPLE_INPUT_ERROR` | 輸入參數/檔案錯誤（不存在、格式無法讀取、未知旗標） | 確認路徑與檔案完整性；必要時先以 `ffprobe` 驗證 |
| 6 | `APPLE_TRANSCRIPTION_ERROR` | 辨識失敗 | 檢查音訊內容（全靜音/毀損）與系統資源 |
| 7 | `APPLE_CANCELLED` | 使用者取消（SIGTERM/SIGINT，5 秒寬限後強制結束） | 正常取消；**不會** fallback，重新上傳即可 |

對外行為：Mac 上上述任何錯誤（含 `APPLE_CANCELLED`）都直接回報並使任務失敗
（fail-closed）；Mac 沒有 fallback，永不改用其他引擎。

## 6. 觀測 `helper_invocations` 與 `conversion_reason`

- `helper_invocations`：本次任務實際呼叫 helper 的次數。目標是 **1**：
  音檔（含長 MP3）先由 Python 端轉成 16k mono WAV，再由 helper 一次辨識完成。
  若大於 1，代表發生重試或未預期的二次呼叫（請保留日誌回報）。
- `conversion_reason`：`fragile_native_container`＝MP3（一律先預轉，不賭原生讀取）、
  `non_native_container`＝非原生容器（m4a/wav 等原生格式不會出現此鍵）。
- 觀測方式：

```bash
# 任務 metadata 落地處：當日 app 日誌的「ASR 引擎觀測」行（鍵名見 §2.3）；
# structured_<日期>.jsonl 亦會收到同一行訊息（同一筆 loguru INFO 記錄）
grep "ASR 引擎觀測" "data/logs/app_$(date +%F).log" | tail -5
# API 沒有 JSON metadata 端點：model_info（backend/models/schemas.py:67）從未被賦值
# 逐字稿＝GET /api/tasks/<TASK_ID>/transcript（text/plain）
# 會議紀錄檔案下載＝GET /api/tasks/<TASK_ID>/result（僅 md/docx）
```

驗收參考：≥27 分鐘 MP3 應為 `conversion_reason=fragile_native_container`、
`helper_invocations=1`，且端到端成功。

## 7. 常見問題

**Q1：macOS < 26（例如 macOS 14/15）**
Apple 引擎不可用，helper 會誠實回報 `APPLE_UNAVAILABLE`（離場碼 2）。
`auto` 與 `apple` 都直接失敗（fail-closed，不 fallback）；Mac 沒有其他引擎可退。
處理：升級 macOS 26+。

**Q2：Intel Mac**
不支援 Apple 引擎（Apple SpeechAnalyzer 為 darwin+arm64 限定）。`auto` 走非 Apple
平台既有解析、不會解析到 `apple`；明確指定 `apple` 會得到平台拒絕訊息。

**Q3：Asset（語音模型）未安裝**
`probe` 不會安裝模型；`transcribe` 首次遇到未安裝的 locale 會嘗試下載（需要網路）。
下載中會顯示進度，逾時回離場碼 1，安裝失敗回 4。
處理：保持網路連線、先跑 `probe --locale <id>` 確認 `asset_status`；
避免在離線環境使用未安裝的 locale。

**Q4：找不到 helper**
症狀：`auto` 與 `apple` 皆直接失敗（fail-closed；任務 failed，不會回退 MLX/Whisper）。
處理：

```bash
ls -l apple_speech_cli/.build/release/apple-speech-cli   # 產物是否存在
cd apple_speech_cli && swift build -c release            # 重新建置（需 Xcode 工具鏈）
```

或設 `APPLE_SPEECH_CLI_PATH` 指向既有執行檔；`uv run python scripts/verify_env.py`
（macOS 專屬段落）會提示目前狀態與建置指令。

**Q5：轉錄卡很久**
首次使用某 locale 需下載 asset；Apple 端逾時下限為 600 秒、長檔依音長放寬
（`max(600, 音長*3+300)`）。若超過此上限，任務會以逾時失敗並保留診斷。
處理：先 `probe` 確認 asset 狀態，避免把 Asset 下載誤判為卡死。

**Q6：如何確認 Windows 完全沒被影響**
Windows 的 `accelerator` 不會是 `apple-neural`，狀態列只會顯示 CUDA/CPU 等；
`python install_deps.py --check` 與 `python scripts/verify_env.py` 的輸出不含
Xcode / Swift / Apple / helper 字樣。此為自動化測試守衛（見 `tests/`）。

## 8. 相關文件

- [Apple Speech CLI 建置與驗證手冊](apple-speech-cli-build.md)：Swift 建置、契約、實測記錄
- [Apple SpeechAnalyzer 移植開發上下文](apple-speech-analyzer-porting-context.md)：設計與地雷
- [README 快速開始](../README.md)：安裝、環境變數與引擎設定
- `.env.example`：`APPLE_*` 設定範例（僅 macOS 生效）
