# 獨立計畫審查 — T20260922-2037-02-local-model-quality-parity（Stage 02，attempt-05）

- 受審對象：`.agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md`，自稱 `PLAN_REVISION 6`（`plan.md:4`）。
- `REVIEWED_PLAN_REVISION`：**6**
- `REVIEWED_PLAN_SHA256`：**`3b89a437d01d9dccf7dd160b6a531815d649066a5f1375bbd134b3d8339943d6`**
  - 開審量測：同值；收審複量（本報告寫入後）：同值。審查期間 `plan.md` 未被任何動作修改。
  - 依本輪使用者指令，僅寫本檔（append-only），未建立 `plan_snapshot.md`；受審內容以雙次 SHA-256＋逐行引用固定。
- 審查者：獨立 Stage 02（fresh context；read-only）。未修改 `plan.md`、產品碼、既有 `review/attempt-01`～`04`、`e2e/*`、研究文件。
- 必讀已讀：`~/.codex/AGENTS.md`、`~/.codex/prompts/02_plan_review_prompt.md`、`~/.codex/policies/plan-review-gate.md`、
  `~/.codex/policies/goal-alignment-design-economy.md`；本任務 `plan.md`（rev 6）＋ `review/attempt-01`～`04`；
  `e2e/attempt-B2-27b-fix/`（`attempt.json`、`run_notes.md`、`record_quality.json`、`instrument_recheck_20260922.json`）與
  `e2e/attempt-B1-moe-fix/run_notes.md`；研究文件 `doc/規格與設計/地端會議紀錄品質對齊雲端-研究與優化規劃.md` §10（含 §10.3／§10.4／§10.5／§10.7）。
- 環境備註（與交付說明之事實差異，如實記錄）：
  1. 交付說明預期「HEAD `3fec08f`＋工作樹含未提交變更」；本審查行程早期確為此狀態。收尾複查時，本波已於 23:13:54 提交為
     **`e90040b`**（`fix/qwen-local-quality-parity`）。`plan.md` 提交前後位元組相同（hash 同值）→ 審查對象不受影響；
     此為流程事實，非計畫缺陷。
  2. 分支**無 upstream**（`git rev-parse @{u}` → `fatal: no upstream configured`）＝**未 push**。工作樹僅餘未追蹤之
     `e2e/attempt-C1-gemma31b-fix/`。
  3. `e2e/attempt-C1-gemma31b-fix/` 為**進行中**：23:15:57 health snapshot（build revision `e90040b…` 相符、
     `gemma-4-31b-it-mlx`（4bit、context 71,936）已載入、`upload_response.json` 已排隊 `task_id ac1edcec`）；
     尚無 `run_notes.md`／`record_quality.json`。此與 §7 N-1 的路由一致；**結果未知，本報告不預判、不得引用為實測結論**。

## 0. Goal Baseline（權威來源：使用者需求＋研究文件 §10＋attempt-02～04 紀錄）

1. 主目標：Mac＋LM Studio（`section_meeting`、模式 `local`）的地端會議紀錄品質「接近雲端 Gemini」；優化機制必須**與模型／平台無關**（使用者需求 4）。
2. 本波 CORE＝出處標註可查核性：時間戳落在逐字稿真實段落、吸附後落真實段首（比例表述）、修復位於確定性層（無模型名／OS 分支）。
3. 前次閘門（歷史）：attempt-04 對 rev 5 判 `PLAN_REVISION_REQUIRED`，**純文字層、不阻斷產品碼**；阻斷項 F-C（R20 計數與量尺誤植）與 F-D（W3 未列 `metric_version` 卻自稱已補列）。rev 6 必須逐字收斂。
4. rev 6 另納入使用者當晚新增需求：N-1（Gemma 4 31B 修復後 E2E）、N-2（macOS／Windows 雙平台支援驗收）；未驗證部分必須如實標示，不得放寬既有閘門。

## 1. 實際動作清單（全部實跑，含指令與輸出摘要）

| # | 指令／動作 | 輸出摘要 |
|---|---|---|
| 1 | `DATA_DIR="$PWD/data" uv run --no-sync pytest tests/test_t20260922_record_quality.py -q -p no:randomly -p no:cacheprovider` | **22 passed in 0.49s** |
| 2 | `DATA_DIR="$PWD/data" uv run --no-sync pytest tests/ -q --ignore=tests/test_end_to_end.py -p no:randomly -p no:cacheprovider` | **899 passed, 2 skipped in 9.78s**（現值；`plan.md` 內基線 881 為前波歷史值，非本輪缺陷） |
| 3 | `shasum -a 256 plan.md`（開審、收審各一次） | 同值 `3b89a437…`（見檔頭） |
| 4 | `git status --short`、`git log --oneline -3`、`git rev-parse @{u}`、`git show --stat e90040b` | 見環境備註；未 push；commit message 涵蓋量尺更正／跨平台契約／27B E2E 證據 |
| 5 | `sed` 逐字核對 `plan.md`（:4、:14–18、:44–62、:80–99、:104–110、:176–199、:217–244） | R20／W3／§4-3／§6.5／§7 原文（下節引用） |
| 6 | `sed -n '42,45p;56,58p;120,123p;127p;201p;203p;427p' data/cache/e2e/p2-27b-fix-01/backend.log` | ASR 16.73 s（:42–45）；diarization 153.7 s（:45）；:201 completion=**4,146**；:203 筆記 3,886 tokens 零損串接；:427 `chunk_count=1, merge_rounds=0, extraction=360.9, merge=0.0, final_and_refine=1043.9, total=1404.7` |
| 7 | `python3` 解析 `backend.log:56–123` | **恰 12 筆**語意校正診斷（21:21:40→21:23:24；首筆 completion 787、其餘 11 筆 222–326） |
| 8 | `python3` 讀 `e2e/attempt-B2-27b-fix/attempt.json` | 原始 `timing_breakdown` 三欄（299／80／360＋`merge_completion_tokens=4146`）**保留未改**；新增 `timing_breakdown_errata_20260922`（corrections／corrected_breakdown／evidence）與日誌一致 |
| 9 | `git diff 3fec08f..e90040b -- e2e/attempt-B1-moe-fix/run_notes.md` | 僅追加「errata」段；原表與原內文未動 |
| 10 | `python3` 讀 `instrument_recheck_20260922.json` | `metric_version=tag_traceability-1.1.0`；A1 `on_start 0.9508（58/61）`、`exact 0.7541（46/61）`；P1 `0.3704（10/27）`、`0.1481（4/27）`；B2 `1.0（52/52）`、`ex0 1.0` |
| 11 | 以現行產物逐筆重算 A1／B2 正文標籤（regex＋計數） | A1：61 筆＝發言者1×58／發言者3×2／發言者2×1；B2：52 筆＝科長×51／發言者3×1；兩場 `00:00:00` 各 7 筆 |
| 12 | `sed` 核對研究文件 §10（:798–822、:876–890）與 `backend/core/config.py:45–55` | Ollama 預設 `http://host.docker.internal:11434`（config:49–52）；六項硬前提清單；§10.7 耗時構成 errata；§10.5 0.9／0.95 註記 |

（未重跑：B1／B2 之模型 E2E 全鏈——非本輪要求且不可回溯；B1 之 errata 以 diff 與日誌引用核對。）

## 2. 逐項查核結論

### 2.1 F-C（§2 R20 計數與量尺）→ **已逐字收斂** [VERIFIED]

- `plan.md:90` R20 現文逐字：MoE（p1）`on_start 10/27 = 37.0%`、`exact 4/27`；27B（A1）`on_start 58/61 = 95.1%`、`exact 46/61`（「發言者一致的嚴格版僅 75.4%」）；影響欄改為「MoE：過半標註落在段落中間的任意秒數；27B：多數已落段首…」。
- 我以 `instrument_recheck_20260922.json` 逐值核對：P1 `0.37037（10/27）`／`0.14815（4/27）`；A1 `0.95082（58/61）`／`0.75410（46/61）`；B2 `1.0（52/52）` → **與 R20 完全一致**。原缺陷（把 `exact` 的 4／46 寫成「落在段落起點」、稱「27B 多為段落內任意秒數」）**均已消失**。
- 殘留（M3，低）：R20 同一列「標籤多用角色名（『科長』）」為 **B2（修復後）**現象（B2 52 筆＝科長×51），但證據欄數字引自 **A1（修復前）**，A1 標籤實為發言者N（發言者1×58）。建議標註場次或拆述。此為敘述精確度問題，不影響量尺（speaker-agnostic）與閘門結論。

### 2.2 F-D（W3／`metric_version`）→ **已收斂** [VERIFIED]

- `plan.md:98–99` W3 現文已含：「量測儀器新增 `tag_traceability`（**含 `metric_version`** 與 `exact_tag_ratio`；rev 3 追加…）」。
- `instrument_recheck_20260922.json` 已含 `metric_version: tag_traceability-1.1.0`；本審查行程與 rev 5 前副本逐欄比對相同（量測值未動）。
- 殘留（M2，低）：`plan.md:16`（rev 5 清單⑤「W3 工作項補列儀器新欄位」）與 `:179`（「W3 已補列」）把該動作記在 **rev 5**；實際於 **rev 6** 才補（`:191` 即 rev 6 的 F-D→W3 補列）。現行內容已為真，僅時序歸屬不精確。

### 2.3 §7 新增需求（N-1／N-2）→ **忠實、比例合理、未放寬閘門** [VERIFIED]

- N-1（`:217–226`）：忠實對應使用者原話——模型 `gemma-4-31B-it-MLX-4bit`、同一支 `0903-科務會議.m4a`、模板／模式不變、「同一組閘門」（`:220–221`）；證據目錄 `attempt-C1-gemma31b-fix/`（`:223`）；降級語意明示：下載未完成／載入失敗／引擎拒絕參數時「如實記錄為未執行／部分執行與原因，不得以推論代替實測」，降 `BEST_EFFORT` 並須明示未取得哪些數字（`:223–225`）；承載性 `[UNVERIFIED]`（`:226`）。**未宣稱已實測**。
  - 旁證（時序）：審查期間觀察到 `attempt-C1-gemma31b-fix/` 正在執行（環境備註 3），與計畫路由一致；結果未出爐。
- N-2（`:228–243`）：第 1–3 項以程式碼事實核對成立（地端後處理鏈兩平台共用並由契約測試釘住；`platform_config`：macOS→LM Studio、非 Darwin `auto`→Ollama 優先；`text_postprocess` 無 OS／模型名分支）；第 4 項標為 `[SUPPORTING]`（`:241`）；**Windows 實機行為未驗 `[UNVERIFIED]`**（`:242`）。硬前提與程式碼一致（`config.py:49–52` 預設 URL；compose 寫死 `OLLAMA_BASE_URL`／`LOCAL_LLM_MODEL`；context 預算；段落列格式）。
- 閘門與降級語意：**未偷偷放寬**——§4 第 3 點（`:108–110`）主閘門 `on_start_tag_ratio ≥ 0.95`、輔助閘 `ex0 ≥ 0.9`、`traceable_tag_ratio ≥ 0.95`、`body_source_tag_count ≥ 17`、表格標註 = 0 均未動；`exact_tag_ratio` 維持觀察值（`:59`）。`:244`「N-1 的機械閘門（若實際執行）與 N-2 第 1–3 項具全域阻斷力；N-2 第 4 項為 SUPPORTING」符合 CORE 比例原則。
- 殘留（M1，低）：§1 排除清單（`:80–82`）仍寫「Gemma 4 31B 實測（本機無模型）」為排除項；`:226` 雖有「原 §1 曾列為排除項」補註，建議在 §1 該行加註「rev 6 由 §7 N-1 取代」。

### 2.4 §6.5 產物標籤更正（B2／B1）→ **如實** [VERIFIED]

- 三項核心事實以日誌逐字驗證為真：①**抽取＝單次 360.9 s／4,146 tokens**（`:201` completion=4146；`:427` `extraction=360.9`、`chunk_count=1`）；②**`merge_rounds=0`、無整併呼叫**（`:427`；`:203` 3,886 tokens 零損串接）；③**12 次語意校正**（`:56–123` 恰 12 筆診斷；`:127` 校正完成紀錄）。
- `attempt.json`：原始欄位保留未改；errata 與日誌一致。`run_notes.md` §六（B2）與 attempt.json 一致且明言「原表不修改」；B1 `run_notes.md` 經 `git diff 3fec08f..e90040b` 證實**僅追加 errata**（原表 14/14 與內文未動）；其 v1.0 `exact` 語意說明與 `f1e6bfe` 版本查證相符。
- 殘留（M4，低）：`:196` 括註「7–9 s／222–326 tokens（12 次）」實為 11/12（首筆 787 tokens／較長）；errata 內「~80 s（加總）」與「約 127 s（窗長）」兩種數字未說明關係。建議後續 errata 精確化。

### 2.5 研究文件 §10 更正 → **正確** [VERIFIED]

- Ollama 預設 URL：已更正為 `http://host.docker.internal:11434`（`backend/core/config.py:49–52`）、Windows compose 亦同——與程式碼一致。
- 六項硬前提清單（§10 :808–818）逐項有實作依據；「示警只在離線量測（`traceable_tag_ratio`），系統不自動告警」與實作（僅 `scripts/e2e/measure_record_quality.py` 使用）一致。
- §10.7 耗時構成更正（:883 起）與日誌一致（ASR 16.7＋diarization 153.7＋校正 ~127；抽取 360.9／4,146；無整併；`merge_rounds=0`；總 1,404.7 s）；§10.5 的 0.9（前哨）vs 0.95（驗收）關係已註記。

### 2.6 有無新放寬／新不實宣稱 → **未發現** [VERIFIED]

- 全文未出現「Gemma／Ollama／Windows 已實測」之主張：N-1 承載性與結果、N-2 Windows 實機均為 `[UNVERIFIED]`；Gemma E2E 未宣稱完成。
- 未宣稱覆蓋率改善完成、未宣稱與 Gemini 對照完成；閘門值未動；觀測值／閘門區分維持。
- 環境層注意：`attempt-C1` 正在執行不得被後續文件引用為已驗證，直到 `run_notes`／`record_quality` 落地（本報告亦不引用）。

## 3. 發現清單

| # | 發現 | 嚴重度 | 要求 |
|---|---|---|---|
| M1 | §1 排除清單（`:80–82`）仍列「Gemma 4 31B 實測」為排除項，與 §7 N-1 並存 | 低（MINOR） | 建議：§1 該行加註「rev 6 由 §7 N-1 取代」 |
| M2 | `:16`／`:179` 將「W3 補列 `metric_version`」記為 rev 5 動作（實際 rev 6 才補） | 低（MINOR） | 建議：改註 rev 6（內容已為真，僅時序歸屬） |
| M3 | R20（`:90`）27B 敘述採 B2 現象（標籤用「科長」），證據欄卻引 A1（發言者N） | 低（MINOR） | 建議：標註場次（A1 vs B2）或拆分句子 |
| M4 | `:196`「7–9 s／222–326 tokens（12 次）」僅涵蓋 11/12（首筆 787 tokens）；errata「~80 s」與「約 127 s」措辭並存 | 低（MINOR） | 建議：後續 errata 精確化（可與 M1–M3 一併處理） |

（M1–M4 均為純文字精確度項，不影響量尺、閘門語意、產品行為或既有 E2E 結論。）

## 4. 閘門結論

**PLAN_APPROVED**

- 唯一閘門；核准綁定：`PLAN_REVISION 6`／`sha256 3b89a437d01d9dccf7dd160b6a531815d649066a5f1375bbd134b3d8339943d6`（開審＝收審同值）。
- F-C／F-D 兩阻斷項逐字收斂（§2.1／§2.2）；§7 新增需求忠實、比例合理且未放寬既有閘門；§6.5 與研究 §10 更正與日誌／程式碼一致；未發現新放寬或新不實宣稱。
- **阻斷判定**：不阻斷產品碼；不阻斷 Stage 05。N-1 的 Gemma E2E 正在執行中（結果未知）；N-2 為程式碼／文件層 CORE 驗收。
- M1–M4 為建議性文字精確度項，不構成本次核准之條件；**若後續任何 `plan.md` 文字被修改，本 approval 依修訂綁定規則即失效，需重新審查**。
- NEXT_ACTION：Stage 03 Handoff（綁定本 rev 6／上列 hash；handoff 應保留：①attempt-C1 進行中、結果不得預判；②B2／B1 產物以 errata 補註、原欄位不覆寫；③N-1 未執行時降 `BEST_EFFORT` 且須列未取得數字；④N-2 第 4 項為 `SUPPORTING`、Windows 實機 `[UNVERIFIED]`）。
