# execution.md — Stage 04 實作記錄（P7-A）

- 計畫：`plan.md` **PLAN_REVISION 2**（`sha256` 前 16 碼 `a8b2a4881f8701f1`，實作者開工前已重算比對一致）
- handoff：`handoff.md`（與計畫同修訂）
- 實作 commit：`3e9311a`
- 實作範圍：`backend/core/config.py`、`backend/services/summarization.py`、
  `tests/test_t20260923_p7a_refine_no_regression.py`（新）、
  `tests/test_t20260923_p4a_record_coverage.py`（T17 斷言 additive 鍵）

## 做了什麼（與計畫逐項對應）

| 計畫項 | 落地 |
|---|---|
| A1.1 兩條回退判定 | `_refinement_regression_reason()`（純函式；①未涵蓋數變多②等量互換） |
| A1.2 最佳版本交付 | `_summarize_with_local_pipeline()`：`best_summary`／`best_snapshot`，同分取最後一版 |
| A1.3 `false` 回本波前 | `LOCAL_LLM_REFINEMENT_NO_REGRESSION=false` ⇒ 不取快照、無守衛 log、交付最後一版 |
| A1.4 問題清單一致 | 回退後以 `_validate_local_record()` 重算；`cov_*` 與交付版本一致 |
| A1.5 停用路徑 | 快照 `None`／期望數變動 ⇒ 停用比較、留 `log.info` 說明 |
| A2 觀測 | info：`地端補強不回退守衛：…`；回退 warning：`地端補強第 N 輪造成事實回退（…）…` |
| A3 測試 | T01–T12 全綠；既有測試不變（T17 僅新增 additive 鍵斷言） |

## 驗證（實跑）

- 全套：`DATA_DIR=/tmp/probe_scratch_p7a uv run --frozen python -m pytest tests/ -q --ignore=tests/test_end_to_end.py`
  ⇒ **1100 passed, 2 skipped**（P6-A 基線 1088 → +12）。
- 新檔＋受影響檔：`tests/test_t20260923_p7a_refine_no_regression.py tests/test_t20260923_p4a_record_coverage.py`
  ⇒ **47 passed**。
- A0 離線重播（真實逐字稿＋真實筆記＋真實交付紀錄；同一份產品判定函式）：
  `e2e/attempt-P7A-offline-replay/` ⇒ 較佳版 26/46、真實交付版 27/46 ⇒
  `guard_would_revert: true`、原因「未涵蓋數變多」（獨立審查者已重跑重現同數字）。

## 與計畫的偏差

- 無語意偏差。唯一未動的是計畫 §2 內一處行號引用（`summarization.py:3320-3330`）
  已因本波新增程式碼而漂移（現為 `:3396-3419`）——**刻意不改** `plan.md`，
  因為任何修訂都會改變計畫指紋、使 `review/attempt-02` 的 `PLAN_APPROVED` 失效；
  以本檔與審查報告共同登錄即可。

## 未完成／已知落差（不得宣稱已解決）

- 正式 E2E（`e2e/attempt-P7A-gemma31b-e7c`）於本檔撰寫時仍在執行：**verdict 未產生**。
- A0 離線重播的輸入（逐字稿、筆記）來自 gitignored 的 runtime 目錄與 `/tmp`，
  且 committed `output.json` 由較早版本腳本產生（schema 與現行腳本有漂移，數字已由
  獨立審查者重現）⇒ 屬**不可完全重現的輔助證據**，不是 CORE 驗收來源。
- Windows 11＋Ollama 實機 `[UNVERIFIED]`（本機僅 macOS；靜態追蹤顯示兩引擎共用同一條
  地端 pipeline，守衛在其上層，無平台／模型分支）。
