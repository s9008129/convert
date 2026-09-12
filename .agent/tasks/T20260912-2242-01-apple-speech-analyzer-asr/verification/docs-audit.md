# 文件 ↔ 程式碼一致性稽核報告（T20260912-2242-01-apple-speech-analyzer-asr）

- **任務**：T20260912-2242-01-apple-speech-analyzer-asr（Stage 04 / PLAN_REVISION 1）
- **稽核角色**：獨立文件稽核者（對產品碼 read-only；本報告未修改任何產品碼、既有測試或被稽核文件）
- **稽核時間**：2026-09-12 23:37–23:42 CST（Asia/Taipei）
- **稽核環境**：`/Users/hsiaojohnny/dev/convert`（branch `main`；工作樹含本任務與平行 agent 之未提交變更；所有實測以稽核當下狀態為準，另見 §七）
- **稽核方式**：靜態逐行比對權威碼 ＋ 本機實跑（真 helper 二進位、真子程序、settings override、FastAPI TestClient health 探測、實際日誌 grep）
- **判定用語**：`PASS`＝文件敘述與程式碼一致；`MISMATCH`＝文件敘述可一行重現為錯；`UNVERIFIABLE`＝於本 repo／本任務內找不到依據可證實

## 一、稽核範圍

### 被稽核文件（本任務新增／修改段落）

| 檔案 | 段落 |
|---|---|
| `doc/apple-speech-analyzer-operations.md` | 全文（本任務新增） |
| `doc/apple-speech-cli-build.md` | 全文（本任務新增） |
| `README.md` | 本任務 git diff 新增行（Apple 段落，含 :126、:369–:370、:376、:426 等） |
| `CHANGELOG.md` | `[Unreleased]` Apple 段落（:1–:34） |
| `.env.example` | :54–:63（Apple 段落） |
| `config.macos.yaml` | :24–:38（`whisper.apple` 參考段） |

### 對照權威（程式碼）

`backend/core/config.py:357–372`、`backend/core/platform_config.py`、`backend/core/asr_model_resolver.py`、`backend/services/asr_apple/*.py`、`backend/api/routes.py`、`backend/services/transcription.py`、`scripts/verify_env.py`、`install_deps.py`、`scripts/download_models.py`；輔助落地點：`backend/core/logger.py`、`backend/services/asr_subprocess.py`；Swift 契約：`apple_speech_cli/Sources/AppleSpeechKit/{CLIArgumentParser,Errors,Runner}.swift`。

## 二、逐項判定表

（# 1–8 對應任務指定稽核項；# 9–10 為稽核中另行發現）

| # | 稽核項 | 判定 | 證據（檔案:行號／實測） |
|---|---|---|---|
| 1 | env 變數名稱、預設值（`APPLE_LOCALE=zh-Hant-TW`、`APPLE_PRESET=time-indexed`、`APPLE_ENABLE_PREFLIGHT=true`、`APPLE_SPEECH_CLI_PATH=""`） | **PASS** | `backend/core/config.py:357–360`（`APPLE_SPEECH_CLI_PATH=""`）、`:361–364`（`zh-Hant-TW`）、`:365–368`（`time-indexed`）、`:369–372`（`True`）；文件：`doc/apple-speech-analyzer-operations.md:89–91`、`README.md:369–370`、`.env.example:59–62`。實測 override `APPLE_LOCALE=ja-JP APPLE_PRESET=plain APPLE_ENABLE_PREFLIGHT=false` → settings 正確反映。（`APPLE_PRESET` 可選值集合未記載＝缺漏 G1，非錯述） |
| 2 | helper 離場碼對照表（0/1/2/3/4/5/6/7 → 錯誤碼字串） | **PASS** | `backend/services/asr_apple/contract.py:66–74` 逐條 = `operations:116–123` = build doc 離場碼表；Swift 端 `Errors.swift:47–61`（`.timeout/.outputInvalid→1`、`.cancelled→7`）一致。實測：`probe --locale xx-XX`→3、`--input` 不存在→5、bogus preset→5、`--help`→5、SIGINT 取消→7＋`APPLE_CANCELLED`。 |
| 3 | `--preset` 可選值、`--timeout` 語意 | **PASS**（含缺漏 G1） | `apple_speech_cli/Sources/AppleSpeechKit/CLIArgumentParser.swift:103–123`（`--timeout` 非負數、0=disable；`--preset` 允許 `time-indexed｜plain｜plain-alternatives｜progressive｜time-indexed-progressive`）；`Runner.swift:77–81`（僅 >0 啟動 watchdog）；Python 端 `apple_cli.py:134–151` 逾時公式 `max(600, 音長*3+300)`、`:706–740` `build_transcribe_argv` 一律帶 `--timeout <值>`，與 `operations:117` 公式一致。`--preset` 未列於 build doc usage（`doc/apple-speech-cli-build.md:53–61`；helper 自身 usage 亦未列，屬文件沿襲缺漏）。 |
| 4 | 回滾 `ASR_BACKEND=mlx_whisper` 是否真能回滾 | **PASS** | `backend/core/asr_model_resolver.py`（`infer_asr_backend`／`resolve_engine_chain`）＋`backend/services/asr_apple/dispatcher.py:22–52`。實測：`mlx_whisper`→`('mlx_whisper',)`；Darwin/arm64 `auto`→`apple`／`('apple','mlx_whisper')`；顯式 `apple`→`('apple',)`；非 Mac 模擬 `auto`→`('transformers',)`；非 Mac 顯式 `apple`→`ValueError`（僅 macOS 訊息）。TestClient 實測 `ASR_BACKEND=mlx_whisper` 之 `/health`：`device_info.asr_backend=mlx_whisper`、`accelerator=mlx-metal`。`operations:96–110` 回滾敘述成立。 |
| 5 | `helper_invocations`／`conversion_reason` 觀測方式（實測 grep 位置） | **MISMATCH** | 文件指示 `grep ... data/logs/app.log`（`operations:62`、`:139`）＝**該檔不存在**（實際 sink 為 `app_{time:YYYY-MM-DD}.log`，`backend/core/logger.py:47–48`）；文件指示 `curl /api/tasks/<TASK_ID>/result`（`operations:141`）＝**非 JSON**（`backend/api/routes.py:319–372` 僅回傳 md/docx 檔下載），且 `TranscriptionResult.model_info`（`backend/models/schemas.py:67`）全 backend 未被賦值。實測真 helper 短音檔（`say`＋`ffmpeg` 5s 中文 wav/mp3 經 `transcribe_isolated_detailed`）：metadata 13 鍵含 `helper_invocations:1`、`conversion_reason:null`（wav）／`fragile_native_container`（mp3）；**唯一可見位置**＝`data/logs/app_2026-09-12.log:11,21` 的 `ASR 引擎觀測：{...}` 行（由 `backend/services/asr_subprocess.py:188` 寫出），`data/logs/structured_2026-09-12.jsonl` 亦可見。另 `apple.py:616` stdlib `LOGGER.info("apple transcribe ok ...")` 不進任何 loguru sink（全 `data/logs` 無命中）。`conversion_reason` 值域定義本身（`apple.py:127–137`：`.mp3` fragile、原生容器無鍵）與 `operations:133–134` 一致。 |
| 6 | `/health` `apple_helper` 欄位語意（含 `quick=true`） | **MISMATCH** | 實作 `backend/api/routes.py:63–121`：非 Darwin→`supported:false`；`quick=true`→不執行 probe（`supported:true, available:false, path:null, probe:null, reason:"quick 模式：未執行 helper probe"`，:81–87）；完整模式真 probe（實測 `available:true`、`path=apple_speech_cli/.build/release/apple-speech-cli`）。**`effective_asr_backend` 不在 `/health`**（實測頂層鍵無此欄；僅存在 `/api/config`，`routes.py:533`），故 `operations:36`、`operations:104`、`README.md:426` 之指示無效；`device_info.asr_backend`／`device_info.accelerator=apple-neural` 實測存在（`routes.py:149`）。`quick=true` 語意未文件化＝缺漏 G3。 |
| 7 | 效能宣稱約 4.9× | **UNVERIFIABLE** | `README.md:126`、`:376`、`CHANGELOG.md:8`。repo 內唯一來源為 `doc/apple-speech-analyzer-porting-context.md:232`（外部來源專案 27.7min MP3 48.4s→11.3s）。**本 repo／本任務內無端到端實測佐證**（本任務 e2e `attempt-03` 為 1658.958s 音檔、elapsed 9.9s、RTF 0.006，量級相近但非同一宣稱，且 `summary_failed=true`；`e2e/comparison-0903` 稽核時仍在跑未完）。文件已標「來源專案實測」，屬引用外部數據，但作為本 repo README 效能指標仍無本 repo 依據。 |
| 8 | Windows 相關敘述是否洩漏 Apple | **PASS** | `install_deps.py:41–47`（非 darwin→`apple_helper_hint` 回 `None`；實測 Windows/Linux 皆 None）；`scripts/verify_env.py` `check_apple_native_environment` 非 macOS 回 `None`、`is_apple_silicon_mac` 僅 Darwin+arm64（有測試覆蓋，含「非 macOS 不輸出 Apple 字樣」）。文件面：`operations:3–7`、`README.md` Apple 需求以 macOS 26+ blockquote 標注、`CHANGELOG.md:9–10` 均為「不受影響／零 Apple」語境；build doc 屬 Mac 專章，範圍合理。 |
| 9 | （另行發現）§2.3 `locale` 語意 | **MISMATCH** | `operations:54` 稱「實際協商後的 Apple locale（例如 `zh_TW`）」；實作 `backend/services/asr_apple/apple.py:604` 寫入 `"locale": str(locale)`＝**requested** locale（實測 metadata `locale=zh-Hant-TW`）；helper 協商後 `zh_TW` 未進 metadata；`backend/services/transcription.py:698` 之 `language` 亦為 `settings.APPLE_LOCALE`。 |
| 10 | （另行發現）§2.3 `engine_chain` 語意 | **MISMATCH**（敘述與實作不符，影響輕微） | `operations:53` 稱「本次 fallback 鏈」；實作 `backend/services/transcription.py:701` `",".join(chain)` 為**靜態解析鏈**（實測 `apple,mlx_whisper`），非「實際走過的 fallback 紀錄」。`requested_engine`（`transcription.py:699` `normalize_engine_name(settings.ASR_BACKEND)`，`auto` 時即 `"auto"`）與 `resolved_engine="apple"` 對照語意成立。 |

## 三、發現的不一致清單（每項含建議最小修正一行）

1. **M1 — `app.log` 路徑不存在（觀測指示失效）**：`doc/apple-speech-analyzer-operations.md:62`、`:139` 指示 `grep ... data/logs/app.log`，實測該檔不存在。
   最小修正：改為 `grep ... data/logs/app_$(date +%F).log`（或 `data/logs/app_*.log`）。
2. **M2 — `/api/tasks/<TASK_ID>/result` 取不到 metadata**：`operations:135–142` 指示以該端點取得 `model_info`，實測端點僅回 md/docx 檔下載（`routes.py:319–372`），且 `model_info` 從未被賦值（`schemas.py:67`）。
   最小修正：刪除該 `curl` 段，改寫為「metadata 僅落地於 `data/logs/app_<日期>.log` 的 `ASR 引擎觀測` 行（`structured_<日期>.jsonl` 同樣可見）；API 無 JSON metadata 端點」。
3. **M3 — `effective_asr_backend` 指示無效**：`operations:36`、`:104`、`README.md:426` 要使用者檢查 `/health` 的 `effective_asr_backend`，實測該欄不在 `/health`，僅在 `/api/config`（`routes.py:533`）。
   最小修正：改為檢查 `device_info.asr_backend`（或明確指向 `/api/config` 的 `effective_asr_backend`）。
4. **M4 — `locale` 語意錯述**：`operations:54` 稱 metadata `locale` 為「實際協商後」（例 `zh_TW`），實為 requested（`zh-Hant-TW`；`apple.py:604`）。
   最小修正：改為「請求的 Apple locale（如 `zh-Hant-TW`）；協商後值見 helper payload／日誌」。
5. **M5 — `engine_chain` 語意錯述（輕微）**：`operations:53` 稱「本次 fallback 鏈」，實為靜態解析鏈（`transcription.py:701`）。
   最小修正：改為「本次解析出的引擎嘗試鏈」。
6. **G1（文件缺漏，非錯述）— `APPLE_PRESET`／`--preset` 可選值未記載**：`operations:89–91`、`doc/apple-speech-cli-build.md:53–61`。
   最小修正：建置文件 usage 補一行 `--preset <time-indexed|plain|plain-alternatives|progressive|time-indexed-progressive>`（預設 `time-indexed`）。
7. **G2（可選補強）— helper `--timeout` 來源未說明**：`operations:117` 已載逾時公式，未說 helper `--timeout` 由 Python 端計算帶入。
   最小修正：補一句「helper `--timeout` 由 Python 端以 `max(600, 音長*3+300)` 計算後帶入（`apple_cli.py:134–151,706–740`）」。
8. **G3（文件缺漏）— `/health?quick=true` 語意未記載**：`operations:36` 附近。
   最小修正：補一行「`quick=true` 時不執行 helper probe，僅回報平台支援度（`reason` 為『quick 模式：未執行 helper probe』）」。

## 四、UNVERIFIABLE 清單

1. **4.9×／27.7 分鐘 → 約 11 秒（`README.md:126`、`:376`、`CHANGELOG.md:8`）**：本 repo 無本任務內實測依據；唯一來源為 `doc/apple-speech-analyzer-porting-context.md:232` 之外部來源專案數據。
   建議：改引本任務可用實測（e2e `attempt-03`：1658.958s 音檔、`elapsed_seconds=9.9`、RTF 0.006），或明確標註「外部來源引用，未於本 repo 複驗」。
2. （附帶提醒）`README.md:440` 既有 `cat data/logs/app.log` 同為不存在路徑——經 `git show HEAD:README.md` 確認為**本任務前即存在**（HEAD:409），不在本次稽核範圍，但可一併修正為日期檔名。

## 五、「無發現」結論（明確聲明）

除上述 **M1–M5** 與 **G1–G3**（缺漏／補強）及 UNVERIFIABLE 之 4.9× 宣稱外，本次逐項核對之其餘文件敘述與程式碼一致，**未發現其他不一致**：

- env 名稱／預設值（4 個 `APPLE_*`）逐條一致，override 實測反映正確。
- 離場碼表 8 條（0–7）與 `APPLE_EXIT_CODE_TO_ERROR_CODE` 及 Swift `exitCode` 逐條一致，且有實際觸發實測。
- `--timeout` 語意（非負、0=disable、Python 端公式並一定帶入）一致；`--preset` 缺漏已列 G1。
- 回滾與引擎鏈語意（`auto`／`mlx_whisper`／`apple`，含非 Mac 拒絕）與實作一致。
- metadata 13 鍵名（`backend/services/asr_apple/apple.py:601–611`）與 `operations:52–57` 表格一致；ASR 快取簽名含 backend（`file_manager.py` `get_asr_cache_signature`→`build_asr_cache_signature(...backend...)`）。
- `config.macos.yaml` 已自述「後端只讀環境變數／`.env`，此檔僅供舊版 CLI 與文件參考」（:2–3、:32–34），與實作相符（`config.py` 讀 `.env`）。
- Windows／Linux 之「零 Apple」保證（`install_deps.py`、`verify_env.py`、前端顯示）與文件敘述一致。

## 六、重現指令摘要（節錄）

```bash
# 1) env 預設值與 override
# （.venv/bin/python 3.12；跑 backend 模組需 DATA_DIR/PYTHONPATH）
APPLE_LOCALE=ja-JP APPLE_PRESET=plain APPLE_ENABLE_PREFLIGHT=false \
  DATA_DIR="$PWD/data" PYTHONPATH="$PWD" .venv/bin/python -c \
  "from backend.core.config import settings; print(settings.APPLE_LOCALE, settings.APPLE_PRESET, settings.APPLE_ENABLE_PREFLIGHT)"

# 2) 觀測位置實測（真 helper；約 5 秒中文音檔）
say -v Meijia -o /tmp/docs-audit/audit.aiff "今天天氣很好，我們來測試語音辨識系統"
ffmpeg -y -i /tmp/docs-audit/audit.aiff -ar 16000 -ac 1 /tmp/docs-audit/audit-5s.wav
# …經 transcribe_isolated_detailed 以真 helper 二進位跑完後：
ls data/logs/app.log                                    # → 不存在（M1）
grep -n "ASR 引擎觀測" data/logs/app_$(date +%F).log     # → :11,:21 可見 helper_invocations／conversion_reason
grep -rn "model_info" backend/                          # → 僅 schemas.py:67 定義、無賦值（M2）

# 3) /health 欄位實測
grep -n "effective_asr_backend" backend/api/routes.py   # → 僅 :533（/api/config）；/health 無此欄（M3）

# 4) 離場碼實測
apple_speech_cli/.build/release/apple-speech-cli probe --locale xx-XX; echo $?   # → 3
```

## 七、限制與殘留風險

- **平行變更**：稽核期間另有 agent 正在寫入／執行（`backend/services/asr_subprocess.py`、`backend/workers/asr_worker.py`、`tests/`、`e2e/comparison-0903`、`data/cache/apple-vs-whisper-0903` 等）。本報告以 **2026-09-12 23:37–23:42 CST** 之工作樹狀態為準；若其後被稽核文件或權威碼再被修改，本報告即失效，需重新稽核。
- **4.9× 宣稱**仍在 `README.md`／`CHANGELOG.md`（§四）；在補上本 repo 實測或降格措辭前，屬未證實的效能宣稱。
- **觀測指示（M1／M2）為本次最嚴重不一致**：使用者照文件操作會完全看不到 `helper_invocations`／`conversion_reason`。
- 稽核者未修改任何產品碼、既有測試或被稽核文件；本報告為本次稽核唯一新增產物。
