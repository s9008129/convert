# Handoff — P7-C local summary quality parity: rev14 Qwen recovery

## TASK
- TASK_ID: T20260923-2050-01-local-extraction-adherence
- STATUS: READY_FOR_IMPLEMENTATION
- PLAN_PATH: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/plan.md`
- PLAN_REVISION: 14
- PLAN_SHA256: `53ee307586a3569cc5e91eac9c48a973147058f02a105263de9791ae6efdae9f`
- REVIEW_REQUIRED: YES
- REVIEW_REPORT: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-15/review_report.md`
- REVIEWED_PLAN_REVISION: 14
- REVIEWED_PLAN_SHA256: `53ee307586a3569cc5e91eac9c48a973147058f02a105263de9791ae6efdae9f`
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: E2E
- Fresh Implementer required: YES
- Planner/Reviewer transcript required: NO

## GOAL_ANCHOR
在正式產品地端摘要路徑中，Gemma 4 31B 與 Qwen 3.8 27B 對專案雲端 Gemini 3.5 Flash-lite 的四個核心品質維度，各自每一份都須嚴格低於 cloud median 的 10% 差距。
只用固定 canonical transcript、`section_meeting` 模板、凍結 rubric 與核准 profile；候選通過後才持久化 local-only defaults，再用新輸出做 final 3×3 並由 Stage 05 獨立驗收。
不得更換 Qwen 3.8 27B 身分、window/context、門檻、prompt、樣本或評分規則；雲端／地端隔離、使用者 override、failure atomicity、raw 隱私及真實狀態語意必須維持。

## CRITICAL_PATH
1. Fresh Stage 04 核對此 handoff、Plan rev14、attempt-15 Review 與 snapshot 的 hash/revision，再核對 HEAD、工作樹、固定輸入/checklist/rubric。
2. 重新確認 LM Studio 可用並載入唯一核准模型 Qwen 3.8 27B (`qwen3.8-27b-splash`)，量化及 context 必須與 rev14 固定值一致（4-bit、65,536）；不符即停止。
3. 使用新唯一 ignored cache 做 **僅一次** `C-R03-recovery-01`。不因外層累計 30 分鐘而取消；等 LM Studio 回覆。只有 exit 0 且有效輸出/hash 齊全才把它映射為匿名 candidate `C-R03`。舊 C-R03 無輸出，永不計分或覆寫。
4. Recovery 成功後才續跑 `C-R04–C-R09`，完成 candidate cloud/Gemma/Qwen 各 3 份；任一其他 runner 非零、timeout、無輸出或 provenance 不符都停止，不再自行重試。
5. 所有 9 份有效生成完成後才進入 blind scoring。僅 candidate 全數通過才持久化六個 local-only defaults；接著做新 commit 的 fresh final 3×3、兩場 supporting audio→DOCX E2E，最後 Stage 05。

## SEMANTIC_INVARIANTS
- rev14 是唯一核准的後續路徑：其 one-recovery 條款只適用於使用者回報 LM Studio 更新／重啟後的 C-R03 缺失樣本，不構成一般 retry permission。
- 保留原始 C-R03 `predict` error 與 cache；它是 runner/provider failure、沒有品質分數，不是模型品質 FAIL。
- 不改四個 CORE 維度與 strict `<10%`、同輸入/模板/候選 profile、模型 key/量化/context、prompt/temperature、local/cloud route 或 `.env`／process override。
- 外層 Stage 04 不加 30 分鐘總取消；程式既有每次請求 1,800 秒設定維持不變。若單次呼叫真的以 timeout 結束，按 rev14 停止並另行 replan，不自行調大 timeout。
- 不讀取或揭露 raw candidate output、transcript、prompt、完整 score ledger 或 identity mapping；只寫 Plan 允許的 safe derivatives。

## BEST_EFFORT_DO_NOT_GATE
速度/TPS、字面 coverage、項目數、平均字數與 near-duplicate 僅作 supporting diagnostics，不取代四維盲評，也不得把速度分析變成 parity veto。ASR/helper/DOCX E2E 只驗 supporting integration；其失敗只阻斷該 integration evidence，不抹除有效 parity 結果。

## DEFERRED_NOT_THIS_TASK
不做 window-size/量化/模型/生成參數效能調校，不測其他模型或 Qwen 3.6，不做跨會議泛化、Windows/Ollama 實機、額外 E2E 樣本或未核准的 prompt/產品語意修正。

## REPO_ANCHOR
- Project root: `/Users/hsiaojohnny/dev/convert`
- Branch: `fix/qwen-local-quality-parity`
- Anchor HEAD: `a576b06fc93c4a9d057ae59cdb54f07426ce343d`
- Relevant dirty state: only untracked `.agent/tasks/T20260923-2050-01-local-extraction-adherence/`; tracked product/test tree clean at Stage 02 review.
- Drift since plan/review: product HEAD unchanged. User reports LM Studio completed a software update and restart after the prior Qwen failure; API is reachable, but most recent read-only inventory showed models not loaded. Recheck at execution time.

## CURRENT_STATE_DELTA
- Plan rev14 and Stage 02 attempt-15 are approved for the exact SHA listed above.
- Rubric is already frozen before generation. C-R01 cloud and C-R02 Gemma exited 0 and have hashes, but neither has been scored.
- C-R03 Qwen 3.8 27B exited 1 with no output; contemporaneous LM Studio `predict` errors have no safe subtype. No provider completion or quality result is proven.
- Candidate parity remains BLOCKED; implementation is COMPLETE; primary outcome UNKNOWN; required verification INCOMPLETE; independent acceptance PENDING. No profile persistence, scoring, final cohort, supporting E2E or Stage 05 has started.

## MUST_READ_PLAN
Read Plan §§0.12–0.14 (goal/replan/current evidence), §§1–5 (goal, fixed profile/input, scoring contract), §§6–8 including rev14 recovery clause (rollback, compatibility, sequence/privacy/status), and §§9–10 (budget/risks). §11 is historical provenance only and must not override rev14.

## SETTLED_DO_NOT_REOPEN
- Exact goal, fixed input/checklist/template, four scoring dimensions, strict `<10%`, hard factual fail, Qwen 3.8 27B identity and Gemini 3.5 Flash-lite baseline.
- `PLAN_REVISION=14`, Review attempt-15, and their matching SHA; rev13 handoff is archived at `handoff-history/handoff-plan-r13-20260924-103643.md` and is stale.
- Candidate-before-persistence, persistence-before-final, final-before-supporting-E2E, then fresh Stage 05.
- C-R01/C-R02 remain generation-only; old failed C-R03 is not a sample. Only the single rev14 recovery can fill Qwen candidate run 1.

## REVERIFY_ON_START
- Recompute Plan, Review report/snapshot, and handoff hashes; confirm revision 14, review PASS, branch/HEAD and no tracked product/test drift.
- Confirm canonical transcript SHA `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0`, checklist SHA `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`, `section_meeting`, mode and frozen rubric/hash.
- Verify LM Studio server reachable; record only safe version/model inventory fields and confirm exact Qwen model, quantization, single loaded LLM and context 65,536. Do not assume that restarting loaded the model.
- Check candidate profile values from Plan §5 and effective environment values without exposing secrets. If provenance/profile differs, stop; never rewrite user settings.
- Ensure recovery cache/output path is new, unique and gitignored; never reuse any C-R01/C-R02/C-R03 path.

## TRIGGERED_POLICIES
- `testing-verification.md`
- `workflow-routing.md` §7 Status Semantics Contract v2
- `security-privacy.md`
- `dependencies-contracts.md` for config and load-bearing contracts
- `debugging-recovery.md` for any new failure
- `git-change-hygiene.md` only for the already-authorized conditional publish after Stage 05

## FIRST_ACTION
Fresh Stage 04 verifies all Plan/review/snapshot/handoff hashes, reads the already-appended C-R01–C-R03 terminal record in `execution.md`, and appends a new continuation snapshot without rewriting prior history. Then recheck current branch/HEAD/dirty product tree and LM Studio readiness. Do not load Qwen or generate output until those checks pass.

## IMPLEMENTATION_WAVES
- **W0 — CORE evidence/provenance:** fresh-session handoff/hash/branch/input/rubric/profile checks and safe LM Studio inventory.
- **W1 — CORE recovery:** one Qwen 3.8 27B generation under rev14; failure stops and escalates.
- **W2 — CORE candidate parity:** only after W1 PASS, finish remaining six candidates; blind-score complete anonymous 3×3.
- **W3 — CORE profile persistence:** only after candidate PASS; modify only approved six local defaults and `.env.example`, with required baseline/contract/rollback checks.
- **W4 — CORE final parity:** fresh cloud/Gemma/Qwen 3×3 against persisted settings and the same frozen rubric.
- **W5 — SUPPORTING integration:** only after final parity PASS, one audio→DOCX E2E for each local model.
- **W6 — CORE independent acceptance/closure:** fresh Stage 05; preserve Stage 04 snapshot and all six orthogonal statuses.

## ACCEPTANCE_CONTRACT
Every material check must carry `CHECK_ID | COMMAND/SCENARIO | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | BASELINE_RULE | FAILURE_ROUTING | WAIVER_ALLOWED | WAIVER_AUTHORITY`, plus result/waiver status. Recovery is a missing-sample path within `CANDIDATE-PARITY`, not a new independent acceptance gate.

- `CANDIDATE-PARITY`: CORE / OUTCOME / HARD_CLEAN; the missing first Qwen sample may be filled only by the single rev14 exact-model/profile recovery request with a new cache. Continue only on exit 0 + valid output/hash; otherwise scoped BLOCKED and Stage 01 replan. The complete gate remains valid cloud/Gemma/Qwen 3×3, anonymous dual scoring, every local output/dimension `<10%` vs cloud median and no hard fail; quality shortfall is FAIL/replan, invalid provider/provenance is BLOCKED; no waiver.
- `PROFILE-PERSISTENCE`, `LOCAL-CONTRACTS`, `BYTE-ROLLBACK`, `FULL-SUITE`, `FINAL-PARITY`, `E2E-ASR-HELPER-PREFLIGHT`, `E2E-COMMIT-PROVENANCE`, `STAGE05-INDEPENDENT`, and `STATUS-CONTRACT-FIXTURES` follow Plan §§5/8 and remain conditional/in their defined scopes; no self-waiver.

## STOP_AND_ESCALATE_IF
- Plan/review/handoff revision or hash mismatch; branch/HEAD/product drift; wrong transcript/checklist/rubric/model/context/profile; absent/unverifiable privacy boundary; reused cache; or raw output exposure.
- C-R03 recovery nonzero, timeout, missing output/hash, or mismatch: stop immediately, preserve raw evidence in ignored cache, append allowlisted diagnostics, do not retry again, score, persist, or start final/E2E; return to Stage 01.
- Any later candidate runner failure: preserve evidence and apply original stop condition; no unplanned retry.
- Candidate/final valid quality gap `>=10%`, hard fidelity failure, or any proposed change to model identity, context, prompt, settings, gates, timeout, requiredness, fallback or error semantics: stop and follow Plan’s Stage 01/02/03 replan route.
- Stage 05 not PASS, required verification incomplete, or any hard closure blocker: do not claim DONE or publish.

## HISTORICAL_TASK_DEPENDENCIES
- `T20260923-1810-01-local-record-fidelity-density`: only the Plan-cited P7-B quality/cost evidence; historical context, not current acceptance.
- `T20260922-2037-02-local-model-quality-parity`: only the canonical checklist artifact/hash referenced in Plan §5.
