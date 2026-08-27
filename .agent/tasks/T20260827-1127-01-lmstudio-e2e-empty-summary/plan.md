# 最新音檔空摘要、Stale Runtime 與模型代理 E2E 修復計畫 — Escalation Replan

## META

- `TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary`
- `PLAN_REVISION: 3`
- `PLAN_STATUS: READY_FOR_IMPLEMENTATION`
- `DEBUG_STATUS: READY_FOR_IMPLEMENTATION`
- `FIX_TYPE: MIXED`
- `TASK_MODE: ESCALATION_REPLAN`
- `TASK_CLASS: CRITICAL`
- `REVIEW_REQUIRED: NO`
- `REVIEW_WAIVER: 使用者於 2026-08-27 明確指示本次計畫不做 Review，批准 Revision 3 後直接進入 Handoff`
- `INDEPENDENT_ACCEPTANCE_REQUIRED: YES`
- `E2E_REQUIRED: YES`
- `ACCEPTANCE_MODE: FAIL_FIRST_ACCEPTANCE_HARNESS + OWNED_PROCESS_BROWSER_UI_TRUE_E2E + SIDECAR_RUNTIME_MONITORING + DOCX_SEMANTIC_AND_FULL_PAGE_QA + OWNED_LOCAL_9527_ROLLOUT_SMOKE`
- `NEXT_STAGE: 03_HANDOFF`
- `BRANCH: main`
- `ANCHOR_HEAD: ad37146ff599f960b930889cf07b28f3cee8e0fb`
- `WORKING_TREE_AT_REPLAN_TIME: CLEAN; main ahead of origin/main by 18 commits`
- `ENVIRONMENT: Apple Silicon; MLX ASR; LM Studio 127.0.0.1:1234; one loaded qwen3.6-35b-a3b-mlx LLM instance with context_length 183296; no listener on 9527 at planning time`
- `CREATED_AT: 2026-08-27T11:27:42+08:00`
- `REVISED_AT: 2026-08-27T18:51:28+08:00`
- `SUPERSEDES: PLAN_REVISION 2`
- `PREDECESSOR_IMPLEMENTATION: Revision 2 Stage 04 completed at ad37146; focused baseline 33 passed; recorded full suite 517 passed / 2 skipped / 0 failed; primary outcome still unproven by independent true E2E`
- `STALE_ARTIFACTS: review/attempt-02 and the Revision 2 handoff authorize only Revision 2; Revision 3 has an explicit owner Review waiver and MUST use a newly compiled handoff`

## OWNER_CHECK

### Plain-language owner view

- **主要目標：** 讓模型真正代理人類操作系統，使用使用者最新提供的 `/Users/hsiaojohnny/Downloads/盤點工具討論.m4a` 完成一次受控、可監看的全新 UI 上傳，最後取得可正式使用的「會議紀錄」DOCX，而不是只看失敗 DOCX 的表面結果。
- **真正必要的工作：** 證明執行中的 backend 就是待驗收 Git revision；證明 UI 上傳的位元組就是指定音檔；把 `summary_failed=true`、fallback 檔名與 fallback DOCX 一律判為 E2E FAIL；逐階段監看 ASR、校正、摘要、merge 與最終輸出；做內容與全頁視覺驗收。
- **本輪先不做的事：** 在 current HEAD 尚未用這支音檔、fresh process、fresh DATA_DIR 失敗以前，不再修改摘要 prompt、token budget、retry、chunk/merge 或模型選擇演算法。最新人工失敗命中了舊 process，不能當成 current HEAD 的失敗證據。
- **最佳努力項目：** 同音字校正、paragraphization、overlap enrichment 本來就可以局部降級；其失敗不得把正式摘要錯判為失敗，亦不得被拿來掩蓋正式摘要真的失敗。
- **可以阻擋驗收的條件與理由：** revision/dirty state 不可證明、唯一模型 inventory 不成立、DATA_DIR 不可寫、UI 未真正上傳指定音檔、`summary_failed=true`、fallback DOCX、監控證據不足以判定執行邊界、內容失真或版面不可用。這些都會使「已修復」判定失去正確性。
- **最大殘餘風險：** current HEAD 可能仍會在這支 86.95 分鐘音檔上產生 reasoning-only empty content；只有新的 Browser UI E2E 能判定。若發生，保存精確 telemetry 並重新規劃產品修復，不允許低階實作者臨場擴張範圍。

## GOAL_CONTRACT

### PRIMARY_OUTCOME

使用 `/Users/hsiaojohnny/Downloads/盤點工具討論.m4a`，由 Stage 05 的新鮮模型代理透過真實網頁 UI 選擇本地處理與 general 會議模板、實際上傳檔案，經 owned current-revision backend、fresh isolated writable DATA_DIR、MLX ASR 與啟動時唯一選定的 LM Studio instance，產出非 fallback、內容忠實、結構完整、可下載且版面可讀的正式「會議紀錄」DOCX；通過後自動把本機 9527 切換到同一核准 revision。

### SUCCESS_EVIDENCE

- `REQ-CORE-01`：E2E 啟動並只管理自己的 backend child；Git HEAD、clean worktree、health `build_revision` 三者完全一致，任何 mismatch 在 UI ready／API upload 前立即停止。
- `REQ-CORE-02`：Browser 實際開啟 owned backend 首頁、選擇 local + general、以 file input 上傳指定音檔並觀看 WebSocket 進度；API 僅作 sidecar 監控，不可取代 UI journey。
- `REQ-CORE-03`：來源音檔與 isolated DATA_DIR 中實際上傳檔案的 SHA-256 都是 `5ffba7448c6846e56b358113c7ed4525507480ece9b031c5281435f59c6683d0`，且本次只有一個新 task。
- `REQ-CORE-04`：task 終態為 `completed` 且 `summary_failed=false`；UI 不顯示 `summaryFailedBanner`；下載檔名為正式 `會議紀錄`，不含 `逐字稿(會議紀錄生成失敗)`。
- `REQ-CORE-05`：DOCX/OOXML 不含 fallback title、warning、traceback 或空摘要錯誤；general 模板必要段落 `一、報告事項`、`二、討論事項`、`決議`、`三、主席裁示事項` 均有實質內容。
- `REQ-CORE-06`：在先讀逐字稿、尚未讀 DOCX 前，從逐字稿開頭／中段／尾段各建立 3 個語意錨點；正式 DOCX 必須覆蓋具代表性的 9 個錨點，尤其包含明確決議／待辦，且不得虛構逐字稿未支持的人名、日期、數字或決議。
- `REQ-CORE-07`：Documents render-and-verify 檢查 DOCX 全部頁面；不得有 clipping、overlap、亂碼、缺字、非預期空白頁或不可讀版面。
- `REQ-CORE-08`：Stage 05 PASS 後，先重新確認 9527 listener/PID/cwd/command ownership，再以同一核准 SHA 與 `DATA_DIR=/Users/hsiaojohnny/dev/convert/data` 啟動本機服務；health revision 完全一致並通過 Browser UI smoke。
- `REQ-SUP-01`：保存可稽核但不洩漏完整敏感內容的 evidence：revision、hash、model/instance snapshots、task verdict、redacted metrics、semantic anchor 判定與頁面 QA 結果；完整 transcript、DOCX、backend log 與 uploaded bytes 留在 gitignored runtime data。

### MUST_NOT_BREAK

- 不硬編碼、載入、卸載、切換或替換 LM Studio 模型；維持 zero/one/multiple/optional exact override 選模契約與啟動後 immutable selection。
- 不改變 `TaskStatus.COMPLETED + summary_failed=true` 作為「來源逐字稿已安全保存但摘要降級」的產品語意；只修正 E2E acceptance 不得把它判為正式會議紀錄成功。
- 保留 Ollama、Gemini、ASR、transcript fallback、下載路徑與既有 HTTP schema；本 revision 不新增 HTTP 欄位、不變更 public API。
- 不新增第三方依賴、database/schema/backfill、模型 lifecycle、跨 repository 耦合或 production readiness generation probe。
- 不在 Git 中新增原始音檔、完整逐字稿、完整 DOCX、完整 backend log、模型 reasoning/prompt 或其他敏感 payload。
- 不終止 ownership 不明的 process；只停止本輪明確啟動且 PID/command 可證明的 process。
- 保留使用者既有 `data/uploads`、`data/outputs`、`data/logs`、cache 與歷史 E2E evidence；append-only，不覆寫舊 attempt。

### NON_GOALS

- 不在真實 current-revision E2E 失敗前調整 summarization service、prompt、token/retry/merge/chunk/cleanup 演算法。
- 不把 fallback 產品路徑刪除或把摘要失敗改為整個 task `failed`。
- 不要求所有同音字、說話者、自然口語或專有名詞自動修正完美。
- 不重新跑舊的 `/Users/hsiaojohnny/Downloads/0818-優規需求確認會議.m4a` 作為本次主要驗收；本次唯一 primary input 是 `盤點工具討論.m4a`。
- 不部署遠端 production、不 push、不建立 PR、不管理 LM Studio inventory。

## EXPECTED_VS_OBSERVED

### Expected

最新手動上傳應命中包含 Revision 2 修復的 current backend，在 fresh/current runtime 完成 MLX ASR、bounded correction、extraction/merge/final generation，輸出正式會議紀錄；驗收器必須能區分正式摘要與 transcript fallback。

### Observed — latest user manual upload

- 使用者來源音檔：`/Users/hsiaojohnny/Downloads/盤點工具討論.m4a`；44,773,357 bytes；AAC mono 48 kHz；duration 5,216.917333 秒；SHA-256 `5ffba7448c6846e56b358113c7ed4525507480ece9b031c5281435f59c6683d0`。
- 系統實際 upload：`data/uploads/29767e54d905.m4a`，SHA-256 完全相同，排除「人工提供檔與系統實際處理檔不同」。
- task ID：`c218e432`；16:31:13 接受，16:44:51 ASR 成功並快取逐字稿，17:00:46 開始 formal summary，17:01:18 首個 extraction 產生空結果後失敗。
- 失敗 DOCX：`/Users/hsiaojohnny/Downloads/20260827163113_逐字稿(會議紀錄生成失敗).docx`；SHA-256 `69e4072c731a3cfd482b9ca382b6203b7466e8bb8734971cfe9251f113f00d63`，與 `data/outputs/盤點工具討論_c218e432.docx` 完全相同。
- DOCX exact error：`RuntimeError: 摘要生成失敗：結果為空`。Documents skill 已 render 並逐頁檢查全部 17 頁：版面本身乾淨，但內容只有 fallback transcript，沒有隱藏的正式會議紀錄。
- 該 runtime 於 09:26 啟動；使用者 16:31 上傳。它早於 12:28 的 `96e6e74`、15:17 的 `b8a446d`、16:11 的 `a692dff`、16:14 的 `5be217c` 與 16:23 的 `ad37146`。traceback 指向舊 `_summarize_with_lmstudio` line 1755，該舊版遇到空 content 直接 raise；current code 的 bounded state machine 位於後續約 line 1975 起。
- 舊 runtime 在 correction 對 69 段做大量 LM Studio 呼叫但 0 段修正；formal context plan 為 `context_window=8192, estimated_tokens=21482, chunk_budget=3112, merge_budget=900, needs_chunking=True`，首個 extraction `max_tokens=2066` 回傳空 content。

### Observed — current repository and acceptance tooling

- Revision 2 focused baseline 以隔離 writable DATA_DIR 實跑：`33 passed, 2 warnings`；Stage 04 報告記錄完整 suite `517 passed / 2 skipped / 0 failed`。這些證明已實作契約，但不是最新音檔的真實 E2E 成功證據。
- `backend/services/task_processor.py` 在 summary exception 時設定 `summary_failed=true`，仍呼叫 `complete_task(..., success=True)`，因此 task 合法終態是 `completed`；這是 transcript fallback 的既有安全契約。
- `scripts/e2e/run_owned_e2e.py` 目前 full verdict 只要求 `task_completed`、`transcript_downloaded`、`docx_downloaded`，沒有拒絕 `summary_failed=true`、fallback filename 或 fallback OOXML，故可對這次失敗產物 false-PASS。
- runner 記錄 revision mismatch，卻仍可進入完整 upload；昂貴 E2E 沒有在 freshness 失效時 fail closed。
- `scripts/macos/start-mac-native.sh` 沒有注入 `MEETINGSCRIBE_BUILD_REVISION`，也沒有解析 health revision；重啟後 health 可能為 null，無法證明 9527 跑的是哪個 Git SHA。
- current shell 繼承 `DATA_DIR=/app/data` 時，focused pytest collection 曾因 `/app` 唯讀失敗；改用 `/private/tmp` isolated DATA_DIR 後 33 tests 通過。最新人工失敗使用 repo data，故 `/app` 不是該次根因，但 launcher/E2E 必須顯式驗證 writable DATA_DIR。
- planning time 9527 沒有 listener；LM Studio 目前只有一個 loaded LLM model/instance `qwen3.6-35b-a3b-mlx`，context length 183,296。

## SYMPTOM_SIGNATURE

- **表面錯誤：** DOCX 顯示「逐字稿（會議紀錄生成失敗）」及 `摘要生成失敗：結果為空`。
- **直接機制：** 09:26 啟動的 stale pre-fix process 在 LM Studio completed response 沒有 final content 時走舊版直接 raise 路徑。
- **驗收缺陷：** task fallback 仍是 `completed` 且兩個檔案可下載；現有 runner 把「完成＋下載成功」錯當成正式摘要成功。
- **影響：** 使用者無法取得正式會議紀錄，且重複修復因 runtime provenance 與 E2E success predicate 不完整而無法判定真正修復是否生效。
- **決定性：** stale runtime 對本次產物是確定證據；current HEAD 對同一音檔是否成功仍為 `[UNKNOWN]`，必須由新的 owned Browser E2E 決定。

## SOURCE_OF_TRUTH

| Claim | Source of truth | Status |
|---|---|---|
| 使用者要驗收的音檔 | 使用者明確提供的 Downloads path + SHA-256 | `[VERIFIED]` |
| 最新 DOCX 是系統該次輸出 | user DOCX 與 data output SHA-256 完全相同 | `[VERIFIED]` |
| 該次失敗命中 stale process | process/log timestamps、commit timestamps、traceback line/body | `[CONFIRMED]` |
| fallback task 仍是 completed | current task processor、schema、routes、frontend | `[VERIFIED]` |
| current runner 會 false-PASS fallback | runner required checks 與 `run_full_e2e` 實作 | `[CONFIRMED]` |
| current HEAD 已根治最新音檔 | 尚無 same-input fresh Browser E2E | `[UNKNOWN]` |
| 正式 DOCX 內容是否忠實可用 | transcript-first semantic anchors + DOCX structural/visual QA | `Stage 05 required` |

## SYSTEM_BOUNDARY

`Fresh Git revision -> owned backend launcher -> health/provenance/model/data preflight -> Browser UI local/general selection -> browser file upload -> isolated upload bytes -> queue/WebSocket -> fresh MLX ASR -> deterministic cleanup -> BEST_EFFORT correction -> immutable LM Studio extraction/merge/final -> task completed + summary_failed flag -> result download headers/OOXML -> semantic anchors -> full-page DOCX QA -> accepted SHA rollout on 9527`

- **Last known-good in latest failed run：** Browser upload bytes、queue、MLX ASR、transcript persistence、fallback persistence/download。
- **First known-bad in latest failed run：** stale old-code LM Studio generation returned empty final content and raised at first formal extraction。
- **Current first unverified boundary：** current HEAD on this exact audio through extraction/merge/final generation。
- **Acceptance gate boundary：** product `completed` means processing/fallback persisted; acceptance success additionally requires `summary_failed=false` and formal document evidence。
- **External dependency：** local LM Studio service and current loaded model inventory; verifier is read-only and may not modify it。

## SEMANTIC_CONTRACT_AUDIT

- `TaskStatus.COMPLETED + summary_failed=true` remains a valid **product degradation state** because the transcript was preserved; it is never a valid **formal meeting-record acceptance state**.
- Revision/dirty/model/DATA_DIR checks are E2E decision-validity gates, not general product readiness gates. They block a PASS claim because without them the tested build/input/model cannot be identified; they must not change `/api/health` behavior for normal users.
- Browser interaction is CORE because the user explicitly requires a model to proxy the human journey. API polling/download and log inspection are sidecar evidence only.
- Formal output requires both structural success (`summary_failed=false`, formal filename/title/sections) and semantic usability (representative source facts, decisions/actions, no unsupported facts). Either alone is insufficient.
- Existing bounded retry/merge/token behavior is settled Revision 2 product semantics. This plan verifies it but does not redesign it. If the true E2E falsifies it, route to a new plan revision.
- correction/overlap/paragraphization remain BEST_EFFORT and non-gating for product completion; their telemetry may explain quality but cannot substitute for CORE meeting-record success.
- Post-PASS 9527 rollout is a controlled operational mutation. Unknown process ownership is a stop condition; no guessed PID kill is allowed.

## DECISION_CONTRIBUTION_MATRIX

| ID / element | Classification | E2E veto? | Missing/failure behavior | Goal contribution / rationale |
|---|---|---:|---|---|
| `REQ-CORE-01` exact revision + clean tree | CORE | YES | Stop before UI ready/upload | Prevents another stale/dirty runtime from invalidating the entire acceptance decision |
| unique immutable LM Studio inventory | CORE prerequisite | YES | Stop before UI ready | Without a unique instance, model identity and Revision 2 selection contract cannot be proven |
| writable isolated DATA_DIR | CORE prerequisite | YES | Explicit preflight failure | Prevents cache contamination, source overwrite and late `/app` permission failure |
| `REQ-CORE-02/03` Browser upload + byte hash | CORE | YES | No E2E PASS | Proves the model executed the requested human journey on the exact file |
| task `summary_failed=false` | CORE | YES | Verdict FAIL; preserve fallback artifacts | Distinguishes formal meeting record from safe transcript fallback |
| formal filename/title/sections/OOXML | CORE | YES | Verdict FAIL | Prevents a downloadable fallback DOCX from masquerading as success |
| semantic anchors + no fabrication | CORE | YES | Verdict FAIL | Proves the document is useful and faithful, not merely non-empty |
| full-page DOCX visual QA | CORE usability | YES | Verdict FAIL | A clipped/garbled formal record does not satisfy the requested deliverable |
| bounded metrics/model snapshots | SUPPORTING decision evidence | YES for acceptance evidence only | Product may continue; acceptance remains unproven | User explicitly requires full monitoring; missing evidence prevents causal/revision/model validation but must not become a product gate |
| correction/paragraphization/overlap quality | BEST_EFFORT | NO | Record degradation; continue | Improves transcript quality without deciding formal summary validity |
| automatic local 9527 rollout | CORE operational finish | YES after E2E PASS | Do not switch; report blocker | User selected automatic switch only after accepted revision is proven |

## CONFIRMED_FACTS

- `FACT-01`：audio and uploaded copy SHA-256 match exactly: `5ffba7...6683d0`.
- `FACT-02`：user and system failed DOCX SHA-256 match exactly: `69e407...00d63`.
- `FACT-03`：all 17 rendered DOCX pages contain only fallback transcript; no hidden summary/layout defect explains the failure.
- `FACT-04`：latest task `c218e432` hit a process started before every applicable fix commit.
- `FACT-05`：current product intentionally allows completed fallback with `summary_failed=true` and labels UI/download accordingly.
- `FACT-06`：current runner does not include `summary_failed`, formal filename, OOXML or semantic checks in PASS requirements and does not hard-stop mismatch before upload.
- `FACT-07`：current macOS launcher does not inject/verify `MEETINGSCRIBE_BUILD_REVISION`.
- `FACT-08`：Revision 2 focused regression tests pass with isolated writable DATA_DIR; no same-input current-head E2E exists.

## UNKNOWNS

- `UNKNOWN-01`：current HEAD/implementation commit 是否可對 exact latest audio 完成非空 extraction/merge/final generation。
- `UNKNOWN-02`：Stage 05 執行時 LM Studio inventory、context length、9527 ownership 與 worktree 是否仍與 planning time 相同；必須重驗。
- `UNKNOWN-03`：Browser runtime 在 Stage 05 是否提供 local file upload 與下載存取能力；缺少必要 Browser capability 時是 environment blocker，不能改用 API 冒充 UI E2E。
- `UNKNOWN-04`：正式輸出會包含哪些具體 9 個語意錨點；為避免對 DOCX 結果反向挑題，必須在讀 DOCX 前由 fresh verifier 從新 transcript 建立。

## HYPOTHESES

### H-1 — Latest manual failure was caused by stale runtime

- **Mechanism：** pre-fix process retained old direct-empty raise behavior after source commits changed.
- **Prediction：** process timestamp precedes commits; traceback matches old source and not current state machine.
- **Result：** `[CONFIRMED]` by logs/timestamps/line-body comparison.

### H-2 — Current HEAD may still fail on the exact latest audio

- **Mechanism：** stochastic reasoning-only output, merge non-convergence, context pressure or an undiscovered product defect may survive Revision 2.
- **Prediction：** owned current-revision fresh-data E2E reaches summary fallback or stable error with current diagnostics.
- **Result：** `[UNKNOWN]`; only WAVE-04 true E2E may decide it.

### H-3 — Existing E2E runner can false-PASS the exact user-visible failure

- **Mechanism：** required checks stop at completed/downloaded and ignore product degradation markers/document semantics.
- **Prediction：** fixture with `status=completed, summary_failed=true` and downloadable fallback files returns no failure.
- **Result：** `[CONFIRMED]` statically; WAVE-01 must lock a fail-first regression.

### H-4 — Managed restart can still create an unprovable/null revision runtime

- **Mechanism：** launcher never sets build revision and only checks HTTP success.
- **Prediction：** clean managed start without inherited env reports null revision but launcher announces ready.
- **Result：** `[CONFIRMED]` statically; WAVE-01/02 must fix launcher contract.

### H-5 — Inherited/unwritable DATA_DIR can cause an environment failure unrelated to product logic

- **Mechanism：** config defaults/inherited shell point to `/app/data` on macOS, which is not writable.
- **Prediction：** preflight on a non-directory/unwritable path fails explicitly before backend/UI upload; isolated `/private/tmp` or repo data works.
- **Result：** `[SUPPORTED]`; focused pytest reproduced the environment distinction.

## FALSIFICATION_RESULTS

- Falsified “the user uploaded a different audio” by identical SHA-256.
- Falsified “the DOCX only has a visual/render bug” by OOXML extraction and all-page render review.
- Falsified “latest manual DOCX proves current HEAD fix failed” because the serving process predates current code.
- Falsified “completed + downloadable files prove meeting-record success” by explicit product fallback semantics and failed DOCX.
- Not yet falsified H-2; therefore no new product algorithm edit is authorized in Revision 3.

## ROOT_CAUSE

### RC-3A — Immediate cause of latest artifact: stale pre-fix runtime

The manual request was executed by a backend started before the fixes. Source files on disk changed, but the long-lived Python process retained old code. Missing enforceable runtime provenance allowed the user to unknowingly retest the old implementation.

### RC-3B — Acceptance-control defect: fallback is misclassified as E2E success

The product correctly persists a transcript fallback as `completed + summary_failed=true`; the E2E runner incorrectly equates `completed + downloads` with formal meeting-record success. The verifier therefore cannot detect the exact user-visible failure it exists to prevent.

### RC-3C — Launcher provenance/rollout defect

The managed macOS launcher neither derives/injects the clean Git revision nor validates health against it. A restart can still be operationally “ready” while its tested revision is null/mismatched.

### RC-3D — Product outcome on current HEAD remains undecided

The previous product fixes have test evidence but no same-input fresh Browser E2E. Treating the old process failure as a new summarization root cause would be speculation. The correct next diagnostic is a strict true E2E, not another algorithm patch.

## FIX_TYPE_AND_ENVELOPE

- `FIX_TYPE: MIXED` because this revision combines a mechanical verifier/launcher correction with a strict acceptance/operational contract, while deliberately freezing existing product summary/fallback semantics.
- **Allowed implementation files：** `scripts/e2e/run_owned_e2e.py`, `scripts/macos/start-mac-native.sh`, focused tests under `tests/`, and current task Stage 04/05 evidence artifacts owned by the proper stage.
- **Allowed behavior：** hard preflight gates within the E2E harness; browser-upload wait/monitor mode; formal result checks; redacted/append-only evidence split from gitignored raw runtime; managed launcher revision/data/health validation; owned rollout/rollback.
- **Conditional product work：** NONE in Stage 04. If WAVE-04 current-revision E2E fails in product code, Stage 05 records evidence and routes to Revision 4; it does not patch product code.

## DO_NOT_TOUCH

- `backend/services/summarization.py`, correction/chunk/merge/retry/prompt/token logic.
- `backend/services/task_processor.py` fallback status/formatting semantics.
- `backend/api/routes.py`, `backend/models/schemas.py`, `frontend/` public/UI behavior unless a new product defect is proven and replanned.
- LM Studio model inventory/config/lifecycle; Ollama/Gemini behavior; ASR decoder/model settings.
- dependencies/lockfiles, database/data schema, existing user runtime files and historical Review/E2E attempts.
- any other repository or `/Users/hsiaojohnny/dev/yt_down_txt`.

## GLOBAL_GATES_AND_RATIONALE

- **E2E revision/cleanliness gate：** global to the acceptance run because dirty/mismatched code makes the tested implementation indeterminate; local degradation cannot preserve decision validity.
- **Unique loaded model gate：** global to this local-LM E2E because the approved immutable selection contract cannot be attributed when inventory is ambiguous.
- **Exact upload hash gate：** global because testing a different file does not answer the user’s request.
- **`summary_failed=false` + formal document gate：** global to PASS because fallback is explicitly not the requested outcome.
- **Browser capability gate：** global because the user explicitly asked for model-as-human UI E2E; API-only execution is a different acceptance mode.
- **Unknown 9527 ownership gate：** global to rollout because killing/replacing an unknown process is unsafe; it does not invalidate the already completed isolated E2E evidence.

## COMPLEXITY_BUDGET

- One browser upload mode in the existing runner: necessary to let Browser execute the real UI while the runner owns/monitors backend.
- Small pure validation helpers for revision/model/task/hash/DOCX/metrics: necessary to make acceptance predicates unit-testable and prevent false-PASS.
- Evidence/runtime directory split: necessary to satisfy append-only auditability without committing sensitive raw artifacts.
- Launcher revision/data/health validation: necessary to make post-acceptance 9527 rollout attributable and repeatable.
- No new service, dependency, endpoint, database, orchestration framework or product gate.

## CRITICAL_PATH

1. `WAVE-01` 建立 fail-first verifier/launcher tests，證明 current runner 對 fallback、mismatch、wrong bytes、ambiguous inventory 與 launcher null revision 的判定不正確。
2. `WAVE-02` 最小修改現有 runner：在 UI ready/upload 前完成 clean SHA/revision/data/model hard gates；增加 Browser upload detection/monitor mode；統一 API/browser 的正式摘要、hash、filename、OOXML、metrics 與 immutable inventory checks。
3. `WAVE-03` 修改 macOS launcher：可靠注入 clean revision、顯示/驗證 actual port/DATA_DIR、解析 health revision；完成 focused/full verification，不跑真實音檔。
4. `WAVE-04` fresh Stage 05 使用 in-app Browser 對 exact latest audio 做一次 true E2E，全程 sidecar 監看，完成 transcript-first semantic anchors 與 Documents 全頁 QA。
5. `WAVE-05` 只有 WAVE-04 PASS 後，依 ownership gate 自動切換本機 9527 到核准 revision並做 Browser smoke；寫入 `result.md`。

## CHANGE_MAP

### `CM-01` Fail-first acceptance predicates — CORE

新增 `tests/test_owned_e2e_acceptance.py`（名稱可依 repo convention 微調，但不可散落到產品測試）並擴充 `tests/test_macos_scripts.py`。在修改 production scripts 前，至少鎖定：

1. health revision mismatch 必須在任何 upload function 被呼叫前結束；fixture 需斷言 upload call count 為 0。
2. `status=completed, summary_failed=true` 必須 FAIL；`summary_failed=false` 才可進入正式文件檢查。
3. `Content-Disposition` 含 fallback label、DOCX OOXML 含 `逐字稿（會議紀錄生成失敗）`／failure banner／empty-summary error，任一即 FAIL。
4. isolated upload bytes SHA 與 expected audio SHA 不同必須 FAIL；一致才通過。
5. loaded LLM model/instance 不是「恰好一個 model 且恰好一個 instance」或 run 前後 snapshot 改變，必須 FAIL。
6. DATA_DIR 是一般檔案、不可建立或不可寫時，必須在 backend 啟動前輸出明確 failure。
7. Browser mode 只接受 isolated backend log 中唯一一筆本輪 upload mapping，提取 `stored filename + task_id`；0 筆逾時或 >1 筆都 FAIL。
8. metrics parser 拒絕缺少 success metrics、`logical_generations<=0`、`semantic_attempts > 2 * logical_generations`、`merge_rounds > 3`、`max_tokens=1`、hard truncation 或 `LOCAL_LLM_MERGE_NOT_CONVERGED` 成功假象。
9. launcher 靜態/行為契約至少證明 revision derivation/injection、dirty distinction、writable DATA_DIR validation、health JSON revision match、actual port logging，且不得使用 broad `pkill`。

Fail-first evidence 必須保存首個具代表性的正確原因；如果測試因 import/fixture/環境錯誤失敗，先修測試，不得當成產品 red。

### `CM-02` Harden `scripts/e2e/run_owned_e2e.py` — CORE acceptance harness

- 保留既有 `--smoke`、API upload 與 owned-process/free-port 能力；新增明確 `--upload-mode api|browser`（default `api`）或等價單一參數，不建立第二支 runner。
- 非 smoke 均要求 `--audio`，runner 先計算 expected SHA；Browser mode 的 `--audio` 只作 expected-byte authority，runner 不得代 Browser 上傳。
- **啟動前 hard preflight：** repo 必須 clean；actual HEAD 等於 expected revision；audio 存在；evidence/runtime/DATA_DIR 可建立且可寫。任何 failure 不得啟動 backend。
- **啟動後、UI ready 前 hard preflight：** health 200 且 `build_revision == expected == HEAD`；LM Studio 可達且 loaded LLM 恰好一 model/一 instance。任何 failure 立刻只終止 owned child，不得 upload。
- Browser mode 通過 gate 後 stdout flush 一行 machine-readable `BROWSER_E2E_READY`（至少含 URL、expected SHA、evidence/runtime paths）；Stage 05 Browser 此後才可開頁上傳。
- Browser mode 透過本輪 isolated `backend.log` 的既有 upload success line，bounded poll 出唯一 `stored filename + task_id`；不得新增 public API。API mode 從 upload response 取得同兩項資訊。兩種 mode 後續共用同一 monitor/validation path。
- 從 isolated `DATA_DIR/uploads/<stored filename>` 計算實際 SHA 並與 expected 比對；只允許一個本輪 task/upload。
- task 終態要求 `completed` 且 `summary_failed is False`；缺欄位、true 或其他終態均 FAIL。
- 下載 transcript/DOCX 時保存 `Content-Disposition`；正式 DOCX label 必須是 `會議紀錄` 且不含 fallback label。
- 使用既有 `python-docx` 或 stdlib OOXML 讀取文字；拒絕 fallback title/banner/error/traceback，要求 formal title 與 general 模板四個必要 section pattern 有非空後續內容。此機械檢查不取代 Stage 05 語意/視覺 QA。
- 解析成功 run 的 structured metrics 與 diagnostics：`logical_generations > 0`、`semantic_attempts <= 2 * logical_generations`、`merge_rounds <= LOCAL_LLM_MAX_MERGE_ROUNDS(目前 3)`；不得出現 `max_tokens=1`、hard truncation、merge non-convergence；run 前後 model key/instance/context snapshot 完全一致。
- `summary_failed`/formal DOCX/upload hash/model/metrics 全部加入 full-mode `required` checks；不再只要求 completed/downloaded。
- revision mismatch 必須 raise/return before `capture_model_snapshot` 之後的 UI-ready/upload path；不可僅 append failure 後繼續昂貴工作。
- artifacts 採雙層：`.agent/tasks/<TASK_ID>/e2e/attempt-<NN>/` 自動選下一個不存在的 append-only evidence dir，只保存 hash/redacted verdict/metrics/QA manifest；完整 uploaded bytes、transcript、DOCX、backend log 與 backend DATA_DIR 放在 `data/cache/e2e/<attempt>/` 或等價 gitignored runtime dir。不得將原始敏感 payload 寫入 tracked evidence。
- exception/finally 仍只終止 runner 自己用新 process group 啟動的 child；任何 attempt 不覆寫前一 attempt。

### `CM-03` Fix `scripts/macos/start-mac-native.sh` provenance — CORE rollout support

- 在 Git 可用時，以 repo `git rev-parse HEAD` 為本機 launcher authoritative revision；以 tracked/staged/untracked status 判斷 dirty，dirty 必須顯示為可區分值並在 Stage 05 exact-SHA rollout gate 失敗，不能冒充 clean SHA。
- Git 可用時，如 caller 明示 `MEETINGSCRIBE_BUILD_REVISION` 且不同於 clean HEAD，啟動前 fail loudly；相同則保留。Git/metadata 不可用的 packaged environment 才允許 explicit revision 或 unknown/null，普通產品 startup 不因此新增 global health veto。
- 在啟動前建立並驗證實際 `DATA_DIR` 可寫；錯誤訊息列出 path，不依賴 shell inherited `/app/data` 靜默失敗。
- 啟動 log 明確列出 project root、actual host/port、DATA_DIR、build revision/dirty state。
- readiness 不只 `curl` 200：以既有 `.venv` Python 解析 `/api/health` JSON，取得 `build_revision`，在本機 Git/explicit expected revision 已知時要求完全相同後才顯示 ready。
- revision mismatch、health parse failure、timeout 或 child early exit 時，只終止本 script 剛啟動且 ownership 已知的 process/child，清除自己寫入的 PID file，不使用 `pkill` 或猜測性終止。
- 不變更 stop/restart public invocation；不安裝 dependency、不管理外部 LM runtime。

### `CM-04` Fresh-context Browser UI E2E + live monitoring — Stage 05 CORE

- 必須是新的 Stage 05 verifier context，載入 `05_e2e_test_prompt.md`、Revision 3 plan/handoff、`browser:control-in-app-browser` 與 `documents:documents`；Verifier 不修改 product code。
- 先執行 runner Browser mode，等待 `BROWSER_E2E_READY`；若 Browser skill/runtime 不支援 local file upload，記為 environment blocker，不得改用 API 並宣稱 user-journey E2E。
- Browser 真正執行：開首頁 → 明確選 local → general → 選擇 `/Users/hsiaojohnny/Downloads/盤點工具討論.m4a` → 上傳 → 確認排隊/進度 UI → 監看 WebSocket 驅動階段 → result UI → 確認 failure banner 不可見 → 點擊下載逐字稿與 DOCX。
- Sidecar 每 30–60 秒或每個 stage transition 讀取 bounded log tail/task state，記錄 ASR、cleanup/correction、extraction、merge、final/refinement、persistence；不得把完整 transcript/prompt/reasoning 貼入 tracked evidence。
- 監控檢查：fresh ASR（isolated DATA_DIR 無 cache）、一個 task、相同 audio SHA、唯一 model/instance 不變、每 logical generation completed provider calls 的測試契約上限（E2E aggregate `semantic_attempts <= 2 * logical_generations`）、merge rounds <=3、無 hard truncation/max_tokens=1/non-convergence/fallback。
- task 完成後先讀新 transcript，依內容位置建立 `B1-B3`、`M1-M3`、`E1-E3` 九個簡短語意錨點並先保存 hash/redacted description；之後才讀 DOCX，避免反向挑選容易通過的錨點。
- 每個區段至少要有代表性覆蓋；明確決議與行動項必須出現在 DOCX。對人名、日期、數字、決議做 source-backed 抽查；任何 unsupported material fact 是 FAIL。
- 使用 Documents skill canonical `render_docx.py`，逐頁檢查全部頁面；OOXML、section substance、全頁 render 三者都 PASS 才能接受。
- Browser 點擊下載是 user journey 的一部分；runner sidecar 下載副本可供 deterministic hash/OOXML/Documents QA，但不能代替 Browser 點擊。

### `CM-05` Automatic accepted-revision rollout to local 9527 — post-PASS CORE

- 只有 Stage 05 CORE verdict PASS 後執行；accepted revision 是 E2E 實際 health/HEAD 完全一致的 SHA。
- 重新執行 `lsof`/PID file/`ps`/cwd/command checks。planning time 無 9527 listener，但這是 mutable fact；如果當下有 ownership 不明 listener，停止 rollout 並請使用者決定，不得 kill。
- 如果存在本 repo managed process，使用 canonical stop script 且再次確認 target；否則直接以 `DATA_DIR=/Users/hsiaojohnny/dev/convert/data`、`MEETINGSCRIBE_PORT=9527` 與 accepted SHA 啟動 canonical macOS launcher。
- health 200 且 `build_revision == accepted SHA`；Browser 打開 9527 首頁做 UI smoke（頁面載入、local/general 控件可用、file picker 可開但不再次上傳昂貴音檔）。
- 保留 `data/uploads`、`data/outputs`、`data/logs` 與 cache，不清理、不覆寫。
- rollback：只終止 rollout 當下由本流程啟動並記錄 PID/command 的新 process。planning time 沒有 prior service，因此 rollback 後維持 stopped；不得回復一個不存在/未知的舊 process。

## IMPLEMENTATION_WAVES

### `WAVE-01 [CORE]` — Verifier/launcher fail-first evidence lock

- 只新增/修改 focused tests，先跑並保存正確 failure 原因。
- 覆蓋 `CM-01` 九類契約；不得先改 scripts 再補 fail-first 敘事。
- 第一個 red run 若混有 test defect，先修 test harness 到只剩預期行為 red。

### `WAVE-02 [CORE]` — Acceptance runner hardening

- 只修改 `scripts/e2e/run_owned_e2e.py` 與必要 focused tests。
- 完成 preflight、Browser mode、shared task/formal DOCX/hash/metrics/model checks、raw/evidence split。
- 先讓 runner tests 全綠，再做 smoke/dry-run；不跑真實音檔。

### `WAVE-03 [CORE/SUPPORTING]` — macOS launcher provenance + Stage 04 verification

- 修改 `scripts/macos/start-mac-native.sh` 與 `tests/test_macos_scripts.py`。
- focused tests、`bash -n`、runner dry-run/smoke、Revision 2 regression tests、完整 suite、final diff。
- 驗證後把 scoped implementation/evidence 形成可識別 Git commit，讓 Stage 05 能在 clean worktree 上以 exact HEAD/build revision 驗收；不得夾帶其他變更。
- Stage 04 寫 `execution.md`，不得寫 `result.md` 或宣稱 primary outcome fixed。

### `WAVE-04 [CORE]` — Independent Browser UI true E2E

- Stage 05 fresh verifier 依 `CM-04` 執行 exact latest audio 一次。
- append-only `e2e/attempt-01` 起；失敗後修 verifier/environment 再用下一 attempt，不覆寫。
- product failure 直接 `PLANNER_REPLAN`；Verifier 不改 product code。

### `WAVE-05 [CORE operational]` — Accepted SHA local rollout

- 僅在 WAVE-04 PASS 後依 `CM-05` 自動執行。
- health + Browser smoke PASS 後才由 Stage 05 寫 `result.md` 並關閉任務。

## REGRESSION_AND_ACCEPTANCE

### Stage 04 focused verification

1. 建立 isolated writable test data root，避免 inherited `/app/data` 污染測試。
2. Fail-first：`uv run pytest -q tests/test_owned_e2e_acceptance.py tests/test_macos_scripts.py`（先 red，保存正確原因）。
3. Post-fix 同一 focused command 全綠。
4. Revision 2 product regression：
   `uv run pytest -q tests/test_wave01_merge_budget_separation.py tests/test_wave01_recovery_sequence.py tests/test_wave01_merge_convergence.py tests/test_wave01_overlap_provenance.py tests/test_t20260827_regression.py`。
5. `bash -n scripts/macos/start-mac-native.sh`；runner `--help`、`--smoke --dry-run`。
6. 使用 free port、gitignored/private runtime path 做一次非昂貴 runner `--smoke`；驗證 exact revision gate 與 owned child cleanup。另以 mismatch fixture/unit test 證明 upload 不會發生，不需要實際長音檔。
7. 完整 `uv run pytest tests/ -q`（若 repo baseline 按慣例排除 hardware-direct test，必須明列 command/skip 理由）；分類任何 failure。
8. `git diff --check`、scope diff inspection；不允許 product/dependency/lockfile/HTTP schema 變更。

### Stage 05 independent acceptance

- `REQ-CORE-01` 至 `REQ-CORE-08` 全數有實際觀察證據才可 PASS。
- API-only full runner PASS、unit/full suite PASS、或下載成功都不能替代 Browser true E2E。
- Stage 05 evidence result 至少記錄：accepted SHA、clean status、audio/source/upload hashes、task ID/status/summary_failed、start/end model snapshots、redacted metrics、UI states、download header/OXML checks、9-anchor matrix、all-page QA count、9527 rollout PID/health/smoke、raw runtime paths/hashes。
- 真實音檔預期耗時可能超過一小時；Verifier 要持續監控並提供簡短進度，不因暫時無輸出自行中止。timeout 以 runner 既有 7200 秒為起點，只有觀察到 process/task stall 才分類。

## DEGRADATION_AND_GATE_TESTS

- `summary_failed=true`：產品仍可下載 transcript fallback，但 E2E formal-record verdict 必須 FAIL。
- correction stable failure：保留原文並繼續；只要正式 meeting record 成功且內容可接受，不得單獨 veto。
- build revision unknown：一般 `/api/health` 仍可 200；Stage 05/managed accepted-SHA rollout 必須 FAIL closed。
- model snapshot API unreachable/ambiguous：產品一般 health contract不改；本 local-LM E2E 不具可歸因性，停止。
- Browser capability missing：environment blocker；API mode 可作診斷但不得標 true E2E PASS。
- Documents renderer missing：記錄 environment blocker；OOXML pass 不能冒充 all-page QA。
- telemetry parser/test defect：修 verifier，建立新 append-only attempt；不把 verifier defect 誤報為 product defect。

## MIGRATION_COMPATIBILITY_ROLLBACK

- **Migration：** NONE。
- **Public compatibility：** HTTP schema、frontend contract、task state、fallback filename semantics不變。
- **Internal CLI compatibility：** 保留 runner 現有 `--smoke`、`--dry-run`、`--audio`、`--artifacts-dir` 可用；如重新命名 evidence/runtime 參數，提供相容 alias 或清楚 migration error，不讓 Stage 04/05 指令含糊。
- **Launcher compatibility：** canonical start/stop/restart entry 保留；新增的 revision/DATA_DIR/health mismatch 只讓不可歸因或不可寫的啟動 fail loudly。
- **Implementation rollback：** runner/launcher 變更可用單一 implementation commit revert；不涉及資料格式。
- **Operational rollback：** 只停止 WAVE-05 新啟動的 owned process；不刪除 data/cache/evidence，不恢復未知 process。

## DEFERRED_OR_BEST_EFFORT

- 所有 transcript 同音字、語者與專有名詞精修。
- 更細緻的 E2E dashboard、event stream、長期 metrics storage 或 browser automation framework。
- 為 Qwen/特定模型建立 adapter、thinking-disable 或改模型策略。
- 將 build revision 升級為一般產品 global readiness gate。
- 遠端部署、CI E2E、NVIDIA hardware E2E、performance SLO。

## RISKS

- **Stochastic LLM failure：** 同一音檔仍可能偶發空 content；以 exact evidence、bounded contract 與新 attempt 處理，不 rerun-until-green 後隱瞞第一次失敗。
- **長時間資源使用：** 約 87 分鐘音檔會長時間占用 ASR/LLM；只允許一個新 task，避免平行重跑。
- **False semantic PASS：** 結構檢查可能通過但內容不忠實；以 transcript-first 9 anchors 和 unsupported-fact audit 控制。
- **Sensitive artifacts：** runner 若仍把 raw data 寫進 tracked task dir 會造成洩漏；evidence/runtime split 是 implementation gate。
- **Rollout ownership drift：** 9527 在驗收期間可能被其他 process 占用；未知 ownership 必須停止自動切換。
- **Lower-tier Implementer scope drift：** handoff 必須把 `DO_NOT_TOUCH` 與 product-failure replan stop condition放在第一屏，避免看到空摘要就再改 summarization。

## DEFINITION_OF_DONE

- `DoD-01`：Revision 3 verifier/launcher fail-first tests 先 red（正確原因）後 green；Revision 2 focused regressions與完整 suite 無新 regression。
- `DoD-02`：runner 在 revision mismatch/dirty/data/model gate 失敗時，Browser UI 未 ready、API upload call count 0、owned child安全終止。
- `DoD-03`：runner 對 `completed + summary_failed=true`、fallback header/OOXML、wrong upload hash、ambiguous/changed model、invalid metrics 一律 FAIL。
- `DoD-04`：macOS launcher 注入可歸因 revision，顯示 actual port/DATA_DIR，只有 health revision match 才宣告 ready；不 broad-kill。
- `DoD-05`：fresh Stage 05 Browser 真正上傳 exact audio；source/server SHA一致，只有一個 task，task completed且`summary_failed=false`，UI 無 failure banner，正式兩個下載按鈕均點擊。
- `DoD-06`：formal DOCX 的 header/title/OOXML/general sections、9 semantic anchors、決議/待辦、unsupported-fact audit與全部頁面 visual QA 全數通過。
- `DoD-07`：run 前後唯一 model/instance一致；metrics與 bounded-call/merge contract無違規；完整 raw artifacts留在 gitignored runtime，tracked attempt只有 redacted evidence/hash。
- `DoD-08`：通過後 local 9527 確認 ownership並自動啟動 accepted SHA；health revision一致、Browser smoke通過；資料未刪除。
- `DoD-09`：Stage 05 寫入 `result.md`；若任何 CORE failure，沒有 PASS/rollout/result，並依 failure routing 建立新 attempt、environment處理或 Revision 4 replan。

## FAILURE_ROUTING

- **Verifier/test harness defect：** 修 verifier/tests；不改 product；建立下一個 append-only Stage 05 attempt。
- **Environment blocker：** 修環境或取得缺失 Browser/Documents capability；不得宣稱 PASS。
- **Current HEAD product failure：** 保存 exact task/log/metrics/model/revision/audio hash 與 first bad boundary，停止 Stage 05，建立 same TASK_ID Revision 4 debug replan；不得由 Stage 04/05 即席改 summarization/task-state/fallback。
- **Semantic contract change required：** 任何成功/requiredness/gating/error/fallback/model selection/priority 改變均回 Stage 01；使用者本次免 Review 只適用 Revision 3，不自動套用未來 revision。
- **Unknown 9527 ownership：** isolated E2E PASS 可保留，但 rollout 標 blocked 並請使用者處理；不得 kill。

## HANDOFF_HINTS

- Fresh Implementer 先驗證 `PLAN_REVISION=3` 與 plan SHA，再讀 `GOAL_CONTRACT`、`ROOT_CAUSE`、`DO_NOT_TOUCH`、`CRITICAL_PATH`、`CHANGE_MAP CM-01~03`、`IMPLEMENTATION_WAVES WAVE-01~03`、`REGRESSION_AND_ACCEPTANCE`、`FAILURE_ROUTING`。
- Stage 04 第一刀是 verifier/launcher fail-first tests，不是 summarization service。
- 建議把 runner 的 acceptance predicates抽成少量 pure helpers再由 API/browser shared path呼叫，讓 tests 不需要啟動 ASR/LM Studio；不要建立新 framework。
- Browser upload detection 使用 isolated backend 已存在的「檔案上傳成功 … stored filename … 任務ID」log line，bounded poll且要求唯一；不新增 endpoint。
- Stage 04 不執行真實 86.95 分鐘音檔、不寫 `result.md`；Stage 05 才執行 exact audio 與 rollout。

## REVIEW_AND_HANDOFF_GATES

- 使用者已批准 Revision 3 並明確要求本次不做 Review；`REVIEW_REQUIRED: NO`、`REVIEW_REPORT: NONE`。
- Stage 03 必須先 archive Revision 2 handoff，再以 Revision 3 SHA 編譯新 handoff；不得引用 Revision 2 review 作為 Revision 3 approval。
- Handoff 後 `NEXT_STAGE: 04_IMPLEMENT`，Fresh Implementer required。
- Stage 04 若 handoff/plan SHA mismatch、工作樹有未知 dirty changes、或需要修改 `DO_NOT_TOUCH`，立即停止。

## ARTIFACT_GATE

- `TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary`
- `PLAN_PATH: .agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/plan.md`
- `PLAN_REVISION: 3`
- `PLAN_STATUS: READY_FOR_IMPLEMENTATION`
- `DEBUG_STATUS: READY_FOR_IMPLEMENTATION`
- `FIX_TYPE: MIXED`
- `REVIEW_REQUIRED: NO`
- `INDEPENDENT_ACCEPTANCE_REQUIRED: YES`
- `E2E_REQUIRED: YES`
- `NEXT_STAGE: 03_HANDOFF`
