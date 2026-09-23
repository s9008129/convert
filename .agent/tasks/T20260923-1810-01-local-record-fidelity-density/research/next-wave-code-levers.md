# P7-B 後續波：產品程式碼「零模型呼叫」可用槓桿稽核（唯讀）

- 角色：唯讀程式碼稽核員（subagent）。日期：2026-09-23（Asia/Taipei）。
- 分支／HEAD：`fix/qwen-local-quality-parity` / `66add73`（稽核時工作樹僅 `e2e/attempt-P7B-qwen27b-e8/` 未追蹤＝另一場 E2E 進行中，本檔未動它）。
- 硬約束遵守：無任何模型呼叫（未 curl LM Studio、未跑生成／E2E）、未改產品碼或既有文件、只新增本檔、未 commit。
- 題目：使用者要「地端會議紀錄品質至少跟雲端 Gemini 不要差太多」。已知 P7-B 後**字面事實覆蓋已接近或超越雲端**，雲端領先維度是「結構／密度／可讀性／不亂拆條／不亂用（待確認）」。本檔只回答一件事：**產品程式碼裡還有哪些確定性、零模型呼叫的槓桿可以拉近這段落差。**
- 標註：`[VERIFIED]`＝本檔作者實際讀檔／實算核對；`[INFERRED]`＝由既有事實推得、未實測；`[UNKNOWN]`＝現有證據不足。

## 白話結論（5 行內）

1. 產品目前有五道確定性後處理，全部只做「格式／可查核性」（術語、出處標註、表格標註、佔位符、跨節去重），**沒有一道在管密度或條目粒度**。
2. 密度／不亂拆條目前**只有提示詞紀律**（P7-B CORE-2a 三開關，預設開）在管；模板層也**沒有**「每節條目上限／每條最少字數／禁止單句獨立成條」這類硬規則。
3. 因此「雲端勝在結構／密度／可讀性」這段差距，**目前沒有任何確定性機制在處理**，也**沒有任何確定性機制能證明它變好了**（密度欄位沒進 E2E 證據投影）。
4. 最可行兩個新槓桿：(a) 把「密度／粒度」做成絆索、**先 observe**、再走既有補強迴圈（唯一能真正改寫密度又不新增事實的路）；(b) 「模板定值欄位回填」＋「佔位符作用域補洞」兩個純格式後處理（零新增事實、可逐字回退）。
5. 但後處理與量尺**直接耦合**：量尺讀交付檔，任何刪除型後處理都會立刻反映成 coverage 變動 → 密度類改善必須同時用同一把 coverage 尺證明「沒有換掉事實」。

## 現有後處理清單（含執行順序）

### A. 逐字稿層（`clean_transcript` 串起；呼叫端 `backend/services/task_processor.py:240-242`）

| 函式 | 行號 | 作用 |
|---|---|---|
| `to_taiwan_traditional` | `backend/core/text_postprocess.py:52` | OpenCC 台灣正體（只轉含簡體的行） |
| `remove_hallucination_lines` | `:106` | 幻覺黑名單句式移除 |
| `collapse_repetition_loops` | `:159` | 無句界連續重複迴圈壓縮（保留兩次） |
| `dedup_consecutive_sentences` | `:121` | 相鄰完全重複句壓縮 |
| `apply_official_term_fixes` | `:201` | 公務用字白名單＋詞彙表 `錯=>對` |
| `clean_transcript` | `:231` | 上列五者的固定順序編排（回傳統計 dict） |

### B. 紀錄層（雲端＋地端共用；由 `finalize_record` 串起）

| 函式 | 行號 | 作用／備註 |
|---|---|---|
| `remove_english_segments` | `:293` | 移除英文比例過高的行（詞彙表命中行受保護） |
| `sanitize_text_language` | `:333` | 常見英文詞彙換中文 |
| `to_taiwan_traditional` | `:52`（重用） | 台灣正體 |
| `has_excessive_english` | `:341` | **只 warning，不改字** |
| `ensure_record_structure` | `:429` | 缺欄位／缺章節時**主動補骨架行（含「（待確認）」）**；模板驅動 |
| `finalize_record` | `:474` | 上列固定順序包裝（紀錄級） |

### C. 紀錄層—地端專屬（僅 `mode="local"`；見下方執行順序）

| 函式 | 行號 | 作用／備註 |
|---|---|---|
| `apply_record_term_fixes` | `:548` | 模板 `record_term_fixes`（`templates.py:474`）＋詞彙表確定性誤辨 |
| `snap_source_tags_to_transcript` | `:1059` | 出處標註吸附到真實段落起點；`transcript` 空＝完全不作用 |
| ↳ 輔助 | `:862` `iter_transcript_segments`、`:918/:931` `_diversify_source_tag_times*`、`:798/:803/:822/:848` 時間換算 | 同一步的內部件 |
| `strip_source_tags_from_table_rows` | `:521`（gate：`:508` `template_forbids_table_source_tags`） | 只動 `^\s*\|` 表格列的來源標註 |
| `normalize_unfilled_placeholders` | `:391` | **雲端＋地端共用**：開頭欄位／標題行的 `（年）（月）…` 佔位符 →「（待確認）」 |
| `normalize_unfilled_placeholders_ext` | `:1448`（`_is_placeholder_head_line:1385`、`_placeholder_summary_table_rows:1405`、`_normalize_placeholder_table_row:1435`、`_collapse_nested_placeholder:1378`） | 地端 SUPPORTING-1：開頭 15 行內相鄰重複「（待確認）」收斂＋彙整表**第 2 欄**多層括號／半形冒號 |
| `dedupe_cross_section_items` | `:680`（判重件 `:629/:640/:653/:662`） | 跨節逐條重複抑制；**只對 `template=None` 或 `id=="general"` 生效**（`:696-699`） |

### D. 執行順序（`_finalize_record_text`，`backend/services/summarization.py:3681`）

1. `:3721` `finalize_record` →（`:475-479` remove_english → sanitize → to_taiwan → has_excessive_english(warn) → ensure_record_structure）
2. `:3722-3723` `if mode != "local": return normalize_unfilled_placeholders(...)` ← **雲端出口（byte 凍結線）**
3. `:3736` `apply_record_term_fixes`
4. `:3737` `snap_source_tags_to_transcript`
5. `:3738` `strip_source_tags_from_table_rows`
6. `:3739` `normalize_unfilled_placeholders`（共用那道）
7. `:3746-3749` `normalize_unfilled_placeholders_ext`（`LOCAL_LLM_PLACEHOLDER_NORMALIZE_EXT`）
8. `:3750` `dedupe_cross_section_items` ← **嚴格最後一步**（`:3700-3705` 註解；測試 `tests/test_t20260922_record_quality.py:509-540` 釘住 `["normalize","dedupe"]`）
9. `:3751-3774` 僅在有變動時寫一行 log（含術語／吸附／表格／佔位符／去重五個計數）

`[VERIFIED]` 全段順序與行號皆逐一 `sed` 核對；雲端 byte 凍結測試在 `tests/test_t20260922_record_quality.py:452-475`。

## 模板層結構約束現況

`[VERIFIED]` `MeetingTemplate`（`backend/core/templates.py:129-180`）可用來約束「紀錄成品」的欄位只有六類：`required_section_patterns`（存在性）、`extra_field_patterns`、`forbidden_patterns`、`record_header_fields`（`:147`，缺 → 補 `line`）、`record_sections`（`:148`，缺 → 補 `skeleton_lines`／`subfields`）、`docx_section_pattern`／`docx_label_pattern`（`:153-156`，DOCX 渲染用）、`record_term_fixes`（`:175`）。

`section_meeting`（`templates.py:385-479`）實際硬性約束：

- `required_section_patterns`（`:395-405`）：6 條「必須出現」樣式（標題／時間／主持人／彙整表表頭／指示及提醒／散會）→ 缺者進補強問題清單（`summarization.py:1413-1415`）。
- `forbidden_patterns`（`:406-414`）：1 條「彙整表內出現來源標註」→ 命中即視為問題（`summarization.py:1422-1424`）。
- `record_header_fields`（`:415-430`）：6 個欄位；缺者補骨架。**其中只有「出席人員：如後附簽到表」（`:426`）的 `line` 不含佔位符**，其餘五個都含「（待確認）」或骨架佔位符。
- `record_sections`（`:432-461`）：4 節（彙整表／科長轉知／指示及提醒／散會）；缺者補 `skeleton_lines`，節存在但子欄位缺者補 `subfields`。
- `docx_section_pattern`（`:463-465`）：**只有**「一、科長轉知」「二、科長指示」「臨時動議」「散會」開頭的行會被 DOCX 當成章節標題渲染；其餘編號行一律當一般內文（→ 模型若自創章節或跳號，成品會「扁掉」，是可讀性風險源）。
- `record_term_fixes`（`:474`）＋ `attachment`（`:476-479`，列管附件由本文 Markdown 確定性抽出）。

**沒有的規則**（本檔作者以 `rg '條目數|密度|最少字數|一案一條|拆條'` 全庫掃描核對）：沒有每節條目數上限、沒有每條最少／最多字數、沒有「禁止單句獨立成條」、沒有「同節條目相似度上限」。唯一的密度相關程式碼是**提示詞紀律**（`summarization.py:161-178`）與 E2E 儀器的觀測值（`scripts/e2e/measure_record_quality.py:266-273`）。`[VERIFIED]`

**若要加，應加在哪一層？（`[INFERRED]`，需 Planner 核可）**

- 「生成約束」（一案一條、每節條目上限、最少字數、不得跳層）→ **提示詞／模板層**。理由：這些是「塑造輸出」而不是「事後整形」；且已有先例（地端紀律區塊 `summarization.py:161-178`、模板增補 `templates.py:393`＝`SECTION_MEETING_GENERATION_EXTRA`，本文 `backend/core/prompt_templates/section_meeting.py:101-109`）。注意：`SECTION_MEETING_SYSTEM_PROMPT`／`generation_message_extra` 是**雲端共用**的，要動它必須先確認雲端 byte 契約（見下節風險 3）；新的地端規則請走 `_local_record_discipline_rule`（`:2525`）那條 local-only 區塊。
- 「格式一致性」（佔位符、編號階層、表格樣態、欄位定值）→ **後處理層**（`_finalize_record_text` 的地端分支，`:3723` 之後）。理由：後處理無權產生新內容，但能保證格式；`ensure_record_structure`（`:429`）本身是**雲端共用**，任何字面規則不得加在裡面。
- 「密度／粒度」→ **不能只靠後處理**（合併條目＝改寫內容，會動事實）。要能修，只能走既有補強迴圈（見槓桿 L1），或用「生成約束」讓模型一次寫對。

## 地端可調開關全表（含預設與生效行號）

`[VERIFIED]` 以下每一列都以 `config.py` 宣告行＋`rg` 找出生效位置核對（`backend` 內）。標「✗」者＝找不到生效位置。

### 管線預算／分塊

| 開關 | 預設 | `config.py` | 生效位置 | 作用 |
|---|---|---|---|---|
| `LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS` | 8192 | :198 | `summarization.py:624,744,2737` | 實際可用 context（LM Studio 有 loaded instance 時以 instance 為權威 `:3419-3427`） |
| `LOCAL_LLM_RESERVED_OUTPUT_TOKENS` | 3072 | :202 | `:625,742,2735` | 保留給輸出的下限 |
| `LOCAL_LLM_CHUNK_OVERLAP_LINES` | 4 | :206 | `:1063` | 分塊重疊行數 |
| `LOCAL_LLM_CHUNK_INPUT_TOKENS_CEILING` | 0（＝依 context 推導） | :220 | `:636` | **舊鈕**：分塊輸入上限 |
| `LOCAL_LLM_OUTPUT_TOKENS_CEILING` | 8192 | :225 | `:751` | 單次生成輸出天花板 |
| `LOCAL_LLM_CONTEXT_SAFETY_MARGIN_TOKENS` | 256 | :230 | `:748,2952` | 預算安全邊界 |
| `LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS` | **6000** | :653 | `:646-661` | **P7-B CORE-1b**：結構性分塊上限＝`min(context 推導, 本值)`；0＝停用 |
| `LOCAL_LLM_TRANSCRIPT_IN_FINAL_GENERATION` | True | :234 | `:2970,3002` | 最終生成／補強是否雙輸入（筆記＋逐字稿） |
| `LOCAL_LLM_ZERO_LOSS_NOTES_PASSTHROUGH` | True | :239 | `:2866` | 筆記塞得下就跳過有損整併 |
| `LOCAL_LLM_MAX_MERGE_ROUNDS` | 3 | :323 | `:2771` | 整併輪數上限（超過拋錯） |

### 取樣與時序

| 開關 | 預設 | `config.py` | 生效位置 | 作用 |
|---|---|---|---|---|
| `LOCAL_LLM_SAMPLING_TOP_P` | 0.8 | :251 | `:3980,4530` | LM Studio top_p |
| `LOCAL_LLM_SAMPLING_TOP_K` | 20 | :255 | `:3981,4532` | LM Studio top_k |
| `LOCAL_LLM_SAMPLING_REPEAT_PENALTY` | 1.08 | :314 | `:3982` | 僅 Ollama |
| `LOCAL_LLM_EXTRACTION_TEMPERATURE` | 0.6 | :259 | `:3475` | 萃取 |
| `LOCAL_LLM_GENERATION_TEMPERATURE` | 0.7 | :263 | `:3514` | 最終生成 |
| `LOCAL_LLM_REFINEMENT_TEMPERATURE` | 0.7 | :267 | `:3593` | 補強 |
| `LOCAL_LLM_MERGE_TEMPERATURE` | 0.6 | :271 | **✗ 死旋鈕**：整併實際寫死 `temperature=0.1`（`:2815`） | 文件承諾與實際不符 |
| `LOCAL_LLM_CORRECTION_TEMPERATURE` | 0.3 | :275 | `task_processor.py:268` | 逐字稿語意校正 |
| `LOCAL_LLM_MAX_REFINEMENT_ROUNDS` | 2 | :280 | `:3564` | 補強輪數上限 |
| `LOCAL_LLM_KEEP_ALIVE` | `30m` | :319 | `:4064,5338`；`main.py:111` | Ollama 模型保留 |
| `LOCAL_LLM_DISABLE_THINKING` | True | :333 | `:4052,4528` | 關思考輸出 |
| `LOCAL_LLM_REQUEST_TIMEOUT` | 1800.0 | :343 | `:414,460,472` | 單次呼叫總逾時 |
| `LOCAL_LLM_STREAM_IDLE_TIMEOUT` | 120.0 | :347 | `:3832` | 串流閒置逾時 |
| `LOCAL_LLM_MIN_TOKENS_PER_SECOND` | 5.0 | :351 | `:3894` | 吞吐過低警告（疑似 CPU offload） |
| `LOCAL_LLM_DEGRADED_CONTEXT_TOKENS` | 8192 | :355 | `:5453` | warmup 失敗降級 context |
| `LOCAL_LLM_WARMUP_TIMEOUT` | 600.0 | :359 | `:5341` | 預熱逾時 |
| `LOCAL_LLM_TRANSIENT_RETRIES` | 2 | :363 | `:3156,3913` | 瞬時錯誤重試 |
| `LOCAL_LLM_RETRY_BACKOFF_SECONDS` | 5.0 | :367 | `:3164,3176` | 線性退避基數 |

### 品質／後處理／紀律（本題主戰場）

| 開關 | 預設 | `config.py` | 生效位置 | 作用 |
|---|---|---|---|---|
| `LOCAL_LLM_RECORD_COVERAGE_MODE` | `enforce` | :287 | `:2034`（`off` 於 `:2030-2033` 直接返回） | 逐條對帳：off／observe／enforce |
| `LOCAL_LLM_RECORD_COVERAGE_CATEGORIES` | `topic,decision,number,date` | :293 | `:2014` | 對帳類別 |
| `LOCAL_LLM_RECORD_COVERAGE_ITEM_LIMIT` | 12 | :298 | `:2050` | 問題字串每類別最多列幾項 |
| `LOCAL_FIDELITY_TRIPWIRES` | True | :304 | `:2246` | P4-B 忠實度絆索（自創專名／無依據歸屬／數字單位） |
| `LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED` | True | :309 | `text_postprocess.py:887-900`（吸附規則 6） | 同標籤同時戳去重複化 |
| `LOCAL_LLM_REFINEMENT_NO_REGRESSION` | True | :636 | `:3546`（跳過路徑 log `:3548-3560`） | 補強輪不回退守衛 |
| `LOCAL_LLM_DUMP_EXTRACTION_NOTES` | False | :664 | `:2910` | 萃取筆記落檔（觀測；不改輸出） |
| `LOCAL_LLM_ONEPERITEM_RULE` | True | :677 | `:601`（萃取）、`:2535`（生成＋補強） | **密度相關唯一開關**：一案一條（提示詞） |
| `LOCAL_LLM_SPEAKER_DISCIPLINE_RULE` | True | :682 | `:2537` | 主詞不得為「（待確認）」等 |
| `LOCAL_LLM_ANTI_DUPLICATE_RULE` | True | :687 | `:2539` | 同件事不得跨節重複 |
| `LOCAL_LLM_PLACEHOLDER_NORMALIZE_EXT` | True | :696 | `:3746-3749` | 佔位符正規化（後處理） |

**密度／條目粒度**：`[VERIFIED]` **沒有專屬開關**；只有 `LOCAL_LLM_ONEPERITEM_RULE`（提示詞側）與分塊上限（結構側）間接影響。**沒有**任何「後處理把碎條合併／拆條守門」的機制。

## 可行新槓桿（確定性後處理優先，含風險／回退／可觀測性）

> 全部遵守：模型無關、平台無關、預設關閉時 byte 級回退、雲端 byte 不變（見下節）。分級：L1／L2 為本稽核建議的優先項。

### L1【首選】密度／粒度絆索 —— 接進既有補強迴圈，先 `observe`

- 做法：新增 `LOCAL_LLM_RECORD_DENSITY_MODE`（`off`／`observe`／`enforce`，**預設 `observe`**；與 `LOCAL_LLM_RECORD_COVERAGE_MODE` 同語意家族）。在 `_validate_summary_quality`（`summarization.py:1395`）同一層新增一條問題字串，門檻來源＝**既有儀器定義**（`scripts/e2e/measure_record_quality.py:266-273` 的 `full_document_item_count`／`full_document_avg_item_chars`），不另造新尺。
- 為什麼這是最有效的一條：密度是「寫作風格」問題，後處理無權刪內容；唯一能改寫又不新增事實的路是既有補強迴圈（`:3564`），而且它已被 P7-A 不回退守衛保護（`:3546-3660` 只保**事實**，不會被密度改善換掉）。
- 具體門檻建議（`[INFERRED]`，需 Planner 定案）：以雲端基線為錨（雲端 28 條／65.1 字，`research/format-density-comparison.md` §1.1）→ qwen 場「leaf ≤62 且平均 ≥48 字」（plan 既有目標）、gemma 場「不劣化」。
- 風險：① `enforce` 會改變既有場次問題集合與輪數（＝牆鐘成本）；② 預設若為 `enforce` 會破壞 `observe` 的「品質零變化」契約（該契約的界線見 `config.py:636-643`：observe 的「零變化」僅指**問題清單**，交付版本仍受守衛影響）；③ 問題字串過長會擠壓 context（`_resolve_final_refinement_message:2985`）。
- 回退：一行 `off`（並遵守風險 1：`off` 時不得留任何 metrics／log）。
- 可觀測性：沿用 `cov_*` 的 metrics 模式（`:2208` `_record_coverage_metrics_fields`）；E2E 需 L6 才看得見。
- 落地前置：必須先有一場 qwen／gemma `observe` 場，證明「密度問題字串」的觸發率與判準不會亂咬。

### L2【首選】模板定值欄位回填（零新增事實的純格式後處理）

- 做法：在 `_finalize_record_text` 地端分支新增一步（建議插在 `:3739` 之後、`:3746` 之前，不得晚於 `dedupe`）：若某 `record_header_fields[i].pattern` 命中某行，且該行值仍是佔位符，而**模板宣告的 `line` 不含佔位符** → 以模板 `line` 取代該行。
- 目前唯一會命中的欄位：`templates.py:426`「出席人員：如後附簽到表」（其餘五個欄位的 `line` 都含「（待確認）」→ 規則自動不作用）。模板驅動、模型無關，且**不新增任何事實**（模板自己宣告該欄位是定值）。
- 效果：直接消掉地端紀錄開頭最常見的無資訊佔位符之一（`research/format-density-comparison.md` §1.1：地端檔頭佔位符 14-15 個 vs 雲端 11-12 個）。
- 風險：低。唯二注意：① 只認「模型自己寫了佔位符」的行（模型若已寫對，規則不作用）；② 欄位判定必須用模板 pattern，不得寫死字串（否則模板漂移即失效）。
- 回退：`LOCAL_LLM_RECORD_FIELD_CONSTANT_BACKFILL`（預設可為 True，或先 `observe` 只計數）。
- 可觀測性：log 命中數＋量測器的「（待確認）」分區計數（既有方法）。

### L3 佔位符／表格標註作用域補洞（P7-B 已自認的兩個界線）

- 缺口 (i)：彙整表**第 1 欄**的「（（待確認））」不在 `normalize_unfilled_placeholders_ext` 作用域（`config.py:696-703` 明文；`text_postprocess.py:1435-1446` 只改第 2 欄）。
- 缺口 (ii)：表格列定義只認 `^\s*\|`（`text_postprocess.py:496-505`，`TABLE_ROW_PATTERN:498`＋相容別名 `:499`）；全形「｜」或行內 ≥2 管線字元的「真表格列」是殘餘缺口（儀器自己在 `measure_record_quality.py:455-467` 標成已知殘餘，`non_prefixed_tableish_source_tag_count` 就是它的觀察值）。
- 做法：把 `_normalize_placeholder_table_row`（`:1435`）與 `strip_source_tags_from_table_rows`（`:521`）的表列判定，從 `^|\s*\|` 擴到「表格樣態列」（行首管線 **或** 行內 ≥2 管線），並維持「非表格列一字不改」。模板 gate（`:508`）不動。
- 風險：中。表格列會**原樣**流入列管附件（`backend/api/routes.py:397-409`；`text_postprocess.py:530-536` 註解即為此理由）→ 表格類改動必須連**附件 DOCX** 一起抽樣驗。
- 回退：開關（可與 (i)(ii) 分開）。
- 可觀測性：既有 `table_source_tag_count`／`non_prefixed_tableish_source_tag_count`（`:392`、`:455-467`）＋佔位符分區計數。

### L4 條目粒度離線判準（只讀，零產品風險）

- 做法：把「一案一條／不亂拆條」量成可比較的三個值：每條字元數分佈、`<30` 字條目比例、動詞開頭無主詞比例。定義已在 `research/format-density-comparison.md` §1.1 手算過（雲端 4%／地端 qwen 19%），建議直接固化成儀器欄位（`measure_record_quality.py` 既有 `extract_body_items`／`count_instruction_items` 可重用，`:157-186`）。
- 用途：L1 的 `observe` 場以此判讀；`enforce` 門檻也以此為來源（避免另立一把尺）。
- 風險：零（不改產品輸出）。

### L5 補強問題字串必須「可執行」（L1 的成敗關鍵）

- 做法：密度問題字串要帶**合併指示**（例：「同一議題被拆成 3 條短句（行 12／13／14），請合併為 1 條並保留全部事實」），沿用既有「片段預覽＋每類別上限」模式（`:2050-2058`、`ACTION_ISSUE_PREVIEW_LIMIT:183`／`RECORD_COVERAGE_ITEM_PREVIEW_LIMIT:225`）。
- 理由：補強輪是「整份重生成」，只說「太碎」模型常以「加字」回應（反而更冗長）；明確指示合併才可能同時保住覆蓋率與可讀性。
- 風險：issue 文案過長 → context 擠壓（同 L1）；且密度問題不得與事實問題互相排擠（總量需上限）。

### L6 E2E 證據投影補齊密度／近似重複欄位（觀察值；不得成為閘門）

- 現況 `[VERIFIED]`：`scripts/e2e/run_owned_e2e.py:928-980` 只投影 11 個欄位；**密度欄位（`full_document_item_count`／`full_document_avg_item_chars`）與 `near_duplicate_items` 不在其中**，只存在 `<runtime_dir>/quality/record_quality.json`（例：gemma P7-B e8 ＝ 23 條／60.7 字／near_dup 0；同一場儀器原始值我實讀核對）。
- 做法：投影補上這三個數（＋`exact_count`）。**不得新增／放寬任何門檻**（`QUALITY_TAG_THRESHOLDS` `:179-190` 凍結）。
- 風險：低（純投影）。若不補，L1 的密度目標在 E2E 證據裡不可見 → 下一波無法用同一把尺驗收。

### L7 兩個「小而真」的既有缺陷（非密度，但影響可讀性／可查核性）

- (i) 死旋鈕 `LOCAL_LLM_MERGE_TEMPERATURE`（`config.py:271-274` 宣稱 0.6；實際整併寫死 0.1，`:2815`）。選項 A：移除承諾；選項 B：接線但**預設改為 0.1**（行為 byte 不變、但屬語意變更 → 需 Planner）。現況＝文件與行為不一致，任何人調它都不會生效。`[VERIFIED]`
- (ii) 歸因缺口：目前**無法分辨**紀錄裡的「（待確認）」是模型寫的，還是 `ensure_record_structure`（`:429-506`）補的骨架。建議在**地端分支**加一個純計數（比較 `finalize_record` 前後佔位符數），log-only、雲端不受影響（注意：不得掛在 P7-A 守衛路徑上）。
- (iii) 既有限檻未過的維度（gemma P7-B e8：`on_start_tag_ratio=0.84 < 0.95`、`exact_tag_ratio=0.08`）不得靠放寬門檻解決（`run_owned_e2e.py:177-190`）。可行的確定性方向是延伸 `snap_source_tags_to_transcript`（`:1059`）對「位移超限／不可回溯」標註的處理；但這會動到「可查核性契約」的文字 → 屬語意變更，僅列為候選，需 Planner 先定語意。`[INFERRED]`

## 與量尺的耦合與影響

1. `[VERIFIED]` `scripts/e2e/measure_coverage.py` **不套用**產品後處理：它直接讀交付的 Markdown（`:12`、`:869-905`），只用 `to_taiwan_traditional`（`:137-157`）做**兩邊對稱**正規化。⇒ **任何後處理的刪除／改寫都會直接改變量到的 coverage**；反之，把一條長句拆開或把一段合併都可能造成字面 probes 的假遺漏（probes 語意＝group 內 AND、group 間 OR，`:35-40`）。
2. `[VERIFIED]` `scripts/e2e/measure_record_quality.py` **共用產品函式**：`dedupe_cross_section_items`（`:344`）、`measure_tag_traceability`（`:350`）、`SOURCE_TAG_PATTERN`／`TABLE_ROW_PATTERN`（`:24-30`）。⇒ 改產品語意，儀器自動跟著變（同一把尺的好處；壞處＝**歷史數字基準改變**，必須在報告註記或重算，例如 `research/format-density-comparison.md` 的 `cross_section_duplicate_pairs` 對 section_meeting 恆 0 就是這個耦合的歷史教訓，P7-B 才另加模板無關的 `near_duplicate_items`）。
3. `[VERIFIED]` 產品自己的閘門也吃**後處理後**的文本：`:3521` 收尾 → `:3530-3533` 驗證；補強輪 `:3600` → `:3607` 重驗。⇒ 刪除型後處理會**觸發補強輪**（成本↑）；而回退守衛只比「未涵蓋事實數」（`:3546-3560`、`_refinement_regression_reason:3373`），**不看守密度**。
4. ⇒ 驗收建議三件式（L1 上線時）：`coverage_core` 不降 ＋ 密度欄位達標 ＋ `near_duplicate_items.count` 不升。**任何只證明密度變好、沒證明事實覆蓋不變的驗收都不成立。**
5. 表格類槓桿（L3）另有一條耦合：交付 Markdown → 列管附件（`routes.py:397-409`）與 DOCX（`docx_converter.py:131-132` 用 `docx_section_pattern`／`docx_label_pattern`）都是**同一份文字**確定性轉出。⇒ 改表格／編號，必須同時抽驗附件與 DOCX 版面。

## 語意不變式風險

| # | 不變式 | 出處 | 新槓桿的硬性要求 |
|---|---|---|---|
| 1 | `LOCAL_LLM_RECORD_COVERAGE_MODE=off` ⇒ 本波前 byte 級（連 metrics 欄位都不得出現） | `summarization.py:2026-2033`；`config.py:287-292` | 掛在 `_validate_summary_quality`（`:1395`）的新密度絆索必須自行尊重 `off`，且 `off` 時不得新增任何 log／metrics |
| 2 | `LOCAL_LLM_REFINEMENT_NO_REGRESSION=false` ⇒ **不得有任何守衛 log** | `summarization.py:3548-3550`；P7-A 契約 | 新 log 不得掛在守衛分支上（含「未評估」那條） |
| 3 | 雲端三支提示詞在任何開關組合下 **byte 不變**；`CLOUD_EXTRACTION_PROMPT = LOCAL_EXTRACTION_PROMPT + …` | `summarization.py:298-305`；`tests/test_t20260923_p7b_generation_discipline.py:83,101,156` | 地端規則只能以 local-only 區塊追加（`:589-607`、`:2525-2543`）；**不得就地改** `LOCAL_EXTRACTION_PROMPT`／`SECTION_MEETING_SYSTEM_PROMPT`／`generation_message_extra` |
| 4 | `_finalize_record_text(mode != "local")` 與 v4.8.0 **byte 相同** | `summarization.py:3722-3723`；`tests/test_t20260922_record_quality.py:452-475` | 新後處理**只能**加在 `:3723` 之後的地端分支 |
| 5 | 順序凍結：`dedupe_cross_section_items` 嚴格最後；佔位符修復必須在它之前 | `summarization.py:3700-3705,3750`；測試 `:509-540` | 新步驟必須插在 `dedupe` 之前，且不得破壞「切除尾端括號後完全相等」的判重前提 |
| 6 | `dedupe_cross_section_items` 作用域 **general-only** | `text_postprocess.py:696-699` | 擴到 `section_meeting` ＝語意變更 → 必須走 Planner |
| 7 | 表格標註清理只對「模板契約禁止」者生效、只動 `^\s*\|` 列 | `text_postprocess.py:508-519` | L3 擴作用域＝語意變更（作用域變寬）→ 需 Planner 核可，且必須附附件抽驗 |
| 8 | E2E 既有 5 項來源標註門檻**不得新增、不得放寬** | `scripts/e2e/run_owned_e2e.py:177-190` | L6 只准補**投影**，不准加門檻；coverage 永遠 observation（`coverage_observation.json` 的 `gate_effect=none`） |
| 9 | 不得平台分流／模型名分流 | `tests/test_t20260923_p7b_generation_discipline.py:182-193` | 所有新機制必須走同一碼路徑（macOS／LM Studio 與 Windows／Ollama 共用） |
| 10 | 逐字稿校正呼叫介面凍結 | `backend/services/task_processor.py:259,262` | 不得改動（本稽核未動） |
| 11 | 萃取筆記落檔（CORE-1a）預設關、且不改輸出 | `config.py:664-672`；`summarization.py:2910` | 任何新觀測不得讓預設路徑多寫檔或改輸出 |

`[VERIFIED]` 上列 1／2／3／4／5／9／10／11 皆以讀檔核對；6／7／8 為「現況即契約」的界線，任何擴張都屬語意變更。

## 證據索引

- `backend/core/text_postprocess.py`：函式行號見本檔第 2 節（`52/77/106/121/159/201/231/293/333/341/379/391/429/474/508/521/548/629/640/653/662/680/862/887/918/931/1059/1241/1378/1385/1394/1405/1435/1448`）；表格列定義 `:496-505`；general-only 去重 `:696-699`；吸附容忍 `:781`／位移上限 `:785`／同標籤同時戳上限 `:791`。
- `backend/services/summarization.py`：`_finalize_record_text` `:3681-3774`；雲端出口 `:3722-3723`；地端五步 `:3736-3750`；`_validate_summary_quality` `:1395-1470`；`_validate_local_record` `:3319-3346`；`_core_coverage_snapshot` `:3347`；`_refinement_regression_reason` `:3373`；`_summarize_with_local_pipeline` `:3395-3678`（萃取 `:3456`、整併 `:3483`、落檔 `:3492`、生成 `:3510`、收尾 `:3521`、驗證 `:3530`、守衛 `:3546-3660`、補強 `:3564-3607`）；整併寫死 `temperature=0.1` `:2815`；地端紀律常數 `:148-178`；`_local_record_discipline_rule` `:2525-2543`；`_local_extraction_prompt` `:589-607`；`_estimate_cloud_min_summary_chars` `:4700-4711`。
- `backend/core/config.py`：本檔第 4 節全表（行號逐一列出）。
- `backend/core/templates.py`：`RecordFieldSpec` `:33-37`；`RecordSectionSpec` `:41-49`；`MeetingTemplate` `:129-180`；`section_meeting` `:385-479`（`record_header_fields:415-430` 含「出席人員：如後附簽到表」`:426`；`record_sections:432-461`；`docx_section_pattern:463-465`；`record_term_fixes:474`；`attachment:476-479`）。
- `backend/core/prompt_templates/section_meeting.py`：`SECTION_MEETING_SYSTEM_PROMPT` `:25`；`SECTION_MEETING_EXTRACTION_EXTRA` `:88`；`SECTION_MEETING_GENERATION_EXTRA` `:101-109`；`build_tracking_attachment` `:203-250`。
- `scripts/e2e/measure_coverage.py`：metric 語意 `:12-40`；`_read_text` `:869-874`；不使用產品後處理（只 import `to_taiwan_traditional` `:137-157`）。
- `scripts/e2e/measure_record_quality.py`：共用產品定義 `:24-30,77-81`；`extract_body_items` `:157`；`count_instruction_items` `:169-186`；`measure_near_duplicates` `:225-263`；`measure_full_item_stats` `:266-273`；輸出面 `:471-490`；已知殘餘缺口 `:455-467`。
- `scripts/e2e/run_owned_e2e.py`：門檻凍結 `:176-191`；投影 `:928-980`；儀器呼叫與落檔 `:1194-1240,1285-1309`。
- `backend/api/routes.py`：列管附件確定性轉出 `:389-421`。
- `backend/services/docx_converter.py`：DOCX 章節／標籤樣式 `:40-41,127-133`。
- 既有證據檔（未修改）：`.agent/tasks/T20260923-1810-01-local-record-fidelity-density/e2e/attempt-P7B-gemma31b-e8/{run_summary.json,record_quality.json,coverage_observation.json}`；密度原始值 `data/cache/e2e/p7b-gemma31b-e8/quality/record_quality.json`（23 條／60.7 字／near_dup 0）`[VERIFIED]` 實讀。
- 既有研究（未修改）：`research/format-density-comparison.md`（雲端 vs 地端維度對照、§1.1 主表）、`research/placeholder-audit.md`、`research/qwen-specific-gap.md`、`research/crossos-ollama-audit.md`。
- 測試契約（唯讀引用）：`tests/test_t20260922_record_quality.py:446-540`；`tests/test_t20260923_p7b_generation_discipline.py:83/101/138/156/182/196`；`tests/test_t20260923_p7b_placeholder_normalize.py`（T1–T6）；`tests/test_t20260922_record_quality.py:1306-1308`。
- 稽核限制：未跑任何模型／E2E／backend 服務；未跑 pytest（避免與 GPU 上的 qwen 場競用資源）；行號以 HEAD `66add73` 為基準，若後續 commit 位移請以 `git show 66add73:<file>` 複核。
