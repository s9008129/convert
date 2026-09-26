# P7-C 實作落點圖（C1c／C2a／C2b／S1）— 唯讀分析產物

- 任務：`T20260923-2050-01-local-extraction-adherence`（P7-C）
- 分支／HEAD：`fix/qwen-local-quality-parity` / `ab2528b`（分析時 `git status` 僅 `?? .agent/tasks/T20260923-2050-01-local-extraction-adherence/`）
- 本檔性質：**只讀**。不含產品碼修改；所有行號皆為 `ab2528b` 當下實讀值。
- 引註約定：`檔案:行號`；`[VERIFIED]`＝本次實讀原始碼／實檔確認；`[INFERRED]`＝由實讀推得。
- **不要**把本檔當成計畫（plan rev1 受審中，語意決策以 plan／審查為準）。

## 白話結論（5 行內）

1. C1c 的「呼叫預算」在萃取側**完全沒有**既有機制，最接近的先例是「merge 輪數上限→拋錯」與「觀測 skip log」兩族；建議照後者（觀察優先、不拋錯）。
2. 停止加塊的正確位置是 **`chunks` 建好之後、`total_chunks` 之前**（`summarization.py:3449-3453`），不是在 `for` 迴圈裡 `break`——否則 `chunk_count=` 會說謊、尾段會靜默消失。
3. C2a 的新類別是「加一格抽取器＋加一格白名單」，本體不難；難的是**兩個硬列清單**（`:3361`、`:2219-2229`）與預設類別字串——不動它們就等於新類別只算一半。
4. C2b 有一顆**藏在雲端的連帶風險**：`LOCAL_LLM_MAX_REFINEMENT_ROUNDS` 是雲端共用（`:4821`），2→3 會順手改掉雲端補強輪數。
5. S1 是純投影補洞，但要小心：量尺自身契約已把 `full_document_*`／`near_duplicate_items` 釘為「永不作為閘門」（`measure_record_quality.py:403-414`），**只補投影、不加門檻**是唯一合規寫法。

## C1c 萃取呼叫預算（`LOCAL_LLM_EXTRACTION_CALL_BUDGET`，新，預設 2；0＝不限制）

### 落點

| 項目 | 位置 | 現況 |
|---|---|---|
| 萃取迴圈本體 | `backend/services/summarization.py:3455` | `for chunk_index, chunk in enumerate(chunks, start=1)`；逐塊循序、非並行 [VERIFIED] |
| chunk 清單建構 | `summarization.py:3443-3448` | `_split_transcript_into_chunks(...)` 或 `[transcript]`；空清單回退 `[transcript]` [VERIFIED] |
| `total_chunks` 決定點 | `summarization.py:3453` | `total_chunks = len(chunks)`；被 progress、`chunk_count=`、落檔 header 三處共用 [VERIFIED] |
| 真正的 provider 呼叫 | `summarization.py:3464-3472` | `_generate_with_local_engine(engine, extraction_prompt, extraction_message, temperature=settings.LOCAL_LLM_EXTRACTION_TEMPERATURE, ...)` [VERIFIED] |
| 每塊前置訊息 | `summarization.py:3456-3458` | `_emit_progress(..., f"萃取逐字稿重點 {chunk_index}/{total_chunks}...")` ＋ `_build_chunk_extraction_message` (`:2457`) [VERIFIED] |
| 分塊上限決策 | `summarization.py:610`（`_build_local_context_plan`）；`extraction_ceiling` 讀取 `:644-646` | `LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS` 只做 `min()` 夾住 [VERIFIED] |
| 既有 skip log 樣式 A | `summarization.py:656-661` | `"結構性分塊萃取：未評估（skipped_reason=ceiling_disabled；...）"` [VERIFIED] |
| 既有 skip log 樣式 B | `summarization.py:662-668` | `"結構性分塊萃取：未觸發（skipped_reason=context_budget_below_ceiling；...）"` [VERIFIED] |
| 既有 skip log 樣式 C（守衛） | `summarization.py:3554-3563` | `"地端補強不回退守衛：未評估（skipped_reason={coverage_mode_off｜empty_or_unavailable_expectation_set}）"` [VERIFIED] |
| 呼叫計數器（現成） | 歸零 `:3408`、累加 `:4215`、輸出 `:3665` | `_lmstudio_logical_generations` **只在 lmstudio 路徑累加**（`_summarize_with_ollama` `:3991` 起無累加）⇒ 不能當跨 OS 預算依據 [VERIFIED] |
| 觀測落檔樣式 | `summarization.py:2895-2934`（header `:2917-2923`） | `chunk_count={chunk_count} raw_notes={len(raw_notes)} merged_tokens=…` [VERIFIED] |
| metrics 行樣式 | `summarization.py:3662-3676` | `chunk_count=`／`logical_generations=`／… ＋ 動態 `cov_*`（`:3675`） [VERIFIED] |
| 開關登錄位置 | `backend/core/config.py:647-670`（P7-B 區塊）；`.env.example:136-150` | 新開關照此區塊與註解風格新增 [VERIFIED] |

### 目前有沒有「呼叫數上限／中止」機制？

| 既有機制 | 位置 | 語意 | 可否沿用 |
|---|---|---|---|
| `LOCAL_LLM_MAX_MERGE_ROUNDS` | 設定 `backend/core/config.py:323-325`；生效 `summarization.py:2771-2779` | **fail loudly**（拋 `LOCAL_LLM_MERGE_NOT_CONVERGED`），不是跳過 [VERIFIED] | 不可直接沿用（C1c 要的是觀測式降級，不是讓整份紀錄 fallback） |
| LM Studio growth retry 上限 | `summarization.py:4398-4405` | 第二次仍失敗即拋 `LMSTUDIO_NO_FINAL_CONTENT` [VERIFIED] | 不可沿用（單呼叫層、拋錯） |
| 萃取側呼叫數上限 | — | **不存在** [VERIFIED：全檔 `budget` 掃描僅命中 token/context/merge 預算與上述兩處] | C1c 為全新機制 |

### 逾預算時「停止加塊」的正確插入點與不可破壞的保證

| 項目 | 位置 | 內容 |
|---|---|---|
| 建議插入點 | `summarization.py:3449-3452`（`chunks` 建好之後、`total_chunks` 之前） | 由「塊清單」推導「實際呼叫清單」與 `total_chunks`，讓三者（progress／`chunk_count=`／落檔 header）自動一致 [INFERRED] |
| 不建議 | `summarization.py:3455` 迴圈內 `break` 或 `:3453` 之後截斷 `chunks` | `chunk_count={total_chunks}`（`:3666`）與 `_dump_extraction_notes(chunk_count=total_chunks)`（`:3493`）會與真實呼叫數不符 [INFERRED] |
| 既有保證①：chunks 非空 | `summarization.py:1004-1008` | 空 ⇒ 拋 `LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED` [VERIFIED] |
| 既有保證②：每塊 ≤ input budget | `summarization.py:1010-1016` | 違反即拋（provider I/O 前） [VERIFIED] |
| 既有保證③：**去重疊串接 == 原文** | `summarization.py:1018-1032` | 「chunk 切塊未完整涵蓋原始逐字稿（遺失或改動內容）」⇒ 拋 [VERIFIED] |
| 檢查時機（關鍵） | `summarization.py:1067-1069`（`_split_transcript_into_chunks` 尾端 `:1036-1071`） | 檢查發生在**迴圈之前**；之後任何截斷都不會被攔下 ⇒ 靜默內容遺失 [VERIFIED] |
| 相容寫法 | 合併尾塊（把剩下的塊併成最後一次呼叫）而非丟棄 | 同時滿足「≤ budget 次呼叫」與保證③的覆蓋精神；`CEILING` 不動時行為不變 [INFERRED] |
| 觀測欄位建議落點 | `summarization.py:3664-3674` | 新增整數欄位（如 `extraction_calls=`／`extraction_call_budget=`）安全；**非整數字串欄位不會被 runner 解析**（`scripts/e2e/run_owned_e2e.py:158` 只抓 `key=-?\d+`），故 `skipped_reason=` 走 log 行、不進 metrics 值域 [VERIFIED] |

## C2a 對帳類別擴充（「筆記有、交付沒寫」新類別）

### 既有 5 類對帳（實讀；題目提示之 `:1508／:2137／:2171` 已核對）

| # | 類別 | 期望集合來源 | 抽取／比對函式（行號） | stats 鍵 | 產生位置（行號） |
|---|---|---|---|---|---|
| 1 | 待辦 | 萃取筆記待辦表格 | `_extract_action_table_keys` `:1377`；`_find_missing_action_keys` `:1200`；`_normalize_action_key` `:1073` | **不進** `_record_coverage_stats`（只在 `_validate_summary_quality` 內成問題字串） | `:1444`（抽期望）、`:1453`（比對）、`:1462-1469`（空集合 warning，mode=off 靜音）、`:1484-1504`（問題字串） |
| 2 | 議題 | 筆記「議題與決議」 | `_extract_notes_topic_items` `:1785`（`include_bold_titles=True`）；接受規則 `_topic_terms_cover` `:1304` | `expected_topic`／`missing_topic`／`missing_items_topic` | 迴圈 `:2064`（`for category, label, extractor, tail in (`）／`:2081`（呼叫抽取器）／`:2103`（比對）／`:2117-2135`（stats＋log＋issue） |
| 3 | 決議 | 筆記「議題與決議」 | `_extract_notes_decision_items` `:1799`；複合決議子句 AND `_split_match_clauses` `:1285` | `expected_decision`／`missing_decision`／`missing_items_decision` | 同上迴圈（`:2071-2078` 為第 2 筆 tuple 項） |
| 4 | 數字 | **逐字稿** | `_scan_transcript_number_items` `:1915`；比對 `_number_literal_is_covered` `:1850`；折疊 `_fold_record_for_number_coverage` `:1830` | `expected_number`／`missing_number`／`missing_items_number` | `:2137-2169`（註解 `:2137`） |
| 5 | 日期 | **逐字稿** | `_scan_transcript_date_items` `:1943`；比對 `_date_canonical_is_covered` `:1978` | `expected_date`／`missing_date`／`missing_items_date` | `:2171-2204`（註解 `:2171`） |

### 資料結構與閘門

| 項目 | 位置 | 內容 |
|---|---|---|
| 函式入口 | `summarization.py:2018`（`_validate_record_source_coverage`） | 回傳 issues（`enforce`）或 `[]`（`observe`） [VERIFIED] |
| mode 讀取／off 短路 | `:2034-2038` | `off` ⇒ `self._record_coverage_stats = {}` ＋ `return []`（連 log 都不記） [VERIFIED] |
| stats 容器 | `:2040-2041` | `stats: dict = {}`；`self._record_coverage_stats = stats` [VERIFIED] |
| 類別白名單 | `:2012-2016`（`_coverage_categories`） | `requested & {"topic","decision","number","date"}` ⇒ **新類別名稱必須進這個交集** [VERIFIED] |
| 預設類別字串 | `backend/core/config.py:293-297` | `LOCAL_LLM_RECORD_COVERAGE_CATEGORIES="topic,decision,number,date"` [VERIFIED] |
| 每類預覽上限 | `backend/core/config.py:298-303`；常數 `summarization.py:183`（`ACTION_ISSUE_PREVIEW_LIMIT=12`）、`:225`（`RECORD_COVERAGE_ITEM_PREVIEW_LIMIT`） | `LOCAL_LLM_RECORD_COVERAGE_ITEM_LIMIT` [VERIFIED] |
| issues 計數／回傳 | `:2205-2206` | `stats["issues_added"] = len(issues)`；`return issues if mode == "enforce" else []` [VERIFIED] |
| metrics 欄位 | `:2208-2233` | **硬列 9 鍵 tuple**（`:2219-2229`）；`if not any(key in stats …) return ""`（`:2227-2228`）[VERIFIED] |
| 守衛快照 | `:3347-3369`；**硬列 4 類** `:3361` | `for category in ("topic","decision","number","date")` [VERIFIED] |
| 回退判定 | `_refinement_regression_reason` `:3373-3392` | 未涵蓋數變多／等量互換 [VERIFIED] |

### 新增「筆記有、交付沒寫」一類要動哪些函式（且既有 5 類不變）

| 動作 | 位置 | 備註 |
|---|---|---|
| **放置位置（先決）** | 必須放在 `_validate_record_source_coverage`（`summarization.py:2018`；唯一呼叫端 `_validate_local_record` `:3341`，而 `_validate_local_record` 只在 `:3531／:3607／:3642` 被呼叫＝**地端專屬**） | **不可**仿待辦類別放進 `_validate_summary_quality`（`:1395`）：該函式雲端也在用（`:4815`／`:4853`），會直接改動雲端輸出 [VERIFIED] |
| 建新抽取器（確定性、零模型呼叫） | 放在 `_extract_notes_topic_items`（`:1785`）／`_extract_notes_decision_items`（`:1799`）旁，重用 `_parse_notes_items`、`_append_notes_item`（`:1670`）、`_strip_notes_item_quote_prefix`（`:1572`） | 沿用既有筆記格式知識（含 P6-A「空殼標記＋巢狀條列」樣式）[INFERRED] |
| 擴白名單 | `:2012-2016` | 不擴 ⇒ 新類別永遠不跑（靜默 no-op） [VERIFIED] |
| 新增一筆類別 tuple | `:2064-2078` 迴圈內的 tuple 清單 | 可完全重用既有 `_find_missing_action_keys` 比對器 [VERIFIED] |
| 決定是否改預設 | `backend/core/config.py:293-297` | 不改預設 ⇒ 既有 5 類 issues／stats／metrics 完全不變（`off` 仍 byte 級）；改預設 ⇒ 動到 metrics 行內容（見下表斷言） [INFERRED] |
| 決定是否進守衛基準 | `:3361` | 納入 ⇒ 不回退守衛的比較基準改變＝**語意變更**，須走 Plan／Review；不納入 ⇒ 守衛與 metrics 對新類別靜默漏算 [VERIFIED] |
| 決定是否進 metrics | `:2219-2229` | 新增 `cov_expected_<新類別>` 等鍵 ⇒ 既有 `EXPECTED_COVERAGE_FIELDS` 全字串斷言需更新 [VERIFIED] |

### 既有測試檔名與會受影響的斷言

| 測試檔 | 行號 | 斷言內容（會受影響者） |
|---|---|---|
| `tests/test_t20260923_p4a_record_coverage.py` | `:106-111` | `EXPECTED_COVERAGE_FIELDS`：`cov_*` metrics 行**全字串相等** [VERIFIED] |
| 同上 | `:347-358`（T13） | 問題字串類別順序 `["議題","數字","日期"]` 與 `issues_added == 3` [VERIFIED] |
| 同上 | `:361-376`（T14） | `observe` 下 `_record_coverage_metrics_fields() == EXPECTED_COVERAGE_FIELDS` [VERIFIED] |
| 同上 | `:377-393`（T15） | `off` ⇒ `messages == []`、stats 空、fields 空 [VERIFIED] |
| 同上 | `:395-414`（T15b） | **地端 pipeline 函式級 golden**（`prewave_stub` 對照；遮罩 wall-clock `:118-121`）[VERIFIED] |
| 同上 | `:417-437`（T15c） | metrics 行必須同時保有 `chunk_count=`／`logical_generations=`／`semantic_attempts=`／`merge_rounds=` [VERIFIED] |
| 同上 | `:439-456`（T16） | 空期望集合 warning 數 `>= 3` 與 `cov_expected_topic=0` [VERIFIED] |
| 同上 | `:458-486`（T17） | `set(stats) == {"expected_topic","missing_topic","missing_items_topic","issues_added"}`（**精確集合**，新增類別／新增鍵即失敗）[VERIFIED] |
| 同上 | `:485-496`（T18） | item limit 行為 [VERIFIED] |
| 同上 | `:497-522`（T19） | 待辦空集合 warning；`off` 靜音 [VERIFIED] |
| `tests/test_t20260923_p4a_paren_fix.py` | `:62`、`:114` | `_record_coverage_stats["expected_topic"]` 值 [VERIFIED] |
| `tests/test_t20260923_p4a_false_positive_fix.py` | `:54` | `expected_topic` 值 [VERIFIED] |
| `tests/test_t20260923_p7a_refine_no_regression.py` | `:108-130` | 以 `expected_topic`／`missing_topic`／`missing_items_topic` 餵快照的 stub（新類別若要進守衛需同步；`:115-117`）[VERIFIED] |
| `tests/test_t20260923_p4d_runner_quality_gate.py` | `:948-966`（`test_quality_helpers_pure_functions`） | 門檻純函式行為（與類別無關，但同在品質鏈上，改動後需回歸）[VERIFIED] |
| `scripts/e2e/run_owned_e2e.py` | `:158`（`METRICS_KEY_VALUE_PATTERN`） | 只解析 `key=整數`；新增 `cov_*` 整數鍵安全、字串鍵自動忽略 [VERIFIED] |

### 與 Stage 02 審查的交叉註記（本檔不重複其論證）

| 項目 | 內容 |
|---|---|
| 審查 I3（阻斷）指出 | C2a 的既有敘述「讓 R2 型（qwen）漏寫進入補強問題清單」與證據相反：qwen 場第 1／2 輪清單**已含**「議題遺漏：土地稅科倉庫漏水與土地卡重印」而模型仍未寫入 ⇒ 再加一筆**同粒度**類別不會改變該型失敗（出處：`.agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-01/review.md` §4 I3；`summarization.py` 端對應落點＝`:2064-2135` 的期望集合粒度）[VERIFIED：本檔實讀審查檔] |
| 對本落點圖的影響 | 落點（抽取器／白名單／stats／metrics／守衛）**不變**，但若要把槓桿對準 gemma「事實級」缺口，期望集合必須改由**事實級**抽取器產生（粒度決策屬 Plan 層，不在本檔） [INFERRED] |

## C2b 補強輪上限與呼叫預算（`LOCAL_LLM_MAX_REFINEMENT_ROUNDS` 2→3；`LOCAL_LLM_REFINEMENT_CALL_BUDGET` 新）

| 項目 | 位置 | 內容 |
|---|---|---|
| 補強迴圈（地端） | `summarization.py:3564` | `while issues and attempts < settings.LOCAL_LLM_MAX_REFINEMENT_ROUNDS:` [VERIFIED] |
| 不收斂保護 | `:3565-3574` | 問題集合與上一輪相同 ⇒ `break`（`:3566-3574`） [VERIFIED] |
| 輪次計數與進度 | `:3575`（`attempts += 1`）、`:3576` | [VERIFIED] |
| 補強呼叫 | `:3589-3596`（`_resolve_final_refinement_message` `:3578`） | `temperature=settings.LOCAL_LLM_REFINEMENT_TEMPERATURE` [VERIFIED] |
| 每輪後處理＋重驗 | `:3598-3609`（`_finalize_record_text` `:3600-3605`；`_validate_local_record` `:3607-3609`） | 後處理順序凍結（`dedupe_cross_section_items` 嚴格最後：`:3750`） [VERIFIED] |
| 輪數上限設定 | `backend/core/config.py:280-283`（預設 2） | [VERIFIED] |
| **雲端共用同一上限** | `summarization.py:4821`（`_summarize_with_gemini` `:4778`） | 2→3 會**順手改掉雲端補強輪數**（行為變更，非 byte 變更）；doc 亦載明「本地與雲端共用」`doc/規格與設計/系統架構與程式設計書.md:466／:827` [VERIFIED] |
| `NO_REGRESSION=false` ⇒ 無任何守衛 log：程式依據① | `:3546`（讀開關）、`:3548`（`best_snapshot = … if no_regression else None`） | 關閉時快照不取、`guard_comparable=False` [VERIFIED] |
| 程式依據② | `:3554`（`if no_regression and best_snapshot is None:` 才寫 skip log） | [VERIFIED] |
| 程式依據③ | `:3610`（`if no_regression and guard_comparable:` 包住全部守衛 log） | 關閉時四種守衛 log（`:3615／:3622／:3631／:3647`）都不可能產生 [VERIFIED] |
| 契約文字 | `backend/core/config.py:636-643`（末句「false＝一行回本波前（交付最後一版、無任何守衛 log）」）、程式註解 `:3550-3553` | [VERIFIED] |
| 測試鎖 | `tests/test_t20260923_p7a_refine_no_regression.py:232` | `assert not [line for line in messages if "不回退守衛" in line]` ⇒ **任何新 log 只要含字串「不回退守衛」就會踩到** [VERIFIED] |
| `COVERAGE_MODE=off` ⇒ 無 log／無 metrics：依據① | `:2034-2038` | off 短路：不跑比對、不記 log、`stats={}` [VERIFIED] |
| 依據② | `:2227-2233` | `_record_coverage_metrics_fields()` 回空字串（`off` 或未執行） [VERIFIED] |
| 契約文字／測試 | `backend/core/config.py:287-292`；`tests/test_t20260923_p4a_record_coverage.py:377-393`、`:395-414` | [VERIFIED] |
| **重要例外（易誤解）** | `:3554-3563` ＋ `tests/test_t20260923_p7a_refine_no_regression.py:236-254`（T05；斷言 `:252`） | `off` 時**仍會**有守衛 skip log `skipped_reason=coverage_mode_off`（P7-B §8 既定）；「off 無 log」只保證對帳自身不記 [VERIFIED] |
| 新預算插入點 | `:3564`（while 條件）或 `:3575-3576` 之後 | 需與不收斂保護（`:3566`）並存；skip 樣式沿用 `skipped_reason=` [INFERRED] |
| metrics 欄位相容性 | `:3662-3676`；`scripts/e2e/run_owned_e2e.py:158`、`:768-788` | 新增整數鍵安全；`validate_pipeline_metrics` 只檢查 `logical_generations`／`semantic_attempts`／`merge_rounds` [VERIFIED] |
| 開關登錄 | `backend/core/config.py`（本波新增區塊）＋`.env.example` | 全關須能 byte 級回 `ab2528b` [VERIFIED：既有 P7-B 區塊作法 `config.py:647-670`] |

## S1 E2E 投影補洞（零成本）

| 項目 | 位置 | 內容 |
|---|---|---|
| 投影函式 | `scripts/e2e/run_owned_e2e.py:928-976`（`project_record_quality_metrics`） | 回傳 11 鍵（`:956-976`）：`char_count`／`body_source_tag_count`／`table_source_tag_count`／`non_prefixed_tableish_source_tag_count`／`instruction_item_count`／`tagged_item_ratio`／`cross_section_duplicate_pairs`／`known_term_fix_hits`／`tag_traceability`／`unsupported_entities_count`／`unsupported_entities_sha256` [VERIFIED] |
| 儀器呼叫 | `:1194-1240`（raw 落檔 `:1196`；`quality_block["metrics"] = project…` `:1232`；門檻評估 `:1258`） | [VERIFIED] |
| tracked 證據落檔 | `:1301-1309`（`evidence_dir / "record_quality.json"` `:1302`；`observation_only` `:1306`） | [VERIFIED] |
| 門檻凍結（不得新增／放寬） | `:176-191`：`QUALITY_SOURCE_TAG_TEMPLATES` `:176`、`QUALITY_TAG_THRESHOLDS` `:179-190`、`QUALITY_TAG_CHECK_NAMES` `:191` | 註解 `:176-178` 明言「不得新增、不得放寬」；`evaluate_quality_checks` docstring `:979` 重申 [VERIFIED] |
| 產生處：density | `scripts/e2e/measure_record_quality.py:266-273` | 鍵名 `full_document_item_count`／`full_document_avg_item_chars`；條目定義 `extract_all_items` `:213-223` [VERIFIED] |
| 產生處：near-dup | `measure_record_quality.py:225-263` | 回傳 `count`／`exact_count`／`item_count`／`threshold`／`top`；門檻預設 `:511-516`（`--near-duplicate-threshold` 0.80，「純觀測，不影響 verdict」`:513`） [VERIFIED] |
| 輸出組成 | `measure_record_quality.py:471-489` | `**measure_full_item_stats(record_text)` `:477`；`"near_duplicate_items": measure_near_duplicates(...)` `:481-483` [VERIFIED] |
| 實際鍵名（實檔） | `data/cache/e2e/p7b-gemma31b-e8/quality/record_quality.json` | `full_document_item_count=23`、`full_document_avg_item_chars=60.7`、`near_duplicate_items.count=0`／`exact_count=0`／`item_count=23`／`threshold=0.8`、`instruction_item_count=21`、`char_count=2576` [VERIFIED] |
| 投影缺口（實檔） | `.agent/tasks/T20260923-1810-01-local-record-fidelity-density/e2e/attempt-P7B-gemma31b-e8/record_quality.json` | `metrics` 只有上述 11 鍵，**無**任何 `full_document_*`／`near_duplicate*` 鍵 [VERIFIED] |

### 「只補投影、不得新增／放寬門檻」——新增門檻會踩到的既有契約行

| 契約行 | 位置 | 為什麼會踩到 |
|---|---|---|
| 門檻清單本體 | `scripts/e2e/run_owned_e2e.py:176-190` | 註解即禁令；新增一項即改動凍結清單 [VERIFIED] |
| 必過清單自動擴張 | `scripts/e2e/run_owned_e2e.py:191` | `QUALITY_TAG_CHECK_NAMES` 由 thresholds 推導 ⇒ 新門檻自動成為 required 必過項，直接改變 `verdict`（既有 PASS／FAIL 語意變更） [VERIFIED] |
| 量尺自身語意 | `scripts/e2e/measure_record_quality.py:403-414`（notes 定義，兩處寫「**永不作為閘門**」） | 量尺已把這兩族釘為觀察值；加門檻＝就地改量尺語意 [VERIFIED] |
| 量尺 CLI 語意 | `scripts/e2e/measure_record_quality.py:513` | near-dup 門檻參數明文「純觀測，不影響 verdict」 [VERIFIED] |
| 量尺 schema 凍結 | `tests/test_record_quality_metrics.py:39-56`（`EXPECTED_KEYS`）、`:220-232`（`set(payload) == EXPECTED_KEYS`）、`:234-238`（notes 必須寫「永不作為閘門」） | 動量尺欄位語意即失敗 [VERIFIED] |
| runner 函式級 golden | `tests/test_t20260923_p4d_runner_quality_gate.py:585-597`（`set(result.summary.keys()) == GOLDEN_SUMMARY_KEYS` `:591`；`checks == GOLDEN_FULL_CHECKS` `:593`）、`:600-607` | 新增 `checks` 項會直接失敗 [VERIFIED] |

## byte 級回退證明怎麼寫

### 現況

| 事實 | 依據 |
|---|---|
| 專案**沒有** golden 目錄，也沒有任何 `ab2528b` 專屬基準檔 | `find` 無 `*golden*` 目錄；`rg -n "ab2528b" tests scripts backend doc .env.example` 無命中 [VERIFIED] |
| 既有 byte 級證明靠**同型 stub 對照**，不是外部 golden 檔 | `tests/test_t20260923_p4a_record_coverage.py:614-656`（`_run_local_pipeline_golden`：`prewave_stub=True` 把新方法換成本波前等效實作）＋`:118-121`（遮罩 wall-clock）[VERIFIED] |
| 既有唯一 sha256 golden | `tests/test_t20260922_2037_p4b_fidelity_tripwires.py:56`（`GOLDEN_LEGACY_SHA256`）＋`:347-377`（剝除 additive 鍵後 digest 必須相等） [VERIFIED] |

### 建議的全關組合與對應驗證

| 開關（全關／回前波值） | 設定值 | 應回到的行為 |
|---|---|---|
| `LOCAL_LLM_EXTRACTION_CALL_BUDGET` | `0` | 不限制呼叫數（＝P7-B 分塊行為） |
| `LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS` | `6000` | P7-B 既有值（`config.py:653-662`） |
| `LOCAL_LLM_MAX_REFINEMENT_ROUNDS` | `2` | 本波前（`config.py:280-283`） |
| `LOCAL_LLM_REFINEMENT_CALL_BUDGET` | `0` | 不限制（新增開關） |
| `LOCAL_LLM_RECORD_COVERAGE_MODE` | `off` | 對帳完全不跑、無 `cov_*`（`summarization.py:2034-2038`、`:2227-2233`） |
| `LOCAL_FIDELITY_TRIPWIRES` | `false` | 不呼叫忠實度檢查器（`config.py:304-308`） |
| `LOCAL_LLM_REFINEMENT_NO_REGRESSION` | `false` | 交付最後一版、無任何守衛 log（`config.py:636-643`） |

| 驗證手法 | 具體動作 | 對應既有測試（可照抄骨架） |
|---|---|---|
| A. 函式級紀錄＋log 逐字比對 | 以 `prewave_stub=True`（stub 掉 C1c／C2b 新分支）與實作各跑一次地端 pipeline，比 `summary` 與遮罩 wall-clock 後的 log | `tests/test_t20260923_p4a_record_coverage.py:395-414`（骨架 `:614-656`） |
| B. 雲端路徑 byte 不變 | `_finalize_record_text(mode="cloud")` 與 `_finalize_cloud_record_text` 對舊管線逐字元相等 | `tests/test_t20260922_record_quality.py:451-478` |
| C. 雲端三支提示詞 byte 不變 | 三開關任意組合下雲端訊息字串不變 | `tests/test_t20260923_p7b_generation_discipline.py:83-108` |
| D. 後處理順序／去重最後一步 | `calls == ["normalize","dedupe"]` | `tests/test_t20260922_record_quality.py:502-536` |
| E. 守衛關閉 ⇒ 無守衛 log | 對 log 掃「不回退守衛」 | `tests/test_t20260923_p7a_refine_no_regression.py:217-238`（斷言 `:232`） |
| F. runner off 模式函式級 golden | `summary` 頂層鍵集合與 `checks` 全集不變；off 不觸發儀器 | `tests/test_t20260923_p4d_runner_quality_gate.py:585-607`（常數 `:60-90`） |
| G. 量尺 schema／bytes | `EXPECTED_KEYS` 精確相等；additive 鍵剝除後 digest == `GOLDEN_LEGACY_SHA256` | `tests/test_record_quality_metrics.py:220-232`；`tests/test_t20260922_2037_p4b_fidelity_tripwires.py:347-377` |
| H. 分塊契約本身 | `CEILING=0` ⇒ 分塊上限完全依 context 推導；小 context 只做 `min()` | `tests/test_t20260923_p7b_tail_coverage.py:57-77`、`:78-94` |

### 若要「與 `ab2528b` 逐字一致」的具體寫法（本波新增，零模型呼叫）

| 步驟 | 做法 |
|---|---|
| 1 | 以 `git show ab2528b:backend/services/summarization.py`（及 `backend/core/config.py`、`scripts/e2e/run_owned_e2e.py`）取基準，落地為 `tests/fixtures/` 下的文字基準檔（目前 `tests/fixtures/` 只有 lmstudio JSON 與 `mock_transcripts.py`，需新增）[VERIFIED：`ls tests/fixtures`] |
| 2 | 對「新槓桿入口函式」做 source 級斷言：新函式在 `settings` 為前波值時必須 early-return（例如 `budget <= 0` 直接回原 `chunks`），並以 A 手法證明輸出逐字相同 [INFERRED] |
| 3 | 觀測落檔與 metrics 屬 additive：新增整數欄位安全（`run_owned_e2e.py:158`），但**不得**改既有鍵順序／既有 `cov_*` 字串格式（`tests/test_t20260923_p4a_record_coverage.py:106-111` 全字串相等）[VERIFIED] |
| 4 | 提醒：`DATA_DIR` 必須在 import backend 前設好（`tests/test_t20260923_p7b_tail_coverage.py:24-26`）[VERIFIED] |

## 最可能出錯的 2 個點（本檔主張）

| # | 風險 | 為什麼 | 證據 |
|---|---|---|---|
| 1 | C1c 若在 `for` 迴圈內 `break`／在 `total_chunks` 之後截斷 `chunks`，會同時踩到「觀測說謊」與「靜默遺失尾段」 | `chunk_count={total_chunks}`（`:3666`）與落檔 header `chunk_count=`（`:3493`）都以 `chunks` 全長為準；而 `_validate_chunk_postcondition` 只在 `:1067-1069`（迴圈之前）檢查「去重疊串接 == 原文」（`:1018-1032`），之後截斷不會被攔下，結果與 P7-B R1 的尾段稀釋症狀同型但更難歸因 | `summarization.py:3449-3455`、`:1018-1032`、`:3493`、`:3666` |
| 2 | C2a／C2b 的「硬列清單」漏同步：`_core_coverage_snapshot:3361`（4 類）與 `_record_coverage_metrics_fields:2219-2229`（9 鍵） | 新類別若只加在抽取側，守衛（不回退判定）與 metrics 會**靜默**漏算；若補進守衛，P7-A 契約「比較基準只有核心覆蓋率」（`config.py:636-643`）即被改義，且 `tests/test_t20260923_p7a_refine_no_regression.py:115-117` 的 stub 需同步 | `summarization.py:3361`、`:2219-2229`、`:3373-3392` |

補充（同樣容易忽略，列為次高）：`LOCAL_LLM_MAX_REFINEMENT_ROUNDS` 為**雲端共用**（`summarization.py:4821`；`doc/規格與設計/系統架構與程式設計書.md:466／:827`），2→3 會改變雲端補強輪數；若本波只想動地端，需另立地端專屬上限，否則屬跨路徑行為變更。另：C2b 新增的預算 skip log **不得**含字串「不回退守衛」，否則 `tests/test_t20260923_p7a_refine_no_regression.py:232` 會失敗。

## 證據索引（全部為本次實讀）

| 主題 | 位置 |
|---|---|
| 萃取迴圈／呼叫／metrics | `backend/services/summarization.py:3443-3455`、`:3464-3472`、`:3662-3676` |
| 分塊上限與 skip log | `summarization.py:610`、`:644-668`、`:931`、`:986-1033`、`:1036-1067` |
| 落檔觀測 | `summarization.py:2895-2934`、`:3492-3494` |
| 對帳 5 類與 stats | `summarization.py:1377`、`:1395`、`:1444-1504`、`:1785-1812`、`:2012-2016`、`:2018-2206`、`:2208-2233` |
| 守衛與補強 | `summarization.py:3319-3392`、`:3538-3676`、`:4821` |
| 後處理順序 | `summarization.py:3681-3760`（去重 `:3750`） |
| 設定 | `backend/core/config.py:183`、`:225`、`:280-311`、`:323-325`、`:636-670`；`.env.example:136-150` |
| E2E runner | `scripts/e2e/run_owned_e2e.py:158`、`:176-191`、`:740-800`、`:928-976`、`:1194-1240`、`:1301-1309` |
| 量尺 | `scripts/e2e/measure_record_quality.py:213-273`、`:403-414`、`:471-489`、`:511-516` |
| 實檔證據 | `data/cache/e2e/p7b-gemma31b-e8/quality/record_quality.json`；`.agent/tasks/T20260923-1810-01-local-record-fidelity-density/e2e/attempt-P7B-gemma31b-e8/record_quality.json` |
| 測試 | `tests/test_t20260923_p4a_record_coverage.py`、`tests/test_t20260923_p7a_refine_no_regression.py`、`tests/test_t20260923_p7b_tail_coverage.py`、`tests/test_t20260923_p7b_generation_discipline.py`、`tests/test_t20260922_record_quality.py`、`tests/test_record_quality_metrics.py`、`tests/test_t20260922_2037_p4b_fidelity_tripwires.py`、`tests/test_t20260923_p4d_runner_quality_gate.py` |
| P7-C 現有素材 | `.agent/tasks/T20260923-2050-01-local-extraction-adherence/plan.md`（rev1）、`evidence/chunk-replay-p7c/replay.json` |

（本檔未修改任何產品碼；未 commit。）
