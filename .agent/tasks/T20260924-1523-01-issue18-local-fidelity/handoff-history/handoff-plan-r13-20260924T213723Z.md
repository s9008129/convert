# Handoff — Issue #18 Local Meeting Record Architecture V2

## TASK
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- STATUS: READY_FOR_IMPLEMENTATION
- PLAN_PATH: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/plan.md`
- PLAN_REVISION: 13
- PLAN_SHA256: `ea0334db6c32294f26fdcf7b22db52c376b9cc03e98dd3214cb011f6ac56f900`
- REVIEW_REQUIRED: YES
- REVIEW_REPORT: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-12/review_report.md`
- REVIEWED_PLAN_REVISION: 13
- REVIEWED_PLAN_SHA256: `ea0334db6c32294f26fdcf7b22db52c376b9cc03e98dd3214cb011f6ac56f900`
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: CONTRACT + INTEGRATION + E2E + BLIND_RUBRIC
- Fresh Implementer required: YES
- Planner/Reviewer transcript required: NO

## GOAL_ANCHOR
- **Primary outcome:** deliver a local V2 meeting-record path that keeps immutable raw source as truth, preserves evidence-backed facts through deterministic checks and controlled generation, and meets the frozen blind Gemini quality bar for fresh Gemma/Qwen outputs.
- **Success evidence:** selected causal claim is correct from designated source through delivered final bytes; live-path regressions and cloud/privacy invariants pass; fresh model E2E and blind 3+3 meet every per-output/per-dimension 0.80 threshold against the original unrounded Gemini median with zero adjudicated major fidelity hard failures.
- **Must not break:** cloud semantics, v4.7.4 runtime/retry behavior, template/output compatibility, raw-source privacy/provenance, explicit V1 rollback, and no hidden fallback or fabricated/lowered quality evidence.

## CRITICAL_PATH
W0 preserve/classify the tree and establish baselines → W1 fail-first contracts → W2 typed extraction and exact raw-occurrence resolution → W3 deterministic evidence-overlap ledger/conflicts → W4 trusted template policy and section rendering → W5/W6 live final-byte firewall, scoped repair/rollback and explicit selector → W7 eligible runtime profiles → W8 focused/full/cloud and model/quality acceptance → W9 docs, privacy audit, execution evidence and redacted Draft PR #19 update. Before any C1 Qwen acceptance call, independently preflight the user-designated source identity, unique exact occurrence, and relation derived from raw source. Continue valid engineering work if scoped Gemma/evaluator inputs remain unavailable.

## SEMANTIC_INVARIANTS
- Raw transcript is the immutable source of truth; corrected text is comprehension-only. Raw excerpts, prompts, outputs, and selected-target payload remain private/local or ignored; tracked evidence contains only redacted IDs/hashes/counts/status.
- Asserted evidence resolves by unique exact quote or validated offsets to a raw-source interval. No fuzzy matching, arbitrary first occurrence, corrected-only grounding, or invalid reference in conflict/prompt/render paths. Conflicts require overlapping validated raw intervals plus typed incompatibility; no winner, and impact is scoped.
- Requiredness is assigned only by trusted template policy or explicit caller target after evidence resolution. Model labels, generated IDs, ordering, and position cannot assign it. Unclassified claims are optional; uncertainty and optional failures stay local. Required failures affect their mapped section; selected-target failure affects only its C1 acceptance.
- For C1, the attachment designates the target and raw input as authoritative. Any ignored local artifact is only an untrusted locator/hash link; authorship and embedded relation are not trusted. Derive expected relation from the unique raw occurrence. If identity, occurrence, or relation is inconclusive, C1 is `BLOCKED/AUTHORITY`; do not make/count an acceptance model call.
- Render one section per model call from allowed resolved claims/evidence; assemble deterministically in template order. Validate selected relation and required coverage independently of prose claim-ID presence. Evaluate exact post-finalizer bytes; decisive mapped-required coverage/provenance loss, confirmed unsupported high-risk addition, or confirmed required cross-section duplicate cannot return success. Ambiguous/optional signals remain local diagnostics.
- Extraction errors are classified: only JSON/schema validation failure gets exactly one schema-only repair; provider/transport/timeout/generation/cancellation errors fail explicitly without that retry. Profile selection requires ≥3 distinct observed runs, complete finite required metrics, supported controls, and evaluator evidence; missing dimensions never default to zero.
- No changes to validity/readiness, requiredness, gating/veto, error/retry/fallback, priority, or failure propagation without Stage01 replan, required fresh Stage02 review, new Stage03 handoff, and fresh Stage04. V2 is explicit/opt-in; V1 remains selectable rollback, never hidden fallback. Preserve the six independent status subjects; `DONE` means task closure only.

## BEST_EFFORT_DO_NOT_GATE
Corrected-transcript enrichment; uncertain entity/glossary completion (except an explicitly verified template-required term); optional facts/tags; performance diagnostics; held-out examples without an approved privacy-safe source; and weak similarity/ambiguous normalization signals remain local/non-gating. Gemma/hardware and frozen-evaluator/baseline gaps block only their named acceptance checks and closure, never unrelated implementation or valid records/sections.

## DEFERRED_NOT_THIS_TASK
No wholesale experimental-branch merge; no hard-coded Issue #18 facts/timestamps; no fabricated/rounded quality baseline or second LLM truth judge; no tracked/private source content; no unrelated ASR/UI work or speculative optimization; no prompt-only recovery or automatic full-document rewrite.

## REPO_ANCHOR
- Project root: `/Users/hsiaojohnny/dev/convert`
- Branch: `issue-18-first-divergence-diagnostic`
- Anchor HEAD: `35e98a29f63c155e25454b494c5d21436529aa28` (attempt12 review anchor; live at handoff compile)
- Relevant dirty state: task `plan.md` is modified for R13; review attempts 11 and 12 are append-only untracked task evidence; prior handoff archived at `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/handoff-history/handoff-plan-r11-20260924T202933Z.md`. No product-code changes are present in the observed status. Stage04 W0 must timestamp/classify all paths and preserve them; stop before product mutation on any unclassified path.
- Drift since plan/review: no branch/HEAD drift from R13 or attempt12 anchor. R13 is approved, but the worktree is intentionally not clean because plan/review/handoff artifacts are task evidence. Re-inventory mutable tree/runtime/remote state before mutation. Listed safety branches: `backup/issue-18-before-gpt6-20260924-074037`, `backup/issue-18-before-gpt6-20260924-153522`; verify current protection/relationship in W0.

## CURRENT_STATE_DELTA
Plan R13 corrects target authority: the user attachment identifies the selected claim, and the designated raw source is authoritative; the ignored locator's authorship is unknown. Independent source mapping supports scheduling, but Stage05 must recheck source identity/hash, unique occurrence, and raw-derived typed relation before a Qwen C1 acceptance call. User confirms Qwen 3.8 27B is usable; recheck live immediately before its run. Gemma is not loaded, and the frozen rubric/evaluator plus original unrounded Gemini baseline remain unresolved. Current-head audit identified finalizer coverage loss not enforced as a postcondition, unrepresented generated high-risk prose, schema/runtime failures conflated for repair retry, and incomplete profile-sample eligibility. Prior attempts are evidence of defects, not accepted implementation. These acceptance blockers are scoped; unaffected architecture and Qwen work must proceed.

## MUST_READ_PLAN
Before FIRST_ACTION read `GOAL_CONTRACT`, `OWNER_CHECK`, `SOURCE_OF_TRUTH_AND_BASELINE`, `REQUIREMENTS_AND_CRITICALITY`, `DECISION_CONTRIBUTION_MATRIX`, R11→R13 deltas in `ESCALATION_REPLAN_EVIDENCE`, `SEMANTIC_CONTRACT_AND_FAILURE_CONTAINMENT`, `TARGET_CONTRACT`, W0–W9 in `CHANGE_MAP_AND_WAVES`, `VERIFICATION_AND_CLOSURE_MATRIX` including `C9/C10/C14 STATUS AGGREGATION`, `BLOCKING_AND_NON_BLOCKING_UNKNOWNS`, `DEFINITION_OF_DONE`, and `HANDOFF_HINTS`.

## SETTLED_DO_NOT_REOPEN
- R13 decisions M/N: the designated raw source + attachment establish C1 target authority; private locator is untrusted; pre-model identity/unique-occurrence/relation preflight fails closed to scoped `BLOCKED/AUTHORITY` with no C1 model call when inconclusive.
- R10–R12 decisions remain: no positional selected-claim heuristic; trusted template/caller requiredness only; exact raw occurrence intervals define same evidence; invalid refs never enter conflicts/prompts/rendered evidence; ambiguity and optional failure remain local.
- Post-finalizer exact-byte checks are a real success postcondition; only decisive mapped-required loss, confirmed unsupported high-risk additions, or confirmed required duplicates veto that candidate. Do not broaden heuristic vetoes.
- Exactly one schema-only repair; operational/generation failures do not use that path. ≥3 distinct complete supported samples are required for profile eligibility; no imputed metrics.
- Qwen usability is user-confirmed but is not proof of C1 source mapping or an executed E2E. Gemma/evaluator gaps are scoped. v4.2 six-field status routing and Stage05 immutable Stage04 snapshot are canonical; no self-waivers.

## REVERIFY_ON_START
Exact plan/review/handoff revision and SHA; branch/HEAD/status and path classification; safety-branch relationship; focused cloud baseline and environment; V1/V2 selector; loaded runtime/model identity and supported parameters; C1 private preflight before acceptance call; Gemma state; frozen evaluator/rubric/unrounded baseline; PR #19 Draft state. Do not assume mutable state remains unchanged.

## TRIGGERED_POLICIES
`workflow-routing.md`, `goal-alignment-design-economy.md`, `debugging-recovery.md`, `dependencies-contracts.md`, `testing-verification.md`, `security-privacy.md`, `data-migration.md`, `performance-concurrency.md`, `git-change-hygiene.md`, `high-risk-change.md` (consult at the relevant decisions).

## FIRST_ACTION
W0 before product mutation: capture a timestamped redacted `git status --short` plus classification of every path, HEAD and protection relationship to safety branches; preserve all paths and stop on any unclassified path. Capture the exact pre-change cloud baseline `uv run pytest -q tests/test_summarization_service.py -k "cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat"` and record runtime/config/evaluator/PR state. Then add fail-first live-boundary probes before behavioral changes; do not issue a C1 acceptance model call until the Stage05 source preflight succeeds.

## IMPLEMENTATION_WAVES
- W0 CORE — protect/classify tree, verify backup relation, capture cloud/runtime/evaluator/PR baselines.
- W1 CORE — fail-first synthetic A–I and R12/R13 live-boundary contracts, typed models.
- W2 CORE — structured extraction, exact provenance resolution, schema-only retry classification.
- W3 CORE — deterministic validated-overlap dedupe/conflicts.
- W4 CORE — trusted policies for four active templates, source-present coverage/placeholders, real selected-target caller route, section render/assembly.
- W5 CORE — conservative source alignment, source tags/diversification, verified template-local term correction, final-byte coverage/fidelity/dedupe postconditions.
- W6 CORE — guarded section patch/rollback, explicit V1/V2 selector, redacted diagnostics.
- W7 CORE acceptance/closure, not per-record gate — capability-validated Qwen/Gemma profiles and complete repeated sampling.
- W8 CORE — C1–C10 and C13–C17 acceptance/verification, cloud/v4.7.4/privacy, E2E, and blind cohort; retain scoped blockers.
- W9 CORE closure — durable execution/status fixtures, docs, privacy scan, atomic commits, safe push, redacted Draft PR #19 update; keep PR Draft while acceptance remains unresolved.
- C11–C12 SUPPORTING/BEST_EFFORT diagnostics/held-out runs; never promote them to gates.

## ACCEPTANCE_CONTRACT
No waiver is allowed (`WAIVER_ALLOWED: NO`, `WAIVER_AUTHORITY: NONE`). Keep `PRIMARY_OUTCOME_STATUS`, `IMPLEMENTATION_STATUS`, `CORE_ACCEPTANCE_STATUS`, `REQUIRED_VERIFICATION_STATUS`, `INDEPENDENT_ACCEPTANCE_STATUS`, and `TASK_CLOSURE_STATUS` orthogonal. Stage04 must write/update durable `execution.md` for every material run with all six fields, matrix/results, scoped blockers/next action, evidence, plan/handoff identity and timestamp/hash inputs. Stage05 must freshness-check it and preserve immutable `STAGE_04_REPORTED_IMPLEMENTATION_STATUS`, `STAGE_04_REPORTED_CORE_ACCEPTANCE_STATUS`, `STAGE_04_REPORTED_REQUIRED_VERIFICATION_STATUS`, and `STAGE_04_EXECUTION_ARTIFACT_SHA256`. Acceptance blockers do not downgrade proven Stage04 implementation/CORE facts. `IMPLEMENTATION_BLOCKED` is only unfinished implementation unable to continue; `DONE` is overall closure only.

| CHECK_ID | COMMAND/SCENARIO | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | BASELINE_RULE | FAILURE_ROUTING | WAIVER_ALLOWED | WAIVER_AUTHORITY |
|---|---|---|---|---|---|---|---|---|
| C1 | Selected target source→facts→ledger→render→final delivery; live causal inversion/omission probe | CORE | OUTCOME | HARD_CLEAN | No baseline | Preflight inconclusive → `BLOCKED/AUTHORITY`, no model call; criterion failure → CORE acceptance FAIL or replan if premise invalid | NO | NONE |
| C2 | Synthetic A–I and live extraction/schema/evidence/policy/conflict/render/firewall suite | CORE | OUTCOME | HARD_CLEAN | New focused contracts | Changed-path defect → TASK_REGRESSION/FIX; invalid contract → replan | NO | NONE |
| C3 | `uv run pytest -q tests/test_summarization_service.py -k "cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat"` plus touched-boundary golden | CORE | MUST_NOT_BREAK | HARD_CLEAN | Exact same-command pre/post baseline | Relevant delta → TASK_REGRESSION; missing/empty baseline → scoped BLOCKED, verification INCOMPLETE | NO | NONE |
| C4 | Tracked/GitHub privacy audit | CORE | MUST_NOT_BREAK | HARD_CLEAN | No baseline | Private content/path leak → must-not-break failure | NO | NONE |
| C5 | Focused local pipeline/summarization/v4.7.4 contracts | CORE | OUTCOME | HARD_CLEAN | New focused tests | Changed-path failure → TASK_REGRESSION/FIX | NO | NONE |
| C6 | `uv run pytest tests/ -q` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | Pre-change baseline | New/worsened relevant signature → regression; existing debt disclosed | NO | NONE |
| C7 | `bash scripts/check_docs.sh` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | Pre-change baseline | Baseline delta; unresolved required gate keeps closure pending | NO | NONE |
| C8 | `git diff --check` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | No baseline | Task-attributable whitespace issue must be fixed | NO | NONE |
| C9 | Fresh selected-target E2E on Qwen and Gemma; loaded-model/no-hidden-fallback evidence | CORE | OUTCOME | HARD_CLEAN | No baseline | Model failure → FAIL; unavailable required runtime → scoped `BLOCKED/ENVIRONMENT`; preserve each model's result and v4.2 routing | NO | NONE |
| C10 | Blind Gemma 3 + Qwen 3 against frozen rubric/original unrounded baseline; each output/dimension ≥0.80, zero major hard fails | CORE | OUTCOME | HARD_CLEAN | Frozen evaluator and unrounded baseline | Missing authority → `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`; never guess/round/waive | NO | NONE |
| C11 | Calls/time/tokens/context/patch count | SUPPORTING | DIAGNOSTIC | NON_GATING | No baseline | Report material overhead; non-gating absent proven correctness risk | NO | NONE |
| C12 | Held-out meeting/template only with approved privacy-safe source | SUPPORTING | DIAGNOSTIC | NON_GATING | Approved local source only | Missing source disclosed; non-gating | NO | NONE |
| C13 | `execution.md`, docs, redacted Draft PR #19 update, v4.2 status-contract fixture matrix | CORE | MUST_NOT_BREAK | HARD_CLEAN | No baseline | Missing artifact/update/fixture or incorrect Draft state leaves closure incomplete | NO | NONE |
| C14 | Runtime capability and repeated candidate-profile sampling/selection; N≥3 distinct complete runs (N≥5 preferred), evaluator dimensions/statistics | CORE | OUTCOME | HARD_CLEAN | Evaluator/profile evidence required | Missing evaluator → C10 authority blocker; unavailable runtime → environment blocker; incomplete/unsupported samples ineligible, no imputation | NO | NONE |
| C15 | Exact post-finalizer coverage/fidelity/source-tag/duplicate checks incl. high-risk novelty | CORE | OUTCOME | HARD_CLEAN | No baseline | Decisive mapped-required loss, confirmed unsupported addition or required duplicate → candidate FAIL/TASK_REGRESSION; ambiguous/optional signals remain local | NO | NONE |
| C16 | Failure-classification probe: schema error exactly one repair; provider/runtime/generation errors no schema retry | CORE | MUST_NOT_BREAK | HARD_CLEAN | New focused contracts | Wrong retry/failure classification → TASK_REGRESSION | NO | NONE |
| C17 | Profile eligibility: repeats<3, replay/incomplete metrics/unsupported controls rejected; no default-zero dimensions | CORE | OUTCOME | HARD_CLEAN | New focused contracts | Ineligible evidence blocks only C14 as warranted; never gates unrelated records | NO | NONE |

## STOP_AND_ESCALATE_IF
Plan/review/handoff revision or hash mismatch; unexplained/unclassified dirty path; cloud baseline unavailable before shared behavior change; invalidated source-fidelity root cause, C1 target/source premise, architecture, privacy, migration or other load-bearing Plan premise; any semantic validity/readiness/requiredness/gating/error/retry/fallback/priority/failure-propagation/model-selection change; hidden V1 fallback or weakened validator; raw/private content entering tracked artifacts/PR. Replan through Stage01 + fresh Stage02 + Stage03 on semantic change. Missing evaluator/baseline blocks C10/C14 authority and missing Gemma blocks its C9/C14 environment component only; continue unaffected work and never invent, round, or waive.

## HISTORICAL_TASK_DEPENDENCIES
Same task `T20260924-1523-01-issue18-local-fidelity`: read only relevant prior `execution.md`, `baseline/claim-attempt-3-baseline.json`, `e2e/attempt-01/e2e_report.md`, Stage05 attempt06/escalation, and attempts08–09 as evidence for established first-divergence, inversion, provenance and carried-forward verification results. Do not repeat settled diagnosis or treat prior candidate evidence as acceptance of R13 implementation.

TASK_ID: T20260924-1523-01-issue18-local-fidelity
HANDOFF_PATH: .agent/tasks/T20260924-1523-01-issue18-local-fidelity/handoff.md
PLAN_REVISION: 13
STATUS: READY_FOR_IMPLEMENTATION
NEXT_STAGE: 04_IMPLEMENT
