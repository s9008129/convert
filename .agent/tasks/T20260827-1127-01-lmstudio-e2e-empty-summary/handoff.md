# Handoff — 最新音檔空摘要：先修驗收器與 runtime provenance，再做模型代理 Browser E2E

## EXECUTOR_PROMPT

你是新的 **Stage 04 Implementer**，將在 GitHub Copilot CLI 的 fresh session 中執行本任務。這份交接已刻意寫給能力較低的模型：請照順序逐項完成，不要自行重做根因分析、擴張範圍或跳過 fail-first。

你的任務不是再次修改摘要演算法。最新使用者失敗 task `c218e432` 命中 09:26 啟動的 stale pre-fix backend；current HEAD 對最新音檔尚未被真正驗收。你現在只能修正：

1. `scripts/e2e/run_owned_e2e.py` 的 false-PASS 與 Browser-sidecar E2E 能力；
2. `scripts/macos/start-mac-native.sh` 的 revision/DATA_DIR/health provenance；
3. 上述兩者的 focused fail-first tests；
4. Stage 04 execution evidence。

**絕對禁止修改** `backend/services/summarization.py`、`backend/services/task_processor.py`、`backend/api/routes.py`、`backend/models/schemas.py`、`frontend/`、模型設定、依賴或 lockfile。若 true E2E 之後證明 current code 仍有產品失敗，那是 Stage 05 保存證據後回 Revision 4 replan 的工作，不是你現在的授權。

開始後嚴格執行：

1. `cd /Users/hsiaojohnny/dev/convert`，讀適用 `AGENTS.md`、`/Users/hsiaojohnny/.codex/prompts/04_implement_prompt.md`、本 handoff，以及 `MUST_READ_PLAN` 指定章節。
2. 驗證 `plan.md` SHA-256 必須是 `d76e236204e53a298741f02e012a3d96e7de12cb89be072c77cdc0a9b9d7dafd`、`PLAN_REVISION: 3`、`REVIEW_REQUIRED: NO`；任何 mismatch 立即停止。
3. 執行 `git status --short --branch`。若有非本 handoff commit 產生、來源不明的 dirty changes，停止，不要 stash/reset/overwrite。
4. 第一刀只寫 `tests/test_owned_e2e_acceptance.py` 與 `tests/test_macos_scripts.py` 的 fail-first tests。先觀察它們因 current runner/launcher 缺少批准行為而 red；import/fixture/permission error 不算有效 red。
5. 第二刀只改 runner。把 revision/clean/Data/model gates 放在 Browser ready 或 API upload 之前；加入 Browser upload mode；API/browser 共用 task/hash/formal DOCX/metrics/model validation；把 tracked redacted evidence 與 gitignored raw runtime 分開。保留現有 smoke/API mode 與 owned-process cleanup。
6. 第三刀只改 macOS launcher。由 clean Git HEAD 注入/驗證 revision，明確驗證 writable DATA_DIR，解析 health JSON，只在 exact revision match 後宣告 ready；任何失敗只終止自己啟動的 process，禁止 `pkill`。
7. 每一刀後先跑 focused tests；最後跑 Revision 2 regression、runner dry-run/smoke、shell syntax、完整 pytest、`git diff --check` 與 scoped diff inspection。
8. Stage 04 **不得**上傳 `/Users/hsiaojohnny/Downloads/盤點工具討論.m4a`、不得執行昂貴真實 E2E、不得啟動/切換本機 9527、不得寫 `result.md`。Stage 05 fresh verifier 才做 Browser E2E 與 rollout。
9. 驗證全過後，把 scoped implementation/evidence commit 成 clean HEAD，寫 `execution.md` 並交給 Stage 05。不要宣稱使用者 primary outcome 已修復。

任何需要改變成功定義、task state、fallback、HTTP schema、model selection/readiness、retry/merge/token 語意，或需要觸碰 `DO_NOT_TOUCH` 的情況，一律停止並寫 `escalation.md`；不得即席修補。

## TASK

- TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary
- STATUS: READY_FOR_IMPLEMENTATION
- PLAN_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/plan.md
- PLAN_REVISION: 3
- PLAN_SHA256: d76e236204e53a298741f02e012a3d96e7de12cb89be072c77cdc0a9b9d7dafd
- REVIEW_REQUIRED: NO
- REVIEW_REPORT: NONE
- REVIEWED_PLAN_REVISION: N/A
- REVIEWED_PLAN_SHA256: N/A
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: FAIL_FIRST_ACCEPTANCE_HARNESS + OWNED_PROCESS_BROWSER_UI_TRUE_E2E + SIDECAR_RUNTIME_MONITORING + DOCX_SEMANTIC_AND_FULL_PAGE_QA + OWNED_LOCAL_9527_ROLLOUT_SMOKE
- Fresh Implementer required: YES
- Planner/Reviewer transcript required: NO

## GOAL_ANCHOR

- **PRIMARY_OUTCOME：** 用 Browser 真正上傳 `/Users/hsiaojohnny/Downloads/盤點工具討論.m4a`，在 exact clean revision/fresh DATA_DIR/唯一 LM Studio instance 上取得非 fallback、忠實完整、可讀的正式會議紀錄 DOCX。
- **SUCCESS_EVIDENCE：** source/server audio SHA 同為 `5ffba7448c6846e56b358113c7ed4525507480ece9b031c5281435f59c6683d0`；task `completed + summary_failed=false`；UI 無 failure banner；正式 filename/title/sections；9 個 transcript-first semantic anchors；所有 DOCX 頁面 QA 通過。
- **MUST_NOT_BREAK：** fallback 產品語意、HTTP schema、模型選擇/lifecycle、Ollama/Gemini/ASR、使用者 data 與歷史 evidence 不變；raw sensitive artifacts 不進 Git；未知 process 不終止。
- **OPERATIONAL FINISH：** independent E2E PASS 後，才把本機 9527 自動切換到同一 accepted SHA 並做 health + Browser smoke。

## CRITICAL_PATH

1. `WAVE-01`：用 fail-first tests 鎖定 runner 的 revision mismatch 仍 upload、fallback false-PASS、wrong upload hash、ambiguous/changed model、invalid metrics/raw evidence 與 launcher null revision 問題。
2. `WAVE-02`：最小強化既有 runner；preflight fail closed，加入 Browser upload detection，API/browser 共用正式結果判定，保留 owned process/append-only。
3. `WAVE-03`：修 launcher provenance 與 writable DATA_DIR；完成 Stage 04 focused/full verification並 commit clean HEAD。
4. `WAVE-04`（Stage 05 only）：fresh in-app Browser 執行 exact audio true E2E、sidecar 監控、semantic/visual QA。
5. `WAVE-05`（Stage 05 only）：PASS 後依 ownership gate rollout accepted SHA 到 9527。

## SEMANTIC_INVARIANTS

1. 產品 `completed + summary_failed=true` 仍表示 transcript fallback 已安全保存；不得改成 task failed。但正式會議紀錄 E2E 必須把它判為 FAIL。
2. E2E 的 revision/dirty/model/data/hash gates 只保護 acceptance decision validity，不得變成一般 `/api/health` 或產品 upload global gate。
3. Browser 必須實際操作 UI；API/log 只可 sidecar monitor/download/check，不可冒充 user journey。
4. generation success 仍要求非空 final content；reasoning 不得寫入 DOCX/evidence。Revision 2 的 bounded retry/merge/token契約不在本輪重設。
5. correction、paragraphization、overlap enrichment 是 BEST_EFFORT；失敗應局部降級，不能單獨 veto formal-record success。
6. Stage 04 不以 latest stale-process DOCX 作為 current product failure；只有 WAVE-04 fresh exact-input E2E 才可推翻 current product premise。
7. Stage 05 product failure、任何 task-state/fallback/success/error/model-selection語意改變都必須 replan；Verifier/Implementer 不得修 product code。
8. tracked Stage 05 attempt 僅保存 redacted evidence/hash；完整 audio copy/transcript/DOCX/backend log 必須留在 `data/cache/...` 等 gitignored runtime path。

## BEST_EFFORT_DO_NOT_GATE

- LLM 同音／專有名詞 correction、paragraphization、overlap enrichment。
- 細部 transcript 自然口語品質（除非已造成 formal record 的 material semantic error）。
- 一般 product health 的 unknown build metadata；只有 Stage 05/accepted rollout 要求 exact revision。
- 額外 dashboard、長期 metrics storage、自動化 browser framework。

上述失敗要局部記錄；不得把它們升級成一般產品 global veto，也不得讓它們掩蓋 CORE formal-document failure。

## DEFERRED_NOT_THIS_TASK

- 修改 summarization/correction/chunk/merge/retry/token/prompt/model-selection 演算法。
- 刪除 fallback 或改變 task status/public HTTP/frontend contract。
- 更換/載入/卸載 LM Studio model、模型專屬 adapter 或 thinking-disable。
- 遠端 production/CI/NVIDIA E2E、database/schema/dependency/lockfile、跨 repo 變更。
- 重跑舊 `0818-優規需求確認會議.m4a` 作為本次 primary acceptance。

## REPO_ANCHOR

- Project root: /Users/hsiaojohnny/dev/convert
- Branch: main
- Anchor HEAD: ad37146ff599f960b930889cf07b28f3cee8e0fb（Revision 2 Stage 04 product baseline；本 handoff 的 docs-only commit 會使 HEAD 前進）
- Relevant dirty state: Handoff 編譯時只有 current task 的 Revision 3 plan、Revision 2 handoff archive 與 Revision 3 handoff；product tree 無變更
- Drift since plan/review: 無 product code drift；Revision 3 明確免 Review，沒有 review report 可匹配

## CURRENT_STATE_DELTA

- Revision 2 product implementation已存在於 current branch，Stage 04 報告記錄 517 passed / 2 skipped；本次 focused recheck 在 isolated writable DATA_DIR 為 33 passed。
- 最新 manual task `c218e432` 的 input/output hashes 已確認，但它命中 09:26 stale process，不能證明 current HEAD 失敗。
- 現有 runner full PASS 只要求 task completed + transcript/docx downloaded；因 product fallback 仍 completed，它會 false-PASS 使用者這次失敗。
- runner revision mismatch 目前只記 failure 仍繼續 upload；launcher 目前不注入/驗證 build revision；inherited `/app/data` 可能不可寫。
- Planning/Handoff 時 9527 無 listener；LM Studio 有唯一 `qwen3.6-35b-a3b-mlx` instance（context 183296）。這些是 mutable facts，實作/驗收起始需重驗。

## MUST_READ_PLAN

在 `FIRST_ACTION` 前完整讀以下章節；不要只靠本 prompt：

- `META`、`OWNER_CHECK`
- `GOAL_CONTRACT`：`REQ-CORE-01`～`REQ-CORE-08`、`MUST_NOT_BREAK`、`NON_GOALS`
- `EXPECTED_VS_OBSERVED`、`ROOT_CAUSE`：`RC-3A`～`RC-3D`
- `SEMANTIC_CONTRACT_AUDIT`、`DECISION_CONTRIBUTION_MATRIX`
- `FIX_TYPE_AND_ENVELOPE`、`DO_NOT_TOUCH`、`GLOBAL_GATES_AND_RATIONALE`
- `CRITICAL_PATH`
- `CHANGE_MAP`：Stage 04 必做 `CM-01`、`CM-02`、`CM-03`；Stage 05 contract `CM-04`、`CM-05`
- `IMPLEMENTATION_WAVES`：Stage 04 只執行 `WAVE-01`～`WAVE-03`
- `REGRESSION_AND_ACCEPTANCE`、`DEGRADATION_AND_GATE_TESTS`
- `DEFINITION_OF_DONE`、`FAILURE_ROUTING`、`HANDOFF_HINTS`

## SETTLED_DO_NOT_REOPEN

- `RC-3A`：latest artifact 的直接原因是 stale runtime；不要再從該 DOCX推導新的 current-code product patch。
- `RC-3B`：runner 的 success predicate 必須拒絕 `summary_failed=true` 與 fallback document。
- `RC-3C`：macOS launcher 必須提供可驗證 revision/DATA_DIR/health provenance。
- `RC-3D`：current product outcome仍未知；Stage 04不修改產品，Stage 05 exact Browser E2E才裁決。
- `DEC-BROWSER`：Browser 做實際 UI upload/download；API只作 sidecar。
- `DEC-EVIDENCE`：tracked attempt只有 redacted metadata/hash；raw sensitive files在 gitignored runtime。
- `DEC-ROLLOUT`：Stage 05 PASS後自動切換 9527；unknown ownership則停止，不猜測性 kill。
- `DEC-REVIEW`：使用者明確免除 Revision 3 Review；`REVIEW_REQUIRED: NO`，不得重新加 gate。

## REVERIFY_ON_START

Stage 04 開始只重驗這些 mutable facts：

- plan path/revision/SHA 完全匹配本 handoff；handoff docs commit存在於 HEAD 或其 ancestor。
- branch/HEAD/worktree；沒有來源不明 dirty changes。
- `DATA_DIR` shell value；所有 pytest 明確改用新建的 writable isolated test root，不沿用 `/app/data`。
- current runner/launcher/tests仍與 plan 所述缺陷一致；若已被其他 commit修復，先分類 drift，不重複改。
- Stage 04 smoke 時 LM Studio service可達且只有一個 loaded LLM/instance；不得修改 inventory。

Stage 05 另重驗：exact audio path/hash、clean accepted HEAD、Browser/Documents capabilities、LM Studio inventory/context、9527 listener ownership。

## TRIGGERED_POLICIES

- goal-alignment-design-economy.md
- workflow-routing.md
- testing-verification.md
- debugging-recovery.md
- dependencies-contracts.md
- security-privacy.md
- git-change-hygiene.md

Stage 05 另載入 `ui-accessibility.md`，因其會實際驗收 UI interaction/state。

## FIRST_ACTION

完成 startup consistency checks 後，建立/擴充 fail-first tests，**不要先改 scripts**：

1. 新增 `tests/test_owned_e2e_acceptance.py`。以 `importlib` 或 repository-consistent方式載入 runner，使用 pure helper/fake client/temporary DOCX/log/data；不可啟動 ASR或上傳真音檔。
2. 在 `tests/test_macos_scripts.py` 加入 launcher revision/DATA_DIR/health/owned-cleanup contract checks。
3. 建立 isolated writable env，例如先用 `TEST_DATA_ROOT=$(mktemp -d)`，再以 `DATA_DIR="$TEST_DATA_ROOT/data"` 執行：
   `uv run pytest -q tests/test_owned_e2e_acceptance.py tests/test_macos_scripts.py`。
4. 保存第一個有效 red：revision mismatch仍可能 upload、fallback completed未被拒絕、wrong hash/model/metrics/launcher provenance契約缺失。若是 collection/import/permission error，修測試直到失敗原因正確。

最低 fail-first case 清單（全部見 plan `CM-01`）：

- revision mismatch → upload call count 必須 0；
- completed + `summary_failed=true` → FAIL；
- fallback Content-Disposition/OOXML → FAIL；
- server upload SHA mismatch → FAIL；
- model/instance 非唯一或 before/after 改變 → FAIL；
- invalid/unwritable DATA_DIR → backend未啟動且明確錯誤；
- Browser log upload mapping 0/>1 → FAIL；
- invalid/missing metrics、`semantic_attempts > 2 * logical_generations`、merge rounds >3、`max_tokens=1`/truncation/nonconvergence → FAIL；
- launcher未 derive/inject/verify revision 或使用 broad kill → FAIL。

## IMPLEMENTATION_WAVES

### `WAVE-01 [CORE]` — Fail-first tests only

- Allowed: `tests/test_owned_e2e_acceptance.py`, `tests/test_macos_scripts.py`, append-only Stage 04 fail-first evidence。
- Exit: tests fail only for approved missing behavior; no product/script edit yet。

### `WAVE-02 [CORE]` — Runner hardening

- Allowed: `scripts/e2e/run_owned_e2e.py` + WAVE-01 tests。
- Add small testable helpers for SHA, repo/revision/data/model/task/formal DOCX/metrics validation；API/browser後續共用，避免兩套 success semantics。
- Add `--upload-mode api|browser` or equivalent single mode flag。Browser mode不POST audio；gate通過後 flush `BROWSER_E2E_READY`，bounded parse isolated backend既有 upload-success log取得唯一 stored filename/task ID。
- Gate order固定：clean HEAD/audio/data → start owned child → health exact revision → unique model → UI ready/API upload → actual stored bytes SHA → task completion + `summary_failed=false` → transcript/DOCX header/OOXML/sections → metrics + ending model snapshot → owned cleanup。
- Hard failure before ready/upload must stop owned child and record FAIL；不能 append error後繼續。
- Tracked `.agent/tasks/.../e2e/attempt-N`只放 redacted evidence/hash；raw `backend_data/backend.log/transcript/docx`放 `data/cache/e2e/...` 等 gitignored path。保留 existing CLI compatibility。
- Exit: WAVE-01 focused tests green；runner help/dry-run/smoke通過；不跑真音檔。

### `WAVE-03 [CORE/SUPPORTING]` — Launcher + verification/package

- Allowed: `scripts/macos/start-mac-native.sh`, `tests/test_macos_scripts.py`, Stage 04 `execution.md`/evidence。
- Git available：clean HEAD authoritative；explicit revision不同則啟動前 fail；dirty可區分且不得冒充 accepted clean SHA。No-Git packaged case才允許 explicit/unknown。
- Validate actual DATA_DIR writable；log root/host/port/data/revision；parse health JSON並 exact-match後 ready。
- On mismatch/parse/timeout/early-exit只清理 own PID/process；no `pkill`。
- Run all checks in `ACCEPTANCE_CONTRACT`，inspect final diff，commit scoped changes形成 clean HEAD，寫 `execution.md`；交給 Stage 05，不寫 `result.md`。

### `WAVE-04 [CORE, STAGE 05 ONLY]` — Browser exact-audio E2E

- Stage 04 Implementer不可執行。Fresh Verifier依 plan `CM-04` 真正操作 Browser、sidecar監控、建立9 anchors、Documents全頁QA。

### `WAVE-05 [CORE, STAGE 05 ONLY]` — 9527 rollout

- 只有 WAVE-04 PASS才執行；依 plan `CM-05` ownership gate自動啟動 accepted SHA，health + Browser smoke後才寫 `result.md`。

## ACCEPTANCE_CONTRACT

### Stage 04 CORE（Implementer 必須實際觀察）

- Fail-first focused suite在 script修改前以正確原因 red；修改後同一 suite green。
- mismatch/dirty/unwritable data/ambiguous model任一發生時，UI未 ready、API/browser upload未發生、owned child終止、verdict FAIL。
- `completed + summary_failed=true`、fallback header/OOXML、wrong uploaded SHA、changed model、缺失/超界 metrics全部 FAIL。
- API mode與Browser mode共用同一 task/formal-document validation，不得有一邊較寬鬆。
- `--smoke --dry-run`不建目錄/不啟動；actual smoke使用 free port、exact HEAD、gitignored/private runtime，結束後 child不存在。
- launcher `bash -n`通過；exact clean revision注入並解析 health match後才 ready；unwritable DATA_DIR與mismatch明確 fail；無 broad process kill。
- Revision 2 regression command：
  `uv run pytest -q tests/test_wave01_merge_budget_separation.py tests/test_wave01_recovery_sequence.py tests/test_wave01_merge_convergence.py tests/test_wave01_overlap_provenance.py tests/test_t20260827_regression.py`。
- 完整 `uv run pytest tests/ -q`（依repo慣例需排除hardware-direct test時明列）；任何 failure分類，不 rerun-until-green。
- `git diff --check`與final diff只含 approved runner/launcher/tests/Stage04 artifacts；無 backend/frontend/dependency/lockfile/API schema變更。
- Stage 04 implementation/evidence commit後 worktree clean；`execution.md`清楚寫「READY_FOR_STAGE_05，尚未證明 primary outcome」。

### Stage 05 CORE（不可由 Stage 04 或 API smoke 冒充）

- Browser local/general exact-audio upload journey真正執行；source/server SHA皆為 `5ffba7...6683d0`且只有一個task。
- health/HEAD/clean revision一致；run前後唯一 model key/instance/context一致；fresh DATA_DIR/ASR。
- task `completed + summary_failed=false`；UI failure banner不可見；Browser點擊transcript與DOCX下載。
- formal filename/title/OOXML/general四節非空；無 fallback/error/traceback；metrics bounded且無 `max_tokens=1`/hard truncation/nonconvergence。
- 先 transcript後DOCX的開頭/中段/尾段各3 anchors具代表性覆蓋；決議/待辦存在；無unsupported material facts。
- Documents逐頁render/inspect全部頁面，無clipping/overlap/亂碼/缺字/非預期空白頁。
- PASS後才做9527 ownership check/accepted SHA rollout/health exact match/Browser smoke；unknown ownership不kill。
- tracked evidence redacted/append-only；raw sensitive artifacts只在gitignored runtime。全部通過後Stage05才寫`result.md`。

## STOP_AND_ESCALATE_IF

- plan SHA/revision與handoff不符，或harness/role prompt要求的freshness不成立。
- 工作樹有來源不明dirty changes，或需要覆寫使用者工作。
- fail-first無法以approved behavior建立，或新證據推翻`RC-3A`～`RC-3D`。
- 需要觸碰`DO_NOT_TOUCH`、改HTTP schema/task state/fallback/success/error/model-selection/readiness/retry/merge/token語意。
- 需要新增dependency/lockfile/database/schema/cross-repo change。
- runner Browser mode只能靠新增production endpoint或修改frontend才能取得task；先回Planner，不自行擴scope。
- Stage04 smoke需要修改LM Studio inventory，或process ownership無法證明。
- Stage05 exact current-head E2E產生`summary_failed=true`、empty content、merge nonconvergence、semantic/visual material failure：保存精確evidence，建立Revision4 replan；Verifier不修product。
- Browser local-file capability或Documents renderer不可用：environment blocker；不得以API/OOXML-only宣稱PASS。
- 9527已有ownership不明listener：保留isolated E2E結果但停止rollout，不kill。

## HISTORICAL_TASK_DEPENDENCIES

NONE。Revision 2 implementation/review/stage04 report位於同一TASK_ID，僅作verified predecessor evidence；Revision 3執行權威是current `plan.md`與本handoff，不需載入其他task。

---

TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary
HANDOFF_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/handoff.md
PLAN_REVISION: 3
STATUS: READY_FOR_IMPLEMENTATION
NEXT_STAGE: 04_IMPLEMENT
