# review/attempt-02 — 獨立 Plan Review（Stage 02，fresh context）

- 受審對象：`.agent/tasks/T20260923-1700-03-local-refine-no-regress/plan.md` **PLAN_REVISION 2**
- 計畫 sha256（本審查者自行重算）：`a8b2a4881f8701f17148c358b0bd4a04c20ffb5e7452ded41a8c453ffe7f5ba0`
  ⇒ 前 16 碼 `a8b2a4881f8701f1`，與計畫／`handoff.md` 宣稱一致。
- 受審程式基線：`3e9311a`（實作 commit）；HEAD＝`b2f11ca`；分支 `fix/qwen-local-quality-parity`。
- 審查模式：**唯讀**（未修改任何產品程式、測試、`plan.md`、`handoff.md`；本目錄外的檔案一律未寫）。
  本審查者未參與規劃與實作，為獨立 context。
- 本輪實跑（非耗時、未觸模型、未碰進行中的 E2E）：
  - `uv run --frozen python -m pytest tests/test_t20260923_p7a_refine_no_regression.py -q` ⇒ **12 passed**
  - 同指令加 `tests/test_t20260923_p4a_record_coverage.py`＋`p4a_paren_fix`＋`p4a_number_boundary_fix`
    ＋`p4a_false_positive_fix` ⇒ **54 passed**
  - `tests/test_t20260922_2037_p3_parity.py`＋`tests/test_t20260922_record_quality.py` ⇒ **44 passed**（含呼叫次數斷言，R-D 面）
  - 離線重播 **由審查者自行重跑**（`e2e/attempt-P7A-offline-replay/replay_guard.py`）⇒ 重現
    `26/46 → 27/46`、`guard_would_revert=true`、`reason=未涵蓋數變多`（詳見 F4／N-08）
  - 追加行為探針（`/tmp` 暫存腳本，未寫 repo）：`LOCAL_LLM_MAX_REFINEMENT_ROUNDS=3` 下
    「回退後下一輪頂端即 break」；「期望集合變動後守衛永久停用、交付最後一版」（詳見 N-04／N-03）

---

## 1. Goal Baseline（審查者自權威來源重建）

- 主目標：Mac＋LM Studio 地端模型（`qwen3.8-27b-splash`、`gemma-4-31B-it-MLX-4bit`）的會議紀錄品質
  「接近雲端 Gemini」；機制必須**模型無關、平台無關**（macOS／LM Studio 與 Windows＋Ollama 共用同一條地端路徑）。
- 硬約束：不動任何既有閘門門檻；不動 `LOCAL_LLM_RECORD_COVERAGE_MODE=off` 語意；不改雲端提示詞；
  不改 `backend/services/task_processor.py:259/262`；不得做模型名分支。
- 本切片（P7-A）唯一意圖：補強輪＝**整份紀錄重生成**，實測同一任務同一模型數字類未涵蓋數 `3 → 0 → 又 1`
  （gemma 場）；交付的「最後一版」可能比中途某輪更差。本波以**確定性守衛**保證
  「交付版本的核心覆蓋率不得低於本次執行曾達到的最佳值」。明示非目標：不提升初始品質、不得推論「已達雲端」。
- 依此 Baseline，審查主軸＝①守衛是否真的以「最佳版本」交付且不誤傷；②是否守住 `off`／閘門／雲端／
  跨平台不變式；③「observe 契約修訂」是否被完整揭露（F1）；④驗收證據是否獨立可查核。

---

## 2. F1–F10 逐項裁決（rev 2 是否真的收斂）

> 判定基準：不看計畫自述，逐項對 `plan.md` 內文＋實作（`3e9311a`）＋實測（本輪實跑）三面查核。

| # | 裁決 | 一句話證據 |
| --- | --- | --- |
| F1 | **CONFIRMED** | 計畫 §1 CORE-2／§5 邊界 6 明文揭露；`config.py:636-646` 描述已寫契約修訂；手冊（工作樹 L13／L217）與 CHANGELOG（工作樹 L41-44）已補同句 |
| F2 | **CONFIRMED** | 「交付版本與 log／metrics 一致」已升 CORE-4（§1 CORE-4、§4 A1.5），SUPPORTING 不再重複列該項 |
| F3 | **CONFIRMED** | §4 A1.3 改為 pre-wave stub 等價命題；`tests/test_t20260923_p7a_refine_no_regression.py:340`（T12）實作、本輪 12 passed |
| F4 | **CONFIRMED** | §4 A2 釘死前置條件＋log 前綴；A0 腳本／輸出已進 repo；**審查者重跑 A0 並重現 26/46→27/46 與回退判定** |
| F5 | **CONFIRMED** | 判定②等量互換已落地（`summarization.py:3251-3253`）＋`missing_items_<類別>` additive 鍵（`:2046／:2074／:2106`）；T11 green |
| F6 | **CONFIRMED** | §3.2-4／§5 邊界 5 敘述已更正；本輪實測（MAX_ROUNDS=3）＝回退後下一輪頂端即 break、總生成 4 次、交付「版本二」 |
| F7 | **CONFIRMED（殘留 1 個 NIT）** | 全面改「函式名＋關鍵字」；但 §2 保留的 `summarization.py:3320-3330` 仍是**本波前**行號（現為 `:3396-3419`，見 N-09） |
| F8 | **CONFIRMED** | `research/p7-gap-analysis.md` 已入 repo（18,577 bytes，隨 `3e9311a` 提交），不再依賴 `/tmp` |
| F9 | **CONFIRMED** | §4 A1.1 已改稱「三版序列（初稿＋2 輪補強）」 |
| F10 | **CONFIRMED（流程違序已如實登記）** | 計畫 §9 F10 列＋`handoff.md` 已補（指紋 `a8b2a4881f8701f1` 正確）；rev 1 審查期間已有實作、且實作與 rev 2 計畫同 commit 的界線問題已明文登記，非隱匿 |

### F 項細部證據

- **F1**：契約修訂句「observe 的問題清單零變化、但交付版本可被守衛換掉」見 `plan.md` §1 CORE-2；程式側
  `backend/core/config.py:636-646`（欄位＋description 同句）為**已提交**；`doc/操作手冊/…v4.10.md`
  工作樹 L13／L217、`CHANGELOG.md` 工作樹 L41-44（「📜 契約修訂（重要）」）為**未提交但已寫**（見 N-09）。
  另提供 `LOCAL_LLM_REFINEMENT_NO_REGRESSION=false` 精確回本波前。**無未揭露的語意變更殘留。**
- **F2**：`plan.md` §1 CORE-4 與 §4 A1.5 一致；SUPPORTING 清單已從 4 起算（CORE-4 升格）。實作面
  `summarization.py:3484-3487` 回退後以同一組檢查重算 `issues`（連帶刷新 `_record_coverage_stats`／
  `cov_*`），T07（回退後 `cov_missing_topic=1` 且殘餘問題屬交付版本）本輪 green。
- **F3**：T12 以 `no_regression=False` vs `prewave_stub=True`（`_core_coverage_snapshot → None`）比對
  「交付內容／生成訊息序列／log（wall-clock 除外）」逐字相同。此為**等效實作對照**（stub 讓守衛失效），
  非歷史版本 binary 對照；此侷限已由 p4a `test_T15b`（`tests/test_t20260923_p4a_record_coverage.py:395`，
  真實 pipeline、off vs pre-wave stub，逐字比對 log）補強，本輪亦 green。
- **F4**：`plan.md` §4 A2 已釘死：runner 不選模型／須先載入 `gemma-4-31b-it-mlx`／`--quality-mode observe`
  與產品 `LOCAL_LLM_RECORD_COVERAGE_MODE` 無關／log 前綴 `地端補強不回退守衛：`（與
  `summarization.py:3458／3466／3490` 實際字串一致）／不具備觸發條件時如實登記不得記 FAIL。
  A0：`e2e/attempt-P7A-offline-replay/replay_guard.py`＋`output.json` 已進 repo；**審查者獨立重跑**，
  得到相同判定（26/46→27/46、回退原因「未涵蓋數變多」）。
- **F5**：等量互換語意＝「未涵蓋數相同且 `candidate.identities - best.identities` 非空 ⇒ 回退」；
  身分字串為 `類別:項目`（`:3226-3228`），項目字串取自期望集合本身（跨輪穩定）。刻意不採「掉任何一項即回退」
  已列 §5 邊界 3。additive 鍵不進 metrics（見 N-01）。
- **F6**：`plan.md` §3.2-4 與 §5 邊界 5 已改為「回退後命中不收斂保護而停止（不多花輪、不震盪）」。
  實測：`LOCAL_LLM_MAX_REFINEMENT_ROUNDS=3` 且第 2 輪回退時，第 3 輪「頂端」即印
  `本地摘要補強未收斂（問題集合與上一輪相同，共 1 項）→ 停止再補強` 並 break，總生成 4 次
  （萃取 1＋初稿 1＋補強 2），交付版本＝第 1 輪的較佳版。**無超輪、無震盪。**
- **F7**：§2／§3.1 已全面改「函式名＋關鍵字」為主；唯 §2 「既有不收斂保護只比問題集合是否完全相同
  `summarization.py:3320-3330`」的數字是**本波前**座標（ab03682 為 3318-3330；現行檔案 `previous_issue_signature`
  在 `:3396／:3408／:3410／:3418`）。關鍵字錨明確，屬 NIT（N-09）。
- **F8**：`research/p7-gap-analysis.md` 已於 `3e9311a` 提交；`plan.md` §7 引用同檔。
- **F9**：§4 A1.1 措辭已與 `LOCAL_LLM_MAX_REFINEMENT_ROUNDS=2` 對齊。
- **F10**：`handoff.md` 存在、`PLAN_REVISION 2`、指紋與實測 sha256 一致；但**審查時序**仍為
  計畫審查→實作同批（`3e9311a` 同時含 plan.md／handoff.md／review attempt-01／產品碼＋測試），
  此違序已由計畫 §9 F10 明文登記，非隱匿；本審查依使用者指示就此繼續實質審查，不因程序現況放寬標準。

---

## 3. 新風險清單（含指定六題逐題結論）

### N-01（指定題）additive 鍵是否破壞 `cov_*` metrics 行格式或既有解析／測試？⇒ **SAFE**

- `_record_coverage_metrics_fields()`（`backend/services/summarization.py:2133-2154`）以**固定 9 鍵**輸出，
  `missing_items_*` 不在鍵清單內 ⇒ 永不出現在 metrics 行（C2 反例守住）。
- E2E runner 只解析含「pipeline metrics」的行（`scripts/e2e/run_owned_e2e.py:746-758`，通用 int `key=value`
  捕捉），沒有針對「未涵蓋」等字串的專用解析 ⇒ 守衛新 log 行不會被 runner 誤吃。
- 既有測試僅 `tests/test_t20260923_p4a_record_coverage.py:458-483`（T17）斷言 stats 鍵集合，已同步更新；
  其餘 p4a 測試為逐鍵斷言（本輪 54 passed 驗證）。
- 殘留（可接受）：T17 這種「精確鍵集合」斷言，未來再加 additive 鍵時需再改一次。

### N-02（指定題）期望集合中途變動、快照 `None` 的兩條停用路徑是否真的安全？⇒ **SAFE**

- 實作：`summarization.py:3454-3470`，兩條皆 `guard_comparable=False`＋`log.info`＋交付最後一版，
  之後各輪不再進比較區塊；`_refinement_regression_reason(None, …)` 亦直接回 `None`（`:3247-3248`）。
- 實測（審查者探針）：第 1 輪期望集合 10→9 ⇒ 印「基準不同不可比→停用比較」，後續輪照常生成、
  不再有任何守衛判定，最終交付最後一版。**不會錯誤回退。**
- 設計取捨（已登記）：停用後本場不再重啟比較（即使期望集合回到原值）；符合 §5 風險 2「最壞＝不作用、不誤傷」。

### N-03（指定題）`off` 是否真的是 byte 級回本波前（含「無任何守衛 log 行」）？⇒ **CONFIRMED**

- `off`：`_validate_record_source_coverage` 先 `self._record_coverage_stats = {}` 再 `return []`
  （`:1960-1963`）⇒ 快照 `None` ⇒ 守衛區塊整體被短路（`no_regression and guard_comparable` 為假），
  守衛的所有 log 都在該區塊內（`:3458／3466／3478／3490`）⇒ **一行都不會產生**。
- `no_regression=False`：連 `_core_coverage_snapshot()` 都不呼叫（`:3406` 三元短路）⇒ 無額外副作用。
- 證據：T05（off＋管線、斷言無「不回退守衛」字樣）與 p4a `test_T15b`（真實管線、off vs pre-wave stub、
  log 逐字相同）本輪皆 green；`off` 的 `cov_*` 仍為空字串（`:2152-2153`）。

### N-04（指定題）回退後是否可能震盪或超輪？⇒ **NO（已證）**

- 不變式：回退時「本輪生成前所依據的版本」就是 best ⇒ 回退重算得到的 `issues` 與
  `previous_issue_signature` 相同 ⇒ 下一輪頂端必命中不收斂保護。預設 `MAX_REFINEMENT_ROUNDS=2`
  時迴圈自然結束；=3 時實測 break（見 F6）。**不多花模型呼叫、不震盪。**
- 代價已登記：回退即放棄該輪其他修法（§5 邊界 5）。

### N-05（指定題）新測試是否真空（mock 產品函式／測副本）？⇒ **不真空，但有兩點侷限（可接受）**

- T01–T08／T11／T12 走**真的** `_summarize_with_local_pipeline()` 迴圈與真的
  `_core_coverage_snapshot()`／`_refinement_regression_reason()`；只把「覆蓋率驗證器」以腳本替身注入，
  替身寫入的是**產品真實 stats schema**（`:2046／:2074／:2106` 同構），且 quality 驗證器以「版本→問題」
  腳本化——這是必要 seam（否則無法確定性重播模型輸出），非真空測試。
- 真實 `_validate_record_source_coverage()` 由 T09（observe 供快照）／T10（off 不供快照）覆蓋；
  端到端真實素材由 A0 重播覆蓋（審查者已重跑）。
- 侷限（可選強化，非缺口）：沒有「以真實覆蓋率函式驅動之管線級回退」整合測試；T12 的「本波前」是
  等效 stub 而非歷史修訂版 binary。兩者都已由 F3 指定手法與 T15b golden 補強，**不影響本輪結論**。

### N-06（指定題）是否有模型名／平台分支？⇒ **無**

- `3e9311a` 對 `backend/` 的 diff 中，`gemma` 僅出現於註解；無 `sys.platform`／`os.name`／引擎名判斷；
  守衛只讀 `settings`、`self._record_coverage_stats`、`logging`。`LOCAL_LLM_REFINEMENT_NO_REGRESSION`
  為 `backend/core/config.py:636` 的一般欄位（同一份 config 供 macOS／Windows＋Ollama）。
  Windows 實機仍標 `[UNVERIFIED]`（如實）。

### N-07（新發現）分類語意殘留兩處模糊（非阻斷，建議下一次修訂一併收斂）

1. `plan.md` §1 CORE-2 寫「手冊／CHANGELOG／`config.py` 描述**必須**同步寫…」，但同一件事又列為
   SUPPORTING-5／§4 B3（「失敗如實降級，不阻斷 CORE」）——同一交付物同時「必須」與「可降級」。
   以保守讀法（CORE-2）檢視，工作樹已完成同步（config 已提交、手冊／CHANGELOG 已寫待提交）
   ⇒ **實質無缺口**；但文字上仍可被自我 waive（F2 同型問題的殘影）。
2. A0 放在 §4「A. CORE」區並標「必要證據」，但 §4 表頭只點名「A1／A2 為 CORE」，而 `handoff.md`
   把 A0 歸到 BEST_EFFORT。保守讀法下 A0 已交付且審查者已重現 ⇒ 無實質風險。
   - 最小修法：CORE-2 的「必須同步」改指 B3 為其落點（或把 B3 升 CORE）；A0 在 §4 明寫
     `GOAL_CRITICALITY=CORE｜CLOSURE_GATE=REQUIRED` 或改列 SUPPORTING 並同步 handoff。

### N-08（新發現）A0 證據成對性瑕疵（數字已重現；建議補一份 append-only 重跑輸出）

- `output.json` 的鍵為 `missing_items_core_count／_sample`，而**已提交腳本**（`replay_guard.py:44-56`）
  輸出的是完整 `missing_items_core` 清單 ⇒ committed output 不是由 committed script 這一版產生
  （schema 漂移；推測為輸出瘦身後的歷史版本）。審查者重跑腳本：**數字與判定完全重現**
  （26/46 → 27/46、`guard_would_revert=true`、原因「未涵蓋數變多」），故 A0 的**實質主張成立**。
- 另：腳本輸入含 `/tmp/notes_repro/qwen_e5b_chunk1_notes.txt`（現存 11,409 bytes；腳本 L6／L29 已如實註明
  為 qwen E5b 場筆記替代）——`/tmp` 清理後無法重播。
- 最小修法：在下一個 append-only 目錄提交「由 committed script 產生的完整輸出」，並把 notes fixture
  （或至少 sha256＋來源）登錄於同目錄；另刪 `replay_guard.py:63` 的死行
  （`snap_better = probe.__wrapped__ if False else None  # noqa: F841`）。

### N-09（新發現）文件殘留與時序（B3 進行中）

- 手冊（工作樹）L217 已寫契約修訂，但 L56 的 P4-A 開關表仍寫 `observe（只記錄，品質零變化）`，
  且 L55 的 `summarization.py:2131-2141／3390／2119-2120` 行號為本波前座標（現行：metrics 欄位
  `:2133-2154`、輸出點 `:3506`）。建議 B3 一併校正，避免同一份手冊自相矛盾。
- `plan.md` §2 的 `summarization.py:3320-3330`（見 F7）同屬行號殘留（NIT）。
- 工作樹目前有未提交的 `CHANGELOG.md`／手冊（`git status`：` M`），而 `b2f11ca` 已登錄
  「dirty worktree、未啟動 backend」的 fail-closed preflight ⇒ **A2 正式場須先提交 B3 文件**
  以滿足 runner 的乾淨工作樹前置，再起跑（本審查未碰進行中的 `attempt-P7A-gemma31b-e7c`）。

---

## 4. 未驗證項／不確定

- `[UNVERIFIED]` Windows 11＋Ollama 實機（本機 macOS；靜態面已驗：無平台／引擎／模型分支）。
- `[UNVERIFIED]` 全套測試「1100 passed／2 skipped」總量（本輪僅實跑 6 檔 110 項全綠；全量宣稱未獨立複核）。
- `[UNVERIFIED]` A2 正式 E2E 結果（審查時仍在跑；場次登錄尚未產生）。
- `[UNVERIFIED]` 未來若把 `LOCAL_LLM_RECORD_COVERAGE_CATEGORIES` 縮到只剩部分類別，快照語意仍成立
  （推論成立：expected>0 即供快照；未實測此組態）。
- `[INFERRED]` `output.json` 由腳本歷史版本產生（由 schema 差異推得；commit message 未載明）。

---

## 5. 閘門結論

**`PLAN_APPROVED`**

一句理由：F1–F10 全數以獨立證據收斂，守衛之目標契約、不變式（`off` byte 級、observe 契約已揭露、
雲端／閘門／無模型平台分支）與失敗圍堵（停用比較不誤傷、回退不超輪）皆經實查與實跑成立；
本輪新發現僅餘**非阻斷**的分類措辭模糊（N-07）、A0 證據成對性／`/tmp` 依賴（N-08）與文件行號與一行措辭
殘留（N-09），其保守讀法在 repo 內已實質滿足，不構成核心路徑或缺一即敗的驗收缺口，建議併入 B3
與證據登錄步驟收斂即可。

---

## 6. 校訂（append-only；本檔首次寫入後之精確化）

- 守衛 log 行的**精確**位置：`:3459`（快照消失）／`:3466`（期望集合變動）／`:3475`（回退 warning）／
  `:3491`（每輪 info）；回退後重算呼叫＝`:3486`；最佳版本更新＝`:3498-3499`。
  前文若出現 `3458／3478／3490／3484-3487` 等座標，以本段為準（差異 ≤2 行，不影響任何裁決或閘門結論）。
- 審查期間觀察到工作樹新增未追蹤目錄 `.agent/tasks/.../verification/`（非本審查者所寫；本審查者唯一寫入＝本檔）。
