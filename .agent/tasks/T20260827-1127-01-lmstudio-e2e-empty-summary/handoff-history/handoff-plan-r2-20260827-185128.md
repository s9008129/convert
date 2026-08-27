# Handoff — 修復 LM Studio 空摘要：merge 預算語意分離與有界 recovery

## EXECUTOR_PROMPT

你是接手本任務的實作工程師。你的唯一目標是：讓使用者上傳原始會議音檔後，系統以 fresh-cache MLX ASR 轉錄、以啟動時唯一選定的 LM Studio LLM 產出**非空、結構完整、保留尾端決議／待辦、可下載的「會議紀錄」DOCX**。

嚴格依序執行下方 `IMPLEMENTATION_WAVES`，**不得跳步、不得先改 production code 再補測試**。每個 WAVE 完成後先跑對應 focused tests 確認結果，再進入下一 WAVE。

你必須遵守的鐵律（違反即失敗）：
1. **先寫會以正確原因失敗的測試**（WAVE-01），再改 production code。
2. **不硬編碼／載入／卸載／切換 LM Studio 模型**；保留零／一／多模型與 optional override 選模契約。
3. **不新增第三方依賴、不變更 database/schema/backfill、不變更 task state、不建立跨 repository 耦合**。
4. **health 只允許新增向後相容 nullable `build_revision` 欄位**，其餘 HTTP contract 不變。
5. **correction、overlap、paragraphization、diagnostics、build metadata 缺失不得升級成全域 veto**。
6. **merge 不得以 hard truncation 偽造成功**；無法收斂時拋 `LOCAL_LLM_MERGE_NOT_CONVERGED` 走既有 fallback。
7. 遇到 `STOP_AND_ESCALATE_IF` 任一情況，**停止並回報**，不得自行改語意。

開始前先讀 `MUST_READ_PLAN` 列出的 plan 章節，再執行 `FIRST_ACTION`。

---

## TASK
- TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary
- STATUS: READY_FOR_IMPLEMENTATION
- PLAN_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/plan.md
- PLAN_REVISION: 2
- PLAN_SHA256: 7ecccb5633b6c35f618e8b2901d16ca65f6ea44c160aa181f318e8d8ba654731
- REVIEW_REQUIRED: YES
- REVIEW_REPORT: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/review/attempt-02/review_report.md
- REVIEWED_PLAN_REVISION: 2
- REVIEWED_PLAN_SHA256: 7ecccb5633b6c35f618e8b2901d16ca65f6ea44c160aa181f318e8d8ba654731
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: FAIL_FIRST_REGRESSION + CONTRACT_INTEGRATION + OWNED_PROCESS_FRESH_CACHE_TRUE_E2E + DOCX_FULL_PAGE_QA
- Fresh Implementer required: YES
- Planner/Reviewer transcript required: NO

## GOAL_ANCHOR

- **PRIMARY_OUTCOME**：原始會議音檔 → fresh-cache MLX ASR → 唯一已載入 LM Studio LLM → 非空、結構完整、保留尾端決議／待辦、可下載的「會議紀錄」DOCX。
- **SUCCESS_EVIDENCE**：隔離 fresh-cache 環境完成真實上傳；DOCX 標題「會議紀錄」、無失敗警告、必要章節有實質內容、尾端決議／待辦存在、逐字稿可獨立下載、全程沿用啟動時唯一選出的 loaded instance。
- **MUST_NOT_BREAK**：不硬編碼/載入/卸載/切換模型；保留零/一/多模型與 optional override 選模契約；保留 Ollama、Gemini、task state 與「摘要失敗仍保存逐字稿」降級路徑；不新增依賴、不變更 database/schema/backfill、不建立跨 repository 耦合；health 僅允許新增向後相容 nullable `build_revision`。

## CRITICAL_PATH

1. 先建立能重現兩個 current-code failure shapes 與 silent truncation 的 fail-first tests。
2. 分離 merge input、visible target、provider completion 三種 token 語意，恢復 reasoning-aware merge generation。
3. 擴充有界 recovery state machine，涵蓋 growth retry 後 `stop + reasoning + empty content`。
4. 移除 CORE hard truncation，改用有進度證明的 hierarchical compaction 與 stable non-convergence error。
5. 對齊 220-token overlap 實作與規劃假設，新增 bounded-call diagnostics。
6. 新增 revision/port provenance，執行 owned-process fresh-cache true E2E 與 DOCX 全頁 QA。
7. Stage 05 通過後才把本機 9527 切換到已核准 HEAD。

## SEMANTIC_INVARIANTS

以下語意邊界**不可變更**，否則視為語意契約變更需重新 Review：

1. **generation success 必須有非空 final content**；reasoning 不得當作正式摘要或寫入 DOCX/log。
2. **provider total completion budget 與 orchestration visible-output target 是不同契約**，不能共用一個 token 欄位。
3. **merge 必須保留全部來源事實並確定性收斂**；不能以 hard truncation 偽造成功。
4. **semantic retry、network retry、merge rounds 必須分開計數且各自有界**。
5. **correction 是 BEST_EFFORT**；CORE extraction/merge/final 才能啟用 reasoning recovery。
6. **health revision 是 E2E freshness gate**，但 unknown revision 不得使一般產品 startup/global health 失敗。
7. **fallback transcript 是必要安全機制**，不得被 acceptance 誤判為正式會議紀錄成功。

## BEST_EFFORT_DO_NOT_GATE

以下元素失敗時**必須局部降級、保留原文並繼續**，不得阻擋核心摘要：

- LLM 同音／專有名詞校正（correction）——首次 `StableServiceError` 後保留該段及剩餘原文並熔斷。
- overlap enrichment——可降為零。
- paragraphization。
- token diagnostics。
- build metadata 缺失——一般執行允許 unknown。

## DEFERRED_NOT_THIS_TASK

- 不針對 Qwen 或個別模型家族建立專屬 thinking-disable adapter。
- 不新增 speaker diarization、時間戳排版、語意段落重建或 ASR decoder tuning。
- 不為 build revision 建立一般產品 readiness veto。
- 不承諾所有自然重複都被刪除；cleanup 保持高 threshold 與保守策略。
- 不宣稱 NVIDIA hardware E2E；只執行可用的 shared regression tests。

## REPO_ANCHOR

- Project root: /Users/hsiaojohnny/dev/convert
- Branch: main
- Anchor HEAD: 96e6e7416a0791b674b0ef5f17f8ba34355ef5c5（Revision 1 實作 commit）
- Relevant dirty state: 工作樹 clean
- Drift since plan/review: 無 product code 變更；僅新增 review/attempt-02/ 與 handoff-history/ 產物

## CURRENT_STATE_DELTA

無。plan 撰寫後僅新增 review/attempt-02/ 產物與 handoff-history/ 歸檔，product code 未變。

## MUST_READ_PLAN

開始 FIRST_ACTION 前，**必須**先讀 plan.md 以下章節（其餘可略讀）：

- `GOAL_CONTRACT`（PRIMARY_OUTCOME / CORE_ACCEPTANCE_SIGNAL / MUST_NOT_BREAK / NON_GOALS）
- `CONFIRMED_ROOT_CAUSE`（RC-1~RC-5，逐條對應修復）
- `SEMANTIC_CONTRACT_AUDIT`
- `DECISION_CONTRIBUTION_MATRIX`
- `CRITICAL_PATH`
- `CHANGE_MAP`（1~5 五組變更的完整規格）
- `IMPLEMENTATION_WAVES`（WAVE-01~04 順序）
- `REGRESSION_AND_ACCEPTANCE`（fail-first unit/contract、integration/full suite、independent owned-process true E2E）
- `DEFINITION_OF_DONE`

## SETTLED_DO_NOT_REOPEN

以下已由 plan + review 定案，**不得重新討論或推翻**：

- 五個根因（RC-1~RC-5 已 falsified/confirmed，見 plan `CONFIRMED_ROOT_CAUSE` 與 `FALSIFIED_ALTERNATIVES`）。
- 選模契約：zero/one/multiple/override 規則不變。
- 不新增模型 allowlist、不新增模型專屬 prompt 分支、不新增 LM Studio lifecycle 管理。
- 不把 health check 升級為會主動執行昂貴生成的全域 readiness gate。
- 不更換目前 loaded model 作為根因修復。
- 三種 merge budget 語意分離是 CORE 修復方向，不是可選項。

## REVERIFY_ON_START

僅以下**可變事實**需在開始時重新確認（其餘以 plan 為準）：

- LM Studio 是否仍只有一個 loaded LLM（預期 `qwen3.6-35b-a3b-mlx`，loaded context length 183,296）。
- LM Studio 服務可達性（`/api/v1/models`）。
- 音檔 `/Users/hsiaojohnny/Downloads/0818-優規需求確認會議.m4a` 是否存在。
- 目前 `LOCAL_LLM_RESERVED_OUTPUT_TOKENS`（預期 3072）與 `LOCAL_LLM_MAX_MERGE_ROUNDS`（預期 3）的實際值。

## TRIGGERED_POLICIES

- goal-alignment-design-economy.md
- plan-review-gate.md
- testing-verification.md
- debugging-recovery.md
- dependencies-contracts.md
- security-privacy.md
- git-change-hygiene.md

## FIRST_ACTION

**WAVE-01**：在 `tests/` 下新增 production-shaped regression tests，先觀察它們以正確原因失敗，**不得先改 production code 再補測試敘事**。至少涵蓋：

1. task `90fdb193` 的 merge `length/reasoning/empty` fixture。
2. task `8fd56c54` 的 `initial length/empty -> growth stop/empty -> replay content` fixture。
3. non-converging merge、tail sentinel、overlap 220-token 與 health revision compatibility tests。

## IMPLEMENTATION_WAVES

- **WAVE-01 [CORE]** — Fail-first evidence lock：新增上述 4 類測試，確認以正確原因失敗，保存實際 failure。
- **WAVE-02 [CORE]** — 恢復 CORE merge/output contracts：實作三種 merge budgets、來源分組、visible-target compaction、preflight、最多三次 semantic recovery state machine、移除 hard truncation、新增 `LOCAL_LLM_MERGE_NOT_CONVERGED` stable error。
- **WAVE-03 [SUPPORTING]** — 收斂 supporting amplification 與 provenance：對齊 220-token overlap、新增 diagnostics、optional build revision、actual port logging、owned-process E2E runner。
- **WAVE-04 [VERIFICATION]** — 完整驗證與獨立驗收：focused tests、完整 `uv run pytest tests/ -q`、final diff inspection、獨立 Stage 05 true E2E 與 DOCX 全頁 QA。

詳細規格見 plan `CHANGE_MAP` 1~5，此處不重複。

## ACCEPTANCE_CONTRACT

**CORE（必須全過）**：

- `merge_visible_target_tokens=900` 時，provider 初始 completion cap 仍為 reserved output（3072），而不是 900。
- reasoning-only growth retry 可成功；回傳 note 經 orchestration 最終收斂到 `<=900`。
- merge 不會因 visible target 而設定 `allow_reasoning_retry=False`。
- `initial length/empty -> growth stop/empty -> final replay content` 精確三次 calls，model/instance/prompt/temperature 不變，只有 growth retry 增加 token cap。
- 第三次仍空、第二次再度 length、無 reasoning、無 headroom 都回傳 `LMSTUDIO_NO_FINAL_CONTENT`，不再呼叫 provider。
- correction 相同回應 shape 最多一次 provider call，保留當段及剩餘文字，摘要核心繼續。
- Context 可行時每組至少容納兩份目標大小 notes；single oversized note 可壓縮；持續不縮短時在 max rounds 內回傳 `LOCAL_LLM_MERGE_NOT_CONVERGED`。
- Tail sentinel 永不因 truncation 消失。
- 每個 chunk boundary 重複 carry `<=220 tokens`，line cap 仍生效；所有非 overlap 來源內容保持順序與完整覆蓋。
- `build_revision` 可為 null；舊 health consumer、zero/one/multiple selection、Ollama/Gemini、task fallback 不回歸。
- 完整執行 `uv run pytest tests/ -q`；任何 failure 必須分類為 regression、pre-existing、environment 或 test defect。

**Independent owned-process true E2E（DoD 核心）**：

1. 以 free port、隔離 temp `DATA_DIR` 與 expected Git revision 啟動並擁有 backend child process。
2. Health `build_revision` 必須等於核准 HEAD；記錄唯一 loaded model/instance/context snapshot，不修改 LM Studio inventory。
3. 實際上傳 `/Users/hsiaojohnny/Downloads/0818-優規需求確認會議.m4a`，確定 fresh MLX ASR 執行。
4. Poll 到終態；不得為 `summary_failed`，不得出現 fallback title/warning、`max_tokens=1`、98-call correction amplification、hard truncation 或 merge non-convergence。
5. 驗證每個 chunk 合法、correction stable failure 後最多一次呼叫、semantic retries/merge rounds 符合各自上限、全流程 model selection 不變。
6. 下載逐字稿與 DOCX；必要章節非空，抽查尾端決議／待辦存在，逐字稿無達 cleanup threshold 的病態連續 run。
7. 以 OOXML 結構抽取加 LibreOffice/Poppler render 檢查 DOCX 每一頁；100% 檢查 clipping、overlap、缺字、亂碼、failure banner、空白頁與可讀性。
8. 保存完整 artifacts/log/result 至新的 Stage 05 append-only attempt；不得覆寫舊 E2E 證據。

## STOP_AND_ESCALATE_IF

遇到以下任一情況，**停止並回到 Stage 01 escalation replan**，不得自行決定：

- 需要模型 allowlist、模型專屬 prompt 分支或 LM Studio lifecycle 管理。
- 需要改變 selection readiness 語意。
- 需要變更 task state、fallback DOCX 或 HTTP response schema（除 additive `build_revision` 外）。
- 發現與 plan 不同的 root-cause decision。
- 需要新增依賴或 lockfile 變更。
- 需要修改 `/Users/hsiaojohnny/dev/yt_down_txt` 或建立跨 repository 耦合。
- 無法用本 plan 的 progress/retry contract 修復（例如 merge 3 輪仍無法收斂且調整 provider cap/visible target 差距仍無效）。

## HISTORICAL_TASK_DEPENDENCIES

- T20260826-2310-01-mac-m4-dual-runtime（前置 Mac dual-runtime task）：本 task 承接其「任意唯一 loaded LLM」與真實 E2E 的明文要求；其 commit 明確未宣稱 LM Studio 真實 E2E 已完成。

---

TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary
HANDOFF_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/handoff.md
PLAN_REVISION: 2
STATUS: READY_FOR_IMPLEMENTATION
NEXT_STAGE: 04_IMPLEMENT
