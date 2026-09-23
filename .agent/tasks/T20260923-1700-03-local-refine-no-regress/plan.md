# T20260923-1700-03-local-refine-no-regress — PLAN（P7-A：地端補強輪「不回退」守衛）

- TASK_ID: `T20260923-1700-03-local-refine-no-regress`
- PLAN_REVISION: 2
  - rev 1＝P7-A 開場：以「補強輪整份重生成造成事實回退」的實測證據定出唯一 CORE。
  - rev 2＝依獨立 Plan Review（`review/attempt-01/report.md`，閘門 `PLAN_REVISION_REQUIRED`）修訂：
    ①**F1（MAJOR）** 明文揭露 `observe` 的契約修訂——逐條對帳在 `observe` 下仍不產生補強問題
    （問題清單零變化），但**交付版本會受不回退守衛影響**；`config.py` 描述／手冊／CHANGELOG 同步。
    ②**F2** 把「交付版本與 log／metrics 一致」升為 CORE-4（原列 SUPPORTING-4，分類矛盾）。
    ③**F3** A1.3 改為可證的等價命題（旗標 false ≡ 沒有守衛的程式碼路徑，pre-wave stub 對照）。
    ④**F4** A2 釘死前置條件（後端實際 `LOCAL_LLM_RECORD_COVERAGE_MODE`、守衛 log 字串前綴、
    模型需先載入）＋新增 0 模型成本的離線重播為必要證據。
    ⑤**F5** 新增第二條判定「等量互換」＝把未涵蓋**項目身分集合**納入比較（原設計只比計數會漏掉
    痛點同型事件「補回一項、掉另一項」），並把 `missing_items_<類別>` 列為 additive 內部鍵。
    ⑥**F6** 更正交互敘述：回退後問題集合回到驅動該輪的集合 ⇒ 下一輪頂端即命中不收斂保護而停止
    （**不多花輪**，也不震盪）。
    ⑦**F7** 行號引用全面校正為「函式名＋關鍵字」為主。
    ⑧**F8** 研究檔 `p7-gap-analysis.md` 移入本任務 `research/`（不再依賴 repo 外 `/tmp`）。
    ⑨**F9** A1.1 改稱「三版序列」以免與 `LOCAL_LLM_MAX_REFINEMENT_ROUNDS=2` 混淆。
    ⑩**F10（流程）** 如實登記：rev 1 審查期間工作樹已有實作（不符 Stage 03/04 界線）；
    rev 2 起補上 `handoff.md` 並以 rev 2 重新送獨立審查，實作改動僅限本 rev 2 新增的判定與測試。
- TASK_CLASS: **STANDARD**（地端補強迴圈的回退／交付語意變更；非架構、非資料、非安全邊界）
- REVIEW_REQUIRED: **YES**（語意變更＝規劃變更；需獨立 Plan Review）
- INDEPENDENT_ACCEPTANCE_REQUIRED: **YES**（新交付語意）
- E2E_REQUIRED: **YES**（使用者明示：同一支音檔＋`section_meeting` 版型實跑）
- 前置任務：`T20260922-2037-02-local-model-quality-parity`（P4／P6-A 已落地；本任務即該計畫 §9.9
  「**『保留最佳版本』（補強取最後一版 vs 最好一版）：屬語意變更，另開任務**」所指的那個任務）

---

## 1. 目標契約（白話）

**現況痛點**：地端補強輪是「整份重生成」。實測（同一支音檔、同一模板、同一顆 gemma-4-31B-it-MLX-4bit）
同一場的三次對帳顯示：`15:28 數字缺 15／600／100` → `15:35 缺 0 項` → `15:42 又缺 600`。
也就是**第 1 輪補回的事實，第 2 輪被寫掉**；決議類同場亦「補回一項、掉另一項」。
⇒ 交付出去的是**最後一版**，不是**最好一版**；補強輪因此可能讓紀錄**變差**。

**目標結果**：地端交付的紀錄，其**核心覆蓋率不得低於本次執行中曾達到的最佳值**。
補強輪只能讓覆蓋率持平或更好；一旦某輪把覆蓋率弄差，該輪輸出不採用，改交付最佳版本。

**CORE（不做＝任務失敗）**
1. 新增 `LOCAL_LLM_REFINEMENT_NO_REGRESSION`（bool，預設 `True`）：地端補強「不回退」守衛。
   - `True`：交付本次執行中**核心覆蓋率最佳**的那一版（同分取最後一版）。
   - `False`：一行回本波前（交付最後一版，行為與 `ab03682` byte 級相同）。
2. 守衛的比較基準**只有核心覆蓋率**（`cov_expected_*`／`cov_missing_*` 四類），且僅在
   `LOCAL_LLM_RECORD_COVERAGE_MODE != off` 且期望集合非空時可比。
   - **契約修訂（F1，rev 2 明文揭露）**：逐條對帳的 `observe` 模式**問題清單**仍零變化
     （不產生補強問題），但**交付版本**在本守衛開啟時可能被換成較佳版本。
     ⇒ 手冊／CHANGELOG／`config.py` 描述必須同步寫「observe 的零變化僅指問題清單」，
       並提供 `LOCAL_LLM_REFINEMENT_NO_REGRESSION=false` 作為精確回本波前的開關。
   - `off` 模式不受影響：逐條對帳完全不跑 ⇒ 取不到快照 ⇒ 守衛不作用且無任何守衛 log。
3. 觸發時必須留下可查核證據：`log.warning`（含前後覆蓋率、輪次、採用的版本）。

4. **CORE-4**：交付版本與 log／metrics 必須一致（回退後以同一組檢查重算問題清單與 `cov_*`，
   不留下「log 說缺、實際不缺」的假象）。（rev 2 由 SUPPORTING-4 升為 CORE，見 F2。）

**SUPPORTING（失敗如實降級，不阻斷 CORE）**
5. 手冊／CHANGELOG／規劃文件同步（含 **F1 的 `observe` 契約修訂**）。

**BEST_EFFORT（本波不做，登記為後續候選）**
6. 局部編輯（patch-only 補強）取代整份重生成——見 §7。
7. 提示詞層「只能增補不得刪除」導引——見 §7（理由：會破壞
   `tests/test_t20260922_record_quality.py::test_record_prompt_tag_placement_guidance_is_local_only`
   的「地端訊息＝雲端訊息＋單一導引列」逐字元契約，且效果無 A/B 證據）。

**全域阻斷項**：僅 CORE-1（守衛）。理由：本波唯一意圖即「不讓補強使品質變差」；
其餘皆為觀察性或文件性，缺漏不影響主結果。

---

## 2. 證據（可查核）

| 事實 | 證據 |
| --- | --- |
| 補強＝整份重生成，無「已達標不得回退」保護 | `summarization.py` → `_summarize_with_local_pipeline()` 補強迴圈（`while issues and attempts < settings.LOCAL_LLM_MAX_REFINEMENT_ROUNDS`）：每輪 `_generate_with_local_engine(...)` 產出整份 summary 後直接覆蓋 `summary`（rev 1 行號引用已校正，見 F7） |
| 覆蓋率統計每輪重算且**在 `observe` 模式也照算** | `summarization.py` → `_validate_record_source_coverage()`：`off`→清空 `_record_coverage_stats` 後 `return []`；`observe`／`enforce` 皆寫入統計，僅回傳值不同（`return issues if mode == "enforce" else []`）、`_record_coverage_metrics_fields()` |
| 真實回退事件（gemma 場） | `data/cache/e2e/p6a-gemma31b-e6/backend.log:328／421／511`；手冊 §8-18 |
| 既有不收斂保護只比「問題集合是否完全相同」 | `summarization.py:3320-3330`（`previous_issue_signature`）→「換項」不會被擋 |
| 既有 E2E 閘門與 `cov_*` 解析契約 | `scripts/e2e/run_owned_e2e.py:750-767`、`tests/test_t20260923_p4a_record_coverage.py:418-455` |

`[VERIFIED]`（本計畫撰寫時逐項對檔查核）

---

## 3. 設計

### 3.1 範圍
- **只動地端路徑**：`_summarize_with_local_pipeline()` 的補強迴圈。
  雲端同型迴圈（`_summarize_with_gemini()` 內的同構 `while`）**一字不動**
  （雲端提示詞與輸出為對照基準；獨立審查 R-C 已逐項確認）。
- **不動**：任何既有門檻與 `off` 模式語意、`LOCAL_LLM_RECORD_COVERAGE_MODE` 判定、`task_processor.py:259/262`、
  雲端提示詞、`cov_*` metrics 欄位格式（新觀測走**獨立 log 行**，不進 metrics 行）。

### 3.2 機制
1. 迴圈前：`best_summary = summary`、`best_missing = 本次核心未涵蓋數`、`best_expected = 核心期望數`。
2. 每輪補強後（既有的重算區塊之後）：讀 `_record_coverage_stats` 取核心快照
   `(未涵蓋數, 期望數, 未涵蓋項目身分集合)`（`_core_coverage_snapshot()`）。
   - 若 `expected` 與基準不同（不可比）→ 不比較，`log.info` 一次並停用守衛比較（避免錯誤回退）。
   - 判定由純函式 `_refinement_regression_reason(best, candidate)` 給出，兩條：
     **①未涵蓋數變多**；**②未涵蓋數相同但換項**（原本已寫到的事實被寫掉＝痛點同型，F5）。
     刻意不採「掉了就回退」的嚴格版（會為保住 1 項放棄同輪淨修好的多項）→ §5 已知邊界。
   - 判為回退 → **本輪輸出不採用**：`summary = best_summary`、
     以同一組檢查重算 `issues`（同時刷新 `cov_*`）、`log.warning` 記錄前後數字與採用的版本。
   - 其餘（持平／更好）→ 更新最佳版本。
3. 交付＝`summary`（＝最佳版本）。
4. 與既有不收斂保護的交互：回退後問題集合回到上一輪的集合 ⇒ 既有的 `previous_issue_signature`
   保護會在下一次迴圈頂端命中並停止再補強（＝**不多花輪**、且不會震盪；rev 2 依 F6 更正敘述）。
   **這是已知且可接受的界線**，寫入 §5 驗收觀測。
   ※可觀察副作用：回退輪會多一次 `_validate_summary_quality` 呼叫（每輪最多 +1，F4／R-D）。
5. 可觀測性：
   - `log.info("地端補強不回退守衛：核心未涵蓋 {} → {}（輪 {}）")` 每輪一次；
   - 觸發時 `log.warning`（含 `expected`／前後 `missing`／採用輪次）。

### 3.3 為何不採「提示詞導引」與「局部編輯」
- 提示詞導引：屬機率性，且破壞既有逐字元契約測試（§1 BEST_EFFORT-7）；先以**確定性**守衛取得保證。
- 局部編輯：需要模型輸出可套用的 patch，地端小模型對 patch 格式的遵循度未驗；風險／成本顯著高於本波目標，
  列後續候選（P7-B）。

### 3.4 設計經濟性（刻意不做的事）
- **不**新增 `LOCAL_LLM_REFINEMENT_ROLLBACK_METRIC` 這類「只有一個合法值」的選擇器（YAGNI）；
  比較基準寫死為核心覆蓋率，寫進 docstring 與本計畫。
- **不**把守衛做成多目標（忠實度／長度／待辦一起比）：會出現「用捏造換事實」的反向交易，
  且稀釋「不得回退」的單一保證；其餘維度仍由既有補強迴圈負責。

---

## 4. 驗收

> **EVIDENCE_ROLE／CLOSURE_GATE**：下列 A1／A2 為 `CORE`；B 群為 `SUPPORTING`；
> 全部 `CLOSURE_GATE=REQUIRED`（無 waiver）。`GOAL_CRITICALITY`：A1／A2＝CORE。

### A. CORE
- **A1（單元／離線，確定性）** `tests/test_t20260923_p7a_refine_no_regression.py`（新檔）
  1. 觸發回退：**三版序列** `missing 2 → 1 → 3`（初稿＋2 輪補強，F9）⇒ 交付第二版（missing 1），
     `log.warning` 存在。
  2. 無回退需求：`2 → 1 → 0` ⇒ 交付最後一版（不得誤回退）。
  3. `LOCAL_LLM_REFINEMENT_NO_REGRESSION=False` ⇒ 交付最後一版、**無任何守衛 log**，
     且交付內容／生成訊息序列／log（wall-clock 除外）與**沒有守衛的程式碼路徑**逐字相同
     （F3：以 `_core_coverage_snapshot()` 永遠回 `None` 的 pre-wave stub 對照，不是自我對照）。
  4. `LOCAL_LLM_RECORD_COVERAGE_MODE=off` ⇒ 守衛不作用（`cov_*` 為空、交付最後一版）。
  5. 回退後 `issues`／`cov_*` 與交付版本一致（不得 log 與實際不符）。
  6. 期望集合不一致（不可比）⇒ 不回退，只 `log.info`。
  7. 同分 ⇒ 取最後一版（不得為同分而回退）。
  8. **等量互換**（`missing 1 → 1` 但項目身分由 A 換成 B）⇒ 判為回退（F5；只比計數會漏掉）。
  9. 執行中快照消失（防禦路徑）⇒ 停用比較、交付最後一版、如實 log。
  10. 真實 `_validate_record_source_coverage()`：`observe` 供快照、`off` 不供快照。
- **A2（真實 E2E，`E2E_REQUIRED=YES`）** runner：同一音檔 `0903-科務會議.m4a`、`--template section_meeting`、
  `--quality-mode observe`、模型 `gemma-4-31b-it-mlx`（實測出回退事件的那顆）。
  - 前置條件（F4）：runner **不選模型** ⇒ 必須先在 LM Studio 載入 `gemma-4-31b-it-mlx`
    且恰為唯一已載入 LLM；`--quality-mode observe` 只控 runner 的品質儀器，
    與產品管線的 `LOCAL_LLM_RECORD_COVERAGE_MODE` **無關** ⇒ 必須登記後端**實際**生效模式
    （判準：`backend.log` 是否出現 `cov_*` metrics 欄位／`紀錄覆蓋率比對` log）。
  - 必須 PASS 16/16（既有 required 閘門不得破）。
  - 必須在 `backend.log` 找到守衛的 `log.info`，字串前綴釘死為 **`地端補強不回退守衛：`**
    （證明機制在真實路徑上活著）；觸發回退時另需 `地端補強第 N 輪造成事實回退` 的 `log.warning`。
  - 若該場後端模式為 `off` 或期望集合為 0 ⇒ 守衛**結構上不可能**產生 log：
    此時不得記為 FAIL，而應如實寫「本場不具備觸發條件」並說明判準。
  - 若本次具備條件但未觸發回退，**必須如實寫「本次未觸發」**，不得宣稱已證明回退被修好。
  - 產物 `.md`／`.docx` 與 coverage 觀察值一併登錄。
- **A0（0 模型成本，必要證據；F4）** 離線重播：以**真實**逐字稿
  （`data/cache/e2e/p6a-gemma31b-e6/transcript.txt`）＋**真實**萃取筆記＋gemma E6 場
  **真實交付紀錄**與其「把 600 元寫回」的變體，呼叫產品路徑同一份
  `_validate_record_source_coverage()` 與 `_refinement_regression_reason()`，證明
  「未涵蓋 26 → 27（期望同為 46）⇒ 判為回退」。腳本與輸出登錄於 `e2e/`（不得只留 `/tmp`）。

### B. SUPPORTING
- B1 `uv run --frozen python -m pytest tests/ -q --ignore=tests/test_end_to_end.py` 全綠（既有 1088 passed／2 skipped 不得退）。
- B2 `bash scripts/check_docs.sh` 不得新增 error。
- B3 文件：CHANGELOG／手冊（新增判讀段落）／規劃文件 P7-A 實證回饋。

### C. 反例（不得發生）
- C1 守衛不得改變 `enforce` 模式的**問題清單語意**（只改「交付哪一版」）。
- C2 守衛不得寫入 `cov_*` metrics 行（解析契約不變）。
- C3 雲端路徑輸出不得有任何 byte 級變化。

---

## 5. 回退、風險與如實邊界

- **一行回退**：`LOCAL_LLM_REFINEMENT_NO_REGRESSION=false`（行為＝`ab03682`）。
- **風險 1（已量化、可接受）**：回退會放棄該輪的其他改善（例如忠實度修正）。
  理由：本波目標是「事實不得因補強而變少」；忠實度仍由後續輪次與既有絆索負責。
  若獨立審查認為不可接受，替代案＝「回退後把被放棄的輪次問題併入下一輪問題清單」（需再 1 輪算力）。
- **風險 2**：`expected` 集合在同一場內應為常數但不保證（筆記／逐字稿在同場不變）；
  已以「不一致即不比」處理，最壞情況＝守衛不作用（不誤傷）。
- **已知邊界 3（F5）**：回退判定以「未涵蓋計數」與「未涵蓋身分集合」為準；**掉了多項但淨改善**
  （例如 3 項→1 項、其中 1 項是新掉的）**不判為回退**——這是刻意的取捨（保住淨改善）。
  更嚴格的「掉任何一項即回退」列後續候選，需先有 A/B 證明不會讓補強整體失去價值。
- **已知邊界 4（F5／R-F）**：守衛的排序只認覆蓋率，**不認忠實度**；若某輪靠捏造換取覆蓋率提升，
  守衛會採用該輪（P4-B 忠實度絆索是唯一緩解）。本波不變更此取捨，列為殘餘風險。
- **已知邊界 5（F6）**：回退後即命中不收斂保護而停止再補強（不多花輪、也不震盪）；
  代價是「回退後不再嘗試其他修法」。若改為「回退後續跑」需另外規劃。
- **已知邊界 6（F1）**：`observe` 的「品質零變化」自本波起精確表述為「**問題清單**零變化」；
  交付版本仍受本守衛影響。此修訂必須同步 `config.py` 描述、手冊與 CHANGELOG（B3）。
- **已知邊界 7（F4／R-D）**：回退輪會多一次 `_validate_summary_quality()` 呼叫（每輪最多 +1）；
  既有呼叫次數斷言不受影響（已全套實跑驗證）。
- **如實邊界**：單場 E2E 為單次抽樣（temperature≠0）；「品質已達雲端」**不得**由此推論。
  三場逐字稿 md5 不同（語意校正層仍走本地 LLM）⇒ 跨場比較含抽樣雜訊。
- **Windows／Ollama**：本機制為純 Python 條件式＋既有 `cov_*` 統計，**引擎無關、平台無關**；
  但 Windows 實機 `[UNVERIFIED]`（本機 macOS）。

---

## 6. 跨 OS／跨引擎要求
- 只用既有 `settings`、既有 `cov_*` 統計與 `logging`；不得使用 POSIX-only API、不得讀 LM Studio 專屬欄位。
- 新增設定一律走 `backend/core/config.py`（同一份 config 供 macOS／Windows／Ollama 讀取）。

## 7. 本波不做
- 局部編輯（patch-only 補強）／提示詞「只能增補」導引／多目標守衛／雲端補強語意／
  萃取提示詞「討論型事實必收」（另一包，見本任務 `research/p7-gap-analysis.md` §3-P7-2
  ＝F8 移入 repo 的持久副本，並見 `doc/規格與設計/地端會議紀錄品質對齊雲端-研究與優化規劃.md`
  §12.2，需 2 場 A/B）／逐條化與 `（待確認）` 收斂（`research/p7-gap-analysis.md` §3-P7-3）／
  詞表擴充（同檔 §3-P7-4）。

## 8. 關鍵路徑
`config 開關` → `迴圈守衛＋最佳版本交付` → `新單元測試` → `既有測試全綠` → `commit` →
`E2E（gemma31B／section_meeting／observe）` → `證據登錄 commit` → `push`。

## 9. 審查處置對照（rev 2；來源 `review/attempt-01/report.md`）

| # | 嚴重度 | 處置 | 落點 |
| --- | --- | --- | --- |
| F1 | MAJOR | 修訂計畫明文揭露 `observe` 契約（問題清單零變化、交付版本可變）＋文件同步列 B3 | §1 CORE-2、§5 邊界 6、§4 B3 |
| F2 | MINOR | 「交付版本與 log／metrics 一致」升為 CORE-4 | §1 CORE-4、§4 A1.5 |
| F3 | MINOR | A1.3 改為 pre-wave stub 等價命題（可證） | §4 A1.3、測試 `T12` |
| F4 | MINOR | A2 釘死前置條件與 log 前綴；新增 A0 離線重播為必要證據 | §4 A0／A2 |
| F5 | MINOR | 新增「等量互換」判定＋`missing_items_<類別>` additive 鍵；已知邊界 3／4 | §3.2、§5、測試 `T11` |
| F6 | MINOR | 更正交互敘述（回退即停止、不多花輪） | §3.2-4、§5 邊界 5 |
| F7 | NIT | 行號引用改為函式名＋關鍵字（並保留校正後行號） | §2、§3.1 |
| F8 | NIT | 研究檔移入 `research/p7-gap-analysis.md` | §7 |
| F9 | NIT | A1.1 改稱「三版序列」 | §4 A1.1 |
| F10 | MINOR（流程） | 如實登記 rev 1 審查期間已有實作；rev 2 補 `handoff.md` 並重新送獨立審查 | 本檔 rev 2 紀錄、`handoff.md` |

**獨立審查已確認站得住的項（不因修訂而改變）**：R-A／R-B／R-C／R-E／R-G／R-I 皆 CONFIRMED；
R-D 為 FALSIFIED（未破壞既有測試斷言）；R-F 部分同意（取捨已於 §5 邊界 4 明文登記）。
