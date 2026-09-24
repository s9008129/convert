# Handoff — Issue #18 Local Meeting Record Architecture V2

## TASK
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- STATUS: READY_FOR_IMPLEMENTATION
- PLAN_PATH: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/plan.md`
- PLAN_REVISION: 9
- PLAN_SHA256: `63b30bcae58abbba98e15a9d3b62ef23da391cbcbded19d6e22e494b29f1ba67`
- REVIEW_REQUIRED: YES
- REVIEW_REPORT: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-08/review_report.md`
- REVIEWED_PLAN_REVISION: 9
- REVIEWED_PLAN_SHA256: `63b30bcae58abbba98e15a9d3b62ef23da391cbcbded19d6e22e494b29f1ba67`
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: CONTRACT + INTEGRATION + E2E + BLIND_RUBRIC
- Fresh Implementer required: YES
- Planner/Reviewer transcript required: NO

## GOAL_ANCHOR

- **Primary outcome:** make the local Gemma 4 31B/Qwen 3.8 27B meeting-record path preserve immutable raw-source facts through structured evidence, deterministic validation, and controlled generation.
- **Success evidence:** selected causal claim remains correct source→facts→ledger→render→delivery; focused/full/cloud/privacy checks pass; fresh Gemma/Qwen E2E and blind 3+3 meet each per-output/per-dimension 80% threshold against the original unrounded Gemini baseline with zero adjudicated major fidelity hard fails.
- **Must not break:** cloud behavior, template/output contracts, v4.7.4 invariants, provenance/privacy, retry/runtime-selection safety, and explicit V1 rollback. Unknown/ambiguous facts stay unknown; no silent V1 fallback.

## CRITICAL_PATH

Protect and classify the dirty tree → establish cloud baseline and fail-first live C1 inversion regression → evidence/schema → structured extraction → deterministic ledger/conflicts → raw-evidence source-alignment firewall → template-derived section plans and per-section rendering → guarded targeted patch/rollback → selected-claim live E2E → fresh model/profile acceptance and blind cohort → docs/privacy/PR #19 delivery.

## SEMANTIC_INVARIANTS

- Raw transcript is the sole immutable source of truth; corrected text is comprehension-only. Tracked diagnostics contain IDs/hashes/counts/status/profile metadata/verdict only.
- Typed claims preserve relation direction, polarity, condition/dependency, number/unit, date, attribution/uncertainty, and evidence refs. Strict JSON/schema repair is one schema-only retry; second failure is explicit V2 failure, never hidden success or silent V1 fallback.
- Required claims are validated from structured metadata against ordered raw evidence and rendered relation metadata. Never skip relation validation because an opaque claim ID is absent from prose. C1 inversion/omission is a CORE acceptance failure requiring the v4.2 fix/replan route without retroactively erasing prior implementation facts.
- Template-derived section plans restrict each renderer to allowed claims/evidence; assembly is deterministic. Patch only the affected section, and rollback byte-for-byte if any CORE quality dimension regresses.
- Profile controls and C9/C10/C14 are CORE system-acceptance/closure evidence and hard-clean verification items, but never per-record/section gates. Missing evaluator/model/hardware is scoped to the affected acceptance; preserve unrelated valid records and implementation evidence.
- C9/C10/C14 status aggregation follows the canonical six-field table in the Plan. Stage04 known blocker: CORE `BLOCKED`, required verification `INCOMPLETE` when other valid evidence exists (otherwise phase `BLOCKED` only if no valid conclusion), independent acceptance `PENDING`, closure `CORE_ACCEPTANCE_BLOCKED`. Not run/no known blocker: CORE `NOT_RUN`, closure `PENDING_CORE_ACCEPTANCE`. Stage05 blocker: preserve Stage04 implementation/core/verification values and immutable snapshot; set independent acceptance `BLOCKED`, closure `ACCEPTANCE_BLOCKED`.
- `IMPLEMENTATION_BLOCKED` is only for unfinished product implementation that cannot safely continue. Never collapse CORE acceptance, required verification, independent acceptance, and closure into one status.

## BEST_EFFORT_DO_NOT_GATE

- Corrected-transcript enrichment, optional entity/glossary completion, unsupported optional fields, performance diagnostics, and held-out examples remain local/non-gating unless evidence establishes a concrete correctness risk.
- If no approved privacy-safe held-out input exists, disclose absence; do not source private data or block core work.
- Missing evaluator or runtime blocks only the affected system acceptance/closure; it never vetoes unrelated valid records or sections.

## DEFERRED_NOT_THIS_TASK

- No wholesale experimental branch merge; reuse only isolated, goal-traceable mechanisms.
- No hard-coded Issue #18 claim/timestamp, lowered quality threshold, second LLM truth judge, transcript/raw prompt/raw output in Git, unrelated ASR/UI work, or speculative optimization before correctness.
- Do not repeat the disproven “put more transcript in final prompt” as the core repair.

## REPO_ANCHOR

- Project root: `/Users/hsiaojohnny/dev/convert`
- Branch: `issue-18-first-divergence-diagnostic`
- Anchor HEAD: `eb3ca049cc72d21d2f4db974db5314b5f399d736`
- Relevant dirty state: prior Stage04 candidate product files (`backend/core/config.py`, `backend/services/summarization.py`, untracked `backend/services/local_pipeline_v2.py`, `tests/test_local_pipeline_v2.py`, and `doc/規格與設計/local-meeting-record-v2.md`) plus task execution/plan/evidence/review artifacts. The prior handoff R4 is archived in `handoff-history/handoff-plan-r4-20260924-201319.md`; R1 is also archived. Two safety branches exist: `backup/issue-18-before-gpt6-20260924-074037` and `backup/issue-18-before-gpt6-20260924-153522`.
- Drift since plan/review: HEAD/branch unchanged. Stage03 archived the stale R4 handoff and compiled this R9 handoff. Re-run `git status` before any product edit; classify every path and stop/escalate on unclassified owner work.

## CURRENT_STATE_DELTA

- Stage04 R4 implementation is an unaccepted candidate, not a baseline or proof of completion. Stage05 attempt 01 found the live firewall accepts a causal predicate inversion because relation checks are skipped when claim IDs are not in prose; the live summarization caller also omitted selected-claim identity. Its immutable report and execution snapshot remain historical evidence.
- The confirmed historical first divergence remains `C-R03-F056-CAUSAL-DIRECTION` at `extraction.chunk.3.raw`. Do not re-diagnose or return to prompt-only recovery.
- Current runtime inventory previously showed Qwen loaded and Gemma listed but not loaded; recheck live. The frozen evaluator/rubric/original unrounded Gemini baselines were not found in prior read-only search; recheck only authorized locations and report exact scoped blocker if still absent.

## MUST_READ_PLAN

Before first action, read: `GOAL_CONTRACT`, `OWNER_CHECK`, `SOURCE_OF_TRUTH_AND_BASELINE`; R1–R12 and `DECISION_CONTRIBUTION_MATRIX`; `SEMANTIC_CONTRACT_AND_FAILURE_CONTAINMENT` and `TARGET_CONTRACT`; W0–W9; `VERIFICATION_AND_CLOSURE_MATRIX` plus `C9/C10/C14 STATUS AGGREGATION`; `BLOCKING_AND_NON_BLOCKING_UNKNOWNS`, `DEFINITION_OF_DONE`, and `HANDOFF_HINTS`.

## SETTLED_DO_NOT_REOPEN

- Historical extraction first divergence and rejected prompt-only fix: settled by prior evidence; no re-diagnosis.
- Stage05 live C1 inversion finding: confirmed defect; reproduce through actual live gate and repair mechanism, not merely a helper.
- V1 remains explicit/default during development; V2 is additive/opt-in with no hidden fallback. Cloud path remains semantically unchanged.
- Runtime profiles/repeated sampling are required for system acceptance and task closure, not per-record gates. C9/C10/C14 status routes and Stage05 preservation follow R9 exactly; no self-waiver.
- Experimental branches are read-only mechanism libraries, not merge targets.

## REVERIFY_ON_START

- Plan/review/handoff revision and SHA-256 match; branch/HEAD and exact `git status --short`; timestamped redacted path classification before mutation; safety branch relationship; no unclassified owner paths.
- Cloud focused baseline command and safe test environment; current local model inventory and active loaded-instance identity/context; frozen evaluator/rubric/unrounded baseline availability; PR #19 state. Never assume prior live state is current.
- Tests previously hit a read-only `/app/data/logs` default. If reproduced, use the verified process-scoped `DATA_DIR=$(mktemp -d /tmp/meetingscribe-pytest-log.XXXXXX)` override; do not change product logging for this environment workaround.

## TRIGGERED_POLICIES

`workflow-routing.md`, `goal-alignment-design-economy.md`, `debugging-recovery.md`, `dependencies-contracts.md`, `testing-verification.md`, `security-privacy.md`, `data-migration.md`, `performance-concurrency.md`, `git-change-hygiene.md`, and `high-risk-change.md` as their listed decisions are reached.

## FIRST_ACTION

W0 before product mutation: record timestamped redacted status/path classification, current HEAD and safety-branch relationship; stop if any path is unclassified. Capture the exact focused cloud baseline in the Plan. Then add/run the fail-first live C1 causal-predicate inversion probe before changing the firewall; it must fail against the current candidate at the real summarization→render→firewall boundary.

## IMPLEMENTATION_WAVES

- W0 CORE — tree protection, environment/model/evaluator/baseline recheck, cloud baseline.
- W1 CORE — fail-first A–I and live-boundary contracts; typed evidence/fact/conflict/section/snapshot models.
- W2 CORE — strict structured extraction, raw provenance/high-risk validation, one schema-only repair.
- W3 CORE — deterministic dedupe/conflict consolidation.
- W4 CORE — production-template-derived section plan, per-section LLM render, deterministic assembly.
- W5/W6 CORE — live scoped fidelity firewall mechanisms; targeted section patch/rollback; explicit V1/V2 selector and privacy-safe diagnostics.
- W7 CORE acceptance/closure, not per-record gate — runtime capability-checked Qwen/Gemma controls and repeated candidate sampling.
- W8 CORE acceptance — C1 live selected-claim E2E, Gemma/Qwen E2E, blind 3+3 where frozen inputs exist; C1–C10 and C14 status routing per the Plan. Runtime/evaluator blockers are scoped and do not block unrelated work.
- W9 CORE closure — documentation, execution evidence, privacy audit, atomic commits, safe push, update existing Draft PR #19; keep Draft if any required acceptance remains unresolved.

## ACCEPTANCE_CONTRACT

Use the v4.2 matrix in Plan as canonical. No waiver is allowed (`WAIVER_AUTHORITY: NONE`). `HARD_CLEAN` closure items are listed even when they do not represent product CORE behavior.

| CHECK_ID | COMMAND/SCENARIO | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | BASELINE_RULE | FAILURE_ROUTING | WAIVER_ALLOWED | WAIVER_AUTHORITY |
|---|---|---|---|---|---|---|---|---|
| C1 | Live selected-claim source→facts→render→delivery plus exact inverted-predicate/omission probe | CORE | OUTCOME | HARD_CLEAN | No baseline required | CORE FAIL; repair or semantic replan by v4.2; retain prior implementation facts | NO | NONE |
| C2 | Synthetic A–I and extraction→schema→alignment→section-render→firewall integration suite | CORE | OUTCOME | HARD_CLEAN | No baseline required | Changed-path regression → FIX; invalid contract → replan | NO | NONE |
| C3 | `uv run pytest -q tests/test_summarization_service.py -k "cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat"`, same pre/post; add byte-level golden if shared helper changes | CORE | MUST_NOT_BREAK | HARD_CLEAN | Exact same-command baseline required | Relevant behavior delta → TASK_REGRESSION; unavailable baseline → scoped BLOCKED/verification INCOMPLETE | NO | NONE |
| C4 | Tracked/GitHub privacy scan; no raw transcript, prompt, raw output, private names, or absolute local paths | CORE | MUST_NOT_BREAK | HARD_CLEAN | No baseline | Violation → must-not-break failure; remove tracked sensitive material safely | NO | NONE |
| C5 | Focused local pipeline/summarization/v4.7.4 contract tests | CORE | OUTCOME | HARD_CLEAN | New focused tests | Changed-path failure → TASK_REGRESSION/FIX | NO | NONE |
| C6 | `uv run pytest tests/ -q` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | Capture pre-change baseline; distinguish same-signature debt | New/worsened relevant failure → regression; existing debt remains disclosed | NO | NONE |
| C7 | `bash scripts/check_docs.sh` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | Capture pre-change baseline | Same baseline-vs-new rule; closure remains pending if unsatisfied | NO | NONE |
| C8 | `git diff --check` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | No baseline | Task-attributable whitespace error → fix before closure | NO | NONE |
| C9 | Fresh selected-claim E2E on Gemma and Qwen; verify actual loaded model and no hidden fallback | CORE | OUTCOME | HARD_CLEAN | No baseline | Model/hardware unavailable → item BLOCKED/ENVIRONMENT; Stage04 CORE BLOCKED; Stage05 preserves Stage04 fields, independent BLOCKED, closure ACCEPTANCE_BLOCKED | NO | NONE |
| C10 | Blind Gemma 3 + Qwen 3 using frozen rubric and original unrounded Gemini baseline; each output/dimension ≥0.80 and zero major hard fails | CORE | OUTCOME | HARD_CLEAN | Original unrounded baseline/evaluator required | Missing frozen inputs → `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`; item BLOCKED/AUTHORITY; Stage04 CORE BLOCKED; Stage05 preserves snapshot and sets independent BLOCKED | NO | NONE |
| C11 | Record calls, time, input/output tokens, context and patch count | SUPPORTING | DIAGNOSTIC | NON_GATING | No baseline | Report material overhead; cannot veto absent proven correctness risk | NO | NONE |
| C12 | Held-out privacy-safe meeting/template if available | SUPPORTING | DIAGNOSTIC | NON_GATING | Only approved local source | Missing source is disclosed; non-gating | NO | NONE |
| C13 | `execution.md`, architecture/operational docs as needed, privacy-safe PR #19 update | CORE | MUST_NOT_BREAK | HARD_CLEAN | No baseline | Missing artifact/update keeps closure incomplete | NO | NONE |
| C14 | Per candidate runtime profile, N≥5 preferred/N=3 minimum with limitation; compare median/worst/range/hard-fail and select by fidelity-first priorities | CORE | OUTCOME | HARD_CLEAN | Evaluator/profile capability evidence required | Missing evaluator/model → item BLOCKED/AUTHORITY or ENVIRONMENT; Stage04 CORE BLOCKED; Stage05 preserves Stage04 fields and routes independent BLOCKED/ACCEPTANCE_BLOCKED | NO | NONE |

Every Stage04 material outcome must write `execution.md` with all six orthogonal status fields, verification matrix/results, scoped blockers, next action and freshness inputs. Stage05 must freshness-check it, record the immutable Stage04 implementation/core/verification snapshot and preserve those values on an acceptance environment/authority blocker. Follow the canonical `C9/C10/C14 STATUS AGGREGATION` table in Plan exactly; never use `IMPLEMENTATION_BLOCKED` for acceptance-only blockers.

## STOP_AND_ESCALATE_IF

- Plan/review/handoff SHA or revision mismatch; unclassified dirty path; no safe cloud baseline before shared behavior changes.
- New evidence invalidates source-fidelity root cause, selected C1 premise, architecture, privacy/security, migration, or a load-bearing Plan contract.
- Any proposed change alters VALID/requiredness/gating/error/fallback/priority/failure propagation, introduces a global veto, silently falls back to V1, weakens a validator, or changes model-selection semantics. Stop and use Stage01 replan; semantic changes require fresh Stage02 review and Stage03 handoff.
- Frozen evaluator, original unrounded baseline, or required cohort source is missing: do not invent/round/waive; finish unaffected architecture/regression/E2E work and record the precise scoped acceptance blocker.
- Raw/private payload would enter tracked artifacts or PR; preserve existing dirty work and stop if safe reconciliation is impossible.

## HISTORICAL_TASK_DEPENDENCIES

`T20260924-1523-01-issue18-local-fidelity` historical `execution.md`, `baseline/claim-attempt-3-baseline.json`, and Stage05 `e2e/attempt-01/e2e_report.md` only for the established first divergence and causal-inversion evidence. Do not repeat their diagnosis or treat R4 implementation evidence as R9 acceptance.
