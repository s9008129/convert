# 跨平台稽核 04 — P6-A／P7-A 品質機制在 Windows 11 ＋ Ollama 的可攜性

- **稽核角色**：研究型 subagent（**唯讀**；不得修改既有檔案、不得 commit、不得跑 E2E、不得呼叫 LM Studio／Ollama／網路）
- **日期**：2026-09-23　**工作目錄**：`/Users/hsiaojohnny/dev/convert`　**分支**：`fix/qwen-local-quality-parity`
- **受查快照**：`39a2cb0`（P7-B 前期；進場時 `git status --short` 只有本任務的未追蹤 `research/`，**受查的 tracked 檔皆等於 HEAD** ⇒ 本報告行號＝`39a2cb0` 行號）
- **受查問題**：Q1「P6-A／P7-A 這波新增的品質機制，在 Windows 11 是否同樣成立？」　Q2「同一套機制在 Ollama（RTX 4090／Windows）路徑是否同樣被套用？」

## 0. 方法與限制宣告

- 全程**唯讀**：只用 `git log/show`、`sed`、`rg`、`shasum` 讀取；未啟動後端、未執行測試或 E2E、未對外發出任何請求、未跑長時指令。
- **本機無 Windows 實機**：凡屬「實機才會知道」的一律標 `[UNVERIFIED]`；本報告**不得被引用為「Windows 已驗」**。
- 受查檔案內容指紋（sha256 前 16 碼；供日後行號漂移時重新定位）：

| 檔案 | sha256(16) |
|---|---|
| `backend/services/summarization.py` | `92cb95ce9e420c61` |
| `backend/core/config.py` | `179939eee515dbae` |
| `backend/core/text_postprocess.py` | `090822a01c93398a` |
| `backend/core/fidelity_checks.py` | `9dae0dc3f77dde36` |
| `backend/core/platform_config.py` | `145ef922afccf266` |
| `backend/services/task_processor.py` | `ac8832ae53507fda` |
| `scripts/e2e/measure_coverage.py` | `6b4ed8f5dfae3945` |
| `scripts/e2e/run_owned_e2e.py` | `3a6557fcdda65b2c` |
| `tests/test_platform_provider_routing.py` | `058f9d247bf0434f` |

---

## 1. 結論（TL;DR）

- **Q1（Windows 11 是否成立）**：**程式碼層成立，實機未驗**。P6-A／P7-A 所在的品質模組（`text_postprocess.py`、`fidelity_checks.py`、覆蓋率對帳、不回退守衛）**沒有任何平台判斷、沒有任何 OS API**（純字串／集合運算），而且有測試**明文禁止**這些模組出現 `platform.system`／`sys.platform`／`os.name`／`darwin`／`win32`（`tests/test_platform_provider_routing.py:180-192`）⇒ `[VERIFIED]`（code）；但**沒有任何 Windows 實機執行證據** ⇒ 實機 `[UNVERIFIED]`。
- **Q2（Ollama 路徑是否同一套）**：**是，同一條管線**。LM Studio 與 Ollama 都走 `_summarize_with_local_pipeline`（`backend/services/summarization.py:3257`），只用 `_generate_with_local_engine`（`:3136`）分派「誰來生成文字」；**P6-A（決議逐條對帳）／P4-A（覆蓋率與 `cov_*`）／P7-A（不回退守衛）／地端後處理鏈／忠實度絆索**全部在分派點之後、與引擎無關 ⇒ `[VERIFIED]`（code）；Ollama 實機 `[UNVERIFIED]`。

---

## 2. 兩條路徑的關係（Q2 的完整證據）

### 2.1 共用管線（呼叫圖，皆為 `backend/services/summarization.py`）

```
_summarize_with_local_pipeline(:3257)
 ├─ _select_local_engine(:3099)              ← 平台/設定只決定「選誰」
 ├─ _generate_with_local_engine(:3136)       ← 唯一引擎分派點（:3155 ollama / :3166 lmstudio）
 │    ├─ _summarize_with_ollama(:3817)       ┐ 只負責「傳輸 + 清理 + 空回應重試」
 │    └─ _summarize_with_lmstudio(:4016)     ┘
 ├─ _finalize_record_text(..., mode="local", transcript=...)  最終生成後（:3379）
 ├─ _validate_local_record(:3181)            ← 初稿檢查（:3389）
 ├─ while issues and attempts < LOCAL_LLM_MAX_REFINEMENT_ROUNDS(:3408)
 │    ├─ 不收斂保護 previous_issue_signature(:3396)
 │    ├─ _generate_with_local_engine(...)    ← 補強輪（同樣經分派點）
 │    ├─ _finalize_record_text(mode="local") ← 補強輪也走同一條後處理（:3444）
 │    ├─ _validate_local_record(:3451)
 │    └─ P7-A 守衛：_core_coverage_snapshot(:3209) / _refinement_regression_reason(:3235)
 │         （呼叫點 :3404-3406 初始化、:3455-3498 判定與回退）
 └─ metrics 彙總 _record_coverage_metrics_fields(:2133)
```

`_validate_local_record`（`:3181-3207`）內容固定為五道、順序固定：
`_validate_summary_quality` → `_validate_cloud_speaker_traceability` → `_validate_cloud_date_grounding` → `_validate_record_source_coverage`（`:1943`，P4-A／P6-A）→ `_validate_record_fidelity`（`:2156`，P4-B）。**這四道全部吃 `summary`＋`notes`＋`transcript` 三個字串，與引擎無關**。

P6-A 的三種真實寫法修補落在 `_parse_notes_items`（`:1613`）及其 helper：`_strip_notes_item_quote_prefix`（`:1497`）、`_notes_line_indent`（`:1524`）、`_collect_nested_notes_items`（`:1537`）、`_append_notes_item`（`:1595`）——全部是 `@classmethod`／`@staticmethod` 純文字解析，**沒有引擎參數、沒有平台參數**。

### 2.2 引擎差異清單（哪些地方真的不一樣）

| # | 差異 | 位置 | 是否影響品質機制 | 判定 |
|---|---|---|---|---|
| 1 | **context 預算來源**：LM Studio＝本次載入 instance 的 `context_length`；Ollama＝`settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS` | `summarization.py:3287`（`lmstudio_instance`）／`:3790-3793`（`_effective_context_tokens`）；`config.py:198-201` 預設 8192 | **會影響**：切塊數、merge 輪數、`_resolve_final_generation_message` 是否附逐字稿（`:2817-2845`）、問題集合 | `[VERIFIED]`（code） |
| 2 | **取樣 payload**：Ollama 送 `top_p`／`top_k`／`repeat_penalty`／`num_ctx`／`num_predict`／`stop`／`keep_alive`；LM Studio 走 `_lmstudio_extra_body`（`:4340`）且 penalty 類欄位不送 | `summarization.py:3893-3899`（payload）、`:3795-3815`（`_ollama_sampling_options`）、`:4340` | 間接（模型行為），**機制本身不受影響** | `[VERIFIED]`（code） |
| 3 | **空回應恢復機制不同**：LM Studio＝reasoning/semantic recovery 狀態機（`allow_reasoning_retry`）；Ollama＝固定 2 次重試＋`think:false` 降級重送 | `summarization.py:3151-3153`、`:4035-4039`、`:4086-4120`；Ollama `:3878`、`:3741-3748` | 不影響後處理；影響「失敗長相」與診斷欄位 | `[VERIFIED]`（code） |
| 4 | **輸出預算擴張**：`expand_output_budget` 只作用 Ollama 的 `num_predict` | `summarization.py:3853`、`:4036-4039` | 間接（輸出長度） | `[VERIFIED]`（code） |
| 5 | **選模來源**：LM Studio＝`/api/v1/models` loaded instance inventory（`:3016`、`:3052`）；Ollama＝`/api/tags` ＋家族別名解析（`:4808`、`:4885-4924`） | 同左 | 不影響品質機制（只決定「跑哪顆」） | `[VERIFIED]`（code） |

### 2.3 只在單邊生效的事（必須誠實列舉）

| 只在 LM Studio 生效 | 只在 Ollama 生效 |
|---|---|
| 載入 instance 的 `context_length` 當 context 預算（`:3282-3289`） | `think:false` 關思考（`config.py:333-336` 預設 true；`summarization.py:3878`） |
| `allow_reasoning_retry` 語意回復（`:3151-3153`） | `repeat_penalty`／`num_ctx`／`num_predict` 擴張（`:3853`、`:3897-3898`） |
| `LMSTUDIO_*` 錯誤碼（unreachable／not loaded／multiple）（`:3075-3090`） | Ollama 模型存在性檢查與「不靜默換模型」錯誤（`:4834-4840`） |
| — | keep-alive 保留模型避免 20GB 重載（`:3890`，`LOCAL_LLM_KEEP_ALIVE`） |

**沒有任何 P6-A／P7-A 條目出現在這張表**——它們全部在分派點之後。

---

## 3. OS 相依風險清單（Q1；依嚴重度排序）

| # | 風險 | 位置 | 等級 | 判定 |
|---|---|---|---|---|
| 1 | **平台判斷集中化**：全庫平台判斷只在 `platform_config.py`（`:23-25` `is_darwin_arm64`、`:53` provider auto、`:62-83` ASR backend）、`api/routes.py:73`（Apple helper health）與 Apple ASR 子系統；品質模組零命中 | 同左；否證測試 `tests/test_platform_provider_routing.py:180-192` | 不影響 | `[VERIFIED]` |
| 2 | **Apple SpeechAnalyzer 在 Windows**：`ASR_BACKEND=apple` → 非 Mac 直接 `ValueError`（fail-fast，非靜默）；`auto` 在非 Mac 走模型型 resolver（faster-whisper／transformers）；`/health` 回 `supported=false` 且**不載入 Apple 模組、不 spawn** | `platform_config.py:66-72`、`asr_model_resolver.py:89-92`、`asr_apple/dispatcher.py:44-49`、`api/routes.py:73-81` | 不影響（設計即 fail-soft） | `[VERIFIED]`（code） |
| 3 | **換行 CRLF**：記錄／逐字稿以 text mode 寫檔（Windows 會寫成 CRLF），但讀回走 universal newline 正規化；逐字稿解析用 `splitlines()`（CRLF 安全）；量尺的比對前處理明文 strip「含 Windows CRLF」 | 寫：`file_manager.py:210`、`:229`、`:249`；讀：`file_manager.py:198-200`、`routes.py:405`、`:442`；解析：`text_postprocess.py:870`、`:956`；量尺：`measure_coverage.py:275-284`（`_WHITESPACE_PATTERN`＝`\s+`，`:110` 註解明列 `\r`） | 需驗證（低） | `[VERIFIED]`（code 層面已處理）；實機 `[UNVERIFIED]` |
| 4 | **編碼**：全庫硬編碼 `utf-8`；機關詞彙表刻意用 **`utf-8-sig`**（吃 Windows 記事本 BOM，避免第一行配對靜默失效）；資料檔（`data/glossary/*.txt`、`data/entities/entity_registry.json`）實查**無 BOM** | `glossary.py:64-67`；`fidelity_checks.py:300`（`utf-8`，靠 try/except fail-soft）；`logger.py:54,67` | 需驗證（低）：`fidelity_checks.py:300` 用 `utf-8` 讀 JSON，若使用者事後用記事本另存會帶 BOM → `json.load` 失敗 → **靜默 fail-soft**（白名單失效，非崩潰） | `[INFERRED]` |
| 5 | **子程序**：ffmpeg（diarization 音訊解碼）與 ASR worker 皆用 **list-args、無 `shell=True`**；worker 注入 `PYTHONIOENCODING=utf-8` 並在 worker 內 `reconfigure(encoding="utf-8")`；全程未見 `os.system`／shell 字串 | `diarization.py:160-180`、`asr_subprocess.py:135-145`、`workers/asr_worker.py:47-49` | 需驗證（低）：Windows 需 ffmpeg 在 PATH；diarization 模型需就位 | `[VERIFIED]`（code） |
| 6 | **路徑處理**：`os.path.join`／`pathlib`／`tempfile.mkstemp`；未見字串拼接路徑（全庫 grep `+ "/"`／`f"{settings.*}/"` 零命中） | `file_manager.py:24-40`、`platform_config.py:184-196`、`glossary.py:33`、`diarization.py:157-158` | 不影響 | `[VERIFIED]` |
| 7 | **E2E runner 的 process 終止**：POSIX 用 `os.killpg`（包在 `os.name == "posix"` 內），非 POSIX 走 `terminate()`／`kill()` | `scripts/e2e/run_owned_e2e.py:270-300` | 不影響 | `[VERIFIED]`（code） |
| 8 | **full E2E 在 Ollama-only 機器會 gate 失敗**：模型快照讀 LM Studio `/api/v1/models`，`model_inventory_unique`／`model_snapshot_consistent` 是 provider-specific 必檢項；已有豁免邏輯（非 lmstudio 豁免） | `run_owned_e2e.py:97`、`:192-193`、`:489-521`、`:1316-1328`、`:1346` | 需驗證（中）：豁免是否真的在「Windows 容器內 configured=ollama」情境生效，需實機 | `[INFERRED]` |
| 9 | **`DATA_DIR` 預設 `/app/data`**（容器拓樸）；原生 Windows（不進容器）需顯式設定 | `config.py:597` | 需驗證（低） | `[VERIFIED]` |
| 10 | **`OLLAMA_BASE_URL` 預設 `http://host.docker.internal:11434`**：只對「後端在 Docker、Ollama 在主機」成立；原生 Windows 需改 `127.0.0.1` | `config.py:49-52`；`.env.example:44`；手冊 `doc/操作手冊/地端模型品質優化與驗證手冊_v4.10.md:357-361` 已明載 | 需驗證（低） | `[VERIFIED]`（code）；實機 `[UNVERIFIED]` |
| 11 | **`LMSTUDIO_BASE_URL` 預設在非 Mac 是 `host.docker.internal:1234`** | `platform_config.py:88-92` | 不影響（Windows 走 Ollama；只在 Windows 硬要跑 LM Studio 時需覆蓋） | `[VERIFIED]` |

---

## 4. 模型無關性風險清單

| # | 項目 | 位置 | 判定 |
|---|---|---|---|
| 1 | **沒有任何 `if "qwen" in model`／`gemma`／`mlx` 之類的品質分支**：全庫模型名字串只出現在（a）註解／實測註記、（b）Ollama 選模 helper、（c）取樣預設說明 | 註解：`summarization.py:1436,1451,1507,1538,1625,1632`；選模：`:4885-4924`、`:4983-4984`；取樣說明：`:3838`、`:4345-4349`、`:4385` | `[VERIFIED]` |
| 2 | **Ollama 選模 helper 有「Gemma4 家族偏好」**（正規化 `gemma4:31b` → 優先 `q4_K_M` 變體；找不到則報錯，不靜默換模型） | `summarization.py:4885-4924`、`:4983-4984` | `[VERIFIED]`；屬「選哪顆模型」，**不是品質槓桿**，但換模型時要確認實際選中的 tag（log 可見） |
| 3 | **context window 大小假設**：Ollama 一律吃 `settings`（程式預設 8192；Windows GPU compose 16384）；若主機未開 FLASH_ATTENTION／KV 量化，warmup 失敗 → 任務級降級 | `config.py:198-201`、`docker/docker-compose-windows-gpu.yml:118`、`.env.example:121-125` | `[VERIFIED]`（code）；主機設定 `[UNVERIFIED]` |
| 4 | **「本地模型一定支援某功能」的假設**：Ollama `think:false` 對不支援的模型回 400 → 實作已降級為「不帶 think 欄位重送」 | `summarization.py:3878`、`:3741-3748` | `[VERIFIED]` |
| 5 | **真正模型相依的是「萃取筆記格式」**：P4-A 期望集合從筆記的議題／決議／數字／日期抽取（P6-A 才把三種真實寫法補進來）。若換模型（例如 Ollama 上的 `gemma4:31b`）寫法不受支援 → 期望集合為空 → **有 `log.warning` 與 `cov_expected_*=0`，但守衛與「具體遺漏清單」靜默不作用**，任務照常成功 | 期望集合：`summarization.py:1985-2005`；空集合告警：`:1388-1394`、方法 docstring `:1952-1958`；守衛停用：`:3220-3231`（`expected <= 0` ⇒ 回 `None`） | `[VERIFIED]`（機制）；**Windows／gemma4 的實際筆記格式 `[UNVERIFIED]`** |
| 6 | **測試覆蓋缺口**：P7-A 守衛的單元測試以 `_select_local_engine → "lmstudio"` 標籤跑（`tests/test_t20260923_p7a_refine_no_regression.py:85`），**沒有 `engine="ollama"` 參數化**；「分派後共用」靠結構保證而非測試保證 | 同左＋`tests/test_platform_provider_routing.py:189-195`（分派函式禁平台分支） | `[INFERRED]`：結構上等價（守衛碼不含 engine 變數），但缺一條「engine=ollama 也走到守衛」的回歸測試 |

---

## 5. Windows ＋ Ollama：哪些槓桿「有程式碼證據會生效」

| 槓桿 | 生效判定 | 證據 |
|---|---|---|
| P6-A 決議逐條對帳（三種寫法不再整類 no-op） | `[VERIFIED]`（引擎／平台無關） | `summarization.py:1613`／`:1497-1610`；由 `:1943` 呼叫，`:3181` 統一進入 |
| P4-A 覆蓋率統計 ＋ `cov_*` metrics（守衛的輸入） | `[VERIFIED]` | `:1943`、`:2133-2150`；`off` 才不跑（`config.py:287` 預設 `enforce`） |
| P7-A 不回退守衛（丟棄事實回退的那一輪） | `[VERIFIED]`（code）／實機 `[UNVERIFIED]` | `:3404-3406`、`:3455-3498`、`:3209`、`:3235`；開關 `config.py:636-645` 預設 True |
| 地端後處理鏈（吸附→術語→表格標註清除→佔位符→去重） | `[VERIFIED]`（code） | `:3525-3615`（唯一入口，`mode="local"`）；吸附需逐字稿段落時間表（Windows 需 diarization 可用） |
| 忠實度絆索（自創專名／無依據歸屬／數字單位） | `[VERIFIED]` | `:2156`；`fidelity_checks.py:1-25`（自述模型無關、fail-soft）；`tests/test_platform_provider_routing.py:180-192` |
| 不收斂保護（問題集合相同就停） | `[VERIFIED]` | `:3396-3407` |
| 兩引擎取樣同源（P4-C） | `[VERIFIED]` | `:3795-3815` 讀 `config.py:251-259`、`:314-318` |
| Windows 預設就吃得到這些機制（compose 未覆蓋相關鍵） | `[VERIFIED]` | `docker/docker-compose-windows-gpu.yml:86-87,118-143` **未設** `LOCAL_LLM_RECORD_COVERAGE_MODE`／`LOCAL_LLM_REFINEMENT_NO_REGRESSION` ⇒ 用 `config.py` 預設（`enforce`／`True`） |
| 量尺（`measure_coverage.py`）在 Windows 可用 | `[VERIFIED]`（code）／實機 `[UNVERIFIED]` | `:869-872` 以 `read_bytes().decode("utf-8")`（**不做換行轉譯、sha256 以原始 bytes 計**）、`:110`＋`:275-284` 前處理以 `\s+` 去空白（含 `\r`）；**BOM 清單檔會直接退出 2**（`json.loads` 失敗，`:905-909`） |
| 「Mac 量到的品質數字」可直接當 Windows 驗收基準 | **不成立** `[INFERRED]` | context 預算不同（差異表 #1）＋吸附／切塊與問題集合會變；手冊亦明載 `doc/操作手冊/地端模型品質優化與驗證手冊_v4.10.md:290-296`、`部署更新手冊_v4.1.md`（Windows 段） |

**沒有任何一條 P6-A／P7-A 槓桿被判定「只在 macOS 生效」**；反過來說，**也沒有任何一條有 Windows 實機證據**。

---

## 6. 無法在 macOS 驗證、必須在 Windows 實機確認的清單

1. **完整任務跑通**（faster-whisper ASR → diarization（ffmpeg／sherpa-onnx 模型就位）→ 語意校正 → 地端摘要 → DOCX），並確認 `backend.log` 出現：`本地摘要上下文規劃`、`cov_expected_*`／`cov_missing_*`、`地端補強不回退守衛` 或「本場停用比較」三種行之一。
2. **守衛在 Ollama 上真的會作用**：需要一場「第 1 輪補回、第 2 輪寫掉」的實際重生成 → 看到 `造成事實回退` warning 或 `（持平／更好，取本輪）` info；**注意 Windows 預設 `enforce`（Mac E2E 用的是 `observe`），行為可能不同**。
3. **CRLF 實機驗證**：跑完後檢查 `data/outputs/*.md`、`data/cache/...txt` 的實際位元組（是否 `\r\n`），並比對同一份紀錄在 Windows 產出的 `sha256` 與 macOS 是否相等（預期**不相等**，屬正常）。
4. **量尺跨平台一致性**：同一份 `.md` 分別在 macOS／Windows 跑 `measure_coverage.py`，比對 `coverage_core` 是否相同（`--json-out` 檔案為準；stdout 在 Windows 可能被轉譯）。
5. **full E2E runner 的豁免路徑**：Ollama-only 機器上 `model_inventory_unique`／`model_snapshot_consistent` 是否真的被豁免（`run_owned_e2e.py:1316-1346`）；否則需改用 `--smoke` ＋ 產物量測。
6. **`fidelity_checks` 白名單在 Windows 是否讀得到**（`data/entities/entity_registry.json` 無 BOM `[VERIFIED]`；但若經 Windows 編輯器另存需複驗）。
7. **`think:false` 400 降級路徑**在實機 Ollama 版本的實際行為（`summarization.py:3741-3748`）。
8. **`OLLAMA_BASE_URL` 拓樸**：Docker（`host.docker.internal`）vs 原生（`127.0.0.1`）——決定任務能不能開始，非品質問題但會擋住驗收。

---

## 7. 風險排序（摘要）

- **H（會擋住驗收，非產品壞）**：無 Windows 實機證據；full E2E 在 Ollama-only 機器需豁免或改用 smoke＋產物量測（§3-#8）。
- **M（會讓機制靜默不作用）**：換模型後筆記格式不受支援 → 期望集合空 → 守衛與遺漏清單靜默停用（§4-#5，有 log 但不失敗）；`context` 預算不同 → Mac 數字不可當 Windows 基準（§2.2-#1）。
- **L（維運雜訊）**：`OLLAMA_BASE_URL`／`DATA_DIR` 預設是容器拓樸；`.env.example` **未列** `LOCAL_LLM_REFINEMENT_NO_REGRESSION`／`LOCAL_LLM_RECORD_COVERAGE_MODE`／`LOCAL_LLM_MAX_REFINEMENT_ROUNDS`（只在 CHANGELOG 與 v4.10 手冊出現）——功能預設開啟，不影響行為，但 Windows 維運者從 `.env.example` 看不到開關。
- **L**：`fidelity_checks.py:300` 用 `utf-8` 讀 JSON（非 `utf-8-sig`），BOM 情況 fail-soft 靜默失效（§3-#4）。
- **L**：P7-A 缺 `engine="ollama"` 參數化回歸測試（§4-#6）。

---

*本報告由唯讀稽核 agent 產出；所有 `[VERIFIED]` 皆以 `39a2cb0` 的檔案內容與實際 `rg`／`sed` 輸出為準，未引用任何未重跑的外部結論。*
