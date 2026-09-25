# Handoff — Issue #18 Local Meeting Record Architecture V2

## TASK
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- STATUS: READY_FOR_IMPLEMENTATION
- PLAN_PATH: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/plan.md`
- PLAN_REVISION: 17
- PLAN_SHA256: `835a2888be6b593a35dc1d59ff53b714b11371d8bd37b8cd5b373aa8d14896a5`
- REVIEW_REQUIRED: YES
- REVIEW_REPORT: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-17/review_report.md`
- REVIEWED_PLAN_REVISION: 17
- REVIEWED_PLAN_SHA256: `835a2888be6b593a35dc1d59ff53b714b11371d8bd37b8cd5b373aa8d14896a5`
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: CONTRACT + INTEGRATION + E2E + BLIND_RUBRIC
- Fresh Implementer required: YES
- Planner/Reviewer transcript required: NO

## GOAL_ANCHOR
PRIMARY_OUTCOME: ship an operational local V2 meeting-record path for Gemma 4 31B and Qwen 3.8 27B that preserves raw-source facts and relationships through final delivery.
SUCCESS_EVIDENCE: the selected causal target is correct end-to-end; fresh blind outputs each reach ≥80% of the original unrounded Gemini median in every dimension, with zero adjudicated major fidelity hard failures; required regressions, cloud/privacy invariants, and delivery evidence pass.
MUST_NOT_BREAK: immutable raw-source authority and privacy/provenance; cloud and v4.7.4 behavior; template/output compatibility; explicit failure, rollback, and V1/V2 selection; no hidden fallback or fabricated/rounded quality evidence.
The exact Gemini denominator and displayed-value rounding cross-check are verified; authority/applicability of the rubric remains a separate pending decision affecting C10/C14 only.

## CRITICAL_PATH
W0 classify/preserve every current path and establish pre-change baselines before product mutation → W1 fail-first synthetic and live-boundary contracts → W2 typed extraction, LM Studio/Ollama-native schema adapters and capability/error classification, and unique raw-occurrence resolution → W3 deterministic validated-overlap ledger/conflicts → W4 trusted template requiredness and section rendering → W5 conservative live fidelity checks on exact final bytes → W6 one issue-triggered section patch with rollback and explicit V1/V2 selection → W7 runtime-validated profiles/samples → W8 required regression, Qwen C1 preflight/E2E, Gemma when loaded, evaluator applicability adjudication, and authorized blind cohort → W9 docs/privacy/execution evidence and redacted Draft PR #19 update. Complete approved implementation gaps and fail-first/live-boundary checks before fresh acceptance; keep scoped environment/authority blockers local.

## SEMANTIC_INVARIANTS
- Raw transcript is immutable truth; corrected text is comprehension-only and may ground nothing without explicit safe alignment back to raw. No raw transcript, prompt, model output, name, or selected-target payload in tracked/GitHub artifacts.
- Evidence must resolve by unique exact raw quote or validated offsets to an absolute occurrence. No fuzzy/first-match/corrected-only grounding; unresolved refs cannot enter conflicts, prompts, or rendered provenance. Same-evidence conflicts require overlapping validated raw intervals plus material typed incompatibility; no winner and impact remains scoped.
- Requiredness comes only from trusted template policy or the explicit caller target, after evidence resolution. Model labels, generated IDs, position, and relation type do not assign it. Unknown/unclassified claims are optional; optional/ambiguous failures remain local. Required failures affect their mapped section; selected-target failure affects that target's acceptance.
- Native structured-output support uses one normalized `SUPPORTED | UNSUPPORTED | UNKNOWN` contract with backend-specific adapters. LM Studio uses its active loaded-instance identity and `response_format`; local Ollama uses configured/effective model identity and `/api/chat` `format: <JSON Schema>` for both the source-free exact fact-payload probe and user-source extraction. `SUPPORTED` requires normal probe completion plus parsed output that validates against and equals the exact synthetic fact-payload contract. `UNSUPPORTED` requires a recognized explicit backend/model-specific capability response. Generic 400/request/schema errors, unknown error text, invalid output, timeout, truncation, cancellation, transport/runtime failures retain their original classification, remain `UNKNOWN`, and stop before user-source extraction. Only confirmed `UNSUPPORTED` permits strict-JSON/schema-validation fallback; client validation remains mandatory even for native output. Ollama Cloud is excluded. Diagnostics contain backend/model identity and result only. Unknown model family/context stays `UNKNOWN`, never Gemma or inferred loaded context.
- Only classified JSON/schema validation failure permits exactly one schema-only repair. Runtime/provider/transport/timeout/truncation/cancellation/generation/unsupported-capability errors do not enter that path.
- Render one section per model call from allowed claims and corresponding resolved evidence; assemble deterministically. Validate selected relation and required coverage independently of prose claim IDs. Exact post-finalizer bytes are the success boundary; decisive mapped-required loss, confirmed unsupported high-risk content, or confirmed required duplicate cannot return success. Ambiguous/optional signals stay local.
- Corrected-view alignment is explicit; if unavailable/ambiguous, use corresponding raw view and report the scoped diagnostic. Targeted repair is at most one affected-section patch, only on a validation issue; use existing snapshot/rollback and accept only non-regressive bytes. No hidden V1 fallback. Any semantic-contract change requires replan/review/new handoff.
- Keep the six v4.2 status subjects orthogonal. Stage04 writes durable `execution.md` for every material run. Stage05 freshness-checks it and preserves immutable Stage04 implementation/CORE/verification fields and execution SHA; acceptance blockers do not downgrade proven implementation. `DONE` means task closure only.

## BEST_EFFORT_DO_NOT_GATE
Corrected-transcript enrichment when alignment is unavailable; uncertain entity/glossary completion except a verified template-required term; optional facts/tags; performance diagnostics; held-out examples without an approved privacy-safe source; weak similarity or ambiguous normalization signals. Gemma/hardware, source-target authority, and rubric-applicability blockers affect only their named acceptance items, not unrelated implementation, sections, or records. C11 and C12 are supporting/diagnostic and non-gating.

## DEFERRED_NOT_THIS_TASK
No wholesale experiment-branch merge; no hard-coded Issue #18 facts/timestamps; no tracked/private source payload; no second LLM truth judge; no lowered/rounded threshold or imported P7-C `<10%` gate; no reuse of P7-C local candidates; no unrelated ASR/UI rework, speculative optimization, prompt-only recovery, or default full-document rewrite.

## REPO_ANCHOR
- Project root: `/Users/hsiaojohnny/dev/convert`
- Branch: `issue-18-first-divergence-diagnostic`
- Anchor HEAD: `430950148cf02ece5845cc807665e0e4f35ea7e1`
- Relevant dirty state at R17 replan: the worktree contains preserved uncommitted R16 Stage04 product/test/docs changes and R16 W0 artifacts, plus task artifacts. Stage04 stopped at the semantic boundary. W0 must timestamp and classify every current path, preserve the existing diff, and stop before product mutation if any path is unclassified. Do not reset/stash/clean/overwrite or commit these paths before the matching R17 handoff.
- Drift since plan/review: the plan records HEAD and origin at `430950148cf02ece5845cc807665e0e4f35ea7e1`; Stage04 must reverify the live HEAD and its relation to both safety branches. R16 test evidence does not verify the newly approved Ollama contract. Generate a fresh Stage04 execution record bound to R17; do not treat earlier execution as acceptance of R17 changes.

## CURRENT_STATE_DELTA
R17 adds only the approved per-backend native structured-output contract to the preserved R16 work: LM Studio uses `response_format`; local Ollama uses `/api/chat` `format` with the JSON Schema for the source-free exact-payload probe and source-bearing extraction. Both feed the same normalized capability states; Ollama Cloud is excluded. Generic probe errors (including generic 400/request/schema errors, invalid output, timeout, truncation, cancellation, transport/runtime errors, or unknown text) remain their original error class with capability `UNKNOWN` and stop before source use; only a narrow explicit unsupported-capability response permits strict-JSON/schema-validation fallback. Review attempt17 approves this exact R17 plan. Preserve the uncommitted R16 product/test/docs diff and R16 W0 artifacts; Stage04 must inventory them afresh and add focused fail-first/integration coverage for the newly approved Ollama contract. The source-free probe does not contain meeting data and is not a per-record quality veto. Other acceptance facts remain scoped: Qwen is user-confirmed usable but rechecked live; Gemma is not loaded; C1 requires fresh independent source identity/occurrence/relation preflight before any acceptance call; Gemini denominators numerically cross-check but rubric applicability is still pending, so C10/C14 remain `NOT_RUN` only during adjudication or become precisely scoped `BLOCKED/AUTHORITY` if unresolved.

## MUST_READ_PLAN
Before FIRST_ACTION, read `GOAL_CONTRACT`, `OWNER_CHECK`, `SOURCE_OF_TRUTH_AND_BASELINE`, `REQUIREMENTS_AND_CRITICALITY`, `DECISION_CONTRIBUTION_MATRIX`, R13→R17 decisions in `ESCALATION_REPLAN_EVIDENCE` (Decisions P–U), `SEMANTIC_CONTRACT_AND_FAILURE_CONTAINMENT`, `TARGET_CONTRACT`, W0–W9 in `CHANGE_MAP_AND_WAVES`, `VERIFICATION_AND_CLOSURE_MATRIX` including canonical `C9/C10/C14 STATUS AGGREGATION`, `BLOCKING_AND_NON_BLOCKING_UNKNOWNS`, `DEFINITION_OF_DONE`, and `HANDOFF_HINTS`.

## SETTLED_DO_NOT_REOPEN
- Review attempt17 approves only Plan Revision 17 with SHA-256 `835a2888be6b593a35dc1d59ff53b714b11371d8bd37b8cd5b373aa8d14896a5`. R16 approval is stale.
- Decision P: capability is per active backend/model; only explicit metadata or a source-free schema probe establishes support; only narrow explicit unsupported evidence permits fallback; generic/unknown errors retain their class and capability `UNKNOWN`; unknown family/context remains unknown. Decision U specifies LM Studio `response_format` and local Ollama `/api/chat` `format: <JSON Schema>` adapters for both probe and structured extraction; the probe must validate and equal the exact synthetic payload. Ollama generic 400/request/schema errors are not unsupported, must stop before source use, and Ollama Cloud is excluded. Client validation is mandatory for native output.
- Decision Q: corrected view aids comprehension only when safely aligned; all evidence/provenance/fidelity checks resolve against raw source.
- Decision R: validation issue maps to at most one affected-section patch; compare against existing non-regression snapshot and restore prior bytes on regression/failure; never default to whole-record rewrite.
- Decision S: C1 expected positive causal direction is supported by broader-context adjudication with no adjacent-speaker corroboration; keep that caveat and repeat independent Stage05 source/hash/occurrence/relation preflight before any acceptance call.
- Decision T: exact unrounded Gemini denominator numerically cross-checks to user-displayed `83.9286 / 89.7959 / 93.8776 / 85.0000`; rubric applicability remains pending. Preserve user's per-output/per-dimension ≥80% and zero-major-hard-fail gate; do not use P7-C's local candidates or >90% rule.
- Prior approved constraints: no positional selected-claim heuristic; trusted policy/caller requiredness only; exact raw-occurrence overlap for same-evidence conflict; invalid refs never enter conflict/prompt/render; optional uncertainty remains local; exact final-byte checks are a success postcondition; exactly one schema-only retry; ≥3 complete, supported, distinct observations for profile eligibility; no self-waivers.

## REVERIFY_ON_START
Recompute current plan SHA and confirm R17 Review attempt17 freshness; timestamp/classify full status and path state and verify HEAD/safety-branch relationship; establish the exact pre-mutation cloud baseline; inspect V1/V2 selector; recheck active runtime/model identity, capability, supported controls and loaded-instance effective context; confirm Qwen before its run and Gemma load state; perform fresh C1 source/run identity, unique exact occurrence and raw-derived relation preflight before any acceptance call; adjudicate rubric applicability before new blind cohort; recheck PR #19 Draft/base/head. Keep private source and evaluator payloads out of tracked artifacts.

## TRIGGERED_POLICIES
`workflow-routing.md`, `goal-alignment-design-economy.md`, `debugging-recovery.md`, `dependencies-contracts.md`, `testing-verification.md`, `security-privacy.md`, `data-migration.md`, `performance-concurrency.md`, `git-change-hygiene.md`, `high-risk-change.md` (consult at the relevant decision).

## FIRST_ACTION
W0 before any product mutation: persist a timestamped, redacted `git status --short` with classification of every path, current HEAD and relation to both safety branches; preserve all paths and stop on any unclassified path. Reverify branch/HEAD/status, runtime/model/evaluator/PR/V1-V2 state, then establish and save the exact pre-change cloud baseline `uv run pytest -q tests/test_summarization_service.py -k "cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat"` (command, exit status, count, redacted output). Do not mutate product code if the baseline cannot run or selects no tests. Next add the approved fail-first synthetic and live-boundary tests before behavioral changes. No C1 acceptance model call before Stage05's fresh source preflight.

## IMPLEMENTATION_WAVES
- W0 CORE — protect/classify the tree; verify safety-branch relationship; capture focused/full/docs/cloud and runtime/evaluator/PR baselines.
- W1 CORE — fail-first A–I and R12/R16/R17 live-boundary contracts, including both backend schema adapters; typed evidence/fact/conflict/section/snapshot models.
- W2 CORE — structured extraction, raw/corrected alignment, LM Studio `response_format` and local Ollama `/api/chat` `format: <JSON Schema>` adapters for source-free probe and user-source generation, capability/error classification, unique provenance resolution, schema-only retry. Probe `SUPPORTED` requires exact synthetic-payload schema validation; only explicit backend/model-specific unsupported evidence allows fallback; generic errors remain `UNKNOWN` and stop before user-source use.
- W3 CORE — deterministic dedupe/conflicts only on validated overlapping raw occurrences.
- W4 CORE — trusted policies for active templates, source-present coverage/placeholders, explicit selected-target caller route, section render/assembly.
- W5 CORE — conservative source alignment; source tags/diversification; verified template-scoped terms; exact final-byte coverage/fidelity/dedupe checks.
- W6 CORE — issue-triggered one-section patch/rollback, explicit V1/V2 selector, redacted diagnostics.
- W7 CORE acceptance/closure, not per-record gate — capability-validated Qwen/Gemma profiles and complete repeated samples; ≥3 distinct supported runs, N≥5 preferred, no imputed metrics.
- W8 CORE — C1–C10 and C13–C17 acceptance/verification, cloud/v4.7.4/privacy, E2E and blind cohort; retain scoped blockers.
- W9 CORE closure — durable execution/status fixtures, docs, privacy audit, atomic commits/safe push and redacted Draft PR #19 update; keep PR Draft while acceptance remains unresolved.
- C11 SUPPORTING/BEST_EFFORT diagnostics and C12 SUPPORTING held-out run only if approved privacy-safe source exists; neither gates core work.

## ACCEPTANCE_CONTRACT
No waiver is allowed (`WAIVER_ALLOWED: NO`, `WAIVER_AUTHORITY: NONE`). Material check dimensions are separate; C9/C10/C14 are CORE acceptance inputs and required HARD_CLEAN verification items, not per-record gates. Record `CHECK_RESULT` and `WAIVER_STATUS` per item; never rewrite a check result through waiver. Stage04 must durably write `execution.md` with all six orthogonal status fields, matrix/results, scoped blockers/next action, evidence, plan/handoff identity and timestamp/hash inputs. Stage05 must read and freshness-check it, snapshot the Stage04 implementation/core/required-verification fields plus `execution.md` SHA, and preserve those facts if acceptance is blocked. Apply workflow-routing v2; do not label verification-only/acceptance blockers `IMPLEMENTATION_BLOCKED`.

| CHECK_ID | COMMAND/SCENARIO | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | BASELINE_RULE | FAILURE_ROUTING | WAIVER_ALLOWED | WAIVER_AUTHORITY | PLAN_RESULT |
|---|---|---|---|---|---|---|---|---|---|
| C1 | Selected target source→facts→ledger→render→post-finalizer delivery; live predicate inversion/omission probe | CORE | OUTCOME | HARD_CLEAN | None | Fresh preflight inconclusive → item `BLOCKED/AUTHORITY`, no call; criterion failure → CORE acceptance FAIL, replan if premise invalid | NO | NONE | NOT_RUN |
| C2 | Synthetic A–I plus live extraction/schema/evidence/policy/conflict/render/firewall integration; LM Studio `response_format` and local Ollama `/api/chat` `format: <JSON Schema>` on probe and source generation; supported/explicit-unsupported/UNKNOWN capability cases | CORE | OUTCOME | HARD_CLEAN | New focused contracts | Changed-path defect → task regression/FIX; contract premise invalid → replan | NO | NONE | NOT_RUN |
| C3 | `uv run pytest -q tests/test_summarization_service.py -k "cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat"` plus touched-boundary golden if shared helper changes | CORE | MUST_NOT_BREAK | HARD_CLEAN | Exact same-command pre/post baseline | Relevant delta → task regression; unavailable/empty baseline → scoped BLOCKED, verification INCOMPLETE | NO | NONE | NOT_RUN |
| C4 | Tracked/GitHub privacy audit | CORE | MUST_NOT_BREAK | HARD_CLEAN | No baseline | Private content/path leak → must-not-break failure | NO | NONE | NOT_RUN |
| C5 | Focused local V2/task-processor/v4.7.4 contract integration checks | CORE | OUTCOME | HARD_CLEAN | New focused checks | Changed-path failure → task regression/FIX | NO | NONE | NOT_RUN |
| C6 | `uv run pytest tests/ -q` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | Pre-change baseline | Existing debt remains disclosed; new/worsened relevant signature → task regression | NO | NONE | NOT_RUN |
| C7 | `bash scripts/check_docs.sh` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | Pre-change baseline | Baseline delta; unresolved required gate keeps closure pending | NO | NONE | NOT_RUN |
| C8 | `git diff --check` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | No baseline | Task-attributable whitespace issue must be fixed | NO | NONE | NOT_RUN |
| C9 | Fresh selected-target E2E on Qwen and Gemma; loaded-model/no-hidden-fallback evidence | CORE | OUTCOME | HARD_CLEAN | No baseline | Model criterion failure → FAIL; unavailable required runtime → scoped `BLOCKED/ENVIRONMENT`; preserve per-model results | NO | NONE | NOT_RUN |
| C10 | Blind fresh 3+3; every output/dimension ≥0.80 × original unrounded Gemini median and zero major hard fails | CORE | OUTCOME | HARD_CLEAN | Exact verified Gemini denominator; first adjudicate rubric applicability | Keep NOT_RUN during applicability adjudication; if unresolved/unusable → precise `BLOCKED/AUTHORITY`; never guess, round, reuse candidate locals, import >90%, or waive | NO | NONE | NOT_RUN |
| C11 | Calls/time/tokens/context/patch count | SUPPORTING | DIAGNOSTIC | NON_GATING | No baseline | Report material overhead; cannot veto absent correctness risk | NO | NONE | NOT_RUN |
| C12 | Held-out different meeting/template, only with approved privacy-safe source | SUPPORTING | DIAGNOSTIC | NON_GATING | Approved local source only | Missing source disclosed; non-gating | NO | NONE | NOT_RUN |
| C13 | Durable `execution.md`, docs, redacted Draft PR #19 update, v4.2 status-contract fixture matrix | CORE | MUST_NOT_BREAK | HARD_CLEAN | No baseline | Missing artifacts/fixture/correct Draft state leaves closure incomplete | NO | NONE | NOT_RUN |
| C14 | Runtime-validated repeated candidate-profile sampling/selection; N≥3 distinct complete supported runs (N≥5 preferred), per-dimension stats | CORE | OUTCOME | HARD_CLEAN | Authorized evaluator required | Keep NOT_RUN during applicability adjudication; unresolved rubric → precise `BLOCKED/AUTHORITY`; unavailable model/hardware → `BLOCKED/ENVIRONMENT`; incomplete/unsupported sample is ineligible, no imputation | NO | NONE | NOT_RUN |
| C15 | Exact post-finalizer coverage/fidelity/source-tag/duplicate postcondition incl. high-risk novelty | CORE | OUTCOME | HARD_CLEAN | No baseline | Decisive mapped-required loss, confirmed unsupported addition or required duplicate → candidate FAIL/task regression; ambiguity/optional signal diagnostic only | NO | NONE | NOT_RUN |
| C16 | Failure classification: schema error permits exactly one schema-only repair; provider/transport/timeout/generation/cancellation do not | CORE | MUST_NOT_BREAK | HARD_CLEAN | New focused contracts | Wrong retry/error classification → task regression | NO | NONE | NOT_RUN |
| C17 | Profile evidence eligibility: repeats<3, replay/incomplete metrics/unsupported controls rejected; no default-zero dimensions | CORE | OUTCOME | HARD_CLEAN | New focused contracts | Ineligible evidence scopes C14 as `BLOCKED`/`NOT_RUN`; never gates unrelated records | NO | NONE | NOT_RUN |

Apply the Plan's canonical C9/C10/C14 aggregation. Stage04 with implementation complete plus a confirmed scoped blocker uses `CORE_ACCEPTANCE_STATUS: BLOCKED`, `REQUIRED_VERIFICATION_STATUS: INCOMPLETE` when other required evidence exists (otherwise `BLOCKED` only if the phase as a whole has no valid conclusion), `INDEPENDENT_ACCEPTANCE_STATUS: PENDING`, `TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED`. When merely not run and no blocker is known, use CORE `NOT_RUN` and `PENDING_CORE_ACCEPTANCE`. If Stage05 cannot conclude due a scoped blocker, preserve Stage04 implementation/core/required-verification values and its immutable snapshot; Stage05 records its own `INDEPENDENT_ACCEPTANCE_STATUS: BLOCKED`, `TASK_CLOSURE_STATUS: ACCEPTANCE_BLOCKED`. Every blocker names scope/subject, class, evidence, next action, owner and waiver policy. Only task closure is `DONE`.

## STOP_AND_ESCALATE_IF
Plan/review/handoff revision or hash mismatch; unclassified dirty path; unavailable/empty cloud baseline before shared behavior mutation; invalidated goal, source/C1 authority, root-cause, architecture, privacy/migration or other load-bearing premise; any change to validity/readiness, requiredness, gating, stable error/retry/fallback, priority, model selection or failure propagation; hidden V1 fallback/weakened validator; private/raw content in tracked or PR artifacts. Stop safely and use Stage01 replan + fresh Stage02 + regenerated Stage03 for a semantic change. A C1 preflight uncertainty is scoped `BLOCKED/AUTHORITY` with no model call; Gemma/evaluator blockers stay scoped to their checks, never self-waived.

## HISTORICAL_TASK_DEPENDENCIES
Same task only: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/execution.md` for the R13 implementation/status snapshot (preserve as historical); `baseline/claim-attempt-3-baseline.json` and `e2e/attempt-01/e2e_report.md` for established first-divergence/inversion evidence; Stage04 escalation/execution follow-up and Stage05 attempts 06–10 for already established provenance, architecture, and carried-forward verification results. Review attempt17 is the controlling R17 approval. R16 execution did not verify Ollama capability semantics; do not treat it as R17 acceptance. Do not repeat settled diagnosis or treat prior candidate/synthetic evidence as R17 acceptance.

TASK_ID: T20260924-1523-01-issue18-local-fidelity
HANDOFF_PATH: .agent/tasks/T20260924-1523-01-issue18-local-fidelity/handoff.md
PLAN_REVISION: 17
STATUS: READY_FOR_IMPLEMENTATION
NEXT_STAGE: 04_IMPLEMENT
