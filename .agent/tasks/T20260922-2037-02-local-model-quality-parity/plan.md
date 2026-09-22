# T20260922-2037-02-local-model-quality-parity — PLAN（P2 可查核性波；rev 9 含 P3 波定稿）

- TASK_ID: `T20260922-2037-02-local-model-quality-parity`
- PLAN_REVISION: 9
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
  - rev 7＝**新波 P3（品質對齊度量與補強收斂）**，見 §8。觸發事實有三：
    ①使用者原始痛點「地端品質跟雲端 Gemini 差很多」至今**沒有任何量尺能量**——
      rev 6 的閘門（`on_start_tag_ratio` 等）只證明「標註可查核」，C1 實測 Gemma 已在閘門全綠的情況下
      漏掉整條事實，證明閘門與痛點之間存在**指標盲區**（R25）。
    ②獨立驗收（`e2e/attempt-C1-gemma31b-fix/verify_independent.md`）發現吸附有**倒退一格**與**非冪等**
      兩個實作缺陷（R24），而主指標對它們無感。
    ③`P1-17` 補強迴圈的假陽性根因已定位（R23）：27B 實測 2 輪補強白燒 710 s（佔總時長 42%），
      且每輪都是「整份紀錄重生成」，對品質是**負向**風險（可能改壞已正確的段落）。
    本輪使用者另確認 `gemma-4-31B-it-MLX-4bit` 已下載完成並要求實測（§8.0 N-3）。
  - rev 8＝依 `review/attempt-06`（判 `PLAN_REVISION_REQUIRED`：R1／R3／R2）收斂三個阻斷項，
    並如實回填 C2 雲端基線的**外部失敗**（Gemini `503 high demand`）與覆蓋率初步數字。
    ①**R3**：CORE-5 放棄「半開區間」，改採審查者實測等效但更小的**閉區間 ＋ 段首命中優先**
    （保留 C1 唯一真修正的良性吸附，且同樣不倒退、冪等）；
    ②**R1**：觀察值更名 `snapped_across_segment`（定義＝落點段落**不含**原時間戳），
    移除與「段落內吸附本來就往段首退」自相矛盾的舊定義（舊名 `snapped_backward`）；
    ③**R2**：門檻由草案的「bigram ≥0.75」改為**滑窗 LCS ≥0.6**（如實反映已定案實作），
    並新增兩條方向一律「往更嚴」的守衛（否定詞、≥3 位數字）。本修訂只動受影響段落，
    已核准的 rev 7 敘述不重寫。`[DECIDED]`
  - rev 9＝依 `review/attempt-07`（判 `PLAN_REVISION_REQUIRED`：R1／R3／R2）收斂三個阻斷項，
    並與實作／證據對齊（本修訂**只改寫受影響段落**，rev 7／rev 8 的敘述原則上保留）。
    ①**R1（閘門效度／如實性）**：`snapped_across_segment` 由建構保證恆 0、無鑑別力，
    不得當回歸絆索 → **移除**；回歸絆索改為「冪等 ＋ 規則 0 有作用 ＋ 後退幅度可觀測」，
    並補上「鑑別力對照」（新實作 0 筆 vs v1.0 23 筆）以證明絆索真的會亮。
    ②**R3（冪等失效）**：rev 8 的單層「段首命中優先」擋不住**跨發言者交界**（後段屬別的發言者
    時，同發言者清單內沒有 `start == seconds` 的段落）→ 新增**規則 0 全域段首保護**
    （時間戳若已是**任一**真實段落起點即原樣保留），才使「不跨段後退」與冪等在**一般輸入**下成立。
    ③**R2（守衛可被洗白）**：否定詞／數字守衛的判定範圍由「整份紀錄」縮為**局部**
    （最佳視窗 ∩ 最相近一句），且數字門檻由 3 位放寬為 **2 位**（`9月30日→9月20日` 的
    LCS 0.9375 反例）；並如實記錄殘留盲區（否定詞緊鄰反轉子句且落在視窗內仍可能放行）。
    另：§8.6-1 的測試基準由 928 更新為 rev 9 實測值。`[DECIDED]`
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

## 8. P3 波（rev 7，2026-09-23）：品質對齊度量與補強收斂

### 8.0 使用者本輪需求（不可縮小）

- **N-3（Gemma 4 31B 實測）**：`gemma-4-31B-it-MLX-4bit` 已下載完成。LM Studio 內的 model key
  為 `gemma-4-31b-it-mlx`（`lmstudio-community`，`4bit`，18.44 GB，`gemma4`，context 71,936）。
  C1 已於此模型完成修復後 E2E（PASS ＋獨立驗收，`e2e/attempt-C1-gemma31b-fix/`）；本波再以
  **新量尺**重跑一次（D1），讓 Gemma 這條基線同時具備「可查核性」與「涵蓋率」兩個維度。
- **N-4（品質對齊）**：使用者原話——「人工看過這兩次輸出的會議紀錄，品質都非常不夠理想，
  跟雲端 Gemini 差很多」。這是本任務的**第一性目標**；在能量測之前，「差距」與「改善」都無法被證明。
- **N-5（模型無關＋雙平台，沿用）**：機制不得針對特定模型；macOS（LM Studio）與
  Windows 11＋RTX 4090（Ollama）皆須適用。

### 8.1 本波根因（新增）

| ID | 根因 | 證據 | 影響 |
|---|---|---|---|
| R23 | **補強迴圈的待辦召回比對是「整條標籤的連續子字串」判定，且正規化不對稱**：紀錄側已過 OpenCC 台灣正體＋模板詞彙修正（`_finalize_record_text(mode="local")` 在驗證**之前**執行），筆記側（`merged_notes`）完全沒過同一條正規化。加上 `merged_notes` 在迴圈中**固定不變**，假陽性集合註定逐輪相同 → **不收斂** | `backend/services/summarization.py:1014-1016`（`key not in normalized_summary`）、`:914-916`（`_normalize_action_key` 不做簡繁折疊）、`:2180-2240`（補強迴圈） | 27B 實測 2 輪補強、白燒 710 s（總時長 1,703 s 的 42%）；且每輪都是整份紀錄重生成 → 對品質是負向風險 |
| R24 | **吸附規則 3 用閉區間取「第一個含此秒數的段落」**：時間戳恰好等於前一段 `end` 時，會被拉回**前一段**的 `start`（倒退一格）；且函式**非冪等**（重複套用單向後退） | `backend/core/text_postprocess.py:868/876`（`seg[0] <= seconds <= seg[1]`）；C1 獨立驗收：7 個改變值中 6 個是倒退（如 `00:18:09→00:18:06`） | 落點仍是「真實段落起點」→ 主指標 `on_start_tag_ratio` 無感（**指標盲區**）；時間精度受損，且對已吸附過的文字再跑一次會再退一格 |
| R25 | **沒有任何量尺能量涵蓋率／忠實度** | C1 實測 Gemma 在閘門全綠（`on_start 20/20 = 1.000`、表格標註 0）的情況下漏掉整條事實（省員／小秘書／嘉義／選舉／視察／排水管／露臺／藤蔓／李飛，部分曾出現在萃取筆記） | 「跟 Gemini 差多少」無法回答；品質改善無法被驗證，只能靠人工印象 |

### 8.2 CORE-3：涵蓋率量尺（確定性、模型無關、雲端與地端共用）`[全域阻斷]`

- 交付 `scripts/e2e/measure_coverage.py`：輸入「受測紀錄 Markdown」＋「事實清單 JSON」→ 輸出
  `coverage_all`／`coverage_core`／`coverage_supporting`／`missing_core_ids`／`by_category` 等指標。
- **不靠第二個 LLM**：判定完全是字串運算（正規化＋probe 比對），因此雲端與地端受同一把尺量測，
  也因此在 Windows/Ollama 上可重現（純 Python、無 MLX/CoreML 依賴）。
- 正規化必須**雙向對稱**：受測文字與 checklist probe **走同一條**正規化
  （NFKC → 空白/換行折疊 → 標點移除 → 簡繁折疊；CRLF 不得造成差異）。
- 事實清單（`quality/fact_checklist.json`）由逐字稿**逐段人工/agent 萃取**，≥45 條、`core` ≥20 條，
  每條含 `probes`（group 內 AND、group 間 OR，token ≥2 字，需含同音錯字與改寫變體）。
- **明示限制**：這是「以人工標準答案為基準的召回率」，不是語意相似度；probe 寫不好會系統性低估。
  工具必須輸出 `warnings` 與自身 `metric_version`，且同一輸入必須 byte 級可重現。
- **rev 8 回填（已落地）**：儀器 `scripts/e2e/measure_coverage.py` 已完成（`metric_version: coverage-1.0.0`，
  確定性、15 項單元測試），事實清單 `quality/fact_checklist.json` 為 67 條（core 28／supporting 39，
  sha256 前綴 `cf012d1f`），作者註記在 `quality/fact_checklist_notes.md`。三份既有地端紀錄的初步量測
  （見 `quality/coverage/coverage_*.md`）：**Gemma 4 31B `coverage_core 0.7500`／`coverage_all 0.5672`、
  Qwen 27B dense `0.8929`／`0.8209`、Qwen 35B-A3B MoE `0.8214`／`0.6269`**；三模型共同缺 `F025`
  （800×17＝13600 元的文康經費算式）與 `F066`（原空間移交新聞行銷處）。同一組 probes 對逐字稿自檢
  0.9701–0.9851 → 清單本身有落地，缺口主要來自模型漏寫（但仍有偽陰性，需人工抽查）。
  `[VERIFIED]`（單次抽樣，不得外推為模型本質優劣。）
- **C2 雲端基線如實狀態**：`attempt-C2-cloud-baseline` 為 **FAIL（外部因素）**——Gemini 回 `503 high demand`，
  產品正確 fallback 成逐字稿 DOCX（`summary_failed=true`），因此**本波拿不到可比的雲端紀錄**，
  「地端 vs 雲端」的覆蓋率對照在 D1 之後仍需一次重跑（另開 `attempt-C3-cloud-baseline`，append-only）。
  旁證：雲端模式仍會用 LM Studio 跑 11 次語意校正小呼叫（`needs_local_llm` 含逐字稿校正），總 wall time ≈10.5 分。
  `[VERIFIED]`

### 8.3 CORE-4：補強假陽性與不收斂修復（R23）`[全域阻斷]`

- 對稱化：`_normalize_action_key` 對「紀錄側」與「筆記側」套用**同一條**正規化
  （含簡繁折疊；沿用 `backend/core/text_postprocess.to_taiwan_traditional` 的既有能力，不新增依賴）。
- 判定改為**滑窗 LCS（最長共同子序列）比例**＋「整條子字串」短路（rev 8 定案，取代 rev 7 草案的
  「bigram ≥0.75」）：只有當紀錄中存在一段**連續視窗**（長度＝標籤正規化長度 ＋ 4，
  候選視窗由標籤自身的字元 bigram 在紀錄中的出現位置反推）涵蓋標籤的 ≥ 門檻比例才算已涵蓋，
  門檻常數 `ACTION_MATCH_MIN_LCS_RATIO = 0.6`。**不得**改成「所有字都在紀錄裡就算過」
  （那會製造 false negative，讓真遺漏不再觸發補強）。
  - 校準（真實 0903 場 27B 輸出）：**確實已涵蓋**的改寫標籤落點 **0.69–1.00**
    （含被舊版整條子字串比對誤判的假陽性，例「征收股→徵收股」0.94）；逐字稿**真的沒寫**的
    對照句落點 **0.27–0.42**。兩側皆留有餘裕。
  - **LCS 是字面量尺**，對「語意反轉但字面重疊」不敏感 → 追加兩條**往更嚴**的確定性守衛
    （近似比對通過後仍必須成立，否則一律判遺漏）：
    ①**否定詞守衛**：標籤內的否定詞（`ACTION_NEGATION_TERMS`＝嚴禁／禁止／不得／勿／避免／不可）
    必須原樣出現在紀錄中（實測對照句 LCS 0.917 會被誤判已涵蓋）；
    ②**數字守衛**：標籤內 **≥2 位數字串**必須原樣出現（實測 0.818；真實缺口：800×17＝13600 元
    的算式被寫成「約一萬多元」）。兩條都在同一條對稱正規化後比對（全形／半形、千分位逗號已折疊）。
    方向刻意往更嚴：代價是可能多一輪補強（已有不收斂保護上限），收益是不會把失真當成已涵蓋。
    - **rev 9 收斂（`review/attempt-07` R2）**：兩條守衛的判定範圍由「整份紀錄」縮為**局部**——
      必須同時落在①最佳比對視窗（該 LCS 得分的來源視窗）與②與該項目最相近的一句紀錄
      （以 `[。！？!?；;\n]` 切句）之內；**兩者都必須含該 token 才放行**。
      理由：全域判定會被「別的子句剛好有『嚴禁』」洗白（實測：反轉後他處仍留「嚴禁」→
      ratio 0.9048、舊全域守衛放行）。
    - **數字門檻由 3 位放寬為 2 位**（rev 9）：`9月30日` 被改寫成 `9月20日` 時，唯一可辨識的
      差異是 2 位數 `30`，LCS 0.9375 會把它洗白；放寬後該反例**判遺漏** `[VERIFIED]`。
    - **已知代價（如實）**：更嚴的守衛會把「以中文國字表示的兩位數」（例「十七台」）判成遺漏 →
      至多多觸發**一輪**補強（不收斂保護＋輪數上限仍在），不會把失真當成已涵蓋。
    - **殘留盲區（如實，`review/attempt-07` 反例的殘餘）**：否定詞若**緊鄰**被反轉的子句、
      且落在最佳視窗內（≈標籤長度 ＋4），仍可能被放行——實測
      `嚴禁遲到，得將科內群組訊息（含照片）外流至任何外部渠道。` 判為「已涵蓋」
      （掃描：gap 0–9／0–11 放行、≥10／12 判遺漏）。這是舊版「任意距離白名單」的**子集**
      （非回歸），列為已知限制（見 §8.7），下一波以語意層量尺處理。`[VERIFIED]`
    - 真實材料假陽性（`quality/guard_calibration.md` §rev 9）：主探針 37 keys **額外假陽性 0**、
      真實 log 的 14 個 key **額外假陽性 0**（其中 `嚴禁轉傳科內群組訊息至外部` ratio 0.6923
      由守衛實跑並放行）；tamper（抽掉否定詞／數字）4/4 判遺漏、整條刪除 21/37 立即判遺漏。`[VERIFIED]`
- 不收斂保護：補強前後問題集合相同 → 立即停止並記錄，不再重生成第二輪（避免白燒與品質退化）。
- 驗收（單元測試，三側都要）：①把一項待辦從紀錄整條刪掉 → **必須**觸發補強；
  ②同一項待辦改寫（的／之、征收／徵收、及／、，或加上「請於下週三前」）→ **不得**誤判遺漏；
  ③守衛雙向：否定詞／數字**缺失**時即使 LCS 已達門檻也必須判遺漏；**保留**時（含「13,600」＝「13600」
  這類千分位對稱）不得誤判；且不到三位數的數字（例 17 台）不納入守衛。

### 8.4 CORE-5：吸附精度（不倒退）與冪等性（R24／R26）`[全域阻斷]`

- **rev 9 定案（兩層保證）**：R24 的真正根因不是「閉區間」，而是「**取清單中第一個命中的段落**」
  這個**順序**——時間戳恰等於相鄰兩段交界（前段 `end` ＝ 後段 `start`）時，先出現的前一段勝出
  → 被吸回前一段起點＝倒退一格。修正由**兩層**構成（單層不足，見下）：
  ①**規則 0 全域段首保護**：時間戳若已是**任一**真實段落的起點 → 原樣保留（計 `kept_on_start`）；
  ②**段首命中優先**：先找 `start == seconds` 的段落，找不到才取第一個含此秒數的段落；
  且**所有吸附落點都只能是某段 `start`**（規則 1／2／3 的目標一律取 `seg[0]`）。
  段落區間維持**閉區間 `[start, end]`**（零長度段落退化為單點）。
  - **為什麼 rev 8 的單層不夠（`review/attempt-07` R3 反例）**：**跨發言者交界**時
    （前段 `end` ＝ 後段 `start`，而後段屬**別的發言者**），同發言者清單內沒有任何
    `start == seconds` 的段落 → 段首優先接不住，仍會後退。A1 素材實測 `changed=12`、
    其中 9 筆原值已是**全域**段首（例 `00:13:37 → 00:13:12`，並出現鏈式後退
    `00:18:40→00:16:40→00:14:40`＝非冪等）。規則 0 直接封住這一類。
  - 採用理由（審查者 `review/attempt-06` 實測 ＋ Planner 對照重跑）：半開區間雖然也能不倒退，
    但會把「時間戳恰為某段 `end` 且非任何段 `start`」的**良性吸附**打成不可回溯
    （C1 唯一真正被修正的 `00:10:04 → 00:08:15` 即屬此類），並使 `on_start_tag_ratio` 由 1.000
    降到 0.95＝恰壓閘門線。
- 保證 `f(f(x)) == f(x)`：吸附後再套用一次**必須** byte 級不變（不是「同輸入跑兩次相同」——
  既有測試只驗了後者，這是它抓不到這個 bug 的原因）。冪等的**保證來源是規則 0**：
  落點一律是真實段首，第二輪必落入規則 0 而被原樣保留；`_pick_containing_segment` 的段首優先
  只是輔助。`[VERIFIED]`（`quality/snap_interval_variant_check.md` §rev 9：五個素材二次套用皆
  byte 相同、`changed=0`。）
- 觀察值（**rev 9 更名**）：`kept_on_start`（規則 0 接住的筆數）、`backward_moves`／
  `max_backward_seconds`（往前收筆數與最大幅度）、`forward_moves`、`snapped_exact`／
  `snapped_nearest`／`snapped_speaker_mismatch`、`changed`、`kept_far`、`untraceable`；
  產品端 log（`[品質] 地端紀錄後處理…`）與 E2E 都要能看到。
  - **如實**：`snapped_across_segment`（rev 8 工作名；定義＝落點段落「不含」原時間戳）**已移除**。
    理由（`review/attempt-07` R1）：規則 1／3 的落點由建構即為「含原時間戳之段落的 `start`」，
    故該值恆 0、**無鑑別力**——把 `_pick_containing_segment` 換回 v1.0 順序時 `changed=14`，
    它仍是 0。**恆真值不得當閘門或回歸絆索**（本波自省：rev 8 犯了與 rev 3 `exact_tag_ratio`
    同型的錯誤）。
  - 回歸絆索因此改為三件事：①**冪等**（二次套用 `changed == 0`）；②**規則 0 有作用**
    （已是全域段首的標註不得被搬動）；③**後退幅度可觀測且受限**（`backward_moves`／
    `max_backward_seconds`；段落內吸附本來就往段首退，這是設計而非缺陷）。
- **鑑別力實測**（`quality/snap_interval_variant_check.md` §rev 9）：指標「原值已是全域真實段首
  卻仍被改寫」——新實作 **0/0/0/0/0**（27B／Gemma／MoE＋A1＋跨發言者 fixture）；
  v1.0 對照 **4/4/3/11/1（合計 23 筆，全為後退）**。另以「機械移除規則 0 區塊」重建 rev 8：
  A1 素材 `changed=12`、其中 9 筆∈全域段首（與 `review/attempt-07` 記載的 12／9 一致），
  跨發言者 fixture 上 rev 8 仍會改寫 → 證實規則 0 是「不跨段後退」與「冪等」的**必要條件**。`[VERIFIED]`
- A1 素材（舊執行產物）在新實作下 `changed=3`、`kept_on_start=58/61`、`backward_moves=3`、
  `max_backward_seconds=70`；三筆皆為同一時間戳 `00:25:21 → 00:24:11`——該值＝某段 `end`
  且非任一 `start`，屬**段落內邊界吸附**，不是跨段倒退。`[VERIFIED]`
- `measure_tag_traceability` 的「落在任一真實段落內」與吸附**共用同一份閉區間語意**（量尺不得與產品
  對同一份逐字稿給出不同答案）；區間語意變更時必須**同步遞增 `metric_version`**，且**量測既有三份
  紀錄的受影響筆數**，若 > 0 必須在新報告中明示（避免歷史數字被靜默改寫）。

### 8.5 工作項（本波）

- W7：`scripts/e2e/measure_coverage.py`（＋單元測試；確定性、對稱正規化、OpenCC 不可用時 fallback 並標記）。
  **狀態：已完成**（15 項單元測試綠）。
- W8：`quality/fact_checklist.json`（逐段萃取；≥45 條／core ≥20）＋作者註記（收／不收的判準與限制）。
  **狀態：已完成**（67 條／core 28）。
- W9：`backend/core/text_postprocess.py` 吸附**閉區間＋段首命中優先＋規則 0 全域段首保護**＋新觀察值
  （`kept_on_start`／`backward_moves`／`max_backward_seconds`）＋冪等／跨發言者交界回歸測試。
  **狀態：程式與測試已完成（`tests/test_t20260922_2037_p3_parity.py` 19 項綠；rev 9 校準見
  `quality/snap_interval_variant_check.md`）；待 D1 E2E 以真實輸出複驗。**
- W10：`backend/services/summarization.py` 對稱正規化＋滑窗 LCS（0.6）＋否定詞／數字兩守衛
  （**局部判定＋≥2 位**）＋不收斂保護。
  **狀態：程式與測試已完成（含審查 R2 的兩個反例：反轉＋他處仍有否定詞、`9月30日→9月20日`）；
  待 D1 E2E 複驗（補強輪數 ≤1）。**
- W11：E2E — C2＝雲端 Gemini 同一音檔／模板（`attempt-C2-cloud-baseline`）；**結果 FAIL（Gemini 503，
  外部因素，見 §8.2）**，需另開 `attempt-C3-cloud-baseline` 重跑（append-only）。
  D1＝Gemma 4 31B 修復後（`local`，含新量尺）；兩份紀錄用同一把尺量覆蓋率並公開缺口。
- W12：研究文件 §11 回填、操作手冊勘誤（`LOCAL_LLM_PROVIDER` 語意、v1.0→v1.1 吸附 errata、
  E2E runner 的 LM Studio-only 限制、diarization／tzdata 前提）、`run_notes.md`、commit＋push。
- W13：P3 的跨平台稽核（`research/audit-03-windows-ollama-p3.md`）與真實產物校準證據
  （`quality/snap_interval_variant_check.md`、`quality/guard_calibration.md`；兩份報告的
  §rev 9 量測為 append-only 追加，rev 8 段落保留並標註「勿混用」）。
  **狀態：已完成**（rev 9：鑑別力對照、五素材冪等、審查兩反例、真實材料假陽性 0）。

### 8.8 獨立審查（P3，如實）與 rev 9 的收斂

- `review/attempt-05`（fresh context；受審＝rev 7 快照）→ `PLAN_REVISION_REQUIRED`。
- `review/attempt-06`（fresh context；受審＝rev 7）→ `PLAN_REVISION_REQUIRED`（R1／R3／R2）→ rev 8。
- `review/attempt-07`（fresh context；受審＝rev 8 快照，sha256 見該目錄）→ `PLAN_REVISION_REQUIRED`：
  - **R1**：`snapped_across_segment` 恆 0、**無鑑別力**（換回 v1.0 順序時 `changed=14` 它仍為 0）
    → 不得當回歸絆索／閘門。**rev 9 動作**：移除該值，絆索改為冪等＋規則 0 有作用＋後退幅度，
    並補「鑑別力對照」（新 0 筆 vs v1.0 23 筆）。
  - **R3**：跨發言者交界冪等失效（`00:18:40→00:16:40→00:14:40`；A1 素材 `changed=12`，
    其中 9 筆原值已是全域段首，例 `00:13:37→00:13:12`）。**rev 9 動作**：新增**規則 0 全域段首保護**。
  - **R2**：否定詞守衛只攔「全域缺席」（別子句有『嚴禁』就放行）、`9月30日→9月20日` LCS 0.9375
    被洗白。**rev 9 動作**：守衛判定改為**局部**（最佳視窗 ∩ 最相近一句）＋數字門檻 **≥2 位**；
    並如實保留殘留盲區（否定詞緊鄰反轉子句且落在視窗內仍可能放行）於 §8.3／§8.7。
- **本節如實界線**：以上都是**單一會議、單次抽樣**的實測與合成 fixture，不得外推為模型或方法的
  本質優劣；rev 9 的收斂是否成立，由獨立的 `review/attempt-08` 判定（append-only）。

### 8.6 驗收（本波）

1. `pytest tests/ -q --ignore=tests/test_end_to_end.py` 全綠（rev 6 基準：900 passed／2 skipped；
   rev 8 實測：928 passed／2 skipped；**rev 9 實測：933 passed／2 skipped**）。
2. CORE-3：新儀器存在、確定性可重現（同輸入 byte 相同）、對稱正規化測試通過（全形/半形、簡繁、標點、CRLF）。
3. CORE-4：§8.3 的三側單元測試通過（含守衛雙向）；**rev 9 追加**：`review/attempt-07` 的兩個
   反例（反轉後他處仍有否定詞、`9月30日→9月20日`）必須判遺漏，且「否定詞出現在**別的子句**」
   仍必須判遺漏；D1 E2E 的補強輪數 ≤ 1（C1 為 1 輪、B2 為 2 輪），且 log 不得出現
   「連續兩輪問題集合相同仍繼續補強」；守衛若攔下任何一項，log 必須留下「未涵蓋項目＋最佳 LCS 比例」
   的可查核訊息。
4. CORE-5：冪等測試通過（含**跨發言者交界**）；**rev 9 回歸絆索**（取代 rev 8 的恆真閘門）：
   ①D1 紀錄**二次套用吸附 `changed == 0`**；②**已是全域段首的標註未被搬動**
   （`kept_on_start` 有作用；等價檢查＝「原值為全域段首卻被改寫」筆數為 0，鑑別力已對照
   v1.0 的 23 筆）；③`backward_moves` 只出現在段落內吸附、幅度 `max_backward_seconds` 可觀測；
   ④`on_start_tag_ratio` 不低於 rev 6 閘門（≥0.95）。
5. 對照：D1（地端 Gemma 4 31B）產出正式 DOCX 並以同一把尺公開 `coverage_core`／`coverage_all`；
   C2（雲端）因 Gemini 503 失敗，**本波不宣稱取得雲端可比基線**，改列為下一波第一優先（`attempt-C3`）。
6. 雲端不變性：`mode="cloud"` byte 級不變（既有測試釘住，本波不得放寬）。
7. **明示不宣稱**：本波**不**把「地端 `coverage_core` ≥ 雲端 − X」設為阻斷閘門。理由：單次抽樣
   （temperature 0.6／0.7）＋量尺本身是近似；把單樣本數字當全域閘門會製造 system-wide false FAIL
   （與 rev 3 判定 `exact_tag_ratio` 屬量尺缺陷同一類錯誤）。改為：**量測、公開、若缺口 > 20 個百分點
   則必須列出下一波可執行槓桿**，且不得把「閘門全綠」表述為「品質已達雲端水準」。

### 8.7 風險與已知限制

- 覆蓋率量尺是人工標準答案的近似；同音錯字／ASR 誤辨可能讓某條事實「就算寫對也對不上 probe」。
- LCS 門檻（0.6）是 false positive 與 false negative 的取捨：D1 之後需**人工複核**一份缺失清單，
  確認沒有把真遺漏洗成「已涵蓋」（`quality/guard_calibration.md` 已有既有三份紀錄的假陽性量測）。
- 兩條守衛是**往更嚴**的方向：可能把「否定詞被同義改寫（嚴禁→不得）」「數字被合理改寫
  （13600→一萬三千六百）」誤判成遺漏 → 觸發一輪補強。此風險由①不收斂保護（最多 1 輪）
  ②補強訊息指名具體缺項 兩者圍堵；殘餘風險＝多花一輪生成時間。
- **覆蓋率量尺不判否定與數值正確性、也無法量「寫得對不對、歸屬對不對」**（關鍵詞堆砌可刷分）；
  它只是「人工標準答案的召回率」。品質的忠實度維度需另一把尺（下一波）。
- 雲端可比基線本波**未取得**（Gemini 503）：任何「地端 vs 雲端」的數字在 C3 重跑前都**不得**發布。
- 單樣本、溫度 0.6／0.7，數字不得外推為模型本質優劣。
- Windows 11＋Ollama 實機仍未驗 `[UNVERIFIED]`（本波只有程式碼／文件層證據＋ §7 N-2 的前提清單）。
- **rev 9 新增風險①（規則 0 的語意界線）**：規則 0 保護的是「時間戳已是**任一真實段落起點**」
  這件事實，**不是**「內容歸屬正確」。逐字稿段落表若有錯（例如同一秒被兩段共用、或模型標了
  真段首但語意上該指別的段落），規則 0 會**原樣保留**該值 → 這類錯誤本波不處理（屬下一波的
  語意層量尺）。如實界線：本波只保證「不跨段後退」與「冪等」。
- **rev 9 新增風險②（守衛的已知盲區）**：①否定詞若**緊鄰**反轉子句且落在最佳視窗內
  （≈標籤長度 ＋4），仍可能被放行（實測反例見 §8.3）；②`\\d{2,}` 在**真實文件**上的假陽性率
  `[UNKNOWN]`（本批校準沒有「含 2 位數 token 且需走守衛路徑」的真實 key）；③否定詞被**同義替換**
  （嚴禁→禁止）仍會被字面守衛誤攔 → 多一輪補強。三者皆**非回歸**（方向一律往更嚴），
  但都是下一波（語意層／詞彙表擴充）的待辦。
- **rev 9 新增風險③（樣本代表性）**：校準素材＝同一場會議（0903）的舊執行產物 ＋ 合成 fixture；
  A1 素材是**修復前**的執行產物。因此 rev 9 的「三份紀錄 `changed=0`、冪等」屬 fixpoint 材料，
  不得外推為「任意輸入都不倒退」——一般輸入的保證由**規則 0 的建構性論證 ＋ 鑑別力對照**提供。
