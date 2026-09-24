# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 05
- REVIEWED_PLAN_REVISION: 6
- REVIEWED_PLAN_SHA256: f7d390adeafbab7e39be1f68254bbbf10daa752969417dd6a1c8f3a322c35652
- PLAN_SNAPSHOT_PATH: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-05/plan_snapshot.md`
- Repository anchor observed: branch `issue-18-first-divergence-diagnostic`, HEAD `eb3ca049cc72d21d2f4db974db5314b5f399d736` (`eb3ca04`)
- Working tree observed: dirty with the expected Stage 04 product candidate and task artifacts; no reset, clean, stash, or overwrite was performed.
- Reviewer runtime/model: Codex GPT-5
- Review mode: read-only for product code and canonical `plan.md`; only attempt-05 artifacts were written.

## OWNER_VERDICT

Revision 6 is substantially responsive to the prior review. It correctly records the dirty replan state, assigns the Stage 04 W0 status/path snapshot to the next implementation wave, and consistently treats runtime profile wiring and repeated candidate sampling as required for controlled acceptance/task closure without making them per-record vetoes. The core architecture remains aligned with the user's source-grounded local V2 goal, and the previous implementation's causal-inversion defect is directly addressed.

The plan is not yet ready for Handoff because missing evaluator/baseline or unavailable runtime evidence is not fully mapped to the v4.2 orthogonal status fields for the required verification item itself. C10/C14 are `HARD_CLEAN` closure gates, but their prose primarily names `INDEPENDENT_ACCEPTANCE_STATUS: BLOCKED` or a scoped E2E blocker while leaving `CHECK_RESULT`, `REQUIRED_VERIFICATION_STATUS`, and the resulting closure state implicit. This can cause Stage 04/05 to report a legal acceptance blocker while incorrectly leaving required verification `NOT_RUN`, `PASS`, or otherwise unresolved without the required `INCOMPLETE/BLOCKED` routing.

## GOAL_BASELINE

- **Primary outcome:** redesign the local Gemma 4 31B/Qwen 3.8 27B meeting-record pipeline around immutable raw-source evidence, structured fact/evidence architecture, deterministic validation, and controlled generation, reaching the fresh blind quality target with zero major fidelity hard fails.
- **Success evidence:** selected causal claim correctness source→facts→render→delivery; regression coverage; cloud/template/privacy invariants; fresh Gemma/Qwen E2E; and blind 3+3 where every output/dimension reaches at least 0.80 of the original unrounded Gemini median with zero adjudicated major hard fails.
- **Must not break:** cloud semantics, v4.7.4 invariants, template/output contracts, privacy/provenance, retry/runtime-selection safety, explicit degradation and V1 rollback.
- **Non-goals:** direct experimental-branch merge, hard-coded private facts, tracked raw content, a second LLM truth oracle, lowered quality threshold, broad ASR/UI work.
- **Smallest safe critical path:** evidence/schema → validated structured extraction → deterministic ledger/conflict handling → raw-evidence source-alignment firewall → template-derived section render/assembly → guarded targeted patch/rollback → selected-claim live E2E → fresh model and blind acceptance.

## GOAL_ALIGNMENT

The plan's primary outcome, critical path, and acceptance evidence match the authoritative request. R1–R7, R9–R10, and R12 directly support source fidelity, semantic preservation, rollback, requested model acceptance, privacy, and durable delivery. R8 is appropriately retained because the request explicitly requires controlled Gemma/Qwen execution and variance-aware quality selection. R11/C11 and R12's optional held-out/performance portions remain supporting or non-gating where applicable.

The Stage 05 causal inversion is correctly treated as a live-boundary defect and not as a prompt-only problem. No new unrelated product objective is introduced.

## NECESSITY_AND_TRACEABILITY

The evidence span, typed ledger, deterministic consolidation, section plan, relation metadata, firewall, targeted patch, profile controls, and diagnostics each have an explicit contribution to a stated fidelity, provenance, rollback, or acceptance obligation. Unknown/ambiguous facts remain representable rather than being silently asserted. The plan also keeps experimental branches as read-only mechanism sources rather than merge targets.

## GATE_AND_VETO_AUDIT

RV5-002 is corrected. OWNER_CHECK, R8, the contribution matrix, W7/W8, C14, and the Definition of Done now consistently state that runtime profiles and repeated candidate sampling are CORE for controlled acceptance/task closure, but do not veto an unrelated valid record or section. Selected/core evidence, schema validity, and selected causal correctness retain scoped veto authority with explicit source-fidelity rationale. Optional enrichment, held-out data, unsupported controls, and performance diagnostics remain locally degrading or non-gating.

One status-routing gap remains: the plan does not state the required-verification result/aggregate when a `HARD_CLEAN` C10/C14 check cannot obtain a valid evaluator or baseline. A scoped independent-acceptance blocker alone does not define the material required-verification item or closure route.

## COUPLING_AND_FAILURE_CONTAINMENT

Failure scope is generally narrow: optional evidence and enrichment remain local; required claim failures affect the selected section/record and CORE acceptance; runtime/model availability affects only the applicable E2E/profile acceptance. The profile rule avoids global per-record coupling. The remaining evaluator status gap could couple implementation and closure incorrectly if Stage 04/05 lacks a prescribed orthogonal result.

## DESIGN_ECONOMY

The plan passes the deletion test at plan level. Its additional moving parts address observed failures or explicit acceptance obligations; W1–W6 prioritize the proven causal defect before profile/quality selection. No wholesale experimental-branch port or second judge is authorized.

## CRITICAL_PATH_AND_PRIORITY

W0 protects the dirty tree and establishes baselines, W1–W6 implement and prove the source-fidelity path, and W7–W9 perform controlled runtime acceptance and delivery. This ordering is appropriate. The missing evaluator is correctly not fabricated, but its required-verification consequence must be made explicit before implementation.

## REQUIREMENT_FIDELITY

The revision preserves the user's requirements: full typed extraction fields, immutable raw evidence, deterministic conflict handling, per-section rendering, source-alignment checks, targeted rollback, Qwen/Gemma controls, repeated sampling, blind 3+3 thresholds, privacy, and Draft PR continuity. It does not relax the 80%/zero-major-fail target.

## GROUNDING_AND_DRIFT

The plan is grounded in the observed branch/HEAD and Stage 05 attempt-01 evidence. META and SOURCE_OF_TRUTH_AND_BASELINE no longer claim a clean planning worktree. W0 requires a timestamped redacted status/path classification before mutation and stops on unclassified paths, addressing RV5-001. Stage 04 must re-check rather than infer absence of owner changes.

## ARCHITECTURE_AND_CONTRACTS

The source-to-structured-to-ledger-to-section-render contract is explicit, including relation metadata outside prose so validation cannot depend on claim-ID substring presence. V1 remains explicit and default during development; cloud behavior is protected by focused baseline/golden requirements. The remaining contract ambiguity is status routing for unavailable evaluator/baseline on C10/C14.

## DATA_SECURITY_RELIABILITY

Raw transcript/full prompt/output retention remains local/ignored; tracked diagnostics are metadata-only. The plan preserves fail-loud schema behavior, deterministic conflict handling, patch rollback, loaded-instance context authority, retry safety, and no silent V1 fallback. No new data migration or destructive operation is proposed.

## IMPLEMENTATION_SEQUENCE

The sequence is safe and reviewable after the status correction: W0 classification/baseline, fail-first contracts, architecture, live integration, then runtime and blind acceptance. Handoff must remain deferred until the plan is revised and reviewed again.

## TESTABILITY_AND_ACCEPTANCE

C1/C2 require the live causal inversion probe through the actual gate, not helper-only tests. C3–C8 cover cloud, privacy, focused/full/docs, and diff checks. C9 covers fresh loaded-model E2E. C10/C14 correctly require frozen baseline/evaluator and repeated profile statistics, but their missing-input outcomes need explicit v4.2 fields and routing.

## SCOPE_AND_COMPLEXITY

Scope is large but justified by the requested architecture-level redesign and the prior live-boundary failure. Profile and evaluator work is constrained to acceptance/task closure; held-out/performance work remains non-gating. No unnecessary dependency or branch merge is specified.

## FINDINGS

### RV6-001 — MAJOR — HARD_CLEAN EVALUATOR/BASELINE BLOCKER LACKS REQUIRED-VERIFICATION ROUTING

- **Category:** SEMANTIC_CONTRACT / TEST
- **Affected plan sections:** `VERIFICATION_AND_CLOSURE_MATRIX` rows C10 and C14; W7; W8; `BLOCKING_AND_NON_BLOCKING_UNKNOWNS`; `DEFINITION_OF_DONE`; `HANDOFF_HINTS`.
- **Evidence:** C10 says a missing evaluator/baseline is “scoped BLOCKED”; C14 says missing evaluator is `INDEPENDENT_ACCEPTANCE_STATUS: BLOCKED` and unavailable model/hardware is a scoped E2E acceptance blocker. W8 similarly says these items block the corresponding acceptance and task closure. However, C10/C14 are `GOAL_CRITICALITY: CORE`, `EVIDENCE_ROLE: OUTCOME`, `CLOSURE_GATE: HARD_CLEAN`, `BASELINE_REQUIRED: YES`, with `CHECK_RESULT: NOT_RUN`, and the plan does not prescribe the item-level `CHECK_RESULT` plus aggregate `REQUIRED_VERIFICATION_STATUS`/`TASK_CLOSURE_STATUS` for a missing authority or environment result.
- **Failure/rework mechanism:** Stage 04/05 can preserve an independent-acceptance blocker but leave a required HARD_CLEAN gate as `NOT_RUN`, or incorrectly mark required verification `PASS`/implementation `BLOCKED`. This violates the v4.2 orthogonal status contract, obscures whether closure is `PENDING_REQUIRED_VERIFICATION`, `CORE_ACCEPTANCE_BLOCKED`, or `ACCEPTANCE_BLOCKED`, and can cause later agents to fabricate a waiver or Done state.
- **Smallest required correction:** For C10 and C14, explicitly state that missing frozen evaluator/original unrounded baseline yields `CHECK_RESULT: BLOCKED` (or aggregate `REQUIRED_VERIFICATION_STATUS: BLOCKED/INCOMPLETE` when other required evidence exists), preserves implementation/CORE facts, sets the corresponding independent-acceptance status to `BLOCKED` when acceptance cannot run, and routes task closure to the exact scoped pending/blocked state. For unavailable model/hardware, prescribe the same item-level result and distinguish `ENVIRONMENT` scope from `INDEPENDENT_ACCEPTANCE`; do not self-waive. Keep the original missing-authority evidence label and no-waiver policy.

## REQUIRED_PLAN_CHANGES

1. Add explicit v4.2 item-level and aggregate status routing for missing evaluator/baseline and unavailable model/hardware in C10/C14/W7/W8, preserving orthogonal Stage 04/05 facts and scoped blocker subjects.
2. Increment `PLAN_REVISION` by exactly one on the same TASK_ID and obtain a fresh Stage 02 review. Do not regenerate Handoff or implement product changes from this unapproved revision.

## RESIDUAL_MINOR_NOTES

- W0's status/path snapshot and backup relation are correctly assigned to Stage 04 before mutation; the planner did not overwrite the canonical plan with a generated snapshot.
- C3's same-command baseline and safe-environment distinction are appropriately explicit.
- The runtime profile controls and sampling counts match the authoritative request: Qwen `thinking=OFF, temperature=0.7, top_p=0.8, top_k=20`; extraction candidates `0.3/0.5/0.7`; Gemma `thinking=OFF, temperature=1.0, top_p=0.95, top_k=64`; N≥5 preferred/N=3 minimum.
- The approval, if obtained later, would bind only to revision 6 and SHA `f7d390adeafbab7e39be1f68254bbbf10daa752969417dd6a1c8f3a322c35652`.

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 revision mode on the same TASK_ID; add explicit C10/C14 missing-evaluator/baseline/runtime status routing, increment to PLAN_REVISION 7, then obtain a fresh Stage 02 review.
