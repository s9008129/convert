# Stage 04 實作紀錄 — W1（P4-A 覆蓋率對帳擴類／P4-B 絆索接線／P4-C W-1・W-2 引擎同源）

- 任務：`T20260922-2037-02-local-model-quality-parity`（P4 波）；角色：W1 實作者（產品側）。
- 授權來源：`handoff.md`（220 行；plan **PLAN_REVISION 15**／sha256 `a7ea4be6…35fb`）；本檔為 W1 實作紀錄（§7.4 指定產出）。
- 基準：HEAD `6e12931b4c97`（分支 `fix/qwen-local-quality-parity`）＋工作樹；**未 commit**。行號一律為本工作樹現況。
- 所有權：只改 `backend/services/summarization.py`、`backend/core/config.py`（＋本人兩個測試檔）；未碰 `text_postprocess.py`、`fidelity_checks.py`、`scripts/e2e/**`、`task_processor.py`、雲端提示詞、任何既有門檻值。

## 1. 變更清單（檔案與行號）

| 檔案 | 行號（工作樹） | 內容 |
|---|---|---|
| `backend/core/config.py` | L132-141 | `LOCAL_LLM_RECORD_COVERAGE_MODE` validator（off／observe／enforce；空白→enforce；非法值 raise） |
| `backend/core/config.py` | L284-318 | 新欄位：`LOCAL_LLM_RECORD_COVERAGE_MODE`／`_CATEGORIES`／`_ITEM_LIMIT`／`LOCAL_FIDELITY_TRIPWIRES`／`LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED`（P4-D 用）／`LOCAL_LLM_SAMPLING_REPEAT_PENALTY` |
| `backend/services/summarization.py` | L167-199 | P4-A 常數（單位錨定樣式、日期四樣式、佔位語、`LEGACY_OLLAMA_SAMPLING_OPTIONS` 一行 rollback） |
| 同上 | L1256-1268 | 待辦期望集合為空的 `log.warning`（off 時完全靜音） |
| 同上 | L1310-1356 | `_parse_notes_items`（筆記「議題與決議」區塊條列；標頭限定、佔位／過短濾除、同鍵去重） |
| 同上 | L1357-1365 | `_extract_notes_topic_items`／`_extract_notes_decision_items` |
| 同上 | L1367-1399 | `_fold_record_for_number_matching`（剝來源標註→NFKC→去千分位逗號→去空白）＋`_iter_transcript_segment_bodies`（lazy import `TRANSCRIPT_SEGMENT_PATTERN`） |
| 同上 | L1401-1412 | `_snippet_around_span`（原文片段 ≤40 字） |
| 同上 | L1414-1440 | `_scan_transcript_number_items`（單位錨定 clause 閘門、≥2 位、`13,600`／`13600` 皆可抽、折疊去重） |
| 同上 | L1442-1475 | `_scan_transcript_date_items`（月日／月底／M/D／下週X 四樣式＋範圍檢查） |
| 同上 | L1477-1509 | `_date_canonical_is_covered`（等價展開 `11月1日≡11/1`、`下週一≡下個禮拜一`、月底） |
| 同上 | L1511-1515 | `_coverage_categories`（類別開關交集） |
| 同上 | L1517-1672 | `_validate_record_source_coverage`（三模式；重用既有比對器／否定詞＋數字守衛） |
| 同上 | L1673-1695 | `_record_coverage_metrics_fields`（`cov_*`；off／未跑＝空字串） |
| 同上 | L1696-1733 | `_validate_record_fidelity`（P4-B 接線：lazy import＋try/except fail-soft） |
| 同上 | L2411-2416 | 補強階段「context 不足→只餵筆記」WARNING（與 L2376-2383 的最終生成階段既有警告對稱） |
| 同上 | L2754（＋既有 L2761 log） | W-2：`self._context_window_source` 登錄（`lmstudio_instance`／`settings`） |
| 同上 | L2860-2863、L2917-2920 | **僅地端**兩呼叫點：覆蓋率＋忠實度併入既有補強問題清單（首輪與每輪補強後重算） |
| 同上 | L2940 | pipeline metrics 行尾接 `cov_*`（off＝空字串，byte 不變；既有整數鍵不動） |
| 同上 | L3216-3234 | `_ollama_sampling_options`（top_p／top_k／repeat_penalty 讀同一份 config；None＝不送） |
| 同上 | L3276-3285、L3312-3320 | Ollama 取樣＋`num_ctx`＋`context_window_source` log；options payload 改 `**sampling_options`（400 相容降級保留） |

## 2. 開關與預設值

| 開關 | 預設值 | 語意 |
|---|---|---|
| `LOCAL_LLM_RECORD_COVERAGE_MODE` | `enforce` | `observe`＝只記 log／metrics（issues 不併入，品質零變化）；`off`＝完全不跑（無 log／無 metrics，一行回本波前 byte 級） |
| `LOCAL_LLM_RECORD_COVERAGE_CATEGORIES` | `topic,decision,number,date` | 可縮類別子集；未知名稱一律過濾 |
| `LOCAL_LLM_RECORD_COVERAGE_ITEM_LIMIT` | `12`（ge 1／le 50） | 每類別問題字串最多列出的項目數，超出以「其餘 N 項」帶過 |
| `LOCAL_FIDELITY_TRIPWIRES` | `True` | `False`＝完全不呼叫 `analyze_fidelity`（P4-B 一行回退） |
| `LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED` | `True` | P4-D（W4 消費）；本波僅提供欄位，未動其邏輯 |
| `LOCAL_LLM_SAMPLING_REPEAT_PENALTY` | `1.08`（float，可 None） | 依 handoff §4.2 新立欄位名稱登錄；Ollama 專用（LM Studio 對 penalty 欄位回 400） |

## 3. P4-A 實際離線判缺表（**W1 親自重跑**；不使用設計書「5 數字、零誤判」舊措辭）

- 量測（2026-09-23 04:53，離線、無 LM Studio／網路）：`/tmp/p4/measure_table.py`（抽取器層）＋`/tmp/p4/measure_through_path.py`（走真實 `_validate_record_source_coverage` 路徑）。
- 配對：B2＝`data/cache/e2e/p2-27b-fix-01/…_dc3c8f7a`；B1＝`p2-moe-fix-01/…_0cc199da`；C1＝`p2-gemma31b-fix-01/…_ac1edcec`；D1＝`p3-gemma31b-d1/…_ab5571ea`（四份逐字稿內容同源；差異在紀錄產物）。

| fixture | 數字候選 | **判缺數字** | 日期候選 | **判缺日期** | `cov_*`（number／date／issues） |
|---|---|---|---|---|---|
| B2 | 11, 40, 25, 15, 600, 800, 17, 13600, 100（9） | **15, 600, 800, 17, 13600（5）** | 11/1, 10/14, 週一, 10月底（4） | **10月底（1）** | 9/5・4/1・issues 2 |
| B1 | 同上 | **同上（5）** | 同上 | **10月底（1）** | 同上 |
| C1 | 同上 | **同上（5）** | 同上 | **10月底（1）** | 同上 |
| D1 | 同上 | **同上（5）** | 同上 | **週一, 10月底（2）** | 9/5・4/2・issues 2 |

- 議題／決議兩列皆為 0：四份快取未持久化 `merged_notes`（萃取筆記），重跑時以空字串代入 → 期望集合為空，**已觸發**空集合 WARNING（`summarization.py:1595`；log 證據見下）。筆記落地後這兩類的實際良率仍 `[UNVERIFIED]`。
- 與 §11 C1 對照：設計原型漏的 `13600` 已進候選；被來源標註洗白的 `17` 已判缺（修正生效）。`15` 亦判缺（原型判為未缺）——四份紀錄的 `15` 全部只出現在來源標註內（見下人工複核）。

### 3.1 人工複核（判缺真實性；`grep` 可核）

| 項目 | 紀錄側事實 | 逐字稿側事實（原文片段） | 判定 |
|---|---|---|---|
| `15` | B2 6 次／B1·C1 各 2 次／D1 1 次，**全部在 `（科長，00:08:15）` 標註內**；剝標註後 0 次 | 「所以就原則上委任的部分就會少了 15%當然有 15%的人會升稅務員」 | 真漏寫（真陽性） |
| `17` | B2 1 次，在 `（科長，00:17:52）` 內；其餘三份 0 次 | 「有 17個人所以 13600」 | 真漏寫（C1 阻斷級修正點） |
| `600`／`800`／`13600` | 四份紀錄 0 次 | 「發禮券啊 600…」「一個人 800塊嘛」「所以 13600」 | 真漏寫 |
| `10月底` | 四份紀錄 0 次 | 「他們 10月底就要搬進來了」 | 真漏寫 |
| `週一`（僅 D1） | D1 紀錄 0 次（`週／星期／禮拜` 全無） | 「下個禮拜一我們要做內稽」（逐字稿 `禮拜一`×3、`星期一`×1） | 真漏寫 |

- 逐字稿存在性：`10月底`×1、`800塊`×1、`13600`×2、`17個人`×1、`15%`×2、`600`×6（四份逐字稿計數一致）。
- 每項判缺均附原文片段（≤40 字）於問題字串／`/tmp/p4/p4a_measured_table.json`（**/tmp 非持久**；片段已抄錄於本表與問題字串中）。

## 4. P4-B 接線（§4.3 凍結介面）

- 呼叫：`_validate_record_fidelity` → lazy `from backend.core import fidelity_checks` → `analyze_fidelity(summary, transcript, template_id=template.id)`；`report["problems"]` **原樣**（不改寫、不刪句、不排序、不新增提示詞）併入既有補強問題清單。
- `LOCAL_FIDELITY_TRIPWIRES=False`：**完全不呼叫**（函式級 golden 證明與本波前逐字相同）。
- fail-soft：模組不存在／ImportError／分析器丟錯 → `log.warning`／`log.exception` ＋回 `[]`，主流程照走（W2 於 04:50 落地 38 KB 實體模組後，另加一條真實模組整合測試：`problems` 逐字過帳不變形）。
- 雲端路徑（`_summarize_with_gemini`）原始碼斷言：不得出現兩個新檢查（測試守住；雲端提示詞與問題清單本波未動）。

## 5. P4-C（W-1／W-2 引擎同源）

- W-1：Ollama `options` 不再寫死 `top_p=0.95/top_k=64`；改讀 `LOCAL_LLM_SAMPLING_TOP_P/TOP_K`＋新欄位 `LOCAL_LLM_SAMPLING_REPEAT_PENALTY`（None＝不送，與 `_lmstudio_extra_body` 同語意）。舊寫死值＝`LEGACY_OLLAMA_SAMPLING_OPTIONS`（一行 rollback）。
- W-2：context 預算沿用 `LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS`／LM Studio instance `context_length`，**不強改**；登錄 `self._context_window_source`＋引擎層 log（`num_ctx=…（context_window_source=lmstudio_instance|settings）`）；補強階段退回筆記-only 時補 WARNING（與最終生成階段既有警告同構）。
- A/B 中位數表（`top_p` 0.7 vs 0.3，每組 2 次）＝**未跑**（需 LM Studio 實跑，非本波離線測試範圍）→ `[UNVERIFIED]`，列為 escalation。本波證據為 payload 級（P-01～P-03）。

## 6. 測試與驗證（實跑）

- `DATA_DIR=/tmp/probe_scratch uv run --frozen python -m pytest tests/test_t20260923_p4a_record_coverage.py tests/test_t20260923_p4b_fidelity_wiring.py -q` → **32 passed（24＋8）／0 failed**（0.44s）。
- import 健檢：`DATA_DIR=/tmp/probe_scratch uv run --frozen python -c "import backend.main"` → `IMPORT OK`（logger 初始化至 /tmp/probe_scratch/logs）。
- 未跑全套（其他 W 並行改碼中）；未跑 E2E（Stage 05 另立 attempt 目錄）。
- A 類 15 項（落地為 T-01～T-19，共 24 條測試）＋三模式（enforce／observe／off）＋反例（個位數／全零／無單位句／非法日期／佔位語／來源標註洗白）全數涵蓋；P4-B I-1（含真模組整合）／I-2 全數涵蓋（共 8 條）。測試不依賴 LM Studio／網路（fake engine＋fake fidelity 注入；真模組測試以 `importorskip` 保護）。

## 7. byte 級不變證據（§11 N3 函式級 golden）

- P4-A：`test_T15_off_不跑不記`（off → 無 issues／無 log／無 `cov_*`）＋`test_T15b_off_地端pipeline函式級golden`（`prewave_stub=True`＝本波前等效實作：兩方法不存在、metrics 欄位不存在；同一輸入下紀錄與 log 逐字相同，僅遮罩 wall-clock 欄位）。
- P4-B：`test_I2_關閉開關完全不呼叫檢查器`＋`test_I2_關閉時地端pipeline函式級golden`（同上方法；檢查器 0 次呼叫）。
- 雲端：`test_雲端路徑不得呼叫覆蓋率與忠實度檢查`（source 斷言）。

## 8. 補強輪數計數方式（§11 N2）

- `pipeline_metrics` 未結構化補強輪數（僅 `merge_rounds`）；本波實作**未改**該結構。計數方式＝每次地端任務 log 內出現幾次 `本地摘要品質補強（第 N 輪），問題：…`（`summarization.py` 補強迴圈內 `log.info`；每輪恰一行）。
- baseline（沿用 handoff §7.2 既有紀錄，非本人新測）：D1 `duration_seconds=1227.2`／`pipeline_total_seconds=738.8`／該場補強輪數 **0**。本波未跑 E2E → 新輪數 `[UNVERIFIED]`。

## 9. 偏離 handoff 之處（附理由）

1. **observe 模式仍計算 `issues_added`**：observe 下覆蓋率照算統計（`cov_*` 有值＝可觀測），但回傳 `[]`（品質零變化、不觸發補強）。理由：handoff §9 要求 observe「只記 log／metrics」；若完全不組 issues，`issues_added` 這類觀察值會失真。**未改任何既有語意**。
2. **`_validate_summary_quality` 空待辦警告**（L1256-1268）：此為**共用方法**（雲端共用）。只加 log、不改 issues；且 `off` 時靜音。屬「空集合不得不靜默」要求的最小落點，未動雲端輸出。
3. **P4-B 測試多一條真模組整合測試**（handoff 未列）：W2 模組已落地，補驗介面不漂移；不依賴網路、模組缺席時 skip。

## 10. 如實邊界與 escalation

- **未跑**：E2E（27B／Gemma 各一次）、P4-C A/B 中位數表、Windows／Ollama 實機 → 全部 `[UNVERIFIED]`。
- 議題／決議對帳的實際召回升降（依賴 `merged_notes`）→ `[UNVERIFIED]`；本表僅證明數字／日期與空集合告警行為。
- 殘餘風險 R1（設計明文、未改）：`_SOURCE_TAG_PATTERN` 會剝掉含時間的整個括號內容；若真實數字夾在如「（每人 600 元，領取時間 12:00 前）」內會一併被剝除 → 可能假陰性。屬既有模式語意，改它＝動跨包共用正則，留待 planner 決策。
- 五場對照為單次抽樣；本波任何「追上雲端」宣稱皆不成立（未量測）。
