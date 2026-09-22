# P3 跨平台稽核報告（Windows 11 ＋ RTX 4090／Ollama）

> 稽核任務：`T20260922-2037-02-local-model-quality-parity`（分支 `fix/qwen-local-quality-parity`）
> 範圍：P3 波新增之三項機制＋Windows 部署前提（不含 P2，P2 見 `e2e/crossos-audit-01/audit.md`）
> 方法：逐檔開啟程式碼逐行核對；純函式在 macOS 本機以 `.venv` 實跑做決定性驗證（下方標「本機實跑」）。
> 限制：**本機無 Windows 實機**。凡屬「實機才會知道」的一律標 `[UNVERIFIED]`，本文不得被引用為 Windows 已驗。

---

## ① 一句總結

- P3 三個機制的**程式碼層對平台無關**：查無任何 `os.name`／`sys.platform`／`platform.*` 分支介入量尺、吸附、待辦守衛或補強迴圈；Windows 的 `auto` 與 macOS 的 `auto` 只在「選哪個本地引擎」分岔（`backend/core/platform_config.py:23-28`、`:46-55`），選完後**共用同一條** `_summarize_with_local_pipeline`。
- 但兩處會「**靜默失效**」（不報錯、紀錄照產出、只是品質機制不再作用）：(a) 吸附＝diarization 未就緒／逐字稿無段落列／模板非科務會議／非本地模式；(b) 待辦召回守衛＝萃取筆記的待辦表格少於 3 欄。這兩者都是**資料與模型前提**，不是平台分支。
- 量尺 `measure_coverage.py` 是純 Python、可重現，但**跨平台「byte 相同輸出」不成立**（Windows CRLF、stdout 編碼、Windows 路徑分隔、BOM 檔）；度量值本身不受影響。另有 1 個 Windows 專屬硬錯誤風險：帶 BOM 的 checklist JSON 直接退出 2。

---

## ② `scripts/e2e/measure_coverage.py` 平台差異逐項

| # | 檢查項 | 判定 | 證據（檔案:行號） |
|---|---|---|---|
| 1 | 是否純 Python（無 MLX／CoreML／平台套件） | **無風險**：只 import 標準庫＋兩個選配純 Python 套件；`backend` 模組僅在 OpenCC fallback 內延遲 import | `scripts/e2e/measure_coverage.py:61-70`（stdlib）、`:148`（opencc）、`:155`（backend fallback）、`:172`、`:185`（pypinyin）；依賴 wheel 皆 `py2.py3-none-any`（`uv.lock:974`、`:1117`） |
| 2 | locale 相依（大小寫、排序、數字格式） | **無風險**：未 import `locale`；用 `casefold()`（非 `lower()` 做語意折疊）；`sorted()` 為碼位序；`f"{v*100:.1f}%"` 為固定格式 | `scripts/e2e/measure_coverage.py:279-284`、`:1000-1009`（僅字典序 set/dict 遍歷）、`:700-706` |
| 3 | `sys.stdout` 編碼 | **有風險**：JSON（`ensure_ascii=False`，含中文）以 `print` 寫 stdout；Windows 上若 stdout 被重導向（管線／`>` 檔），文字模式編碼＝主機 ANSI 代碼頁（如 cp950／cp936／cp1252），非常用字元或非中文語系會 `UnicodeEncodeError` → traceback、無報告。專案已有正確慣例可照抄 | 風險點 `:934`、`:941`；既有慣例 `scripts/e2e/run_owned_e2e.py:204`（`PYTHONIOENCODING=utf-8`） |
| 4 | 換行／CRLF | **有風險（僅 byte 層）**：Windows 文字模式會把 `\n` 轉 `\r\n`，因此 `--json-out`／`--md-out` 檔案與 stdout 內容在 Windows 為 CRLF、macOS 為 LF →「同輸入 → byte 相同」只在**同一平台內**成立。度量與正規化不受影響（空白／換行在 NFKC 後由 `\s+` 全數移除） | 寫檔 `:937`、`:940`；stdout `:941`；換行折疊 `:110`、`:283-284` |
| 5 | 檔案讀取編碼 | **無風險（明確 UTF-8）**：`read_bytes()`＋`decode("utf-8")`，不隨 locale；解碼失敗明確退出 2。**但 BOM 有風險**：`utf-8`（非 `utf-8-sig`）會把 `\ufeff` 留在字串開頭 → 帶 BOM 的 checklist JSON（Windows 記事本／PowerShell 常見）在 `json.loads` 直接失敗退出 2；帶 BOM 的紀錄 Markdown 則安全（BOM 字元會被 `_KEEP_PATTERN` 濾掉） | 讀取 `:869-872`、`:891-903`；JSON 解析 `:905-909`；濾除非保留字元 `:112-119` |
| 6 | `pathlib` 路徑分隔 | **無風險（功能）／有風險（輸出欄位）**：`Path`、`suffix`、`stem`、`exists()` 在 Windows 正常；但 `record_path`／`checklist_path` 會帶 `\`，`label` 預設取檔名 stem → 兩平台 JSON 不同（比較報告時應忽略這些欄位） | `:920`、`:922`、`:925`、`:678`（`Path(...).stem`）、`:88-90`（專案根探測） |
| 7 | OpenCC 是否必要／fallback | **非必要**：三層（`opencc` → `backend.core.text_postprocess.to_taiwan_traditional` → identity），且**兩側套同一函式**、報告標記 `opencc_available`。但缺 OpenCC 時簡繁不互通 → 若 checklist 用簡體、紀錄用正體，Windows 會量到**較低**的覆蓋率（不是錯誤、是誠實降級）；反之亦然。容器／映像已納入此依賴 | `:132-160`、`:255-273`、`:305-310`；依賴在 `requirements-correction.txt:10`＋`docker/Dockerfile.gpu:96-97`（`docker/Dockerfile:35-36` 同） |
| 8 | 時間／時區相依 | **無風險**：預設不寫時間戳（`--no-timestamp` 為預設）；`--timestamp` 用 `datetime.now(timezone.utc)`（UTC、不讀本機時區），且**不需要 `tzdata`**（未用 `ZoneInfo`／`localtime`） | `:911-913`、`:869-872`；對照手冊所述 E2E runner 才需 `tzdata`（`doc/操作手冊/部署更新手冊_v4.1.md:491`） |
| 9 | 其他（sha／字元數） | **無風險但跨平台不可比**：`sha256` 以原始 bytes 計（同內容 LF vs CRLF → 不同 sha）；`record_char_count` 用 `len(text)`（CRLF 檔多計換行字元）。`record_normalized_char_count`／`matched_positions` 以正規化字串為準 → 跨平台一致 | `:871-872`、`:676-677`、`:684-685`、`:288-291` |

補充：CLI 測試 `tests/test_measure_coverage.py:319-330` 以 `sys.executable` 起子行程並比對 stdout 與 `--json-out` bytes；在 Windows 兩者都經換行轉譯、可能仍相等，但**跨平台**必不等（同 ②-4）。此測試未在 Windows 跑過 `[UNVERIFIED]`。

---

## ③ 吸附區間語意、`measure_tag_traceability`、與 Ollama 呼叫鏈

### 3.1 平台無關性：`[VERIFIED]`
- `_segment_contains`（閉區間；零長度段退化為單點）：只用整數比較。`backend/core/text_postprocess.py:772-788`
- `_pick_containing_segment`（**段首命中優先**；提供冪等性）：整數比較＋清單順序。`:791-812`
- `measure_tag_traceability`（`metric_version: tag_traceability-1.1.0`）：regex＋整數＋`set`，與吸附共用同一份閉區間定義。`:970-1048`（定義共用點 `:1010`、`:1012-1015`、`:1021-1026`）
- 無 locale／時區／檔案系統／平台判斷；regex 的 `\s`、`\d` 在 CPython 各平台同一實作。
- 本機實跑（決定性）：逐字稿 `[00:00:00-00:00:30]`＋`[00:00:30-00:01:00]`，`_pick_containing_segment(segs, 30)` → `(30, 60, '發言者1')`（段首優先，不倒退）；`on_start_tag_ratio = 1.0`。
- 附註（低風險、與平台無關）：`:954-956` 的 `_pick_containing_segment(...) or ()` 若真的拿到空值會 `IndexError`；依 `:929-939` 的建構（`same_speaker ⊆ segments`）實際走不到，屬潛在脆弱點而非現行缺陷。

### 3.2 Ollama 路徑下是否真的會被呼叫：`[VERIFIED]`（會）
呼叫鏈（Windows 走同一條，無 provider 分支）：
1. `backend/services/task_processor.py:298` 取得逐字稿（含 diarization 發言者標註）→ `:313` 語意校正（閘門禁止刪字，見 3.4）→ `:333-339` 呼叫 `summarize(transcript, mode=task.processing_mode)`。
2. `backend/services/summarization.py:460-464`：`mode=local` → `_summarize_with_local_pipeline`。
3. `:2199` `_select_local_engine()`：Windows `auto` → Ollama-first；顯式 `ollama` → 只走 Ollama（`:2109-2144`）。
4. 最終生成後 `:2310-2315` `_finalize_record_text(mode="local", transcript=transcript)`；`:2455` 呼叫 `snap_source_tags_to_transcript(text, transcript or "", template)`。
5. 每一輪補強後 `:2366-2371` 再走同一條後處理（吸附也會重跑，且函式冪等）。

### 3.3 fail-soft no-op 條件（會靜默失效，全部不報錯）
`snap_source_tags_to_transcript` 早退條件：`backend/core/text_postprocess.py:900-905`（無文字／無逐字稿／模板無 `speaker_traceability`／逐字稿解析不出任何段落列）。

| 條件 | 程式位置 | Windows 風險 |
|---|---|---|
| 模板非科務會議 | 只有 `section_meeting` 開旗標：`backend/core/templates.py:388`；`general` 為預設 `False`：`:169` | 中：預設模板就不會吸附（非 Windows 專屬） |
| 非本地模式（雲端） | `summarization.py:2441-2442`（cloud 直接 return）、`:2475-2484`（cloud 收尾不吸附） | 中：Windows 若用雲端模式＝不吸附（與 macOS 相同、非平台差異） |
| diarization 未就緒 → 逐字稿無 `[HH:MM:SS-HH:MM:SS] 發言者N：` 段落列 | `task_processor.py:202-204`（`result` 為 None 即回 None，**呼叫端不記 log**）、`:219-221`、`backend/services/diarization.py:307-312`（只有 warning）；解析端 `text_postprocess.py:829-846` | **高**：模型／套件就緒度取決於 Windows 部署；且 `/health`、`/api/config` **完全沒有 diarization 欄位**（`backend/api/routes.py:530-560` 僅本地 LLM），`diarization_service.is_available()` 無任何呼叫端 → 使用者沒有介面訊號 |
| 模型標註未用全形括號 | `SOURCE_TAG_PATTERN`（`:479`）只認 `（…）` | 中：模型寫半形 `(...)` 就不作用（模型相依） |
| 逐字稿段落列格式不符（例：時間戳被改寫） | `TRANSCRIPT_SEGMENT_PATTERN`（`:752-754`）要求行首 `[`＋空白容忍 | 低：ASR＋標註器為系統產生，格式固定（`backend/services/speaker_transcript.py:316-329`） |

**結論**：吸附機制在 Windows 上**不會被平台分支繞過，但會被上述前提靜默關閉**；最可能的情境是「diarization 模型沒進到容器 volume」→ 逐字稿沒有發言者段落 → 吸附與 `_validate_cloud_speaker_traceability` 皆無感，紀錄仍正常產出。

### 3.4 校正層不會破壞段落列（吸附輸入保真）
逐字稿校正以句界切段後送 LLM，再過 `gate_correction`：`delete`／`insert` 非空白一律退回原文（`backend/services/correction.py:130-186`，`delete` 於 `:172-176`），且整段改動 > 10% 直接放棄（`:144-152`，預設 `CORRECTION_MAX_CHANGE_RATIO=0.10`，`backend/core/config.py:354-357`）→ 段落列前綴不會被刪除。`clean_transcript` 的確定性層亦不動段落列（`text_postprocess.py:219-248`）。

---

## ④ 待辦召回守衛與不收斂保護（所有 provider 分支）

### 4.1 provider 分派點盤點（生成路徑本身沒有分岔）
| 分派點 | 行為 | 是否影響 P3 機制 |
|---|---|---|
| `backend/core/platform_config.py:46-55` | `auto`＋Apple Silicon → `lmstudio`；其他 → 原樣 | 否（只決定引擎） |
| `backend/services/summarization.py:2109-2144` | 顯式 `lmstudio`→`:2113-2121`；顯式 `ollama`→`:2122-2128`（失敗直接 raise）；`auto`→Ollama 優先、否則 LM Studio（`:2130-2144`） | 否 |
| `summarization.py:2146-2189` | `_generate_with_local_engine` 只分派 Ollama／LM Studio 傳輸 | 否 |
| `summarization.py:3649-3653`、`:3857-3869`、`:4070-4071`、`:4141-4149` | health／warmup／release，**Ollama-only**、且都在生成路徑之外 | 否 |
| `backend/main.py:102-114`、`backend/api/routes.py:530-557` | 只做啟動 log／公開設定回報 | 否 |

### 4.2 守衛與不收斂保護：任何分支都執行 `[VERIFIED]`
- 待辦守衛本體：`ACTION_NEGATION_TERMS`／`_ACTION_NUMBER_PATTERN`＝`summarization.py:143-159`；`_find_missing_action_keys`＝`:1011-1065`；掛在 `_validate_summary_quality`＝`:1114-1210`（缺漏判定 `:1172-1210`）。
- 本地路徑（**Ollama 與 LM Studio 共用**）：初次 `:2320-2322`、每輪補強後 `:2372-2374`。
- 雲端路徑（Gemini／Ollama Cloud 共用同一雲端程式）：初次 `:3475`、補強後 `:3513`。
- 不收斂保護：`previous_issue_signature = tuple(sorted(issues))`，與上一輪相同即 break，並記 warning：本地 `:2329-2340`、雲端 `:3480-3489`；輪數上限 `LOCAL_LLM_MAX_REFINEMENT_ROUNDS` 預設 2（`backend/core/config.py:270-273`），**兩份 compose 皆未覆寫**（查無命中）→ Windows 與 macOS 同界。
- 故：**任何 provider 分支都會執行**；不會有「Windows 走 Ollama 就跳過守衛」的情形。

### 4.3 `\d` 的 Unicode 行為與 NFKC
- CPython 的 `str` regex 中 `\d` 預設匹配 **Unicode 十進位數字**（含全形、阿拉伯-印度數字等）。本機實跑：`re.findall(r"\d{3,}", "１３６００")` → `['１３６００']`；`_ACTION_NUMBER_PATTERN` 因此對全形數字也命中。
- 但同一條正規化內已先 NFKC：`_normalize_action_key` 第一步即 `unicodedata.normalize("NFKC", text)`（`summarization.py:954`），本機實跑 `NFKC("１３６００") = "13600"`；千分位逗號由 `:961` 的去除字元集移除（本機實跑 `13,600 → 13600`；`１３，６００ → 13600`）。
- 比對兩側（紀錄 `:1164` 與標籤 `:1102-1105`）都走同一函式 → 全形／半形／逗號差異被折疊，**不會因語系或輸入法造成平台差異**；NFKC 不折疊的其他語系數字（如 `١٢٣`）在兩側同樣保留，行為一致、只是判為「不同數字」（往更嚴，安全）。
- 本機實跑守衛：key「嚴禁轉傳科內群組訊息至外部」對紀錄「…科內群組訊息外流至外部渠道…」→ LCS 0.69 ≥ 0.6 但缺否定詞「嚴禁」→ 判遺漏（符合 R2 設計）。
- 低風險觀察（與平台無關）：`_action_key_best_lcs_ratio` 的候選視窗由 key 自身 bigram 反推、`start < 0` 直接丟棄（`:992-1000`），key 有未命中的前綴時可能整段得 `0.0`（本機實跑：「嚴禁將資料外流」對紀錄「將資料外流」→ 0.0）。方向偏嚴（不會把失真放行），但日誌中的 ratio 不可當精確校正分佈。

### 4.4 守衛的靜默停用條件（Windows 需注意）
- 待辦 key 只從萃取筆記的 markdown 表格第一欄抽取，且**該列至少 3 欄**才會被視為待辦列（`summarization.py:1084-1086`）。若 Windows 上的模型（gemma4:31b 等）沒照 `LOCAL_EXTRACTION_PROMPT`（`:213-219`）輸出四欄表格 → `expected_actions` 為空集合 → 守衛與「具體遺漏清單」完全不作用、也不報錯。模型相依 → `[UNVERIFIED]`。

---

## ⑤ Windows 部署前提（與 macOS 行為對齊還缺什麼）

| # | 項目 | 狀態 | 證據 |
|---|---|---|---|
| 1 | Windows 引擎＝Ollama（`auto` → Ollama 優先；建議顯式 `LOCAL_LLM_PROVIDER=ollama`，避免 Ollama 掛掉時錯誤訊息誤指 LM Studio） | `[VERIFIED]` 程式碼；`LOCAL_LLM_PROVIDER` 未在兩份 compose 設定（預設 `auto`） | `platform_config.py:46-55`、`summarization.py:2110-2144`、`config.py:58-61`；`手冊:474-478` |
| 2 | `OLLAMA_BASE_URL`／`LOCAL_LLM_MODEL` 寫死在 GPU compose；改 `.env` 無效（`environment` > `env_file`） | `[VERIFIED]` | `docker/docker-compose-windows-gpu.yml:86-87`、`:49-50`；`手冊:422`、`:481` |
| 3 | diarization 模型必須就位（容器內 `/app/models/diarization`）：compose 只掛具名 volume `meetingscribe-whisper-models:/app/models`，**未掛 host `models/`**；沒有任何程式會自動下載；缺模型時只記 warning、無介面訊號（見 3.3） | `[VERIFIED]`（設定事實）；模型實際存在 `[UNVERIFIED]`（需實機） | `docker-compose-windows-gpu.yml:163-173`、`:168`；`docker/docker-compose.yml:134`、`:182-184`；`scripts/download_diarization_models.py:101-110`；`config.py:511-518`；`手冊:425` |
| 4 | 容器內已有 `sherpa-onnx`（diarization）、`opencc`、`pypinyin`（量尺選配） | `[VERIFIED]`（安裝設定）；實機 `[UNVERIFIED]` | `requirements.txt:49` + `docker/Dockerfile.gpu:91-93`；`requirements-correction.txt:10,13` + `Dockerfile.gpu:96-97` |
| 5 | Windows ASR（faster_whisper）提供 segment `start/end` → 可通過時間軸守門 → 才能做發言者標註 | `[VERIFIED]`（程式碼）；實機 `[UNVERIFIED]` | `backend/services/transcription.py:471-487`；守門 `task_processor.py:182-197` |
| 6 | 吸附只在「科務會議模板 ＋ 本地模式」生效（其他模板／雲端不會做） | `[VERIFIED]` | `templates.py:388`（對照 `:169`）、`summarization.py:2441-2442`、`:2455`；`手冊:426` |
| 7 | context 預算不同（GPU compose 16384 vs macOS LM Studio instance context）→ 切塊／整併／問題集合不同，**Mac 量到的品質數字不能直接當 Windows 驗收基準** | `[VERIFIED]` | `docker-compose-windows-gpu.yml:118`；`config.py:188-191`；`手冊:424`、`:483` |
| 8 | 主機端 Ollama 必設 `OLLAMA_FLASH_ATTENTION=1`＋`OLLAMA_KV_CACHE_TYPE=q8_0`；未生效會 offload → 本任務降級 `num_ctx=8192`，長會議切更多塊、更容易觸發補強輪 | `[VERIFIED]`（程式與文件）；主機設定 `[UNVERIFIED]` | `summarization.py:4086-4135`、`:4141-4149`；`compose:233-236`；`.env.example:121-125` |
| 9 | 量尺腳本更新到 Windows：`scripts/` **不在** volume 掛載清單（只掛 `backend/`、`frontend/`、`VERSION`），但 `.dockerignore` 未排除 `scripts/`、`COPY . .` 有進映像 → 新版量尺要 rebuild（或 `docker cp`／在 host 跑），`restart` 不會更新它 | `[VERIFIED]` | `docker-compose-windows-gpu.yml:163-173`；`.dockerignore:1-20`（無 `scripts`）；`Dockerfile.gpu:125`；`手冊:450`（只說 backend/frontend） |
| 10 | 量尺在 Windows 執行時的 stdout 編碼：需 `PYTHONUTF8=1` 或 `PYTHONIOENCODING=utf-8`，或改用 `--json-out`（檔案明確 UTF-8） | `[VERIFIED]`（機制與既有慣例）；實機 `[UNVERIFIED]` | `measure_coverage.py:934,937,941`；`run_owned_e2e.py:204` 為專案既有做法 |
| 11 | checklist JSON 需為 **UTF-8 無 BOM**；帶 BOM 會直接退出 2（本波未使用 `utf-8-sig`） | `[VERIFIED]`（機制）；實機 `[UNVERIFIED]` | `measure_coverage.py:871-872`、`:905-909` |
| 12 | 量尺本身**不需要** `tzdata`（無 `ZoneInfo`）；`tzdata` 是 E2E runner 的需求，勿混淆 | `[VERIFIED]` | `measure_coverage.py:68`、`:911-913`；`手冊:491` |
| 13 | Windows 實機（RTX 4090＋Ollama）端到端驗證（含吸附、守衛、補強收斂、量尺） | `[UNVERIFIED]`（無實機；本波 E2E attempts 全為 macOS） | `plan.md` 自述；`e2e/attempt-*` 無 Windows 環境 |

---

## ⑥ 風險清單

| # | 風險 | 會不會「被繞過／靜默失效」 | 等級 | 位置 |
|---|---|---|---|---|
| R1 | diarization 未就緒（Windows 最可能）→ 吸附與 `measure_tag_traceability` 的 `segments=0`，紀錄照出、不報錯 | **會靜默失效**（非平台分支，是部署前提） | 高 | `task_processor.py:202-204`、`:219-221`；`text_postprocess.py:904-905` |
| R2 | 模板非科務會議或非本地模式 → 吸附不作用 | 會（設計內） | 中 | `templates.py:169,388`；`summarization.py:2441-2442` |
| R3 | 萃取筆記待辦表格 <3 欄 → 待辦守衛與「具體遺漏清單」不作用 | 會靜默失效（模型相依） | 中 | `summarization.py:1084-1086`、`:1172-1210` |
| R4 | 量尺 stdout 編碼（Windows 重導向）→ `UnicodeEncodeError`、無報告 | 會硬失敗（有明確 traceback，非靜默） | 中 | `measure_coverage.py:941` |
| R5 | checklist JSON 帶 BOM → 退出 2 | 會硬失敗（訊息明確） | 中 | `:871-872`、`:905-909` |
| R6 | 跨平台 byte 不同（CRLF／路徑分隔／sha）被誤讀成「結果不同」 | 認知風險 | 低 | `:937,940,941`、`:920-925`、`:871-872` |
| R7 | 吸附與量尺的平台無關性本身：查無風險 | 無 | — | `text_postprocess.py:772-812`、`:970-1048` |
| R8 | `_pick_containing_segment(...) or ()` 潛在 `IndexError`（依建構走不到） | 否（僅脆弱點） | 低 | `text_postprocess.py:954-956` |

---

## ⑦ 建議（最小、可執行，皆不需改產品程式）

 1. Windows 首驗（實機）依序：確認容器內 `models/diarization` 兩個模型檔存在 → 以「科務會議＋本地模式」跑一份錄音 → 用 `measure_record_quality.py`（`tag_traceability`）與 `measure_coverage.py` 各量一次，並確認 `kept_on_start`（已是段首的標註未被搬動）＋ `backward_moves`／`max_backward_seconds`（後退僅限段落內吸附、幅度受觀測）。（舊名 `snapped_across_segment`＝rev 8 工作名，恆 0 無鑑別力，已移除。）
    - **rev 12 errata（2026-09-23）**：上述「後退僅限段落內吸附」不成立於規則 2（nearest 容忍 180 s 可跨段後退；只有規則 1／3 的後退在段落內）；首驗只需看 `backward_moves`／`max_backward_seconds` 的**幅度**，別推論落點在段落內／不跨段——見 `plan.md` §8.7 風險⑤ 與研究文件 §11.7。
2. 量尺在 Windows 一律加 `PYTHONUTF8=1`（或 `set PYTHONIOENCODING=utf-8`）；checklist 存成 UTF-8 無 BOM。
3. 跨平台比對只比數值欄位（`coverage_*`／`tag_*`），忽略 `*_path`、`*_sha256`、`record_char_count` 與 `generated_at`。
4. 在 `.env` 明確設 `LOCAL_LLM_PROVIDER=ollama`（compose 未寫死此鍵，`env_file` 生效；改 `.env` 後記得 `up -d`）。
5. 若 Windows 首驗的紀錄「待辦遺漏清單」從未出現，先查 log 是否出現「待辦召回比對（P3，門檻…）」——沒有＝萃取表格形狀不符（R3），不是守衛壞掉。

> 誠實邊界：以上全部為程式碼／設定層證據；**Windows 實機未驗**，任何「實機已驗」的說法都不成立。
