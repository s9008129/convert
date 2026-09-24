# P7-C Stage 02 獨立審查 — 原始證據（attempt-01）

- 產生者：**Stage 02 獨立計畫審查員（fresh context、唯讀）**；本檔＝`review.md` §0「原始輸出見同目錄 `evidence.md`」所指之證據落檔。
- **零模型呼叫**：未呼叫 LM Studio／任何 LLM、未跑 E2E、未跑全 suite。唯一執行過的產品程式＝**純字串函式**（`SummarizationService._build_local_context_plan` ＋ `_split_transcript_into_chunks`＋`_estimate_tokens`），環境 `DATA_DIR=/tmp/rev_scratch`。
- 受審快照（`shasum -a 256`，開審前／審查中／寫入 `review.md` 前共 3 次，同值）：`plan.md = 325e8487b4430b3fcf38f301513487314b0d730f7d6385b88eec191357d2cb0a`。

## E1 零呼叫分塊重播（原始 stdout；ANSI 去除、每段前 INFO 行已略）

- 執行：`DATA_DIR=/tmp/rev_scratch .venv/bin/python`（stdin 腳本）→ 逐 ceiling 設 `settings.LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS` 後呼叫產品函式。
- 輸入：`data/cache/e2e/p7b-gemma31b-e8/backend_data/outputs/0903-科務會議_5444cdef_逐字稿.txt`（sha256 `fd40a201…`，15,666 字；＝P7-B gemma E8 實跑吃進的同一份）。
- context window＝`71,936`（P7-B gemma backend.log／app log 實錄，見 E2）。探針＝`quality/fact_checklist.json` 的既有 `probes`。
- 每段對應 INFO：`結構性分塊萃取：上限 N tokens（來源 LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS）、實際分塊上限 N tokens（依 context 推導值 65953 tokens）`。

```
transcript_chars = 15666
--- ceiling=6000 blocks=2 est_tokens=[5960, 5918] budget=6000 est_transcript_tokens=11711
    F044: chunk(0-based)=1 kind=pair probe=['選舉', '小心']
    F054: chunk(0-based)=1 kind=single_token_fallback probe=['搬遷']
    F055: chunk(0-based)=1 kind=pair probe=['三樓', '淹水']
    F056: chunk(0-based)=1 kind=pair probe=['防水層', '排水管']
    F060: chunk(0-based)=1 kind=pair probe=['政風室', '黴味']
    F065: chunk(0-based)=1 kind=pair probe=['第一階段', '工產科']
    F066: chunk(0-based)=1 kind=pair probe=['局長室', '處長']
--- ceiling=5860 blocks=3 est_tokens=[5801, 5541, 682] budget=5860 est_transcript_tokens=11711
    F044: chunk(0-based)=1 kind=pair probe=['選舉', '小心']
    F054: chunk(0-based)=2 kind=single_token_fallback probe=['搬遷']
    F055: chunk(0-based)=1 kind=pair probe=['三樓', '淹水']
    F056: chunk(0-based)=1 kind=pair probe=['防水層', '排水管']
    F060: chunk(0-based)=1 kind=pair probe=['政風室', '黴味']
    F065: chunk(0-based)=2 kind=pair probe=['第一階段', '工產科']
    F066: chunk(0-based)=2 kind=pair probe=['局長室', '處長']
--- ceiling=5500 blocks=3 est_tokens=[5459, 5379, 1397] budget=5500 est_transcript_tokens=11711
    F044: chunk(0-based)=1 kind=pair probe=['選舉', '小心']
    F054: chunk(0-based)=2 kind=single_token_fallback probe=['搬遷']
    F055: chunk(0-based)=1 kind=pair probe=['三樓', '淹水']
    F056: chunk(0-based)=1 kind=pair probe=['防水層', '排水管']
    F060: chunk(0-based)=1 kind=pair probe=['政風室', '黴味']
    F065: chunk(0-based)=2 kind=pair probe=['第一階段', '工產科']
    F066: chunk(0-based)=2 kind=pair probe=['局長室', '處長']
--- ceiling=4500 blocks=3 est_tokens=[4466, 4413, 2995] budget=4500 est_transcript_tokens=11711
    F044: chunk(0-based)=1 kind=pair probe=['選舉', '小心']
    F054: chunk(0-based)=2 kind=single_token_fallback probe=['搬遷']
    F055: chunk(0-based)=2 kind=pair probe=['三樓', '淹水']
    F056: chunk(0-based)=2 kind=pair probe=['防水層', '排水管']
    F060: chunk(0-based)=2 kind=pair probe=['政風室', '黴味']
    F065: chunk(0-based)=2 kind=pair probe=['第一階段', '工產科']
    F066: chunk(0-based)=2 kind=pair probe=['局長室', '處長']
--- ceiling=3800 blocks=4 est_tokens=[3737, 3761, 3554, 1397] budget=3800 est_transcript_tokens=11711
    F044: chunk(0-based)=1 kind=pair probe=['選舉', '小心']
    F054: chunk(0-based)=3 kind=single_token_fallback probe=['搬遷']
    F055: chunk(0-based)=2 kind=pair probe=['三樓', '淹水']
    F056: chunk(0-based)=2 kind=pair probe=['防水層', '排水管']
    F060: chunk(0-based)=2 kind=pair probe=['政風室', '黴味']
    F065: chunk(0-based)=3 kind=pair probe=['第一階段', '工產科']
    F066: chunk(0-based)=3 kind=pair probe=['局長室', '處長']
--- ceiling=3000 blocks=5 est_tokens=[2986, 2922, 2981, 2961, 151] budget=3000 est_transcript_tokens=11711
    F044: chunk(0-based)=2 kind=pair probe=['選舉', '小心']
    F054: chunk(0-based)=3 kind=single_token_fallback probe=['搬遷']
    F055: chunk(0-based)=3 kind=pair probe=['三樓', '淹水']
    F056: chunk(0-based)=3 kind=pair probe=['防水層', '排水管']
    F060: chunk(0-based)=3 kind=pair probe=['政風室', '黴味']
    F065: chunk(0-based)=3 kind=pair probe=['第一階段', '工產科']
    F066: chunk(0-based)=3 kind=pair probe=['局長室', '處長']
```

- **對帳**：`est_transcript_tokens=11711`、`context 推導上限 65953` 與 P7-B 實跑 log 一致（E2），亦與 Planner `evidence/chunk-replay-p7c/README.md §0` 相同 ⇒ 重播＝實跑分塊器。
- **落檔時複核更正**：`review.md` §3.3 表格 5,500 列原記「第 3 塊 5 條」；本重播＋Planner 重播（F054／F065／F066＝第 2 塊；F060 跨重疊區）皆為 **3 條**，已更正為「第 3 塊 3 條（F054／F065／F066；F060 跨重疊區）」。其餘各列數字重播後**全部相符**。
- 原始未清洗檔留存：`/tmp/rev_scratch/review-replay-raw.txt`（含 logger 行）。

## E2 gemma `backend.log` 關鍵行（節錄）

檔：`data/cache/e2e/p7b-gemma31b-e8/backend.log`

- L62–L171（19:24:49–19:30:16）：**逐字稿語意校正** 12 次呼叫，`max_tokens=3072`，`completion_tokens`＝294／322／279／296／235／249／235／300／331／295／283／263（＝R1 引用的 235–331 出處；**非萃取階段**）。
- L225（19:34:00）：`finish_reason=stop, max_tokens=8192, prompt_tokens=7981, completion_tokens=1356`（**萃取**）。
- L264（19:37:03）：`finish_reason=stop, max_tokens=8192, prompt_tokens=6307, completion_tokens=1248`（**萃取**）。
- L266（19:37:03）：`萃取筆記零損串接（略過有損整併）：2 份、2303 tokens ≤ 下游可承接上限 62492 tokens，context window 71936 tokens`。
- L593（20:00:44）：`本地摘要 pipeline metrics：chunk_count=2, logical_generations=5, semantic_attempts=0, network_retries=0, merge_rounds=0, duration_seconds={'extraction': 406.1, 'merge': 0.0, 'final_and_refine': 1421.3, 'total': 1827.4}`。
- L476（19:52:33）：第 1 輪守衛 `核心未涵蓋 11 → 4 項`；L586（20:00:44）：第 2 輪造成回退、丟棄本輪。

## E3 qwen `backend.log` 關鍵行（節錄）

檔：`data/cache/e2e/p7b-qwen27b-e8/backend.log`

- L388（20:26:56）：`地端補強不回退守衛：第 1 輪核心未涵蓋 21 → 14 項（期望 60 項）（更好，取本輪）`。
- L471（20:32:56）：`第 2 輪核心未涵蓋 14 → 14 項（持平，取本輪）`。
  ⇒ **每輪補強 ≈360 s**（20:26:56→20:32:56）。
- L472（20:32:56，第 2 輪後）：待補清單仍含「議題遺漏 6 項：**土地稅科倉庫漏水與土地卡重印**、內部稽核…」⇒ CORE-2a 目標型失敗在第 2 輪後仍在。
- L473（20:32:56）：`pipeline metrics：chunk_count=2, logical_generations=5, duration_seconds={'extraction': 427.6, 'merge': 0.0, 'final_and_refine': 1069.7, 'total': 1497.3}`。

## E4 牆鐘（runner `run_summary.json`，唯一權威鐘）

| 場 | started_at | finished_at | 牆鐘 |
|---|---|---|---|
| gemma E8 | `2026-09-23T19:21:08.659100+08:00` | `2026-09-23T20:00:47.137288+08:00` | **2,378.5 s** |
| qwen E8 | `2026-09-23T20:02:42.885919+08:00` | `2026-09-23T20:32:57.823777+08:00` | **1,814.9 s** |

- 出處：`.agent/tasks/T20260923-1810-01-local-record-fidelity-density/e2e/attempt-P7B-gemma31b-e8/run_summary.json`、`attempt-P7B-qwen27b-e8/run_summary.json`。
- 交叉核對：前波 `e2e/attempt-P7B-stage05/verification-report.md:81-82`（§1.7）同值；`:91-97`（§1.8）明載「牆鐘 − pipeline ＝ 551.1 s（gemma）／317.6 s（qwen）」且**兩鐘不可混算**。

## E5 萃取筆記實查（`rg`）

- gemma：`data/cache/e2e/p7b-gemma31b-e8/backend_data/debug/extraction-notes/notes-20260923-193703-2c452049.md`
  - `政治`＝0 命中；`禮堂|走廊|三樓`＝0；`新聞行銷處|局長室`＝0；`選舉` 僅 L66／L178（日期行「僅提到近期為年底選舉前」）。
  - 時戳：全檔首＝`00:04:52`；第 2 份筆記首＝`00:22:44`（L72）；全檔末＝`00:32:34`（尾段 00:32–00:44 未進筆記）。
- qwen：`data/cache/e2e/p7b-qwen27b-e8/backend_data/debug/extraction-notes/notes-20260923-201506-466dd7bc.md`
  - L47：「上次颱風平上班日，土地稅科倉庫嚴重漏水，影響土地卡。」（F019 在筆記內）
  - L199：「[00:33:07-00:39:44] …樓上施工（防水層重做）刨掉舊防水層，導致早期埋設的排水管外漏…」（F056 在筆記內；第 2 輪後版本 L281／L432 同）。

## E6 開關存在性（`rg` 全庫；程式碼面）

| 名稱 | 結果 | 出處 |
|---|---|---|
| `LOCAL_LLM_DUMP_EXTRACTION_NOTES` | 存在（預設 False） | `backend/core/config.py:664` |
| `LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS` | 存在（預設 6000） | `backend/core/config.py:653` |
| `LOCAL_LLM_MAX_REFINEMENT_ROUNDS` | 存在（預設 2） | `backend/core/config.py:280` |
| `LOCAL_LLM_RECORD_COVERAGE_MODE` | 存在 | `backend/core/config.py:287` |
| `LOCAL_LLM_REFINEMENT_NO_REGRESSION` | 存在 | `backend/core/config.py:636` |
| `LOCAL_LLM_EXTRACTION_CALL_BUDGET` | **0 命中（不存在）** | — |
| `LOCAL_LLM_REFINEMENT_CALL_BUDGET` | **0 命中（不存在）** | — |
| `LOCAL_LLM_PROPER_NOUN_NORMALIZE` | **0 命中（不存在）** | — |
| `LOCAL_LLM_TAG_SNAP_SIMILARITY` | **0 命中（不存在）** | 真槓桿＝`TAG_SNAP_TOLERANCE_SECONDS`／`TAG_SNAP_MAX_SHIFT_SECONDS`（`backend/core/text_postprocess.py:781,785`） |

- 5 項既有門檻：`scripts/e2e/run_owned_e2e.py:179-195`（恰 5 條 `QUALITY_TAG_THRESHOLDS`）。
- 投影缺口：`scripts/e2e/run_owned_e2e.py:928-980`（`project_record_quality_metrics` 無 `full_document_item_count`／`full_document_avg_item_chars`／`near_duplicate_items`）。
- plan 引註：`plan.md:62-67`（C1b「由 6,000 下調」、C1c「新，預設 2」）；`plan.md:99-103`（CORE-A/B/C/D 門檻）；`plan.md:108`（「2 場取中位數」）。

## E7 素材／量尺 sha256（`shasum -a 256`）

| 對象 | sha256 |
|---|---|
| `/Users/hsiaojohnny/Downloads/0903-科務會議.m4a` | `982151f4629ade0c38f164b57a2f105c1e305677e7e10e4dc0e252f1ac012828` |
| gemma E8 逐字稿 | `fd40a2018def853580bda83db26f9939b7a053cf1f0049ff80b08829e75b72bf` |
| qwen E8 逐字稿 | `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0` |
| `quality/fact_checklist.json`（全庫僅一份） | `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001` |

## E8 尾段探針（I13 引據）

檔：`.agent/tasks/T20260923-1810-01-local-record-fidelity-density/evidence/tail-extraction-probe/README.md`

- §A2（:96-108）：run-02 尾半段（00:22:28 起）**單次呼叫 150.5 s**、探針命中 **6/7（F044 ✅）**；run-01（00:33:00 起）6/7 但 F044 不在切片內。
- §A3（:110-117）：兩次各 6/7、**命中集合不同** ⇒ 單一視窗尾段萃取是**機率性的**。
- §A4（:120-125）：方案 A（整份 1 次＋尾半段 1 次）＝340.6＋150.5＝**491 s（+44%）**。

## E9 前波證據出處（行號）

- `.../T20260923-1810-01-local-record-fidelity-density/e2e/attempt-P7B-stage05/verification-report.md:78-97`（§1.7 停損／§1.8 兩鐘對照）與 §2 Gate 表（qwen 密度②為**非阻斷**）。
- `.agent/tasks/T20260923-1810-01-local-record-fidelity-density/progress-report.md:14-17`（噪聲帶 ±10pp；14–18pp 擺動）。
- `.agent/tasks/T20260923-1810-01-local-record-fidelity-density/escalation.md`（D1–D4）。
- `.agent/tasks/T20260923-1810-01-local-record-fidelity-density/e2e/attempt-P7B-gemma31b-e8/`、`attempt-P7B-qwen27b-e8/`（run_summary.json 見 E4）。
