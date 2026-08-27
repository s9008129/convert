# Handoff Stage 05 — 最新音檔空摘要：Browser true E2E 驗收與 9527 rollout

> **本文件是 T20260827-1127-01-lmstudio-e2e-empty-summary 的 Stage 05 執行權威（STATUS: READY_FOR_VERIFICATION）。**
> 前手 `.agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/handoff.md`（Stage 04, READY_FOR_IMPLEMENTATION）為 predecessor evidence；Stage 05 fresh verifier 以**本文件**為 current handoff。
> 編譯依據：Revision 3 plan（SHA-256 `d76e236204e53a298741f02e012a3d96e7de12cb89be072c77cdc0a9b9d7dafd`）、Stage 04 `execution.md`（scoped commit `91af3d2b`）、plan `CM-04`/`CM-05`。未經 Planner 不得修改本 handoff。

## EXECUTOR_PROMPT

你是新的 **Stage 05 Independent Verifier**，在 fresh session 執行真實 Browser E2E 驗收。你的目標不是再修任何程式碼，而是回答一個問題：

> **current HEAD 對最新音檔，是否真的能透過網頁 UI 產出非 fallback、忠實完整、可下載可讀的正式「會議紀錄」DOCX？**

嚴格規則：

1. `cd /Users/hsiaojohnny/dev/convert`，讀 `/Users/hsiaojohnny/.codex/prompts/05_e2e_test_prompt.md`、本 handoff 全文、`MUST_READ_PLAN` 指定章節、`ui-accessibility.md` policy。
2. 驗證 `plan.md` SHA-256 = `d76e236204e53a298741f02e012a3d96e7de12cb89be072c77cdc0a9b9d7dafd`、`PLAN_REVISION: 3`；mismatch 立即 BLOCKED。
3. `git status --short --branch` 必須 **clean**；記下 `git rev-parse HEAD`（這就是本次 accepted candidate revision）。若 worktree dirty，停止回報，不要 stash/reset。
4. **絕對禁止修改** product code（backend/frontend/scripts/設定/依賴）。Verifier 只能：執行 runner、操作 Browser、讀 log/state、寫 evidence。任何 product 修復需求 → 保存證據 → 走 anomaly routing。
5. 先啟動 runner Browser mode（背景），等到 stdout 出現 `BROWSER_E2E_READY` 才開始 Browser 操作；runner 負責所有 gate 與判定，你負責真實 UI journey 與 sidecar 監控。
6. **必須用真實 Browser 完成上傳與下載**（開首頁 → 選 local → general → 選擇 `/Users/hsiaojohnny/Downloads/盤點工具討論.m4a` → 上傳 → 看排隊/進度 → 等結果 → 確認無 failure banner → 點擊下載逐字稿與 DOCX）。API/log 只能 sidecar 監控與 QA 取樣，不可冒充 user journey。若 Browser runtime 不支援 local file 選擇/上傳 → environment blocker，記 BLOCKED，不得用 API 冒充。
7. task 完成後**先讀 transcript** 建 9 個語意錨點（B1-B3/M1-M3/E1-E3，依內容位置），**之後才讀 DOCX**，避免反向挑錨。再用 Documents skill `render_docx.py` 逐頁 QA 全部頁面。
8. 全部 PASS 才做 WAVE-05 rollout（9527 切換），最後才寫 `result.md`。任何 CORE failure：保存精確證據 → `e2e_report.md` 判 `PLANNER_REPLAN_REQUIRED`（product defect）→ **不得即席修 product**。
9. tracked evidence 只放 redacted metadata/hash；完整 transcript/DOCX/backend log/audio 只留 `data/cache/` 等 gitignored runtime path。時間戳一律台北時間。

## TASK

- TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary
- STATUS: READY_FOR_VERIFICATION
- PLAN_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/plan.md
- PLAN_REVISION: 3
- PLAN_SHA256: d76e236204e53a298741f02e012a3d96e7de12cb89be072c77cdc0a9b9d7dafd
- REVIEW_REQUIRED: NO（Revision 3 免 Review）
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: OWNED_PROCESS_BROWSER_UI_TRUE_E2E + SIDECAR_RUNTIME_MONITORING + DOCX_SEMANTIC_AND_FULL_PAGE_QA + OWNED_LOCAL_9527_ROLLOUT_SMOKE
- STAGE_05_VERIFIER_PROMPT: /Users/hsiaojohnny/.codex/prompts/05_e2e_test_prompt.md
- PREDECESSOR: Stage 04 execution.md（READY_FOR_STAGE_05；完整套件 549 passed / 2 skipped / 0 failed）

## GOAL_ANCHOR

- **PRIMARY_OUTCOME：** 用 Browser 真正上傳 `/Users/hsiaojohnny/Downloads/盤點工具討論.m4a`，在 exact clean revision/fresh DATA_DIR/唯一 LM Studio instance 上取得非 fallback、忠實完整、可讀的正式會議紀錄 DOCX。
- **SUCCESS_EVIDENCE：** source/server audio SHA 同為 `5ffba7448c6846e56b358113c7ed4525507480ece9b031c5281435f59c6683d0`；只有一個 task；task `completed + summary_failed=false`；UI 無 failure banner；正式 filename/title/sections；9 個 transcript-first semantic anchors；DOCX 全頁 QA 通過；metrics bounded。
- **MUST_NOT_BREAK：** fallback 產品語意、HTTP schema、模型選擇/lifecycle、Ollama/Gemini/ASR、使用者 data 與歷史 evidence 不變；raw sensitive artifacts 不進 Git；未知 process 不終止；不修改 LM Studio inventory。
- **OPERATIONAL FINISH：** E2E PASS 後才把本機 9527 切換到同一 accepted SHA 並做 health + Browser smoke。

## CRITICAL_PATH

1. `WAVE-04 [CORE]`：runner Browser mode 啟動 owned backend（exact HEAD、fresh DATA_DIR、free port）→ `BROWSER_E2E_READY` → 真實 Browser UI 上傳 exact 音檔 → sidecar 監控 → task `completed + summary_failed=false` → 正式 DOCX 驗證 → 9 anchors + Documents 全頁 QA → verdict。
2. `WAVE-05 [CORE, 僅 WAVE-04 PASS 後]`：9527 ownership 檢查 → 以 accepted SHA + `DATA_DIR=/Users/hsiaojohnny/dev/convert/data` 啟動 canonical launcher → health exact revision → Browser UI smoke（不再上傳昂貴音檔）→ 寫 `result.md`。

## SEMANTIC_INVARIANTS

1. `completed + summary_failed=true` 產品上仍是安全的 transcript fallback；E2E 必須把它判 **FAIL**（這是本次修復的核心驗收點）。
2. revision/dirty/model/data/hash gates 只保護 acceptance decision validity，不得變成一般 `/api/health` 或產品 upload 的 global gate。
3. Browser 必須實際操作 UI；API/log 只可 sidecar monitor/download/check。
4. generation success 要求非空 final content；reasoning 不得出現在 DOCX/evidence。
5. correction、paragraphization、overlap enrichment 是 BEST_EFFORT；個別失敗局部降級，不單獨 veto 正式紀錄成功。
6. 只有 WAVE-04 fresh exact-input E2E 可裁決 current product premise；不得拿舊 stale-process DOCX 當證據。
7. Verifier 不修 product code。`summary_failed=true`、empty content、merge nonconvergence、semantic/visual material failure → 保存證據 → Revision 4 replan。
8. tracked attempt 只有 redacted evidence/hash；raw 檔案只在 gitignored runtime。

## BEST_EFFORT_DO_NOT_GATE

- LLM 同音／專有名詞 correction、paragraphization、overlap enrichment 的細部品質（除非造成 formal record 的 material semantic error）。
- transcript 自然口語瑕疵（非 material）。
- 一般 product health 的 unknown build metadata（只有 Stage 05/rollout 要求 exact revision）。

## DEFERRED_NOT_THIS_TASK

- 修改 summarization/correction/chunk/merge/retry/token/prompt/model-selection 演算法。
- 刪除 fallback、改變 task status/public HTTP/frontend contract。
- 更換/載入/卸載 LM Studio model、thinking-disable。
- 遠端 production/CI E2E、dependency/lockfile、跨 repo 變更。

## REPO_ANCHOR

- Project root: /Users/hsiaojohnny/dev/convert
- Branch: main；Stage 04 packaging commit：`91af3d2b9298d349f37c89a18f7cb5045d35c094`（runner +887、launcher +94、tests +1264、rev3-* 證據）
- Worktree 狀態（Stage 04 結束時）：**clean**；本 handoff 落檔若產生新 docs commit，**accepted revision 一律以 E2E 啟動當下 `git rev-parse HEAD` 為準**（runner 會自動 derive 並做 exact-match gate）
- Runner 入口：`scripts/e2e/run_owned_e2e.py`（`--upload-mode browser`、`--runtime-dir`、`BROWSER_E2E_READY`、append-only attempt 目錄）

## CURRENT_STATE_DELTA

- Stage 04 已完成驗收器強化：runner 的 false-PASS（`summary_failed=true`/fallback DOCX 照樣 PASS）已修為 FAIL；mismatch/dirty/無效 DATA_DIR 已 fail-closed（不啟動、不上傳、verdict FAIL）；launcher 已提供可歸因 revision/DATA_DIR/health provenance。
- **runner 的 Browser mode（`BROWSER_E2E_READY` → UI 上傳 → bounded log 解析）尚未被真實 Browser 執行過**；若發現 verifier/harness 缺陷，修 verifier 並開新 attempt，不得誤報 product defect。
- 最新使用者失敗 task `c218e432` 命中 09:26 stale pre-fix backend；current HEAD 對最新音檔 **尚未被驗收**——本次 E2E 就是裁決。
- Planning 時 9527 無 listener；LM Studio 唯一 `qwen3.6-35b-a3b-mlx`（ctx 183296，另有 2 個 embedding model 會被正確排除）。皆為 mutable facts，啟動時重驗。

## MUST_READ_PLAN

- `META`、`OWNER_CHECK`
- `GOAL_CONTRACT`：`REQ-CORE-01`～`REQ-CORE-08`、`MUST_NOT_BREAK`、`NON_GOALS`
- `EXPECTED_VS_OBSERVED`、`ROOT_CAUSE`：`RC-3A`～`RC-3D`
- `GLOBAL_GATES_AND_RATIONALE`
- `CRITICAL_PATH`
- `CHANGE_MAP`：`CM-04`、`CM-05`（Stage 05 執行契約）
- `IMPLEMENTATION_WAVES`：`WAVE-04`、`WAVE-05`
- `REGRESSION_AND_ACCEPTANCE`（Stage 05 段）、`DEGRADATION_AND_GATE_TESTS`
- `DEFINITION_OF_DONE`：`DoD-05`、`DoD-09`
- `FAILURE_ROUTING`、`HANDOFF_HINTS`

## SETTLED_DO_NOT_REOPEN

- `RC-3A`：舊 DOCX 失敗源於 stale runtime，不再從它推導 product patch。
- `RC-3B`：runner success predicate 必須拒絕 `summary_failed=true` 與 fallback 文件（已實作，本次驗證）。
- `RC-3C`：launcher 必須提供 revision/DATA_DIR/health provenance（已實作，本次驗證）。
- `RC-3D`：current product outcome 未知，只有本次 exact Browser E2E 可裁決。
- `DEC-BROWSER`/`DEC-EVIDENCE`/`DEC-ROLLOUT`/`DEC-REVIEW`：見前手 handoff，維持不變。

## REVERIFY_ON_START（mutable facts，全部實測）

1. plan path/revision/SHA 與本 handoff 完全一致。
2. branch/HEAD/worktree **clean**；記錄 accepted candidate HEAD SHA。
3. 音檔存在且 `shasum -a 256 /Users/hsiaojohnny/Downloads/盤點工具討論.m4a` = `5ffba7448c6846e56b358113c7ed4525507480ece9b031c5281435f59c6683d0`。
4. LM Studio 可達（`http://127.0.0.1:1234`），**唯一** loaded LLM/instance（預期 `qwen3.6-35b-a3b-mlx`，ctx 183296）；不得修改 inventory。
5. 9527 listener 狀態（`lsof -i :9527` / PID file / `ps`）：E2E 本身不需 9527；rollout 前必須確認 ownership。
6. Browser capability：in-app Browser control（如 `browser:control-in-app-browser` / agent-browser skill）可開頁、可開 local file picker、可下載檔案；Documents skill 可用。

## TRIGGERED_POLICIES

- ui-accessibility.md（Stage 05 必載：實際驗收 UI interaction/state）
- testing-verification.md、debugging-recovery.md、security-privacy.md、git-change-hygiene.md

## FIRST_ACTION

1. 完成 Startup 檢查（05 prompt 1-7 步 + 本 handoff REVERIFY_ON_START）。
2. 建立 attempt 目錄：`.agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/e2e/attempt-01/`（verifier report/QA 用；runner 的 artifacts 目錄用其子路徑 `e2e/attempt-01/runner/`，**由 runner 自建，勿預先建立**——append-only 已存在即拒絕）。
3. 背景啟動 runner（stdout/stderr tee 到 gitignored runtime log，例如 `data/cache/e2e/attempt-01-runner-console.log`）：

```bash
cd /Users/hsiaojohnny/dev/convert
uv run python scripts/e2e/run_owned_e2e.py \
  --audio "/Users/hsiaojohnny/Downloads/盤點工具討論.m4a" \
  --upload-mode browser \
  --artifacts-dir .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/e2e/attempt-01/runner \
  --runtime-dir data/cache/e2e/attempt-01 \
  --processing-mode local \
  --health-timeout 180 \
  --task-timeout 7200
```

4. 輪詢 runner console 直到出現 `BROWSER_E2E_READY`（含 URL/port/expected revision）。**出現之前不得開頁**；若 runner 提前 FAIL（verdict FAIL、exit 1），保存 console 與 `run_summary.json`，分類原因後依 routing 決策，不得重試掩蓋。
5. `BROWSER_E2E_READY` 後立即執行 Browser UI journey（見 WAVE-04 步驟），並每 30–60 秒 sidecar 讀 bounded log tail/task state。

## EXECUTION_WAVES

### `WAVE-04 [CORE]` — Browser exact-audio true E2E

1. Runner gates 通過（clean HEAD、audio SHA、fresh DATA_DIR、health exact revision、唯一 model）後才會 flush `BROWSER_E2E_READY`。
2. Browser journey（每步截圖/記錄 UI 狀態）：開首頁 → 選 **local** 處理 → 選 **general** 模板 → file picker 選 exact 音檔 → 上傳 → 確認排隊/進度 → 監看 WebSocket 階段（ASR → cleanup/correction → extraction → merge → final → persistence）→ result UI → **failure banner 不可見** → 點擊「下載逐字稿」與「下載 DOCX」。
3. Sidecar 監控（不貼完整 transcript/prompt/reasoning 進 tracked evidence）：fresh ASR（無 cache）、單一 task、audio SHA 一致、唯一 model/instance 前後不變、`semantic_attempts <= 2 × logical_generations`、merge rounds <= 3、無 `max_tokens=1`/hard truncation/nonconvergence/fallback markers。
4. task 終態後：**先**讀新 transcript（runner sidecar 下載副本 + Browser 下載兩者都要存在；sidecar 副本供 deterministic QA，不能代替 Browser 點擊），依內容建立 `B1-B3/M1-M3/E1-E3` 九個錨點（開頭/中段/尾段各 3），先存 hash + redacted description。決議與行動項必須存在；對人名/日期/數字/決議做 source-backed 抽查；任何 unsupported material fact = FAIL。
5. 之後讀 DOCX：formal filename/title、OOXML（`PK\x03\x04`）、general 四節非空、無 fallback/error/traceback；runner 的機械驗證 verdict PASS 後，再用 Documents skill `render_docx.py` **逐頁檢查全部頁面**（無 clipping/overlap/亂碼/缺字/非預期空白頁）。
6. 核對 runner `run_summary.json`：`verdict=PASS`、`task_completed`、`summary_failed=false`、stored-bytes SHA == 音檔 SHA、start/end model snapshot 一致。

### `WAVE-05 [CORE, operational]` — 9527 rollout（僅 WAVE-04 PASS）

1. Ownership check：`lsof -i :9527`、PID file、`ps`/cwd/command。planning 時無 listener；若有 **ownership 不明** listener → 停止 rollout，保留 E2E 結果，請使用者決定，**不得 kill**。
2. 以 accepted SHA（= WAVE-04 實際 health/HEAD 一致的 SHA）啟動：`MEETINGSCRIBE_PORT=9527 DATA_DIR=/Users/hsiaojohnny/dev/convert/data scripts/macos/start-mac-native.sh`（背景；記錄 PID）。
3. Health 200 且 `build_revision == accepted SHA`；Browser 開 9527 首頁 smoke（頁面載入、local/general 控件可用、file picker 可開、**不再上傳昂貴音檔**）。
4. 保留 `data/uploads`、`data/outputs`、`data/logs`、cache；不清理不覆寫。rollback 只終止本次自己啟動的 process。

## ACCEPTANCE_CONTRACT

### CORE（全部必須實際觀察，不得冒充）

- `BROWSER_E2E_READY` 前所有 gate 實際執行（mismatch/dirty 情境已在 Stage 04 測試鎖定，E2E 當下應為 clean/exact）。
- Browser 真實完成上傳 journey；source/server SHA 皆為 `5ffba744…6683d0`；只有一個 task。
- task `completed + summary_failed=false`；UI 無 failure banner；兩個下載按鈕都被 Browser 點擊。
- 正式 DOCX：formal filename/title、OOXML 正常、general 四節非空、無 fallback/error/traceback；9 anchors 全數命中；決議/待辦存在；無 unsupported material facts。
- Documents 逐頁 render 全部頁面 PASS；metrics bounded（無 `max_tokens=1`/truncation/nonconvergence）。
- PASS 後才 rollout：health exact match + Browser smoke；unknown ownership 不 kill。
- tracked evidence redacted/append-only；raw 只在 gitignored runtime。

### 必產 artifacts

- `.agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/e2e/attempt-01/e2e_report.md`（依 05 prompt 的 Required report 範本：RUN_METADATA/GOAL_ALIGNMENT_CHECK/ACCEPTANCE_CONTRACT/CORE_CRITICAL_PATH_RESULTS/DEGRADATION_AND_GATE_RESULTS/TEST_MATRIX/EXECUTION_SUMMARY/ANOMALIES/REGRESSION_RESULTS/ROUTING_DECISION/RESIDUAL_RISK/FINAL_STATUS/NEXT_ACTION/REPORT_PATH）
- `e2e/attempt-01/runner/`：runner 產生的 redacted evidence（由 runner 寫入）
- PASS 時才寫 `result.md`（final revision、acceptance report path、簡短結論、residual risk）

## STOP_AND_ESCALATE_IF

- plan SHA/revision 與本 handoff 不符，或 worktree dirty 有來源不明變更 → BLOCKED，不修復合約。
- Browser 不支援 local file 上傳/下載，或 Documents renderer 不可用 → environment blocker（BLOCKED），不得以 API/OOXML-only 宣稱 PASS。
- runner Browser mode 無法取得 task（需新增 production endpoint/改 frontend）→ 保存證據，回報 Planner，不自行擴 scope。
- E2E 產生 `summary_failed=true`、empty content、merge nonconvergence、semantic/visual material failure → 保存精確證據（task/log/metrics/model/revision/audio hash + first bad boundary）→ `PLANNER_REPLAN_REQUIRED` → 建 Revision 4 replan；**不修 product**。
- LM Studio 不可達、inventory 變動（≠ 唯一 qwen3.6-35b-a3b-mlx）或需要修改 inventory → 停止回報，不得自行載入/卸載 model。
- 9527 ownership 不明 listener → 保留 E2E 結果，停止 rollout，不 kill。
- 驗收期間 LM Studio context/instance 變動 → 記為 model gate FAIL（屬 acceptance decision validity）。

## HISTORICAL_TASK_DEPENDENCIES

本 TASK_ID 內：Revision 3 plan + Stage 04 handoff/execution.md 為 predecessor evidence（`evidence/rev3-wave01..03b/`）。不需載入其他 task。

---

TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary
HANDOFF_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/handoff-stage05.md
PLAN_REVISION: 3
STATUS: READY_FOR_VERIFICATION
NEXT_STAGE: 05_E2E_VERIFY