# Independent Acceptance Report

## RUN_METADATA
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- PLAN_REVISION: 4
- PLAN_SHA256: 72d23f2facf0a88b12ec2f18a6850db011a2ff0dd9e15cefa1037bc230220c89
- HANDOFF identity: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/handoff.md`; PLAN_REVISION 4; PLAN_SHA256 72d23f2facf0a88b12ec2f18a6850db011a2ff0dd9e15cefa1037bc230220c89; handoff SHA-256 16825d49c983a37e4034ee050032e8e3b6f88b85a9183aa9c85ad21de6263a4d
- Attempt: 01
- Acceptance mode: CONTRACT + INTEGRATION + E2E + BLIND_RUBRIC (E2E and blind portions blocked/failed as detailed below)
- Environment/runtime: macOS; branch `issue-18-first-divergence-diagnostic`; HEAD `eb3ca049cc72d21d2f4db974db5314b5f399d736`; Python/uv repository environment; fresh writable process-scoped `DATA_DIR` for test commands.
- Commands/actions/timestamps: see `evidence/acceptance_commands.txt`, executed 2026-09-24 19:35–19:36 Asia/Taipei.

## STAGE_04_SNAPSHOT
STAGE_04_REPORTED_IMPLEMENTATION_STATUS: COMPLETE
STAGE_04_REPORTED_CORE_ACCEPTANCE_STATUS: BLOCKED
STAGE_04_REPORTED_REQUIRED_VERIFICATION_STATUS: INCOMPLETE
STAGE_04_EXECUTION_ARTIFACT_SHA256: 8121cea64f47b96003ae069abb18d115913d48bad83b03b87c89dcb37a2be0bc

The snapshot is immutable carry-forward from the Stage 04 execution record observed before acceptance execution. Current findings do not rewrite it.

## GOAL_ALIGNMENT_CHECK
The authoritative attachment and approved revision 4 require an opt-in live V2 source→typed facts→ledger→section render→delivery path, selected causal claim correctness, no hidden V1 fallback, cloud/privacy invariants, fresh Gemma/Qwen E2E, and frozen blind 3+3 quality acceptance. The contract remains the correct target. The current implementation contains the requested primitives and dispatch, but the selected causal firewall contract is not actually enforced.

## ACCEPTANCE_CONTRACT
CORE: selected causal source-to-delivery fidelity, strict schema/ledger behavior, A–I regression coverage, explicit v1/v2 behavior, live v2 dispatch, cloud/privacy invariants, fresh model E2E and blind quality gate.
SUPPORTING: full repository/docs health, runtime/profile diagnostics and held-out data. Repository/docs checks are still required closure gates per the approved DoD; they are not substitutes for CORE outcome acceptance.
BEST_EFFORT/non-gating: optional enrichment, performance diagnostics, held-out private data, unsupported optional runtime controls.
Global blockers are scoped: missing local models blocks C9/C14; missing frozen evaluator and unrounded Gemini baselines blocks C10; the selected causal firewall defect blocks CORE acceptance because it allows an inverted predicate to be accepted.

## CORE_CRITICAL_PATH_RESULTS
- C1 selected causal source→facts→render→delivery: FAIL (conclusive implementation defect). A deterministic probe built a typed causal claim whose source contained `subject + expected predicate + object`; rendered output contained subject/object but a different predicate. `fidelity_firewall(..., selected_claim_id=...)` returned `accepted=True`, `relation_issues=()`, and `source_trace_complete=True`. The implementation's condition `claim_id not in rendered` skips relation checks because `render_section` does not render claim IDs. The live V2 call also invokes `fidelity_firewall` without `selected_claim_id`. This is a load-bearing semantic/gating defect; route `PLANNER_REPLAN`.
- C2 synthetic A–I and contract suite: PASS, 9 passed. This validates the isolated primitives/tests but does not override the C1 integration defect.
- C3 cloud focused contract: PASS under writable process-scoped DATA_DIR, 13 passed/41 deselected. Existing default `/app/data/logs` read-only failure remains an environment baseline issue documented in the task baseline; no cloud code was changed by the implementation diff.
- C4 privacy/tracked artifacts: PASS for this attempt; see `evidence/privacy_audit.txt`.
- C9 fresh Gemma/Qwen E2E: PARTIAL/BLOCKED. A later LM Studio inventory observation found Qwen loaded and Gemma listed but not loaded. The synthetic Qwen V2 invocation executed through the live dispatch and returned an output (length/hash recorded without content). The Gemma invocation was attempted and returned `LMSTUDIO_MODEL_NOT_LOADED`; no Gemma generation executed. The earlier empty Ollama result is retained only as a time-scoped observation.
- C10 blind Gemma×3 + Qwen×3: BLOCKED by quality acceptance input. The required frozen scorer/protocol and original unrounded Gemini baselines are absent; only rounded medians are referenced historically. Exact label: `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`.
- C14 repeated candidate profiles: BLOCKED/INCOMPLETE. Three repeated Qwen V2 baseline invocations at the implementation's fixed temperature 0.3 completed, but the required candidate controls/0.3, 0.5, 0.7 comparison and per-candidate statistics could not be executed because the live V2 path hardcodes temperature 0.3 and has no profile-selection wiring. Gemma candidate samples were blocked by no loaded instance.

## DEGRADATION_AND_GATE_RESULTS
- Explicit V1/V2 selector: static audit confirms `LOCAL_PIPELINE_VERSION` defaults to `v1`, validates only `v1|v2`, and dispatches V2 only on explicit `v2`; V2 exceptions are not converted to V1 in the dispatch branch. Isolated contract test passes.
- Schema-only repair/no hidden fallback: static audit and isolated tests show one repair attempt and explicit `LocalPipelineV2Error` after the second invalid result. The live Qwen run exercised the normal structured path, but did not force the invalid-schema repair branch.
- Evidence/ledger/render path: isolated primitives and tests pass, but live selected-claim gate integration fails as reported in C1. This is not a safe optional degradation because it affects the required core relation.
- Optional enrichment/profile unsupported controls/held-out data remain non-gating per handoff.

## TEST_MATRIX

| CHECK_ID | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | BASELINE_REQUIRED | FAILURE_CLASSIFICATION_RULE | WAIVER_ALLOWED | WAIVER_AUTHORITY | CHECK_RESULT | WAIVER_STATUS |
|---|---|---|---|---|---|---|---|---|---|
| C1 | CORE | OUTCOME | HARD_CLEAN | NO | Inversion/omission of selected relation is CORE failure; semantic gate defect routes PLANNER_REPLAN | NO | NONE | FAIL | NOT_ALLOWED |
| C2 | CORE | OUTCOME | HARD_CLEAN | NO | Changed contract failure = TASK_REGRESSION | NO | NONE | PASS | NOT_ALLOWED |
| C3 | CORE | MUST_NOT_BREAK | HARD_CLEAN | YES | Safe-env contract passes; default logger path is scoped environment baseline issue | NO | NONE | PASS (safe env); BLOCKED (default env baseline) | NOT_ALLOWED |
| C4 | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | Raw private content/artifact is invariant violation | NO | NONE | PASS | NOT_ALLOWED |
| C5 | CORE | OUTCOME | HARD_CLEAN | NO | Changed-path failure = TASK_REGRESSION | NO | NONE | PASS (covered by full suite) | NOT_ALLOWED |
| C6 | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | YES | Separate baseline debt from task regression | NO | NONE | PASS (826 passed, 2 skipped) | NOT_ALLOWED |
| C7 | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | YES | Unresolved docs check keeps closure pending | NO | NONE | PASS with 2 pre-existing warnings | NOT_ALLOWED |
| C8 | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | NO | Diff whitespace failure requires fix | NO | NONE | PASS | NOT_ALLOWED |
| C9 | CORE | OUTCOME | HARD_CLEAN | NO | Missing model/backend = environment BLOCKED; hidden fallback/model failure = FAIL | NO | NONE | BLOCKED | NOT_ALLOWED |
| C10 | CORE | OUTCOME | HARD_CLEAN | YES | Missing frozen evaluator/baseline = scoped quality BLOCKED | NO | NONE | BLOCKED | NOT_ALLOWED |
| C11 | SUPPORTING | DIAGNOSTIC | NON_GATING | NO | Report observed overhead; absent runtime is non-gating | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C12 | SUPPORTING | DIAGNOSTIC | NON_GATING | NO | Missing safe held-out source is disclosed only | NO | NONE | NOT_RUN (no safe held-out source supplied) | NOT_ALLOWED |
| C13 | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | Missing durable evidence leaves closure incomplete | NO | NONE | INCOMPLETE (parent-owned execution/PR update remains) | NOT_ALLOWED |
| C14 | CORE | OUTCOME | HARD_CLEAN | NO | Missing runtime/hardware or absent candidate controls = scoped BLOCKED/INCOMPLETE | NO | NONE | BLOCKED/INCOMPLETE | NOT_ALLOWED |

## EXECUTION_SUMMARY
Observed checks: C2 9 passed; C3 safe-env 13 passed/41 deselected; C5/C6 full suite 826 passed/2 skipped; C7 exit 0 with 2 warnings; C8 clean. Qwen live V2 synthetic invocation completed; Gemma was attempted but not loaded. Three Qwen fixed-profile repeats completed; no candidate-profile comparison or blind cohort was fabricated. Privacy audit passed. The deterministic C1 probe found a conclusive selected-causal-gate defect.

## ANOMALIES
1. `fidelity_firewall` only enters its relation/attribution checks when `claim_id in rendered`. `render_section` emits no claim ID, so this condition is false for normal V2 output. Even when a caller supplies `selected_claim_id`, a predicate inversion can be accepted if subject/object and evidence ref remain present.
2. `_summarize_with_local_pipeline_v2` calls `fidelity_firewall` without `selected_claim_id`, so the required selected relation is not wired as a record-level veto.
3. The live V2 extraction prompt requests only claim_id, subject, predicate, object, relation_type, polarity, and evidence_refs. Although `FactClaim` accepts condition/number/unit/date/attribution/uncertainty, the live extraction contract does not request them. The isolated C-test constructs these fields directly and therefore does not prove model extraction preserves them.
4. No live V2 implementation symbol or test covers transcript-derived coverage, an entity registry/provenance layer, source-tag validation, or template-scoped term corrections. `plan_sections` hardcodes three generic titles and receives no template; its only duplicate detection is line duplication within one rendered section. Global fingerprint dedupe exists, but the required cross-section duplicate audit/template coverage is not live-wired.
Classification: product semantic/acceptance-contract gaps, not verifier defects. The selected-gate defect affects core validity/gating/failure propagation and routes `PLANNER_REPLAN`; the missing live extraction/coverage/template mechanisms must be addressed in that replan or explicitly reconciled against the approved contract.

## REGRESSION_RESULTS
Cloud-focused tests, full suite, docs check and diff check passed in the safe process-scoped environment. No cloud shared helper was modified in the current product diff. Default logger collection remains blocked by `/app/data/logs` permissions as previously recorded. The isolated V2 suite and one live Qwen run pass, but the live selected-gate integration is defective and Gemma/blind/profile acceptance is incomplete; therefore CORE acceptance is not established.

## ROUTING_DECISION
The selected causal acceptance premise is invalidated by observed implementation behavior. Per Stage 05 precedence, current implementation status is escalated and task closure requires replan. Do not self-waive the defect. Parent delivery role must replan/review/reimplement the selected-causal firewall wiring, then create a fresh Stage 05 attempt and rerun C1 before relying on any model-quality result.

## RESIDUAL_RISK
- `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`: frozen scorer/protocol and original unrounded Gemini baselines are absent; rounded medians are not sufficient.
- `BLK-MODEL`: Qwen live instance was available and exercised; Gemma required model was listed but not loaded, so the Gemma half of C9/C14 remains blocked.
- Live profile controls/selection are absent: fixed extraction temperature 0.3 prevented the approved Qwen A/B profile comparison.
- C13 PR/execution durable update remains parent-owned.
- The C1 semantic defect means no claim of end-to-end selected causal correctness is valid from this attempt.

PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: ESCALATED
CORE_ACCEPTANCE_STATUS: FAIL
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: FAIL
TASK_CLOSURE_STATUS: REPLAN_REQUIRED
NEXT_ACTION: PLANNER_REPLAN for selected-causal firewall wiring; after approved replan/reimplementation, rerun C1 and all affected degradation/regression checks. Independently obtain active Gemma/Qwen runtime and frozen evaluator/unrounded Gemini baseline for C9/C10/C14.
REPORT_PATH: .agent/tasks/T20260924-1523-01-issue18-local-fidelity/e2e/attempt-01/e2e_report.md
