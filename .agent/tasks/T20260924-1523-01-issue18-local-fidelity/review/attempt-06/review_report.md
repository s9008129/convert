# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 06
- REVIEWED_PLAN_REVISION: 7
- REVIEWED_PLAN_SHA256: 24d1eddaf2ab494d0b424f1e72f30edbcac02b4a599ea3ae5bad482f8724fb87
- PLAN_SNAPSHOT_PATH: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-06/plan_snapshot.md`
- Repository anchor observed: branch `issue-18-first-divergence-diagnostic`, HEAD `eb3ca049cc72d21d2f4db974db5314b5f399d736` (`eb3ca04`)
- Working tree observed: dirty with the expected Stage 04 candidate and task artifacts; no reset, clean, stash, or overwrite was performed.
- Reviewer runtime/model: Codex GPT-5
- Review mode: read-only for product code and canonical `plan.md`; only attempt-06 review artifacts were written.

## OWNER_VERDICT

Revision 7 remains aligned with the requested Local Meeting Record Architecture V2: immutable raw evidence, typed claims/ledger, deterministic consolidation and source alignment, section-scoped generation, guarded patch/rollback, controlled Gemma/Qwen execution, and fresh blind quality acceptance. It also resolves the two prior findings: the dirty worktree is now explicitly acknowledged and delegated to a Stage 04 W0 classification, and runtime profiles/sampling are consistently CORE for controlled acceptance/task closure while not vetoing unrelated records.

The plan is not yet ready for Handoff. The new C9/C10/C14 prose now gives item-level `CHECK_RESULT: BLOCKED`, blocker scope, and an aggregate required-verification rule, but it still does not state how these `CORE`/`OUTCOME`/`HARD_CLEAN` items map to `CORE_ACCEPTANCE_STATUS` at Stage 04. The plan simultaneously routes a missing model/evaluator to `REQUIRED_VERIFICATION_STATUS: INCOMPLETE` and `TASK_CLOSURE_STATUS: PENDING_REQUIRED_VERIFICATION`, while v4.2 Stage 04 precedence requires `CORE_ACCEPTANCE_STATUS: BLOCKED` to route to `CORE_ACCEPTANCE_BLOCKED` when a CORE acceptance item cannot conclude. This remains a material orthogonal-status contradiction, not a preference about naming.

## GOAL_BASELINE

- **Primary outcome:** redesign the local Gemma 4 31B/Qwen 3.8 27B meeting-record pipeline around immutable raw-source evidence, structured fact/evidence architecture, deterministic validation, and controlled generation, reaching the fresh blind quality target with zero major fidelity hard fails.
- **Success evidence:** selected causal claim correctness source→facts→render→delivery; regression coverage; cloud/template/privacy invariants; fresh Gemma/Qwen E2E; and blind 3+3 where every output/dimension reaches at least 0.80 of the original unrounded Gemini median with zero adjudicated major hard fails.
- **Must not break:** cloud semantics, v4.7.4 invariants, template/output contracts, privacy/provenance, retry/runtime-selection safety, explicit degradation and V1 rollback.
- **Non-goals:** direct experimental-branch merge, hard-coded private facts, tracked raw content, a second LLM truth oracle, lowered quality threshold, broad ASR/UI work.
- **Smallest safe critical path:** evidence/schema → validated structured extraction → deterministic ledger/conflict handling → raw-evidence source-alignment firewall → template-derived section render/assembly → guarded targeted patch/rollback → selected-claim live E2E → fresh model and blind acceptance.

## GOAL_ALIGNMENT

The plan's primary outcome and critical path match the authoritative user request. R1–R7, R9–R10, and R12 directly serve source fidelity, semantic preservation, rollback, requested model acceptance, privacy, and durable delivery. R8 and C14 remain justified because the request explicitly requires separate Gemma/Qwen runtime controls and repeated sampling for stable quality selection. Supporting performance/held-out work remains non-gating.

The plan correctly treats the Stage 05 causal-predicate inversion as a live-boundary architecture defect. It does not revert to the disproven prompt-only recovery strategy or introduce unrelated product scope.

## NECESSITY_AND_TRACEABILITY

Evidence spans, typed claims, ledger consolidation, section planning, rendered relation metadata, the firewall, targeted patching, runtime profiles, and diagnostics each have a stated fidelity, provenance, rollback, or acceptance contribution. Unknown/ambiguous facts remain representable. Experimental branches remain read-only mechanism sources rather than merge targets.

## GATE_AND_VETO_AUDIT

RV5-001 is resolved: META and SOURCE_OF_TRUTH_AND_BASELINE consistently describe the dirty Stage 04/task tree, and W0 requires a timestamped redacted status/path classification before mutation, with escalation for unclassified paths.

RV5-002 is resolved: OWNER_CHECK, R8, the contribution matrix, W7/W8, C14, and the Definition of Done consistently make profile wiring/sampling required for controlled acceptance/task closure, while explicitly forbidding per-record vetoes. Selected/core evidence and causal correctness retain scoped veto authority with source-fidelity rationale; optional enrichment and diagnostics remain locally degrading/non-gating.

The remaining gate issue is the C9/C10/C14 status mapping described in RV7-001 below. A CORE outcome check can be closure-required without invalidating unrelated records, but the plan must still declare whether its unresolved result contributes to `CORE_ACCEPTANCE_STATUS`, `REQUIRED_VERIFICATION_STATUS`, or both, and which v4.2 precedence route applies.

## COUPLING_AND_FAILURE_CONTAINMENT

The failure scope is otherwise appropriately narrow: optional evidence/enrichment remains local; selected/core claim failures affect the relevant section/record and CORE acceptance; runtime/model/evaluator blockers affect the applicable acceptance scope and task closure, not unrelated records or implementation status. The unresolved CORE-versus-required-verification mapping could still cause agents to couple or uncouple the wrong aggregate status.

## DESIGN_ECONOMY

The architecture passes the deletion test at plan level. The added moving parts address observed information-integrity failures or explicit acceptance obligations; W1–W6 prioritize the causal defect before profile and blind-quality work. No wholesale experimental mechanism port or second judge is authorized.

## CRITICAL_PATH_AND_PRIORITY

W0 protection/baseline, W1–W6 source-fidelity implementation, and W7–W9 controlled runtime acceptance/delivery are ordered correctly. The plan does not let missing authority fabricate a quality result. The remaining status ambiguity must be fixed before implementation because it affects Stage 04/05 routing, not because the runtime work should be expanded.

## REQUIREMENT_FIDELITY

The plan preserves the requested full typed extraction fields, immutable raw evidence, deterministic conflicts, template-derived per-section rendering, live source-alignment checks, guarded patch rollback, Qwen/Gemma controls, repeated samples, blind 3+3 threshold, privacy, and Draft PR continuity. It does not lower the 80%/zero-major-fail requirement.

## GROUNDING_AND_DRIFT

The branch, HEAD, prior Stage 05 evidence, and dirty-tree facts are grounded in observed repository state. The current plan is revision 7 with the expected SHA and does not inherit prior approval. Existing Stage 04/05 artifacts remain historical evidence and are not treated as acceptance for this revision.

## ARCHITECTURE_AND_CONTRACTS

The source→structured→ledger→section-render contract is explicit, including relation metadata outside prose so validation cannot depend on claim-ID substring presence. V1 remains an explicit development rollback, cloud behavior is protected by a focused baseline, and live boundary evidence is required. The unresolved contract is status aggregation for CORE E2E/quality/profile checks blocked by environment or authority.

## DATA_SECURITY_RELIABILITY

Raw transcript/full prompt/output retention remains runtime-local/ignored, with tracked diagnostics limited to metadata. The plan preserves fail-loud schema handling, deterministic conflicts, patch rollback, loaded-instance authority, retry safety, and no silent V1 fallback. No migration or destructive operation is proposed.

## IMPLEMENTATION_SEQUENCE

W0 correctly precedes mutation and requires classification of the dirty tree. W1–W6 prove the source-fidelity path before W7–W9 runtime/quality selection. Handoff and Stage 04 must remain deferred until this review gate is resolved.

## TESTABILITY_AND_ACCEPTANCE

C1/C2 require the live causal inversion probe rather than helper-only tests. C3–C8 cover cloud, privacy, focused/full/docs, and diff checks. C9 covers fresh loaded-model E2E. C10/C14 now specify the missing-authority/environment `CHECK_RESULT`, scope, exact quality blocker label, and aggregate required-verification behavior. However, because C9/C10/C14 are also `CORE` + `OUTCOME` + `HARD_CLEAN`, the plan must explicitly specify their Stage 04 `CORE_ACCEPTANCE_STATUS` consequence and the precedence between `CORE_ACCEPTANCE_BLOCKED` and `PENDING_REQUIRED_VERIFICATION`.

## SCOPE_AND_COMPLEXITY

Scope is large but justified by the requested architecture-level redesign and the proven live-boundary defect. Profile/evaluator work is bounded to acceptance/task closure, and held-out/performance work remains non-gating. No unnecessary dependency or branch merge is specified.

## FINDINGS

### RV7-001 — MAJOR — CORE C9/C10/C14 BLOCKED RESULTS STILL LACK ORTHOGONAL CORE-ACCEPTANCE ROUTING

- **Category:** SEMANTIC_CONTRACT / TEST
- **Affected plan sections:** W7; W8; `VERIFICATION_AND_CLOSURE_MATRIX` rows C9, C10, C14; `BLOCKING_AND_NON_BLOCKING_UNKNOWNS`; `DEFINITION_OF_DONE`; `HANDOFF_HINTS`.
- **Evidence:** C9, C10, and C14 are each `GOAL_CRITICALITY: CORE`, `EVIDENCE_ROLE: OUTCOME`, and `CLOSURE_GATE: HARD_CLEAN`. Revision 7 now correctly says missing model/evaluator/baseline yields item-level `CHECK_RESULT: BLOCKED` and may yield aggregate `REQUIRED_VERIFICATION_STATUS: INCOMPLETE`; W7/W8 then prescribe Stage 04 `INDEPENDENT_ACCEPTANCE_STATUS: PENDING` plus `TASK_CLOSURE_STATUS: PENDING_REQUIRED_VERIFICATION`, or Stage 05 `INDEPENDENT_ACCEPTANCE_STATUS: BLOCKED` plus `TASK_CLOSURE_STATUS: ACCEPTANCE_BLOCKED`. It does not say whether a blocked CORE outcome item makes `CORE_ACCEPTANCE_STATUS: BLOCKED`, `NOT_RUN`, or leaves CORE acceptance satisfied by the other C1–C5 evidence.
- **Failure/rework mechanism:** Under workflow-routing §7.7, implementation complete plus `CORE_ACCEPTANCE_STATUS: BLOCKED` routes to `TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED`; under §7.7 #9, implementation complete plus CORE closure-satisfied and unresolved required verification routes to `PENDING_REQUIRED_VERIFICATION`. Both are plausible from the current plan. Stage 04/05 can therefore produce contradictory or non-canonical states (for example item C10 `CHECK_RESULT: BLOCKED` while aggregate CORE is `PASS`, or use `PENDING_REQUIRED_VERIFICATION` when a CORE block requires `CORE_ACCEPTANCE_BLOCKED`). The same ambiguity recurs for C9 unavailable runtime and C14 unavailable profile/evaluator. This can lead to incorrect closure, an unapproved self-waiver, or unnecessary implementation downgrade, violating the v4.2 orthogonal status contract.
- **Smallest required correction:** Decide and state the exact aggregation rule before Handoff. At minimum, for each C9/C10/C14 blocker specify (a) whether the affected item contributes to `CORE_ACCEPTANCE_STATUS` or only required verification/independent acceptance, (b) the exact Stage 04 six-field state, including `CORE_ACCEPTANCE_STATUS`, aggregate `REQUIRED_VERIFICATION_STATUS`, and `TASK_CLOSURE_STATUS`, and (c) the exact Stage 05 state while preserving the immutable Stage 04 snapshot. If these checks are closure-only acceptance prerequisites despite `CORE`, say so explicitly and route them through `PENDING_REQUIRED_VERIFICATION`/`ACCEPTANCE_BLOCKED`; otherwise route them through `CORE_ACCEPTANCE_BLOCKED`. Preserve `CHECK_RESULT: BLOCKED`, blocker scope (`AUTHORITY`/`ENVIRONMENT`), and no-waiver policy in either case. Increment the plan revision and obtain a fresh review.

## REQUIRED_PLAN_CHANGES

1. Define the missing orthogonal `CORE_ACCEPTANCE_STATUS` aggregation and Stage 04/05 routing for blocked C9/C10/C14, without changing the user's quality requirement or per-record failure scope.
2. Increment `PLAN_REVISION` by exactly one on the same TASK_ID and obtain a fresh Stage 02 review. Do not regenerate Handoff or implement product changes from this unapproved revision.

## RESIDUAL_MINOR_NOTES

- W0's dirty-tree classification and backup relation are correctly assigned to Stage 04 before mutation.
- Runtime controls match the authoritative request: Qwen `thinking=OFF, temperature=0.7, top_p=0.8, top_k=20`; extraction candidates `0.3/0.5/0.7`; Gemma `thinking=OFF, temperature=1.0, top_p=0.95, top_k=64`; N≥5 preferred/N=3 minimum.
- C10/C14 retain the exact missing-frozen-evaluator label, prohibit rounded-baseline substitution, and prohibit self-waiver.
- This review binds only to revision 7 and SHA `24d1eddaf2ab494d0b424f1e72f30edbcac02b4a599ea3ae5bad482f8724fb87`.

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 revision mode on the same TASK_ID; define C9/C10/C14 CORE_ACCEPTANCE_STATUS aggregation and exact Stage 04/05 routing, increment to PLAN_REVISION 8, then obtain a fresh Stage 02 review.
