# Apple SpeechAnalyzer ASR 移植開發上下文

> 來源專案：`yt_down_txt`，提交 `ce7abe6` + `2de061d`
> 目標：把同一套本機 `SpeechAnalyzer` 轉錄能力帶到會議記錄專案
> 平台限定：`macOS 26+` + `Apple Silicon`，`Python >=3.12,<3.13`，需 `ffmpeg`

## 1. 架構總覽

最小可移植單位是兩層：

```text
會議音檔(mp3/wav/m4a)
  -> Python facade(media_toolbox/asr/pipeline.py + apple.py + apple_cli.py)
  -> Swift helper(apple_speech_cli，本機建置，不提交 binary)
  -> schema 1.0 JSON(stdout) + 診斷(stderr)
  -> Python 驗證 + CJK 正規化 + 原子寫 .md
```

- Swift 只做辨識，不寫檔。
- Python 只做路由、前處理、驗證、寫檔，不做推論。
- `contract.py` 是唯一凍結介面，`dispatcher.py` 是唯一路由擁有者。

關鍵檔案：

- `apple_speech_cli/Sources/AppleSpeechKit/TranscriptionService.swift`
- `apple_speech_cli/Sources/AppleSpeechKit/SpeechRuntime.swift`
- `apple_speech_cli/Sources/AppleSpeechKit/Runner.swift`
- `apple_speech_cli/Sources/AppleSpeechKit/OutputGuard.swift`
- `apple_speech_cli/Sources/AppleSpeechKit/SchemaPayload.swift`
- `apple_speech_cli/Sources/AppleSpeechKit/Errors.swift`
- `apple_speech_cli/Sources/apple-speech-cli/AppleSpeechCLI.swift`
- `apple_speech_cli/Package.swift`
- `media_toolbox/asr/contract.py`
- `media_toolbox/asr/dispatcher.py`
- `media_toolbox/asr/apple.py`
- `media_toolbox/asr/apple_cli.py`
- `media_toolbox/asr/pipeline.py`
- `media_toolbox/asr/transcript_utils.py`

## 2. Swift 核心邏輯

### 2.1 為何要獨立 helper

`SpeechTranscriber` / `SpeechAnalyzer` 只有 Swift API，沒有 Python 綁定。專案選擇 `SwiftPM` 做一個無簽名、無 `Info.plist` 的裸 `executable`，Python 用 `subprocess` 呼叫，避免 `mlx` / `torch` / `silero` 污染 Apple 路徑。

`apple_speech_cli/Package.swift` 重點：

```swift
platforms: [.macOS(.v14)]
```

- 部署目標刻意設 `14`，弱連結 `Speech`，舊系統啟動後回 `APPLE_UNAVAILABLE`，而非載入失敗。

### 2.2 辨識主流程

`apple_speech_cli/Sources/AppleSpeechKit/TranscriptionService.swift`：

```swift
guard HostInfo.isAppleSilicon else {
  throw AppleSpeechError(code: .unavailable, message: "requires Apple Silicon")
}
guard #available(macOS 26.0, *) else {
  throw AppleSpeechError(code: .unavailable, message: "requires macOS 26+")
}
let report = try await SpeechRuntime.localeReport(for: options.locale)
guard report.isSupported, let resolvedIdentifier = report.resolvedIdentifier else {
  throw AppleSpeechError(code: .localeUnsupported, message: "no locale equivalent")
}
let transcriber = SpeechTranscriber(
  locale: Locale(identifier: resolvedIdentifier),
  preset: SpeechRuntime.preset(named: options.preset)
)
let analyzer = SpeechAnalyzer(modules: [transcriber])
await control.attach { await analyzer.cancelAndFinishNow() }
try await AssetInstallFlow.ensureReady(statusBefore: report.assetStatus, ...)
let audioFile = try AVAudioFile(forReading: input)
// 餵入 analyzer，最後只收 final results
```

移植要點：

- 先 `localeReport`，再 `AssetInstallFlow.ensureReady`，再開檔。
- 預設 `preset` 用 `time-indexed`，才有逐詞時間軸。會議建議 `time-indexed`。
- 只收 `isFinal == true`，`volatile` 只計數不入稿。`TranscriptionCollector.snapshot` 最後依 `start` 排序。
- `attributedPieces` 優先用 `TimeRangeAttribute` 切 run，拿不到才退回整個 `CMTimeRange`。

### 2.3 雙命令契約

- `probe [--locale] [--debug]`：不裝模型、不保留額度，只回報可用性。
- `transcribe --input <path> [--locale] [--timeout] [--debug]`：會觸發 `AssetInventory` 自動安裝。

`Runner.swift` 保證 `stdout` 只有一份 JSON，`stderr` 全是診斷。`OutputGuard.writeOnce` 用 `NSLock` 擋 `watchdog` 與正常完成的競態。

### 2.4 錯誤與離場碼

`apple_speech_cli/Sources/AppleSpeechKit/Errors.swift`：

```text
0 成功
2 APPLE_UNAVAILABLE
3 APPLE_LOCALE_UNSUPPORTED
4 APPLE_ASSET_ERROR
5 APPLE_INPUT_ERROR
6 APPLE_TRANSCRIPTION_ERROR
7 APPLE_CANCELLED
1 通用，子型別看 JSON(APPLE_TIMEOUT / APPLE_OUTPUT_INVALID 共用此碼)
```

- 絕不自動釋放其他 `locale` 的保留額度。
- `SIGTERM` / `SIGINT` 轉協作式取消，5 秒寬限後強制結束，回 `APPLE_CANCELLED`。

## 3. Python 橋接核心邏輯

### 3.1 契約層

`media_toolbox/asr/contract.py`：

```python
EngineName = Literal["auto", "apple", "breeze", "mlx"]
AUTO_FALLBACK_ORDER = ("apple", "breeze", "mlx")
TAIGI_FALLBACK_ORDER = ("breeze", "mlx")
DEFAULT_ENGINE = "auto"
```

- `ASRSegment(start, end, text)` 時間可為 `None`，文字非空即有效。
- `metadata` 只放純量，不放逐字稿與原始 payload。
- `import contract` 不得拉入 `mlx_whisper` / `torch` / `silero`。

### 3.2 路由層

`media_toolbox/asr/dispatcher.py` 的凍結規則：

```python
def resolve_engine_chain(requested_engine, *, taigi=False):
    if requested_engine == "apple":
        return ("apple",)  # fail-closed，零 fallback
    if requested_engine == "breeze":
        return ("breeze",)
    if requested_engine == "mlx":
        return ("mlx",)
    return ("breeze", "mlx") if taigi else ("apple", "breeze", "mlx")
```

- 只有 `auto` 會 fallback。
- `APPLE_CANCELLED` 永不 fallback，取消優先於逾時。
- Apple 嘗試一律用 `use_vad=False` 的新 `ASRRequest`，不改傳入的 frozen 物件。
- 會議專案若無台語需求，可簡化為 `auto -> (apple, whisper)`，但保留 `explicit apple fail-closed` 語意。

### 3.3 超時公式

```python
TIMEOUT_FLOOR_SECONDS = 600.0
def resolved_timeout_seconds(duration):
    return max(600.0, duration * 3.0 + 300.0)
```

- `duration` 來自 `ffprobe`，失敗就用 600 秒下限，絕不因此失敗。
- 會議動輒 1~2 小時，此公式比固定超時重要。

### 3.4 Helper 探索與執行

`media_toolbox/asr/apple_cli.py`：

```python
def resolve_executable(configured=None, repo_root=None, which=None):
    # configured -> repo release 產物 -> PATH
```

- 設定值無效只記 `configured_rejected`，繼續往後找。
- 找不到就回明確建置指令，不自動編譯。

`SubprocessRunner.run`：

- `stdout` / `stderr` 獨立執行緒排空，避免 pipe 滿載卡死。
- 取消與逾時走 `terminate() -> 5s grace -> kill()`，返回前回收子行程。
- 預設擷取上限 `stdout 8_000_000` 字元，長會議 JSON 很大，不要設太小。

### 3.5 嚴格 schema 驗證

`media_toolbox/asr/apple_cli.py:validate_transcription_payload`：

- 檢查 `schema_version`、`engine`、`text`、`segments`、`metadata`。
- `start` / `end` 只接受數字或 `null`，`end < start` 就把 `end` 降級為 `None` 並計數。
- 空白正規化後為空的 segment 直接丟棄並計 `segments_dropped`。
- 任何違反丟 `APPLE_OUTPUT_INVALID`，可參與 `auto` fallback。

### 3.6 CJK 空白正規化

`media_toolbox/asr/apple_cli.py:normalize_apple_text`，Apple 邊界專用：

```python
_CJK_TEXT_CLASS = "\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_WHITESPACE_RUN_RE = re.compile(r"\s+")
_SPACE_BETWEEN_CJK_RE = re.compile(rf"(?<=[{_CJK_TEXT_CLASS}])[\s]+(?=[{_CJK_TEXT_CLASS}])")

def normalize_apple_text(text: str) -> str:
    normalized = _WHITESPACE_RUN_RE.sub(" ", text)
    normalized = _SPACE_BETWEEN_CJK_RE.sub("", normalized)
    normalized = _SPACE_BEFORE_CJK_MARK_RE.sub("", normalized)
    normalized = _SPACE_AFTER_CJK_MARK_RE.sub("", normalized)
    return normalized.strip()
```

- 例：`今天天氣很好 ，我們一起去公園散步` 變成 `今天天氣很好，我們一起去公園散步`。
- 會議專案直接複用此函式，不要動共用 normalizer。

### 3.7 轉檔邊界，這是效能關鍵

`media_toolbox/asr/apple.py` 實測結論：

- `transcriber.availableCompatibleAudioFormats` 只有 `16000 Hz` 與 `8000 Hz` 單聲道。
- 舊寫法轉 `AAC 192k / 44.1kHz / 立體聲`，framework 還要重取樣，27.7 分鐘檔轉檔 28.6 秒，辨識才 10.6 秒。
- 新寫法直接輸出 Apple 要的格式：

```python
CONVERSION_SUFFIX = ".wav"
CONVERSION_ARGS = ("-vn", "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1")
NATIVE_INPUT_SUFFIXES = frozenset({".m4a", ".mp4", ".wav", ".aif", ".aiff", ".caf", ".mp3"})
PREFLIGHT_CONVERSION_SUFFIXES = frozenset({".mp3"})
```

```python
def preflight_conversion_reason(input_suffix: str) -> str | None:
    if input_suffix not in NATIVE_INPUT_SUFFIXES:
        return "non_native_container"
    if input_suffix in PREFLIGHT_CONVERSION_SUFFIXES:
        return "fragile_native_container"
    return None
```

- `27.7` 分鐘 `MP3` 原生讀取穩定失敗，`MP3` 一律先轉，不賭原生嘗試。
- 成果：轉檔 `28.6s -> 0.88s`，端到端 `48.4s -> 11.3s`，比 `MLX Whisper large-v3-turbo` 快約 4.9 倍。（此為來源專案 yt_down_txt 之實測數據，未於本 repo 複驗；本 repo 的實測數字見 e2e attempt-03）
- 轉 `WAV` 與 `AAC` 輸出逐字相同，證明二次有損壓縮不是品質因素，選 `WAV` 純為速度與免重取樣。

暫存檔安全：

```python
# .<stem>.<12 hex>.apple.wav
STALE_TEMP_NAME_PATTERN = re.compile(r"^\..+\.[0-9a-f]{12}\.apple\.(?:wav|m4a)$")
```

- 正常結束 `finally` 刪除，被硬殺才靠 `sweep_stale_apple_temp_files` 清超過 24 小時者。
- 只認精確樣式，只刪單層一般檔案，不跟隨連結，不遞迴。

### 3.8 原子寫檔

`media_toolbox/asr/transcript_utils.py:write_text_atomic`：

```python
def write_text_atomic(path, content, *, encoding="utf-8") -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, staged = _open_staging_file(target)
    with os.fdopen(descriptor, "w", encoding=encoding) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(staged, target)
    _fsync_directory(target.parent)
    return target
```

- 會議逐字稿很長，中斷不可留半寫檔，此函式直接複用。

## 4. 已驗證的地雷

- `AnalysisContext.contextualStrings` 在 `SpeechTranscriber` 是 no-op，熱詞實測逐位元相同，不要投入工時。
- Apple 繁中辭典對現代詞覆蓋極低，`台積電`、`輝達`、`光通訊` 都缺，辭典校正無鑑別力。
- 通用錯字表對 ASR 有害，50 組只有 4 組安全，其餘兩邊都是合法詞。
- 長 `MP3` 原生不可靠，`3/15/25` 分鐘可讀，`27.7` 分鐘起穩定失敗。
- `probe` 不裝模型，`transcribe` 才裝，`auto` 流程應先 `probe` 再決定是否換手。

## 5. 移植到會議專案的最小清單

- 複製 `apple_speech_cli/` 整包，`swift build -c release` 產出 `apple-speech-cli`。
- 複製 `media_toolbox/asr/apple_cli.py` 的 `resolve_executable`、`SubprocessRunner`、`normalize_apple_text`、`validate_transcription_payload`、`parse_progress_line`。
- 複製 `media_toolbox/asr/apple.py` 的 `PREFLIGHT_CONVERSION_SUFFIXES`、`CONVERSION_ARGS`、`_temp_target`、`_convert`、重試一次邏輯。
- 複製 `resolved_timeout_seconds` 與 `write_text_atomic`。
- 簡化路由：

```python
chain = ("apple", "whisper") if requested == "auto" else (requested,)
```

- 會議欄位建議 `metadata`：
  - `requested_engine`、`resolved_engine`、`engine_chain`
  - `locale`、`audio_duration_seconds`、`elapsed_seconds`、`real_time_factor`
  - `helper_invocations`、`conversion_reason`、`conversion_seconds`
  - `segment_count`、`segments_dropped`、`segments_time_degraded`
- 會議若要說話人區分，Apple 本階段不做 `diarization`，需另起模組，不要塞進 ASR provider。

## 6. 驗證建議

- `swift test` 全綠。
- 短中文 `probe` + `transcribe`，確認 `.md` 標點無多餘空白。
- `27` 分鐘以上 `MP3`，確認 `helper_invocations=1`、`conversion_reason=fragile_native_container`。
- 拔掉 helper，確認 `auto` fallback 可觀察，`explicit apple` fail-closed。
- `SIGTERM` 取消，確認回 `APPLE_CANCELLED` 且無殘留暫存。
