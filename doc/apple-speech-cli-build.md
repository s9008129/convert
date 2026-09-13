# Apple Speech CLI 建置與驗證手冊（`apple_speech_cli/`）

> 本文由 WAVE-02 於真實機器實測撰寫：macOS 26.6.2（build 25G83）、arm64（Apple M4 Pro）、Xcode 26.6、Swift 6.3.3。
> 對應程式碼位於 repo 根目錄的 `apple_speech_cli/`（SwiftPM 套件，移植自 `yt_down_txt/apple_speech_cli`，未改任何 Swift 原始碼）。

## 概述

`apple_speech_cli` 是一支無簽章、無 Info.plist、無 App bundle 的 SwiftPM executable，直接使用 macOS 26 的 `SpeechAnalyzer` / `SpeechTranscriber` API 對本地音訊檔做語音辨識。

- 對外契約：stdout **有且僅有一份** schema 1.0 JSON；所有診斷訊息一律走 stderr。
- 兩個子命令：
  - `probe`：只回報 locale/模型可用性，**不會**安裝模型（asset）。
  - `transcribe --input <path>`：需要時自動確保 asset 就緒後才進行辨識。
- `Package.swift` 宣告 `platforms: [.macOS(.v14)]`，並對 `Speech.framework` 弱連結（weak link）。因此同一顆 binary 在較舊的 macOS 上仍可啟動，並誠實回報 `APPLE_UNAVAILABLE`（離場碼 2），而不是啟動時就動態連結失敗。
- binary 不進版控；`apple_speech_cli/.gitignore` 已忽略 `.build/`、`.swiftpm/`、`Package.resolved`、`*.o`。

## 需求（實測環境）

| 項目 | 需求 | 實測值 |
|---|---|---|
| 作業系統 | macOS 26 以上才能進行辨識（API 最低需求 macOS 26.0）；較舊版本可執行但回報 `APPLE_UNAVAILABLE` | macOS 26.6.2 (25G83) |
| CPU | Apple Silicon（arm64） | arm64 / Apple M4 Pro |
| 工具鏈 | Xcode（含 Swift 6.0+ 工具鏈，`swift-tools-version: 6.0`） | Xcode 26.6、Swift 6.3.3 |
| 其他（僅 smoke 測試用） | `say`（產中文語音）、`ffmpeg`/`ffprobe`（轉 16 kHz 單聲道 wav） | ffmpeg 7.0、ffprobe 7.1.1 |
| 網路 | 首次使用某 locale 且本機無對應模型時，`transcribe` 需要網路下載 asset | 本次 zh_TW 模型已存在，未觸發下載 |

## 建置

```bash
cd apple_speech_cli
swift build -c release
```

實測結果（成功）：

```
Building for production...
[6/7] Linking apple-speech-cli
Build complete! (5.43s)
```

產物路徑（實測存在）：

```
apple_speech_cli/.build/release/apple-speech-cli
```

- 大小：515,376 bytes（約 504 KiB）
- 類型：`Mach-O 64-bit executable arm64`
- 連結檢查（`otool -L`）可見 `Speech.framework ... (weak)`，符合弱連結設計。

## 執行方式

```
USAGE:
  apple-speech-cli probe      [--locale <id>] [--output-format json] [--debug]
  apple-speech-cli transcribe --input <path> [--locale <id>] [--output-format json]
                              [--timeout <seconds>] [--debug]

OPTIONS:
  --input <path>          Local audio file to transcribe.
  --locale <id>           BCP-47 locale identifier (default: zh-TW).
  --output-format <fmt>   Only 'json' is supported.
  --timeout <seconds>     Abort analysis after N seconds (0 disables, default: 0).
  --debug                 Write per-result diagnostics to stderr.
  --preset <name>         SpeechTranscriber preset for transcribe: one of time-indexed|plain|plain-alternatives|progressive|time-indexed-progressive (default: time-indexed).
```

範例（實測）：

```bash
BIN=apple_speech_cli/.build/release/apple-speech-cli
$BIN probe --locale zh-Hant-TW
$BIN transcribe --input /tmp/apple-smoke.wav --locale zh-Hant-TW
```

備註：

- 沒有 `--help`；傳入未定義的旗標會走錯誤路徑（離場碼 5，usage 會夾在錯誤 JSON 的 message 內）。
- 預設 preset 為 `time-indexed`，只收 `isFinal == true` 的結果。
- `probe --locale zh-Hant-TW` 會把請求 locale 正規化為 `zh_TW`（輸出含 `locale_requested`、`locale_resolved` 等欄位）。

## 輸出契約

- 成功時 stdout 為一行 JSON，`schema_version` 固定 `"1.0"`：

```json
{"schema_version":"1.0","engine":"apple","locale":"zh_TW","text":"...","segments":[{"start":0.0,"end":1.2,"text":"..."}],"metadata":{...}}
```

- 失敗時 stdout 仍為單一 JSON 錯誤信封，錯誤訊息一律在 stdout 的 JSON 內、診斷文字在 stderr：

```json
{"schema_version":"1.0","engine":"apple","error":{"code":"APPLE_LOCALE_UNSUPPORTED","message":"..."}}
```

- `metadata` 含 `elapsed_seconds`、`analysis_seconds`、`real_time_factor`、`asset_status_before/after`、`asset_install_attempted`、`asset_install_seconds`、`preset`、`segment_count` 等欄位（實測全文見下述 smoke 記錄）。

## 離場碼表（凍結契約）

| 離場碼 | 錯誤碼 | 意義 | 本次實測 |
|---|---|---|---|
| 0 | — | 成功 | probe、transcribe 皆實測 0 |
| 1 | `APPLE_TIMEOUT` / `APPLE_OUTPUT_INVALID` | 通用錯誤（逾時、輸出驗證失敗） | 未實測 |
| 2 | `APPLE_UNAVAILABLE` | 平台/API 不可用（例如 macOS < 26） | 未實測 |
| 3 | `APPLE_LOCALE_UNSUPPORTED` | 不支援的 locale | 實測 `--locale xx-XX` → 3 |
| 4 | `APPLE_ASSET_ERROR` | 模型（asset）安裝/狀態錯誤 | 未實測 |
| 5 | `APPLE_INPUT_ERROR` | 輸入參數/檔案錯誤 | 實測 `--input` 不存在檔案 → 5；未知旗標 → 5 |
| 6 | `APPLE_TRANSCRIPTION_ERROR` | 辨識失敗 | 未實測 |
| 7 | `APPLE_CANCELLED` | 使用者以 SIGTERM/SIGINT 取消 | 未實測 |

## 測試

```bash
cd apple_speech_cli
swift test
```

實測結果（2026-09-12 22:47）：

```
Test Suite 'AppleSpeechKitTests' passed   — Executed 19 tests, with 0 failures
Test Suite 'AssetInstallTests' passed     — Executed 33 tests, with 0 failures
Test Suite 'All tests' passed             — Executed 52 tests, with 0 failures in 0.067 seconds
```

（完整輸出已留存於 `apple_speech_cli/.build/wave02/swift-test-full.log`，`.build/` 不進版控。）

## Smoke 測試（實機實測記錄）

### 1. probe

```bash
$BIN probe --locale zh-Hant-TW > probe.out.json 2> probe.err.txt   # exit=0，約 0.4s
```

stdout（單行 JSON，節錄關鍵欄位；完整檔案留存於 `.build/wave02/probe.out.json`）：

```json
{"schema_version":"1.0","engine":"apple","command":"probe","locale_requested":"zh-Hant-TW","locale_resolved":"zh_TW","locale_supported":true,"locale_installed":true,"asset_status":"installed","transcriber_is_available":true,"supported_locales_count":30,"installed_locales_count":2,"installed_locales":["zh_CN","zh_TW"],"maximum_reserved_locales":5,...,"metadata":{"api":"SpeechAnalyzer/SpeechTranscriber","api_minimum_required":"macOS 26.0","api_available":true,"os_version":"26.6.2","arch":"arm64","is_apple_silicon":true,"hardware_model":"Mac16,8","hardware_chip":"Apple M4 Pro",...}}
```

stderr（診斷）：

```
apple-speech-cli 0.1.0 probe
probe ok: asset_status=installed resolved=zh_TW
```

### 2. 產生中文語音並轉檔

```bash
say -v Meijia -o /tmp/apple-smoke.aiff "今天天氣很好，我們下午一起去公園散步，順便買一杯珍珠奶茶。"
# → /tmp/apple-smoke.aiff, 6.56s
ffmpeg -y -i /tmp/apple-smoke.aiff -ar 16000 -ac 1 /tmp/apple-smoke.wav
# → /tmp/apple-smoke.wav, pcm_s16le, 16000 Hz, mono, 209,892 bytes
```

### 3. transcribe

```bash
$BIN transcribe --input /tmp/apple-smoke.wav --locale zh-Hant-TW > transcribe.out.json 2> transcribe.err.txt
# exit=0，wall time 約 0.18s
```

stderr（診斷）：

```
apple-speech-cli 0.1.0 transcribe
resolved locale 'zh-Hant-TW' -> 'zh_TW'
asset status before: installed; installed locales: ["zh_TW", "zh_CN"]
audio: 16000.0 Hz, 1 ch, 104907 frames, duration=6.5566875s
transcribe ok: 31 chars, 8 segments, 8 final results
```

stdout（單行 JSON）關鍵結果：

- `schema_version`: `"1.0"`（正確）
- `text`: `今天天氣很好 ，我們下午一起去公園散步 ，順便買一盃珍珠奶茶。`（非空，31 字元；「盃」為語音辨識原始輸出，未經人為修正）
- `segments`: 8 段（`segment_source: "result"`、preset `time-indexed`）
- `metadata.elapsed_seconds`: 0.172；`analysis_seconds`: 0.119；`real_time_factor`: 0.018
- `asset_status_before/after`: `installed` / `installed`；`asset_install_attempted`: `false`（模型已存在，未觸發下載）

### 4. stdout/stderr 分離驗證

```bash
python3 -c "import json; d=json.load(open('probe.out.json')); print(d['schema_version'])"
python3 -c "import json; d=json.load(open('transcribe.out.json')); print(len(d['segments']), bool(d['text'].strip()))"
```

兩個檔案皆可被 `python3 json.load` 解析，且皆為「單行」JSON（`splitlines()` 長度 = 1），確認 stdout 未被 stderr 診斷污染。錯誤路徑（`err_input.out.json`、`err_locale.out.json`）亦同樣可解析。

## 常見錯誤

| 症狀 | 原因 | 處理 |
|---|---|---|
| 離場碼 5，message 含 `input file does not exist` | `--input` 路徑不存在（實測） | 確認音檔路徑；先以 `ffprobe` 驗證檔可讀 |
| 離場碼 5，message 含 `unknown flag '--help'` | 本 CLI 沒有 `--help`（實測） | 直接照本文件 usage 傳參 |
| 離場碼 3，`APPLE_LOCALE_UNSUPPORTED` | 要求的 locale 不在支援清單（實測 `xx-XX`） | 先跑 `probe --locale <id>` 確認支援與已安裝狀態 |
| 離場碼 2，`APPLE_UNAVAILABLE` | 主機 macOS < 26 或 API 不可用 | 升級 macOS；此情境 binary 可啟動並誠實回報 |
| 首次 `transcribe` 很慢或失敗 | 本機沒有該 locale 的模型，需網路下載 asset；下載進度與狀態走 stderr，逾時/失敗會回報 `APPLE_ASSET_ERROR`(4) 或 `APPLE_TIMEOUT`(1) | 保持網路連線並耐心等待；必要時先用 `probe` 檢查 `asset_status` |
| 想除錯逐段結果 | — | 加 `--debug`；每筆結果診斷會寫到 stderr（實測 stdout 仍為單一乾淨 JSON） |
| 以 pipeline 消費 stdout 時 JSON 解析失敗 | 把 stderr 混入 stdout 了 | 使用 `2>err.txt` 或 `2>/dev/null` 分離 |

## 附註（本次實測範圍）

- 本機 zh_TW（及 zh_CN）模型已存在，因此本次 smoke **未觸發**首次下載；`transcribe` 輸出中 `asset_install_attempted=false`、`asset_install_seconds=null` 可佐證。於乾淨機器首次使用新 locale 時，預期需下載並耗費數分鐘（視網路而定），該路徑本次未實測。
- 已實測離場碼：0（probe/transcribe success）、3（bad locale）、5（missing input、unknown flag）。其餘碼別依凍結契約與原始碼（`Sources/AppleSpeechKit/Errors.swift`）記載，未逐一實測。
- 本次移植與母本（`yt_down_txt/apple_speech_cli`，HEAD 3465726）逐檔 SHA-256 比對全數一致，未修改任何 Swift 原始碼。
- 版控注意（2026-09-13 更新）：convert repo 根目錄 `.gitignore` 雖含 `.gitignore` 規則（Git 段），
  `apple_speech_cli/.gitignore` 已於 T20260912-2242-01 以 `git add -f` 納入版控（`git ls-files` 可查），
  且根目錄 `.gitignore` 另補了 `apple_speech_cli/.build/` 與 `apple_speech_cli/apple-speech-cli` 兩條明確規則；
  因此不論 clone 或本機（實測 `git status --ignored` 顯示 `!! apple_speech_cli/.build/`），binary 都不會被誤提交。
