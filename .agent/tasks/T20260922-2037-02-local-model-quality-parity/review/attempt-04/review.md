# 獨立計畫審查 — T20260922-2037-02-local-model-quality-parity（Stage 02／attempt-04，修訂複審）

- 受審對象：`.agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md`；自稱 `PLAN_REVISION 5`（`plan.md:4`）。
- 受審快照：sha256 `3c0474a96a04fd889e2edbfe5b79cf53e23f641d511491f94efed8a20effeaf3`（176 行、15,574 bytes、mtime `2026-09-22 22:27:30`）；開審前後各量一次，同值（見 §11）。
- 審查者：獨立 Stage 02（fresh context；read-only）。未修改產品碼、`plan.md`、`review/attempt-01..03`、既有 e2e 證據、研究文件；僅新增本檔（`review/attempt-04/`）。依任務硬約束，本目錄只寫 `review.md`、未另存 `plan_snapshot.md`；受審內容以 revision＋sha256＋逐處引文釘住。
- 範圍（依指派）：①R1（修訂紀錄不準確）是否真收斂、是否主動寫出「rev 4 曾宣稱不實」；②R2–R5 是否處理；③是否放寬標準／契約文字與實作是否相反；④是否新稱未驗證之事（尤其 B2 覆蓋率／與雲端 Gemini 對照）；⑤兩位獨立查核者所指之兩類「標籤錯誤／跨量尺比較」（B2 timing 錯標、B1 跨量尺錯標）之獨立複核與 rev 6 判定。
- 實際動作（全部實跑；輸出摘要）：

1. `git status --short`、`git log --oneline -3` → HEAD `3fec08f`（branch `fix/qwen-local-quality-parity`）；工作樹含本波未提交變更（`plan.md`、`backend/core/text_postprocess.py`、研究文件、`tests/test_t20260922_record_quality.py`、`scripts/e2e/measure_record_quality.py`、`CHANGELOG/README/VERSION` 等）與未追蹤之 `e2e/attempt-B2-27b-fix/`、`review/`（預期現象）；**無新 commit、無 push**。
2. `shasum -a 256 plan.md` → `3c0474a9…`（開審量測；收審複量同值）。
3. `DATA_DIR="$PWD/data" PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest tests/test_t20260922_record_quality.py -q -p no:randomly -p no:cacheprovider` → **`22 passed in 0.52s`**。
4. 讀 `backend/core/text_postprocess.py`：`TAG_SNAP_MAX_SHIFT_SECONDS = 120`（:762）、`kept_far` 分支（:883–887）、`metric_version`（:959）、`on_start_tag_ratio_excluding_zero` 之 `None` 分支（:969–970）。
5. 讀測試：`test_finalize_cloud_mode_is_byte_identical_to_prechange_pipeline`（`tests/test_t20260922_record_quality.py:424`）、`test_finalize_record_text_local_吸附_但_cloud_不變`（:668）、`metric_version` 斷言（:726）。
6. `python3` 讀 `e2e/attempt-B2-27b-fix/instrument_recheck_20260922.json`，與 `/tmp/b2-verify/{A1,B1,B2,P1,P1BASE}.json`（21:49–21:50、rev 5 之前副本）逐欄比對 → 五份 `tag_traceability` **逐欄完全相同（量測值未被更動）**；top-level 新增 `metric_version = tag_traceability-1.1.0`（該檔 :5）。
7. `python3` 讀 B2 `record_quality.json`（閘門值逐欄複核）與 `attempt.json`（timing_breakdown）；逐行讀 `data/cache/e2e/p2-27b-fix-01/backend.log`（:42–46、:56–123、:127、:201、:204、:271、:348、:423、:427）與 `data/cache/e2e/p2-27b-01/backend.log:255`。
8. 讀 `e2e/attempt-B2-27b-fix/{run_notes.md,attempt.json}`、`e2e/attempt-B1-moe-fix/{run_notes.md,record_quality.json}`、研究文件 §10 全文（:697–889）。
9. 逐句比對 `review/attempt-01/02/03` 與 rev 5 文字；rev 5 之實際編輯另以 planner session 逐筆編輯紀錄作**輔助**核對（凡引用處均標示「輔助」；主要證據皆為 repo 內檔案）。

## 0. Goal Baseline（重建自使用者需求與既有審查鏈）

1. 主目標：Mac＋LM Studio（`qwen3.8-27b-splash` dense 27B、`qwen3.6-35b-a3b-splash` MoE 35B-A3B）以 `section_meeting` 產出的地端會議紀錄品質「接近雲端 Gemini」；優化機制須**模型無關**（日後 Win11＋RTX 4090＋Ollama／Gemma 一體適用）。
2. 本波（P2）CORE：CORE-1 出處標註真實性（時間戳須落在逐字稿真實段落，吸附後盡量落在**真實段落起點**，閘門以**比例**表述）；CORE-2 修復位於共用確定性層、無模型名分支。S-1–S-3 為 supporting；Ollama 實機與 27B 第二輪為 best-effort；覆蓋率檢查表、溫度再校準、Gemma 實測明確排除。
3. 審查處置鏈與本輪判準：attempt-01（F1 契約文字漂移／F2 輔助閘門定義於驗收期間變更／F3 研究數字為推論值）→ attempt-02（內容面收斂；唯一阻斷 N1＝修訂身分；並判「`exact_tag_ratio` 降級是量尺修正、不是放水」）→ attempt-03（唯一阻斷 R1＝**修訂紀錄不準確**；R2–R5 低嚴重度建議）→ rev 5（本輪受審）。核心準則：**核准必須綁定唯一且如實的修訂**。

## 1. R1 驗證（真收斂＋紀錄如實）→ **主體已收斂（①已、②已）；惟新增同軸之新宣稱問題 F-D**

1. **三處絕對語氣確已改寫，且與實作一致**：
   - `plan.md:42–45`（§1 CORE-1）：「且吸附後**應**落在真實段落起點」＋「吸附**不是全量**：位移超過 `TAG_SNAP_MAX_SHIFT_SECONDS`（120 s）者…保留原時間戳」＋「閘門以**比例**表述（≥ 0.95），而非『每一筆都必須在起點』」。
   - `plan.md:88`（§2 R21）：「證明**多數**標註可用『吸附』確定性修復，**在規則覆蓋範圍內**不必重生成；超出覆蓋者（`kept_far`、跨發言者）只改時間、不改歸屬」。
   - `plan.md:111–115`（§5）：「吸附是**部分覆蓋**、且有兩種改寫語意：①規則 1／2…②規則 3…③位移 > 120 s → 原樣保留（`kept_far`）」＋「『吸附後每一筆都在段落起點』**不成立**，閘門必須用比例」。
   - 實作核對：`backend/core/text_postprocess.py:883–887`（`abs(target - seconds) > 120` → `kept_far`、保留原時間戳，仍在真實段落內）、規則 3 只改時間不改歸屬（:871–877）。**文字＝實作**。
2. **修訂紀錄如實（關鍵）**：`plan.md:12–13` 主動寫出「rev 4 曾宣稱『已收斂 N2–N5』，但 `review/attempt-03` 查核後指出 **N2 實際未收斂**（三處絕對語氣未改…）——**該宣稱不實**，已在 rev 5 更正並實際改寫這三處」；`plan.md:165–166`（§6.4）再以「**如實更正**」具名重述。對自己不利之事實已主動寫出，未見美化。
3. **惟**：rev 5 新增宣稱「⑤W3 工作項補列儀器新欄位」（`plan.md:17`、`:174–175`）與 R3 所指交付物不符 → **F-D**（與 R1 同軸之紀錄如實性問題，程度較輕）。

## 2. R2 驗證 → **已收斂**

- 研究文件 §10.5（:820–824）新增「**門檻關係（勿混淆）**」：0.9＝換引擎上線前哨寬鬆下限、0.95＝波次驗收閘門，並指向本計畫 §4 第 3 點；`plan.md:105–106` 對稱註記 `[DECIDED 依 review/attempt-03 的 R2]`。兩份文件互指、語意一致，無衝突殘留。

## 3. R3 驗證 → **①已收斂；②未收斂（W3 宣稱不實）**

1. ①recheck 檔：`instrument_recheck_20260922.json` 已含 top-level `metric_version: tag_traceability-1.1.0`（:5），且 A1／B2／P1／B1／P1BASE 之量測欄位與 rev 5 前副本**逐欄相同**（動作 6）→ 符合「僅 metadata 補註、未動量測值」。
2. ②W3（`plan.md:94–95`）現行文字僅列 `tag_traceability／exact_tag_ratio／zero_time_tag_*／distinct_tag_time_*／on_start_tag_ratio_excluding_zero`，**未列 `metric_version`**；attempt-02 原文即「W3 工作項未列 `metric_version` 為交付物（僅見於 §6.2-3）」、attempt-03 R3 為「W3 未列交付物」。rev 5 卻宣稱「W3 已補列」→ 見 F-D。

## 4. R4 驗證 → **已收斂（如實列為已知殘餘，未被宣稱解決）**

- `plan.md:52–53`：全零標註時 `on_start_tag_ratio_excluding_zero` 為 `None`＝**不判定**，改用 `on_start_tag_ratio` 與 `zero_time_tag_ratio` 人工判讀；`plan.md:171–172`：「已知殘餘風險，留待後續波為 `zero_time_tag_ratio` 訂上限」。研究 §10.7（:888）亦記 B2 覆蓋率 `[UNVERIFIED]`。**未見「已解決」宣稱**。

## 5. R5 驗證 → **已收斂**

- `plan.md:120`：標題改為「## 6. 追加實測與審查紀錄（rev 3 起；含 rev 4／rev 5 的修訂內容）」；三顆受審 hash 並列：`bf6158d0…`（:154）、`4cf6ac0a…`（:161）、`86c9744f…`（:167）。
- 微瑕（極低）：§6.4 `:173`「改寫 §1 CORE-1／§5 的**三處**」措辭易誤讀（三處＝§1 CORE-1、§2 R21、§5；`:13` 已正確列出）→ 併 F-D 順修。

## 6. 標準未放寬／契約與實作一致／未新稱未驗證之事

1. **閘門未放寬**：§4-3（:104）與 §1（:50–55）之閘門值與 rev 3／rev 4 相同（`on_start_tag_ratio ≥ 0.95`、`on_start_tag_ratio_excluding_zero ≥ 0.9`、`traceable_tag_ratio ≥ 0.95`、`body_source_tag_count ≥ 17`、表格標註 = 0；`exact_tag_ratio` 仍列觀察值，:56–57）。`ex0` 之加入使檢核更嚴（排除結構性必然命中之 `00:00:00`）；`exact_tag_ratio` 降級仍屬**量尺修正、非放水**（維持 attempt-02／attempt-03 判定）：嚴格版仍量測並如實揭露（B2 `exact = 1/52 = 0.019`），且主指標 `on_start_tag_ratio` 在釘住版 `3fec08f` 即存在。
2. **B2 閘門值與 `record_quality.json` 逐欄一致**（實讀）：`on_start_tag_ratio 1.0（52/52）`、`on_start_tag_ratio_excluding_zero 1.0（45/45）`、`traceable_tag_ratio 1.0`、`body_source_tag_count 52`、`table_source_tag_count 0`、`instruction_item_count 25`、`char_count 4,062`、`zero_time_tag_count 7`、`distinct_tag_time_count 15（0.288）`、`metric_version 1.1.0`；plan §6.1 表（:125–126）逐欄相同。
3. **`mode="cloud"` 不變性未破壞**：`tests/test_t20260922_record_quality.py:424`（cloud 與 v4.8.0 舊後處理 byte 級相同、且不套用地端修正）與 :668（local 吸附／cloud 不變）釘住；本輪 22 passed 含此二契約。
4. **未新稱未驗證之事**：plan 全文無「B2 覆蓋率已完成」「與雲端 Gemini 對照已完成」等宣稱（`:28` 為需求句；`:77` 將覆蓋率列入**明確排除**）；`run_notes.md` §四與研究 §10.7（:888）均如實記 `[UNVERIFIED]`；MoE 本輪未重測亦如實註明（§6.1 :128）。**無阻斷項。**

## 7. 補充證據複核（兩類標籤錯誤）

### F-A：B2 `timing_breakdown` 標籤錯誤 → **複核成立**

- 日誌實證（`data/cache/e2e/p2-27b-fix-01/backend.log`）：
  - :427 pipeline metrics：`chunk_count=1, logical_generations=4, merge_rounds=0, merge_groups_last_round=0, duration_seconds={'extraction': 360.9, 'merge': 0.0, 'final_and_refine': 1043.9, 'total': 1404.7}`。
  - :127 `needs_chunking=False` → 本場**沒有 9 個 chunk**。
  - :201（21:29:25）之 4,146-token 大呼叫＝**extraction**（21:23:25→21:29:25＝360 s），非 merge；其後三次大呼叫 :271（3,123 tokens／334 s）、:348（3,120／359 s）、:423（3,120／351 s）＝最終與兩輪補強（`final_and_refine` 1,043.9 ≈ 334+359+351）。
  - :56–:123（21:21:40–21:23:24）共 **12 次小呼叫**（每通間隔 7–16 s；輸出 222–326 tokens，首通 787；:123 為「語意校正完成：45 段中 8 段有修正…」）→ 這才是「約 80 s／7–9 s／250–330 tokens」之來源，**不是抽取**。
  - :42–:45：ASR 16.73 s（:42–43）、diarization 153.7 s（:45）→ `asr_and_diarization_seconds: 299` 之窗（21:18:26→21:23:25）實含發言者標註＋12 次語意校正（21:21:17→21:23:24，約 127 s）。
- 錯誤落地處：`e2e/attempt-B2-27b-fix/attempt.json:70–74`（`chunk_extraction_seconds: 80` 無對應呼叫；`merge_call_seconds: 360`＋`merge_completion_tokens: 4146` 實為 extraction）、`run_notes.md:14–16`、研究文件 §10.7（:870–871，「抽取 9 個 chunk 約 1 分鐘…整併 360 s」）。
- **同族錯誤**亦見研究 §10.7（:872）「A1…整併 306 s」——A1 日誌（`data/cache/e2e/p2-27b-01/backend.log:255`）為 `extraction=305.4, merge=0.0`。
- 不影響本波閘門與結論：B2 慢於 A1 之正確歸因（兩輪補強合計 710 s，假陽性）見 plan §6.2-1 與 `verify_independent.md`；**plan 未引用錯誤分相**。

### F-B：B1 `run_notes.md` 對照表跨量尺 → **複核成立（補充證據之括註用語需修正）**

- `e2e/attempt-B1-moe-fix/run_notes.md:20–24` 以單一欄名 `on_start_tag_ratio` 陳列三列：`p1-fixed-01 4/27 = 0.148`、`p2-27b-01 46/61 = 0.754`、`B1 14/14 = 1.000`。
- 同量尺（v1.1）實測（`instrument_recheck_20260922.json`）：P1 `exact 4/27 = 0.148`、`on_start 10/27 = 0.370`；A1 `exact 46/61 = 0.754`、`on_start 58/61 = 0.951`；B1 `on_start 14/14 = 1.0`。→ 該表 P1／A1 兩列實為 **`exact_tag_ratio`**（起點＋發言者一致），與 B1 之 `on_start` 併欄比較＝**跨量尺**。
- 用語更正（本審查獨立複核）：補充證據括註稱「`exact_tag_ratio` 在 v1.0 的定義＝時間戳等於任一真實段落起點」**不精確**——`f1e6bfe`（B1 當時 HEAD）之 instrument 實作**已要求發言者一致**（不精確的是其 docstring）；故 4/27、46/61 自始即為嚴格版數字，「應讀為 `exact`」之結論不變、僅成因描述不同。
- 修正後對照更有利（`on_start` 0.370→1.000、0.951→1.000），**無誇大風險**；須更正欄名或加註量尺。

### plan rev 5 是否重複上述錯標？→ **未重複**

- plan 對 A1／B2 只引用**總時數**（§6.1 :125–126 之 `910 s`／`1,710 s`）；全文 grep 無「360」「80 s」「9 個 chunk」「整併」等分相敘述，亦無把 4/27／46/61 標為 `on_start_tag_ratio`（`:61` 已正確標示 `on_start 10/27`／`58/61` 與 `exact 4/27`／`46/61`）。→ **此兩類錯標不落在 plan；屬產物標籤更正即可、不阻斷計畫修訂，不需為它們遞增 rev 6。**
- **但** plan 自身另有一處同族殘留（F-C，下節），此為本輪 plan 需修訂的原因之一。

## 8. 補充發現（plan 文字層）

### F-C：§2 R20 量尺誤標，且對 27B 之敘述不成立（中）

- `plan.md:86`：「模型寫得出標註，但時間戳多半是『段落內的任意秒數』｜MoE：27 個標註僅 **4** 個落在段落起點；27B：61 個中 **46** 個」。
- 4／46 是 `exact_tag_ratio` 的分子（起點**且**發言者一致）；「落在段落起點」在 v1.1 對應 `on_start_tag_ratio`，實測為 MoE **10**/27、27B **58**/61（`instrument_recheck_20260922.json`；本檔 `:61` §1 基線與 `:50–55` 定義即如此）。→ **同一份 plan 內自我矛盾**，且屬研究 §10.3 更正註記（:775）所稱「把 exact 記為 on_start」之同一錯誤家族。
- 實質影響：對 27B 而言「時間戳多半是任意秒數」**不成立**（起點命中 95%），R20 根因敘述實際只適用於 MoE（起點命中僅 37%）；保留恐誤導後續波（如 P1-16 辨別力）做出錯誤的問題排序。
- 最小修正（一行）：改為「MoE：27 個標註僅 10 個落在段落起點（嚴格發言者一致版 4 個）；27B：61 個中 58 個（嚴格版 46 個）——27B 的缺口主要在辨別力與發言者標籤，而非起點命中」。

### F-D：rev 5 宣稱「W3 已補列」與 R3 要求不符（中；R1 同軸）

- 事實：`plan.md:94–95` W3 未含 `metric_version`；attempt-02 `:64` 所指交付物即 `metric_version`；`plan.md:17`「⑤W3 工作項補列儀器新欄位」、`:174–175`「R3→…、W3 已補列」均置於「rev 5 對應動作」。
- 輔助核對（planner session 編輯紀錄）：rev 5 之實際編輯為（a）三段替換（CORE-1／R21／§5）＋header；（b）§4-3 註記＋§6 標題；（c）§6.4 補記——**未含 W3**；W3 之欄位清單至少自 rev 3 週期內容修訂（21:54 前）即存在。
- 判定：該宣稱僅在「W3 早已列出 rev 3 追加欄位」之讀法下勉強成立，但（i）它並非 rev 5 動作、（ii）R3 要求的 `metric_version` 仍未列於 W3、（iii）置於動作清單將使讀者認定 R3 已處理。與 attempt-03 判 rev 4 阻斷之「宣稱已收斂而事實未收斂」屬同一軸，程度較輕（純文字修訂層）。
- 最小修正（二選一，建議一）：①W3 補列 `metric_version`（保留現有欄位清單）；②改寫 `:17`／`:174–175` 為如實描述（如「W3 已列 rev 3 追加欄位；`metric_version` 見 §6.2-3 與儀器輸出」）。順帶修 §6.4 `:173` 之「三處」措辭。

## 9. 發現清單

| # | 發現 | 嚴重度 | 要求 |
|---|---|---|---|
| F-C | plan §2 R20（:86）以 `exact` 計數（4／46）敘述為「落在段落起點」，與本檔 §1（:61）／§6.1 及實測（10／58）矛盾；對 27B 之「任意秒數」敘述不成立 | 中（文字與量尺／事實不符；恐誤導後續波；不影響本波閘門） | **rev 6 必做（一行）**：改用 `on_start` 計數並分述 MoE／27B 缺口 |
| F-D | rev 5 自稱「W3 已補列（儀器新欄位）」（:17、:174–175），但 R3 所指交付物 `metric_version` 未列於 W3（:94–95），且 W3 於 rev 5 並未變動 | 中（修訂紀錄如實性；R1 同軸） | **rev 6 必做（一行）**：W3 補列 `metric_version`，或改寫宣稱為如實描述；順修 :173 措辭 |
| F-A | B2 `attempt.json:70–74`／`run_notes.md:14–16`／研究 §10.7（:870–871）之 timing 錯標（「80 s 抽取」不存在；360 s 實為 extraction；299 s 窗含 12 次語意校正；「9 個 chunk」不實；A1「整併 306 s」同族） | 低（交付物標籤；plan 未重複） | 更正產物標籤；**不需 rev 6**。研究文件（本波交付物 W6）就地更正；e2e 檔依 append-only 原則以 errata 補註（不就地改寫既有證據） |
| F-B | B1 `run_notes.md:20–24` 對照表跨量尺（P1／A1 兩列實為 `exact_tag_ratio`） | 低（同上） | 更正欄名或加註量尺；**不需 rev 6** |
| F-E | §6.4 :173「§1 CORE-1／§5 的三處」措辭易誤讀（三處＝§1、§2、§5） | 極低 | 併 F-D 順修 |

## 10. 閘門結論

**PLAN_REVISION_REQUIRED**（bounded、純文字；阻斷項＝F-C、F-D；**不阻斷產品碼**）

- 依據：R1 **主體真收斂**（三處文字已改、與 `kept_far` 實作一致，且主動自承 rev 4 曾宣稱不實——如實性通過）；R2／R4／R5 已收斂；R3① 已收斂；未發現放寬標準；B2 閘門值與 `record_quality.json` 逐欄一致；`mode="cloud"` 不變性由測試釘住；plan 未宣稱 B2 覆蓋率或 Gemini 對照已完成；本輪實跑 pytest 22 passed。
- 但仍存在兩項**文字層事實／紀錄缺陷**：F-C（量尺誤標致 plan 自我矛盾、且對 27B 之根因敘述不成立）與 F-D（對 R3 之「已補列」宣稱不實）。兩者皆落在「核准必須綁定唯一且如實之修訂」之準則內——與 attempt-03 判 R1 為阻斷之準則一致——故須以最小文字修訂收斂後複審（attempt-05 僅需複核此二行）。
- 狀態語意：本結論**不阻斷產品碼**（產品實作、22 passed、B2 產物、雲端不變性本輪未發現新缺陷）；亦不阻擋 Stage 05 獨立驗收之進行（本結論僅涉及 `plan.md` 文字）。
- **補充證據之 rev 6 判定**：B2 timing 錯標與 B1 跨量尺錯標**不需要 rev 6**——屬**產物標籤更正即可、不阻斷計畫修訂**（plan 未重複；更正對象為研究文件與 e2e 註記）。研究文件 §10.7 為本波交付物（W6），其錯誤段落應在本波內更正，但不構成 plan 修訂理由。
- 建議 rev 6 最小內容：①§2 R20 一行（F-C）；②W3 一行或宣稱改寫＋§6.4 :173 措辭（F-D）；可選③§6.4 增一句記載「產物標籤更正（B2 timing／B1 量表）已處理」以備追溯。

## 11. 附錄：受審快照與收尾量測

- 開審量測：`3c0474a96a04fd889e2edbfe5b79cf53e23f641d511491f94efed8a20effeaf3`（plan.md 176 行、15,574 bytes、mtime 2026-09-22 22:27:30；本 attempt 開始後量測）。
- 收審複量：同值（本檔寫入後複量；審查期間 `plan.md` 未被修改）。
- `git status --short`／HEAD 與開審時相同：`3fec08f`、無新 commit、無 push。
- 本審查未修改任何其他檔案；`review/attempt-04/` 僅含本檔（`review.md`）。
