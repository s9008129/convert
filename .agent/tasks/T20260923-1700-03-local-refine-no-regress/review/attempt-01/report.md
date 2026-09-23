# review/attempt-01 — 獨立 Plan Review（Stage 02，fresh context）

- 受審對象：`.agent/tasks/T20260923-1700-03-local-refine-no-regress/plan.md` **PLAN_REVISION 1**
- 審查模式：唯讀（未修改任何 repo 檔）；審查者為獨立 context 的 agent，未參與規劃。
- 審查方法：先自權威來源重建 Goal Baseline，再 Top-down（目標對齊／必要性／關鍵路徑／
  比例性／失敗圍堵／耦合／設計經濟）＋ Bottom-up（逐個 `檔案:行號` 實查）。

## 閘門結論

`PLAN_REVISION_REQUIRED`

理由：F1 是**未揭露的既有模式語意變更**（守衛在 `observe` 下也會改變交付版本，而
`LOCAL_LLM_RECORD_COVERAGE_MODE=observe` 的既有契約是「只記錄、品質零變化」），必須先修計畫文字
並補文件同步清單；F2–F6 為同批可一併修訂的小項；其餘 R 項證據與機制本身已站得住。

## Goal Baseline（審查者重建）

- 主目標：地端 LM Studio（`qwen3.8-27b-splash`、`gemma-4-31B-it-MLX-4bit`）會議紀錄品質
  「接近雲端 Gemini」；機制須模型無關、macOS＋Windows（含 Ollama）共用。
- 硬約束：不動任何既有閘門門檻；不動 `LOCAL_LLM_RECORD_COVERAGE_MODE=off` 語意；不改雲端提示詞；
  不改 `backend/services/task_processor.py:259`／`:262`；不做模型名分支。
- 本切片（P7-A）唯一意圖：補強輪「整份重生成」可能讓交付版本低於中途最佳版
  （實測同一任務 `15:28` 數字缺 3 → `15:35` 缺 0 → `15:42` 又缺 1），以確定性守衛保證
  「核心覆蓋率不回退」。明示非目標：本波不提升初始品質，不得推論「已達雲端」。

## Findings

- **F1（MAJOR）** 守衛在 `observe` 生效，卻未揭露這使既有「observe＝只記錄、品質零變化」
  契約失效（交付版本會變）。修法：明文改寫契約並列文件同步，或改為只在 `enforce` 生效。
- **F2（MINOR）** 「交付版本與 log／metrics 一致」在 §1 列 SUPPORTING、在 §4 列 A（CORE 區）
  ＝分類自相矛盾。修法：升為 CORE 或移出 A 區。
- **F3（MINOR）** A1.3「訊息序列與開啟時逐一字元相同」自我對照，無法證明「回本波前」。
  修法：改用 pre-wave stub 對照（沿用 `tests/test_t20260923_p4a_record_coverage.py` 的手法）。
- **F4（MINOR）** A2 可操作性不足：`--quality-mode observe` 只控 runner 品質儀器，與產品管線
  `LOCAL_LLM_RECORD_COVERAGE_MODE` 無關；該場若為 `off` 或期望集合為 0，守衛不會產生 log，
  「必須找到 log」會非機制性失敗。修法：登錄後端實際模式、釘死 log 前綴、註明 runner 不選模型、
  並補一條 0 模型成本的離線重播。
- **F5（MINOR）** 比較基準是四類未涵蓋數的**總和**，等量互換（補回一項、掉另一項）不會被擋
  ——正是痛點同型事件（決議類）。修法：改比未涵蓋**項目集合**（不得動 `cov_*` 格式）。
- **F6（MINOR）** §3.2-4「最多多花 1 輪」方向相反：回退後問題集合回到驅動該輪的集合 ⇒
  下一輪頂端必命中不收斂保護而停止（實際是不多花、可能少一輪且不震盪）。
- **F7（NIT）** 行號引用漂移（§3.1 迴圈範圍、§2「3330 起」、`run_owned_e2e.py:750-767`）。
- **F8（NIT）** §7 以 repo 外 `/tmp/p7-gap-analysis.md` 支撐延後項，不持久／不可查核。
- **F9（NIT）** A1.1「3 輪序列」與 `LOCAL_LLM_MAX_REFINEMENT_ROUNDS=2` 不一致。
- **F10（MINOR，流程）** 計畫 rev 1 尚在審查，工作樹已出現未提交實作，不符 Stage 03/04 界線。

## 風險項逐項核對（CONFIRMED／FALSIFIED）

| 項 | 結論 | 證據 |
| --- | --- | --- |
| R-A：`observe` 仍寫入 `_record_coverage_stats` | CONFIRMED | `_validate_record_source_coverage()`：`off` 先清空後 `return []`；`observe` 照算，僅回傳值不同 |
| R-B：`off` 使守衛完全不作用、byte 級回本波前 | CONFIRMED | 同上；統計每次呼叫整份覆寫，無殘值路徑 |
| R-C：雲端路徑與共用訊息 builder 不受影響 | CONFIRMED | 雲端迴圈只跑品質／出處／年份三檢查；diff 未動 `_build_record_refinement_message()`／`_resolve_final_refinement_message()` |
| R-D：既有呼叫次數斷言會被破壞 | FALSIFIED（未破壞） | `tests/test_t20260922_2037_p3_parity.py`、`tests/test_t20260922_record_quality.py` 的案例期望集合為 0 或逐輪輸出恆定 ⇒ 不回退 |
| R-E：與不收斂保護的交互會卡死 | CONFIRMED（不卡死；敘述需更正） | 回退後問題集合＝該輪驅動集合 ⇒ 下輪頂端立即 break；措辭見 F6 |
| R-F：以覆蓋率為唯一基準是否會出現反向交易 | 部分同意 | 單一基準是最小正確設計；但「等量互換不擋」（F5）與「忽略忠實度」須明文登記為已知邊界 |
| R-G：不新增 metric 選擇器（YAGNI）是否合理 | CONFIRMED | 觀測以 log 行即可滿足；要求把 log 字串釘為契約（F4） |
| R-H：驗收是否可被偽造 | 部分可操作 | 「本次未觸發」的如實登記正確；A1.3／A2 條件需修（F3／F4） |
| R-I：Windows／Ollama 適用性 | CONFIRMED（靜態） | 只讀 `settings`／既有統計／`logging`，無 OS／引擎分支；實機仍 `[UNVERIFIED]` |

## 審查者未驗證項

- `[UNVERIFIED]` Windows 11＋Ollama 實機行為。
- `[UNVERIFIED]` 基線測試數（審查者未執行測試）。
- `[UNVERIFIED]` A2「16/16」在 `--quality-mode observe` 下的 required 計數逐項比對。
- `[UNVERIFIED]` gemma 該場 `LOCAL_LLM_RECORD_COVERAGE_MODE` 的實際生效值（有 `cov_*` ⇒ 非 `off`）。
- `[UNVERIFIED]` 審查期間工作樹實作仍在變動，後續 diff 是否與 rev 1 一致未再核（見 F10）。

## 後續

rev 2 已依 F1–F10 逐項處置（對照表見 `plan.md` §9），並補 `handoff.md` 後重新送獨立審查
（`review/attempt-02/`）。本檔為 append-only 證據，不得就地修改。
