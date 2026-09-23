# HANDOFF — T20260923-1700-03-local-refine-no-regress（P7-A）

- 來源計畫：`plan.md`，**PLAN_REVISION 2**
- 修訂指紋：`sha256(plan.md)` 前 16 碼 = `a8b2a4881f8701f1`
  （rev 2 已依 `review/attempt-01/report.md` 的 F1–F10 修訂；實作者開工前必須重算並比對，
  不一致即**停止**，不得猜測。）
- 審查狀態：attempt-01 = `PLAN_REVISION_REQUIRED`（已處置）→ attempt-02 待審（獨立 context）。

## GOAL_ANCHOR（不得漂移）

地端補強輪是「整份紀錄重生成」；實測（gemma-4-31B-it-MLX-4bit、同一支音檔、同一模板、同一任務）
同一場三次對帳 = 數字未涵蓋 `3 → 0 → 又 1`，即**第 1 輪補回的事實被第 2 輪寫掉**。
本波唯一意圖：**地端交付的紀錄，其核心覆蓋率不得低於本次執行中曾達到的最佳值**。
機制必須**模型無關、平台無關**（macOS／LM Studio 與 Windows＋Ollama 同一條程式路徑）。

**非目標（不得宣稱）**：本波**不**提升初始生成品質；不得推論「地端已達雲端 Gemini 水準」。

## CRITICAL_PATH（照序執行）

1. `backend/core/config.py`：`LOCAL_LLM_REFINEMENT_NO_REGRESSION`（bool，預設 `True`）。
2. `backend/services/summarization.py`（**只在地端路徑**）：
   `_validate_local_record()`／`_core_coverage_snapshot()`／`_refinement_regression_reason()`、
   `_summarize_with_local_pipeline()` 補強迴圈的最佳版本交付。
3. `tests/test_t20260923_p7a_refine_no_regression.py`（A1 全項）。
4. 全套測試綠（`tests/`，排除 `tests/test_end_to_end.py`）。
5. commit（工作樹必須乾淨——E2E runner 的前置條件）。
6. E2E：`gemma-4-31b-it-mlx`＋同一音檔＋`--template section_meeting`＋`--quality-mode observe`。
7. 證據登錄（`e2e/attempt-*/`，append-only）→ commit → push。

## 語意不變式（動了就要 replan，不是 bounded fix）

- `LOCAL_LLM_RECORD_COVERAGE_MODE=off`：完全不跑、無 log、無 metrics、守衛不作用
  （＝byte 級回本波前）。
- `observe`：逐條對帳**問題清單**零變化；但**交付版本**可被本守衛換成較佳版本
  （F1 修訂後的精確表述，文件已同步）。
- `cov_*` metrics 行格式與解析契約不動；新觀測值一律走獨立 log 行。
- `missing_items_<類別>` 為 additive 內部統計鍵（不進 metrics 行）。
- 雲端路徑（`_summarize_with_gemini()` 的補強迴圈）與共用訊息 builder：**一字不動**。
- 不回退判定＝①未涵蓋數變多；②未涵蓋數相同但換項。**不採**「掉任何一項即回退」（見計畫 §5 邊界 3）。

## BEST_EFFORT／不阻斷（如實降級即可）

- B1 全套測試、B2 `scripts/check_docs.sh` 不得新增 error、B3 文件同步（CHANGELOG／手冊／規劃文件）。
- A0 離線重播腳本必須進 repo（不得只留 `/tmp`）。
- 回退後即停止再補強（不收斂保護）＝已知界線，不需修。

## 停止／升級條件

- 計畫指紋不符、或需要動到上面任一「語意不變式」⇒ **停止並回 Planner**。
- E2E 出現既有 required 閘門 FAIL ⇒ 停止並回報（不得改門檻）。
- 若某輪判定需要「掉了就回退」的嚴格版或改比忠實度 ⇒ 那是語意變更，回 Planner。
- Windows／Ollama 實機一律標 `[UNVERIFIED]`（本機 macOS），不得宣稱已驗。

## 已知證據（實作者可直接引用，勿重跑）

- 回退事件：`data/cache/e2e/p6a-gemma31b-e6/backend.log`（`15:28`／`15:35`／`15:42` 三段對帳）。
- 手冊判讀法：`doc/操作手冊/地端模型品質優化與驗證手冊_v4.10.md` §8-18。
- 落差研究（本任務持久副本）：`research/p7-gap-analysis.md`。
