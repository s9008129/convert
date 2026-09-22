# T20260922-2037-02-local-model-quality-parity — PLAN（P2 可查核性波）

- TASK_ID: `T20260922-2037-02-local-model-quality-parity`
- PLAN_REVISION: 6
  - rev 1＝品質波開場：27B／MoE 實測與根因量測。
  - rev 2＝把「模型無關的可查核性修復」定為本波 CORE，其餘槓桿列為後續波。
  - rev 3＝依獨立驗收（`e2e/attempt-B2-27b-fix/verify_independent.md`）更正 CORE-1 的**閘門量尺**：
    主指標改為 speaker-agnostic 的 `on_start_tag_ratio`、`exact_tag_ratio` 降為觀察值。
  - rev 4＝**修訂身分修正**：rev 3 被 `review/attempt-01` 判 `PLAN_REVISION_REQUIRED`（F1／F2／F3）後，
    修訂內容被就地寫回同一份 `plan.md` 而仍自稱 rev 3（違反修訂單調與 approval 綁定規則，`review/attempt-02`
    的 N1）。rev 4 把版本遞增並補上修訂紀錄。`[DECIDED]`
    - **如實修正**：rev 4 曾宣稱「已收斂 N2–N5」，但 `review/attempt-03` 查核後指出 **N2 實際未收斂**
      （三處絕對語氣未改：§1 CORE-1、§2 R21、§5）——該宣稱不實，已在 rev 5 更正並實際改寫這三處。
  - rev 5＝依 `review/attempt-03` 收斂：①改寫三處與設計不符的絕對語氣（吸附受 `kept_far` 精度保護、
    並非所有標註都會落在段落起點）；②修訂紀錄改為如實清單；③釐清研究文件 §10.5（輔助線 0.9）
    與本計畫 §4-3（主線 0.95）的關係；④`instrument_recheck_20260922.json` 補 `metric_version`；
    ⑤W3 工作項補列儀器新欄位。
  - rev 6＝依 `review/attempt-04` 收斂 F-C／F-D（§2 R20 的計數與量尺、W3 未列 `metric_version`），
    並納入**使用者新增需求**（§7：Gemma 4 31B 實測、macOS／Windows 雙平台支援）與
    **獨立查核發現的產物標籤更正**（§6.5：時間軸標籤、v1.0／v1.1 同名指標別名）。
    本波的 27B 實測結論與 B2 證據不受影響。
- **修訂與證據 append-only 原則**：`plan.md` 只由 Planner 遞增修訂；`review/attempt-NN/*` 與
  `e2e/attempt-*/*` 一律新增、不得就地覆寫（B2 的 `record_quality.json` 曾在儀器微調時被就地覆寫，
  已於 §6.2 記錄並以 `metric_version` 收斂）。
- TASK_CLASS: STANDARD｜REVIEW_REQUIRED: YES｜INDEPENDENT_ACCEPTANCE_REQUIRED: YES｜E2E_REQUIRED: YES（真實音檔 `0903-科務會議.m4a` ＋ `section_meeting` ＋ `local`）
- 分支：`fix/qwen-local-quality-parity`（自 `fix/local-lmstudio-record-quality` HEAD `4f1fb23` 開出）
- 前波：`T20260922-1930-01-local-record-quality-parity`（P1 品質波，已完成並推送；本波不重做其成果）

## 0. 使用者需求（不可縮小）

1. 讓 Mac ＋ LM Studio（`qwen3.8-27b-splash` dense 27B、`qwen3.6-35b-a3b-splash` MoE 35B-A3B）用 `section_meeting`
   生成的會議紀錄品質「接近雲端 Gemini」。
2. 深度的研究與優化規劃。
3. 另開分支修好 27B／35B 兩顆模型的品質問題。
4. **新增需求（本輪）**：優化機制必須**與模型無關**——日後在辦公室 Windows 11 ＋ RTX 4090 ＋ Ollama、
   跑 Gemma 4 31B 時也要一體適用，不得只為 LM Studio 現有模型客製。

## 1. Goal Contract

**設計原則（回應需求 4）**：品質保證必須落在「模型無關的確定性層」——
①逐字稿事實層（段落時間表、詞彙表、來源標註）、②確定性後處理、
③確定性驗證與補強清單。提示詞只負責「告訴模型規則」，不得成為品質的唯一依靠。

**CORE（本波，具全域阻斷力）**

- **CORE-1 出處標註真實性**：地端紀錄的正文出處標註，其時間戳必須落在逐字稿的真實段落上，
  且吸附後應落在**真實段落起點**（speaker-agnostic）。吸附**不是全量**：位移超過
  `TAG_SNAP_MAX_SHIFT_SECONDS`（120 s）者，依精度保護刻意保留原時間戳（仍在真實段落內）。
  因此閘門以**比例**表述（≥ 0.95），而非「每一筆都必須在起點」。
  - **已除役（rev 3，非閘門殘餘風險）**：「時間戳落在**該標註指名發言者**的段落內」不再作為本波閘門。
    理由：實測 51/52 筆標註使用角色名（「科長」），而逐字稿只有 `發言者N`；且吸附規則 3（時間戳落在
    別的發言者段落內時只改時間、**不改歸屬**）本來就會產生跨發言者結果（B2：39–44/45）。
    因此 `tags_inside_same_speaker_segment` 列為觀察值；**發言者歸屬正確性仍是已知殘餘風險**（P1-1）。
  - **閘門量尺（rev 3 更正）**：主指標 `on_start_tag_ratio ≥ 0.95`（時間戳恰為**任一**真實段落起點；
    speaker-agnostic）＋輔助 `on_start_tag_ratio_excluding_zero ≥ 0.9`（排除 `00:00:00`；分母＝非
    `00:00:00` 的標註數；若全場標註皆為 `00:00:00`，該指標為 `None` ＝ **不判定**（此時改用
    `on_start_tag_ratio` 與 `zero_time_tag_ratio` 人工判讀）。
    ＋ `traceable_tag_ratio ≥ 0.95`。
  - **觀察值（不作為閘門）**：`exact_tag_ratio`（時間戳恰為段落起點**且**發言者標籤與該段一致）、
    `tags_inside_same_speaker_segment / tags_total`、`zero_time_tag_ratio`、`distinct_tag_time_ratio`。
  - **rev 3 更正理由**：`exact_tag_ratio` 要求發言者標籤等於逐字稿的 `發言者N`；實測本場 51/52 筆標註
    使用角色名（「科長」），使該指標結構上不可能通過（B2 實測 0.0192）——拿它當閘門會造成 system-wide
    false FAIL，屬量尺缺陷而非產品缺陷。獨立驗收報告已逐條記錄（見 `verify_independent.md`）。
  - 基線（實測，0903 場；rev 3 以新儀器重測，見研究文件 §10.3 量尺更正）：
    MoE 35B `on_start 10/27 = 37.0%`（`exact 4/27`）；dense 27B `on_start 58/61 = 95.1%`（`exact 46/61`）。
  - 退化防線：`body_source_tag_count ≥ 17`（前波 CORE-1 防線沿用；避免模型少寫標註換分數）。
    適用範圍：**與 `section_meeting` 同族的來源標註模板**；若換到不要求標註的模板，此防線改為觀察值
    （模板是否要求標註由 `template_supports_source_tags()` 判定）。
- **CORE-2 模型無關性**：修復必須位於 LM Studio／Ollama 共用的地端管線
  （`_summarize_with_local_pipeline` → `_finalize_record_text(mode="local")`），
  且不得依賴模型名稱、模型家族或引擎特有參數。
  - 驗收：單元測試以「假引擎」與純函式契約證明；程式碼不得出現模型名分支。

**SUPPORTING**

- S-1：量測儀器 `measure_record_quality.py` 增列 `tag_traceability`（與產品共用同一份段落解析定義）。
- S-2：研究文件新增「P2 波」章節，記錄 27B vs MoE 實測對照與模型無關設計。
- S-3：真實音檔 E2E（MoE；時間允許再補 27B）＋吸附前後對照。

**BEST_EFFORT**：27B 的第二輪 E2E、Ollama 引擎路徑的實機驗證（本機無 Ollama 服務）。
**明確排除**：溫度／取樣再校準（P1-3，需 A/B 實驗設計）、覆蓋率檢查表（P1-4）、
Gemma 4 31B 實測（本機無模型；48GB 承載性 `[UNVERIFIED]`）。

**全域阻斷**：只有 CORE-1／CORE-2 具阻斷力。

## 2. 本波根因（實測）

| ID | 根因 | 證據 | 影響 |
|---|---|---|---|
| R20 | 模型寫得出標註，但時間戳的可查核性不足——**兩顆模型的成因不同** | v1.1 儀器實測：MoE（p1）`on_start 10/27 = 37.0%`、`exact 4/27`；27B（A1）`on_start 58/61 = 95.1%`、`exact 46/61`（發言者一致的嚴格版僅 75.4%） | MoE：過半標註落在段落中間的任意秒數；27B：多數已落段首，但標籤多用角色名（「科長」）而非 `發言者N`，嚴格版查核失敗 → 標註看似可查核、實際查不到，使用者對紀錄的信任度低於雲端 |
| R21 | 同一份紀錄中 25/27（MoE）、61/61（27B）的時間戳**落在正確發言者的段落內** | 逐字稿段落時間表比對（本波新儀器） | 證明多數標註可用「吸附」確定性修復，**在規則覆蓋範圍內**不必重生成；超出覆蓋者（`kept_far`、跨發言者）只改時間、不改歸屬 |
| R22 | 前波的「可回溯率 37%」量尺只看「時間戳是否存在於逐字稿」 | 前波 quality review | 量尺不一致會誤導決策 → 本波建立共用定義 |

## 3. 工作項（本波）

- W1：`snap_source_tags_to_transcript`（確定性吸附；fail-soft；僅 `speaker_traceability` 模板）。
- W2：接進 `_finalize_record_text(mode="local")`，順序＝術語修正 → **吸附** → 表格標註清除 → 佔位符 → 去重。
- W3：量測儀器新增 `tag_traceability`（含 `metric_version` 與 `exact_tag_ratio`；rev 3 追加 `zero_time_tag_*`／
  `distinct_tag_time_*`／`on_start_tag_ratio_excluding_zero`）。
- W4：單元測試（吸附／fail-soft／cloud 不變／量測共用定義）。
- W5：E2E（真實音檔、`section_meeting`、`local`）＋吸附前後對照。
- W6：研究文件與本計畫回填實測數字；commit＋push。

## 4. 驗收（Stage 05）

1. `pytest tests/ -q --ignore=tests/test_end_to_end.py` 全綠（前波基準 881 passed／2 skipped）。
2. E2E：真實音檔、`section_meeting`、`local`、clean HEAD、`verdict=PASS`。
3. 品質（rev 3）：`on_start_tag_ratio ≥ 0.95`（**主閘門線**）、`on_start_tag_ratio_excluding_zero ≥ 0.9`、`traceable_tag_ratio ≥ 0.95`、`body_source_tag_count ≥ 17`、表格標註 = 0；`exact_tag_ratio` 為觀察值。
   **與研究文件 §10.5 SOP 的關係**：§10.5 第 1 項的 `on_start_tag_ratio ≥ 0.9` 是「換模型／換引擎上線前哨」的寬鬆下限，
   本點的 `≥ 0.95` 才是本波的**驗收閘門**；同一指標、兩種用途（前哨＝是否續查，驗收＝修復是否成立）。`[DECIDED 依 review/attempt-03 的 R2]`
4. 雲端不變性：`mode="cloud"` 對既有輸入 byte 級不變（單元測試釘住）。

## 5. 風險

- 吸附是**部分覆蓋**、且有兩種「改寫」語意：①命中規則 1／2 者 → 改寫目標＝該（同發言者）段落起點；
  ②命中規則 3 者 → 只改時間、**不保證同一發言者**（B2 實測 45 筆吸附中 44 筆屬規則 3、最終輸出
  40 筆中 39 筆屬規則 3）；③位移 > 120 s 者 → 原樣保留（`kept_far`）。
  因此「吸附後每一筆都在段落起點」**不成立**，閘門必須用比例。`[VERIFIED 實作＋實測]`
  （先前版本的 `[VERIFIED]` 敘述「仍改到同一發言者同一段落」與實作不符，rev 3 一併更正。）
- 模型改用角色名（如「科長」）而非 `發言者N` 時，`exact` 不計入 → **rev 2 的閘門文字未同步此量尺，
  已於 rev 3 更正為主指標 `on_start_tag_ratio`**（這正是獨立驗收抓到的問題）。
- 單次抽樣（temperature 0.7）：E2E 數字僅為單場證據，不外推。

## 6. 追加實測與審查紀錄（rev 3 起；含 rev 4／rev 5 的修訂內容）

### 6.1 本波 E2E 結果（27B dense，使用者指定唯一受測模型）

| 場次 | 吸附 | verdict | 耗時 | `on_start` | `on_start_excl0` | 表格標註 | 正文標註 | 指示章節條目 | 字元 |
|---|---|---|---|---|---|---|---|---|---|
| attempt-A1-27b | 無 | PASS | 910 s | 0.951（58/61） | 0.944（51/54） | 0 | 61 | 21 | 4,338 |
| **attempt-B2-27b-fix** | **有** | **PASS** | 1,710 s | **1.000（52/52）** | **1.000（45/45）** | 0 | 52 | 25 | 4,062 |

（MoE 場次 B1 為前次 commit 的迴歸證據，依使用者指示本輪不新增 MoE 測次。）

### 6.2 獨立驗收發現（不得略過）

1. **約 710 s（42% 耗時）花在兩輪「無效補強」**：品質閘門第 1 輪報「待辦事項遺漏 11 項」、第 2 輪剩 6 項，
   但獨立驗收比對後確認第 2 輪的 6 項**其實都已寫進紀錄**，差異只是「的／之」「征收／徵收」「及／、」
   等字面變體 → 確定性涵蓋檢查的**假陽性**導致 27B 多燒兩個 ~6 分鐘的生成。
   → 新工作項 **P1-17（下一波最高價值）**：補強問題清單的字面比對需做同義／變體正規化，
   否則「慢」與「品質」會互相掩蓋。
2. **標註辨別力不足**（新 P1-16）：B2 的 52 個標註只用 15 個不同時間戳（0.288），7 筆為 `00:00:00`。
3. **證據完整性**：同一場次的 `record_quality.json` 在儀器微調後被就地覆寫（`on_start_tag_ratio_excluding_zero`
   由分母＝總數改為分母＝非零數，0.865 → 1.000）。**rev 3 處理**：①儀器輸出加 `metric_version`
   （`tag_traceability` schema 內）；②明示 **B2 的閘門判定只依賴 `on_start_tag_ratio`**，
   該指標定義在釘住的產品版本 `3fec08f` 即已存在（commit `3fec08f` 引入）；`on_start_tag_ratio_excluding_zero`
   與 `zero_time_*`／`distinct_tag_time_*` 為**驗收後補的輔助觀察**，其定義變更不影響閘門結論。`[DECIDED]`

### 6.3 研究文件數字更正（依審查 F3）

研究文件 §10.3 的「吸附後」數字先前為**推論值**，已改為實跑吸附後的量測值：
MoE `on_start` 37.0% → **74.1%**（7 筆因位移 > 120 s 而被 `TAG_SNAP_MAX_SHIFT_SECONDS`
精度保護刻意保留原時間戳——這是設計選擇，不是吸附失效，但仍代表「未到 100%」）
27B 95.1% → **100%**；`exact` 分別為 70.4%／95.1%。`[VERIFIED 重跑]`

### 6.4 審查紀錄（如實）

- `review/attempt-01`（fresh context；受審＝當時自稱 rev 3 的快照，sha256 `bf6158d0…`）→ `PLAN_REVISION_REQUIRED`：
  F1 契約文字漂移（高）／
  F2 輔助閘門定義在驗收期間變更（中高）／F3 研究文件「吸附後」數字為推論值不可重現（中）。
- 修訂動作（內容；完成後才遞增版號）：①§1 CORE-1 明示「指名發言者」除役為非閘門殘餘風險；
  ②§5 更正與實作相反的舊敘述（吸附**不保證**同發言者，規則 3）；③研究文件 §10.3 改為實跑吸附的
  量測值（§6.3）；④`metric_version` 加入儀器並由測試釘住；⑤明示 B2 閘門只依 `on_start_tag_ratio`
  （該指標在釘住版 `3fec08f` 即存在，`excluding_zero` 等為驗收後補的輔助觀察）。
- `review/attempt-02`（fresh context；受審＝已就地修訂但仍自稱 rev 3 的快照，sha256 `4cf6ac0a…`）→
  `PLAN_REVISION_REQUIRED`，**唯一阻斷項 N1＝修訂身分**：上述修訂被就地寫回仍自稱 rev 3，
  違反修訂單調／approval 綁定（同一「rev 3」承載兩份不同內容）；內容面 F1／F2／F3 全部判定已收斂，
  並明確判定「降級 `exact_tag_ratio` 是量尺修正、不是放水」。
- **如實更正**：rev 4 的修訂紀錄曾寫「非阻斷建議 N2–N5 亦已收斂於 rev 4」——`review/attempt-03` 查核後
  證實該句**不實**（N2 的三處絕對語氣當下並未改動）。rev 5 已改寫這三處並改列如實清單。
- `review/attempt-03`（fresh context；受審＝rev 4，sha256 `86c9744f…`）→ `PLAN_REVISION_REQUIRED`，
  **唯一阻斷項 R1＝修訂紀錄不準確**（即上一段的「宣稱已收斂但事實未收斂」）；同時**明確判定未發現放寬標準**
  （`exact_tag_ratio` 降級、`ex0` 新增、B2 閘門值全數複核成立），並列低嚴重度建議 R2–R5：
  R2 研究 §10.5 的 0.9 與本計畫 §4 第 3 點的 0.95 關係未說明；R3 `instrument_recheck_20260922.json`
  缺 `metric_version`、W3 未列交付物；R4 全零標註退化紀錄可過全部機械閘門（`ex0=None` 不判定，已知殘餘風險，
  留待後續波為 `zero_time_tag_ratio` 訂上限）；R5 §6 標題與受審 hash 陳列。
- **rev 5 對應動作**：R1→實際改寫 §1 CORE-1／§5 的三處絕對語氣（吸附受 `kept_far` 精度保護、非全量）；
  R2→研究 §10.5 加註「前哨下限 vs 驗收閘門」並於本計畫 §4 第 3 點註明；R3→`instrument_recheck_20260922.json`
  補 `metric_version: tag_traceability-1.1.0`（僅 metadata，量測值未動）、W3 已補列；
  R5→本節標題改為「rev 3 起；含 rev 4／rev 5」，並並列各受審 hash（本段）。`[DECIDED]`

### 6.5 第四次獨立審查（attempt-04）與 rev 6 動作

- `review/attempt-04`（fresh context；受審＝rev 5，sha256 `3c0474a9…`）→ `PLAN_REVISION_REQUIRED`，
  **純文字修訂層、不阻斷產品碼**。逐項：R1 主體**已收斂**（三處確實改寫且與實作一致）；
  R2／R4／R5 **已收斂**；R3 **部分收斂**——`instrument_recheck_20260922.json` 已補 `metric_version`
  且量測值未動（與 rev 5 前副本逐欄相同），但 **W3 未列 `metric_version`，rev 5 卻自稱「W3 已補列」＝不實**。
  另新增兩項阻斷：**F-C**（§2 R20 的「4／46」其實是 `exact` 計數，卻寫成「落在段落起點」；
  同一儀器實測 `on_start` 為 `10/27`／`58/61`，且「27B 多為段落內任意秒數」不成立）、
  **F-D**（W3 宣稱，即上述不實句）。審查同時**維持「未放寬標準」判定**。
- **rev 6 對應動作**：F-C→R20 改寫並分述 MoE／27B 兩種成因（本節 §2）；F-D→W3 補列 `metric_version`
  （與 header `:17`、本節 R3 敘述一致）；R5 的極低瑕疵（措辭）不動。
- **產物標籤更正（獨立查核發現，attempt-04 複核成立；該輪明確判定「不需為此遞增計畫修訂」）**：
  1. `e2e/attempt-B2-27b-fix/attempt.json` 的 `timing_breakdown` 有**三處標籤錯**：
     `merge_call_seconds=360`（＋`4,146` tokens）實為**抽取（extraction）**那一次呼叫；
     `chunk_extraction_seconds=80` 在日誌**無對應大呼叫**（那 7–9 s／222–326 tokens 是 12 次**語意校正**小呼叫）；
     `asr_and_diarization_seconds=299` 實為「ASR 16.7 s ＋ diarization 153.7 s ＋ 語意校正 127 s」的窗。
     管線自證行：`chunk_count=1, merge_rounds=0, extraction=360.9, final_and_refine=1043.9, total=1404.7`
     （`data/cache/e2e/p2-27b-fix-01/backend.log:427`）。→ 以 **errata 補註**處理（`attempt.json` 新增
     `timing_breakdown_errata_20260922`、`run_notes.md` 追加「§六 errata」；**原始欄位保留不修改**，
     符合 append-only）。`[DECIDED]`
  2. 研究文件 §10.7「B2 耗時構成」段落同一個錯標 → **就地更正**（該文件是本波交付物）。
  3. `e2e/attempt-B1-moe-fix/run_notes.md` 對照表把 **v1.0 儀器的同名欄位**標成 `on_start_tag_ratio`
     （v1.0 的 `exact_tag_ratio` 已要求發言者一致，不精確的是 docstring）→ **以 errata 段落補註**，
     不改既有數字（append-only）。
  4. **模型無關性查核（另開 fresh context）**：修復路徑 `backend/core/text_postprocess.py` 內
     **零模型名、零引擎分支** `[VERIFIED]`；`_finalize_record_text(mode="local")` 由 lmstudio／ollama
     共用（測試以假引擎釘住）`[VERIFIED]`；但 **Ollama 實機未驗** `[UNVERIFIED]`，且文件原本漏列多項
     可攜性硬前提 → 由 §7 N-2 處理。
  5. **研究文件兩處事實更正（已完成）**：`OLLAMA_BASE_URL` 預設值（`http://127.0.0.1:11434` →
     `http://host.docker.internal:11434`，`config.py:49-52`）；「唯一硬前提」改為**六項硬前提清單**
     （段落列格式、diarization 模型、compose 寫死值、模型 tag、context 預算不對稱、模板／模式），
     並明示「示警只在離線量測、系統不會自動告警」。`[DECIDED]`

## 7. 使用者新增需求（2026-09-22 晚間；rev 6 納入）

**N-1 Gemma 4 31B 修復後 E2E（CORE，本輪新增）**

- 模型：`gemma-4-31B-it-MLX-4bit`（LM Studio；使用者下載中，ETA 約 25 分鐘）。
- 條件與判準：與 §4 第 3 點完全相同（同一支 `0903-科務會議.m4a`、模板 `section_meeting`、模式 `local`、
  同一支 v1.1 儀器、同一組閘門），必要時附吸附前後對照。
- 目的：證明「出處標註確定性吸附」**不是為 qwen-splash 客製**——換第三方模型家族（Gemma）仍達標。
- 證據：新增 `e2e/attempt-C1-gemma31b-fix/`（append-only）。若下載未完成、載入失敗、或引擎拒絕所需參數，
  **如實記錄為未執行／部分執行與原因**，不得以推論代替實測；此情境下 N-1 降級為 `BEST_EFFORT`，
  並需在 `run_notes.md` 明示未取得哪些數字。
- 已知風險：本機（Mac）對 31B MLX-4bit 的承載性與速度 `[UNVERIFIED]`（原 §1 曾列為排除項）。

**N-2 macOS／Windows 雙平台支援（CORE，本輪新增）**

- 本專案原本即設計為跨平台（macOS：LM Studio；Windows 11＋RTX 4090：Ollama）；本波修復必須兩邊都成立。
- 驗收（程式碼／文件層；本機**無 Windows 實機**，該事實必須明示）：
  1. 地端後處理鏈為兩平台共用：`_summarize_with_local_pipeline` → `_finalize_record_text(mode="local")`，
     由測試以假引擎釘住（既有契約測試）。
  2. 引擎選擇符合平台設計：macOS 走 LM Studio、非 Darwin 的 `auto` 走 Ollama
     （`backend/core/platform_config.py`、`_select_local_engine`）。
  3. 修復路徑**無 OS 分支、無模型名分支**（`backend/core/text_postprocess.py`）。
  4. 文件如實列出 Win11／Ollama 的可攜性硬前提：diarization 模型需就緒、`docker-compose-windows-gpu.yml`
     會寫死 `OLLAMA_BASE_URL` 與 `LOCAL_LLM_MODEL`（改 `.env` 無效，須改 compose）、
     `LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS` 決定可用 context、逐字稿段落列格式
     `[HH:MM:SS - HH:MM:SS] 發言者：`；並更正研究文件兩處與事實不符的敘述（Ollama 預設 URL、
     「唯一硬前提」的過度簡化）。`[SUPPORTING]`
- 明示：**Windows 實機行為未驗** `[UNVERIFIED]`；本輪做到的是「程式碼／文件層證明＋前提完整揭露」。

**本輪阻斷力**：N-1 的機械閘門（若實際執行）與 N-2 的第 1–3 項具全域阻斷力；N-2 第 4 項為 SUPPORTING。
