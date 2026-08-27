# Stage 04 實作完成報告 — LM Studio 空摘要修復

- TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary
- STAGE: 04_IMPLEMENT → READY_FOR_STAGE_05
- PLAN_REVISION: 2（SHA-256 7ecccb56…，與 handoff/review attempt-02 一致）
- 報告時間: 2026-08-27T16:22+08:00
- 執行模式: Fleet（主協調者 + 7 個平行/序列子代理）

## 意圖（為何做）

Revision 1 實作宣稱通過 495 tests，但兩次 fresh-process true E2E 仍失敗：
task `90fdb193`（merge 以 visible target 900 當 provider cap 且禁用 reasoning
recovery → reasoning 吃光預算 → 空摘要）與 task `8fd56c54`（growth retry 後
`stop + reasoning + empty` 無 replay → `LMSTUDIO_NO_FINAL_CONTENT`）。Plan
Revision 2 確認 RC-1~RC-5 五個根因，本階段依 CHANGE_MAP 1~5 實作修復，
並以 fail-first 測試先行鎖定契約（先見證以正確原因失敗，再實作轉綠）。

## 做了什麼（Waves 與 commits）

- `2e446ed` WAVE-01（4 子代理平行）：22 個 production-shaped fail-first 測試
  （merge budget 分離 4、三次呼叫 recovery 序列 7、收斂/tail sentinel 5、
  overlap 220-token + health revision 6）；合併驗證 16 failed（全部為預期
  行為原因）+ 6 passed（刻意契約鎖定）、0 collection errors；5 份證據歸檔。
- `a692dff` WAVE-02 CORE：
  - `LocalContextPlan` 單一 merge 欄位拆為 `merge_input_budget_tokens` /
    `merge_visible_target_tokens` / `merge_provider_output_tokens`（RC-1）。
  - preflight：context 須同時容納 merge prompt、兩份目標大小 notes、
    provider completion reserve，否則 `LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED`。
  - 最多三次 completed provider calls 的 semantic recovery state machine：
    initial → growth retry（僅 length+reasoning+empty）→ stop replay（僅
    growth 後 stop+reasoning+empty）；`allow_reasoning_retry` 單獨決定
    （RC-2）；correction 維持 BEST_EFFORT 熔斷。
  - 移除 CORE merge hard truncation；無進度/達 max rounds 拋新增 stable
    error `LOCAL_LLM_MERGE_NOT_CONVERGED`（RC-3）；tail sentinel 保留。
  - diagnostics 改記 attempt_type；修復 production pipeline 呼叫端新欄位。
- `5be217c` WAVE-03a：共享常數 `LOCAL_LLM_CHUNK_OVERLAP_BUDGET_TOKENS=220`
  同時約束 planner step 與 assembler carry（RC-4）；structured metrics
  （logical generations / semantic attempts / network retries / merge rounds
  / chunk count / 階段 durations）。
- `b8a446d` WAVE-03b：health nullable `build_revision`（RC-5）、actual port
  logging、`scripts/e2e/run_owned_e2e.py`（free port、隔離 DATA_DIR、
  revision gate、append-only artifacts）。
- `54afc16` / `d13c5cb`：驗證證據歸檔 + config 描述 doc-sync。

### 過程異常與處置（可審計）

wave02 CORE 子代理於 15:17 後靜默 45 分鐘（零檔案活動、queued 訊息無法
喚醒），主協調者宣告卡死並接管：修復其半成品遺留（`attempt_type` 簽名、
pipeline 呼叫端舊欄位、測試 LocalContextPlan 欄位適配）並完成 WAVE-03a。
子代理喚醒後獨立驗證與主協調者成果互相印證（16/82/517 passed），並貢獻
config 描述 doc-sync；其對 diff 的逐行審計確認無斷言竄改。

## 驗證結果

- 完整 `uv run pytest tests/ --ignore=tests/test_mlx_direct.py`：
  **517 passed / 2 skipped / 0 failed**（baseline 495 + 22 新測試）。
- WAVE-01 fail-first 16 個測試全數轉綠；6 個契約鎖定維持通過。
- final diff inspection（b493c74..HEAD）：無依賴/lockfile/task-state 變更；
  health 僅 additive nullable 欄位；無模型 lifecycle/selection 語意變更。
- REVERIFY_ON_START 已核：LM Studio 唯一 loaded LLM（qwen3.6-35b-a3b-mlx,
  ctx 183,296）、音檔存在、reserved output 3072、max merge rounds 3。

## 下一步建議（Stage 05 — 獨立驗收，本報告不宣稱 primary outcome 已修復）

1. 以 fresh context 執行 `scripts/e2e/run_owned_e2e.py`：free port + 隔離
   temp DATA_DIR + `MEETINGSCRIBE_BUILD_REVISION=$(git rev-parse HEAD)`
   （必須等於 d13c5cb 之後的核准 HEAD）。
2. 上傳 `/Users/hsiaojohnny/Downloads/0818-優規需求確認會議.m4a`，確認
   fresh MLX ASR；poll 終態不得為 summary_failed、無 fallback title、
   `max_tokens=1`、98-call amplification、hard truncation 或 non-convergence。
3. 驗證 metrics log：semantic attempts ≤ 上限、merge rounds ≤ 3、chunk 數
   與 overlap 收斂後行為一致。
4. 下載 DOCX 做 OOXML 結構 + LibreOffice/Poppler 全頁 visual QA；抽查尾端
   決議／待辦 sentinel。
5. artifacts 存入新的 Stage 05 append-only attempt（不得覆寫舊證據）。
6. Stage 05 通過後才依 LOCAL_ROLLOUT_AND_ROLLBACK 切換本機 9527（先以
   PID/cwd/指令行證實 ownership，不猜測性 kill），並執行 health smoke。
7. 通過後再寫入 result.md 與宣稱修復完成；handoff.md 編譯 Revision 3 依
   harness 規則先歸檔現行版本。

## 風險與殘餘事項

- 完整 suite 的 skip 數在不同執行環境出現 2/3 差異（環境相關 skip，
  非本次引入；Stage 05 應記錄其條件）。
- E2E runner 已煙霧驗證（含 revision gate 鑑別力），但尚未跑過真實昂貴
  E2E——runner 對真實音檔的 poll/下載路徑需 Stage 05 首跑確認。
- 9527/9631 既有 process 為 stale pre-fix 服務，Stage 05 ownership 流程前
  不得終止。